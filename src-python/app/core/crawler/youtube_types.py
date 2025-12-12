"""Type definitions for YouTube crawling."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class YouTubeUrlType(Enum):
    """Types of YouTube URLs that can be crawled."""
    VIDEO = "video"
    PLAYLIST = "playlist"
    CHANNEL = "channel"
    SEARCH = "search"
    UNKNOWN = "unknown"


@dataclass
class YouTubeVideoResult:
    """Extended video info for YouTube content."""
    # Required fields
    video_url: str
    video_id: str
    title: str

    # Optional metadata
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    upload_date: Optional[str] = None  # YYYYMMDD format from yt-dlp

    # Channel info
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None
    channel_id: Optional[str] = None

    # Transcript
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None

    # Tags and categories
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class YouTubeCrawlStats:
    """Statistics for YouTube crawl."""
    videos_found: int = 0
    videos_indexed: int = 0
    videos_with_transcript: int = 0
    videos_failed: int = 0
