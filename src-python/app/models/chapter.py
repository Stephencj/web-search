"""Chapter model - stores timestamp chapters for feed items."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.feed_item import FeedItem


class Chapter(Base):
    """
    Represents a chapter/segment within a feed item (podcast episode or video).

    Chapters can be created from:
    - Manual entry by user
    - Parsing episode description timestamps
    - Matching description segments to transcript
    """
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    feed_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("feed_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Chapter content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(30), default="manual"
    )  # "manual", "description_parse", "transcript_match"
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 - 1.0 for matched chapters
    matched_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Transcript text that matched

    # Ordering (allows manual reordering)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    feed_item: Mapped["FeedItem"] = relationship("FeedItem", backref="chapters")

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, title='{self.title[:30]}', start={self.start_seconds})>"

    @property
    def start_formatted(self) -> str:
        """Get start time as HH:MM:SS or MM:SS."""
        total_seconds = int(self.start_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get chapter duration if end time is known."""
        if self.end_seconds is not None:
            return self.end_seconds - self.start_seconds
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "feed_item_id": self.feed_item_id,
            "title": self.title,
            "description": self.description,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "start_formatted": self.start_formatted,
            "source": self.source,
            "confidence": self.confidence,
            "order_index": self.order_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
