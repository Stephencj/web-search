"""
Backfill service for updating legacy data with new fields.
"""
import asyncio
from typing import Optional
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feed_item import FeedItem


class BackfillService:
    """Service for backfilling missing data in legacy records."""

    async def backfill_redbar_video_urls(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Backfill video_stream_url for Red Bar feed items.

        Fetches each episode page and extracts the direct video URL.
        """
        try:
            from app.core.platforms.redbar import RedBarPlatform
        except ImportError as e:
            return {"success": False, "error": f"Red Bar platform not available: {e}"}

        adapter = RedBarPlatform()
        updated = 0
        failed = 0
        skipped = 0

        # Get Red Bar items missing video_stream_url
        query = select(FeedItem).where(
            FeedItem.platform == "redbar",
            FeedItem.video_stream_url.is_(None),
        )
        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        logger.info(f"Found {len(items)} Red Bar items to backfill")

        for item in items:
            try:
                # Get video info from adapter (this fetches the page and extracts video URL)
                video_info = await adapter.get_video_info(item.video_url)

                if video_info and video_info.video_stream_url:
                    item.video_stream_url = video_info.video_stream_url
                    updated += 1
                    logger.debug(f"Updated {item.video_id}: {video_info.video_stream_url[:50]}...")
                else:
                    skipped += 1
                    logger.debug(f"No video URL found for {item.video_id}")

                # Small delay to avoid hammering the server
                await asyncio.sleep(0.5)

            except Exception as e:
                failed += 1
                logger.warning(f"Failed to backfill {item.video_id}: {e}")

        await db.commit()

        logger.info(f"Red Bar backfill complete: {updated} updated, {skipped} skipped, {failed} failed")
        return {
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "total": len(items),
        }

    async def backfill_podcast_audio_fields(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Backfill audio fields for podcast feed items.

        Re-fetches RSS feeds and updates items missing audio_url by matching video_id.
        """
        try:
            from app.core.platforms.podcast import PodcastPlatform
            from app.models.channel import Channel
        except ImportError as e:
            return {"success": False, "error": f"Podcast platform not available: {e}"}

        adapter = PodcastPlatform()
        updated = 0
        failed = 0
        skipped = 0

        # Get all podcast channels
        channel_query = select(Channel).where(Channel.platform == "podcast")
        channel_result = await db.execute(channel_query)
        channels = channel_result.scalars().all()

        logger.info(f"Found {len(channels)} podcast channels to process")

        for channel in channels:
            try:
                # Get all episodes from RSS feed (channel_url contains RSS feed URL for podcasts)
                episodes = await adapter.get_channel_videos(
                    channel.channel_url,
                )

                # Create lookup by video_id
                episode_map = {ep.video_id: ep for ep in episodes}

                # Get items for this channel missing audio_url
                items_query = select(FeedItem).where(
                    FeedItem.channel_id == channel.id,
                    FeedItem.audio_url.is_(None),
                )
                if limit:
                    items_query = items_query.limit(limit)

                items_result = await db.execute(items_query)
                items = items_result.scalars().all()

                for item in items:
                    if item.video_id in episode_map:
                        ep = episode_map[item.video_id]
                        if ep.audio_url:
                            item.audio_url = ep.audio_url
                            item.audio_file_size = ep.audio_file_size
                            item.audio_mime_type = ep.audio_mime_type
                            updated += 1
                            logger.debug(f"Updated podcast {item.video_id}")
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                        logger.debug(f"Episode {item.video_id} not found in RSS")

                await asyncio.sleep(1)  # Rate limit between channels

            except Exception as e:
                failed += 1
                logger.warning(f"Failed to backfill channel {channel.name}: {e}")

        await db.commit()

        total = updated + skipped + failed
        logger.info(f"Podcast backfill complete: {updated} updated, {skipped} skipped, {failed} failed")
        return {
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "total": total,
            "channels_processed": len(channels),
        }

    async def get_backfill_status(self, db: AsyncSession) -> dict:
        """Get current backfill status showing missing data counts."""

        # Count Red Bar items missing video_stream_url
        redbar_missing = await db.execute(
            select(FeedItem).where(
                FeedItem.platform == "redbar",
                FeedItem.video_stream_url.is_(None),
            )
        )
        redbar_missing_count = len(redbar_missing.scalars().all())

        # Count podcast items missing audio_url
        podcast_missing = await db.execute(
            select(FeedItem).where(
                FeedItem.platform == "podcast",
                FeedItem.audio_url.is_(None),
            )
        )
        podcast_missing_count = len(podcast_missing.scalars().all())

        # Total counts by platform
        total_redbar = await db.execute(
            select(FeedItem).where(FeedItem.platform == "redbar")
        )
        total_redbar_count = len(total_redbar.scalars().all())

        total_podcast = await db.execute(
            select(FeedItem).where(FeedItem.platform == "podcast")
        )
        total_podcast_count = len(total_podcast.scalars().all())

        return {
            "redbar": {
                "total": total_redbar_count,
                "missing_video_stream_url": redbar_missing_count,
                "complete": total_redbar_count - redbar_missing_count,
            },
            "podcast": {
                "total": total_podcast_count,
                "missing_audio_url": podcast_missing_count,
                "complete": total_podcast_count - podcast_missing_count,
            },
        }


# Singleton instance
backfill_service = BackfillService()
