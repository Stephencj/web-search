"""Dailymotion platform adapter using official API."""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, quote

import httpx
from loguru import logger

from app.core.platforms.base import (
    PlatformAdapter,
    VideoResult,
    ChannelResult,
    PlaylistResult,
)


class DailymotionPlatform(PlatformAdapter):
    """
    Dailymotion platform adapter.

    Uses the official Dailymotion API which doesn't require authentication
    for basic read operations.
    """

    platform_id = "dailymotion"
    platform_name = "Dailymotion"
    platform_icon = "🔵"
    platform_color = "#0066dc"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = True

    API_BASE = "https://api.dailymotion.com"

    def __init__(self):
        pass

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is a Dailymotion URL."""
        try:
            parsed = urlparse(url.lower())
            dailymotion_domains = [
                "dailymotion.com",
                "www.dailymotion.com",
                "dai.ly",
            ]
            return parsed.netloc in dailymotion_domains
        except Exception:
            return False

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """Search for videos on Dailymotion."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/videos",
                    params={
                        "search": query,
                        "limit": max_results,
                        "fields": "id,title,description,thumbnail_url,duration,views_total,"
                        "created_time,owner.id,owner.screenname,owner.url,owner.avatar_url",
                        "sort": "relevance",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("list", []):
                try:
                    video_id = item.get("id", "")
                    if not video_id:
                        continue

                    # Parse owner info
                    owner = item.get("owner", {})

                    # Parse created time
                    upload_date = None
                    created_time = item.get("created_time")
                    if created_time:
                        try:
                            upload_date = datetime.fromtimestamp(created_time)
                        except (ValueError, TypeError):
                            pass

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=video_id,
                            video_url=f"https://www.dailymotion.com/video/{video_id}",
                            title=item.get("title", "Untitled"),
                            description=item.get("description"),
                            thumbnail_url=item.get("thumbnail_url"),
                            duration_seconds=item.get("duration"),
                            view_count=item.get("views_total"),
                            upload_date=upload_date,
                            channel_name=owner.get("screenname"),
                            channel_id=owner.get("id"),
                            channel_url=owner.get("url"),
                            channel_avatar_url=owner.get("avatar_url"),
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Dailymotion video: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Dailymotion video search failed: {e}")
            return []

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """Search for channels (users) on Dailymotion."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/users",
                    params={
                        "search": query,
                        "limit": max_results,
                        "fields": "id,screenname,description,avatar_url,cover_url,"
                        "followers_total,videos_total,url",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("list", []):
                try:
                    user_id = item.get("id", "")
                    if not user_id:
                        continue

                    results.append(
                        ChannelResult(
                            platform=self.platform_id,
                            channel_id=user_id,
                            channel_url=item.get("url")
                            or f"https://www.dailymotion.com/{item.get('screenname', user_id)}",
                            name=item.get("screenname", "Unknown"),
                            description=item.get("description"),
                            avatar_url=item.get("avatar_url"),
                            banner_url=item.get("cover_url"),
                            subscriber_count=item.get("followers_total"),
                            video_count=item.get("videos_total"),
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Dailymotion user: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Dailymotion channel search failed: {e}")
            return []

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get videos from a Dailymotion channel."""
        try:
            # Extract user ID from URL
            user_id = self._extract_user_id(channel_url)
            if not user_id:
                return []

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/user/{user_id}/videos",
                    params={
                        "limit": max_results,
                        "fields": "id,title,description,thumbnail_url,duration,views_total,"
                        "created_time,owner.id,owner.screenname,owner.url,owner.avatar_url",
                        "sort": "recent",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("list", []):
                try:
                    video_id = item.get("id", "")
                    if not video_id:
                        continue

                    # Parse owner info
                    owner = item.get("owner", {})

                    # Parse created time
                    upload_date = None
                    created_time = item.get("created_time")
                    if created_time:
                        try:
                            upload_date = datetime.fromtimestamp(created_time)
                        except (ValueError, TypeError):
                            pass

                    # Filter by date
                    if since and upload_date and upload_date < since:
                        continue

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=video_id,
                            video_url=f"https://www.dailymotion.com/video/{video_id}",
                            title=item.get("title", "Untitled"),
                            description=item.get("description"),
                            thumbnail_url=item.get("thumbnail_url"),
                            duration_seconds=item.get("duration"),
                            view_count=item.get("views_total"),
                            upload_date=upload_date,
                            channel_name=owner.get("screenname"),
                            channel_id=owner.get("id"),
                            channel_url=owner.get("url") or channel_url,
                            channel_avatar_url=owner.get("avatar_url"),
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Dailymotion video: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Failed to get Dailymotion channel videos: {e}")
            return []

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get Dailymotion channel metadata."""
        try:
            user_id = self._extract_user_id(channel_url)
            if not user_id:
                return None

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/user/{user_id}",
                    params={
                        "fields": "id,screenname,description,avatar_url,cover_url,"
                        "followers_total,videos_total,url",
                    },
                )
                response.raise_for_status()
                data = response.json()

            return ChannelResult(
                platform=self.platform_id,
                channel_id=data.get("id", user_id),
                channel_url=data.get("url") or channel_url,
                name=data.get("screenname", "Unknown"),
                description=data.get("description"),
                avatar_url=data.get("avatar_url"),
                banner_url=data.get("cover_url"),
                subscriber_count=data.get("followers_total"),
                video_count=data.get("videos_total"),
            )

        except Exception as e:
            logger.warning(f"Failed to get Dailymotion channel info: {e}")
            return None

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """Get single Dailymotion video metadata."""
        try:
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return None

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/video/{video_id}",
                    params={
                        "fields": "id,title,description,thumbnail_url,duration,views_total,"
                        "likes_total,created_time,tags,owner.id,owner.screenname,owner.url,"
                        "owner.avatar_url",
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Parse owner info
            owner = data.get("owner", {})

            # Parse created time
            upload_date = None
            created_time = data.get("created_time")
            if created_time:
                try:
                    upload_date = datetime.fromtimestamp(created_time)
                except (ValueError, TypeError):
                    pass

            return VideoResult(
                platform=self.platform_id,
                video_id=data.get("id", video_id),
                video_url=video_url,
                title=data.get("title", "Untitled"),
                description=data.get("description"),
                thumbnail_url=data.get("thumbnail_url"),
                duration_seconds=data.get("duration"),
                view_count=data.get("views_total"),
                like_count=data.get("likes_total"),
                upload_date=upload_date,
                channel_name=owner.get("screenname"),
                channel_id=owner.get("id"),
                channel_url=owner.get("url"),
                channel_avatar_url=owner.get("avatar_url"),
                tags=data.get("tags", []) or [],
            )

        except Exception as e:
            logger.warning(f"Failed to get Dailymotion video info: {e}")
            return None

    async def search_playlists(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[PlaylistResult]:
        """Search for playlists on Dailymotion."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/playlists",
                    params={
                        "search": query,
                        "limit": max_results,
                        "fields": "id,name,description,thumbnail_url,videos_total,"
                        "owner.id,owner.screenname,owner.url",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("list", []):
                try:
                    playlist_id = item.get("id", "")
                    if not playlist_id:
                        continue

                    owner = item.get("owner", {})

                    results.append(
                        PlaylistResult(
                            platform=self.platform_id,
                            playlist_id=playlist_id,
                            playlist_url=f"https://www.dailymotion.com/playlist/{playlist_id}",
                            name=item.get("name", "Untitled"),
                            description=item.get("description"),
                            thumbnail_url=item.get("thumbnail_url"),
                            video_count=item.get("videos_total"),
                            channel_name=owner.get("screenname"),
                            channel_url=owner.get("url"),
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Dailymotion playlist: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Dailymotion playlist search failed: {e}")
            return []

    async def get_playlist_videos(
        self,
        playlist_url: str,
        max_results: int = 100,
    ) -> list[VideoResult]:
        """Get videos from a Dailymotion playlist."""
        try:
            playlist_id = self._extract_playlist_id(playlist_url)
            if not playlist_id:
                return []

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/playlist/{playlist_id}/videos",
                    params={
                        "limit": max_results,
                        "fields": "id,title,description,thumbnail_url,duration,views_total,"
                        "created_time,owner.id,owner.screenname,owner.url,owner.avatar_url",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("list", []):
                try:
                    video_id = item.get("id", "")
                    if not video_id:
                        continue

                    owner = item.get("owner", {})

                    upload_date = None
                    created_time = item.get("created_time")
                    if created_time:
                        try:
                            upload_date = datetime.fromtimestamp(created_time)
                        except (ValueError, TypeError):
                            pass

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=video_id,
                            video_url=f"https://www.dailymotion.com/video/{video_id}",
                            title=item.get("title", "Untitled"),
                            description=item.get("description"),
                            thumbnail_url=item.get("thumbnail_url"),
                            duration_seconds=item.get("duration"),
                            view_count=item.get("views_total"),
                            upload_date=upload_date,
                            channel_name=owner.get("screenname"),
                            channel_id=owner.get("id"),
                            channel_url=owner.get("url"),
                            channel_avatar_url=owner.get("avatar_url"),
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Dailymotion video: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Failed to get Dailymotion playlist videos: {e}")
            return []

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from Dailymotion URL."""
        try:
            parsed = urlparse(url)

            # Handle dai.ly short URLs
            if parsed.netloc == "dai.ly":
                return parsed.path.strip("/")

            # Handle /video/id format
            if "/video/" in parsed.path:
                parts = parsed.path.split("/video/")
                if len(parts) > 1:
                    # Get ID, removing any slug after underscore
                    vid = parts[1].split("/")[0]
                    return vid.split("_")[0]

        except Exception:
            pass
        return None

    def _extract_user_id(self, url: str) -> Optional[str]:
        """Extract user ID from Dailymotion URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")

            # Handle /username or /@username format
            if path and not path.startswith("video/") and not path.startswith("playlist/"):
                return path.lstrip("@").split("/")[0]

        except Exception:
            pass
        return None

    def _extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from Dailymotion URL."""
        try:
            parsed = urlparse(url)

            if "/playlist/" in parsed.path:
                parts = parsed.path.split("/playlist/")
                if len(parts) > 1:
                    return parts[1].split("/")[0]

        except Exception:
            pass
        return None
