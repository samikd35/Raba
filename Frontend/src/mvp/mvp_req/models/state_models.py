"""
State Models for MVP Requirements Generator (AMRG)

These models define the state structure for the LangGraph workflow
and intermediate data structures.
"""

from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime

from .enums import TemplateCode, ResearchMode, RunStatus, QuestionCategory, ValidationStatus


class ArtifactData(TypedDict, total=False):
    """Individual artifact data structure."""
    data: Dict[str, Any]
    version: str
    generated_at: Optional[str]


class ContextPack(TypedDict):
    """
    Authoritative context loaded from project artifacts.
    
    Contains all business-definition artifacts needed for PRD generation.
    """
    project_id: str
    tenant_id: str
    
    # Required artifacts
    artifacts: Dict[str, ArtifactData]  # vps_v1, bmc_v1, solution_critique, vps_v2, bmc_v2
    
    # Optional artifacts (per user request - use if exists)
    optional_artifacts: Dict[str, ArtifactData]  # vpc_v2
    
    # Project metadata
    metadata: Dict[str, Any]  # project_title, project_description, industry, geography


class TemplateCandidate(TypedDict):
    """A candidate template from routing."""
    code: str  # TemplateCode value
    confidence: float  # 0.0 - 1.0
    rationale: str
    key_signals: List[str]  # Signals from context that led to this choice


class TemplateRoutingResult(TypedDict):
    """Result from template routing (coarse or final)."""
    top_templates: List[TemplateCandidate]
    confidence_threshold_met: bool
    ambiguity_points: List[str]  # Areas of uncertainty
    routing_rationale: str


class ClarifyingQuestion(TypedDict):
    """A clarifying question for the user."""
    q_index: int  # 1, 2, or 3
    question_text: str
    category: str  # QuestionCategory value
    purpose: str  # Why this question is being asked
    relates_to_templates: List[str]  # Template codes this question helps disambiguate


class ClarifyingAnswer(TypedDict):
    """User's answer to a clarifying question."""
    q_index: int
    answer_text: str
    answered_at: str  # ISO timestamp


class ResearchPlan(TypedDict, total=False):
    """Plan for optional web research."""
    should_research: bool
    max_queries: int
    max_sources: int
    extraction_targets: List[str]
    research_queries: List[Dict[str, Any]]


class ResearchResult(TypedDict):
    """Result from web research."""
    sources: List[Dict[str, Any]]  # url, title, snippet
    findings: List[Dict[str, Any]]  # extracted notes
    queries_executed: int


class ValidationReport(TypedDict):
    """Schema validation report."""
    status: str  # ValidationStatus value
    errors: List[Dict[str, Any]]
    warnings: List[str]
    repair_attempts: int


class PRDOutput(TypedDict):
    """Generated PRD JSON output."""
    template_code: str
    template_version: str
    schema_version: str
    purpose: Dict[str, Any]
    objective: Dict[str, Any]
    scope: Dict[str, Any]
    must_have_features: Dict[str, Any]
    nice_to_have_features: Dict[str, Any]
    critical_workflows: Dict[str, Any]
    constraints: Dict[str, Any]
    success_signals: Dict[str, Any]
    assumptions_and_risks: Dict[str, Any]
    source_artifacts_used: Dict[str, str]
    research: Optional[ResearchResult]


class AMRGState(TypedDict, total=False):
    """
    LangGraph state for AMRG workflow.
    
    This is the complete state object passed through all workflow nodes.
    """
    # Identity
    run_id: str
    tenant_id: str
    project_id: str
    user_id: str
    
    # Configuration
    research_mode: str  # ResearchMode value
    
    # Context (from ContextLoaderNode)
    context_pack: ContextPack
    eligibility_passed: bool
    eligibility_errors: List[str]
    
    # Coarse Routing (from TypeRouterCoarseNode)
    coarse_routing: TemplateRoutingResult
    
    # Clarification (from ClarifyingQuestionNode)
    clarifying_questions: List[ClarifyingQuestion]
    clarifying_answers: List[ClarifyingAnswer]
    
    # Final Routing (from TypeRouterFinalNode)
    selected_template_code: str  # Final locked template
    final_routing: TemplateRoutingResult
    template_spec_ref: Dict[str, Any]  # Resolved TemplateSpec
    
    # Research (optional, from ResearchPlannerNode + WebResearchLoopNode)
    research_plan: ResearchPlan
    research_results: ResearchResult
    
    # Output (from PRDGenerationNode)
    prd_json: PRDOutput
    
    # Validation (from SchemaValidationNode + RepairNode)
    validation_report: ValidationReport
    repair_attempts: int
    
    # Persistence
    thread_id: str
    status: str  # RunStatus value
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    error: Optional[str]


class AMRGRunRecord(TypedDict):
    """
    Database record for an AMRG run.
    
    Stored in vmp_projects.mvp_data.amrg or separate amrg_runs table.
    """
    id: str  # run_id
    tenant_id: str
    project_id: str
    user_id: str
    status: str
    
    # Coarse routing
    coarse_top_templates: List[Dict[str, Any]]
    coarse_confidence_map: Dict[str, float]
    coarse_rationale: str
    
    # Final routing
    selected_template_code: Optional[str]
    final_confidence: Optional[float]
    final_rationale: Optional[str]
    
    # Version info
    template_version: Optional[str]
    schema_version: Optional[str]
    
    # Configuration
    research_mode: str
    
    # State
    thread_id: str
    state_json: Dict[str, Any]
    
    # Timestamps
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    
    # Error handling
    error_code: Optional[str]
    error_message: Optional[str]


class AMRGQnARecord(TypedDict):
    """Database record for Q&A."""
    run_id: str
    q_index: int
    question_text: str
    question_category: str
    answer_text: Optional[str]
    answered_at: Optional[str]


class AMRGOutputRecord(TypedDict):
    """Database record for PRD output versions."""
    run_id: str
    version: int
    prd_json: Dict[str, Any]
    validation_report_json: Dict[str, Any]
    created_at: str
