"""
Data Models for Pitch Deck Generator

Contains Pydantic models for:
- LangGraph state schema
- Slide specifications and content
- Citations (project and web)
- API request/response models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================

class DeckPurpose(str, Enum):
    """Purpose of the pitch deck."""
    FUNDRAISING = "FUNDRAISING"
    PARTNER_SALES = "PARTNER_SALES"
    DEMO = "DEMO"


class DeckStage(str, Enum):
    """Stage of the startup/project."""
    IDEATION = "IDEATION"
    PRE_SEED = "PRE_SEED"
    SEED = "SEED"
    GROWTH = "GROWTH"


class DeckCategory(str, Enum):
    """Category/type of business."""
    PLATFORM_SAAS = "PLATFORM_SAAS"
    CPG = "CPG"
    INFRA_PROJECT = "INFRA_PROJECT"
    OTHER = "OTHER"


class SlideType(str, Enum):
    """Types of slides in a pitch deck."""
    TITLE = "Title"
    PROBLEM = "Problem"
    SOLUTION = "Solution"
    PRODUCT = "Product"
    MARKET = "Market"
    BUSINESS_MODEL = "BusinessModel"
    GTM = "GTM"
    COMPETITION = "Competition"
    TRACTION = "Traction"
    VALIDATION = "Validation"
    TEAM = "Team"
    FINANCIALS = "Financials"
    ASK = "Ask"
    ROADMAP = "Roadmap"
    RISKS = "Risks"
    IMPACT = "Impact"


class SlidePriority(str, Enum):
    """Priority of a slide in the deck plan."""
    MUST_HAVE = "MUST_HAVE"
    CONDITIONAL = "CONDITIONAL"


class PlaceholderPolicy(str, Enum):
    """Policy for handling missing data in slides."""
    NONE = "NONE"
    TEMPLATE_IF_MISSING = "TEMPLATE_IF_MISSING"
    OMIT_IF_MISSING = "OMIT_IF_MISSING"
    REPLACE_IF_MISSING = "REPLACE_IF_MISSING"


class EvidenceGrade(str, Enum):
    """Grade of evidence sufficiency for a slide."""
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class NextStep(str, Enum):
    """Next step after evidence grading."""
    WRITE_FROM_PROJECT = "WRITE_FROM_PROJECT"
    DO_WEB_RESEARCH = "DO_WEB_RESEARCH"
    PLACEHOLDER_ONLY = "PLACEHOLDER_ONLY"


class DeckGenerationStatus(str, Enum):
    """Status of deck generation."""
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# SLIDE SPECIFICATION MODELS
# ============================================================================

class SlideSpec(BaseModel):
    """Specification for a single slide in the deck plan."""
    slide_type: str = Field(..., description="Type of slide (Problem, Solution, etc.)")
    priority: str = Field(..., description="MUST_HAVE or CONDITIONAL")
    web_allowed: bool = Field(default=False, description="Whether web research is allowed")
    data_requirements: List[str] = Field(default_factory=list, description="Data needed to avoid placeholders")
    placeholder_policy: str = Field(default="NONE", description="Policy for missing data")
    replacement_slide_type: Optional[str] = Field(None, description="Replacement slide if omitted")


class Placeholder(BaseModel):
    """Placeholder field for missing data in a slide."""
    field: str = Field(..., description="Field path (e.g., team.member_1_name)")
    prompt: str = Field(..., description="Prompt text for user to fill")


class SlideContent(BaseModel):
    """Generated content for a single slide."""
    slide_type: str = Field(..., description="Type of slide")
    slide_title: str = Field(..., description="Slide headline (no citations)")
    slide_bullets: List[str] = Field(default_factory=list, description="3-6 bullets (no citations)")
    description: str = Field(..., description="Description with citation markers [P1], [W1]")
    citations_used: List[str] = Field(default_factory=list, description="Citation IDs used")
    placeholders: List[Placeholder] = Field(default_factory=list, description="Fields user must fill")
    warnings: List[str] = Field(default_factory=list, description="Slide-specific warnings")


# ============================================================================
# CITATION MODELS
# ============================================================================

class ProjectCitation(BaseModel):
    """Citation for project artifact evidence."""
    id: str = Field(..., description="Reference ID (P1, P2, etc.)")
    type: Literal["project"] = "project"
    artifact_ref: str = Field(..., description="Artifact type reference")
    artifact_version: Optional[int] = Field(None, description="Artifact version")
    chunk_ref: str = Field(..., description="Chunk ID reference")
    snippet: str = Field(..., description="Evidence snippet")


class WebCitation(BaseModel):
    """Citation for web evidence."""
    id: str = Field(..., description="Reference ID (W1, W2, etc.)")
    type: Literal["web"] = "web"
    url: str = Field(..., description="Source URL")
    domain: str = Field(..., description="Source domain")
    title: str = Field(..., description="Page title")
    snippet: str = Field(..., description="Evidence snippet")
    fetched_at: str = Field(..., description="ISO timestamp when fetched")


# ============================================================================
# EVIDENCE MODELS
# ============================================================================

class ProjectEvidence(BaseModel):
    """Evidence retrieved from project artifacts via RAG."""
    chunk_id: str = Field(..., description="Database ID of the chunk")
    content: str = Field(..., description="Text content of the chunk")
    artifact_type: str = Field(..., description="Type of artifact")
    section: Optional[str] = Field(None, description="Section within artifact")
    chunk_index: int = Field(default=0, description="Index of chunk")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WebEvidence(BaseModel):
    """Evidence extracted from web search results."""
    claim: str = Field(..., description="The factual claim extracted")
    snippet: str = Field(..., description="Supporting text snippet")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    domain: str = Field(..., description="Source domain")
    published_at: Optional[str] = Field(None, description="Publication date")
    fetched_at: str = Field(..., description="When fetched (ISO timestamp)")


# ============================================================================
# RUN TRACE MODEL
# ============================================================================

class RunTrace(BaseModel):
    """Trace information for a deck generation run."""
    retrieval_queries: List[Dict[str, Any]] = Field(default_factory=list)
    web_queries: List[str] = Field(default_factory=list)
    latency_ms: int = Field(default=0)
    tokens_used: int = Field(default=0)
    node_executions: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# DECK VERSION MODEL
# ============================================================================

class DeckVersion(BaseModel):
    """A single version of a generated pitch deck."""
    version: int = Field(..., description="Version number")
    deck_purpose: str = Field(..., description="Purpose of deck")
    stage: str = Field(..., description="Startup stage")
    category: str = Field(..., description="Business category")
    slides: List[SlideContent] = Field(default_factory=list, description="Generated slides")
    citations: List[Union[ProjectCitation, WebCitation]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="Deck-level warnings")
    user_inputs: Dict[str, Any] = Field(default_factory=dict, description="User-provided inputs")
    run_trace: Dict[str, Any] = Field(default_factory=dict, description="Generation trace")
    status: str = Field(default="completed", description="Generation status")
    error_message: Optional[str] = Field(None, description="Error if failed")
    created_at: str = Field(..., description="ISO timestamp")
    created_by: Optional[str] = Field(None, description="User ID")


class PitchDeckData(BaseModel):
    """Full pitch deck data stored in vmp_projects.pitch_deck_data."""
    current_version: int = Field(default=0, description="Latest version number")
    versions: List[DeckVersion] = Field(default_factory=list, description="All versions")


# ============================================================================
# LANGGRAPH STATE
# ============================================================================

class PitchDeckState(TypedDict, total=False):
    """LangGraph state for pitch deck generation workflow."""
    # Inputs
    project_id: str
    tenant_id: str
    user_id: str
    user_hints: Dict[str, Any]
    
    # Project context
    project_summary: str
    project_name: str
    project_description: str
    available_artifacts: List[str]
    detected_category: str  # Auto-detected from project data
    enhanced_context: Dict[str, Any]  # From requirement generator
    
    # Deck planning
    deck_purpose: str
    stage: str
    category: str  # Final category (user override or detected)
    reasoning_brief: str
    missing_inputs: List[str]
    slides_plan: List[Dict[str, Any]]
    deck_warnings: List[str]
    
    # Current slide processing
    current_slide_index: int
    current_slide_spec: Dict[str, Any]
    current_retrieval_query: str
    current_artifact_hints: List[str]
    current_project_evidence: List[Dict[str, Any]]
    current_web_evidence: List[Dict[str, Any]]
    current_evidence_grade: str
    current_missing_items: List[str]
    current_next_step: str
    
    # Web research (if needed)
    web_queries: List[str]
    extraction_targets: List[str]
    
    # Accumulated slides
    slides_draft: List[Dict[str, Any]]
    all_project_citations: List[Dict[str, Any]]
    all_web_citations: List[Dict[str, Any]]
    
    # Final output
    slides_final: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    consistency_issues: List[Dict[str, Any]]
    auto_fixes: List[Dict[str, Any]]
    
    # Run trace
    tool_trace: Dict[str, Any]
    start_time: str
    
    # Output
    deck_version: int
    generation_status: str
    error_message: Optional[str]


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class TeamMember(BaseModel):
    """Team member information."""
    name: str = Field(..., description="Member name")
    role: str = Field(..., description="Role/title")
    bio: Optional[str] = Field(None, description="Short bio/credentials")


class FinancialInputs(BaseModel):
    """Financial assumptions and inputs."""
    pricing_model: Optional[str] = Field(None, description="Pricing model description")
    price_per_unit: Optional[float] = Field(None, description="Price per unit/customer")
    target_customers_y1: Optional[int] = Field(None, description="Target customers year 1")
    costs: Optional[Dict[str, float]] = Field(None, description="Cost breakdown")
    runway_months: Optional[int] = Field(None, description="Current runway in months")
    funding_ask: Optional[float] = Field(None, description="Funding amount requested")
    use_of_funds: Optional[Dict[str, float]] = Field(None, description="Use of funds breakdown")


class TractionMetrics(BaseModel):
    """Traction metrics if available."""
    users: Optional[int] = Field(None, description="Number of users")
    revenue: Optional[float] = Field(None, description="Revenue to date")
    growth_rate: Optional[str] = Field(None, description="Growth rate (e.g., '20% MoM')")
    partnerships: Optional[List[str]] = Field(None, description="Notable partnerships")
    pilots: Optional[List[str]] = Field(None, description="Pilot customers")
    other_metrics: Optional[Dict[str, Any]] = Field(None, description="Other metrics")


class GenerateDeckRequest(BaseModel):
    """Request to generate a pitch deck."""
    deck_purpose: Optional[DeckPurpose] = Field(None, description="Purpose of deck (FUNDRAISING, PARTNER_SALES, DEMO)")
    stage: Optional[DeckStage] = Field(None, description="Startup stage (IDEATION, PRE_SEED, SEED, GROWTH)")
    category: Optional[DeckCategory] = Field(
        None, 
        description="Business category - AUTO-DETECTED from project data (BMC, MVP requirements, enhanced_context). "
                    "Only provide to override auto-detection."
    )
    team_info: Optional[List[TeamMember]] = Field(None, description="Team members")
    financial_inputs: Optional[FinancialInputs] = Field(None, description="Financial data")
    traction_metrics: Optional[TractionMetrics] = Field(None, description="Traction data")
    target_investor_type: Optional[str] = Field(None, description="Target investor type")
    geography: Optional[str] = Field(None, description="Target geography")
    sector: Optional[str] = Field(None, description="Industry sector")


class GenerateDeckResponse(BaseModel):
    """Response after triggering deck generation."""
    deck_id: str = Field(..., description="Project ID (deck stored in project)")
    version: int = Field(..., description="Version being generated")
    status: str = Field(..., description="Generation status")
    message: str = Field(..., description="Status message")


class DeckPackageResponse(BaseModel):
    """Full deck package response."""
    project_id: str
    version: int
    deck_purpose: str
    stage: str
    category: str
    slides: List[SlideContent]
    citations: List[Union[ProjectCitation, WebCitation]]
    warnings: List[str]
    user_inputs: Dict[str, Any]
    created_at: str
    created_by: Optional[str]
    run_trace: Optional[Dict[str, Any]] = None


class DeckVersionSummary(BaseModel):
    """Summary of a deck version for listing."""
    version: int
    deck_purpose: str
    stage: str
    category: str
    slide_count: int
    status: str
    created_at: str
    created_by: Optional[str]


class DeckVersionListResponse(BaseModel):
    """Response for listing deck versions."""
    project_id: str
    current_version: int
    versions: List[DeckVersionSummary]
    total_count: int


class DeckPlanPreviewResponse(BaseModel):
    """Preview of deck plan (slides list only, no content)."""
    project_id: str
    deck_purpose: str
    stage: str
    category: str
    slides_plan: List[SlideSpec]
    warnings: List[str]


class DeckStatusResponse(BaseModel):
    """Status of deck generation."""
    project_id: str
    version: int
    status: str
    message: str
    progress: Optional[Dict[str, Any]] = None


# ============================================================================
# CONSISTENCY CHECK MODELS
# ============================================================================

class ConsistencyIssue(BaseModel):
    """Issue found in cross-slide consistency check."""
    type: str = Field(..., description="CONTRADICTION|UNSUPPORTED_CLAIM|INCONSISTENT_TERM")
    where: str = Field(..., description="Slide type where issue found")
    detail: str = Field(..., description="Description of issue")
    suggested_fix: str = Field(..., description="Suggested resolution")


class AutoFix(BaseModel):
    """Automatic fix applied during consistency check."""
    slide_type: str = Field(..., description="Slide being fixed")
    field: str = Field(..., description="Field being fixed")
    replacement_text: str = Field(..., description="New text")


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

class PitchDeckConfig(BaseModel):
    """Configuration for pitch deck generation."""
    max_bullets_per_slide: int = Field(default=6)
    min_bullets_per_slide: int = Field(default=3)
    max_web_queries_per_slide: int = Field(default=4)
    max_web_results_per_query: int = Field(default=5)
    rag_top_k: int = Field(default=8)
    max_slides: int = Field(default=16)


DEFAULT_PITCH_CONFIG = PitchDeckConfig()


# ============================================================================
# SLIDE TYPE TO ARTIFACT MAPPING
# ============================================================================

SLIDE_ARTIFACT_HINTS = {
    "Title": ["vmp_vps_v2", "vmp_persona"],
    "Problem": ["vmp_market_research", "vmp_customer_profile", "vmp_customer_profile_v2"],
    "Solution": ["vmp_vps_v2", "vmp_vps_v1"],
    "Product": ["vmp_vps_v2", "vmp_mvp_requirements"],
    "Market": ["vmp_market_research"],
    "BusinessModel": ["vmp_bmc_v2", "vmp_bmc_v1"],
    "GTM": ["vmp_bmc_v2", "vmp_assumptions"],
    "Competition": ["vmp_market_research"],
    "Traction": [],  # Only from user inputs
    "Validation": ["vmp_hypothesis", "vmp_questionnaire", "vmp_assumptions"],
    "Team": [],  # Only from user inputs
    "Financials": [],  # Only from user inputs
    "Ask": [],  # Only from user inputs
    "Roadmap": ["vmp_mvp_requirements"],
    "Risks": ["vmp_assumptions", "vmp_market_research"],
    "Impact": ["vmp_vps_v2", "vmp_market_research"],
}
