"""Feed API endpoints."""

from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUserOrDefault
from app.models import Channel, FeedItem, UserWatchState
from app.schemas.feed import (
    FeedItemResponse,
    FeedItemWithChannel,
    FeedResponse,
    ChannelGroupedFeed,
    ChannelGroupedFeedResponse,
    WatchStateUpdate,
)

router = APIRouter()


def _feed_item_to_response(
    item: FeedItem,
    channel: Optional[Channel] = None,
    watch_state: Optional[UserWatchState] = None,
) -> FeedItemWithChannel:
    """Convert FeedItem model to response schema with per-user watch state."""
    # Use user-specific watch state if provided, otherwise fall back to global (for backward compat)
    is_watched = watch_state.is_watched if watch_state else item.is_watched
    watched_at = watch_state.watched_at if watch_state else item.watched_at
    watch_progress = watch_state.watch_progress_seconds if watch_state else item.watch_progress_seconds

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
        categories=item.categories,
        audio_url=item.audio_url,
        audio_file_size=item.audio_file_size,
        audio_mime_type=item.audio_mime_type,
        video_stream_url=item.video_stream_url,
        content_type=item.content_type,
        is_watched=is_watched,
        watched_at=watched_at,
        watch_progress_seconds=watch_progress,
        discovered_at=item.discovered_at,
        duration_formatted=item.duration_formatted,
        is_recent=item.is_recent,
        channel_name=channel.name if channel else item.channel.name if item.channel else "",
        channel_avatar_url=channel.avatar_url if channel else (item.channel.avatar_url if item.channel else None),
    )


# Category mappings for mood-based feed modes
MOOD_CATEGORIES = {
    "focus_learning": ["Education", "Science & Technology", "Howto & Style"],
    "stay_positive": ["Comedy", "Entertainment"],
    "music_mode": ["Music"],
    "news_politics": ["News & Politics"],
    "gaming": ["Gaming"],
}


def _apply_mode_preset(mode: str) -> dict:
    """Apply preset settings for a feed mode."""
    presets = {
        # Standard modes - just sorting
        "newest": {"sort_by": "newest"},
        "oldest": {"sort_by": "oldest"},
        "most_viewed": {"sort_by": "views"},
        "shortest": {"sort_by": "duration_asc"},
        "longest": {"sort_by": "duration_desc"},
        "random": {"sort_by": "random"},
        # Smart modes
        "catch_up": {"filter": "unwatched", "sort_by": "oldest"},
        "quick_watch": {"filter": "unwatched", "duration_max": 600, "sort_by": "newest"},
        "deep_dive": {"filter": "unwatched", "duration_min": 1800, "sort_by": "newest"},
        # Mood-based modes
        "focus_learning": {"filter": "unwatched", "categories": MOOD_CATEGORIES["focus_learning"], "sort_by": "newest"},
        "stay_positive": {"filter": "unwatched", "categories": MOOD_CATEGORIES["stay_positive"], "sort_by": "newest"},
        "music_mode": {"categories": MOOD_CATEGORIES["music_mode"], "sort_by": "newest"},
        "news_politics": {"filter": "unwatched", "categories": MOOD_CATEGORIES["news_politics"], "sort_by": "newest"},
        "gaming": {"filter": "unwatched", "categories": MOOD_CATEGORIES["gaming"], "sort_by": "newest"},
    }
    return presets.get(mode, {})


