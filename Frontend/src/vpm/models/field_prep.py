"""
Field Prep Models for VPM Integration

These models define the Field Research Preparation workflow that follows VPC generation.
Integrates with Yuba's existing authentication, credit system, and database infrastructure.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class FieldPrepStage(str, Enum):
    """Field Prep workflow stages"""
    HYPOTHESIS = "field_prep_hypothesis"
    ASSUMPTIONS = "field_prep_assumptions" 
    STAKEHOLDERS = "field_prep_stakeholders"
    QUESTIONNAIRES = "field_prep_questionnaires"
    COMPLETED = "field_prep_completed"


class StakeholderType(str, Enum):
    """Types of stakeholders for field research"""
    CUSTOMER = "customer"
    PARTNER = "partner"
    EXPERT = "expert"
    INTERNAL = "internal"
    OTHER = "other"


# ==================== REQUEST/RESPONSE MODELS ====================

class FieldPrepHypothesisRequest(BaseModel):
    """Request to generate market hypothesis"""
    creativity_level: float = Field(0.5, ge=0.0, le=1.0, description="AI creativity level")


class FieldPrepHypothesisResponse(BaseModel):
    """Response with generated hypotheses (supports multi-persona)"""
    hypothesis: List[Dict[str, Any]] = Field(..., description="Generated hypotheses with evidence (one per persona)")
    project_id: str = Field(..., description="VMP project ID")
    stage: FieldPrepStage = Field(FieldPrepStage.HYPOTHESIS, description="Current workflow stage")
    context_summary: Optional[Dict[str, Any]] = Field(None, description="Context used for generation")
    total_hypotheses: int = Field(..., description="Total number of hypotheses generated")
    personas_count: int = Field(..., description="Number of personas processed")


class FieldPrepAssumptionsRequest(BaseModel):
    """Request to generate assumptions from hypothesis - always generates exactly 2"""
    max_assumptions: int = Field(2, description="Number of assumptions to generate (ignored - always generates 2 per hypothesis)")


class FieldPrepAssumptionsResponse(BaseModel):
    """Response with generated assumptions (supports multi-persona)"""
    assumptions: List[Dict[str, Any]] = Field(..., description="Generated assumptions")
    project_id: str = Field(..., description="VMP project ID")
    stage: FieldPrepStage = Field(FieldPrepStage.ASSUMPTIONS, description="Current workflow stage")
    total_assumptions: int = Field(..., description="Total number of assumptions generated")
    hypotheses_count: int = Field(..., description="Number of hypotheses processed")
    hypotheses_reference: List[Dict[str, Any]] = Field(..., description="Reference to source hypotheses")


class FieldPrepStakeholdersRequest(BaseModel):
    """Request to assign stakeholders to assumptions"""
    project_id: str = Field(..., description="VPM project ID")
    stakeholder_preferences: Optional[List[StakeholderType]] = Field(None, description="Preferred stakeholder types")


class FieldPrepStakeholdersResponse(BaseModel):
    """Response with stakeholder assignments"""
    stakeholder_assignments: List[Dict[str, Any]] = Field(..., description="Assumptions with assigned stakeholders")
    project_id: str = Field(..., description="VPM project ID")
    stage: FieldPrepStage = Field(FieldPrepStage.STAKEHOLDERS, description="Current workflow stage")
    assignment_summary: Dict[str, Any] = Field(..., description="Summary of stakeholder assignments")


class FieldPrepQuestionnairesRequest(BaseModel):
    """Request to generate questionnaires"""
    questions_per_assumption: int = Field(5, ge=3, le=10, description="Questions per assumption")
    include_demographic_questions: bool = Field(True, description="Include demographic questions")


class FieldPrepQuestionnairesResponse(BaseModel):
    """Response with generated questionnaires (persona-based workflow)"""
    questionnaires: List[Dict[str, Any]] = Field(..., description="Generated questions for each assumption")
    project_id: str = Field(..., description="VPM project ID")
    stage: FieldPrepStage = Field(FieldPrepStage.QUESTIONNAIRES, description="Current workflow stage")
    total_questions: int = Field(..., description="Total number of questions generated")
    assumptions_count: int = Field(..., description="Number of assumptions processed")
    personas_count: int = Field(..., description="Number of personas involved")
    questions_per_assumption: int = Field(..., description="Questions generated per assumption")


# ==================== EDITING MODELS ====================

class CustomerProfileEditRequest(BaseModel):
    """Request to edit customer profile selections - accepts either direct or wrapped format"""
    customer_profile_selections: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None, 
        description="Direct format: {'jobs_to_be_done': [...], 'pains': [...], 'gains': [...]}"
    )
    data: Optional[Dict[str, Any]] = Field(None, description="Wrapped format with data.customer_profile_selections")
    
    def get_customer_profile(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract customer profile from either format"""
        if self.customer_profile_selections is not None:
            return self.customer_profile_selections
        elif self.data is not None and "customer_profile_selections" in self.data:
            return self.data["customer_profile_selections"]
        else:
            raise ValueError("Must provide either 'customer_profile_selections' or 'data.customer_profile_selections'")


