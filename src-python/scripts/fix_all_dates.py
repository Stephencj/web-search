#!/usr/bin/env python3
"""
Comprehensive script to fix all video upload dates using YouTube Data API.

This script:
1. Finds all videos where upload_date is within 48h of discovered_at (likely wrong)
2. Uses YouTube Data API videos.list endpoint (50 videos per request - much faster than yt-dlp)
3. Updates all upload dates in the database

Usage:
    docker exec -it websearch-app python scripts/fix_all_dates.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy import select

# Add parent to path for imports
sys.path.insert(0, "/app")

from app.database import get_session_factory
from app.models import FeedItem, PlatformAccount
from app.services.oauth_service import OAuthService


YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
BATCH_SIZE = 50  # YouTube API max per request


async def get_youtube_access_token(db) -> Optional[str]:
    """Get a valid YouTube access token from stored accounts."""
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.platform == "youtube",
            PlatformAccount.is_active == True,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        logger.error("No active YouTube account found. Please link your YouTube account first.")
        return None

    oauth = OAuthService()
    token = await oauth.get_valid_token(db, account.id)

    if not token:
        logger.error("Could not get valid YouTube token. Please re-authenticate.")
        return None

    return token


async def fetch_video_details(access_token: str, video_ids: list[str]) -> dict:
    """
    Fetch video details from YouTube Data API.

    Returns dict mapping video_id -> upload_date
    """
    results = {}

    async with httpx.AsyncClient() as client:
        # YouTube API accepts comma-separated video IDs (max 50)
        ids_param = ",".join(video_ids)

        response = await client.get(
            f"{YOUTUBE_API_URL}/videos",
            params={
                "part": "snippet",
                "id": ids_param,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            logger.error(f"YouTube API error: {response.status_code} - {response.text[:200]}")
            return results

        data = response.json()

        for item in data.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            published_at = snippet.get("publishedAt")

            if published_at:
                # Parse ISO 8601 format: 2024-01-15T12:00:00Z
                try:
                    upload_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    # Convert to naive UTC datetime for database
                    upload_date = upload_date.replace(tzinfo=None)
                    results[video_id] = upload_date
                except Exception as e:
                    logger.warning(f"Could not parse date {published_at}: {e}")

    return results


async def find_videos_needing_fix(db, batch_size: int = 1000) -> list[FeedItem]:
    """Find all YouTube videos where upload_date is likely wrong."""
    all_bad_videos = []
    offset = 0

    while True:
        result = await db.execute(
            select(FeedItem)
            .where(FeedItem.platform == "youtube")
            .order_by(FeedItem.id)
            .offset(offset)
            .limit(batch_size)
        )
        items = list(result.scalars().all())

        if not items:
            break

        for item in items:
            if item.upload_date and item.discovered_at:
                diff = abs((item.upload_date - item.discovered_at).total_seconds())
                if diff < 172800:  # 48 hours
                    all_bad_videos.append(item)

        offset += batch_size
        logger.info(f"Scanned {offset} videos, found {len(all_bad_videos)} needing fix so far...")

    return all_bad_videos


async def main():
    """Main function to fix all video dates."""
    logger.info("=" * 60)
    logger.info("Starting comprehensive date fix")
    logger.info("=" * 60)

    async with get_session_factory()() as db:
        # Get YouTube access token
        logger.info("Getting YouTube access token...")
        access_token = await get_youtube_access_token(db)

        if not access_token:
            logger.error("Cannot proceed without YouTube access token")
            return

        logger.info("Got valid YouTube access token")

        # Find videos needing fix
        logger.info("Scanning database for videos with suspect dates...")
        videos_to_fix = await find_videos_needing_fix(db)

        if not videos_to_fix:
            logger.info("No videos need date fixing!")
            return

        logger.info(f"Found {len(videos_to_fix)} videos needing date fix")

        # Process in batches of 50 (YouTube API limit)
        fixed_count = 0
        error_count = 0

        for i in range(0, len(videos_to_fix), BATCH_SIZE):
            batch = videos_to_fix[i:i + BATCH_SIZE]
            video_ids = [v.video_id for v in batch]

            logger.info(f"Processing batch {i // BATCH_SIZE + 1} ({i + 1}-{min(i + BATCH_SIZE, len(videos_to_fix))} of {len(videos_to_fix)})")

            try:
                # Fetch from YouTube API
                date_map = await fetch_video_details(access_token, video_ids)

                # Update database
                for video in batch:
                    if video.video_id in date_map:
                        new_date = date_map[video.video_id]
                        old_date = video.upload_date

                        # Only update if significantly different
                        if abs((new_date - old_date).total_seconds()) > 86400:  # More than 1 day difference
                            video.upload_date = new_date
                            fixed_count += 1
                    else:
                        error_count += 1

                await db.commit()

                # Rate limiting - YouTube API allows 10,000 units/day
                # videos.list costs 1 unit per request, so we're fine
                # But let's be polite and add a small delay
                await asyncio.sleep(0.2)

            except Exception as e:
                logger.exception(f"Error processing batch: {e}")
                error_count += len(batch)
                continue

            # Progress update every 500 videos
            if (i + BATCH_SIZE) % 500 == 0:
                logger.info(f"Progress: {fixed_count} fixed, {error_count} errors")

        logger.info("=" * 60)
        logger.info(f"Date fix complete!")
        logger.info(f"  Fixed: {fixed_count}")
        logger.info(f"  Errors/Not found: {error_count}")
        logger.info(f"  Total processed: {len(videos_to_fix)}")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
