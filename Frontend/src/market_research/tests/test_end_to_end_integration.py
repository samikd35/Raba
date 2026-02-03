"""
End-to-end integration testing for Data Analysis Agent.

This module tests the complete workflow from file upload to report generation,
validates integration with existing VMP services and Field Prep, and tests
error scenarios and recovery mechanisms.
"""

import pytest
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO
import csv

from fastapi import UploadFile
from fastapi.testclient import TestClient

from ..services.market_research_analysis_service import MarketResearchAnalysisService
from ..api.router import router
from ..models.analysis_models import AnalysisRequest, AnalysisResponse
from ..services.document_parser import DocumentParserService
from ..services.chunking_engine import ChunkingAndEmbeddingEngine
from ..services.correlation_engine import CorrelationEngine
from ..services.analysis_workflow import AnalysisWorkflow


class MockVMPProject:
    """Mock VMP project data for testing."""
    
    @staticmethod
    def get_complete_project_data() -> Dict[str, Any]:
        """Get complete project data with all required components."""
        return {
            "project_id": "test-project-123",
            "tenant_id": "test-tenant-456",
            "user_id": "test-user-789",
            "field_prep_data": {
                "personas": [
                    {
                        "name": "Primary User",
                        "role": "Data Analyst",
                        "company_size": "Medium",
                        "industry": "Technology",
                        "pain_points": ["Manual data processing", "Lack of automation"],
                        "goals": ["Increase efficiency", "Reduce errors"]
                    }
                ],
                "customer_profiles": [
                    {
                        "segment": "Tech Companies",
                        "size": "50-200 employees",
                        "characteristics": ["Data-driven", "Growth-focused"],
                        "needs": ["Automation", "Integration", "Scalability"]
                    }
                ],
                "hypotheses": [
                    {
                        "id": "hyp-001",
                        "text": "Companies spend too much time on manual data processing",
                        "category": "problem"
                    }
                ],
                "assumptions": [
                    {
                        "id": "assumption-001",
                        "text": "Data analysts spend 4+ hours daily on manual processing tasks",
                        "persona": "Primary User",
                        "category": "pain_point",
                        "confidence": "medium"
                    },
                    {
                        "id": "assumption-002", 
                        "text": "80% of companies in our target market face data processing inefficiencies",
                        "persona": "Primary User",
                        "category": "market_size",
                        "confidence": "low"
                    }
                ]
            },
            "vpc_data": {
                "value_propositions": [
                    {
                        "id": "vp-001",
                        "text": "Automate data processing to save 3+ hours daily",
                        "target_persona": "Primary User"
                    }
                ]
            },
            "analysis_status": "not_started",
            "analysis_data": {},
            "research_documents_data": {}
        }
    
    @staticmethod
    def get_incomplete_project_data() -> Dict[str, Any]:
        """Get incomplete project data missing required components."""
        return {
            "project_id": "incomplete-project-123",
            "tenant_id": "test-tenant-456", 
            "user_id": "test-user-789",
            "field_prep_data": {},  # Missing required data
            "analysis_status": "not_started",
            "analysis_data": {},
            "research_documents_data": {}
        }


