"""UserWatchState model - tracks watch progress per user per video."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.feed_item import FeedItem
    from app.models.user import User


class UserWatchState(Base):
    """
    Tracks watch progress for a specific user on a specific feed item.

    This enables per-user watch history while sharing the same feed items
    across all users.
    """
    __tablename__ = "user_watch_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feed_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("feed_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Watch state
    is_watched: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    watch_progress_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    watched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="watch_states")
    feed_item: Mapped["FeedItem"] = relationship("FeedItem", back_populates="watch_states")

    # Unique constraint: one watch state per user per feed item
    __table_args__ = (
        UniqueConstraint("user_id", "feed_item_id", name="uix_user_feed_item"),
    )

    def mark_watched(self) -> None:
        """Mark as watched."""
        self.is_watched = True
        self.watched_at = datetime.utcnow()

    def mark_unwatched(self) -> None:
        """Mark as unwatched."""
        self.is_watched = False
        self.watched_at = None
        self.watch_progress_seconds = None

    def update_progress(self, seconds: int) -> None:
        """Update watch progress."""
        self.watch_progress_seconds = seconds
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<UserWatchState(user_id={self.user_id}, feed_item_id={self.feed_item_id}, watched={self.is_watched})>"
