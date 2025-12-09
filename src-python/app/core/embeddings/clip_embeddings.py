"""CLIP-based image and text embeddings for semantic search."""

import asyncio
from io import BytesIO
from typing import Optional
from pathlib import Path

import httpx
from loguru import logger

from app.config import get_settings

# Lazy imports for optional dependencies
_model = None
_processor = None


def _load_model():
    """Lazy load the CLIP model."""
    global _model, _processor

    if _model is not None:
        return _model, _processor

    try:
        from sentence_transformers import SentenceTransformer

        # Use a small but effective CLIP model
        # clip-ViT-B-32 is ~600MB, good balance of speed/quality
        model_name = "clip-ViT-B-32"

        logger.info(f"Loading CLIP model: {model_name}")
        _model = SentenceTransformer(model_name)
        logger.info("CLIP model loaded successfully")

        return _model, None

    except ImportError:
        logger.warning("sentence-transformers not installed. Image embeddings disabled.")
        return None, None
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}")
        return None, None


class CLIPEmbeddings:
    """Generate CLIP embeddings for images and text."""

    def __init__(self):
        self.settings = get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._model_loaded = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for downloading images."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": self.settings.crawler.user_agent}
            )
        return self._http_client

    def _ensure_model(self):
        """Ensure model is loaded."""
        if not self._model_loaded:
            _load_model()
            self._model_loaded = True

    def is_available(self) -> bool:
        """Check if CLIP embeddings are available."""
        self._ensure_model()
        return _model is not None

    def encode_text(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding for text.

        Args:
            text: Text to encode

        Returns:
            Embedding vector as list of floats, or None if unavailable
        """
        self._ensure_model()

        if _model is None:
            return None

        try:
            embedding = _model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Failed to encode text: {e}")
            return None

    async def encode_image_url(self, url: str) -> Optional[list[float]]:
        """
        Download and encode an image from URL.

        Args:
            url: URL of image to encode

        Returns:
            Embedding vector as list of floats, or None if unavailable
        """
        self._ensure_model()

        if _model is None:
            return None

        try:
            from PIL import Image

            # Download image
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code != 200:
                return None

            # Check content type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                return None

            # Load image
            image = Image.open(BytesIO(response.content))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Encode image
            embedding = _model.encode(image, convert_to_numpy=True)
            return embedding.tolist()

        except Exception as e:
            logger.warning(f"Failed to encode image {url}: {e}")
            return None

    def encode_image_file(self, path: str) -> Optional[list[float]]:
        """
        Encode an image from local file.

        Args:
            path: Path to image file

        Returns:
            Embedding vector as list of floats, or None if unavailable
        """
        self._ensure_model()

        if _model is None:
            return None

        try:
            from PIL import Image

            image = Image.open(path)

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            embedding = _model.encode(image, convert_to_numpy=True)
            return embedding.tolist()

        except Exception as e:
            logger.warning(f"Failed to encode image file {path}: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_clip_embeddings: Optional[CLIPEmbeddings] = None


def get_clip_embeddings() -> CLIPEmbeddings:
    """Get CLIP embeddings singleton."""
    global _clip_embeddings
    if _clip_embeddings is None:
        _clip_embeddings = CLIPEmbeddings()
    return _clip_embeddings
