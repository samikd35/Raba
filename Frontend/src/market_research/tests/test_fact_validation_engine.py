"""
Tests for Fact Validation Engine

Comprehensive test suite for the fact validation engine including
claim extraction, validation against statistics registry, and confidence adjustment.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, Any, List

from ..services.fact_validation_engine import (
    FactValidationEngine,
    QuantitativeClaim,
    ValidationResult
)


class TestFactValidationEngine:
    """Test suite for FactValidationEngine"""
    
    @pytest.fixture
    def validation_engine(self):
        """Create a fact validation engine instance"""
        return FactValidationEngine()
    
    @pytest.fixture
    def sample_statistics_registry(self):
        """Create sample statistics registry for testing"""
        return {
            "csv_statistics": {
                "metadata": {
                    "filename": "survey_responses.csv",
                    "total_rows": 1000
                },
                "categorical_distributions": {
                    "age_group": {
                        "distribution": [
                            {
                                "value": "25-34",
                                "count": 350,
                                "percentage": 35.0,
                                "citation_id": "csv_age_25_34"
                            },
                            {
                                "value": "35-44",
                                "count": 300,
                                "percentage": 30.0,
                                "citation_id": "csv_age_35_44"
                            }
                        ]
                    },
                    "satisfaction": {
                        "distribution": [
                            {
                                "value": "satisfied",
                                "count": 720,
                                "percentage": 72.0,
                                "citation_id": "csv_satisfaction_satisfied"
                            },
                            {
                                "value": "dissatisfied",
                                "count": 280,
                                "percentage": 28.0,
                                "citation_id": "csv_satisfaction_dissatisfied"
                            }
                        ]
                    }
                }
            },
            "pdf_statistics": {
                "metadata": {
                    "filename": "interviews.pdf",
                    "total_pages": 50
                },
                "themes": {
                    "pricing_concerns": {
                        "frequency": 15,
                        "percentage": 75.0,
                        "citation_id": "pdf_theme_pricing"
                    },
                    "usability_issues": {
                        "frequency": 12,
                        "percentage": 60.0,
                        "citation_id": "pdf_theme_usability"
                    }
                }
            }
        }
    
    def test_extract_percentage_claims(self, validation_engine):
        """Test extraction of percentage claims from AI response"""
        ai_response = """
        Based on the survey data, 72% of respondents reported satisfaction with the product.
        Additionally, 35% of users fall into the 25-34 age group.
        The analysis shows that 15 out of 20 participants mentioned pricing concerns.
        """
        
        claims = validation_engine.extract_quantitative_claims(ai_response)
        
        # Should extract percentage claims
        percentage_claims = [c for c in claims if c.percentage is not None]
        assert len(percentage_claims) >= 2
        
        # Check specific percentages
        percentages = [c.percentage for c in percentage_claims]
        assert 72.0 in percentages
        assert 35.0 in percentages
        
        # Check fraction claim (15 out of 20 = 75%)
        fraction_claims = [c for c in claims if "out of" in c.context.lower()]
        assert len(fraction_claims) >= 1
    
    def test_extract_count_claims(self, validation_engine):
        """Test extraction of count-based claims"""
        ai_response = """
        The study included 1000 respondents from various demographics.
        350 participants were in the 25-34 age group.
        """
        
        claims = validation_engine.extract_quantitative_claims(ai_response)
        
        # Should extract count claims
        count_claims = [c for c in claims if c.count is not None]
        assert len(count_claims) >= 2
        
        # Check specific counts
        counts = [c.count for c in count_claims]
        assert 1000 in counts
        assert 350 in counts
    
    def test_extract_frequency_claims(self, validation_engine):
        """Test extraction of frequency/qualitative claims"""
        ai_response = """
        Most users mentioned pricing as a concern.
        Many participants frequently use the mobile app.
        Few respondents rarely encounter technical issues.
        """
        
        claims = validation_engine.extract_quantitative_claims(ai_response)
        
        # Should extract frequency claims
        frequency_claims = [c for c in claims if c.percentage is None and c.count is None]
        assert len(frequency_claims) >= 3
        
        # Check for frequency keywords
        contexts = [c.context.lower() for c in frequency_claims]
        assert any("most" in context for context in contexts)
        assert any("many" in context for context in contexts)
        assert any("few" in context for context in contexts)
    
    def test_validate_accurate_percentage_claims(self, validation_engine, sample_statistics_registry):
        """Test validation of accurate percentage claims"""
        # Create claims that match the registry
        claims = [
            QuantitativeClaim(
                claim_text="72% of respondents reported satisfaction",
                percentage=72.0,
                context="satisfaction respondents",
                sample_reference="respondents"
            ),
            QuantitativeClaim(
                claim_text="35% are in 25-34 age group",
                percentage=35.0,
                context="25-34 age group",
                sample_reference="users"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should have high fact-check score
        assert validation_results["fact_check_score"] >= 0.8
        
        # Should have valid claims
        assert len(validation_results["valid_claims"]) >= 2
        assert len(validation_results["unsupported_claims"]) == 0
    
    def test_validate_inaccurate_percentage_claims(self, validation_engine, sample_statistics_registry):
        """Test validation of inaccurate percentage claims"""
        # Create claims that don't match the registry
        claims = [
            QuantitativeClaim(
                claim_text="90% of respondents reported satisfaction",
                percentage=90.0,
                context="satisfaction respondents",
                sample_reference="respondents"
            ),
            QuantitativeClaim(
                claim_text="50% are in 25-34 age group",
                percentage=50.0,
                context="25-34 age group",
                sample_reference="users"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should have low fact-check score
        assert validation_results["fact_check_score"] < 0.5
        
        # Should have questionable or unsupported claims
        total_problematic = len(validation_results["questionable_claims"]) + len(validation_results["unsupported_claims"])
        assert total_problematic >= 2
    
    def test_validate_count_claims(self, validation_engine, sample_statistics_registry):
        """Test validation of count claims"""
        claims = [
            QuantitativeClaim(
                claim_text="350 respondents in 25-34 age group",
                count=350,
                context="25-34 age group respondents",
                sample_reference="respondents"
            ),
            QuantitativeClaim(
                claim_text="720 satisfied participants",
                count=720,
                context="satisfied participants",
                sample_reference="participants"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should validate successfully
        assert validation_results["fact_check_score"] >= 0.8
        assert len(validation_results["valid_claims"]) >= 2
    
    def test_validate_pdf_theme_claims(self, validation_engine, sample_statistics_registry):
        """Test validation of PDF theme-based claims"""
        claims = [
            QuantitativeClaim(
                claim_text="75% mentioned pricing concerns",
                percentage=75.0,
                context="pricing concerns mentioned",
                sample_reference="participants"
            ),
            QuantitativeClaim(
                claim_text="60% had usability issues",
                percentage=60.0,
                context="usability issues",
                sample_reference="users"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should validate against PDF statistics
        assert validation_results["fact_check_score"] >= 0.8
        assert len(validation_results["valid_claims"]) >= 2
    
    def test_confidence_score_adjustment(self, validation_engine):
        """Test confidence score adjustment based on fact-checking"""
        # Test high validation score (should boost confidence)
        adjusted = validation_engine.adjust_confidence_score(0.7, 0.9)
        assert adjusted >= 0.7  # Should maintain or boost
        
        # Test medium validation score (should maintain)
        adjusted = validation_engine.adjust_confidence_score(0.7, 0.7)
        assert 0.6 <= adjusted <= 0.8  # Should be around original
        
        # Test low validation score (should reduce)
        adjusted = validation_engine.adjust_confidence_score(0.7, 0.3)
        assert adjusted < 0.5  # Should be significantly reduced
        
        # Test very low validation score (should heavily reduce)
        adjusted = validation_engine.adjust_confidence_score(0.8, 0.1)
        assert adjusted < 0.4  # Should be heavily penalized
    
    def test_confidence_adjustment_with_validation_details(self, validation_engine):
        """Test confidence adjustment with detailed validation results"""
        validation_details = {
            "unsupported_claims": ["90% satisfaction", "80% retention"],
            "questionable_claims": ["45% age group"],
            "total_claims": 5
        }
        
        # Many unsupported claims should heavily reduce confidence
        adjusted = validation_engine.adjust_confidence_score(0.8, 0.6, validation_details)
        assert adjusted < 0.5
    
    def test_empty_claims_validation(self, validation_engine, sample_statistics_registry):
        """Test validation with no claims extracted"""
        claims = []
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should return perfect score when no claims to validate
        assert validation_results["fact_check_score"] == 1.0
        assert validation_results["total_claims"] == 0
        assert len(validation_results["valid_claims"]) == 0
    
    def test_empty_statistics_registry(self, validation_engine):
        """Test validation against empty statistics registry"""
        claims = [
            QuantitativeClaim(
                claim_text="72% satisfaction",
                percentage=72.0,
                context="satisfaction",
                sample_reference="respondents"
            )
        ]
        
        empty_registry = {
            "csv_statistics": {"categorical_distributions": {}},
            "pdf_statistics": {"themes": {}}
        }
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, empty_registry
        )
        
        # Should mark claims as unsupported
        assert len(validation_results["unsupported_claims"]) >= 1
        assert validation_results["fact_check_score"] < 0.5
    
    def test_validation_report_generation(self, validation_engine, sample_statistics_registry):
        """Test generation of human-readable validation reports"""
        claims = [
            QuantitativeClaim(
                claim_text="72% satisfaction",
                percentage=72.0,
                context="satisfaction",
                sample_reference="respondents"
            ),
            QuantitativeClaim(
                claim_text="90% retention",  # Inaccurate claim
                percentage=90.0,
                context="retention",
                sample_reference="users"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Generate report
        report = validation_engine.generate_validation_report(validation_results)
        
        # Should contain key sections
        assert "FACT VALIDATION REPORT" in report
        assert "Overall Fact-Check Score" in report
        assert "Total Claims Analyzed" in report
        
        # Should include claim details
        if validation_results["valid_claims"]:
            assert "VALIDATED CLAIMS" in report
        if validation_results["unsupported_claims"]:
            assert "UNSUPPORTED CLAIMS" in report
    
    def test_context_similarity_calculation(self, validation_engine):
        """Test context similarity calculation"""
        # Exact match
        similarity = validation_engine._calculate_context_similarity(
            "satisfaction respondents", "satisfaction respondents"
        )
        assert similarity == 1.0
        
        # Partial match
        similarity = validation_engine._calculate_context_similarity(
            "satisfaction survey respondents", "satisfaction respondents"
        )
        assert 0.5 < similarity < 1.0
        
        # No match
        similarity = validation_engine._calculate_context_similarity(
            "pricing concerns", "satisfaction respondents"
        )
        assert similarity < 0.3
        
        # Empty contexts
        similarity = validation_engine._calculate_context_similarity("", "test")
        assert similarity == 0.0
    
    def test_error_handling_in_validation(self, validation_engine):
        """Test error handling during validation process"""
        # Test with malformed statistics registry
        malformed_registry = {
            "csv_statistics": "invalid_structure",
            "pdf_statistics": None
        }
        
        claims = [
            QuantitativeClaim(
                claim_text="72% satisfaction",
                percentage=72.0,
                context="satisfaction",
                sample_reference="respondents"
            )
        ]
        
        # Should not crash and return error results
        validation_results = validation_engine.validate_claims_against_registry(
            claims, malformed_registry
        )
        
        assert "error" in validation_results
        assert validation_results["fact_check_score"] == 0.0
    
    def test_tolerance_levels(self, validation_engine, sample_statistics_registry):
        """Test percentage tolerance levels in validation"""
        # Within tolerance (72% vs 72.5%)
        claims = [
            QuantitativeClaim(
                claim_text="72.5% satisfaction",
                percentage=72.5,
                context="satisfaction respondents",
                sample_reference="respondents"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should be valid within tolerance
        assert len(validation_results["valid_claims"]) >= 1
        
        # Outside tolerance (72% vs 80%)
        claims = [
            QuantitativeClaim(
                claim_text="80% satisfaction",
                percentage=80.0,
                context="satisfaction respondents",
                sample_reference="respondents"
            )
        ]
        
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Should be questionable outside tolerance
        assert len(validation_results["questionable_claims"]) >= 1


class TestValidationIntegration:
    """Integration tests for fact validation with analysis agents"""
    
    @pytest.fixture
    def mock_analysis_output(self):
        """Mock analysis output for testing"""
        return {
            "content": """
            {
                "claim": "Based on survey data, 72% of respondents are satisfied with the product. The 25-34 age group represents 35% of users.",
                "accuracy_level": "high",
                "supporting_evidence": ["Survey responses show clear satisfaction patterns"],
                "confidence_score": 0.85
            }
            """
        }
    
    def test_end_to_end_validation_workflow(self, mock_analysis_output, sample_statistics_registry):
        """Test complete validation workflow from AI response to adjusted confidence"""
        validation_engine = FactValidationEngine()
        
        # Extract claims from AI response
        ai_response = mock_analysis_output["content"]
        claims = validation_engine.extract_quantitative_claims(ai_response)
        
        # Validate against registry
        validation_results = validation_engine.validate_claims_against_registry(
            claims, sample_statistics_registry
        )
        
        # Adjust confidence
        original_confidence = 0.85
        adjusted_confidence = validation_engine.adjust_confidence_score(
            original_confidence, validation_results["fact_check_score"], validation_results
        )
        
        # Should complete successfully
        assert validation_results["fact_check_score"] > 0.0
        assert adjusted_confidence >= 0.0
        assert "validated_at" in validation_results
    
    @pytest.mark.asyncio
    async def test_validation_with_error_handling(self):
        """Test validation with error handling scenarios"""
        validation_engine = FactValidationEngine()
        
        # Test with invalid AI response
        invalid_response = "This is not a valid JSON response with claims"
        claims = validation_engine.extract_quantitative_claims(invalid_response)
        
        # Should handle gracefully
        assert isinstance(claims, list)
        
        # Test with None registry
        validation_results = validation_engine.validate_claims_against_registry(claims, None)
        
        # Should return error results
        assert "error" in validation_results
        assert validation_results["fact_check_score"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])