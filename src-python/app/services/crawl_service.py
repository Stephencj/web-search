"""Crawl service - orchestrates crawling and indexing."""

import asyncio
import hashlib
from datetime import datetime
from typing import Optional, Callable

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.crawler.engine import CrawlerEngine, CrawlResult, CrawlStats
from app.core.search.meilisearch import get_meilisearch_client
from app.models import CrawlJob, Source, Index


def _should_index_text(crawl_mode: str) -> bool:
    """Check if text should be indexed based on crawl mode."""
    return crawl_mode in ("text_only", "text_images", "text_videos", "all")


def _should_index_images(crawl_mode: str) -> bool:
    """Check if images should be indexed based on crawl mode."""
    return crawl_mode in ("images_only", "text_images", "images_videos", "all")


def _should_index_videos(crawl_mode: str) -> bool:
    """Check if videos should be indexed based on crawl mode."""
    return crawl_mode in ("videos_only", "text_videos", "images_videos", "all")


class CrawlService:
    """Service for managing crawl operations."""

    def __init__(self):
        self.meilisearch = get_meilisearch_client()
        self._active_crawls: dict[int, CrawlerEngine] = {}  # job_id -> engine
        self._crawl_tasks: dict[int, asyncio.Task] = {}  # job_id -> task

    async def start_crawl(
        self,
        db: AsyncSession,
        job: CrawlJob,
        source: Source,
        index: Index,
        on_progress: Optional[Callable[[CrawlJob], None]] = None
    ) -> CrawlStats:
        """
        Start crawling a source and indexing results to Meilisearch.

        Args:
            db: Database session
            job: The crawl job record
            source: The source to crawl
            index: The index to add documents to
            on_progress: Optional callback for progress updates

        Returns:
            Final crawl statistics
        """
        logger.info(f"Starting crawl job {job.id} for source {source.url}")

        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        await db.commit()

        # Determine what to index based on crawl_mode
        crawl_mode = getattr(source, 'crawl_mode', 'all') or 'all'
        index_text = _should_index_text(crawl_mode)
        index_images = _should_index_images(crawl_mode)
        index_videos = _should_index_videos(crawl_mode)

        # Ensure Meilisearch indexes exist
        if index_text:
            await self.meilisearch.create_index(index.slug)
        if index_images:
            await self.meilisearch.create_images_index(index.slug)
        if index_videos:
            await self.meilisearch.create_videos_index(index.slug)

        # Create crawler engine
        engine = CrawlerEngine(
            source_url=source.url,
            source_id=source.id,
            crawl_depth=source.crawl_depth,
            max_pages=source.max_pages,
            include_patterns=source.include_patterns or [],
            exclude_patterns=source.exclude_patterns or [],
            respect_robots=source.respect_robots,
            on_page_crawled=lambda result: asyncio.create_task(
                self._handle_page_result(db, job, source, index, result)
            )
        )

        self._active_crawls[job.id] = engine

        try:
            # Run the crawl
            stats = await engine.crawl()

            # Update job with final stats
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.pages_crawled = stats.pages_crawled
            job.pages_indexed = stats.pages_indexed
            job.pages_skipped = stats.pages_skipped
            job.pages_failed = stats.pages_failed
            # duration_seconds is computed from started_at and completed_at

            # Update source stats
            source.last_crawl_at = datetime.utcnow()
            source.page_count = stats.pages_indexed
            source.error_count = stats.pages_failed

            await db.commit()

            logger.info(
                f"Crawl job {job.id} completed: "
                f"{stats.pages_indexed} indexed, {stats.pages_failed} failed"
            )

            return stats

        except Exception as e:
            logger.exception(f"Crawl job {job.id} failed with error: {e}")
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)[:500]
            source.last_error = str(e)[:500]
            source.error_count += 1
            await db.commit()
            raise

        finally:
            self._active_crawls.pop(job.id, None)

    async def _handle_page_result(
        self,
        db: AsyncSession,
        job: CrawlJob,
        source: Source,
        index: Index,
        result: CrawlResult
    ) -> None:
        """Handle a single crawled page result."""
        if result.error or result.is_duplicate:
            return

        if not result.content:
            return

        # Determine what to index based on crawl_mode
        crawl_mode = getattr(source, 'crawl_mode', 'all') or 'all'
        index_text = _should_index_text(crawl_mode)
        index_images = _should_index_images(crawl_mode)
        index_videos = _should_index_videos(crawl_mode)

        try:
            # Generate document ID from URL
            doc_id = hashlib.sha256(result.url.encode()).hexdigest()[:16]

            # Get domain boost from index config
            domain = self._extract_domain(result.url)
            domain_boost = 1.0
            if index.ranking_config and "domain_boosts" in index.ranking_config:
                domain_boost = index.ranking_config["domain_boosts"].get(domain, 1.0)

            # Index text content to main index
            if index_text:
                await self.meilisearch.index_document(
                    slug=index.slug,
                    doc_id=doc_id,
                    url=result.url,
                    title=result.title or "Untitled",
                    description=result.description,
                    content=result.content,
                    headings=result.headings,
                    domain=domain,
                    source_id=source.id,
                    crawled_at=result.crawled_at,
                    published_at=result.published_date,
                    domain_boost=domain_boost,
                    images=result.images if not index_images else [],  # Only in page doc if not using dedicated index
                )

            # Index images to dedicated images index
            if index_images and result.images:
                await self._index_images(
                    index_slug=index.slug,
                    page_url=result.url,
                    page_title=result.title,
                    domain=domain,
                    source_id=source.id,
                    images=result.images,
                )

            # Index videos to dedicated videos index
            if index_videos and result.videos:
                await self._index_videos(
                    index_slug=index.slug,
                    page_url=result.url,
                    page_title=result.title,
                    domain=domain,
                    source_id=source.id,
                    videos=result.videos,
                )

        except Exception as e:
            logger.warning(f"Failed to index page {result.url}: {e}")

    async def _index_images(
        self,
        index_slug: str,
        page_url: str,
        page_title: Optional[str],
        domain: str,
        source_id: int,
        images: list[dict],
    ) -> None:
        """Index images to dedicated images index with optional CLIP embeddings."""
        settings = get_settings()
        clip = None

        if settings.crawler.image_embeddings_enabled:
            try:
                from app.core.embeddings.clip_embeddings import get_clip_embeddings
                clip = get_clip_embeddings()
                if not clip.is_available():
                    clip = None
            except Exception as e:
                logger.warning(f"Failed to load CLIP embeddings: {e}")
                clip = None

        for img in images[:20]:  # Limit per page
            img_url = img.get("src")
            if not img_url:
                continue

            doc_id = hashlib.sha256(img_url.encode()).hexdigest()[:16]

            # Generate CLIP embedding if enabled
            embedding = None
            if clip:
                try:
                    embedding = await clip.encode_image_url(img_url)
                except Exception as e:
                    logger.debug(f"Failed to generate CLIP embedding for {img_url}: {e}")

            await self.meilisearch.index_image(
                slug=index_slug,
                doc_id=doc_id,
                image_url=img_url,
                alt=img.get("alt"),
                title=img.get("title"),
                page_url=page_url,
                page_title=page_title or "",
                domain=domain,
                source_id=source_id,
                embedding=embedding,
            )

    async def _index_videos(
        self,
        index_slug: str,
        page_url: str,
        page_title: Optional[str],
        domain: str,
        source_id: int,
        videos: list[dict],
    ) -> None:
        """Index videos to dedicated videos index."""
        for vid in videos[:15]:  # Limit per page
            video_url = vid.get("video_url")
            if not video_url:
                continue

            doc_id = hashlib.sha256(video_url.encode()).hexdigest()[:16]

            await self.meilisearch.index_video(
                slug=index_slug,
                doc_id=doc_id,
                video_url=video_url,
                thumbnail_url=vid.get("thumbnail_url"),
                embed_type=vid.get("embed_type", "direct"),
                video_id=vid.get("video_id"),
                video_title=vid.get("title"),
                page_url=page_url,
                page_title=page_title or "",
                domain=domain,
                source_id=source_id,
            )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    def stop_crawl(self, job_id: int) -> bool:
        """
        Stop a running crawl.

        Args:
            job_id: The crawl job ID to stop

        Returns:
            True if crawl was stopped, False if not found
        """
        engine = self._active_crawls.get(job_id)
        if engine:
            engine.cancel()
            logger.info(f"Cancelled crawl job {job_id}")
            return True
        return False

    def is_crawling(self, job_id: int) -> bool:
        """Check if a crawl job is currently running."""
        return job_id in self._active_crawls

    def get_active_crawl_ids(self) -> list[int]:
        """Get list of active crawl job IDs."""
        return list(self._active_crawls.keys())


# Global service instance
_crawl_service: Optional[CrawlService] = None


def get_crawl_service() -> CrawlService:
    """Get the crawl service singleton."""
    global _crawl_service
    if _crawl_service is None:
        _crawl_service = CrawlService()
    return _crawl_service
