"""System status endpoints (health + migrations + dependencies)."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.core.runtime_state import get_migration_report
from app.core.security import verify_bearer_token
from app.services.health import gather_checks

router = APIRouter(prefix="/v1/system", tags=["system"])


@router.get("/status")
async def system_status(
    authenticated: bool = Depends(verify_bearer_token),
) -> dict:
    try:
        checks, errors = await gather_checks()
    except Exception as exc:  # pragma: no cover - defensive runtime safeguard
        checks, errors = {}, {"system": str(exc)}
    migrations = get_migration_report()

    required_ok = bool(checks.get("postgres")) and (migrations.required_ok if migrations else True)
    status = "ok" if required_ok and all(checks.values()) else "degraded"
    issues: list[str] = []
    for name, ok in checks.items():
        if not ok:
            issues.append(f"{name.upper()}_DOWN")
    if migrations and not migrations.ok:
        issues.append("MIGRATIONS_DEGRADED")

    return {
        "version": "v1",
        "request_id": str(uuid4()),
        "status": status,
        "required_ok": required_ok,
        "checks": checks,
        "errors": errors,
        "migrations": migrations.to_dict() if migrations else None,
        "issues": issues,
    }
