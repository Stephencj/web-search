"""CrawlJob model - tracks crawl execution status."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.source import Source


class CrawlJob(Base):
    """
    Represents a crawl job execution.

    Tracks progress, statistics, and errors for each crawl run.
    """
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )

    # Status: pending, running, completed, failed, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Statistics
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_indexed: Mapped[int] = mapped_column(Integer, default=0)
    pages_skipped: Mapped[int] = mapped_column(Integer, default=0)  # duplicates, excluded
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Trigger type
    trigger: Mapped[str] = mapped_column(
        String(20), default="manual"  # manual, scheduled
    )

    # Created timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="crawl_jobs")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate crawl duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == "running"

    @property
    def is_finished(self) -> bool:
        """Check if job has finished (success or failure)."""
        return self.status in ("completed", "failed", "cancelled")

    def start(self) -> None:
        """Mark job as started."""
        self.status = "running"
        self.started_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark job as completed successfully."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()

    def fail(self, error: str, details: Optional[dict] = None) -> None:
        """Mark job as failed."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error[:1000] if error else None
        self.error_details = details

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<CrawlJob(id={self.id}, source_id={self.source_id}, status='{self.status}')>"
