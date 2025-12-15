"""API endpoints for managing hidden channels."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, delete

from app.api.deps import DbSession, CurrentUserOrDefault
from app.models import UserHiddenChannel
from app.schemas.hidden_channel import (
    HiddenChannelCreate,
    HiddenChannelResponse,
    HiddenChannelListResponse,
)

router = APIRouter(prefix="/hidden-channels", tags=["hidden-channels"])


@router.get("", response_model=HiddenChannelListResponse)
async def list_hidden_channels(
    db: DbSession,
    user: CurrentUserOrDefault,
):
    """List all hidden channels for the current user."""
    query = (
        select(UserHiddenChannel)
        .where(UserHiddenChannel.user_id == user.id)
        .order_by(UserHiddenChannel.hidden_at.desc())
    )
    result = await db.execute(query)
    channels = result.scalars().all()

    return HiddenChannelListResponse(
        items=[HiddenChannelResponse.model_validate(c) for c in channels],
        total=len(channels),
    )


@router.post("", response_model=HiddenChannelResponse, status_code=201)
async def hide_channel(
    data: HiddenChannelCreate,
    db: DbSession,
    user: CurrentUserOrDefault,
):
    """Hide a channel from Discover results."""
    # Check if already hidden
    existing = await db.execute(
        select(UserHiddenChannel).where(
            UserHiddenChannel.user_id == user.id,
            UserHiddenChannel.platform == data.platform,
            UserHiddenChannel.channel_id == data.channel_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Channel is already hidden",
        )

    # Create new hidden channel entry
    hidden_channel = UserHiddenChannel(
        user_id=user.id,
        platform=data.platform,
        channel_id=data.channel_id,
        channel_name=data.channel_name,
        channel_avatar_url=data.channel_avatar_url,
    )
    db.add(hidden_channel)
    await db.commit()
    await db.refresh(hidden_channel)

    return HiddenChannelResponse.model_validate(hidden_channel)


@router.delete("/{platform}/{channel_id}", status_code=204)
async def unhide_channel(
    platform: str,
    channel_id: str,
    db: DbSession,
    user: CurrentUserOrDefault,
):
    """Unhide a channel (remove from hidden list)."""
    result = await db.execute(
        delete(UserHiddenChannel).where(
            UserHiddenChannel.user_id == user.id,
            UserHiddenChannel.platform == platform,
            UserHiddenChannel.channel_id == channel_id,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Hidden channel not found",
        )
