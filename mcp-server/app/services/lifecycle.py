"""Container lifecycle service layer."""

from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Container
from app.models.agent import (
    CreateContainerRequest,
    UpdateContainerRequest,
    DeleteContainerRequest,
)


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

    # Create container
    container = Container(
        id=uuid4(),
        name=request.name,
        theme=request.theme,
        description=request.description,
        modalities=request.modalities,
        embedder=request.embedder,
        embedder_version=request.embedder_version,
        dims=request.dims,
        policy=request.policy,
        acl={},
        state="active",
        stats={},
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

    if request.permanent:
        # Hard delete (use with caution!)
        await session.delete(container)
    else:
        # Soft delete (archive)
        container.state = "archived"
        container.updated_at = datetime.utcnow()

    await session.commit()
    return True


def _maybe_uuid(value: str) -> Optional[UUID]:
    """Try to parse value as UUID."""
    try:
        return UUID(value)
    except (TypeError, ValueError):
        return None

