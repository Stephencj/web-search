"""Content deduplication using SimHash."""

from simhash import Simhash


class SimHashDedup:
    """Deduplication using SimHash for near-duplicate detection."""

    def __init__(self, threshold: int = 3):
        """
        Initialize deduplicator.

        Args:
            threshold: Hamming distance threshold for considering
                      documents as duplicates. Lower = stricter.
        """
        self.threshold = threshold
        self._hashes: dict[str, int] = {}  # url -> simhash value

    def compute_hash(self, content: str) -> str:
        """
        Compute SimHash for content.

        Returns hex string representation of the hash.
        """
        if not content:
            return "0" * 16

        # Compute simhash
        sh = Simhash(content)
        return format(sh.value, '016x')

    def is_duplicate(self, content: str, url: str) -> bool:
        """
        Check if content is a near-duplicate of already seen content.

        Args:
            content: Text content to check
            url: URL of the page (for caching)

        Returns:
            True if content is a duplicate
        """
        if not content:
            return False

        sh = Simhash(content)

        # Check against existing hashes
        for existing_url, existing_value in self._hashes.items():
            if existing_url == url:
                continue

            distance = self._hamming_distance(sh.value, existing_value)
            if distance <= self.threshold:
                return True

        # Not a duplicate - store this hash
        self._hashes[url] = sh.value
        return False

    def add_hash(self, url: str, content_hash: str) -> None:
        """Add a pre-computed hash to the cache."""
        try:
            self._hashes[url] = int(content_hash, 16)
        except ValueError:
            pass

    def _hamming_distance(self, a: int, b: int) -> int:
        """Calculate Hamming distance between two integers."""
        x = a ^ b
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance

    def clear(self) -> None:
        """Clear the hash cache."""
        self._hashes.clear()
