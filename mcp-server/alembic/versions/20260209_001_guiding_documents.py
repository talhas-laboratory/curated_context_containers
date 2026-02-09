"""Add guiding_document_id to containers

Revision ID: 20260209_001
Revises: 20260201_001
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260209_001'
down_revision = '20260201_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add guiding_document_id column to containers table
    op.add_column('containers', sa.Column('guiding_document_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_containers_guiding_document',
        'containers', 'documents',
        ['guiding_document_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for performance
    op.create_index('idx_containers_guiding_document', 'containers', ['guiding_document_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_containers_guiding_document', table_name='containers')
    
    # Remove foreign key
    op.drop_constraint('fk_containers_guiding_document', 'containers', type_='foreignkey')
    
    # Remove column
    op.drop_column('containers', 'guiding_document_id')
