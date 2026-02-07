from __future__ import annotations

import pytest

from app.migrations import runner as migration_runner


@pytest.mark.asyncio
async def test_migration_runner_aborts_when_postgres_fails(monkeypatch):
    def pg_fail():
        raise RuntimeError("pg boom")

    def qdrant_ok():
        return {"ok": True}

    def neo4j_ok():
        return {"ok": True}

    monkeypatch.setattr(migration_runner, "run_postgres_migrations", pg_fail)
    monkeypatch.setattr(migration_runner, "run_qdrant_migrations", qdrant_ok)
    monkeypatch.setattr(migration_runner, "run_neo4j_migrations", neo4j_ok)

    report = await migration_runner.run_best_effort_migrations()
    assert report.required_ok is False
    assert report.ok is False
    assert report.subsystems["postgres"].ok is False
    # Optional subsystems should not run if PG fails.
    assert "qdrant" not in report.subsystems
    assert "neo4j" not in report.subsystems


@pytest.mark.asyncio
async def test_migration_runner_captures_optional_failures(monkeypatch):
    def pg_ok():
        return {"ok": True}

    def qdrant_fail():
        raise RuntimeError("qdrant boom")

    def neo4j_ok():
        return {"ok": True}

    monkeypatch.setattr(migration_runner, "run_postgres_migrations", pg_ok)
    monkeypatch.setattr(migration_runner, "run_qdrant_migrations", qdrant_fail)
    monkeypatch.setattr(migration_runner, "run_neo4j_migrations", neo4j_ok)

    report = await migration_runner.run_best_effort_migrations()
    assert report.required_ok is True
    assert report.ok is False
    assert report.subsystems["postgres"].ok is True
    assert report.subsystems["qdrant"].ok is False
    assert report.subsystems["neo4j"].ok is True

