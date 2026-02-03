"""
Bootstrap Module Unit Tests

Tests for individual components of the Module 3 Bootstrap feature.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
import uuid

# Test fixtures and mocks


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": str(uuid.uuid4())}]
    )
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": str(uuid.uuid4()), "name": "Test Project"}]
    )
    return mock


@pytest.fixture
def sample_project_data():
    """Sample project data for tests."""
    return {
        "project_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "name": "Test Startup Idea",
        "idea_text": "A mobile app for farmers to detect crop diseases using AI",
        "file_keys": []
    }


@pytest.fixture
def sample_enhanced_context():
    """Sample enhanced context structure."""
    return {
        "draft": {
            "IdeaSummary": "AI-powered crop disease detection app for farmers",
            "CustomerSegments": ["Smallholder farmers", "Agricultural cooperatives"],
            "Problem": {
                "who": "Farmers in developing regions",
                "what": "Difficulty detecting crop diseases early",
                "where": "Sub-Saharan Africa",
                "why_now": "Climate change increasing disease prevalence"
            },
            "SolutionOverview": "Mobile app using phone camera and AI to detect diseases",
            "Differentiation": [
                "Works offline in rural areas",
                "Supports local crop varieties",
                "Available in local languages"
            ],
            "BusinessModelSeeds": {
                "revenue_model": "Freemium with premium advisory",
                "pricing_hypothesis": "$5/month for premium features"
            },
            "Research": {
                "body": "Market research findings...",
                "sources": [
                    {"n": 1, "title": "FAO Report", "url": "https://fao.org/...", "snippet": "Crop losses..."}
                ]
            }
        },
        "confirmed": None,
        "metadata": {
            "version": 1,
            "created_at": datetime.utcnow().isoformat()
        }
    }


# ==========================================
# Database Adapter Tests
# ==========================================

class TestBootstrapDatabaseAdapter:
    """Tests for BootstrapDatabaseAdapter."""
    
    @pytest.mark.asyncio
    async def test_create_bootstrap_project(self, mock_supabase, sample_project_data):
        """Test creating a new bootstrap project."""
        with patch('src.mint.api.system.core.supabase_client.get_service_role_client', return_value=mock_supabase):
            from src.mvp.bootstrap.adapters.database_adapter import BootstrapDatabaseAdapter
            
            adapter = BootstrapDatabaseAdapter()
            adapter.supabase = mock_supabase  # Direct assignment for test
            result = adapter.create_bootstrap_project(
                project_name=sample_project_data["name"],
                tenant_id=sample_project_data["tenant_id"],
                user_id=sample_project_data["user_id"],
                idea_text=sample_project_data["idea_text"],
                file_keys=sample_project_data["file_keys"]
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_update_context_status(self, mock_supabase, sample_project_data):
        """Test updating project context status."""
        # Setup mock chain: supabase.client.table().update().eq().eq().execute()
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"context_status": "questions_pending"}]
        )
        
        with patch('src.mint.api.system.core.supabase_client.get_service_role_client', return_value=mock_supabase):
            from src.mvp.bootstrap.adapters.database_adapter import BootstrapDatabaseAdapter
            
            adapter = BootstrapDatabaseAdapter()
            adapter.supabase = mock_supabase
            success = adapter.update_context_status(
                project_id=sample_project_data["project_id"],
                tenant_id=sample_project_data["tenant_id"],
                status="questions_pending"
            )
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_save_enhanced_context(self, mock_supabase, sample_project_data, sample_enhanced_context):
        """Test saving enhanced context."""
        # Setup mock chains for both select and update operations
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": sample_project_data["project_id"], "enhanced_context": {}}
        )
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"enhanced_context": sample_enhanced_context}]
        )
        
        with patch('src.mint.api.system.core.supabase_client.get_service_role_client', return_value=mock_supabase):
            from src.mvp.bootstrap.adapters.database_adapter import BootstrapDatabaseAdapter
            
            adapter = BootstrapDatabaseAdapter()
            adapter.supabase = mock_supabase
            success = adapter.save_enhanced_context(
                project_id=sample_project_data["project_id"],
                tenant_id=sample_project_data["tenant_id"],
                enhanced_context=sample_enhanced_context,
                version=1
            )
            
            assert success is True


# ==========================================
# Question Generator Tests
# ==========================================

class TestQuestionGeneratorService:
    """Tests for QuestionGeneratorService."""
    
    @pytest.mark.asyncio
    async def test_generate_questions_fallback(self):
        """Test fallback question generation when LLM unavailable."""
        from src.mvp.bootstrap.services.question_generator import QuestionGeneratorService, FALLBACK_QUESTIONS
        
        service = QuestionGeneratorService()
        # Disable LLM providers to force fallback
        service.llm_provider = None
        service.ai_service = None
        
        questions = await service.generate_questions(
            project_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            intake_content="Test business idea",
            max_questions=6
        )
        
        assert len(questions) <= 6
        assert all("question" in q for q in questions)
        assert all("priority" in q for q in questions)
        assert questions == FALLBACK_QUESTIONS[:6]
    
    @pytest.mark.asyncio
    async def test_generate_questions_with_llm(self):
        """Test LLM-based question generation."""
        mock_response = {
            "content": json.dumps({
                "content_analysis": {
                    "provided": ["target market: farmers"],
                    "gaps": ["revenue model"]
                },
                "questions": [
                    {
                        "id": "q1",
                        "priority": "P0",
                        "category": "revenue",
                        "question": "How will farmers pay?",
                        "why_needed": "Critical for BMC",
                        "required": True
                    }
                ]
            })
        }
        
        mock_llm = AsyncMock()
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)
        
        from src.mvp.bootstrap.services.question_generator import QuestionGeneratorService
        
        service = QuestionGeneratorService()
        service.llm_provider = mock_llm
        service.ai_service = None
        service.embedding_service = None
        
        questions = await service.generate_questions(
            project_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            intake_content="A mobile app for farmers to detect crop diseases",
            max_questions=6
        )
        
        assert len(questions) >= 1
        assert questions[0]["category"] == "revenue"
    
    def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response."""
        from src.mvp.bootstrap.services.question_generator import QuestionGeneratorService
        
        service = QuestionGeneratorService()
        
        response = json.dumps({
            "questions": [
                {"id": "q1", "priority": "P0", "category": "revenue", "question": "Test?", "required": True}
            ]
        })
        
        questions = service._parse_llm_response(response, 6)
        assert len(questions) == 1
        assert questions[0]["id"] == "q1"
    
    def test_parse_llm_response_with_markdown(self):
        """Test parsing response with markdown wrapping."""
        from src.mvp.bootstrap.services.question_generator import QuestionGeneratorService
        
        service = QuestionGeneratorService()
        
        response = """```json
{
    "questions": [
        {"id": "q1", "priority": "P0", "category": "problem", "question": "Test?", "required": true}
    ]
}
```"""
        
        questions = service._parse_llm_response(response, 6)
        assert len(questions) == 1


