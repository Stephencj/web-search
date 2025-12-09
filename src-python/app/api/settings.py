"""Settings API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.config import get_settings
from app.models import ApiKey, AppSetting

router = APIRouter()


class ApiKeyCreate(BaseModel):
    """Schema for creating an API key."""
    provider: str
    api_key: str
    extra_config: Optional[str] = None
    daily_limit: Optional[int] = None


class ApiKeyResponse(BaseModel):
    """Schema for API key response (masked)."""
    provider: str
    masked_key: str
    is_active: bool
    daily_limit: Optional[int]
    daily_usage: int
    remaining_quota: Optional[int]


@router.get("")
async def get_settings_endpoint() -> dict:
    """Get application settings."""
    settings = get_settings()

    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "data_dir": str(settings.data_dir),
        "crawler": {
            "user_agent": settings.crawler.user_agent,
            "concurrent_requests": settings.crawler.concurrent_requests,
            "request_delay_ms": settings.crawler.request_delay_ms,
            "timeout_seconds": settings.crawler.timeout_seconds,
            "max_retries": settings.crawler.max_retries,
            "respect_robots_txt": settings.crawler.respect_robots_txt,
            "max_pages_per_source": settings.crawler.max_pages_per_source,
        },
        "meilisearch": {
            "host": settings.meilisearch.host,
            "index_prefix": settings.meilisearch.index_prefix,
        }
    }


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(db: DbSession) -> list[ApiKeyResponse]:
    """List all API keys (masked)."""
    result = await db.execute(select(ApiKey).order_by(ApiKey.provider))
    keys = result.scalars().all()

    return [
        ApiKeyResponse(
            provider=key.provider,
            masked_key=key.masked_key,
            is_active=key.is_active,
            daily_limit=key.daily_limit,
            daily_usage=key.daily_usage,
            remaining_quota=key.remaining_quota,
        )
        for key in keys
    ]


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(data: ApiKeyCreate, db: DbSession) -> ApiKeyResponse:
    """Add or update an API key."""
    # Check if provider already exists
    result = await db.execute(
        select(ApiKey).where(ApiKey.provider == data.provider)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing key
        existing.api_key = data.api_key
        existing.extra_config = data.extra_config
        existing.daily_limit = data.daily_limit
        existing.is_active = True
        key = existing
    else:
        # Create new key
        key = ApiKey(
            provider=data.provider,
            api_key=data.api_key,
            extra_config=data.extra_config,
            daily_limit=data.daily_limit,
        )
        db.add(key)

    await db.flush()
    await db.refresh(key)

    return ApiKeyResponse(
        provider=key.provider,
        masked_key=key.masked_key,
        is_active=key.is_active,
        daily_limit=key.daily_limit,
        daily_usage=key.daily_usage,
        remaining_quota=key.remaining_quota,
    )


@router.delete("/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(provider: str, db: DbSession) -> None:
    """Delete an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.provider == provider)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key for provider '{provider}' not found"
        )

    await db.delete(key)
