"""Discovery API endpoints for federated video search."""

from typing import Union, List

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platforms import (
    PlatformRegistry,
    VideoResult,
    ChannelResult,
    PlaylistResult,
    detect_platform_from_url,
)
from app.schemas.discover import (
    SearchRequest,
    VideoSearchResponse,
    ChannelSearchResponse,
    PlaylistSearchResponse,
    VideoResultSchema,
    ChannelResultSchema,
    PlaylistResultSchema,
    PlatformInfoSchema,
    PlatformListResponse,
    SearchTimingSchema,
    QuickSaveRequest,
    QuickSaveResponse,
)
from app.services.federated_search_service import get_federated_search_service
from app.api.deps import DbSession, CurrentUserOrDefault
from app.models import SavedVideo, FeedItem, UserWatchState

router = APIRouter()


def _video_to_schema(video: VideoResult) -> VideoResultSchema:
    """Convert VideoResult to schema."""
    return VideoResultSchema(
        platform=video.platform,
        video_id=video.video_id,
        video_url=video.video_url,
        title=video.title,
        description=video.description,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=video.duration_seconds,
        view_count=video.view_count,
        upload_date=video.upload_date,
        channel_name=video.channel_name,
        channel_id=video.channel_id,
        channel_url=video.channel_url,
        channel_avatar_url=video.channel_avatar_url,
        like_count=video.like_count,
        tags=video.tags,
    )


def _channel_to_schema(channel: ChannelResult) -> ChannelResultSchema:
    """Convert ChannelResult to schema."""
    return ChannelResultSchema(
        platform=channel.platform,
        channel_id=channel.channel_id,
        channel_url=channel.channel_url,
        name=channel.name,
        description=channel.description,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        subscriber_count=channel.subscriber_count,
        video_count=channel.video_count,
    )


def _playlist_to_schema(playlist: PlaylistResult) -> PlaylistResultSchema:
    """Convert PlaylistResult to schema."""
    return PlaylistResultSchema(
        platform=playlist.platform,
        playlist_id=playlist.playlist_id,
        playlist_url=playlist.playlist_url,
        name=playlist.name,
        description=playlist.description,
        thumbnail_url=playlist.thumbnail_url,
        video_count=playlist.video_count,
        channel_name=playlist.channel_name,
        channel_url=playlist.channel_url,
    )


@router.get("/platforms", response_model=PlatformListResponse)
async def list_platforms() -> PlatformListResponse:
    """
    List all available video platforms.

    Returns platform IDs, names, icons, and supported features.
    """
    platforms = PlatformRegistry.get_platform_info()

    return PlatformListResponse(
        platforms=[PlatformInfoSchema(**p) for p in platforms],
        total=len(platforms),
    )


@router.post("/search")
async def search(
    request: SearchRequest,
) -> Union[VideoSearchResponse, ChannelSearchResponse, PlaylistSearchResponse]:
    """
    Federated search across multiple video platforms.

    Search for videos, channels, or playlists across YouTube, Rumble, Odysee,
    BitChute, and Dailymotion simultaneously.

    Results are merged and interleaved from all platforms, with timing
    information for each platform's response.
    """
    service = get_federated_search_service()

    try:
        if request.type == "videos":
            result = await service.search_videos(
                query=request.query,
                platforms=request.platforms,
                max_per_platform=request.max_per_platform,
            )

            # Convert results to schemas
            results_schema = [_video_to_schema(v) for v in result.results]
            by_platform_schema = {
                platform: [_video_to_schema(v) for v in videos]
                for platform, videos in result.by_platform.items()
            }

            return VideoSearchResponse(
                query=result.query,
                search_type=result.search_type,
                total_results=result.total_results,
                results=results_schema,
                by_platform=by_platform_schema,
                timings=[
                    SearchTimingSchema(
                        platform=t.platform,
                        duration_ms=t.duration_ms,
                        success=t.success,
                        error=t.error,
                    )
                    for t in result.timings
                ],
                total_duration_ms=result.total_duration_ms,
                platforms_searched=result.platforms_searched,
                platforms_failed=result.platforms_failed,
            )

        elif request.type == "channels":
            result = await service.search_channels(
                query=request.query,
                platforms=request.platforms,
                max_per_platform=request.max_per_platform,
            )

            results_schema = [_channel_to_schema(c) for c in result.results]
            by_platform_schema = {
                platform: [_channel_to_schema(c) for c in channels]
                for platform, channels in result.by_platform.items()
            }

            return ChannelSearchResponse(
                query=result.query,
                search_type=result.search_type,
                total_results=result.total_results,
                results=results_schema,
                by_platform=by_platform_schema,
                timings=[
                    SearchTimingSchema(
                        platform=t.platform,
                        duration_ms=t.duration_ms,
                        success=t.success,
                        error=t.error,
                    )
                    for t in result.timings
                ],
                total_duration_ms=result.total_duration_ms,
                platforms_searched=result.platforms_searched,
                platforms_failed=result.platforms_failed,
            )

        else:  # playlists
            result = await service.search_playlists(
                query=request.query,
                platforms=request.platforms,
                max_per_platform=request.max_per_platform,
            )

            results_schema = [_playlist_to_schema(p) for p in result.results]
            by_platform_schema = {
                platform: [_playlist_to_schema(p) for p in playlists]
                for platform, playlists in result.by_platform.items()
            }

            return PlaylistSearchResponse(
                query=result.query,
                search_type=result.search_type,
                total_results=result.total_results,
                results=results_schema,
                by_platform=by_platform_schema,
                timings=[
                    SearchTimingSchema(
                        platform=t.platform,
                        duration_ms=t.duration_ms,
                        success=t.success,
                        error=t.error,
                    )
                    for t in result.timings
                ],
                total_duration_ms=result.total_duration_ms,
                platforms_searched=result.platforms_searched,
                platforms_failed=result.platforms_failed,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("/quick-save", response_model=QuickSaveResponse)
async def quick_save(request: QuickSaveRequest) -> QuickSaveResponse:
    """
    Quick-save a video, channel, or playlist by URL.

    Automatically detects the platform and content type from the URL,
    fetches metadata, and returns the result for saving.
    """
    url = request.url.strip()

    # Detect platform
    adapter = detect_platform_from_url(url)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not detect platform from URL. Supported: YouTube, Rumble, Odysee, BitChute, Dailymotion",
        )

    # Determine content type from URL patterns
    url_lower = url.lower()

    try:
        # Check for playlist URLs
        if "playlist" in url_lower or "list=" in url_lower:
            if adapter.supports_playlists:
                # This is a playlist URL, but we don't have playlist saving yet
                # For now, get the video info instead if it's also a video
                pass

        # Check for channel URLs
        if any(
            pattern in url_lower
            for pattern in [
                "/channel/",
                "/c/",
                "/user/",
                "/@",
                "/u/",
            ]
        ):
            # This looks like a channel URL
            info = await adapter.get_channel_info(url)
            if info:
                return QuickSaveResponse(
                    type="channel",
                    platform=adapter.platform_id,
                    saved=_channel_to_schema(info),
                    message=f"Found channel: {info.name}",
                )

        # Default: try as video URL
        info = await adapter.get_video_info(url)
        if info:
            return QuickSaveResponse(
                type="video",
                platform=adapter.platform_id,
                saved=_video_to_schema(info),
                message=f"Found video: {info.title}",
            )

        # Try as channel if video failed
        info = await adapter.get_channel_info(url)
        if info:
            return QuickSaveResponse(
                type="channel",
                platform=adapter.platform_id,
                saved=_channel_to_schema(info),
                message=f"Found channel: {info.name}",
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find video or channel at this URL",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch content: {str(e)}",
        )


