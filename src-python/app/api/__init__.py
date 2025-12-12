"""API routes."""

from fastapi import APIRouter

from app.api import indexes, sources, search, crawl, settings, collections

api_router = APIRouter()

api_router.include_router(indexes.router, prefix="/indexes", tags=["indexes"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(crawl.router, prefix="/crawl", tags=["crawl"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
