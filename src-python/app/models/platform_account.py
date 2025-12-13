"""PlatformAccount model - stores OAuth tokens for video platforms."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlatformAccount(Base):
    """
    Stores OAuth tokens for video platforms (YouTube, etc.).

    Enables premium features like ad-free playback, higher quality streams,
    and access to members-only content.
    """
    __tablename__ = "platform_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Platform identification
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True  # "youtube", "rumble"
    )
    account_email: Mapped[str] = mapped_column(String(200), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Encrypted OAuth tokens (Fernet encrypted)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # OAuth scopes granted
    scopes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True  # JSON array of scope strings
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_premium: Mapped[bool] = mapped_column(
        Boolean, default=False  # Has YouTube Premium or equivalent
    )

    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_refresh_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Unique constraint: one account per platform per email
    __table_args__ = (
        UniqueConstraint('platform', 'account_email', name='uix_platform_account_email'),
    )

    @property
    def display_name(self) -> str:
        """Get display name for the account."""
        return self.account_name or self.account_email

    @property
    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if the token needs refreshing (within 5 minutes of expiry)."""
        if not self.token_expires_at:
            return False
        from datetime import timedelta
        buffer = timedelta(minutes=5)
        return datetime.utcnow() >= (self.token_expires_at - buffer)

    def mark_used(self) -> None:
        """Mark the account as recently used."""
        self.last_used_at = datetime.utcnow()

    def mark_refreshed(self) -> None:
        """Mark tokens as refreshed."""
        self.last_refresh_at = datetime.utcnow()
        self.last_error = None

    def mark_error(self, error: str) -> None:
        """Record an error with the account."""
        self.last_error = error[:500] if error else None

    def __repr__(self) -> str:
        return f"<PlatformAccount(id={self.id}, platform='{self.platform}', email='{self.account_email}')>"
