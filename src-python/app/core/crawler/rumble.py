"""Rumble extractor using RSS feeds and HTML scraping."""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

import httpx
from loguru import logger


@dataclass
class RumbleVideo:
    """Rumble video data."""
    video_id: str
    video_url: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    upload_date: Optional[datetime] = None


@dataclass
class RumbleChannelInfo:
    """Rumble channel information."""
    channel_id: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    subscriber_count: Optional[int] = None


class RumbleExtractor:
    """
    Extract video metadata from Rumble channels.

    Supports:
    - RSS feed parsing (primary method)
    - HTML scraping (fallback)
    """

    def __init__(
        self,
        rate_limit_delay: float = 5.0,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ):
        """
        Initialize Rumble extractor.

        Args:
            rate_limit_delay: Delay between requests in seconds
            user_agent: User agent string for requests
        """
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent

    async def get_channel_info(self, channel_url: str) -> Optional[RumbleChannelInfo]:
        """
        Get channel information from Rumble.

        Args:
            channel_url: Rumble channel URL

        Returns:
            RumbleChannelInfo or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    channel_url,
                    headers={"User-Agent": self.user_agent},
                    timeout=30,
                    follow_redirects=True,
                )

                if response.status_code != 200:
                    return None

                return self._parse_channel_info(response.text, channel_url)

        except Exception as e:
            logger.warning(f"Failed to get Rumble channel info: {e}")
            return None

    async def get_videos(
        self,
        channel_url: str,
        since: Optional[datetime] = None,
        max_videos: int = 50,
    ) -> AsyncGenerator[dict, None]:
        """
        Get videos from a Rumble channel.

        Args:
            channel_url: Rumble channel URL
            since: Only get videos after this date
            max_videos: Maximum number of videos to fetch

        Yields:
            Dict with video data
        """
        # Extract channel ID from URL
        channel_id = self._extract_channel_id(channel_url)
        if not channel_id:
            logger.warning(f"Could not extract channel ID from {channel_url}")
            return

        # Try RSS feed first
        rss_url = f"https://rumble.com/c/{channel_id}/feed"
        videos_found = 0

        try:
            async for video in self._get_videos_from_rss(rss_url, since):
                yield video
                videos_found += 1
                if videos_found >= max_videos:
                    return
        except Exception as e:
            logger.info(f"RSS failed for {channel_url}, trying HTML scrape: {e}")

        # Fall back to HTML scraping if RSS didn't work or didn't find videos
        if videos_found == 0:
            try:
                async for video in self._get_videos_from_html(channel_url, since):
                    yield video
                    videos_found += 1
                    if videos_found >= max_videos:
                        return
            except Exception as e:
                logger.warning(f"HTML scrape failed for {channel_url}: {e}")

    async def _get_videos_from_rss(
        self,
        rss_url: str,
        since: Optional[datetime] = None,
    ) -> AsyncGenerator[dict, None]:
        """Parse videos from RSS feed."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                rss_url,
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )

            if response.status_code != 200:
                raise Exception(f"RSS feed returned {response.status_code}")

            videos = self._parse_rss_feed(response.text)

            for video in videos:
                # Filter by date if specified
                if since and video.get("upload_date"):
                    if video["upload_date"] < since:
                        continue

                yield video

                # Rate limiting
                await asyncio.sleep(0.1)

    async def _get_videos_from_html(
        self,
        channel_url: str,
        since: Optional[datetime] = None,
    ) -> AsyncGenerator[dict, None]:
        """Scrape videos from HTML page."""
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient() as client:
            response = await client.get(
                channel_url,
                headers={"User-Agent": self.user_agent},
                timeout=30,
                follow_redirects=True,
            )

            if response.status_code != 200:
                raise Exception(f"HTML page returned {response.status_code}")

            soup = BeautifulSoup(response.text, 'lxml')

            # Find video items
            video_items = soup.select('.video-listing-entry, .videostream')

            for item in video_items:
                video = self._parse_video_item(item)
                if not video:
                    continue

                # Filter by date if specified
                if since and video.get("upload_date"):
                    if video["upload_date"] < since:
                        continue

                yield video

                # Rate limiting
                await asyncio.sleep(0.1)

    def _parse_rss_feed(self, xml_content: str) -> list[dict]:
        """Parse RSS feed XML into video list."""
        videos = []

        try:
            root = ET.fromstring(xml_content)

            # Handle different RSS formats
            namespaces = {
                'media': 'http://search.yahoo.com/mrss/',
                'atom': 'http://www.w3.org/2005/Atom',
            }

            # Find all items
            items = root.findall('.//item')

            for item in items:
                try:
                    title = item.findtext('title', '')
                    link = item.findtext('link', '')

                    # Extract video ID from link
                    video_id = self._extract_video_id_from_url(link)
                    if not video_id:
                        continue

                    # Get description
                    description = item.findtext('description', '')

                    # Get thumbnail from media:thumbnail or enclosure
                    thumbnail_url = None
                    media_thumb = item.find('media:thumbnail', namespaces)
                    if media_thumb is not None:
                        thumbnail_url = media_thumb.get('url')
                    else:
                        enclosure = item.find('enclosure')
                        if enclosure is not None and 'image' in enclosure.get('type', ''):
                            thumbnail_url = enclosure.get('url')

                    # Get duration from media:content
                    duration_seconds = None
                    media_content = item.find('media:content', namespaces)
                    if media_content is not None:
                        duration = media_content.get('duration')
                        if duration:
                            try:
                                duration_seconds = int(float(duration))
                            except (ValueError, TypeError):
                                pass

                    # Get publish date
                    upload_date = None
                    pub_date = item.findtext('pubDate', '')
                    if pub_date:
                        upload_date = self._parse_rss_date(pub_date)

                    videos.append({
                        "video_id": video_id,
                        "video_url": link,
                        "title": title,
                        "description": self._clean_html(description),
                        "thumbnail_url": thumbnail_url,
                        "duration_seconds": duration_seconds,
                        "upload_date": upload_date,
                    })

                except Exception as e:
                    logger.debug(f"Failed to parse RSS item: {e}")
                    continue

        except ET.ParseError as e:
            logger.warning(f"Failed to parse RSS XML: {e}")

        return videos

    def _parse_video_item(self, item) -> Optional[dict]:
        """Parse a video item from HTML."""
        try:
            # Get link
            link_elem = item.select_one('a[href*="/v"]')
            if not link_elem:
                return None

            href = link_elem.get('href', '')
            if not href.startswith('http'):
                href = f"https://rumble.com{href}"

            video_id = self._extract_video_id_from_url(href)
            if not video_id:
                return None

            # Get title
            title_elem = item.select_one('.video-item--title, h3, .title')
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Get thumbnail
            thumbnail_url = None
            img_elem = item.select_one('img')
            if img_elem:
                thumbnail_url = img_elem.get('src') or img_elem.get('data-src')

            # Get duration
            duration_seconds = None
            duration_elem = item.select_one('.video-item--duration, .duration')
            if duration_elem:
                duration_text = duration_elem.get_text(strip=True)
                duration_seconds = self._parse_duration(duration_text)

            # Get view count
            view_count = None
            views_elem = item.select_one('.video-item--views, .views')
            if views_elem:
                views_text = views_elem.get_text(strip=True)
                view_count = self._parse_view_count(views_text)

            # Get upload date (relative)
            upload_date = None
            date_elem = item.select_one('.video-item--time, .date, time')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                upload_date = self._parse_relative_date(date_text)

            return {
                "video_id": video_id,
                "video_url": href,
                "title": title,
                "thumbnail_url": thumbnail_url,
                "duration_seconds": duration_seconds,
                "view_count": view_count,
                "upload_date": upload_date,
            }

        except Exception as e:
            logger.debug(f"Failed to parse video item: {e}")
            return None

    def _parse_channel_info(self, html: str, channel_url: str) -> Optional[RumbleChannelInfo]:
        """Parse channel info from HTML."""
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Extract channel ID from URL
            channel_id = self._extract_channel_id(channel_url)

            # Get name
            name = None
            name_elem = soup.select_one('h1.channel-header--title, .channel-header--title h1, .channel-name')
            if name_elem:
                name = name_elem.get_text(strip=True)

            if not name:
                name = channel_id or "Unknown"

            # Get avatar
            avatar_url = None
            avatar_elem = soup.select_one('.channel-header--thumb img, .channel-avatar img')
            if avatar_elem:
                avatar_url = avatar_elem.get('src')

            # Get subscriber count
            subscriber_count = None
            sub_elem = soup.select_one('.channel-header--followers, .subscribers')
            if sub_elem:
                sub_text = sub_elem.get_text(strip=True)
                subscriber_count = self._parse_subscriber_count(sub_text)

            # Get description
            description = None
            desc_elem = soup.select_one('.channel-header--description, .channel-description')
            if desc_elem:
                description = desc_elem.get_text(strip=True)

            return RumbleChannelInfo(
                channel_id=channel_id or "",
                name=name,
                description=description,
                avatar_url=avatar_url,
                subscriber_count=subscriber_count,
            )

        except Exception as e:
            logger.warning(f"Failed to parse channel info: {e}")
            return None

    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from Rumble URL."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            path = parsed.path

            # rumble.com/c/channelname
            if '/c/' in path:
                parts = path.split('/c/')
                if len(parts) > 1:
                    return parts[1].split('/')[0]

            # rumble.com/user/username
            if '/user/' in path:
                parts = path.split('/user/')
                if len(parts) > 1:
                    return parts[1].split('/')[0]

            return None
        except Exception:
            return None

    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from Rumble video URL."""
        # rumble.com/v2abc123-video-title.html
        match = re.search(r'/v([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        return None

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date format."""
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=None)
            except (ValueError, TypeError):
                continue

        return None

    def _parse_duration(self, duration_text: str) -> Optional[int]:
        """Parse duration text like '10:30' or '1:02:15'."""
        try:
            parts = duration_text.strip().split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, TypeError):
            pass
        return None

    def _parse_view_count(self, text: str) -> Optional[int]:
        """Parse view count from text like '1.2K views'."""
        try:
            text = text.lower().replace(',', '').replace('views', '').strip()
            match = re.search(r'([\d.]+)\s*([kmb])?', text)
            if not match:
                return None

            num = float(match.group(1))
            suffix = match.group(2)

            if suffix == 'k':
                return int(num * 1000)
            elif suffix == 'm':
                return int(num * 1_000_000)
            elif suffix == 'b':
                return int(num * 1_000_000_000)
            return int(num)
        except (ValueError, TypeError):
            return None

    def _parse_subscriber_count(self, text: str) -> Optional[int]:
        """Parse subscriber count from text."""
        return self._parse_view_count(text)

    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        """Parse relative date like '2 days ago'."""
        try:
            text = text.lower().strip()
            now = datetime.utcnow()

            if 'hour' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    hours = int(match.group(1))
                    return now.replace(minute=0, second=0, microsecond=0) - \
                           __import__('datetime').timedelta(hours=hours)

            if 'day' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    days = int(match.group(1))
                    return now.replace(hour=0, minute=0, second=0, microsecond=0) - \
                           __import__('datetime').timedelta(days=days)

            if 'week' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    weeks = int(match.group(1))
                    return now.replace(hour=0, minute=0, second=0, microsecond=0) - \
                           __import__('datetime').timedelta(weeks=weeks)

            if 'month' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    months = int(match.group(1))
                    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - \
                           __import__('datetime').timedelta(days=months * 30)

        except Exception:
            pass

        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        # Simple HTML tag removal
        clean = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        clean = ' '.join(clean.split())
        return clean[:1000]  # Limit length
