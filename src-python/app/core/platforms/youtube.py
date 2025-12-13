"""YouTube platform adapter using yt-dlp."""

import asyncio
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import yt_dlp
from loguru import logger

from app.core.platforms.base import (
    PlatformAdapter,
    VideoResult,
    ChannelResult,
    PlaylistResult,
)


class YouTubePlatform(PlatformAdapter):
    """
    YouTube platform adapter using yt-dlp.

    Supports:
    - Video search
    - Channel search
    - Video metadata extraction
    - Channel video listing
    - Playlist support
    """

    platform_id = "youtube"
    platform_name = "YouTube"
    platform_icon = "📺"
    platform_color = "#FF0000"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = True

    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize YouTube platform adapter.

        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL."""
        try:
            parsed = urlparse(url.lower())
            youtube_domains = [
                "youtube.com",
                "www.youtube.com",
                "m.youtube.com",
                "youtu.be",
                "music.youtube.com",
            ]
            return parsed.netloc in youtube_domains
        except Exception:
            return False

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """Search for videos on YouTube."""
        search_url = f"ytsearch{max_results}:{query}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._extract_with_ytdlp(search_url, ydl_opts)
            )

            if not info or "entries" not in info:
                return []

            results = []
            for entry in info.get("entries", []):
                if not entry:
                    continue

                video_id = entry.get("id")
                if not video_id:
                    continue

                results.append(
                    VideoResult(
                        platform=self.platform_id,
                        video_id=video_id,
                        video_url=f"https://www.youtube.com/watch?v={video_id}",
                        title=entry.get("title", "Untitled"),
                        description=entry.get("description"),
                        thumbnail_url=self._get_thumbnail(entry, video_id),
                        duration_seconds=entry.get("duration"),
                        view_count=entry.get("view_count"),
                        upload_date=self._parse_upload_date(entry.get("upload_date")),
                        channel_name=entry.get("channel") or entry.get("uploader"),
                        channel_id=entry.get("channel_id") or entry.get("uploader_id"),
                        channel_url=entry.get("channel_url") or entry.get("uploader_url"),
                    )
                )

            return results

        except Exception as e:
            logger.error(f"YouTube video search failed: {e}")
            return []

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """Search for channels on YouTube."""
        # Search for videos and extract unique channels
        search_url = f"ytsearch{max_results * 2}:{query} channel"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._extract_with_ytdlp(search_url, ydl_opts)
            )

            if not info or "entries" not in info:
                return []

            seen_channels = set()
            results = []

            for entry in info.get("entries", []):
                if not entry:
                    continue

                channel_id = entry.get("channel_id") or entry.get("uploader_id")
                if not channel_id or channel_id in seen_channels:
                    continue

                seen_channels.add(channel_id)
                channel_url = entry.get("channel_url") or entry.get("uploader_url")
                if not channel_url:
                    channel_url = f"https://www.youtube.com/channel/{channel_id}"

                results.append(
                    ChannelResult(
                        platform=self.platform_id,
                        channel_id=channel_id,
                        channel_url=channel_url,
                        name=entry.get("channel") or entry.get("uploader") or "Unknown",
                        description=entry.get("description"),
                        avatar_url=self._get_thumbnail(entry),
                    )
                )

                if len(results) >= max_results:
                    break

            # Return results directly without enrichment
            # Enrichment was causing timeouts due to sequential get_channel_info() calls
            # Channel details can be fetched lazily when user views a specific channel
            logger.debug(f"YouTube channel search found {len(results)} channels for query: {query}")
            return results[:max_results]

        except Exception as e:
            logger.error(f"YouTube channel search failed for query '{query}': {e}")
            return []

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get videos from a YouTube channel."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "ignoreerrors": True,
            "playlistend": max_results,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._extract_with_ytdlp(channel_url, ydl_opts)
            )

            if not info:
                return []

            # Get channel metadata
            channel_name = info.get("channel") or info.get("uploader")
            channel_id = info.get("channel_id") or info.get("uploader_id")
            channel_url_final = info.get("channel_url") or info.get("uploader_url") or channel_url

            results = []
            entries = info.get("entries", [])

            for entry in entries:
                if not entry:
                    continue

                video_id = entry.get("id")
                if not video_id:
                    continue

                upload_date = self._parse_upload_date(entry.get("upload_date"))

                # Filter by date if specified
                if since and upload_date and upload_date < since:
                    continue

                results.append(
                    VideoResult(
                        platform=self.platform_id,
                        video_id=video_id,
                        video_url=f"https://www.youtube.com/watch?v={video_id}",
                        title=entry.get("title", "Untitled"),
                        description=entry.get("description"),
                        thumbnail_url=self._get_thumbnail(entry, video_id),
                        duration_seconds=entry.get("duration"),
                        view_count=entry.get("view_count"),
                        upload_date=upload_date,
                        channel_name=entry.get("channel") or channel_name,
                        channel_id=entry.get("channel_id") or channel_id,
                        channel_url=entry.get("channel_url") or channel_url_final,
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Failed to get YouTube channel videos: {e}")
            return []

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get YouTube channel metadata."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlist_items": "0",
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._extract_with_ytdlp(channel_url, ydl_opts)
            )

            if not info:
                return None

            channel_id = info.get("channel_id") or info.get("id") or info.get("uploader_id")
            if not channel_id:
                return None

            return ChannelResult(
                platform=self.platform_id,
                channel_id=channel_id,
                channel_url=info.get("channel_url") or info.get("webpage_url") or channel_url,
                name=info.get("channel") or info.get("uploader") or info.get("title") or "Unknown",
                description=info.get("description"),
                avatar_url=self._get_thumbnail(info),
                subscriber_count=info.get("channel_follower_count"),
                video_count=info.get("playlist_count"),
            )

        except Exception as e:
            logger.warning(f"Failed to get YouTube channel info: {e}")
            return None

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """Get single YouTube video metadata."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._extract_with_ytdlp(video_url, ydl_opts)
            )

            if not info:
                return None

            video_id = info.get("id", "")

            return VideoResult(
                platform=self.platform_id,
                video_id=video_id,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                title=info.get("title", "Untitled"),
                description=info.get("description"),
                thumbnail_url=self._get_thumbnail(info, video_id),
                duration_seconds=info.get("duration"),
                view_count=info.get("view_count"),
                like_count=info.get("like_count"),
                upload_date=self._parse_upload_date(info.get("upload_date")),
                channel_name=info.get("channel") or info.get("uploader"),
                channel_id=info.get("channel_id") or info.get("uploader_id"),
                channel_url=info.get("channel_url") or info.get("uploader_url"),
                tags=info.get("tags", []) or [],
            )

        except Exception as e:
            logger.warning(f"Failed to get YouTube video info: {e}")
            return None

    async def search_playlists(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[PlaylistResult]:
        """Search for playlists on YouTube."""
        search_url = f"ytsearch{max_results}:{query} playlist"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._extract_with_ytdlp(search_url, ydl_opts)
            )

            if not info or "entries" not in info:
                return []

            results = []
            for entry in info.get("entries", []):
                if not entry:
                    continue

                # Check if this is a playlist
                if entry.get("_type") != "playlist":
                    continue

                playlist_id = entry.get("id")
                if not playlist_id:
                    continue

                results.append(
                    PlaylistResult(
                        platform=self.platform_id,
                        playlist_id=playlist_id,
                        playlist_url=f"https://www.youtube.com/playlist?list={playlist_id}",
                        name=entry.get("title", "Untitled"),
                        description=entry.get("description"),
                        thumbnail_url=self._get_thumbnail(entry),
                        video_count=entry.get("playlist_count"),
                        channel_name=entry.get("channel") or entry.get("uploader"),
                        channel_url=entry.get("channel_url") or entry.get("uploader_url"),
                    )
                )

            return results

        except Exception as e:
            logger.error(f"YouTube playlist search failed: {e}")
            return []

    async def get_playlist_videos(
        self,
        playlist_url: str,
        max_results: int = 100,
    ) -> list[VideoResult]:
        """Get videos from a YouTube playlist."""
        return await self.get_channel_videos(playlist_url, max_results)

    def _extract_with_ytdlp(self, url: str, opts: dict) -> dict | None:
        """Synchronous extraction using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.debug(f"yt-dlp extraction failed for {url}: {e}")
            return None

    def _get_thumbnail(self, info: dict, video_id: str = None) -> Optional[str]:
        """Get best thumbnail URL from info dict."""
        if info.get("thumbnail"):
            return info["thumbnail"]

        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda t: t.get("preference", 0) or t.get("width", 0),
                reverse=True,
            )
            return sorted_thumbs[0].get("url")

        # Fall back to standard YouTube thumbnail
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

        return None

    def _parse_upload_date(self, date_str: str | None) -> Optional[datetime]:
        """Parse YouTube upload date format (YYYYMMDD)."""
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except (ValueError, TypeError):
            return None
