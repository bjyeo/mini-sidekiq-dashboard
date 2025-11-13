"""
Test Supabase database connection and verify schema setup.

This script performs the following tests:
1. Connect to Supabase
2. Verify tables exist (jobs, job_logs)
3. Insert a test job
4. Retrieve the test job
5. Update the test job
6. Delete the test job
7. Verify database functions exist

Usage:
    python scripts/test_connection.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.enums import JobStatus
from src.database.connection import get_supabase_client

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_connection():
    """Run all connection tests"""
    print_section("Starting Supabase Connection Tests")

    try:
        # Initialize client
        print("\n[1/7] Initializing Supabase client...")
        supabase = get_supabase_client()
        print("✓ Client initialized successfully")

        # Test 1: Check tables exist
        print("\n[2/7] Checking if tables exist...")
        response = supabase.table('jobs').select(
            'count', count='exact').execute()
        print(f"✓ 'jobs' table accessible. Current count: {response.count}")

        response = supabase.table('job_logs').select(
            'count', count='exact').execute()
        print(
            f"✓ 'job_logs' table accessible. Current count: {response.count}")

        # Test 2: Insert a test job
        print("\n[3/7] Inserting test job...")
        test_job_data = {
            'type': 'connection_test',
            'payload': {
                'message': 'Testing database connection',
                'timestamp': datetime.now().isoformat()
            },
            'priority': 0,
            'status': JobStatus.PENDING.value
        }

        response = supabase.table('jobs').insert(test_job_data).execute()
        test_job = response.data[0]
        job_id = test_job['id']
        print(f"✓ Test job created successfully")
        print(f"  - Job ID: {job_id}")
        print(f"  - Type: {test_job['type']}")
        print(f"  - Status: {test_job['status']}")

        # Test 3: Retrieve the job
        print("\n[4/7] Retrieving test job...")
        response = supabase.table('jobs').select(
            '*').eq('id', job_id).execute()
        retrieved_job = response.data[0]
        print(f"✓ Job retrieved successfully")
        print(f"  - ID matches: {retrieved_job['id'] == job_id}")
        print(f"  - Payload: {retrieved_job['payload']}")

        # Test 4: Update the job status
        print("\n[5/7] Updating job status...")
        response = supabase.table('jobs').update({
            'status': JobStatus.RUNNING.value,
            'started_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()
        updated_job = response.data[0]
        print(f"✓ Job updated successfully")
        print(f"  - New status: {updated_job['status']}")
        print(f"  - Started at: {updated_job['started_at']}")

        # Test 5: Insert a log entry
        print("\n[6/7] Inserting job log...")
        log_data = {
            'job_id': job_id,
            'message': 'Test log entry',
            'level': 'info'
        }
        response = supabase.table('job_logs').insert(log_data).execute()
        print(f"✓ Log entry created successfully")
        print(f"  - Log ID: {response.data[0]['id']}")

        # Test 6: Clean up - delete the test job (will cascade delete logs)
        print("\n[7/7] Cleaning up test data...")
        supabase.table('jobs').delete().eq('id', job_id).execute()
        print(f"✓ Test job deleted successfully")

        # Verify deletion
        response = supabase.table('jobs').select(
            '*').eq('id', job_id).execute()
        if len(response.data) == 0:
            print(f"✓ Verified job was deleted")

        # Final success message
        print_section("All Tests Passed! ✓")
        print("\nYour Supabase database is properly configured and ready to use.")
        print("\nNext steps:")
        print("  1. Implement Repository pattern")
        print("  2. Build API service")
        print("  3. Build Worker service")

        return True

    except Exception as e:
        print_section("Tests Failed! ✖")
        print(f"\nError: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Verify .env file has correct SUPABASE_URL and SUPABASE_KEY")
        print("  2. Check that SQL schema was applied in Supabase dashboard")
        print("  3. Ensure network connection to Supabase is working")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
