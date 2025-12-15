"""UserHiddenChannel model - tracks hidden channels per user for Discover filtering."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserHiddenChannel(Base):
    """
    Tracks channels that a user has hidden from Discover results.

    Hidden channels are filtered out of video and channel search results
    on the Discover page. Each user maintains their own list.
    """
    __tablename__ = "user_hidden_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Channel identification (platform + channel_id is unique per platform)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Display info for Settings UI
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    hidden_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="hidden_channels")

    # Unique constraint: one entry per user per platform per channel
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "channel_id", name="uix_user_platform_channel"),
    )

    def __repr__(self) -> str:
        return f"<UserHiddenChannel(user_id={self.user_id}, platform={self.platform}, channel={self.channel_name})>"
