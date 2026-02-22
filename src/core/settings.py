from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# APP_ENV = os.getenv("ENVIRONMENT", "development")
# ENV_FILE = f".env.{APP_ENV}" if APP_ENV else ".env"


class Settings(BaseSettings):
    """Application settings."""

    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "10 days"
    LOG_COMPRESSION: str = "gz"

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    MODEL_PROVIDER: Literal["google", "groq"] = "groq"

    LANGSMITH_API_KEY: str = ""
    LANGSMITH_TRACING: bool = True
    LANGSMITH_PROJECT: str = "quizzer"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()  # type: ignore #
