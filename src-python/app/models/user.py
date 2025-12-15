"""User model - represents a user account in the system."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user_hidden_channel import UserHiddenChannel
    from app.models.user_session import UserSession
    from app.models.user_watch_state import UserWatchState


class User(Base):
    """
    Represents a user account in the system.

    Users can optionally have a PIN for authentication.
    In "open mode", users can be created and used without any authentication.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Authentication (optional - nullable for passwordless users)
    pin_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Profile
    avatar_color: Mapped[str] = mapped_column(
        String(20), default="#6366f1", nullable=False
    )

    # Permissions
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    watch_states: Mapped[list["UserWatchState"]] = relationship(
        "UserWatchState", back_populates="user", cascade="all, delete-orphan"
    )
    hidden_channels: Mapped[list["UserHiddenChannel"]] = relationship(
        "UserHiddenChannel", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_pin(self) -> bool:
        """Check if user has a PIN set."""
        return self.pin_hash is not None

    @property
    def initials(self) -> str:
        """Get user initials for avatar display."""
        parts = self.display_name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.display_name[:2].upper()

    def mark_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
