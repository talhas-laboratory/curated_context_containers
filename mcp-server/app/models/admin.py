"""Admin endpoint schemas."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    container: str
    strategy: Literal["in_place", "shadow"] = "in_place"
    embedder_version: Optional[str] = None
    graph_llm_enabled: bool = Field(default=False, description="Use LLM-assisted graph extraction during refresh.")


class RefreshResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    job_id: str
    status: str
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    container: str
    format: Literal["tar", "zip"] = "tar"
    include_vectors: bool = True
    include_blobs: bool = True


class ExportResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    job_id: str
    status: str
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
