from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Shared configuration for all PayPause backend modules."""

    # Ayush: core application
    APP_NAME: str = "PayPause API"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    LOG_LEVEL: str = "INFO"

    # Ayush: Supabase
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # Ayush: AI provider
    AI_PROVIDER: Literal["groq"] = "groq"
    AI_API_KEY: str | None = None
    AI_REQUEST_TIMEOUT_SECONDS: float = 30.0
    AI_MODEL: str | None = None

    # Bhuvan: independent module application metadata
    app_env: str = "development"

    # Bhuvan: Flagsmith experimentation
    flagsmith_environment_key: str | None = None
    flagsmith_api_url: str = "https://edge.api.flagsmith.com/api/v1/"
    flagsmith_request_timeout_seconds: float = 3.0

    # Bhuvan: development-only fallback identity
    dev_default_user_id: str = "usr_dev_bhuvan_001"
    dev_default_user_email: str = "bhuvan.developer@paypause.local"


    @property
    def app_name(self) -> str:
        """Compatibility property for Bhuvan's development application."""
        return self.APP_NAME
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached shared application settings."""
    return Settings()


settings = get_settings()

