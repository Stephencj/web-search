"""add watch tracking fields to collection_items

Revision ID: 004_collection_watch
Revises: 003_youtube_metadata
Create Date: 2026-01-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_collection_watch'
down_revision = '003_youtube_metadata'
branch_labels = None
depends_on = None


def upgrade():
    # Add watch tracking fields to collection_items
    # Note: SQLite interprets 'false' string as truthy, must use '0' for false
    op.add_column('collection_items', sa.Column('is_watched', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('collection_items', sa.Column('watched_at', sa.DateTime(), nullable=True))
    op.add_column('collection_items', sa.Column('watch_progress_seconds', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('collection_items', 'watch_progress_seconds')
    op.drop_column('collection_items', 'watched_at')
    op.drop_column('collection_items', 'is_watched')
