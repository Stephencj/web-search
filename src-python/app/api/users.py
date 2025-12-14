"""User management API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.services.user_service import get_user_service


router = APIRouter()


# === Schemas ===

class UserResponse(BaseModel):
    """Full user response."""
    id: int
    username: str
    display_name: str
    avatar_color: str
    has_pin: bool
    is_admin: bool
    created_at: str
    last_login_at: Optional[str] = None

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    """Create user request."""
    username: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    pin: Optional[str] = Field(None, min_length=4, max_length=20)
    is_admin: bool = False
    avatar_color: str = "#6366f1"


class UpdateUserRequest(BaseModel):
    """Update user request."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_color: Optional[str] = None
    is_admin: Optional[bool] = None


class SetPinRequest(BaseModel):
    """Set/change PIN request."""
    new_pin: Optional[str] = Field(None, min_length=4, max_length=20)
    current_pin: Optional[str] = None


class UsersListResponse(BaseModel):
    """List of users response."""
    users: list[UserResponse]
    total: int


# === Endpoints ===

@router.get("", response_model=UsersListResponse)
async def list_users(db: DbSession) -> UsersListResponse:
    """List all users."""
    service = get_user_service()
    users = await service.list_users(db)

    return UsersListResponse(
        users=[
            UserResponse(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                avatar_color=u.avatar_color,
                has_pin=u.has_pin,
                is_admin=u.is_admin,
                created_at=u.created_at.isoformat(),
                last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            )
            for u in users
        ],
        total=len(users),
    )


@router.post("", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    db: DbSession,
) -> UserResponse:
    """Create a new user."""
    service = get_user_service()

    try:
        user = await service.create_user(
            db,
            username=request.username,
            display_name=request.display_name,
            pin=request.pin,
            is_admin=request.is_admin,
            avatar_color=request.avatar_color,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_color=user.avatar_color,
        has_pin=user.has_pin,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: DbSession) -> UserResponse:
    """Get user by ID."""
    service = get_user_service()
    user = await service.get_user(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_color=user.avatar_color,
        has_pin=user.has_pin,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db: DbSession,
) -> UserResponse:
    """Update user profile."""
    service = get_user_service()

    user = await service.update_user(
        db,
        user_id,
        display_name=request.display_name,
        avatar_color=request.avatar_color,
        is_admin=request.is_admin,
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_color=user.avatar_color,
        has_pin=user.has_pin,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: DbSession) -> dict:
    """Delete a user."""
    service = get_user_service()

    # Check user count to prevent deleting last user
    count = await service.get_user_count(db)
    if count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the last user"
        )

    success = await service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True}


@router.put("/{user_id}/pin")
async def set_user_pin(
    user_id: int,
    request: SetPinRequest,
    db: DbSession,
) -> dict:
    """Set or remove user PIN."""
    service = get_user_service()

    success = await service.set_user_pin(
        db,
        user_id,
        new_pin=request.new_pin,
        current_pin=request.current_pin,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to update PIN. Check current PIN is correct."
        )

    return {"success": True, "has_pin": request.new_pin is not None}
