"""Collections management API endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from loguru import logger

from app.api.deps import DbSession
from app.models import Collection, CollectionItem
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionWithItemsResponse,
    CollectionListResponse,
    CollectionItemCreate,
    CollectionItemUpdate,
    CollectionItemResponse,
    ReorderItemsRequest,
    QuickAddRequest,
    CollectionExport,
)

router = APIRouter()

FAVORITES_NAME = "Favorites"


def _collection_to_response(collection: Collection) -> CollectionResponse:
    """Convert Collection model to response schema."""
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        cover_url=collection.cover_url,
        sort_order=collection.sort_order,
        item_count=collection.item_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def _item_to_response(item: CollectionItem) -> CollectionItemResponse:
    """Convert CollectionItem model to response schema."""
    return CollectionItemResponse(
        id=item.id,
        item_type=item.item_type,
        url=item.url,
        thumbnail_url=item.thumbnail_url,
        title=item.title,
        source_url=item.source_url,
        domain=item.domain,
        embed_type=item.embed_type,
        video_id=item.video_id,
        sort_order=item.sort_order,
        added_at=item.added_at,
    )


@router.get("", response_model=CollectionListResponse)
async def list_collections(db: DbSession) -> CollectionListResponse:
    """List all collections with item counts."""
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .order_by(Collection.sort_order, Collection.name)
    )
    collections = result.scalars().all()

    return CollectionListResponse(
        items=[_collection_to_response(c) for c in collections],
        total=len(collections)
    )


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(data: CollectionCreate, db: DbSession) -> CollectionResponse:
    """Create a new collection."""
    # Check for duplicate name
    existing = await db.execute(select(Collection).where(Collection.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Collection with name '{data.name}' already exists"
        )

    collection = Collection.create(
        name=data.name,
        description=data.description,
    )
    db.add(collection)
    await db.flush()
    await db.refresh(collection)

    logger.info(f"Created collection '{collection.name}' (id={collection.id})")
    return _collection_to_response(collection)


@router.get("/{collection_id}", response_model=CollectionWithItemsResponse)
async def get_collection(collection_id: int, db: DbSession) -> CollectionWithItemsResponse:
    """Get a collection with all its items."""
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    return CollectionWithItemsResponse(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        cover_url=collection.cover_url,
        sort_order=collection.sort_order,
        item_count=collection.item_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        items=[_item_to_response(item) for item in collection.items],
    )


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int, data: CollectionUpdate, db: DbSession
) -> CollectionResponse:
    """Update a collection's name, description, or sort order."""
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)

    collection.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(collection)

    return _collection_to_response(collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: int, db: DbSession) -> None:
    """Delete a collection and all its items."""
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    logger.info(f"Deleting collection '{collection.name}' (id={collection.id})")
    await db.delete(collection)


# --- Collection Items ---


@router.post("/{collection_id}/items", response_model=CollectionItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_collection(
    collection_id: int, data: CollectionItemCreate, db: DbSession
) -> CollectionItemResponse:
    """Add an item (image or video) to a collection."""
    # Verify collection exists
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    # Check for duplicate URL in this collection
    existing = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.url == data.url
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item with this URL already exists in the collection"
        )

    # Get max sort order
    max_order = 0
    if collection.items:
        max_order = max(item.sort_order for item in collection.items)

    item = CollectionItem(
        collection_id=collection_id,
        item_type=data.item_type,
        url=data.url,
        thumbnail_url=data.thumbnail_url,
        title=data.title,
        source_url=data.source_url,
        domain=data.domain,
        embed_type=data.embed_type,
        video_id=data.video_id,
        sort_order=max_order + 1,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)

    # Update collection cover if this is the first item
    if not collection.cover_url:
        collection.cover_url = data.thumbnail_url or data.url
        collection.updated_at = datetime.utcnow()

    return _item_to_response(item)


@router.put("/{collection_id}/items/{item_id}", response_model=CollectionItemResponse)
async def update_item(
    collection_id: int, item_id: int, data: CollectionItemUpdate, db: DbSession
) -> CollectionItemResponse:
    """Update an item's sort order."""
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.id == item_id,
            CollectionItem.collection_id == collection_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found in collection {collection_id}"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)

    return _item_to_response(item)


@router.delete("/{collection_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(collection_id: int, item_id: int, db: DbSession) -> None:
    """Remove an item from a collection."""
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.id == item_id,
            CollectionItem.collection_id == collection_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found in collection {collection_id}"
        )

    await db.delete(item)


@router.post("/{collection_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_items(
    collection_id: int, data: ReorderItemsRequest, db: DbSession
) -> None:
    """Bulk reorder items in a collection."""
    # Verify collection exists
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    # Update sort orders
    for order, item_id in enumerate(data.item_ids):
        result = await db.execute(
            select(CollectionItem).where(
                CollectionItem.id == item_id,
                CollectionItem.collection_id == collection_id
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.sort_order = order

    await db.flush()


# --- Quick Add & Export ---


@router.post("/quick-add", response_model=CollectionItemResponse, status_code=status.HTTP_201_CREATED)
async def quick_add_to_favorites(data: QuickAddRequest, db: DbSession) -> CollectionItemResponse:
    """Quick-add an item to the default Favorites collection (creates it if needed)."""
    # Get or create Favorites collection
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .where(Collection.name == FAVORITES_NAME)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        collection = Collection.create(name=FAVORITES_NAME, description="Quick-saved favorites")
        db.add(collection)
        await db.flush()
        await db.refresh(collection)
        logger.info(f"Created default '{FAVORITES_NAME}' collection")

    # Check for duplicate
    existing = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.url == data.url
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already in Favorites"
        )

    # Get max sort order
    max_order = 0
    if collection.items:
        max_order = max(item.sort_order for item in collection.items)

    item = CollectionItem(
        collection_id=collection.id,
        item_type=data.item_type,
        url=data.url,
        thumbnail_url=data.thumbnail_url,
        title=data.title,
        source_url=data.source_url,
        domain=data.domain,
        embed_type=data.embed_type,
        video_id=data.video_id,
        sort_order=max_order + 1,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)

    # Update collection cover if first item
    if not collection.cover_url:
        collection.cover_url = data.thumbnail_url or data.url
        collection.updated_at = datetime.utcnow()

    return _item_to_response(item)


@router.get("/export/{collection_id}")
async def export_collection(collection_id: int, db: DbSession) -> JSONResponse:
    """Export a collection as JSON."""
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    export_data = CollectionExport(
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        item_count=collection.item_count,
        created_at=collection.created_at,
        items=[_item_to_response(item) for item in collection.items],
    )

    return JSONResponse(
        content=export_data.model_dump(mode="json"),
        headers={
            "Content-Disposition": f'attachment; filename="{collection.slug}.json"'
        }
    )