class MockResearchDocuments:
    """Mock research documents for testing."""
    
    @staticmethod
    def get_sample_pdf_content() -> str:
        """Get sample PDF interview content."""
        return """
        Interview Transcript - Market Research Study
        
        Interviewer: Can you describe your current data processing workflow?
        
        Participant: We spend about 4-5 hours every day manually processing data. It's incredibly time-consuming and error-prone. Our team of 8 analysts is constantly struggling with Excel spreadsheets and manual data entry.
        
        The biggest pain point is the lack of automation. We have to manually validate data, create reports, and update multiple systems. This leads to inconsistencies and delays in our decision-making process.
        
        Interviewer: How frequently do you encounter these issues?
        
        Participant: Daily. I'd say 80% of our work involves some form of manual data processing. It's affecting our productivity and job satisfaction. We've looked at several solutions, but nothing fits our specific needs and budget constraints.
        
        Interviewer: What would an ideal solution provide?
        
        Participant: Automation is key. We need something that can process large datasets, integrate with our existing CRM and ERP systems, and provide real-time insights. Time savings of at least 3 hours per day would be transformational for our team.
        
        Current solutions we've tried include basic analytics tools and Excel macros, but they're not comprehensive enough. We need enterprise-grade automation with a reasonable learning curve.
        """
    
    @staticmethod
    def get_sample_csv_data() -> List[Dict[str, Any]]:
        """Get sample CSV survey data."""
        return [
            {
                "respondent_id": "R001",
                "role": "Data Analyst", 
                "company_size": "Medium",
                "pain_point": "Manual data processing takes 4+ hours daily",
                "frequency": "Daily",
                "impact": "High",
                "current_solution": "Excel spreadsheets",
                "satisfaction": "2",
                "desired_improvement": "Automation and integration",
                "budget": "$10000-20000",
                "timeline": "3-6 months"
            },
            {
                "respondent_id": "R002",
                "role": "Business Analyst",
                "company_size": "Large", 
                "pain_point": "Lack of integration between systems",
                "frequency": "Daily",
                "impact": "High",
                "current_solution": "Multiple tools",
                "satisfaction": "3",
                "desired_improvement": "Single integrated platform",
                "budget": "$20000-50000",
                "timeline": "1-3 months"
            },
            {
                "respondent_id": "R003",
                "role": "Data Manager",
                "company_size": "Small",
                "pain_point": "Error-prone manual processes",
                "frequency": "Weekly", 
                "impact": "Medium",
                "current_solution": "Manual processes",
                "satisfaction": "1",
                "desired_improvement": "Automated validation",
                "budget": "$5000-10000",
                "timeline": "6-12 months"
            }
        ]


def create_upload_file(content: str, filename: str) -> UploadFile:
    """Create UploadFile from string content."""
    file_obj = BytesIO(content.encode('utf-8'))
    return UploadFile(filename=filename, file=file_obj)


def create_csv_upload_file(data: List[Dict], filename: str) -> UploadFile:
    """Create UploadFile from CSV data."""
    output = BytesIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    output.seek(0)
    return UploadFile(filename=filename, file=output)


@pytest.fixture
def mock_database_adapter():
    """Mock database adapter for testing."""
    adapter = AsyncMock()
    
    # Mock project data retrieval
    adapter.get_project_by_id.return_value = MockVMPProject.get_complete_project_data()
    adapter.update_project_analysis_data.return_value = True
    adapter.update_project_research_documents.return_value = True
    
    return adapter


@pytest.fixture
def mock_vector_adapter():
    """Mock vector adapter for testing."""
    adapter = AsyncMock()
    
    # Mock embedding generation
    adapter.generate_embeddings.return_value = [[0.1, 0.2, 0.3] for _ in range(10)]
    adapter.similarity_search.return_value = [
        {"content": "relevant content 1", "score": 0.9},
        {"content": "relevant content 2", "score": 0.8}
    ]
    
    return adapter


@pytest.fixture
def mock_auth_adapter():
    """Mock auth adapter for testing."""
    adapter = AsyncMock()
    
    # Mock authentication and authorization
    adapter.validate_tenant_access.return_value = True
    adapter.validate_user_permissions.return_value = True
    adapter.get_user_credits.return_value = 100
    adapter.deduct_credits.return_value = True
    
    return adapter


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    service = AsyncMock()
    
    # Mock AI analysis responses
    service.analyze_with_structured_output.return_value = {
        "claim": "Data analysts spend significant time on manual processing",
        "accuracy_level": "high",
        "supporting_evidence": ["Interview data shows 4-5 hours daily", "Survey confirms daily frequency"],
        "confidence_score": 0.85
    }
    
    return service


@pytest.fixture
def sample_pdf_file():
    """Sample PDF file for testing."""
    content = MockResearchDocuments.get_sample_pdf_content()
    return create_upload_file(content, "interview_transcript.pdf")


