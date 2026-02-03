"""
Tests for Fact Validation Integration with Analysis Agents

Test suite for integration of fact validation engine with analysis agents,
including real-time validation, confidence adjustment, and error handling.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from ..agents.base_analysis_agent import BaseAnalysisAgent
from ..services.fact_validation_engine import FactValidationEngine
from ..services.statistics_registry_service import StatisticsRegistryService
from ..services.ground_truth_context_builder import GroundTruthContextBuilder
from ..services.evidence_retrieval_engine import EvidenceRetrievalEngine
from ..models.analysis_models import AnalysisOutput, AnalysisContext
from ..utils.error_handling import ErrorHandlingService


class MockAnalysisAgent(BaseAnalysisAgent):
    """Mock analysis agent for testing"""
    
    def _get_analysis_type(self) -> str:
        return "test_analysis"
    
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": "Test system prompt"},
            {"role": "user", "content": f"Analyze: {context.assumption.get('text', '')}"}
        ]
    
    def _get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "accuracy_level": {"type": "string"},
                "confidence_score": {"type": "number"}
            }
        }


class TestFactValidationIntegration:
    """Test suite for fact validation integration"""
    
    @pytest.fixture
    def mock_statistics_registry(self):
        """Mock statistics registry service"""
        registry = Mock(spec=StatisticsRegistryService)
        registry.get_statistics_for_analysis = AsyncMock(return_value={
            "csv_statistics": {
                "categorical_distributions": {
                    "satisfaction": {
                        "distribution": [
                            {
                                "value": "satisfied",
                                "count": 720,
                                "percentage": 72.0,
                                "citation_id": "csv_satisfaction_satisfied"
                            }
                        ]
                    }
                }
            },
            "pdf_statistics": {
                "themes": {
                    "pricing_concerns": {
                        "frequency": 15,
                        "percentage": 75.0,
                        "citation_id": "pdf_theme_pricing"
                    }
                }
            }
        })
        return registry
    
    @pytest.fixture
    def mock_ground_truth_builder(self):
        """Mock ground truth context builder"""
        builder = Mock(spec=GroundTruthContextBuilder)
        builder.build_statistics_context = AsyncMock(return_value="""
        ═══════════════════════════════════════════════════════════
        📊 GROUND TRUTH STATISTICS - SOURCE OF TRUTH FOR ALL PERCENTAGES
        ═══════════════════════════════════════════════════════════
        CSV Statistics:
        - Satisfaction: 72% satisfied (720/1000 respondents)
        
        PDF Statistics:
        - Pricing concerns: 75% of interview participants
        ═══════════════════════════════════════════════════════════
        """)
        return builder
    
    @pytest.fixture
    def mock_evidence_retrieval(self):
        """Mock evidence retrieval engine"""
        engine = Mock(spec=EvidenceRetrievalEngine)
        engine.retrieve_balanced_evidence = AsyncMock(return_value=[
            {
                "content": "Many users expressed satisfaction with the product features",
                "source_type": "csv",
                "source_file": "survey.csv",
                "similarity_score": 0.85
            },
            {
                "content": "Pricing was mentioned as a concern by several participants",
                "source_type": "pdf",
                "source_file": "interviews.pdf",
                "similarity_score": 0.78
            }
        ])
        return engine
    
    @pytest.fixture
    def analysis_agent(self, mock_statistics_registry, mock_ground_truth_builder, mock_evidence_retrieval):
        """Create analysis agent with fact validation"""
        fact_validator = FactValidationEngine()
        
        agent = MockAnalysisAgent(
            statistics_registry=mock_statistics_registry,
            ground_truth_builder=mock_ground_truth_builder,
            evidence_retrieval=mock_evidence_retrieval,
            fact_validator=fact_validator
        )
        
        return agent
    
    @pytest.fixture
    def analysis_context(self):
        """Create analysis context for testing"""
        return AnalysisContext(
            assumption={"id": "test_assumption", "text": "Users are satisfied with pricing"},
            persona={"id": "test_persona", "name": "Business User"},
            research_data=[
                {
                    "content": "Survey shows 72% satisfaction rate",
                    "source_type": "csv",
                    "metadata": {"filename": "survey.csv"}
                }
            ],
            project_context={"project_id": "test_project", "tenant_id": "test_tenant"},
            analysis_type="test_analysis"
        )
    
    @pytest.mark.asyncio
    async def test_enhanced_fact_validation_workflow(self, analysis_agent, analysis_context):
        """Test complete enhanced fact validation workflow"""
        # Mock AI service response with quantitative claims
        mock_ai_response = {
            "content": json.dumps({
                "claim": "Based on survey data, 72% of respondents are satisfied with the product. Pricing concerns were mentioned by 75% of interview participants.",
                "accuracy_level": "high",
                "supporting_evidence": ["Survey responses", "Interview feedback"],
                "confidence_score": 0.85
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback', 
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should complete analysis with fact validation
            assert isinstance(result, AnalysisOutput)
            assert result.claim is not None
            assert result.fact_validation_score is not None
            assert result.validation_metadata is not None
            
            # Should have high fact validation score (accurate claims)
            assert result.fact_validation_score >= 0.8
            
            # Should include citation IDs
            assert len(result.citation_ids) > 0
            
            # Should have persona relevance score
            assert result.persona_relevance_score is not None
    
    @pytest.mark.asyncio
    async def test_inaccurate_claims_validation(self, analysis_agent, analysis_context):
        """Test validation of inaccurate claims"""
        # Mock AI response with inaccurate claims
        mock_ai_response = {
            "content": json.dumps({
                "claim": "Survey shows 90% satisfaction rate and 95% mentioned pricing concerns.",
                "accuracy_level": "high",
                "supporting_evidence": ["Survey data"],
                "confidence_score": 0.9
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should detect inaccurate claims
            assert result.fact_validation_score < 0.5
            
            # Should reduce confidence score
            assert result.confidence_score < 0.9  # Should be reduced from original
            
            # Should have validation metadata with unsupported claims
            assert "unsupported_claims" in result.validation_metadata
            assert len(result.validation_metadata["unsupported_claims"]) > 0
    
    @pytest.mark.asyncio
    async def test_fallback_validation_when_registry_unavailable(self, analysis_agent, analysis_context):
        """Test fallback validation when statistics registry is unavailable"""
        # Make statistics registry fail
        analysis_agent.statistics_registry.get_statistics_for_analysis.side_effect = Exception("Registry unavailable")
        
        mock_ai_response = {
            "content": json.dumps({
                "claim": "72% of users are satisfied",
                "accuracy_level": "medium",
                "confidence_score": 0.7
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should use fallback validation
            assert result.validation_metadata["validation_method"] == "legacy_chunks"
            
            # Should still complete analysis
            assert isinstance(result, AnalysisOutput)
            assert result.claim is not None
    
    @pytest.mark.asyncio
    async def test_two_tier_rag_with_validation(self, analysis_agent, analysis_context):
        """Test two-tier RAG system integration with fact validation"""
        mock_ai_response = {
            "content": json.dumps({
                "claim": "Ground truth statistics show 72% satisfaction",
                "accuracy_level": "high",
                "confidence_score": 0.8
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should use enhanced validation with registry
            assert result.validation_metadata["validation_method"] == "enhanced_registry"
            
            # Should call two-tier RAG components
            analysis_agent.ground_truth_builder.build_statistics_context.assert_called_once()
            analysis_agent.evidence_retrieval.retrieve_balanced_evidence.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_persona_relevance_calculation(self, analysis_agent, analysis_context):
        """Test persona relevance score calculation"""
        # Update context with detailed persona
        analysis_context.persona = {
            "id": "business_user",
            "name": "Business User",
            "description": "Small business owner focused on cost-effectiveness",
            "demographics": ["business owner", "cost-conscious"],
            "pain_points": ["pricing", "budget constraints"]
        }
        
        mock_ai_response = {
            "content": json.dumps({
                "claim": "Business users are concerned about pricing and budget constraints",
                "accuracy_level": "high",
                "confidence_score": 0.8
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should have high persona relevance
            assert result.persona_relevance_score > 0.5
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, analysis_agent, analysis_context):
        """Test error handling during fact validation"""
        # Make fact validator fail
        with patch.object(analysis_agent.fact_validator, 'extract_quantitative_claims',
                         side_effect=Exception("Validation error")):
            
            mock_ai_response = {
                "content": json.dumps({
                    "claim": "Test claim",
                    "accuracy_level": "medium",
                    "confidence_score": 0.7
                })
            }
            
            with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                             return_value=mock_ai_response):
                
                result = await analysis_agent._analyze_with_context(analysis_context)
                
                # Should fallback to legacy validation
                assert result.validation_metadata["validation_method"] == "legacy_chunks"
                
                # Should still complete analysis
                assert isinstance(result, AnalysisOutput)
    
    @pytest.mark.asyncio
    async def test_confidence_adjustment_integration(self, analysis_agent, analysis_context):
        """Test confidence score adjustment integration"""
        # Test high validation score (should maintain/boost confidence)
        mock_ai_response = {
            "content": json.dumps({
                "claim": "72% satisfaction rate confirmed by survey data",
                "accuracy_level": "high",
                "confidence_score": 0.7
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should maintain or boost confidence for accurate claims
            assert result.confidence_score >= 0.6  # Should not be heavily penalized
            
            # Should have high fact validation score
            assert result.fact_validation_score >= 0.8
    
    @pytest.mark.asyncio
    async def test_citation_extraction_integration(self, analysis_agent, analysis_context):
        """Test citation ID extraction from validation results"""
        mock_ai_response = {
            "content": json.dumps({
                "claim": "Survey shows 72% satisfaction",
                "accuracy_level": "high",
                "confidence_score": 0.8
            })
        }
        
        with patch.object(analysis_agent.ai_service_wrapper, 'generate_with_fallback',
                         return_value=mock_ai_response):
            
            result = await analysis_agent._analyze_with_context(analysis_context)
            
            # Should extract citation IDs from validation
            if result.validation_metadata.get("validation_details"):
                # Check if any validation details have citation IDs
                has_citations = any(
                    detail.get("registry_match", {}).get("citation_id")
                    for detail in result.validation_metadata["validation_details"]
                )
                if has_citations:
                    assert len(result.citation_ids) > 0


class TestValidationWithErrorHandling:
    """Test validation integration with error handling"""
    
    @pytest.fixture
    def error_handling_service(self):
        """Create error handling service"""
        return ErrorHandlingService()
    
    @pytest.mark.asyncio
    async def test_validation_error_recovery(self, error_handling_service):
        """Test recovery from validation errors"""
        from ..utils.error_handling import FactValidationError
        
        error = FactValidationError("Claim extraction failed")
        ai_response = "72% of users are satisfied"
        context = {"analysis_type": "satisfaction"}
        
        fallback_result = await error_handling_service.handle_fact_validation_error(
            error, ai_response, context
        )
        
        # Should provide fallback validation
        assert fallback_result["fact_check_score"] == 0.5
        assert fallback_result["validation_method"] == "error_fallback"
    
    @pytest.mark.asyncio
    async def test_statistics_registry_error_recovery(self, error_handling_service):
        """Test recovery from statistics registry errors"""
        from ..utils.error_handling import StatisticsRegistryError
        
        error = StatisticsRegistryError("Database connection failed")
        
        fallback_result = await error_handling_service.handle_statistics_registry_error(
            error, "test_project", "pain", {}
        )
        
        # Should provide fallback registry
        assert "csv_statistics" in fallback_result
        assert "pdf_statistics" in fallback_result
        assert fallback_result["fallback_used"] is True


class TestValidationPerformance:
    """Test validation performance and scalability"""
    
    @pytest.mark.asyncio
    async def test_validation_with_large_response(self):
        """Test validation performance with large AI responses"""
        validation_engine = FactValidationEngine()
        
        # Create large response with many claims
        large_response = " ".join([
            f"Survey shows {i}% satisfaction for feature {i}."
            for i in range(10, 100, 5)
        ])
        
        # Should handle large responses efficiently
        claims = validation_engine.extract_quantitative_claims(large_response)
        
        # Should extract multiple claims
        assert len(claims) > 10
        
        # Should complete in reasonable time (this is implicit in the test passing)
    
    @pytest.mark.asyncio
    async def test_validation_with_complex_registry(self):
        """Test validation against complex statistics registry"""
        validation_engine = FactValidationEngine()
        
        # Create complex registry with many statistics
        complex_registry = {
            "csv_statistics": {
                "categorical_distributions": {
                    f"field_{i}": {
                        "distribution": [
                            {
                                "value": f"value_{j}",
                                "count": j * 10,
                                "percentage": j * 5.0,
                                "citation_id": f"csv_{i}_{j}"
                            }
                            for j in range(1, 6)
                        ]
                    }
                    for i in range(1, 11)
                }
            },
            "pdf_statistics": {
                "themes": {
                    f"theme_{i}": {
                        "frequency": i * 2,
                        "percentage": i * 10.0,
                        "citation_id": f"pdf_theme_{i}"
                    }
                    for i in range(1, 11)
                }
            }
        }
        
        claims = [
            QuantitativeClaim(
                claim_text="25% for field_5",
                percentage=25.0,
                context="field_5",
                sample_reference="respondents"
            )
        ]
        
        # Should handle complex registry efficiently
        validation_results = validation_engine.validate_claims_against_registry(
            claims, complex_registry
        )
        
        # Should complete validation
        assert "fact_check_score" in validation_results
        assert "validation_details" in validation_results


if __name__ == "__main__":
    pytest.main([__file__])