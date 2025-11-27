"""Prometheus metrics helpers for ingestion workers."""
from __future__ import annotations

from prometheus_client import Counter, Histogram, start_http_server

from workers.config import settings

METRICS_ENABLED = getattr(settings, "metrics_enabled", True)

INGEST_DURATION = Histogram(
    "llc_ingest_duration_seconds",
    "Ingestion duration per job",
    labelnames=("modality",),
)
CACHE_HITS = Counter(
    "llc_embedding_cache_hits_total",
    "Embedding cache hits per modality",
    labelnames=("modality",),
)
CACHE_MISSES = Counter(
    "llc_embedding_cache_misses_total",
    "Embedding cache misses per modality",
    labelnames=("modality",),
)
SEMANTIC_DEDUPS = Counter(
    "llc_semantic_dedup_chunks_total",
    "Chunks skipped due to semantic dedup",
    labelnames=("modality",),
)
QDRANT_UPSERTS = Counter(
    "llc_qdrant_upserts_total",
    "Chunks upserted into Qdrant",
    labelnames=("modality",),
)


def start_metrics_server() -> None:
    """Expose Prometheus metrics if enabled."""
    if not METRICS_ENABLED:
        return
    port = getattr(settings, "metrics_port", 9105)
    addr = getattr(settings, "metrics_host", "0.0.0.0")
    start_http_server(port, addr=addr)


def observe_ingest(
    *,
    modality: str,
    duration_ms: int,
    cache_hits: int,
    cache_misses: int,
    deduped_chunks: int,
    qdrant_points: int,
) -> None:
    if not METRICS_ENABLED:
        return
    label = {"modality": modality}
    INGEST_DURATION.labels(**label).observe(max(duration_ms, 1) / 1000)
    if cache_hits:
        CACHE_HITS.labels(**label).inc(cache_hits)
    if cache_misses:
        CACHE_MISSES.labels(**label).inc(cache_misses)
    if deduped_chunks:
        SEMANTIC_DEDUPS.labels(**label).inc(deduped_chunks)
    if qdrant_points:
        QDRANT_UPSERTS.labels(**label).inc(qdrant_points)