@router.get("", response_model=FeedResponse)
async def get_feed(
    db: DbSession,
    user: CurrentUserOrDefault,
    filter: Literal["all", "unwatched", "watched"] = Query("all", description="Filter by watch status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    channel_ids: Optional[str] = Query(None, description="Comma-separated channel IDs"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    since: Optional[datetime] = Query(None, description="Only videos uploaded after this date"),
    # New feed mode parameters
    mode: Optional[str] = Query(None, description="Feed mode preset (catch_up, quick_watch, etc.)"),
    sort_by: Optional[str] = Query(None, description="Sort order: newest, oldest, views, duration_asc, duration_desc, random"),
    category: Optional[str] = Query(None, description="Filter by YouTube category"),
    duration_min: Optional[int] = Query(None, description="Min duration in seconds"),
    duration_max: Optional[int] = Query(None, description="Max duration in seconds"),
) -> FeedResponse:
    """
    Get the video feed with flexible sorting and filtering.

    Supports feed modes (catch_up, quick_watch, deep_dive, mood-based) and custom sorting.
    Watch status is per-user.
    """
    from sqlalchemy.orm import aliased

    # Apply mode presets (overrides some parameters)
    category_filter = None
    if mode:
        mode_settings = _apply_mode_preset(mode)
        if "filter" in mode_settings:
            filter = mode_settings["filter"]
        if "sort_by" in mode_settings:
            sort_by = mode_settings["sort_by"]
        if "duration_min" in mode_settings:
            duration_min = mode_settings["duration_min"]
        if "duration_max" in mode_settings:
            duration_max = mode_settings["duration_max"]
        if "categories" in mode_settings:
            category_filter = mode_settings["categories"]
    elif category:
        category_filter = [category]

    # Create alias for UserWatchState to left-join per-user watch state
    UserWatchStateAlias = aliased(UserWatchState)

    # Build base query - only include items from channels the user is subscribed to
    # Left join with user's watch state
    query = (
        select(FeedItem, UserWatchStateAlias)
        .join(Channel)
        .outerjoin(
            UserWatchStateAlias,
            (UserWatchStateAlias.feed_item_id == FeedItem.id) &
            (UserWatchStateAlias.user_id == user.id)
        )
        .where(Channel.is_active == True)
        .where(Channel.user_id == user.id)  # Only show videos from user's subscribed channels
        .options(selectinload(FeedItem.channel))
    )

    # Apply watch status filter (using user's watch state)
    if filter == "unwatched":
        # Unwatched = no watch state OR watch state with is_watched=False
        query = query.where(
            or_(
                UserWatchStateAlias.id.is_(None),
                UserWatchStateAlias.is_watched == False
            )
        )
    elif filter == "watched":
        # Watched = has watch state with is_watched=True
        query = query.where(UserWatchStateAlias.is_watched == True)

    # Apply platform filter
    if platform:
        query = query.where(FeedItem.platform == platform)

    # Apply channel filter
    if channel_ids:
        ids = [int(id.strip()) for id in channel_ids.split(",") if id.strip().isdigit()]
        if ids:
            query = query.where(FeedItem.channel_id.in_(ids))

    # Apply date filter
    if since:
        query = query.where(FeedItem.upload_date >= since)

    # Apply duration filters
    if duration_min is not None:
        query = query.where(FeedItem.duration_seconds >= duration_min)
    if duration_max is not None:
        query = query.where(FeedItem.duration_seconds <= duration_max)

    # Apply category filter (JSON array contains check for SQLite)
    if category_filter:
        category_conditions = []
        for cat in category_filter:
            # SQLite JSON contains - check if category string exists in JSON array
            category_conditions.append(
                FeedItem.categories.contains(f'"{cat}"')
            )
        if category_conditions:
            query = query.where(or_(*category_conditions))

    # Apply sorting
    if sort_by == "oldest":
        query = query.order_by(FeedItem.upload_date.asc())
    elif sort_by == "views":
        query = query.order_by(FeedItem.view_count.desc().nullslast())
    elif sort_by == "duration_asc":
        query = query.order_by(FeedItem.duration_seconds.asc().nullslast())
    elif sort_by == "duration_desc":
        query = query.order_by(FeedItem.duration_seconds.desc().nullslast())
    elif sort_by == "random":
        query = query.order_by(func.random())
    else:  # newest (default)
        query = query.order_by(desc(FeedItem.upload_date))

    # Get total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = list(result.all())

    # Convert to response with per-user watch state
    items_with_state = []
    for row in rows:
        item = row[0]  # FeedItem
        watch_state = row[1]  # UserWatchState or None
        items_with_state.append(_feed_item_to_response(item, watch_state=watch_state))

    return FeedResponse(
        items=items_with_state,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(rows)) < total,
    )


