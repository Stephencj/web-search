"""OAuth service - handles platform authentication and token management."""

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PlatformAccount


class OAuthService:
    """Service for OAuth2 authentication with video platforms."""

    # OAuth endpoints
    YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    YOUTUBE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    YOUTUBE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"

    # Required scopes for YouTube
    YOUTUBE_SCOPES = [
        "https://www.googleapis.com/auth/youtube.readonly",  # Read subscriptions, playlists
        "https://www.googleapis.com/auth/userinfo.email",  # Get user email
        "https://www.googleapis.com/auth/userinfo.profile",  # Get user profile
    ]

    def __init__(self):
        self.settings = get_settings()
        self._fernet: Optional[Fernet] = None
        self._state_store: dict[str, datetime] = {}  # In-memory state validation

    @property
    def fernet(self) -> Optional[Fernet]:
        """Get Fernet cipher for token encryption."""
        if self._fernet is None and self.settings.oauth.encryption_key:
            try:
                self._fernet = Fernet(self.settings.oauth.encryption_key.encode())
            except Exception as e:
                logger.error(f"Failed to initialize Fernet cipher: {e}")
        return self._fernet

    def is_configured(self, platform: str) -> bool:
        """Check if OAuth is configured for the given platform."""
        if platform == "youtube":
            return bool(
                self.settings.oauth.youtube_client_id
                and self.settings.oauth.youtube_client_secret
                and self.settings.oauth.encryption_key
            )
        return False

    def get_authorization_url(self, platform: str) -> Optional[dict]:
        """
        Generate OAuth authorization URL.

        Returns:
            Dict with 'url' and 'state' if configured, None otherwise
        """
        if not self.is_configured(platform):
            return None

        # Generate and store state for CSRF protection
        state = secrets.token_urlsafe(32)
        self._state_store[state] = datetime.utcnow()
        self._cleanup_old_states()

        if platform == "youtube":
            params = {
                "client_id": self.settings.oauth.youtube_client_id,
                "redirect_uri": self.settings.oauth.youtube_redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.YOUTUBE_SCOPES),
                "access_type": "offline",  # Get refresh token
                "prompt": "consent",  # Always show consent screen
                "state": state,
            }
            url = f"{self.YOUTUBE_AUTH_URL}?{urlencode(params)}"
            return {"url": url, "state": state}

        return None

    def validate_state(self, state: str) -> bool:
        """Validate OAuth state parameter."""
        if state not in self._state_store:
            return False
        # State is valid for 10 minutes
        created = self._state_store.pop(state)
        return datetime.utcnow() - created < timedelta(minutes=10)

    async def handle_callback(
        self,
        db: AsyncSession,
        platform: str,
        code: str,
        state: str,
    ) -> Optional[PlatformAccount]:
        """
        Handle OAuth callback and exchange code for tokens.

        Args:
            db: Database session
            platform: Platform ID (e.g., "youtube")
            code: Authorization code from OAuth provider
            state: State parameter for CSRF validation

        Returns:
            PlatformAccount if successful, None otherwise
        """
        if not self.validate_state(state):
            logger.warning("Invalid OAuth state parameter")
            return None

        if platform == "youtube":
            return await self._handle_youtube_callback(db, code)

        return None

    async def _handle_youtube_callback(
        self,
        db: AsyncSession,
        code: str,
    ) -> Optional[PlatformAccount]:
        """Exchange YouTube authorization code for tokens."""
        try:
            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    self.YOUTUBE_TOKEN_URL,
                    data={
                        "client_id": self.settings.oauth.youtube_client_id,
                        "client_secret": self.settings.oauth.youtube_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.settings.oauth.youtube_redirect_uri,
                    },
                )

                if token_response.status_code != 200:
                    logger.error(f"Token exchange failed: {token_response.text}")
                    return None

                tokens = token_response.json()
                access_token = tokens.get("access_token")
                refresh_token = tokens.get("refresh_token")
                expires_in = tokens.get("expires_in", 3600)
                scope = tokens.get("scope", "")

                if not access_token:
                    logger.error("No access token in response")
                    return None

                # Get user info
                userinfo_response = await client.get(
                    self.YOUTUBE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if userinfo_response.status_code != 200:
                    logger.error(f"User info fetch failed: {userinfo_response.text}")
                    return None

                userinfo = userinfo_response.json()
                email = userinfo.get("email", "")
                name = userinfo.get("name", email)

                if not email:
                    logger.error("No email in user info")
                    return None

            # Encrypt tokens
            encrypted_access = self._encrypt_token(access_token)
            encrypted_refresh = self._encrypt_token(refresh_token) if refresh_token else None

            if not encrypted_access:
                logger.error("Failed to encrypt access token")
                return None

            # Check for existing account
            result = await db.execute(
                select(PlatformAccount).where(
                    PlatformAccount.platform == "youtube",
                    PlatformAccount.account_email == email,
                )
            )
            account = result.scalar_one_or_none()

            if account:
                # Update existing account
                account.access_token_encrypted = encrypted_access
                if encrypted_refresh:
                    account.refresh_token_encrypted = encrypted_refresh
                account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                account.scopes = scope
                account.is_active = True
                account.last_error = None
                account.account_name = name
            else:
                # Create new account
                account = PlatformAccount(
                    platform="youtube",
                    account_email=email,
                    account_name=name,
                    access_token_encrypted=encrypted_access,
                    refresh_token_encrypted=encrypted_refresh,
                    token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                    scopes=scope,
                    is_active=True,
                )
                db.add(account)

            await db.commit()
            await db.refresh(account)

            logger.info(f"YouTube account linked: {email}")
            return account

        except Exception as e:
            logger.exception(f"YouTube callback error: {e}")
            return None

    async def refresh_token(
        self,
        db: AsyncSession,
        account: PlatformAccount,
    ) -> bool:
        """
        Refresh an expired access token.

        Returns:
            True if refresh successful, False otherwise
        """
        if not account.refresh_token_encrypted:
            logger.warning(f"No refresh token for account {account.id}")
            return False

        refresh_token = self._decrypt_token(account.refresh_token_encrypted)
        if not refresh_token:
            logger.error(f"Failed to decrypt refresh token for account {account.id}")
            return False

        try:
            if account.platform == "youtube":
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.YOUTUBE_TOKEN_URL,
                        data={
                            "client_id": self.settings.oauth.youtube_client_id,
                            "client_secret": self.settings.oauth.youtube_client_secret,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                        },
                    )

                    if response.status_code != 200:
                        logger.error(f"Token refresh failed: {response.text}")
                        account.mark_error(f"Token refresh failed: {response.status_code}")
                        await db.commit()
                        return False

                    tokens = response.json()
                    new_access_token = tokens.get("access_token")
                    expires_in = tokens.get("expires_in", 3600)

                    if not new_access_token:
                        logger.error("No access token in refresh response")
                        return False

                    # Encrypt and update
                    encrypted_access = self._encrypt_token(new_access_token)
                    if not encrypted_access:
                        return False

                    account.access_token_encrypted = encrypted_access
                    account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    account.mark_refreshed()

                    # Update refresh token if a new one was provided
                    new_refresh = tokens.get("refresh_token")
                    if new_refresh:
                        encrypted_refresh = self._encrypt_token(new_refresh)
                        if encrypted_refresh:
                            account.refresh_token_encrypted = encrypted_refresh

                    await db.commit()
                    logger.info(f"Refreshed token for account {account.id}")
                    return True

            return False

        except Exception as e:
            logger.exception(f"Token refresh error: {e}")
            account.mark_error(str(e))
            await db.commit()
            return False

    async def get_valid_access_token(
        self,
        db: AsyncSession,
        account: PlatformAccount,
    ) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Decrypted access token or None if unavailable
        """
        if not account.is_active:
            return None

        # Refresh if needed
        if account.needs_refresh:
            success = await self.refresh_token(db, account)
            if not success:
                return None

        # Decrypt and return
        access_token = self._decrypt_token(account.access_token_encrypted)
        if access_token:
            account.mark_used()
            await db.commit()

        return access_token

    async def revoke_account(
        self,
        db: AsyncSession,
        account: PlatformAccount,
    ) -> bool:
        """
        Revoke OAuth tokens and delete account.

        Returns:
            True if successful
        """
        try:
            # Try to revoke tokens with the provider
            if account.platform == "youtube":
                access_token = self._decrypt_token(account.access_token_encrypted)
                if access_token:
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                self.YOUTUBE_REVOKE_URL,
                                params={"token": access_token},
                            )
                    except Exception as e:
                        logger.warning(f"Token revocation failed (non-fatal): {e}")

            # Delete the account
            await db.delete(account)
            await db.commit()

            logger.info(f"Revoked and deleted account {account.id}")
            return True

        except Exception as e:
            logger.exception(f"Account revocation error: {e}")
            return False

    async def get_account(
        self,
        db: AsyncSession,
        platform: str,
    ) -> Optional[PlatformAccount]:
        """Get the active account for a platform."""
        result = await db.execute(
            select(PlatformAccount).where(
                PlatformAccount.platform == platform,
                PlatformAccount.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_accounts(
        self,
        db: AsyncSession,
    ) -> list[PlatformAccount]:
        """Get all platform accounts."""
        result = await db.execute(select(PlatformAccount))
        return list(result.scalars().all())

    def _encrypt_token(self, token: str) -> Optional[str]:
        """Encrypt a token for storage."""
        if not self.fernet or not token:
            return None
        try:
            return self.fernet.encrypt(token.encode()).decode()
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            return None

    def _decrypt_token(self, encrypted: str) -> Optional[str]:
        """Decrypt a stored token."""
        if not self.fernet or not encrypted:
            return None
        try:
            return self.fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            logger.error("Invalid token - decryption failed")
            return None
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            return None

    def _cleanup_old_states(self) -> None:
        """Remove expired state tokens."""
        now = datetime.utcnow()
        expired = [
            state for state, created in self._state_store.items()
            if now - created > timedelta(minutes=10)
        ]
        for state in expired:
            self._state_store.pop(state, None)

    async def fetch_youtube_subscriptions(
        self,
        db: AsyncSession,
        account: PlatformAccount,
    ) -> list[dict]:
        """
        Fetch all YouTube subscriptions for an account.

        Returns:
            List of subscription dicts with channel info
        """
        access_token = await self.get_valid_access_token(db, account)
        if not access_token:
            logger.error("No valid access token for fetching subscriptions")
            return []

        subscriptions = []
        page_token = None

        try:
            async with httpx.AsyncClient() as client:
                while True:
                    params = {
                        "part": "snippet",
                        "mine": "true",
                        "maxResults": 50,
                    }
                    if page_token:
                        params["pageToken"] = page_token

                    response = await client.get(
                        f"{self.YOUTUBE_API_URL}/subscriptions",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=30,
                    )

                    if response.status_code != 200:
                        logger.error(f"Failed to fetch subscriptions: {response.text}")
                        break

                    data = response.json()

                    for item in data.get("items", []):
                        snippet = item.get("snippet", {})
                        resource_id = snippet.get("resourceId", {})
                        channel_id = resource_id.get("channelId")

                        if channel_id:
                            subscriptions.append({
                                "channel_id": channel_id,
                                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                                "title": snippet.get("title"),
                                "description": snippet.get("description"),
                                "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                            })

                    # Check for more pages
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break

            logger.info(f"Fetched {len(subscriptions)} YouTube subscriptions")
            return subscriptions

        except Exception as e:
            logger.exception(f"Error fetching YouTube subscriptions: {e}")
            return subscriptions

    async def fetch_youtube_playlists(
        self,
        db: AsyncSession,
        account: PlatformAccount,
    ) -> list[dict]:
        """
        Fetch all YouTube playlists for an account (including Watch Later, Liked Videos).

        Returns:
            List of playlist dicts
        """
        access_token = await self.get_valid_access_token(db, account)
        if not access_token:
            logger.error("No valid access token for fetching playlists")
            return []

        playlists = []
        page_token = None

        try:
            async with httpx.AsyncClient() as client:
                while True:
                    params = {
                        "part": "snippet,contentDetails",
                        "mine": "true",
                        "maxResults": 50,
                    }
                    if page_token:
                        params["pageToken"] = page_token

                    response = await client.get(
                        f"{self.YOUTUBE_API_URL}/playlists",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=30,
                    )

                    if response.status_code != 200:
                        logger.error(f"Failed to fetch playlists: {response.text}")
                        break

                    data = response.json()

                    for item in data.get("items", []):
                        snippet = item.get("snippet", {})
                        content_details = item.get("contentDetails", {})

                        playlists.append({
                            "playlist_id": item.get("id"),
                            "playlist_url": f"https://www.youtube.com/playlist?list={item.get('id')}",
                            "title": snippet.get("title"),
                            "description": snippet.get("description"),
                            "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                            "video_count": content_details.get("itemCount", 0),
                        })

                    # Check for more pages
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break

            logger.info(f"Fetched {len(playlists)} YouTube playlists")
            return playlists

        except Exception as e:
            logger.exception(f"Error fetching YouTube playlists: {e}")
            return playlists

    async def import_youtube_subscriptions(
        self,
        db: AsyncSession,
        account: PlatformAccount,
    ) -> dict:
        """
        Fetch and import all YouTube subscriptions as channels.

        Returns:
            Dict with import results (imported, skipped, failed counts)
        """
        from app.services.channel_service import get_channel_service

        # Fetch subscriptions from YouTube API
        subscriptions = await self.fetch_youtube_subscriptions(db, account)

        if not subscriptions:
            return {"imported": 0, "skipped": 0, "failed": 0, "total_found": 0}

        # Extract channel URLs
        urls = [sub["channel_url"] for sub in subscriptions]

        # Import using channel service (handles duplicates automatically)
        channel_service = get_channel_service()
        result = await channel_service.import_from_urls(db, urls, import_source="youtube_oauth")

        result["total_found"] = len(subscriptions)
        logger.info(
            f"YouTube subscription import complete: "
            f"{result['imported']} imported, {result['skipped']} skipped, "
            f"{result['failed']} failed (from {len(subscriptions)} total)"
        )

        return result


# Singleton instance
_oauth_service: Optional[OAuthService] = None


def get_oauth_service() -> OAuthService:
    """Get the OAuth service singleton."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service
