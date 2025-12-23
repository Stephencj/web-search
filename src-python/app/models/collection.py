"""Collection models - for saving and organizing images/videos."""

import re
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text


class Collection(Base):
    """
    A collection of saved images and videos.

    Collections are per-user and can contain any saved media from search results.
    """
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User ownership
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Unique constraint per user (different users can have same collection name)
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uix_user_collection_name'),
        UniqueConstraint('user_id', 'slug', name='uix_user_collection_slug'),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to items
    items: Mapped[list["CollectionItem"]] = relationship(
        "CollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CollectionItem.sort_order"
    )

    @classmethod
    def create(cls, name: str, description: Optional[str] = None, **kwargs) -> "Collection":
        """Create a new collection with auto-generated slug."""
        return cls(
            name=name,
            slug=slugify(name),
            description=description,
            **kwargs
        )

    @property
    def item_count(self) -> int:
        """Get the number of items in this collection."""
        return len(self.items) if self.items else 0

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}', items={self.item_count})>"


class CollectionItem(Base):
    """
    An item (image or video) saved to a collection.

    Stores metadata about the saved media including URL, thumbnail,
    source page, and ordering information.
    """
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Item type: "image", "video", or "podcast_episode"
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Primary URL (image_url or video_url)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    # Thumbnail (for videos, or can store smaller version of image)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # page_url
    domain: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Video-specific fields
    embed_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Ordering within collection
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationship back to collection
    collection: Mapped["Collection"] = relationship(
        "Collection",
        back_populates="items"
    )

    def __repr__(self) -> str:
        return f"<CollectionItem(id={self.id}, type='{self.item_type}', collection_id={self.collection_id})>"
