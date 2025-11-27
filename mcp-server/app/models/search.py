"""Search request/response schemas."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    container_ids: List[str] = Field(min_length=1)
    mode: Literal["semantic", "bm25", "hybrid"] = "hybrid"
    k: int = Field(default=10, ge=1, le=50)
    rerank: bool = False
    diagnostics: bool = False


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    container_id: str
    container_name: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    uri: Optional[str]
    score: float
    stage_scores: dict = Field(default_factory=dict)
    modality: Optional[str]
    provenance: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    query: str
    results: List[SearchResult]
    total_hits: int
    returned: int
    diagnostics: dict = Field(default_factory=dict)
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


SearchResult.model_rebuild()
SearchResponse.model_rebuild()
