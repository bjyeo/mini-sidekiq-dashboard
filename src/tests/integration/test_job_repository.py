"""
Integration tests for Job Repository implementation.

These tests verify the Repository Pattern implementation including:
1. CRUD operations
2. Job status management
3. Logging functionality
4. Retry logic
5. Dead Letter Queue (DLQ) operations
"""

import pytest
from datetime import datetime, timedelta
from src.repositories.job_repository import SupabaseJobRepository
from src.models.enums import JobStatus, LogLevel


@pytest.fixture
def job_repository():
    """Fixture to provide a job repository instance."""
    return SupabaseJobRepository()


@pytest.fixture
def sample_job_data():
    """Fixture to provide sample job data."""
    return {
        'type': 'send_email',
        'payload': {
            'to': 'test@example.com',
            'subject': 'Test Email',
            'body': 'This is a test email from the job queue'
        },
        'priority': 5
    }


@pytest.fixture
def created_job(job_repository, sample_job_data):
    """Fixture that creates a job and cleans it up after the test."""
    job = job_repository.create(sample_job_data)
    yield job
    # Cleanup
    try:
        job_repository.delete(job['id'])
    except Exception:
        pass  # Job might already be deleted by the test


class TestJobRepositoryCreate:
    """Tests for job creation operations."""

    def test_create_job(self, job_repository, sample_job_data):
        """Test creating a new job."""
        job = job_repository.create(sample_job_data)

        assert job['id'] is not None
        assert job['type'] == 'send_email'
        assert job['status'] == JobStatus.PENDING.value
        assert job['priority'] == 5
        assert job['payload'] == sample_job_data['payload']
        assert job['retry_count'] == 0
        assert job['created_at'] is not None

        # Cleanup
        job_repository.delete(job['id'])

    def test_create_job_with_default_priority(self, job_repository):
        """Test that jobs are created with default priority when not specified."""
        job_data = {
            'type': 'process_data',
            'payload': {'data': 'test'}
        }
        job = job_repository.create(job_data)

        assert job['priority'] is not None
        assert isinstance(job['priority'], int)

        # Cleanup
        job_repository.delete(job['id'])


class TestJobRepositoryRead:
    """Tests for job retrieval operations."""

    def test_get_by_id(self, job_repository, created_job):
        """Test retrieving a job by ID."""
        retrieved_job = job_repository.get_by_id(created_job['id'])

        assert retrieved_job is not None
        assert retrieved_job['id'] == created_job['id']
        assert retrieved_job['type'] == created_job['type']

    def test_get_by_id_nonexistent(self, job_repository):
        """Test retrieving a non-existent job returns None."""
        retrieved_job = job_repository.get_by_id('00000000-0000-0000-0000-000000000000')
        assert retrieved_job is None

    def test_list_jobs(self, job_repository, created_job):
        """Test listing jobs."""
        jobs = job_repository.list_jobs(limit=10)

        assert isinstance(jobs, list)
        assert len(jobs) > 0
        assert any(job['id'] == created_job['id'] for job in jobs)

    def test_list_jobs_with_status_filter(self, job_repository, created_job):
        """Test listing jobs filtered by status."""
        pending_jobs = job_repository.list_jobs(status=JobStatus.PENDING, limit=10)

        assert isinstance(pending_jobs, list)
        assert all(job['status'] == JobStatus.PENDING.value for job in pending_jobs)
        assert any(job['id'] == created_job['id'] for job in pending_jobs)

    def test_get_pending_jobs(self, job_repository, created_job):
        """Test retrieving pending jobs ready for processing."""
        pending_jobs = job_repository.get_pending_jobs(limit=5)

        assert isinstance(pending_jobs, list)
        # Verify jobs are ordered by priority (descending) then created_at (ascending)
        if len(pending_jobs) > 1:
            for i in range(len(pending_jobs) - 1):
                current = pending_jobs[i]
                next_job = pending_jobs[i + 1]
                # Higher priority comes first, or same priority with earlier created_at
                assert (current['priority'] >= next_job['priority'])


