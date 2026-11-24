"""App settings, read from environment variables or the .env file."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database: Neon PostgreSQL via .env; SQLite fallback if DATABASE_URL is not set
    database_url: str = "sqlite:///./shopassist.db"

    # Auth
    jwt_secret: SecretStr = SecretStr("change-me-in-env")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    # LLM
    openai_api_key: SecretStr | None = None
    llm_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
