"""Data models for LLC Agents SDK."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    """Search mode for container queries."""

    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    BM25 = "bm25"


class ContainerState(str, Enum):
    """Container lifecycle state."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ALL = "all"


class JobStatus(str, Enum):
    """Job execution status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ContainerStats(BaseModel):
    """Container statistics."""

    document_count: int = Field(alias="documents")
    chunk_count: int = Field(alias="chunks")
    text_chunks: Optional[int] = None
    image_chunks: Optional[int] = None
    size_mb: float
    last_ingest: Optional[datetime] = None

    class Config:
        populate_by_name = True


class Container(BaseModel):
    """Container metadata."""

    id: str
    name: str
    theme: str
    description: Optional[str] = None
    modalities: list[str]
    state: str
    embedder: Optional[str] = None
    embedder_version: Optional[str] = None
    dims: Optional[int] = None
    stats: Optional[ContainerStats] = None
    created_at: datetime
    updated_at: datetime
    created_by_agent: Optional[str] = None
    mission_context: Optional[str] = None


class SearchResult(BaseModel):
    """A single search result."""

    chunk_id: str
    doc_id: str
    container_id: str
    container_name: str
    title: str
    snippet: str
    uri: Optional[str] = None
    score: float
    stage_scores: Optional[dict[str, float]] = None
    provenance: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response with results and diagnostics."""

    query: str
    containers: list[str]
    mode: str
    results: list[SearchResult]
    total_hits: int
    returned: int
    diagnostics: Optional[dict[str, Any]] = None
    timings_ms: Optional[dict[str, float]] = None
    issues: Optional[list[dict[str, Any]]] = None


class Job(BaseModel):
    """Ingestion job."""

    job_id: str
    source_uri: Optional[str] = None
    status: JobStatus
    error: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Source(BaseModel):
    """Source to ingest."""

    uri: str
    title: Optional[str] = None
    mime: Optional[str] = None
    modality: Optional[str] = None
    meta: Optional[dict[str, Any]] = None