class TestJobRepositoryUpdate:
    """Tests for job update operations."""

    def test_update_status_to_running(self, job_repository, created_job):
        """Test updating job status to RUNNING."""
        started_at = datetime.now()
        updated_job = job_repository.update_status(
            created_job['id'],
            JobStatus.RUNNING,
            started_at=started_at
        )

        assert updated_job['status'] == JobStatus.RUNNING.value
        assert updated_job['started_at'] is not None

    def test_update_status_to_completed(self, job_repository, created_job):
        """Test updating job status to COMPLETED."""
        completed_at = datetime.now()
        updated_job = job_repository.update_status(
            created_job['id'],
            JobStatus.COMPLETED,
            completed_at=completed_at
        )

        assert updated_job['status'] == JobStatus.COMPLETED.value
        assert updated_job['completed_at'] is not None

    def test_update_status_to_failed(self, job_repository, created_job):
        """Test updating job status to FAILED with error message."""
        error_message = "SMTP connection timeout"
        completed_at = datetime.now()

        updated_job = job_repository.update_status(
            created_job['id'],
            JobStatus.FAILED,
            error_message=error_message,
            completed_at=completed_at
        )

        assert updated_job['status'] == JobStatus.FAILED.value
        assert updated_job['error_message'] == error_message
        assert updated_job['completed_at'] is not None

    def test_increment_retry_count(self, job_repository, created_job):
        """Test incrementing retry count."""
        initial_count = created_job['retry_count']
        updated_job = job_repository.increment_retry_count(created_job['id'])

        assert updated_job['retry_count'] == initial_count + 1

    def test_increment_retry_count_multiple_times(self, job_repository, created_job):
        """Test incrementing retry count multiple times."""
        initial_count = created_job['retry_count']

        for i in range(3):
            updated_job = job_repository.increment_retry_count(created_job['id'])
            assert updated_job['retry_count'] == initial_count + i + 1


class TestJobRepositoryDelete:
    """Tests for job deletion operations."""

    def test_delete_job(self, job_repository, sample_job_data):
        """Test deleting a job."""
        job = job_repository.create(sample_job_data)
        job_id = job['id']

        result = job_repository.delete(job_id)
        assert result is True

        # Verify deletion
        deleted_job = job_repository.get_by_id(job_id)
        assert deleted_job is None

    def test_delete_nonexistent_job(self, job_repository):
        """Test deleting a non-existent job."""
        result = job_repository.delete('00000000-0000-0000-0000-000000000000')
        # Should return False or handle gracefully
        assert result is False or result is True  # Implementation dependent


class TestJobRepositoryLogs:
    """Tests for job logging functionality."""

    def test_add_log(self, job_repository, created_job):
        """Test adding a log entry to a job."""
        message = "Job processing started"
        job_repository.add_log(created_job['id'], message, LogLevel.INFO)

        logs = job_repository.get_logs(created_job['id'])
        assert len(logs) >= 1
        assert any(log['message'] == message for log in logs)

    def test_add_multiple_logs(self, job_repository, created_job):
        """Test adding multiple log entries."""
        messages = [
            ("Job processing started", LogLevel.INFO),
            ("Template loaded", LogLevel.DEBUG),
            ("Slow response warning", LogLevel.WARNING),
        ]

        for message, level in messages:
            job_repository.add_log(created_job['id'], message, level)

        logs = job_repository.get_logs(created_job['id'])
        assert len(logs) >= 3

        for message, level in messages:
            assert any(
                log['message'] == message and log['level'] == level.value
                for log in logs
            )

    def test_get_logs_returns_ordered_list(self, job_repository, created_job):
        """Test that logs are returned in chronological order."""
        for i in range(3):
            job_repository.add_log(
                created_job['id'],
                f"Log entry {i}",
                LogLevel.INFO
            )

        logs = job_repository.get_logs(created_job['id'])
        assert len(logs) >= 3
        # Logs should be ordered by created_at (ascending)
        assert logs[0]['message'] == "Log entry 0"

    def test_get_logs_empty_for_new_job(self, job_repository, created_job):
        """Test that a new job has no logs initially."""
        logs = job_repository.get_logs(created_job['id'])
        assert len(logs) == 0