# Schemas for watch state check
class VideoIdentifier(BaseModel):
    """Identifies a video by platform and video_id."""
    platform: str
    video_id: str


class WatchStateItem(BaseModel):
    """Watch state for a single video."""
    platform: str
    video_id: str
    is_watched: bool
    is_partially_watched: bool
    watch_progress_seconds: int | None
    duration_seconds: int | None


class WatchStateCheckRequest(BaseModel):
    """Request to check watch states for multiple videos."""
    videos: List[VideoIdentifier]


class WatchStateCheckResponse(BaseModel):
    """Response with watch states for requested videos."""
    states: List[WatchStateItem]


@router.post("/watch-states", response_model=WatchStateCheckResponse)
async def check_watch_states(
    request: WatchStateCheckRequest,
    db: DbSession,
    user: CurrentUserOrDefault,
) -> WatchStateCheckResponse:
    """
    Check watch states for multiple videos.

    Checks both SavedVideo and FeedItem tables to determine watch state.
    Returns is_watched (fully watched) and is_partially_watched for each video.
    """
    states = []

    for video in request.videos:
        is_watched = False
        is_partially_watched = False
        watch_progress_seconds = None
        duration_seconds = None

        # Check SavedVideo first
        saved_result = await db.execute(
            select(SavedVideo).where(
                and_(
                    SavedVideo.user_id == user.id,
                    SavedVideo.platform == video.platform,
                    SavedVideo.video_id == video.video_id,
                )
            )
        )
        saved_video = saved_result.scalar_one_or_none()

        if saved_video:
            is_watched = saved_video.is_watched
            watch_progress_seconds = saved_video.watch_progress_seconds
            duration_seconds = saved_video.duration_seconds
            # Partially watched if there's progress but not marked as watched
            if not is_watched and watch_progress_seconds and watch_progress_seconds > 0:
                is_partially_watched = True

        # If not found in saved, check FeedItem with UserWatchState
        if not saved_video:
            # Find feed item by platform and video_id
            feed_result = await db.execute(
                select(FeedItem).where(
                    and_(
                        FeedItem.platform == video.platform,
                        FeedItem.video_id == video.video_id,
                    )
                )
            )
            feed_item = feed_result.scalar_one_or_none()

            if feed_item:
                duration_seconds = feed_item.duration_seconds
                # Check user's watch state for this feed item
                watch_state_result = await db.execute(
                    select(UserWatchState).where(
                        and_(
                            UserWatchState.user_id == user.id,
                            UserWatchState.feed_item_id == feed_item.id,
                        )
                    )
                )
                watch_state = watch_state_result.scalar_one_or_none()

                if watch_state:
                    is_watched = watch_state.is_watched
                    watch_progress_seconds = watch_state.watch_progress_seconds
                    if not is_watched and watch_progress_seconds and watch_progress_seconds > 0:
                        is_partially_watched = True

        states.append(WatchStateItem(
            platform=video.platform,
            video_id=video.video_id,
            is_watched=is_watched,
            is_partially_watched=is_partially_watched,
            watch_progress_seconds=watch_progress_seconds,
            duration_seconds=duration_seconds,
        ))

    return WatchStateCheckResponse(states=states)
