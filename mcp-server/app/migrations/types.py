from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@dataclass(frozen=True)
class SubsystemMigrationReport:
    subsystem: str
    ok: bool
    status: str  # ok | failed | skipped
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "ok": self.ok,
            "status": self.status,
            "started_at": _iso(self.started_at),
            "finished_at": _iso(self.finished_at),
            "duration_ms": self.duration_ms,
            "details": self.details,
            "error": self.error,
        }


@dataclass(frozen=True)
class MigrationReport:
    ok: bool
    required_ok: bool
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    subsystems: dict[str, SubsystemMigrationReport] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "required_ok": self.required_ok,
            "started_at": _iso(self.started_at),
            "finished_at": _iso(self.finished_at),
            "duration_ms": self.duration_ms,
            "subsystems": {k: v.to_dict() for k, v in self.subsystems.items()},
        }

