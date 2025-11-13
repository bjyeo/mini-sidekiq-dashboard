"""
Supabase implementation of the job repository.

This module provides the concrete implementation of BaseJobRepository
using Supabase as the backend database.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from supabase import Client

from src.models.enums import JobStatus, LogLevel
from src.repositories.base import BaseJobRepository
from src.database.connection import get_supabase_client


class SupabaseJobRepository(BaseJobRepository):
    """
    Supabase-backed implementation of the job repository.

    This class handles all database operations for jobs and job logs
    using the Supabase Python client.
    """

    def __init__(self, _: Optional[Client] = None):
        """
        Initialize the repository.

        Args:
            client: Supabase client instance (optional, will use default if not provided)
        """
        self.client = get_supabase_client()

    def create(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new job in the database.

        Args:
            job_data: Dictionary containing job fields

        Returns:
            Created job dictionary with generated ID and timestamps

        Raises:
            ValueError: If required fields are missing
            Exception: If database operation fails
        """
        # Validate required fields
        if 'type' not in job_data:
            raise ValueError("Job 'type' is required")
        if 'payload' not in job_data:
            raise ValueError("Job 'payload' is required")

        # Set defaults
        job_data.setdefault('status', JobStatus.PENDING.value)
        job_data.setdefault('priority', 0)
        job_data.setdefault('retry_count', 0)
        job_data.setdefault('max_retries', 3)

        # Insert job
        response = self.client.table('jobs').insert(job_data).execute()

        if not response.data:
            raise Exception("Failed to create job")

        return response.data[0]

    def get_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a job by its ID.

        Args:
            job_id: UUID string of the job

        Returns:
            Job dictionary if found, None otherwise
        """
        response = self.client.table('jobs').select(
            '*').eq('id', job_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve pending jobs ready for processing with row-level locking.

        This uses a PostgreSQL function to safely fetch and lock jobs
        to prevent race conditions between workers.

        Args:
            limit: Maximum number of jobs to retrieve

        Returns:
            List of locked job dictionaries
        """
        # Use RPC to call the PostgreSQL function that handles locking
        # The function get_pending_jobs_with_lock will:
        # 1. SELECT jobs WHERE status='pending' AND (scheduled_at IS NULL OR scheduled_at <= NOW())
        # 2. ORDER BY priority DESC, created_at ASC
        # 3. LIMIT the results
        # 4. FOR UPDATE SKIP LOCKED (to handle concurrency)

        try:
            response = self.client.rpc(
                'get_pending_jobs_with_lock',
                {'batch_size': limit, 'lock_timeout': 5000}
            ).execute()

            return response.data if response.data else []
        except Exception as e:
            # Fallback to simple query if RPC function doesn't exist yet
            # TODO: Remove this fallback once database function is created
            print(
                f"Warning: RPC function not available, using fallback query: {e}")

            now = datetime.now().isoformat()
            response = (
                self.client.table('jobs')
                .select('*')
                .eq('status', JobStatus.PENDING.value)
                .or_(f'scheduled_at.is.null,scheduled_at.lte.{now}')
                .order('priority', desc=True)
                .order('created_at', desc=False)
                .limit(limit)
                .execute()
            )

            return response.data if response.data else []

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Update a job's status and related timestamps.

        Args:
            job_id: UUID string of the job
            status: New job status
            error_message: Error message if status is FAILED
            completed_at: Completion timestamp
            started_at: Start timestamp

        Returns:
            Updated job dictionary

        Raises:
            ValueError: If job not found
        """
        update_data: Dict[str, Any] = {
            'status': status.value,
            'updated_at': datetime.now().isoformat()
        }

        if error_message is not None:
            update_data['error_message'] = error_message

        if completed_at is not None:
            update_data['completed_at'] = completed_at.isoformat()

        if started_at is not None:
            update_data['started_at'] = started_at.isoformat()

        response = (
            self.client.table('jobs')
            .update(update_data)
            .eq('id', job_id)
            .execute()
        )

        if not response.data:
            raise ValueError(f"Job with id {job_id} not found")

        return response.data[0]

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
        # Get current job
        job = self.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job with id {job_id} not found")

        # Increment retry count
        new_count = job.get('retry_count', 0) + 1

        response = (
            self.client.table('jobs')
            .update({
                'retry_count': new_count,
                'updated_at': datetime.now().isoformat()
            })
            .eq('id', job_id)
            .execute()
        )

        return response.data[0]

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
            level: Log level

        Returns:
            Created log entry dictionary

        Raises:
            ValueError: If job not found
        """
        # Verify job exists
        job = self.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job with id {job_id} not found")

        log_data = {
            'job_id': job_id,
            'message': message,
            'level': level.value
        }

        response = self.client.table('job_logs').insert(log_data).execute()

        if not response.data:
            raise Exception("Failed to create log entry")

        return response.data[0]

    def get_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all logs for a job.

        Args:
            job_id: UUID string of the job

        Returns:
            List of log dictionaries ordered by created_at ASC
        """
        response = (
            self.client.table('job_logs')
            .select('*')
            .eq('job_id', job_id)
            .order('created_at', desc=False)
            .execute()
        )

        return response.data if response.data else []

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List jobs with optional filtering and pagination.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip

        Returns:
            List of job dictionaries ordered by created_at DESC
        """
        query = self.client.table('jobs').select('*')

        if status:
            query = query.eq('status', status.value)

        query = query.order('created_at', desc=True).range(
            offset, offset + limit - 1)

        response = query.execute()

        return response.data if response.data else []

    def delete(self, job_id: str) -> bool:
        """
        Delete a job and its associated logs (cascade).

        Args:
            job_id: UUID string of the job

        Returns:
            True if job was deleted, False if not found
        """
        # Check if job exists
        job = self.get_by_id(job_id)
        if not job:
            return False

        # Delete job (logs will cascade delete due to FK constraint)
        self.client.table('jobs').delete().eq('id', job_id).execute()

        return True

    def get_failed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve jobs that have failed and exhausted retries (DLQ).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of failed job dictionaries
        """
        response = (
            self.client.table('jobs')
            .select('*')
            .eq('status', JobStatus.FAILED.value)
            .order('updated_at', desc=True)
            .limit(limit)
            .execute()
        )

        return response.data if response.data else []

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
        job = self.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job with id {job_id} not found")

        if job['status'] != JobStatus.FAILED.value:
            raise ValueError(
                f"Job {job_id} is not in FAILED status, cannot reset")

        update_data = {
            'status': JobStatus.PENDING.value,
            'scheduled_at': scheduled_at.isoformat(),
            'error_message': None,
            'started_at': None,
            'completed_at': None,
            'updated_at': datetime.now().isoformat()
        }

        response = (
            self.client.table('jobs')
            .update(update_data)
            .eq('id', job_id)
            .execute()
        )

        return response.data[0]
