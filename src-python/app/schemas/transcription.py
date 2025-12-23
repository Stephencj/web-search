"""Pydantic schemas for transcription and chapters."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    """A segment of transcribed text with timestamps."""
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    """Response schema for Transcript."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    feed_item_id: int
    model_used: str
    language: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    segment_count: int = 0
    has_full_text: bool = False


class TranscriptWithText(TranscriptResponse):
    """Transcript with full text and segments."""
    full_text: Optional[str] = None
    segments: Optional[list[TranscriptSegment]] = None


class TranscriptionRequest(BaseModel):
    """Request to start transcription."""
    generate_chapters: bool = Field(
        default=True,
        description="Parse description and generate chapters after transcription"
    )


class TranscriptionStatusResponse(BaseModel):
    """Status of a transcription job."""
    feed_item_id: int
    status: Literal["pending", "processing", "completed", "failed", "not_found"]
    progress: Optional[int] = None
    error_message: Optional[str] = None
    transcript_id: Optional[int] = None


class ChapterResponse(BaseModel):
    """Response schema for Chapter."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    feed_item_id: int
    title: str
    description: Optional[str] = None
    start_seconds: float
    end_seconds: Optional[float] = None
    start_formatted: str = ""
    source: Literal["manual", "description_parse", "transcript_match", "pending_match"]
    confidence: Optional[float] = None
    order_index: int = 0
    created_at: Optional[datetime] = None


class ChapterCreate(BaseModel):
    """Schema for creating a manual chapter."""
    title: str = Field(..., min_length=1, max_length=500)
    start_seconds: float = Field(..., ge=0)
    end_seconds: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)


class ChapterUpdate(BaseModel):
    """Schema for updating a chapter."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    start_seconds: Optional[float] = Field(default=None, ge=0)
    end_seconds: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)
    order_index: Optional[int] = Field(default=None, ge=0)


class ChapterListResponse(BaseModel):
    """List of chapters for a feed item."""
    feed_item_id: int
    chapters: list[ChapterResponse]
    total: int
