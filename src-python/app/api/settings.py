"""Settings API endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.config import get_settings
from app.models import ApiKey
from app.services.settings_service import get_settings_service
from app.schemas.settings import (
    ApiKeyCreate,
    ApiKeyResponse,
    CrawlerSettingsUpdate,
)

router = APIRouter()
settings_service = get_settings_service()


@router.get("")
async def get_settings_endpoint(db: DbSession) -> dict:
    """Get application settings with source information."""
    settings = get_settings()

    # Get crawler settings with source info
    crawler_settings = await settings_service.get_crawler_settings(db)

    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "data_dir": str(settings.data_dir),
        "crawler": crawler_settings,
        "meilisearch": {
            "host": settings.meilisearch.host,
            "index_prefix": settings.meilisearch.index_prefix,
        }
    }


@router.get("/crawler")
async def get_crawler_settings(db: DbSession) -> dict:
    """Get crawler settings with source information."""
    return await settings_service.get_crawler_settings(db)


@router.put("/crawler")
async def update_crawler_settings(
    data: CrawlerSettingsUpdate,
    db: DbSession
) -> dict:
    """
    Update crawler settings.

    Only settings not overridden by environment variables can be updated.
    """
    # Convert to dict, excluding None values
    updates = data.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No settings provided to update"
        )

    try:
        updated_settings = await settings_service.update_crawler_settings(db, updates)
        return {
            "success": True,
            "message": f"Updated {len(updates)} setting(s)",
            "settings": updated_settings,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/crawler/{setting_key}")
async def reset_crawler_setting(setting_key: str, db: DbSession) -> dict:
    """Reset a crawler setting to its default value."""
    try:
        updated_settings = await settings_service.reset_crawler_setting(db, setting_key)
        return {
            "success": True,
            "message": f"Reset '{setting_key}' to default value",
            "settings": updated_settings,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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
