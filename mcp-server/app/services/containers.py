"""Container service layer."""
from __future__ import annotations

from time import perf_counter
from typing import List, Tuple
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Container
from app.models.containers import (
    ContainerDetail,
    ContainerStats,
    ContainerSummary,
    DescribeContainerRequest,
    DescribeContainerResponse,
    ListContainersRequest,
    ListContainersResponse,
)
from app.services import manifests


def _stats_from_dict(payload: dict | None) -> ContainerStats:
    payload = payload or {}
    data = {**ContainerStats().model_dump(), **payload}
    return ContainerStats(**data)


def _to_summary(model: Container) -> ContainerSummary:
    return ContainerSummary(
        id=str(model.id),
        parent_id=str(model.parent_id) if model.parent_id else None,
        name=model.name,
        theme=model.theme,
        modalities=[str(m) for m in (model.modalities or [])],
        state=model.state,
        graph_enabled=bool(getattr(model, "graph_enabled", True)),
        stats=_stats_from_dict(model.stats),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_detail(model: Container) -> ContainerDetail:
    summary = _to_summary(model)
    detail = ContainerDetail(
        **summary.model_dump(),
        description=model.description,
        embedder=model.embedder,
        embedder_version=model.embedder_version,
        dims=model.dims,
        policy=model.policy or {},
        graph_url=model.graph_url,
        graph_schema=model.graph_schema or {},
    )
    manifest = manifests.load_manifest(model.name) or manifests.load_manifest(str(model.id))
    if manifest:
        detail.description = manifest.get("description") or detail.description
        detail.modalities = manifest.get("modalities", detail.modalities)
        detail.embedder = manifest.get("embedder", detail.embedder)
        detail.embedder_version = manifest.get("embedder_version", detail.embedder_version)
        detail.dims = manifest.get("dims", detail.dims)
        retrieval_policy = manifest.get("retrieval")
        if retrieval_policy:
            detail.policy = retrieval_policy
        graph_cfg = manifest.get("graph") or {}
        if graph_cfg:
            detail.graph_enabled = graph_cfg.get("enabled", detail.graph_enabled)
            detail.graph_url = graph_cfg.get("url", detail.graph_url)
            detail.graph_schema = graph_cfg.get("schema", detail.graph_schema)
        # Policy checks: ensure graph-enabled manifests require graph_enabled flag
        if detail.graph_enabled is False and graph_cfg.get("enabled"):
            detail.graph_enabled = True
    return detail


async def list_containers(
    session: AsyncSession, request: ListContainersRequest
) -> Tuple[List[ContainerSummary], int]:
    stmt = select(Container)
    if request.state and request.state != "all":
        stmt = stmt.where(Container.state == request.state)
    if request.parent_id:
        parent_uuid = _maybe_uuid(request.parent_id)
        if parent_uuid is None:
            parent = (
                await session.execute(select(Container.id).where(Container.name == request.parent_id))
            ).scalar_one_or_none()
            if parent is None:
                return [], 0
            parent_uuid = parent
        stmt = stmt.where(Container.parent_id == parent_uuid)
    stmt = stmt.order_by(Container.created_at.desc()).limit(request.limit).offset(request.offset)

    total_stmt = select(func.count()).select_from(Container)
    if request.state and request.state != "all":
        total_stmt = total_stmt.where(Container.state == request.state)
    if request.parent_id:
        parent_uuid = _maybe_uuid(request.parent_id)
        if parent_uuid is None:
            parent = (
                await session.execute(select(Container.id).where(Container.name == request.parent_id))
            ).scalar_one_or_none()
            if parent is None:
                return [], 0
            parent_uuid = parent
        total_stmt = total_stmt.where(Container.parent_id == parent_uuid)

    result = await session.execute(stmt)
    containers = result.scalars().all()
    total = (await session.execute(total_stmt)).scalar_one()
    return [_to_summary(c) for c in containers], total


async def describe_container(
    session: AsyncSession, request: DescribeContainerRequest
) -> ContainerDetail:
    stmt = select(Container).where(
        or_(
            Container.name == request.container,
            *(
                [Container.id == container_uuid]
                if (container_uuid := _maybe_uuid(request.container))
                else []
            ),
        )
    )
    result = await session.execute(stmt)
    container = result.scalar_one_or_none()
    if not container:
        raise ValueError("CONTAINER_NOT_FOUND")
    return _to_detail(container)


async def list_containers_response(
    session: AsyncSession, request: ListContainersRequest
) -> ListContainersResponse:
    start = perf_counter()
    containers, total = await list_containers(session, request)
    elapsed = int((perf_counter() - start) * 1000)
    return ListContainersResponse(
        request_id=str(uuid4()),
        containers=containers,
        total=total,
        timings_ms={"db_query": elapsed},
    )


async def describe_container_response(
    session: AsyncSession, request: DescribeContainerRequest
) -> DescribeContainerResponse:
    start = perf_counter()
    container = await describe_container(session, request)
    elapsed = int((perf_counter() - start) * 1000)
    return DescribeContainerResponse(
        request_id=str(uuid4()),
        container=container,
        timings_ms={"db_query": elapsed},
    )
def _maybe_uuid(value: str | None) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None
