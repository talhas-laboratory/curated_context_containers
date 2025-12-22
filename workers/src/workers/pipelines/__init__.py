"""Pipeline implementations for ingestion."""
from __future__ import annotations

import hashlib
import time
import uuid
from array import array
from pathlib import Path
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

import psycopg
import structlog
import yaml
from psycopg import Binary
from psycopg.types.json import Json
from qdrant_client.http import models as qmodels

from workers.adapters.embedder import EmbeddingClient
from workers.adapters.minio import minio_adapter
from workers.adapters.qdrant import QdrantAdapter
from workers.adapters.neo4j import neo4j_adapter
from workers.adapters import llm as llm_adapter
from workers.config import settings
from workers.metrics import observe_ingest
from workers.util.image import load_image_bytes, make_thumbnail, infer_mime
from workers.util.pdf import extract_text_from_source
from .chunker import chunk_text

PipelineFn = Callable[[psycopg.Connection, dict, Optional[Callable[[], None]]], None]

LOGGER = structlog.get_logger()
EMBEDDER = EmbeddingClient()
QDRANT = QdrantAdapter()
CACHE_TTL_SECONDS = max(0, settings.embedding_cache_ttl_seconds)
MANIFEST_ROOT = Path(settings.manifests_path)
GRAPH_ENABLED_DEFAULT = False


def _clamp_threshold(value: float | None, default: float) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        threshold = default
    return max(0.0, min(1.0, threshold))


def _load_manifest(container_name: str | None) -> dict:
    if not container_name:
        return {}
    path = MANIFEST_ROOT / f"{container_name}.yaml"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}
    except Exception:  # pragma: no cover - best-effort manifest read
        return {}


def _container_context(conn: psycopg.Connection, payload: dict) -> dict:
    """Resolve manifest + sizing knobs for this container."""
    manifest = payload.get("manifest") or {}
    container_name = payload.get("container_name")
    embedder_version = payload.get("embedder_version") or "stub-0"
    dims = payload.get("container_dims") or settings.embedding_dims
    graph_cfg = {}

    if (not manifest) and container_name:
        manifest = _load_manifest(container_name)

    if not container_name or embedder_version == "stub-0" or dims == settings.embedding_dims:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name, dims, embedder_version FROM containers WHERE id = %s LIMIT 1",
                    (payload.get("container_id"),),
                )
                row = cur.fetchone()
            if row:
                container_name = container_name or row.get("name") if isinstance(row, dict) else row[0]
                dims = row.get("dims", dims) if isinstance(row, dict) else (row[1] if len(row) > 1 else dims)
                embedder_version = (
                    row.get("embedder_version", embedder_version)
                    if isinstance(row, dict)
                    else (row[2] if len(row) > 2 else embedder_version)
                )
                if not manifest and container_name:
                    manifest = _load_manifest(container_name)
                if not graph_cfg and manifest:
                    graph_cfg = manifest.get("graph") or {}
        except Exception:  # pragma: no cover - optional lookup
            pass

    semantic_threshold = _clamp_threshold(
        (manifest.get("dedup") or {}).get("semantic_threshold"),
        settings.semantic_dedup_threshold,
    )
    image_cfg = manifest.get("image") or {}
    return {
        "manifest": manifest,
        "container_name": container_name,
        "semantic_threshold": semantic_threshold,
        "dims": dims,
        "embedder_version": embedder_version,
        "image_thumbnail_max_edge": image_cfg.get("thumbnail_max_edge", settings.image_thumbnail_max_edge),
        "image_compress_quality": image_cfg.get("compress_quality", settings.image_compress_quality),
        "graph_enabled": (graph_cfg.get("enabled") if graph_cfg else GRAPH_ENABLED_DEFAULT),
        "graph_llm_enabled": bool(
            graph_cfg.get("llm_extractor") if graph_cfg else payload.get("graph_llm_enabled", settings.graph_llm_enabled)
        ),
    }


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


