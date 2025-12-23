"""Download API endpoints for offline video storage."""

import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from app.api.deps import DbSession
from app.services.oauth_service import get_oauth_service


router = APIRouter()


class DownloadInfo(BaseModel):
    """Response schema for download info."""
    video_id: str
    platform: str
    title: Optional[str] = None
    size: Optional[int] = None  # Bytes
    mimeType: str = "video/mp4"
    duration: Optional[int] = None  # Seconds
    quality: Optional[str] = None
    download_url: Optional[str] = None  # Direct URL (for debugging)
    error: Optional[str] = None


@router.get("/{platform}/{video_id}/info", response_model=DownloadInfo)
async def get_download_info(
    platform: str,
    video_id: str,
    db: DbSession,
) -> DownloadInfo:
    """
    Get download information for a video or podcast episode.

    Returns metadata about the downloadable content including file size,
    format, and quality. This is used by the frontend to check storage
    requirements before downloading.
    """
    if platform == "youtube":
        return await _get_youtube_download_info(video_id, db)
    elif platform == "rumble":
        return await _get_rumble_download_info(video_id)
    elif platform == "podcast":
        return await _get_podcast_download_info(video_id, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Downloads not supported for platform: {platform}",
        )


@router.get("/{platform}/{video_id}")
async def download_video(
    platform: str,
    video_id: str,
    db: DbSession,
):
    """
    Download a video or podcast episode for offline storage.

    Returns a streaming response with the content.
    The frontend stores this in IndexedDB for offline access.
    """
    if platform == "youtube":
        return await _stream_youtube_video(video_id, db)
    elif platform == "rumble":
        return await _stream_rumble_video(video_id)
    elif platform == "podcast":
        return await _stream_podcast_episode(video_id, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Downloads not supported for platform: {platform}",
        )


async def _get_youtube_download_info(video_id: str, db: DbSession) -> DownloadInfo:
    """Get download info for a YouTube video."""
    import yt_dlp

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Try to get OAuth token for potentially higher quality
    oauth_service = get_oauth_service()
    account = await oauth_service.get_account(db, "youtube")
    access_token = None
    if account:
        access_token = await oauth_service.get_valid_access_token(db, account)
    _ = access_token  # Not used with yt-dlp currently

    # Format for combined video+audio (progressive) - these are directly downloadable
    # Prefer mp4 for browser compatibility
    format_str = "best[ext=mp4]/best"

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
                    "duration": info.get("duration"),
                }

                # Get the selected format info
                if "url" in info:
                    result["download_url"] = info["url"]
                    result["size"] = info.get("filesize") or info.get("filesize_approx")
                    result["quality"] = f"{info.get('height')}p" if info.get("height") else info.get("format_note")
                    result["mimeType"] = f"video/{info.get('ext', 'mp4')}"
                elif "requested_formats" in info:
                    # DASH format - need to combine, use the first format for size estimate
                    for fmt in info["requested_formats"]:
                        if fmt.get("vcodec") != "none":
                            result["download_url"] = fmt.get("url")
                            result["size"] = fmt.get("filesize") or fmt.get("filesize_approx")
                            result["quality"] = f"{fmt.get('height')}p" if fmt.get("height") else fmt.get("format_note")
                            result["mimeType"] = f"video/{fmt.get('ext', 'mp4')}"
                            break

                return result
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, extract)

    if "error" in info:
        return DownloadInfo(
            video_id=video_id,
            platform="youtube",
            error=info["error"],
        )

    return DownloadInfo(
        video_id=video_id,
        platform="youtube",
        title=info.get("title"),
        size=info.get("size"),
        mimeType=info.get("mimeType", "video/mp4"),
        duration=info.get("duration"),
        quality=info.get("quality"),
        download_url=info.get("download_url"),
    )


async def _get_rumble_download_info(video_id: str) -> DownloadInfo:
    """Get download info for a Rumble video."""
    import yt_dlp

    # Rumble embed URL format
    video_url = f"https://rumble.com/embed/{video_id}/"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[ext=mp4]/best",
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
                    "duration": info.get("duration"),
                }

                if "url" in info:
                    result["download_url"] = info["url"]
                    result["size"] = info.get("filesize") or info.get("filesize_approx")
                    result["quality"] = f"{info.get('height')}p" if info.get("height") else info.get("format_note")
                    result["mimeType"] = f"video/{info.get('ext', 'mp4')}"
                elif "formats" in info and info["formats"]:
                    # Pick best format
                    sorted_formats = sorted(
                        [f for f in info["formats"] if f.get("url") and f.get("ext") == "mp4"],
                        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
                        reverse=True
                    )
                    if sorted_formats:
                        fmt = sorted_formats[0]
                        result["download_url"] = fmt.get("url")
                        result["size"] = fmt.get("filesize") or fmt.get("filesize_approx")
                        result["quality"] = f"{fmt.get('height')}p" if fmt.get("height") else fmt.get("format_note")
                        result["mimeType"] = f"video/{fmt.get('ext', 'mp4')}"

                return result
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, extract)

    if "error" in info:
        return DownloadInfo(
            video_id=video_id,
            platform="rumble",
            error=info["error"],
        )

    return DownloadInfo(
        video_id=video_id,
        platform="rumble",
        title=info.get("title"),
        size=info.get("size"),
        mimeType=info.get("mimeType", "video/mp4"),
        duration=info.get("duration"),
        quality=info.get("quality"),
        download_url=info.get("download_url"),
    )


