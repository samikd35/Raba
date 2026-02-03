"""
Pydantic models for Problem Generator database schema.

This module defines the data models for problem statements, analytics,
and related entities in the Problem Generator feature.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator


class ProblemCategory(str, Enum):
    """Enumeration of problem categories."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    FINANCE = "finance"
    ENVIRONMENT = "environment"
    SOCIAL = "social"
    BUSINESS = "business"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Enumeration of problem severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemType(str, Enum):
    """Enumeration of problem types."""
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    TECHNICAL = "technical"
    SOCIAL = "social"
    ENVIRONMENTAL = "environmental"
    REGULATORY = "regulatory"


class TimeHorizon(str, Enum):
    """Enumeration of time horizons for problem resolution."""
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class ComplexityLevel(str, Enum):
    """Enumeration of problem complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    HIGHLY_COMPLEX = "highly_complex"


class PopulationSize(str, Enum):
    """Enumeration of affected population sizes."""
    LOCAL = "local"
    REGIONAL = "regional"
    NATIONAL = "national"
    GLOBAL = "global"


class ValidationStatus(str, Enum):
    """Enumeration of validation statuses."""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


# =============================================
# REQUEST/RESPONSE MODELS
# =============================================

class ProblemStatementCreate(BaseModel):
    """Model for creating a new problem statement with restructured fields."""
    # Core information
    title: str = Field(..., min_length=1, max_length=350, description="Concise problem statement")
    description: str = Field(..., min_length=1, description="Detailed problem explanation")
    
    # Contextual information
    category: ProblemCategory = Field(..., description="Industry/category of the problem")
    target_geography: List[str] = Field(default=[], description="Geographic regions affected by the problem")
    impact_focus: List[str] = Field(default=[], description="Impact focus areas for the problem")
    
    # Problem characteristics
    severity_level: SeverityLevel = Field(..., description="Problem severity level")
    problem_type: ProblemType = Field(..., description="Type of problem")
    time_horizon: TimeHorizon = Field(..., description="Expected time horizon for resolution")
    complexity_level: ComplexityLevel = Field(..., description="Problem complexity level")
    affected_population_size: Optional[PopulationSize] = Field(None, description="Size of affected population")
    
    # Detailed analysis sections
    root_causes: List[str] = Field(default=[], description="Identified root causes of the problem")
    potential_effects: List[str] = Field(default=[], description="Potential effects if the problem remains unresolved")
    stakeholders: List[str] = Field(default=[], description="Key stakeholders affected by or involved with the problem")
    success_metrics: List[str] = Field(default=[], description="Measurable indicators showing problem resolution")
    
    # Source information
    supporting_sources: List[Dict[str, Any]] = Field(default=[], description="Sources supporting the problem statement")
    
    # Generation metadata
    generation_parameters: Dict[str, Any] = Field(default={}, description="Parameters used for generation")
    generation_model: str = Field(default="gpt-4o", description="AI model used for generation")
    quality_score: float = Field(default=0.0, description="Quality score of the generated problem statement")
    session_id: Optional[uuid.UUID] = Field(None, description="ID of the generation session this problem belongs to")
    
    @validator('target_geography', 'impact_focus', 'root_causes', 'potential_effects', 'stakeholders', 'success_metrics')
    def validate_lists(cls, v):
        """Ensure lists don't exceed reasonable limits."""
        if len(v) > 20:  # Reasonable limit for array fields
            raise ValueError("List cannot contain more than 20 items")
        return v


class ProblemStatementUpdate(BaseModel):
    """Model for updating an existing problem statement."""
    title: Optional[str] = Field(None, min_length=1, max_length=350)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[ProblemCategory] = None
    severity_level: Optional[SeverityLevel] = None
    target_geography: Optional[List[str]] = None
    impact_focus: Optional[List[str]] = None
    affected_population_size: Optional[PopulationSize] = None
    problem_type: Optional[ProblemType] = None
    time_horizon: Optional[TimeHorizon] = None
    complexity_level: Optional[ComplexityLevel] = None
    root_causes: Optional[List[str]] = None
    potential_effects: Optional[List[str]] = None
    stakeholders: Optional[List[str]] = None
    success_metrics: Optional[List[str]] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    validation_status: Optional[ValidationStatus] = None
    validation_feedback: Optional[str] = None


