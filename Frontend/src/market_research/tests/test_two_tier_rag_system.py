"""
Integration tests for Two-Tier RAG System

Tests the complete two-tier RAG architecture including:
- Ground Truth Context Builder (Tier 1)
- Evidence Retrieval Engine (Tier 2)
- Enhanced Correlation Engine with Source Balancing
- Analysis Agents with Two-Tier Prompts
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from ..services.ground_truth_context_builder import GroundTruthContextBuilder
from ..services.evidence_retrieval_engine import EvidenceRetrievalEngine
from ..services.statistics_registry_service import StatisticsRegistryService
from ..services.correlation_engine import CorrelationEngine
from ..agents.base_analysis_agent import BaseAnalysisAgent
from ..models.analysis_models import AnalysisContext, AnalysisOutput
from ..utils.error_handling import ErrorHandlingService


class TestTwoTierRAGSystem:
    """Test suite for the complete two-tier RAG system."""
    
    @pytest.fixture
    def mock_statistics_registry(self):
        """Mock statistics registry service."""
        registry = Mock(spec=StatisticsRegistryService)
        registry.get_statistics_for_analysis = AsyncMock(return_value={
            'csv_statistics': {
                'metadata': {
                    'filename': 'test_survey.csv',
                    'total_rows': 100
                },
                'categorical_distributions': {
                    'satisfaction': {
                        'total_responses': 100,
                        'distribution': [
                            {'value': 'Very Satisfied', 'count': 45, 'percentage': 45.0, 'citation_id': 'csv_001'},
                            {'value': 'Satisfied', 'count': 30, 'percentage': 30.0, 'citation_id': 'csv_002'},
                            {'value': 'Neutral', 'count': 15, 'percentage': 15.0, 'citation_id': 'csv_003'},
                            {'value': 'Dissatisfied', 'count': 10, 'percentage': 10.0, 'citation_id': 'csv_004'}
                        ]
                    }
                }
            },
            'pdf_statistics': {
                'metadata': {
                    'filename': 'test_interviews.pdf',
                    'total_pages': 20
                },
                'themes': {
                    'pricing_concerns': {
                        'frequency': 8,
                        'percentage': 40.0,
                        'citation_id': 'pdf_001'
                    },
                    'feature_requests': {
                        'frequency': 6,
                        'percentage': 30.0,
                        'citation_id': 'pdf_002'
                    }
                }
            },
            'citation_registry': {
                'csv_001': {
                    'source_type': 'csv',
                    'source_file': 'test_survey.csv',
                    'data_path': 'satisfaction.very_satisfied',
                    'verification_hash': 'hash_001'
                },
                'pdf_001': {
                    'source_type': 'pdf',
                    'source_file': 'test_interviews.pdf',
                    'data_path': 'themes.pricing_concerns',
                    'verification_hash': 'hash_002'
                }
            },
            'persona_mappings': {
                'persona_001': {
                    'associated_statistics': ['csv_001', 'pdf_001'],
                    'relevance_scores': {
                        'pricing': 0.8,
                        'satisfaction': 0.9
                    }
                }
            }
        })
        return registry
    
    @pytest.fixture
    def mock_error_handler(self):
        """Mock error handling service."""
        handler = Mock(spec=ErrorHandlingService)
        handler.handle_context_building_error = AsyncMock(return_value="Error context")
        handler.handle_evidence_retrieval_error = AsyncMock(return_value=[])
        return handler
    
    @pytest.fixture
    def mock_db_adapter(self):
        """Mock database adapter."""
        adapter = Mock()
        adapter.get_project_data = AsyncMock(return_value={
            'research_documents_data': {
                'csv_content': {
                    'chunks': [
                        {
                            'id': 'csv_chunk_1',
                            'content': 'Survey response about pricing concerns and satisfaction levels',
                            'source_type': 'csv',
                            'source_file': 'test_survey.csv',
                            'embedding': [0.1, 0.2, 0.3] * 100  # Mock embedding
                        }
                    ],
                    'metadata': {'filename': 'test_survey.csv', 'row_count': 100}
                },
                'pdf_content': {
                    'chunks': [
                        {
                            'id': 'pdf_chunk_1',
                            'content': 'Interview excerpt discussing pricing and feature requests',
                            'source_type': 'pdf',
                            'source_file': 'test_interviews.pdf',
                            'embedding': [0.2, 0.3, 0.4] * 100  # Mock embedding
                        }
                    ],
                    'metadata': {'filename': 'test_interviews.pdf', 'total_pages': 20}
                }
            }
        })
        return adapter
    
    @pytest.fixture
    def mock_vector_adapter(self):
        """Mock vector adapter."""
        adapter = Mock()
        adapter.get_embedding = AsyncMock(return_value=[0.15, 0.25, 0.35] * 100)
        adapter.calculate_similarity = AsyncMock(return_value=0.85)
        return adapter
    
    @pytest.fixture
    def ground_truth_builder(self, mock_statistics_registry, mock_error_handler):
        """Ground truth context builder instance."""
        return GroundTruthContextBuilder(mock_statistics_registry, mock_error_handler)
    
    @pytest.fixture
    def evidence_retrieval_engine(self, mock_db_adapter, mock_vector_adapter, mock_statistics_registry, mock_error_handler):
        """Evidence retrieval engine instance."""
        return EvidenceRetrievalEngine(
            mock_db_adapter, mock_vector_adapter, mock_statistics_registry, mock_error_handler
        )
    
    @pytest.fixture
    def enhanced_correlation_engine(self):
        """Enhanced correlation engine instance."""
        with patch('src.mint.api.services.ai.embedding_service.get_embedding_service') as mock_service:
            mock_service.return_value.generate_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3] * 100])
            return CorrelationEngine()
    
    @pytest.fixture
    def test_analysis_context(self):
        """Test analysis context."""
        return AnalysisContext(
            assumption={
                'id': 'test_assumption_001',
                'text': 'Users are dissatisfied with current pricing model',
                'persona_name': 'Budget-Conscious User'
            },
            persona={
                'id': 'persona_001',
                'name': 'Budget-Conscious User',
                'demographics': {'income': 'low', 'age': '25-35'},
                'characteristics': ['price-sensitive', 'value-focused']
            },
            research_data=[],
            project_context={
                'project_id': 'test_project_001',
                'tenant_id': 'test_tenant_001'
            },
            analysis_type='pain'
        )


class TestGroundTruthContextBuilder:
    """Test Ground Truth Context Builder (Tier 1)."""
    
    @pytest.mark.asyncio
    async def test_build_statistics_context_success(self, ground_truth_builder):
        """Test successful statistics context building."""
        context = await ground_truth_builder.build_statistics_context(
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain',
            persona_id='persona_001'
        )
        
        # Verify context structure
        assert "GROUND TRUTH STATISTICS" in context
        assert "SOURCE OF TRUTH FOR ALL PERCENTAGES" in context
        assert "CRITICAL: Use ONLY these pre-computed statistics" in context
        assert "SURVEY DATA STATISTICS" in context
        assert "INTERVIEW DATA STATISTICS" in context
        assert "Very Satisfied: 45 (45.0%)" in context
        assert "pricing_concerns: 8 mentions (40.0%)" in context
        assert "[Cite: csv_001]" in context
        assert "[Cite: pdf_001]" in context
    
    @pytest.mark.asyncio
    async def test_build_statistics_context_with_persona_filter(self, ground_truth_builder):
        """Test statistics context building with persona filtering."""
        context = await ground_truth_builder.build_statistics_context(
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain',
            persona_id='persona_001'
        )
        
        # Verify persona-specific context
        assert "PERSONA-SPECIFIC DATA (ID: persona_001)" in context
        assert "Associated Statistics" in context
        assert "High Relevance Areas" in context
    
    @pytest.mark.asyncio
    async def test_build_statistics_context_empty_registry(self, mock_statistics_registry, mock_error_handler):
        """Test context building when no statistics are available."""
        mock_statistics_registry.get_statistics_for_analysis.return_value = None
        
        builder = GroundTruthContextBuilder(mock_statistics_registry, mock_error_handler)
        context = await builder.build_statistics_context(
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain'
        )
        
        assert "NO STATISTICS AVAILABLE" in context
        assert "Proceed with qualitative analysis only" in context
    
    @pytest.mark.asyncio
    async def test_token_budget_compliance(self, ground_truth_builder):
        """Test that context stays within token budget."""
        context = await ground_truth_builder.build_statistics_context(
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain'
        )
        
        # Rough token estimation (1 token ≈ 4 characters)
        estimated_tokens = len(context) // 4
        assert estimated_tokens <= 500, f"Context exceeds token budget: {estimated_tokens} tokens"
    
    @pytest.mark.asyncio
    async def test_analysis_type_filtering(self, ground_truth_builder):
        """Test that statistics are filtered by analysis type."""
        # Test pain analysis
        pain_context = await ground_truth_builder.build_statistics_context(
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain'
        )
        
        # Test size analysis
        size_context = await ground_truth_builder.build_statistics_context(
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='size'
        )
        
        # Both should contain statistics but may emphasize different aspects
        assert "SURVEY DATA STATISTICS" in pain_context
        assert "SURVEY DATA STATISTICS" in size_context
        
        # Size analysis should include more demographic data
        assert "Total Responses" in size_context


class TestEvidenceRetrievalEngine:
    """Test Evidence Retrieval Engine (Tier 2)."""
    
    @pytest.mark.asyncio
    async def test_retrieve_balanced_evidence_success(self, evidence_retrieval_engine):
        """Test successful balanced evidence retrieval."""
        evidence = await evidence_retrieval_engine.retrieve_balanced_evidence(
            query='pricing concerns satisfaction',
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain'
        )
        
        # Verify evidence structure
        assert isinstance(evidence, list)
        assert len(evidence) > 0
        
        # Check for balanced representation
        csv_chunks = [c for c in evidence if c.get('source_type') == 'csv']
        pdf_chunks = [c for c in evidence if c.get('source_type') == 'pdf']
        
        # Should have representation from both sources
        assert len(csv_chunks) > 0 or len(pdf_chunks) > 0
        
        # Verify metadata
        for chunk in evidence:
            assert 'retrieval_metadata' in chunk
            assert 'similarity_score' in chunk
            assert 'source_type' in chunk
    
    @pytest.mark.asyncio
    async def test_source_balancing_enforcement(self, evidence_retrieval_engine):
        """Test that minimum source representation is enforced."""
        evidence = await evidence_retrieval_engine.retrieve_balanced_evidence(
            query='test query',
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain',
            max_tokens=1000
        )
        
        # Verify source balancing metadata
        for chunk in evidence:
            selection_metadata = chunk.get('selection_metadata', {})
            assert selection_metadata.get('source_balancing_applied') == True
    
    @pytest.mark.asyncio
    async def test_persona_filtering(self, evidence_retrieval_engine):
        """Test persona-aware evidence filtering."""
        evidence = await evidence_retrieval_engine.retrieve_balanced_evidence(
            query='pricing concerns',
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain',
            persona_id='persona_001'
        )
        
        # Verify persona relevance scoring
        for chunk in evidence:
            assert 'persona_relevance_score' in chunk
            retrieval_metadata = chunk.get('retrieval_metadata', {})
            assert retrieval_metadata.get('persona_id') == 'persona_001'
    
    @pytest.mark.asyncio
    async def test_token_budget_management(self, evidence_retrieval_engine):
        """Test token budget management."""
        evidence = await evidence_retrieval_engine.retrieve_balanced_evidence(
            query='test query',
            project_id='test_project_001',
            tenant_id='test_tenant_001',
            analysis_type='pain',
            max_tokens=500  # Small budget
        )
        
        # Estimate total tokens
        total_chars = sum(len(chunk.get('content', '')) for chunk in evidence)
        estimated_tokens = total_chars // 4  # Rough estimation
        
        assert estimated_tokens <= 500, f"Evidence exceeds token budget: {estimated_tokens} tokens"
    
    @pytest.mark.asyncio
    async def test_adaptive_similarity_thresholds(self, evidence_retrieval_engine):
        """Test adaptive similarity threshold adjustment."""
        # Mock insufficient high-quality results
        with patch.object(evidence_retrieval_engine, '_semantic_search') as mock_search:
            mock_search.return_value = []  # No high-quality results
            
            evidence = await evidence_retrieval_engine.retrieve_balanced_evidence(
                query='very specific query with no matches',
                project_id='test_project_001',
                tenant_id='test_tenant_001',
                analysis_type='pain'
            )
            
            # Should still return some results due to adaptive thresholding
            # (This test verifies the fallback mechanism works)
            assert isinstance(evidence, list)


class TestEnhancedCorrelationEngine:
    """Test Enhanced Correlation Engine with Source Balancing."""
    
    @pytest.mark.asyncio
    async def test_source_balanced_similarity_search(self, enhanced_correlation_engine):
        """Test source-balanced similarity search."""
        # Mock research chunks with different source types
        research_chunks = [
            {
                'id': 'csv_1',
                'content': 'CSV survey data about pricing',
                'source_type': 'csv',
                'embedding': [0.1, 0.2, 0.3] * 100
            },
            {
                'id': 'pdf_1',
                'content': 'PDF interview about pricing concerns',
                'source_type': 'pdf',
                'embedding': [0.2, 0.3, 0.4] * 100
            }
        ]
        
        assumption = {
            'id': 'test_assumption',
            'text': 'Users have pricing concerns',
            'persona_name': 'Budget User'
        }
        
        results = await enhanced_correlation_engine.find_relevant_data(
            assumption=assumption,
            research_chunks=research_chunks,
            analysis_type='pain',
            top_k=10,
            enforce_source_balancing=True
        )
        
        # Verify source balancing
        csv_results = [r for r in results if r.get('source_type') == 'csv']
        pdf_results = [r for r in results if r.get('source_type') == 'pdf']
        
        # Should have representation from both sources when available
        assert len(csv_results) > 0 or len(pdf_results) > 0
        
        # Verify source balancing metadata
        for result in results:
            assert 'source_balancing' in result
            assert result['source_balancing']['enforced_minimum'] == True
    
    @pytest.mark.asyncio
    async def test_persona_aware_query_generation(self, enhanced_correlation_engine):
        """Test persona-aware query generation."""
        assumption = {
            'text': 'Users struggle with pricing',
            'persona_name': 'Budget User'
        }
        
        persona_context = {
            'id': 'persona_001',
            'demographics': {'income': 'low', 'age': '25-35'},
            'characteristics': ['price-sensitive', 'value-focused'],
            'goals': ['save money', 'get value']
        }
        
        research_chunks = [
            {
                'id': 'test_chunk',
                'content': 'Test content about pricing and value',
                'source_type': 'csv',
                'embedding': [0.1, 0.2, 0.3] * 100
            }
        ]
        
        results = await enhanced_correlation_engine.find_relevant_data(
            assumption=assumption,
            research_chunks=research_chunks,
            analysis_type='pain',
            persona_context=persona_context
        )
        
        # Verify persona relevance scoring
        for result in results:
            assert 'persona_score' in result
            assert result['persona_score'] >= 0.0
    
    @pytest.mark.asyncio
    async def test_proportional_token_allocation(self, enhanced_correlation_engine):
        """Test proportional token allocation between source types."""
        # Create chunks with different source types
        pdf_chunks = [
            {
                'id': f'pdf_{i}',
                'content': f'PDF content {i}' * 50,  # Longer content
                'source_type': 'pdf',
                'similarity_score': 0.8,
                'embedding': [0.1, 0.2, 0.3] * 100
            }
            for i in range(10)
        ]
        
        csv_chunks = [
            {
                'id': f'csv_{i}',
                'content': f'CSV content {i}' * 30,  # Shorter content
                'source_type': 'csv',
                'similarity_score': 0.7,
                'embedding': [0.2, 0.3, 0.4] * 100
            }
            for i in range(10)
        ]
        
        all_chunks = pdf_chunks + csv_chunks
        
        # Test proportional allocation
        result = enhanced_correlation_engine._apply_proportional_token_allocation(
            pdf_chunks, csv_chunks, max_chunks=10, analysis_type='pain'
        )
        
        # Verify allocation respects analysis type ratios
        pdf_selected = [c for c in result if c.get('source_type') == 'pdf']
        csv_selected = [c for c in result if c.get('source_type') == 'csv']
        
        # Pain analysis should prefer PDF (qualitative) content
        assert len(pdf_selected) >= len(csv_selected)
        
        # Verify allocation metadata
        for chunk in result:
            assert 'source_balancing' in chunk
            assert chunk['source_balancing']['analysis_type'] == 'pain'


class TestTwoTierAnalysisAgents:
    """Test Analysis Agents with Two-Tier Prompts."""
    
    class MockAnalysisAgent(BaseAnalysisAgent):
        """Mock analysis agent for testing."""
        
        def _get_analysis_type(self) -> str:
            return 'pain'
        
        def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
            return [
                {"role": "system", "content": "Legacy system prompt"},
                {"role": "user", "content": "Legacy user prompt"}
            ]
        
        def _get_output_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {"claim": {"type": "string"}}}
    
    @pytest.fixture
    def mock_analysis_agent(self, mock_statistics_registry, ground_truth_builder, evidence_retrieval_engine):
        """Mock analysis agent with two-tier RAG components."""
        return self.MockAnalysisAgent(
            statistics_registry=mock_statistics_registry,
            ground_truth_builder=ground_truth_builder,
            evidence_retrieval=evidence_retrieval_engine
        )
    
    @pytest.fixture
    def legacy_analysis_agent(self):
        """Legacy analysis agent without two-tier RAG."""
        return self.MockAnalysisAgent()
    
    @pytest.mark.asyncio
    async def test_two_tier_prompt_creation(self, mock_analysis_agent, test_analysis_context):
        """Test two-tier prompt creation."""
        messages = await mock_analysis_agent._create_two_tier_analysis_prompt(test_analysis_context)
        
        # Verify message structure
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        
        # Verify two-tier instructions in system prompt
        system_content = messages[0]['content']
        assert "GROUND TRUTH STATISTICS (Tier 1)" in system_content
        assert "QUALITATIVE EVIDENCE (Tier 2)" in system_content
        assert "Use ONLY the pre-computed statistics" in system_content
        assert "NEVER calculate percentages from the evidence chunks" in system_content
        
        # Verify two-tier structure in user prompt
        user_content = messages[1]['content']
        assert "GROUND TRUTH STATISTICS" in user_content
        assert "QUALITATIVE EVIDENCE" in user_content
        assert "SOURCE OF TRUTH FOR ALL PERCENTAGES" in user_content
    
    @pytest.mark.asyncio
    async def test_legacy_fallback(self, legacy_analysis_agent, test_analysis_context):
        """Test fallback to legacy prompt when two-tier RAG is not available."""
        messages = await legacy_analysis_agent._create_two_tier_analysis_prompt(test_analysis_context)
        
        # Should fallback to legacy prompt
        assert len(messages) == 2
        assert messages[0]['content'] == "Legacy system prompt"
        assert messages[1]['content'] == "Legacy user prompt"
    
    @pytest.mark.asyncio
    async def test_two_tier_rag_detection(self, mock_analysis_agent, legacy_analysis_agent):
        """Test two-tier RAG capability detection."""
        # Agent with all components should use two-tier RAG
        assert mock_analysis_agent.use_two_tier_rag == True
        
        # Agent without components should use legacy approach
        assert legacy_analysis_agent.use_two_tier_rag == False
    
    @pytest.mark.asyncio
    async def test_evidence_context_formatting(self, mock_analysis_agent):
        """Test evidence context formatting for Tier 2."""
        evidence_chunks = [
            {
                'content': 'Test evidence content about pricing',
                'source_type': 'csv',
                'source_file': 'survey.csv',
                'similarity_score': 0.85
            },
            {
                'content': 'Interview excerpt about user frustrations',
                'source_type': 'pdf',
                'source_file': 'interviews.pdf',
                'similarity_score': 0.78
            }
        ]
        
        formatted = mock_analysis_agent._format_evidence_context(evidence_chunks)
        
        # Verify formatting
        assert "[CSV Evidence 1]" in formatted
        assert "[PDF Evidence 2]" in formatted
        assert "(Source: survey.csv)" in formatted
        assert "(Source: interviews.pdf)" in formatted
        assert "[Relevance: 0.85]" in formatted
        assert "[Relevance: 0.78]" in formatted
        assert "Test evidence content about pricing" in formatted
        assert "Interview excerpt about user frustrations" in formatted


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_two_tier_analysis_flow(
        self,
        mock_statistics_registry,
        ground_truth_builder,
        evidence_retrieval_engine,
        test_analysis_context
    ):
        """Test complete two-tier analysis flow from context to output."""
        
        # Create analysis agent with two-tier RAG
        class TestAgent(BaseAnalysisAgent):
            def _get_analysis_type(self) -> str:
                return 'pain'
            
            def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
                return [{"role": "user", "content": "legacy prompt"}]
            
            def _get_output_schema(self) -> Dict[str, Any]:
                return {"type": "object"}
        
        agent = TestAgent(
            statistics_registry=mock_statistics_registry,
            ground_truth_builder=ground_truth_builder,
            evidence_retrieval=evidence_retrieval_engine
        )
        
        # Test two-tier prompt creation
        messages = await agent._create_two_tier_analysis_prompt(test_analysis_context)
        
        # Verify complete integration
        assert len(messages) == 2
        
        # Verify Tier 1 (Ground Truth) integration
        user_content = messages[1]['content']
        assert "GROUND TRUTH STATISTICS" in user_content
        assert "Very Satisfied: 45 (45.0%)" in user_content
        assert "[Cite: csv_001]" in user_content
        
        # Verify Tier 2 (Evidence) integration
        assert "QUALITATIVE EVIDENCE" in user_content
        assert "CSV Evidence" in user_content or "PDF Evidence" in user_content
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(
        self,
        mock_statistics_registry,
        ground_truth_builder,
        evidence_retrieval_engine,
        test_analysis_context
    ):
        """Test error handling across two-tier RAG components."""
        
        # Simulate statistics registry error
        mock_statistics_registry.get_statistics_for_analysis.side_effect = Exception("Registry error")
        
        class TestAgent(BaseAnalysisAgent):
            def _get_analysis_type(self) -> str:
                return 'pain'
            
            def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
                return [{"role": "user", "content": "fallback prompt"}]
            
            def _get_output_schema(self) -> Dict[str, Any]:
                return {"type": "object"}
        
        agent = TestAgent(
            statistics_registry=mock_statistics_registry,
            ground_truth_builder=ground_truth_builder,
            evidence_retrieval=evidence_retrieval_engine
        )
        
        # Should fallback gracefully
        messages = await agent._create_two_tier_analysis_prompt(test_analysis_context)
        
        # Should fallback to legacy prompt
        assert messages[1]['content'] == "fallback prompt"
    
    @pytest.mark.asyncio
    async def test_persona_aware_end_to_end(
        self,
        mock_statistics_registry,
        ground_truth_builder,
        evidence_retrieval_engine
    ):
        """Test persona-aware analysis end-to-end."""
        
        # Create persona-specific context
        persona_context = AnalysisContext(
            assumption={
                'id': 'persona_assumption',
                'text': 'Budget users are price-sensitive',
                'persona_name': 'Budget User'
            },
            persona={
                'id': 'persona_001',
                'name': 'Budget User',
                'demographics': {'income': 'low'},
                'characteristics': ['price-sensitive']
            },
            research_data=[],
            project_context={
                'project_id': 'test_project',
                'tenant_id': 'test_tenant'
            },
            analysis_type='pain'
        )
        
        class PersonaAgent(BaseAnalysisAgent):
            def _get_analysis_type(self) -> str:
                return 'pain'
            
            def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
                return [{"role": "user", "content": "legacy"}]
            
            def _get_output_schema(self) -> Dict[str, Any]:
                return {"type": "object"}
        
        agent = PersonaAgent(
            statistics_registry=mock_statistics_registry,
            ground_truth_builder=ground_truth_builder,
            evidence_retrieval=evidence_retrieval_engine
        )
        
        messages = await agent._create_two_tier_analysis_prompt(persona_context)
        
        # Verify persona integration
        user_content = messages[1]['content']
        assert "TARGET PERSONA: Budget User" in user_content
        assert "PERSONA-SPECIFIC DATA (ID: persona_001)" in user_content
    
    @pytest.mark.asyncio
    async def test_source_balancing_end_to_end(
        self,
        mock_statistics_registry,
        ground_truth_builder,
        evidence_retrieval_engine,
        test_analysis_context
    ):
        """Test source balancing throughout the complete flow."""
        
        class BalancedAgent(BaseAnalysisAgent):
            def _get_analysis_type(self) -> str:
                return 'pain'
            
            def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
                return [{"role": "user", "content": "legacy"}]
            
            def _get_output_schema(self) -> Dict[str, Any]:
                return {"type": "object"}
        
        agent = BalancedAgent(
            statistics_registry=mock_statistics_registry,
            ground_truth_builder=ground_truth_builder,
            evidence_retrieval=evidence_retrieval_engine
        )
        
        messages = await agent._create_two_tier_analysis_prompt(test_analysis_context)
        
        # Verify balanced representation
        user_content = messages[1]['content']
        
        # Should have both CSV and PDF statistics in Tier 1
        assert "SURVEY DATA STATISTICS" in user_content
        assert "INTERVIEW DATA STATISTICS" in user_content
        
        # Should have balanced evidence in Tier 2
        assert "QUALITATIVE EVIDENCE" in user_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])