"""Channel search service for finding channels on YouTube and Rumble."""

import asyncio
import re
from typing import Optional

import httpx
import yt_dlp
from loguru import logger

from app.schemas.channel import ChannelSearchResult


async def search_youtube_channels(query: str, limit: int = 10) -> list[ChannelSearchResult]:
    """
    Search for YouTube channels by name using yt-dlp.

    Args:
        query: Search query
        limit: Maximum results to return

    Returns:
        List of channel search results
    """
    search_url = f"ytsearch{limit}:{query} channel"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
        'ignoreerrors': True,
    }

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: _extract_with_ytdlp(search_url, ydl_opts)
        )

        if not info or 'entries' not in info:
            return []

        results = []
        seen_channels = set()

        for entry in info.get('entries', []):
            if not entry:
                continue

            # Skip non-channel results - we want uploader info
            channel_id = entry.get('channel_id') or entry.get('uploader_id')
            channel_url = entry.get('channel_url') or entry.get('uploader_url')
            channel_name = entry.get('channel') or entry.get('uploader')

            if not channel_id or channel_id in seen_channels:
                continue

            seen_channels.add(channel_id)

            # Build channel URL if not provided
            if not channel_url and channel_id:
                channel_url = f"https://www.youtube.com/channel/{channel_id}"

            results.append(ChannelSearchResult(
                platform="youtube",
                channel_id=channel_id,
                channel_url=channel_url or "",
                name=channel_name or "Unknown",
                description=entry.get('description'),
                avatar_url=_get_thumbnail(entry),
                subscriber_count=None,  # Not available in search
                video_count=None,
            ))

            if len(results) >= limit:
                break

        # If we got video results, try to get more channel info
        if results:
            results = await _enrich_youtube_results(results[:limit])

        return results

    except Exception as e:
        logger.error(f"YouTube channel search failed: {e}")
        return []


async def _enrich_youtube_results(results: list[ChannelSearchResult]) -> list[ChannelSearchResult]:
    """Enrich YouTube results with channel metadata."""
    enriched = []

    for result in results:
        try:
            # Try to get channel info
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'playlist_items': '0',  # Don't get videos
            }

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda url=result.channel_url: _extract_with_ytdlp(url, ydl_opts)
            )

            if info:
                result = ChannelSearchResult(
                    platform="youtube",
                    channel_id=info.get('channel_id') or info.get('id') or result.channel_id,
                    channel_url=info.get('channel_url') or info.get('webpage_url') or result.channel_url,
                    name=info.get('channel') or info.get('uploader') or info.get('title') or result.name,
                    description=info.get('description') or result.description,
                    avatar_url=_get_thumbnail(info) or result.avatar_url,
                    subscriber_count=info.get('channel_follower_count'),
                    video_count=info.get('playlist_count'),
                )

            enriched.append(result)

        except Exception as e:
            logger.debug(f"Failed to enrich channel {result.channel_id}: {e}")
            enriched.append(result)

    return enriched


async def search_rumble_channels(query: str, limit: int = 10) -> list[ChannelSearchResult]:
    """
    Search for Rumble channels by name using web scraping.

    Args:
        query: Search query
        limit: Maximum results to return

    Returns:
        List of channel search results
    """
    search_url = f"https://rumble.com/search/channel?q={query}"

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        ) as client:
            response = await client.get(search_url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        return _parse_rumble_search_results(html, limit)

    except Exception as e:
        logger.error(f"Rumble channel search failed: {e}")
        return []


def _parse_rumble_search_results(html: str, limit: int) -> list[ChannelSearchResult]:
    """Parse Rumble search results HTML."""
    results = []

    # Find channel cards in the HTML
    # Rumble uses various patterns, try to extract channel info

    # Pattern for channel links: /c/channelname or /user/username
    channel_pattern = re.compile(
        r'<a[^>]*href="(/(?:c|user)/([^"]+))"[^>]*>.*?'
        r'(?:<img[^>]*src="([^"]*)"[^>]*>)?.*?'
        r'(?:class="[^"]*channel-name[^"]*"[^>]*>([^<]+)<)?',
        re.DOTALL | re.IGNORECASE
    )

    # Alternative simpler pattern
    simple_pattern = re.compile(
        r'href="/(c|user)/([^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]+)',
        re.IGNORECASE
    )

    seen = set()

    # Try to find channel listing items
    # Look for channel-item or similar class
    item_pattern = re.compile(
        r'class="[^"]*(?:channel-item|listing-entry)[^"]*"[^>]*>.*?'
        r'href="/(c|user)/([^"]+)"[^>]*>.*?'
        r'(?:class="[^"]*(?:channel-name|title)[^"]*"[^>]*>([^<]+)<)?.*?'
        r'(?:<img[^>]*src="([^"]*)")?.*?'
        r'(?:(\d+(?:\.\d+)?[KMB]?)\s*(?:followers|subscribers))?',
        re.DOTALL | re.IGNORECASE
    )

    for match in item_pattern.finditer(html):
        channel_type, channel_slug, name, avatar, followers = match.groups()

        if channel_slug in seen:
            continue
        seen.add(channel_slug)

        channel_url = f"https://rumble.com/{channel_type}/{channel_slug}"

        results.append(ChannelSearchResult(
            platform="rumble",
            channel_id=channel_slug,
            channel_url=channel_url,
            name=name.strip() if name else channel_slug,
            description=None,
            avatar_url=avatar,
            subscriber_count=_parse_follower_count(followers) if followers else None,
            video_count=None,
        ))

        if len(results) >= limit:
            break

    # Fallback to simpler pattern if no results
    if not results:
        for match in simple_pattern.finditer(html):
            channel_type, channel_slug, name = match.groups()

            if channel_slug in seen:
                continue
            seen.add(channel_slug)

            # Skip common non-channel paths
            if channel_slug in ('search', 'browse', 'live', 'latest'):
                continue

            channel_url = f"https://rumble.com/{channel_type}/{channel_slug}"

            results.append(ChannelSearchResult(
                platform="rumble",
                channel_id=channel_slug,
                channel_url=channel_url,
                name=name.strip() if name else channel_slug,
                description=None,
                avatar_url=None,
                subscriber_count=None,
                video_count=None,
            ))

            if len(results) >= limit:
                break

    return results


def _parse_follower_count(text: str) -> Optional[int]:
    """Parse follower count from text like '1.2M' or '500K'."""
    if not text:
        return None

    text = text.strip().upper()
    multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}

    try:
        for suffix, mult in multipliers.items():
            if suffix in text:
                num = float(text.replace(suffix, '').strip())
                return int(num * mult)
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _extract_with_ytdlp(url: str, opts: dict) -> dict | None:
    """Extract info using yt-dlp synchronously."""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        logger.debug(f"yt-dlp extraction failed for {url}: {e}")
        return None


def _get_thumbnail(info: dict) -> Optional[str]:
    """Get best thumbnail URL from info dict."""
    if info.get('thumbnail'):
        return info['thumbnail']

    thumbnails = info.get('thumbnails', [])
    if thumbnails:
        # Sort by preference/size
        sorted_thumbs = sorted(
            thumbnails,
            key=lambda t: t.get('preference', 0) or t.get('width', 0),
            reverse=True
        )
        return sorted_thumbs[0].get('url')

    return None
