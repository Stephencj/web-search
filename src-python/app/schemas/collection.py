"""Pydantic schemas for Collection operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class CollectionItemCreate(BaseModel):
    """Schema for adding an item to a collection."""
    item_type: Literal["image", "video"] = Field(..., description="Type of media item")
    url: str = Field(..., description="Primary URL (image_url or video_url)")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL for videos")
    title: Optional[str] = Field(None, max_length=500, description="Item title")
    source_url: Optional[str] = Field(None, description="Source page URL")
    domain: Optional[str] = Field(None, max_length=200, description="Source domain")
    embed_type: Optional[str] = Field(None, max_length=20, description="Video embed type")
    video_id: Optional[str] = Field(None, max_length=50, description="Video platform ID")


class CollectionItemUpdate(BaseModel):
    """Schema for updating an item in a collection."""
    sort_order: Optional[int] = Field(None, ge=0, description="Item sort order")


class CollectionItemResponse(BaseModel):
    """Schema for collection item response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str
    url: str
    thumbnail_url: Optional[str]
    title: Optional[str]
    source_url: Optional[str]
    domain: Optional[str]
    embed_type: Optional[str]
    video_id: Optional[str]
    sort_order: int
    added_at: datetime


class CollectionCreate(BaseModel):
    """Schema for creating a collection."""
    name: str = Field(..., min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Collection description")


class CollectionUpdate(BaseModel):
    """Schema for updating a collection."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0)


class CollectionResponse(BaseModel):
    """Schema for collection response (without items)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    cover_url: Optional[str]
    sort_order: int
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class CollectionWithItemsResponse(CollectionResponse):
    """Schema for collection response with all items."""
    items: list[CollectionItemResponse] = []


class CollectionListResponse(BaseModel):
    """Schema for listing collections."""
    items: list[CollectionResponse]
    total: int


class ReorderItemsRequest(BaseModel):
    """Schema for bulk reordering items."""
    item_ids: list[int] = Field(..., description="Item IDs in desired order")


class QuickAddRequest(BaseModel):
    """Schema for quick-add to default Favorites collection."""
    item_type: Literal["image", "video"]
    url: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None
    domain: Optional[str] = None
    embed_type: Optional[str] = None
    video_id: Optional[str] = None


class CollectionExport(BaseModel):
    """Schema for collection export."""
    name: str
    slug: str
    description: Optional[str]
    item_count: int
    created_at: datetime
    items: list[CollectionItemResponse]
