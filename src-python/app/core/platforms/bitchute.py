"""BitChute platform adapter using web scraping."""

import re
from datetime import datetime, timedelta
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


class BitChutePlatform(PlatformAdapter):
    """
    BitChute platform adapter.

    Uses web scraping since BitChute has no official API.
    """

    platform_id = "bitchute"
    platform_name = "BitChute"
    platform_icon = "🟠"
    platform_color = "#ef4a23"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = False

    BASE_URL = "https://www.bitchute.com"

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ):
        self.user_agent = user_agent

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is a BitChute URL."""
        try:
            parsed = urlparse(url.lower())
            return parsed.netloc in ["bitchute.com", "www.bitchute.com"]
        except Exception:
            return False

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """Search for videos on BitChute."""
        search_url = f"{self.BASE_URL}/search/?query={quote(query)}&kind=video"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    search_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_video_list(response.text, max_results)

        except Exception as e:
            logger.error(f"BitChute video search failed: {e}")
            return []

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """Search for channels on BitChute."""
        search_url = f"{self.BASE_URL}/search/?query={quote(query)}&kind=channel"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    search_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

            return self._parse_channel_list(response.text, max_results)

        except Exception as e:
            logger.error(f"BitChute channel search failed: {e}")
            return []

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get videos from a BitChute channel."""
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

            results = self._parse_video_list(response.text, max_results)

            # Get channel info for metadata
            channel_id = self._extract_channel_id(channel_url)

            # Add channel info to results
            for result in results:
                result.channel_url = channel_url
                result.channel_id = channel_id

            # Filter by date if specified
            if since:
                results = [
                    r for r in results if not r.upload_date or r.upload_date >= since
                ]

            return results

        except Exception as e:
            logger.error(f"Failed to get BitChute channel videos: {e}")
            return []

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get BitChute channel metadata."""
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
            logger.warning(f"Failed to get BitChute channel info: {e}")
            return None

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """Get single BitChute video metadata."""
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
            logger.warning(f"Failed to get BitChute video info: {e}")
            return None

    def _parse_video_list(self, html: str, max_results: int) -> list[VideoResult]:
        """Parse video list from HTML."""
        results = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Find video cards
            video_cards = soup.select(
                ".video-card, .channel-videos-container .video-result-container, "
                ".search-results-list .video-result-container"
            )

            for card in video_cards[:max_results]:
                try:
                    # Get video URL
                    link = card.select_one("a[href*='/video/']")
                    if not link:
                        continue

                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = f"{self.BASE_URL}{href}"

                    video_id = self._extract_video_id(href)
                    if not video_id:
                        continue

                    # Get title
                    title_elem = card.select_one(
                        ".video-card-title, .video-result-title, .channel-videos-title"
                    )
                    title = title_elem.get_text(strip=True) if title_elem else "Untitled"

                    # Get thumbnail
                    thumbnail_url = None
                    img = card.select_one("img")
                    if img:
                        thumbnail_url = img.get("src") or img.get("data-src")
                        if thumbnail_url and not thumbnail_url.startswith("http"):
                            thumbnail_url = f"{self.BASE_URL}{thumbnail_url}"

                    # Get duration
                    duration_seconds = None
                    duration_elem = card.select_one(".video-duration, .video-card-duration")
                    if duration_elem:
                        duration_seconds = self._parse_duration(
                            duration_elem.get_text(strip=True)
                        )

                    # Get view count
                    view_count = None
                    views_elem = card.select_one(".video-views, .video-card-views")
                    if views_elem:
                        view_count = self._parse_count(views_elem.get_text(strip=True))

                    # Get channel info
                    channel_name = None
                    channel_url = None
                    channel_elem = card.select_one("a[href*='/channel/']")
                    if channel_elem:
                        channel_name = channel_elem.get_text(strip=True)
                        channel_href = channel_elem.get("href", "")
                        if channel_href and not channel_href.startswith("http"):
                            channel_url = f"{self.BASE_URL}{channel_href}"
                        else:
                            channel_url = channel_href

                    # Get upload date
                    upload_date = None
                    date_elem = card.select_one(".video-card-published, .video-publish-date")
                    if date_elem:
                        upload_date = self._parse_relative_date(
                            date_elem.get_text(strip=True)
                        )

                    results.append(
                        VideoResult(
                            platform=self.platform_id,
                            video_id=video_id,
                            video_url=href,
                            title=title,
                            thumbnail_url=thumbnail_url,
                            duration_seconds=duration_seconds,
                            view_count=view_count,
                            upload_date=upload_date,
                            channel_name=channel_name,
                            channel_url=channel_url,
                            channel_id=self._extract_channel_id(channel_url)
                            if channel_url
                            else None,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse BitChute video card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse BitChute video list: {e}")

        return results

    def _parse_channel_list(self, html: str, max_results: int) -> list[ChannelResult]:
        """Parse channel list from HTML."""
        results = []
        seen = set()

        try:
            soup = BeautifulSoup(html, "lxml")

            # Find channel cards
            channel_cards = soup.select(
                ".channel-card, .search-results-list .channel-result-container"
            )

            for card in channel_cards[:max_results]:
                try:
                    # Get channel URL
                    link = card.select_one("a[href*='/channel/']")
                    if not link:
                        continue

                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = f"{self.BASE_URL}{href}"

                    channel_id = self._extract_channel_id(href)
                    if not channel_id or channel_id in seen:
                        continue

                    seen.add(channel_id)

                    # Get name
                    name_elem = card.select_one(".channel-card-title, .channel-result-title")
                    name = name_elem.get_text(strip=True) if name_elem else channel_id

                    # Get avatar
                    avatar_url = None
                    img = card.select_one("img")
                    if img:
                        avatar_url = img.get("src") or img.get("data-src")
                        if avatar_url and not avatar_url.startswith("http"):
                            avatar_url = f"{self.BASE_URL}{avatar_url}"

                    # Get subscriber count
                    subscriber_count = None
                    sub_elem = card.select_one(".channel-card-subscribers, .subscribers")
                    if sub_elem:
                        subscriber_count = self._parse_count(sub_elem.get_text(strip=True))

                    # Get description
                    description = None
                    desc_elem = card.select_one(
                        ".channel-card-description, .channel-description"
                    )
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:500]

                    results.append(
                        ChannelResult(
                            platform=self.platform_id,
                            channel_id=channel_id,
                            channel_url=href,
                            name=name,
                            description=description,
                            avatar_url=avatar_url,
                            subscriber_count=subscriber_count,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Failed to parse BitChute channel card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse BitChute channel list: {e}")

        return results

    def _parse_channel_page(self, html: str, channel_url: str) -> Optional[ChannelResult]:
        """Parse channel page for metadata."""
        try:
            soup = BeautifulSoup(html, "lxml")

            channel_id = self._extract_channel_id(channel_url)

            # Get name
            name = channel_id
            name_elem = soup.select_one(
                ".channel-banner .name, .owner .name, h1.name"
            )
            if name_elem:
                name = name_elem.get_text(strip=True)

            # Get description
            description = None
            desc_elem = soup.select_one(".channel-banner .description, .owner .description")
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:500]

            # Get avatar
            avatar_url = None
            avatar_elem = soup.select_one(".channel-banner img, .owner img")
            if avatar_elem:
                avatar_url = avatar_elem.get("src")
                if avatar_url and not avatar_url.startswith("http"):
                    avatar_url = f"{self.BASE_URL}{avatar_url}"

            # Get subscriber count
            subscriber_count = None
            sub_elem = soup.select_one(".subscribers, .channel-subscribers")
            if sub_elem:
                subscriber_count = self._parse_count(sub_elem.get_text(strip=True))

            return ChannelResult(
                platform=self.platform_id,
                channel_id=channel_id or "",
                channel_url=channel_url,
                name=name or "Unknown",
                description=description,
                avatar_url=avatar_url,
                subscriber_count=subscriber_count,
            )

        except Exception as e:
            logger.warning(f"Failed to parse BitChute channel page: {e}")
            return None

    def _parse_video_page(self, html: str, video_url: str) -> Optional[VideoResult]:
        """Parse video page for metadata."""
        try:
            soup = BeautifulSoup(html, "lxml")

            video_id = self._extract_video_id(video_url)

            # Get title
            title = "Untitled"
            title_elem = soup.select_one("#video-title, .video-title, h1")
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Get description
            description = None
            desc_elem = soup.select_one("#video-description, .video-description")
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:1000]

            # Get thumbnail from meta
            thumbnail_url = None
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image:
                thumbnail_url = og_image.get("content")

            # Get view count
            view_count = None
            views_elem = soup.select_one("#video-views, .video-views")
            if views_elem:
                view_count = self._parse_count(views_elem.get_text(strip=True))

            # Get channel info
            channel_name = None
            channel_url = None
            channel_elem = soup.select_one(
                ".owner a[href*='/channel/'], .channel-banner a[href*='/channel/']"
            )
            if channel_elem:
                channel_name = channel_elem.get_text(strip=True)
                channel_href = channel_elem.get("href", "")
                if channel_href and not channel_href.startswith("http"):
                    channel_url = f"{self.BASE_URL}{channel_href}"
                else:
                    channel_url = channel_href

            # Get upload date
            upload_date = None
            date_elem = soup.select_one("#video-publish-date, .video-publish-date")
            if date_elem:
                upload_date = self._parse_date_text(date_elem.get_text(strip=True))

            return VideoResult(
                platform=self.platform_id,
                video_id=video_id or "",
                video_url=video_url,
                title=title,
                description=description,
                thumbnail_url=thumbnail_url,
                view_count=view_count,
                upload_date=upload_date,
                channel_name=channel_name,
                channel_url=channel_url,
                channel_id=self._extract_channel_id(channel_url) if channel_url else None,
            )

        except Exception as e:
            logger.warning(f"Failed to parse BitChute video page: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from BitChute video URL."""
        match = re.search(r"/video/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None

    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from BitChute channel URL."""
        if not url:
            return None

        match = re.search(r"/channel/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
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

    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        """Parse relative date like '2 days ago'."""
        try:
            text = text.lower().strip()
            now = datetime.utcnow()

            if "hour" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    hours = int(match.group(1))
                    return now - timedelta(hours=hours)

            if "day" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    days = int(match.group(1))
                    return now - timedelta(days=days)

            if "week" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    weeks = int(match.group(1))
                    return now - timedelta(weeks=weeks)

            if "month" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    months = int(match.group(1))
                    return now - timedelta(days=months * 30)

            if "year" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    years = int(match.group(1))
                    return now - timedelta(days=years * 365)

        except Exception:
            pass

        return None

    def _parse_date_text(self, text: str) -> Optional[datetime]:
        """Parse date from text."""
        # Try relative date first
        relative = self._parse_relative_date(text)
        if relative:
            return relative

        # Try common date formats
        formats = [
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except (ValueError, TypeError):
                continue

        return None
