"""
Unit Tests for AMRG Enums

Run with: pytest src/mvp/mvp_req/tests/unit_enums.py -v
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestTemplateCode:
    """Tests for TemplateCode enum."""
    
    def test_all_codes_present(self):
        """Verify all expected template codes exist."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        expected = ["A1", "A2", "A3", "A4", "A5", "B1", "C1", "C2"]
        actual = [tc.value for tc in TemplateCode]
        
        assert sorted(expected) == sorted(actual)
    
    def test_get_category(self):
        """Test get_category() class method."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        # Digital & Software Products
        assert "Digital" in TemplateCode.get_category(TemplateCode.A1)
        assert "Digital" in TemplateCode.get_category(TemplateCode.A5)
        
        # Services
        assert "Services" in TemplateCode.get_category(TemplateCode.B1)
        
        # Physical Products
        assert "Physical" in TemplateCode.get_category(TemplateCode.C1)
        assert "Physical" in TemplateCode.get_category(TemplateCode.C2)
    
    def test_get_display_name(self):
        """Test get_display_name() class method."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        assert "SaaS" in TemplateCode.get_display_name(TemplateCode.A1)
        assert "Marketplace" in TemplateCode.get_display_name(TemplateCode.A3)
        assert "Fintech" in TemplateCode.get_display_name(TemplateCode.A5)
        assert "Hardware" in TemplateCode.get_display_name(TemplateCode.C2)


class TestResearchMode:
    """Tests for ResearchMode enum."""
    
    def test_research_modes(self):
        """Verify research mode values."""
        from src.mvp.mvp_req.models.enums import ResearchMode
        
        expected = ["off", "auto", "on"]
        actual = [rm.value for rm in ResearchMode]
        
        assert sorted(expected) == sorted(actual)


class TestRunStatus:
    """Tests for RunStatus enum."""
    
    def test_run_statuses(self):
        """Verify run status values."""
        from src.mvp.mvp_req.models.enums import RunStatus
        
        expected = ["created", "awaiting_answers", "running", "completed", "failed"]
        actual = [rs.value for rs in RunStatus]
        
        assert sorted(expected) == sorted(actual)
    
    def test_terminal_statuses(self):
        """Test identification of terminal statuses."""
        from src.mvp.mvp_req.models.enums import RunStatus
        
        # Terminal statuses are COMPLETED and FAILED
        terminal = [RunStatus.COMPLETED, RunStatus.FAILED]
        non_terminal = [RunStatus.CREATED, RunStatus.AWAITING_ANSWERS, RunStatus.RUNNING]
        
        for status in terminal:
            assert status.value in ["completed", "failed"]
        
        for status in non_terminal:
            assert status.value not in ["completed", "failed"]


class TestValidationStatus:
    """Tests for ValidationStatus enum."""
    
    def test_validation_statuses(self):
        """Verify validation status values."""
        from src.mvp.mvp_req.models.enums import ValidationStatus
        
        expected = ["valid", "invalid", "repaired", "repair_failed"]
        actual = [vs.value for vs in ValidationStatus]
        
        assert sorted(expected) == sorted(actual)


class TestQuestionCategory:
    """Tests for QuestionCategory enum."""
    
    def test_question_categories(self):
        """Verify question category values."""
        from src.mvp.mvp_req.models.enums import QuestionCategory
        
        expected_categories = [
            "template_disambiguation",
            "scope_clarification", 
            "feature_priority",
            "user_context",
            "technical_constraint",
            "business_model"
        ]
        actual = [qc.value for qc in QuestionCategory]
        
        assert sorted(expected_categories) == sorted(actual)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
