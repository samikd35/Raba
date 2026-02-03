"""
Schema Validator Service for MVP Requirements Generator

Validates PRD JSON output against template-specific schemas.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError, RefResolver
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    logging.warning("jsonschema not installed. Schema validation will be limited.")

from ..models.enums import TemplateCode, ValidationStatus
from ..templates.registry import get_template_spec, TEMPLATES_BASE_PATH

logger = logging.getLogger(__name__)


class SchemaValidatorService:
    """
    Service for validating PRD JSON against template schemas.
    
    Features:
    - Load and cache JSON schemas
    - Validate against template-specific + base schemas
    - Return detailed validation errors
    - Support repair suggestions
    """
    
    def __init__(self):
        """Initialize schema validator with cached schemas."""
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._base_schema: Optional[Dict[str, Any]] = None
        self._load_base_schema()
    
    def _load_base_schema(self) -> None:
        """Load the base schema that all templates extend."""
        try:
            base_path = TEMPLATES_BASE_PATH / "schemas" / "base_schema.json"
            if base_path.exists():
                with open(base_path, 'r') as f:
                    self._base_schema = json.load(f)
                logger.info("✅ Loaded base schema")
            else:
                logger.warning(f"Base schema not found at {base_path}")
        except Exception as e:
            logger.error(f"Error loading base schema: {e}")
    
    def _load_template_schema(self, template_code: TemplateCode) -> Optional[Dict[str, Any]]:
        """Load schema for a specific template."""
        cache_key = template_code.value
        
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]
        
        try:
            spec = get_template_spec(template_code)
            if not spec:
                logger.error(f"No template spec for {template_code}")
                return None
            
            schema_path = spec.get_schema_full_path()
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                self._schema_cache[cache_key] = schema
                logger.info(f"✅ Loaded schema for {template_code.value}")
                return schema
            else:
                logger.warning(f"Schema not found at {schema_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading schema for {template_code}: {e}")
            return None
    
    def validate_prd(
        self,
        prd_json: Dict[str, Any],
        template_code: TemplateCode
    ) -> Tuple[ValidationStatus, List[Dict[str, Any]], List[str]]:
        """
        Validate PRD JSON against template schema.
        
        Args:
            prd_json: Generated PRD JSON
            template_code: Template code for schema selection
            
        Returns:
            Tuple of (status, errors, warnings)
        """
        logger.info(f"🔍 Validating PRD against {template_code.value} schema")
        
        errors = []
        warnings = []
        
        # Basic structure validation (without jsonschema)
        base_errors = self._validate_base_structure(prd_json)
        if base_errors:
            errors.extend(base_errors)
        
        # Template-specific validation
        template_errors = self._validate_template_specific(prd_json, template_code)
        if template_errors:
            errors.extend(template_errors)
        
        # JSON Schema validation (if available)
        if HAS_JSONSCHEMA:
            schema_errors = self._validate_with_jsonschema(prd_json, template_code)
            if schema_errors:
                errors.extend(schema_errors)
        
        # Determine status
        if not errors:
            status = ValidationStatus.VALID
            logger.info("✅ PRD validation passed")
        else:
            status = ValidationStatus.INVALID
            logger.warning(f"❌ PRD validation failed with {len(errors)} errors:")
            for i, err in enumerate(errors, 1):
                logger.warning(f"   {i}. [{err.get('error')}] {err.get('field')}: {err.get('message')}")
        
        return status, errors, warnings
    
    def _validate_base_structure(self, prd_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate base required fields present in all PRDs."""
        errors = []
        
        required_fields = [
            "template_code",
            "template_version",
            "schema_version",
            "purpose",
            "objective",
            "scope",
            "primary_persona",
            "must_have_features",
            "nice_to_have_features",
            "critical_workflows",
            "success_signals",
            "source_artifacts_used"
        ]
        
        for field in required_fields:
            if field not in prd_json:
                errors.append({
                    "field": field,
                    "error": "missing_required_field",
                    "message": f"Required field '{field}' is missing",
                    "severity": "error"
                })
            elif prd_json[field] is None:
                errors.append({
                    "field": field,
                    "error": "null_value",
                    "message": f"Required field '{field}' cannot be null",
                    "severity": "error"
                })
        
        # Validate nested structures
        if "must_have_features" in prd_json and prd_json["must_have_features"]:
            must_have_features = prd_json["must_have_features"]
            features = must_have_features.get("features", [])
            if not features:
                errors.append({
                    "field": "must_have_features.features",
                    "error": "empty_must_haves",
                    "message": "Must-have features cannot be empty",
                    "severity": "error"
                })
            elif len(features) < 3:
                errors.append({
                    "field": "must_have_features.features",
                    "error": "insufficient_features",
                    "message": "At least 3 must-have features required",
                    "severity": "error"
                })
        
        if "critical_workflows" in prd_json:
            workflows_obj = prd_json["critical_workflows"]
            # Support both old array format and new object format
            if isinstance(workflows_obj, list):
                workflows = workflows_obj
            else:
                workflows = workflows_obj.get("workflows", [])
            if not workflows or len(workflows) < 1:
                errors.append({
                    "field": "critical_workflows",
                    "error": "empty_workflows",
                    "message": "At least 1 critical workflow required",
                    "severity": "error"
                })
        
        if "success_signals" in prd_json and prd_json["success_signals"]:
            signals = prd_json["success_signals"]
            if "quantitative" not in signals or len(signals.get("quantitative", [])) < 2:
                errors.append({
                    "field": "success_signals.quantitative",
                    "error": "insufficient_metrics",
                    "message": "At least 2 quantitative success metrics required",
                    "severity": "error"
                })
        
        return errors
    
    def _validate_template_specific(
        self,
        prd_json: Dict[str, Any],
        template_code: TemplateCode
    ) -> List[Dict[str, Any]]:
        """Validate template-specific fields."""
        errors = []
        
        # A1 - Software/SaaS specific
        if template_code == TemplateCode.A1:
            required_a1 = ["data_requirements", "automation_level", "platform_choices"]
            for field in required_a1:
                if field not in prd_json:
                    errors.append({
                        "field": field,
                        "error": "missing_template_field",
                        "message": f"A1 template requires '{field}'",
                        "severity": "error"
                    })
        
        # A3 - Platform/Marketplace specific
        elif template_code == TemplateCode.A3:
            required_a3 = ["platform_sides", "matching_flow"]
            for field in required_a3:
                if field not in prd_json:
                    errors.append({
                        "field": field,
                        "error": "missing_template_field",
                        "message": f"A3 template requires '{field}'",
                        "severity": "error"
                    })
            
            # Validate platform_sides has at least 2 sides
            if "platform_sides" in prd_json:
                sides = prd_json["platform_sides"].get("sides", [])
                if len(sides) < 2:
                    errors.append({
                        "field": "platform_sides.sides",
                        "error": "insufficient_sides",
                        "message": "Marketplace must have at least 2 sides",
                        "severity": "error"
                    })
        
        # A5 - Fintech specific
        elif template_code == TemplateCode.A5:
            required_a5 = ["financial_flow", "risk_compliance"]
            for field in required_a5:
                if field not in prd_json:
                    errors.append({
                        "field": field,
                        "error": "missing_template_field",
                        "message": f"A5 template requires '{field}'",
                        "severity": "error"
                    })
        
        # C2 - Hardware/IoT specific
        elif template_code == TemplateCode.C2:
            required_c2 = ["sensing_control_job", "connectivity_power"]
            for field in required_c2:
                if field not in prd_json:
                    errors.append({
                        "field": field,
                        "error": "missing_template_field",
                        "message": f"C2 template requires '{field}'",
                        "severity": "error"
                    })
        
        return errors
    
    def _validate_with_jsonschema(
        self,
        prd_json: Dict[str, Any],
        template_code: TemplateCode
    ) -> List[Dict[str, Any]]:
        """Validate using jsonschema library."""
        if not HAS_JSONSCHEMA:
            return []
        
        errors = []
        
        # Try template-specific schema first
        schema = self._load_template_schema(template_code)
        
        # Fall back to base schema
        if not schema:
            schema = self._base_schema
        
        if not schema:
            logger.warning("No schema available for validation")
            return []
        
        try:
            # Build a schema store for resolving $ref references
            schema_dir = TEMPLATES_BASE_PATH / "schemas"
            schema_store = {}
            
            # Load all schemas into the store for $ref resolution
            for schema_file in schema_dir.glob("*.json"):
                try:
                    with open(schema_file, 'r') as f:
                        loaded_schema = json.load(f)
                        # Use the filename as the URI
                        schema_store[schema_file.name] = loaded_schema
                        # Also add with $id if present
                        if "$id" in loaded_schema:
                            schema_store[loaded_schema["$id"]] = loaded_schema
                except Exception as e:
                    logger.debug(f"Could not load schema {schema_file}: {e}")
            
            # Create resolver with the schema store
            resolver = RefResolver.from_schema(schema, store=schema_store)
            
            validator = Draft7Validator(schema, resolver=resolver)
            for error in validator.iter_errors(prd_json):
                errors.append({
                    "field": ".".join(str(p) for p in error.path) or "root",
                    "error": "schema_validation",
                    "message": error.message,
                    "severity": "error",
                    "schema_path": ".".join(str(p) for p in error.schema_path)
                })
        except Exception as e:
            logger.error(f"JSON Schema validation error: {e}")
        
        return errors
    
    def get_repair_suggestions(
        self,
        errors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate repair suggestions for validation errors.
        
        Args:
            errors: List of validation errors
            
        Returns:
            List of repair suggestions
        """
        suggestions = []
        
        for error in errors:
            suggestion = {
                "field": error.get("field"),
                "error_type": error.get("error"),
                "suggestion": None
            }
            
            error_type = error.get("error")
            
            if error_type == "missing_required_field":
                suggestion["suggestion"] = f"Add the '{error['field']}' field to the PRD"
            elif error_type == "null_value":
                suggestion["suggestion"] = f"Provide a non-null value for '{error['field']}'"
            elif error_type == "empty_must_haves":
                suggestion["suggestion"] = "Add at least 3 must-have features to must_have_features.features"
            elif error_type == "insufficient_features":
                suggestion["suggestion"] = "Add more must-have features (minimum 3 required)"
            elif error_type == "insufficient_metrics":
                suggestion["suggestion"] = "Add at least 2 quantitative success metrics"
            elif error_type == "insufficient_sides":
                suggestion["suggestion"] = "Define at least 2 sides for the marketplace (e.g., buyers and sellers)"
            else:
                suggestion["suggestion"] = f"Fix the validation error in '{error['field']}'"
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def create_validation_report(
        self,
        status: ValidationStatus,
        errors: List[Dict[str, Any]],
        warnings: List[str],
        repair_attempts: int = 0
    ) -> Dict[str, Any]:
        """Create a structured validation report."""
        return {
            "status": status.value,
            "is_valid": status == ValidationStatus.VALID,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "repair_attempts": repair_attempts,
            "repair_suggestions": self.get_repair_suggestions(errors) if errors else []
        }
