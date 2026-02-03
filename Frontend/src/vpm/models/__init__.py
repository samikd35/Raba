"""
VMP Models Integration

This module provides model definitions that are compatible with both
the original VMP codebase and Yuba's existing patterns.
"""

# Import Field Prep models
from .field_prep import (
    FieldPrepStage, StakeholderType,
    FieldPrepHypothesisRequest, FieldPrepHypothesisResponse,
    FieldPrepAssumptionsRequest, FieldPrepAssumptionsResponse,
    FieldPrepStakeholdersRequest, FieldPrepStakeholdersResponse,
    FieldPrepQuestionnairesRequest, FieldPrepQuestionnairesResponse,
    FieldPrepProgressResponse, FieldPrepExportRequest, FieldPrepExportResponse,
    HYPOTHESIS_SCHEMA, ASSUMPTION_SCHEMA, STAKEHOLDER_ASSIGNMENT_SCHEMA
)

__all__ = [
    # Field Prep Enums
    "FieldPrepStage",
    "StakeholderType",
    
    # Field Prep Request/Response Models
    "FieldPrepHypothesisRequest",
    "FieldPrepHypothesisResponse", 
    "FieldPrepAssumptionsRequest",
    "FieldPrepAssumptionsResponse",
    "FieldPrepStakeholdersRequest",
    "FieldPrepStakeholdersResponse",
    "FieldPrepQuestionnairesRequest",
    "FieldPrepQuestionnairesResponse",
    "FieldPrepProgressResponse",
    "FieldPrepExportRequest",
    "FieldPrepExportResponse",
    
    # Field Prep Schemas
    "HYPOTHESIS_SCHEMA",
    "ASSUMPTION_SCHEMA", 
    "STAKEHOLDER_ASSIGNMENT_SCHEMA"
]
