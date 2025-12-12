"""Source model - represents a crawl source configuration."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.crawl_job import CrawlJob
    from app.models.index import Index


class Source(Base):
    """
    Represents a crawl source (domain, URL, or sitemap).

    Defines what to crawl, how deep, how often, and what to include/exclude.
    """
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("indexes.id", ondelete="CASCADE"), nullable=False
    )

    # Source definition
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(20), default="domain"  # "domain", "url", "sitemap"
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Crawl configuration
    crawl_depth: Mapped[int] = mapped_column(Integer, default=2)
    crawl_frequency: Mapped[str] = mapped_column(
        String(20), default="daily"  # "hourly", "daily", "weekly", "monthly"
    )
    max_pages: Mapped[int] = mapped_column(Integer, default=1000)

    # Filtering rules (JSON arrays)
    include_patterns: Mapped[list] = mapped_column(
        JSON, default=list  # ["/blog/*", "/docs/*"]
    )
    exclude_patterns: Mapped[list] = mapped_column(
        JSON, default=list  # ["/admin/*", "*.pdf"]
    )

    # robots.txt behavior
    respect_robots: Mapped[bool] = mapped_column(Boolean, default=True)

    # Content extraction mode
    crawl_mode: Mapped[str] = mapped_column(
        String(20), default="all"  # "text_only", "images_only", "videos_only", "text_images", "text_videos", "images_videos", "all"
    )

    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="sources")
    crawl_jobs: Mapped[list["CrawlJob"]] = relationship(
        "CrawlJob",
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return parsed.netloc or parsed.path.split('/')[0]

    @property
    def display_name(self) -> str:
        """Get display name (custom name or domain)."""
        return self.name or self.domain

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, url='{self.url[:50]}...', index_id={self.index_id})>"
