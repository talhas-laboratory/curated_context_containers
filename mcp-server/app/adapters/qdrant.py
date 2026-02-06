"""Qdrant adapter for MCP server."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Tuple
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Chunk, Document

settings = get_settings()
LOGGER = logging.getLogger(__name__)


class QdrantAdapter:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            prefer_grpc=False,
            timeout=3.0,
            check_compatibility=False,
        )
        self.collections: set[str] = set()
        self.max_retries = 2
        self.retry_backoff = 0.25

    def _collection_name(self, container_id: str, modality: str = "text") -> str:
        return f"c_{container_id}_{modality}"

    def ensure_collection(self, container_id: str, modality: str = "text", dims: int | None = None) -> None:
        """Ensure the collection exists before searching."""
        name = self._collection_name(container_id, modality)
        if name in self.collections:
            return
        try:
            self.client.get_collection(name)
        except UnexpectedResponse:
            self.client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(
                    size=dims or settings.embedding_dims,
                    distance=qmodels.Distance.COSINE,
                ),
            )
        self.collections.add(name)

    def _build_filter(self, modalities: List[str] | None) -> qmodels.Filter | None:
        if not modalities:
            return None
        return qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="modality",
                    match=qmodels.MatchAny(any=modalities),
                )
            ]
        )

    async def search_batch(
        self,
        session: AsyncSession,
        container_ids: List[UUID] | None,
        vector: List[float],
        limit: int,
        modalities: List[str] | None = None,
    ) -> List[Tuple[Chunk, Document, float]]:
        """Search multiple containers in parallel."""
        if not container_ids:
            return []
        
        tasks = [self.search(session, [cid], vector, limit, modalities=modalities) for cid in container_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        combined = []
        for result in results:
            if isinstance(result, list):
                combined.extend(result)
        return combined

    async def search(
        self,
        session: AsyncSession,
        container_ids: List[UUID] | None,
        vector: List[float],
        limit: int,
        modalities: List[str] | None = None,
    ) -> List[Tuple[Chunk, Document, float]]:
        loop = asyncio.get_running_loop()
        container_hex = [str(cid) for cid in container_ids] if container_ids else None
        target_modalities = modalities or ["text"]

        def _search():
            results = []
            target_collections = container_hex or []
            if not target_collections:
                # fallback to single default collection; future: enumerate
                target_collections = ["00000000-0000-0000-0000-000000000001"]
            for cid in target_collections:
                for modality in target_modalities:
                    collection = self._collection_name(cid, modality)
                    self.ensure_collection(cid, modality)
                    hits = []
                    for attempt in range(self.max_retries + 1):
                        try:
                            search_fn = (
                                getattr(self.client, "query_points", None)
                                or getattr(self.client, "search_points", None)
                                or getattr(self.client, "search", None)
                            )
                            if not search_fn:
                                raise AttributeError("qdrant_client missing search method")
                            # query_points accepts `query` instead of `query_vector`
                            kwargs = {
                                "collection_name": collection,
                                "limit": limit,
                                "with_vectors": False,
                                "with_payload": True,
                            }
                            if "query_vector" in search_fn.__code__.co_varnames or search_fn.__name__ == "search_points":
                                kwargs["query_vector"] = vector
                            else:
                                kwargs["query"] = vector
                            result = search_fn(**kwargs)
                            if hasattr(result, "points"):
                                hits = list(result.points or [])
                            else:
                                hits = list(result or [])
                            break
                        except Exception as e:  # pragma: no cover - runtime safeguard
                            LOGGER.warning(
                                "qdrant_search_failed",
                                extra={
                                    "collection": collection,
                                    "attempt": attempt,
                                    "error": str(e),
                                },
                            )
                            if attempt >= self.max_retries:
                                break
                            time.sleep(self.retry_backoff * (attempt + 1))
                    for hit in hits:
                        payload = hit.payload or {}
                        chunk_id = payload.get("chunk_id")
                        doc_id = payload.get("doc_id")
                        payload_container = payload.get("container_id", cid)
                        payload_modality = payload.get("modality")
                        if not chunk_id or not doc_id:
                            continue
                        try:
                            UUID(str(chunk_id))
                            UUID(str(doc_id))
                        except Exception:
                            continue
                        if modalities and payload_modality and payload_modality not in modalities:
                            # Defensive guard if payload doesn't match filter
                            continue
                        results.append(
                            (
                                chunk_id,
                                doc_id,
                                str(payload_container),
                                float(hit.score or 0.0),
                            )
                        )
            return results

        hit_payloads = await loop.run_in_executor(None, _search)
        if not hit_payloads:
            return []

        chunk_ids = [UUID(cid) for cid, *_ in hit_payloads if cid]
        stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.doc_id)
            .where(Chunk.id.in_(chunk_ids))
        )
        rows = (await session.execute(stmt)).all()
        chunk_map = {str(row[0].id): row for row in rows}

        results: List[Tuple[Chunk, Document, float]] = []
        for chunk_id, _doc_id, _container_id, score in hit_payloads:
            try:
                normalized_id = str(UUID(str(chunk_id)))
            except Exception:
                normalized_id = str(chunk_id)
            row = chunk_map.get(normalized_id)
            if not row:
                continue
            chunk, doc = row
            results.append((chunk, doc, score))
        return results

    async def delete_document(self, container_id: str, document_id: str) -> None:
        """Delete all vector points associated with a document."""
        if not document_id:
            return
        loop = asyncio.get_running_loop()

        def _delete():
            for modality in ("text", "pdf", "image"):
                collection = self._collection_name(container_id, modality)
                self.ensure_collection(container_id, modality)
                selector = qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="doc_id",
                                match=qmodels.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                )
                try:
                    self.client.delete(collection_name=collection, points_selector=selector)
                except Exception as exc:  # pragma: no cover - runtime safeguard
                    LOGGER.warning(
                        "qdrant_delete_failed",
                        extra={
                            "collection": collection,
                            "doc_id": document_id,
                            "error": str(exc),
                        },
                    )

        await loop.run_in_executor(None, _delete)

    async def delete_container(self, container_id: str, modalities: List[str] | None = None) -> None:
        """Delete all collections associated with a container (best-effort)."""
        if not container_id:
            return
        loop = asyncio.get_running_loop()
        target_modalities = sorted(
            {
                *(modalities or []),
                "text",
                "pdf",
                "image",
                "web",
            }
        )

        def _delete():
            for modality in target_modalities:
                collection = self._collection_name(container_id, modality)
                try:
                    self.client.delete_collection(collection_name=collection)
                    self.collections.discard(collection)
                except UnexpectedResponse as exc:  # pragma: no cover - runtime safeguard
                    status_code = getattr(exc, "status_code", None)
                    if status_code and status_code == 404:
                        self.collections.discard(collection)
                        continue
                    LOGGER.warning(
                        "qdrant_collection_delete_failed",
                        extra={
                            "collection": collection,
                            "container_id": container_id,
                            "error": str(exc),
                        },
                    )
                except Exception as exc:  # pragma: no cover - runtime safeguard
                    LOGGER.warning(
                        "qdrant_collection_delete_failed",
                        extra={
                            "collection": collection,
                            "container_id": container_id,
                            "error": str(exc),
                        },
                    )

        await loop.run_in_executor(None, _delete)


qdrant_adapter = QdrantAdapter()
