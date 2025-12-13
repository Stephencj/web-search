"""Discovery API endpoints for federated video search."""

from typing import Union

from fastapi import APIRouter, HTTPException, status

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
