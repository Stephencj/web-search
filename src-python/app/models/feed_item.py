"""FeedItem model - represents a video from a subscribed channel."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.channel import Channel
    from app.models.user_watch_state import UserWatchState


class FeedItem(Base):
    """
    Represents a video from a subscribed channel in the personal feed.

    Tracks video metadata and watch state.
    """
    __tablename__ = "feed_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Video identification
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True  # "youtube", "rumble"
    )
    video_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True  # Platform-specific video ID
    )
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    view_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    categories: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)  # YouTube categories

    # Podcast/audio fields (from RSS enclosure)
    audio_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Direct audio file URL
    audio_file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Size in bytes
    audio_mime_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., 'audio/mpeg'

    # Video stream URL (for platforms with separate video files like Redbar)
    video_stream_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Direct video file URL

    # Watch state
    is_watched: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    watched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    watch_progress_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="feed_items")
    watch_states: Mapped[list["UserWatchState"]] = relationship(
        "UserWatchState", back_populates="feed_item", cascade="all, delete-orphan"
    )

    # Unique constraint: one video per platform
    __table_args__ = (
        UniqueConstraint('platform', 'video_id', name='uix_platform_video'),
    )

    @property
    def duration_formatted(self) -> str:
        """Get duration as HH:MM:SS or MM:SS."""
        if not self.duration_seconds:
            return ""
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def is_recent(self) -> bool:
        """Check if video was uploaded in the last 24 hours."""
        if not self.upload_date:
            return False
        delta = datetime.utcnow() - self.upload_date
        return delta.total_seconds() < 86400  # 24 hours

    def mark_watched(self) -> None:
        """Mark video as watched."""
        self.is_watched = True
        self.watched_at = datetime.utcnow()

    def mark_unwatched(self) -> None:
        """Mark video as unwatched."""
        self.is_watched = False
        self.watched_at = None
        self.watch_progress_seconds = None

    def __repr__(self) -> str:
        return f"<FeedItem(id={self.id}, platform='{self.platform}', title='{self.title[:30]}')>"
