"""Odysee/LBRY platform adapter."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, quote

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.platforms.base import (
    PlatformAdapter,
    VideoResult,
    ChannelResult,
)


class OdyseePlatform(PlatformAdapter):
    """
    Odysee/LBRY platform adapter.

    Uses Odysee web API and HTML scraping.
    """

    platform_id = "odysee"
    platform_name = "Odysee"
    platform_icon = "🔴"
    platform_color = "#e50054"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = False

    # Odysee API base URL
    API_BASE = "https://odysee.com"
    LIGHTHOUSE_API = "https://lighthouse.odysee.tv/search"

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ):
        self.user_agent = user_agent

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is an Odysee/LBRY URL."""
        try:
            parsed = urlparse(url.lower())
            odysee_domains = ["odysee.com", "www.odysee.com", "lbry.tv", "open.lbry.com"]
            return parsed.netloc in odysee_domains
        except Exception:
            return False

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """Search for videos on Odysee using Lighthouse API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use Lighthouse search API
                response = await client.get(
                    self.LIGHTHOUSE_API,
                    params={
                        "s": query,
                        "size": max_results,
                        "from": 0,
                        "nsfw": "false",
                        "mediaType": "video",
                    },
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data:
                try:
                    claim_id = item.get("claimId", "")
                    name = item.get("name", "")

                    if not claim_id or not name:
                        continue

                    # Build canonical URL
                    channel_name = item.get("channel_name", "")
                    if channel_name:
                        video_url = f"https://odysee.com/@{channel_name}/{name}"
                    else:
                        video_url = f"https://odysee.com/{name}:{claim_id[:8]}"

                    # Parse duration
                    duration = item.get("duration")
                    duration_seconds = int(duration) if duration else None

                    # Parse release time
                    upload_date = None
                    release_time = item.get("release_time")
                    if release_time:
                        try:
                            upload_date = datetime.fromtimestamp(int(release_time))
                        except (ValueError, TypeError):
                            pass

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=claim_id,
                            video_url=video_url,
                            title=item.get("title", name),
                            description=item.get("description"),
                            thumbnail_url=item.get("thumbnail_url"),
                            duration_seconds=duration_seconds,
                            view_count=None,  # Not in search results
                            upload_date=upload_date,
                            channel_name=channel_name or item.get("channel"),
                            channel_id=item.get("channel_claim_id"),
                            channel_url=f"https://odysee.com/@{channel_name}"
                            if channel_name
                            else None,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Odysee search result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Odysee video search failed: {e}")
            return []

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """Search for channels on Odysee."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use Lighthouse search API for channels
                response = await client.get(
                    self.LIGHTHOUSE_API,
                    params={
                        "s": query,
                        "size": max_results,
                        "from": 0,
                        "claimType": "channel",
                    },
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data:
                try:
                    claim_id = item.get("claimId", "")
                    name = item.get("name", "")

                    if not claim_id or not name.startswith("@"):
                        continue

                    channel_url = f"https://odysee.com/{name}"

                    results.append(
                        ChannelResult(
                            platform=self.platform_id,
                            channel_id=claim_id,
                            channel_url=channel_url,
                            name=item.get("title", name.lstrip("@")),
                            description=item.get("description"),
                            avatar_url=item.get("thumbnail_url"),
                            subscriber_count=None,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Odysee channel result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Odysee channel search failed: {e}")
            return []

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get videos from an Odysee channel."""
        try:
            # Extract channel name from URL
            channel_name = self._extract_channel_name(channel_url)
            if not channel_name:
                return []

            # Search for videos by this channel
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.LIGHTHOUSE_API,
                    params={
                        "s": "",
                        "size": max_results,
                        "from": 0,
                        "channel": channel_name,
                        "mediaType": "video",
                    },
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data:
                try:
                    claim_id = item.get("claimId", "")
                    name = item.get("name", "")

                    if not claim_id or not name:
                        continue

                    video_url = f"https://odysee.com/@{channel_name}/{name}"

                    # Parse release time
                    upload_date = None
                    release_time = item.get("release_time")
                    if release_time:
                        try:
                            upload_date = datetime.fromtimestamp(int(release_time))
                        except (ValueError, TypeError):
                            pass

                    # Filter by date
                    if since and upload_date and upload_date < since:
                        continue

                    duration = item.get("duration")

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=claim_id,
                            video_url=video_url,
                            title=item.get("title", name),
                            description=item.get("description"),
                            thumbnail_url=item.get("thumbnail_url"),
                            duration_seconds=int(duration) if duration else None,
                            upload_date=upload_date,
                            channel_name=channel_name,
                            channel_url=channel_url,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse Odysee video: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Failed to get Odysee channel videos: {e}")
            return []

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get Odysee channel metadata."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    channel_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_channel_page(response.text, channel_url)

        except Exception as e:
            logger.warning(f"Failed to get Odysee channel info: {e}")
            return None

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """Get single Odysee video metadata."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    video_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_video_page(response.text, video_url)

        except Exception as e:
            logger.warning(f"Failed to get Odysee video info: {e}")
            return None

    def _parse_channel_page(self, html: str, channel_url: str) -> Optional[ChannelResult]:
        """Parse channel page for metadata."""
        try:
            soup = BeautifulSoup(html, "lxml")

            channel_name = self._extract_channel_name(channel_url)

            # Get title from meta or page
            name = channel_name
            title_elem = soup.select_one('meta[property="og:title"]')
            if title_elem:
                name = title_elem.get("content", channel_name)

            # Get description
            description = None
            desc_elem = soup.select_one('meta[property="og:description"]')
            if desc_elem:
                description = desc_elem.get("content")

            # Get avatar
            avatar_url = None
            avatar_elem = soup.select_one('meta[property="og:image"]')
            if avatar_elem:
                avatar_url = avatar_elem.get("content")

            return ChannelResult(
                platform=self.platform_id,
                channel_id=channel_name or "",
                channel_url=channel_url,
                name=name or "Unknown",
                description=description,
                avatar_url=avatar_url,
            )

        except Exception as e:
            logger.warning(f"Failed to parse Odysee channel page: {e}")
            return None

    def _parse_video_page(self, html: str, video_url: str) -> Optional[VideoResult]:
        """Parse video page for metadata."""
        try:
            soup = BeautifulSoup(html, "lxml")

            # Get title
            title = "Untitled"
            title_elem = soup.select_one('meta[property="og:title"]')
            if title_elem:
                title = title_elem.get("content", title)

            # Get description
            description = None
            desc_elem = soup.select_one('meta[property="og:description"]')
            if desc_elem:
                description = desc_elem.get("content")

            # Get thumbnail
            thumbnail_url = None
            thumb_elem = soup.select_one('meta[property="og:image"]')
            if thumb_elem:
                thumbnail_url = thumb_elem.get("content")

            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)

            # Extract channel info from URL
            channel_name = self._extract_channel_from_video_url(video_url)

            return VideoResult(
                platform=self.platform_id,
                video_id=video_id or "",
                video_url=video_url,
                title=title,
                description=description,
                thumbnail_url=thumbnail_url,
                channel_name=channel_name,
                channel_url=f"https://odysee.com/@{channel_name}" if channel_name else None,
            )

        except Exception as e:
            logger.warning(f"Failed to parse Odysee video page: {e}")
            return None

    def _extract_channel_name(self, url: str) -> Optional[str]:
        """Extract channel name from Odysee URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path

            # Format: /@channelname or /@channelname:claimid
            match = re.search(r"/@([^/:]+)", path)
            if match:
                return match.group(1)

        except Exception:
            pass
        return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video claim ID from URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path

            # Format: /@channel/video:claimid or /video:claimid
            match = re.search(r":([a-f0-9]+)$", path)
            if match:
                return match.group(1)

            # Try to get from path segment
            parts = path.strip("/").split("/")
            if parts:
                return parts[-1].split(":")[0]

        except Exception:
            pass
        return None

    def _extract_channel_from_video_url(self, url: str) -> Optional[str]:
        """Extract channel name from video URL."""
        return self._extract_channel_name(url)
