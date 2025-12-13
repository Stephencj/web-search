"""Playlist model - represents a followed playlist from any video platform."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Playlist(Base):
    """
    Represents a followed playlist from any video platform.

    Users can follow playlists to have their videos synced to the feed.
    """
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Playlist identification
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True  # "youtube", "rumble", "odysee", "dailymotion"
    )
    playlist_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True  # Platform-specific playlist ID
    )
    playlist_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Metadata
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Channel info (who created the playlist)
    channel_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    channel_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Sync state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Unique constraint: one playlist per platform
    __table_args__ = (
        UniqueConstraint('platform', 'playlist_id', name='uix_playlist_platform_id'),
    )

    @property
    def display_name(self) -> str:
        """Get display name for the playlist."""
        if self.channel_name:
            return f"{self.name} ({self.channel_name})"
        return self.name

    def __repr__(self) -> str:
        return f"<Playlist(id={self.id}, platform='{self.platform}', name='{self.name[:30]}')>"
