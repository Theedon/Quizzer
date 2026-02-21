import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ENV = os.getenv("ENVIRONMENT", "development")
ENV_FILE = f".env.{APP_ENV}" if APP_ENV else ".env"


class Settings(BaseSettings):
    """Application settings."""

    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "10 days"
    LOG_COMPRESSION: str = "gz"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
