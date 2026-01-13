"""Stream API endpoints for authenticated video playback."""

import asyncio
import time
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.services.oauth_service import get_oauth_service


router = APIRouter()

# In-memory cache for extracted streams (shared across requests)
_stream_cache: dict[str, "StreamInfo"] = {}
_cache_timestamps: dict[str, float] = {}
_active_extractions: dict[str, float] = {}
CACHE_TTL_SECONDS = 5 * 60 * 60  # 5 hours
MAX_CACHE_ENTRIES = 100

# Platforms that support stream extraction via yt-dlp
SUPPORTED_STREAM_PLATFORMS = {"youtube", "rumble", "odysee", "bitchute", "dailymotion", "redbar"}


class StreamInfo(BaseModel):
    """Response schema for stream info."""
    video_id: str
    platform: str
    title: Optional[str] = None
    stream_url: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    is_authenticated: bool = False
    is_premium: bool = False
    quality: Optional[str] = None
    format: Optional[str] = None
    error: Optional[str] = None


class StreamFormats(BaseModel):
    """Available stream formats."""
    video_id: str
    platform: str
    formats: list[dict]
    is_authenticated: bool = False


class ExtractionStatus(BaseModel):
    """Status of a stream extraction."""
    video_id: str
    platform: str
    status: Literal["idle", "extracting", "ready", "failed"]
    started_at: Optional[float] = None
    stream_info: Optional[StreamInfo] = None
    error: Optional[str] = None


class ExtractionStarted(BaseModel):
    """Response when extraction is started."""
    video_id: str
    platform: str
    status: Literal["started", "already_cached", "already_extracting"]
    poll_url: str


@router.get("/{platform}/{video_id}", response_model=StreamInfo)
async def get_stream_info(
    platform: str,
    video_id: str,
    db: DbSession,
    quality: str = Query("best", description="Video quality (best, 1080p, 720p, 480p, worst)"),
    audio_only: bool = Query(False, description="Get audio stream only"),
    video_url: Optional[str] = Query(None, description="Original video URL for proper path resolution"),
) -> StreamInfo:
    """
    Get direct stream URL for a video.

    If the user has linked their platform account, uses authenticated
    extraction for premium benefits (no ads, higher quality).

    Args:
        platform: Platform ID (youtube, rumble, redbar)
        video_id: Video ID on the platform
        quality: Desired video quality
        audio_only: If true, return audio stream only
        video_url: Original video URL (used for Red Bar to determine /shows/ vs /archives/ path)

    Returns:
        StreamInfo with direct stream URLs
    """
    # Handle Red Bar
    if platform == "redbar":
        return await _get_redbar_stream(video_id, audio_only, video_url, db)

    # Check if platform is supported
    if platform not in SUPPORTED_STREAM_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Streaming not supported for platform: {platform}",
        )

    # Handle YouTube with OAuth support
    if platform == "youtube":
        oauth_service = get_oauth_service()
        account = await oauth_service.get_account(db, platform)

        # Get access token if account exists
        access_token = None
        is_premium = False
        if account:
            access_token = await oauth_service.get_valid_access_token(db, account)
            is_premium = account.is_premium

        # Build video URL
        yt_video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Extract stream info using yt-dlp
        try:
            stream_info = await _extract_youtube_stream(
                video_url=yt_video_url,
                access_token=access_token,
                quality=quality,
                audio_only=audio_only,
            )

            return StreamInfo(
                video_id=video_id,
                platform=platform,
                title=stream_info.get("title"),
                stream_url=stream_info.get("stream_url"),
                audio_url=stream_info.get("audio_url"),
                thumbnail_url=stream_info.get("thumbnail"),
                duration_seconds=stream_info.get("duration"),
                is_authenticated=access_token is not None,
                is_premium=is_premium,
                quality=stream_info.get("quality"),
                format=stream_info.get("format"),
                error=stream_info.get("error"),
            )

        except Exception as e:
            return StreamInfo(
                video_id=video_id,
                platform=platform,
                is_authenticated=access_token is not None,
                is_premium=is_premium,
                error=str(e),
            )

    # Handle other platforms (Rumble, Odysee, BitChute, Dailymotion) with generic extraction
    try:
        platform_video_url = _build_video_url(platform, video_id, video_url)
        if not platform_video_url:
            return StreamInfo(
                video_id=video_id,
                platform=platform,
                error=f"Could not build video URL for platform: {platform}",
            )

        stream_info = await _extract_generic_stream(
            video_url=platform_video_url,
            platform=platform,
            quality=quality,
            audio_only=audio_only,
        )

        return StreamInfo(
            video_id=video_id,
            platform=platform,
            title=stream_info.get("title"),
            stream_url=stream_info.get("stream_url"),
            audio_url=stream_info.get("audio_url"),
            thumbnail_url=stream_info.get("thumbnail"),
            duration_seconds=stream_info.get("duration"),
            is_authenticated=False,
            is_premium=False,
            quality=stream_info.get("quality"),
            format=stream_info.get("format"),
            error=stream_info.get("error"),
        )

    except Exception as e:
        return StreamInfo(
            video_id=video_id,
            platform=platform,
            error=str(e),
        )


