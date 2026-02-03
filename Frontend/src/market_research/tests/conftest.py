"""
Simple test configuration for Data Analysis Agent API tests.

Provides basic fixtures without complex imports.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "project_id": "test_project_123",
        "tenant_id": "test_tenant_456",
        "user_id": "test_user_789",
        "name": "Test Market Research Project"
    }


# Common test constants
TEST_PROJECT_ID = "test_project_123"
TEST_TENANT_ID = "test_tenant_456"
TEST_USER_ID = "test_user_789"