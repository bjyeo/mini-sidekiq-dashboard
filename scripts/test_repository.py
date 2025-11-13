"""
Test script for Repository Pattern implementation.

This script tests all repository methods to ensure they work correctly
with the Supabase database.

Usage:
    python scripts/test_repository.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.repositories.job_repository import SupabaseJobRepository
from src.models.enums import JobStatus, LogLevel


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_job(job: dict, indent: int = 2):
    """Pretty print job details"""
    prefix = " " * indent
    print(f"{prefix}ID: {job['id']}")
    print(f"{prefix}Type: {job['type']}")
    print(f"{prefix}Status: {job['status']}")
    print(f"{prefix}Priority: {job['priority']}")
    print(f"{prefix}Retry Count: {job['retry_count']}/{job['max_retries']}")
    print(f"{prefix}Created: {job['created_at']}")
    if job.get('error_message'):
        print(f"{prefix}Error: {job['error_message']}")


def test_repository():
    """Run all repository tests"""
    print_section("Starting Repository Pattern Tests")

    try:
        # Initialize repository
        print("\n[1/12] Initializing repository...")
        repo = SupabaseJobRepository()
        print("✓ Repository initialized successfully")

        # Test 1: Create a job
        print("\n[2/12] Creating a new job...")
        job_data = {
            'type': 'send_email',
            'payload': {
                'to': 'test@example.com',
                'subject': 'Test Email',
                'body': 'This is a test email from the job queue'
            },
            'priority': 5
        }

        created_job = repo.create(job_data)
        job_id = created_job['id']
        print("✓ Job created successfully")
        print_job(created_job)

        # Test 2: Get job by ID
        print("\n[3/12] Retrieving job by ID...")
        retrieved_job = repo.get_by_id(job_id)
        assert retrieved_job is not None, "Job should be found"
        assert retrieved_job['id'] == job_id, "Job ID should match"
        print(f"✓ Job retrieved successfully")

        # Test 3: Add logs
        print("\n[4/12] Adding log entries...")
        repo.add_log(job_id, "Job processing started", LogLevel.INFO)
        repo.add_log(job_id, "Email template loaded", LogLevel.DEBUG)
        repo.add_log(
            job_id, "Warning: Slow SMTP response", LogLevel.WARNING)
        print(f"✓ Added {3} log entries")

        # Test 4: Get logs
        print("\n[5/12] Retrieving job logs...")
        logs = repo.get_logs(job_id)
        assert len(logs) == 3, f"Expected 3 logs, got {len(logs)}"
        print(f"✓ Retrieved {len(logs)} logs:")
        for log in logs:
            print(f"    [{log['level']}] {log['message']}")

        # Test 5: Update status to RUNNING
        print("\n[6/12] Updating job status to RUNNING...")
        updated_job = repo.update_status(
            job_id,
            JobStatus.RUNNING,
            started_at=datetime.now()
        )
        assert updated_job['status'] == JobStatus.RUNNING.value
        assert updated_job['started_at'] is not None
        print("✓ Job status updated to RUNNING")

        # Test 6: Increment retry count
        print("\n[7/12] Incrementing retry count...")
        initial_count = updated_job['retry_count']
        updated_job = repo.increment_retry_count(job_id)
        assert updated_job['retry_count'] == initial_count + 1
        print(
            f"✓ Retry count incremented: {initial_count} → {updated_job['retry_count']}")

        # Test 7: Update status to FAILED
        print("\n[8/12] Marking job as FAILED...")
        failed_job = repo.update_status(
            job_id,
            JobStatus.FAILED,
            error_message="SMTP connection timeout",
            completed_at=datetime.now()
        )
        assert failed_job['status'] == JobStatus.FAILED.value
        assert failed_job['error_message'] == "SMTP connection timeout"
        print("✓ Job marked as FAILED")
        print(f"    Error: {failed_job['error_message']}")

        # Test 8: Get failed jobs (DLQ)
        print("\n[9/12] Retrieving failed jobs (DLQ)...")
        failed_jobs = repo.get_failed_jobs(limit=10)
        assert len(failed_jobs) > 0, "Should have at least one failed job"
        print(f"✓ Found {len(failed_jobs)} failed job(s) in DLQ")

        # Test 9: Reset job for retry
        print("\n[10/12] Resetting job for retry...")
        retry_time = datetime.now() + timedelta(minutes=5)
        reset_job = repo.reset_job_for_retry(job_id, retry_time)
        assert reset_job['status'] == JobStatus.PENDING.value
        assert reset_job['error_message'] is None
        print("✓ Job reset to PENDING status")
        print(f"    Scheduled for: {reset_job['scheduled_at']}")

        # Test 10: List jobs with filtering
        print("\n[11/12] Listing pending jobs...")
        pending_jobs = repo.list_jobs(status=JobStatus.PENDING, limit=5)
        print(f"✓ Found {len(pending_jobs)} pending job(s)")

        # Test 11: Get pending jobs (simulating worker poll)
        print("\n[12/12] Simulating worker polling for jobs...")
        jobs_to_process = repo.get_pending_jobs(limit=3)
        print(
            f"✓ Retrieved {len(jobs_to_process)} job(s) ready for processing")
        if jobs_to_process:
            print("    Jobs ready to process:")
            for job in jobs_to_process:
                print(f"      - {job['type']} (Priority: {job['priority']})")

        # Test 12: Clean up - Delete job
        print("\n[CLEANUP] Deleting test job...")
        deleted = repo.delete(job_id)
        assert deleted is True, "Job deletion should succeed"
        print("✓ Test job deleted successfully")

        # Verify deletion
        deleted_job = repo.get_by_id(job_id)
        assert deleted_job is None, "Job should not exist after deletion"
        print("✓ Verified job was deleted from database")

        # Final success message
        print_section("All Repository Tests Passed! ✓")
        print("\nRepository Pattern Implementation Summary:")
        print("  ✓ BaseJobRepository interface defined")
        print("  ✓ SupabaseJobRepository implementation complete")
        print("  ✓ All CRUD operations working")
        print("  ✓ Logging functionality verified")
        print("  ✓ Status transitions working")
        print("  ✓ Retry logic functional")
        print("  ✓ DLQ (Dead Letter Queue) ready")
        print("\nNext Steps:")
        print("  → Implement Service Layer (business logic)")
        print("  → Build FastAPI endpoints")
        print("  → Create Worker service")

        return True

    except AssertionError as e:
        print_section("Assertion Failed! ✖")
        print(f"\nAssertion Error: {str(e)}")
        return False

    except Exception as e:
        print_section("Tests Failed! ✖")
        print(f"\nError: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Ensure database connection is working")
        print("  2. Verify all tables exist (jobs, job_logs)")
        print("  3. Check that previous test scripts passed")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_repository()
    sys.exit(0 if success else 1)
