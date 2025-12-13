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
        Dict with stream info
    """
    import yt_dlp

    # Quality mapping
    quality_formats = {
        "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
        "worst": "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst",
        "audio": "bestaudio[ext=m4a]/bestaudio",
    }

    if audio_only:
        format_str = quality_formats["audio"]
    else:
        format_str = quality_formats.get(quality, quality_formats["best"])

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": format_str,
        "skip_download": True,
    }

    # Add OAuth token if available
    # Note: yt-dlp supports OAuth via cookies, but direct token injection
    # requires custom handling. For now, we pass the token as a header.
    if access_token:
        ydl_opts["http_headers"] = {
            "Authorization": f"Bearer {access_token}",
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

                # Get the actual stream URL
                if "url" in info:
                    result["stream_url"] = info["url"]
                    result["quality"] = info.get("format_note") or info.get("resolution")
                    result["format"] = info.get("ext")
                elif "requested_formats" in info:
                    # Separate video and audio streams
                    for fmt in info["requested_formats"]:
                        if fmt.get("vcodec") != "none":
                            result["stream_url"] = fmt.get("url")
                            result["quality"] = fmt.get("format_note") or fmt.get("resolution")
                            result["format"] = fmt.get("ext")
                        if fmt.get("acodec") != "none":
                            result["audio_url"] = fmt.get("url")
                elif "formats" in info and info["formats"]:
                    # Fallback to first available format
                    fmt = info["formats"][-1]
                    result["stream_url"] = fmt.get("url")
                    result["quality"] = fmt.get("format_note")
                    result["format"] = fmt.get("ext")

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
