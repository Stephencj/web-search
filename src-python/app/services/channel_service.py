"""Channel service - manages subscribed video channels."""

import asyncio
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crawler.url_detector import (
    Platform,
    detect_platform,
    detect_channel_info,
    is_youtube_url,
    is_rumble_url,
    get_youtube_url_type,
)
from app.core.crawler.youtube_types import YouTubeUrlType
from app.models import Channel


class ChannelService:
    """Service for managing subscribed video channels."""

    async def add_channel(
        self,
        db: AsyncSession,
        url: str,
        import_source: str = "manual",
    ) -> Channel:
        """
        Add a new channel subscription.

        Args:
            db: Database session
            url: Channel URL (YouTube or Rumble)
            import_source: How the channel was added ("manual", "takeout", "bookmarklet")

        Returns:
            Created Channel

        Raises:
            ValueError: If URL is invalid or unsupported platform
        """
        # Detect platform and extract channel ID
        platform, channel_id = detect_channel_info(url)

        if platform == Platform.UNKNOWN:
            raise ValueError(f"Unsupported platform for URL: {url}")

        if not channel_id:
            # For YouTube, try to extract from the URL type
            if platform == Platform.YOUTUBE:
                url_type = get_youtube_url_type(url)
                if url_type != YouTubeUrlType.CHANNEL:
                    raise ValueError(f"URL is not a channel URL: {url}")
            raise ValueError(f"Could not extract channel ID from URL: {url}")

        # Check if channel already exists
        existing = await self.get_channel_by_platform_id(
            db, platform.value, channel_id
        )
        if existing:
            logger.info(f"Channel already exists: {existing.name}")
            return existing

        # Fetch channel metadata
        metadata = await self._fetch_channel_metadata(url, platform)

        # Create channel
        channel = Channel(
            platform=platform.value,
            platform_channel_id=channel_id,
            channel_url=self._normalize_channel_url(url, platform, channel_id),
            name=metadata.get("name", channel_id),
            description=metadata.get("description"),
            avatar_url=metadata.get("avatar_url"),
            banner_url=metadata.get("banner_url"),
            subscriber_count=metadata.get("subscriber_count"),
            import_source=import_source,
        )

        db.add(channel)
        await db.commit()
        await db.refresh(channel)

        logger.info(f"Added channel: {channel.name} ({platform.value})")
        return channel

    async def import_from_urls(
        self,
        db: AsyncSession,
        urls: list[str],
        import_source: str = "bookmarklet",
    ) -> dict:
        """
        Import multiple channels from a list of URLs.

        Args:
            db: Database session
            urls: List of channel URLs
            import_source: Import source identifier

        Returns:
            Dict with imported, skipped, failed counts and details
        """
        imported = []
        skipped = []
        failed = []
        errors = []

        for url in urls:
            url = url.strip()
            if not url:
                continue

            try:
                channel = await self.add_channel(db, url, import_source)
                if channel.created_at.replace(microsecond=0) == channel.updated_at.replace(microsecond=0):
                    # Newly created
                    imported.append(channel)
                else:
                    # Already existed
                    skipped.append(channel)
            except ValueError as e:
                failed.append(url)
                errors.append(f"{url}: {str(e)}")
            except Exception as e:
                failed.append(url)
                errors.append(f"{url}: Unexpected error - {str(e)}")
                logger.warning(f"Failed to import channel {url}: {e}")

            # Small delay between imports to avoid rate limiting
            await asyncio.sleep(0.5)

        return {
            "imported": len(imported),
            "skipped": len(skipped),
            "failed": len(failed),
            "channels": imported,
            "errors": errors,
        }

    async def import_from_takeout(
        self,
        db: AsyncSession,
        subscriptions: list[dict],
    ) -> dict:
        """
        Import channels from Google Takeout subscriptions JSON.

        Args:
            db: Database session
            subscriptions: List of subscription entries from Takeout

        Returns:
            Dict with imported, skipped, failed counts and details

        Expected Takeout format:
        [
            {
                "snippet": {
                    "resourceId": {"channelId": "UC..."},
                    "title": "Channel Name"
                }
            }
        ]
        """
        urls = []

        for sub in subscriptions:
            try:
                # Handle different Takeout formats
                if "snippet" in sub:
                    # YouTube API format
                    snippet = sub["snippet"]
                    channel_id = snippet.get("resourceId", {}).get("channelId")
                    if channel_id:
                        urls.append(f"https://www.youtube.com/channel/{channel_id}")
                elif "channelId" in sub:
                    # Simplified format
                    urls.append(f"https://www.youtube.com/channel/{sub['channelId']}")
                elif "url" in sub:
                    # Direct URL format
                    urls.append(sub["url"])
            except Exception as e:
                logger.warning(f"Failed to parse Takeout entry: {e}")
                continue

        return await self.import_from_urls(db, urls, import_source="takeout")

    async def get_channel(
        self,
        db: AsyncSession,
        channel_id: int,
    ) -> Optional[Channel]:
        """Get a channel by ID."""
        result = await db.execute(
            select(Channel).where(Channel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_channel_by_platform_id(
        self,
        db: AsyncSession,
        platform: str,
        platform_channel_id: str,
    ) -> Optional[Channel]:
        """Get a channel by platform and platform channel ID."""
        result = await db.execute(
            select(Channel).where(
                Channel.platform == platform,
                Channel.platform_channel_id == platform_channel_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_channels(
        self,
        db: AsyncSession,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[Channel]:
        """
        List all channels, optionally filtered.

        Args:
            db: Database session
            platform: Filter by platform ("youtube", "rumble")
            is_active: Filter by active status

        Returns:
            List of channels
        """
        query = select(Channel).order_by(Channel.name)

        if platform:
            query = query.where(Channel.platform == platform)
        if is_active is not None:
            query = query.where(Channel.is_active == is_active)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_channel(
        self,
        db: AsyncSession,
        channel_id: int,
        **kwargs,
    ) -> Optional[Channel]:
        """
        Update a channel.

        Args:
            db: Database session
            channel_id: Channel ID
            **kwargs: Fields to update

        Returns:
            Updated channel or None if not found
        """
        channel = await self.get_channel(db, channel_id)
        if not channel:
            return None

        for key, value in kwargs.items():
            if hasattr(channel, key) and value is not None:
                setattr(channel, key, value)

        await db.commit()
        await db.refresh(channel)
        return channel

    async def delete_channel(
        self,
        db: AsyncSession,
        channel_id: int,
    ) -> bool:
        """
        Delete a channel and all its feed items.

        Args:
            db: Database session
            channel_id: Channel ID

        Returns:
            True if deleted, False if not found
        """
        channel = await self.get_channel(db, channel_id)
        if not channel:
            return False

        await db.delete(channel)
        await db.commit()
        logger.info(f"Deleted channel: {channel.name}")
        return True

    async def _fetch_channel_metadata(
        self,
        url: str,
        platform: Platform,
    ) -> dict:
        """
        Fetch channel metadata from the platform.

        Args:
            url: Channel URL
            platform: Platform enum

        Returns:
            Dict with channel metadata
        """
        if platform == Platform.YOUTUBE:
            return await self._fetch_youtube_metadata(url)
        elif platform == Platform.RUMBLE:
            return await self._fetch_rumble_metadata(url)
        return {}

    async def _fetch_youtube_metadata(self, url: str) -> dict:
        """Fetch YouTube channel metadata using yt-dlp."""
        try:
            import yt_dlp

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'playlistend': 1,  # Just need channel info, not videos
            }

            loop = asyncio.get_event_loop()

            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await loop.run_in_executor(None, extract)

            if not info:
                return {}

            return {
                "name": info.get("channel") or info.get("uploader") or info.get("title"),
                "description": info.get("description"),
                "avatar_url": self._get_best_thumbnail(info),
                "subscriber_count": info.get("channel_follower_count"),
            }

        except Exception as e:
            logger.warning(f"Failed to fetch YouTube metadata for {url}: {e}")
            return {}

    async def _fetch_rumble_metadata(self, url: str) -> dict:
        """Fetch Rumble channel metadata by scraping."""
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30, follow_redirects=True)
                if response.status_code != 200:
                    return {}

                soup = BeautifulSoup(response.text, 'lxml')

                # Extract channel name
                name = None
                name_elem = soup.select_one('h1.channel-header--title')
                if name_elem:
                    name = name_elem.get_text(strip=True)

                # Try other selectors
                if not name:
                    name_elem = soup.select_one('.channel-header--title-wrapper h1')
                    if name_elem:
                        name = name_elem.get_text(strip=True)

                # Extract avatar
                avatar_url = None
                avatar_elem = soup.select_one('.channel-header--thumb img')
                if avatar_elem:
                    avatar_url = avatar_elem.get('src')

                # Extract subscriber count
                subscriber_count = None
                sub_elem = soup.select_one('.channel-header--followers')
                if sub_elem:
                    text = sub_elem.get_text(strip=True)
                    subscriber_count = self._parse_subscriber_count(text)

                return {
                    "name": name,
                    "avatar_url": avatar_url,
                    "subscriber_count": subscriber_count,
                }

        except Exception as e:
            logger.warning(f"Failed to fetch Rumble metadata for {url}: {e}")
            return {}

    def _get_best_thumbnail(self, info: dict) -> Optional[str]:
        """Get best thumbnail URL from yt-dlp info."""
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            # Sort by preference or width
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda t: t.get("preference", 0) or t.get("width", 0),
                reverse=True
            )
            return sorted_thumbs[0].get("url")
        return info.get("thumbnail")

    def _parse_subscriber_count(self, text: str) -> Optional[int]:
        """Parse subscriber count from text like '1.2M followers'."""
        import re
        text = text.lower().replace(',', '')
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

    def _normalize_channel_url(
        self,
        url: str,
        platform: Platform,
        channel_id: str,
    ) -> str:
        """Normalize channel URL to a canonical form."""
        if platform == Platform.YOUTUBE:
            # Prefer @handle format if it looks like a handle
            if channel_id.startswith('UC'):
                return f"https://www.youtube.com/channel/{channel_id}"
            return f"https://www.youtube.com/@{channel_id}"
        elif platform == Platform.RUMBLE:
            return f"https://rumble.com/c/{channel_id}"
        return url


# Global service instance
_channel_service: Optional[ChannelService] = None


def get_channel_service() -> ChannelService:
    """Get the channel service singleton."""
    global _channel_service
    if _channel_service is None:
        _channel_service = ChannelService()
    return _channel_service
