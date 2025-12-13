"""Feed sync service - syncs videos from subscribed channels."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.crawler.youtube import YouTubeExtractor
from app.models import Channel, FeedItem


class FeedSyncService:
    """Service for syncing videos from subscribed channels."""

    def __init__(self):
        self.settings = get_settings()

    async def sync_channel(
        self,
        db: AsyncSession,
        channel: Channel,
    ) -> dict:
        """
        Sync a single channel to fetch new videos.

        Args:
            db: Database session
            channel: Channel to sync

        Returns:
            Dict with success status and counts
        """
        logger.info(f"Syncing channel: {channel.name} ({channel.platform})")

        try:
            if channel.platform == "youtube":
                result = await self._sync_youtube_channel(db, channel)
            elif channel.platform == "rumble":
                result = await self._sync_rumble_channel(db, channel)
            else:
                result = {"success": False, "error": f"Unknown platform: {channel.platform}"}

            if result.get("success"):
                channel.mark_sync_success()
            else:
                channel.mark_sync_error(result.get("error", "Unknown error"))

            await db.commit()
            return result

        except Exception as e:
            logger.exception(f"Failed to sync channel {channel.name}: {e}")
            channel.mark_sync_error(str(e))
            await db.commit()
            return {"success": False, "error": str(e), "new_videos": 0}

    async def sync_all_channels(
        self,
        db: AsyncSession,
        platform: Optional[str] = None,
    ) -> list[dict]:
        """
        Sync all active channels.

        Args:
            db: Database session
            platform: Optional platform filter

        Returns:
            List of sync results
        """
        # Get active channels
        query = select(Channel).where(Channel.is_active == True)
        if platform:
            query = query.where(Channel.platform == platform)

        result = await db.execute(query)
        channels = list(result.scalars().all())

        logger.info(f"Syncing {len(channels)} channels")

        results = []
        for channel in channels:
            # Deactivate channels with too many consecutive errors
            if channel.consecutive_errors >= 5:
                logger.warning(
                    f"Deactivating channel {channel.name} due to {channel.consecutive_errors} consecutive errors. "
                    f"Last error: {channel.last_sync_error}"
                )
                channel.is_active = False
                await db.commit()
                results.append({
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "success": False,
                    "error": f"Deactivated after {channel.consecutive_errors} consecutive errors",
                    "new_videos": 0,
                })
                continue

            sync_result = await self.sync_channel(db, channel)
            results.append({
                "channel_id": channel.id,
                "channel_name": channel.name,
                **sync_result,
            })

            # Rate limiting between channels
            await asyncio.sleep(1.0)

        return results

    async def _sync_youtube_channel(
        self,
        db: AsyncSession,
        channel: Channel,
    ) -> dict:
        """Sync a YouTube channel using yt-dlp."""
        settings = self.settings

        extractor = YouTubeExtractor(
            max_videos=settings.crawler.youtube_max_videos_per_source,
            fetch_transcripts=False,  # Skip transcripts for feed sync (faster)
            rate_limit_delay=settings.crawler.youtube_rate_limit_delay_ms / 1000.0,
        )

        new_videos = 0
        skipped = 0

        try:
            async for video in extractor.extract(channel.channel_url):
                # Check if video already exists
                existing = await self._get_existing_feed_item(
                    db, "youtube", video.video_id
                )
                if existing:
                    skipped += 1
                    continue

                # Parse upload date
                upload_date = self._parse_upload_date(video.upload_date)

                # Skip very old videos on first sync
                if not channel.last_synced_at:
                    # On first sync, only get videos from last 30 days
                    if upload_date < datetime.utcnow() - timedelta(days=30):
                        skipped += 1
                        continue

                # Create feed item
                feed_item = FeedItem(
                    channel_id=channel.id,
                    platform="youtube",
                    video_id=video.video_id,
                    video_url=video.video_url,
                    title=video.title,
                    description=video.description[:1000] if video.description else None,
                    thumbnail_url=video.thumbnail_url,
                    duration_seconds=video.duration_seconds,
                    view_count=video.view_count,
                    upload_date=upload_date,
                )

                db.add(feed_item)
                new_videos += 1

                # Commit in batches
                if new_videos % 10 == 0:
                    await db.commit()

                # Limit new videos per sync
                if new_videos >= 50:
                    break

            await db.commit()

            logger.info(f"YouTube sync complete for {channel.name}: {new_videos} new, {skipped} skipped")
            return {"success": True, "new_videos": new_videos, "skipped": skipped}

        except Exception as e:
            logger.warning(f"YouTube sync error for {channel.name}: {e}")
            return {"success": False, "error": str(e), "new_videos": new_videos}

    async def _sync_rumble_channel(
        self,
        db: AsyncSession,
        channel: Channel,
    ) -> dict:
        """Sync a Rumble channel using RSS/scraping."""
        # Import Rumble extractor when needed
        try:
            from app.core.crawler.rumble import RumbleExtractor
        except ImportError:
            return {"success": False, "error": "Rumble extractor not available", "new_videos": 0}

        extractor = RumbleExtractor()
        new_videos = 0
        skipped = 0

        try:
            # Get videos since last sync (or last 30 days for new channels)
            since = channel.last_synced_at or (datetime.utcnow() - timedelta(days=30))

            async for video in extractor.get_videos(channel.channel_url, since=since):
                # Check if video already exists
                existing = await self._get_existing_feed_item(
                    db, "rumble", video["video_id"]
                )
                if existing:
                    skipped += 1
                    continue

                # Create feed item
                feed_item = FeedItem(
                    channel_id=channel.id,
                    platform="rumble",
                    video_id=video["video_id"],
                    video_url=video["video_url"],
                    title=video["title"],
                    description=video.get("description"),
                    thumbnail_url=video.get("thumbnail_url"),
                    duration_seconds=video.get("duration_seconds"),
                    view_count=video.get("view_count"),
                    upload_date=video.get("upload_date", datetime.utcnow()),
                )

                db.add(feed_item)
                new_videos += 1

                # Limit new videos per sync
                if new_videos >= 50:
                    break

            await db.commit()

            logger.info(f"Rumble sync complete for {channel.name}: {new_videos} new, {skipped} skipped")
            return {"success": True, "new_videos": new_videos, "skipped": skipped}

        except Exception as e:
            logger.warning(f"Rumble sync error for {channel.name}: {e}")
            return {"success": False, "error": str(e), "new_videos": new_videos}

    async def _get_existing_feed_item(
        self,
        db: AsyncSession,
        platform: str,
        video_id: str,
    ) -> Optional[FeedItem]:
        """Check if a feed item already exists."""
        result = await db.execute(
            select(FeedItem).where(
                FeedItem.platform == platform,
                FeedItem.video_id == video_id,
            )
        )
        return result.scalar_one_or_none()

    def _parse_upload_date(self, date_str: Optional[str]) -> datetime:
        """Parse upload date from yt-dlp format (YYYYMMDD)."""
        if not date_str:
            return datetime.utcnow()

        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except (ValueError, TypeError):
            return datetime.utcnow()


# Global service instance
_feed_sync_service: Optional[FeedSyncService] = None


def get_feed_sync_service() -> FeedSyncService:
    """Get the feed sync service singleton."""
    global _feed_sync_service
    if _feed_sync_service is None:
        _feed_sync_service = FeedSyncService()
    return _feed_sync_service
