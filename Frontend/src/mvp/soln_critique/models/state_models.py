"""
State models for Solution Critique workflow

These models define the state structure for the LangGraph workflow
and individual critique components.
"""
from typing import Dict, Any, List, Optional, TypedDict


class SolutionCritiqueState(TypedDict):
    """LangGraph state for solution critique workflow"""
    
    # Project context
    project_id: str
    tenant_id: str
    user_id: str
    session_id: str
    geography: str
    industry: str
    solution_description: str
    
    # Input data (snapshots from project)
    vpc_data: Dict[str, Any]
    vps_data: Dict[str, Any]
    bmc_data: Dict[str, Any]
    
    # Research phase
    research_queries: List[Dict[str, Any]]
    search_results: Dict[str, List[Dict[str, Any]]]
    
    # Critique results (parallel processing)
    market_critique: Optional[Dict[str, Any]]
    operational_critique: Optional[Dict[str, Any]]
    business_model_critique: Optional[Dict[str, Any]]
    competitive_critique: Optional[Dict[str, Any]]
    technical_critique: Optional[Dict[str, Any]]
    dominant_logic_critique: Optional[Dict[str, Any]]
    
    # Final output
    all_critiques: List[Dict[str, Any]]
    final_report: Optional[Dict[str, Any]]
    
    # Metadata
    status: str
    completed_at: Optional[str]
    error: Optional[str]


class CritiqueResult(TypedDict):
    """Individual critique result structure with citations"""
    critique_id: str
    dimension: str
    section_name: str  # Human-readable section name (e.g., "Market Viability")
    title: str
    severity: str  # high | medium | low
    summary: List[str]  # 3-5 bullet points summarizing the problem
    problem: str  # Text with [1], [2], [3] citations
    sources: List[Dict[str, Any]]  # Numbered sources list
    impact: str  # Impact with citations
    suggestions: List[Dict[str, Any]]  # Suggestions with supporting_sources
    confidence: float
    citation_count: int  # Total citations in critique
    unique_sources_used: int  # Number of unique sources referenced


class SearchQuery(TypedDict):
    """Web search query structure"""
    id: str
    category: str  # market | regulatory | competition | operational | technology
    query: str
    priority: str  # high | medium | low
    rationale: str


class SourceReference(TypedDict):
    """Source reference structure for citations"""
    id: int  # Sequential number for citations
    type: str  # web | bmc | vpc | vps
    # Web source fields
    title: Optional[str]
    url: Optional[str]
    # BMC/VPC/VPS source fields
    field: Optional[str]
    content: Optional[str]
    issue: Optional[str]  # For BMC
    context: Optional[str]  # For VPC/VPS
