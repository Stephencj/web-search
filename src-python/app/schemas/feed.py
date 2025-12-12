"""Pydantic schemas for Feed operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class FeedItemResponse(BaseModel):
    """Schema for FeedItem response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    platform: str
    video_id: str
    video_url: str

    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: Optional[int]
    view_count: Optional[int]
    upload_date: datetime

    is_watched: bool
    watched_at: Optional[datetime]
    watch_progress_seconds: Optional[int]

    discovered_at: datetime

    # Computed
    duration_formatted: str = ""
    is_recent: bool = False

    # Joined from channel (optional)
    channel_name: Optional[str] = None
    channel_avatar_url: Optional[str] = None


class FeedItemWithChannel(FeedItemResponse):
    """FeedItem with channel info included."""
    channel_name: str
    channel_avatar_url: Optional[str] = None


class FeedResponse(BaseModel):
    """Schema for paginated feed response."""
    items: list[FeedItemWithChannel]
    total: int
    page: int
    per_page: int
    has_more: bool


class ChannelGroupedFeed(BaseModel):
    """Feed items grouped by channel."""
    channel_id: int
    channel_name: str
    channel_avatar_url: Optional[str]
    platform: str
    items: list[FeedItemResponse]
    total_items: int
    unwatched_count: int


class ChannelGroupedFeedResponse(BaseModel):
    """Response for channel-grouped feed."""
    channels: list[ChannelGroupedFeed]
    total_channels: int
    total_items: int


class FeedQuery(BaseModel):
    """Query parameters for feed."""
    view: Literal["chronological", "by_channel"] = "chronological"
    filter: Literal["all", "unwatched", "watched"] = "all"
    platform: Optional[Literal["youtube", "rumble"]] = None
    channel_ids: Optional[list[int]] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)
    since: Optional[datetime] = None


class WatchStateUpdate(BaseModel):
    """Schema for updating watch state."""
    is_watched: bool
    watch_progress_seconds: Optional[int] = None
