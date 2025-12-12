"""Sync scheduler - manages automatic video feed syncing."""

import asyncio
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.config import get_settings


class SyncScheduler:
    """
    Manages scheduled sync jobs for video feed.

    Uses APScheduler for reliable interval-based scheduling.
    """

    def __init__(self):
        self.settings = get_settings()
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._is_running = False

    async def start(self) -> None:
        """Start the sync scheduler."""
        if self._is_running:
            logger.warning("Sync scheduler already running")
            return

        # Check if sync is enabled
        sync_settings = getattr(self.settings, 'sync', None)
        if sync_settings and not getattr(sync_settings, 'sync_enabled', True):
            logger.info("Sync scheduler disabled by configuration")
            return

        self.scheduler = AsyncIOScheduler()

        # Add hourly sync job
        self.scheduler.add_job(
            self._run_sync,
            trigger=IntervalTrigger(hours=1),
            id='hourly_sync',
            name='Hourly Feed Sync',
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True

        logger.info("Sync scheduler started - hourly sync enabled")

    async def shutdown(self) -> None:
        """Shutdown the sync scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Sync scheduler shut down")

    async def _run_sync(self) -> None:
        """Run the scheduled sync job."""
        logger.info("Running scheduled sync...")

        try:
            # Import here to avoid circular imports
            from app.database import get_async_session
            from app.services.feed_sync_service import get_feed_sync_service

            # Get a database session
            async with get_async_session() as db:
                service = get_feed_sync_service()
                results = await service.sync_all_channels(db)

                # Log summary
                success_count = sum(1 for r in results if r.get("success"))
                new_videos = sum(r.get("new_videos", 0) for r in results)

                logger.info(
                    f"Scheduled sync complete: {success_count}/{len(results)} channels synced, "
                    f"{new_videos} new videos found"
                )

        except Exception as e:
            logger.exception(f"Scheduled sync failed: {e}")

    async def trigger_manual_sync(self) -> None:
        """Trigger an immediate sync (outside of schedule)."""
        await self._run_sync()

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled sync time."""
        if not self.scheduler:
            return None

        job = self.scheduler.get_job('hourly_sync')
        if job:
            return job.next_run_time
        return None

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running


# Global scheduler instance
_sync_scheduler: Optional[SyncScheduler] = None


def get_sync_scheduler() -> SyncScheduler:
    """Get the sync scheduler singleton."""
    global _sync_scheduler
    if _sync_scheduler is None:
        _sync_scheduler = SyncScheduler()
    return _sync_scheduler
