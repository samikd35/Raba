"""
Pydantic models for idea refinement feature.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ParsedContext(BaseModel):
    """Parsed context from user's raw idea."""
    persona: str = Field(..., description="User's persona/background")
    industry: str = Field(..., description="Industry or domain")
    geography: str = Field(..., description="Geographic location or market")
    delivery_mode: str = Field(..., description="How the solution would be delivered")
    assumptions: List[str] = Field(default_factory=list, description="Key assumptions identified")


class ProblemStatement(BaseModel):
    """A refined problem statement."""
    stakeholder: str = Field(..., description="Who is affected by this problem")
    statement: str = Field(..., description="Clear problem statement")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions underlying this problem")


class ProblemStatementsOutput(BaseModel):
    """Collection of problem statements."""
    problem_statements: List[ProblemStatement] = Field(..., description="List of refined problem statements")


class RefinedVariants(BaseModel):
    """Refined variants of a problem statement."""
    variants: List[str] = Field(..., description="Different variations of the problem statement")


class IdeaRefinementRequest(BaseModel):
    """Request model for idea refinement API."""
    raw_idea: str = Field(..., description="The user's raw idea or concept", min_length=10)
    user_id: Optional[str] = Field(None, description="User ID for tracking")


class IdeaRefinementResponse(BaseModel):
    """Response model for idea refinement API."""
    session_id: str = Field(..., description="Unique session ID for this refinement")
    parsed_context: ParsedContext = Field(..., description="Parsed context from the raw idea")
    problem_statements: ProblemStatementsOutput = Field(..., description="Generated problem statements")
    refined_variants: Optional[RefinedVariants] = Field(None, description="Additional refined variants")
    original_idea: str = Field(..., description="The original raw idea")
    processing_time_seconds: float = Field(..., description="Time taken to process the refinement")


class InterviewQuestion(BaseModel):
    """Interview question for problem validation."""
    question: str = Field(..., description="The interview question")
    purpose: str = Field(..., description="What this question aims to validate")
    follow_up_prompts: List[str] = Field(default_factory=list, description="Follow-up prompts based on answers")


class ValidationCue(BaseModel):
    """Validation cue for testing the problem."""
    cue: str = Field(..., description="The validation cue or test")
    method: str = Field(..., description="How to implement this validation")
    success_criteria: str = Field(..., description="What indicates success")


class ProblemScore(BaseModel):
    """Scoring for a problem statement."""
    clarity_score: float = Field(..., description="How clear and specific the problem is (0-10)")
    urgency_score: float = Field(..., description="How urgent/painful the problem is (0-10)")
    market_size_score: float = Field(..., description="Potential market size (0-10)")
    testability_score: float = Field(..., description="How easily the problem can be validated (0-10)")
    overall_score: float = Field(..., description="Overall problem strength (0-10)")
    reasoning: str = Field(..., description="Explanation of the scoring")


class EnhancedRefinementResponse(BaseModel):
    """Enhanced response with scoring and validation guidance."""
    session_id: str = Field(..., description="Unique session ID for this refinement")
    parsed_context: ParsedContext = Field(..., description="Parsed context from the raw idea")
    problem_statements: ProblemStatementsOutput = Field(..., description="Generated problem statements")
    problem_scores: List[ProblemScore] = Field(..., description="Scores for each problem statement")
    interview_questions: List[InterviewQuestion] = Field(..., description="Questions to validate the problems")
    validation_cues: List[ValidationCue] = Field(..., description="Ways to test the problems")
    original_idea: str = Field(..., description="The original raw idea")
    processing_time_seconds: float = Field(..., description="Time taken to process the refinement")


class ProblemRefinerHistoryEntry(BaseModel):
    """History entry for problem refiner sessions."""
    session_id: str = Field(..., description="Unique session ID")
    user_id: Optional[str] = Field(None, description="User ID if available")
    original_idea: str = Field(..., description="The original raw idea")
    refined_problems: List[str] = Field(..., description="List of refined problem statements")
    created_at: datetime = Field(default_factory=datetime.now, description="When the entry was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When the entry was last updated")
    status: str = Field(default="completed", description="Status of the refinement")


class ProblemRefinerAnalytics(BaseModel):
    """Analytics data for problem refiner usage."""
    total_sessions: int = Field(..., description="Total number of refinement sessions")
    avg_problems_per_session: float = Field(..., description="Average problems generated per session")
    most_common_industries: List[str] = Field(..., description="Most common industries")
    most_common_geographies: List[str] = Field(..., description="Most common geographies")
    success_rate: float = Field(..., description="Success rate of refinements")


class ProblemRefinerSearchRequest(BaseModel):
    """Request model for searching problem refiner history."""
    query: Optional[str] = Field(None, description="Search query")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    industry: Optional[str] = Field(None, description="Filter by industry")
    geography: Optional[str] = Field(None, description="Filter by geography")
    limit: int = Field(default=10, description="Maximum number of results")
    offset: int = Field(default=0, description="Offset for pagination")


class ProblemRefinerSearchResponse(BaseModel):
    """Response model for problem refiner search."""
    results: List[ProblemRefinerHistoryEntry] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of matching entries")
    has_more: bool = Field(..., description="Whether there are more results")


class ResearchedStatusUpdate(BaseModel):
    """Model for updating the researched status of a problem."""
    session_id: str = Field(..., description="Session ID of the problem")
    problem_index: int = Field(..., description="Index of the problem statement")
    researched: bool = Field(..., description="Whether the problem has been researched")
    research_notes: Optional[str] = Field(None, description="Notes from research")
