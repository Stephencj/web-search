"""robots.txt parser and checker."""

import asyncio
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsChecker:
    """Check if URLs are allowed by robots.txt."""

    def __init__(self, user_agent: str = "WebSearch/1.0"):
        self.user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}
        self._lock = asyncio.Lock()

    async def can_fetch(self, url: str) -> bool:
        """Check if the URL can be fetched according to robots.txt."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        parser = await self._get_parser(robots_url)
        if parser is None:
            return True  # Allow if robots.txt can't be fetched

        return parser.can_fetch(self.user_agent, url)

    async def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get crawl delay from robots.txt if specified."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        parser = await self._get_parser(robots_url)
        if parser is None:
            return None

        delay = parser.crawl_delay(self.user_agent)
        return float(delay) if delay else None

    async def _get_parser(self, robots_url: str) -> Optional[RobotFileParser]:
        """Get or fetch robots.txt parser for a domain."""
        async with self._lock:
            if robots_url in self._cache:
                return self._cache[robots_url]

            parser = await self._fetch_robots(robots_url)
            self._cache[robots_url] = parser
            return parser

    async def _fetch_robots(self, robots_url: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)

                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                    return parser
                elif response.status_code in (404, 403):
                    # No robots.txt or forbidden - allow everything
                    return None
                else:
                    return None

        except Exception:
            # On error, allow crawling
            return None

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
