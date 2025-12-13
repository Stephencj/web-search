"""Platform accounts API endpoints for OAuth authentication."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.deps import DbSession
from app.services.oauth_service import get_oauth_service


router = APIRouter()


class AccountResponse(BaseModel):
    """Response schema for platform account."""
    id: int
    platform: str
    account_email: str
    account_name: str
    is_active: bool
    is_premium: bool
    scopes: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuthUrlResponse(BaseModel):
    """Response for authorization URL request."""
    url: str
    state: str
    configured: bool = True


class AccountStatusResponse(BaseModel):
    """Response for account status check."""
    id: int
    platform: str
    account_email: str
    is_active: bool
    is_premium: bool
    token_valid: bool
    needs_refresh: bool
    last_error: Optional[str] = None


class OAuthConfigStatus(BaseModel):
    """Response for OAuth configuration status."""
    youtube: bool = False


class ImportSubscriptionsResponse(BaseModel):
    """Response for subscription import."""
    imported: int
    skipped: int
    failed: int
    total_found: int


@router.get("", response_model=list[AccountResponse])
async def list_accounts(db: DbSession) -> list[AccountResponse]:
    """
    List all linked platform accounts.
    """
    service = get_oauth_service()
    accounts = await service.get_all_accounts(db)
    return [AccountResponse.model_validate(acc) for acc in accounts]


@router.get("/config-status", response_model=OAuthConfigStatus)
async def get_oauth_config_status() -> OAuthConfigStatus:
    """
    Check which platforms have OAuth configured.
    """
    service = get_oauth_service()
    return OAuthConfigStatus(
        youtube=service.is_configured("youtube"),
    )


@router.get("/auth/{platform}", response_model=AuthUrlResponse)
async def get_auth_url(platform: str) -> AuthUrlResponse:
    """
    Get OAuth authorization URL for a platform.

    The frontend should open this URL in a popup window.
    After authorization, the user will be redirected back to the callback endpoint.
    """
    service = get_oauth_service()

    if not service.is_configured(platform):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth not configured for platform: {platform}. "
                   f"Set WEBSEARCH_OAUTH__YOUTUBE_CLIENT_ID and WEBSEARCH_OAUTH__YOUTUBE_CLIENT_SECRET environment variables.",
        )

    result = service.get_authorization_url(platform)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate authorization URL for platform: {platform}",
        )

    return AuthUrlResponse(**result)


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    db: DbSession,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
) -> RedirectResponse:
    """
    OAuth callback endpoint.

    This is called by the OAuth provider after user authorization.
    Exchanges the authorization code for tokens and stores them.
    Redirects to frontend with success/error status.
    """
    # Base redirect URL (frontend settings page)
    base_redirect = "/settings"

    if error:
        # OAuth provider returned an error
        return RedirectResponse(
            url=f"{base_redirect}?oauth_error={error}&platform={platform}",
            status_code=status.HTTP_302_FOUND,
        )

    service = get_oauth_service()
    account = await service.handle_callback(db, platform, code, state)

    if not account:
        return RedirectResponse(
            url=f"{base_redirect}?oauth_error=callback_failed&platform={platform}",
            status_code=status.HTTP_302_FOUND,
        )

    # Success - redirect with account info
    return RedirectResponse(
        url=f"{base_redirect}?oauth_success=true&platform={platform}&email={account.account_email}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{account_id}/import-subscriptions", response_model=ImportSubscriptionsResponse)
async def import_subscriptions(account_id: int, db: DbSession) -> ImportSubscriptionsResponse:
    """
    Import YouTube subscriptions from a linked account.

    Fetches all subscriptions from the YouTube API and imports them as channels.
    Existing channels are skipped (duplicates handled automatically).
    """
    from loguru import logger
    from sqlalchemy import select
    from app.models import PlatformAccount

    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    if account.platform != "youtube":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import subscriptions is only supported for YouTube accounts",
        )

    service = get_oauth_service()

    try:
        logger.info(f"Starting subscription import for {account.account_email}")
        import_result = await service.import_youtube_subscriptions(db, account)
        logger.info(f"Import complete: {import_result}")
        return ImportSubscriptionsResponse(
            imported=import_result.get("imported", 0),
            skipped=import_result.get("skipped", 0),
            failed=import_result.get("failed", 0),
            total_found=import_result.get("total_found", 0),
        )
    except Exception as e:
        logger.exception(f"Subscription import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import subscriptions: {str(e)}",
        )


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: DbSession) -> AccountResponse:
    """
    Get a specific platform account.
    """
    from sqlalchemy import select
    from app.models import PlatformAccount

    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    return AccountResponse.model_validate(account)


@router.get("/{account_id}/status", response_model=AccountStatusResponse)
async def get_account_status(account_id: int, db: DbSession) -> AccountStatusResponse:
    """
    Check the status of an account's OAuth tokens.
    """
    from sqlalchemy import select
    from app.models import PlatformAccount

    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    return AccountStatusResponse(
        id=account.id,
        platform=account.platform,
        account_email=account.account_email,
        is_active=account.is_active,
        is_premium=account.is_premium,
        token_valid=not account.is_token_expired,
        needs_refresh=account.needs_refresh,
        last_error=account.last_error,
    )


@router.post("/{account_id}/refresh", response_model=AccountResponse)
async def refresh_account_token(account_id: int, db: DbSession) -> AccountResponse:
    """
    Force refresh the access token for an account.
    """
    from sqlalchemy import select
    from app.models import PlatformAccount

    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    service = get_oauth_service()
    success = await service.refresh_token(db, account)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to refresh token: {account.last_error or 'Unknown error'}",
        )

    await db.refresh(account)
    return AccountResponse.model_validate(account)


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: DbSession) -> dict:
    """
    Unlink a platform account.

    Revokes the OAuth tokens and removes the account from the database.
    """
    from sqlalchemy import select
    from app.models import PlatformAccount

    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    service = get_oauth_service()
    success = await service.revoke_account(db, account)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke account",
        )

    return {"success": True, "message": f"Account {account_id} unlinked successfully"}
