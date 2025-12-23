"""Index management API endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models import Index, Source
from app.schemas.index import (
    IndexCreate,
    IndexUpdate,
    IndexResponse,
    IndexListResponse,
)
from app.core.search import get_meilisearch_client

router = APIRouter()


def _index_to_response(index: Index, document_count: int = 0) -> IndexResponse:
    """Convert Index model to response schema."""
    # Ensure ranking_config is never None
    ranking_config = index.ranking_config or {
        "domain_boosts": {},
        "recency_weight": 0.3,
        "custom_weights": {}
    }
    return IndexResponse(
        id=index.id,
        name=index.name,
        slug=index.slug,
        description=index.description,
        ranking_config=ranking_config,
        is_active=index.is_active,
        created_at=index.created_at,
        updated_at=index.updated_at,
        source_count=len(index.sources) if index.sources else 0,
        document_count=document_count,
    )


async def _get_document_count(slug: str) -> int:
    """Get document count from Meilisearch for an index."""
    try:
        meili = get_meilisearch_client()
        stats = await meili.get_stats(slug)
        return stats.get("document_count", 0)
    except Exception:
        return 0


@router.get("", response_model=IndexListResponse)
async def list_indexes(db: DbSession) -> IndexListResponse:
    """List all indexes."""
    result = await db.execute(
        select(Index).options(selectinload(Index.sources)).order_by(Index.name)
    )
    indexes = result.scalars().all()

    # Fetch document counts from Meilisearch in parallel
    counts = await asyncio.gather(*[_get_document_count(idx.slug) for idx in indexes])

    return IndexListResponse(
        items=[_index_to_response(idx, count) for idx, count in zip(indexes, counts)],
        total=len(indexes)
    )


@router.post("", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def create_index(data: IndexCreate, db: DbSession) -> IndexResponse:
    """Create a new index."""
    # Check for duplicate name
    existing = await db.execute(select(Index).where(Index.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Index with name '{data.name}' already exists"
        )

    # Create index
    index = Index.create(
        name=data.name,
        description=data.description,
        ranking_config=data.ranking_config.model_dump() if data.ranking_config else None
    )
    db.add(index)
    await db.flush()
    await db.refresh(index)

    return _index_to_response(index)


@router.get("/{index_id}", response_model=IndexResponse)
async def get_index(index_id: int, db: DbSession) -> IndexResponse:
    """Get an index by ID."""
    result = await db.execute(
        select(Index)
        .options(selectinload(Index.sources))
        .where(Index.id == index_id)
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index with id {index_id} not found"
        )

    document_count = await _get_document_count(index.slug)
    return _index_to_response(index, document_count)


@router.put("/{index_id}", response_model=IndexResponse)
async def update_index(index_id: int, data: IndexUpdate, db: DbSession) -> IndexResponse:
    """Update an index."""
    result = await db.execute(
        select(Index)
        .options(selectinload(Index.sources))
        .where(Index.id == index_id)
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index with id {index_id} not found"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    if "ranking_config" in update_data and update_data["ranking_config"]:
        update_data["ranking_config"] = data.ranking_config.model_dump()

    for field, value in update_data.items():
        setattr(index, field, value)

    await db.flush()
    await db.refresh(index)

    return _index_to_response(index)


@router.delete("/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(index_id: int, db: DbSession) -> None:
    """Delete an index and all its sources."""
    result = await db.execute(select(Index).where(Index.id == index_id))
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index with id {index_id} not found"
        )

    await db.delete(index)


@router.get("/{index_id}/stats")
async def get_index_stats(index_id: int, db: DbSession) -> dict:
    """Get statistics for an index."""
    result = await db.execute(
        select(Index)
        .options(selectinload(Index.sources))
        .where(Index.id == index_id)
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index with id {index_id} not found"
        )

    # Calculate stats
    total_pages = sum(s.page_count for s in index.sources)
    active_sources = sum(1 for s in index.sources if s.is_active)
    document_count = await _get_document_count(index.slug)

    return {
        "index_id": index.id,
        "name": index.name,
        "source_count": len(index.sources),
        "active_sources": active_sources,
        "total_pages": total_pages,
        "document_count": document_count,
    }