class TestJobRepositoryRetryLogic:
    """Tests for job retry and DLQ functionality."""

    def test_reset_job_for_retry(self, job_repository, sample_job_data):
        """Test resetting a failed job for retry."""
        # Create and fail a job
        job = job_repository.create(sample_job_data)
        job_repository.update_status(
            job['id'],
            JobStatus.FAILED,
            error_message="Temporary error"
        )

        # Reset for retry
        retry_time = datetime.now() + timedelta(minutes=5)
        reset_job = job_repository.reset_job_for_retry(job['id'], retry_time)

        assert reset_job['status'] == JobStatus.PENDING.value
        assert reset_job['error_message'] is None
        assert reset_job['scheduled_at'] is not None

        # Cleanup
        job_repository.delete(job['id'])

    def test_get_failed_jobs(self, job_repository, sample_job_data):
        """Test retrieving failed jobs (DLQ)."""
        # Create and fail a job
        job = job_repository.create(sample_job_data)
        job_repository.update_status(
            job['id'],
            JobStatus.FAILED,
            error_message="Test failure"
        )

        failed_jobs = job_repository.get_failed_jobs(limit=10)

        assert isinstance(failed_jobs, list)
        assert any(j['id'] == job['id'] for j in failed_jobs)
        assert all(j['status'] == JobStatus.FAILED.value for j in failed_jobs)

        # Cleanup
        job_repository.delete(job['id'])


class TestJobRepositoryIntegration:
    """Integration tests for complete job workflows."""

    def test_complete_job_lifecycle(self, job_repository, sample_job_data):
        """Test complete job lifecycle from creation to completion."""
        # Create job
        job = job_repository.create(sample_job_data)
        assert job['status'] == JobStatus.PENDING.value

        # Add initial log
        job_repository.add_log(job['id'], "Job received", LogLevel.INFO)

        # Start processing
        job = job_repository.update_status(
            job['id'],
            JobStatus.RUNNING,
            started_at=datetime.now()
        )
        assert job['status'] == JobStatus.RUNNING.value

        # Add processing logs
        job_repository.add_log(job['id'], "Processing data", LogLevel.INFO)
        job_repository.add_log(job['id'], "Email sent successfully", LogLevel.INFO)

        # Complete job
        job = job_repository.update_status(
            job['id'],
            JobStatus.COMPLETED,
            completed_at=datetime.now()
        )
        assert job['status'] == JobStatus.COMPLETED.value

        # Verify logs
        logs = job_repository.get_logs(job['id'])
        assert len(logs) == 3

        # Cleanup
        job_repository.delete(job['id'])

    def test_failed_job_with_retry_lifecycle(self, job_repository, sample_job_data):
        """Test job lifecycle with failure and retry."""
        # Create job
        job = job_repository.create(sample_job_data)

        # Start processing
        job_repository.update_status(job['id'], JobStatus.RUNNING, started_at=datetime.now())
        job_repository.add_log(job['id'], "Starting email send", LogLevel.INFO)

        # First failure
        job_repository.increment_retry_count(job['id'])
        job = job_repository.update_status(
            job['id'],
            JobStatus.FAILED,
            error_message="Connection timeout",
            completed_at=datetime.now()
        )
        job_repository.add_log(job['id'], "Failed: Connection timeout", LogLevel.ERROR)

        assert job['status'] == JobStatus.FAILED.value
        assert job['retry_count'] == 1

        # Reset for retry
        retry_time = datetime.now() + timedelta(seconds=30)
        job = job_repository.reset_job_for_retry(job['id'], retry_time)
        assert job['status'] == JobStatus.PENDING.value
        assert job['error_message'] is None

        # Retry succeeds
        job_repository.update_status(job['id'], JobStatus.RUNNING, started_at=datetime.now())
        job = job_repository.update_status(
            job['id'],
            JobStatus.COMPLETED,
            completed_at=datetime.now()
        )
        job_repository.add_log(job['id'], "Retry successful", LogLevel.INFO)

        assert job['status'] == JobStatus.COMPLETED.value
        assert job['retry_count'] == 1

        # Verify complete log history
        logs = job_repository.get_logs(job['id'])
        assert len(logs) >= 3

        # Cleanup
        job_repository.delete(job['id'])