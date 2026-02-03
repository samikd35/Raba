"""
Data models for analysis agents and workflow state.

Provides Pydantic models for structured analysis output and LangGraph state management.
"""

from typing import Dict, Any, List, Optional, Literal, TypedDict, Union
from typing_extensions import Annotated
from pydantic import BaseModel, Field
from datetime import datetime
import operator


class AnalysisOutput(BaseModel):
    """Structured output for individual analysis results with fact validation."""
    
    claim: str = Field(description="Main claim or finding from the analysis")
    accuracy_level: Literal["high", "medium", "low"] = Field(
        description="Confidence level in the analysis result"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting the claim from research data"
    )
    debunking_evidence: Optional[List[str]] = Field(
        default_factory=list,
        description="Evidence that contradicts or weakens the claim"
    )
    statistical_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Quantitative data extracted from research including fact validation"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Numerical confidence score between 0 and 1 (adjusted by fact validation)"
    )
    
    # New fields for enhanced fact validation
    citation_ids: List[str] = Field(
        default_factory=list,
        description="All citation IDs used in analysis for traceability"
    )
    persona_relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Relevance to target persona (0.0-1.0)"
    )
    fact_validation_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Fact-checking validation score (0.0-1.0)"
    )
    validation_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed fact validation results and metadata"
    )


class StatisticsRegistryEntry(BaseModel):
    """Registry entry for a single statistic in the two-tier RAG system."""
    
    statistic_id: str = Field(description="Unique identifier")
    source_type: Literal["csv", "pdf"] = Field(description="Type of data source")
    source_file: str = Field(description="Original filename")
    data_path: str = Field(description="Path to data within source")
    value: Union[float, int, str] = Field(description="Statistical value")
    context: str = Field(description="Contextual description")
    citation_id: str = Field(description="Citation identifier")
    persona_associations: List[str] = Field(
        default_factory=list,
        description="Associated persona IDs"
    )
    verification_hash: str = Field(description="Hash for integrity verification")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )


class PersonaDataAssociation(BaseModel):
    """Association between data and personas in the two-tier RAG system."""
    
    persona_id: str = Field(description="Persona identifier")
    data_id: str = Field(description="Data identifier")
    association_type: Literal["explicit", "inferred", "general"] = Field(
        description="Type of association"
    )
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="Relevance score between data and persona"
    )
    confidence_level: Literal["high", "medium", "low"] = Field(
        description="Confidence in the association"
    )
    reasoning: str = Field(description="Why this association was made")


class AssumptionValidation(BaseModel):
    """Complete validation result for a single assumption."""
    
    assumption_id: str = Field(description="Unique identifier for the assumption")
    assumption_text: str = Field(description="Full text of the assumption being validated")
    persona_name: str = Field(description="Name of the persona this assumption relates to")
    validation_status: Literal["validated", "partially_validated", "invalidated"] = Field(
        description="Overall validation status based on all analyses"
    )
    analyses: Dict[str, AnalysisOutput] = Field(
        default_factory=dict,
        description="Results from each analysis type (pain, size, solution, gains, jtbd)"
    )
    overall_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Overall confidence score across all analyses"
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="Key insights and findings from the analysis"
    )


def merge_dicts(x: Dict[str, Any], y: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with y taking precedence over x."""
    if not x:
        return y
    if not y:
        return x
    return {**x, **y}

class AssumptionAnalysisState(TypedDict):
    """Enhanced LangGraph state for assumption analysis workflow with two-tier RAG and fact validation."""
    
    # Project context - these fields might be accessed by multiple parallel nodes
    project_id: Annotated[str, lambda x, y: y if y else x]
    tenant_id: Annotated[str, lambda x, y: y if y else x]
    
    # VMP context - these might be updated by parallel nodes
    project_context: Annotated[Dict[str, Any], merge_dicts]
    current_assumption: Annotated[Dict[str, Any], lambda x, y: y if y is not None else x]  # Replace, don't merge
    target_persona: Annotated[Dict[str, Any], lambda x, y: y if y is not None else x]  # Replace, don't merge
    
    # Research data - might be accessed by parallel nodes
    research_chunks: Annotated[List[Dict[str, Any]], lambda x, y: y if y else x]
    
    # Enhanced fields for statistics registry and two-tier RAG
    statistics_registry: Annotated[Dict[str, Any], merge_dicts]  # From research_documents_data.statistics_registry
    persona_data_associations: Annotated[Dict[str, List[str]], merge_dicts]  # From statistics_registry.persona_mappings
    current_ground_truth: Annotated[Dict[str, Any], merge_dicts]  # Filtered from statistics_registry
    current_evidence_chunks: Annotated[List[Dict[str, Any]], lambda x, y: y if y else x]  # Filtered research_chunks
    citation_registry: Annotated[Dict[str, Any], merge_dicts]  # From statistics_registry.citation_registry
    
    # Analysis results per assumption (accumulated with concurrent updates)
    assumption_analyses: Annotated[List[Dict[str, Any]], operator.add]
    
    # Current assumption analysis (updated concurrently by parallel agents)
    current_assumption_analysis: Annotated[Dict[str, Any], merge_dicts]
    
    # Enhanced analysis metadata
    fact_validation_results: Annotated[Dict[str, Any], merge_dicts]  # Added to analysis output
    generated_visualizations: Annotated[Dict[str, Any], merge_dicts]  # Stored in analysis_data.generated_visualizations
    
    # Report generation - might be updated by parallel nodes
    report_sections: Annotated[Dict[str, Any], merge_dicts]
    structured_report: Annotated[Optional[Dict[str, Any]], lambda x, y: y if y is not None else x]  # 🚀 JSON ONLY
    final_report: Annotated[str, lambda x, y: y if y else x]  # DEPRECATED: Kept for backward compatibility
    
    # Control flow - might be accessed by parallel nodes
    current_step: Annotated[str, lambda x, y: y if y else x]
    processed_assumptions: Annotated[List[str], lambda x, y: list(set(x + y))]  # Avoid duplicates
    errors: Annotated[List[str], operator.add]


class AnalysisContext(BaseModel):
    """Enhanced context data passed to analysis agents with two-tier RAG support."""
    
    assumption: Dict[str, Any] = Field(description="Assumption being analyzed")
    persona: Dict[str, Any] = Field(description="Target persona")
    research_data: List[Dict[str, Any]] = Field(description="Relevant research chunks (Tier 2)")
    project_context: Dict[str, Any] = Field(description="Full project context")
    analysis_type: str = Field(description="Type of analysis being performed")
    
    # Enhanced fields for two-tier RAG
    ground_truth_statistics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed statistics from registry (Tier 1)"
    )
    evidence_chunks: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Balanced evidence chunks with source representation (Tier 2)"
    )
    persona_relevance_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Persona-specific data associations and relevance scores"
    )
    citation_registry: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Citation registry for fact validation and traceability"
    )
    statistics_registry: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Statistics registry from workflow state for fact validation"
    )

    context_flags: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Flags describing context quality (e.g., partial ground truth)"
    )

    # Backward compatibility
    def get_research_data(self) -> List[Dict[str, Any]]:
        """Get research data with backward compatibility."""
        return self.evidence_chunks or self.research_data