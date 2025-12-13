"""Video platform adapters for federated search."""

from app.core.platforms.base import (
    PlatformAdapter,
    VideoResult,
    ChannelResult,
    PlaylistResult,
)
from app.core.platforms.registry import (
    PlatformRegistry,
    get_platform,
    get_all_platforms,
    detect_platform_from_url,
)

__all__ = [
    # Base classes
    "PlatformAdapter",
    "VideoResult",
    "ChannelResult",
    "PlaylistResult",
    # Registry
    "PlatformRegistry",
    "get_platform",
    "get_all_platforms",
    "detect_platform_from_url",
]
