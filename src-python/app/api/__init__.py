"""API routes."""

from fastapi import APIRouter

from app.api import indexes, sources, search, crawl, settings, collections, channels, feed, discover, saved_videos, playlists, accounts, stream, auth, users, hidden_channels

api_router = APIRouter()

api_router.include_router(indexes.router, prefix="/indexes", tags=["indexes"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(crawl.router, prefix="/crawl", tags=["crawl"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(feed.router, prefix="/feed", tags=["feed"])
api_router.include_router(discover.router, prefix="/discover", tags=["discover"])
api_router.include_router(saved_videos.router, prefix="/saved-videos", tags=["saved-videos"])
api_router.include_router(playlists.router, prefix="/playlists", tags=["playlists"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(hidden_channels.router)
