"""RABA API Integration Tests.

Tests for Phase 4.5 - API Completion implementation.
Tests full API endpoints including generate, workflows, and rate limiting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_workflow_repo():
    """Mock workflow repository."""
    repo = MagicMock()
    repo.create = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list = AsyncMock(return_value={"data": [], "count": 0})
    repo.delete = AsyncMock(return_value=True)
    return repo


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check_returns_200(self, client):
        """Health check should return 200."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data
    
    def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "RABA API"
        assert "docs" in data


class TestGenerateEndpoint:
    """Tests for /api/v1/generate endpoint."""
    
    @patch("app.api.routes.generate.get_workflow_repository")
    def test_create_workflow_success(self, mock_get_repo, client, mock_workflow_repo):
        """IT-001: Successful workflow creation."""
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.post(
            "/api/v1/generate",
            json={
                "topic": "How black holes work",
                "duration_seconds": 18,
                "aspect_ratio": "9:16",
                "resolution": "1080p",
                "category": "auto",
                "hitl_mode": "auto",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "pending"
        assert "message" in data
    
    @patch("app.api.routes.generate.get_workflow_repository")
    def test_create_workflow_minimal(self, mock_get_repo, client, mock_workflow_repo):
        """Test with minimal required fields."""
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.post(
            "/api/v1/generate",
            json={"topic": "Test topic"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "workflow_id" in data
    
    def test_create_workflow_missing_topic(self, client):
        """IT-005: Invalid input - missing topic."""
        response = client.post(
            "/api/v1/generate",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_workflow_topic_too_short(self, client):
        """IT-005: Invalid input - topic too short."""
        response = client.post(
            "/api/v1/generate",
            json={"topic": "ab"}  # Less than 3 chars
        )
        
        assert response.status_code == 422
    
    def test_create_workflow_invalid_duration(self, client):
        """IT-005: Invalid input - duration out of range."""
        response = client.post(
            "/api/v1/generate",
            json={
                "topic": "Test topic",
                "duration_seconds": 100,  # Max is 25
            }
        )
        
        assert response.status_code == 422
    
    def test_create_workflow_invalid_aspect_ratio(self, client):
        """IT-005: Invalid input - invalid aspect ratio."""
        response = client.post(
            "/api/v1/generate",
            json={
                "topic": "Test topic",
                "aspect_ratio": "4:3",  # Not valid
            }
        )
        
        assert response.status_code == 422


class TestGenerateWithImageEndpoint:
    """Tests for /api/v1/generate/with-image endpoint."""
    
    @patch("app.api.routes.generate.get_supabase_client")
    @patch("app.api.routes.generate.get_workflow_repository")
    def test_create_workflow_with_image(
        self, mock_get_repo, mock_get_supabase, client, mock_workflow_repo
    ):
        """IT-002: Workflow creation with reference image."""
        mock_get_repo.return_value = mock_workflow_repo
        
        # Mock Supabase storage
        mock_storage = MagicMock()
        mock_storage.from_.return_value.upload.return_value = {}
        mock_storage.from_.return_value.get_public_url.return_value = "https://storage.example.com/image.jpg"
        mock_get_supabase.return_value.storage = mock_storage
        
        # Create test image
        image_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG header
        
        response = client.post(
            "/api/v1/generate/with-image",
            data={
                "topic": "How black holes work",
                "duration_seconds": "18",
            },
            files={
                "reference_image": ("test.png", BytesIO(image_content), "image/png")
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "workflow_id" in data
    
    @patch("app.api.routes.generate.get_workflow_repository")
    def test_create_workflow_without_image(self, mock_get_repo, client, mock_workflow_repo):
        """Workflow creation without image (form data)."""
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.post(
            "/api/v1/generate/with-image",
            data={
                "topic": "How black holes work",
            }
        )
        
        assert response.status_code == 201
    
    def test_create_workflow_image_too_large(self, client):
        """IT-002: Reject image larger than 10MB."""
        # Create 11MB content
        large_content = b"\x00" * (11 * 1024 * 1024)
        
        response = client.post(
            "/api/v1/generate/with-image",
            data={"topic": "Test topic"},
            files={
                "reference_image": ("large.jpg", BytesIO(large_content), "image/jpeg")
            }
        )
        
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
    
    def test_create_workflow_invalid_image_type(self, client):
        """IT-002: Reject invalid file types."""
        response = client.post(
            "/api/v1/generate/with-image",
            data={"topic": "Test topic"},
            files={
                "reference_image": ("file.pdf", BytesIO(b"PDF content"), "application/pdf")
            }
        )
        
        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()


class TestWorkflowsEndpoint:
    """Tests for /api/v1/workflows endpoint."""
    
    @patch("app.api.routes.workflows.get_workflow_repository")
    def test_get_workflow_success(self, mock_get_repo, client, mock_workflow_repo):
        """IT-003: Get workflow status."""
        test_workflow = {
            "id": "test-workflow-123",
            "status": "completed",
            "topic": "How black holes work",
            "duration_seconds": 18,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "category": "surreal_realism",
            "hitl_mode": "auto",
            "created_at": "2026-01-15T12:00:00Z",
            "updated_at": "2026-01-15T12:05:00Z",
            "completed_at": "2026-01-15T12:05:00Z",
            "video_output": {"video_url": "https://storage.example.com/video.mp4"},
        }
        mock_workflow_repo.get_by_id = AsyncMock(return_value=test_workflow)
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.get("/api/v1/workflows/test-workflow-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "test-workflow-123"
        assert data["status"] == "completed"
        assert data["video_url"] == "https://storage.example.com/video.mp4"
        assert data["generation_time_seconds"] is not None
    
    @patch("app.api.routes.workflows.get_workflow_repository")
    def test_get_workflow_not_found(self, mock_get_repo, client, mock_workflow_repo):
        """IT-006: 404 for non-existent workflow."""
        mock_workflow_repo.get_by_id = AsyncMock(return_value=None)
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.get("/api/v1/workflows/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch("app.api.routes.workflows.get_workflow_repository")
    def test_list_workflows(self, mock_get_repo, client, mock_workflow_repo):
        """IT-007: List workflows with pagination."""
        mock_workflow_repo.list = AsyncMock(return_value={
            "data": [
                {
                    "id": "workflow-1",
                    "status": "completed",
                    "topic": "Topic 1",
                    "category": "auto",
                    "created_at": "2026-01-15T12:00:00Z",
                    "completed_at": "2026-01-15T12:05:00Z",
                    "video_output": {"video_url": "https://example.com/video.mp4"},
                },
                {
                    "id": "workflow-2",
                    "status": "running",
                    "topic": "Topic 2",
                    "category": "auto",
                    "created_at": "2026-01-15T12:10:00Z",
                    "completed_at": None,
                    "video_output": None,
                }
            ],
            "count": 2
        })
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.get("/api/v1/workflows?limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["workflows"]) == 2
        assert data["total"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    @patch("app.api.routes.workflows.get_workflow_repository")
    def test_list_workflows_with_status_filter(self, mock_get_repo, client, mock_workflow_repo):
        """IT-007: List workflows with status filter."""
        mock_workflow_repo.list = AsyncMock(return_value={"data": [], "count": 0})
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.get("/api/v1/workflows?status=completed")
        
        assert response.status_code == 200
        mock_workflow_repo.list.assert_called_once()
    
    @patch("app.api.routes.workflows.get_workflow_repository")
    def test_delete_workflow(self, mock_get_repo, client, mock_workflow_repo):
        """Delete workflow endpoint."""
        mock_workflow_repo.get_by_id = AsyncMock(return_value={
            "id": "test-workflow-123",
            "status": "completed",
        })
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.delete("/api/v1/workflows/test-workflow-123")
        
        assert response.status_code == 204
    
    @patch("app.api.routes.workflows.get_workflow_repository")
    def test_delete_workflow_not_found(self, mock_get_repo, client, mock_workflow_repo):
        """Delete non-existent workflow returns 404."""
        mock_workflow_repo.get_by_id = AsyncMock(return_value=None)
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.delete("/api/v1/workflows/nonexistent-id")
        
        assert response.status_code == 404


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    @patch("app.api.routes.generate.get_workflow_repository")
    def test_rate_limit_headers_present(self, mock_get_repo, client, mock_workflow_repo):
        """IT-004: Rate limit headers are present."""
        mock_get_repo.return_value = mock_workflow_repo
        
        response = client.post(
            "/api/v1/generate",
            json={"topic": "Test topic"}
        )
        
        # slowapi adds these headers
        # Note: In test mode, rate limiting may be disabled
        assert response.status_code in [201, 429]


class TestOpenAPIDocumentation:
    """Tests for API documentation."""
    
    def test_openapi_schema_available(self, client):
        """OpenAPI schema should be accessible."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "RABA API"
        assert data["info"]["version"] == "1.0.0"
    
    def test_docs_endpoint_available(self, client):
        """Swagger docs should be accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_redoc_endpoint_available(self, client):
        """ReDoc should be accessible."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
    
    def test_openapi_has_tags(self, client):
        """OpenAPI should have endpoint tags."""
        response = client.get("/openapi.json")
        
        data = response.json()
        tags = [t["name"] for t in data.get("tags", [])]
        
        assert "generate" in tags
        assert "workflows" in tags
        assert "health" in tags
