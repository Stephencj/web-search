"""Pydantic schemas for API validation."""

from app.schemas.index import (
    IndexCreate,
    IndexUpdate,
    IndexResponse,
    IndexListResponse,
)
from app.schemas.source import (
    SourceCreate,
    SourceUpdate,
    SourceResponse,
)
from app.schemas.search import (
    SearchRequest,
    SearchResult,
    SearchResponse,
)
from app.schemas.channel import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelListResponse,
    ChannelImportUrl,
    ChannelImportTakeout,
    ImportResult,
    SyncResult,
)
from app.schemas.feed import (
    FeedItemResponse,
    FeedItemWithChannel,
    FeedResponse,
    FeedQuery,
    ChannelGroupedFeed,
    ChannelGroupedFeedResponse,
    WatchStateUpdate,
)
from app.schemas.settings import (
    SettingValue,
    CrawlerSettingsResponse,
    CrawlerSettingsUpdate,
    ApiKeyCreate,
    ApiKeyResponse,
    AppSettingsResponse,
    SettingUpdateResponse,
)

__all__ = [
    "IndexCreate",
    "IndexUpdate",
    "IndexResponse",
    "IndexListResponse",
    "SourceCreate",
    "SourceUpdate",
    "SourceResponse",
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    # Channel
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelResponse",
    "ChannelListResponse",
    "ChannelImportUrl",
    "ChannelImportTakeout",
    "ImportResult",
    "SyncResult",
    # Feed
    "FeedItemResponse",
    "FeedItemWithChannel",
    "FeedResponse",
    "FeedQuery",
    "ChannelGroupedFeed",
    "ChannelGroupedFeedResponse",
    "WatchStateUpdate",
    # Settings
    "SettingValue",
    "CrawlerSettingsResponse",
    "CrawlerSettingsUpdate",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "AppSettingsResponse",
    "SettingUpdateResponse",
]
