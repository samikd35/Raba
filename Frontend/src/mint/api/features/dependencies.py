"""
Feature resolution dependencies for automatic feature_id handling.
"""

from fastapi import HTTPException, status
from .service import ModuleFeatureService

# Global service instance for dependency injection
feature_service = ModuleFeatureService()


async def resolve_feature_id(feature_identifier: str) -> str:
    """
    FastAPI dependency to automatically resolve feature names to UUIDs.
    
    Args:
        feature_identifier: Either feature name (e.g., 'problem-generator') or UUID
        
    Returns:
        Resolved feature UUID
        
    Raises:
        HTTPException: If feature not found or inactive
    """
    resolved_id = feature_service.resolve_feature_identifier(feature_identifier)
    
    if not resolved_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "feature_not_found",
                "message": f"Feature '{feature_identifier}' not found or inactive",
                "identifier": feature_identifier
            }
        )
    
    return resolved_id


def get_feature_mapping() -> dict:
    """
    Get mapping of user-friendly names to database feature names.
    Based on actual Supabase table data and endpoint usage.
    """
    return {
        # Core Features (User-Friendly → Database Name)
        "problem-generator": "problem_generator",           # /api/v1/pgen/generate/{feature_id}
        "problem-refiner": "PRefiner",                      # /api/v1/idea-refinement/refine/{feature_id}
        "problem-validator": "Problem Validator",           # /api/workflow/jobs/{feature_id}
        "customer-profile-generator": "customer_profile_generator",  # /api/v2/vmp/.../generate-customer-profile/{feature_id}
        
        # Additional Features (from Supabase table)
        "hypothesis-generator": "hypothesis_generator",
        "vpc-validator": "vpc_validator", 
        "assumptions-generator": "assumptions_generator",
        "questionnaire-generator": "questionnaire_generator",
        "vpc-canvas-composer": "vpc_canvas_composer",
        "value-map-generator": "value_map_generator",
        "field-prep-exporter": "field_prep_exporter",
        "stakeholder-mapper": "stakeholder_mapper",
        
        # MVP Module Features
        "mvp-requirements": "mvp_requirements",           # /mvp/projects/.../amrg/runs
        "solution-critique": "solution_critique",         # /mvp/projects/.../solution-critique/generate
    }
