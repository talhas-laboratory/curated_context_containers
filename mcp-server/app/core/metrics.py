"""Prometheus metrics helpers for the MCP server."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

metrics_router = APIRouter()

REQUEST_COUNTER = Counter(
    "llc_search_requests_total",
    "Total search requests",
    labelnames=("container", "mode", "status"),
)
RESULTS_RETURNED = Histogram(
    "llc_search_results_returned",
    "Distribution of search results returned",
    labelnames=("mode",),
    buckets=(0, 1, 3, 5, 10, 20, 50),
)
STAGE_LATENCY = Histogram(
    "llc_search_stage_latency_seconds",
    "Latency per search stage",
    labelnames=("stage",),
    buckets=(0.01, 0.05, 0.1, 0.2, 0.35, 0.5, 1, 2),
)
TOTAL_LATENCY = Histogram(
    "llc_search_total_latency_seconds",
    "End-to-end search latency",
    buckets=(0.02, 0.05, 0.1, 0.25, 0.5, 1, 2, 4),
)
INGEST_CHUNKS = Counter(
    "llc_ingest_chunks_total",
    "Total chunks ingested per container and modality",
    labelnames=("container", "modality"),
)
DEDUP_HITS = Counter(
    "llc_dedup_hits_total",
    "Chunks skipped due to semantic deduplication",
    labelnames=("container", "threshold"),
)


def observe_search(mode: str, timings_ms: Dict[str, int], returned: int, container_ids: list[str], issues: list[str]) -> None:
    """Record Prometheus metrics for a search response."""
    status = "success" if not issues else "partial" if "LATENCY_BUDGET_EXCEEDED" in issues else "error"
    for container_id in container_ids:
        REQUEST_COUNTER.labels(container=container_id, mode=mode, status=status).inc()
    RESULTS_RETURNED.labels(mode=mode).observe(max(returned, 0))
    total_ms = timings_ms.get("total_ms")
    if total_ms is not None:
        TOTAL_LATENCY.observe(max(total_ms, 1) / 1000)
    for stage_key, value in timings_ms.items():
        if not stage_key.endswith("_ms") or stage_key == "total_ms":
            continue
        stage = stage_key.replace("_ms", "")
        STAGE_LATENCY.labels(stage=stage).observe(max(value, 1) / 1000)


def observe_ingest_chunks(container_id: str, modality: str, count: int) -> None:
    """Record chunk ingestion metrics."""
    INGEST_CHUNKS.labels(container=container_id, modality=modality).inc(count)


def observe_dedup_hits(container_id: str, threshold: float, count: int) -> None:
    """Record semantic deduplication metrics."""
    DEDUP_HITS.labels(container=container_id, threshold=str(threshold)).inc(count)


@metrics_router.get("/metrics", tags=["metrics"])
async def prometheus_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
