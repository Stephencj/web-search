"""Crawl management API endpoints."""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.database import get_async_session
from app.models import CrawlJob, Source, Index
from app.services.crawl_service import get_crawl_service

router = APIRouter()


async def _run_crawl_job(job_id: int, source_id: int, index_id: int) -> None:
    """Background task to run a crawl job."""
    logger.info(f"Background task starting for job {job_id}")
    crawl_service = get_crawl_service()

    try:
        async with get_async_session() as db:
            # Fetch job, source, and index
            job = await db.get(CrawlJob, job_id)
            source = await db.get(Source, source_id)
            result = await db.execute(
                select(Index).where(Index.id == index_id)
            )
            index = result.scalar_one_or_none()

            if not job or not source or not index:
                logger.error(f"Missing data for job {job_id}: job={job}, source={source}, index={index}")
                return

            logger.info(f"Starting crawl service for job {job_id}, source {source.url}")
            await crawl_service.start_crawl(db, job, source, index)
            logger.info(f"Crawl service completed for job {job_id}")
    except Exception as e:
        logger.exception(f"Background task failed for job {job_id}: {e}")


@router.post("/start")
async def start_crawl(
    source_ids: list[int],
    db: DbSession,
    background_tasks: BackgroundTasks
) -> dict:
    """Start crawl for specified sources."""
    # Verify sources exist and get their indexes
    result = await db.execute(
        select(Source)
        .options(selectinload(Source.index))
        .where(Source.id.in_(source_ids))
    )
    sources = result.scalars().all()

    if len(sources) != len(source_ids):
        found_ids = {s.id for s in sources}
        missing = [sid for sid in source_ids if sid not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sources not found: {missing}"
        )

    # Check for inactive sources
    inactive = [s.id for s in sources if not s.is_active]
    if inactive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sources are inactive: {inactive}"
        )

    # Create crawl jobs and schedule them
    jobs = []
    for source in sources:
        job = CrawlJob(
            source_id=source.id,
            status="pending",
            trigger="manual"
        )
        db.add(job)
        await db.flush()  # Get job.id

        jobs.append({
            "id": job.id,
            "source_id": source.id,
            "index_id": source.index_id
        })

    await db.commit()

    # Schedule background tasks for each crawl
    for job_info in jobs:
        background_tasks.add_task(
            _run_crawl_job,
            job_info["id"],
            job_info["source_id"],
            job_info["index_id"]
        )

    return {
        "status": "started",
        "jobs": [{"id": j["id"], "source_id": j["source_id"]} for j in jobs],
        "message": f"Started {len(jobs)} crawl job(s)"
    }


@router.post("/stop")
async def stop_crawl(
    job_ids: Optional[list[int]] = None,
    db: DbSession = None
) -> dict:
    """Stop running crawl jobs."""
    crawl_service = get_crawl_service()

    if job_ids is None:
        # Stop all active crawls in memory
        active_ids = crawl_service.get_active_crawl_ids()
        for job_id in active_ids:
            crawl_service.stop_crawl(job_id)

        # Also get all "running" jobs from DB that might be stuck
        result = await db.execute(
            select(CrawlJob).where(CrawlJob.status.in_(["running", "pending"]))
        )
        job_ids = [job.id for job in result.scalars().all()]

    stopped = []

    for job_id in job_ids:
        # Try to stop in memory
        crawl_service.stop_crawl(job_id)

        # Always update database status
        job = await db.get(CrawlJob, job_id)
        if job and job.status in ["running", "pending"]:
            job.status = "cancelled"
            job.error_message = "Cancelled by user"
            job.completed_at = datetime.utcnow()
            stopped.append(job_id)

    await db.commit()

    return {
        "status": "ok",
        "stopped": stopped,
        "message": f"Stopped {len(stopped)} crawl(s)"
    }


@router.get("/status")
async def get_crawl_status(
    db: DbSession,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100)
) -> dict:
    """Get status of all crawl jobs."""
    query = select(CrawlJob).options(selectinload(CrawlJob.source))

    if status_filter:
        query = query.where(CrawlJob.status == status_filter)

    query = query.order_by(CrawlJob.created_at.desc()).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Get active crawl IDs
    crawl_service = get_crawl_service()
    active_ids = set(crawl_service.get_active_crawl_ids())

    return {
        "jobs": [
            {
                "id": job.id,
                "source_id": job.source_id,
                "source_url": job.source.url if job.source else None,
                "status": job.status,
                "trigger": job.trigger,
                "pages_crawled": job.pages_crawled,
                "pages_indexed": job.pages_indexed,
                "pages_failed": job.pages_failed,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "is_active": job.id in active_ids,
            }
            for job in jobs
        ],
        "total": len(jobs),
        "active_count": len(active_ids)
    }


@router.get("/jobs/{job_id}")
async def get_crawl_job(job_id: int, db: DbSession) -> dict:
    """Get details of a specific crawl job."""
    result = await db.execute(
        select(CrawlJob)
        .options(selectinload(CrawlJob.source))
        .where(CrawlJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl job with id {job_id} not found"
        )

    # Check if actively running
    crawl_service = get_crawl_service()
    is_active = crawl_service.is_crawling(job_id)

    return {
        "id": job.id,
        "source_id": job.source_id,
        "source_url": job.source.url if job.source else None,
        "status": job.status,
        "trigger": job.trigger,
        "pages_crawled": job.pages_crawled,
        "pages_indexed": job.pages_indexed,
        "pages_skipped": job.pages_skipped,
        "pages_failed": job.pages_failed,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "duration_seconds": job.duration_seconds,
        "error_message": job.error_message,
        "error_details": job.error_details,
        "created_at": job.created_at.isoformat(),
        "is_active": is_active,
    }


@router.delete("/jobs/{job_id}")
async def delete_crawl_job(job_id: int, db: DbSession) -> dict:
    """Delete a crawl job record."""
    job = await db.get(CrawlJob, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl job with id {job_id} not found"
        )

    # Don't delete running jobs
    crawl_service = get_crawl_service()
    if crawl_service.is_crawling(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running crawl job. Stop it first."
        )

    await db.delete(job)
    await db.commit()

    return {"status": "deleted", "id": job_id}


@router.get("/history")
async def get_crawl_history(
    db: DbSession,
    source_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
) -> dict:
    """Get crawl history with pagination."""
    query = select(CrawlJob).options(selectinload(CrawlJob.source))

    if source_id:
        query = query.where(CrawlJob.source_id == source_id)

    # Get total count
    count_query = select(func.count(CrawlJob.id))
    if source_id:
        count_query = count_query.where(CrawlJob.source_id == source_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get paginated results
    offset = (page - 1) * per_page
    query = query.order_by(CrawlJob.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [
            {
                "id": job.id,
                "source_id": job.source_id,
                "source_url": job.source.url if job.source else None,
                "status": job.status,
                "trigger": job.trigger,
                "pages_indexed": job.pages_indexed,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in jobs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0
    }
