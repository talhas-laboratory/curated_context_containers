from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Callable

from app.core.metrics import observe_migration
from app.migrations.neo4j import run_neo4j_migrations
from app.migrations.pg import run_postgres_migrations
from app.migrations.qdrant import run_qdrant_migrations
from app.migrations.types import MigrationReport, SubsystemMigrationReport


async def run_best_effort_migrations() -> MigrationReport:
    """Run migrations.

    - Postgres: required. Failure aborts startup.
    - Qdrant/Neo4j: best-effort. Failures are reported via system status.
    """
    started_at = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    subsystems: dict[str, SubsystemMigrationReport] = {}

    # Required: Postgres
    pg_started = datetime.now(timezone.utc)
    pg_t0 = time.perf_counter()
    try:
        pg_details = await asyncio.to_thread(run_postgres_migrations)
        observe_migration(subsystem="postgres", ok=True, duration_ms=int((time.perf_counter() - pg_t0) * 1000))
        subsystems["postgres"] = SubsystemMigrationReport(
            subsystem="postgres",
            ok=True,
            status="ok",
            started_at=pg_started,
            finished_at=datetime.now(timezone.utc),
            duration_ms=int((time.perf_counter() - pg_t0) * 1000),
            details=pg_details,
        )
        required_ok = True
    except Exception as exc:
        observe_migration(subsystem="postgres", ok=False, duration_ms=int((time.perf_counter() - pg_t0) * 1000))
        subsystems["postgres"] = SubsystemMigrationReport(
            subsystem="postgres",
            ok=False,
            status="failed",
            started_at=pg_started,
            finished_at=datetime.now(timezone.utc),
            duration_ms=int((time.perf_counter() - pg_t0) * 1000),
            details={},
            error=str(exc),
        )
        required_ok = False

    if not required_ok:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        return MigrationReport(
            ok=False,
            required_ok=False,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            subsystems=subsystems,
        )

    # Best-effort: run in parallel and capture failures.
    async def optional_subsystem(name: str, fn: Callable[[], dict]) -> None:
        s_started = datetime.now(timezone.utc)
        s_t0 = time.perf_counter()
        try:
            details = await asyncio.to_thread(fn)
            observe_migration(subsystem=name, ok=True, duration_ms=int((time.perf_counter() - s_t0) * 1000))
            subsystems[name] = SubsystemMigrationReport(
                subsystem=name,
                ok=True,
                status="ok",
                started_at=s_started,
                finished_at=datetime.now(timezone.utc),
                duration_ms=int((time.perf_counter() - s_t0) * 1000),
                details=details,
            )
        except Exception as exc:
            observe_migration(subsystem=name, ok=False, duration_ms=int((time.perf_counter() - s_t0) * 1000))
            subsystems[name] = SubsystemMigrationReport(
                subsystem=name,
                ok=False,
                status="failed",
                started_at=s_started,
                finished_at=datetime.now(timezone.utc),
                duration_ms=int((time.perf_counter() - s_t0) * 1000),
                details={},
                error=str(exc),
            )

    await asyncio.gather(
        optional_subsystem("qdrant", run_qdrant_migrations),
        optional_subsystem("neo4j", run_neo4j_migrations),
    )

    finished_at = datetime.now(timezone.utc)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    overall_ok = all(r.ok for r in subsystems.values())
    return MigrationReport(
        ok=overall_ok,
        required_ok=True,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        subsystems=subsystems,
    )
