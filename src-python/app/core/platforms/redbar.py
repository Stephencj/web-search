"""Red Bar Radio platform adapter with session-based authentication."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.platforms.base import (
    PlatformAdapter,
    VideoResult,
    ChannelResult,
)


class RedBarPlatform(PlatformAdapter):
    """
    Red Bar Radio platform adapter.

    Supports authenticated access to premium podcast episodes via session cookies.
    Episodes are treated as "videos" for compatibility with the existing feed system.
    """

    platform_id = "redbar"
    platform_name = "Red Bar Radio"
    platform_icon = "🎙️"
    platform_color = "#FF0000"

    supports_search = True
    supports_channel_feed = True
    supports_playlists = False

    BASE_URL = "https://redbarradio.net"
    EPISODES_URL = "https://redbarradio.net/episodes"
    LOGIN_URL = "https://redbarradio.net/user/login"

    def __init__(
        self,
        rate_limit_delay: float = 2.0,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        session_cookies: Optional[dict] = None,
    ):
        """
        Initialize Red Bar Radio platform adapter.

        Args:
            rate_limit_delay: Delay between requests in seconds
            user_agent: User agent string for requests
            session_cookies: Optional session cookies for authenticated access
        """
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent
        self.session_cookies = session_cookies or {}

    def set_session_cookies(self, cookies: dict):
        """Set session cookies for authenticated requests."""
        self.session_cookies = cookies

    def can_handle_url(self, url: str) -> bool:
        """Check if URL is a Red Bar Radio URL."""
        try:
            parsed = urlparse(url.lower())
            return parsed.netloc in ["redbarradio.net", "www.redbarradio.net"]
        except Exception:
            return False

    def _get_headers(self) -> dict:
        """Get request headers."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with optional authentication."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    cookies=self.session_cookies,
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Red Bar fetch failed for {url}: {e}")
            return None

    async def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[VideoResult]:
        """Search for episodes on Red Bar Radio."""
        # Red Bar uses WordPress search
        search_url = f"{self.BASE_URL}/?s={query}"

        html = await self._fetch_page(search_url)
        if not html:
            return []

        return self._parse_episode_list(html, max_results)

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ChannelResult]:
        """
        Search for channels - Red Bar is a single show/channel.
        Returns the show itself if query matches.
        """
        if "red bar" in query.lower() or "redbar" in query.lower():
            return [
                ChannelResult(
                    platform=self.platform_id,
                    channel_id="redbarradio",
                    channel_url=self.BASE_URL,
                    name="Red Bar Radio",
                    description="Comedy talk radio show and podcast since 2003",
                    avatar_url=None,
                    subscriber_count=None,
                    video_count=None,
                )
            ]
        return []

    async def get_channel_videos(
        self,
        channel_url: str,
        max_results: int = 50,
        since: Optional[datetime] = None,
    ) -> list[VideoResult]:
        """Get episodes from Red Bar Radio."""
        results = []
        page = 1

        while len(results) < max_results:
            if page == 1:
                url = self.EPISODES_URL
            else:
                url = f"{self.EPISODES_URL}?page={page}"

            html = await self._fetch_page(url)
            if not html:
                break

            page_results = self._parse_episode_list(html, max_results - len(results))
            if not page_results:
                break

            # Filter by date if specified
            for episode in page_results:
                if since and episode.upload_date and episode.upload_date < since:
                    # Episodes are chronological, stop if we hit old content
                    return results
                results.append(episode)

            # Check if there's a next page
            if not self._has_next_page(html):
                break

            page += 1

        return results[:max_results]

    async def get_channel_info(
        self,
        channel_url: str,
    ) -> Optional[ChannelResult]:
        """Get Red Bar Radio channel info."""
        return ChannelResult(
            platform=self.platform_id,
            channel_id="redbarradio",
            channel_url=self.BASE_URL,
            name="Red Bar Radio",
            description="Comedy talk radio show and podcast broadcast out of Chicago since 2003",
            avatar_url=None,
            banner_url=None,
            subscriber_count=None,
            video_count=None,
        )

    async def get_video_info(
        self,
        video_url: str,
    ) -> Optional[VideoResult]:
        """Get single episode metadata."""
        html = await self._fetch_page(video_url)
        if not html:
            return None

        return self._parse_episode_page(html, video_url)

    def _parse_episode_list(self, html: str, max_results: int) -> list[VideoResult]:
        """Parse episodes from Red Bar's episode list page."""
        results = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Red Bar uses a table structure for episode listing
            # Look for the episode table first
            episode_table = soup.select_one("table.full-content-list, table#media-content, table")

            if episode_table:
                # Parse table rows - each row is an episode
                rows = episode_table.select("tbody tr")

                for row in rows[:max_results]:
                    try:
                        # Get all cells in the row
                        cells = row.select("td")
                        if len(cells) < 2:
                            continue

                        # First cell: date with link
                        # Second cell: episode title with link
                        date_cell = cells[0]
                        title_cell = cells[1]

                        # Get the episode link (from title cell or date cell)
                        link = title_cell.select_one("a[href]") or date_cell.select_one("a[href]")
                        if not link:
                            continue

                        href = link.get("href", "")
                        if not href:
                            continue

                        # Skip non-episode links
                        if any(skip in href.lower() for skip in ["/user/", "/login", "/register", "javascript:"]):
                            continue

                        # Must be a redbarradio.net link or relative path
                        if href.startswith("http") and "redbarradio.net" not in href:
                            continue

                        if not href.startswith("http"):
                            href = urljoin(self.BASE_URL, href)

                        video_id = self._extract_episode_id(href)
                        if not video_id:
                            continue

                        # Get title from title cell
                        title = title_cell.get_text(strip=True)
                        if not title or len(title) < 3:
                            continue

                        # Parse date from date cell (format: MM/DD/YY)
                        upload_date = None
                        date_text = date_cell.get_text(strip=True)
                        if date_text:
                            # Try MM/DD/YY format
                            date_match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_text)
                            if date_match:
                                month, day, year = date_match.groups()
                                # Handle 2-digit year
                                if len(year) == 2:
                                    year = "20" + year
                                try:
                                    upload_date = datetime(int(year), int(month), int(day))
                                except ValueError:
                                    pass

                        # Check if it's a free episode (third cell may have "FREE!" class)
                        is_free = False
                        if len(cells) >= 3:
                            free_link = cells[2].select_one("a.free")
                            is_free = free_link is not None

                        results.append(VideoResult(
                            platform=self.platform_id,
                            video_id=video_id,
                            video_url=href,
                            title=title,
                            description=f"{'Free episode' if is_free else 'Scars Club episode'}",
                            thumbnail_url=None,
                            duration_seconds=None,
                            upload_date=upload_date,
                            channel_name="Red Bar Radio",
                            channel_id="redbarradio",
                            channel_url=self.BASE_URL,
                        ))

                        logger.debug(f"Parsed Red Bar episode: {title} ({href})")

                    except Exception as e:
                        logger.debug(f"Failed to parse episode row: {e}")
                        continue

                if results:
                    logger.info(f"Parsed {len(results)} episodes from Red Bar table")
                    return results

            # Fallback: Try article-based parsing for search results or other pages
            episode_selectors = [
                "article.post",
                ".episode-item",
                ".post-item",
            ]

            episodes = []
            for selector in episode_selectors:
                episodes = soup.select(selector)
                if episodes:
                    break

            # If no containers found, try parsing h2 links directly (search results page)
            if not episodes:
                h2_links = soup.select("h2 a[href], h3 a[href]")
                for link in h2_links[:max_results]:
                    href = link.get("href", "")
                    if not href:
                        continue

                    if any(skip in href.lower() for skip in ["/user/", "/login", "/register", "javascript:"]):
                        continue

                    if href.startswith("http") and "redbarradio.net" not in href:
                        continue

                    if not href.startswith("http"):
                        href = urljoin(self.BASE_URL, href)

                    video_id = self._extract_episode_id(href)
                    if not video_id:
                        continue

                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue

                    upload_date = None
                    parent = link.find_parent()
                    if parent:
                        parent_text = parent.get_text()
                        date_match = re.search(
                            r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})",
                            parent_text,
                            re.IGNORECASE
                        )
                        if date_match:
                            upload_date = self._parse_date(date_match.group(1))

                    results.append(VideoResult(
                        platform=self.platform_id,
                        video_id=video_id,
                        video_url=href,
                        title=title,
                        description=None,
                        thumbnail_url=None,
                        duration_seconds=None,
                        upload_date=upload_date,
                        channel_name="Red Bar Radio",
                        channel_id="redbarradio",
                        channel_url=self.BASE_URL,
                    ))

                    if len(results) >= max_results:
                        break

                return results

            for item in episodes[:max_results]:
                try:
                    episode = self._parse_episode_item(item)
                    if episode:
                        results.append(episode)
                except Exception as e:
                    logger.debug(f"Failed to parse episode item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse Red Bar episode list: {e}")

        return results

    def _parse_episode_item(self, item) -> Optional[VideoResult]:
        """Parse a single episode from a list item."""
        try:
            # Get episode URL
            link = item.select_one("a[href]")
            if not link:
                return None

            href = link.get("href", "")
            if not href.startswith("http"):
                href = urljoin(self.BASE_URL, href)

            # Skip non-episode links
            if "/episodes/" not in href and "/show/" not in href and "/node/" not in href:
                # Try to find title link
                title_link = item.select_one("h2 a, h3 a, .title a, .entry-title a")
                if title_link:
                    href = title_link.get("href", "")
                    if not href.startswith("http"):
                        href = urljoin(self.BASE_URL, href)

            video_id = self._extract_episode_id(href)
            if not video_id:
                return None

            # Get title
            title_elem = item.select_one("h2, h3, .title, .entry-title, .episode-title")
            title = title_elem.get_text(strip=True) if title_elem else "Untitled Episode"

            # Get description
            description = None
            desc_elem = item.select_one(".excerpt, .description, .entry-content, .summary, p")
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:500]

            # Get thumbnail
            thumbnail_url = None
            img = item.select_one("img")
            if img:
                thumbnail_url = img.get("src") or img.get("data-src")
                if thumbnail_url and not thumbnail_url.startswith("http"):
                    thumbnail_url = urljoin(self.BASE_URL, thumbnail_url)

            # Get date
            upload_date = None
            date_elem = item.select_one("time, .date, .post-date, .entry-date")
            if date_elem:
                date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                upload_date = self._parse_date(date_text)

            # Get duration (often shown as "X hours Y minutes")
            duration_seconds = None
            duration_elem = item.select_one(".duration, .length, .runtime")
            if duration_elem:
                duration_seconds = self._parse_duration(duration_elem.get_text(strip=True))

            # Get audio URL if visible
            audio_url = None
            audio_link = item.select_one("a[href*='.mp3'], a[href*='media.redbarradio']")
            if audio_link:
                audio_url = audio_link.get("href")

            return VideoResult(
                platform=self.platform_id,
                video_id=video_id,
                video_url=audio_url or href,  # Prefer direct audio URL
                title=title,
                description=description,
                thumbnail_url=thumbnail_url,
                duration_seconds=duration_seconds,
                upload_date=upload_date,
                channel_name="Red Bar Radio",
                channel_id="redbarradio",
                channel_url=self.BASE_URL,
            )

        except Exception as e:
            logger.debug(f"Failed to parse episode item: {e}")
            return None

    def _parse_episode_page(self, html: str, video_url: str) -> Optional[VideoResult]:
        """Parse single episode page for full metadata."""
        try:
            soup = BeautifulSoup(html, "lxml")

            video_id = self._extract_episode_id(video_url)
            if not video_id:
                return None

            # Get title
            title_elem = soup.select_one("h1, .episode-title, .entry-title")
            title = title_elem.get_text(strip=True) if title_elem else "Untitled Episode"

            # Get description
            description = None
            desc_elem = soup.select_one(".episode-content, .entry-content, .description, article p")
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:2000]

            # Get thumbnail from meta tag
            thumbnail_url = None
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image:
                thumbnail_url = og_image.get("content")

            # Get date
            upload_date = None
            date_elem = soup.select_one("time, .date, .post-date, .entry-date")
            if date_elem:
                date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                upload_date = self._parse_date(date_text)

            # Get duration
            duration_seconds = None
            # Look for duration in text
            duration_match = re.search(r"(\d+)\s*hours?\s*(?:and\s*)?(\d+)?\s*min", html, re.IGNORECASE)
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2) or 0)
                duration_seconds = hours * 3600 + minutes * 60

            # Find audio/download URL (MP3 fallback)
            audio_url = None
            audio_link = soup.select_one(
                "a[href*='.mp3'], a[href*='media.redbarradio'], audio source, .download-link a"
            )
            if audio_link:
                audio_url = audio_link.get("href") or audio_link.get("src")
                if audio_url and not audio_url.startswith("http"):
                    audio_url = urljoin(self.BASE_URL, audio_url)

            # Also look for audio URL in specific patterns
            if not audio_url:
                audio_match = re.search(
                    r'["\']?(https?://media\.redbarradio[^"\'>\s]+\.mp3)["\']?',
                    html,
                    re.IGNORECASE
                )
                if audio_match:
                    audio_url = audio_match.group(1)

            # Extract HLS video URL from embed iframe
            # Red Bar embeds video in /embed/vod2?id={EPISODE-ID} iframe
            video_stream_url = None
            embed_match = re.search(r'/embed/vod2\?id=([^"\'&\s]+)', html)
            if embed_match:
                embed_id = embed_match.group(1)
                video_stream_url = self._fetch_embed_hls_url(embed_id)

            # Fallback: try extracting from main page
            if not video_stream_url:
                video_stream_url = self._extract_hls_url(soup, html)

            # If still no HLS URL found, try other video formats
            if not video_stream_url:
                video_stream_url = self._extract_video_url(soup, html)

            return VideoResult(
                platform=self.platform_id,
                video_id=video_id,
                video_url=video_url,  # Keep original episode page URL
                title=title,
                description=description,
                thumbnail_url=thumbnail_url,
                duration_seconds=duration_seconds,
                upload_date=upload_date,
                channel_name="Red Bar Radio",
                channel_id="redbarradio",
                channel_url=self.BASE_URL,
                audio_url=audio_url,  # MP3 fallback
                video_stream_url=video_stream_url,  # HLS stream
            )

        except Exception as e:
            logger.warning(f"Failed to parse Red Bar episode page: {e}")
            return None

    def _fetch_embed_hls_url(self, embed_id: str) -> Optional[str]:
        """
        Fetch the embed page and extract HLS URL.

        Red Bar video is served from /embed/vod2?id={EPISODE-ID} which contains
        the signed HLS URL from vid.redbarradio.com.
        """
        import httpx

        embed_url = f"{self.BASE_URL}/embed/vod2?id={embed_id}"
        logger.debug(f"Fetching embed page: {embed_url}")

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                response = client.get(embed_url, cookies=self.session_cookies)
                if response.status_code != 200:
                    logger.debug(f"Embed page returned {response.status_code}")
                    return None

                html = response.text

                # Look for HLS URL in source tag or script
                # Pattern: https://vid.redbarradio.com/{token},{expiry}/encoded/{ID}/hls.m3u8
                hls_match = re.search(
                    r'https://vid\.redbarradio\.com/[^"\'<>\s]+\.m3u8',
                    html
                )
                if hls_match:
                    hls_url = hls_match.group(0)
                    logger.info(f"Found HLS URL from embed: {hls_url[:80]}...")
                    return hls_url

                logger.debug("No HLS URL found in embed page")
                return None

        except Exception as e:
            logger.warning(f"Failed to fetch embed page: {e}")
            return None

    def _extract_hls_url(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """
        Extract HLS manifest URL from episode page (fallback).

        Red Bar uses HLS streaming at vid.redbarradio.com with signed URLs.
        URL pattern: https://vid.redbarradio.com/{token},{expiry}/encoded/{EPISODE-ID}/hls/master.m3u8
        """
        # Look for HLS manifest in JavaScript/HTML
        hls_patterns = [
            # Direct HLS manifest URLs
            r'["\']?(https://vid\.redbarradio\.com/[^"\']+/hls/[^"\']*\.m3u8)["\']?',
            r'["\']?(https://vid\.redbarradio\.com/[^"\']+/hls/master\.m3u8)["\']?',
            # Generic HLS source patterns
            r'source["\s:=]+["\']([^"\']+\.m3u8)["\']',
            r'hls["\s:=]+["\']([^"\']+\.m3u8)["\']',
            r'src["\s:=]+["\']([^"\']+\.m3u8)["\']',
        ]

        for pattern in hls_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                logger.debug(f"Found HLS manifest URL: {url}")
                return url

        # Look for vid.redbarradio base URL pattern and construct manifest
        # Pattern: vid.redbarradio.com/{token},{expiry}/encoded/{EPISODE-ID}
        token_pattern = r'vid\.redbarradio\.com/([^/,]+,[^/]+)/encoded/([^/\s"\']+)'
        match = re.search(token_pattern, html)
        if match:
            token, episode_id = match.groups()
            hls_url = f"https://vid.redbarradio.com/{token}/encoded/{episode_id}/hls/master.m3u8"
            logger.debug(f"Constructed HLS URL from token: {hls_url}")
            return hls_url

        # Look for any vid.redbarradio URL that might lead to HLS
        vid_pattern = r'["\']?(https://vid\.redbarradio\.com/[^"\'>\s]+)["\']?'
        match = re.search(vid_pattern, html)
        if match:
            base_url = match.group(1)
            # Check if it's already an HLS URL
            if '.m3u8' in base_url:
                return base_url
            # Try to construct master.m3u8 URL
            if '/encoded/' in base_url:
                parts = base_url.split('/hls/')
                if len(parts) > 1:
                    # Already has /hls/ path, construct master URL
                    return parts[0] + '/hls/master.m3u8'
                elif '/encoded/' in base_url:
                    # Has /encoded/ but no /hls/, append it
                    base = base_url.rstrip('/')
                    # Remove any segment path
                    if '.ts' in base or '.aac' in base:
                        base = '/'.join(base.split('/')[:-1])
                    if not base.endswith('/hls'):
                        base = base.rsplit('/hls', 1)[0] if '/hls' in base else base
                    return f"{base}/hls/master.m3u8"

        return None

    def _extract_video_url(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """
        Extract video URL from episode page (non-HLS fallback).

        Looks for video content in multiple locations:
        - <video> tags with src/source
        - og:video meta tag
        - MP4 URLs in script tags (player configuration)
        - data-video-* attributes

        Note: HLS extraction is handled separately by _extract_hls_url()
        """
        video_url = None

        # 1. Check <video> tags
        video_elem = soup.select_one("video")
        if video_elem:
            # Check direct src
            video_url = video_elem.get("src")
            if not video_url:
                # Check source children - prefer HLS, then MP4
                source = video_elem.select_one("source[src*='.m3u8']")
                if source:
                    return source.get("src")
                source = video_elem.select_one("source[src*='.mp4'], source[type*='video']")
                if source:
                    video_url = source.get("src")

        # 2. Check og:video meta tag
        if not video_url:
            og_video = soup.select_one('meta[property="og:video"], meta[property="og:video:url"]')
            if og_video:
                video_url = og_video.get("content")

        # 3. Check data-video-* attributes
        if not video_url:
            video_data = soup.select_one("[data-video-url], [data-video-src], [data-video]")
            if video_data:
                video_url = (
                    video_data.get("data-video-url") or
                    video_data.get("data-video-src") or
                    video_data.get("data-video")
                )

        # 4. Search for MP4 URLs in script tags
        if not video_url:
            # Look for common video URL patterns in scripts
            mp4_patterns = [
                r'["\']([^"\']+\.mp4)["\']',  # Simple quoted .mp4 URLs
                r'video[_\-]?url["\s:=]+["\']([^"\']+)["\']',  # video_url: "..."
                r'src["\s:=]+["\']([^"\']+\.mp4)["\']',  # src: "...mp4"
                r'file["\s:=]+["\']([^"\']+\.mp4)["\']',  # file: "...mp4"
                r'source["\s:=]+["\']([^"\']+\.mp4)["\']',  # source: "...mp4"
            ]

            for pattern in mp4_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    potential_url = match.group(1)
                    # Validate it looks like a real video URL
                    if (potential_url.startswith("http") or potential_url.startswith("/")) and \
                       ".mp4" in potential_url.lower():
                        video_url = potential_url
                        break

        # 5. Look for media.redbarradio video URLs specifically
        if not video_url:
            redbar_video_match = re.search(
                r'["\']?(https?://media\.redbarradio[^"\'>\s]+\.mp4)["\']?',
                html,
                re.IGNORECASE
            )
            if redbar_video_match:
                video_url = redbar_video_match.group(1)

        # Normalize URL
        if video_url:
            if not video_url.startswith("http"):
                video_url = urljoin(self.BASE_URL, video_url)
            logger.debug(f"Found video URL: {video_url}")

        return video_url

    def _has_next_page(self, html: str) -> bool:
        """Check if there's a next page of episodes."""
        try:
            soup = BeautifulSoup(html, "lxml")
            # Look for pagination links (note: :contains() is not valid CSS, use text search)
            next_link = soup.select_one(
                "a.next, .pagination a[rel='next'], .pager-next a"
            )
            if next_link:
                return True
            # Check for any link containing "next" text
            for link in soup.select("a[href]"):
                if "next" in link.get_text(strip=True).lower():
                    return True
            return False
        except Exception:
            return False

    def _extract_episode_id(self, url: str) -> Optional[str]:
        """Extract episode ID from URL."""
        if not url:
            return None

        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")

            # Try various patterns
            # /shows/episode-name -> episode-name
            # /archives/episode-name -> episode-name
            # /show/episode-name -> episode-name
            # /episodes/episode-name -> episode-name
            # /music/playlist-name -> music-playlist-name (skip these)
            if path:
                # Skip non-episode paths
                if path.startswith("music/"):
                    return None

                # Remove common prefixes
                for prefix in ["shows/", "archives/", "show/", "episodes/", "episode/", "node/"]:
                    if path.startswith(prefix):
                        path = path[len(prefix):]
                        break

                # Use slug or path as ID
                episode_id = path.split("/")[0]
                if episode_id:
                    return episode_id

        except Exception:
            pass

        return None

    def _parse_duration(self, text: str) -> Optional[int]:
        """Parse duration from various formats."""
        if not text:
            return None

        try:
            # Try "HH:MM:SS" or "MM:SS"
            time_match = re.search(r"(\d+):(\d+)(?::(\d+))?", text)
            if time_match:
                parts = [int(p) for p in time_match.groups() if p]
                if len(parts) == 3:
                    return parts[0] * 3600 + parts[1] * 60 + parts[2]
                elif len(parts) == 2:
                    return parts[0] * 60 + parts[1]

            # Try "X hours Y minutes"
            hours_match = re.search(r"(\d+)\s*h(?:our)?s?", text, re.IGNORECASE)
            mins_match = re.search(r"(\d+)\s*m(?:in(?:ute)?)?s?", text, re.IGNORECASE)

            total = 0
            if hours_match:
                total += int(hours_match.group(1)) * 3600
            if mins_match:
                total += int(mins_match.group(1)) * 60

            return total if total > 0 else None

        except Exception:
            return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        """Parse date from various formats."""
        if not text:
            return None

        try:
            # ISO format
            if "T" in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00"))

            # Common date formats
            for fmt in [
                "%Y-%m-%d",
                "%B %d, %Y",
                "%b %d, %Y",
                "%d %B %Y",
                "%d %b %Y",
                "%m/%d/%Y",
                "%d/%m/%Y",
            ]:
                try:
                    return datetime.strptime(text.strip(), fmt)
                except ValueError:
                    continue

        except Exception:
            pass

        return None
