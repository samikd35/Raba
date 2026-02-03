"""
Unit Tests for AMRG Template Registry

Run with: pytest src/mvp/mvp_req/tests/unit_template_registry.py -v
"""

import pytest
from pathlib import Path


class TestTemplateRegistry:
    """Tests for template registry functionality."""
    
    def test_all_template_codes_registered(self):
        """Verify all template codes have registry entries."""
        from ..models.enums import TemplateCode
        from ..templates.registry import TEMPLATE_REGISTRY, get_template_spec
        
        for template_code in TemplateCode:
            spec = get_template_spec(template_code)
            assert spec is not None, f"Template {template_code.value} not in registry"
            assert spec.code == template_code
    
    def test_template_spec_has_required_fields(self):
        """Verify each template spec has all required fields."""
        from ..models.enums import TemplateCode
        from ..templates.registry import get_template_spec
        
        for template_code in TemplateCode:
            spec = get_template_spec(template_code)
            
            # Required fields
            assert spec.code is not None
            assert spec.name is not None
            assert len(spec.name) > 0
            assert spec.description is not None
            assert spec.prd_prompt_path is not None
            assert spec.schema_path is not None
            assert spec.template_version is not None
            assert spec.schema_version is not None
    
    def test_prompt_files_exist(self):
        """Verify all prompt template files exist."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        from src.mvp.mvp_req.templates.registry import get_template_spec
        
        for template_code in TemplateCode:
            spec = get_template_spec(template_code)
            prompt_path = spec.get_prd_prompt_full_path()
            
            assert prompt_path.exists(), f"Prompt file missing: {prompt_path}"
    
    def test_schema_files_exist(self):
        """Verify all schema files exist."""
        from ..models.enums import TemplateCode
        from ..templates.registry import get_template_spec
        
        for template_code in TemplateCode:
            spec = get_template_spec(template_code)
            schema_path = spec.get_schema_full_path()
            
            assert schema_path.exists(), f"Schema file missing: {schema_path}"
    
    def test_base_schema_exists(self):
        """Verify base schema file exists."""
        from ..templates.registry import TEMPLATES_BASE_PATH
        
        base_schema_path = TEMPLATES_BASE_PATH / "schemas" / "base_schema.json"
        assert base_schema_path.exists(), "Base schema file missing"
    
    def test_routing_prompts_exist(self):
        """Verify routing prompt templates exist."""
        from ..templates.registry import TEMPLATES_BASE_PATH
        
        prompts_dir = TEMPLATES_BASE_PATH / "prompts"
        
        required_prompts = [
            "routing_coarse.j2",
            "routing_final.j2",
            "questions_base.j2"
        ]
        
        for prompt_name in required_prompts:
            prompt_path = prompts_dir / prompt_name
            assert prompt_path.exists(), f"Required prompt missing: {prompt_name}"
    
    def test_template_categories(self):
        """Verify templates are in correct categories via TemplateCode."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        digital_templates = [TemplateCode.A1, TemplateCode.A2, TemplateCode.A3, 
                           TemplateCode.A4, TemplateCode.A5]
        service_templates = [TemplateCode.B1]
        physical_templates = [TemplateCode.C1, TemplateCode.C2]
        
        for tc in digital_templates:
            category = TemplateCode.get_category(tc)
            assert "Digital" in category, f"{tc.value} should be digital"
        
        for tc in service_templates:
            category = TemplateCode.get_category(tc)
            assert "Services" in category, f"{tc.value} should be services"
        
        for tc in physical_templates:
            category = TemplateCode.get_category(tc)
            assert "Physical" in category, f"{tc.value} should be physical"
    
    def test_get_all_template_codes(self):
        """Test getting all template codes."""
        from ..templates.registry import get_all_template_codes
        
        codes = get_all_template_codes()
        assert len(codes) == 8
        assert "A1" in codes
        assert "C2" in codes


class TestTemplateCode:
    """Tests for TemplateCode enum."""
    
    def test_template_code_values(self):
        """Verify template code values."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        expected_codes = ["A1", "A2", "A3", "A4", "A5", "B1", "C1", "C2"]
        actual_codes = [tc.value for tc in TemplateCode]
        
        assert set(expected_codes) == set(actual_codes)
    
    def test_digital_category_classification(self):
        """Test digital category classification."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        assert "Digital" in TemplateCode.get_category(TemplateCode.A1)
        assert "Digital" in TemplateCode.get_category(TemplateCode.A5)
        assert "Digital" not in TemplateCode.get_category(TemplateCode.B1)
        assert "Digital" not in TemplateCode.get_category(TemplateCode.C1)
    
    def test_physical_category_classification(self):
        """Test physical category classification."""
        from src.mvp.mvp_req.models.enums import TemplateCode
        
        assert "Physical" in TemplateCode.get_category(TemplateCode.C1)
        assert "Physical" in TemplateCode.get_category(TemplateCode.C2)
        assert "Physical" not in TemplateCode.get_category(TemplateCode.A1)
        assert "Physical" not in TemplateCode.get_category(TemplateCode.B1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
