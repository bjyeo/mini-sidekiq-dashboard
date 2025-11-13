"""
Integration tests for Supabase database connection.

These tests verify:
1. Connection to Supabase
2. Table accessibility (jobs, job_logs)
3. CRUD operations on jobs table
4. Cascade deletion behavior
"""

import pytest
from datetime import datetime
from src.models.enums import JobStatus
from src.database.connection import get_supabase_client


@pytest.fixture
def supabase_client():
    """Fixture to provide Supabase client for tests."""
    return get_supabase_client()


@pytest.fixture
def test_job_data():
    """Fixture to provide test job data."""
    return {
        'type': 'connection_test',
        'payload': {
            'message': 'Testing database connection',
            'timestamp': datetime.now().isoformat()
        },
        'priority': 0,
        'status': JobStatus.PENDING.value
    }


class TestDatabaseConnection:
    """Test suite for database connectivity and basic operations."""

    def test_client_initialization(self, supabase_client):
        """Test that Supabase client can be initialized."""
        assert supabase_client is not None

    def test_jobs_table_accessible(self, supabase_client):
        """Test that jobs table exists and is accessible."""
        response = supabase_client.table('jobs').select('count', count='exact').execute()
        assert response.count is not None
        assert response.count >= 0

    def test_job_logs_table_accessible(self, supabase_client):
        """Test that job_logs table exists and is accessible."""
        response = supabase_client.table('job_logs').select('count', count='exact').execute()
        assert response.count is not None
        assert response.count >= 0

    def test_create_job(self, supabase_client, test_job_data):
        """Test creating a new job in the database."""
        response = supabase_client.table('jobs').insert(test_job_data).execute()

        assert len(response.data) == 1
        job = response.data[0]
        assert job['id'] is not None
        assert job['type'] == 'connection_test'
        assert job['status'] == JobStatus.PENDING.value

        # Cleanup
        supabase_client.table('jobs').delete().eq('id', job['id']).execute()

    def test_retrieve_job(self, supabase_client, test_job_data):
        """Test retrieving a job by ID."""
        # Create job
        insert_response = supabase_client.table('jobs').insert(test_job_data).execute()
        job_id = insert_response.data[0]['id']

        # Retrieve job
        response = supabase_client.table('jobs').select('*').eq('id', job_id).execute()

        assert len(response.data) == 1
        retrieved_job = response.data[0]
        assert retrieved_job['id'] == job_id
        assert retrieved_job['type'] == 'connection_test'
        assert retrieved_job['payload']['message'] == 'Testing database connection'

        # Cleanup
        supabase_client.table('jobs').delete().eq('id', job_id).execute()

    def test_update_job_status(self, supabase_client, test_job_data):
        """Test updating a job's status."""
        # Create job
        insert_response = supabase_client.table('jobs').insert(test_job_data).execute()
        job_id = insert_response.data[0]['id']

        # Update status
        response = supabase_client.table('jobs').update({
            'status': JobStatus.RUNNING.value,
            'started_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()

        assert len(response.data) == 1
        updated_job = response.data[0]
        assert updated_job['status'] == JobStatus.RUNNING.value
        assert updated_job['started_at'] is not None

        # Cleanup
        supabase_client.table('jobs').delete().eq('id', job_id).execute()

    def test_create_job_log(self, supabase_client, test_job_data):
        """Test creating a job log entry."""
        # Create job
        insert_response = supabase_client.table('jobs').insert(test_job_data).execute()
        job_id = insert_response.data[0]['id']

        # Create log
        log_data = {
            'job_id': job_id,
            'message': 'Test log entry',
            'level': 'info'
        }
        log_response = supabase_client.table('job_logs').insert(log_data).execute()

        assert len(log_response.data) == 1
        log = log_response.data[0]
        assert log['id'] is not None
        assert log['job_id'] == job_id
        assert log['message'] == 'Test log entry'
        assert log['level'] == 'info'

        # Cleanup
        supabase_client.table('jobs').delete().eq('id', job_id).execute()

    def test_cascade_delete_job_logs(self, supabase_client, test_job_data):
        """Test that deleting a job cascades to delete its logs."""
        # Create job
        insert_response = supabase_client.table('jobs').insert(test_job_data).execute()
        job_id = insert_response.data[0]['id']

        # Create log
        log_data = {
            'job_id': job_id,
            'message': 'Test log for cascade delete',
            'level': 'info'
        }
        log_response = supabase_client.table('job_logs').insert(log_data).execute()
        log_id = log_response.data[0]['id']

        # Delete job
        supabase_client.table('jobs').delete().eq('id', job_id).execute()

        # Verify job is deleted
        job_check = supabase_client.table('jobs').select('*').eq('id', job_id).execute()
        assert len(job_check.data) == 0

        # Verify log is also deleted (cascade)
        log_check = supabase_client.table('job_logs').select('*').eq('id', log_id).execute()
        assert len(log_check.data) == 0

    def test_full_job_lifecycle(self, supabase_client, test_job_data):
        """Test complete job lifecycle: create -> update -> log -> delete."""
        # Create
        insert_response = supabase_client.table('jobs').insert(test_job_data).execute()
        job_id = insert_response.data[0]['id']
        assert job_id is not None

        # Update to RUNNING
        update_response = supabase_client.table('jobs').update({
            'status': JobStatus.RUNNING.value,
            'started_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()
        assert update_response.data[0]['status'] == JobStatus.RUNNING.value

        # Add log
        log_response = supabase_client.table('job_logs').insert({
            'job_id': job_id,
            'message': 'Job processing',
            'level': 'info'
        }).execute()
        assert log_response.data[0]['job_id'] == job_id

        # Update to COMPLETED
        complete_response = supabase_client.table('jobs').update({
            'status': JobStatus.COMPLETED.value,
            'completed_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()
        assert complete_response.data[0]['status'] == JobStatus.COMPLETED.value

        # Delete
        supabase_client.table('jobs').delete().eq('id', job_id).execute()

        # Verify deletion
        verify_response = supabase_client.table('jobs').select('*').eq('id', job_id).execute()
        assert len(verify_response.data) == 0