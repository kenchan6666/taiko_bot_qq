"""
Configuration management module.

This module handles loading and validation of environment variables
for the Mika Taiko Chatbot application. All API keys and sensitive
credentials MUST be loaded from environment variables via os.getenv().
Configuration files MUST contain placeholder values only.

Per NFR-009: All API keys MUST be loaded from environment variables
via config.py using os.getenv(). Configuration files MUST contain
placeholder values only (leave API keys empty/blank), with actual
secrets provided via environment variables.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All sensitive values (API keys, connection strings) are loaded
    from environment variables. Default values are placeholders only.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017/"
    mongodb_database: str = "mika_bot"

    # Temporal Configuration
    temporal_host: str = "localhost"
    temporal_port: int = 7233
    temporal_namespace: str = "default"

    # OpenRouter API Configuration
    # Per NFR-009: API keys MUST be loaded from environment variables
    # Leave empty in .env.example, provide actual key via environment variable
    openrouter_api_key: Optional[str] = None

    # LangBot Configuration
    langbot_webhook_url: str = "http://localhost:8000/webhook/langbot"
    langbot_allowed_groups: str = ""  # Comma-separated list of group IDs

    # Application Configuration
    bot_name: str = "Mika"
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Rate Limiting Configuration
    # Per FR-012: 20 requests per user per minute, 50 requests per group per minute
    rate_limit_user_per_minute: int = 20
    rate_limit_group_per_minute: int = 50

    # Content Filtering Configuration
    content_filter_enabled: bool = True

    # Language Detection Configuration
    # Per NFR-008: Default language if detection fails
    default_language: str = "zh"  # zh or en

    # Taiko.wiki API Configuration
    # Per FR-002: Song data source URL (PRIMARY data source)
    # Options:
    # - https://taiko.wiki/api/v1/song/all (official API - PRIMARY)
    # - https://raw.githubusercontent.com/taikowiki/taiko-song-database/main/database.json (static JSON)
    # - file:///path/to/local/database.json (local file)
    taikowiki_json_url: str = "https://taiko.wiki/api/v1/song/all"
    
    # Local JSON fallback file path (used ONLY when API unavailable)
    taikowiki_local_json_path: str = "data/database.json"

    # Conversation History Limit Configuration
    # Per FR-005: Configurable limit via environment variable
    conversation_history_limit: int = 10  # Default: 10 conversations

    # Message Deduplication Configuration
    # Per FR-008 Enhancement: Configurable similarity threshold and deduplication window
    message_deduplication_enabled: bool = True
    message_deduplication_similarity_threshold: float = 0.85  # 0.0-1.0, higher = more strict
    message_deduplication_window_seconds: int = 5  # Time window for deduplication

    # Image Processing Configuration
    # Per FR-006: Image processing limits (10MB max, JPEG/PNG/WebP only)
    image_max_size_mb: int = 10  # Maximum image size in MB
    image_allowed_formats: list[str] = ["jpeg", "jpg", "png", "webp"]  # Allowed image formats

    def get_langbot_allowed_groups_list(self) -> list[str]:
        """
        Parse comma-separated allowed groups string into a list.

        Returns:
            List of allowed group IDs as strings. Empty list if none configured.
        """
        if not self.langbot_allowed_groups:
            return []
        return [
            group_id.strip()
            for group_id in self.langbot_allowed_groups.split(",")
            if group_id.strip()
        ]

    def validate_openrouter_api_key(self) -> None:
        """
        Validate that OpenRouter API key is provided.

        Raises:
            ValueError: If API key is not set (None or empty string).
        """
        if not self.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )


# Global settings instance (lazy-loaded to avoid Temporal workflow sandbox restrictions)
# Settings are loaded on first access, not at module import time
_settings_instance: Optional[Settings] = None


def _get_settings() -> Settings:
    """
    Get or create the global settings instance.

    This function uses lazy loading to avoid initializing Settings()
    at module import time, which would trigger file system access
    (Path.expanduser) that is not allowed in Temporal workflow sandbox.

    Returns:
        Settings instance (created on first call).
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# Property-like access to settings
# This allows code to use `settings.xxx` as before, but initialization
# is delayed until first access
class _SettingsProxy:
    """
    Proxy class for lazy-loaded settings.

    This allows code to access settings attributes normally (e.g., `settings.mongodb_url`),
    but initialization is delayed until first attribute access, avoiding Temporal
    workflow sandbox restrictions during module import.
    """

    def __getattr__(self, name: str):
        """Get attribute from settings instance."""
        return getattr(_get_settings(), name)


# Global settings proxy instance
# Use this instead of direct Settings() instance
settings = _SettingsProxy()


def get_bot_name() -> str:
    """
    Get the bot's name from configuration.

    Returns:
        Bot name string (default: "Mika").
    """
    return settings.bot_name
