"""Supabase database connection management"""

from supabase import create_client, Client
from functools import lru_cache
from src.config.settings import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get Supabase client instance (singleton pattern).

    Returns:
        Client: Configured Supabase client

    Raises:
        ValueError: If required environment variables are missing
    """
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError(
            "Missing required Supabase configuration. "
            "Ensure SUPABASE_URL and SUPABASE_KEY are set in .env"
        )

    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key
    )


def get_db() -> Client:
    """
    Dependency function for FastAPI to inject Supabase client.

    Usage in FastAPI:
        @app.get("/jobs")
        def get_jobs(db: Client = Depends(get_db)):
            ...
    """
    return get_supabase_client()