@router.get("/{platform}/{video_id}/formats", response_model=StreamFormats)
async def get_stream_formats(
    platform: str,
    video_id: str,
    db: DbSession,
) -> StreamFormats:
    """
    Get available stream formats for a video.

    Returns list of available qualities and formats.
    """
    if platform not in SUPPORTED_STREAM_PLATFORMS or platform == "redbar":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format listing not supported for platform: {platform}",
        )

    # Build video URL
    video_url = _build_video_url(platform, video_id)
    if not video_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not build video URL for platform: {platform}",
        )

    # For YouTube, try to get OAuth token
    access_token = None
    is_authenticated = False
    if platform == "youtube":
        oauth_service = get_oauth_service()
        account = await oauth_service.get_account(db, platform)
        if account:
            access_token = await oauth_service.get_valid_access_token(db, account)
            is_authenticated = access_token is not None

    try:
        formats = await _list_youtube_formats(video_url, access_token)
        return StreamFormats(
            video_id=video_id,
            platform=platform,
            formats=formats,
            is_authenticated=is_authenticated,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get formats: {e}",
        )


# ============================================================================
# Async Extraction Endpoints (for instant-start architecture)
# ============================================================================


def _get_cache_key(platform: str, video_id: str) -> str:
    """Generate cache key for a video."""
    return f"{platform}:{video_id}"


def _is_cache_valid(key: str) -> bool:
    """Check if cache entry is still valid."""
    if key not in _cache_timestamps:
        return False
    return (time.time() - _cache_timestamps[key]) < CACHE_TTL_SECONDS


def _prune_cache():
    """Remove old entries if cache is too large."""
    if len(_stream_cache) <= MAX_CACHE_ENTRIES:
        return
    # Remove oldest entries
    sorted_keys = sorted(_cache_timestamps.keys(), key=lambda k: _cache_timestamps[k])
    to_remove = sorted_keys[: len(sorted_keys) - MAX_CACHE_ENTRIES + 10]
    for key in to_remove:
        _stream_cache.pop(key, None)
        _cache_timestamps.pop(key, None)


@router.get("/{platform}/{video_id}/status", response_model=ExtractionStatus)
async def get_extraction_status(
    platform: str,
    video_id: str,
) -> ExtractionStatus:
    """
    Check the status of a stream extraction.

    Use this to poll for extraction completion after starting with /extract.
    """
    cache_key = _get_cache_key(platform, video_id)

    # Check if cached
    if cache_key in _stream_cache and _is_cache_valid(cache_key):
        return ExtractionStatus(
            video_id=video_id,
            platform=platform,
            status="ready",
            stream_info=_stream_cache[cache_key],
        )

    # Check if extracting
    if cache_key in _active_extractions:
        return ExtractionStatus(
            video_id=video_id,
            platform=platform,
            status="extracting",
            started_at=_active_extractions[cache_key],
        )

    # Not started
    return ExtractionStatus(
        video_id=video_id,
        platform=platform,
        status="idle",
    )


