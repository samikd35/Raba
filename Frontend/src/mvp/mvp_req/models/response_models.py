"""
Response Models for MVP Requirements Generator (AMRG) API

Pydantic models for API request/response validation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .enums import ResearchMode, RunStatus, TemplateCode


# ==================== REQUEST MODELS ====================

class AMRGGenerateRequest(BaseModel):
    """Request to start AMRG PRD generation."""
    research_mode: ResearchMode = Field(
        default=ResearchMode.AUTO,
        description="Web research mode: 'off', 'auto', or 'on'"
    )
    force_regenerate: bool = Field(
        default=True,
        description="Force regeneration even if PRD already exists"
    )


class AMRGAnswersRequest(BaseModel):
    """Request to submit answers to clarifying questions."""
    answers: List[Dict[str, Any]] = Field(
        ...,
        description="Array of answers with q_index and answer_text",
        min_length=3,
        max_length=3
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "answers": [
                    {"q_index": 1, "answer_text": "B2B SaaS targeting SMBs"},
                    {"q_index": 2, "answer_text": "Web-first, mobile later"},
                    {"q_index": 3, "answer_text": "Subscription model with freemium tier"}
                ]
            }
        }


class AMRGRegenerateRequest(BaseModel):
    """Request to regenerate PRD with revisions."""
    revision_instructions: str = Field(
        ...,
        description="Instructions for what to change in the PRD",
        min_length=10
    )
    template_override: Optional[str] = Field(
        default=None,
        description="Optional template code to force (e.g., 'A1')"
    )
    research_mode: ResearchMode = Field(
        default=ResearchMode.AUTO,
        description="Web research mode for regeneration"
    )


# ==================== RESPONSE MODELS ====================

class ClarifyingQuestionResponse(BaseModel):
    """A clarifying question in API response."""
    q_index: int = Field(..., description="Question index (1, 2, or 3)")
    question_text: str = Field(..., description="The question text")
    category: str = Field(..., description="Question category")
    purpose: str = Field(..., description="Why this question is being asked")


class TemplateCandidate(BaseModel):
    """A candidate template from routing."""
    code: str = Field(..., description="Template code (e.g., 'A1')")
    name: str = Field(..., description="Human-readable template name")
    confidence: float = Field(..., description="Confidence score 0.0-1.0")
    rationale: str = Field(..., description="Why this template matches")


class CoarseRoutingResponse(BaseModel):
    """Coarse routing result in API response."""
    top_templates: List[TemplateCandidate]
    confidence_threshold_met: bool
    routing_rationale: str


class AMRGGenerateResponse(BaseModel):
    """Response from starting AMRG generation."""
    success: bool
    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(..., description="Run status")
    message: str
    
    # Coarse routing results
    coarse_routing: Optional[CoarseRoutingResponse] = None
    
    # Clarifying questions (exactly 3)
    questions: Optional[List[ClarifyingQuestionResponse]] = None
    
    # Estimated time if processing
    estimated_completion_seconds: Optional[int] = None


class AMRGStatusResponse(BaseModel):
    """Response for run status check."""
    run_id: str
    project_id: str
    status: str
    
    # Progress info
    current_step: Optional[str] = None
    progress_percentage: Optional[int] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    # If completed
    prd_available: bool = False
    
    # If failed
    error: Optional[str] = None


class PRDMetadata(BaseModel):
    """Metadata about the generated PRD."""
    template_code: str
    template_name: Optional[str] = None
    template_version: Optional[str] = None
    schema_version: Optional[str] = None
    generated_at: Optional[datetime] = None
    research_used: bool = False
    research_sources_count: Optional[int] = None


class AMRGResultsResponse(BaseModel):
    """Response containing the generated PRD."""
    success: bool
    run_id: str
    project_id: str
    status: str
    
    # PRD output
    prd_json: Optional[Dict[str, Any]] = None
    prd_metadata: Optional[PRDMetadata] = None
    
    # Validation info
    validation_status: Optional[str] = None
    validation_warnings: Optional[List[str]] = None
    
    # Version info
    version: int = 1
    
    # Timestamps
    completed_at: Optional[datetime] = None


class AMRGHistoryItem(BaseModel):
    """Single item in PRD history."""
    version: int
    template_code: str
    generated_at: datetime
    validation_status: str
    is_current: bool


class AMRGHistoryResponse(BaseModel):
    """Response for PRD version history."""
    project_id: str
    total_versions: int
    versions: List[AMRGHistoryItem]


# ==================== ERROR MODELS ====================

class MissingArtifactDetail(BaseModel):
    """Detail about a missing artifact."""
    artifact_name: str
    description: str
    how_to_generate: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    # For eligibility errors
    missing_artifacts: Optional[List[MissingArtifactDetail]] = None


class EligibilityErrorResponse(BaseModel):
    """Error response for eligibility check failure."""
    success: bool = False
    error_code: str = "MISSING_REQUIRED_ARTIFACTS"
    message: str = "Project is missing required artifacts for PRD generation"
    missing_artifacts: List[str]
    artifact_details: List[MissingArtifactDetail]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "MISSING_REQUIRED_ARTIFACTS",
                "message": "Project is missing required artifacts for PRD generation",
                "missing_artifacts": ["solution_critique", "vps_v2"],
                "artifact_details": [
                    {
                        "artifact_name": "solution_critique",
                        "description": "Solution Critique analysis",
                        "how_to_generate": "Run solution critique generation first"
                    },
                    {
                        "artifact_name": "vps_v2",
                        "description": "Value Proposition Statement v2",
                        "how_to_generate": "Generate VPS v2 after solution critique"
                    }
                ]
            }
        }