async def _stream_youtube_video(video_id: str, db: DbSession):
    """Stream a YouTube video for download."""
    import yt_dlp

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Get direct download URL
    format_str = "best[ext=mp4]/best"

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
                    return None, None, None

                download_url = info.get("url")
                content_type = f"video/{info.get('ext', 'mp4')}"
                filesize = info.get("filesize") or info.get("filesize_approx")

                # Handle DASH formats
                if not download_url and "requested_formats" in info:
                    for fmt in info["requested_formats"]:
                        if fmt.get("vcodec") != "none":
                            download_url = fmt.get("url")
                            content_type = f"video/{fmt.get('ext', 'mp4')}"
                            filesize = fmt.get("filesize") or fmt.get("filesize_approx")
                            break

                return download_url, content_type, filesize
        except Exception as e:
            logger.error(f"Failed to extract YouTube download URL: {e}")
            return None, None, None

    loop = asyncio.get_event_loop()
    download_url, content_type, filesize = await loop.run_in_executor(None, extract)

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get download URL",
        )

    return await _proxy_stream(download_url, content_type, filesize)


async def _stream_rumble_video(video_id: str):
    """Stream a Rumble video for download."""
    import yt_dlp

    video_url = f"https://rumble.com/embed/{video_id}/"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[ext=mp4]/best",
        "skip_download": True,
    }

    def extract():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return None, None, None

                download_url = info.get("url")
                content_type = f"video/{info.get('ext', 'mp4')}"
                filesize = info.get("filesize") or info.get("filesize_approx")

                if not download_url and "formats" in info and info["formats"]:
                    sorted_formats = sorted(
                        [f for f in info["formats"] if f.get("url") and f.get("ext") == "mp4"],
                        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
                        reverse=True
                    )
                    if sorted_formats:
                        fmt = sorted_formats[0]
                        download_url = fmt.get("url")
                        content_type = f"video/{fmt.get('ext', 'mp4')}"
                        filesize = fmt.get("filesize") or fmt.get("filesize_approx")

                return download_url, content_type, filesize
        except Exception as e:
            logger.error(f"Failed to extract Rumble download URL: {e}")
            return None, None, None

    loop = asyncio.get_event_loop()
    download_url, content_type, filesize = await loop.run_in_executor(None, extract)

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get download URL",
        )

    return await _proxy_stream(download_url, content_type, filesize)


async def _proxy_stream(
    download_url: str,
    content_type: str,
    filesize: Optional[int] = None,
):
    """
    Proxy a video stream from a direct URL.

    This streams the video through our server to avoid CORS issues
    and to provide progress tracking via Content-Length header.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity",  # Don't compress for accurate size
    }

    async def stream_generator():
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
            async with client.stream("GET", download_url, headers=headers, follow_redirects=True) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=65536):  # 64KB chunks
                    yield chunk

    response_headers = {
        "Content-Type": content_type,
        "Cache-Control": "no-cache",
    }

    if filesize:
        response_headers["Content-Length"] = str(filesize)

    return StreamingResponse(
        stream_generator(),
        media_type=content_type,
        headers=response_headers,
    )


async def _get_podcast_download_info(episode_id: str, db: DbSession) -> DownloadInfo:
    """Get download info for a podcast episode from the database."""
    from sqlalchemy import select
    from app.models.feed_item import FeedItem

    # Look up the feed item by video_id (which stores episode ID for podcasts)
    stmt = select(FeedItem).where(
        FeedItem.platform == "podcast",
        FeedItem.video_id == episode_id
    )
    result = await db.execute(stmt)
    feed_item = result.scalar_one_or_none()

    if not feed_item:
        return DownloadInfo(
            video_id=episode_id,
            platform="podcast",
            error="Episode not found in database",
        )

    if not feed_item.audio_url:
        return DownloadInfo(
            video_id=episode_id,
            platform="podcast",
            title=feed_item.title,
            error="No audio URL available for this episode",
        )

    # Get file size via HEAD request if not stored
    file_size = feed_item.audio_file_size
    if not file_size:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(feed_item.audio_url, follow_redirects=True)
                if response.status_code == 200:
                    file_size = int(response.headers.get("content-length", 0)) or None
        except Exception:
            pass

    return DownloadInfo(
        video_id=episode_id,
        platform="podcast",
        title=feed_item.title,
        size=file_size,
        mimeType=feed_item.audio_mime_type or "audio/mpeg",
        duration=feed_item.duration_seconds,
        quality="audio",
        download_url=feed_item.audio_url,
    )


async def _stream_podcast_episode(episode_id: str, db: DbSession):
    """Stream a podcast episode for download."""
    from sqlalchemy import select
    from app.models.feed_item import FeedItem

    # Look up the feed item
    stmt = select(FeedItem).where(
        FeedItem.platform == "podcast",
        FeedItem.video_id == episode_id
    )
    result = await db.execute(stmt)
    feed_item = result.scalar_one_or_none()

    if not feed_item or not feed_item.audio_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast episode not found or no audio URL",
        )

    content_type = feed_item.audio_mime_type or "audio/mpeg"
    file_size = feed_item.audio_file_size

    return await _proxy_stream(feed_item.audio_url, content_type, file_size)