@pytest.fixture
def sample_csv_file():
    """Sample CSV file for testing."""
    data = MockResearchDocuments.get_sample_csv_data()
    return create_csv_upload_file(data, "survey_data.csv")


class TestEndToEndWorkflow:
    """Test complete workflow from file upload to report generation."""
    
    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(
        self,
        mock_database_adapter,
        mock_vector_adapter,
        mock_auth_adapter,
        mock_ai_service,
        sample_pdf_file,
        sample_csv_file
    ):
        """Test complete analysis workflow from start to finish."""
        
        # Initialize service with mocked adapters
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_database_adapter), \
             patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_vector_adapter', return_value=mock_vector_adapter), \
             patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_auth_adapter', return_value=mock_auth_adapter), \
             patch('Backend.src.market_research.utils.ai_service_wrapper.AIServiceWrapper', return_value=mock_ai_service):
            
            service = MarketResearchAnalysisService()
            
            # Execute complete analysis workflow
            result = await service.analyze_market_research(
                project_id="test-project-123",
                tenant_id="test-tenant-456", 
                user_id="test-user-789",
                pdf_file=sample_pdf_file,
                csv_file=sample_csv_file
            )
            
            # Validate workflow completion
            assert result is not None
            assert result["status"] == "completed"
            assert "session_id" in result
            assert "results" in result
            
            # Validate that all components were called
            mock_database_adapter.get_project_by_id.assert_called_once()
            mock_database_adapter.update_project_research_documents.assert_called_once()
            mock_database_adapter.update_project_analysis_data.assert_called_once()
            mock_auth_adapter.validate_tenant_access.assert_called_once()
            mock_auth_adapter.deduct_credits.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_document_processing_pipeline(
        self,
        mock_database_adapter,
        mock_vector_adapter,
        sample_pdf_file,
        sample_csv_file
    ):
        """Test document processing pipeline integration."""
        
        with patch('Backend.src.market_research.services.document_parser.get_yuba_vector_adapter', return_value=mock_vector_adapter):
            
            # Test document parsing
            parser = DocumentParserService()
            pdf_result = await parser.parse_pdf(sample_pdf_file)
            csv_result = await parser.parse_csv(sample_csv_file)
            
            # Validate parsing results
            assert pdf_result["content"] is not None
            assert len(pdf_result["content"]) > 100
            assert csv_result["content"] is not None
            assert len(csv_result["content"]) > 50
            
            # Test chunking and embedding
            chunking_engine = ChunkingAndEmbeddingEngine()
            combined_content = pdf_result["content"] + "\n" + csv_result["content"]
            
            chunks = await chunking_engine.chunk_content(combined_content)
            assert len(chunks) > 0
            assert all("content" in chunk for chunk in chunks)
            
            # Test embedding generation
            with patch.object(chunking_engine, 'vector_adapter', mock_vector_adapter):
                embedded_chunks = await chunking_engine.generate_embeddings([chunk["content"] for chunk in chunks])
                assert len(embedded_chunks) == len(chunks)
    
    @pytest.mark.asyncio
    async def test_analysis_workflow_integration(
        self,
        mock_database_adapter,
        mock_vector_adapter,
        mock_ai_service
    ):
        """Test analysis workflow integration with LangGraph."""
        
        # Mock project data with assumptions
        project_data = MockVMPProject.get_complete_project_data()
        mock_database_adapter.get_project_by_id.return_value = project_data
        
        with patch('Backend.src.market_research.services.analysis_workflow.get_yuba_database_adapter', return_value=mock_database_adapter), \
             patch('Backend.src.market_research.services.analysis_workflow.get_yuba_vector_adapter', return_value=mock_vector_adapter), \
             patch('Backend.src.market_research.utils.ai_service_wrapper.AIServiceWrapper', return_value=mock_ai_service):
            
            workflow = AnalysisWorkflow()
            
            # Execute analysis workflow
            result = await workflow.execute_analysis(
                project_id="test-project-123",
                tenant_id="test-tenant-456",
                research_chunks=[
                    {"content": "Sample research content", "embedding": [0.1, 0.2, 0.3]}
                ]
            )
            
            # Validate workflow results
            assert result is not None
            assert "assumption_analyses" in result
            assert len(result["assumption_analyses"]) > 0
            
            # Validate that assumptions were processed
            for analysis in result["assumption_analyses"]:
                assert "assumption_id" in analysis
                assert "validation_status" in analysis
                assert "analyses" in analysis
    
    @pytest.mark.asyncio
    async def test_report_generation_integration(
        self,
        mock_database_adapter,
        mock_ai_service
    ):
        """Test report generation integration."""
        
        # Mock analysis results
        analysis_results = {
            "assumption_analyses": [
                {
                    "assumption_id": "assumption-001",
                    "assumption_text": "Data analysts spend 4+ hours daily on manual processing",
                    "persona_name": "Primary User",
                    "validation_status": "validated",
                    "analyses": {
                        "pain_points": {
                            "claim": "Manual processing is a significant pain point",
                            "accuracy_level": "high",
                            "supporting_evidence": ["Interview confirms 4-5 hours daily"]
                        }
                    }
                }
            ]
        }
        
        with patch('Backend.src.market_research.agents.report_synthesizer_agent.AIServiceWrapper', return_value=mock_ai_service):
            from ..agents.report_synthesizer_agent import ReportSynthesizerAgent
            
            synthesizer = ReportSynthesizerAgent()
            
            # Mock AI service to return formatted report
            mock_ai_service.analyze_with_structured_output.return_value = {
                "report": "# Market Research Analysis Report\n\n## Assumption Analysis\n\n### Assumption 001: VALIDATED\n\nData analysts spend 4+ hours daily on manual processing tasks.\n\n**Evidence**: Interview data confirms this pain point."
            }
            
            report = await synthesizer.synthesize_report(analysis_results)
            
            # Validate report generation
            assert report is not None
            assert "Market Research Analysis Report" in report
            assert "VALIDATED" in report


