"""
Backfill API endpoints for updating legacy data.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.backfill_service import backfill_service

router = APIRouter()


@router.get("/status")
async def get_backfill_status(
    db: AsyncSession = Depends(get_session),
):
    """Get current backfill status showing missing data counts by platform."""
    return await backfill_service.get_backfill_status(db)


@router.post("/redbar")
async def backfill_redbar(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    limit: Optional[int] = Query(None, description="Limit number of items to process"),
    run_async: bool = Query(False, description="Run in background"),
):
    """
    Backfill video_stream_url for Red Bar feed items.

    This fetches each episode page and extracts the direct video URL.
    Can take a while for many items.
    """
    if run_async:
        background_tasks.add_task(
            backfill_service.backfill_redbar_video_urls, db, limit
        )
        return {"status": "started", "message": "Backfill running in background"}

    return await backfill_service.backfill_redbar_video_urls(db, limit)


@router.post("/podcast")
async def backfill_podcast(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    limit: Optional[int] = Query(None, description="Limit number of items to process"),
    run_async: bool = Query(False, description="Run in background"),
):
    """
    Backfill audio fields for podcast feed items.

    Re-fetches RSS and updates items missing audio_url.
    """
    if run_async:
        background_tasks.add_task(
            backfill_service.backfill_podcast_audio_fields, db, limit
        )
        return {"status": "started", "message": "Backfill running in background"}

    return await backfill_service.backfill_podcast_audio_fields(db, limit)


@router.post("/all")
async def backfill_all(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    limit: Optional[int] = Query(None, description="Limit number of items per platform"),
):
    """Run all backfill tasks in background."""
    background_tasks.add_task(
        backfill_service.backfill_redbar_video_urls, db, limit
    )
    background_tasks.add_task(
        backfill_service.backfill_podcast_audio_fields, db, limit
    )
    return {"status": "started", "message": "All backfill tasks running in background"}
