"""Settings API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.config import get_settings
from app.models import ApiKey
from app.services.settings_service import get_settings_service
from app.services.user_service import get_user_service
from app.services.network_service import get_network_service
from app.schemas.settings import (
    ApiKeyCreate,
    ApiKeyResponse,
    CrawlerSettingsUpdate,
)


# Network settings schemas
class NetworkInfoResponse(BaseModel):
    """Network information response."""
    local_ip: str
    local_url: str
    external_ip: Optional[str]
    external_url: Optional[str]
    external_mode: str


class SetExternalModeRequest(BaseModel):
    """Set external URL mode request."""
    mode: str  # "auto", "manual", or "disabled"


class SetExternalUrlRequest(BaseModel):
    """Set manual external URL request."""
    url: Optional[str]


class SetAuthModeRequest(BaseModel):
    """Set auth mode request."""
    mode: str  # "open" or "protected"


class QrCodeResponse(BaseModel):
    """QR code response."""
    url: str
    qr_code_data: Optional[str]


class TestAccessResponse(BaseModel):
    """Test external access response."""
    success: bool
    status_code: Optional[int]
    message: str

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


# === Network Settings ===

@router.get("/network", response_model=NetworkInfoResponse)
async def get_network_info(db: DbSession) -> NetworkInfoResponse:
    """Get network access information."""
    network_service = get_network_service()
    info = await network_service.get_access_urls(db)
    return NetworkInfoResponse(**info)


@router.put("/network/external-mode")
async def set_external_mode(
    request: SetExternalModeRequest,
    db: DbSession,
) -> dict:
    """Set external URL mode (auto/manual/disabled)."""
    network_service = get_network_service()
    try:
        await network_service.set_external_url_mode(db, request.mode)
        return {"success": True, "mode": request.mode}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/network/external-url")
async def set_external_url(
    request: SetExternalUrlRequest,
    db: DbSession,
) -> dict:
    """Set manual external URL."""
    network_service = get_network_service()
    await network_service.set_manual_external_url(db, request.url)
    return {"success": True, "url": request.url}


@router.get("/network/qr-code", response_model=QrCodeResponse)
async def get_qr_code(
    db: DbSession,
    url_type: str = "local",  # "local" or "external"
) -> QrCodeResponse:
    """Generate QR code for app access URL."""
    network_service = get_network_service()
    info = await network_service.get_access_urls(db)

    if url_type == "external" and info.get("external_url"):
        url = info["external_url"]
    else:
        url = info["local_url"]

    qr_data = network_service.generate_qr_code_data(url)
    return QrCodeResponse(url=url, qr_code_data=qr_data)


@router.post("/network/test-access", response_model=TestAccessResponse)
async def test_external_access(
    db: DbSession,
    url: Optional[str] = None,
) -> TestAccessResponse:
    """Test if external URL is accessible."""
    network_service = get_network_service()

    if not url:
        info = await network_service.get_access_urls(db)
        url = info.get("external_url")
        if not url:
            return TestAccessResponse(
                success=False,
                status_code=None,
                message="No external URL configured",
            )

    result = await network_service.test_external_access(url)
    return TestAccessResponse(**result)


@router.get("/network/port-forwarding-help")
async def get_port_forwarding_help() -> dict:
    """Get port forwarding setup instructions."""
    network_service = get_network_service()
    return network_service.get_port_forwarding_instructions()


# === Auth Mode Settings ===

@router.get("/auth-mode")
async def get_auth_mode_setting(db: DbSession) -> dict:
    """Get current auth mode."""
    user_service = get_user_service()
    mode = await user_service.get_auth_mode(db)
    return {"mode": mode}


@router.put("/auth-mode")
async def set_auth_mode_setting(
    request: SetAuthModeRequest,
    db: DbSession,
) -> dict:
    """Set auth mode (open/protected)."""
    user_service = get_user_service()
    try:
        await user_service.set_auth_mode(db, request.mode)
        return {"success": True, "mode": request.mode}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
