"""
FastAPI application for the job queue dashboard.

This module contains the main FastAPI application and all API endpoints.
"""

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from src.repositories.job_repository import SupabaseJobRepository

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