@router.get("/by-channel", response_model=ChannelGroupedFeedResponse)
async def get_feed_by_channel(
    db: DbSession,
    user: CurrentUserOrDefault,
    filter: Literal["all", "unwatched", "watched"] = Query("all"),
    platform: Optional[str] = Query(None),
    max_per_channel: int = Query(5, ge=1, le=20, description="Max videos per channel"),
) -> ChannelGroupedFeedResponse:
    """
    Get the video feed grouped by channel.

    Shows recent videos from each subscribed channel with per-user watch state.
    """
    from sqlalchemy.orm import aliased

    UserWatchStateAlias = aliased(UserWatchState)

    # Get all active channels the user is subscribed to
    channel_query = (
        select(Channel)
        .where(Channel.is_active == True)
        .where(Channel.user_id == user.id)  # Only show user's subscribed channels
    )
    if platform:
        channel_query = channel_query.where(Channel.platform == platform)
    channel_query = channel_query.order_by(Channel.name)

    channel_result = await db.execute(channel_query)
    channels = list(channel_result.scalars().all())

    grouped_feeds = []
    total_items = 0

    for channel in channels:
        # Get recent videos for this channel with user's watch state
        item_query = (
            select(FeedItem, UserWatchStateAlias)
            .outerjoin(
                UserWatchStateAlias,
                (UserWatchStateAlias.feed_item_id == FeedItem.id) &
                (UserWatchStateAlias.user_id == user.id)
            )
            .where(FeedItem.channel_id == channel.id)
            .order_by(desc(FeedItem.upload_date))
        )

        if filter == "unwatched":
            item_query = item_query.where(
                or_(
                    UserWatchStateAlias.id.is_(None),
                    UserWatchStateAlias.is_watched == False
                )
            )
        elif filter == "watched":
            item_query = item_query.where(UserWatchStateAlias.is_watched == True)

        item_query = item_query.limit(max_per_channel)

        item_result = await db.execute(item_query)
        rows = list(item_result.all())

        if not rows:
            continue

        # Count totals for this channel (per user)
        count_query = select(func.count()).where(FeedItem.channel_id == channel.id)

        # Unwatched = items without watch state OR with is_watched=False for this user
        unwatched_subquery = (
            select(FeedItem.id)
            .outerjoin(
                UserWatchState,
                (UserWatchState.feed_item_id == FeedItem.id) &
                (UserWatchState.user_id == user.id)
            )
            .where(FeedItem.channel_id == channel.id)
            .where(
                or_(
                    UserWatchState.id.is_(None),
                    UserWatchState.is_watched == False
                )
            )
        )
        unwatched_query = select(func.count()).select_from(unwatched_subquery.subquery())

        total_result = await db.execute(count_query)
        unwatched_result = await db.execute(unwatched_query)

        channel_total = total_result.scalar() or 0
        unwatched_count = unwatched_result.scalar() or 0

        # Build response items with per-user watch state
        response_items = []
        for row in rows:
            item = row[0]
            watch_state = row[1]
            is_watched = watch_state.is_watched if watch_state else False
            watched_at = watch_state.watched_at if watch_state else None
            watch_progress = watch_state.watch_progress_seconds if watch_state else None

            response_items.append(FeedItemResponse(
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
                categories=item.categories,
                is_watched=is_watched,
                watched_at=watched_at,
                watch_progress_seconds=watch_progress,
                discovered_at=item.discovered_at,
                duration_formatted=item.duration_formatted,
                is_recent=item.is_recent,
            ))

        grouped_feeds.append(ChannelGroupedFeed(
            channel_id=channel.id,
            channel_name=channel.name,
            channel_avatar_url=channel.avatar_url,
            platform=channel.platform,
            items=response_items,
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
async def get_feed_item(item_id: int, db: DbSession, user: CurrentUserOrDefault) -> FeedItemWithChannel:
    """Get a specific feed item with per-user watch state."""
    from sqlalchemy.orm import aliased

    UserWatchStateAlias = aliased(UserWatchState)

    result = await db.execute(
        select(FeedItem, UserWatchStateAlias)
        .outerjoin(
            UserWatchStateAlias,
            (UserWatchStateAlias.feed_item_id == FeedItem.id) &
            (UserWatchStateAlias.user_id == user.id)
        )
        .options(selectinload(FeedItem.channel))
        .where(FeedItem.id == item_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed item with id {item_id} not found",
        )

    item = row[0]
    watch_state = row[1]

    return _feed_item_to_response(item, watch_state=watch_state)


@router.put("/items/{item_id}/watched", response_model=FeedItemWithChannel)
async def mark_watched(item_id: int, db: DbSession, user: CurrentUserOrDefault) -> FeedItemWithChannel:
    """Mark a feed item as watched for the current user."""
    # First verify the feed item exists
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

    # Get or create user's watch state
    watch_state_result = await db.execute(
        select(UserWatchState).where(
            UserWatchState.user_id == user.id,
            UserWatchState.feed_item_id == item_id,
        )
    )
    watch_state = watch_state_result.scalar_one_or_none()

    if not watch_state:
        watch_state = UserWatchState(user_id=user.id, feed_item_id=item_id)
        db.add(watch_state)

    watch_state.mark_watched()
    await db.commit()
    await db.refresh(watch_state)
    await db.refresh(item)

    return _feed_item_to_response(item, watch_state=watch_state)


@router.put("/items/{item_id}/unwatched", response_model=FeedItemWithChannel)
async def mark_unwatched(item_id: int, db: DbSession, user: CurrentUserOrDefault) -> FeedItemWithChannel:
    """Mark a feed item as unwatched for the current user."""
    # First verify the feed item exists
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

    # Get or create user's watch state
    watch_state_result = await db.execute(
        select(UserWatchState).where(
            UserWatchState.user_id == user.id,
            UserWatchState.feed_item_id == item_id,
        )
    )
    watch_state = watch_state_result.scalar_one_or_none()

    if not watch_state:
        watch_state = UserWatchState(user_id=user.id, feed_item_id=item_id)
        db.add(watch_state)

    watch_state.mark_unwatched()
    await db.commit()
    await db.refresh(watch_state)
    await db.refresh(item)

    return _feed_item_to_response(item, watch_state=watch_state)


@router.put("/items/{item_id}/progress", response_model=FeedItemWithChannel)
async def update_watch_progress(
    item_id: int,
    progress_seconds: int,
    db: DbSession,
    user: CurrentUserOrDefault,
) -> FeedItemWithChannel:
    """Update watch progress for a feed item for the current user."""
    # First verify the feed item exists
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

    # Get or create user's watch state
    watch_state_result = await db.execute(
        select(UserWatchState).where(
            UserWatchState.user_id == user.id,
            UserWatchState.feed_item_id == item_id,
        )
    )
    watch_state = watch_state_result.scalar_one_or_none()

    if not watch_state:
        watch_state = UserWatchState(user_id=user.id, feed_item_id=item_id)
        db.add(watch_state)

    watch_state.update_progress(progress_seconds)
    await db.commit()
    await db.refresh(watch_state)
    await db.refresh(item)

    return _feed_item_to_response(item, watch_state=watch_state)


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


@router.post("/fix-metadata")
async def fix_video_metadata(
    background_tasks: BackgroundTasks,
    limit: int = Query(100, ge=1, le=500, description="Max videos to fix"),
) -> dict:
    """
    One-time fix for videos with incorrect upload dates.

    Finds videos where upload_date is close to discovered_at (suggesting the
    fallback was used during sync) and fetches accurate metadata.
    """
    background_tasks.add_task(_run_metadata_fix_in_background, limit)
    return {"status": "started", "message": f"Metadata fix started for up to {limit} videos"}


async def _run_metadata_fix_in_background(limit: int):
    """Background task to fix metadata for existing videos."""
    from datetime import timedelta
    from loguru import logger
    from app.services.feed_sync_service import get_feed_sync_service
    from app.database import get_session_factory

    logger.info(f"Starting metadata fix (limit={limit})")

    async with get_session_factory()() as db:
        try:
            # Find YouTube videos where upload_date is suspiciously close to discovered_at
            # These are likely videos where the fallback datetime.utcnow() was used
            result = await db.execute(
                select(FeedItem)
                .where(FeedItem.platform == "youtube")
                .order_by(FeedItem.discovered_at.desc())
                .limit(limit * 2)  # Get more, then filter
            )
            all_items = list(result.scalars().all())

            # Filter items where upload_date is within 48 hours of discovered_at
            # This is done in Python to avoid database-specific SQL functions
            items = []
            for item in all_items:
                if item.upload_date and item.discovered_at:
                    diff = abs((item.upload_date - item.discovered_at).total_seconds())
                    if diff < 172800:  # 48 hours in seconds
                        items.append(item)
                        if len(items) >= limit:
                            break

            if not items:
                logger.info("No videos need metadata fixing")
                return

            logger.info(f"Found {len(items)} videos that may need metadata fixing")

            # Use the sync service's metadata fetching
            service = get_feed_sync_service()
            video_ids = [item.video_id for item in items]

            await service._fetch_and_update_metadata(db, video_ids)

            logger.info(f"Metadata fix complete for {len(video_ids)} videos")

        except Exception as e:
            logger.exception(f"Metadata fix failed: {e}")


@router.get("/stats", response_model=dict)
async def get_feed_stats(db: DbSession, user: CurrentUserOrDefault) -> dict:
    """Get feed statistics for the current user's subscribed channels."""
    # Total videos from user's subscribed channels
    total_result = await db.execute(
        select(func.count(FeedItem.id))
        .join(Channel)
        .where(Channel.user_id == user.id)
        .where(Channel.is_active == True)
    )
    total_videos = total_result.scalar() or 0

    # Watched videos count for this user (via UserWatchState) from their subscribed channels
    watched_result = await db.execute(
        select(func.count(UserWatchState.id))
        .join(FeedItem, UserWatchState.feed_item_id == FeedItem.id)
        .join(Channel, FeedItem.channel_id == Channel.id)
        .where(
            UserWatchState.user_id == user.id,
            UserWatchState.is_watched == True,
            Channel.user_id == user.id
        )
    )
    watched_videos = watched_result.scalar() or 0
    unwatched_videos = total_videos - watched_videos

    # Total channels for this user
    channel_result = await db.execute(
        select(func.count(Channel.id))
        .where(Channel.is_active == True)
        .where(Channel.user_id == user.id)
    )
    total_channels = channel_result.scalar() or 0

    # Videos by platform from user's subscribed channels
    platform_result = await db.execute(
        select(FeedItem.platform, func.count(FeedItem.id))
        .join(Channel)
        .where(Channel.user_id == user.id)
        .where(Channel.is_active == True)
        .group_by(FeedItem.platform)
    )
    by_platform = dict(platform_result.all())

    return {
        "total_videos": total_videos,
        "unwatched_videos": unwatched_videos,
        "watched_videos": watched_videos,
        "total_channels": total_channels,
        "by_platform": by_platform,
    }


@router.post("/backfill-redbar")
async def backfill_redbar_urls(
    background_tasks: BackgroundTasks,
    db: DbSession,
    limit: int = Query(50, ge=1, le=500, description="Episodes per batch"),
    skip_existing: bool = Query(True, description="Skip episodes that already have URLs"),
) -> dict:
    """
    Backfill missing video/audio URLs for Red Bar episodes.

    Fetches each individual episode page with authentication to extract:
    - video_stream_url (HLS manifest for video playback)
    - audio_url (MP3 fallback)
    - content_type ("video" or "audio")

    Rate limited to 1 request/second to avoid overwhelming the server.
    """
    from app.services.backfill_service import backfill_service

    # Run in background for large batches
    if limit > 20:
        background_tasks.add_task(
            _run_backfill_in_background,
            limit=limit,
            skip_existing=skip_existing,
        )
        return {
            "status": "started",
            "message": f"Backfill started in background for up to {limit} episodes",
            "note": "Use GET /api/feed/backfill-status to monitor progress",
        }

    # For small batches, run synchronously and return results
    result = await backfill_service.backfill_redbar_video_urls(
        db=db,
        limit=limit,
        skip_existing=skip_existing,
    )
    return result


async def _run_backfill_in_background(limit: int, skip_existing: bool):
    """Background task for backfill."""
    from loguru import logger
    from app.database import get_session_factory
    from app.services.backfill_service import backfill_service

    logger.info(f"Background backfill started (limit={limit})")

    async with get_session_factory()() as db:
        try:
            result = await backfill_service.backfill_redbar_video_urls(
                db=db,
                limit=limit,
                skip_existing=skip_existing,
            )
            logger.info(f"Background backfill complete: {result}")
        except Exception as e:
            logger.exception(f"Background backfill failed: {e}")


@router.get("/backfill-status")
async def get_backfill_status(db: DbSession) -> dict:
    """Get current backfill status showing missing data counts."""
    from app.services.backfill_service import backfill_service
    return await backfill_service.get_backfill_status(db)


@router.get("/history", response_model=FeedResponse)
async def get_watch_history(
    db: DbSession,
    user: CurrentUserOrDefault,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    include_completed: bool = Query(default=True, description="Include fully watched videos"),
) -> FeedResponse:
    """
    Get watch history for the current user - videos that have been played or have progress.

    Returns videos sorted by most recently watched/played first.
    """
    # Build query for videos with any watch activity for this user
    query = (
        select(FeedItem, UserWatchState)
        .join(
            UserWatchState,
            (UserWatchState.feed_item_id == FeedItem.id) &
            (UserWatchState.user_id == user.id)
        )
        .options(selectinload(FeedItem.channel))
        .where(
            or_(
                UserWatchState.watch_progress_seconds > 0,
                UserWatchState.is_watched == True,
                UserWatchState.watched_at.isnot(None),
            )
        )
    )

    if not include_completed:
        # Only show in-progress videos (not fully watched)
        query = query.where(UserWatchState.is_watched == False)

    # Sort by watched_at if available, otherwise by updated_at
    query = query.order_by(
        desc(func.coalesce(UserWatchState.watched_at, UserWatchState.updated_at))
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = list(result.all())

    has_more = (page * per_page) < total

    # Convert to response with per-user watch state
    items_with_state = []
    for row in rows:
        item = row[0]
        watch_state = row[1]
        items_with_state.append(_feed_item_to_response(item, watch_state=watch_state))

    return FeedResponse(
        items=items_with_state,
        total=total,
        page=page,
        per_page=per_page,
        has_more=has_more,
    )
