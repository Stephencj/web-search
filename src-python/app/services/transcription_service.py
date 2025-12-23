"""Whisper-based transcription service for generating transcripts and chapters."""

import asyncio
import os
import re
import tempfile
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import Transcript
from app.models.chapter import Chapter
from app.models.feed_item import FeedItem

# Lazy-loaded Whisper model
_whisper_model = None
_model_name = "small"  # Balance of speed and accuracy


def _load_whisper_model():
    """Lazy load the Whisper model."""
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    try:
        import whisper

        logger.info(f"Loading Whisper model: {_model_name}")
        _whisper_model = whisper.load_model(_model_name)
        logger.info("Whisper model loaded successfully")
        return _whisper_model

    except ImportError:
        logger.warning("openai-whisper not installed. Transcription disabled.")
        return None
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        return None


class TranscriptionService:
    """
    Service for transcribing audio files using Whisper.

    Features:
    - Lazy model loading (only loads on first use)
    - Background processing with progress updates
    - Segment-level timestamps
    - Chapter generation from transcript
    """

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for downloading audio."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=600.0,  # 10 min timeout for large files
                follow_redirects=True,
            )
        return self._http_client

    def is_available(self) -> bool:
        """Check if Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            return False

    async def get_or_create_transcript(
        self,
        db: AsyncSession,
        feed_item_id: int
    ) -> Transcript:
        """Get existing transcript or create a new pending one."""
        result = await db.execute(
            select(Transcript).where(Transcript.feed_item_id == feed_item_id)
        )
        transcript = result.scalar_one_or_none()

        if transcript is None:
            transcript = Transcript(
                feed_item_id=feed_item_id,
                model_used=f"whisper-{_model_name}",
                status="pending",
            )
            db.add(transcript)
            await db.commit()
            await db.refresh(transcript)

        return transcript

    async def get_transcript(
        self,
        db: AsyncSession,
        feed_item_id: int
    ) -> Optional[Transcript]:
        """Get transcript for a feed item."""
        result = await db.execute(
            select(Transcript).where(Transcript.feed_item_id == feed_item_id)
        )
        return result.scalar_one_or_none()

    async def get_chapters(
        self,
        db: AsyncSession,
        feed_item_id: int
    ) -> list[Chapter]:
        """Get chapters for a feed item, ordered by start time."""
        result = await db.execute(
            select(Chapter)
            .where(Chapter.feed_item_id == feed_item_id)
            .order_by(Chapter.order_index, Chapter.start_seconds)
        )
        return list(result.scalars().all())

    async def transcribe_feed_item(
        self,
        db: AsyncSession,
        feed_item_id: int,
        generate_chapters: bool = True,
    ) -> Transcript:
        """
        Transcribe audio from a feed item.

        Args:
            db: Database session
            feed_item_id: ID of the FeedItem to transcribe
            generate_chapters: Whether to parse description and generate chapters

        Returns:
            The Transcript object (may be in processing state)
        """
        # Get feed item
        result = await db.execute(
            select(FeedItem).where(FeedItem.id == feed_item_id)
        )
        feed_item = result.scalar_one_or_none()
        if not feed_item:
            raise ValueError(f"FeedItem {feed_item_id} not found")

        # Get audio URL (prefer audio_url, fall back to video_url)
        audio_url = feed_item.audio_url or feed_item.video_url
        if not audio_url:
            raise ValueError(f"No audio URL for FeedItem {feed_item_id}")

        # Get or create transcript
        transcript = await self.get_or_create_transcript(db, feed_item_id)

        # If already completed, return existing
        if transcript.status == "completed":
            logger.info(f"Transcript {transcript.id} already completed")
            return transcript

        # If already processing, return current state
        if transcript.status == "processing":
            logger.info(f"Transcript {transcript.id} already processing")
            return transcript

        # Start processing
        transcript.status = "processing"
        transcript.started_at = datetime.utcnow()
        transcript.progress = 0
        await db.commit()

        try:
            # Download audio to temp file
            logger.info(f"Downloading audio from {audio_url}")
            transcript.progress = 5
            await db.commit()

            audio_path = await self._download_audio(audio_url)

            # Run transcription
            logger.info(f"Starting Whisper transcription for {audio_path}")
            transcript.progress = 10
            await db.commit()

            transcription_result = await self._run_transcription(audio_path)

            # Store results
            transcript.full_text = transcription_result["text"]
            transcript.segments = transcription_result["segments"]
            transcript.status = "completed"
            transcript.completed_at = datetime.utcnow()
            transcript.progress = 100
            await db.commit()

            # Cleanup temp file
            try:
                os.unlink(audio_path)
            except Exception:
                pass

            # Generate chapters if requested
            if generate_chapters and feed_item.description:
                logger.info("Generating chapters from description")
                # Refresh feed_item after commit
                await db.refresh(feed_item)
                await db.refresh(transcript)
                await self._generate_chapters(db, feed_item, transcript)

            logger.info(f"Transcription completed for FeedItem {feed_item_id}")
            return transcript

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            transcript.status = "failed"
            transcript.error_message = str(e)
            await db.commit()
            raise

    async def _download_audio(self, url: str) -> str:
        """Download audio file to temp location."""
        client = await self._get_client()

        # Create temp file with appropriate extension
        ext = ".mp3" if ".mp3" in url.lower() else ".mp4"
        fd, path = tempfile.mkstemp(suffix=ext)

        try:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with os.fdopen(fd, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        except Exception:
            os.close(fd)
            raise

        return path

    async def _run_transcription(self, audio_path: str) -> dict:
        """Run Whisper transcription with progress updates."""
        model = _load_whisper_model()
        if model is None:
            raise RuntimeError("Whisper model not available")

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def transcribe():
            return model.transcribe(
                audio_path,
                language="en",
                word_timestamps=True,
                verbose=False,
            )

        result = await loop.run_in_executor(None, transcribe)

        # Convert segments to serializable format
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            })

        return {
            "text": result.get("text", "").strip(),
            "segments": segments,
            "language": result.get("language", "en"),
        }

    async def _generate_chapters(
        self,
        db: AsyncSession,
        feed_item: FeedItem,
        transcript: Transcript,
    ) -> list[Chapter]:
        """Generate chapters by parsing description and matching to transcript."""
        if not feed_item.description:
            return []

        # Parse segments from description
        parsed_segments = self._parse_description_segments(feed_item.description)
        if not parsed_segments:
            return []

        chapters = []
        for idx, seg in enumerate(parsed_segments):
            chapter = Chapter(
                feed_item_id=feed_item.id,
                title=seg["title"],
                start_seconds=seg.get("start_seconds", 0.0),
                source="description_parse" if seg.get("has_timestamp") else "pending_match",
                order_index=idx,
            )
            chapters.append(chapter)
            db.add(chapter)

        await db.commit()

        # Refresh chapters to get IDs
        for chapter in chapters:
            await db.refresh(chapter)

        # Match segments without timestamps to transcript
        await self._match_chapters_to_transcript(db, chapters, transcript)

        return chapters

    def _parse_description_segments(self, description: str) -> list[dict]:
        """
        Parse segment names and timestamps from episode description.

        Handles patterns like:
        - "- SEGMENT NAME (1:23:45)" - with timestamp
        - "- Segment Name" - without timestamp
        - "1. Topic Name" - numbered list
        - "SEGMENT: Topic" - colon format
        """
        segments = []
        lines = description.split("\n")

        # Patterns for segment lines
        patterns = [
            # "- SEGMENT NAME (1:23:45)" or "- SEGMENT NAME - 1:23:45"
            r'^[\-\*•]\s*(.+?)\s*[\(\-–]\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[\)]?$',
            # "1:23:45 - SEGMENT NAME" or "1:23:45 SEGMENT NAME"
            r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*[\-–]?\s*(.+?)$',
            # "1. Topic Name" or "1) Topic Name"
            r'^\d+[\.\)]\s*(.+?)$',
            # "- SEGMENT NAME" or "• SEGMENT NAME" (no timestamp)
            r'^[\-\*•]\s*([A-Z][A-Za-z0-9\s\-\'\"&]+)$',
            # "SEGMENT: Details" (all caps header with colon)
            r'^([A-Z][A-Z0-9\s\-]+):\s*.+$',
        ]

        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue

            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()

                    # Determine title and timestamp
                    if len(groups) == 2:
                        # Check if first group is timestamp
                        if re.match(r'^\d{1,2}:\d{2}', groups[0]):
                            timestamp_str = groups[0]
                            title = groups[1]
                        else:
                            title = groups[0]
                            timestamp_str = groups[1] if len(groups) > 1 else None
                    else:
                        title = groups[0]
                        timestamp_str = None

                    # Parse timestamp to seconds
                    start_seconds = 0.0
                    has_timestamp = False
                    if timestamp_str:
                        start_seconds = self._parse_timestamp(timestamp_str)
                        has_timestamp = start_seconds > 0

                    # Skip very short or generic titles
                    if len(title) < 3 or title.lower() in ["intro", "outro", "end"]:
                        continue

                    segments.append({
                        "title": title.strip(),
                        "start_seconds": start_seconds,
                        "has_timestamp": has_timestamp,
                    })
                    break

        return segments

    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse timestamp string to seconds."""
        parts = timestamp.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        except (ValueError, IndexError):
            pass
        return 0.0

    async def _match_chapters_to_transcript(
        self,
        db: AsyncSession,
        chapters: list[Chapter],
        transcript: Transcript,
    ) -> None:
        """Match chapters without timestamps to transcript segments."""
        if not transcript.segments:
            return

        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning("rapidfuzz not installed, skipping transcript matching")
            return

        # Build sliding windows over transcript
        windows = self._build_transcript_windows(transcript.segments, window_seconds=30)

        for chapter in chapters:
            if chapter.source != "pending_match":
                continue

            # Find best matching window
            best_match = None
            best_score = 0

            for window in windows:
                # Fuzzy match chapter title to window text
                score = fuzz.partial_ratio(
                    chapter.title.lower(),
                    window["text"].lower()
                )

                if score > best_score and score > 60:  # Minimum threshold
                    best_score = score
                    best_match = window

            if best_match:
                chapter.start_seconds = best_match["start"]
                chapter.end_seconds = best_match["end"]
                chapter.confidence = best_score / 100.0
                chapter.matched_text = best_match["text"][:500]
                chapter.source = "transcript_match"

        await db.commit()

    def _build_transcript_windows(
        self,
        segments: list[dict],
        window_seconds: float = 30,
    ) -> list[dict]:
        """Build sliding windows over transcript for matching."""
        if not segments:
            return []

        windows = []
        current_window = {"start": 0, "end": 0, "text": ""}

        for seg in segments:
            # Start new window if this segment starts after current window
            if seg["start"] > current_window["end"] + window_seconds:
                if current_window["text"]:
                    windows.append(current_window)
                current_window = {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                }
            else:
                # Extend current window
                current_window["end"] = seg["end"]
                current_window["text"] += " " + seg["text"]

            # If window is full, save it and start overlapping window
            if current_window["end"] - current_window["start"] >= window_seconds:
                windows.append(current_window.copy())
                # Start next window with overlap
                overlap_start = current_window["start"] + window_seconds / 2
                current_window = {
                    "start": overlap_start,
                    "end": seg["end"],
                    "text": seg["text"],
                }

        # Add final window
        if current_window["text"]:
            windows.append(current_window)

        return windows

    async def regenerate_chapters(
        self,
        db: AsyncSession,
        feed_item_id: int
    ) -> list[Chapter]:
        """Delete existing chapters and regenerate from transcript."""
        # Delete existing chapters
        result = await db.execute(
            select(Chapter).where(Chapter.feed_item_id == feed_item_id)
        )
        chapters = result.scalars().all()
        for chapter in chapters:
            await db.delete(chapter)
        await db.commit()

        # Get transcript and feed item
        transcript = await self.get_transcript(db, feed_item_id)
        if not transcript or transcript.status != "completed":
            raise ValueError("No completed transcript for regeneration")

        result = await db.execute(
            select(FeedItem).where(FeedItem.id == feed_item_id)
        )
        feed_item = result.scalar_one_or_none()
        if not feed_item:
            raise ValueError("FeedItem not found")

        # Regenerate
        return await self._generate_chapters(db, feed_item, transcript)

    async def add_manual_chapter(
        self,
        db: AsyncSession,
        feed_item_id: int,
        title: str,
        start_seconds: float,
        end_seconds: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Chapter:
        """Add a manual chapter."""
        # Get max order index
        result = await db.execute(
            select(Chapter).where(Chapter.feed_item_id == feed_item_id)
        )
        existing = list(result.scalars().all())
        max_order = len(existing)

        chapter = Chapter(
            feed_item_id=feed_item_id,
            title=title,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            description=description,
            source="manual",
            order_index=max_order,
        )
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)

        return chapter

    async def update_chapter(
        self,
        db: AsyncSession,
        chapter_id: int,
        **updates,
    ) -> Optional[Chapter]:
        """Update a chapter."""
        result = await db.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            return None

        for key, value in updates.items():
            if hasattr(chapter, key) and value is not None:
                setattr(chapter, key, value)

        await db.commit()
        await db.refresh(chapter)
        return chapter

    async def delete_chapter(
        self,
        db: AsyncSession,
        chapter_id: int
    ) -> bool:
        """Delete a chapter."""
        result = await db.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            return False

        await db.delete(chapter)
        await db.commit()
        return True

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service() -> TranscriptionService:
    """Get transcription service instance."""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service
