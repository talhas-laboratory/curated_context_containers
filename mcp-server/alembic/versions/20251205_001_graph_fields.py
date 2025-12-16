"""Add graph fields to containers for graph RAG.

Revision ID: 20251205_001
Revises: 20251127_001
Create Date: 2025-12-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251205_001"
down_revision = "20251127_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "containers",
        sa.Column("graph_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("containers", sa.Column("graph_url", sa.Text(), nullable=True))
    op.add_column(
        "containers",
        sa.Column("graph_schema", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("containers", "graph_schema")
    op.drop_column("containers", "graph_url")
    op.drop_column("containers", "graph_enabled")
