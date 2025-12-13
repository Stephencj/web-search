"""SavedVideo service - manages bookmarked videos."""

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SavedVideo
from app.core.platforms.registry import platform_registry


class SavedVideoService:
    """Service for managing saved/bookmarked videos."""

    async def save_video(
        self,
        db: AsyncSession,
        platform: str,
        video_id: str,
        video_url: str,
        title: str,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        view_count: Optional[int] = None,
        upload_date: Optional[datetime] = None,
        channel_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        channel_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SavedVideo:
        """
        Save a video to bookmarks.

        If the video already exists, returns the existing one.
        """
        # Check if video already saved
        existing = await self.get_by_platform_video_id(db, platform, video_id)
        if existing:
            logger.info(f"Video already saved: {existing.title}")
            return existing

        # Create saved video
        saved_video = SavedVideo(
            platform=platform,
            video_id=video_id,
            video_url=video_url,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
            view_count=view_count,
            upload_date=upload_date,
            channel_name=channel_name,
            channel_id=channel_id,
            channel_url=channel_url,
            notes=notes,
        )

        db.add(saved_video)
        await db.commit()
        await db.refresh(saved_video)

        logger.info(f"Saved video: {saved_video.title} ({platform})")
        return saved_video

    async def save_from_url(
        self,
        db: AsyncSession,
        url: str,
        notes: Optional[str] = None,
    ) -> SavedVideo:
        """
        Save a video by URL, auto-fetching metadata.

        Args:
            db: Database session
            url: Video URL
            notes: Optional notes

        Returns:
            Created SavedVideo

        Raises:
            ValueError: If URL is invalid or platform not supported
        """
        # Detect platform from URL
        platform_adapter = None
        for adapter in platform_registry.get_all_adapters():
            # Simple URL pattern matching
            if adapter.platform_id in url.lower() or self._matches_platform_url(url, adapter.platform_id):
                platform_adapter = adapter
                break

        if not platform_adapter:
            raise ValueError(f"Could not detect platform for URL: {url}")

        # Fetch video info using the platform adapter
        try:
            video_info = await platform_adapter.get_video_info(url)
        except Exception as e:
            logger.error(f"Failed to fetch video info from {url}: {e}")
            raise ValueError(f"Failed to fetch video info: {str(e)}")

        # Save the video
        return await self.save_video(
            db=db,
            platform=video_info.platform,
            video_id=video_info.video_id,
            video_url=video_info.video_url,
            title=video_info.title,
            description=video_info.description,
            thumbnail_url=video_info.thumbnail_url,
            duration_seconds=video_info.duration_seconds,
            view_count=video_info.view_count,
            upload_date=video_info.upload_date,
            channel_name=video_info.channel_name,
            channel_id=video_info.channel_id,
            channel_url=video_info.channel_url,
            notes=notes,
        )

    def _matches_platform_url(self, url: str, platform_id: str) -> bool:
        """Check if URL matches a platform."""
        url_lower = url.lower()
        patterns = {
            "youtube": ["youtube.com", "youtu.be"],
            "rumble": ["rumble.com"],
            "odysee": ["odysee.com", "lbry.tv"],
            "bitchute": ["bitchute.com"],
            "dailymotion": ["dailymotion.com", "dai.ly"],
        }
        return any(p in url_lower for p in patterns.get(platform_id, []))

    async def get_saved_video(
        self,
        db: AsyncSession,
        video_id: int,
    ) -> Optional[SavedVideo]:
        """Get a saved video by ID."""
        result = await db.execute(
            select(SavedVideo).where(SavedVideo.id == video_id)
        )
        return result.scalar_one_or_none()

    async def get_by_platform_video_id(
        self,
        db: AsyncSession,
        platform: str,
        video_id: str,
    ) -> Optional[SavedVideo]:
        """Get a saved video by platform and video ID."""
        result = await db.execute(
            select(SavedVideo).where(
                SavedVideo.platform == platform,
                SavedVideo.video_id == video_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_saved_videos(
        self,
        db: AsyncSession,
        platform: Optional[str] = None,
        is_watched: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SavedVideo], int]:
        """
        List saved videos with filtering.

        Returns:
            Tuple of (videos, total_count)
        """
        query = select(SavedVideo).order_by(SavedVideo.saved_at.desc())
        count_query = select(func.count()).select_from(SavedVideo)

        if platform:
            query = query.where(SavedVideo.platform == platform)
            count_query = count_query.where(SavedVideo.platform == platform)

        if is_watched is not None:
            query = query.where(SavedVideo.is_watched == is_watched)
            count_query = count_query.where(SavedVideo.is_watched == is_watched)

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        videos = list(result.scalars().all())

        return videos, total

    async def update_saved_video(
        self,
        db: AsyncSession,
        video_id: int,
        **kwargs,
    ) -> Optional[SavedVideo]:
        """Update a saved video."""
        video = await self.get_saved_video(db, video_id)
        if not video:
            return None

        for key, value in kwargs.items():
            if hasattr(video, key) and value is not None:
                setattr(video, key, value)

        await db.commit()
        await db.refresh(video)
        return video

    async def mark_watched(
        self,
        db: AsyncSession,
        video_id: int,
        progress_seconds: Optional[int] = None,
    ) -> Optional[SavedVideo]:
        """Mark a saved video as watched."""
        video = await self.get_saved_video(db, video_id)
        if not video:
            return None

        video.mark_watched()
        if progress_seconds is not None:
            video.watch_progress_seconds = progress_seconds

        await db.commit()
        await db.refresh(video)
        return video

    async def mark_unwatched(
        self,
        db: AsyncSession,
        video_id: int,
    ) -> Optional[SavedVideo]:
        """Mark a saved video as unwatched."""
        video = await self.get_saved_video(db, video_id)
        if not video:
            return None

        video.mark_unwatched()
        await db.commit()
        await db.refresh(video)
        return video

    async def delete_saved_video(
        self,
        db: AsyncSession,
        video_id: int,
    ) -> bool:
        """Delete a saved video."""
        video = await self.get_saved_video(db, video_id)
        if not video:
            return False

        await db.delete(video)
        await db.commit()
        logger.info(f"Deleted saved video: {video.title}")
        return True

    async def get_stats(
        self,
        db: AsyncSession,
    ) -> dict:
        """Get statistics for saved videos."""
        # Total count
        total_result = await db.execute(
            select(func.count()).select_from(SavedVideo)
        )
        total = total_result.scalar() or 0

        # Watched count
        watched_result = await db.execute(
            select(func.count()).select_from(SavedVideo).where(SavedVideo.is_watched == True)
        )
        watched = watched_result.scalar() or 0

        # By platform
        platform_result = await db.execute(
            select(SavedVideo.platform, func.count())
            .group_by(SavedVideo.platform)
        )
        by_platform = {row[0]: row[1] for row in platform_result.all()}

        return {
            "total_videos": total,
            "watched_videos": watched,
            "unwatched_videos": total - watched,
            "by_platform": by_platform,
        }

    async def check_if_saved(
        self,
        db: AsyncSession,
        platform: str,
        video_id: str,
    ) -> bool:
        """Check if a video is already saved."""
        existing = await self.get_by_platform_video_id(db, platform, video_id)
        return existing is not None


# Global service instance
_saved_video_service: Optional[SavedVideoService] = None


def get_saved_video_service() -> SavedVideoService:
    """Get the saved video service singleton."""
    global _saved_video_service
    if _saved_video_service is None:
        _saved_video_service = SavedVideoService()
    return _saved_video_service
