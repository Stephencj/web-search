"""add like_count and tags columns to feed_items

Revision ID: 003_youtube_metadata
Revises: 002_content_type
Create Date: 2026-01-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_youtube_metadata'
down_revision = '002_content_type'
branch_labels = None
depends_on = None


def upgrade():
    # Add like_count column (integer, nullable - not all platforms have likes)
    op.add_column('feed_items', sa.Column('like_count', sa.Integer(), nullable=True))

    # Add tags column (JSON array, nullable)
    op.add_column('feed_items', sa.Column('tags', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('feed_items', 'tags')
    op.drop_column('feed_items', 'like_count')
