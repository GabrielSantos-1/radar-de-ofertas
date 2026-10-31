from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, all overridable through environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./radar.db"
    link_timeout_ms: int = 5000
    page_size: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
