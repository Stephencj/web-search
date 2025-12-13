"""Pydantic schemas for SavedVideo operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SavedVideoBase(BaseModel):
    """Base schema for SavedVideo."""
    platform: str = Field(..., max_length=50)
    video_id: str = Field(..., max_length=100)
    video_url: str = Field(..., max_length=500)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    upload_date: Optional[datetime] = None
    channel_name: Optional[str] = Field(None, max_length=200)
    channel_id: Optional[str] = Field(None, max_length=100)
    channel_url: Optional[str] = Field(None, max_length=500)


class SavedVideoCreate(SavedVideoBase):
    """Schema for creating a SavedVideo."""
    notes: Optional[str] = None


class SavedVideoCreateFromUrl(BaseModel):
    """Schema for creating a SavedVideo from just a URL (auto-fetch metadata)."""
    url: str = Field(..., max_length=500)
    notes: Optional[str] = None


class SavedVideoUpdate(BaseModel):
    """Schema for updating a SavedVideo."""
    notes: Optional[str] = None
    is_watched: Optional[bool] = None
    watch_progress_seconds: Optional[int] = None


class SavedVideoResponse(BaseModel):
    """Schema for SavedVideo response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    video_id: str
    video_url: str

    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: Optional[int]
    view_count: Optional[int]
    upload_date: Optional[datetime]

    channel_name: Optional[str]
    channel_id: Optional[str]
    channel_url: Optional[str]

    is_watched: bool
    watched_at: Optional[datetime]
    watch_progress_seconds: Optional[int]

    notes: Optional[str]
    saved_at: datetime
    updated_at: datetime

    # Computed properties
    duration_formatted: str = ""


class SavedVideoListResponse(BaseModel):
    """Schema for listing saved videos."""
    items: list[SavedVideoResponse]
    total: int


class SavedVideoStats(BaseModel):
    """Statistics for saved videos."""
    total_videos: int
    watched_videos: int
    unwatched_videos: int
    by_platform: dict[str, int]
