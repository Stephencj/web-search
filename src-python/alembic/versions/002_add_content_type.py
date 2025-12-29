"""add content_type column to feed_items

Revision ID: 002_content_type
Revises: 001_video_stream_url
Create Date: 2025-12-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_content_type'
down_revision = '001_video_stream_url'
branch_labels = None
depends_on = None


def upgrade():
    # Add content_type column to feed_items table
    # Values: "video" (has HLS stream), "audio" (MP3 only), None (unknown/not checked)
    op.add_column('feed_items', sa.Column('content_type', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('feed_items', 'content_type')
