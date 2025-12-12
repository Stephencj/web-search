"""Source management API endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models import Index, Source
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse

router = APIRouter()


def _source_to_response(source: Source) -> SourceResponse:
    """Convert Source model to response schema."""
    return SourceResponse(
        id=source.id,
        index_id=source.index_id,
        url=source.url,
        source_type=source.source_type,
        name=source.name,
        crawl_depth=source.crawl_depth,
        crawl_frequency=source.crawl_frequency,
        max_pages=source.max_pages,
        include_patterns=source.include_patterns or [],
        exclude_patterns=source.exclude_patterns or [],
        respect_robots=source.respect_robots,
        crawl_mode=source.crawl_mode,
        is_active=source.is_active,
        last_crawl_at=source.last_crawl_at,
        page_count=source.page_count,
        error_count=source.error_count,
        last_error=source.last_error,
        created_at=source.created_at,
        updated_at=source.updated_at,
        domain=source.domain,
        display_name=source.display_name,
    )


@router.get("/by-index/{index_id}", response_model=list[SourceResponse])
async def list_sources_by_index(index_id: int, db: DbSession) -> list[SourceResponse]:
    """List all sources for an index."""
    # Verify index exists
    index_result = await db.execute(select(Index).where(Index.id == index_id))
    if not index_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index with id {index_id} not found"
        )

    result = await db.execute(
        select(Source)
        .where(Source.index_id == index_id)
        .order_by(Source.created_at.desc())
    )
    sources = result.scalars().all()

    return [_source_to_response(s) for s in sources]


@router.post("/by-index/{index_id}", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(index_id: int, data: SourceCreate, db: DbSession) -> SourceResponse:
    """Create a new source for an index."""
    # Verify index exists
    index_result = await db.execute(select(Index).where(Index.id == index_id))
    if not index_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index with id {index_id} not found"
        )

    # Check for duplicate URL in this index
    existing = await db.execute(
        select(Source).where(
            Source.index_id == index_id,
            Source.url == data.url
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Source with URL '{data.url}' already exists in this index"
        )

    # Create source
    source = Source(
        index_id=index_id,
        **data.model_dump()
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    return _source_to_response(source)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int, db: DbSession) -> SourceResponse:
    """Get a source by ID."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id {source_id} not found"
        )

    return _source_to_response(source)


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: int, data: SourceUpdate, db: DbSession) -> SourceResponse:
    """Update a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id {source_id} not found"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.flush()
    await db.refresh(source)

    return _source_to_response(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: int, db: DbSession) -> None:
    """Delete a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id {source_id} not found"
        )

    await db.delete(source)


@router.post("/{source_id}/test")
async def test_source(source_id: int, db: DbSession) -> dict:
    """Test crawl a single page from this source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id {source_id} not found"
        )

    # TODO: Implement test crawl
    return {
        "status": "not_implemented",
        "message": "Test crawl functionality coming in Phase 2"
    }
