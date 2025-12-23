"""Transcription API endpoints for speech-to-text and chapter generation."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.deps import DbSession
from app.schemas.transcription import (
    TranscriptResponse,
    TranscriptWithText,
    TranscriptionRequest,
    TranscriptionStatusResponse,
    ChapterResponse,
    ChapterCreate,
    ChapterUpdate,
    ChapterListResponse,
)
from app.services.transcription_service import get_transcription_service

router = APIRouter()


@router.get("/availability")
async def check_transcription_availability():
    """Check if transcription service is available."""
    service = get_transcription_service()
    return {
        "available": service.is_available(),
        "model": "whisper-small",
    }


@router.post("/feed-items/{feed_item_id}/transcribe", response_model=TranscriptResponse)
async def start_transcription(
    feed_item_id: int,
    request: TranscriptionRequest,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """
    Start transcription for a feed item.

    This runs in the background. Poll the status endpoint to check progress.
    """
    service = get_transcription_service()

    if not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription service not available. Whisper is not installed.",
        )

    # Get or create transcript record
    transcript = await service.get_or_create_transcript(db, feed_item_id)

    # If already completed or processing, return current state
    if transcript.status in ("completed", "processing"):
        return TranscriptResponse(
            id=transcript.id,
            feed_item_id=transcript.feed_item_id,
            model_used=transcript.model_used,
            language=transcript.language,
            status=transcript.status,
            progress=transcript.progress,
            error_message=transcript.error_message,
            created_at=transcript.created_at,
            started_at=transcript.started_at,
            completed_at=transcript.completed_at,
            segment_count=len(transcript.segments) if transcript.segments else 0,
            has_full_text=bool(transcript.full_text),
        )

    # Start transcription in background
    async def run_transcription():
        from app.database import async_session_maker
        async with async_session_maker() as session:
            try:
                await service.transcribe_feed_item(
                    session,
                    feed_item_id,
                    generate_chapters=request.generate_chapters,
                )
            except Exception as e:
                # Error is logged and stored in transcript record
                pass

    background_tasks.add_task(run_transcription)

    # Return pending status
    return TranscriptResponse(
        id=transcript.id,
        feed_item_id=transcript.feed_item_id,
        model_used=transcript.model_used,
        language=transcript.language,
        status="processing",
        progress=0,
        error_message=None,
        created_at=transcript.created_at,
        started_at=None,
        completed_at=None,
        segment_count=0,
        has_full_text=False,
    )


@router.get("/feed-items/{feed_item_id}/status", response_model=TranscriptionStatusResponse)
async def get_transcription_status(
    feed_item_id: int,
    db: DbSession,
):
    """Get the current status of transcription for a feed item."""
    service = get_transcription_service()
    transcript = await service.get_transcript(db, feed_item_id)

    if not transcript:
        return TranscriptionStatusResponse(
            feed_item_id=feed_item_id,
            status="not_found",
        )

    return TranscriptionStatusResponse(
        feed_item_id=feed_item_id,
        status=transcript.status,
        progress=transcript.progress,
        error_message=transcript.error_message,
        transcript_id=transcript.id,
    )


@router.get("/feed-items/{feed_item_id}/transcript", response_model=TranscriptWithText)
async def get_transcript(
    feed_item_id: int,
    db: DbSession,
):
    """Get the full transcript for a feed item."""
    service = get_transcription_service()
    transcript = await service.get_transcript(db, feed_item_id)

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )

    return TranscriptWithText(
        id=transcript.id,
        feed_item_id=transcript.feed_item_id,
        model_used=transcript.model_used,
        language=transcript.language,
        status=transcript.status,
        progress=transcript.progress,
        error_message=transcript.error_message,
        created_at=transcript.created_at,
        started_at=transcript.started_at,
        completed_at=transcript.completed_at,
        segment_count=len(transcript.segments) if transcript.segments else 0,
        has_full_text=bool(transcript.full_text),
        full_text=transcript.full_text,
        segments=transcript.segments,
    )


@router.get("/feed-items/{feed_item_id}/chapters", response_model=ChapterListResponse)
async def get_chapters(
    feed_item_id: int,
    db: DbSession,
):
    """Get all chapters for a feed item."""
    service = get_transcription_service()
    chapters = await service.get_chapters(db, feed_item_id)

    return ChapterListResponse(
        feed_item_id=feed_item_id,
        chapters=[
            ChapterResponse(
                id=ch.id,
                feed_item_id=ch.feed_item_id,
                title=ch.title,
                description=ch.description,
                start_seconds=ch.start_seconds,
                end_seconds=ch.end_seconds,
                start_formatted=ch.start_formatted,
                source=ch.source,
                confidence=ch.confidence,
                order_index=ch.order_index,
                created_at=ch.created_at,
            )
            for ch in chapters
        ],
        total=len(chapters),
    )


@router.post("/feed-items/{feed_item_id}/chapters", response_model=ChapterResponse)
async def add_chapter(
    feed_item_id: int,
    chapter: ChapterCreate,
    db: DbSession,
):
    """Add a manual chapter to a feed item."""
    service = get_transcription_service()

    new_chapter = await service.add_manual_chapter(
        db,
        feed_item_id,
        title=chapter.title,
        start_seconds=chapter.start_seconds,
        end_seconds=chapter.end_seconds,
        description=chapter.description,
    )

    return ChapterResponse(
        id=new_chapter.id,
        feed_item_id=new_chapter.feed_item_id,
        title=new_chapter.title,
        description=new_chapter.description,
        start_seconds=new_chapter.start_seconds,
        end_seconds=new_chapter.end_seconds,
        start_formatted=new_chapter.start_formatted,
        source=new_chapter.source,
        confidence=new_chapter.confidence,
        order_index=new_chapter.order_index,
        created_at=new_chapter.created_at,
    )


@router.put("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    chapter: ChapterUpdate,
    db: DbSession,
):
    """Update a chapter."""
    service = get_transcription_service()

    # Build updates dict from non-None values
    updates = {}
    if chapter.title is not None:
        updates["title"] = chapter.title
    if chapter.start_seconds is not None:
        updates["start_seconds"] = chapter.start_seconds
    if chapter.end_seconds is not None:
        updates["end_seconds"] = chapter.end_seconds
    if chapter.description is not None:
        updates["description"] = chapter.description
    if chapter.order_index is not None:
        updates["order_index"] = chapter.order_index

    updated = await service.update_chapter(db, chapter_id, **updates)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found",
        )

    return ChapterResponse(
        id=updated.id,
        feed_item_id=updated.feed_item_id,
        title=updated.title,
        description=updated.description,
        start_seconds=updated.start_seconds,
        end_seconds=updated.end_seconds,
        start_formatted=updated.start_formatted,
        source=updated.source,
        confidence=updated.confidence,
        order_index=updated.order_index,
        created_at=updated.created_at,
    )


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: int,
    db: DbSession,
):
    """Delete a chapter."""
    service = get_transcription_service()
    deleted = await service.delete_chapter(db, chapter_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found",
        )

    return {"success": True}


@router.post("/feed-items/{feed_item_id}/regenerate-chapters", response_model=ChapterListResponse)
async def regenerate_chapters(
    feed_item_id: int,
    db: DbSession,
):
    """Delete existing chapters and regenerate from transcript."""
    service = get_transcription_service()

    try:
        chapters = await service.regenerate_chapters(db, feed_item_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ChapterListResponse(
        feed_item_id=feed_item_id,
        chapters=[
            ChapterResponse(
                id=ch.id,
                feed_item_id=ch.feed_item_id,
                title=ch.title,
                description=ch.description,
                start_seconds=ch.start_seconds,
                end_seconds=ch.end_seconds,
                start_formatted=ch.start_formatted,
                source=ch.source,
                confidence=ch.confidence,
                order_index=ch.order_index,
                created_at=ch.created_at,
            )
            for ch in chapters
        ],
        total=len(chapters),
    )
