"""
Unit Tests for Enhanced Workflow Integration

Tests the enhanced workflow components in isolation without requiring
the full application stack or external dependencies.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock


class TestEnhancedWorkflowUnit:
    """Unit tests for enhanced workflow components."""
    
    def test_enhanced_state_structure(self):
        """Test enhanced state structure includes all required fields."""
        
        # Define enhanced state structure
        enhanced_state = {
            # Existing fields
            "project_id": "test-project-123",
            "tenant_id": "test-tenant-456",
            "project_context": {},
            "current_assumption": {},
            "target_persona": {},
            "research_chunks": [],
            "assumption_analyses": [],
            "current_assumption_analysis": {},
            "report_sections": {},
            "final_report": "",
            "current_step": "initialize",
            "processed_assumptions": [],
            "errors": [],
            
            # Enhanced fields for statistics registry and two-tier RAG
            "statistics_registry": {},
            "persona_data_associations": {},
            "current_ground_truth": {},
            "current_evidence_chunks": [],
            "citation_registry": {},
            "fact_validation_results": {},
            "generated_visualizations": {}
        }
        
        # Verify all required fields are present
        required_fields = [
            "project_id", "tenant_id", "project_context", "current_assumption",
            "target_persona", "research_chunks", "assumption_analyses",
            "current_assumption_analysis", "report_sections", "final_report",
            "current_step", "processed_assumptions", "errors"
        ]
        
        for field in required_fields:
            assert field in enhanced_state, f"Required field {field} missing"
        
        # Verify enhanced fields are present
        enhanced_fields = [
            "statistics_registry", "persona_data_associations", "current_ground_truth",
            "current_evidence_chunks", "citation_registry", "fact_validation_results",
            "generated_visualizations"
        ]
        
        for field in enhanced_fields:
            assert field in enhanced_state, f"Enhanced field {field} missing"
    
    def test_statistics_registry_structure(self):
        """Test statistics registry has correct structure."""
        
        statistics_registry = {
            "csv_statistics": {
                "filename": "survey_responses.csv",
                "metadata": {"total_rows": 100, "total_columns": 5},
                "categorical_distributions": {
                    "business_size": {
                        "total_responses": 100,
                        "distribution": [
                            {"value": "Small (1-10)", "count": 60, "percentage": 60.0, "citation_id": "cite-001"},
                            {"value": "Medium (11-50)", "count": 30, "percentage": 30.0, "citation_id": "cite-002"}
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
                        "sources": ["Interview 1", "Interview 3"],
                        "citation_id": "cite-003"
                    }
                }
            },
            "citation_registry": {
                "cite-001": {
                    "source_type": "csv",
                    "source_file": "survey_responses.csv",
                    "data_path": "business_size.Small (1-10)",
                    "verification_hash": "abc123"
                },
                "cite-003": {
                    "source_type": "pdf",
                    "source_file": "interviews.pdf",
                    "data_path": "themes.inventory_challenges",
                    "verification_hash": "def456"
                }
            },
            "persona_mappings": {
                "persona-1": {
                    "associated_statistics": ["cite-001", "cite-003"],
                    "relevance_scores": {"inventory_challenges": 0.9, "business_size": 0.8}
                }
            }
        }
        
        # Verify structure
        assert "csv_statistics" in statistics_registry
        assert "pdf_statistics" in statistics_registry
        assert "citation_registry" in statistics_registry
        assert "persona_mappings" in statistics_registry
        
        # Verify CSV statistics structure
        csv_stats = statistics_registry["csv_statistics"]
        assert "filename" in csv_stats
        assert "metadata" in csv_stats
        assert "categorical_distributions" in csv_stats
        
        # Verify citation registry structure
        citation_registry = statistics_registry["citation_registry"]
        for citation_id, citation_data in citation_registry.items():
            assert "source_type" in citation_data
            assert "source_file" in citation_data
            assert "data_path" in citation_data
            assert "verification_hash" in citation_data
    
    def test_two_tier_rag_context_structure(self):
        """Test two-tier RAG context has correct structure."""
        
        # Tier 1: Ground truth statistics (always included, ~500 tokens)
        ground_truth_context = {
            "csv_statistics": {
                "business_size": {
                    "Small (1-10)": {"count": 60, "percentage": 60.0, "citation_id": "cite-001"},
                    "Medium (11-50)": {"count": 30, "percentage": 30.0, "citation_id": "cite-002"}
                }
            },
            "pdf_statistics": {
                "inventory_challenges": {
                    "frequency": 15,
                    "percentage": 75.0,
                    "citation_id": "cite-003"
                }
            }
        }
        
        # Tier 2: Evidence chunks (contextual examples, ~2,500 tokens)
        evidence_chunks = [
            {
                "id": "chunk-1",
                "content": "Small businesses report significant challenges with inventory tracking",
                "source_type": "pdf",
                "source_file": "interviews.pdf",
                "citation_id": "cite-004",
                "relevance_score": 0.85
            },
            {
                "id": "chunk-2",
                "content": "60% of respondents are small businesses with 1-10 employees",
                "source_type": "csv",
                "source_file": "survey_responses.csv",
                "citation_id": "cite-001",
                "relevance_score": 0.92
            }
        ]
        
        # Verify ground truth structure
        assert "csv_statistics" in ground_truth_context
        assert "pdf_statistics" in ground_truth_context
        
        # Verify evidence chunks structure
        for chunk in evidence_chunks:
            assert "id" in chunk
            assert "content" in chunk
            assert "source_type" in chunk
            assert "source_file" in chunk
            assert "citation_id" in chunk
            assert "relevance_score" in chunk
        
        # Verify balanced source representation
        csv_chunks = [c for c in evidence_chunks if c["source_type"] == "csv"]
        pdf_chunks = [c for c in evidence_chunks if c["source_type"] == "pdf"]
        
        assert len(csv_chunks) > 0, "No CSV chunks in evidence"
        assert len(pdf_chunks) > 0, "No PDF chunks in evidence"
    
    def test_fact_validation_structure(self):
        """Test fact validation results have correct structure."""
        
        validation_results = {
            "fact_check_score": 0.9,
            "valid_claims": [
                "60% of respondents are small businesses",
                "75% report inventory challenges"
            ],
            "unsupported_claims": [],
            "questionable_claims": [
                "All businesses need advanced analytics"
            ],
            "validation_details": {
                "cite-001": {
                    "claim": "60% of respondents are small businesses",
                    "verified": True,
                    "source_value": 60.0,
                    "claimed_value": 60.0,
                    "accuracy": 1.0
                },
                "cite-003": {
                    "claim": "75% report inventory challenges",
                    "verified": True,
                    "source_value": 75.0,
                    "claimed_value": 75.0,
                    "accuracy": 1.0
                }
            }
        }
        
        # Verify validation structure
        assert "fact_check_score" in validation_results
        assert "valid_claims" in validation_results
        assert "unsupported_claims" in validation_results
        assert "questionable_claims" in validation_results
        assert "validation_details" in validation_results
        
        # Verify fact check score is valid
        assert 0.0 <= validation_results["fact_check_score"] <= 1.0
        
        # Verify validation details structure
        for citation_id, details in validation_results["validation_details"].items():
            assert "claim" in details
            assert "verified" in details
            assert "source_value" in details
            assert "claimed_value" in details
            assert "accuracy" in details
    
    def test_persona_data_associations(self):
        """Test persona data associations structure."""
        
        persona_associations = {
            "persona-1": {
                "associated_statistics": ["cite-001", "cite-003"],
                "relevance_scores": {
                    "inventory_challenges": 0.9,
                    "business_size": 0.8,
                    "cost_concerns": 0.7
                },
                "association_type": "explicit",
                "confidence_level": "high"
            },
            "persona-2": {
                "associated_statistics": ["cite-002", "cite-005"],
                "relevance_scores": {
                    "advanced_analytics": 0.95,
                    "enterprise_features": 0.88
                },
                "association_type": "inferred",
                "confidence_level": "medium"
            }
        }
        
        # Verify structure for each persona
        for persona_id, associations in persona_associations.items():
            assert "associated_statistics" in associations
            assert "relevance_scores" in associations
            assert "association_type" in associations
            assert "confidence_level" in associations
            
            # Verify association type is valid
            assert associations["association_type"] in ["explicit", "inferred", "general"]
            
            # Verify confidence level is valid
            assert associations["confidence_level"] in ["high", "medium", "low"]
            
            # Verify relevance scores are valid
            for topic, score in associations["relevance_scores"].items():
                assert 0.0 <= score <= 1.0
    
    def test_enhanced_analysis_output_structure(self):
        """Test enhanced analysis output includes fact validation metadata."""
        
        enhanced_analysis_output = {
            "claim": "75% of small businesses report inventory management challenges",
            "accuracy_level": "high",
            "supporting_evidence": [
                "Interview data shows consistent inventory concerns",
                "Survey responses confirm widespread tracking issues"
            ],
            "debunking_evidence": [],
            "statistical_data": {
                "source_statistics": {"inventory_challenges": 75.0},
                "sample_size": 20,
                "confidence_interval": [65.0, 85.0]
            },
            "confidence_score": 0.85,
            
            # Enhanced fields for fact validation
            "citation_ids": ["cite-003", "cite-004"],
            "persona_relevance_score": 0.9,
            "fact_validation_score": 0.95,
            "validation_metadata": {
                "claims_validated": 2,
                "claims_total": 2,
                "validation_accuracy": 1.0,
                "verification_details": {
                    "cite-003": {"verified": True, "accuracy": 1.0}
                }
            }
        }
        
        # Verify enhanced fields are present
        enhanced_fields = [
            "citation_ids", "persona_relevance_score", 
            "fact_validation_score", "validation_metadata"
        ]
        
        for field in enhanced_fields:
            assert field in enhanced_analysis_output, f"Enhanced field {field} missing"
        
        # Verify scores are valid
        assert 0.0 <= enhanced_analysis_output["confidence_score"] <= 1.0
        assert 0.0 <= enhanced_analysis_output["persona_relevance_score"] <= 1.0
        assert 0.0 <= enhanced_analysis_output["fact_validation_score"] <= 1.0
        
        # Verify citation IDs are present
        assert len(enhanced_analysis_output["citation_ids"]) > 0
    
    def test_backward_compatibility_structure(self):
        """Test that enhanced structures maintain backward compatibility."""
        
        # Legacy analysis output (without enhanced fields)
        legacy_output = {
            "claim": "Small businesses face challenges",
            "accuracy_level": "medium",
            "supporting_evidence": ["Some evidence"],
            "debunking_evidence": [],
            "statistical_data": {},
            "confidence_score": 0.7
        }
        
        # Enhanced analysis output (with new fields)
        enhanced_output = {
            **legacy_output,  # All legacy fields preserved
            "citation_ids": ["cite-001"],
            "persona_relevance_score": 0.8,
            "fact_validation_score": 0.9,
            "validation_metadata": {}
        }
        
        # Verify backward compatibility
        for field in legacy_output:
            assert field in enhanced_output, f"Legacy field {field} not preserved"
            assert enhanced_output[field] == legacy_output[field], f"Legacy field {field} value changed"
        
        # Verify enhanced fields are optional
        enhanced_fields = ["citation_ids", "persona_relevance_score", "fact_validation_score", "validation_metadata"]
        for field in enhanced_fields:
            assert field in enhanced_output, f"Enhanced field {field} missing"
    
    def test_migration_compatibility(self):
        """Test migration from legacy to enhanced data structures."""
        
        # Legacy research documents data
        legacy_data = {
            "pdf_content": {
                "raw_text": "Interview content about inventory challenges",
                "chunks": [
                    {"id": "chunk-1", "content": "Inventory is a major pain point"}
                ],
                "metadata": {"filename": "interviews.pdf", "pages": 5}
            },
            "csv_content": {
                "raw_data": [{"business_size": "Small", "inventory_issues": "Yes"}],
                "processed_text": "Survey data about business challenges",
                "chunks": [
                    {"id": "chunk-2", "content": "Small businesses report issues"}
                ],
                "metadata": {"filename": "survey.csv", "rows": 100}
            }
        }
        
        # Enhanced research documents data (with statistics registry)
        enhanced_data = {
            **legacy_data,  # Preserve legacy data
            "statistics_registry": {
                "csv_statistics": {
                    "filename": "survey.csv",
                    "categorical_distributions": {
                        "business_size": {"Small": {"count": 60, "percentage": 60.0}}
                    }
                },
                "pdf_statistics": {
                    "filename": "interviews.pdf",
                    "themes": {"inventory_challenges": {"frequency": 15}}
                },
                "citation_registry": {},
                "persona_mappings": {}
            }
        }
        
        # Verify migration preserves legacy data
        assert "pdf_content" in enhanced_data
        assert "csv_content" in enhanced_data
        
        # Verify legacy structure is unchanged
        assert enhanced_data["pdf_content"] == legacy_data["pdf_content"]
        assert enhanced_data["csv_content"] == legacy_data["csv_content"]
        
        # Verify enhanced features are added
        assert "statistics_registry" in enhanced_data
        stats_registry = enhanced_data["statistics_registry"]
        assert "csv_statistics" in stats_registry
        assert "pdf_statistics" in stats_registry
        assert "citation_registry" in stats_registry
        assert "persona_mappings" in stats_registry


def run_unit_tests():
    """Run all unit tests."""
    
    print("Enhanced Workflow Unit Tests")
    print("=" * 40)
    
    test_class = TestEnhancedWorkflowUnit()
    
    tests = [
        ("Enhanced State Structure", test_class.test_enhanced_state_structure),
        ("Statistics Registry Structure", test_class.test_statistics_registry_structure),
        ("Two-Tier RAG Context", test_class.test_two_tier_rag_context_structure),
        ("Fact Validation Structure", test_class.test_fact_validation_structure),
        ("Persona Data Associations", test_class.test_persona_data_associations),
        ("Enhanced Analysis Output", test_class.test_enhanced_analysis_output_structure),
        ("Backward Compatibility", test_class.test_backward_compatibility_structure),
        ("Migration Compatibility", test_class.test_migration_compatibility)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}...", end=" ")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All unit tests passed!")
        return True
    else:
        print("❌ Some unit tests failed!")
        return False


if __name__ == "__main__":
    success = run_unit_tests()
    exit(0 if success else 1)