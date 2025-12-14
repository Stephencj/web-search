"""Shared API dependencies."""

from typing import Annotated, Optional

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.services.user_service import get_user_service


# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_session)],
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
) -> Optional[User]:
    """
    Get the current user from session token (optional).

    Returns None if not authenticated.
    """
    service = get_user_service()

    # Get token from header or cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token

    if not token:
        return None

    return await service.validate_session(db, token)


async def get_current_user(
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> User:
    """
    Get the current user (required).

    Raises 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_or_default(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> User:
    """
    Get the current user, or create/return a default user.

    This is used for backward compatibility - in open mode without
    authentication, we still need a user for per-user features.
    """
    if user:
        return user

    # In open mode without auth, get or create default user
    service = get_user_service()
    return await service.get_or_create_default_user(db)


# Type aliases for auth dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
CurrentUserOrDefault = Annotated[User, Depends(get_current_user_or_default)]
