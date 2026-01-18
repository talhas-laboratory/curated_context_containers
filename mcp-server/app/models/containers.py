"""Pydantic schemas for container endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ContainerStats(BaseModel):
    document_count: int = 0
    chunk_count: int = 0
    size_mb: float = 0.0
    last_ingest: Optional[datetime] = None


class ContainerSummary(BaseModel):
    id: str
    name: str
    theme: Optional[str] = None
    modalities: List[str] = Field(default_factory=list)
    state: str = "active"
    graph_enabled: bool = False
    stats: ContainerStats = Field(default_factory=ContainerStats)
    created_at: datetime
    updated_at: datetime


class ContainerDetail(ContainerSummary):
    description: Optional[str] = None
    embedder: Optional[str] = None
    embedder_version: Optional[str] = None
    dims: Optional[int] = None
    policy: dict = Field(default_factory=dict)
    graph_url: Optional[str] = None
    graph_schema: dict = Field(default_factory=dict)


class ListContainersResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    containers: List[ContainerSummary]
    total: int
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class DescribeContainerResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    container: ContainerDetail
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class ListContainersRequest(BaseModel):
    state: Optional[str] = Field(default="active")
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class DescribeContainerRequest(BaseModel):
    container: str = Field(description="Container id or slug")


class AddSource(BaseModel):
    uri: str
    title: Optional[str] = None
    mime: Optional[str] = None
    modality: Optional[str] = None
    meta: dict = Field(default_factory=dict)


class ContainersAddRequest(BaseModel):
    container: str
    sources: List[AddSource]
    mode: str = Field(default="async")


class JobSummary(BaseModel):
    job_id: str
    status: str
    source_uri: str
    submitted_at: datetime


class ContainersAddResponse(BaseModel):
    version: str = "v1"
    request_id: str
    jobs: List[JobSummary]
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
