"""Search API endpoints."""

import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.search.meilisearch import get_meilisearch_client
from app.models import Index
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchFacet,
    SearchTiming,
)

router = APIRouter()


def _extract_snippet(hit: dict, max_length: int = 200) -> str:
    """Extract a snippet from search result, preferring highlighted content."""
    # Check for highlighted content
    formatted = hit.get("_formatted", {})

    # Try highlighted content first
    content = formatted.get("content", hit.get("content", ""))
    if content:
        # Truncate and clean up
        if len(content) > max_length:
            content = content[:max_length].rsplit(" ", 1)[0] + "..."
        return content

    # Fallback to description
    desc = formatted.get("description", hit.get("description", ""))
    if desc:
        if len(desc) > max_length:
            desc = desc[:max_length].rsplit(" ", 1)[0] + "..."
        return desc

    return ""


def _normalize_score(hit: dict, max_score: float) -> float:
    """Normalize score to 0-1 range."""
    # Meilisearch doesn't provide raw scores, so we estimate based on position
    # and other factors. For now, use a simple approach.
    return 0.8  # Default high relevance since Meilisearch ranks by relevance


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest, db: DbSession) -> SearchResponse:
    """
    Execute a search across local indexes and external APIs.

    This is the main search endpoint that:
    1. Queries selected local Meilisearch indexes
    2. Queries selected external APIs (Google, Bing, etc.)
    3. Aggregates and ranks results
    4. Returns unified response with facets
    """
    start_time = time.time()
    meilisearch = get_meilisearch_client()

    all_results: list[SearchResult] = []
    total_results = 0
    local_time_ms = 0

    # Determine which indexes to search
    if request.indexes:
        # Search specific indexes
        index_slugs = request.indexes
    else:
        # Search all active indexes
        result = await db.execute(
            select(Index.slug).where(Index.is_active == True)
        )
        index_slugs = [row[0] for row in result.fetchall()]

    # Build Meilisearch filters
    filters = []
    if request.filters:
        if request.filters.domains:
            domain_filter = " OR ".join(
                f'domain = "{d}"' for d in request.filters.domains
            )
            filters.append(f"({domain_filter})")

        if request.filters.date_from:
            ts = int(request.filters.date_from.timestamp())
            filters.append(f"crawled_at >= {ts}")

        if request.filters.date_to:
            ts = int(request.filters.date_to.timestamp())
            filters.append(f"crawled_at <= {ts}")

    filter_str = " AND ".join(filters) if filters else None

    # Determine sort
    sort = None
    if request.sort == "date":
        sort = ["crawled_at:desc"]

    # Calculate offset
    offset = (request.page - 1) * request.per_page

    # Search each index
    domain_counts: dict[str, int] = {}
    index_counts: dict[str, int] = {}

    for slug in index_slugs:
        local_start = time.time()

        try:
            search_result = await meilisearch.search(
                slug=slug,
                query=request.query,
                filters=filter_str,
                sort=sort,
                offset=offset,
                limit=request.per_page,
            )

            local_time_ms += search_result.get("processing_time_ms", 0)
            total_results += search_result.get("total", 0)

            # Process hits
            for hit in search_result.get("hits", []):
                # Get title from formatted or raw
                formatted = hit.get("_formatted", {})
                title = formatted.get("title", hit.get("title", "Untitled"))
                snippet = _extract_snippet(hit)
                domain = hit.get("domain", "")

                # Track facets
                if domain:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                index_counts[slug] = index_counts.get(slug, 0) + 1

                # Parse published_at
                published_at = None
                if hit.get("published_at"):
                    try:
                        published_at = datetime.fromtimestamp(hit["published_at"])
                    except (ValueError, TypeError):
                        pass

                all_results.append(SearchResult(
                    source="local",
                    index=slug,
                    url=hit.get("url", ""),
                    title=title,
                    snippet=snippet,
                    domain=domain,
                    published_at=published_at,
                    score=_normalize_score(hit, 1.0),
                ))

        except Exception as e:
            # Log error but continue with other indexes
            pass

    # TODO: Query external APIs when implemented (Phase 5)
    external_time_ms = 0

    # Build facets
    facets = {}
    if domain_counts:
        facets["domain"] = [
            SearchFacet(value=domain, count=count)
            for domain, count in sorted(
                domain_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]
    if index_counts:
        facets["index"] = [
            SearchFacet(value=idx, count=count)
            for idx, count in sorted(
                index_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]

    # Calculate total time
    total_time_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=request.query,
        total_results=total_results,
        page=request.page,
        per_page=request.per_page,
        results=all_results[:request.per_page],  # Limit results
        facets=facets,
        timing=SearchTiming(
            local_ms=local_time_ms,
            external_ms=external_time_ms,
            total_ms=total_time_ms
        )
    )
