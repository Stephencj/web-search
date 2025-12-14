"""SavedVideo model - represents a bookmarked video from any platform."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class SavedVideo(Base):
    """
    Represents a bookmarked/saved video from any video platform.

    Unlike FeedItem which is tied to a subscribed channel,
    SavedVideo stores any video the user wants to bookmark.
    """
    __tablename__ = "saved_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User ownership (nullable for backward compatibility during migration)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Video identification
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True  # "youtube", "rumble", "odysee", "bitchute", "dailymotion"
    )
    video_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True  # Platform-specific video ID
    )
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    view_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    upload_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Channel info (denormalized for display without needing channel subscription)
    channel_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    channel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    channel_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Watch state
    is_watched: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    watched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    watch_progress_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Organization
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    saved_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", backref="saved_videos")

    # Unique constraint: one saved entry per video per platform per user
    __table_args__ = (
        UniqueConstraint('user_id', 'platform', 'video_id', name='uix_user_saved_platform_video'),
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
        return f"<SavedVideo(id={self.id}, platform='{self.platform}', title='{self.title[:30]}')>"
