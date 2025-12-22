"""Add agent tracking and container lifecycle fields.

Revision ID: 20251127_001
Revises: 20251109_001
Create Date: 2025-11-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251127_001'
down_revision = '20251109_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add agent tracking fields to containers
    op.add_column('containers', sa.Column('created_by_agent', sa.Text(), nullable=True))
    op.add_column('containers', sa.Column('mission_context', sa.Text(), nullable=True))
    op.add_column('containers', sa.Column('auto_refresh', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('containers', sa.Column('visibility', sa.Text(), server_default='private', nullable=False))
    op.add_column('containers', sa.Column('collaboration_policy', sa.Text(), server_default='read-only', nullable=False))

    # Create agent_sessions table
    op.create_table(
        'agent_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', sa.Text(), nullable=False, index=True),
        sa.Column('agent_name', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_active', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )

    # Create index on agent_id
    op.create_index('ix_agent_sessions_agent_id', 'agent_sessions', ['agent_id'])

    # Create container_links table for multi-agent collaboration
    op.create_table(
        'container_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_container_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('target_container_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('relationship', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by_agent', sa.Text(), nullable=True),
    )

    # Create container_subscriptions table
    op.create_table(
        'container_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('container_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('agent_id', sa.Text(), nullable=False, index=True),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('events', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_notified', sa.DateTime(), nullable=True),
    )

    # Create unique constraint on container_id + agent_id
    op.create_unique_constraint(
        'uq_container_subscriptions_container_agent',
        'container_subscriptions',
        ['container_id', 'agent_id']
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('container_subscriptions')
    op.drop_table('container_links')
    op.drop_table('agent_sessions')

    # Drop columns from containers
    op.drop_column('containers', 'collaboration_policy')
    op.drop_column('containers', 'visibility')
    op.drop_column('containers', 'auto_refresh')
    op.drop_column('containers', 'mission_context')
    op.drop_column('containers', 'created_by_agent')








