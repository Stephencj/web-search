"""Channel model - represents a subscribed video channel."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.feed_item import FeedItem


class Channel(Base):
    """
    Represents a subscribed video channel (YouTube, Rumble, etc.).

    Tracks channel metadata and sync status for the personal feed.
    Subscriptions are per-user.
    """
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User ownership
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Platform identification
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True  # "youtube", "rumble"
    )
    platform_channel_id: Mapped[str] = mapped_column(
        String(100), nullable=False  # YouTube channel ID or Rumble username
    )
    channel_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Display info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    subscriber_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Sync configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_sync_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Import tracking
    import_source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True  # "manual", "takeout", "bookmarklet"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    feed_items: Mapped[list["FeedItem"]] = relationship(
        "FeedItem",
        back_populates="channel",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Unique constraint: one channel per platform per user
    __table_args__ = (
        UniqueConstraint('user_id', 'platform', 'platform_channel_id', name='uix_user_platform_channel'),
    )

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.name or self.platform_channel_id

    @property
    def video_count(self) -> int:
        """Get count of feed items."""
        return len(self.feed_items) if self.feed_items else 0

    @property
    def unwatched_count(self) -> int:
        """Get count of unwatched videos."""
        if not self.feed_items:
            return 0
        return sum(1 for item in self.feed_items if not item.is_watched)

    def mark_sync_success(self) -> None:
        """Mark channel as successfully synced."""
        self.last_synced_at = datetime.utcnow()
        self.last_sync_error = None
        self.consecutive_errors = 0

    def mark_sync_error(self, error: str) -> None:
        """Mark channel sync as failed."""
        self.last_sync_error = error[:500] if error else None
        self.consecutive_errors += 1

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, platform='{self.platform}', name='{self.name[:30]}')>"