@router.post("/{platform}/{video_id}/extract", response_model=ExtractionStarted)
async def start_extraction(
    platform: str,
    video_id: str,
    db: DbSession,
    background_tasks: BackgroundTasks,
    quality: str = Query("best", description="Video quality"),
) -> ExtractionStarted:
    """
    Start stream extraction in the background.

    Returns immediately with a poll URL. Use /status to check when done.
    This enables instant-start playback: start with embed, upgrade when ready.
    """
    if platform not in SUPPORTED_STREAM_PLATFORMS or platform == "redbar":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Background extraction not supported for platform: {platform}",
        )

    cache_key = _get_cache_key(platform, video_id)
    poll_url = f"/api/stream/{platform}/{video_id}/status"

    # Already cached?
    if cache_key in _stream_cache and _is_cache_valid(cache_key):
        return ExtractionStarted(
            video_id=video_id,
            platform=platform,
            status="already_cached",
            poll_url=poll_url,
        )

    # Already extracting?
    if cache_key in _active_extractions:
        return ExtractionStarted(
            video_id=video_id,
            platform=platform,
            status="already_extracting",
            poll_url=poll_url,
        )

    # Get OAuth token if available (YouTube only)
    access_token = None
    is_premium = False
    if platform == "youtube":
        oauth_service = get_oauth_service()
        account = await oauth_service.get_account(db, platform)
        if account:
            access_token = await oauth_service.get_valid_access_token(db, account)
            is_premium = account.is_premium

    # Mark as extracting
    _active_extractions[cache_key] = time.time()

    # Build video URL
    video_url = _build_video_url(platform, video_id)

    # Start background extraction
    async def do_extraction():
        try:
            if platform == "youtube":
                stream_info = await _extract_youtube_stream(
                    video_url=video_url,
                    access_token=access_token,
                    quality=quality,
                    audio_only=False,
                )
            else:
                stream_info = await _extract_generic_stream(
                    video_url=video_url,
                    platform=platform,
                    quality=quality,
                    audio_only=False,
                )

            # Cache the result
            result = StreamInfo(
                video_id=video_id,
                platform=platform,
                title=stream_info.get("title"),
                stream_url=stream_info.get("stream_url"),
                audio_url=stream_info.get("audio_url"),
                thumbnail_url=stream_info.get("thumbnail"),
                duration_seconds=stream_info.get("duration"),
                is_authenticated=access_token is not None,
                is_premium=is_premium,
                quality=stream_info.get("quality"),
                format=stream_info.get("format"),
                error=stream_info.get("error"),
            )

            _stream_cache[cache_key] = result
            _cache_timestamps[cache_key] = time.time()
            _prune_cache()

        except Exception as e:
            # Cache error result briefly so we don't retry immediately
            _stream_cache[cache_key] = StreamInfo(
                video_id=video_id,
                platform=platform,
                is_authenticated=access_token is not None,
                is_premium=is_premium,
                error=str(e),
            )
            _cache_timestamps[cache_key] = time.time()

        finally:
            _active_extractions.pop(cache_key, None)

    background_tasks.add_task(do_extraction)

    return ExtractionStarted(
        video_id=video_id,
        platform=platform,
        status="started",
        poll_url=poll_url,
    )


def _build_video_url(platform: str, video_id: str, original_url: Optional[str] = None) -> str:
    """
    Build full video URL for yt-dlp extraction.

    Args:
        platform: Platform identifier
        video_id: Video ID on the platform
        original_url: Original URL if available (preferred)

    Returns:
        Full video URL for extraction
    """
    if original_url:
        return original_url

    url_templates = {
        "youtube": f"https://www.youtube.com/watch?v={video_id}",
        "rumble": f"https://rumble.com/{video_id}",
        "odysee": f"https://odysee.com/{video_id}",
        "bitchute": f"https://www.bitchute.com/video/{video_id}/",
        "dailymotion": f"https://www.dailymotion.com/video/{video_id}",
    }
    return url_templates.get(platform, "")


async def _extract_generic_stream(
    video_url: str,
    platform: str,
    quality: str = "best",
    audio_only: bool = False,
) -> dict:
    """
    Extract stream URL for non-YouTube platforms using yt-dlp.

    Works for platforms like Rumble, Odysee, BitChute, Dailymotion.
    These platforms typically have simpler format structures than YouTube.

    Args:
        video_url: Full video URL
        platform: Platform identifier (for logging)
        quality: Desired quality (best, 1080p, 720p, 480p, worst)
        audio_only: Get audio stream only

    Returns:
        Dict with stream info
    """
    import yt_dlp
    from loguru import logger

    logger.debug(f"Extracting stream for {platform}: {video_url}")

    # Format selection - simpler than YouTube since most platforms have combined streams
    if audio_only:
        format_str = "bestaudio/best"
    elif quality == "1080p":
        format_str = "best[height<=1080]/best"
    elif quality == "720p":
        format_str = "best[height<=720]/best"
    elif quality == "480p":
        format_str = "best[height<=480]/best"
    elif quality == "worst":
        format_str = "worst"
    else:
        format_str = "best"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": format_str,
        "skip_download": True,
    }

    def extract():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return {"error": "Failed to extract video info"}

                result = {
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                    "duration": info.get("duration"),
                }

                # Get stream URL - most platforms use combined format
                if "url" in info:
                    result["stream_url"] = info["url"]
                    height = info.get("height")
                    result["quality"] = f"{height}p" if height else info.get("format_note") or "best"
                    result["format"] = info.get("ext")
                    result["height"] = height
                elif "formats" in info and info["formats"]:
                    # Find best available format
                    sorted_formats = sorted(
                        [f for f in info["formats"] if f.get("url")],
                        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
                        reverse=True
                    )
                    if sorted_formats:
                        fmt = sorted_formats[0]
                        result["stream_url"] = fmt.get("url")
                        height = fmt.get("height")
                        result["quality"] = f"{height}p" if height else fmt.get("format_note") or "best"
                        result["format"] = fmt.get("ext")
                        result["height"] = height
                else:
                    return {"error": "No stream URL found in extraction result"}

                return result

        except Exception as e:
            logger.error(f"Failed to extract stream for {platform}: {e}")
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract)


