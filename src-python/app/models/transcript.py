"""Transcript model - stores speech-to-text transcription for feed items."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.feed_item import FeedItem


class Transcript(Base):
    """
    Stores transcription data for a feed item.

    Transcriptions are generated on-demand using Whisper and stored
    for search and chapter generation.
    """
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    feed_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("feed_items.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Transcription metadata
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "whisper-small"
    language: Mapped[str] = mapped_column(String(10), default="en")  # ISO 639-1 code

    # Transcription content
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full transcript for search
    segments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [{"start": 0.0, "end": 2.5, "text": "..."}]

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100 percentage

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    feed_item: Mapped["FeedItem"] = relationship("FeedItem", backref="transcript")

    def __repr__(self) -> str:
        return f"<Transcript(id={self.id}, feed_item_id={self.feed_item_id}, status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "feed_item_id": self.feed_item_id,
            "model_used": self.model_used,
            "language": self.language,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "segment_count": len(self.segments) if self.segments else 0,
            "has_full_text": bool(self.full_text),
        }
