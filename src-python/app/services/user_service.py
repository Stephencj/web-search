"""User service - handles user management and authentication."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from loguru import logger
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, AppSetting
from app.models.user_session import UserSession, SESSION_DURATION_DAYS
from app.models.user_watch_state import UserWatchState


# Settings keys
AUTH_MODE_KEY = "auth_mode"
GUEST_ACCESS_KEY = "allow_guest_access"

# Default values
DEFAULT_AUTH_MODE = "open"  # "open" or "protected"
DEFAULT_GUEST_ACCESS = True


class UserService:
    """Service for user management and authentication."""

    # Rate limiting (in-memory, resets on restart)
    _login_attempts: dict[str, list[datetime]] = {}
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_WINDOW_MINUTES = 1

    async def get_auth_mode(self, db: AsyncSession) -> str:
        """Get the current authentication mode."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == AUTH_MODE_KEY)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value.get("mode", DEFAULT_AUTH_MODE)
        return DEFAULT_AUTH_MODE

    async def set_auth_mode(self, db: AsyncSession, mode: str) -> None:
        """Set the authentication mode."""
        if mode not in ("open", "protected"):
            raise ValueError("Invalid auth mode. Must be 'open' or 'protected'.")

        result = await db.execute(
            select(AppSetting).where(AppSetting.key == AUTH_MODE_KEY)
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = {"mode": mode}
        else:
            setting = AppSetting(key=AUTH_MODE_KEY, value={"mode": mode})
            db.add(setting)

        await db.commit()
        logger.info(f"Auth mode set to: {mode}")

    async def is_guest_access_allowed(self, db: AsyncSession) -> bool:
        """Check if guest access is allowed."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == GUEST_ACCESS_KEY)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value.get("allowed", DEFAULT_GUEST_ACCESS)
        return DEFAULT_GUEST_ACCESS

    # === User Management ===

    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        display_name: str,
        pin: Optional[str] = None,
        is_admin: bool = False,
        avatar_color: str = "#6366f1",
    ) -> User:
        """Create a new user."""
        # Check if username exists
        existing = await self.get_user_by_username(db, username)
        if existing:
            raise ValueError(f"Username '{username}' already exists")

        pin_hash = None
        if pin:
            pin_hash = self._hash_pin(pin)

        user = User(
            username=username,
            display_name=display_name,
            pin_hash=pin_hash,
            is_admin=is_admin,
            avatar_color=avatar_color,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Created user: {username} (admin={is_admin})")
        return user

    async def update_user(
        self,
        db: AsyncSession,
        user_id: int,
        display_name: Optional[str] = None,
        avatar_color: Optional[str] = None,
        is_admin: Optional[bool] = None,
    ) -> Optional[User]:
        """Update user profile."""
        user = await self.get_user(db, user_id)
        if not user:
            return None

        if display_name is not None:
            user.display_name = display_name
        if avatar_color is not None:
            user.avatar_color = avatar_color
        if is_admin is not None:
            user.is_admin = is_admin

        await db.commit()
        await db.refresh(user)
        logger.info(f"Updated user: {user.username}")
        return user

    async def set_user_pin(
        self,
        db: AsyncSession,
        user_id: int,
        new_pin: Optional[str],
        current_pin: Optional[str] = None,
    ) -> bool:
        """Set or remove user PIN."""
        user = await self.get_user(db, user_id)
        if not user:
            return False

        # If user has a PIN, verify current PIN
        if user.pin_hash and current_pin:
            if not self._verify_pin(current_pin, user.pin_hash):
                logger.warning(f"PIN change failed for user {user.username}: incorrect current PIN")
                return False

        # Set new PIN (or remove if None)
        if new_pin:
            user.pin_hash = self._hash_pin(new_pin)
            logger.info(f"PIN set for user: {user.username}")
        else:
            user.pin_hash = None
            logger.info(f"PIN removed for user: {user.username}")

        await db.commit()
        return True

    async def delete_user(self, db: AsyncSession, user_id: int) -> bool:
        """Delete a user and all their data."""
        user = await self.get_user(db, user_id)
        if not user:
            return False

        username = user.username

        # Delete user (cascade will handle sessions and watch states)
        await db.delete(user)
        await db.commit()

        logger.info(f"Deleted user: {username}")
        return True

    async def get_user(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def list_users(self, db: AsyncSession) -> list[User]:
        """List all users."""
        result = await db.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def get_user_count(self, db: AsyncSession) -> int:
        """Get total user count."""
        result = await db.execute(select(func.count(User.id)))
        return result.scalar() or 0

    async def get_or_create_default_user(self, db: AsyncSession) -> User:
        """Get or create the default user for migration/initial setup."""
        # Check if any user exists
        users = await self.list_users(db)
        if users:
            # Return first admin user, or first user
            for user in users:
                if user.is_admin:
                    return user
            return users[0]

        # Create default admin user
        return await self.create_user(
            db,
            username="admin",
            display_name="Admin",
            is_admin=True,
            avatar_color="#6366f1",
        )

    # === Authentication ===

    async def authenticate(
        self,
        db: AsyncSession,
        username: str,
        pin: Optional[str] = None,
    ) -> Optional[User]:
        """
        Authenticate a user with username and optional PIN.

        Returns User if successful, None otherwise.
        """
        # Rate limiting check
        if self._is_rate_limited(username):
            logger.warning(f"Login rate limited for user: {username}")
            return None

        user = await self.get_user_by_username(db, username)
        if not user:
            self._record_login_attempt(username)
            return None

        # Check PIN
        if user.pin_hash:
            # User has PIN set - must provide correct PIN
            if not pin or not self._verify_pin(pin, user.pin_hash):
                self._record_login_attempt(username)
                logger.warning(f"Failed login attempt for user: {username}")
                return None
        else:
            # User has no PIN - in open mode, allow login without PIN
            auth_mode = await self.get_auth_mode(db)
            if auth_mode == "protected" and pin:
                # In protected mode with PIN provided but user has none - fail
                self._record_login_attempt(username)
                return None

        # Successful authentication
        user.mark_login()
        await db.commit()
        logger.info(f"User authenticated: {username}")
        return user

    # === Session Management ===

    async def create_session(
        self,
        db: AsyncSession,
        user: User,
        device_name: Optional[str] = None,
    ) -> str:
        """Create a new session for a user. Returns the session token."""
        token = secrets.token_urlsafe(48)  # 64 chars base64

        session = UserSession(
            user_id=user.id,
            token=token,
            device_name=device_name,
            expires_at=UserSession.default_expiry(),
        )
        db.add(session)
        await db.commit()

        logger.info(f"Created session for user: {user.username}")
        return token

    async def validate_session(self, db: AsyncSession, token: str) -> Optional[User]:
        """Validate a session token and return the associated user."""
        if not token:
            return None

        result = await db.execute(
            select(UserSession)
            .where(UserSession.token == token)
            .options()  # Will lazy load user
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        if session.is_expired:
            # Clean up expired session
            await db.delete(session)
            await db.commit()
            return None

        # Refresh session activity
        session.refresh()
        await db.commit()

        # Load and return user
        result = await db.execute(select(User).where(User.id == session.user_id))
        return result.scalar_one_or_none()

    async def logout(self, db: AsyncSession, token: str) -> bool:
        """Invalidate a session."""
        result = await db.execute(
            select(UserSession).where(UserSession.token == token)
        )
        session = result.scalar_one_or_none()

        if session:
            await db.delete(session)
            await db.commit()
            logger.info(f"Session invalidated for user_id: {session.user_id}")
            return True

        return False

    async def logout_all(self, db: AsyncSession, user_id: int) -> int:
        """Invalidate all sessions for a user. Returns count of sessions deleted."""
        result = await db.execute(
            delete(UserSession).where(UserSession.user_id == user_id)
        )
        await db.commit()
        count = result.rowcount
        logger.info(f"Invalidated {count} sessions for user_id: {user_id}")
        return count

    async def cleanup_expired_sessions(self, db: AsyncSession) -> int:
        """Remove all expired sessions. Returns count deleted."""
        result = await db.execute(
            delete(UserSession).where(UserSession.expires_at < datetime.utcnow())
        )
        await db.commit()
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count

    # === Helper Methods ===

    def _hash_pin(self, pin: str) -> str:
        """Hash a PIN using bcrypt."""
        return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

    def _verify_pin(self, pin: str, pin_hash: str) -> bool:
        """Verify a PIN against its hash."""
        try:
            return bcrypt.checkpw(pin.encode(), pin_hash.encode())
        except Exception:
            return False

    def _is_rate_limited(self, username: str) -> bool:
        """Check if login attempts are rate limited."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.LOGIN_WINDOW_MINUTES)

        attempts = self._login_attempts.get(username, [])
        # Filter to recent attempts
        recent = [t for t in attempts if t > cutoff]
        self._login_attempts[username] = recent

        return len(recent) >= self.MAX_LOGIN_ATTEMPTS

    def _record_login_attempt(self, username: str) -> None:
        """Record a failed login attempt."""
        if username not in self._login_attempts:
            self._login_attempts[username] = []
        self._login_attempts[username].append(datetime.utcnow())


# Singleton instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get the user service singleton."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
