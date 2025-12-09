"""Pydantic schemas for Search operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Search filters."""
    domains: Optional[list[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SearchRequest(BaseModel):
    """Schema for search request."""
    query: str = Field(..., min_length=1, max_length=500)

    # Source selection
    indexes: Optional[list[str]] = Field(
        None,
        description="Index slugs to search. None = all indexes"
    )
    external_apis: Optional[list[str]] = Field(
        None,
        description="External APIs to query. None = none"
    )

    # Filters
    filters: Optional[SearchFilters] = None

    # Sorting and pagination
    sort: Literal["relevance", "date"] = "relevance"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    """Single search result."""
    source: str  # "local" or API name like "google", "bing"
    index: Optional[str] = None  # Index slug for local results
    url: str
    title: str
    snippet: str
    domain: str
    published_at: Optional[datetime] = None
    score: float = Field(ge=0, le=1)


class SearchFacet(BaseModel):
    """Facet value and count."""
    value: str
    count: int


class SearchTiming(BaseModel):
    """Search timing information."""
    local_ms: int = 0
    external_ms: int = 0
    total_ms: int = 0


class SearchResponse(BaseModel):
    """Schema for search response."""
    query: str
    total_results: int
    page: int
    per_page: int
    results: list[SearchResult]
    facets: dict[str, list[SearchFacet]] = Field(default_factory=dict)
    timing: SearchTiming = Field(default_factory=SearchTiming)
