"""
Integration tests for job endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """
    Test client fixture for the FastAPI application.
    """
    from src.api.main import app
    return TestClient(app)


@pytest.mark.integration
def test_create_job_returns_201(client):
    """
    Test that creating a job returns 201 Created.
    """
    job_data = {
        "type": "send_email",
        "payload": {"to": "test@example.com", "subject": "Test"}
    }

    response = client.post("/jobs", json=job_data)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["type"] == "send_email"
    assert data["status"] == "pending"
    assert data["payload"] == {"to": "test@example.com", "subject": "Test"}


@pytest.mark.integration
def test_get_job_by_id_returns_200(client):
    """
    Test that getting a job by ID returns 200 OK.
    """
    # First create a job
    job_data = {
        "type": "process_image",
        "payload": {"image_url": "http://example.com/image.jpg"}
    }
    create_response = client.post("/jobs", json=job_data)
    job_id = create_response.json()["id"]

    # Get the job by ID
    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["type"] == "process_image"
    assert data["status"] == "pending"
    assert data["payload"] == {"image_url": "http://example.com/image.jpg"}


@pytest.mark.integration
def test_get_nonexistent_job_returns_404(client):
    """
    Test that getting a non-existent job returns 404 Not Found.
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/jobs/{fake_id}")

    assert response.status_code == 404


@pytest.mark.integration
def test_list_jobs_returns_200(client):
    """
    Test that listing jobs returns 200 OK with array of jobs.
    """
    # Create a couple of jobs first
    client.post("/jobs", json={
        "type": "send_email",
        "payload": {"to": "user1@example.com"}
    })
    client.post("/jobs", json={
        "type": "process_data",
        "payload": {"data_id": "123"}
    })

    response = client.get("/jobs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
