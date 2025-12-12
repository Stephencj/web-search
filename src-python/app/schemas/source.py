"""Pydantic schemas for Source operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class SourceBase(BaseModel):
    """Base schema for Source."""
    url: str = Field(..., max_length=2000)
    source_type: Literal["domain", "url", "sitemap"] = "domain"
    name: Optional[str] = Field(None, max_length=100)

    # Crawl configuration
    crawl_depth: int = Field(default=2, ge=1, le=10)
    crawl_frequency: Literal["hourly", "daily", "weekly", "monthly"] = "daily"
    max_pages: int = Field(default=1000, ge=1, le=100000)

    # Filtering rules
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    # robots.txt behavior
    respect_robots: bool = True

    # Content extraction mode
    crawl_mode: Literal["text_only", "images_only", "videos_only", "text_images", "text_videos", "images_videos", "all"] = "all"


class SourceCreate(SourceBase):
    """Schema for creating a Source."""
    pass


class SourceUpdate(BaseModel):
    """Schema for updating a Source."""
    url: Optional[str] = Field(None, max_length=2000)
    source_type: Optional[Literal["domain", "url", "sitemap"]] = None
    name: Optional[str] = Field(None, max_length=100)
    crawl_depth: Optional[int] = Field(None, ge=1, le=10)
    crawl_frequency: Optional[Literal["hourly", "daily", "weekly", "monthly"]] = None
    max_pages: Optional[int] = Field(None, ge=1, le=100000)
    include_patterns: Optional[list[str]] = None
    exclude_patterns: Optional[list[str]] = None
    respect_robots: Optional[bool] = None
    crawl_mode: Optional[Literal["text_only", "images_only", "videos_only", "text_images", "text_videos", "images_videos", "all"]] = None
    is_active: Optional[bool] = None


class SourceResponse(BaseModel):
    """Schema for Source response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    index_id: int
    url: str
    source_type: str
    name: Optional[str]

    crawl_depth: int
    crawl_frequency: str
    max_pages: int
    include_patterns: list[str]
    exclude_patterns: list[str]
    respect_robots: bool
    crawl_mode: str

    is_active: bool
    last_crawl_at: Optional[datetime]
    page_count: int
    error_count: int
    last_error: Optional[str]

    created_at: datetime
    updated_at: datetime

    # Computed
    domain: str = ""
    display_name: str = ""
