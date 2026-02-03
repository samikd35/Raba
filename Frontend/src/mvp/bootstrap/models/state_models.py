"""
Bootstrap State Models

Defines the TypedDict for LangGraph workflow state and Pydantic models for API.
"""

from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class ContextStatus(str, Enum):
    """Status values for bootstrap context generation workflow."""
    NOT_STARTED = "not_started"
    EMBEDDING = "embedding"
    QUESTIONS_PENDING = "questions_pending"
    ANSWERS_RECEIVED = "answers_received"
    RESEARCHING = "researching"
    PAYMENT_REQUIRED = "payment_required"
    CONTEXT_READY = "context_ready"
    CONTEXT_CONFIRMED = "context_confirmed"
    FAILED = "failed"


class ContextMode(str, Enum):
    """Project context mode."""
    NORMAL = "normal"
    BOOTSTRAP = "bootstrap"
    HYBRID = "hybrid"


class BootstrapState(TypedDict, total=False):
    """
    LangGraph workflow state for bootstrap context generation.
    
    This state flows through all workflow nodes and maintains
    progress across interrupt/resume cycles.
    """
    # Identifiers
    project_id: str
    tenant_id: str
    user_id: str
    
    # User info for credit handling
    is_super_admin: bool
    plan_type: str
    
    # Raw input
    idea_text: Optional[str]
    file_keys: List[str]
    
    # Extracted content
    pdf_extracts: List[Dict[str, Any]]
    
    # Embeddings status
    chunks_embedded: bool
    chunk_count: int
    
    # Clarifying questions
    clarifying_questions: List[Dict[str, Any]]
    clarifying_answers: List[Dict[str, Any]]
    
    # Research
    research_queries: List[Dict[str, Any]]
    research_results: Dict[str, Any]
    
    # Output
    enhanced_context: Optional[Dict[str, Any]]
    
    # Status tracking
    status: str
    error: Optional[str]
    
    # Timestamps
    started_at: str
    completed_at: Optional[str]


# ==================== API Request/Response Models ====================

class ClarifyingQuestion(BaseModel):
    """A single clarifying question."""
    id: str = Field(..., description="Unique question identifier (e.g., 'q1')")
    priority: str = Field(..., description="Priority level: P0, P1, or P2")
    category: str = Field(..., description="Question category (e.g., 'target_customer')")
    question: str = Field(..., description="The question text")
    context: Optional[str] = Field(None, description="Why this question is being asked")
    required: bool = Field(True, description="Whether an answer is required")


class ClarifyingAnswer(BaseModel):
    """User's answer to a clarifying question."""
    question_id: str = Field(..., description="ID of the question being answered")
    answer: str = Field(..., description="User's answer text")


class ResearchSource(BaseModel):
    """A research source with citation number."""
    model_config = ConfigDict(extra='ignore')  # Ignore extra fields like 'id'
    
    n: Optional[int] = Field(None, description="Citation number")
    title: str = Field(default="Source", description="Source title")
    publisher: Optional[str] = Field(None, description="Publisher name")
    url: str = Field(default="", description="Source URL")
    captured_at: Optional[str] = Field(None, description="ISO timestamp when captured")
    snippet: Optional[str] = Field(None, description="Relevant snippet from source")


class ResearchSection(BaseModel):
    """Research results with inline citations."""
    body: str = Field(..., description="Research summary with [n] citations")
    sources: List[ResearchSource] = Field(default_factory=list)


class ProblemDefinition(BaseModel):
    """Structured problem definition."""
    who: str = Field(..., description="Who experiences this problem")
    what: str = Field(..., description="What the problem is")
    where: str = Field(..., description="Where/when the problem occurs")
    why_now: Optional[str] = Field(None, description="Why this problem is urgent now")


class BusinessModelSeeds(BaseModel):
    """Initial business model hypotheses."""
    model_config = ConfigDict(extra='ignore')
    
    revenue_model: Optional[str] = None
    pricing_hypothesis: Optional[str] = None
    cost_drivers: Optional[List[str]] = None


class AlternativesAndCompetition(BaseModel):
    """Competitive landscape analysis."""
    model_config = ConfigDict(extra='ignore')
    
    direct_competitors: List[str] = Field(default_factory=list)
    indirect_alternatives: List[str] = Field(default_factory=list)
    differentiation_summary: Optional[str] = None


class EnhancedContextDraft(BaseModel):
    """The draft enhanced context structure."""
    model_config = ConfigDict(extra='ignore')
    
    IdeaSummary: str
    CustomerSegments: List[str]
    Problem: ProblemDefinition
    SolutionOverview: str
    Differentiation: List[str]
    BusinessModelSeeds: Optional[Dict[str, Any]] = None  # Flexible dict for LLM output
    AlternativesAndCompetition: Optional[Dict[str, Any]] = None  # Flexible dict for LLM output
    ConstraintsAndRisks: List[str] = Field(default_factory=list)
    Research: Optional[Dict[str, Any]] = None  # Flexible dict for LLM output


class ContextInvariants(BaseModel):
    """Invariants that research cannot change."""
    customer_segment: str
    geography: str
    core_problem: str
    core_solution_type: str


class EnhancedContextMetadata(BaseModel):
    """Metadata about the enhanced context."""
    context_mode: str = "bootstrap"
    invariants: Optional[ContextInvariants] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None


class EnhancedContext(BaseModel):
    """Complete enhanced context structure."""
    model_config = ConfigDict(extra='ignore')
    
    version: int = 1
    draft: Optional[EnhancedContextDraft] = None
    confirmed: Optional[EnhancedContextDraft] = None
    metadata: EnhancedContextMetadata = Field(default_factory=EnhancedContextMetadata)


# ==================== API Request Models ====================

class CreateBootstrapProjectRequest(BaseModel):
    """Request to create a new bootstrap project."""
    project_name: str = Field(..., min_length=1, max_length=255)
    idea_text: Optional[str] = Field(None, description="Initial idea description text")
    # Note: PDF files are handled via Form/UploadFile, not JSON body


class SubmitAnswersRequest(BaseModel):
    """Request to submit clarifying question answers."""
    answers: List[ClarifyingAnswer]


class ConfirmContextRequest(BaseModel):
    """Request to confirm (possibly edited) enhanced context."""
    confirmed_context: EnhancedContextDraft


# ==================== API Response Models ====================

class BootstrapProjectResponse(BaseModel):
    """Response after creating a bootstrap project."""
    success: bool
    project_id: str
    project_name: str
    context_status: str
    message: str


class QuestionsResponse(BaseModel):
    """Response containing clarifying questions."""
    success: bool
    project_id: str
    context_status: str
    questions: List[ClarifyingQuestion]
    message: str


class AnswersSubmittedResponse(BaseModel):
    """Response after submitting answers."""
    success: bool
    project_id: str
    context_status: str
    message: str


class EnhancedContextResponse(BaseModel):
    """Response containing the enhanced context."""
    success: bool
    project_id: str
    context_status: str
    enhanced_context: Optional[EnhancedContext] = None
    message: str


class ContextConfirmedResponse(BaseModel):
    """Response after confirming context."""
    success: bool
    project_id: str
    context_status: str
    context_version: int
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
