"""Authentication API endpoints."""

from typing import Optional

from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import DbSession
from app.services.user_service import get_user_service


router = APIRouter()


# === Schemas ===

class AuthModeResponse(BaseModel):
    """Auth mode response."""
    mode: str  # "open" or "protected"
    allow_guest: bool


class UserPublic(BaseModel):
    """Public user info for login screen."""
    id: int
    username: str
    display_name: str
    avatar_color: str
    has_pin: bool

    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    """List of users for login screen."""
    users: list[UserPublic]
    auth_mode: str


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    pin: Optional[str] = None
    device_name: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response."""
    success: bool
    token: Optional[str] = None
    user: Optional[UserPublic] = None
    message: Optional[str] = None


class CurrentUserResponse(BaseModel):
    """Current user response."""
    authenticated: bool
    user: Optional[UserPublic] = None


# === Endpoints ===

@router.get("/mode", response_model=AuthModeResponse)
async def get_auth_mode(db: DbSession) -> AuthModeResponse:
    """Get current authentication mode."""
    service = get_user_service()
    mode = await service.get_auth_mode(db)
    allow_guest = await service.is_guest_access_allowed(db)
    return AuthModeResponse(mode=mode, allow_guest=allow_guest)


@router.get("/users", response_model=UsersListResponse)
async def list_users_for_login(db: DbSession) -> UsersListResponse:
    """List users for the login screen."""
    service = get_user_service()

    users = await service.list_users(db)
    auth_mode = await service.get_auth_mode(db)

    return UsersListResponse(
        users=[
            UserPublic(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                avatar_color=u.avatar_color,
                has_pin=u.has_pin,
            )
            for u in users
        ],
        auth_mode=auth_mode,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: DbSession,
) -> LoginResponse:
    """Authenticate and create a session."""
    service = get_user_service()

    # Authenticate user
    user = await service.authenticate(db, request.username, request.pin)
    if not user:
        return LoginResponse(
            success=False,
            message="Invalid username or PIN",
        )

    # Create session
    token = await service.create_session(db, user, request.device_name)

    # Set cookie for browser clients
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return LoginResponse(
        success=True,
        token=token,
        user=UserPublic(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_color=user.avatar_color,
            has_pin=user.has_pin,
        ),
    )


@router.post("/logout")
async def logout(
    response: Response,
    db: DbSession,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
) -> dict:
    """Invalidate current session."""
    service = get_user_service()

    # Get token from header or cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token

    if token:
        await service.logout(db, token)

    # Clear cookie
    response.delete_cookie("session_token")

    return {"success": True}


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    db: DbSession,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
) -> CurrentUserResponse:
    """Get the currently authenticated user."""
    service = get_user_service()

    # Get token from header or cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token

    if not token:
        return CurrentUserResponse(authenticated=False)

    user = await service.validate_session(db, token)
    if not user:
        return CurrentUserResponse(authenticated=False)

    return CurrentUserResponse(
        authenticated=True,
        user=UserPublic(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_color=user.avatar_color,
            has_pin=user.has_pin,
        ),
    )


@router.post("/session/validate")
async def validate_session(
    db: DbSession,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
) -> dict:
    """Validate if a session token is still valid."""
    service = get_user_service()

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token

    if not token:
        return {"valid": False}

    user = await service.validate_session(db, token)
    return {"valid": user is not None}
