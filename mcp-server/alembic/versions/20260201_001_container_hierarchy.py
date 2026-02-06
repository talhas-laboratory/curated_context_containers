"""Add parent_id to containers for hierarchy support.

Revision ID: 20260201_001
Revises: 20251205_002
Create Date: 2026-02-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260201_001"
down_revision = "20251205_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "containers",
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("containers.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("idx_containers_parent", "containers", ["parent_id"])


def downgrade() -> None:
    op.drop_index("idx_containers_parent", table_name="containers")
    op.drop_column("containers", "parent_id")
