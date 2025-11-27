"""Pipeline implementations for ingestion."""
from __future__ import annotations

import hashlib
import time
import uuid
from array import array
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import psycopg
import structlog
from psycopg import Binary
from psycopg.types.json import Json
from qdrant_client.http import models as qmodels

from workers.adapters.embedder import EmbeddingClient
from workers.adapters.minio import minio_adapter
from workers.adapters.qdrant import QdrantAdapter
from workers.config import settings
from workers.metrics import observe_ingest
from workers.util.pdf import extract_text_from_source
from .chunker import chunk_text

PipelineFn = Callable[[psycopg.Connection, dict, Optional[Callable[[], None]]], None]

LOGGER = structlog.get_logger()
EMBEDDER = EmbeddingClient()
QDRANT = QdrantAdapter()
CACHE_TTL_SECONDS = max(0, settings.embedding_cache_ttl_seconds)
SEMANTIC_THRESHOLD = max(0.0, min(1.0, settings.semantic_dedup_threshold))


def _ensure_text(source: dict, modality: str) -> str:
    meta = source.get("meta") or {}
    text = meta.get("text")
    if text:
        return text
    if modality == "pdf":  # TODO: add page render thumbnails when renderer lands
        extracted = extract_text_from_source(source)
        if extracted:
            return extracted
    uri = source.get("uri") or "unknown"
    return f"Placeholder content for {uri}"


def _upsert_document(cur, container_uuid, source, mime, doc_hash):
    cur.execute(
        "SELECT id FROM documents WHERE container_id = %s AND hash = %s",
        (container_uuid, doc_hash),
    )
    row = cur.fetchone()
    if row:
        doc_id = row["id"]
        cur.execute("SELECT 1 FROM chunks WHERE doc_id = %s LIMIT 1", (doc_id,))
        has_chunks = cur.fetchone() is not None
        if has_chunks:
            return doc_id, True
        # Stale document with no chunks; treat as re-ingest and refresh metadata
        cur.execute(
            """
            UPDATE documents
               SET uri = %s,
                   mime = %s,
                   hash = %s,
                   title = %s,
                   meta = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (
                source.get("uri"),
                mime,
                doc_hash,
                source.get("title"),
                Json(source.get("meta") or {}),
                doc_id,
            ),
        )
        return doc_id, False

    doc_id = uuid.uuid4()
    cur.execute(
        """
        INSERT INTO documents (id, container_id, uri, mime, hash, title, meta)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            doc_id,
            container_uuid,
            source.get("uri"),
            mime,
            doc_hash,
            source.get("title"),
            Json(source.get("meta") or {}),
        ),
    )
    row = cur.fetchone()
    return row["id"], False


def _vector_to_bytes(vector: List[float]) -> bytes:
    arr = array("f", vector)
    return arr.tobytes()


def _bytes_to_vector(blob: bytes) -> List[float]:
    arr = array("f")
    arr.frombytes(blob)
    return list(arr)


def _is_cache_entry_stale(last_used_at) -> bool:
    if not CACHE_TTL_SECONDS or not last_used_at:
        return False
    current = datetime.now(timezone.utc)
    reference = last_used_at
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    age = current - reference
    return age.total_seconds() > CACHE_TTL_SECONDS


def _semantic_duplicate_target(
    container_uuid: uuid.UUID, vector: List[float]
) -> Optional[tuple[uuid.UUID, float]]:
    if not vector or SEMANTIC_THRESHOLD <= 0:
        return None
    hits = QDRANT.search_similar(str(container_uuid), vector, limit=1)
    if not hits:
        return None
    hit = hits[0]
    score = float(hit.score or 0.0)
    if score < SEMANTIC_THRESHOLD:
        return None
    payload = hit.payload or {}
    chunk_id = payload.get("chunk_id")
    if not chunk_id:
        return None
    try:
        return uuid.UUID(chunk_id), score
    except ValueError:
        return None


