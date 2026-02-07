"""Health checks shared by readiness + system status endpoints."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Tuple

from sqlalchemy import text

from app.adapters.minio import minio_adapter
from app.adapters.neo4j import neo4j_adapter
from app.adapters.qdrant import qdrant_adapter
from app.db.session import AsyncSessionLocal


async def gather_checks() -> tuple[dict[str, bool], dict[str, str]]:
    checks: dict[str, bool] = {}
    errors: dict[str, str] = {}

    async def check_postgres() -> bool:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True

    def check_qdrant() -> bool:
        qdrant_adapter.client.get_collections()
        return True

    def check_minio() -> bool:
        minio_adapter.client.bucket_exists(minio_adapter.bucket)
        return True

    def check_neo4j() -> bool:
        return neo4j_adapter.healthcheck()

    async def run(name: str, task: Awaitable[bool]) -> None:
        try:
            ok = await task
            checks[name] = bool(ok)
            if not ok:
                errors[name] = "unhealthy"
        except Exception as exc:
            checks[name] = False
            errors[name] = str(exc)

    await asyncio.gather(
        run("postgres", check_postgres()),
        run("qdrant", asyncio.to_thread(check_qdrant)),
        run("minio", asyncio.to_thread(check_minio)),
        run("neo4j", asyncio.to_thread(check_neo4j)),
    )

    return checks, errors