# ==========================================
# Context Adapter Tests
# ==========================================

class TestBootstrapContextAdapter:
    """Tests for BootstrapContextAdapter."""
    
    def test_adapt_for_vps(self, sample_enhanced_context):
        """Test adapting bootstrap context for VPS generation."""
        from src.mvp.bootstrap.adapters.context_adapter import BootstrapContextAdapter
        
        adapter = BootstrapContextAdapter()
        vps_context = adapter.adapt_for_vps(
            enhanced_context=sample_enhanced_context,
            project_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4())
        )
        
        assert "customer_profile" in vps_context
        assert "value_map" in vps_context
        assert "personas" in vps_context
        assert vps_context["context_mode"] == "bootstrap"
        assert vps_context["context_completeness"] > 0
    
    def test_adapt_for_bmc(self, sample_enhanced_context):
        """Test adapting bootstrap context for BMC generation."""
        from src.mvp.bootstrap.adapters.context_adapter import BootstrapContextAdapter
        
        adapter = BootstrapContextAdapter()
        
        mock_vps_v1 = {
            "value_proposition": "Test VP",
            "customer_segment": "Test Segment"
        }
        
        bmc_context = adapter.adapt_for_bmc(
            enhanced_context=sample_enhanced_context,
            vps_v1=mock_vps_v1,
            project_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4())
        )
        
        assert "vps_v1" in bmc_context
        assert bmc_context["vps_v1"] == mock_vps_v1
        assert bmc_context["loaded_for"] == "bmc_generation"
    
    def test_calculate_completeness(self, sample_enhanced_context):
        """Test context completeness calculation."""
        from src.mvp.bootstrap.adapters.context_adapter import BootstrapContextAdapter
        
        adapter = BootstrapContextAdapter()
        context_data = sample_enhanced_context["draft"]
        
        completeness = adapter._calculate_completeness(context_data)
        
        assert 0 <= completeness <= 1
        assert completeness > 0.5  # Should be high with sample data
    
    def test_build_personas_from_segments(self, sample_enhanced_context):
        """Test building personas from customer segments."""
        from src.mvp.bootstrap.adapters.context_adapter import BootstrapContextAdapter
        
        adapter = BootstrapContextAdapter()
        
        segments = sample_enhanced_context["draft"]["CustomerSegments"]
        problem = sample_enhanced_context["draft"]["Problem"]
        
        personas = adapter._build_personas(segments, problem)
        
        assert len(personas) >= 1
        assert personas[0]["name"] in segments[0]