def _embedding_from_cache_or_compute(
    cur,
    cache_key: str,
    chunk: str,
    modality: str,
    embedder: EmbeddingClient = EMBEDDER,
) -> tuple[List[float], int, int]:
    """Retrieve embedding from cache or compute + refresh if stale."""
    cache_hit = 0
    cache_miss = 0
    cur.execute(
        "SELECT vector, last_used_at FROM embedding_cache WHERE cache_key = %s",
        (cache_key,),
    )
    row = cur.fetchone()
    if row:
        if isinstance(row, dict):
            vector_blob = row.get("vector")
            last_used = row.get("last_used_at")
        else:  # tuple fallback
            vector_blob = row[0]
            last_used = row[1]
    else:
        vector_blob = None
        last_used = None
    if vector_blob and not _is_cache_entry_stale(last_used):
        vector = _bytes_to_vector(vector_blob)
        cache_hit = 1
        cur.execute("UPDATE embedding_cache SET last_used_at = NOW() WHERE cache_key = %s", (cache_key,))
        return vector, cache_hit, cache_miss

    if vector_blob:
        cur.execute("DELETE FROM embedding_cache WHERE cache_key = %s", (cache_key,))

    vector = embedder.embed_text([chunk])[0]
    cache_miss = 1
    cur.execute(
        """
        INSERT INTO embedding_cache (cache_key, modality, dims, vector)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (cache_key)
        DO UPDATE SET vector = EXCLUDED.vector, last_used_at = NOW()
        """,
        (cache_key, modality, settings.embedding_dims, Binary(_vector_to_bytes(vector))),
    )
    return vector, cache_hit, cache_miss


