"""ApiKey model - stores external API credentials."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApiKey(Base):
    """
    Stores API keys for external search providers.

    Tracks usage to stay within rate limits.
    """
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # google, bing, brave, etc.

    # Credentials (consider encryption for production)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    # Some APIs need additional credentials
    extra_config: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage tracking
    daily_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    daily_usage: Mapped[int] = mapped_column(Integer, default=0)
    usage_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def is_quota_exceeded(self) -> bool:
        """Check if daily quota is exceeded."""
        if self.daily_limit is None:
            return False
        return self.daily_usage >= self.daily_limit

    @property
    def remaining_quota(self) -> Optional[int]:
        """Get remaining daily quota."""
        if self.daily_limit is None:
            return None
        return max(0, self.daily_limit - self.daily_usage)

    def increment_usage(self, count: int = 1) -> None:
        """Increment usage counter."""
        self.daily_usage += count

    def reset_usage(self) -> None:
        """Reset daily usage counter."""
        self.daily_usage = 0
        self.usage_reset_at = datetime.utcnow()

    @property
    def masked_key(self) -> str:
        """Get masked API key for display."""
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]

    def __repr__(self) -> str:
        return f"<ApiKey(provider='{self.provider}', active={self.is_active})>"
