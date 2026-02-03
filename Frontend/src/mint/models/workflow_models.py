"""
Workflow Data Models - Separated from Monolithic Structure
==========================================================

This module contains all workflow-related data models that were previously
defined inline in the monolithic app.py file. This separation provides:

1. ✅ Clear data model definitions separate from API logic
2. ✅ Improved type safety and validation
3. ✅ Reusable models across different modules
4. ✅ Better documentation and maintainability

Models included:
- WorkflowRequest - Request to start a new workflow
- WorkflowStatus - Current status of a workflow
- WorkflowReport - Complete workflow report
- ClarificationAnswer - Answers to clarification questions
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator


class WorkflowRequest(BaseModel):
    """Request model for starting a new workflow.
    
    Note: user_id is NOT included in the request body because it's extracted
    from the JWT authentication token. This prevents security issues where
    users could attempt to impersonate others.
    """
    
    query: str = Field(
        ..., 
        description="The initial research query",
        min_length=10,
        max_length=1000
    )
    interactive: bool = Field(
        default=True, 
        description="Whether to run in interactive mode"
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate that the query is meaningful."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        
        # Basic quality checks
        words = v.strip().split()
        if len(words) < 3:
            raise ValueError('Query must contain at least 3 words')
        
        return v.strip()


class ClarificationQuestion(BaseModel):
    """Model for a single clarification question."""
    
    id: str = Field(..., description="Unique question identifier")
    question: str = Field(..., description="The clarification question text")
    question_type: str = Field(
        default="text", 
        description="Type of question (text, multiple_choice, boolean)"
    )
    options: Optional[List[str]] = Field(
        default=None, 
        description="Options for multiple choice questions"
    )
    required: bool = Field(
        default=True, 
        description="Whether this question must be answered"
    )


class ClarificationAnswer(BaseModel):
    """Model for submitting answers to clarification questions."""
    
    answers: Dict[str, Any] = Field(
        ..., 
        description="Dictionary mapping question IDs to answers"
    )
    
    @validator('answers')
    def validate_answers(cls, v):
        """Validate that answers dictionary is not empty."""
        if not v:
            raise ValueError('Answers cannot be empty')
        
        # Check for empty values
        for question_id, answer in v.items():
            if answer is None or (isinstance(answer, str) and not answer.strip()):
                raise ValueError(f'Answer for question {question_id} cannot be empty')
        
        return v


class WorkflowProgress(BaseModel):
    """Model for workflow progress tracking."""
    
    current_stage: str = Field(..., description="Current workflow stage")
    progress_percentage: int = Field(
        ..., 
        description="Progress percentage (0-100)",
        ge=0,
        le=100
    )
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )
    stages_completed: List[str] = Field(
        default=[],
        description="List of completed workflow stages"
    )
    stages_remaining: List[str] = Field(
        default=[],
        description="List of remaining workflow stages"
    )


class WorkflowStatus(BaseModel):
    """Model for workflow status responses."""
    
    session_id: str = Field(..., description="Unique workflow session identifier")
    status: str = Field(
        ..., 
        description="Current workflow status",
        pattern="^(started|pending|initializing|processing|clarifying|researching|analyzing|generating|waiting_for_clarification|completed|failed|cancelled)$"
    )
    progress: int = Field(
        default=0, 
        description="Progress percentage (0-100)",
        ge=0,
        le=100
    )
    message: str = Field(
        default="", 
        description="Human-readable status message"
    )
    clarification_questions: Optional[List[ClarificationQuestion]] = Field(
        default=None,
        description="Clarification questions if workflow is waiting for input"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of last status update"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if workflow failed"
    )
    progress_details: Optional[WorkflowProgress] = Field(
        default=None,
        description="Detailed progress information"
    )
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )


class ReportSection(BaseModel):
    """Model for a section within a workflow report."""
    
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    section_type: str = Field(
        default="analysis",
        description="Type of section (analysis, insights, recommendations, etc.)"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Confidence score for this section (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    sources: Optional[List[str]] = Field(
        default=[],
        description="Sources used for this section"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional metadata for this section"
    )


class WorkflowReport(BaseModel):
    """Model for complete workflow reports."""
    
    session_id: str = Field(..., description="Workflow session identifier")
    report_id: str = Field(..., description="Report ID (document ID in database)")
    query: str = Field(..., description="Original research query")
    title: str = Field(
        default="Market Intelligence Report",
        description="Report title"
    )
    executive_summary: str = Field(
        default="",
        description="Executive summary of the report"
    )
    sections: List[ReportSection] = Field(
        default=[],
        description="Report sections"
    )
    report: Dict[str, Any] = Field(
        default={},
        description="Complete report data structure"
    )
    status: str = Field(
        default="completed",
        description="Report generation status"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Report generation timestamp"
    )
    generation_time_seconds: Optional[float] = Field(
        default=None,
        description="Time taken to generate the report"
    )
    word_count: Optional[int] = Field(
        default=None,
        description="Total word count of the report"
    )
    quality_score: Optional[float] = Field(
        default=None,
        description="Quality score of the report (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    @validator('sections')
    def validate_sections(cls, v):
        """Validate report sections."""
        if not v:
            return v
        
        # Check for duplicate section titles
        titles = [section.title for section in v]
        if len(titles) != len(set(titles)):
            raise ValueError('Report sections must have unique titles')
        
        return v


class WorkflowMetrics(BaseModel):
    """Model for workflow system metrics."""
    
    total_workflows: int = Field(default=0, description="Total number of workflows")
    active_workflows: int = Field(default=0, description="Currently active workflows")
    completed_workflows: int = Field(default=0, description="Completed workflows")
    failed_workflows: int = Field(default=0, description="Failed workflows")
    average_completion_time: float = Field(
        default=0.0,
        description="Average completion time in seconds"
    )
    success_rate: float = Field(
        default=0.0,
        description="Success rate percentage",
        ge=0.0,
        le=100.0
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Metrics collection timestamp"
    )


class CreditStatus(BaseModel):
    """Model for user credit status."""
    
    user_id: str = Field(..., description="User identifier")
    available_credits: int = Field(
        default=0,
        description="Number of available credits",
        ge=0
    )
    total_credits: int = Field(
        default=0,
        description="Total credits allocated",
        ge=0
    )
    used_credits: int = Field(
        default=0,
        description="Number of credits used",
        ge=0
    )
    is_exempt: bool = Field(
        default=False,
        description="Whether user is exempt from credit limits"
    )
    can_generate: bool = Field(
        default=False,
        description="Whether user can generate new reports"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    
    @validator('used_credits')
    def validate_used_credits(cls, v, values):
        """Validate that used credits don't exceed total credits."""
        total_credits = values.get('total_credits', 0)
        if v > total_credits:
            raise ValueError('Used credits cannot exceed total credits')
        return v


