"""Enable graph by default and backfill existing containers.

Revision ID: 20251205_002
Revises: 20251205_001
Create Date: 2025-12-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251205_002"
down_revision = "20251205_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "containers",
        "graph_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
    )
    op.execute("UPDATE containers SET graph_enabled = TRUE WHERE graph_enabled IS DISTINCT FROM TRUE")


def downgrade() -> None:
    op.execute("UPDATE containers SET graph_enabled = FALSE WHERE graph_enabled IS DISTINCT FROM FALSE")
    op.alter_column(
        "containers",
        "graph_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
    )