class CustomerProfileEditResponse(BaseModel):
    """Response after editing customer profile"""
    success: bool = Field(..., description="Whether the edit was successful")
    data: Dict[str, Any] = Field(..., description="Updated customer profile data")
    message: str = Field(..., description="Status message")


class PersonaEditRequest(BaseModel):
    """Request to edit personas - accepts either direct array or wrapped format"""
    personas: Optional[List[Dict[str, Any]]] = Field(None, description="Updated personas data (direct format)")
    data: Optional[Dict[str, Any]] = Field(None, description="Wrapped format with data.personas")
    
    def get_personas(self) -> List[Dict[str, Any]]:
        """Extract personas from either format"""
        if self.personas is not None:
            return self.personas
        elif self.data is not None and "personas" in self.data:
            return self.data["personas"]
        else:
            raise ValueError("Must provide either 'personas' array or 'data.personas' object")


class PersonaEditResponse(BaseModel):
    """Response after editing personas"""
    success: bool = Field(..., description="Whether the edit was successful")
    data: Dict[str, Any] = Field(..., description="Updated personas data")
    message: str = Field(..., description="Status message")


class PersonaAddRequest(BaseModel):
    """Request to add a new user-created persona with AI enrichment.
    
    User provides minimal input (name + description), and the system:
    - Queries PV report and actionable insights
    - Finds relevant evidence automatically
    - Enhances description with data-driven insights
    - Generates problem_relationship automatically
    """
    name: str = Field(..., min_length=1, max_length=100, description="Persona name/title")
    description: str = Field(..., min_length=10, max_length=500, description="Brief persona description (will be enhanced by AI)")
    problem_relationship: Optional[str] = Field(None, min_length=10, max_length=300, description="How this persona relates to the problem (auto-generated if not provided)")
    is_primary_payer: bool = Field(True, description="Whether this persona is likely to pay for solutions")
    evidence: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Optional evidence quotes (auto-generated from PV report if not provided)"
    )


class PersonaAddResponse(BaseModel):
    """Response after adding a new persona"""
    success: bool = Field(..., description="Whether the add was successful")
    data: Dict[str, Any] = Field(..., description="Added persona data with all personas")
    message: str = Field(..., description="Status message")
    total_personas: int = Field(..., description="Total personas after addition")
    requires_multiple_vpcs: bool = Field(..., description="Whether multiple VPCs are now required")


class PersonaDeleteRequest(BaseModel):
    """Request to delete a persona by ID"""
    persona_id: str = Field(..., description="ID of persona to delete")


class PersonaDeleteResponse(BaseModel):
    """Response after deleting a persona"""
    success: bool = Field(..., description="Whether the delete was successful")
    data: Dict[str, Any] = Field(..., description="Remaining personas data")
    message: str = Field(..., description="Status message")
    total_personas: int = Field(..., description="Total personas after deletion")
    requires_multiple_vpcs: bool = Field(..., description="Whether multiple VPCs are still required")


class HypothesisEditRequest(BaseModel):
    """Request to edit hypotheses - accepts either direct array or wrapped format"""
    hypotheses: Optional[List[Dict[str, Any]]] = Field(None, description="Updated hypotheses data (direct format)")
    data: Optional[Dict[str, Any]] = Field(None, description="Wrapped format with data.hypotheses")
    
    def get_hypotheses(self) -> List[Dict[str, Any]]:
        """Extract hypotheses from either format"""
        if self.hypotheses is not None:
            return self.hypotheses
        elif self.data is not None and "hypotheses" in self.data:
            return self.data["hypotheses"]
        else:
            raise ValueError("Must provide either 'hypotheses' array or 'data.hypotheses' object")


class HypothesisEditResponse(BaseModel):
    """Response after editing hypotheses"""
    success: bool = Field(..., description="Whether the edit was successful")
    data: Dict[str, Any] = Field(..., description="Updated hypotheses data")
    message: str = Field(..., description="Status message")


class AssumptionsEditRequest(BaseModel):
    """Request to edit assumptions - accepts either direct array or wrapped format"""
    assumptions: Optional[List[Dict[str, Any]]] = Field(None, description="Updated assumptions data (direct format)")
    data: Optional[Dict[str, Any]] = Field(None, description="Wrapped format with data.assumptions")
    
    def get_assumptions(self) -> List[Dict[str, Any]]:
        """Extract assumptions from either format"""
        if self.assumptions is not None:
            return self.assumptions
        elif self.data is not None and "assumptions" in self.data:
            return self.data["assumptions"]
        else:
            raise ValueError("Must provide either 'assumptions' array or 'data.assumptions' object")


class AssumptionsEditResponse(BaseModel):
    """Response after editing assumptions"""
    success: bool = Field(..., description="Whether the edit was successful")
    data: Dict[str, Any] = Field(..., description="Updated assumptions data")
    message: str = Field(..., description="Status message")