# ==========================================
# PDF Extractor Tests
# ==========================================

class TestPDFExtractorService:
    """Tests for PDFExtractorService."""
    
    def test_pdf_extractor_initialization(self):
        """Test PDF extractor service initialization."""
        from src.mvp.bootstrap.services.pdf_extractor import PDFExtractorService
        
        service = PDFExtractorService()
        assert service is not None
    
    def test_extract_methods_exist(self):
        """Test that extraction methods exist."""
        from src.mvp.bootstrap.services.pdf_extractor import PDFExtractorService
        
        service = PDFExtractorService()
        assert hasattr(service, '_extract_with_pypdf2')
        assert hasattr(service, '_extract_with_pdfplumber')
        assert hasattr(service, 'extract_text_from_files')


# ==========================================
# Workflow Tests
# ==========================================

class TestModule3BootstrapWorkflow:
    """Tests for Module3BootstrapWorkflow."""
    
    def test_workflow_class_exists(self):
        """Test workflow class can be imported."""
        from src.mvp.bootstrap.workflow.bootstrap_graph import Module3BootstrapWorkflow
        assert Module3BootstrapWorkflow is not None
    
    def test_workflow_factory_exists(self):
        """Test workflow factory function exists."""
        from src.mvp.bootstrap.workflow.bootstrap_graph import get_bootstrap_workflow
        assert callable(get_bootstrap_workflow)
    
    @pytest.mark.asyncio
    async def test_workflow_state_structure(self, sample_project_data):
        """Test workflow state has correct structure."""
        from src.mvp.bootstrap.models.state_models import BootstrapState, ContextStatus
        
        state: BootstrapState = {
            "project_id": sample_project_data["project_id"],
            "tenant_id": sample_project_data["tenant_id"],
            "user_id": sample_project_data["user_id"],
            "idea_text": sample_project_data["idea_text"],
            "file_keys": [],
            "is_super_admin": False,
            "plan_type": "individual",
            "pdf_extracts": [],
            "chunks_embedded": False,
            "chunk_count": 0,
            "clarifying_questions": [],
            "clarifying_answers": [],
            "research_queries": [],
            "research_results": {},
            "enhanced_context": None,
            "status": ContextStatus.NOT_STARTED.value,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        assert state["status"] == "not_started"
        assert state["project_id"] == sample_project_data["project_id"]


# ==========================================
# State Models Tests
# ==========================================

class TestStateModels:
    """Tests for state models."""
    
    def test_context_status_enum(self):
        """Test ContextStatus enum values."""
        from src.mvp.bootstrap.models.state_models import ContextStatus
        
        assert ContextStatus.NOT_STARTED.value == "not_started"
        assert ContextStatus.QUESTIONS_PENDING.value == "questions_pending"
        assert ContextStatus.CONTEXT_READY.value == "context_ready"
        assert ContextStatus.CONTEXT_CONFIRMED.value == "context_confirmed"
    
    def test_context_mode_enum(self):
        """Test ContextMode enum values."""
        from src.mvp.bootstrap.models.state_models import ContextMode
        
        assert ContextMode.NORMAL.value == "normal"
        assert ContextMode.BOOTSTRAP.value == "bootstrap"
    
    def test_bootstrap_state_structure(self):
        """Test BootstrapState TypedDict structure."""
        from src.mvp.bootstrap.models.state_models import BootstrapState, ContextStatus
        
        # Create a valid state
        state: BootstrapState = {
            "project_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "idea_text": "Test idea",
            "file_keys": [],
            "is_super_admin": False,
            "plan_type": "individual",
            "pdf_extracts": [],
            "chunks_embedded": False,
            "chunk_count": 0,
            "clarifying_questions": [],
            "clarifying_answers": [],
            "research_queries": [],
            "research_results": {},
            "enhanced_context": None,
            "status": ContextStatus.NOT_STARTED.value,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        assert state["status"] == "not_started"
        assert state["is_super_admin"] is False


# ==========================================
# Run tests
# ==========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
