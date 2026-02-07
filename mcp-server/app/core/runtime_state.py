from __future__ import annotations

from threading import Lock
from typing import Optional

from app.migrations.types import MigrationReport

_lock = Lock()
_migration_report: Optional[MigrationReport] = None


def set_migration_report(report: MigrationReport) -> None:
    global _migration_report
    with _lock:
        _migration_report = report


def clear_migration_report() -> None:
    global _migration_report
    with _lock:
        _migration_report = None


def get_migration_report() -> Optional[MigrationReport]:
    with _lock:
        return _migration_report