class QuestionnairesEditRequest(BaseModel):
    """Request to edit questionnaires - accepts either direct array or wrapped format"""
    questionnaires: Optional[List[Dict[str, Any]]] = Field(None, description="Updated questionnaires data (direct format)")
    data: Optional[Dict[str, Any]] = Field(None, description="Wrapped format with data.questionnaires")
    
    def get_questionnaires(self) -> List[Dict[str, Any]]:
        """Extract questionnaires from either format"""
        if self.questionnaires is not None:
            return self.questionnaires
        elif self.data is not None and "questionnaires" in self.data:
            return self.data["questionnaires"]
        else:
            raise ValueError("Must provide either 'questionnaires' array or 'data.questionnaires' object")


class QuestionnairesEditResponse(BaseModel):
    """Response after editing questionnaires"""
    success: bool = Field(..., description="Whether the edit was successful")
    data: Dict[str, Any] = Field(..., description="Updated questionnaires data")
    message: str = Field(..., description="Status message")


# ==================== EXPORT MODELS ====================

class FieldPrepExportRequest(BaseModel):
    """Request for exporting field prep artifacts"""
    project_id: str = Field(..., description="VPM project ID")
    export_format: str = Field(..., description="Export format: pdf, word, csv, google_forms")
    include_instructions: bool = Field(True, description="Include research instructions")
    project_title: Optional[str] = Field(None, description="Custom project title for export")


class FieldPrepExportResponse(BaseModel):
    """Response with export information"""
    export_url: Optional[str] = Field(None, description="URL to download exported file")
    export_id: str = Field(..., description="Export job ID for tracking")
    export_format: str = Field(..., description="Export format used")
    status: str = Field(..., description="Export status: processing, completed, failed")
    message: str = Field(..., description="Status message")


# ==================== GOOGLE FORMS INTEGRATION ====================

class GoogleFormsAuthRequest(BaseModel):
    """Request to initiate Google Forms authentication"""
    project_id: str = Field(..., description="VPM project ID")
    redirect_url: Optional[str] = Field(None, description="Custom redirect URL after auth")


class GoogleFormsCreateRequest(BaseModel):
    """Request to create Google Forms"""
    project_id: str = Field(..., description="VPM project ID")
    form_title_prefix: Optional[str] = Field("VPC Field Research", description="Prefix for form titles")
    share_with_team: bool = Field(False, description="Share forms with team members")


class GoogleFormsCreateResponse(BaseModel):
    """Response with created Google Forms"""
    forms: List[Dict[str, Any]] = Field(..., description="Created Google Forms with URLs")
    project_id: str = Field(..., description="VPM project ID")
    total_forms: int = Field(..., description="Total number of forms created")
    message: str = Field(..., description="Creation status message")


# ==================== STATUS AND PROGRESS MODELS ====================

class FieldPrepProgressResponse(BaseModel):
    """Response showing field prep progress"""
    project_id: str = Field(..., description="VPM project ID")
    current_stage: FieldPrepStage = Field(..., description="Current workflow stage")
    completed_stages: List[FieldPrepStage] = Field(..., description="Completed workflow stages")
    next_stage: Optional[FieldPrepStage] = Field(None, description="Next available stage")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Overall progress percentage")
    artifacts_summary: Dict[str, Any] = Field(..., description="Summary of generated artifacts")
    can_proceed: bool = Field(..., description="Whether user can proceed to next stage")
    requirements_for_next_stage: List[str] = Field(default=[], description="Requirements to proceed")


# ==================== VALIDATION SCHEMAS ====================

HYPOTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "text": {"type": "string", "maxLength": 200},
        "evidence_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["pv_report", "actionable_insights"]},
                    "quote": {"type": "string", "maxLength": 400},
                    "relevance_score": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["source", "quote"]
            },
            "minItems": 1,
            "maxItems": 3
        },
        "testability_score": {"type": "number", "minimum": 0, "maximum": 1},
        "market_focus": {"type": "string", "maxLength": 100}
    },
    "required": ["id", "text", "evidence_refs"]
}

ASSUMPTION_SCHEMA = {
    "type": "object", 
    "properties": {
        "id": {"type": "string"},
        "text": {"type": "string", "maxLength": 150},
        "category": {"type": "string", "enum": ["customer", "market", "product", "business_model"]},
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "evidence_strength": {"type": "string", "enum": ["strong", "moderate", "weak"]},
        "hypothesis_link": {"type": "string"}
    },
    "required": ["id", "text", "category", "priority", "hypothesis_link"]
}

STAKEHOLDER_ASSIGNMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "assumption_id": {"type": "string"},
        "stakeholder_type": {"type": "string", "enum": ["customer", "partner", "expert", "internal", "other"]},
        "stakeholder_description": {"type": "string", "maxLength": 200},
        "research_method": {"type": "string", "enum": ["interview", "survey", "observation", "focus_group"]},
        "sample_size_recommendation": {"type": "integer", "minimum": 1, "maximum": 100},
        "timeline_days": {"type": "integer", "minimum": 1, "maximum": 90}
    },
    "required": ["assumption_id", "stakeholder_type", "stakeholder_description", "research_method"]
}
