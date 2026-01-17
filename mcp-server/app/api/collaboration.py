"""Collaboration endpoints for multi-agent workflows."""

from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import uuid4

from app.db.session import get_session
from app.core.security import verify_bearer_token
from app.models.agent import (
    LinkContainersRequest,
    LinkContainersResponse,
    ContainerLink,
    SubscribeToContainerRequest,
    SubscribeToContainerResponse,
    ContainerSubscription,
)
from app.services import collaboration as collab_service

router = APIRouter(prefix="/v1/collaboration", tags=["collaboration"])


def get_agent_id(request: Request) -> str:
    """Extract agent ID from request headers."""
    return request.headers.get("X-Agent-ID", "anonymous")


@router.post("/link", response_model=LinkContainersResponse)
async def link_containers(
    payload: LinkContainersRequest,
    request: Request,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
    agent_id: str = Depends(get_agent_id),
) -> LinkContainersResponse:
    """Create a link between two containers."""
    try:
        link_data = await collab_service.link_containers(
            session,
            source_container=payload.source_container,
            target_container=payload.target_container,
            relationship=payload.relationship,
            agent_id=agent_id,
            metadata=payload.metadata,
        )

        link = ContainerLink(**link_data)
        return LinkContainersResponse(
            request_id=str(uuid4()),
            link=link,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/containers/{container_id}/links")
async def get_container_links(
    container_id: str,
    direction: str = "both",
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
):
    """Get links for a container."""
    try:
        links = await collab_service.get_container_links(session, container_id, direction)
        return {
            "request_id": str(uuid4()),
            "container_id": container_id,
            "links": links,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/subscribe", response_model=SubscribeToContainerResponse)
async def subscribe_to_container(
    payload: SubscribeToContainerRequest,
    request: Request,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
    agent_id: str = Depends(get_agent_id),
) -> SubscribeToContainerResponse:
    """Subscribe to container updates."""
    try:
        sub_data = await collab_service.subscribe_to_container(
            session,
            container=payload.container,
            agent_id=agent_id,
            events=payload.events,
            webhook_url=payload.webhook_url,
        )

        subscription = ContainerSubscription(**sub_data)
        return SubscribeToContainerResponse(
            request_id=str(uuid4()),
            subscription=subscription,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/containers/{container_id}/subscriptions")
async def get_container_subscriptions(
    container_id: str,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
):
    """Get all subscriptions for a container."""
    try:
        subs = await collab_service.get_container_subscriptions(session, container_id)
        return {
            "request_id": str(uuid4()),
            "container_id": container_id,
            "subscriptions": subs,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc






















