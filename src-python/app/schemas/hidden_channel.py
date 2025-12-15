"""Pydantic schemas for Hidden Channel operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class HiddenChannelCreate(BaseModel):
    """Schema for hiding a channel."""
    platform: str = Field(..., max_length=50)
    channel_id: str = Field(..., max_length=255)
    channel_name: str = Field(..., max_length=255)
    channel_avatar_url: Optional[str] = Field(None, max_length=500)


class HiddenChannelResponse(BaseModel):
    """Schema for hidden channel response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    channel_id: str
    channel_name: str
    channel_avatar_url: Optional[str]
    hidden_at: datetime


class HiddenChannelListResponse(BaseModel):
    """Schema for list of hidden channels."""
    items: list[HiddenChannelResponse]
    total: int
