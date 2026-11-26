from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    AI_API_KEY: str | None = None
    AI_MODEL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
