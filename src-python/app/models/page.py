"""Page model - represents a crawled web page."""

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Page(Base):
    """
    Represents a crawled web page.

    Stores metadata about crawled pages for tracking and deduplication.
    Actual content is stored in Meilisearch; raw HTML optionally on disk.
    """
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # URL and hash for deduplication
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Content metadata
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)  # SimHash
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Crawl metadata
    first_crawled_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    last_crawled_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    last_modified: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True  # From HTTP headers
    )
    crawl_status: Mapped[str] = mapped_column(String(20), default="success")
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Raw HTML storage reference
    raw_html_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    @property
    def meilisearch_id(self) -> str:
        """Get Meilisearch document ID."""
        return str(self.id)

    @staticmethod
    def compute_url_hash(url: str) -> str:
        """Compute SHA-256 hash of URL for deduplication."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    @classmethod
    def create(cls, source_id: int, url: str, **kwargs) -> "Page":
        """Create a new page with auto-computed URL hash."""
        return cls(
            source_id=source_id,
            url=url,
            url_hash=cls.compute_url_hash(url),
            **kwargs
        )

    def update_crawl(self, http_status: int, title: Optional[str] = None) -> None:
        """Update page after re-crawl."""
        self.last_crawled_at = datetime.utcnow()
        self.http_status = http_status
        if title:
            self.title = title[:500]
        self.crawl_status = "success" if 200 <= http_status < 400 else "error"

    def __repr__(self) -> str:
        return f"<Page(id={self.id}, url='{self.url[:50]}...')>"
