"""Tests for HITL Service.

Tests for Human-in-the-Loop service functionality including
gate management, feedback processing, and regeneration logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models.hitl import (
    HITLAction,
    HITLFeedback,
    HITLFeedbackRequest,
    HITLGate,
    HITLModeNotManualError,
    InvalidHITLActionError,
    MaxRegenerationsExceededError,
    WorkflowNotAtGateError,
    MAX_REGENERATION_ATTEMPTS,
)
from app.services.hitl_service import HITLService, HITLServiceError


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock()
    return mock


@pytest.fixture
def hitl_service(mock_supabase):
    """Create HITLService with mocked Supabase."""
    with patch("app.services.hitl_service.get_supabase_client", return_value=mock_supabase):
        service = HITLService()
        return service


@pytest.fixture
def sample_workflow():
    """Sample workflow data."""
    return {
        "id": "test-workflow-123",
        "hitl_mode": "manual",
        "current_hitl_gate": "script",
        "hitl_approved": {},
        "hitl_feedback": [],
        "regeneration_counts": {},
        "hitl_gate_outputs": {"script": {"script_output": {"hook": "test"}}},
        "status": "awaiting_script_approval",
        "updated_at": datetime.utcnow().isoformat(),
    }


class TestHITLModels:
    """Test HITL model validation."""
    
    def test_hitl_action_enum(self):
        """Test HITLAction enum values."""
        assert HITLAction.APPROVE.value == "approve"
        assert HITLAction.EDIT.value == "edit"
        assert HITLAction.REGENERATE.value == "regenerate"
        assert HITLAction.ADD_IMAGE.value == "add_image"
    
    def test_hitl_gate_enum(self):
        """Test HITLGate enum values."""
        assert HITLGate.TOOL_SELECTION.value == "tool_selection"
        assert HITLGate.RESEARCH.value == "research"
        assert HITLGate.SCRIPT.value == "script"
        assert HITLGate.IMAGES.value == "images"
        assert HITLGate.VIDEO.value == "video"
    
    def test_hitl_feedback_model(self):
        """Test HITLFeedback model creation."""
        feedback = HITLFeedback(
            gate=HITLGate.SCRIPT,
            action=HITLAction.REGENERATE,
            feedback="Make it more dramatic",
            regeneration_attempt=1,
        )
        assert feedback.gate == HITLGate.SCRIPT
        assert feedback.action == HITLAction.REGENERATE
        assert feedback.feedback == "Make it more dramatic"
        assert feedback.regeneration_attempt == 1
    
    def test_hitl_feedback_request_model(self):
        """Test HITLFeedbackRequest model."""
        request = HITLFeedbackRequest(
            action=HITLAction.APPROVE,
        )
        assert request.action == HITLAction.APPROVE
        assert request.feedback is None
        assert request.edited_content is None


class TestHITLServicePauseAtGate:
    """Test pause_at_gate functionality."""
    
    @pytest.mark.asyncio
    async def test_pause_at_gate_updates_status(self, hitl_service, mock_supabase):
        """Test that pause_at_gate updates workflow status correctly."""
        workflow_id = "test-123"
        gate = HITLGate.SCRIPT
        output = {"script_output": {"hook": "test hook"}}
        
        await hitl_service.pause_at_gate(workflow_id, gate, output)
        
        # Verify update was called
        mock_supabase.table.assert_called_with("workflows")
        update_call = mock_supabase.table.return_value.update
        update_call.assert_called_once()
        
        # Check the update data
        update_data = update_call.call_args[0][0]
        assert update_data["status"] == "awaiting_script_approval"
        assert update_data["current_hitl_gate"] == "script"


class TestHITLServiceProcessFeedback:
    """Test process_feedback functionality."""
    
    @pytest.mark.asyncio
    async def test_process_approve(self, hitl_service, mock_supabase, sample_workflow):
        """Test APPROVE action clears gate and continues."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(action=HITLAction.APPROVE)
        response = await hitl_service.process_feedback("test-workflow-123", request)
        
        assert response.action_taken == HITLAction.APPROVE
        assert response.gate == HITLGate.SCRIPT
        assert response.next_step == "image_generator"
    
    @pytest.mark.asyncio
    async def test_process_regenerate_increments_count(self, hitl_service, mock_supabase, sample_workflow):
        """Test REGENERATE increments regeneration count."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(
            action=HITLAction.REGENERATE,
            feedback="Make it funnier",
        )
        response = await hitl_service.process_feedback("test-workflow-123", request)
        
        assert response.action_taken == HITLAction.REGENERATE
        assert response.regeneration_count == 1
    
    @pytest.mark.asyncio
    async def test_process_regenerate_max_exceeded(self, hitl_service, mock_supabase, sample_workflow):
        """Test REGENERATE fails when max attempts reached."""
        sample_workflow["regeneration_counts"] = {"script": 3}
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(
            action=HITLAction.REGENERATE,
            feedback="Try again",
        )
        
        with pytest.raises(MaxRegenerationsExceededError):
            await hitl_service.process_feedback("test-workflow-123", request)
    
    @pytest.mark.asyncio
    async def test_process_edit_applies_changes(self, hitl_service, mock_supabase, sample_workflow):
        """Test EDIT action applies user edits."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(
            action=HITLAction.EDIT,
            edited_content={"hook": {"script": "New hook text"}},
        )
        response = await hitl_service.process_feedback("test-workflow-123", request)
        
        assert response.action_taken == HITLAction.EDIT
    
    @pytest.mark.asyncio
    async def test_auto_mode_rejected(self, hitl_service, mock_supabase, sample_workflow):
        """Test HITL action rejected for auto mode workflow."""
        sample_workflow["hitl_mode"] = "auto"
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(action=HITLAction.APPROVE)
        
        with pytest.raises(HITLModeNotManualError):
            await hitl_service.process_feedback("test-workflow-123", request)
    
    @pytest.mark.asyncio
    async def test_not_at_gate_rejected(self, hitl_service, mock_supabase, sample_workflow):
        """Test feedback rejected when workflow not at any gate."""
        sample_workflow["current_hitl_gate"] = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(action=HITLAction.APPROVE)
        
        with pytest.raises(WorkflowNotAtGateError):
            await hitl_service.process_feedback("test-workflow-123", request)
    
    @pytest.mark.asyncio
    async def test_invalid_action_for_gate(self, hitl_service, mock_supabase, sample_workflow):
        """Test invalid action rejected for gate."""
        sample_workflow["current_hitl_gate"] = "video"
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        # ADD_IMAGE not valid for video gate
        request = HITLFeedbackRequest(
            action=HITLAction.ADD_IMAGE,
            additional_images=["http://example.com/img.png"],
        )
        
        with pytest.raises(InvalidHITLActionError):
            await hitl_service.process_feedback("test-workflow-123", request)
    
    @pytest.mark.asyncio
    async def test_add_image_at_images_gate(self, hitl_service, mock_supabase, sample_workflow):
        """Test ADD_IMAGE action at images gate."""
        sample_workflow["current_hitl_gate"] = "images"
        sample_workflow["generated_images"] = ["existing.png"]
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(
            action=HITLAction.ADD_IMAGE,
            additional_images=["new_image.png"],
        )
        response = await hitl_service.process_feedback("test-workflow-123", request)
        
        assert response.action_taken == HITLAction.ADD_IMAGE


