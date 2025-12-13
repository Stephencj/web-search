"""Federated search service for querying multiple video platforms."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from loguru import logger

from app.core.platforms import (
    PlatformRegistry,
    VideoResult,
    ChannelResult,
    PlaylistResult,
)


@dataclass
class SearchTimings:
    """Timing information for each platform."""

    platform: str
    duration_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class FederatedSearchResult:
    """Result from federated search across platforms."""

    query: str
    search_type: str  # "videos", "channels", "playlists"
    total_results: int
    results: list[VideoResult | ChannelResult | PlaylistResult]
    by_platform: dict[str, list[VideoResult | ChannelResult | PlaylistResult]]
    timings: list[SearchTimings]
    total_duration_ms: int
    platforms_searched: list[str]
    platforms_failed: list[str] = field(default_factory=list)


class FederatedSearchService:
    """
    Service for federated search across multiple video platforms.

    Features:
    - Parallel search across all platforms
    - Per-platform timeouts
    - Result merging and deduplication
    - Graceful degradation on platform failures
    """

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_results_per_platform: int = 20,
    ):
        """
        Initialize federated search service.

        Args:
            timeout_seconds: Timeout for each platform search
            max_results_per_platform: Max results to fetch from each platform
        """
        self.timeout_seconds = timeout_seconds
        self.max_results_per_platform = max_results_per_platform

    async def search_videos(
        self,
        query: str,
        platforms: Optional[list[str]] = None,
        max_per_platform: Optional[int] = None,
    ) -> FederatedSearchResult:
        """
        Search for videos across multiple platforms.

        Args:
            query: Search query string
            platforms: List of platform IDs to search (None = all)
            max_per_platform: Max results per platform (None = default)

        Returns:
            FederatedSearchResult with merged results
        """
        return await self._search(
            query=query,
            search_type="videos",
            platforms=platforms,
            max_per_platform=max_per_platform,
        )

    async def search_channels(
        self,
        query: str,
        platforms: Optional[list[str]] = None,
        max_per_platform: Optional[int] = None,
    ) -> FederatedSearchResult:
        """
        Search for channels across multiple platforms.

        Args:
            query: Search query string
            platforms: List of platform IDs to search (None = all)
            max_per_platform: Max results per platform (None = default)

        Returns:
            FederatedSearchResult with merged results
        """
        return await self._search(
            query=query,
            search_type="channels",
            platforms=platforms,
            max_per_platform=max_per_platform,
        )

    async def search_playlists(
        self,
        query: str,
        platforms: Optional[list[str]] = None,
        max_per_platform: Optional[int] = None,
    ) -> FederatedSearchResult:
        """
        Search for playlists across multiple platforms.

        Args:
            query: Search query string
            platforms: List of platform IDs to search (None = all)
            max_per_platform: Max results per platform (None = default)

        Returns:
            FederatedSearchResult with merged results
        """
        return await self._search(
            query=query,
            search_type="playlists",
            platforms=platforms,
            max_per_platform=max_per_platform,
        )

    async def _search(
        self,
        query: str,
        search_type: str,
        platforms: Optional[list[str]] = None,
        max_per_platform: Optional[int] = None,
    ) -> FederatedSearchResult:
        """
        Internal search implementation.

        Args:
            query: Search query
            search_type: Type of search ("videos", "channels", "playlists")
            platforms: Platforms to search
            max_per_platform: Max results per platform

        Returns:
            FederatedSearchResult
        """
        start_time = datetime.utcnow()
        max_results = max_per_platform or self.max_results_per_platform

        # Get adapters to search
        if platforms:
            adapters = [
                PlatformRegistry.get(p) for p in platforms if PlatformRegistry.get(p)
            ]
        else:
            adapters = PlatformRegistry.searchable()

        if not adapters:
            return FederatedSearchResult(
                query=query,
                search_type=search_type,
                total_results=0,
                results=[],
                by_platform={},
                timings=[],
                total_duration_ms=0,
                platforms_searched=[],
            )

        # Create search tasks
        async def search_platform(adapter):
            platform_start = datetime.utcnow()
            platform_id = adapter.platform_id

            try:
                if search_type == "videos":
                    results = await asyncio.wait_for(
                        adapter.search_videos(query, max_results),
                        timeout=self.timeout_seconds,
                    )
                elif search_type == "channels":
                    results = await asyncio.wait_for(
                        adapter.search_channels(query, max_results),
                        timeout=self.timeout_seconds,
                    )
                elif search_type == "playlists":
                    if not adapter.supports_playlists:
                        return platform_id, [], SearchTimings(
                            platform=platform_id,
                            duration_ms=0,
                            success=True,
                            error="Platform does not support playlists",
                        )
                    results = await asyncio.wait_for(
                        adapter.search_playlists(query, max_results),
                        timeout=self.timeout_seconds,
                    )
                else:
                    results = []

                duration_ms = int(
                    (datetime.utcnow() - platform_start).total_seconds() * 1000
                )

                return platform_id, results, SearchTimings(
                    platform=platform_id,
                    duration_ms=duration_ms,
                    success=True,
                )

            except asyncio.TimeoutError:
                duration_ms = int(
                    (datetime.utcnow() - platform_start).total_seconds() * 1000
                )
                logger.warning(f"Search timeout for {platform_id}")
                return platform_id, [], SearchTimings(
                    platform=platform_id,
                    duration_ms=duration_ms,
                    success=False,
                    error="Timeout",
                )

            except Exception as e:
                duration_ms = int(
                    (datetime.utcnow() - platform_start).total_seconds() * 1000
                )
                logger.error(f"Search error for {platform_id}: {e}")
                return platform_id, [], SearchTimings(
                    platform=platform_id,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                )

        # Run all searches in parallel
        tasks = [search_platform(adapter) for adapter in adapters]
        results = await asyncio.gather(*tasks)

        # Merge results
        all_results = []
        by_platform = {}
        timings = []
        platforms_searched = []
        platforms_failed = []

        for platform_id, platform_results, timing in results:
            platforms_searched.append(platform_id)
            timings.append(timing)

            if timing.success and platform_results:
                by_platform[platform_id] = platform_results
                all_results.extend(platform_results)
            elif not timing.success:
                platforms_failed.append(platform_id)
                by_platform[platform_id] = []

        # Sort merged results by relevance (for now, just interleave platforms)
        # Future: implement proper relevance scoring
        merged_results = self._interleave_results(by_platform)

        total_duration_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        return FederatedSearchResult(
            query=query,
            search_type=search_type,
            total_results=len(merged_results),
            results=merged_results,
            by_platform=by_platform,
            timings=timings,
            total_duration_ms=total_duration_ms,
            platforms_searched=platforms_searched,
            platforms_failed=platforms_failed,
        )

    def _interleave_results(
        self, by_platform: dict[str, list]
    ) -> list:
        """
        Interleave results from different platforms.

        This ensures results from all platforms are visible early,
        rather than showing all of one platform first.

        Args:
            by_platform: Results grouped by platform

        Returns:
            Interleaved list of results
        """
        if not by_platform:
            return []

        # Create iterators for each platform
        iterators = {
            platform: iter(results) for platform, results in by_platform.items() if results
        }

        if not iterators:
            return []

        merged = []
        platform_order = list(iterators.keys())

        # Round-robin through platforms
        while iterators:
            for platform in platform_order[:]:
                if platform not in iterators:
                    continue

                try:
                    result = next(iterators[platform])
                    merged.append(result)
                except StopIteration:
                    del iterators[platform]
                    platform_order.remove(platform)

        return merged


# Singleton instance
_federated_search_service: Optional[FederatedSearchService] = None


def get_federated_search_service() -> FederatedSearchService:
    """Get the federated search service singleton."""
    global _federated_search_service
    if _federated_search_service is None:
        _federated_search_service = FederatedSearchService()
    return _federated_search_service
