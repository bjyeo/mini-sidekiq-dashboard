"""
FastAPI application for the job queue dashboard.

This module contains the main FastAPI application and all API endpoints.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from src.repositories.job_repository import SupabaseJobRepository
from src.models.enums import JobStatus

app = FastAPI(
    title="Mini Sidekiq Dashboard",
    description="A job queue dashboard API",
    version="1.0.0"
)

# Initialize repository
job_repository = SupabaseJobRepository()


# Pydantic models
class CreateJobRequest(BaseModel):
    type: str
    payload: Dict[str, Any]
    priority: int = 0
    max_retries: int = 3


class UpdateJobStatusRequest(BaseModel):
    status: str
    error_message: Optional[str] = None


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicating the service is healthy
    """
    return {"status": "healthy"}


@app.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(job_request: CreateJobRequest):
    """
    Create a new job.

    Args:
        job_request: Job creation request data

    Returns:
        dict: Created job data with ID and timestamps
    """
    job_data = {
        "type": job_request.type,
        "payload": job_request.payload,
        "priority": job_request.priority,
        "max_retries": job_request.max_retries
    }

    created_job = job_repository.create(job_data)
    return created_job


@app.get("/jobs")
async def list_jobs(limit: int = 50, offset: int = 0):
    """
    List jobs with pagination.

    Args:
        limit: Maximum number of jobs to return (default 50)
        offset: Number of jobs to skip (default 0)

    Returns:
        list: List of jobs ordered by created_at DESC
    """
    jobs = job_repository.list_jobs(limit=limit, offset=offset)
    return jobs


@app.get("/jobs/pending")
async def get_pending_jobs(limit: int = 10):
    """
    Get pending jobs ready for processing.

    Args:
        limit: Maximum number of jobs to return (default 10)

    Returns:
        list: List of pending jobs
    """
    jobs = job_repository.get_pending_jobs(limit=limit)
    return jobs


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """
    Get a job by ID.

    Args:
        job_id: UUID of the job

    Returns:
        dict: Job data

    Raises:
        HTTPException: 404 if job not found
    """
    job = job_repository.get_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found"
        )

    return job


@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str):
    """
    Delete a job by ID.

    Args:
        job_id: UUID of the job

    Raises:
        HTTPException: 404 if job not found
    """
    deleted = job_repository.delete(job_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found"
        )


@app.patch("/jobs/{job_id}/status")
async def update_job_status(job_id: str, status_update: UpdateJobStatusRequest):
    """
    Update a job's status.

    Args:
        job_id: UUID of the job
        status_update: New status and optional error message

    Returns:
        dict: Updated job data

    Raises:
        HTTPException: 404 if job not found
    """
    # Verify job exists
    job = job_repository.get_by_id(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found"
        )

    # Convert string to JobStatus enum
    try:
        job_status = JobStatus(status_update.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_update.status}"
        )

    # Set timestamps based on status
    started_at = None
    completed_at = None

    if job_status == JobStatus.RUNNING:
        started_at = datetime.now()
    elif job_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        completed_at = datetime.now()

    # Update the job status
    updated_job = job_repository.update_status(
        job_id=job_id,
        status=job_status,
        error_message=status_update.error_message,
        started_at=started_at,
        completed_at=completed_at
    )

    return updated_job
