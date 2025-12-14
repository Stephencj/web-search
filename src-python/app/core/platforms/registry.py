"""Platform adapter registry for managing video platform integrations."""

from typing import Optional

from loguru import logger

from app.core.platforms.base import PlatformAdapter


class PlatformRegistry:
    """
    Registry of all available platform adapters.

    Use this to get adapters by platform ID, list all available platforms,
    and detect which platform a URL belongs to.
    """

    _adapters: dict[str, PlatformAdapter] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, adapter: PlatformAdapter) -> None:
        """
        Register a platform adapter.

        Args:
            adapter: Platform adapter instance to register
        """
        cls._adapters[adapter.platform_id] = adapter
        logger.debug(f"Registered platform adapter: {adapter.platform_name}")

    @classmethod
    def unregister(cls, platform_id: str) -> None:
        """
        Unregister a platform adapter.

        Args:
            platform_id: Platform ID to unregister
        """
        if platform_id in cls._adapters:
            del cls._adapters[platform_id]

    @classmethod
    def get(cls, platform_id: str) -> Optional[PlatformAdapter]:
        """
        Get a platform adapter by ID.

        Args:
            platform_id: Platform identifier (e.g., "youtube", "rumble")

        Returns:
            Platform adapter or None if not found
        """
        cls._ensure_initialized()
        return cls._adapters.get(platform_id)

    @classmethod
    def all(cls) -> list[PlatformAdapter]:
        """
        Get all registered platform adapters.

        Returns:
            List of all platform adapters
        """
        cls._ensure_initialized()
        return list(cls._adapters.values())

    @classmethod
    def all_ids(cls) -> list[str]:
        """
        Get all registered platform IDs.

        Returns:
            List of platform IDs
        """
        cls._ensure_initialized()
        return list(cls._adapters.keys())

    @classmethod
    def searchable(cls) -> list[PlatformAdapter]:
        """
        Get all platform adapters that support search.

        Returns:
            List of searchable platform adapters
        """
        cls._ensure_initialized()
        return [a for a in cls._adapters.values() if a.supports_search]

    @classmethod
    def detect_platform(cls, url: str) -> Optional[PlatformAdapter]:
        """
        Detect which platform a URL belongs to.

        Args:
            url: URL to check

        Returns:
            Platform adapter that can handle the URL, or None
        """
        cls._ensure_initialized()
        for adapter in cls._adapters.values():
            if adapter.can_handle_url(url):
                return adapter
        return None

    @classmethod
    def get_platform_info(cls) -> list[dict]:
        """
        Get info for all platforms (for API responses).

        Returns:
            List of platform info dicts
        """
        cls._ensure_initialized()
        return [adapter.get_platform_info() for adapter in cls._adapters.values()]

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure all platform adapters are registered."""
        if cls._initialized:
            return

        cls._initialized = True

        # Import and register all platform adapters
        try:
            from app.core.platforms.youtube import YouTubePlatform
            cls.register(YouTubePlatform())
        except Exception as e:
            logger.warning(f"Failed to register YouTube platform: {e}")

        try:
            from app.core.platforms.rumble import RumblePlatform
            cls.register(RumblePlatform())
        except Exception as e:
            logger.warning(f"Failed to register Rumble platform: {e}")

        try:
            from app.core.platforms.odysee import OdyseePlatform
            cls.register(OdyseePlatform())
        except Exception as e:
            logger.warning(f"Failed to register Odysee platform: {e}")

        try:
            from app.core.platforms.bitchute import BitChutePlatform
            cls.register(BitChutePlatform())
        except Exception as e:
            logger.warning(f"Failed to register BitChute platform: {e}")

        try:
            from app.core.platforms.dailymotion import DailymotionPlatform
            cls.register(DailymotionPlatform())
        except Exception as e:
            logger.warning(f"Failed to register Dailymotion platform: {e}")

        try:
            from app.core.platforms.redbar import RedBarPlatform
            cls.register(RedBarPlatform())
        except Exception as e:
            logger.warning(f"Failed to register Red Bar platform: {e}")

        logger.info(f"Initialized {len(cls._adapters)} platform adapters")


# Convenience instance wrapper for simpler API
class PlatformRegistryInstance:
    """Wrapper to provide instance-like access to the registry."""

    def get_adapter(self, platform_id: str) -> Optional[PlatformAdapter]:
        """Get a platform adapter by ID."""
        return PlatformRegistry.get(platform_id)

    def get_all_adapters(self) -> list[PlatformAdapter]:
        """Get all registered platform adapters."""
        return PlatformRegistry.all()

    def detect_platform(self, url: str) -> Optional[PlatformAdapter]:
        """Detect which platform a URL belongs to."""
        return PlatformRegistry.detect_platform(url)

    def get_platform_info(self) -> list[dict]:
        """Get info for all platforms."""
        return PlatformRegistry.get_platform_info()


# Global instance for convenient access
platform_registry = PlatformRegistryInstance()


# Convenience functions
def get_platform(platform_id: str) -> Optional[PlatformAdapter]:
    """Get a platform adapter by ID."""
    return PlatformRegistry.get(platform_id)


def get_all_platforms() -> list[PlatformAdapter]:
    """Get all registered platform adapters."""
    return PlatformRegistry.all()


def detect_platform_from_url(url: str) -> Optional[PlatformAdapter]:
    """Detect which platform a URL belongs to."""
    return PlatformRegistry.detect_platform(url)
