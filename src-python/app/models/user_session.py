"""UserSession model - represents an active login session."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


# Default session duration: 30 days
SESSION_DURATION_DAYS = 30


class UserSession(Base):
    """
    Represents an active login session for a user.

    Sessions are created when a user logs in and can be
    invalidated on logout or expiration.
    """
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Session token (64 character random string)
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    # Device identification (optional, for display purposes)
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the session is still valid."""
        return not self.is_expired

    def refresh(self) -> None:
        """Update last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()

    def extend(self, days: int = SESSION_DURATION_DAYS) -> None:
        """Extend the session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(days=days)

    @classmethod
    def default_expiry(cls) -> datetime:
        """Get the default expiry datetime for new sessions."""
        return datetime.utcnow() + timedelta(days=SESSION_DURATION_DAYS)

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at='{self.expires_at}')>"