async def _extract_youtube_stream(
    video_url: str,
    access_token: Optional[str] = None,
    quality: str = "best",
    audio_only: bool = False,
) -> dict:
    """
    Extract YouTube stream URL using yt-dlp.

    Args:
        video_url: Full YouTube video URL
        access_token: OAuth access token for authenticated extraction
        quality: Desired quality (best, 1080p, 720p, 480p, worst)
        audio_only: Get audio stream only

    Returns:
        Dict with stream info including separate video_url and audio_url for
        highest quality playback (browsers can combine using MediaSource API)
    """
    import yt_dlp

    # YouTube quality strategy:
    # - Progressive formats (combined video+audio) are limited to ~720p
    # - DASH formats (separate streams) go up to 4K/8K
    # - For best quality, we get separate video+audio URLs that modern browsers
    #   can combine using MediaSource Extensions (MSE)
    # - The frontend can choose to use combined stream (simpler) or separate (higher quality)

    # YouTube quality strategy for browser playback:
    # 1. First try high-quality combined formats (have both video+audio, up to 1080p)
    # 2. Then try DASH (separate video+audio) which can go higher but needs sync
    # 3. Fall back to any combined format
    #
    # Combined formats are preferred because they work directly in browser <video>
    # DASH formats need frontend to sync separate video+audio elements

    if audio_only:
        format_str = "bestaudio[ext=m4a]/bestaudio/best"
    elif quality == "1080p":
        # Try 1080p combined first, then DASH, then fall back
        format_str = "best[height<=1080][ext=mp4]/best[height<=1080]/bestvideo[height<=1080]+bestaudio/best"
    elif quality == "720p":
        format_str = "best[height<=720][ext=mp4]/best[height<=720]/bestvideo[height<=720]+bestaudio/best"
    elif quality == "480p":
        format_str = "best[height<=480][ext=mp4]/best[height<=480]/bestvideo[height<=480]+bestaudio/best"
    elif quality == "worst":
        format_str = "worst"
    else:
        # "best" = highest quality available for browser playback
        # Try highest combined format first (usually up to 1080p on YouTube)
        # Then try DASH for even higher quality (4K) with separate streams
        format_str = "best[ext=mp4]/best/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": format_str,
        "skip_download": True,
        # Note: Don't use android player_client - it returns only 360p combined formats
        # Default web client returns up to 1080p combined + higher quality DASH
    }

    # Note: OAuth tokens don't work directly with yt-dlp for YouTube
    # Authentication would require browser cookies export
    _ = access_token  # Unused for now

    def extract():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return {"error": "Failed to extract video info"}

                result = {
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                    "duration": info.get("duration"),
                }

                # Get the actual stream URLs
                if "requested_formats" in info:
                    # Separate video and audio streams (DASH - highest quality)
                    for fmt in info["requested_formats"]:
                        if fmt.get("vcodec") != "none" and fmt.get("acodec") == "none":
                            # Video-only stream
                            result["stream_url"] = fmt.get("url")
                            height = fmt.get("height")
                            result["quality"] = f"{height}p" if height else fmt.get("format_note")
                            result["format"] = fmt.get("ext")
                            result["vcodec"] = fmt.get("vcodec")
                            result["width"] = fmt.get("width")
                            result["height"] = height
                            result["fps"] = fmt.get("fps")
                        elif fmt.get("acodec") != "none":
                            # Audio stream
                            result["audio_url"] = fmt.get("url")
                            result["acodec"] = fmt.get("acodec")
                            result["audio_bitrate"] = fmt.get("abr")
                elif "url" in info:
                    # Single combined stream (progressive - usually ≤720p)
                    result["stream_url"] = info["url"]
                    height = info.get("height")
                    result["quality"] = f"{height}p" if height else info.get("format_note") or info.get("resolution")
                    result["format"] = info.get("ext")
                    result["height"] = height
                    result["fps"] = info.get("fps")
                    # Combined streams have audio built-in, no separate audio_url needed
                elif "formats" in info and info["formats"]:
                    # Fallback: find best available format
                    # Sort by height (resolution) descending
                    sorted_formats = sorted(
                        [f for f in info["formats"] if f.get("url")],
                        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
                        reverse=True
                    )
                    if sorted_formats:
                        fmt = sorted_formats[0]
                        result["stream_url"] = fmt.get("url")
                        height = fmt.get("height")
                        result["quality"] = f"{height}p" if height else fmt.get("format_note")
                        result["format"] = fmt.get("ext")
                        result["height"] = height

                return result

        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract)


