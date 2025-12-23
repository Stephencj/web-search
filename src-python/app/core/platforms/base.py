"""Base classes for video platform adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class VideoResult:
    """Unified video result from any platform."""

    platform: str
    video_id: str
    video_url: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    upload_date: Optional[datetime] = None
    channel_name: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    channel_avatar_url: Optional[str] = None
    like_count: Optional[int] = None
    tags: list[str] = field(default_factory=list)
    # Podcast/audio specific fields
    audio_url: Optional[str] = None  # Direct audio file URL (from RSS enclosure)
    audio_file_size: Optional[int] = None  # Size in bytes
    audio_mime_type: Optional[str] = None  # e.g., 'audio/mpeg'
    # Video stream URL (for platforms with separate video files)
    video_stream_url: Optional[str] = None  # Direct video file URL

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "platform": self.platform,
            "video_id": self.video_id,
            "video_url": self.video_url,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "view_count": self.view_count,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "channel_name": self.channel_name,
            "channel_id": self.channel_id,
            "channel_url": self.channel_url,
            "channel_avatar_url": self.channel_avatar_url,
            "like_count": self.like_count,
            "tags": self.tags,
            "audio_url": self.audio_url,
            "audio_file_size": self.audio_file_size,
            "audio_mime_type": self.audio_mime_type,
            "video_stream_url": self.video_stream_url,
        }


@dataclass
class ChannelResult:
    """Unified channel result from any platform."""

    platform: str
    channel_id: str
    channel_url: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "platform": self.platform,
            "channel_id": self.channel_id,
            "channel_url": self.channel_url,
            "name": self.name,
            "description": self.description,
            "avatar_url": self.avatar_url,
            "banner_url": self.banner_url,
            "subscriber_count": self.subscriber_count,
            "video_count": self.video_count,
        }


@dataclass
class PlaylistResult:
    """Unified playlist result from any platform."""

    platform: str
    playlist_id: str
    playlist_url: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_count: Optional[int] = None
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "platform": self.platform,
            "playlist_id": self.playlist_id,
            "playlist_url": self.playlist_url,
            "name": self.name,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "video_count": self.video_count,
            "channel_name": self.channel_name,
            "channel_url": self.channel_url,
        }


class PlatformAdapter(ABC):
    """
    Base class for video platform adapters.

    Each platform adapter provides a unified interface for:
    - Searching videos and channels
    - Getting video/channel metadata
    - Listing channel videos
    """

    platform_id: str  # e.g., "youtube", "rumble"
    platform_name: str  # e.g., "YouTube", "Rumble"
    platform_icon: str = ""  # Emoji or icon identifier
    platform_color: str = "#000000"  # Hex color for UI

    # Feature flags
    supports_search: bool = True
    supports_channel_feed: bool = True
    supports_playlists: bool = False

    @abstractmethod
    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """
        Search for videos on this platform.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of VideoResult objects
        """
        pass

    @abstractmethod
    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """
        Search for channels on this platform.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of ChannelResult objects
        """
        pass

    @abstractmethod
    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """
        Get videos from a channel.

        Args:
            channel_url: Full channel URL
            max_results: Maximum number of videos to return
            since: Only get videos after this date

        Returns:
            List of VideoResult objects
        """
        pass

    @abstractmethod
    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """
        Get channel metadata.

        Args:
            channel_url: Full channel URL

        Returns:
            ChannelResult or None if not found
        """
        pass

    @abstractmethod
    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """
        Get single video metadata.

        Args:
            video_url: Full video URL

        Returns:
            VideoResult or None if not found
        """
        pass

    async def search_playlists(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[PlaylistResult]:
        """
        Search for playlists on this platform.

        Default implementation raises NotImplementedError.
        Override in platforms that support playlists.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of PlaylistResult objects
        """
        raise NotImplementedError(f"{self.platform_name} does not support playlist search")

    async def get_playlist_videos(
        self,
        playlist_url: str,
        max_results: int = 100,
    ) -> list[VideoResult]:
        """
        Get videos from a playlist.

        Default implementation raises NotImplementedError.
        Override in platforms that support playlists.

        Args:
            playlist_url: Full playlist URL
            max_results: Maximum number of videos to return

        Returns:
            List of VideoResult objects
        """
        raise NotImplementedError(f"{self.platform_name} does not support playlists")

    def can_handle_url(self, url: str) -> bool:
        """
        Check if this adapter can handle the given URL.

        Default implementation checks for platform domain.
        Override for more specific URL handling.

        Args:
            url: URL to check

        Returns:
            True if this adapter can handle the URL
        """
        return False

    def get_platform_info(self) -> dict:
        """Get platform metadata for API responses."""
        return {
            "id": self.platform_id,
            "name": self.platform_name,
            "icon": self.platform_icon,
            "color": self.platform_color,
            "supports_search": self.supports_search,
            "supports_channel_feed": self.supports_channel_feed,
            "supports_playlists": self.supports_playlists,
        }
