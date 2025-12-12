"""Content extraction from HTML pages."""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import trafilatura


@dataclass
class ImageInfo:
    """Information about an image on a page."""
    src: str
    alt: Optional[str]
    title: Optional[str]
    width: Optional[int]
    height: Optional[int]


@dataclass
class VideoInfo:
    """Information about a video on a page."""
    video_url: str
    thumbnail_url: Optional[str]
    embed_type: str  # "youtube", "vimeo", "direct"
    video_id: Optional[str]
    title: Optional[str]
    width: Optional[int]
    height: Optional[int]


@dataclass
class ExtractedContent:
    """Extracted content from a web page."""
    title: Optional[str]
    description: Optional[str]
    content: str
    headings: list[str]
    links: list[str]
    images: list[ImageInfo]
    videos: list[VideoInfo]
    word_count: int
    published_date: Optional[str]


class ContentExtractor:
    """Extract readable content from HTML pages."""

    def extract(self, html: str, url: str) -> ExtractedContent:
        """
        Extract content from HTML.

        Uses trafilatura for main content extraction and BeautifulSoup
        for metadata and links.
        """
        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title = self._extract_title(soup)

        # Extract meta description
        description = self._extract_description(soup)

        # Extract main content using trafilatura
        content = self._extract_main_content(html)

        # Extract headings
        headings = self._extract_headings(soup)

        # Extract links
        links = self._extract_links(soup, url)

        # Extract images
        images = self._extract_images(soup, url)

        # Extract videos
        videos = self._extract_videos(soup, url)

        # Extract published date
        published_date = self._extract_date(html)

        # Count words
        word_count = len(content.split()) if content else 0

        return ExtractedContent(
            title=title,
            description=description,
            content=content,
            headings=headings,
            links=links,
            images=images,
            videos=videos,
            word_count=word_count,
            published_date=published_date,
        )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        # Try <title> tag
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        # Try <h1>
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description."""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()[:500]

        # Try og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()[:500]

        return None

    def _extract_main_content(self, html: str) -> str:
        """Extract main content using trafilatura."""
        try:
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            return content or ""
        except Exception:
            return ""

    def _extract_headings(self, soup: BeautifulSoup) -> list[str]:
        """Extract h1-h3 headings."""
        headings = []
        for tag in ['h1', 'h2', 'h3']:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text and len(text) < 200:
                    headings.append(text)
        return headings[:20]  # Limit to 20 headings

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract links from the page."""
        links = []
        seen = set()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # Skip empty, javascript, and anchor links
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)

            # Only include http/https links
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ('http', 'https'):
                continue

            # Remove fragments
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            # Deduplicate
            if clean_url not in seen:
                seen.add(clean_url)
                links.append(clean_url)

        return links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[ImageInfo]:
        """Extract images from the page."""
        images = []
        seen_srcs = set()

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src:
                continue

            # Resolve relative URLs
            absolute_src = urljoin(base_url, src)

            # Skip data URIs and duplicates
            if absolute_src.startswith('data:') or absolute_src in seen_srcs:
                continue

            # Skip tiny images (likely icons/tracking pixels)
            width = self._parse_dimension(img.get('width'))
            height = self._parse_dimension(img.get('height'))
            if width and height and width < 50 and height < 50:
                continue

            seen_srcs.add(absolute_src)

            images.append(ImageInfo(
                src=absolute_src,
                alt=img.get('alt', '').strip()[:500] or None,
                title=img.get('title', '').strip()[:200] or None,
                width=width,
                height=height,
            ))

        return images[:50]  # Limit to 50 images per page

    def _parse_dimension(self, value: Optional[str]) -> Optional[int]:
        """Parse width/height attribute to integer."""
        if not value:
            return None
        try:
            # Remove 'px' suffix if present
            clean = re.sub(r'[^\d]', '', str(value))
            return int(clean) if clean else None
        except (ValueError, TypeError):
            return None

    def _extract_date(self, html: str) -> Optional[str]:
        """Extract publication date using trafilatura."""
        try:
            from htmldate import find_date
            date = find_date(html)
            return date
        except Exception:
            return None

    def _extract_videos(self, soup: BeautifulSoup, base_url: str) -> list[VideoInfo]:
        """Extract videos from the page (YouTube, Vimeo, direct files)."""
        videos = []
        seen_ids = set()

        # 1. YouTube embeds (iframe src patterns)
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '') or iframe.get('data-src', '')
            if not src:
                continue

            # Match youtube.com/embed/VIDEO_ID or youtu.be/VIDEO_ID
            youtube_match = re.search(r'(?:youtube\.com/embed/|youtu\.be/)([a-zA-Z0-9_-]{11})', src)
            if youtube_match:
                video_id = youtube_match.group(1)
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                videos.append(VideoInfo(
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    thumbnail_url=f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                    embed_type="youtube",
                    video_id=video_id,
                    title=iframe.get('title'),
                    width=self._parse_dimension(iframe.get('width')),
                    height=self._parse_dimension(iframe.get('height')),
                ))
                continue

            # 2. Vimeo embeds
            vimeo_match = re.search(r'player\.vimeo\.com/video/(\d+)', src)
            if vimeo_match:
                video_id = vimeo_match.group(1)
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                videos.append(VideoInfo(
                    video_url=f"https://vimeo.com/{video_id}",
                    thumbnail_url=None,  # Vimeo requires API for thumbnails
                    embed_type="vimeo",
                    video_id=video_id,
                    title=iframe.get('title'),
                    width=self._parse_dimension(iframe.get('width')),
                    height=self._parse_dimension(iframe.get('height')),
                ))

        # 3. Direct video files (<video> and <source> tags)
        for video_tag in soup.find_all('video'):
            src = video_tag.get('src')
            if not src:
                source_tag = video_tag.find('source')
                src = source_tag.get('src') if source_tag else None

            if not src:
                continue

            # Resolve relative URLs
            absolute_src = urljoin(base_url, src)

            # Only include video file extensions
            if not re.search(r'\.(mp4|webm|ogg|mov)(\?|$)', absolute_src, re.I):
                continue

            if absolute_src in seen_ids:
                continue
            seen_ids.add(absolute_src)

            # Get poster/thumbnail
            poster = video_tag.get('poster')
            if poster:
                poster = urljoin(base_url, poster)

            videos.append(VideoInfo(
                video_url=absolute_src,
                thumbnail_url=poster,
                embed_type="direct",
                video_id=None,
                title=video_tag.get('title'),
                width=self._parse_dimension(video_tag.get('width')),
                height=self._parse_dimension(video_tag.get('height')),
            ))

        return videos[:30]  # Limit to 30 videos per page
