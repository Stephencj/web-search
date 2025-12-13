"""Feed API endpoints."""

from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models import Channel, FeedItem
from app.schemas.feed import (
    FeedItemResponse,
    FeedItemWithChannel,
    FeedResponse,
    ChannelGroupedFeed,
    ChannelGroupedFeedResponse,
    WatchStateUpdate,
)

router = APIRouter()


def _feed_item_to_response(item: FeedItem, channel: Optional[Channel] = None) -> FeedItemWithChannel:
    """Convert FeedItem model to response schema."""
    return FeedItemWithChannel(
        id=item.id,
        channel_id=item.channel_id,
        platform=item.platform,
        video_id=item.video_id,
        video_url=item.video_url,
        title=item.title,
        description=item.description,
        thumbnail_url=item.thumbnail_url,
        duration_seconds=item.duration_seconds,
        view_count=item.view_count,
        upload_date=item.upload_date,
        is_watched=item.is_watched,
        watched_at=item.watched_at,
        watch_progress_seconds=item.watch_progress_seconds,
        discovered_at=item.discovered_at,
        duration_formatted=item.duration_formatted,
        is_recent=item.is_recent,
        channel_name=channel.name if channel else item.channel.name if item.channel else "",
        channel_avatar_url=channel.avatar_url if channel else (item.channel.avatar_url if item.channel else None),
    )


