"""Initial schema bootstrap executing migrations/001_initial_schema.sql."""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "20251109_001"
down_revision = None
branch_labels = None
depends_on = None


def _load_sql() -> str:
    root = Path(__file__).resolve().parents[3]
    schema_path = root / "migrations" / "001_initial_schema.sql"
    return schema_path.read_text()


def upgrade() -> None:
    op.execute(_load_sql())


def downgrade() -> None:
    raise RuntimeError("Downgrades are not supported for the initial schema")
