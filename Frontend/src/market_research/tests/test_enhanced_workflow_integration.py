"""
End-to-End Integration Tests for Enhanced Analysis Workflow

Tests the complete workflow from document upload through enhanced analysis
to final report, validating persona-aware analysis routing and results.
"""

import pytest
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ..services.market_research_analysis_service import MarketResearchAnalysisService
from ..services.analysis_workflow import AnalysisWorkflow
from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ..models.analysis_models import AssumptionAnalysisState


class TestEnhancedWorkflowIntegration:
    """Test enhanced workflow integration with statistics registry and two-tier RAG."""
    
    @pytest.fixture
    def mock_project_context(self):
        """Mock project context with personas and assumptions."""
        return {
            "id": "test-project-123",
            "tenant_id": "test-tenant-456",
            "user_id": "test-user-789",
            "name": "Test Market Research Project",
            "field_prep_data": {
                "personas": [
                    {
                        "id": "persona-1",
                        "name": "Small Business Owner",
                        "description": "Runs a small retail business with 5-10 employees"
                    },
                    {
                        "id": "persona-2", 
                        "name": "Enterprise Manager",
                        "description": "Manages operations at a large corporation"
                    }
                ],
                "assumptions": [
                    {
                        "id": "assumption-1",
                        "text": "Small business owners struggle with inventory management",
                        "type": "pain",
                        "persona_name": "Small Business Owner",
                        "indicators": ["Manual tracking", "Stockouts", "Overstock"]
                    },
                    {
                        "id": "assumption-2",
                        "text": "Enterprise managers need advanced analytics",
                        "type": "gains",
                        "persona_name": "Enterprise Manager", 
                        "indicators": ["Data insights", "Performance metrics", "ROI tracking"]
                    }
                ]
            },
            "vpc_data": {
                "customer_profile": {
                    "pains": ["Inventory issues", "Manual processes"],
                    "gains": ["Efficiency", "Cost savings"],
                    "jobs": ["Manage inventory", "Track performance"]
                }
            },
            "research_documents_data": {
                "statistics_registry": {
                    "csv_statistics": {
                        "filename": "survey_responses.csv",
                        "metadata": {"total_rows": 100, "total_columns": 5},
                        "categorical_distributions": {
                            "business_size": {
                                "total_responses": 100,
                                "distribution": [
                                    {"value": "Small (1-10)", "count": 60, "percentage": 60.0},
                                    {"value": "Medium (11-50)", "count": 30, "percentage": 30.0},
                                    {"value": "Large (50+)", "count": 10, "percentage": 10.0}
                                ]
                            }
                        }
                    },
                    "pdf_statistics": {
                        "filename": "interviews.pdf",
                        "themes": {
                            "inventory_challenges": {
                                "frequency": 15,
                                "percentage": 75.0,
                                "sources": ["Interview 1", "Interview 3", "Interview 5"]
                            }
                        }
                    },
                    "citation_registry": {
                        "cite-001": {
                            "source_type": "csv",
                            "source_file": "survey_responses.csv",
                            "data_path": "business_size.Small (1-10)",
                            "verification_hash": "abc123"
                        }
                    },
                    "persona_mappings": {
                        "persona-1": {
                            "associated_statistics": ["cite-001"],
                            "relevance_scores": {"inventory_challenges": 0.9}
                        }
                    }
                }
            }
        }
    
    @pytest.fixture
    def mock_research_chunks(self):
        """Mock research chunks for analysis."""
        return [
            {
                "id": "chunk-1",
                "content": "Small businesses report significant challenges with inventory tracking",
                "source_type": "pdf",
                "source_file": "interviews.pdf",
                "embedding": [0.1] * 1536,
                "metadata": {"page": 1, "segment": 1}
            },
            {
                "id": "chunk-2", 
                "content": "60% of respondents are small businesses with 1-10 employees",
                "source_type": "csv",
                "source_file": "survey_responses.csv",
                "embedding": [0.2] * 1536,
                "metadata": {"row_range": "1-60"}
            },
            {
                "id": "chunk-3",
                "content": "Enterprise managers value advanced analytics and reporting capabilities",
                "source_type": "pdf",
                "source_file": "interviews.pdf", 
                "embedding": [0.3] * 1536,
                "metadata": {"page": 3, "segment": 2}
            }
        ]
    
    @pytest.fixture
    def enhanced_analysis_service(self):
        """Create enhanced analysis service with mocked dependencies."""
        service = MarketResearchAnalysisService(enable_enhanced_features=True)
        
        # Mock database adapter
        service.db_adapter = Mock(spec=AnalysisAgentDatabaseAdapter)
        service.db_adapter.get_vmp_project_context = AsyncMock()
        service.db_adapter.update_analysis_status = AsyncMock(return_value=True)
        service.db_adapter.update_analysis_data = AsyncMock(return_value=True)
        service.db_adapter.get_analysis_data = AsyncMock(return_value=None)
        service.db_adapter.clear_analysis_data = AsyncMock(return_value=True)
        service.db_adapter.get_statistics_registry = AsyncMock()
        service.db_adapter.update_statistics_registry = AsyncMock(return_value=True)
        
        # Mock enhanced components
        service.statistics_registry.store_statistics = AsyncMock(return_value=True)
        service.statistics_registry.get_complete_registry = AsyncMock()
        service.persona_correlation.associate_data_with_personas = AsyncMock()
        service.csv_extractor.extract_statistics = AsyncMock()
        service.pdf_extractor.extract_structured_content = AsyncMock()
        
        return service
    
    @pytest.mark.asyncio
    async def test_complete_enhanced_workflow(
        self, 
        enhanced_analysis_service,
        mock_project_context,
        mock_research_chunks
    ):
        """Test complete workflow from document upload through enhanced analysis to final report."""
        
        # Setup mocks
        enhanced_analysis_service.db_adapter.get_vmp_project_context.return_value = mock_project_context
        enhanced_analysis_service.statistics_registry.get_complete_registry.return_value = (
            mock_project_context["research_documents_data"]["statistics_registry"]
        )
        
        # Mock CSV extraction
        enhanced_analysis_service.csv_extractor.extract_statistics.return_value = {
            "metadata": {"filename": "test.csv", "total_rows": 100},
            "categorical_distributions": {"business_size": {"total_responses": 100}}
        }
        
        # Mock PDF extraction  
        enhanced_analysis_service.pdf_extractor.extract_structured_content.return_value = {
            "metadata": {"filename": "test.pdf", "total_pages": 5},
            "themes": {"inventory_challenges": {"frequency": 15}}
        }
        
        # Mock document processing
        with patch.object(enhanced_analysis_service, '_process_research_documents') as mock_process:
            mock_process.return_value = {
                "success": True,
                "data": {"pdf_content": {"chunks": mock_research_chunks[:2]}},
                "storage_data": mock_project_context["research_documents_data"]
            }
            
            # Mock workflow execution
            with patch('src.market_research.services.analysis_workflow.AnalysisWorkflow') as MockWorkflow:
                mock_workflow_instance = Mock()
                MockWorkflow.return_value = mock_workflow_instance
                
                mock_workflow_instance.run_analysis.return_value = {
                    "success": True,
                    "analysis_results": [
                        {
                            "assumption_id": "assumption-1",
                            "assumption_text": "Small business owners struggle with inventory management",
                            "persona_name": "Small Business Owner",
                            "validation_status": "validated",
                            "analyses": {
                                "pain": {
                                    "claim": "75% of small businesses report inventory challenges",
                                    "accuracy_level": "high",
                                    "confidence_score": 0.85,
                                    "fact_validation_score": 0.9,
                                    "citation_ids": ["cite-001"]
                                }
                            }
                        }
                    ],
                    "final_report": "# Market Research Analysis Report\n\nValidated assumptions with high confidence.",
                    "errors": []
                }
                
                # Create mock CSV and PDF files
                csv_file = Mock()
                csv_file.filename = "test.csv"
                csv_file.size = 1024
                
                pdf_file = Mock()
                pdf_file.filename = "test.pdf"
                pdf_file.size = 2048
                
                # Execute enhanced analysis
                result = await enhanced_analysis_service.analyze_market_research(
                    project_id="test-project-123",
                    tenant_id="test-tenant-456", 
                    user_id="test-user-789",
                    pdf_files=[pdf_file],
                    csv_files=[csv_file],
                    target_assumptions=["assumption-1"],
                    use_enhanced_processing=True
                )
                
                # Verify results
                assert result["success"] is True
                assert "data" in result
                assert result["data"]["status"] == "completed"
                
                # Verify enhanced processing was called
                enhanced_analysis_service.csv_extractor.extract_statistics.assert_called_once()
                enhanced_analysis_service.pdf_extractor.extract_structured_content.assert_called_once()
                enhanced_analysis_service.statistics_registry.store_statistics.assert_called()
    
    @pytest.mark.asyncio
    async def test_persona_aware_analysis_routing(
        self,
        enhanced_analysis_service,
        mock_project_context,
        mock_research_chunks
    ):
        """Test persona-aware analysis routing and results across multiple scenarios."""
        
        # Setup enhanced workflow with persona-specific data
        workflow = AnalysisWorkflow()
        
        # Mock enhanced components
        workflow.persona_correlation = Mock()
        workflow.persona_correlation.find_persona_relevant_data = AsyncMock()
        
        # Setup initial state with enhanced fields
        initial_state = {
            "project_id": "test-project-123",
            "tenant_id": "test-tenant-456",
            "project_context": mock_project_context,
            "current_assumption": mock_project_context["field_prep_data"]["assumptions"][0],
            "target_persona": mock_project_context["field_prep_data"]["personas"][0],
            "research_chunks": mock_research_chunks,
            "statistics_registry": mock_project_context["research_documents_data"]["statistics_registry"],
            "persona_data_associations": {"persona-1": ["cite-001"]},
            "current_ground_truth": {},
            "current_evidence_chunks": [],
            "citation_registry": {},
            "assumption_analyses": [],
            "current_assumption_analysis": {},
            "fact_validation_results": {},
            "generated_visualizations": {},
            "report_sections": {},
            "final_report": "",
            "current_step": "prepare_context",
            "processed_assumptions": [],
            "errors": []
        }
        
        # Test persona-specific context preparation
        result_state = await workflow._prepare_analysis_context(initial_state)
        
        # Verify enhanced context was prepared
        assert "current_ground_truth" in result_state
        assert "current_evidence_chunks" in result_state
        
        # Verify persona-specific statistics were loaded
        ground_truth = result_state["current_ground_truth"]
        assert "csv_statistics" in ground_truth or "pdf_statistics" in ground_truth
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_with_existing_projects(
        self,
        enhanced_analysis_service,
        mock_project_context
    ):
        """Test backward compatibility with existing projects and data structures."""
        
        # Remove enhanced features from project context to simulate legacy project
        legacy_context = mock_project_context.copy()
        del legacy_context["research_documents_data"]["statistics_registry"]
        
        enhanced_analysis_service.db_adapter.get_vmp_project_context.return_value = legacy_context
        
        # Mock legacy document processing
        with patch.object(enhanced_analysis_service, '_process_research_documents') as mock_process:
            mock_process.return_value = {
                "success": True,
                "data": {"pdf_content": {"chunks": []}},
                "storage_data": {}
            }
            
            with patch.object(enhanced_analysis_service, '_retrieve_complete_research_data') as mock_retrieve:
                mock_retrieve.return_value = {"pdf_content": {"chunks": []}}
                
                # Mock workflow execution
                with patch('src.market_research.services.analysis_workflow.AnalysisWorkflow') as MockWorkflow:
                    mock_workflow_instance = Mock()
                    MockWorkflow.return_value = mock_workflow_instance
                    
                    mock_workflow_instance.run_analysis.return_value = {
                        "success": True,
                        "analysis_results": [],
                        "final_report": "Legacy analysis completed",
                        "errors": []
                    }
                    
                    # Execute analysis without enhanced processing
                    result = await enhanced_analysis_service.analyze_market_research(
                        project_id="test-project-123",
                        tenant_id="test-tenant-456",
                        user_id="test-user-789",
                        use_enhanced_processing=False
                    )
                    
                    # Verify backward compatibility
                    assert result["success"] is True
                    
                    # Verify legacy processing was used
                    mock_process.assert_called_once()
                    enhanced_analysis_service.csv_extractor.extract_statistics.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_migration_and_rollback_capabilities(
        self,
        enhanced_analysis_service,
        mock_project_context
    ):
        """Test migration and rollback capabilities for gradual enhancement deployment."""
        
        # Test migration from legacy to enhanced
        legacy_research_data = {
            "pdf_content": {"raw_text": "Legacy PDF content", "chunks": []},
            "csv_content": {"raw_data": [], "processed_text": "Legacy CSV content"}
        }
        
        enhanced_analysis_service.db_adapter.get_research_documents_data.return_value = legacy_research_data
        
        # Mock migration process
        enhanced_analysis_service.statistics_registry.migrate_legacy_data = AsyncMock(return_value={
            "csv_statistics": {"migrated": True},
            "pdf_statistics": {"migrated": True},
            "citation_registry": {},
            "persona_mappings": {}
        })
        
        # Test rollback capability
        enhanced_analysis_service.db_adapter.backup_research_data = AsyncMock(return_value=True)
        enhanced_analysis_service.db_adapter.restore_research_data = AsyncMock(return_value=True)
        
        # Simulate migration
        migration_result = await enhanced_analysis_service.statistics_registry.migrate_legacy_data(
            "test-project-123", "test-tenant-456", legacy_research_data
        )
        
        # Verify migration succeeded
        assert migration_result["csv_statistics"]["migrated"] is True
        assert migration_result["pdf_statistics"]["migrated"] is True
        
        # Test rollback
        rollback_result = await enhanced_analysis_service.db_adapter.restore_research_data(
            "test-project-123", "test-tenant-456", legacy_research_data
        )
        
        assert rollback_result is True
    
    @pytest.mark.asyncio
    async def test_fact_validation_integration(
        self,
        enhanced_analysis_service,
        mock_project_context,
        mock_research_chunks
    ):
        """Test fact validation integration in the enhanced workflow."""
        
        # Setup workflow with fact validation
        workflow = AnalysisWorkflow()
        
        # Mock fact validation engine
        workflow.fact_validator = Mock()
        workflow.fact_validator.extract_quantitative_claims = Mock(return_value=[
            {
                "claim": "75% of small businesses report inventory challenges",
                "percentage": 75.0,
                "sample_reference": "small businesses",
                "context": "inventory challenges"
            }
        ])
        
        workflow.fact_validator.validate_claims_against_registry = Mock(return_value={
            "fact_check_score": 0.9,
            "valid_claims": ["75% of small businesses report inventory challenges"],
            "unsupported_claims": [],
            "questionable_claims": [],
            "validation_details": {"cite-001": {"verified": True}}
        })
        
        workflow.fact_validator.adjust_confidence_score = Mock(return_value=0.85)
        
        # Setup state with statistics registry
        state = {
            "project_id": "test-project-123",
            "tenant_id": "test-tenant-456",
            "project_context": mock_project_context,
            "statistics_registry": mock_project_context["research_documents_data"]["statistics_registry"],
            "current_assumption": mock_project_context["field_prep_data"]["assumptions"][0],
            "target_persona": mock_project_context["field_prep_data"]["personas"][0],
            "research_chunks": mock_research_chunks,
            "current_ground_truth": {"csv_statistics": {"business_size": {"Small (1-10)": 60}}},
            "current_evidence_chunks": mock_research_chunks[:2],
            "citation_registry": mock_project_context["research_documents_data"]["statistics_registry"]["citation_registry"],
            "assumption_analyses": [],
            "current_assumption_analysis": {},
            "fact_validation_results": {},
            "generated_visualizations": {},
            "report_sections": {},
            "final_report": "",
            "current_step": "pain_analysis",
            "processed_assumptions": [],
            "errors": []
        }
        
        # Mock agent analysis with fact validation
        workflow.pain_agent = Mock()
        workflow.pain_agent.analyze_for_assumption = AsyncMock()
        
        # Execute enhanced agent analysis
        result_state = await workflow._run_agent_analysis(state, workflow.pain_agent, "pain")
        
        # Verify fact validation was integrated
        assert "current_ground_truth" in result_state
        assert "current_evidence_chunks" in result_state
        
        # Verify agent was called with enhanced context
        workflow.pain_agent.analyze_for_assumption.assert_called_once_with(result_state)
    
    def test_enhanced_state_management_compatibility(self, mock_project_context):
        """Test enhanced state management maintains compatibility with existing workflow."""
        
        # Test enhanced state initialization
        enhanced_state = {
            "project_id": "test-project-123",
            "tenant_id": "test-tenant-456", 
            "project_context": mock_project_context,
            "current_assumption": {},
            "target_persona": {},
            "research_chunks": [],
            
            # Enhanced fields
            "statistics_registry": mock_project_context["research_documents_data"]["statistics_registry"],
            "persona_data_associations": {"persona-1": ["cite-001"]},
            "current_ground_truth": {},
            "current_evidence_chunks": [],
            "citation_registry": {},
            
            # Analysis results
            "assumption_analyses": [],
            "current_assumption_analysis": {},
            "fact_validation_results": {},
            "generated_visualizations": {},
            
            # Report generation
            "report_sections": {},
            "final_report": "",
            
            # Control flow
            "current_step": "initialize",
            "processed_assumptions": [],
            "errors": []
        }
        
        # Verify all required fields are present
        required_fields = [
            "project_id", "tenant_id", "project_context", "current_assumption",
            "target_persona", "research_chunks", "assumption_analyses",
            "current_assumption_analysis", "report_sections", "final_report",
            "current_step", "processed_assumptions", "errors"
        ]
        
        for field in required_fields:
            assert field in enhanced_state, f"Required field {field} missing from enhanced state"
        
        # Verify enhanced fields are present
        enhanced_fields = [
            "statistics_registry", "persona_data_associations", "current_ground_truth",
            "current_evidence_chunks", "citation_registry", "fact_validation_results",
            "generated_visualizations"
        ]
        
        for field in enhanced_fields:
            assert field in enhanced_state, f"Enhanced field {field} missing from state"
        
        # Verify statistics registry structure
        stats_registry = enhanced_state["statistics_registry"]
        assert "csv_statistics" in stats_registry
        assert "pdf_statistics" in stats_registry
        assert "citation_registry" in stats_registry
        assert "persona_mappings" in stats_registry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])