class ProblemStatementResponse(BaseModel):
    """Model for problem statement API responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    category: ProblemCategory
    severity_level: SeverityLevel
    target_geography: List[str]
    impact_focus: List[str]
    affected_population_size: Optional[PopulationSize]
    problem_type: ProblemType
    time_horizon: TimeHorizon
    complexity_level: ComplexityLevel
    root_causes: List[str]
    potential_effects: List[str]
    stakeholders: List[str]
    success_metrics: List[str]
    supporting_sources: List[Dict[str, Any]] = Field(default_factory=list, description="Array of source objects with citation information")
    generation_parameters: Dict[str, Any]
    generation_model: str
    generation_timestamp: datetime
    quality_score: Optional[float]
    validation_status: ValidationStatus
    validation_feedback: Optional[str]
    view_count: int
    like_count: int
    bookmark_count: int
    created_at: datetime
    updated_at: datetime
    session_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class ProblemStatementSummary(BaseModel):
    """Lightweight model for problem statement lists."""
    id: uuid.UUID
    title: str
    description: str
    category: ProblemCategory
    severity_level: SeverityLevel
    problem_type: ProblemType
    quality_score: Optional[float]
    like_count: int
    bookmark_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================
# SEARCH AND SIMILARITY MODELS
# =============================================

class ProblemSearchRequest(BaseModel):
    """Model for problem statement search requests."""
    query: Optional[str] = Field(None, description="Text query for search")
    category: Optional[ProblemCategory] = None
    severity_level: Optional[SeverityLevel] = None
    problem_type: Optional[ProblemType] = None
    time_horizon: Optional[TimeHorizon] = None
    complexity_level: Optional[ComplexityLevel] = None
    target_geography: Optional[List[str]] = None
    min_quality_score: Optional[float] = Field(None, ge=0, le=1)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    similarity_threshold: float = Field(default=0.7, ge=0, le=1)


class SimilarProblemResponse(BaseModel):
    """Model for similar problem statement responses."""
    id: uuid.UUID
    title: str
    description: str
    category: ProblemCategory
    severity_level: SeverityLevel
    similarity: float
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================
# ANALYTICS MODELS
# =============================================

class GenerationAnalyticsCreate(BaseModel):
    """Model for creating generation analytics records."""
    session_id: uuid.UUID = Field(..., description="Generation session ID")
    input_parameters: Dict[str, Any] = Field(..., description="Input parameters used")
    selected_category: Optional[str] = None
    selected_geography: Optional[List[str]] = None
    selected_impact_focus: Optional[List[str]] = None
    problems_generated: int = Field(default=0, ge=0)
    generation_success: bool = Field(default=False)
    generation_time_ms: Optional[int] = Field(None, ge=0)
    model_used: str = Field(default="gpt-4")
    model_temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=16000, ge=1)  # gpt-5-mini needs large token budget
    average_quality_score: Optional[float] = Field(None, ge=0, le=1)
    user_satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    error_occurred: bool = Field(default=False)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    class Config:
        protected_namespaces = ()


class GenerationAnalyticsResponse(BaseModel):
    """Model for generation analytics API responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID
    input_parameters: Dict[str, Any]
    selected_category: Optional[str]
    selected_severity: Optional[str]
    selected_geography: Optional[List[str]]
    selected_impact_focus: Optional[List[str]]
    problems_generated: int
    generation_success: bool
    generation_time_ms: Optional[int]
    model_used: str
    model_temperature: float
    max_tokens: int
    average_quality_score: Optional[float]
    user_satisfaction_rating: Optional[int]
    error_occurred: bool
    error_message: Optional[str]
    error_type: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
        protected_namespaces = ()


# =============================================
# BOOKMARK AND LIKE MODELS
# =============================================

class BookmarkCreate(BaseModel):
    """Model for creating a bookmark."""
    problem_statement_id: uuid.UUID = Field(..., description="ID of problem statement to bookmark")
    bookmark_notes: Optional[str] = Field(None, description="Optional notes for the bookmark")
    bookmark_tags: List[str] = Field(default=[], description="Tags for organizing bookmarks")

    @validator('bookmark_tags')
    def validate_bookmark_tags(cls, v):
        if len(v) > 10:  # Reasonable limit for tags
            raise ValueError("Cannot have more than 10 bookmark tags")
        return v


class BookmarkResponse(BaseModel):
    """Model for bookmark API responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    problem_statement_id: uuid.UUID
    bookmark_notes: Optional[str]
    bookmark_tags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LikeCreate(BaseModel):
    """Model for creating a like."""
    problem_statement_id: uuid.UUID = Field(..., description="ID of problem statement to like")


class LikeResponse(BaseModel):
    """Model for like API responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    problem_statement_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================
# GENERATION REQUEST MODELS
# =============================================

class ProblemGenerationRequest(BaseModel):
    """Request model for problem generation"""
    industry: List[str] = Field(..., min_items=1, max_items=3, description="Industry categories")
    geography: List[str] = Field(..., min_items=1, max_items=1, description="Single African country")
    background: List[str] = Field(..., min_items=1, max_items=2, description="User background/expertise")
    product_type: List[str] = Field(..., min_items=1, max_items=3, description="Product/service types")
    
    # Now mandatory parameters (moved from optional)
    target_customer: List[str] = Field(..., min_items=1, max_items=3, description="Target customer segments")
    impact_focus: List[str] = Field(
        ..., 
        description="Impact focus defining the nature and scope of venture objectives",
        min_items=1,
        max_items=2
    )
    num_problems: Optional[int] = Field(default=3, ge=1, le=10, description="Number of problems to generate")
    creativity_level: Optional[float] = Field(default=0.7, ge=0.0, le=1.0, description="Creativity level")
    custom_constraints: Optional[str] = Field(default="", description="Custom constraints or requirements")

    class Config:
        # Allow extra fields for future extensibility
        extra = 'allow'


class ProblemGenerationResponse(BaseModel):
    """Model for problem generation API responses."""
    session_id: uuid.UUID
    problems: List[ProblemStatementResponse]
    generation_time_ms: int
    model_used: str
    parameters_used: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================
# UTILITY MODELS
# =============================================

class PaginatedResponse(BaseModel):
    """Generic paginated response model."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ProblemStatementsPaginated(BaseModel):
    """Paginated response for problem statements."""
    items: List[ProblemStatementSummary]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class AnalyticsSummary(BaseModel):
    """Summary analytics for problem generation."""
    total_problems_generated: int
    total_sessions: int
    average_generation_time_ms: float
    success_rate: float
    most_popular_category: Optional[str]
    most_popular_severity: Optional[str]
    average_quality_score: Optional[float]
    user_satisfaction_average: Optional[float]
