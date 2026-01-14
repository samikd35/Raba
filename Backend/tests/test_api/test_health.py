"""RABA Health Endpoint Tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health endpoint returns healthy status."""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "RABA API"
    assert "version" in data
    assert "docs" in data


def test_docs_endpoint(client):
    """Test OpenAPI docs are accessible."""
    response = client.get("/docs")
    
    assert response.status_code == 200


def test_openapi_schema(client):
    """Test OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "RABA API"
