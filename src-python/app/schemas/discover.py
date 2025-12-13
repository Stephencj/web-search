"""Schemas for the discover API."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class VideoResultSchema(BaseModel):
    """Video search result."""

    platform: str
    video_id: str
    video_url: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    upload_date: Optional[datetime] = None
    channel_name: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    channel_avatar_url: Optional[str] = None
    like_count: Optional[int] = None
    tags: list[str] = Field(default_factory=list)


class ChannelResultSchema(BaseModel):
    """Channel search result."""

    platform: str
    channel_id: str
    channel_url: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None


class PlaylistResultSchema(BaseModel):
    """Playlist search result."""

    platform: str
    playlist_id: str
    playlist_url: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_count: Optional[int] = None
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None


class PlatformInfoSchema(BaseModel):
    """Platform information."""

    id: str
    name: str
    icon: str
    color: str
    supports_search: bool
    supports_channel_feed: bool
    supports_playlists: bool


class SearchTimingSchema(BaseModel):
    """Timing information for platform search."""

    platform: str
    duration_ms: int
    success: bool
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """Search request body."""

    query: str = Field(..., min_length=1, max_length=500)
    platforms: Optional[list[str]] = Field(
        None, description="Platform IDs to search (null = all)"
    )
    type: Literal["videos", "channels", "playlists"] = Field(
        default="videos", description="Type of content to search"
    )
    max_per_platform: int = Field(
        default=10, ge=1, le=50, description="Max results per platform"
    )


class VideoSearchResponse(BaseModel):
    """Response for video search."""

    query: str
    search_type: str = "videos"
    total_results: int
    results: list[VideoResultSchema]
    by_platform: dict[str, list[VideoResultSchema]]
    timings: list[SearchTimingSchema]
    total_duration_ms: int
    platforms_searched: list[str]
    platforms_failed: list[str]


class ChannelSearchResponse(BaseModel):
    """Response for channel search."""

    query: str
    search_type: str = "channels"
    total_results: int
    results: list[ChannelResultSchema]
    by_platform: dict[str, list[ChannelResultSchema]]
    timings: list[SearchTimingSchema]
    total_duration_ms: int
    platforms_searched: list[str]
    platforms_failed: list[str]


class PlaylistSearchResponse(BaseModel):
    """Response for playlist search."""

    query: str
    search_type: str = "playlists"
    total_results: int
    results: list[PlaylistResultSchema]
    by_platform: dict[str, list[PlaylistResultSchema]]
    timings: list[SearchTimingSchema]
    total_duration_ms: int
    platforms_searched: list[str]
    platforms_failed: list[str]


class QuickSaveRequest(BaseModel):
    """Request to quick-save a URL."""

    url: str = Field(..., description="URL to video, channel, or playlist")


class QuickSaveResponse(BaseModel):
    """Response from quick-save."""

    type: Literal["video", "channel", "playlist"]
    platform: str
    saved: VideoResultSchema | ChannelResultSchema | PlaylistResultSchema
    message: str


class PlatformListResponse(BaseModel):
    """Response listing available platforms."""

    platforms: list[PlatformInfoSchema]
    total: int
