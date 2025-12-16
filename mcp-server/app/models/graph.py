"""Graph-related request/response schemas."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: Optional[str] = None
    type: Optional[str] = None
    summary: Optional[str] = None
    properties: dict = Field(default_factory=dict)
    source_chunk_ids: List[str] = Field(default_factory=list)
    score: Optional[float] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Optional[str] = None
    properties: dict = Field(default_factory=dict)
    source_chunk_ids: List[str] = Field(default_factory=list)
    score: Optional[float] = None


class GraphUpsertRequest(BaseModel):
    container: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    mode: Literal["merge", "replace"] = "merge"
    diagnostics: bool = False


class GraphUpsertResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    inserted_nodes: int = 0
    inserted_edges: int = 0
    updated_nodes: int = 0
    updated_edges: int = 0
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class GraphSearchRequest(BaseModel):
    container: str
    query: Optional[str] = None
    mode: Literal["nl", "cypher"] = "nl"
    max_hops: int = Field(default=2, ge=1, le=3)
    k: int = Field(default=20, ge=1, le=50)
    expand_from_vector: Optional[dict] = Field(default=None, description="Optional vector-first expansion config")
    diagnostics: bool = False
    intent: Optional[str] = Field(
        default=None,
        description="User intent, e.g., chronological_overview, neighborhood, comparison, path",
    )
    focus_node_types: List[str] = Field(
        default_factory=list,
        description="Preferred node labels/types to prioritize in answers",
    )
    focus_properties: List[str] = Field(
        default_factory=list,
        description="Preferred properties to surface (e.g., year_start, year_end, country)",
    )
    answer_shape: Optional[str] = Field(
        default=None,
        description="Desired answer shape, e.g., timeline, table, path_list",
    )
    constraints: dict = Field(
        default_factory=dict,
        description="Optional constraints, e.g., time_range, max_steps_per_chain",
    )


class GraphSearchResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    snippets: List[dict] = Field(default_factory=list)
    diagnostics: dict = Field(default_factory=dict)
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class GraphSchemaResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    schema: dict = Field(default_factory=dict)
    diagnostics: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