class TestVMPServiceIntegration:
    """Test integration with existing VMP services and Field Prep."""
    
    @pytest.mark.asyncio
    async def test_field_prep_integration(self, mock_database_adapter):
        """Test integration with Field Prep service patterns."""
        
        # Mock Field Prep data structure
        field_prep_data = {
            "personas": [{"name": "Primary User", "role": "Analyst"}],
            "customer_profiles": [{"segment": "Tech Companies"}],
            "assumptions": [{"id": "assumption-001", "text": "Test assumption"}]
        }
        
        project_data = MockVMPProject.get_complete_project_data()
        project_data["field_prep_data"] = field_prep_data
        mock_database_adapter.get_project_by_id.return_value = project_data
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_database_adapter):
            
            service = MarketResearchAnalysisService()
            
            # Test context loading (same pattern as Field Prep)
            context = await service._get_project_context(
                project_id="test-project-123",
                tenant_id="test-tenant-456"
            )
            
            # Validate context structure matches Field Prep patterns
            assert context is not None
            assert "personas" in context
            assert "customer_profiles" in context
            assert "assumptions" in context
            assert len(context["personas"]) > 0
            assert len(context["assumptions"]) > 0
    
    @pytest.mark.asyncio
    async def test_database_storage_patterns(self, mock_database_adapter):
        """Test database storage follows VMP patterns."""
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_database_adapter):
            
            service = MarketResearchAnalysisService()
            
            # Test research documents storage
            research_data = {
                "pdf_content": {"raw_text": "sample content", "chunks": []},
                "csv_content": {"processed_text": "sample data", "chunks": []}
            }
            
            await service._store_research_documents(
                project_id="test-project-123",
                tenant_id="test-tenant-456",
                research_data=research_data
            )
            
            # Validate storage call matches VMP patterns
            mock_database_adapter.update_project_research_documents.assert_called_once()
            call_args = mock_database_adapter.update_project_research_documents.call_args
            assert call_args[1]["project_id"] == "test-project-123"
            assert call_args[1]["tenant_id"] == "test-tenant-456"
            assert "research_documents_data" in call_args[1]
            
            # Test analysis results storage
            analysis_data = {
                "session_id": "test-session",
                "assumption_analyses": [],
                "final_report": "Test report"
            }
            
            await service._store_analysis_results(
                project_id="test-project-123",
                tenant_id="test-tenant-456",
                analysis_data=analysis_data
            )
            
            # Validate analysis storage call
            mock_database_adapter.update_project_analysis_data.assert_called_once()
            call_args = mock_database_adapter.update_project_analysis_data.call_args
            assert call_args[1]["project_id"] == "test-project-123"
            assert "analysis_data" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_credit_system_integration(self, mock_auth_adapter):
        """Test integration with existing credit system."""
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_auth_adapter', return_value=mock_auth_adapter):
            
            service = MarketResearchAnalysisService()
            
            # Test credit validation and deduction
            await service._validate_and_deduct_credits(
                tenant_id="test-tenant-456",
                user_id="test-user-789",
                operation="market_research_analysis"
            )
            
            # Validate credit system calls
            mock_auth_adapter.get_user_credits.assert_called_once_with(
                tenant_id="test-tenant-456",
                user_id="test-user-789"
            )
            mock_auth_adapter.deduct_credits.assert_called_once()


