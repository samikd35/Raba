"""
Problem Generator Graph State Definition

This module defines the state structure for the Problem Generator LangGraph workflow.
Following the existing patterns from the MIntel codebase.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProblemGraphState(BaseModel):
    """
    State schema for the Problem Generator agent graph.
    
    This follows the "Cause → Effect + Context" agent graph (v2.1) specification
    and maintains consistency with existing MIntel agent patterns.
    """
    
    # =============================================
    # INPUT PARAMETERS
    # =============================================
    
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="User input parameters from the API request"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier for authentication and tracking"
    )
    
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for AI usage monitoring and billing"
    )
    
    project_id: Optional[str] = Field(
        default=None,
        description="Project identifier for tracking AI usage per project"
    )
    
    job_id: Optional[str] = Field(
        default=None,
        description="Unique job identifier for tracking"
    )
    
    # =============================================
    # QUERY GENERATION
    # =============================================
    
    queries: List[str] = Field(
        default_factory=list,
        description="Generated search queries from parameters (10-15 queries)"
    )
    
    # =============================================
    # SEARCH RESULTS
    # =============================================
    
    docs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Scraped web pages from search results"
    )
    
    passages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted passages from web + DB with UUID-based source tracking"
    )
    
    db_hits: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results from curated database search"
    )
    
    web_hits: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results from live web search (news + deep)"
    )
    
    # =============================================
    # ENHANCED SOURCE TRACKING
    # =============================================
    
    source_registry: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="UUID-based registry of all sources with rich metadata"
    )
    
    scraped_content: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Scraped content with enhanced source metadata"
    )
    
    embedded_passages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Passages with embeddings and UUID source references"
    )
    
    # =============================================
    # PROCESSING RESULTS
    # =============================================
    
    clusters: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Clustered passages by similarity with UUID source tracking"
    )
    
    micro_stories: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Generated micro-stories with rich source citations"
    )
    
    refined_statements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Problem statements with embedded numbered citations"
    )
    
    filtered_statements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Quality-filtered statements with source validation"
    )
    
    ranked_statements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relevance-ranked statements with citation metadata"
    )
    
    problems: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Generated problem statements before final curation"
    )
    
    final: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top 3-5 curated problem statements with supporting sources"
    )
    
    # =============================================
    # WORKFLOW CONTROL
    # =============================================
    
    status: str = Field(
        default="pending",
        description="Current workflow status: pending, processing, completed, failed"
    )
    
    current_node: Optional[str] = Field(
        default=None,
        description="Currently executing node name"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if workflow fails"
    )
    
    # =============================================
    # CONFIGURATION
    # =============================================
    
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime configuration for agents"
    )
    
    # =============================================
    # METRICS AND TRACKING
    # =============================================
    
    start_time: Optional[datetime] = Field(
        default=None,
        description="Workflow start timestamp"
    )
    
    end_time: Optional[datetime] = Field(
        default=None,
        description="Workflow completion timestamp"
    )
    
    processing_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance and processing metrics"
    )
    
    # =============================================
    # SEARCH METADATA
    # =============================================
    
    search_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata from search operations"
    )
    
    embeddings_cache: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Cached embeddings to avoid regeneration"
    )
    
    # =============================================
    # QUALITY CONTROL
    # =============================================
    
    validation_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results from quality validation checks"
    )
    
    filtered_problems: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Problems filtered out during quality control"
    )
    
    # =============================================
    # HELPER METHODS
    # =============================================
    
    def get_processing_time_ms(self) -> Optional[int]:
        """Calculate processing time in milliseconds."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None
    
    def add_processing_metric(self, node_name: str, metric_name: str, value: Any):
        """Add a processing metric for a specific node."""
        if node_name not in self.processing_metrics:
            self.processing_metrics[node_name] = {}
        self.processing_metrics[node_name][metric_name] = value
    
    def get_node_metric(self, node_name: str, metric_name: str) -> Any:
        """Get a specific metric for a node."""
        return self.processing_metrics.get(node_name, {}).get(metric_name)
    
    def update_status(self, status: str, current_node: Optional[str] = None):
        """Update workflow status and current node."""
        self.status = status
        if current_node:
            self.current_node = current_node
    
    def set_error(self, error_message: str):
        """Set error status and message."""
        self.status = "failed"
        self.error = error_message
        self.end_time = datetime.now()
    
    def is_completed(self) -> bool:
        """Check if workflow is completed successfully."""
        return self.status == "completed" and len(self.final) > 0
    
    def is_failed(self) -> bool:
        """Check if workflow has failed."""
        return self.status == "failed"
    
    def get_final_problems_count(self) -> int:
        """Get count of final curated problems."""
        return len(self.final)
    
    def get_total_passages_count(self) -> int:
        """Get total count of extracted passages."""
        return len(self.passages)
    
    def get_search_results_summary(self) -> Dict[str, int]:
        """Get summary of search results."""
        return {
            "db_hits": len(self.db_hits),
            "web_hits": len(self.web_hits),
            "total_docs": len(self.docs),
            "total_passages": len(self.passages),
            "clusters": len(self.clusters),
            "problems": len(self.problems),
            "final": len(self.final)
        }

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
