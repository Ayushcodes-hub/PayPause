"""Configuration management for PayPause independent backend modules."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PayPause Independent Backend (Bhuvan)"
    app_env: str = "development"
    debug: bool = True

    # Flagsmith Server-side configuration
    flagsmith_environment_key: Optional[str] = None
    flagsmith_api_url: str = "https://edge.api.flagsmith.com/api/v1/"
    flagsmith_request_timeout_seconds: float = 3.0

    # Development Authentication default credentials
    dev_default_user_id: str = "usr_dev_bhuvan_001"
    dev_default_user_email: str = "bhuvan.developer@paypause.local"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
