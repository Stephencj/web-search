"""Settings service - manages application settings with priority handling."""

import os
from typing import Any, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, CrawlerSettings
from app.models import AppSetting


# Map of setting keys to environment variable names
CRAWLER_ENV_VARS = {
    "concurrent_requests": "WEBSEARCH_CRAWLER__CONCURRENT_REQUESTS",
    "request_delay_ms": "WEBSEARCH_CRAWLER__REQUEST_DELAY_MS",
    "timeout_seconds": "WEBSEARCH_CRAWLER__TIMEOUT_SECONDS",
    "max_retries": "WEBSEARCH_CRAWLER__MAX_RETRIES",
    "respect_robots_txt": "WEBSEARCH_CRAWLER__RESPECT_ROBOTS_TXT",
    "max_pages_per_source": "WEBSEARCH_CRAWLER__MAX_PAGES_PER_SOURCE",
    "max_page_size_mb": "WEBSEARCH_CRAWLER__MAX_PAGE_SIZE_MB",
    "user_agent": "WEBSEARCH_CRAWLER__USER_AGENT",
    "raw_html_enabled": "WEBSEARCH_CRAWLER__RAW_HTML_ENABLED",
    "image_embeddings_enabled": "WEBSEARCH_CRAWLER__IMAGE_EMBEDDINGS_ENABLED",
    "youtube_fetch_transcripts": "WEBSEARCH_CRAWLER__YOUTUBE_FETCH_TRANSCRIPTS",
    "youtube_max_videos_per_source": "WEBSEARCH_CRAWLER__YOUTUBE_MAX_VIDEOS_PER_SOURCE",
    "youtube_rate_limit_delay_ms": "WEBSEARCH_CRAWLER__YOUTUBE_RATE_LIMIT_DELAY_MS",
}

# Settings that can be edited in the UI (subset of crawler settings)
EDITABLE_CRAWLER_SETTINGS = [
    "concurrent_requests",
    "request_delay_ms",
    "timeout_seconds",
    "max_retries",
    "respect_robots_txt",
    "max_pages_per_source",
    "user_agent",
]


class SettingsService:
    """Service for managing application settings."""

    def is_env_override(self, key: str) -> bool:
        """Check if a crawler setting is overridden by an environment variable."""
        env_var = CRAWLER_ENV_VARS.get(key)
        if not env_var:
            return False
        return env_var in os.environ

    async def get_setting(self, db: AsyncSession, key: str) -> Optional[Any]:
        """Get a setting value from the database."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return None

    async def set_setting(self, db: AsyncSession, key: str, value: Any) -> AppSetting:
        """Set a setting value in the database."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
        else:
            setting = AppSetting(key=key, value=value)
            db.add(setting)

        await db.commit()
        await db.refresh(setting)
        logger.info(f"Setting updated: {key}")
        return setting

    async def delete_setting(self, db: AsyncSession, key: str) -> bool:
        """Delete a setting from the database."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()

        if not setting:
            return False

        await db.delete(setting)
        await db.commit()
        logger.info(f"Setting deleted: {key}")
        return True

    async def get_crawler_settings(self, db: AsyncSession) -> dict:
        """
        Get crawler settings with source information.

        Priority: Environment > Database > Default

        Returns dict with structure:
        {
            "setting_name": {
                "value": <actual value>,
                "source": "env" | "db" | "default",
                "editable": bool
            }
        }
        """
        # Get default settings from config
        defaults = CrawlerSettings()
        config_settings = get_settings()

        # Get database overrides
        db_settings = await self.get_setting(db, "crawler") or {}

        result = {}

        for field_name in defaults.model_fields.keys():
            default_value = getattr(defaults, field_name)
            config_value = getattr(config_settings.crawler, field_name)
            db_value = db_settings.get(field_name)
            is_env_override = self.is_env_override(field_name)
            is_editable = field_name in EDITABLE_CRAWLER_SETTINGS

            # Determine source and value
            if is_env_override:
                # Environment variable is set - use config value (which includes env)
                value = config_value
                source = "env"
            elif db_value is not None:
                # Database has a value
                value = db_value
                source = "db"
            else:
                # Use default
                value = default_value
                source = "default"

            result[field_name] = {
                "value": value,
                "source": source,
                "editable": is_editable and not is_env_override,
            }

        return result

    async def update_crawler_settings(
        self,
        db: AsyncSession,
        updates: dict[str, Any]
    ) -> dict:
        """
        Update crawler settings in the database.

        Only updates settings that are editable (not env-overridden).

        Args:
            db: Database session
            updates: Dict of setting names to new values

        Returns:
            Updated crawler settings with source info

        Raises:
            ValueError: If trying to update an env-overridden setting
        """
        # Get current db settings
        current_db_settings = await self.get_setting(db, "crawler") or {}

        # Validate and apply updates
        for key, value in updates.items():
            if key not in EDITABLE_CRAWLER_SETTINGS:
                logger.warning(f"Ignoring non-editable setting: {key}")
                continue

            if self.is_env_override(key):
                raise ValueError(
                    f"Cannot update '{key}' - it is overridden by environment variable"
                )

            # Validate value type based on default
            defaults = CrawlerSettings()
            if hasattr(defaults, key):
                default_value = getattr(defaults, key)
                expected_type = type(default_value)

                # Type coercion for common cases
                if expected_type == bool and isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                elif expected_type == int and isinstance(value, (str, float)):
                    value = int(value)
                elif expected_type == str and not isinstance(value, str):
                    value = str(value)

                current_db_settings[key] = value
            else:
                logger.warning(f"Unknown crawler setting: {key}")

        # Save to database
        await self.set_setting(db, "crawler", current_db_settings)
        logger.info(f"Crawler settings updated: {list(updates.keys())}")

        # Return updated settings with source info
        return await self.get_crawler_settings(db)

    async def reset_crawler_setting(
        self,
        db: AsyncSession,
        key: str
    ) -> dict:
        """
        Reset a crawler setting to its default value.

        Removes the setting from the database, allowing the default to take effect.
        """
        if self.is_env_override(key):
            raise ValueError(
                f"Cannot reset '{key}' - it is overridden by environment variable"
            )

        current_db_settings = await self.get_setting(db, "crawler") or {}

        if key in current_db_settings:
            del current_db_settings[key]
            await self.set_setting(db, "crawler", current_db_settings)
            logger.info(f"Crawler setting reset to default: {key}")

        return await self.get_crawler_settings(db)

    async def get_all_settings(self, db: AsyncSession) -> dict:
        """Get all application settings."""
        result = await db.execute(select(AppSetting))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}


# Global service instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get the settings service singleton."""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