def _ingest(conn: psycopg.Connection, job: dict, modality: str, heartbeat: Optional[Callable[[], None]]) -> None:
    start = time.perf_counter()
    payload = job.get("payload", {})
    source = payload.get("source", {})
    container_id = payload.get("container_id")
    if not container_id:
        LOGGER.warning("ingest_missing_container", job_id=job.get("id"))
        return
    container_uuid = uuid.UUID(str(container_id))
    text = _ensure_text(source, modality)
    if not text:
        LOGGER.warning("ingest_empty_text", job_id=job.get("id"))
        return

    mime = (source.get("mime") or ("application/pdf" if modality == "pdf" else "text/plain")).lower()
    fingerprint = (text or "").strip()
    if not fingerprint:
        fingerprint = (source.get("uri") or source.get("title") or "").strip()
    doc_hash = hashlib.sha256(f"{container_uuid}:{fingerprint}".encode()).hexdigest()

    with conn.cursor() as cur:
        doc_id, duplicate = _upsert_document(cur, container_uuid, source, mime, doc_hash)
        if duplicate:
            cur.execute("SELECT 1 FROM chunks WHERE doc_id = %s LIMIT 1", (doc_id,))
            has_chunks = cur.fetchone() is not None
            if not has_chunks:
                LOGGER.info(
                    "ingest_rebuild_missing_chunks",
                    container_id=str(container_uuid),
                    doc_id=str(doc_id),
                    uri=source.get("uri"),
                )
                duplicate = False
            else:
                LOGGER.info(
                    "ingest_duplicate",
                    container_id=str(container_uuid),
                    uri=source.get("uri"),
                    doc_id=str(doc_id),
                )
                conn.commit()
                return
        minio_adapter.store_raw(str(container_uuid), str(doc_id), source.get("uri"), text)

        chunk_list = chunk_text(text)
        if not chunk_list:
            chunk_list = [text]
        total_chunks = len(chunk_list)
        vectors: List[List[float]] = []
        qdrant_points: List[qmodels.PointStruct] = []
        cache_hits = 0
        cache_misses = 0
        deduped_chunks = 0
        for idx, chunk in enumerate(chunk_list):
            if heartbeat and idx % 5 == 0:
                heartbeat()
            chunk_id = uuid.uuid4()
            provenance = {
                "source_uri": source.get("uri"),
                "ingested_at": datetime.utcnow().isoformat(),
                "pipeline": modality,
                "chunk_index": idx,
                "total_chunks": total_chunks,
            }
            meta = source.get("meta") or {}
            meta = {**meta, "chunk_index": idx, "total_chunks": total_chunks}

            chunk_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            cache_key = f"{chunk_hash}:{modality}"
            vector, hit, miss = _embedding_from_cache_or_compute(cur, cache_key, chunk, modality)
            cache_hits += hit
            cache_misses += miss

            dedup_target: Optional[uuid.UUID] = None
            dedup_score: Optional[float] = None
            semantic_match = _semantic_duplicate_target(container_uuid, vector)
            if semantic_match:
                dedup_target, dedup_score = semantic_match
                meta["semantic_dedup_score"] = dedup_score
                deduped_chunks += 1
                LOGGER.info(
                    "ingest_semantic_dedup",
                    container_id=str(container_uuid),
                    uri=source.get("uri"),
                    modality=modality,
                    dedup_target=str(dedup_target),
                    score=dedup_score,
                )

            cur.execute(
                """
                INSERT INTO chunks (
                    id, container_id, doc_id, modality, text, provenance, meta, embedding_version, dedup_of
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chunk_id,
                    container_uuid,
                    doc_id,
                    modality,
                    chunk,
                    Json(provenance),
                    Json(meta),
                    "stub-0",
                    dedup_target,
                ),
            )
            if not dedup_target:
                qdrant_points.append(
                    qmodels.PointStruct(
                        id=chunk_id.hex,
                        vector=vector,
                        payload={
                            "chunk_id": chunk_id.hex,
                            "doc_id": str(doc_id),
                            "container_id": str(container_uuid),
                            "modality": modality,
                        },
                )
            )
    if heartbeat:
        heartbeat()
    _update_container_stats(conn, container_uuid)
    if qdrant_points:
        try:
            QDRANT.upsert(str(container_uuid), qdrant_points)
        except Exception as exc:  # pragma: no cover - Qdrant optional during dev
            LOGGER.warning("qdrant_upsert_failed", error=str(exc))
    conn.commit()
    duration = int((time.perf_counter() - start) * 1000)
    LOGGER.info(
        "ingest_complete",
        container_id=str(container_uuid),
        uri=source.get("uri"),
        modality=modality,
        chunks=total_chunks,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        deduped_chunks=deduped_chunks,
        qdrant_points=len(qdrant_points),
        duration_ms=duration,
    )
    observe_ingest(
        modality=modality,
        duration_ms=duration,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        deduped_chunks=deduped_chunks,
        qdrant_points=len(qdrant_points),
    )


def _update_container_stats(
    conn: psycopg.Connection,
    container_uuid: uuid.UUID,
) -> None:
    """Update container stats and last_ingest timestamp."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE containers
               SET stats = COALESCE(stats, '{}'::jsonb) || jsonb_build_object(
                   'document_count', (SELECT COUNT(*) FROM documents WHERE container_id = %(container_id)s),
                   'chunk_count', (SELECT COUNT(*) FROM chunks WHERE container_id = %(container_id)s),
                   'last_ingest', to_jsonb(NOW())
               ),
                   updated_at = NOW()
             WHERE id = %(container_id)s
            """,
            {"container_id": container_uuid},
        )


def _text_pipeline(conn: psycopg.Connection, job: dict, heartbeat: Optional[Callable[[], None]]) -> None:
    _ingest(conn, job, "text", heartbeat)


def _pdf_pipeline(conn: psycopg.Connection, job: dict, heartbeat: Optional[Callable[[], None]]) -> None:
    _ingest(conn, job, "pdf", heartbeat)


def _detect_modality(source: dict | None) -> str:
    source = source or {}
    modality = (source.get("modality") or "").lower()
    if modality in {"text", "pdf", "image"}:
        return modality
    mime = (source.get("mime") or "").lower()
    uri = (source.get("uri") or "").lower()
    if mime.startswith("application/pdf") or uri.endswith(".pdf"):
        return "pdf"
    if mime.startswith("image/") or uri.endswith((".jpg", ".jpeg", ".png", ".gif")):
        return "image"
    return "text"


def _ingest_pipeline(conn: psycopg.Connection, job: dict, heartbeat: Optional[Callable[[], None]]) -> None:
    source = job.get("payload", {}).get("source", {})
    modality = _detect_modality(source)
    if modality == "pdf":
        _pdf_pipeline(conn, job, heartbeat)
    else:
        _text_pipeline(conn, job, heartbeat)


PIPELINE_REGISTRY: Dict[str, PipelineFn] = {
    "text": _text_pipeline,
    "pdf": _pdf_pipeline,
    "ingest": _ingest_pipeline,
}


def run_pipeline(conn: psycopg.Connection, kind: str, job: dict, heartbeat: Optional[Callable[[], None]] = None) -> None:
    PIPELINE_REGISTRY.get(kind, _ingest_pipeline)(conn, job, heartbeat)
