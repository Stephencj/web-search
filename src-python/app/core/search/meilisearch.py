"""Meilisearch client wrapper for search operations."""

from datetime import datetime
from typing import Optional, Any

from meilisearch_python_sdk import AsyncClient
from meilisearch_python_sdk.errors import MeilisearchApiError
from meilisearch_python_sdk.models.settings import MeilisearchSettings as MeiliSettings
from loguru import logger

from app.config import get_settings


class MeilisearchClient:
    """Async Meilisearch client wrapper."""

    def __init__(self):
        settings = get_settings()
        self.host = settings.meilisearch.host
        self.api_key = settings.meilisearch.api_key
        self.index_prefix = settings.meilisearch.index_prefix
        self._client: Optional[AsyncClient] = None

    async def get_client(self) -> AsyncClient:
        """Get or create the Meilisearch client."""
        if self._client is None:
            self._client = AsyncClient(self.host, self.api_key)
        return self._client

    def get_index_name(self, slug: str) -> str:
        """Get full index name with prefix."""
        return f"{self.index_prefix}{slug}"

    async def create_index(self, slug: str) -> bool:
        """Create a new Meilisearch index with proper settings."""
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            # Create index
            await client.create_index(index_name, primary_key="id")

            # Configure index settings
            index = client.index(index_name)
            settings = MeiliSettings(
                searchable_attributes=[
                    "title",
                    "description",
                    "content",
                    "headings",
                    "image_text",  # Searchable image alt/title text
                ],
                filterable_attributes=[
                    "domain",
                    "source_id",
                    "crawled_at",
                    "published_at",
                ],
                sortable_attributes=[
                    "crawled_at",
                    "published_at",
                    "domain_boost",
                ],
                ranking_rules=[
                    "words",
                    "typo",
                    "proximity",
                    "attribute",
                    "sort",
                    "exactness",
                ],
            )
            await index.update_settings(settings)

            logger.info(f"Created Meilisearch index: {index_name}")
            return True

        except MeilisearchApiError as e:
            if "already exists" in str(e).lower():
                logger.debug(f"Index {index_name} already exists")
                return True
            logger.error(f"Failed to create index {index_name}: {e}")
            return False

    async def delete_index(self, slug: str) -> bool:
        """Delete a Meilisearch index."""
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            await client.delete_index(index_name)
            logger.info(f"Deleted Meilisearch index: {index_name}")
            return True
        except MeilisearchApiError as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False

    async def index_document(
        self,
        slug: str,
        doc_id: str,
        url: str,
        title: str,
        description: Optional[str],
        content: str,
        headings: list[str],
        domain: str,
        source_id: int,
        crawled_at: datetime,
        published_at: Optional[str] = None,
        domain_boost: float = 1.0,
        images: Optional[list[dict]] = None,
    ) -> bool:
        """Index a single document."""
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        # Build searchable image text from alt/title attributes
        image_text = ""
        image_urls = []
        if images:
            image_texts = []
            for img in images[:20]:  # Limit to 20 images
                if img.get("alt"):
                    image_texts.append(img["alt"])
                if img.get("title"):
                    image_texts.append(img["title"])
                if img.get("src"):
                    image_urls.append(img["src"])
            image_text = " ".join(image_texts)

        document = {
            "id": doc_id,
            "url": url,
            "title": title or "Untitled",
            "description": description or "",
            "content": content[:100000],  # Limit content size
            "headings": headings[:20],
            "image_text": image_text[:5000],  # Searchable image metadata
            "images": image_urls[:20],  # Image URLs for display
            "domain": domain,
            "source_id": source_id,
            "crawled_at": int(crawled_at.timestamp()),
            "published_at": self._parse_date(published_at) if published_at else None,
            "domain_boost": domain_boost,
        }

        try:
            index = client.index(index_name)
            await index.add_documents([document])
            return True
        except MeilisearchApiError as e:
            logger.error(f"Failed to index document {url}: {e}")
            return False

    async def index_documents_batch(
        self,
        slug: str,
        documents: list[dict[str, Any]],
    ) -> int:
        """Index multiple documents in a batch."""
        if not documents:
            return 0

        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            index = client.index(index_name)
            await index.add_documents(documents)
            return len(documents)
        except MeilisearchApiError as e:
            logger.error(f"Failed to index batch: {e}")
            return 0

    async def delete_document(self, slug: str, doc_id: str) -> bool:
        """Delete a document from the index."""
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            index = client.index(index_name)
            await index.delete_document(doc_id)
            return True
        except MeilisearchApiError as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    async def delete_documents_by_source(self, slug: str, source_id: int) -> bool:
        """Delete all documents from a source."""
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            index = client.index(index_name)
            await index.delete_documents_by_filter(f"source_id = {source_id}")
            return True
        except MeilisearchApiError as e:
            logger.error(f"Failed to delete documents for source {source_id}: {e}")
            return False

    async def search(
        self,
        slug: str,
        query: str,
        filters: Optional[str] = None,
        sort: Optional[list[str]] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search an index.

        Returns dict with hits, total, and timing info.
        """
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            index = client.index(index_name)
            result = await index.search(
                query,
                filter=filters,
                sort=sort,
                offset=offset,
                limit=limit,
                attributes_to_highlight=["title", "content"],
                highlight_pre_tag="<mark>",
                highlight_post_tag="</mark>",
            )

            return {
                "hits": result.hits,
                "total": result.estimated_total_hits or len(result.hits),
                "processing_time_ms": result.processing_time_ms,
            }

        except MeilisearchApiError as e:
            logger.error(f"Search failed: {e}")
            return {"hits": [], "total": 0, "processing_time_ms": 0}

    async def get_stats(self, slug: str) -> dict[str, Any]:
        """Get index statistics."""
        client = await self.get_client()
        index_name = self.get_index_name(slug)

        try:
            index = client.index(index_name)
            stats = await index.get_stats()
            return {
                "document_count": stats.number_of_documents,
                "is_indexing": stats.is_indexing,
            }
        except MeilisearchApiError:
            return {"document_count": 0, "is_indexing": False}

    async def health_check(self) -> bool:
        """Check if Meilisearch is available."""
        try:
            client = await self.get_client()
            health = await client.health()
            return health.status == "available"
        except Exception:
            return False

    def _parse_date(self, date_str: str) -> Optional[int]:
        """Parse date string to Unix timestamp."""
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            pass

        try:
            # Try common date format
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            return None


# Singleton instance
_client: Optional[MeilisearchClient] = None


def get_meilisearch_client() -> MeilisearchClient:
    """Get the Meilisearch client singleton."""
    global _client
    if _client is None:
        _client = MeilisearchClient()
    return _client
