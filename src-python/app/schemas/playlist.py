"""Pydantic schemas for Playlist operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PlaylistBase(BaseModel):
    """Base schema for Playlist."""
    platform: str = Field(..., max_length=50)
    playlist_id: str = Field(..., max_length=100)
    playlist_url: str = Field(..., max_length=500)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    video_count: Optional[int] = None
    channel_name: Optional[str] = Field(None, max_length=200)
    channel_url: Optional[str] = Field(None, max_length=500)


class PlaylistCreate(PlaylistBase):
    """Schema for creating a Playlist."""
    pass


class PlaylistCreateFromUrl(BaseModel):
    """Schema for creating a Playlist from just a URL (auto-fetch metadata)."""
    url: str = Field(..., max_length=500)


class PlaylistUpdate(BaseModel):
    """Schema for updating a Playlist."""
    name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class PlaylistResponse(BaseModel):
    """Schema for Playlist response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    playlist_id: str
    playlist_url: str

    name: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    video_count: Optional[int]

    channel_name: Optional[str]
    channel_url: Optional[str]

    is_active: bool
    last_synced_at: Optional[datetime]
    last_sync_error: Optional[str]
    consecutive_errors: int

    created_at: datetime
    updated_at: datetime

    # Computed properties
    display_name: str = ""


class PlaylistListResponse(BaseModel):
    """Schema for listing playlists."""
    items: list[PlaylistResponse]
    total: int


class PlaylistSyncResult(BaseModel):
    """Result of a playlist sync operation."""
    playlist_id: int
    playlist_name: str
    success: bool
    new_videos: int = 0
    error: Optional[str] = None