@router.get("", response_model=FeedResponse)
async def get_feed(
    db: DbSession,
    filter: Literal["all", "unwatched", "watched"] = Query("all", description="Filter by watch status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    channel_ids: Optional[str] = Query(None, description="Comma-separated channel IDs"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    since: Optional[datetime] = Query(None, description="Only videos uploaded after this date"),
) -> FeedResponse:
    """
    Get the video feed in chronological order.

    Returns videos from all active subscribed channels, newest first.
    """
    # Build query - only include items from active channels
    query = (
        select(FeedItem)
        .join(Channel)
        .where(Channel.is_active == True)
        .options(selectinload(FeedItem.channel))
        .order_by(desc(FeedItem.upload_date))
    )

    # Apply filters
    if filter == "unwatched":
        query = query.where(FeedItem.is_watched == False)
    elif filter == "watched":
        query = query.where(FeedItem.is_watched == True)

    if platform:
        query = query.where(FeedItem.platform == platform)

    if channel_ids:
        ids = [int(id.strip()) for id in channel_ids.split(",") if id.strip().isdigit()]
        if ids:
            query = query.where(FeedItem.channel_id.in_(ids))

    if since:
        query = query.where(FeedItem.upload_date >= since)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return FeedResponse(
        items=[_feed_item_to_response(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(items)) < total,
    )


@router.get("/by-channel", response_model=ChannelGroupedFeedResponse)
async def get_feed_by_channel(
    db: DbSession,
    filter: Literal["all", "unwatched", "watched"] = Query("all"),
    platform: Optional[str] = Query(None),
    max_per_channel: int = Query(5, ge=1, le=20, description="Max videos per channel"),
) -> ChannelGroupedFeedResponse:
    """
    Get the video feed grouped by channel.

    Shows recent videos from each subscribed channel.
    """
    # Get all active channels
    channel_query = select(Channel).where(Channel.is_active == True)
    if platform:
        channel_query = channel_query.where(Channel.platform == platform)
    channel_query = channel_query.order_by(Channel.name)

    channel_result = await db.execute(channel_query)
    channels = list(channel_result.scalars().all())

    grouped_feeds = []
    total_items = 0

    for channel in channels:
        # Get recent videos for this channel
        item_query = (
            select(FeedItem)
            .where(FeedItem.channel_id == channel.id)
            .order_by(desc(FeedItem.upload_date))
            .limit(max_per_channel)
        )

        if filter == "unwatched":
            item_query = item_query.where(FeedItem.is_watched == False)
        elif filter == "watched":
            item_query = item_query.where(FeedItem.is_watched == True)

        item_result = await db.execute(item_query)
        items = list(item_result.scalars().all())

        if not items:
            continue

        # Count totals for this channel
        count_query = select(func.count()).where(FeedItem.channel_id == channel.id)
        unwatched_query = select(func.count()).where(
            FeedItem.channel_id == channel.id,
            FeedItem.is_watched == False,
        )

        total_result = await db.execute(count_query)
        unwatched_result = await db.execute(unwatched_query)

        channel_total = total_result.scalar() or 0
        unwatched_count = unwatched_result.scalar() or 0

        grouped_feeds.append(ChannelGroupedFeed(
            channel_id=channel.id,
            channel_name=channel.name,
            channel_avatar_url=channel.avatar_url,
            platform=channel.platform,
            items=[FeedItemResponse(
                id=item.id,
                channel_id=item.channel_id,
                platform=item.platform,
                video_id=item.video_id,
                video_url=item.video_url,
                title=item.title,
                description=item.description,
                thumbnail_url=item.thumbnail_url,
                duration_seconds=item.duration_seconds,
                view_count=item.view_count,
                upload_date=item.upload_date,
                is_watched=item.is_watched,
                watched_at=item.watched_at,
                watch_progress_seconds=item.watch_progress_seconds,
                discovered_at=item.discovered_at,
                duration_formatted=item.duration_formatted,
                is_recent=item.is_recent,
            ) for item in items],
            total_items=channel_total,
            unwatched_count=unwatched_count,
        ))

        total_items += channel_total

    return ChannelGroupedFeedResponse(
        channels=grouped_feeds,
        total_channels=len(grouped_feeds),
        total_items=total_items,
    )


@router.get("/items/{item_id}", response_model=FeedItemWithChannel)
async def get_feed_item(item_id: int, db: DbSession) -> FeedItemWithChannel:
    """Get a specific feed item."""
    result = await db.execute(
        select(FeedItem)
        .options(selectinload(FeedItem.channel))
        .where(FeedItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed item with id {item_id} not found",
        )

    return _feed_item_to_response(item)


@router.put("/items/{item_id}/watched", response_model=FeedItemWithChannel)
async def mark_watched(item_id: int, db: DbSession) -> FeedItemWithChannel:
    """Mark a feed item as watched."""
    result = await db.execute(
        select(FeedItem)
        .options(selectinload(FeedItem.channel))
        .where(FeedItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed item with id {item_id} not found",
        )

    item.mark_watched()
    await db.commit()
    await db.refresh(item)

    return _feed_item_to_response(item)


@router.put("/items/{item_id}/unwatched", response_model=FeedItemWithChannel)
async def mark_unwatched(item_id: int, db: DbSession) -> FeedItemWithChannel:
    """Mark a feed item as unwatched."""
    result = await db.execute(
        select(FeedItem)
        .options(selectinload(FeedItem.channel))
        .where(FeedItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed item with id {item_id} not found",
        )

    item.mark_unwatched()
    await db.commit()
    await db.refresh(item)

    return _feed_item_to_response(item)


@router.put("/items/{item_id}/progress", response_model=FeedItemWithChannel)
async def update_watch_progress(
    item_id: int,
    progress_seconds: int,
    db: DbSession,
) -> FeedItemWithChannel:
    """Update watch progress for a feed item."""
    result = await db.execute(
        select(FeedItem)
        .options(selectinload(FeedItem.channel))
        .where(FeedItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed item with id {item_id} not found",
        )

    item.watch_progress_seconds = progress_seconds
    await db.commit()
    await db.refresh(item)

    return _feed_item_to_response(item)


async def _run_sync_in_background(platform: Optional[str] = None):
    """Background task to sync all channels."""
    from loguru import logger
    from app.services.feed_sync_service import get_feed_sync_service
    from app.database import get_session_factory

    logger.info(f"Background sync started (platform={platform})")

    async with get_session_factory()() as db:
        try:
            service = get_feed_sync_service()
            results = await service.sync_all_channels(db, platform=platform)
            logger.info(f"Background sync complete: {len(results)} channels synced")
        except Exception as e:
            logger.exception(f"Background sync failed: {e}")


@router.post("/sync")
async def sync_all_feeds(
    background_tasks: BackgroundTasks,
    platform: Optional[str] = Query(None, description="Sync only this platform"),
) -> dict:
    """
    Manually trigger a sync of all channels.

    Starts a background task to fetch new videos from all active channels.
    Returns immediately - sync continues in the background.
    """
    background_tasks.add_task(_run_sync_in_background, platform)

    return {"status": "started", "message": "Sync started in background"}


@router.get("/stats", response_model=dict)
async def get_feed_stats(db: DbSession) -> dict:
    """Get feed statistics."""
    # Total videos
    total_result = await db.execute(select(func.count(FeedItem.id)))
    total_videos = total_result.scalar() or 0

    # Unwatched videos
    unwatched_result = await db.execute(
        select(func.count(FeedItem.id)).where(FeedItem.is_watched == False)
    )
    unwatched_videos = unwatched_result.scalar() or 0

    # Total channels
    channel_result = await db.execute(
        select(func.count(Channel.id)).where(Channel.is_active == True)
    )
    total_channels = channel_result.scalar() or 0

    # Videos by platform
    platform_result = await db.execute(
        select(FeedItem.platform, func.count(FeedItem.id))
        .group_by(FeedItem.platform)
    )
    by_platform = dict(platform_result.all())

    return {
        "total_videos": total_videos,
        "unwatched_videos": unwatched_videos,
        "watched_videos": total_videos - unwatched_videos,
        "total_channels": total_channels,
        "by_platform": by_platform,
    }