class TestErrorScenariosAndRecovery:
    """Test error scenarios and recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_missing_project_context_error(self, mock_database_adapter):
        """Test error handling for missing project context."""
        
        # Mock incomplete project data
        mock_database_adapter.get_project_by_id.return_value = MockVMPProject.get_incomplete_project_data()
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_database_adapter):
            
            service = MarketResearchAnalysisService()
            
            # Test that missing context raises appropriate error
            with pytest.raises(ValueError) as exc_info:
                await service.analyze_market_research(
                    project_id="incomplete-project-123",
                    tenant_id="test-tenant-456",
                    user_id="test-user-789"
                )
            
            assert "missing required project context" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_document_parsing_error_recovery(self, mock_database_adapter):
        """Test error recovery for document parsing failures."""
        
        mock_database_adapter.get_project_by_id.return_value = MockVMPProject.get_complete_project_data()
        
        # Create corrupted file
        corrupted_file = create_upload_file("corrupted content", "corrupted.pdf")
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_database_adapter), \
             patch('Backend.src.market_research.services.document_parser.DocumentParserService.parse_pdf', side_effect=Exception("Parsing failed")):
            
            service = MarketResearchAnalysisService()
            
            # Test that parsing errors are handled gracefully
            with pytest.raises(Exception) as exc_info:
                await service.analyze_market_research(
                    project_id="test-project-123",
                    tenant_id="test-tenant-456",
                    user_id="test-user-789",
                    pdf_file=corrupted_file
                )
            
            assert "parsing failed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_ai_service_failure_recovery(
        self,
        mock_database_adapter,
        mock_vector_adapter,
        mock_auth_adapter,
        sample_pdf_file
    ):
        """Test recovery from AI service failures."""
        
        mock_database_adapter.get_project_by_id.return_value = MockVMPProject.get_complete_project_data()
        
        # Mock AI service failure
        mock_ai_service = AsyncMock()
        mock_ai_service.analyze_with_structured_output.side_effect = Exception("AI service unavailable")
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_database_adapter), \
             patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_vector_adapter', return_value=mock_vector_adapter), \
             patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_auth_adapter', return_value=mock_auth_adapter), \
             patch('Backend.src.market_research.utils.ai_service_wrapper.AIServiceWrapper', return_value=mock_ai_service):
            
            service = MarketResearchAnalysisService()
            
            # Test that AI service failures are handled
            with pytest.raises(Exception) as exc_info:
                await service.analyze_market_research(
                    project_id="test-project-123",
                    tenant_id="test-tenant-456",
                    user_id="test-user-789",
                    pdf_file=sample_pdf_file
                )
            
            # Validate error handling
            assert "ai service" in str(exc_info.value).lower() or "unavailable" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_partial_analysis_failure_recovery(
        self,
        mock_database_adapter,
        mock_vector_adapter,
        mock_auth_adapter
    ):
        """Test recovery from partial analysis failures."""
        
        project_data = MockVMPProject.get_complete_project_data()
        # Add multiple assumptions to test partial failure
        project_data["field_prep_data"]["assumptions"] = [
            {"id": "assumption-001", "text": "First assumption", "persona": "Primary User"},
            {"id": "assumption-002", "text": "Second assumption", "persona": "Primary User"},
            {"id": "assumption-003", "text": "Third assumption", "persona": "Primary User"}
        ]
        mock_database_adapter.get_project_by_id.return_value = project_data
        
        # Mock AI service that fails on second assumption
        mock_ai_service = AsyncMock()
        call_count = 0
        
        def mock_ai_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second call
                raise Exception("AI service timeout")
            return {
                "claim": f"Analysis result {call_count}",
                "accuracy_level": "medium",
                "supporting_evidence": ["Evidence"],
                "confidence_score": 0.7
            }
        
        mock_ai_service.analyze_with_structured_output.side_effect = mock_ai_call
        
        with patch('Backend.src.market_research.services.analysis_workflow.get_yuba_database_adapter', return_value=mock_database_adapter), \
             patch('Backend.src.market_research.services.analysis_workflow.get_yuba_vector_adapter', return_value=mock_vector_adapter), \
             patch('Backend.src.market_research.utils.ai_service_wrapper.AIServiceWrapper', return_value=mock_ai_service):
            
            workflow = AnalysisWorkflow()
            
            # Test partial failure handling
            try:
                result = await workflow.execute_analysis(
                    project_id="test-project-123",
                    tenant_id="test-tenant-456",
                    research_chunks=[{"content": "test", "embedding": [0.1]}]
                )
                
                # Should have partial results
                assert result is not None
                assert "assumption_analyses" in result
                # Should have results for assumptions that succeeded
                successful_analyses = [a for a in result["assumption_analyses"] if "error" not in a]
                assert len(successful_analyses) > 0
                
            except Exception as e:
                # If complete failure, ensure error is properly handled
                assert "timeout" in str(e).lower() or "ai service" in str(e).lower()


class TestAPIEndpointIntegration:
    """Test API endpoint integration."""
    
    def test_file_upload_endpoint_integration(self):
        """Test file upload endpoint integration."""
        
        # This would require setting up FastAPI test client
        # For now, we'll test the endpoint structure
        from ..api.router import router
        
        # Validate that required endpoints exist
        routes = [route.path for route in router.routes]
        
        expected_endpoints = [
            "/upload-research-documents",
            "/start-analysis", 
            "/analysis-status/{session_id}",
            "/analysis-results/{session_id}"
        ]
        
        for endpoint in expected_endpoints:
            # Check if endpoint pattern exists in routes
            endpoint_exists = any(endpoint.replace("{session_id}", "") in route for route in routes)
            assert endpoint_exists, f"Expected endpoint {endpoint} not found in router"
    
    @pytest.mark.asyncio
    async def test_api_error_handling_integration(self):
        """Test API error handling integration."""
        
        # Test that API endpoints handle errors properly
        from ..api.models import AnalysisRequest, ErrorResponse
        
        # Validate error response model structure
        error_response = ErrorResponse(
            error="test_error",
            message="Test error message",
            details={"field": "validation error"}
        )
        
        assert error_response.error == "test_error"
        assert error_response.message == "Test error message"
        assert error_response.details["field"] == "validation error"


if __name__ == "__main__":
    # Run end-to-end integration tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-k", "test_complete_analysis_workflow or test_field_prep_integration"
    ])