class WorkflowError(BaseModel):
    """Model for workflow error tracking."""
    
    session_id: str = Field(..., description="Workflow session identifier")
    user_id: str = Field(..., description="User identifier")
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(
        default=None,
        description="Standardized error code"
    )
    occurred_at: datetime = Field(
        default_factory=datetime.now,
        description="When the error occurred"
    )
    workflow_stage: Optional[str] = Field(
        default=None,
        description="Workflow stage where error occurred"
    )
    stack_trace: Optional[str] = Field(
        default=None,
        description="Error stack trace (for debugging)"
    )
    recovery_attempted: bool = Field(
        default=False,
        description="Whether automatic recovery was attempted"
    )
    user_notified: bool = Field(
        default=False,
        description="Whether user was notified of the error"
    )


# Response models for API endpoints
class WorkflowStartResponse(BaseModel):
    """Response model for workflow start endpoint."""
    
    session_id: str = Field(..., description="Created workflow session ID")
    status: str = Field(..., description="Initial workflow status")
    message: str = Field(..., description="Success message")
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )


class WorkflowHealthResponse(BaseModel):
    """Response model for workflow health check."""
    
    status: str = Field(..., description="Health status")
    service: str = Field(default="workflow", description="Service name")
    health_details: Dict[str, Any] = Field(
        default={},
        description="Detailed health information"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Health check timestamp"
    )


class WorkflowMetricsResponse(BaseModel):
    """Response model for workflow metrics endpoint."""
    
    status: str = Field(default="success", description="Response status")
    metrics: WorkflowMetrics = Field(..., description="Workflow metrics")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp"
    )
