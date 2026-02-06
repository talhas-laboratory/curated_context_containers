"""Container lifecycle service layer."""

from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional

import logging

from sqlalchemy import delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.minio import minio_adapter
from app.adapters.qdrant import qdrant_adapter
from app.db.models import Container, ContainerVersion, Document, Chunk, Job
from app.models.agent import (
    CreateContainerRequest,
    UpdateContainerRequest,
    DeleteContainerRequest,
)

LOGGER = logging.getLogger(__name__)

async def create_container(
    session: AsyncSession,
    request: CreateContainerRequest,
    agent_id: Optional[str] = None,
) -> Container:
    """Create a new container.

    Args:
        session: Database session
        request: Container creation request
        agent_id: Agent creating the container (from X-Agent-ID header)

    Returns:
        Created Container model

    Raises:
        ValueError: If container name already exists
    """
    # Check if name already exists
    stmt = select(Container).where(Container.name == request.name)
    existing = await session.execute(stmt)
    if existing.scalar_one_or_none():
        raise ValueError(f"Container with name '{request.name}' already exists")

    parent_container: Container | None = None
    if request.parent_id:
        parent_container = await _get_container_by_ref(session, request.parent_id)
        if not parent_container:
            raise ValueError(f"Parent container '{request.parent_id}' not found")

    # Create container
    container = Container(
        id=uuid4(),
        parent_id=parent_container.id if parent_container else None,
        name=request.name,
        theme=request.theme,
        description=request.description,
        modalities=request.modalities,
        embedder=request.embedder,
        embedder_version=request.embedder_version,
        dims=request.dims,
        policy=(dict(parent_container.policy or {})) if parent_container else request.policy,
        acl={},
        state="active",
        stats={},
        graph_enabled=True,
        created_by_agent=agent_id,
        mission_context=request.mission_context,
        visibility=request.visibility,
        collaboration_policy=request.collaboration_policy,
        auto_refresh=request.auto_refresh,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(container)
    await session.commit()
    await session.refresh(container)

    return container


async def update_container(
    session: AsyncSession,
    request: UpdateContainerRequest,
    agent_id: Optional[str] = None,
) -> Container:
    """Update container metadata.

    Args:
        session: Database session
        request: Container update request
        agent_id: Agent updating the container

    Returns:
        Updated Container model

    Raises:
        ValueError: If container not found
    """
    # Find container
    stmt = select(Container).where(
        or_(
            Container.name == request.container,
            Container.id == _maybe_uuid(request.container),
        )
    )
    result = await session.execute(stmt)
    container = result.scalar_one_or_none()

    if not container:
        raise ValueError(f"Container '{request.container}' not found")

    # Update fields if provided
    if request.theme is not None:
        container.theme = request.theme
    if request.description is not None:
        container.description = request.description
    if request.mission_context is not None:
        container.mission_context = request.mission_context
    if request.visibility is not None:
        container.visibility = request.visibility
    if request.collaboration_policy is not None:
        container.collaboration_policy = request.collaboration_policy
    if request.auto_refresh is not None:
        container.auto_refresh = request.auto_refresh
    if request.state is not None:
        if request.state in ["active", "paused", "archived"]:
            container.state = request.state
        else:
            raise ValueError(f"Invalid state: {request.state}")

    container.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(container)

    return container


async def delete_container(
    session: AsyncSession,
    request: DeleteContainerRequest,
    agent_id: Optional[str] = None,
) -> bool:
    """Delete or archive a container.

    Args:
        session: Database session
        request: Container deletion request
        agent_id: Agent deleting the container

    Returns:
        True if successful

    Raises:
        ValueError: If container not found
    """
    # Find container
    stmt = select(Container).where(
        or_(
            Container.name == request.container,
            Container.id == _maybe_uuid(request.container),
        )
    )
    result = await session.execute(stmt)
    container = result.scalar_one_or_none()

    if not container:
        raise ValueError(f"Container '{request.container}' not found")

    container_tree = await _collect_descendants(session, container)
    container_ids = [str(item.id) for item in container_tree]
    container_uuid_list = [item.id for item in container_tree]
    container_modalities = {
        str(item.id): [str(m) for m in (item.modalities or [])] for item in container_tree
    }

    if request.permanent:
        # Hard delete (use with caution!)
        await session.execute(delete(Chunk).where(Chunk.container_id.in_(container_uuid_list)))
        await session.execute(delete(Document).where(Document.container_id.in_(container_uuid_list)))
        await session.execute(delete(Job).where(Job.container_id.in_(container_uuid_list)))
        await session.execute(delete(ContainerVersion).where(ContainerVersion.container_id.in_(container_uuid_list)))
        await session.execute(delete(Container).where(Container.id.in_(container_uuid_list)))
    else:
        # Soft delete (archive)
        now = datetime.utcnow()
        for item in container_tree:
            item.state = "archived"
            item.updated_at = now

    await session.commit()

    if request.permanent:
        for container_id in container_ids:
            try:
                await qdrant_adapter.delete_container(
                    container_id, modalities=container_modalities.get(container_id)
                )
            except Exception as exc:  # pragma: no cover - runtime safeguard
                LOGGER.warning(
                    "qdrant_container_delete_failed",
                    extra={"container_id": container_id, "error": str(exc)},
                )
            try:
                await minio_adapter.delete_container(container_id)
            except Exception as exc:  # pragma: no cover - runtime safeguard
                LOGGER.warning(
                    "minio_container_delete_failed",
                    extra={"container_id": container_id, "error": str(exc)},
                )

    return True


def _maybe_uuid(value: str) -> Optional[UUID]:
    """Try to parse value as UUID."""
    try:
        return UUID(value)
    except (TypeError, ValueError):
        return None


async def _get_container_by_ref(session: AsyncSession, container_ref: str) -> Container | None:
    maybe_uuid = _maybe_uuid(container_ref)
    predicates = [Container.name == container_ref]
    if maybe_uuid:
        predicates.append(Container.id == maybe_uuid)
    stmt = select(Container).where(or_(*predicates))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _collect_descendants(session: AsyncSession, root: Container) -> list[Container]:
    """Return root + all descendant containers."""
    containers = (await session.execute(select(Container))).scalars().all()
    container_map = {str(c.id): c for c in containers}
    children_map: dict[str, list[str]] = {}
    for c in containers:
        if c.parent_id:
            children_map.setdefault(str(c.parent_id), []).append(str(c.id))

    ordered: list[Container] = []
    seen: set[str] = set()

    def visit(cid: str) -> None:
        if cid in seen:
            return
        seen.add(cid)
        container = container_map.get(cid)
        if container:
            ordered.append(container)
            for child_id in children_map.get(cid, []):
                visit(child_id)

    visit(str(root.id))
    return ordered
