"""
Data Models for GTM Strategy Generator

Contains Pydantic models for:
- LangGraph state schema
- GTM step specifications and content
- Citations (project and web)
- API request/response models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# ENUMS
# ============================================================================

class GTMStepType(str, Enum):
    """Types of GTM strategy steps."""
    PROBLEM = "problem"
    AUDIENCE_ICP = "audience_icp"
    MARKET_INSIGHTS = "market_insights"
    VALUE_PROPOSITION = "value_proposition"
    MESSAGING = "messaging"
    CHANNELS = "channels"
    CUSTOMER_SUCCESS = "customer_success"
    GOALS_METRICS = "goals_metrics"


class EvidenceGrade(str, Enum):
    """Grade of evidence sufficiency for a step."""
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class NextStep(str, Enum):
    """Next step after evidence grading."""
    WRITE_FROM_PROJECT = "WRITE_FROM_PROJECT"
    DO_WEB_RESEARCH = "DO_WEB_RESEARCH"
    WRITE_WITH_ASSUMPTIONS = "WRITE_WITH_ASSUMPTIONS"


class GTMGenerationStatus(str, Enum):
    """Status of GTM generation."""
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# GTM STEP CONTENT MODELS
# ============================================================================

class Experiment(BaseModel):
    """A single experiment in the GTM plan."""
    name: str = Field(..., description="Experiment name")
    hypothesis: str = Field(..., description="What we're testing")
    method: str = Field(..., description="How we'll test it")
    success_metric: str = Field(..., description="How we'll measure success")
    duration_days: int = Field(default=14, description="Duration in days")


class GTMStepContent(BaseModel):
    """Generated content for a single GTM step."""
    step: int = Field(..., description="Step number (1-8)")
    name: str = Field(..., description="Step name")
    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="Step content: decisions, plan, experiments"
    )
    description: str = Field(
        ...,
        description="Rationale + citation markers [P#]/[W#] + assumptions applied"
    )
    sources_used: List[str] = Field(
        default_factory=list,
        description="Citation IDs used (P1, W1, etc.)"
    )
    assumptions_applied: List[str] = Field(
        default_factory=list,
        description="Assumptions made when evidence was incomplete"
    )


# ============================================================================
# EXECUTION LAYER MODELS
# ============================================================================

class MilestoneAction(BaseModel):
    """A milestone or action in the execution plan."""
    week: int = Field(..., description="Week number")
    milestone: str = Field(..., description="What to achieve")
    actions: List[str] = Field(default_factory=list, description="Specific actions")
    owner: Optional[str] = Field(None, description="Responsible party")
    success_criteria: Optional[str] = Field(None, description="How to know it's done")


class ExecutionPlan30_60_90(BaseModel):
    """30/60/90-day execution plan."""
    days_0_30: List[MilestoneAction] = Field(
        default_factory=list,
        description="First 30 days milestones"
    )
    days_31_60: List[MilestoneAction] = Field(
        default_factory=list,
        description="Days 31-60 milestones"
    )
    days_61_90: List[MilestoneAction] = Field(
        default_factory=list,
        description="Days 61-90 milestones"
    )


class ChannelExperiment(BaseModel):
    """A channel experiment in the backlog."""
    channel: str = Field(..., description="Channel name")
    hypothesis: str = Field(..., description="What we expect")
    test_design: str = Field(..., description="How to test")
    budget: Optional[str] = Field(None, description="Budget required")
    duration_days: int = Field(default=14, description="Test duration")
    success_metric: str = Field(..., description="Success criteria")
    priority: str = Field(default="medium", description="high/medium/low")


class MessagingExperiment(BaseModel):
    """A messaging experiment in the backlog."""
    message_variant: str = Field(..., description="Message variation")
    target_persona: str = Field(..., description="Target persona")
    channel: str = Field(..., description="Where to test")
    hypothesis: str = Field(..., description="Expected outcome")
    success_metric: str = Field(..., description="Success criteria")


class ExperimentBacklog(BaseModel):
    """Backlog of experiments to run."""
    channel_experiments: List[ChannelExperiment] = Field(
        default_factory=list,
        description="Channel experiments to run"
    )
    messaging_experiments: List[MessagingExperiment] = Field(
        default_factory=list,
        description="Messaging experiments to run"
    )


class FunnelKPI(BaseModel):
    """A funnel KPI in the metrics dashboard."""
    stage: str = Field(..., description="Funnel stage (awareness, activation, retention)")
    metric_name: str = Field(..., description="KPI name")
    current_value: Optional[str] = Field(None, description="Current baseline")
    target_30: Optional[str] = Field(None, description="30-day target")
    target_60: Optional[str] = Field(None, description="60-day target")
    target_90: Optional[str] = Field(None, description="90-day target")


class MetricsDashboardSpec(BaseModel):
    """Metrics dashboard specification."""
    north_star: str = Field(..., description="North star metric")
    north_star_rationale: str = Field(..., description="Why this metric")
    funnel_kpis: List[FunnelKPI] = Field(
        default_factory=list,
        description="Funnel KPIs by stage"
    )
    targets_30_60_90: Dict[str, Any] = Field(
        default_factory=dict,
        description="Target values for 30/60/90 days"
    )


# ============================================================================
# CHANNEL & CUSTOMER SUCCESS MODELS
# ============================================================================

class ChannelPlan(BaseModel):
    """Channel plan with prioritization."""
    prioritized_channels: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Channels ranked by priority"
    )
    channel_to_funnel_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Which funnel stage each channel serves"
    )
    channel_experiments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="2-week channel tests"
    )


class CustomerSuccessMotion(BaseModel):
    """Customer success methodology."""
    motion_type: str = Field(
        ...,
        description="self-serve / assisted / partner-led"
    )
    motion_rationale: str = Field(..., description="Why this motion")
    onboarding_milestones: List[str] = Field(
        default_factory=list,
        description="Key onboarding milestones"
    )
    retention_loops: List[str] = Field(
        default_factory=list,
        description="Retention mechanisms"
    )
    success_metrics: List[str] = Field(
        default_factory=list,
        description="Success metrics for CS"
    )


# ============================================================================
# CITATION MODELS
# ============================================================================

class ProjectCitation(BaseModel):
    """Citation for project artifact evidence."""
    id: str = Field(..., description="Reference ID (P1, P2, etc.)")
    type: Literal["project"] = "project"
    artifact_ref: str = Field(..., description="Artifact type reference")
    artifact_version: Optional[int] = Field(None, description="Artifact version (v1 or v2)")
    chunk_ref: str = Field(..., description="Chunk ID reference")
    snippet: str = Field(..., description="Evidence snippet")


class WebCitation(BaseModel):
    """Citation for web evidence."""
    id: str = Field(..., description="Reference ID (W1, W2, etc.)")
    type: Literal["web"] = "web"
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    domain: str = Field(..., description="Source domain")
    snippet: str = Field(..., description="Evidence snippet")
    fetched_at: str = Field(..., description="ISO timestamp when fetched")
    published_at: Optional[str] = Field(None, description="Publication date if known")


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
    """Trace information for a GTM generation run."""
    retrieval_queries: List[Dict[str, Any]] = Field(default_factory=list)
    web_queries: List[str] = Field(default_factory=list)
    web_urls_fetched: List[str] = Field(default_factory=list)
    latency_ms: int = Field(default=0)
    tokens_used: int = Field(default=0)
    node_executions: List[Dict[str, Any]] = Field(default_factory=list)
    llm_calls: int = Field(default=0)


# ============================================================================
# CONSISTENCY CHECK MODELS
# ============================================================================

class ConsistencyIssue(BaseModel):
    """Issue found in cross-step consistency check."""
    type: str = Field(..., description="INCONSISTENT|UNSUPPORTED|GAP")
    where: str = Field(..., description="Step name where issue found")
    detail: str = Field(..., description="Description of issue")
    suggested_fix: str = Field(..., description="Suggested resolution")


class AutoFix(BaseModel):
    """Automatic fix applied during consistency check."""
    where: str = Field(..., description="Step being fixed")
    field: str = Field(..., description="Field being fixed (content or description)")
    original: str = Field(..., description="Original text")
    replacement: str = Field(..., description="New text")


# ============================================================================
# GTM STRATEGY PACK (FULL OUTPUT)
# ============================================================================

class GTMStrategyPack(BaseModel):
    """Complete GTM Strategy Pack output."""
    version: int = Field(..., description="Version number")
    summary: str = Field(..., description="1-2 paragraph executive summary")
    steps: List[GTMStepContent] = Field(
        default_factory=list,
        description="8 GTM steps with content"
    )
    channel_plan: ChannelPlan = Field(
        default_factory=ChannelPlan,
        description="Prioritized channel plan"
    )
    customer_success_motion: CustomerSuccessMotion = Field(
        default_factory=lambda: CustomerSuccessMotion(
            motion_type="assisted",
            motion_rationale="Default motion"
        ),
        description="Customer success methodology"
    )
    metrics_plan: MetricsDashboardSpec = Field(
        default_factory=lambda: MetricsDashboardSpec(
            north_star="TBD",
            north_star_rationale="To be determined"
        ),
        description="Metrics dashboard spec"
    )
    execution_plan_30_60_90: ExecutionPlan30_60_90 = Field(
        default_factory=ExecutionPlan30_60_90,
        description="30/60/90-day execution plan"
    )
    experiment_backlog: ExperimentBacklog = Field(
        default_factory=ExperimentBacklog,
        description="Experiment backlog"
    )
    sources: List[Union[ProjectCitation, WebCitation]] = Field(
        default_factory=list,
        description="All citations"
    )
    run_trace: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generation trace"
    )
    consistency_check_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results of consistency check"
    )
    status: str = Field(default="completed", description="Generation status")
    error_message: Optional[str] = Field(None, description="Error if failed")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: Optional[str] = Field(None, description="User ID")


class GTMData(BaseModel):
    """Full GTM data stored in vmp_projects.gtm_data."""
    current_version: int = Field(default=0, description="Latest version number")
    versions: List[GTMStrategyPack] = Field(default_factory=list, description="All versions")


# ============================================================================
# LANGGRAPH STATE
# ============================================================================

class GTMState(TypedDict, total=False):
    """LangGraph state for GTM generation workflow."""
    # Inputs
    project_id: str
    tenant_id: str
    user_id: str
    context_constraints: Dict[str, Any]  # geography, timeline, budget, etc.
    
    # Project Context
    project_summary: str
    project_name: str
    project_description: str
    available_artifacts: List[str]
    artifact_version_map: Dict[str, int]  # Track latest versions (v2 preferred)
    enhanced_context: Dict[str, Any]  # From requirement generator
    
    # GTM Planning
    gtm_steps_plan: List[Dict[str, Any]]  # 8 steps with deliverables
    execution_layer_plan: Dict[str, Any]  # What to include
    
    # Current Step Processing
    current_step_index: int
    current_step_spec: Dict[str, Any]
    current_retrieval_query: str
    current_artifact_hints: List[str]
    current_project_evidence: List[Dict[str, Any]]
    current_web_evidence: List[Dict[str, Any]]
    current_evidence_grade: str
    current_missing_items: List[str]
    current_next_step: str
    
    # Web Research
    web_queries: List[str]
    extraction_targets: List[str]
    
    # Accumulated Steps
    steps_draft: List[Dict[str, Any]]
    all_project_citations: List[Dict[str, Any]]
    all_web_citations: List[Dict[str, Any]]
    
    # Final Output
    gtm_pack: Dict[str, Any]
    consistency_issues: List[Dict[str, Any]]
    auto_fixes: List[Dict[str, Any]]
    
    # Trace
    tool_trace: Dict[str, Any]
    start_time: str
    
    # Output
    gtm_version: int
    generation_status: str
    error_message: Optional[str]


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class GenerateGTMRequest(BaseModel):
    """Request to generate a GTM strategy."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "geography_focus": "",
                "launch_timeline": "",
                "budget_band": "",
                "target_segment_priority": "",
                "deck_purpose_alignment": "",
                "product_stage": "",
            }
        }
    )

    geography_focus: Optional[str] = Field(
        None,
        description="Target geography (e.g., 'Ethiopia', 'East Africa')"
    )
    launch_timeline: Optional[str] = Field(
        None,
        description="Launch timeline (e.g., 'Q1 2025', '3 months')"
    )
    budget_band: Optional[str] = Field(
        None,
        description="Budget range (e.g., '$10k-50k', 'bootstrap')"
    )
    target_segment_priority: Optional[str] = Field(
        None,
        description="Priority segment to target first"
    )
    deck_purpose_alignment: Optional[str] = Field(
        None,
        description="Align with deck purpose: 'fundraising' or 'sales'"
    )
    product_stage: Optional[str] = Field(
        None,
        description="Product stage: 'ideation', 'mvp', 'growth'"
    )


