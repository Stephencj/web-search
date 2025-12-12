"""Image and video deduplication using perceptual hashing and CLIP embeddings."""

import asyncio
from io import BytesIO
from typing import Optional
import numpy as np

import httpx
from loguru import logger
from PIL import Image

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning("imagehash not available - perceptual hashing disabled")


class ImageDedup:
    """
    Image deduplication using perceptual hashing (pHash).

    pHash creates a fingerprint based on image structure that is resistant to:
    - Resizing
    - Minor color/brightness changes
    - Slight cropping
    - Different compression levels
    """

    def __init__(self, threshold: int = 8):
        """
        Initialize image deduplicator.

        Args:
            threshold: Maximum Hamming distance between hashes to consider
                      images as duplicates. Lower = stricter matching.
                      Default 8 catches most duplicates while avoiding false positives.
        """
        self.threshold = threshold
        self._hashes: dict[str, str] = {}  # url -> hash hex string
        self._lock = asyncio.Lock()

    async def compute_hash_from_url(self, url: str, timeout: float = 10.0) -> Optional[str]:
        """
        Download image and compute perceptual hash.

        Args:
            url: Image URL to download
            timeout: Download timeout in seconds

        Returns:
            Hex string of perceptual hash, or None if failed
        """
        if not IMAGEHASH_AVAILABLE:
            return None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code != 200:
                    return None

                # Load image
                img = Image.open(BytesIO(response.content))

                # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')

                # Compute perceptual hash
                phash = imagehash.phash(img)
                return str(phash)

        except Exception as e:
            logger.debug(f"Failed to compute image hash for {url}: {e}")
            return None

    def compute_hash_from_bytes(self, image_data: bytes) -> Optional[str]:
        """
        Compute perceptual hash from image bytes.

        Args:
            image_data: Raw image bytes

        Returns:
            Hex string of perceptual hash, or None if failed
        """
        if not IMAGEHASH_AVAILABLE:
            return None

        try:
            img = Image.open(BytesIO(image_data))
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            phash = imagehash.phash(img)
            return str(phash)
        except Exception as e:
            logger.debug(f"Failed to compute image hash from bytes: {e}")
            return None

    def is_duplicate_hash(self, hash1: str, hash2: str) -> bool:
        """
        Check if two hashes represent duplicate images.

        Args:
            hash1: First perceptual hash (hex string)
            hash2: Second perceptual hash (hex string)

        Returns:
            True if images are considered duplicates
        """
        if not IMAGEHASH_AVAILABLE or not hash1 or not hash2:
            return False

        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            distance = h1 - h2  # Hamming distance
            return distance <= self.threshold
        except Exception:
            return False

    async def is_duplicate(self, url: str) -> bool:
        """
        Check if an image URL is a duplicate of any previously seen image.

        Args:
            url: Image URL to check

        Returns:
            True if image is a duplicate
        """
        if not IMAGEHASH_AVAILABLE:
            return False

        img_hash = await self.compute_hash_from_url(url)
        if not img_hash:
            return False

        async with self._lock:
            # Check against existing hashes
            for existing_url, existing_hash in self._hashes.items():
                if existing_url == url:
                    continue
                if self.is_duplicate_hash(img_hash, existing_hash):
                    logger.debug(f"Duplicate image detected: {url} matches {existing_url}")
                    return True

            # Not a duplicate - store this hash
            self._hashes[url] = img_hash
            return False

    def add_hash(self, url: str, hash_value: str) -> None:
        """Add a pre-computed hash to the cache."""
        if hash_value:
            self._hashes[url] = hash_value

    def clear(self) -> None:
        """Clear the hash cache."""
        self._hashes.clear()


class EmbeddingDedup:
    """
    Deduplication using CLIP embedding similarity.

    This is used for display-time deduplication of search results,
    since we already have CLIP embeddings stored in Meilisearch.
    """

    def __init__(self, similarity_threshold: float = 0.95):
        """
        Initialize embedding deduplicator.

        Args:
            similarity_threshold: Cosine similarity threshold (0-1).
                                 Higher = more strict (fewer false positives).
                                 0.95 means 95% similar images are considered duplicates.
        """
        self.similarity_threshold = similarity_threshold

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def deduplicate_results(
        self,
        results: list[dict],
        embedding_key: str = "_vectors",
        embedder_name: str = "image"
    ) -> list[dict]:
        """
        Remove duplicate results based on embedding similarity.

        Args:
            results: List of search result dictionaries
            embedding_key: Key in result dict containing embeddings
            embedder_name: Name of the embedder (for nested vector structure)

        Returns:
            Deduplicated list of results (preserves order, removes later duplicates)
        """
        if not results:
            return results

        unique_results = []
        seen_embeddings: list[list[float]] = []

        for result in results:
            # Extract embedding
            embedding = None
            if embedding_key in result:
                vectors = result[embedding_key]
                if isinstance(vectors, dict) and embedder_name in vectors:
                    embedding = vectors[embedder_name]
                elif isinstance(vectors, list):
                    embedding = vectors

            # If no embedding, keep the result (can't dedupe without it)
            if not embedding:
                unique_results.append(result)
                continue

            # Check against seen embeddings
            is_duplicate = False
            for seen_emb in seen_embeddings:
                similarity = self.cosine_similarity(embedding, seen_emb)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_results.append(result)
                seen_embeddings.append(embedding)

        logger.debug(
            f"Deduplication: {len(results)} -> {len(unique_results)} results "
            f"(removed {len(results) - len(unique_results)} duplicates)"
        )
        return unique_results

    def deduplicate_by_url_similarity(
        self,
        results: list[dict],
        url_key: str = "image_url"
    ) -> list[dict]:
        """
        Remove results with identical or near-identical URLs.

        This handles cases where the same image appears with slightly different URLs
        (e.g., different query params, CDN variations).

        Args:
            results: List of search result dictionaries
            url_key: Key containing the image/video URL

        Returns:
            Deduplicated list
        """
        if not results:
            return results

        unique_results = []
        seen_base_urls: set[str] = set()

        for result in results:
            url = result.get(url_key, "")

            # Normalize URL - remove query params and common CDN variations
            base_url = self._normalize_url(url)

            if base_url not in seen_base_urls:
                unique_results.append(result)
                seen_base_urls.add(base_url)

        return unique_results

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication comparison.

        Removes query params and handles common CDN variations.
        """
        if not url:
            return ""

        # Remove query parameters
        base = url.split('?')[0]

        # Remove common CDN size variations (e.g., /460/ vs /1280/)
        import re
        base = re.sub(r'/\d{3,4}/', '/', base)

        return base.lower()


def deduplicate_search_results(
    results: list[dict],
    url_key: str = "image_url",
    use_embedding_dedup: bool = True,
    similarity_threshold: float = 0.95
) -> list[dict]:
    """
    Convenience function to deduplicate search results.

    Uses both URL-based and embedding-based deduplication.

    Args:
        results: Search results to deduplicate
        url_key: Key containing URL for URL-based dedup
        use_embedding_dedup: Whether to also use embedding similarity
        similarity_threshold: Similarity threshold for embedding dedup

    Returns:
        Deduplicated results
    """
    dedup = EmbeddingDedup(similarity_threshold=similarity_threshold)

    # First pass: URL-based deduplication (fast)
    results = dedup.deduplicate_by_url_similarity(results, url_key)

    # Second pass: Embedding-based deduplication (more thorough)
    if use_embedding_dedup:
        results = dedup.deduplicate_results(results)

    return results
