"""Pydantic schemas for Channel operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class ChannelBase(BaseModel):
    """Base schema for Channel."""
    channel_url: str = Field(..., max_length=500)


class ChannelCreate(ChannelBase):
    """Schema for creating a Channel (minimal - URL only)."""
    pass


class ChannelImportUrl(BaseModel):
    """Schema for importing channels from URL list."""
    urls: list[str] = Field(..., min_length=1, max_length=1000)


class ChannelImportTakeout(BaseModel):
    """Schema for importing channels from Google Takeout."""
    subscriptions: list[dict]  # Raw Takeout JSON format


class ChannelUpdate(BaseModel):
    """Schema for updating a Channel."""
    name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class ChannelResponse(BaseModel):
    """Schema for Channel response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    platform_channel_id: str
    channel_url: str

    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    banner_url: Optional[str]
    subscriber_count: Optional[int]

    is_active: bool
    last_synced_at: Optional[datetime]
    last_sync_error: Optional[str]
    consecutive_errors: int

    import_source: Optional[str]

    created_at: datetime
    updated_at: datetime

    # Computed
    display_name: str = ""
    video_count: int = 0
    unwatched_count: int = 0


class ChannelListResponse(BaseModel):
    """Schema for listing channels."""
    items: list[ChannelResponse]
    total: int


class ImportResult(BaseModel):
    """Result of a channel import operation."""
    imported: int
    skipped: int
    failed: int
    channels: list[ChannelResponse]
    errors: list[str] = Field(default_factory=list)


class SyncResult(BaseModel):
    """Result of a channel sync operation."""
    channel_id: int
    channel_name: str
    success: bool
    new_videos: int = 0
    error: Optional[str] = None


class ChannelSearchResult(BaseModel):
    """A single channel search result."""
    platform: Literal["youtube", "rumble", "podcast"]
    channel_id: str
    channel_url: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None


class ChannelSearchResponse(BaseModel):
    """Response for channel search."""
    query: str
    platform: str
    results: list[ChannelSearchResult]
    total: int