class GenerateGTMResponse(BaseModel):
    """Response after triggering GTM generation."""
    gtm_id: str = Field(..., description="Project ID (GTM stored in project)")
    version: int = Field(..., description="Version being generated")
    status: str = Field(..., description="Generation status")
    message: str = Field(..., description="Status message")


class GTMPackResponse(BaseModel):
    """Full GTM pack response."""
    project_id: str
    version: int
    summary: str
    steps: List[GTMStepContent]
    channel_plan: Dict[str, Any]
    customer_success_motion: Dict[str, Any]
    metrics_plan: Dict[str, Any]
    execution_plan_30_60_90: Dict[str, Any]
    experiment_backlog: Dict[str, Any]
    sources: List[Union[ProjectCitation, WebCitation]]
    created_at: str
    created_by: Optional[str]
    run_trace: Optional[Dict[str, Any]] = None


class GTMVersionSummary(BaseModel):
    """Summary of a GTM version for listing."""
    version: int
    summary: str
    step_count: int
    status: str
    created_at: str
    created_by: Optional[str]


class GTMVersionListResponse(BaseModel):
    """Response for listing GTM versions."""
    project_id: str
    current_version: int
    versions: List[GTMVersionSummary]
    total_count: int


class GTMStatusResponse(BaseModel):
    """Status of GTM generation."""
    project_id: str
    version: int
    status: str
    message: str
    progress: Optional[Dict[str, Any]] = None


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

