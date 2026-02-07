from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import get_settings


def _find_alembic_ini() -> Path:
    """Find `alembic.ini` in common runtime layouts (repo, docker image)."""
    candidates: list[Path] = []

    # 1) Current working directory (docker uses WORKDIR=/app).
    candidates.append(Path.cwd() / "alembic.ini")

    # 2) Walk upwards from this file (useful in editable installs).
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "alembic.ini")

    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError("alembic.ini not found; cannot run Postgres migrations")


def _alembic_config(postgres_dsn: str) -> tuple[Config, str | None]:
    ini_path = _find_alembic_ini()
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", postgres_dsn)
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    return cfg, head


def _read_current_revision(conn: psycopg.Connection) -> str | None:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def run_postgres_migrations() -> dict[str, Any]:
    """Run Alembic migrations under a Postgres advisory lock.

    Returns a dict suitable for attaching to a SubsystemMigrationReport.details.
    Raises on failure.
    """
    settings = get_settings()
    cfg, head = _alembic_config(settings.postgres_dsn)

    details: dict[str, Any] = {"target_revision": head}
    start = time.perf_counter()

    with psycopg.connect(settings.postgres_dsn) as conn:
        # Ensure we serialize migrations across processes/containers.
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(hashtext(%s))", ("llc:pg:migrations",))
        try:
            before = _read_current_revision(conn)
            details["current_revision_before"] = before

            command.upgrade(cfg, "head")

            after = _read_current_revision(conn)
            details["current_revision_after"] = after
            details["migrated"] = before != after
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", ("llc:pg:migrations",))

    details["duration_ms"] = int((time.perf_counter() - start) * 1000)
    return details

