"""Playlist service - manages followed playlists."""

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Playlist
from app.core.platforms.registry import platform_registry


class PlaylistService:
    """Service for managing followed playlists."""

    async def follow_playlist(
        self,
        db: AsyncSession,
        platform: str,
        playlist_id: str,
        playlist_url: str,
        name: str,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        video_count: Optional[int] = None,
        channel_name: Optional[str] = None,
        channel_url: Optional[str] = None,
    ) -> Playlist:
        """
        Follow a playlist.

        If the playlist is already followed, returns the existing one.
        """
        # Check if playlist already followed
        existing = await self.get_by_platform_playlist_id(db, platform, playlist_id)
        if existing:
            logger.info(f"Playlist already followed: {existing.name}")
            return existing

        # Create playlist
        playlist = Playlist(
            platform=platform,
            playlist_id=playlist_id,
            playlist_url=playlist_url,
            name=name,
            description=description,
            thumbnail_url=thumbnail_url,
            video_count=video_count,
            channel_name=channel_name,
            channel_url=channel_url,
        )

        db.add(playlist)
        await db.commit()
        await db.refresh(playlist)

        logger.info(f"Followed playlist: {playlist.name} ({platform})")
        return playlist

    async def follow_from_url(
        self,
        db: AsyncSession,
        url: str,
    ) -> Playlist:
        """
        Follow a playlist by URL, auto-fetching metadata.

        Args:
            db: Database session
            url: Playlist URL

        Returns:
            Created Playlist

        Raises:
            ValueError: If URL is invalid or platform not supported
        """
        # Detect platform from URL
        platform_adapter = None
        for adapter in platform_registry.get_all_adapters():
            if self._matches_platform_url(url, adapter.platform_id):
                if adapter.supports_playlists:
                    platform_adapter = adapter
                    break

        if not platform_adapter:
            raise ValueError(f"Could not detect playlist platform for URL: {url}")

        # Fetch playlist info using the platform adapter
        try:
            playlist_info = await platform_adapter.get_playlist_info(url)
        except Exception as e:
            logger.error(f"Failed to fetch playlist info from {url}: {e}")
            raise ValueError(f"Failed to fetch playlist info: {str(e)}")

        # Follow the playlist
        return await self.follow_playlist(
            db=db,
            platform=playlist_info.platform,
            playlist_id=playlist_info.playlist_id,
            playlist_url=playlist_info.playlist_url,
            name=playlist_info.name,
            description=playlist_info.description,
            thumbnail_url=playlist_info.thumbnail_url,
            video_count=playlist_info.video_count,
            channel_name=playlist_info.channel_name,
            channel_url=playlist_info.channel_url,
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

    async def get_playlist(
        self,
        db: AsyncSession,
        playlist_id: int,
    ) -> Optional[Playlist]:
        """Get a playlist by ID."""
        result = await db.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        return result.scalar_one_or_none()

    async def get_by_platform_playlist_id(
        self,
        db: AsyncSession,
        platform: str,
        playlist_id: str,
    ) -> Optional[Playlist]:
        """Get a playlist by platform and playlist ID."""
        result = await db.execute(
            select(Playlist).where(
                Playlist.platform == platform,
                Playlist.playlist_id == playlist_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_playlists(
        self,
        db: AsyncSession,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[Playlist]:
        """
        List all playlists, optionally filtered.

        Args:
            db: Database session
            platform: Filter by platform
            is_active: Filter by active status

        Returns:
            List of playlists
        """
        query = select(Playlist).order_by(Playlist.name)

        if platform:
            query = query.where(Playlist.platform == platform)
        if is_active is not None:
            query = query.where(Playlist.is_active == is_active)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_playlist(
        self,
        db: AsyncSession,
        playlist_id: int,
        **kwargs,
    ) -> Optional[Playlist]:
        """Update a playlist."""
        playlist = await self.get_playlist(db, playlist_id)
        if not playlist:
            return None

        for key, value in kwargs.items():
            if hasattr(playlist, key) and value is not None:
                setattr(playlist, key, value)

        await db.commit()
        await db.refresh(playlist)
        return playlist

    async def delete_playlist(
        self,
        db: AsyncSession,
        playlist_id: int,
    ) -> bool:
        """Delete/unfollow a playlist."""
        playlist = await self.get_playlist(db, playlist_id)
        if not playlist:
            return False

        await db.delete(playlist)
        await db.commit()
        logger.info(f"Unfollowed playlist: {playlist.name}")
        return True

    async def sync_playlist(
        self,
        db: AsyncSession,
        playlist: Playlist,
    ) -> dict:
        """
        Sync a playlist's videos to the feed.

        Returns:
            Dict with sync result
        """
        try:
            # Get platform adapter
            adapter = platform_registry.get_adapter(playlist.platform)
            if not adapter or not adapter.supports_playlists:
                return {
                    "success": False,
                    "new_videos": 0,
                    "error": f"Platform {playlist.platform} does not support playlists",
                }

            # Fetch playlist videos
            videos = await adapter.get_playlist_videos(
                playlist.playlist_url,
                max_results=50,
            )

            # Update playlist metadata
            playlist.last_synced_at = datetime.utcnow()
            playlist.last_sync_error = None
            playlist.consecutive_errors = 0
            playlist.video_count = len(videos)

            await db.commit()

            return {
                "success": True,
                "new_videos": len(videos),
                "error": None,
            }

        except Exception as e:
            logger.error(f"Failed to sync playlist {playlist.name}: {e}")

            playlist.last_synced_at = datetime.utcnow()
            playlist.last_sync_error = str(e)
            playlist.consecutive_errors += 1

            await db.commit()

            return {
                "success": False,
                "new_videos": 0,
                "error": str(e),
            }

    async def get_stats(
        self,
        db: AsyncSession,
    ) -> dict:
        """Get statistics for playlists."""
        # Total count
        total_result = await db.execute(
            select(func.count()).select_from(Playlist)
        )
        total = total_result.scalar() or 0

        # Active count
        active_result = await db.execute(
            select(func.count()).select_from(Playlist).where(Playlist.is_active == True)
        )
        active = active_result.scalar() or 0

        # By platform
        platform_result = await db.execute(
            select(Playlist.platform, func.count())
            .group_by(Playlist.platform)
        )
        by_platform = {row[0]: row[1] for row in platform_result.all()}

        return {
            "total_playlists": total,
            "active_playlists": active,
            "inactive_playlists": total - active,
            "by_platform": by_platform,
        }


# Global service instance
_playlist_service: Optional[PlaylistService] = None


def get_playlist_service() -> PlaylistService:
    """Get the playlist service singleton."""
    global _playlist_service
    if _playlist_service is None:
        _playlist_service = PlaylistService()
    return _playlist_service
