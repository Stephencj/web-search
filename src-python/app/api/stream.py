"""Stream API endpoints for authenticated video playback."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.api.deps import DbSession
from app.services.oauth_service import get_oauth_service


router = APIRouter()


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


@router.get("/{platform}/{video_id}", response_model=StreamInfo)
async def get_stream_info(
    platform: str,
    video_id: str,
    db: DbSession,
    quality: str = Query("best", description="Video quality (best, 1080p, 720p, 480p, worst)"),
    audio_only: bool = Query(False, description="Get audio stream only"),
) -> StreamInfo:
    """
    Get direct stream URL for a video.

    If the user has linked their platform account, uses authenticated
    extraction for premium benefits (no ads, higher quality).

    Args:
        platform: Platform ID (youtube, rumble)
        video_id: Video ID on the platform
        quality: Desired video quality
        audio_only: If true, return audio stream only

    Returns:
        StreamInfo with direct stream URLs
    """
    if platform != "youtube":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Streaming not supported for platform: {platform}",
        )

    oauth_service = get_oauth_service()
    account = await oauth_service.get_account(db, platform)

    # Get access token if account exists
    access_token = None
    is_premium = False
    if account:
        access_token = await oauth_service.get_valid_access_token(db, account)
        is_premium = account.is_premium

    # Build video URL
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Extract stream info using yt-dlp
    try:
        stream_info = await _extract_youtube_stream(
            video_url=video_url,
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
    if platform != "youtube":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format listing not supported for platform: {platform}",
        )

    oauth_service = get_oauth_service()
    account = await oauth_service.get_account(db, platform)

    access_token = None
    if account:
        access_token = await oauth_service.get_valid_access_token(db, account)

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        formats = await _list_youtube_formats(video_url, access_token)
        return StreamFormats(
            video_id=video_id,
            platform=platform,
            formats=formats,
            is_authenticated=access_token is not None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get formats: {e}",
        )


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
