"""
Integration Tests for AMRG Workflow

Run with: pytest src/mvp/mvp_req/tests/integration_workflow.py -v

Note: These tests require mocking of external services (database, AI).
For full integration testing, use a test database.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime


class TestAMRGWorkflowIntegration:
    """Integration tests for the AMRG workflow."""
    
    @pytest.fixture
    def mock_context_pack(self):
        """Create a mock context pack for testing."""
        return {
            "project_id": "test-project-id",
            "tenant_id": "test-tenant-id",
            "artifacts": {
                "vps_v1": {"data": {"problem_statement": "Test problem"}, "version": "v1"},
                "vps_v2": {"data": {"problem_statement": "Refined problem"}, "version": "v2"},
                "bmc_v1": {"data": {"customer_segments": ["Segment 1"]}, "version": "v1"},
                "bmc_v2": {"data": {"customer_segments": ["Segment 1"]}, "version": "v2"},
                "solution_critique": {"data": {"critiques": []}, "version": "v1"}
            },
            "optional_artifacts": {},
            "metadata": {
                "project_title": "Test Project",
                "project_description": "A test project",
                "industry": "Technology",
                "geography": "Ethiopia"
            }
        }
    
    @pytest.fixture
    def mock_coarse_routing_result(self):
        """Create a mock coarse routing result."""
        return {
            "top_templates": [
                {"code": "A1", "confidence": 0.85, "rationale": "Test rationale", "key_signals": ["Signal 1"]},
                {"code": "A3", "confidence": 0.45, "rationale": "Alternative", "key_signals": ["Signal 2"]}
            ],
            "confidence_threshold_met": True,
            "ambiguity_points": ["Some ambiguity"],
            "routing_rationale": "Overall rationale"
        }
    
    @pytest.fixture
    def mock_clarifying_questions(self):
        """Create mock clarifying questions."""
        return [
            {
                "q_index": 1,
                "question_text": "What is the primary user type?",
                "category": "template_disambiguation",
                "purpose": "To clarify template selection",
                "relates_to_templates": ["A1", "A3"]
            },
            {
                "q_index": 2,
                "question_text": "What features are must-haves?",
                "category": "feature_priority",
                "purpose": "To prioritize features",
                "relates_to_templates": ["A1"]
            },
            {
                "q_index": 3,
                "question_text": "What is the geographic scope?",
                "category": "scope_clarification",
                "purpose": "To clarify scope",
                "relates_to_templates": ["A1"]
            }
        ]
    
    @pytest.mark.asyncio
    async def test_workflow_start_run_returns_questions(
        self, mock_context_pack, mock_coarse_routing_result, mock_clarifying_questions
    ):
        """Test that starting a run returns clarifying questions."""
        from ..services.amrg_workflow import AMRGWorkflow
        from ..models.enums import RunStatus
        
        with patch.multiple(
            AMRGWorkflow,
            __init__=lambda self, **kwargs: None
        ):
            workflow = AMRGWorkflow()
            
            # Mock dependencies
            workflow.context_loader = Mock()
            workflow.context_loader.validate_eligibility.return_value = (True, [], [])
            workflow.context_loader.load_context_pack.return_value = (mock_context_pack, None)
            
            workflow.db_adapter = Mock()
            workflow.db_adapter.save_amrg_run.return_value = "test-run-id"
            workflow.db_adapter.save_amrg_questions.return_value = True
            
            workflow.coarse_router = Mock()
            workflow.coarse_router.route = AsyncMock(return_value=mock_coarse_routing_result)
            
            workflow.questions_agent = Mock()
            workflow.questions_agent.generate_questions = AsyncMock(return_value=mock_clarifying_questions)
            
            # Execute
            result = await workflow.start_run(
                project_id="test-project-id",
                tenant_id="test-tenant-id",
                user_id="test-user-id"
            )
            
            # Assert
            assert result is not None
            assert result.get("run_id") is not None
            assert result.get("status") == RunStatus.AWAITING_ANSWERS.value
            assert len(result.get("questions", [])) == 3
    
    @pytest.mark.asyncio
    async def test_workflow_continue_with_answers_generates_prd(
        self, mock_context_pack, mock_coarse_routing_result, mock_clarifying_questions
    ):
        """Test that continuing with answers generates PRD."""
        from ..services.amrg_workflow import AMRGWorkflow
        from ..models.enums import RunStatus, TemplateCode
        
        with patch.multiple(
            AMRGWorkflow,
            __init__=lambda self, **kwargs: None
        ):
            workflow = AMRGWorkflow()
            
            # Mock saved run state
            saved_state = {
                "run_id": "test-run-id",
                "project_id": "test-project-id",
                "tenant_id": "test-tenant-id",
                "user_id": "test-user-id",
                "status": RunStatus.AWAITING_ANSWERS.value,
                "context_pack": mock_context_pack,
                "coarse_routing": mock_coarse_routing_result,
                "clarifying_questions": mock_clarifying_questions
            }
            
            # Mock dependencies
            workflow.db_adapter = Mock()
            workflow.db_adapter.get_amrg_run.return_value = saved_state
            workflow.db_adapter.update_amrg_status.return_value = True
            workflow.db_adapter.save_amrg_answers.return_value = True
            workflow.db_adapter.save_amrg_output.return_value = True
            
            workflow.final_router = Mock()
            workflow.final_router.route = AsyncMock(return_value={
                "selected_template_code": "A1",
                "final_confidence": 0.92,
                "final_rationale": "Test rationale"
            })
            
            workflow.prd_generator = Mock()
            workflow.prd_generator.generate = AsyncMock(return_value={
                "template_code": "A1",
                "purpose": {"validated_problem": "Test"},
                "mvp_features": {"must_haves": []}
            })
            
            workflow.schema_validator = Mock()
            workflow.schema_validator.validate_prd.return_value = ("valid", [], [])
            
            # Answers
            answers = [
                {"q_index": 1, "answer_text": "Business users"},
                {"q_index": 2, "answer_text": "Dashboard and reporting"},
                {"q_index": 3, "answer_text": "Ethiopia only"}
            ]
            
            # Execute
            result = await workflow.continue_with_answers(
                run_id="test-run-id",
                answers=answers
            )
            
            # Assert
            assert result is not None
            assert result.get("status") == RunStatus.COMPLETED.value
            assert result.get("prd_json") is not None
    
    @pytest.mark.asyncio
    async def test_workflow_fails_when_not_eligible(self):
        """Test workflow fails gracefully when project not eligible."""
        from ..services.amrg_workflow import AMRGWorkflow
        from ..models.response_models import MissingArtifactDetail
        
        with patch.multiple(
            AMRGWorkflow,
            __init__=lambda self, **kwargs: None
        ):
            workflow = AMRGWorkflow()
            
            # Mock ineligible project
            workflow.context_loader = Mock()
            workflow.context_loader.validate_eligibility.return_value = (
                False, 
                ["vps_v2"], 
                [MissingArtifactDetail(
                    artifact_name="vps_v2",
                    description="VPS v2 not found",
                    how_to_generate="Generate VPS v2 first"
                )]
            )
            
            # Execute
            result = await workflow.start_run(
                project_id="test-project-id",
                tenant_id="test-tenant-id",
                user_id="test-user-id"
            )
            
            # Assert
            assert result is not None
            assert result.get("eligible") == False
            assert "vps_v2" in result.get("missing_artifacts", [])


class TestAMRGAPIEndpoints:
    """Integration tests for API endpoints."""
    
    def test_start_run_request_validation(self):
        """Test that start run request validates correctly."""
        from ..models.response_models import AMRGGenerateRequest
        from ..models.enums import ResearchMode
        
        # Valid request
        request = AMRGGenerateRequest(
            research_mode=ResearchMode.OFF,
            force_regenerate=False
        )
        
        assert request.research_mode == ResearchMode.OFF
        assert request.force_regenerate == False
    
    def test_answers_request_validation(self):
        """Test that answers request validates correctly."""
        from ..models.response_models import AMRGAnswersRequest, AnswerItem
        
        # Valid request with 3 answers
        answers = [
            AnswerItem(q_index=1, answer_text="Answer 1"),
            AnswerItem(q_index=2, answer_text="Answer 2"),
            AnswerItem(q_index=3, answer_text="Answer 3")
        ]
        
        request = AMRGAnswersRequest(answers=answers)
        
        assert len(request.answers) == 3
        assert request.answers[0].q_index == 1
    
    def test_answers_request_requires_three(self):
        """Test that answers request requires exactly 3 answers."""
        from ..models.response_models import AMRGAnswersRequest, AnswerItem
        from pydantic import ValidationError
        
        # Invalid - only 2 answers
        answers = [
            AnswerItem(q_index=1, answer_text="Answer 1"),
            AnswerItem(q_index=2, answer_text="Answer 2")
        ]
        
        with pytest.raises(ValidationError):
            AMRGAnswersRequest(answers=answers)


class TestStatePersistence:
    """Tests for state persistence and resume."""
    
    def test_run_state_serialization(self):
        """Test that run state can be serialized and deserialized."""
        from ..models.enums import RunStatus, TemplateCode
        import json
        
        state = {
            "run_id": "test-run-id",
            "project_id": "test-project-id",
            "tenant_id": "test-tenant-id",
            "status": RunStatus.AWAITING_ANSWERS.value,
            "selected_template": TemplateCode.A1.value,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Should be JSON serializable
        json_str = json.dumps(state)
        restored = json.loads(json_str)
        
        assert restored["run_id"] == state["run_id"]
        assert restored["status"] == "awaiting_answers"
    
    def test_context_pack_serialization(self):
        """Test that context pack can be serialized."""
        import json
        
        context_pack = {
            "project_id": "test-id",
            "artifacts": {
                "vps_v2": {"data": {"problem": "test"}, "version": "v2"}
            },
            "metadata": {"project_title": "Test"}
        }
        
        # Should be JSON serializable
        json_str = json.dumps(context_pack)
        restored = json.loads(json_str)
        
        assert restored["project_id"] == context_pack["project_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
