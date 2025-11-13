"""
Pytest configuration and shared fixtures.

This file provides common fixtures and configuration for all tests.
"""

import pytest
from src.database.connection import get_supabase_client
from src.repositories.job_repository import SupabaseJobRepository


@pytest.fixture(scope="session")
def supabase_client():
    """
    Session-scoped fixture for Supabase client.

    Provides a single Supabase client instance for the entire test session.
    """
    return get_supabase_client()


@pytest.fixture(scope="function")
def job_repository():
    """
    Function-scoped fixture for job repository.

    Provides a fresh repository instance for each test.
    """
    return SupabaseJobRepository()


def pytest_configure(config):
    """
    Pytest configuration hook.

    Register custom markers for test categorization.
    """
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require external services)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )