"""Shared API dependencies."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session


# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_session)]
