"""Database configuration and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Engine and session factory (lazy initialization)
_engine = None
_async_session_factory = None


def get_engine():
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.sqlite_url,
            echo=settings.debug,
            future=True
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
    return _async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize the database, creating all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Run migrations for new columns
        await _run_migrations(conn)


async def _run_migrations(conn) -> None:
    """Run database migrations for schema updates."""
    from sqlalchemy import text

    # Add crawl_mode column to sources table if it doesn't exist
    try:
        await conn.execute(text(
            "ALTER TABLE sources ADD COLUMN crawl_mode VARCHAR(20) DEFAULT 'all'"
        ))
    except Exception:
        # Column already exists
        pass

    # Add use_tor column to sources table if it doesn't exist
    try:
        await conn.execute(text(
            "ALTER TABLE sources ADD COLUMN use_tor BOOLEAN DEFAULT 0"
        ))
    except Exception:
        # Column already exists
        pass


async def close_db() -> None:
    """Close database connections."""
    global _engine, _async_session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
