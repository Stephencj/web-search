"""Channel management API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from app.api.deps import DbSession, CurrentUserOrDefault
from app.models import Channel
from app.schemas.channel import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelListResponse,
    ChannelImportUrl,
    ChannelImportTakeout,
    ImportResult,
    SyncResult,
    ChannelSearchResult,
    ChannelSearchResponse,
)
from app.services.channel_service import get_channel_service
from app.services.channel_search_service import (
    search_youtube_channels,
    search_rumble_channels,
    search_podcast_channels,
)

router = APIRouter()


def _channel_to_response(channel: Channel) -> ChannelResponse:
    """Convert Channel model to response schema."""
    return ChannelResponse(
        id=channel.id,
        platform=channel.platform,
        platform_channel_id=channel.platform_channel_id,
        channel_url=channel.channel_url,
        name=channel.name,
        description=channel.description,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        subscriber_count=channel.subscriber_count,
        is_active=channel.is_active,
        last_synced_at=channel.last_synced_at,
        last_sync_error=channel.last_sync_error,
        consecutive_errors=channel.consecutive_errors,
        import_source=channel.import_source,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        display_name=channel.display_name,
        video_count=channel.video_count,
        unwatched_count=channel.unwatched_count,
    )


@router.get("", response_model=ChannelListResponse)
async def list_channels(
    db: DbSession,
    user: CurrentUserOrDefault,
    platform: Optional[str] = Query(None, description="Filter by platform (youtube, rumble)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> ChannelListResponse:
    """List all subscribed channels for the current user."""
    service = get_channel_service()
    channels = await service.list_channels(db, platform=platform, is_active=is_active, user_id=user.id)

    return ChannelListResponse(
        items=[_channel_to_response(c) for c in channels],
        total=len(channels),
    )


@router.get("/search", response_model=ChannelSearchResponse)
async def search_channels(
    query: str = Query(..., min_length=2, description="Search query"),
    platform: str = Query("youtube", description="Platform to search (youtube, rumble, podcast)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
) -> ChannelSearchResponse:
    """
    Search for channels by name on YouTube, Rumble, or Podcasts.

    This allows users to find and subscribe to channels without needing the exact URL.
    """
    if platform not in ("youtube", "rumble", "podcast"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'youtube', 'rumble', or 'podcast'",
        )

    try:
        if platform == "youtube":
            results = await search_youtube_channels(query, limit)
        elif platform == "rumble":
            results = await search_rumble_channels(query, limit)
        else:
            results = await search_podcast_channels(query, limit)

        return ChannelSearchResponse(
            query=query,
            platform=platform,
            results=results,
            total=len(results),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def add_channel(data: ChannelCreate, db: DbSession, user: CurrentUserOrDefault) -> ChannelResponse:
    """
    Add a new channel subscription by URL for the current user.

    Supports YouTube and Rumble channel URLs.
    """
    service = get_channel_service()

    try:
        channel = await service.add_channel(db, data.channel_url, import_source="manual", user_id=user.id)
        return _channel_to_response(channel)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: int, db: DbSession, user: CurrentUserOrDefault) -> ChannelResponse:
    """Get a channel by ID."""
    service = get_channel_service()
    channel = await service.get_channel(db, channel_id, user_id=user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with id {channel_id} not found",
        )

    return _channel_to_response(channel)


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    data: ChannelUpdate,
    db: DbSession,
    user: CurrentUserOrDefault,
) -> ChannelResponse:
    """Update a channel."""
    service = get_channel_service()

    update_data = data.model_dump(exclude_unset=True)
    channel = await service.update_channel(db, channel_id, user_id=user.id, **update_data)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with id {channel_id} not found",
        )

    return _channel_to_response(channel)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: int, db: DbSession, user: CurrentUserOrDefault) -> None:
    """Delete a channel subscription."""
    service = get_channel_service()
    deleted = await service.delete_channel(db, channel_id, user_id=user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with id {channel_id} not found",
        )


@router.post("/{channel_id}/sync", response_model=SyncResult)
async def sync_channel(channel_id: int, db: DbSession, user: CurrentUserOrDefault) -> SyncResult:
    """
    Manually trigger a sync for a channel.

    Fetches new videos from the channel.
    """
    service = get_channel_service()
    channel = await service.get_channel(db, channel_id, user_id=user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with id {channel_id} not found",
        )

    # Import sync service here to avoid circular imports
    from app.services.feed_sync_service import get_feed_sync_service

    sync_service = get_feed_sync_service()
    result = await sync_service.sync_channel(db, channel)

    return SyncResult(
        channel_id=channel.id,
        channel_name=channel.name,
        success=result.get("success", False),
        new_videos=result.get("new_videos", 0),
        error=result.get("error"),
    )


@router.post("/import/urls", response_model=ImportResult)
async def import_from_urls(data: ChannelImportUrl, db: DbSession, user: CurrentUserOrDefault) -> ImportResult:
    """
    Import channels from a list of URLs for the current user.

    Useful for importing from a bookmarklet or manual list.
    """
    service = get_channel_service()
    result = await service.import_from_urls(db, data.urls, import_source="bookmarklet", user_id=user.id)

    return ImportResult(
        imported=result["imported"],
        skipped=result["skipped"],
        failed=result["failed"],
        channels=[_channel_to_response(c) for c in result["channels"]],
        errors=result["errors"],
    )


@router.post("/import/takeout", response_model=ImportResult)
async def import_from_takeout(data: ChannelImportTakeout, db: DbSession, user: CurrentUserOrDefault) -> ImportResult:
    """
    Import channels from Google Takeout subscriptions export for the current user.

    Upload the subscriptions.json content from Google Takeout.
    """
    service = get_channel_service()
    result = await service.import_from_takeout(db, data.subscriptions, user_id=user.id)

    return ImportResult(
        imported=result["imported"],
        skipped=result["skipped"],
        failed=result["failed"],
        channels=[_channel_to_response(c) for c in result["channels"]],
        errors=result["errors"],
    )