def _extract_entities_relations(
    text: str,
    chunk_id: uuid.UUID,
    doc_id: uuid.UUID,
    container_id: uuid.UUID,
    doc_node_exists: bool,
    use_llm: bool = False,
) -> tuple[list[dict], list[dict], bool]:
    """
    Entity/relation extractor with optional LLM-assisted path.
    Falls back to heuristic extraction when LLM is disabled or fails.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    doc_added = doc_node_exists
    cleaned_text = (text or "").strip()
    sentences = [s.strip() for s in cleaned_text.replace("\n", " ").split(".") if s.strip()]
    chunk_summary = (sentences[0] if sentences else cleaned_text)[:200]
    chunk_label = chunk_summary[:64]
    chunk_node_id = f"chunk:{chunk_id}"
    doc_node_id = f"doc:{doc_id}"

    if not doc_node_exists:
        nodes.append(
            {
                "id": doc_node_id,
                "label": doc_node_id,
                "type": "Document",
                "summary": None,
                "properties": {"doc_id": str(doc_id), "confidence": 0.9},
                "source_chunk_ids": [],
            }
        )
        doc_added = True
    nodes.append(
        {
            "id": chunk_node_id,
            "label": chunk_label,
            "type": "Chunk",
            "summary": chunk_summary,
            "properties": {"doc_id": str(doc_id), "confidence": 0.8},
            "source_chunk_ids": [str(chunk_id)],
        }
    )
    edges.append(
        {
            "source": doc_node_id,
            "target": chunk_node_id,
            "type": "HAS_CHUNK",
            "properties": {"confidence": 0.95},
            "source_chunk_ids": [str(chunk_id)],
        }
    )

    if use_llm and settings.graph_llm_enabled:
        llm_entities, llm_relations = llm_adapter.call_llm_for_graph(
            container_id=str(container_id),
            document_id=str(doc_id),
            chunk_id=str(chunk_id),
            chunk_text=cleaned_text,
        )
        id_map: set[str] = set()
        for ent in llm_entities:
            ent_id = ent.get("id")
            if not ent_id or ent_id in id_map:
                continue
            id_map.add(ent_id)
            chunk_ids = ent.get("source_chunk_ids") or [str(chunk_id)]
            nodes.append(
                {
                    "id": ent_id,
                    "label": ent.get("label") or ent_id,
                    "type": ent.get("type") or "Concept",
                    "summary": ent.get("summary") or ent.get("label"),
                    "properties": {**(ent.get("properties") or {}), "confidence": 0.7},
                    "source_chunk_ids": chunk_ids,
                }
            )
            edges.append(
                {
                    "source": chunk_node_id,
                    "target": ent_id,
                    "type": "MENTIONS",
                    "properties": {"confidence": 0.7, "source": "llm"},
                    "source_chunk_ids": chunk_ids,
                }
            )
        for rel in llm_relations:
            src = rel.get("source")
            tgt = rel.get("target")
            if not src or not tgt:
                continue
            edges.append(
                {
                    "source": src,
                    "target": tgt,
                    "type": rel.get("type") or "RELATED_TO",
                    "properties": rel.get("properties") or {"confidence": 0.65},
                    "source_chunk_ids": rel.get("source_chunk_ids") or [str(chunk_id)],
                }
            )
        if llm_entities or llm_relations:
            return nodes, edges, doc_added

    # Heuristic fallback
    seen_entities: set[str] = set()
    cooccur_pairs: list[tuple[str, str]] = []
    for sent in sentences or [cleaned_text]:
        tokens = [tok for tok in sent.split() if tok]
        local_entities: list[str] = []
        span = []
        for tok in tokens:
            if tok[0].isupper():
                span.append(tok)
            else:
                if span:
                    local_entities.append(" ".join(span))
                    span = []
        if span:
            local_entities.append(" ".join(span))
        for ent in local_entities:
            normalized = "".join(ch for ch in ent if ch.isalnum() or ch.isspace()).strip()
            if len(normalized) < 4:
                continue
            ent_id = f"ent:{normalized.lower().replace(' ', '_')}"
            if ent_id in seen_entities:
                continue
            seen_entities.add(ent_id)
            nodes.append(
                {
                    "id": ent_id,
                    "label": normalized,
                    "type": "Entity",
                    "summary": normalized[:128],
                    "properties": {"confidence": 0.55},
                    "source_chunk_ids": [str(chunk_id)],
                }
            )
            edges.append(
                {
                    "source": chunk_node_id,
                    "target": ent_id,
                    "type": "MENTIONS",
                    "properties": {"confidence": 0.6},
                    "source_chunk_ids": [str(chunk_id)],
                }
            )
            local_entities[local_entities.index(ent)] = ent_id  # replace label with id for co-occurrence
        ent_ids = [eid for eid in local_entities if eid.startswith("ent:")]
        for i in range(len(ent_ids)):
            for j in range(i + 1, len(ent_ids)):
                cooccur_pairs.append((ent_ids[i], ent_ids[j]))
    for a, b in cooccur_pairs:
        edges.append(
            {
                "source": a,
                "target": b,
                "type": "CO_OCCURS",
                "properties": {"confidence": 0.45},
                "source_chunk_ids": [str(chunk_id)],
            }
        )
    return nodes, edges, doc_added


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
    container_uuid: uuid.UUID,
    vector: List[float],
    modality: str,
    threshold: float,
) -> Optional[tuple[uuid.UUID, float]]:
    if not vector or threshold <= 0:
        return None
    hits = QDRANT.search_similar(str(container_uuid), vector, limit=1, modality=modality)
    if not hits:
        return None
    hit = hits[0]
    score = float(hit.score or 0.0)
    if score < threshold:
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
    modality: str,
    embed_fn: Callable[[], List[float]],
    dims: int,
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

    vector = embed_fn()
    cache_miss = 1
    cur.execute(
        """
        INSERT INTO embedding_cache (cache_key, modality, dims, vector)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (cache_key)
        DO UPDATE SET vector = EXCLUDED.vector, last_used_at = NOW()
        """,
        (cache_key, modality, dims, Binary(_vector_to_bytes(vector))),
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
    context = _container_context(conn, payload)
    semantic_threshold = context["semantic_threshold"]
    dims = context["dims"]
    embedder_version = context["embedder_version"]
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
        qdrant_points: List[qmodels.PointStruct] = []
        cache_hits = 0
        cache_misses = 0
        deduped_chunks = 0
        graph_nodes: List[dict] = []
        graph_edges: List[dict] = []
        doc_node_added = False
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
            cache_key = f"{chunk_hash}:{modality}:{embedder_version}"
            vector, hit, miss = _embedding_from_cache_or_compute(
                cur,
                cache_key,
                modality,
                embed_fn=lambda c=chunk: EMBEDDER.embed_text([c])[0],
                dims=dims,
            )
            cache_hits += hit
            cache_misses += miss

            dedup_target: Optional[uuid.UUID] = None
            dedup_score: Optional[float] = None
            semantic_match = _semantic_duplicate_target(container_uuid, vector, modality, semantic_threshold)
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
                    embedder_version,
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
            if context.get("graph_enabled"):
                entities, relations, doc_node_added = _extract_entities_relations(
                    chunk,
                    chunk_id,
                    doc_id,
                    container_uuid,
                    doc_node_added,
                    use_llm=context.get("graph_llm_enabled", False),
                )
                for ent in entities:
                    ent.setdefault("source_chunk_ids", []).append(str(chunk_id))
                    graph_nodes.append(ent)
                for rel in relations:
                    rel.setdefault("source_chunk_ids", []).append(str(chunk_id))
                    graph_edges.append(rel)
    if heartbeat:
        heartbeat()
    _update_container_stats(conn, container_uuid)
    if qdrant_points:
        try:
            QDRANT.upsert(str(container_uuid), modality, qdrant_points, dims=dims)
        except Exception as exc:  # pragma: no cover - Qdrant optional during dev
            LOGGER.warning("qdrant_upsert_failed", error=str(exc))
    if context.get("graph_enabled") and graph_nodes:
        graph_vectors: List[qmodels.PointStruct] = []
        for node in graph_nodes:
            summary_text = (node.get("summary") or node.get("label") or "")[:512]
            if not summary_text:
                continue
            try:
                vector = EMBEDDER.embed_text([summary_text])[0]
            except Exception as exc:  # pragma: no cover - embed optional
                LOGGER.warning("graph_node_embed_failed", node=node.get("id"), exc_info=exc)
                continue
            graph_vectors.append(
                qmodels.PointStruct(
                    id=node.get("id"),
                    vector=vector,
                    payload={
                        "graph_node_id": node.get("id"),
                        "container_id": str(container_uuid),
                        "type": node.get("type"),
                        "label": node.get("label"),
                        "source_chunk_ids": node.get("source_chunk_ids") or [],
                    },
                )
            )
        if graph_vectors:
            try:
                QDRANT.upsert(str(container_uuid), "graph_node", graph_vectors, dims=dims)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("qdrant_graph_node_upsert_failed", container=str(container_uuid), exc_info=exc)
    if context.get("graph_enabled") and (graph_nodes or graph_edges):
        try:
            neo4j_adapter.upsert(str(container_uuid), graph_nodes, graph_edges)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("graph_upsert_failed", container=str(container_uuid), exc_info=exc)
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


def _image_pipeline(conn: psycopg.Connection, job: dict, heartbeat: Optional[Callable[[], None]]) -> None:
    start = time.perf_counter()
    payload = job.get("payload", {})
    source = payload.get("source", {})
    container_id = payload.get("container_id")
    if not container_id:
        LOGGER.warning("ingest_missing_container", job_id=job.get("id"))
        return
    context = _container_context(conn, payload)
    semantic_threshold = context["semantic_threshold"]
    dims = context["dims"]
    embedder_version = context["embedder_version"]
    container_uuid = uuid.UUID(str(container_id))

    image_bytes, mime_hint, filename = load_image_bytes(source)
    if not image_bytes:
        LOGGER.warning("ingest_image_missing_bytes", job_id=job.get("id"), uri=source.get("uri"))
        return

    mime = (infer_mime(mime_hint or source.get("mime"), filename)) or "image/jpeg"
    doc_hash = hashlib.sha256(image_bytes).hexdigest()
    thumb_bytes, thumb_meta = make_thumbnail(
        image_bytes,
        max_edge=context["image_thumbnail_max_edge"],
        quality=context["image_compress_quality"],
    )

    with conn.cursor() as cur:
        doc_id, duplicate = _upsert_document(cur, container_uuid, source, mime, doc_hash)
        if duplicate:
            cur.execute("SELECT 1 FROM chunks WHERE doc_id = %s LIMIT 1", (doc_id,))
            has_chunks = cur.fetchone() is not None
            if has_chunks:
                LOGGER.info(
                    "ingest_duplicate",
                    container_id=str(container_uuid),
                    uri=source.get("uri"),
                    doc_id=str(doc_id),
                )
                conn.commit()
                return

        paths = minio_adapter.store_image(
            str(container_uuid),
            str(doc_id),
            image_bytes,
            thumbnail_bytes=thumb_bytes,
            filename=filename,
            mime=mime,
        )

        chunk_id = uuid.uuid4()
        provenance = {
            "source_uri": source.get("uri"),
            "ingested_at": datetime.utcnow().isoformat(),
            "pipeline": "image",
            "chunk_index": 0,
            "total_chunks": 1,
        }
        meta = {**(source.get("meta") or {})}
        meta.update(
            {
                "image_hash": doc_hash,
                "mime": mime,
                "original_path": paths.get("original"),
                "thumbnail_path": paths.get("thumbnail"),
            }
        )
        if thumb_meta:
            meta.update(thumb_meta)

        cache_key = f"{doc_hash}:image:{embedder_version}"
        vector, cache_hit, cache_miss = _embedding_from_cache_or_compute(
            cur,
            cache_key,
            "image",
            embed_fn=lambda: EMBEDDER.embed_image([image_bytes])[0],
            dims=dims,
        )
        dedup_target: Optional[uuid.UUID] = None
        dedup_score: Optional[float] = None
        semantic_match = _semantic_duplicate_target(container_uuid, vector, "image", semantic_threshold)
        if semantic_match:
            dedup_target, dedup_score = semantic_match
            meta["semantic_dedup_score"] = dedup_score
            LOGGER.info(
                "ingest_semantic_dedup",
                container_id=str(container_uuid),
                uri=source.get("uri"),
                modality="image",
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
                "image",
                None,
                Json(provenance),
                Json(meta),
                embedder_version,
                dedup_target,
            ),
        )

    if heartbeat:
        heartbeat()
    _update_container_stats(conn, container_uuid)
    qdrant_points: List[qmodels.PointStruct] = []
    if not dedup_target:
        qdrant_points.append(
            qmodels.PointStruct(
                id=chunk_id.hex,
                vector=vector,
                payload={
                    "chunk_id": chunk_id.hex,
                    "doc_id": str(doc_id),
                    "container_id": str(container_uuid),
                    "modality": "image",
                    "uri": paths.get("thumbnail") or paths.get("original") or source.get("uri"),
                },
            )
        )

    if qdrant_points:
        try:
            QDRANT.upsert(str(container_uuid), "image", qdrant_points, dims=dims)
        except Exception as exc:  # pragma: no cover - Qdrant optional during dev
            LOGGER.warning("qdrant_upsert_failed", error=str(exc))
    conn.commit()
    duration = int((time.perf_counter() - start) * 1000)
    LOGGER.info(
        "ingest_complete",
        container_id=str(container_uuid),
        uri=source.get("uri"),
        modality="image",
        chunks=1,
        cache_hits=cache_hit,
        cache_misses=cache_miss,
        deduped_chunks=1 if dedup_target else 0,
        qdrant_points=len(qdrant_points),
        duration_ms=duration,
    )
    observe_ingest(
        modality="image",
        duration_ms=duration,
        cache_hits=cache_hit,
        cache_misses=cache_miss,
        deduped_chunks=1 if dedup_target else 0,
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
    meta = source.get("meta") or {}
    if meta.get("image_base64") or meta.get("image_bytes"):
        return "image"
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
    elif modality == "image":
        _image_pipeline(conn, job, heartbeat)
    else:
        _text_pipeline(conn, job, heartbeat)


PIPELINE_REGISTRY: Dict[str, PipelineFn] = {
    "text": _text_pipeline,
    "pdf": _pdf_pipeline,
    "image": _image_pipeline,
    "refresh": lambda conn, job, heartbeat=None: None,
    "export": lambda conn, job, heartbeat=None: None,
    "ingest": _ingest_pipeline,
}


def run_pipeline(conn: psycopg.Connection, kind: str, job: dict, heartbeat: Optional[Callable[[], None]] = None) -> None:
    PIPELINE_REGISTRY.get(kind, _ingest_pipeline)(conn, job, heartbeat)
