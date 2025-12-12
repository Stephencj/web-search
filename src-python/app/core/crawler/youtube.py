"""YouTube extractor using yt-dlp for video metadata and transcripts."""

import asyncio
import re
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional

import yt_dlp
from loguru import logger

from app.core.crawler.youtube_types import YouTubeVideoResult, YouTubeUrlType
from app.core.crawler.url_detector import get_youtube_url_type


class YouTubeExtractor:
    """
    Extract video metadata and transcripts from YouTube using yt-dlp.

    Supports:
    - Single videos
    - Playlists
    - Channels
    - Search results
    """

    def __init__(
        self,
        max_videos: int = 500,
        fetch_transcripts: bool = True,
        transcript_languages: list[str] | None = None,
        rate_limit_delay: float = 2.0,
    ):
        """
        Initialize YouTube extractor.

        Args:
            max_videos: Maximum number of videos to extract
            fetch_transcripts: Whether to fetch video transcripts
            transcript_languages: Preferred languages for transcripts
            rate_limit_delay: Delay between requests in seconds
        """
        self.max_videos = max_videos
        self.fetch_transcripts = fetch_transcripts
        self.transcript_languages = transcript_languages or ["en", "en-US", "en-GB"]
        self.rate_limit_delay = rate_limit_delay

    async def extract(self, url: str) -> AsyncGenerator[YouTubeVideoResult, None]:
        """
        Extract videos from any YouTube URL.

        Args:
            url: YouTube URL (video, playlist, channel, or search)

        Yields:
            YouTubeVideoResult for each video found
        """
        url_type = get_youtube_url_type(url)
        logger.info(f"Extracting YouTube content from {url} (type: {url_type.value})")

        if url_type == YouTubeUrlType.VIDEO:
            # Single video
            result = await self._extract_video_info(url)
            if result:
                yield result
        else:
            # Playlist, channel, or search - extract video list first
            video_urls = await self._get_video_list(url)
            logger.info(f"Found {len(video_urls)} videos to process")

            for i, video_url in enumerate(video_urls[:self.max_videos]):
                try:
                    result = await self._extract_video_info(video_url)
                    if result:
                        yield result

                    # Rate limiting
                    if i < len(video_urls) - 1:
                        await asyncio.sleep(self.rate_limit_delay)

                except Exception as e:
                    logger.warning(f"Failed to extract video {video_url}: {e}")
                    continue

    async def _get_video_list(self, url: str) -> list[str]:
        """
        Get list of video URLs from a playlist, channel, or search.

        Args:
            url: YouTube URL

        Returns:
            List of video URLs
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'ignoreerrors': True,
            'playlistend': self.max_videos,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_info(url, ydl_opts)
            )

            if not info:
                return []

            video_urls = []

            # Handle playlist/channel entries
            if 'entries' in info:
                for entry in info['entries']:
                    if entry is None:
                        continue

                    video_id = entry.get('id')
                    if video_id:
                        video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

            return video_urls

        except Exception as e:
            logger.error(f"Failed to get video list from {url}: {e}")
            return []

    async def _extract_video_info(self, url: str) -> Optional[YouTubeVideoResult]:
        """
        Extract full metadata for a single video.

        Args:
            url: Video URL

        Returns:
            YouTubeVideoResult or None if extraction fails
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'ignoreerrors': True,
        }

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_info(url, ydl_opts)
            )

            if not info:
                return None

            # Build result
            video_id = info.get('id', '')
            result = YouTubeVideoResult(
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                video_id=video_id,
                title=info.get('title', 'Untitled'),
                thumbnail_url=self._get_best_thumbnail(info),
                description=info.get('description'),
                duration_seconds=info.get('duration'),
                view_count=info.get('view_count'),
                like_count=info.get('like_count'),
                upload_date=info.get('upload_date'),
                channel_name=info.get('channel') or info.get('uploader'),
                channel_url=info.get('channel_url') or info.get('uploader_url'),
                channel_id=info.get('channel_id') or info.get('uploader_id'),
                tags=info.get('tags', []) or [],
                categories=info.get('categories', []) or [],
            )

            # Fetch transcript if enabled
            if self.fetch_transcripts:
                transcript, language = await self._fetch_transcript(video_id, info)
                result.transcript = transcript
                result.transcript_language = language

            return result

        except Exception as e:
            logger.warning(f"Failed to extract video info from {url}: {e}")
            return None

    def _extract_info(self, url: str, opts: dict) -> dict | None:
        """
        Synchronous extraction using yt-dlp.

        Args:
            url: URL to extract
            opts: yt-dlp options

        Returns:
            Extracted info dict or None
        """
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"yt-dlp extraction failed for {url}: {e}")
            return None

    async def _fetch_transcript(
        self,
        video_id: str,
        info: dict,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Fetch transcript/captions for a video.

        Args:
            video_id: YouTube video ID
            info: Extracted video info dict

        Returns:
            Tuple of (transcript_text, language_code) or (None, None)
        """
        try:
            # Check for available subtitles in info
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})

            # Find best subtitle option
            sub_url = None
            sub_lang = None

            # Prefer manual subtitles in requested languages
            for lang in self.transcript_languages:
                if lang in subtitles:
                    subs = subtitles[lang]
                    sub_url = self._get_subtitle_url(subs)
                    sub_lang = lang
                    break

            # Fall back to auto-generated captions
            if not sub_url:
                for lang in self.transcript_languages:
                    if lang in automatic_captions:
                        caps = automatic_captions[lang]
                        sub_url = self._get_subtitle_url(caps)
                        sub_lang = lang
                        break

            # Try any available subtitles
            if not sub_url and subtitles:
                lang = list(subtitles.keys())[0]
                sub_url = self._get_subtitle_url(subtitles[lang])
                sub_lang = lang

            # Try any auto-captions
            if not sub_url and automatic_captions:
                lang = list(automatic_captions.keys())[0]
                sub_url = self._get_subtitle_url(automatic_captions[lang])
                sub_lang = lang

            if not sub_url:
                return None, None

            # Download and process transcript
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(sub_url, timeout=30)
                if response.status_code == 200:
                    raw_transcript = response.text
                    processed = self._process_transcript(raw_transcript)
                    return processed, sub_lang

            return None, None

        except Exception as e:
            logger.debug(f"Failed to fetch transcript for {video_id}: {e}")
            return None, None

    def _get_subtitle_url(self, subs: list[dict]) -> str | None:
        """Get best subtitle URL from list, preferring vtt format."""
        for sub in subs:
            if sub.get('ext') == 'vtt':
                return sub.get('url')
        # Fall back to any format
        if subs:
            return subs[0].get('url')
        return None

    def _get_best_thumbnail(self, info: dict) -> str | None:
        """Get best thumbnail URL from video info."""
        # Try direct thumbnail field
        if info.get('thumbnail'):
            return info['thumbnail']

        # Try thumbnails list
        thumbnails = info.get('thumbnails', [])
        if thumbnails:
            # Sort by preference (higher resolution first)
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda t: t.get('preference', 0) or t.get('width', 0),
                reverse=True
            )
            return sorted_thumbs[0].get('url')

        # Fall back to YouTube standard thumbnail
        video_id = info.get('id')
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

        return None

    def _process_transcript(self, raw_content: str) -> str:
        """
        Process VTT/SRT transcript into clean searchable text.

        Args:
            raw_content: Raw VTT or SRT content

        Returns:
            Clean text transcript
        """
        lines = raw_content.split('\n')
        text_lines = []
        seen_text = set()

        for line in lines:
            line = line.strip()

            # Skip VTT header
            if line.startswith('WEBVTT'):
                continue

            # Skip empty lines
            if not line:
                continue

            # Skip timestamp lines (VTT format: 00:00:00.000 --> 00:00:00.000)
            if re.match(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->', line):
                continue

            # Skip SRT timestamp lines (00:00:00,000 --> 00:00:00,000)
            if re.match(r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->', line):
                continue

            # Skip numeric lines (SRT sequence numbers)
            if re.match(r'^\d+$', line):
                continue

            # Skip style/metadata tags
            if line.startswith('NOTE') or line.startswith('STYLE'):
                continue

            # Remove VTT positioning tags like <c> and alignment
            line = re.sub(r'<[^>]+>', '', line)
            line = re.sub(r'\{[^}]+\}', '', line)

            # Normalize whitespace
            line = ' '.join(line.split())

            if not line:
                continue

            # Deduplicate (YouTube often has progressive/overlapping captions)
            if line not in seen_text:
                seen_text.add(line)
                text_lines.append(line)

        # Join into paragraphs
        transcript = ' '.join(text_lines)

        # Limit size for indexing (100KB max)
        max_size = 100000
        if len(transcript) > max_size:
            transcript = transcript[:max_size] + '...'

        return transcript
