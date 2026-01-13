"""Feed sync service - syncs videos from subscribed channels."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
            elif channel.platform == "redbar":
                result = await self._sync_redbar_channel(db, channel)
            elif channel.platform == "podcast":
                result = await self._sync_podcast_channel(db, channel)
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
        parallel: bool = False,
        max_concurrent: int = 3,
    ) -> list[dict]:
        """
        Sync all active channels.

        Args:
            db: Database session
            platform: Optional platform filter
            parallel: If True, sync multiple channels concurrently
            max_concurrent: Max concurrent syncs when parallel=True

        Returns:
            List of sync results
        """
        # Get active channels
        query = select(Channel).where(Channel.is_active == True)
        if platform:
            query = query.where(Channel.platform == platform)

        result = await db.execute(query)
        channels = list(result.scalars().all())

        logger.info(f"Syncing {len(channels)} channels (parallel={parallel})")

        # Filter and handle channels with too many errors
        active_channels = []
        results = []

        for channel in channels:
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
            else:
                active_channels.append(channel)

        if parallel and len(active_channels) > 1:
            # Parallel sync with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def sync_with_semaphore(ch: Channel) -> dict:
                async with semaphore:
                    sync_result = await self.sync_channel(db, ch)
                    return {
                        "channel_id": ch.id,
                        "channel_name": ch.name,
                        **sync_result,
                    }

            # Run all syncs concurrently (limited by semaphore)
            parallel_results = await asyncio.gather(
                *[sync_with_semaphore(ch) for ch in active_channels],
                return_exceptions=True
            )

            for i, res in enumerate(parallel_results):
                if isinstance(res, Exception):
                    results.append({
                        "channel_id": active_channels[i].id,
                        "channel_name": active_channels[i].name,
                        "success": False,
                        "error": str(res),
                        "new_videos": 0,
                    })
                else:
                    results.append(res)
        else:
            # Sequential sync with reduced delay
            for channel in active_channels:
                sync_result = await self.sync_channel(db, channel)
                results.append({
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    **sync_result,
                })

                # Reduced rate limiting between channels (0.3s instead of 1s)
                if len(active_channels) > 1:
                    await asyncio.sleep(0.3)

        return results

    async def _sync_youtube_channel(
        self,
        db: AsyncSession,
        channel: Channel,
    ) -> dict:
        """Sync a YouTube channel using yt-dlp with fast flat extraction."""
        import yt_dlp

        new_videos = 0
        skipped = 0
        new_video_ids = []  # Track new videos for category fetching

        try:
            # Use flat extraction - much faster, gets basic metadata without full video extraction
            channel_url = channel.channel_url.rstrip('/')
            if not any(channel_url.endswith(tab) for tab in ['/videos', '/shorts', '/streams', '/playlists']):
                channel_url = f"{channel_url}/videos"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'skip_download': True,
                'ignoreerrors': True,
                'playlistend': 100,  # Get up to 100 recent videos
            }

            loop = asyncio.get_event_loop()

            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(channel_url, download=False)

            info = await loop.run_in_executor(None, extract)

            if not info or 'entries' not in info:
                logger.warning(f"No videos found for channel {channel.name}")
                return {"success": True, "new_videos": 0, "skipped": 0}

            for entry in info.get('entries', []):
                if entry is None:
                    continue

                video_id = entry.get('id')
                if not video_id:
                    continue

                # Check if video already exists
                existing = await self._get_existing_feed_item(db, "youtube", video_id)
                if existing:
                    skipped += 1
                    continue

                # Parse upload date from flat extraction
                upload_date_str = entry.get('upload_date')
                upload_date = self._parse_upload_date(upload_date_str)

                # If flat extraction didn't provide a date, fetch it accurately
                if upload_date is None:
                    upload_date = await self._fetch_youtube_video_date(video_id)
                    if upload_date is None:
                        # Still no date - skip this video to avoid inaccurate feed
                        logger.warning(f"Skipping YouTube video {video_id} - no upload date available")
                        skipped += 1
                        continue

                # Skip very old videos on first sync
                if not channel.last_synced_at:
                    if upload_date < datetime.utcnow() - timedelta(days=30):
                        skipped += 1
                        continue

                # Get thumbnail - flat extraction may have it
                thumbnail_url = entry.get('thumbnail')
                if not thumbnail_url:
                    # Fallback to standard YouTube thumbnail
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

                # Create feed item from flat extraction data
                feed_item = FeedItem(
                    channel_id=channel.id,
                    platform="youtube",
                    video_id=video_id,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    title=entry.get('title', 'Untitled'),
                    description=None,  # Not available in flat extraction
                    thumbnail_url=thumbnail_url,
                    duration_seconds=entry.get('duration'),
                    view_count=entry.get('view_count'),
                    upload_date=upload_date,
                )

                try:
                    # Use savepoint to handle potential duplicates without killing the whole transaction
                    async with db.begin_nested():
                        db.add(feed_item)
                        await db.flush()
                    new_videos += 1
                    new_video_ids.append(video_id)  # Track for category fetching
                except IntegrityError:
                    # Video already exists (race condition or duplicate) - savepoint rolled back automatically
                    skipped += 1
                    continue

                # Commit in batches
                if new_videos % 20 == 0:
                    await db.commit()

                # Limit new videos per sync
                if new_videos >= 50:
                    break

            await db.commit()

            # Fetch full metadata for new videos (categories, accurate dates, descriptions)
            if new_video_ids:
                await self._fetch_and_update_metadata(db, new_video_ids[:20])  # Limit batch size

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

                # Get upload date - skip video if not available
                upload_date = video.get("upload_date")
                if upload_date is None:
                    logger.warning(f"Skipping Rumble video {video['video_id']} - no upload date available")
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
                    upload_date=upload_date,
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

    async def _sync_redbar_channel(
        self,
        db: AsyncSession,
        channel: Channel,
    ) -> dict:
        """Sync Red Bar Radio episodes using platform adapter with authentication."""
        try:
            from app.core.platforms.redbar import RedBarPlatform
            from app.services.redbar_auth_service import get_redbar_auth_service
        except ImportError as e:
            return {"success": False, "error": f"Red Bar modules not available: {e}", "new_videos": 0}

        new_videos = 0
        skipped = 0

        try:
            # Get session cookies for authenticated access
            auth_service = get_redbar_auth_service()
            cookies = await auth_service.get_session_cookies(db)

            # Create adapter with cookies
            adapter = RedBarPlatform(session_cookies=cookies or {})

            # Red Bar has infrequent episodes (sometimes months apart)
            # For first sync, don't filter by date to get full archive
            # For subsequent syncs, use a 1-year lookback
            if channel.last_synced_at:
                since = channel.last_synced_at - timedelta(days=7)  # Small buffer
            else:
                since = None  # First sync: get all available episodes

            # Get channel videos (since=None means no date filter)
            # Red Bar has 1800+ episodes going back to early 2000s
            videos = await adapter.get_channel_videos(
                channel.channel_url,
                max_results=2000,  # Get full archive
                since=since,
            )

            for video in videos:
                # Check if video already exists
                existing = await self._get_existing_feed_item(
                    db, "redbar", video.video_id
                )
                if existing:
                    skipped += 1
                    continue

                # Get upload date - use discovered_at if not available
                upload_date = video.upload_date or datetime.utcnow()

                # For NEW episodes, fetch individual page to get video/audio URLs
                # The list page doesn't have these URLs - they're on individual episode pages
                video_stream_url = video.video_stream_url
                audio_url = video.audio_url
                content_type = None

                if not video_stream_url and not audio_url:
                    try:
                        # Fetch full episode info (includes video/audio URLs)
                        full_info = await adapter.get_video_info(video.video_url)
                        if full_info:
                            video_stream_url = full_info.video_stream_url
                            audio_url = full_info.audio_url
                            # Set content type based on what we found
                            if video_stream_url:
                                content_type = "video"
                            elif audio_url:
                                content_type = "audio"

                        # Rate limit between individual page fetches
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to fetch full info for {video.video_id}: {e}")

                # Create feed item
                feed_item = FeedItem(
                    channel_id=channel.id,
                    platform="redbar",
                    video_id=video.video_id,
                    video_url=video.video_url,
                    title=video.title,
                    description=video.description,
                    thumbnail_url=video.thumbnail_url,
                    duration_seconds=video.duration_seconds,
                    view_count=video.view_count,
                    upload_date=upload_date,
                    # Audio URL for MP3 playback
                    audio_url=audio_url,
                    # Video stream URL for HLS playback
                    video_stream_url=video_stream_url,
                    # Content type
                    content_type=content_type,
                )

                db.add(feed_item)
                new_videos += 1

            await db.commit()

            logger.info(f"Red Bar sync complete for {channel.name}: {new_videos} new, {skipped} skipped")
            return {"success": True, "new_videos": new_videos, "skipped": skipped}

        except Exception as e:
            logger.warning(f"Red Bar sync error for {channel.name}: {e}")
            return {"success": False, "error": str(e), "new_videos": new_videos}

    async def _sync_podcast_channel(
        self,
        db: AsyncSession,
        channel: Channel,
    ) -> dict:
        """Sync a podcast channel using RSS feed via platform adapter."""
        try:
            from app.core.platforms.podcast import PodcastPlatform
        except ImportError as e:
            return {"success": False, "error": f"Podcast platform not available: {e}", "new_videos": 0}

        new_videos = 0
        skipped = 0

        try:
            adapter = PodcastPlatform()

            # Get episodes since last sync (or last 90 days for new channels)
            since = channel.last_synced_at or (datetime.utcnow() - timedelta(days=90))

            # Get channel videos (episodes)
            episodes = await adapter.get_channel_videos(
                channel.channel_url,
                max_results=50,
                since=since,
            )

            for episode in episodes:
                # Check if episode already exists
                existing = await self._get_existing_feed_item(
                    db, "podcast", episode.video_id
                )
                if existing:
                    skipped += 1
                    continue

                # Get upload date - skip episode if not available
                if episode.upload_date is None:
                    logger.warning(f"Skipping podcast episode {episode.video_id} - no upload date available")
                    skipped += 1
                    continue

                # Create feed item
                feed_item = FeedItem(
                    channel_id=channel.id,
                    platform="podcast",
                    video_id=episode.video_id,
                    video_url=episode.video_url,
                    title=episode.title,
                    description=episode.description,
                    thumbnail_url=episode.thumbnail_url,
                    duration_seconds=episode.duration_seconds,
                    view_count=episode.view_count,
                    upload_date=episode.upload_date,
                    # Audio-specific fields from RSS enclosure
                    audio_url=episode.audio_url,
                    audio_file_size=episode.audio_file_size,
                    audio_mime_type=episode.audio_mime_type,
                )

                db.add(feed_item)
                new_videos += 1

            await db.commit()

            logger.info(f"Podcast sync complete for {channel.name}: {new_videos} new, {skipped} skipped")
            return {"success": True, "new_videos": new_videos, "skipped": skipped}

        except Exception as e:
            logger.warning(f"Podcast sync error for {channel.name}: {e}")
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

    def _parse_upload_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse upload date from yt-dlp format (YYYYMMDD).

        Returns None if date cannot be parsed - caller should handle missing dates
        appropriately (fetch accurate date or skip the video).
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except (ValueError, TypeError):
            return None

    async def _fetch_youtube_video_date(self, video_id: str) -> Optional[datetime]:
        """Fetch accurate upload date for a YouTube video using full extraction.

        This is slower than flat extraction but provides accurate dates.
        Used as fallback when flat extraction doesn't include upload_date.
        """
        import yt_dlp

        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': False,
            }

            loop = asyncio.get_event_loop()

            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await loop.run_in_executor(None, extract)

            if info and 'upload_date' in info:
                return self._parse_upload_date(info['upload_date'])

        except Exception as e:
            logger.warning(f"Failed to fetch date for YouTube video {video_id}: {e}")

        return None

    async def _fetch_and_update_metadata(
        self,
        db: AsyncSession,
        video_ids: list[str],
    ) -> None:
        """
        Fetch full metadata for YouTube videos and update the database.

        This fetches categories (for mood-based filtering) and accurate upload dates
        (flat extraction often lacks these). Called after main sync to avoid slowing
        down the primary sync process.
        """
        import yt_dlp

        if not video_ids:
            return

        logger.info(f"Fetching metadata for {len(video_ids)} new videos")
        loop = asyncio.get_event_loop()

        for video_id in video_ids:
            try:
                url = f"https://www.youtube.com/watch?v={video_id}"

                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'extract_flat': False,  # Need full extraction for metadata
                }

                def extract():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(url, download=False)

                info = await loop.run_in_executor(None, extract)

                if info:
                    # Update the feed item with full metadata
                    result = await db.execute(
                        select(FeedItem).where(
                            FeedItem.platform == "youtube",
                            FeedItem.video_id == video_id,
                        )
                    )
                    feed_item = result.scalar_one_or_none()

                    if feed_item:
                        updated_fields = []

                        # Update categories if available
                        if 'categories' in info and info['categories']:
                            feed_item.categories = info['categories']
                            updated_fields.append('categories')

                        # Update upload_date if available (more accurate than flat extraction)
                        if 'upload_date' in info and info['upload_date']:
                            accurate_date = self._parse_upload_date(info['upload_date'])
                            feed_item.upload_date = accurate_date
                            updated_fields.append('upload_date')

                        # Update description if available
                        if 'description' in info and info['description']:
                            feed_item.description = info['description'][:2000]  # Limit length
                            updated_fields.append('description')

                        # Update like_count if available
                        if 'like_count' in info and info['like_count']:
                            feed_item.like_count = info['like_count']
                            updated_fields.append('like_count')

                        # Update tags if available (limit to 50 tags)
                        if 'tags' in info and info['tags']:
                            feed_item.tags = info['tags'][:50]
                            updated_fields.append('tags')

                        if updated_fields:
                            await db.commit()
                            logger.debug(f"Updated {video_id}: {', '.join(updated_fields)}")

            except Exception as e:
                logger.warning(f"Failed to fetch metadata for {video_id}: {e}")

            # Rate limiting between requests to avoid getting blocked
            await asyncio.sleep(0.3)

        logger.info(f"Metadata fetching complete for {len(video_ids)} videos")


# Global service instance
_feed_sync_service: Optional[FeedSyncService] = None


def get_feed_sync_service() -> FeedSyncService:
    """Get the feed sync service singleton."""
    global _feed_sync_service
    if _feed_sync_service is None:
        _feed_sync_service = FeedSyncService()
    return _feed_sync_service
