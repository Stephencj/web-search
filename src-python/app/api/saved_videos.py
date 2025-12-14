"""Saved Videos API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from app.api.deps import DbSession, CurrentUserOrDefault
from app.models import SavedVideo
from app.schemas.saved_video import (
    SavedVideoCreate,
    SavedVideoCreateFromUrl,
    SavedVideoUpdate,
    SavedVideoResponse,
    SavedVideoListResponse,
    SavedVideoStats,
)
from app.services.saved_video_service import get_saved_video_service

router = APIRouter()


def _video_to_response(video: SavedVideo) -> SavedVideoResponse:
    """Convert SavedVideo model to response schema."""
    return SavedVideoResponse(
        id=video.id,
        platform=video.platform,
        video_id=video.video_id,
        video_url=video.video_url,
        title=video.title,
        description=video.description,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=video.duration_seconds,
        view_count=video.view_count,
        upload_date=video.upload_date,
        channel_name=video.channel_name,
        channel_id=video.channel_id,
        channel_url=video.channel_url,
        is_watched=video.is_watched,
        watched_at=video.watched_at,
        watch_progress_seconds=video.watch_progress_seconds,
        notes=video.notes,
        saved_at=video.saved_at,
        updated_at=video.updated_at,
        duration_formatted=video.duration_formatted,
    )


@router.get("", response_model=SavedVideoListResponse)
async def list_saved_videos(
    db: DbSession,
    user: CurrentUserOrDefault,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    is_watched: Optional[bool] = Query(None, description="Filter by watched status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> SavedVideoListResponse:
    """List all saved videos with optional filtering for the current user."""
    service = get_saved_video_service()
    videos, total = await service.list_saved_videos(
        db,
        platform=platform,
        is_watched=is_watched,
        limit=limit,
        offset=offset,
        user_id=user.id,
    )

    return SavedVideoListResponse(
        items=[_video_to_response(v) for v in videos],
        total=total,
    )


@router.get("/stats", response_model=SavedVideoStats)
async def get_stats(db: DbSession, user: CurrentUserOrDefault) -> SavedVideoStats:
    """Get statistics for saved videos for the current user."""
    service = get_saved_video_service()
    stats = await service.get_stats(db, user_id=user.id)
    return SavedVideoStats(**stats)


@router.post("", response_model=SavedVideoResponse, status_code=status.HTTP_201_CREATED)
async def save_video(data: SavedVideoCreate, db: DbSession, user: CurrentUserOrDefault) -> SavedVideoResponse:
    """
    Save a video with full metadata for the current user.

    This endpoint accepts complete video metadata. For saving by URL only,
    use the /from-url endpoint.
    """
    service = get_saved_video_service()

    video = await service.save_video(
        db=db,
        platform=data.platform,
        video_id=data.video_id,
        video_url=data.video_url,
        title=data.title,
        description=data.description,
        thumbnail_url=data.thumbnail_url,
        duration_seconds=data.duration_seconds,
        view_count=data.view_count,
        upload_date=data.upload_date,
        channel_name=data.channel_name,
        channel_id=data.channel_id,
        channel_url=data.channel_url,
        notes=data.notes,
        user_id=user.id,
    )

    return _video_to_response(video)


@router.post("/from-url", response_model=SavedVideoResponse, status_code=status.HTTP_201_CREATED)
async def save_video_from_url(data: SavedVideoCreateFromUrl, db: DbSession, user: CurrentUserOrDefault) -> SavedVideoResponse:
    """
    Save a video by URL, auto-fetching metadata for the current user.

    The platform is detected from the URL and metadata is fetched automatically.
    """
    service = get_saved_video_service()

    try:
        video = await service.save_from_url(db, data.url, notes=data.notes, user_id=user.id)
        return _video_to_response(video)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/check")
async def check_if_saved(
    db: DbSession,
    user: CurrentUserOrDefault,
    platform: str = Query(..., description="Platform identifier"),
    video_id: str = Query(..., description="Platform-specific video ID"),
) -> dict:
    """Check if a video is already saved for the current user."""
    service = get_saved_video_service()
    is_saved = await service.check_if_saved(db, platform, video_id, user_id=user.id)
    return {"is_saved": is_saved, "platform": platform, "video_id": video_id}


@router.get("/{video_id}", response_model=SavedVideoResponse)
async def get_saved_video(video_id: int, db: DbSession, user: CurrentUserOrDefault) -> SavedVideoResponse:
    """Get a saved video by ID for the current user."""
    service = get_saved_video_service()
    video = await service.get_saved_video(db, video_id, user_id=user.id)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved video with id {video_id} not found",
        )

    return _video_to_response(video)


@router.put("/{video_id}", response_model=SavedVideoResponse)
async def update_saved_video(
    video_id: int,
    data: SavedVideoUpdate,
    db: DbSession,
    user: CurrentUserOrDefault,
) -> SavedVideoResponse:
    """Update a saved video for the current user."""
    service = get_saved_video_service()

    update_data = data.model_dump(exclude_unset=True)
    video = await service.update_saved_video(db, video_id, user_id=user.id, **update_data)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved video with id {video_id} not found",
        )

    return _video_to_response(video)


@router.put("/{video_id}/watched", response_model=SavedVideoResponse)
async def mark_watched(
    video_id: int,
    db: DbSession,
    user: CurrentUserOrDefault,
    progress_seconds: Optional[int] = None,
) -> SavedVideoResponse:
    """Mark a saved video as watched for the current user."""
    service = get_saved_video_service()
    video = await service.mark_watched(db, video_id, progress_seconds, user_id=user.id)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved video with id {video_id} not found",
        )

    return _video_to_response(video)


@router.put("/{video_id}/unwatched", response_model=SavedVideoResponse)
async def mark_unwatched(video_id: int, db: DbSession, user: CurrentUserOrDefault) -> SavedVideoResponse:
    """Mark a saved video as unwatched for the current user."""
    service = get_saved_video_service()
    video = await service.mark_unwatched(db, video_id, user_id=user.id)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved video with id {video_id} not found",
        )

    return _video_to_response(video)


@router.put("/{video_id}/progress", response_model=SavedVideoResponse)
async def update_watch_progress(
    video_id: int,
    db: DbSession,
    user: CurrentUserOrDefault,
    progress_seconds: int = Query(..., description="Current playback position in seconds"),
) -> SavedVideoResponse:
    """
    Update watch progress for a saved video for the current user.

    Call this periodically during playback to save the current position.
    Does not mark the video as watched - use the /watched endpoint for that.
    """
    service = get_saved_video_service()
    video = await service.update_progress(db, video_id, progress_seconds, user_id=user.id)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved video with id {video_id} not found",
        )

    return _video_to_response(video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_video(video_id: int, db: DbSession, user: CurrentUserOrDefault) -> None:
    """Delete a saved video for the current user."""
    service = get_saved_video_service()
    deleted = await service.delete_saved_video(db, video_id, user_id=user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved video with id {video_id} not found",
        )
