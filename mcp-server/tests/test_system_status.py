from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import system as system_api
from app.core.runtime_state import clear_migration_report, set_migration_report
from app.core.security import verify_bearer_token
from app.main import app
from app.migrations.types import MigrationReport, SubsystemMigrationReport


client = TestClient(app)


def _auth_override():
    return True


def test_system_status_ok(monkeypatch):
    async def fake_checks():
        return {"postgres": True, "qdrant": True, "minio": True, "neo4j": True}, {}

    monkeypatch.setattr(system_api, "gather_checks", fake_checks)
    app.dependency_overrides[verify_bearer_token] = _auth_override

    resp = client.get("/v1/system/status", headers={"Authorization": "Bearer local-dev-token"})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["required_ok"] is True
    assert payload["checks"]["postgres"] is True

    app.dependency_overrides.clear()


def test_system_status_degraded_includes_service_issue(monkeypatch):
    async def fake_checks():
        return {"postgres": True, "qdrant": False, "minio": True, "neo4j": True}, {"qdrant": "down"}

    monkeypatch.setattr(system_api, "gather_checks", fake_checks)
    app.dependency_overrides[verify_bearer_token] = _auth_override

    resp = client.get("/v1/system/status", headers={"Authorization": "Bearer local-dev-token"})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "degraded"
    assert "QDRANT_DOWN" in payload["issues"]

    app.dependency_overrides.clear()


def test_system_status_reports_migration_degraded(monkeypatch):
    async def fake_checks():
        return {"postgres": True, "qdrant": True, "minio": True, "neo4j": True}, {}

    monkeypatch.setattr(system_api, "gather_checks", fake_checks)
    app.dependency_overrides[verify_bearer_token] = _auth_override

    clear_migration_report()
    now = datetime.now(timezone.utc)
    report = MigrationReport(
        ok=False,
        required_ok=True,
        started_at=now,
        finished_at=now,
        duration_ms=1,
        subsystems={
            "qdrant": SubsystemMigrationReport(
                subsystem="qdrant",
                ok=False,
                status="failed",
                started_at=now,
                finished_at=now,
                duration_ms=1,
                details={},
                error="boom",
            )
        },
    )
    set_migration_report(report)

    resp = client.get("/v1/system/status", headers={"Authorization": "Bearer local-dev-token"})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "MIGRATIONS_DEGRADED" in payload["issues"]
    assert payload["migrations"]["ok"] is False

    clear_migration_report()
    app.dependency_overrides.clear()
