"""add video_stream_url column

Revision ID: 001_video_stream_url
Revises:
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_video_stream_url'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add video_stream_url column to feed_items table
    op.add_column('feed_items', sa.Column('video_stream_url', sa.String(1000), nullable=True))


def downgrade():
    op.drop_column('feed_items', 'video_stream_url')
