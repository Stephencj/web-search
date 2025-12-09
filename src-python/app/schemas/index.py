"""Pydantic schemas for Index operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class RankingConfig(BaseModel):
    """Ranking configuration for an index."""
    domain_boosts: dict[str, float] = Field(
        default_factory=dict,
        description="Domain boost multipliers, e.g., {'arxiv.org': 1.5}"
    )
    recency_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for recency in ranking (0-1)"
    )
    custom_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Custom ranking weights for future use"
    )


class IndexBase(BaseModel):
    """Base schema for Index."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    ranking_config: Optional[RankingConfig] = None


class IndexCreate(IndexBase):
    """Schema for creating an Index."""
    pass


class IndexUpdate(BaseModel):
    """Schema for updating an Index."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    ranking_config: Optional[RankingConfig] = None
    is_active: Optional[bool] = None


class IndexResponse(BaseModel):
    """Schema for Index response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    ranking_config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields
    source_count: int = 0
    document_count: int = 0


class IndexListResponse(BaseModel):
    """Schema for listing indexes."""
    items: list[IndexResponse]
    total: int
