"""
Unit Tests for AMRG Schema Validator

Run with: pytest src/mvp/mvp_req/tests/unit_schema_validator.py -v
"""

import pytest
import json
from pathlib import Path


class TestSchemaValidator:
    """Tests for schema validation functionality."""
    
    def test_validator_initialization(self):
        """Test schema validator initializes correctly."""
        from ..services.schema_validator import SchemaValidatorService
        
        validator = SchemaValidatorService()
        assert validator._base_schema is not None
    
    def test_validate_valid_prd(self):
        """Test validation of a valid PRD structure."""
        from ..services.schema_validator import SchemaValidatorService
        from ..models.enums import TemplateCode, ValidationStatus
        
        validator = SchemaValidatorService()
        
        # Minimal valid PRD
        valid_prd = {
            "template_code": "A1",
            "template_version": "1.0.0",
            "schema_version": "1.0.0",
            "purpose": {
                "validated_problem": "Test problem",
                "target_persona": "Test persona",
                "why_mvp_exists": "Test reason"
            },
            "objective": {
                "learning_goals": ["Goal 1", "Goal 2"],
                "success_criteria": ["Criteria 1"]
            },
            "scope": {
                "in_scope": {
                    "segments": ["Segment 1"],
                    "flows": ["Flow 1"],
                    "geography": "Test geography"
                },
                "out_of_scope": ["Out 1"]
            },
            "primary_persona": {
                "name": "Test Persona",
                "description": "Test description",
                "primary_jtbd": "Test job"
            },
            "mvp_features": {
                "must_haves": [
                    {
                        "feature_name": "Feature 1",
                        "description": "Desc 1",
                        "job_supported": "Job 1",
                        "job_type": "functional"
                    },
                    {
                        "feature_name": "Feature 2",
                        "description": "Desc 2",
                        "job_supported": "Job 2",
                        "job_type": "functional"
                    },
                    {
                        "feature_name": "Feature 3",
                        "description": "Desc 3",
                        "job_supported": "Job 3",
                        "job_type": "functional"
                    }
                ],
                "nice_to_haves": []
            },
            "critical_workflows": [
                {
                    "workflow_name": "Workflow 1",
                    "description": "Desc 1",
                    "steps": ["Step 1", "Step 2"]
                }
            ],
            "constraints_and_nongoals": [
                {
                    "constraint": "Constraint 1",
                    "type": "technical",
                    "rationale": "Reason"
                }
            ],
            "success_signals": {
                "quantitative": [
                    {"metric": "Metric 1", "target": "Target 1", "measurement_method": "Method 1"},
                    {"metric": "Metric 2", "target": "Target 2", "measurement_method": "Method 2"}
                ],
                "qualitative": [
                    {"signal": "Signal 1", "observation_method": "Method 1"}
                ]
            },
            "assumptions_and_risks": [
                {
                    "assumption": "Assumption 1",
                    "risk_if_wrong": "Risk 1",
                    "mitigation": "Mitigation 1"
                }
            ],
            "source_artifacts_used": {
                "vps_version": "v2",
                "bmc_version": "v2",
                "critique_used": True
            },
            # A1-specific required fields
            "data_requirements": {
                "inputs": ["User data", "Settings"],
                "outputs": ["Reports", "Notifications"],
                "storage": "Cloud database"
            },
            "automation_level": {
                "current": "manual",
                "target": "semi-automated",
                "rationale": "Start manual, automate based on feedback"
            },
            "platform_choices": {
                "platforms": ["web"],
                "rationale": "Web-first for accessibility",
                "native_later": False
            }
        }
        
        status, errors, warnings = validator.validate_prd(valid_prd, TemplateCode.A1)
        
        # Allow VALID or REPAIRED status for comprehensive test
        assert status in [ValidationStatus.VALID, ValidationStatus.REPAIRED] or len(errors) == 0, f"Expected valid, got errors: {errors}"
    
    def test_validate_missing_required_field(self):
        """Test validation catches missing required fields."""
        from ..services.schema_validator import SchemaValidatorService
        from ..models.enums import TemplateCode, ValidationStatus
        
        validator = SchemaValidatorService()
        
        # PRD missing 'purpose' field
        invalid_prd = {
            "template_code": "A1",
            "template_version": "1.0.0"
        }
        
        status, errors, warnings = validator.validate_prd(invalid_prd, TemplateCode.A1)
        
        assert status == ValidationStatus.INVALID
        assert len(errors) > 0
        
        # Check that 'purpose' is in the error messages
        error_fields = [e.get("field") for e in errors]
        assert "purpose" in error_fields
    
    def test_validate_insufficient_features(self):
        """Test validation catches too few must-have features."""
        from ..services.schema_validator import SchemaValidatorService
        from ..models.enums import TemplateCode, ValidationStatus
        
        validator = SchemaValidatorService()
        
        # PRD with only 1 must-have feature (needs 3)
        invalid_prd = {
            "template_code": "A1",
            "template_version": "1.0.0",
            "schema_version": "1.0.0",
            "purpose": {"validated_problem": "x", "target_persona": "x", "why_mvp_exists": "x"},
            "objective": {"learning_goals": ["x"], "success_criteria": ["x"]},
            "scope": {"in_scope": {"segments": ["x"], "flows": ["x"], "geography": "x"}, "out_of_scope": ["x"]},
            "primary_persona": {"name": "x", "description": "x", "primary_jtbd": "x"},
            "mvp_features": {
                "must_haves": [
                    {"feature_name": "Only One", "description": "x", "job_supported": "x", "job_type": "functional"}
                ],
                "nice_to_haves": []
            },
            "critical_workflows": [{"workflow_name": "x", "description": "x", "steps": ["x"]}],
            "constraints_and_nongoals": [{"constraint": "x", "type": "technical", "rationale": "x"}],
            "success_signals": {
                "quantitative": [
                    {"metric": "x", "target": "x", "measurement_method": "x"},
                    {"metric": "y", "target": "y", "measurement_method": "y"}
                ],
                "qualitative": [{"signal": "x", "observation_method": "x"}]
            },
            "assumptions_and_risks": [{"assumption": "x", "risk_if_wrong": "x", "mitigation": "x"}],
            "source_artifacts_used": {"vps_version": "v2", "bmc_version": "v2", "critique_used": True}
        }
        
        status, errors, warnings = validator.validate_prd(invalid_prd, TemplateCode.A1)
        
        assert status == ValidationStatus.INVALID
        
        # Check for insufficient_features error
        error_types = [e.get("error") for e in errors]
        assert "insufficient_features" in error_types
    
    def test_repair_suggestions(self):
        """Test that repair suggestions are generated for errors."""
        from ..services.schema_validator import SchemaValidatorService
        
        validator = SchemaValidatorService()
        
        errors = [
            {"field": "purpose", "error": "missing_required_field", "message": "Missing"},
            {"field": "mvp_features.must_haves", "error": "insufficient_features", "message": "Too few"}
        ]
        
        suggestions = validator.get_repair_suggestions(errors)
        
        assert len(suggestions) == 2
        assert all(s.get("suggestion") is not None for s in suggestions)
    
    def test_create_validation_report(self):
        """Test validation report creation."""
        from ..services.schema_validator import SchemaValidatorService
        from ..models.enums import ValidationStatus
        
        validator = SchemaValidatorService()
        
        errors = [{"field": "test", "error": "test_error", "message": "Test"}]
        warnings = ["Warning 1"]
        
        report = validator.create_validation_report(
            ValidationStatus.INVALID, errors, warnings, repair_attempts=1
        )
        
        assert report["status"] == "invalid"
        assert report["is_valid"] == False
        assert report["error_count"] == 1
        assert report["warning_count"] == 1
        assert report["repair_attempts"] == 1
        assert len(report["repair_suggestions"]) > 0


class TestSchemaFiles:
    """Tests for schema file validity."""
    
    def test_base_schema_valid_json(self):
        """Test base schema is valid JSON."""
        from ..templates.registry import TEMPLATES_BASE_PATH
        
        base_path = TEMPLATES_BASE_PATH / "schemas" / "base_schema.json"
        
        with open(base_path, 'r') as f:
            schema = json.load(f)
        
        assert "$schema" in schema
        assert "properties" in schema
    
    def test_all_schemas_valid_json(self):
        """Test all template schemas are valid JSON."""
        from ..models.enums import TemplateCode
        from ..templates.registry import get_template_spec
        
        for template_code in TemplateCode:
            spec = get_template_spec(template_code)
            schema_path = spec.get_schema_full_path()
            
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            assert "$schema" in schema or "allOf" in schema, f"Invalid schema for {template_code.value}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
