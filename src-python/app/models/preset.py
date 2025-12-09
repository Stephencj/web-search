"""SearchPreset model - saved search configurations."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SearchPreset(Base):
    """
    Represents a saved search preset configuration.

    Allows users to save frequently used search configurations
    like "News Only", "Everything", "Local + Google".
    """
    __tablename__ = "search_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Which sources to include
    index_ids: Mapped[list] = mapped_column(JSON, default=list)  # [1, 2, 3] or empty for all
    external_apis: Mapped[list] = mapped_column(JSON, default=list)  # ["google", "bing"]

    # Search configuration
    default_sort: Mapped[str] = mapped_column(
        String(20), default="relevance"  # relevance, date
    )
    results_per_page: Mapped[int] = mapped_column(Integer, default=20)

    # Display settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # emoji or icon name

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def uses_local_indexes(self) -> bool:
        """Check if preset uses any local indexes."""
        return len(self.index_ids) > 0 or len(self.index_ids) == 0  # Empty means all

    @property
    def uses_external_apis(self) -> bool:
        """Check if preset uses any external APIs."""
        return len(self.external_apis) > 0

    def __repr__(self) -> str:
        return f"<SearchPreset(name='{self.name}', default={self.is_default})>"
