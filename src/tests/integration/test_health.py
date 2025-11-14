"""
Integration tests for health check endpoint.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """
    Test client fixture for the FastAPI application.

    This creates a test client that can make requests to the API
    without actually running the server.
    """
    from src.api.main import app
    return TestClient(app)


@pytest.mark.integration
def test_health_endpoint_returns_200(client):
    """
    Test that the health endpoint returns 200 OK.
    """
    response = client.get("/health")
    assert response.status_code == 200
