"""WebSearch API - Personal Search Engine Backend."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.api import api_router
from app.config import get_settings
from app.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting WebSearch API v0.1.0")
    logger.info(f"Data directory: {settings.data_dir}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start sync scheduler
    from app.services.sync_scheduler import get_sync_scheduler
    scheduler = get_sync_scheduler()
    await scheduler.start()

    yield

    # Shutdown scheduler
    await scheduler.shutdown()

    # Cleanup database
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="WebSearch API",
        description="Personal Search Engine Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware for Tauri frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tauri uses custom protocol
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": "0.1.0"
        }

    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Serve static frontend files in Docker/production mode
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        logger.info(f"Serving static files from: {static_dir}")

        # Mount static assets (JS, CSS, etc.)
        app.mount("/_app", StaticFiles(directory=static_dir / "_app"), name="svelte_app")

        # Serve favicon and other static files
        if (static_dir / "favicon.png").exists():
            @app.get("/favicon.png")
            async def favicon():
                return FileResponse(static_dir / "favicon.png")

        # SPA fallback - serve index.html for all non-API routes
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            # Don't intercept API routes
            if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
                return

            # Check if file exists in static dir
            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)

            # Fallback to index.html for SPA routing
            return FileResponse(static_dir / "index.html")

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
