"""Rumble platform adapter using RSS feeds and HTML scraping."""

import asyncio
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
from app.core.crawler.rumble import RumbleExtractor


class RumblePlatform(PlatformAdapter):
    """
    Rumble platform adapter.

    Uses RSS feeds primarily, with HTML scraping as fallback.
    """

    platform_id = "rumble"
    platform_name = "Rumble"
    platform_icon = "🟢"
    platform_color = "#85c742"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = False

    def __init__(
        self,
        rate_limit_delay: float = 2.0,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ):
        """
        Initialize Rumble platform adapter.

        Args:
            rate_limit_delay: Delay between requests in seconds
            user_agent: User agent string for requests
        """
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent
        self._extractor = RumbleExtractor(
            rate_limit_delay=rate_limit_delay,
            user_agent=user_agent,
        )

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is a Rumble URL."""
        try:
            parsed = urlparse(url.lower())
            return parsed.netloc in ["rumble.com", "www.rumble.com"]
        except Exception:
            return False

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """Search for videos on Rumble."""
        search_url = f"https://rumble.com/search/video?q={quote(query)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    search_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_video_search_results(response.text, max_results)

        except Exception as e:
            logger.error(f"Rumble video search failed: {e}")
            return []

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """Search for channels on Rumble."""
        search_url = f"https://rumble.com/search/channel?q={quote(query)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    search_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_channel_search_results(response.text, max_results)

        except Exception as e:
            logger.error(f"Rumble channel search failed: {e}")
            return []

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get videos from a Rumble channel."""
        results = []

        try:
            async for video_data in self._extractor.get_videos(
                channel_url, since=since, max_videos=max_results
            ):
                # Get channel info for metadata
                channel_id = self._extract_channel_id(channel_url)

                results.append(
                    VideoResult(
                        platform=self.platform_id,
                        video_id=video_data.get("video_id", ""),
                        video_url=video_data.get("video_url", ""),
                        title=video_data.get("title", "Untitled"),
                        description=video_data.get("description"),
                        thumbnail_url=video_data.get("thumbnail_url"),
                        duration_seconds=video_data.get("duration_seconds"),
                        view_count=video_data.get("view_count"),
                        upload_date=video_data.get("upload_date"),
                        channel_id=channel_id,
                        channel_url=channel_url,
                    )
                )

        except Exception as e:
            logger.error(f"Failed to get Rumble channel videos: {e}")

        return results

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get Rumble channel metadata."""
        try:
            info = await self._extractor.get_channel_info(channel_url)
            if not info:
                return None

            return ChannelResult(
                platform=self.platform_id,
                channel_id=info.channel_id,
                channel_url=channel_url,
                name=info.name,
                description=info.description,
                avatar_url=info.avatar_url,
                subscriber_count=info.subscriber_count,
            )

        except Exception as e:
            logger.warning(f"Failed to get Rumble channel info: {e}")
            return None

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """Get single Rumble video metadata."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    video_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_video_page(response.text, video_url)

        except Exception as e:
            logger.warning(f"Failed to get Rumble video info: {e}")
            return None

    def _parse_video_search_results(self, html: str, max_results: int) -> list[VideoResult]:
        """Parse video search results from HTML."""
        results = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Find video listing items
            video_items = soup.select(
                ".video-listing-entry, .videostream, .video-item, article.video-item"
            )

            for item in video_items[:max_results]:
                try:
                    # Get video URL
                    link = item.select_one("a[href*='/v']")
                    if not link:
                        continue

                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = f"https://rumble.com{href}"

                    video_id = self._extract_video_id(href)
                    if not video_id:
                        continue

                    # Get title
                    title_elem = item.select_one(
                        ".video-item--title, h3, .title, .video-listing-entry--title"
                    )
                    title = title_elem.get_text(strip=True) if title_elem else "Untitled"

                    # Get thumbnail
                    thumbnail_url = None
                    img = item.select_one("img")
                    if img:
                        thumbnail_url = img.get("src") or img.get("data-src")

                    # Get duration
                    duration_seconds = None
                    duration_elem = item.select_one(".video-item--duration, .duration")
                    if duration_elem:
                        duration_seconds = self._parse_duration(
                            duration_elem.get_text(strip=True)
                        )

                    # Get view count
                    view_count = None
                    views_elem = item.select_one(".video-item--views, .views")
                    if views_elem:
                        view_count = self._parse_count(views_elem.get_text(strip=True))

                    # Get channel info
                    channel_name = None
                    channel_url = None
                    channel_elem = item.select_one(
                        "a[href*='/c/'], a[href*='/user/'], .video-item--by a"
                    )
                    if channel_elem:
                        channel_name = channel_elem.get_text(strip=True)
                        channel_href = channel_elem.get("href", "")
                        if channel_href and not channel_href.startswith("http"):
                            channel_url = f"https://rumble.com{channel_href}"
                        else:
                            channel_url = channel_href

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=video_id,
                            video_url=href,
                            title=title,
                            thumbnail_url=thumbnail_url,
                            duration_seconds=duration_seconds,
                            view_count=view_count,
                            channel_name=channel_name,
                            channel_url=channel_url,
                            channel_id=self._extract_channel_id(channel_url)
                            if channel_url
                            else None,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse video item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse Rumble video search results: {e}")

        return results

    def _parse_channel_search_results(
        self, html: str, max_results: int
    ) -> list[ChannelResult]:
        """Parse channel search results from HTML."""
        results = []
        seen = set()

        try:
            soup = BeautifulSoup(html, "lxml")

            # Find channel links
            channel_links = soup.select("a[href*='/c/'], a[href*='/user/']")

            for link in channel_links:
                if len(results) >= max_results:
                    break

                try:
                    href = link.get("href", "")
                    if not href:
                        continue

                    if not href.startswith("http"):
                        href = f"https://rumble.com{href}"

                    channel_id = self._extract_channel_id(href)
                    if not channel_id or channel_id in seen:
                        continue

                    # Skip common non-channel paths
                    if channel_id in ["search", "browse", "live", "latest"]:
                        continue

                    seen.add(channel_id)

                    # Get channel name
                    name = link.get_text(strip=True) or channel_id

                    # Try to get avatar from nearby img
                    avatar_url = None
                    parent = link.parent
                    if parent:
                        img = parent.select_one("img")
                        if img:
                            avatar_url = img.get("src") or img.get("data-src")

                    results.append(
                        ChannelResult(
                            platform=self.platform_id,
                            channel_id=channel_id,
                            channel_url=href,
                            name=name,
                            avatar_url=avatar_url,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse channel link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse Rumble channel search results: {e}")

        return results

    def _parse_video_page(self, html: str, video_url: str) -> Optional[VideoResult]:
        """Parse single video page for metadata."""
        try:
            soup = BeautifulSoup(html, "lxml")

            video_id = self._extract_video_id(video_url)
            if not video_id:
                return None

            # Get title
            title_elem = soup.select_one("h1, .video-title, title")
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"
            # Clean title (remove " - Rumble" suffix)
            title = re.sub(r"\s*-\s*Rumble$", "", title)

            # Get description
            description = None
            desc_elem = soup.select_one(".media-description, .video-description")
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:1000]

            # Get thumbnail from meta tag
            thumbnail_url = None
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image:
                thumbnail_url = og_image.get("content")

            # Get duration from meta or page
            duration_seconds = None
            duration_elem = soup.select_one(".video-duration, .duration")
            if duration_elem:
                duration_seconds = self._parse_duration(duration_elem.get_text(strip=True))

            # Get view count
            view_count = None
            views_elem = soup.select_one(".media-heading-info, .views")
            if views_elem:
                views_text = views_elem.get_text()
                view_match = re.search(r"([\d,.]+)\s*views?", views_text, re.IGNORECASE)
                if view_match:
                    view_count = self._parse_count(view_match.group(1))

            # Get channel info
            channel_name = None
            channel_url = None
            channel_elem = soup.select_one(
                'a[href*="/c/"], a[href*="/user/"], .media-by a'
            )
            if channel_elem:
                channel_name = channel_elem.get_text(strip=True)
                channel_href = channel_elem.get("href", "")
                if channel_href and not channel_href.startswith("http"):
                    channel_url = f"https://rumble.com{channel_href}"
                else:
                    channel_url = channel_href

            return VideoResult(
                platform=self.platform_id,
                video_id=video_id,
                video_url=video_url,
                title=title,
                description=description,
                thumbnail_url=thumbnail_url,
                duration_seconds=duration_seconds,
                view_count=view_count,
                channel_name=channel_name,
                channel_url=channel_url,
                channel_id=self._extract_channel_id(channel_url) if channel_url else None,
            )

        except Exception as e:
            logger.warning(f"Failed to parse Rumble video page: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from Rumble video URL."""
        match = re.search(r"/v([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None

    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from Rumble channel URL."""
        if not url:
            return None

        try:
            parsed = urlparse(url)
            path = parsed.path

            if "/c/" in path:
                parts = path.split("/c/")
                if len(parts) > 1:
                    return parts[1].split("/")[0]

            if "/user/" in path:
                parts = path.split("/user/")
                if len(parts) > 1:
                    return parts[1].split("/")[0]

        except Exception:
            pass

        return None

    def _parse_duration(self, text: str) -> Optional[int]:
        """Parse duration text like '10:30' or '1:02:15'."""
        try:
            parts = text.strip().split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, TypeError):
            pass
        return None

    def _parse_count(self, text: str) -> Optional[int]:
        """Parse count from text like '1.2K' or '1,000,000'."""
        try:
            text = text.lower().replace(",", "").strip()
            text = re.sub(r"[^\d.kmb]", "", text)

            match = re.search(r"([\d.]+)\s*([kmb])?", text)
            if not match:
                return None

            num = float(match.group(1))
            suffix = match.group(2)

            if suffix == "k":
                return int(num * 1000)
            elif suffix == "m":
                return int(num * 1_000_000)
            elif suffix == "b":
                return int(num * 1_000_000_000)
            return int(num)

        except (ValueError, TypeError):
            return None
