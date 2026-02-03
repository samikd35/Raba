"""RABA Tools Video Endpoints Tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_tools_from_video_preview_requires_file(client):
    """Missing file should return validation error."""
    response = client.post("/api/v1/tools/from-video/preview")
    assert response.status_code == 422


def test_tools_from_video_preview_invalid_mime(client):
    """Invalid mime type should be rejected or fail if Redis unavailable."""
    files = {"reference_video": ("test.txt", b"hello", "text/plain")}
    response = client.post("/api/v1/tools/from-video/preview", files=files)
    assert response.status_code in [400, 503]


def test_tools_from_video_create_requires_draft_id(client):
    """Missing draft_id should return validation error."""
    response = client.post("/api/v1/tools/from-video", json={})
    assert response.status_code == 422


def test_tools_from_video_create_missing_draft(client):
    """Unknown draft should return 400 or 503 when Redis unavailable."""
    response = client.post("/api/v1/tools/from-video", json={"draft_id": "missing"})
    assert response.status_code in [400, 503]
