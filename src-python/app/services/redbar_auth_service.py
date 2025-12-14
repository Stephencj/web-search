"""Red Bar Radio authentication service - handles session-based login."""

import json
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PlatformAccount


class RedBarAuthService:
    """
    Service for Red Bar Radio session-based authentication.

    Handles login, session cookie storage (encrypted), and session validation.
    Uses the same PlatformAccount model as OAuth services but stores session cookies
    instead of OAuth tokens.
    """

    LOGIN_URL = "https://redbarradio.net/user/login"
    LOGOUT_URL = "https://redbarradio.net/user/logout"
    BASE_URL = "https://redbarradio.net"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # WordPress sessions with "Remember Me" typically last 14 days
    SESSION_DURATION_DAYS = 14

    def __init__(self):
        self.settings = get_settings()
        self._fernet: Optional[Fernet] = None

    @property
    def fernet(self) -> Optional[Fernet]:
        """Get Fernet cipher for cookie encryption."""
        if self._fernet is None and self.settings.oauth.encryption_key:
            try:
                self._fernet = Fernet(self.settings.oauth.encryption_key.encode())
            except Exception as e:
                logger.error(f"Failed to initialize Fernet cipher: {e}")
        return self._fernet

    def is_configured(self) -> bool:
        """Check if encryption is configured for secure cookie storage."""
        return bool(self.settings.oauth.encryption_key)

    def _encrypt_cookies(self, cookies: dict) -> Optional[str]:
        """Encrypt session cookies for storage."""
        if not self.fernet:
            logger.error("Encryption not configured")
            return None
        try:
            json_data = json.dumps(cookies)
            return self.fernet.encrypt(json_data.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt cookies: {e}")
            return None

    def _decrypt_cookies(self, encrypted: str) -> Optional[dict]:
        """Decrypt stored session cookies."""
        if not self.fernet:
            logger.error("Encryption not configured")
            return None
        try:
            decrypted = self.fernet.decrypt(encrypted.encode())
            return json.loads(decrypted.decode())
        except InvalidToken:
            logger.error("Invalid encryption token - cookies may be corrupted")
            return None
        except Exception as e:
            logger.error(f"Failed to decrypt cookies: {e}")
            return None

    async def login(
        self,
        db: AsyncSession,
        username: str,
        password: str,
    ) -> dict:
        """
        Login to Red Bar Radio and store session cookies.

        Args:
            db: Database session
            username: Red Bar username
            password: Red Bar password

        Returns:
            Dict with 'success', 'message', and optionally 'account_id'
        """
        if not self.is_configured():
            return {"success": False, "message": "Encryption not configured"}

        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                # First, get the login page to find any CSRF tokens
                login_page = await client.get(
                    self.LOGIN_URL,
                    headers={"User-Agent": self.USER_AGENT},
                )

                # Parse for CSRF token if present
                soup = BeautifulSoup(login_page.text, "lxml")
                csrf_token = None

                # Look for common WordPress CSRF patterns
                csrf_input = soup.select_one(
                    "input[name='_wpnonce'], input[name='csrf_token'], input[name='nonce']"
                )
                if csrf_input:
                    csrf_token = csrf_input.get("value")

                # Build login form data
                form_data = {
                    "log": username,  # WordPress standard field
                    "pwd": password,
                    "rememberme": "forever",
                    "wp-submit": "Log In",
                }

                # Try alternate field names if standard ones don't work
                # Some WordPress sites use different field names
                alt_form_data = {
                    "username": username,
                    "password": password,
                    "rememberme": "1",
                }

                if csrf_token:
                    form_data["_wpnonce"] = csrf_token
                    alt_form_data["_wpnonce"] = csrf_token

                # Submit login form
                response = await client.post(
                    self.LOGIN_URL,
                    data=form_data,
                    headers={
                        "User-Agent": self.USER_AGENT,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": self.BASE_URL,
                        "Referer": self.LOGIN_URL,
                    },
                )

                # Check if login was successful
                # WordPress typically redirects to homepage or dashboard on success
                # Handle duplicate cookie names by using the cookie jar properly
                cookies = {}
                for cookie in client.cookies.jar:
                    # Use the last value for each cookie name (most recent)
                    cookies[cookie.name] = cookie.value

                # Check for authentication cookies
                auth_cookies = [
                    c for c in cookies.keys()
                    if "wordpress_logged_in" in c.lower()
                    or "auth" in c.lower()
                    or "session" in c.lower()
                    or "user" in c.lower()
                ]

                if not auth_cookies:
                    # Try alternate form data
                    response = await client.post(
                        self.LOGIN_URL,
                        data=alt_form_data,
                        headers={
                            "User-Agent": self.USER_AGENT,
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Origin": self.BASE_URL,
                            "Referer": self.LOGIN_URL,
                        },
                    )
                    cookies = {}
                    for cookie in client.cookies.jar:
                        cookies[cookie.name] = cookie.value
                    auth_cookies = [
                        c for c in cookies.keys()
                        if "wordpress_logged_in" in c.lower()
                        or "auth" in c.lower()
                        or "session" in c.lower()
                        or "user" in c.lower()
                    ]

                if not auth_cookies:
                    # Check if response indicates login failure
                    if "incorrect" in response.text.lower() or "invalid" in response.text.lower():
                        return {"success": False, "message": "Invalid username or password"}
                    return {"success": False, "message": "Login failed - no session cookies received"}

                # Validate session by checking if we can access premium content
                is_valid = await self._validate_session_cookies(client, cookies)
                if not is_valid:
                    return {"success": False, "message": "Login appeared successful but session is not valid"}

                # Store session cookies in database
                encrypted_cookies = self._encrypt_cookies(cookies)
                if not encrypted_cookies:
                    return {"success": False, "message": "Failed to encrypt session cookies"}

                # Check for existing account
                existing = await db.execute(
                    select(PlatformAccount).where(
                        PlatformAccount.platform == "redbar",
                    )
                )
                account = existing.scalar_one_or_none()

                if account:
                    # Update existing account
                    account.account_email = username
                    account.account_name = username
                    account.access_token_encrypted = encrypted_cookies
                    account.token_expires_at = datetime.utcnow() + timedelta(days=self.SESSION_DURATION_DAYS)
                    account.is_active = True
                    account.is_premium = True  # Assume SCARS CLUB access
                    account.last_refresh_at = datetime.utcnow()
                    account.last_error = None
                else:
                    # Create new account
                    account = PlatformAccount(
                        platform="redbar",
                        account_email=username,
                        account_name=username,
                        access_token_encrypted=encrypted_cookies,
                        refresh_token_encrypted=None,
                        token_expires_at=datetime.utcnow() + timedelta(days=self.SESSION_DURATION_DAYS),
                        scopes=json.dumps(["premium"]),
                        is_active=True,
                        is_premium=True,
                    )
                    db.add(account)

                await db.commit()
                await db.refresh(account)

                logger.info(f"Red Bar login successful for user: {username}")
                return {
                    "success": True,
                    "message": "Login successful",
                    "account_id": account.id,
                    "username": username,
                }

        except Exception as e:
            logger.error(f"Red Bar login failed: {e}")
            return {"success": False, "message": f"Login error: {str(e)}"}

    async def _validate_session_cookies(
        self,
        client: httpx.AsyncClient,
        cookies: dict,
    ) -> bool:
        """Check if session cookies grant access to premium content."""
        try:
            # Try to access episodes page with cookies
            response = await client.get(
                "https://redbarradio.net/episodes",
                cookies=cookies,
                headers={"User-Agent": self.USER_AGENT},
            )

            # Check for login prompts or membership requirements
            html = response.text.lower()
            if "scarsclub membership required" in html:
                return False
            if "please log in" in html or "please login" in html:
                return False

            # If we can see episode content, session is valid
            if "episode" in html or "download" in html or "mp3" in html:
                return True

            return True  # Assume valid if no blockers detected

        except Exception as e:
            logger.warning(f"Session validation failed: {e}")
            return False

    async def get_session_cookies(
        self,
        db: AsyncSession,
    ) -> Optional[dict]:
        """Get stored session cookies for Red Bar."""
        try:
            result = await db.execute(
                select(PlatformAccount).where(
                    PlatformAccount.platform == "redbar",
                    PlatformAccount.is_active == True,
                )
            )
            account = result.scalar_one_or_none()

            if not account:
                return None

            # Check if session might be expired
            if account.token_expires_at and datetime.utcnow() > account.token_expires_at:
                logger.warning("Red Bar session has expired")
                return None

            cookies = self._decrypt_cookies(account.access_token_encrypted)
            if cookies:
                account.mark_used()
                await db.commit()

            return cookies

        except Exception as e:
            logger.error(f"Failed to get Red Bar session: {e}")
            return None

    async def get_status(
        self,
        db: AsyncSession,
    ) -> dict:
        """Get Red Bar login status."""
        try:
            result = await db.execute(
                select(PlatformAccount).where(
                    PlatformAccount.platform == "redbar",
                )
            )
            account = result.scalar_one_or_none()

            if not account:
                return {"logged_in": False}

            # Check if session is expired
            is_expired = (
                account.token_expires_at
                and datetime.utcnow() > account.token_expires_at
            )

            return {
                "logged_in": account.is_active and not is_expired,
                "username": account.account_name,
                "expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
                "is_premium": account.is_premium,
                "last_used": account.last_used_at.isoformat() if account.last_used_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to get Red Bar status: {e}")
            return {"logged_in": False, "error": str(e)}

    async def logout(
        self,
        db: AsyncSession,
    ) -> dict:
        """Logout from Red Bar (delete stored session)."""
        try:
            result = await db.execute(
                select(PlatformAccount).where(
                    PlatformAccount.platform == "redbar",
                )
            )
            account = result.scalar_one_or_none()

            if account:
                await db.delete(account)
                await db.commit()
                logger.info("Red Bar session deleted")

            return {"success": True, "message": "Logged out successfully"}

        except Exception as e:
            logger.error(f"Red Bar logout failed: {e}")
            return {"success": False, "message": str(e)}

    async def validate_session(
        self,
        db: AsyncSession,
    ) -> bool:
        """
        Validate that stored session is still working.

        Returns:
            True if session is valid, False otherwise
        """
        cookies = await self.get_session_cookies(db)
        if not cookies:
            return False

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await self._validate_session_cookies(client, cookies)
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False


# Singleton instance
_redbar_auth_service: Optional[RedBarAuthService] = None


def get_redbar_auth_service() -> RedBarAuthService:
    """Get or create the Red Bar auth service singleton."""
    global _redbar_auth_service
    if _redbar_auth_service is None:
        _redbar_auth_service = RedBarAuthService()
    return _redbar_auth_service
