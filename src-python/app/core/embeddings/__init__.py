"""Embedding services for semantic search."""

from app.core.embeddings.clip_embeddings import CLIPEmbeddings, get_clip_embeddings

__all__ = ["CLIPEmbeddings", "get_clip_embeddings"]
