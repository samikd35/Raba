"""RABA Generate Endpoint Tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_generate_valid_input(client):
    """Test generate endpoint with valid input."""
    response = client.post(
        "/api/v1/generate",
        json={
            "topic": "How black holes work",
            "duration_seconds": 18,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "category": "auto",
            "hitl_mode": "auto",
            "enable_audio": True,
            "enable_subtitles": False,
        },
    )
    
    assert response.status_code in [201, 503]
    
    if response.status_code == 201:
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "pending"
        assert "message" in data


def test_generate_minimal_input(client):
    """Test generate endpoint with minimal input (only topic)."""
    response = client.post(
        "/api/v1/generate",
        json={"topic": "Test topic"},
    )
    
    assert response.status_code in [201, 503]


def test_generate_missing_topic(client):
    """Test generate endpoint fails without topic."""
    response = client.post(
        "/api/v1/generate",
        json={"duration_seconds": 18},
    )
    
    assert response.status_code == 422


def test_generate_invalid_duration(client):
    """Test generate endpoint fails with invalid duration."""
    response = client.post(
        "/api/v1/generate",
        json={
            "topic": "Test topic",
            "duration_seconds": 5,
        },
    )
    
    assert response.status_code == 422


def test_generate_invalid_duration_too_long(client):
    """Test generate endpoint fails with duration > 25."""
    response = client.post(
        "/api/v1/generate",
        json={
            "topic": "Test topic",
            "duration_seconds": 30,
        },
    )
    
    assert response.status_code == 422


def test_generate_topic_too_short(client):
    """Test generate endpoint fails with topic < 3 chars."""
    response = client.post(
        "/api/v1/generate",
        json={"topic": "ab"},
    )
    
    assert response.status_code == 422


def test_generate_all_categories(client):
    """Test all category values are accepted."""
    categories = ["auto", "surreal_realism", "high_octane_anime", "stylized_3d"]
    
    for category in categories:
        response = client.post(
            "/api/v1/generate",
            json={
                "topic": f"Test topic for {category}",
                "category": category,
            },
        )
        
        assert response.status_code in [201, 503], f"Failed for category: {category}"


def test_generate_hitl_modes(client):
    """Test both HITL modes are accepted."""
    for mode in ["auto", "manual"]:
        response = client.post(
            "/api/v1/generate",
            json={
                "topic": f"Test topic for {mode} mode",
                "hitl_mode": mode,
            },
        )
        
        assert response.status_code in [201, 503], f"Failed for mode: {mode}"
