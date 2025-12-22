"""Search request/response schemas."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SearchRequest(BaseModel):
    query: Optional[str] = None
    query_image_base64: Optional[str] = Field(default=None, description="Base64-encoded image for crossmodal search")
    container_ids: List[str] = Field(min_length=1)
    mode: Literal["semantic", "bm25", "hybrid", "crossmodal", "graph", "hybrid_graph"] = "hybrid"
    k: int = Field(default=10, ge=1, le=50)
    rerank: bool = False
    diagnostics: bool = False
    graph: Optional[dict] = Field(default=None, description="Graph-specific options (max_hops, neighbor_k)")

    @model_validator(mode="after")
    def validate_query_inputs(self):
        if not (self.query or self.query_image_base64):
            raise ValueError("query or query_image_base64 required")
        if self.query_image_base64 and self.mode == "bm25":
            raise ValueError("bm25 mode requires text query")
        if self.mode == "graph" and self.query_image_base64:
            raise ValueError("graph mode requires text query")
        return self


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
    query: Optional[str]
    results: List[SearchResult]
    total_hits: int
    returned: int
    diagnostics: dict = Field(default_factory=dict)
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    graph_context: Optional[dict] = Field(default=None)


SearchResult.model_rebuild()
SearchResponse.model_rebuild()
