"""
Vector Storage Models

Pydantic models for vector storage and RAG system supporting module outputs.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

# Source types for different modules
SourceType = Literal[
    'problem_explorer',
    'pv_report',  # Problem Validation Report
    'actionable_insights',
    'vp_map',  # Value Proposition Map
    'mvp_spec',  # MVP Specification
    'mv_analysis',  # Market Validation Analysis
    'solution_critique'  # Solution Critique Report
]

# Document types
DocumentType = Literal['web', 'document', 'api', 'user_input']

# =============================================
# DOCUMENT MODELS
# =============================================

class DocumentBase(BaseModel):
    """Base document model"""
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: Optional[str] = Field(None, description="Document content")
    source_type: SourceType = Field(..., description="Type of source document")
    storage_path: Optional[str] = Field(None, description="File storage path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")

class DocumentCreate(DocumentBase):
    """Model for creating documents"""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    project_id: Optional[uuid.UUID] = Field(None, description="Project ID")
    created_by: uuid.UUID = Field(..., description="User who created the document")

class DocumentUpdate(BaseModel):
    """Model for updating documents"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)

class Document(DocumentBase):
    """Complete document model"""
    id: uuid.UUID = Field(..., description="Document ID")
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    project_id: Optional[uuid.UUID] = Field(None, description="Project ID")
    created_by: uuid.UUID = Field(..., description="User who created the document")
    sha256: Optional[str] = Field(None, description="Content hash")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

# =============================================
# CHUNK MODELS
# =============================================

class ChunkBase(BaseModel):
    """Base chunk model"""
    content: str = Field(..., min_length=1, description="Chunk content")
    token_count: Optional[int] = Field(None, description="Token count in chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")

class ChunkCreate(ChunkBase):
    """Model for creating chunks"""
    doc_id: uuid.UUID = Field(..., description="Parent document ID")
    chunk_index: int = Field(..., ge=0, description="Chunk index in document")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")

class ChunkUpdate(BaseModel):
    """Model for updating chunks"""
    content: Optional[str] = Field(None, min_length=1)
    token_count: Optional[int] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")

class Chunk(ChunkBase):
    """Complete chunk model"""
    id: uuid.UUID = Field(..., description="Chunk ID")
    doc_id: uuid.UUID = Field(..., description="Parent document ID")
    chunk_index: int = Field(..., description="Chunk index in document")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True

# =============================================
# PROBLEM VALIDATION REPORT MODELS
# =============================================

class ProblemValidationReportBase(BaseModel):
    """Base problem validation report model"""
    title: str = Field(..., min_length=1, max_length=500, description="Report title")
    executive_summary: Optional[str] = Field(None, description="Executive summary")
    problem_statement: str = Field(..., min_length=1, description="Problem statement")
    market_analysis: Optional[str] = Field(None, description="Market analysis")
    competitive_analysis: Optional[str] = Field(None, description="Competitive analysis")
    customer_validation: Optional[str] = Field(None, description="Customer validation")
    technical_feasibility: Optional[str] = Field(None, description="Technical feasibility")
    business_model: Optional[str] = Field(None, description="Business model")
    recommendations: Optional[str] = Field(None, description="Recommendations")
    
    # Metadata
    report_type: Literal['market_validation', 'problem_validation', 'solution_validation'] = Field(
        default='problem_validation', description="Type of report"
    )
    industry: Optional[str] = Field(None, description="Industry")
    geography: Optional[str] = Field(None, description="Geography")
    target_audience: Optional[str] = Field(None, description="Target audience")
    
    # Validation metrics
    market_size_estimate: Optional[Dict[str, Any]] = Field(None, description="Market size estimate")
    customer_segments: Optional[Dict[str, Any]] = Field(None, description="Customer segments")
    competitive_landscape: Optional[Dict[str, Any]] = Field(None, description="Competitive landscape")
    risk_assessment: Optional[Dict[str, Any]] = Field(None, description="Risk assessment")

class ProblemValidationReportCreate(ProblemValidationReportBase):
    """Model for creating problem validation reports"""
    session_id: uuid.UUID = Field(..., description="Session ID")
    user_id: uuid.UUID = Field(..., description="User ID")

