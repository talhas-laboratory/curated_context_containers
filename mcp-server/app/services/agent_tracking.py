"""Agent tracking and session management."""

from uuid import uuid4
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AgentSession:
    """Represents an agent session in the database."""

    def __init__(
        self,
        id: str,
        agent_id: str,
        agent_name: Optional[str],
        started_at: datetime,
        last_active: datetime,
        metadata: Optional[dict],
    ):
        self.id = id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.started_at = started_at
        self.last_active = last_active
        self.metadata = metadata or {}


async def track_agent_activity(
    session: AsyncSession,
    agent_id: str,
    agent_name: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AgentSession:
    """Track or update agent activity.

    Creates a new session if this is the first time seeing this agent,
    or updates the last_active timestamp if they already have a session.

    Args:
        session: Database session
        agent_id: Unique agent identifier
        agent_name: Human-readable agent name
        metadata: Optional metadata

    Returns:
        AgentSession object
    """
    from app.db.models import Base
    from sqlalchemy import Table, Column, Text, DateTime, JSON
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    # Define table dynamically (in case model isn't loaded)
    agent_sessions = Table(
        'agent_sessions',
        Base.metadata,
        Column('id', PG_UUID(as_uuid=True), primary_key=True),
        Column('agent_id', Text, nullable=False),
        Column('agent_name', Text),
        Column('started_at', DateTime, nullable=False),
        Column('last_active', DateTime, nullable=False),
        Column('metadata', JSON),
        extend_existing=True,
    )

    # Check if agent already has a session
    stmt = select(agent_sessions).where(agent_sessions.c.agent_id == agent_id)
    result = await session.execute(stmt)
    row = result.first()

    now = datetime.utcnow()

    if row:
        # Update existing session
        from sqlalchemy import update
        stmt = (
            update(agent_sessions)
            .where(agent_sessions.c.agent_id == agent_id)
            .values(last_active=now, agent_name=agent_name or row.agent_name)
        )
        await session.execute(stmt)
        await session.commit()

        return AgentSession(
            id=str(row.id),
            agent_id=agent_id,
            agent_name=agent_name or row.agent_name,
            started_at=row.started_at,
            last_active=now,
            metadata=row.metadata,
        )
    else:
        # Create new session
        from sqlalchemy import insert
        session_id = uuid4()
        stmt = insert(agent_sessions).values(
            id=session_id,
            agent_id=agent_id,
            agent_name=agent_name,
            started_at=now,
            last_active=now,
            metadata=metadata or {},
        )
        await session.execute(stmt)
        await session.commit()

        return AgentSession(
            id=str(session_id),
            agent_id=agent_id,
            agent_name=agent_name,
            started_at=now,
            last_active=now,
            metadata=metadata or {},
        )

