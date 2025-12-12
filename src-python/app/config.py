"""Application configuration management."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class CrawlerSettings(BaseSettings):
    """Crawler-specific settings."""
    user_agent: str = "WebSearch/1.0 (Personal Search Engine)"
    concurrent_requests: int = 5
    request_delay_ms: int = 1000
    timeout_seconds: int = 30
    max_retries: int = 3
    respect_robots_txt: bool = True
    max_pages_per_source: int = 10000
    max_page_size_mb: int = 10
    raw_html_enabled: bool = True
    # Image embeddings - generates CLIP vectors for semantic image search
    # Requires ~2GB RAM when model is loaded
    image_embeddings_enabled: bool = True

    # YouTube/yt-dlp settings
    youtube_fetch_transcripts: bool = True
    youtube_transcript_languages: list[str] = ["en", "en-US", "en-GB"]
    youtube_max_videos_per_source: int = 500
    youtube_rate_limit_delay_ms: int = 2000


class MeilisearchSettings(BaseSettings):
    """Meilisearch connection settings."""
    host: str = "http://127.0.0.1:7700"
    api_key: str = "TBmZdGLVexFLTf6Pl1_JZoQt1e07aBt6z-vIF4ldTF8"
    index_prefix: str = "websearch_"


class SyncSettings(BaseSettings):
    """Video feed sync settings."""
    sync_enabled: bool = True
    default_sync_frequency: str = "hourly"  # "hourly", "twice_daily", "daily"
    max_videos_per_sync: int = 50
    max_consecutive_errors: int = 5  # Auto-disable channel after this many failures


class Settings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(
        env_prefix="WEBSEARCH_",
        env_nested_delimiter="__",
        extra="ignore"
    )

    # Application info
    app_name: str = "WebSearch"
    debug: bool = False

    # Paths
    app_dir: Path = Field(default_factory=lambda: Path.home() / ".websearch")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".websearch" / "data")

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    # Database
    database_url: Optional[str] = None

    # Sub-settings
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    meilisearch: MeilisearchSettings = Field(default_factory=MeilisearchSettings)
    sync: SyncSettings = Field(default_factory=SyncSettings)

    @property
    def sqlite_url(self) -> str:
        """Get SQLite database URL."""
        if self.database_url:
            return self.database_url
        db_path = self.data_dir / "websearch.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def sync_sqlite_url(self) -> str:
        """Get synchronous SQLite URL for Alembic."""
        db_path = self.data_dir / "websearch.db"
        return f"sqlite:///{db_path}"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "raw_html").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
