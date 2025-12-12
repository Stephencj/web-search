"""Async web crawler engine."""

import asyncio
import fnmatch
import gzip
import hashlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse, urljoin

import httpx
from aiolimiter import AsyncLimiter
from loguru import logger

from app.config import get_settings
from app.core.crawler.extractor import ContentExtractor, ExtractedContent
from app.core.crawler.robots import RobotsChecker
from app.core.crawler.dedup import SimHashDedup


@dataclass
class CrawlResult:
    """Result of crawling a single page."""
    url: str
    status_code: int
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)  # List of image info dicts
    videos: list[dict] = field(default_factory=list)  # List of video info dicts
    content_hash: Optional[str] = None
    word_count: int = 0
    published_date: Optional[str] = None
    raw_html_path: Optional[str] = None
    error: Optional[str] = None
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    is_duplicate: bool = False


@dataclass
class CrawlStats:
    """Statistics for a crawl session."""
    pages_crawled: int = 0
    pages_indexed: int = 0
    pages_skipped: int = 0
    pages_failed: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None


class CrawlerEngine:
    """Async web crawler with politeness controls."""

    def __init__(
        self,
        source_url: str,
        source_id: int,
        crawl_depth: int = 2,
        max_pages: int = 1000,
        include_patterns: Optional[list[str]] = None,
        exclude_patterns: Optional[list[str]] = None,
        respect_robots: bool = True,
        on_page_crawled: Optional[Callable[[CrawlResult], None]] = None,
    ):
        self.source_url = source_url
        self.source_id = source_id
        self.crawl_depth = crawl_depth
        self.max_pages = max_pages
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.respect_robots = respect_robots
        self.on_page_crawled = on_page_crawled

        # Get settings
        settings = get_settings()
        self.user_agent = settings.crawler.user_agent
        self.concurrent_requests = settings.crawler.concurrent_requests
        self.request_delay_ms = settings.crawler.request_delay_ms
        self.timeout_seconds = settings.crawler.timeout_seconds
        self.max_retries = settings.crawler.max_retries
        self.raw_html_enabled = settings.crawler.raw_html_enabled
        self.data_dir = settings.data_dir

        # Rate limiter: requests per second based on delay
        requests_per_second = 1000 / self.request_delay_ms
        self.rate_limiter = AsyncLimiter(requests_per_second, 1)

        # Components
        self.extractor = ContentExtractor()
        self.dedup = SimHashDedup()
        self.robots = RobotsChecker(self.user_agent) if respect_robots else None

        # State
        self.visited: set[str] = set()
        self.queue: deque[tuple[str, int]] = deque()  # (url, depth)
        self.stats = CrawlStats()
        self._cancelled = False

        # Parse source domain for filtering
        parsed = urlparse(source_url)
        self.source_domain = parsed.netloc

    async def crawl(self) -> CrawlStats:
        """
        Execute the crawl.

        Returns crawl statistics.
        """
        logger.info(f"Starting crawl of {self.source_url}")
        self.stats = CrawlStats()
        self._cancelled = False

        # Initialize queue with starting URL
        self.queue.append((self.source_url, 0))

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent}
        ) as client:
            tasks: list[asyncio.Task] = []

            while (self.queue or tasks) and not self._cancelled:
                # Check if we've hit max pages
                if self.stats.pages_crawled >= self.max_pages:
                    logger.info(f"Reached max pages limit ({self.max_pages})")
                    break

                # Fill task pool
                while (
                    self.queue
                    and len(tasks) < self.concurrent_requests
                    and self.stats.pages_crawled + len(tasks) < self.max_pages
                ):
                    url, depth = self.queue.popleft()

                    if url in self.visited:
                        continue

                    if depth > self.crawl_depth:
                        continue

                    self.visited.add(url)
                    task = asyncio.create_task(
                        self._crawl_page(client, url, depth)
                    )
                    tasks.append(task)

                if tasks:
                    # Wait for at least one task to complete
                    done, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    tasks = list(pending)

                    for task in done:
                        try:
                            result, new_urls, depth = task.result()
                            self.stats.pages_crawled += 1

                            if result.error:
                                self.stats.pages_failed += 1
                            elif result.is_duplicate:
                                self.stats.pages_skipped += 1
                            else:
                                self.stats.pages_indexed += 1

                                # Add discovered URLs to queue
                                for new_url in new_urls:
                                    if self._should_crawl(new_url):
                                        self.queue.append((new_url, depth + 1))

                            # Callback for each page
                            if self.on_page_crawled:
                                self.on_page_crawled(result)

                        except Exception as e:
                            logger.error(f"Task error: {e}")
                            self.stats.pages_failed += 1

        # Cancel remaining tasks if we're stopping
        for task in tasks:
            task.cancel()

        self.stats.end_time = datetime.utcnow()
        logger.info(
            f"Crawl complete: {self.stats.pages_indexed} indexed, "
            f"{self.stats.pages_skipped} skipped, "
            f"{self.stats.pages_failed} failed"
        )

        return self.stats

    def cancel(self) -> None:
        """Cancel the crawl."""
        self._cancelled = True

    async def _crawl_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        depth: int
    ) -> tuple[CrawlResult, list[str], int]:
        """Crawl a single page."""

        # Check robots.txt
        if self.robots:
            try:
                allowed = await self.robots.can_fetch(url)
                if not allowed:
                    logger.debug(f"Blocked by robots.txt: {url}")
                    return CrawlResult(
                        url=url,
                        status_code=0,
                        error="Blocked by robots.txt"
                    ), [], depth
            except Exception as e:
                logger.warning(f"Error checking robots.txt: {e}")

        # Rate limiting
        async with self.rate_limiter:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url)
                    break
                except httpx.TimeoutException:
                    if attempt == self.max_retries - 1:
                        return CrawlResult(
                            url=url,
                            status_code=0,
                            error="Timeout"
                        ), [], depth
                    await asyncio.sleep(1)
                except Exception as e:
                    return CrawlResult(
                        url=url,
                        status_code=0,
                        error=str(e)
                    ), [], depth

        # Check status code
        if response.status_code != 200:
            return CrawlResult(
                url=url,
                status_code=response.status_code,
                error=f"HTTP {response.status_code}"
            ), [], depth

        # Check content type
        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type.lower():
            return CrawlResult(
                url=url,
                status_code=response.status_code,
                error=f"Not HTML: {content_type}"
            ), [], depth

        html = response.text

        # Extract content
        extracted = self.extractor.extract(html, url)

        # Check for duplicates
        content_hash = self.dedup.compute_hash(extracted.content)
        is_duplicate = self.dedup.is_duplicate(extracted.content, url)

        # Save raw HTML if enabled
        raw_html_path = None
        if self.raw_html_enabled and not is_duplicate:
            raw_html_path = await self._save_raw_html(url, html)

        # Resolve relative URLs
        links = [urljoin(url, link) for link in extracted.links]

        # Convert images to dicts
        images = [
            {
                "src": img.src,
                "alt": img.alt,
                "title": img.title,
            }
            for img in extracted.images
        ]

        # Convert videos to dicts
        videos = [
            {
                "video_url": vid.video_url,
                "thumbnail_url": vid.thumbnail_url,
                "embed_type": vid.embed_type,
                "video_id": vid.video_id,
                "title": vid.title,
            }
            for vid in extracted.videos
        ]

        result = CrawlResult(
            url=url,
            status_code=200,
            title=extracted.title,
            description=extracted.description,
            content=extracted.content,
            headings=extracted.headings,
            links=links,
            images=images,
            videos=videos,
            content_hash=content_hash,
            word_count=extracted.word_count,
            published_date=extracted.published_date,
            raw_html_path=raw_html_path,
            is_duplicate=is_duplicate,
        )

        return result, links, depth

    def _should_crawl(self, url: str) -> bool:
        """Check if URL should be crawled based on patterns."""
        if url in self.visited:
            return False

        parsed = urlparse(url)

        # Must be same domain
        if parsed.netloc != self.source_domain:
            return False

        # Must be http/https
        if parsed.scheme not in ('http', 'https'):
            return False

        path = parsed.path

        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False

        # Check include patterns (if any)
        if self.include_patterns:
            return any(
                fnmatch.fnmatch(path, pattern)
                for pattern in self.include_patterns
            )

        return True

    async def _save_raw_html(self, url: str, html: str) -> Optional[str]:
        """Save raw HTML to disk."""
        try:
            # Create unique filename from URL hash
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            filename = f"{self.source_id}_{url_hash}.html.gz"

            raw_dir = self.data_dir / "raw_html"
            raw_dir.mkdir(parents=True, exist_ok=True)
            filepath = raw_dir / filename

            # Compress and save
            compressed = gzip.compress(html.encode('utf-8'))
            filepath.write_bytes(compressed)

            return str(filepath)

        except Exception as e:
            logger.warning(f"Failed to save raw HTML: {e}")
            return None
