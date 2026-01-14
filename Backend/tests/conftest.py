"""RABA Test Configuration.

Pytest fixtures and configuration for testing.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def sample_workflow_input():
    """Sample workflow input for testing."""
    return {
        "topic": "How black holes work",
        "duration_seconds": 18,
        "aspect_ratio": "9:16",
        "resolution": "1080p",
        "category": "auto",
        "hitl_mode": "auto",
        "enable_audio": True,
        "enable_subtitles": False,
    }


@pytest.fixture
def sample_workflow_input_manual():
    """Sample workflow input with manual HITL mode."""
    return {
        "topic": "The history of the Roman Empire",
        "duration_seconds": 25,
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "category": "high_octane_anime",
        "hitl_mode": "manual",
        "enable_audio": True,
        "enable_subtitles": True,
    }
