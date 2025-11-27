"""Qdrant adapter for ingestion workers."""
from __future__ import annotations

from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from workers.config import settings


class QdrantAdapter:
    def __init__(self, client: Optional[QdrantClient] = None) -> None:
        self.client = client or QdrantClient(
            url=settings.qdrant_url,
            prefer_grpc=False,
            timeout=3.0,
            check_compatibility=False,
        )
        self.collections: set[str] = set()

    def _collection_name(self, container_id: str) -> str:
        return f"c_{container_id}"

    def ensure_collection(self, container_id: str) -> None:
        name = self._collection_name(container_id)
        if name in self.collections:
            return
        try:
            self.client.get_collection(name)
        except UnexpectedResponse:
            self.client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(
                    size=settings.embedding_dims,
                    distance=qmodels.Distance.COSINE,
                ),
            )
        self.collections.add(name)

    def upsert(self, container_id: str, vectors: List[qmodels.PointStruct]) -> None:
        name = self._collection_name(container_id)
        self.ensure_collection(container_id)
        self.client.upsert(collection_name=name, points=vectors)

    def search_similar(
        self,
        container_id: str,
        vector: List[float],
        limit: int = 1,
    ) -> List[qmodels.ScoredPoint]:
        name = self._collection_name(container_id)
        self.ensure_collection(container_id)
        try:
            search_fn = (
                getattr(self.client, "query_points", None)
                or getattr(self.client, "search_points", None)
                or getattr(self.client, "search", None)
            )
            if not search_fn:
                raise AttributeError("qdrant_client missing search method")
            kwargs = {
                "collection_name": name,
                "limit": limit,
                "with_payload": True,
                "with_vectors": False,
            }
            if "query_vector" in search_fn.__code__.co_varnames or search_fn.__name__ == "search_points":
                kwargs["query_vector"] = vector
            else:
                kwargs["query"] = vector
            result = search_fn(**kwargs)
            if hasattr(result, "points"):
                return list(result.points or [])
            return list(result or [])
        except Exception:
            return []
