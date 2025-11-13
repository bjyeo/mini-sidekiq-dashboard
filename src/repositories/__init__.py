"""
Repository layer for data access.

This module exposes the repository interfaces and implementations
for accessing job data.
"""

from src.repositories.base import BaseJobRepository
from src.repositories.job_repository import SupabaseJobRepository

__all__ = [
    "BaseJobRepository",
    "SupabaseJobRepository",
]
