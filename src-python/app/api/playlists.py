"""Playlists API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from app.api.deps import DbSession
from app.models import Playlist
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistCreateFromUrl,
    PlaylistUpdate,
    PlaylistResponse,
    PlaylistListResponse,
    PlaylistSyncResult,
)
from app.services.playlist_service import get_playlist_service

router = APIRouter()


def _playlist_to_response(playlist: Playlist) -> PlaylistResponse:
    """Convert Playlist model to response schema."""
    return PlaylistResponse(
        id=playlist.id,
        platform=playlist.platform,
        playlist_id=playlist.playlist_id,
        playlist_url=playlist.playlist_url,
        name=playlist.name,
        description=playlist.description,
        thumbnail_url=playlist.thumbnail_url,
        video_count=playlist.video_count,
        channel_name=playlist.channel_name,
        channel_url=playlist.channel_url,
        is_active=playlist.is_active,
        last_synced_at=playlist.last_synced_at,
        last_sync_error=playlist.last_sync_error,
        consecutive_errors=playlist.consecutive_errors,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        display_name=playlist.display_name,
    )


@router.get("", response_model=PlaylistListResponse)
async def list_playlists(
    db: DbSession,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> PlaylistListResponse:
    """List all followed playlists."""
    service = get_playlist_service()
    playlists = await service.list_playlists(
        db,
        platform=platform,
        is_active=is_active,
    )

    return PlaylistListResponse(
        items=[_playlist_to_response(p) for p in playlists],
        total=len(playlists),
    )


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def follow_playlist(data: PlaylistCreate, db: DbSession) -> PlaylistResponse:
    """
    Follow a playlist with full metadata.

    This endpoint accepts complete playlist metadata. For following by URL only,
    use the /from-url endpoint.
    """
    service = get_playlist_service()

    playlist = await service.follow_playlist(
        db=db,
        platform=data.platform,
        playlist_id=data.playlist_id,
        playlist_url=data.playlist_url,
        name=data.name,
        description=data.description,
        thumbnail_url=data.thumbnail_url,
        video_count=data.video_count,
        channel_name=data.channel_name,
        channel_url=data.channel_url,
    )

    return _playlist_to_response(playlist)


@router.post("/from-url", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def follow_playlist_from_url(data: PlaylistCreateFromUrl, db: DbSession) -> PlaylistResponse:
    """
    Follow a playlist by URL, auto-fetching metadata.

    The platform is detected from the URL and metadata is fetched automatically.
    """
    service = get_playlist_service()

    try:
        playlist = await service.follow_from_url(db, data.url)
        return _playlist_to_response(playlist)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(playlist_id: int, db: DbSession) -> PlaylistResponse:
    """Get a playlist by ID."""
    service = get_playlist_service()
    playlist = await service.get_playlist(db, playlist_id)

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist with id {playlist_id} not found",
        )

    return _playlist_to_response(playlist)


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    data: PlaylistUpdate,
    db: DbSession,
) -> PlaylistResponse:
    """Update a playlist."""
    service = get_playlist_service()

    update_data = data.model_dump(exclude_unset=True)
    playlist = await service.update_playlist(db, playlist_id, **update_data)

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist with id {playlist_id} not found",
        )

    return _playlist_to_response(playlist)


@router.post("/{playlist_id}/sync", response_model=PlaylistSyncResult)
async def sync_playlist(playlist_id: int, db: DbSession) -> PlaylistSyncResult:
    """
    Manually trigger a sync for a playlist.

    Fetches the latest playlist info and videos.
    """
    service = get_playlist_service()
    playlist = await service.get_playlist(db, playlist_id)

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist with id {playlist_id} not found",
        )

    result = await service.sync_playlist(db, playlist)

    return PlaylistSyncResult(
        playlist_id=playlist.id,
        playlist_name=playlist.name,
        success=result.get("success", False),
        new_videos=result.get("new_videos", 0),
        error=result.get("error"),
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_playlist(playlist_id: int, db: DbSession) -> None:
    """Unfollow a playlist."""
    service = get_playlist_service()
    deleted = await service.delete_playlist(db, playlist_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist with id {playlist_id} not found",
        )
