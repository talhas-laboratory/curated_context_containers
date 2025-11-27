"""Async session factory."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()
_engine = create_async_engine(_settings.async_postgres_dsn, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
