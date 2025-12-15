"""Podcast platform adapter using Podcast Index API and RSS feeds."""

import hashlib
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.config import get_settings
from app.core.platforms.base import (
    PlatformAdapter,
    VideoResult,
    ChannelResult,
)


class PodcastPlatform(PlatformAdapter):
    """
    Podcast platform adapter.

    Uses Podcast Index API for discovery and RSS feeds for episode data.
    Episodes are treated as "videos" for compatibility with the feed system.
    """

    platform_id = "podcast"
    platform_name = "Podcast"
    platform_icon = "🎙️"
    platform_color = "#8B5CF6"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = False

    def __init__(
        self,
        rate_limit_delay: float = 1.0,
        user_agent: str = "WebSearch/1.0 Podcast Client",
    ):
        """
        Initialize Podcast platform adapter.

        Args:
            rate_limit_delay: Delay between requests in seconds
            user_agent: User agent string for requests
        """
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent
        self._settings = None

    @property
    def settings(self):
        """Get podcast index settings lazily."""
        if self._settings is None:
            self._settings = get_settings().podcast_index
        return self._settings

    def _get_podcast_index_headers(self) -> dict:
        """Generate Podcast Index API authentication headers."""
        api_key = self.settings.api_key
        api_secret = self.settings.api_secret

        if not api_key or not api_secret:
            return {}

        # Podcast Index uses epoch time and SHA1 hash for auth
        epoch_time = str(int(time.time()))
        data_to_hash = api_key + api_secret + epoch_time
        sha1_hash = hashlib.sha1(data_to_hash.encode()).hexdigest()

        return {
            "X-Auth-Key": api_key,
            "X-Auth-Date": epoch_time,
            "Authorization": sha1_hash,
            "User-Agent": self.user_agent,
        }

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is an RSS feed URL."""
        try:
            parsed = urlparse(url.lower())
            path = parsed.path.lower()

            # Common RSS feed patterns
            if any(ext in path for ext in [".rss", ".xml", "/feed", "/rss"]):
                return True

            # Known podcast hosting domains
            podcast_hosts = [
                "feeds.libsyn.com",
                "feeds.megaphone.fm",
                "feeds.simplecast.com",
                "feeds.transistor.fm",
                "feeds.buzzsprout.com",
                "anchor.fm",
                "feeds.soundcloud.com",
                "feeds.podbean.com",
                "rss.art19.com",
                "feeds.acast.com",
                "omnycontent.com",
                "podcastfeeds.nbcnews.com",
                "feeds.npr.org",
                "audioboom.com",
            ]
            if any(host in parsed.netloc for host in podcast_hosts):
                return True

            return False
        except Exception:
            return False

    async def _fetch_rss(self, feed_url: str) -> Optional[dict]:
        """Fetch and parse an RSS feed."""
        try:
            import feedparser

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    feed_url,
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                return feed
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
            return None

    async def _search_podcast_index(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[dict]:
        """Search podcasts via Podcast Index API."""
        if not self.settings.api_key or not self.settings.api_secret:
            logger.warning("Podcast Index API credentials not configured")
            return []

        try:
            url = f"{self.settings.base_url}/search/byterm"
            params = {"q": query, "max": max_results}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_podcast_index_headers(),
                )
                response.raise_for_status()
                data = response.json()
                return data.get("feeds", [])
        except Exception as e:
            logger.error(f"Podcast Index search failed: {e}")
            return []

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """
        Search for podcast episodes.

        Note: Podcast Index doesn't support episode search directly.
        This searches for podcasts, then returns recent episodes from top results.
        """
        # Search for podcasts first
        podcasts = await self._search_podcast_index(query, max_results=5)
        if not podcasts:
            return []

        results = []
        for podcast in podcasts[:3]:  # Get episodes from top 3 matching podcasts
            feed_url = podcast.get("url")
            if not feed_url:
                continue

            episodes = await self.get_channel_videos(feed_url, max_results=5)
            results.extend(episodes)

            if len(results) >= max_results:
                break

        return results[:max_results]

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """Search for podcasts via Podcast Index API."""
        podcasts = await self._search_podcast_index(query, max_results)

        results = []
        for podcast in podcasts:
            try:
                results.append(ChannelResult(
                    platform=self.platform_id,
                    channel_id=str(podcast.get("id", "")),
                    channel_url=podcast.get("url", ""),
                    name=podcast.get("title", "Unknown Podcast"),
                    description=podcast.get("description", ""),
                    avatar_url=podcast.get("artwork") or podcast.get("image"),
                    subscriber_count=None,
                    video_count=podcast.get("episodeCount"),
                ))
            except Exception as e:
                logger.debug(f"Failed to parse podcast result: {e}")
                continue

        return results

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get episodes from a podcast RSS feed."""
        feed = await self._fetch_rss(channel_url)
        if not feed or not feed.get("entries"):
            return []

        # Get podcast info for channel metadata
        podcast_title = feed.feed.get("title", "Unknown Podcast")
        podcast_image = None
        if hasattr(feed.feed, "image") and feed.feed.image:
            podcast_image = getattr(feed.feed.image, "href", None)

        results = []
        for entry in feed.entries[:max_results]:
            try:
                # Parse publish date
                upload_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    upload_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    upload_date = datetime(*entry.updated_parsed[:6])

                # Filter by date if specified
                if since and upload_date and upload_date < since:
                    continue

                # Get audio URL from enclosures
                audio_url = None
                if hasattr(entry, "enclosures") and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("audio/"):
                            audio_url = enc.get("href") or enc.get("url")
                            break

                # Skip entries without audio
                if not audio_url:
                    # Try link as fallback
                    audio_url = entry.get("link")

                # Parse duration (iTunes format: HH:MM:SS or seconds)
                duration_seconds = self._parse_itunes_duration(
                    entry.get("itunes_duration", "")
                )

                # Get episode ID (use GUID or generate from URL)
                episode_id = entry.get("id") or entry.get("guid")
                if not episode_id and audio_url:
                    episode_id = hashlib.md5(audio_url.encode()).hexdigest()[:16]

                # Get thumbnail (episode-specific or fall back to podcast art)
                thumbnail = None
                if hasattr(entry, "image") and entry.image:
                    thumbnail = getattr(entry.image, "href", None)
                if not thumbnail:
                    thumbnail = podcast_image

                # Get description
                description = None
                if hasattr(entry, "summary"):
                    description = self._clean_html(entry.summary)[:2000]
                elif hasattr(entry, "description"):
                    description = self._clean_html(entry.description)[:2000]

                results.append(VideoResult(
                    platform=self.platform_id,
                    video_id=episode_id,
                    video_url=audio_url,
                    title=entry.get("title", "Untitled Episode"),
                    description=description,
                    thumbnail_url=thumbnail,
                    duration_seconds=duration_seconds,
                    upload_date=upload_date,
                    channel_name=podcast_title,
                    channel_id=self._generate_channel_id(channel_url),
                    channel_url=channel_url,
                ))

            except Exception as e:
                logger.debug(f"Failed to parse episode: {e}")
                continue

        return results

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get podcast info from RSS feed."""
        feed = await self._fetch_rss(channel_url)
        if not feed or not hasattr(feed, "feed"):
            return None

        podcast = feed.feed
        episode_count = len(feed.entries) if feed.entries else None

        # Get artwork
        artwork = None
        if hasattr(podcast, "image") and podcast.image:
            artwork = getattr(podcast.image, "href", None)
        if not artwork and hasattr(podcast, "itunes_image"):
            artwork = podcast.itunes_image.get("href") if isinstance(podcast.itunes_image, dict) else None

        return ChannelResult(
            platform=self.platform_id,
            channel_id=self._generate_channel_id(channel_url),
            channel_url=channel_url,
            name=podcast.get("title", "Unknown Podcast"),
            description=podcast.get("subtitle") or podcast.get("summary", ""),
            avatar_url=artwork,
            banner_url=None,
            subscriber_count=None,
            video_count=episode_count,
        )

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """
        Get single episode info.

        Note: For podcasts, video_url is typically the audio file URL.
        We can't fetch metadata from just the audio URL, so this returns None.
        Episode info should be obtained via get_channel_videos instead.
        """
        return None

    def _generate_channel_id(self, feed_url: str) -> str:
        """Generate a consistent channel ID from feed URL."""
        return hashlib.md5(feed_url.encode()).hexdigest()[:16]

    def _parse_itunes_duration(self, duration_str: str) -> Optional[int]:
        """Parse iTunes duration format (HH:MM:SS, MM:SS, or seconds)."""
        if not duration_str:
            return None

        try:
            duration_str = str(duration_str).strip()

            # If it's just a number, it's seconds
            if duration_str.isdigit():
                return int(duration_str)

            # Parse HH:MM:SS or MM:SS
            parts = duration_str.split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + int(s)

        except Exception:
            pass

        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""

        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()