async def _list_youtube_formats(
    video_url: str,
    access_token: Optional[str] = None,
) -> list[dict]:
    """List available formats for a YouTube video."""
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "listformats": True,
    }

    if access_token:
        ydl_opts["http_headers"] = {
            "Authorization": f"Bearer {access_token}",
        }

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if not info or "formats" not in info:
                return []

            formats = []
            for fmt in info["formats"]:
                formats.append({
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "resolution": fmt.get("resolution"),
                    "quality": fmt.get("format_note"),
                    "vcodec": fmt.get("vcodec"),
                    "acodec": fmt.get("acodec"),
                    "filesize": fmt.get("filesize"),
                    "fps": fmt.get("fps"),
                    "tbr": fmt.get("tbr"),  # Total bitrate
                })

            return formats

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract)


async def _get_redbar_stream(
    video_id: str,
    audio_only: bool = False,
    video_url: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> StreamInfo:
    """
    Get Red Bar Radio stream info.

    Fetches the episode page and extracts the HLS video URL or MP3 audio URL.

    Args:
        video_id: Red Bar episode ID (slug from URL)
        audio_only: If true, prefer audio URL over video
        video_url: Original video URL (if provided, uses correct path)
        db: Database session for auth cookie retrieval

    Returns:
        StreamInfo with HLS stream URL and audio fallback
    """
    from app.core.platforms.redbar import RedBarPlatform
    from app.services.redbar_auth_service import get_redbar_auth_service
    from loguru import logger

    # Get session cookies for authenticated access
    session_cookies = {}
    if db:
        try:
            auth_service = get_redbar_auth_service()
            cookies = await auth_service.get_session_cookies(db)
            if cookies:
                session_cookies = cookies
                logger.debug(f"Using authenticated session for Red Bar stream")
        except Exception as e:
            logger.warning(f"Failed to get Red Bar session cookies: {e}")

    adapter = RedBarPlatform(session_cookies=session_cookies)

    # Determine episode URL
    # Use provided video_url if available (has correct /shows/ or /archives/ path)
    if video_url and "redbarradio.net" in video_url:
        episode_url = video_url
        logger.debug(f"Using provided video URL: {episode_url}")
    else:
        # Default to /shows/ path
        episode_url = f"https://redbarradio.net/shows/{video_id}"
        logger.debug(f"Constructed episode URL: {episode_url}")

    try:
        # Fetch episode info (this will extract HLS and audio URLs)
        result = await adapter.get_video_info(episode_url)

        if not result:
            logger.warning(f"No result from Red Bar adapter for {video_id}")
            return StreamInfo(
                video_id=video_id,
                platform="redbar",
                error="Episode not found or not accessible",
            )

        # Build response
        stream_url = None
        audio_url = result.audio_url
        format_type = None

        # Prefer audio if requested
        if audio_only and audio_url:
            stream_url = audio_url
            format_type = "mp3"
        elif result.video_stream_url:
            stream_url = result.video_stream_url
            format_type = "hls"
        elif audio_url:
            # Fallback to audio if no video available
            stream_url = audio_url
            format_type = "mp3"

        return StreamInfo(
            video_id=video_id,
            platform="redbar",
            title=result.title,
            stream_url=stream_url,
            audio_url=audio_url,
            thumbnail_url=result.thumbnail_url,
            duration_seconds=result.duration_seconds,
            is_authenticated=bool(adapter.session_cookies),
            is_premium=bool(adapter.session_cookies),
            quality="HLS" if format_type == "hls" else "Audio",
            format=format_type,
        )

    except Exception as e:
        logger.error(f"Failed to get Red Bar stream for {video_id}: {e}")
        return StreamInfo(
            video_id=video_id,
            platform="redbar",
            error=str(e),
        )
