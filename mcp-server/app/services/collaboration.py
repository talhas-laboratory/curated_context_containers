"""Multi-agent collaboration services."""

from uuid import uuid4, UUID
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, or_, Table, Column, Text, DateTime, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Container, Base


async def link_containers(
    session: AsyncSession,
    source_container: str,
    target_container: str,
    relationship: str,
    agent_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a link between two containers.

    Args:
        session: Database session
        source_container: Source container UUID or slug
        target_container: Target container UUID or slug
        relationship: Relationship type (e.g., 'influenced_by')
        agent_id: Agent creating the link
        metadata: Optional metadata

    Returns:
        Link dictionary with id, source_container_id, target_container_id, etc.

    Raises:
        ValueError: If containers not found
    """
    # Resolve source container
    source = await _resolve_container(session, source_container)
    if not source:
        raise ValueError(f"Source container '{source_container}' not found")

    # Resolve target container
    target = await _resolve_container(session, target_container)
    if not target:
        raise ValueError(f"Target container '{target_container}' not found")

    # Define table
    container_links = Table(
        'container_links',
        Base.metadata,
        Column('id', PG_UUID(as_uuid=True), primary_key=True),
        Column('source_container_id', PG_UUID(as_uuid=True), nullable=False),
        Column('target_container_id', PG_UUID(as_uuid=True), nullable=False),
        Column('relationship', Text, nullable=False),
        Column('metadata', JSON),
        Column('created_at', DateTime, nullable=False),
        Column('created_by_agent', Text),
        extend_existing=True,
    )

    # Create link
    from sqlalchemy import insert
    link_id = uuid4()
    stmt = insert(container_links).values(
        id=link_id,
        source_container_id=source.id,
        target_container_id=target.id,
        relationship=relationship,
        metadata=metadata or {},
        created_at=datetime.utcnow(),
        created_by_agent=agent_id,
    )
    await session.execute(stmt)
    await session.commit()

    return {
        "id": str(link_id),
        "source_container_id": str(source.id),
        "target_container_id": str(target.id),
        "relationship": relationship,
        "metadata": metadata,
        "created_at": datetime.utcnow(),
        "created_by_agent": agent_id,
    }


async def get_container_links(
    session: AsyncSession,
    container: str,
    direction: str = "both",  # "outgoing", "incoming", or "both"
) -> List[dict]:
    """Get links for a container.

    Args:
        session: Database session
        container: Container UUID or slug
        direction: Link direction to fetch

    Returns:
        List of link dictionaries
    """
    resolved = await _resolve_container(session, container)
    if not resolved:
        raise ValueError(f"Container '{container}' not found")

    container_links = Table(
        'container_links',
        Base.metadata,
        Column('id', PG_UUID(as_uuid=True), primary_key=True),
        Column('source_container_id', PG_UUID(as_uuid=True)),
        Column('target_container_id', PG_UUID(as_uuid=True)),
        Column('relationship', Text),
        Column('metadata', JSON),
        Column('created_at', DateTime),
        Column('created_by_agent', Text),
        extend_existing=True,
    )

    # Build query based on direction
    if direction == "outgoing":
        stmt = select(container_links).where(container_links.c.source_container_id == resolved.id)
    elif direction == "incoming":
        stmt = select(container_links).where(container_links.c.target_container_id == resolved.id)
    else:  # both
        stmt = select(container_links).where(
            or_(
                container_links.c.source_container_id == resolved.id,
                container_links.c.target_container_id == resolved.id,
            )
        )

    result = await session.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "source_container_id": str(row.source_container_id),
            "target_container_id": str(row.target_container_id),
            "relationship": row.relationship,
            "metadata": row.metadata,
            "created_at": row.created_at,
            "created_by_agent": row.created_by_agent,
        }
        for row in rows
    ]


async def subscribe_to_container(
    session: AsyncSession,
    container: str,
    agent_id: str,
    events: List[str],
    webhook_url: Optional[str] = None,
) -> dict:
    """Subscribe an agent to container updates.

    Args:
        session: Database session
        container: Container UUID or slug
        agent_id: Agent subscribing
        events: List of events to subscribe to
        webhook_url: Optional webhook URL for notifications

    Returns:
        Subscription dictionary

    Raises:
        ValueError: If container not found
    """
    resolved = await _resolve_container(session, container)
    if not resolved:
        raise ValueError(f"Container '{container}' not found")

    # Define table
    container_subscriptions = Table(
        'container_subscriptions',
        Base.metadata,
        Column('id', PG_UUID(as_uuid=True), primary_key=True),
        Column('container_id', PG_UUID(as_uuid=True), nullable=False),
        Column('agent_id', Text, nullable=False),
        Column('webhook_url', Text),
        Column('events', ARRAY(Text), nullable=False),
        Column('created_at', DateTime, nullable=False),
        Column('last_notified', DateTime),
        extend_existing=True,
    )

    # Check if subscription already exists
    stmt = select(container_subscriptions).where(
        (container_subscriptions.c.container_id == resolved.id)
        & (container_subscriptions.c.agent_id == agent_id)
    )
    result = await session.execute(stmt)
    existing = result.first()

    if existing:
        # Update existing subscription
        from sqlalchemy import update
        stmt = (
            update(container_subscriptions)
            .where(
                (container_subscriptions.c.container_id == resolved.id)
                & (container_subscriptions.c.agent_id == agent_id)
            )
            .values(
                events=events,
                webhook_url=webhook_url,
            )
        )
        await session.execute(stmt)
        await session.commit()

        return {
            "id": str(existing.id),
            "container_id": str(resolved.id),
            "agent_id": agent_id,
            "webhook_url": webhook_url,
            "events": events,
            "created_at": existing.created_at,
            "last_notified": existing.last_notified,
        }
    else:
        # Create new subscription
        from sqlalchemy import insert
        sub_id = uuid4()
        stmt = insert(container_subscriptions).values(
            id=sub_id,
            container_id=resolved.id,
            agent_id=agent_id,
            webhook_url=webhook_url,
            events=events,
            created_at=datetime.utcnow(),
            last_notified=None,
        )
        await session.execute(stmt)
        await session.commit()

        return {
            "id": str(sub_id),
            "container_id": str(resolved.id),
            "agent_id": agent_id,
            "webhook_url": webhook_url,
            "events": events,
            "created_at": datetime.utcnow(),
            "last_notified": None,
        }


async def get_container_subscriptions(
    session: AsyncSession,
    container: str,
) -> List[dict]:
    """Get all subscriptions for a container.

    Args:
        session: Database session
        container: Container UUID or slug

    Returns:
        List of subscription dictionaries
    """
    resolved = await _resolve_container(session, container)
    if not resolved:
        raise ValueError(f"Container '{container}' not found")

    container_subscriptions = Table(
        'container_subscriptions',
        Base.metadata,
        Column('id', PG_UUID(as_uuid=True), primary_key=True),
        Column('container_id', PG_UUID(as_uuid=True)),
        Column('agent_id', Text),
        Column('webhook_url', Text),
        Column('events', ARRAY(Text)),
        Column('created_at', DateTime),
        Column('last_notified', DateTime),
        extend_existing=True,
    )

    stmt = select(container_subscriptions).where(
        container_subscriptions.c.container_id == resolved.id
    )
    result = await session.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "container_id": str(row.container_id),
            "agent_id": row.agent_id,
            "webhook_url": row.webhook_url,
            "events": row.events,
            "created_at": row.created_at,
            "last_notified": row.last_notified,
        }
        for row in rows
    ]


async def _resolve_container(session: AsyncSession, identifier: str) -> Optional[Container]:
    """Resolve container by UUID or slug."""
    stmt = select(Container).where(
        or_(
            Container.name == identifier,
            Container.id == _maybe_uuid(identifier),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _maybe_uuid(value: str) -> Optional[UUID]:
    """Try to parse value as UUID."""
    try:
        return UUID(value)
    except (TypeError, ValueError):
        return None






















