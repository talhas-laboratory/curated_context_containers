"""Admin services (refresh/export)."""
from __future__ import annotations

from time import perf_counter
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Container, Job
from app.models.admin import RefreshRequest, RefreshResponse, ExportRequest, ExportResponse
from app.services.jobs import ContainerNotFoundError, _maybe_uuid
from app.core.config import get_settings


async def enqueue_refresh(session: AsyncSession, request: RefreshRequest) -> RefreshResponse:
    start = perf_counter()
    settings = get_settings()

    container_filters: List = [Container.name == request.container]
    candidate_uuid = _maybe_uuid(request.container)
    if candidate_uuid:
        container_filters.append(Container.id == candidate_uuid)
    container_stmt = select(Container).where(or_(*container_filters))
    container = (await session.execute(container_stmt)).scalar_one_or_none()
    if not container:
        raise ContainerNotFoundError("CONTAINER_NOT_FOUND")

    job_id = uuid4()
    job = Job(
        id=job_id,
        kind="refresh",
        status="queued",
        container_id=container.id,
        payload={
            "container_id": str(container.id),
            "container_name": container.name,
            "strategy": request.strategy,
            "embedder_version": request.embedder_version,
            "graph_llm_enabled": bool(getattr(request, "graph_llm_enabled", False)),
        },
        error=None,
        retries=0,
    )
    session.add(job)
    await session.commit()
    elapsed = int((perf_counter() - start) * 1000)
    if settings.admin_fastpath:
        job.status = "done"
        session.add(job)
        await session.commit()
    return RefreshResponse(
        request_id=str(uuid4()),
        job_id=str(job_id),
        status="done" if settings.admin_fastpath else "queued",
        timings_ms={"db_query": elapsed},
        issues=[],
    )


async def enqueue_export(session: AsyncSession, request: ExportRequest) -> ExportResponse:
    start = perf_counter()
    settings = get_settings()

    container_filters: List = [Container.name == request.container]
    candidate_uuid = _maybe_uuid(request.container)
    if candidate_uuid:
        container_filters.append(Container.id == candidate_uuid)
    container_stmt = select(Container).where(or_(*container_filters))
    container = (await session.execute(container_stmt)).scalar_one_or_none()
    if not container:
        raise ContainerNotFoundError("CONTAINER_NOT_FOUND")

    job_id = uuid4()
    job = Job(
        id=job_id,
        kind="export",
        status="queued",
        container_id=container.id,
        payload={
            "container_id": str(container.id),
            "container_name": container.name,
            "format": request.format,
            "include_vectors": request.include_vectors,
            "include_blobs": request.include_blobs,
        },
        error=None,
        retries=0,
    )
    session.add(job)
    await session.commit()
    elapsed = int((perf_counter() - start) * 1000)
    if settings.admin_fastpath:
        job.status = "done"
        session.add(job)
        await session.commit()
    return ExportResponse(
        request_id=str(uuid4()),
        job_id=str(job_id),
        status="done" if settings.admin_fastpath else "queued",
        timings_ms={"db_query": elapsed},
        issues=[],
    )
