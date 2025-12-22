"""Container endpoints (temporary stubs until DB wiring lands)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import uuid4

from app.db.session import get_session
from app.models.containers import (
    ContainersAddRequest,
    ContainersAddResponse,
    DescribeContainerRequest,
    DescribeContainerResponse,
    ListContainersRequest,
    ListContainersResponse,
)
from app.models.graph import (
    GraphSchemaResponse,
    GraphSearchRequest,
    GraphSearchResponse,
    GraphUpsertRequest,
    GraphUpsertResponse,
)
from app.models.agent import (
    CreateContainerRequest,
    UpdateContainerRequest,
    DeleteContainerRequest,
    ContainerLifecycleResponse,
)
from app.services import containers as container_service
from app.services import jobs as job_service
from app.services import lifecycle as lifecycle_service
from app.services import graph as graph_service
from app.services.jobs import ContainerNotFoundError, JobValidationError
from app.core.security import verify_bearer_token

router = APIRouter(prefix="/v1/containers", tags=["containers"])


def get_agent_id(request: Request) -> str:
    """Extract agent ID from request headers."""
    return request.headers.get("X-Agent-ID", "anonymous")


@router.post("/list", response_model=ListContainersResponse)
async def list_containers(
    payload: ListContainersRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> ListContainersResponse:
    return await container_service.list_containers_response(session, payload)


@router.post("/describe", response_model=DescribeContainerResponse)
async def describe_container(
    payload: DescribeContainerRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> DescribeContainerResponse:
    try:
        return await container_service.describe_container_response(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/add", response_model=ContainersAddResponse)
async def add_to_container(
    payload: ContainersAddRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> ContainersAddResponse:
    try:
        return await job_service.enqueue_jobs(session, payload)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JobValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.post("/create", response_model=ContainerLifecycleResponse)
async def create_container(
    payload: CreateContainerRequest,
    request: Request,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
    agent_id: str = Depends(get_agent_id),
) -> ContainerLifecycleResponse:
    """Create a new container."""
    try:
        container = await lifecycle_service.create_container(session, payload, agent_id)
        return ContainerLifecycleResponse(
            request_id=str(uuid4()),
            success=True,
            container_id=str(container.id),
            message=f"Container '{container.name}' created successfully",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{container_id}/update", response_model=ContainerLifecycleResponse)
async def update_container(
    container_id: str,
    payload: UpdateContainerRequest,
    request: Request,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
    agent_id: str = Depends(get_agent_id),
) -> ContainerLifecycleResponse:
    """Update container metadata."""
    # Override container from path param
    payload.container = container_id
    
    try:
        container = await lifecycle_service.update_container(session, payload, agent_id)
        return ContainerLifecycleResponse(
            request_id=str(uuid4()),
            success=True,
            container_id=str(container.id),
            message=f"Container '{container.name}' updated successfully",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{container_id}", response_model=ContainerLifecycleResponse)
async def delete_container(
    container_id: str,
    request: Request,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
    agent_id: str = Depends(get_agent_id),
    permanent: bool = False,
) -> ContainerLifecycleResponse:
    """Delete or archive a container."""
    try:
        delete_request = DeleteContainerRequest(container=container_id, permanent=permanent)
        await lifecycle_service.delete_container(session, delete_request, agent_id)
        
        action = "deleted permanently" if permanent else "archived"
        return ContainerLifecycleResponse(
            request_id=str(uuid4()),
            success=True,
            container_id=container_id,
            message=f"Container {action} successfully",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/graph_upsert", response_model=GraphUpsertResponse)
async def graph_upsert(
    payload: GraphUpsertRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> GraphUpsertResponse:
    try:
        return await graph_service.graph_upsert(session, payload)
    except Exception as exc:  # pragma: no cover - safeguard
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/graph_search", response_model=GraphSearchResponse)
async def graph_search(
    payload: GraphSearchRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> GraphSearchResponse:
    try:
        return await graph_service.graph_search(session, payload)
    except Exception as exc:  # pragma: no cover - safeguard
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/graph_schema", response_model=GraphSchemaResponse)
async def graph_schema(
    container: str,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> GraphSchemaResponse:
    try:
        return await graph_service.graph_schema(session, container)
    except Exception as exc:  # pragma: no cover - safeguard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
