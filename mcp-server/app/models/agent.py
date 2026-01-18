"""Pydantic schemas for agent and lifecycle endpoints."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Container lifecycle requests/responses

class CreateContainerRequest(BaseModel):
    """Request to create a new container."""
    name: str = Field(description="Unique container name (slug)")
    theme: str = Field(description="Container theme/topic")
    description: Optional[str] = None
    modalities: List[str] = Field(default=["text", "pdf", "image"], description="Allowed modalities")
    embedder: str = Field(default="google-gemma3-text", description="Embedder model")
    embedder_version: str = Field(default="1.0.0")
    dims: int = Field(default=768, description="Embedding dimensions")
    policy: dict = Field(default_factory=dict, description="Retrieval policy")
    mission_context: Optional[str] = Field(None, description="Why this container exists")
    visibility: str = Field(default="private", description="private, team, or public")
    collaboration_policy: str = Field(default="read-only", description="read-only or contribute")
    auto_refresh: bool = Field(default=False, description="Auto-update on manifest changes")


class UpdateContainerRequest(BaseModel):
    """Request to update container metadata."""
    container: str = Field(description="Container UUID or slug")
    theme: Optional[str] = None
    description: Optional[str] = None
    mission_context: Optional[str] = None
    visibility: Optional[str] = None
    collaboration_policy: Optional[str] = None
    auto_refresh: Optional[bool] = None
    state: Optional[str] = None


class DeleteContainerRequest(BaseModel):
    """Request to delete/archive a container."""
    container: str = Field(description="Container UUID or slug")
    permanent: bool = Field(default=False, description="If true, hard delete; otherwise archive")


class ContainerLifecycleResponse(BaseModel):
    """Generic response for lifecycle operations."""
    version: str = "v1"
    request_id: str
    success: bool
    container_id: Optional[str] = None
    message: Optional[str] = None
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


# Agent session models

class AgentSessionInfo(BaseModel):
    """Agent session information."""
    id: str
    agent_id: str
    agent_name: Optional[str] = None
    started_at: datetime
    last_active: datetime
    metadata: Optional[dict] = None


# Container recommendation

class RecommendContainersRequest(BaseModel):
    """Request to recommend containers based on mission."""
    mission: str = Field(description="Agent's mission description")
    k: int = Field(default=5, ge=1, le=20, description="Number of recommendations")


class ContainerRecommendation(BaseModel):
    """A single container recommendation."""
    container_id: str
    name: str
    theme: str
    description: Optional[str] = None
    relevance_score: float
    reason: str


class RecommendContainersResponse(BaseModel):
    """Response with recommended containers."""
    version: str = "v1"
    request_id: str
    mission: str
    recommendations: List[ContainerRecommendation]
    timings_ms: dict = Field(default_factory=dict)


# Container links

class LinkContainersRequest(BaseModel):
    """Request to link two containers."""
    source_container: str = Field(description="Source container UUID or slug")
    target_container: str = Field(description="Target container UUID or slug")
    relationship: str = Field(description="Relationship type (e.g., 'influenced_by', 'related_to')")
    metadata: Optional[dict] = None


class ContainerLink(BaseModel):
    """A container link."""
    id: str
    source_container_id: str
    target_container_id: str
    relationship: str
    metadata: Optional[dict] = None
    created_at: datetime
    created_by_agent: Optional[str] = None


class LinkContainersResponse(BaseModel):
    """Response for link creation."""
    version: str = "v1"
    request_id: str
    link: ContainerLink
    timings_ms: dict = Field(default_factory=dict)


# Container subscriptions

class SubscribeToContainerRequest(BaseModel):
    """Request to subscribe to container updates."""
    container: str = Field(description="Container UUID or slug")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    events: List[str] = Field(
        default=["source_added", "source_removed"],
        description="Events to subscribe to"
    )


class ContainerSubscription(BaseModel):
    """A container subscription."""
    id: str
    container_id: str
    agent_id: str
    webhook_url: Optional[str] = None
    events: List[str]
    created_at: datetime
    last_notified: Optional[datetime] = None


class SubscribeToContainerResponse(BaseModel):
    """Response for subscription creation."""
    version: str = "v1"
    request_id: str
    subscription: ContainerSubscription
    timings_ms: dict = Field(default_factory=dict)








