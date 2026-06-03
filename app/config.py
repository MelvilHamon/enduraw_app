"""Application settings, loaded from the environment via pydantic-settings."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

DEV_JWT_SECRET = "changeme-dev-only"


class Settings(BaseSettings):
    """Runtime configuration for the API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: Literal["dev", "prod"] = "dev"

    DATABASE_URL: str = "sqlite:///./data/enduraw.db"

    JWT_SECRET: str = DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    ENGINE_MODE: Literal["mock", "live"] = "mock"
    COACHAGENT_BASE_URL: str | None = None
    COACHAGENT_API_KEY: str | None = None

    SEED_ON_START: bool = False

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        # Allow a plain comma-separated string in addition to a JSON array.
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _validate_secret(self) -> Settings:
        weak_secret = not self.JWT_SECRET or self.JWT_SECRET == DEV_JWT_SECRET
        if weak_secret:
            if self.ENV == "prod":
                raise ValueError(
                    "JWT_SECRET must be set to a strong, non-default value when ENV=prod."
                )
            logger.warning(
                "Using the default development JWT secret. "
                "Set JWT_SECRET before deploying to production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (override the cache in tests)."""

    return Settings()
