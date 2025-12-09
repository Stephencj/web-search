"""Index model - represents a search index collection."""

import re
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.source import Source


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text


class Index(Base):
    """
    Represents a search index collection.

    Each index has its own set of sources, crawl rules, and ranking settings.
    Examples: "AI Research", "Local News", "Cooking"
    """
    __tablename__ = "indexes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Ranking configuration stored as JSON
    ranking_config: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "domain_boosts": {},      # {"arxiv.org": 1.5, "medium.com": 0.8}
            "recency_weight": 0.3,    # 0.0-1.0, higher = more recency bias
            "custom_weights": {}      # Future: ML model weights
        }
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sources: Mapped[list["Source"]] = relationship(
        "Source",
        back_populates="index",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    @property
    def meilisearch_index(self) -> str:
        """Get the Meilisearch index name."""
        return f"websearch_{self.slug}"

    @classmethod
    def create(cls, name: str, description: Optional[str] = None, **kwargs) -> "Index":
        """Create a new index with auto-generated slug."""
        return cls(
            name=name,
            slug=slugify(name),
            description=description,
            **kwargs
        )

    def __repr__(self) -> str:
        return f"<Index(id={self.id}, name='{self.name}', slug='{self.slug}')>"