class TestHITLServiceGetGateStatus:
    """Test get_gate_status functionality."""
    
    @pytest.mark.asyncio
    async def test_get_gate_status_at_gate(self, hitl_service, mock_supabase, sample_workflow):
        """Test getting status when at a gate."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        response = await hitl_service.get_gate_status("test-workflow-123")
        
        assert response.workflow_id == "test-workflow-123"
        assert response.current_gate == HITLGate.SCRIPT
        assert response.hitl_mode == "manual"
    
    @pytest.mark.asyncio
    async def test_get_gate_status_not_at_gate(self, hitl_service, mock_supabase, sample_workflow):
        """Test getting status when not at any gate."""
        sample_workflow["current_hitl_gate"] = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        response = await hitl_service.get_gate_status("test-workflow-123")
        
        assert response.current_gate is None


class TestRegenerationLimits:
    """Test regeneration limit enforcement."""
    
    def test_max_regeneration_constant(self):
        """Test MAX_REGENERATION_ATTEMPTS is 3."""
        assert MAX_REGENERATION_ATTEMPTS == 3
    
    @pytest.mark.asyncio
    async def test_regeneration_count_tracking(self, hitl_service, mock_supabase, sample_workflow):
        """Test regeneration count is tracked per gate."""
        sample_workflow["regeneration_counts"] = {"script": 1, "images": 0}
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_workflow
        
        request = HITLFeedbackRequest(
            action=HITLAction.REGENERATE,
            feedback="Try again",
        )
        response = await hitl_service.process_feedback("test-workflow-123", request)
        
        # Should be 2 (1 existing + 1 new)
        assert response.regeneration_count == 2
