"""Search module for Meilisearch integration and result aggregation."""

from app.core.search.meilisearch import get_meilisearch_client

__all__ = ["get_meilisearch_client"]
