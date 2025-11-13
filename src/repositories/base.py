"""
Base repository interface for job data access.

This module defines the abstract base class that all repository implementations
must follow. This ensures consistency and makes it easy to swap implementations
(e.g., for testing with an in-memory repository).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.models.enums import JobStatus, LogLevel


class BaseJobRepository(ABC):
    """
    Abstract base class for job repository implementations.

    This interface defines all operations needed to manage jobs and their logs.
    Concrete implementations (e.g., SupabaseJobRepository) must implement all methods.
    """

    @abstractmethod
    def create(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new job.

        Args:
            job_data: Dictionary containing job fields:
                - type (str): Job type identifier
                - payload (dict): Job-specific data
                - priority (int, optional): Job priority (default: 0)
                - max_retries (int, optional): Maximum retry attempts
                - scheduled_at (datetime, optional): When to run the job

        Returns:
            Dict containing the created job with all fields including generated ID

        Raises:
            ValueError: If required fields are missing or invalid
            Exception: If database operation fails
        """
        pass

    @abstractmethod
    def get_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a job by its ID.

        Args:
            job_id: UUID string of the job

        Returns:
            Job dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve pending jobs ready for processing.

        This method should:
        1. Filter for jobs with status='pending'
        2. Check that scheduled_at <= now (or is null)
        3. Order by priority DESC, created_at ASC
        4. Use row-level locking (FOR UPDATE SKIP LOCKED) to prevent race conditions

        Args:
            limit: Maximum number of jobs to retrieve

        Returns:
            List of job dictionaries, locked for processing
        """
        pass

    @abstractmethod
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Update a job's status and related fields.

        Args:
            job_id: UUID string of the job
            status: New job status
            error_message: Error message if status is FAILED
            completed_at: Completion timestamp (for COMPLETED/FAILED status)
            started_at: Start timestamp (for RUNNING status)

        Returns:
            Updated job dictionary

        Raises:
            ValueError: If job not found or invalid status transition
        """
        pass

    @abstractmethod
    def increment_retry_count(self, job_id: str) -> Dict[str, Any]:
        """
        Increment the retry count for a job.

        Args:
            job_id: UUID string of the job

        Returns:
            Updated job dictionary

        Raises:
            ValueError: If job not found
        """
        pass

    @abstractmethod
    def add_log(
        self,
        job_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO
    ) -> Dict[str, Any]:
        """
        Add a log entry for a job.

        Args:
            job_id: UUID string of the job
            message: Log message
            level: Log level (info, warning, error, debug)

        Returns:
            Created log entry dictionary

        Raises:
            ValueError: If job not found
        """
        pass

    @abstractmethod
    def get_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all logs for a job.

        Args:
            job_id: UUID string of the job

        Returns:
            List of log dictionaries ordered by created_at ASC
        """
        pass

    @abstractmethod
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List jobs with optional filtering.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)

        Returns:
            List of job dictionaries ordered by created_at DESC
        """
        pass

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """
        Delete a job and its associated logs.

        Args:
            job_id: UUID string of the job

        Returns:
            True if job was deleted, False if not found
        """
        pass

    @abstractmethod
    def get_failed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve jobs that have failed and exhausted retries.

        This is useful for implementing a Dead Letter Queue (DLQ).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of failed job dictionaries
        """
        pass

    @abstractmethod
    def reset_job_for_retry(self, job_id: str, scheduled_at: datetime) -> Dict[str, Any]:
        """
        Reset a failed job to pending status for retry.

        Args:
            job_id: UUID string of the job
            scheduled_at: When to retry the job

        Returns:
            Updated job dictionary

        Raises:
            ValueError: If job not found or not in FAILED status
        """
        pass
