"""Centralized application configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_db_password: str

    # Worker Configuration
    worker_poll_interval: int = 5
    worker_batch_size: int = 10
    worker_concurrency: int = 4

    # Job Configuration
    default_max_retries: int = 3
    job_timeout: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