class ProblemValidationReportUpdate(BaseModel):
    """Model for updating problem validation reports"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    executive_summary: Optional[str] = Field(None)
    problem_statement: Optional[str] = Field(None)
    market_analysis: Optional[str] = Field(None)
    competitive_analysis: Optional[str] = Field(None)
    customer_validation: Optional[str] = Field(None)
    technical_feasibility: Optional[str] = Field(None)
    business_model: Optional[str] = Field(None)
    recommendations: Optional[str] = Field(None)
    status: Optional[Literal['draft', 'in_progress', 'completed', 'archived']] = Field(None)
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)

class ProblemValidationReport(ProblemValidationReportBase):
    """Complete problem validation report model"""
    id: uuid.UUID = Field(..., description="Report ID")
    session_id: uuid.UUID = Field(..., description="Session ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Status
    status: Literal['draft', 'in_progress', 'completed', 'archived'] = Field(
        default='draft', description="Report status"
    )
    completion_percentage: int = Field(default=0, ge=0, le=100, description="Completion percentage")
    
    # File storage
    report_file_path: Optional[str] = Field(None, description="Report file path")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Attachments")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        from_attributes = True

# =============================================
# ACTIONABLE INSIGHTS MODELS
# =============================================

class ActionableInsightBase(BaseModel):
    """Base actionable insight model"""
    insight_type: Literal['opportunity', 'risk', 'trend', 'recommendation', 'alert'] = Field(
        ..., description="Type of insight"
    )
    title: str = Field(..., min_length=1, max_length=500, description="Insight title")
    description: str = Field(..., min_length=1, description="Insight description")
    priority: Literal['low', 'medium', 'high', 'critical'] = Field(
        default='medium', description="Priority level"
    )
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")
    supporting_data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    impact_assessment: Dict[str, Any] = Field(default_factory=dict, description="Impact assessment")
    timeline: Optional[str] = Field(None, description="Timeline")
    resources_required: List[str] = Field(default_factory=list, description="Resources required")
    
    # Enhanced functionality fields
    implementation_steps: List[Dict[str, Any]] = Field(default_factory=list, description="Implementation steps")
    success_metrics: List[Dict[str, Any]] = Field(default_factory=list, description="Success metrics")
    estimated_effort: Optional[str] = Field(None, description="Estimated effort")
    estimated_timeline: Optional[str] = Field(None, description="Estimated timeline")
    tags: List[str] = Field(default_factory=list, description="Tags")
    source_sections: Dict[str, Any] = Field(default_factory=dict, description="Source sections")
    impact_level: Optional[Literal['low', 'medium', 'high', 'transformational']] = Field(
        None, description="Impact level"
    )

class ActionableInsightCreate(ActionableInsightBase):
    """Model for creating actionable insights"""
    report_id: uuid.UUID = Field(..., description="Report ID")
    user_id: uuid.UUID = Field(..., description="User ID")

class ActionableInsightUpdate(BaseModel):
    """Model for updating actionable insights"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[Literal['low', 'medium', 'high', 'critical']] = Field(None)
    status: Optional[Literal['active', 'implemented', 'dismissed', 'archived']] = Field(None)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    user_feedback: Optional[Dict[str, Any]] = Field(None)

class ActionableInsight(ActionableInsightBase):
    """Complete actionable insight model"""
    id: uuid.UUID = Field(..., description="Insight ID")
    report_id: uuid.UUID = Field(..., description="Report ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    
    # Status
    status: Literal['active', 'implemented', 'dismissed', 'archived'] = Field(
        default='active', description="Insight status"
    )
    user_feedback: Dict[str, Any] = Field(default_factory=dict, description="User feedback")
    
    # Review
    reviewed_by: Optional[uuid.UUID] = Field(None, description="Reviewed by user ID")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    
    # Timestamps
    generated_at: datetime = Field(..., description="Generation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

# =============================================
# SEARCH MODELS
# =============================================

class VectorSearchRequest(BaseModel):
    """Model for vector search requests"""
    query: str = Field(..., min_length=1, description="Search query")
    source_types: Optional[List[SourceType]] = Field(None, description="Filter by source types")
    tenant_id: Optional[uuid.UUID] = Field(None, description="Filter by tenant ID")
    project_id: Optional[uuid.UUID] = Field(None, description="Filter by project ID")
    match_threshold: float = Field(default=0.7, ge=0, le=1, description="Similarity threshold")
    match_count: int = Field(default=10, ge=1, le=100, description="Number of matches to return")

class VectorSearchResult(BaseModel):
    """Model for vector search results"""
    id: uuid.UUID = Field(..., description="Document/chunk ID")
    title: str = Field(..., description="Title")
    content: str = Field(..., description="Content")
    source_type: SourceType = Field(..., description="Source type")
    similarity: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

class VectorSearchResponse(BaseModel):
    """Response model for vector search"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    query: str = Field(..., description="Original query")
    results: List[VectorSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")

# =============================================
# RESPONSE MODELS
# =============================================

class DocumentResponse(BaseModel):
    """Response model for document operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Document] = Field(None, description="Document data")

class DocumentListResponse(BaseModel):
    """Response model for document list operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: List[Document] = Field(..., description="List of documents")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")

class ProblemValidationReportResponse(BaseModel):
    """Response model for problem validation report operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[ProblemValidationReport] = Field(None, description="Report data")

class ActionableInsightResponse(BaseModel):
    """Response model for actionable insight operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[ActionableInsight] = Field(None, description="Insight data")
