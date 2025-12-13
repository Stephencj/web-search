"""Pydantic schemas for Settings operations."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SettingValue(BaseModel):
    """A setting value with source information."""
    value: Any
    source: Literal["env", "db", "default"]
    editable: bool


class CrawlerSettingsResponse(BaseModel):
    """Response schema for crawler settings with source information."""
    user_agent: SettingValue
    concurrent_requests: SettingValue
    request_delay_ms: SettingValue
    timeout_seconds: SettingValue
    max_retries: SettingValue
    respect_robots_txt: SettingValue
    max_pages_per_source: SettingValue
    max_page_size_mb: SettingValue
    raw_html_enabled: SettingValue
    image_embeddings_enabled: SettingValue
    youtube_fetch_transcripts: SettingValue
    youtube_transcript_languages: SettingValue
    youtube_max_videos_per_source: SettingValue
    youtube_rate_limit_delay_ms: SettingValue


class CrawlerSettingsUpdate(BaseModel):
    """Schema for updating crawler settings."""
    user_agent: Optional[str] = Field(None, min_length=1, max_length=200)
    concurrent_requests: Optional[int] = Field(None, ge=1, le=50)
    request_delay_ms: Optional[int] = Field(None, ge=0, le=60000)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    respect_robots_txt: Optional[bool] = None
    max_pages_per_source: Optional[int] = Field(None, ge=1, le=100000)


class ApiKeyCreate(BaseModel):
    """Schema for creating/updating an API key."""
    provider: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1, max_length=500)
    extra_config: Optional[str] = Field(None, max_length=500)
    daily_limit: Optional[int] = Field(None, ge=1)


class ApiKeyResponse(BaseModel):
    """Schema for API key response (with masked key)."""
    provider: str
    masked_key: str
    is_active: bool
    daily_limit: Optional[int]
    daily_usage: int
    remaining_quota: Optional[int]


class AppSettingsResponse(BaseModel):
    """Full application settings response."""
    app_name: str
    debug: bool
    data_dir: str
    crawler: CrawlerSettingsResponse
    meilisearch: dict


class SettingUpdateResponse(BaseModel):
    """Response after updating a setting."""
    success: bool
    message: str
    settings: Optional[CrawlerSettingsResponse] = None
