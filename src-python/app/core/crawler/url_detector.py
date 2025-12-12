"""URL detection utilities for routing to appropriate crawlers."""

import re
from enum import Enum
from urllib.parse import urlparse, parse_qs

from app.core.crawler.youtube_types import YouTubeUrlType


# YouTube hostname patterns
YOUTUBE_HOSTS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'youtu.be',
    'www.youtu.be',
}

# Rumble hostname patterns
RUMBLE_HOSTS = {
    'rumble.com',
    'www.rumble.com',
}


class Platform(Enum):
    """Supported video platforms."""
    YOUTUBE = "youtube"
    RUMBLE = "rumble"
    UNKNOWN = "unknown"


def is_youtube_url(url: str) -> bool:
    """
    Check if URL is a YouTube URL that should use yt-dlp.

    Args:
        url: URL to check

    Returns:
        True if URL is a YouTube URL
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in YOUTUBE_HOSTS
    except Exception:
        return False


def get_youtube_url_type(url: str) -> YouTubeUrlType:
    """
    Determine the type of YouTube URL.

    Args:
        url: YouTube URL to analyze

    Returns:
        YouTubeUrlType indicating the URL type

    URL patterns:
    - Channel: youtube.com/@handle, youtube.com/channel/UCXXX, youtube.com/c/name, youtube.com/user/name
    - Playlist: youtube.com/playlist?list=PLXXX
    - Video: youtube.com/watch?v=XXX, youtu.be/XXX
    - Search: youtube.com/results?search_query=XXX
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parse_qs(parsed.query)

        # Check for youtu.be short URLs (always videos)
        if parsed.netloc.lower() in ('youtu.be', 'www.youtu.be'):
            return YouTubeUrlType.VIDEO

        # Check for playlist
        if 'list' in query and path in ('/playlist', '/watch'):
            # If it's just a playlist URL (not a video in a playlist)
            if path == '/playlist':
                return YouTubeUrlType.PLAYLIST
            # Video with playlist context - treat as playlist to get all videos
            if 'v' not in query:
                return YouTubeUrlType.PLAYLIST

        # Check for video
        if path == '/watch' and 'v' in query:
            return YouTubeUrlType.VIDEO

        # Check for search results
        if path == '/results' and 'search_query' in query:
            return YouTubeUrlType.SEARCH

        # Check for channel patterns
        if re.match(r'^/@[\w.-]+', path):
            return YouTubeUrlType.CHANNEL
        if path.startswith('/channel/'):
            return YouTubeUrlType.CHANNEL
        if path.startswith('/c/'):
            return YouTubeUrlType.CHANNEL
        if path.startswith('/user/'):
            return YouTubeUrlType.CHANNEL

        # Check for embedded video
        if path.startswith('/embed/'):
            return YouTubeUrlType.VIDEO

        # Check for shorts
        if path.startswith('/shorts/'):
            return YouTubeUrlType.VIDEO

        return YouTubeUrlType.UNKNOWN

    except Exception:
        return YouTubeUrlType.UNKNOWN


def extract_video_id(url: str) -> str | None:
    """
    Extract video ID from a YouTube video URL.

    Args:
        url: YouTube video URL

    Returns:
        Video ID or None if not found
    """
    try:
        parsed = urlparse(url)

        # youtu.be/VIDEO_ID
        if parsed.netloc.lower() in ('youtu.be', 'www.youtu.be'):
            return parsed.path.lstrip('/')

        # youtube.com/watch?v=VIDEO_ID
        if parsed.path == '/watch':
            query = parse_qs(parsed.query)
            if 'v' in query:
                return query['v'][0]

        # youtube.com/embed/VIDEO_ID
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/')[2]

        # youtube.com/shorts/VIDEO_ID
        if parsed.path.startswith('/shorts/'):
            return parsed.path.split('/')[2]

        return None

    except Exception:
        return None


# ==================== RUMBLE URL DETECTION ====================

def is_rumble_url(url: str) -> bool:
    """
    Check if URL is a Rumble URL.

    Args:
        url: URL to check

    Returns:
        True if URL is a Rumble URL
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in RUMBLE_HOSTS
    except Exception:
        return False


def is_rumble_channel_url(url: str) -> bool:
    """
    Check if URL is a Rumble channel/user URL.

    Args:
        url: URL to check

    Returns:
        True if URL is a Rumble channel URL

    URL patterns:
    - rumble.com/c/channelname
    - rumble.com/user/username
    """
    try:
        parsed = urlparse(url)
        if parsed.netloc.lower() not in RUMBLE_HOSTS:
            return False

        path = parsed.path.lower()
        return path.startswith('/c/') or path.startswith('/user/')
    except Exception:
        return False


def extract_rumble_channel_id(url: str) -> str | None:
    """
    Extract channel/user ID from a Rumble channel URL.

    Args:
        url: Rumble channel URL

    Returns:
        Channel ID or None if not found
    """
    try:
        parsed = urlparse(url)
        path = parsed.path

        # rumble.com/c/channelname
        if path.lower().startswith('/c/'):
            parts = path.split('/')
            if len(parts) >= 3:
                return parts[2]

        # rumble.com/user/username
        if path.lower().startswith('/user/'):
            parts = path.split('/')
            if len(parts) >= 3:
                return parts[2]

        return None
    except Exception:
        return None


# ==================== PLATFORM DETECTION ====================

def detect_platform(url: str) -> Platform:
    """
    Detect which video platform a URL belongs to.

    Args:
        url: URL to check

    Returns:
        Platform enum value
    """
    if is_youtube_url(url):
        return Platform.YOUTUBE
    if is_rumble_url(url):
        return Platform.RUMBLE
    return Platform.UNKNOWN


def extract_youtube_channel_id(url: str) -> str | None:
    """
    Extract channel ID from a YouTube channel URL.

    Args:
        url: YouTube channel URL

    Returns:
        Channel ID or handle, or None if not found
    """
    try:
        parsed = urlparse(url)
        path = parsed.path

        # youtube.com/@handle
        if path.startswith('/@'):
            return path[2:].split('/')[0]

        # youtube.com/channel/UCXXXX
        if path.startswith('/channel/'):
            parts = path.split('/')
            if len(parts) >= 3:
                return parts[2]

        # youtube.com/c/channelname
        if path.startswith('/c/'):
            parts = path.split('/')
            if len(parts) >= 3:
                return parts[2]

        # youtube.com/user/username
        if path.startswith('/user/'):
            parts = path.split('/')
            if len(parts) >= 3:
                return parts[2]

        return None
    except Exception:
        return None


def detect_channel_info(url: str) -> tuple[Platform, str | None]:
    """
    Detect platform and extract channel ID from a URL.

    Args:
        url: Channel URL

    Returns:
        Tuple of (Platform, channel_id or None)
    """
    platform = detect_platform(url)

    if platform == Platform.YOUTUBE:
        return platform, extract_youtube_channel_id(url)
    elif platform == Platform.RUMBLE:
        return platform, extract_rumble_channel_id(url)
    else:
        return platform, None
