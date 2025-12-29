"""
Backfill service for updating legacy data with new fields.
"""
import asyncio
from typing import Optional
from loguru import logger
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feed_item import FeedItem


class BackfillService:
    """Service for backfilling missing data in legacy records."""

    async def backfill_redbar_video_urls(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> dict:
        """
        Backfill video_stream_url, audio_url, and content_type for Red Bar feed items.

        Fetches each episode page with authentication and extracts all media URLs.

        Args:
            db: Database session
            limit: Max episodes to process
            skip_existing: If True, only process episodes without video_stream_url
        """
        try:
            from app.core.platforms.redbar import RedBarPlatform
            from app.services.redbar_auth_service import get_redbar_auth_service
        except ImportError as e:
            return {"success": False, "error": f"Red Bar platform not available: {e}"}

        # Get auth cookies for premium content
        auth_service = get_redbar_auth_service()
        cookies = await auth_service.get_session_cookies(db)

        adapter = RedBarPlatform(session_cookies=cookies or {})

        updated = 0
        failed = 0
        skipped = 0

        # Build query
        if skip_existing:
            # Get items missing video_stream_url (not yet processed)
            query = select(FeedItem).where(
                FeedItem.platform == "redbar",
                FeedItem.video_stream_url.is_(None),
            ).order_by(FeedItem.upload_date.desc())
        else:
            # Get all redbar items (re-process everything)
            query = select(FeedItem).where(
                FeedItem.platform == "redbar",
            ).order_by(FeedItem.upload_date.desc())

        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        items = list(result.scalars().all())

        # Get total remaining for progress tracking
        remaining_query = select(func.count()).where(
            FeedItem.platform == "redbar",
            FeedItem.video_stream_url.is_(None),
        )
        remaining_result = await db.execute(remaining_query)
        total_remaining = remaining_result.scalar() or 0

        logger.info(f"Starting Red Bar backfill: {len(items)} to process, {total_remaining} remaining total")
        logger.info(f"Using auth cookies: {bool(cookies)}")

        for i, item in enumerate(items, 1):
            try:
                # Get video info from adapter (this fetches the page and extracts video URL)
                video_info = await adapter.get_video_info(item.video_url)

                if video_info:
                    has_updates = False

                    # Update video stream URL (HLS)
                    if video_info.video_stream_url:
                        item.video_stream_url = video_info.video_stream_url
                        has_updates = True

                    # Update audio URL (MP3 fallback)
                    if video_info.audio_url and not item.audio_url:
                        item.audio_url = video_info.audio_url
                        has_updates = True

                    # Set content type based on what we found
                    if video_info.video_stream_url:
                        item.content_type = "video"
                    elif video_info.audio_url:
                        item.content_type = "audio"
                    else:
                        item.content_type = None  # Unknown

                    if has_updates:
                        updated += 1
                        logger.info(f"[{i}/{len(items)}] Updated {item.video_id}: "
                                  f"video={bool(video_info.video_stream_url)}, "
                                  f"audio={bool(video_info.audio_url)}, "
                                  f"type={item.content_type}")
                    else:
                        skipped += 1
                        logger.debug(f"[{i}/{len(items)}] No URLs found for {item.video_id}")
                else:
                    skipped += 1
                    logger.debug(f"[{i}/{len(items)}] No video info for {item.video_id}")

                # Rate limit: 1 request per second
                await asyncio.sleep(1.0)

                # Commit every 10 items to save progress
                if i % 10 == 0:
                    await db.commit()
                    logger.info(f"Progress: {i}/{len(items)} processed, {updated} updated")

            except Exception as e:
                failed += 1
                logger.warning(f"[{i}/{len(items)}] Failed to backfill {item.video_id}: {e}")

        await db.commit()

        # Calculate new remaining count
        new_remaining_result = await db.execute(remaining_query)
        new_remaining = new_remaining_result.scalar() or 0

        logger.info(f"Red Bar backfill complete: {updated} updated, {skipped} skipped, {failed} failed")
        return {
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "processed": len(items),
            "remaining": new_remaining,
            "authenticated": bool(cookies),
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
        redbar_missing_result = await db.execute(
            select(func.count()).where(
                FeedItem.platform == "redbar",
                FeedItem.video_stream_url.is_(None),
            )
        )
        redbar_missing_count = redbar_missing_result.scalar() or 0

        # Count Red Bar by content type
        video_count_result = await db.execute(
            select(func.count()).where(
                FeedItem.platform == "redbar",
                FeedItem.content_type == "video",
            )
        )
        video_count = video_count_result.scalar() or 0

        audio_count_result = await db.execute(
            select(func.count()).where(
                FeedItem.platform == "redbar",
                FeedItem.content_type == "audio",
            )
        )
        audio_count = audio_count_result.scalar() or 0

        # Count podcast items missing audio_url
        podcast_missing_result = await db.execute(
            select(func.count()).where(
                FeedItem.platform == "podcast",
                FeedItem.audio_url.is_(None),
            )
        )
        podcast_missing_count = podcast_missing_result.scalar() or 0

        # Total counts by platform
        total_redbar_result = await db.execute(
            select(func.count()).where(FeedItem.platform == "redbar")
        )
        total_redbar_count = total_redbar_result.scalar() or 0

        total_podcast_result = await db.execute(
            select(func.count()).where(FeedItem.platform == "podcast")
        )
        total_podcast_count = total_podcast_result.scalar() or 0

        return {
            "redbar": {
                "total": total_redbar_count,
                "missing_video_stream_url": redbar_missing_count,
                "complete": total_redbar_count - redbar_missing_count,
                "video_content": video_count,
                "audio_content": audio_count,
            },
            "podcast": {
                "total": total_podcast_count,
                "missing_audio_url": podcast_missing_count,
                "complete": total_podcast_count - podcast_missing_count,
            },
        }


# Singleton instance
backfill_service = BackfillService()