class GTMConfig(BaseModel):
    """Configuration for GTM generation."""
    max_web_queries_per_step: int = Field(default=4)
    max_web_results_per_query: int = Field(default=5)
    rag_top_k: int = Field(default=10)
    max_steps: int = Field(default=8)
    include_30_60_90_plan: bool = Field(default=True)
    include_experiment_backlog: bool = Field(default=True)
    include_metrics_dashboard: bool = Field(default=True)


DEFAULT_GTM_CONFIG = GTMConfig()


# ============================================================================
# GTM STEP TO ARTIFACT MAPPING
# ============================================================================

GTM_STEP_ARTIFACT_HINTS = {
    "problem": [
        "vmp_market_research",
        "vmp_hypothesis",
        "vmp_assumptions",
        "vmp_customer_profile_v2",
    ],
    "audience_icp": [
        "vmp_persona",
        "vmp_customer_profile_v2",
        "vmp_customer_profile",
        "vmp_questionnaire",
    ],
    "market_insights": [
        "vmp_market_research",
    ],  # web_allowed
    "value_proposition": [
        "vmp_vps_v2",
        "vmp_vps_v1",
        "vmp_value_map",
        "vmp_soln_critique",
    ],
    "messaging": [
        "vmp_vps_v2",
        "vmp_customer_profile_v2",
        "vmp_pitch_deck",
        "vmp_persona",
    ],
    "channels": [
        "vmp_bmc_v2",
        "vmp_bmc_v1",
        "vmp_market_research",
        "vmp_questionnaire",
    ],  # web_allowed
    "customer_success": [
        "vmp_bmc_v2",
        "vmp_mvp_requirements",
        "vmp_soln_critique",
    ],
    "goals_metrics": [
        "vmp_hypothesis",
        "vmp_assumptions",
        "vmp_mvp_requirements",
        "vmp_market_research",
    ],
}

# Steps that allow web research
GTM_STEPS_WEB_ALLOWED = {"market_insights", "channels"}

# Version priority boost for artifact types (v2 preferred)
VERSION_PRIORITY_BOOST = {
    "vmp_bmc_v2": 0.20,
    "vmp_vps_v2": 0.20,
    "vmp_customer_profile_v2": 0.15,
    "vmp_mvp_requirements": 0.12,
    "vmp_market_research": 0.12,
    "vmp_soln_critique": 0.10,
    "vmp_pitch_deck": 0.08,
    "vmp_bmc_v1": 0.05,
    "vmp_vps_v1": 0.05,
    "vmp_customer_profile": 0.03,
}

# Section penalty (reduce score for metadata-heavy sections)
SECTION_PENALTY = {
    "sources": -0.20,
    "references": -0.20,
    "metadata": -0.15,
}
