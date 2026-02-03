"""
Pydantic models for Team Credit Request system.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class CreditRequestCreate(BaseModel):
    """Request model for creating a credit request."""
    requested_credits: int = Field(..., gt=0, description="Number of credits requested")
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for the request")

    @validator('requested_credits')
    def validate_credits(cls, v):
        if v <= 0:
            raise ValueError('Requested credits must be greater than 0')
        if v > 10000:  # Reasonable upper limit
            raise ValueError('Requested credits cannot exceed 10,000')
        return v


class CreditRequestReview(BaseModel):
    """Request model for reviewing (approving/rejecting) a credit request."""
    action: str = Field(..., description="Action to take: 'approve' or 'reject'")
    credits_to_allocate: Optional[int] = Field(None, gt=0, description="Credits to allocate (for approval)")
    review_notes: Optional[str] = Field(None, max_length=1000, description="Review notes")

    @validator('action')
    def validate_action(cls, v):
        if v not in ['approve', 'reject']:
            raise ValueError('Action must be either "approve" or "reject"')
        return v

    @validator('credits_to_allocate')
    def validate_credits_for_approval(cls, v, values):
        if values.get('action') == 'approve' and (v is None or v <= 0):
            raise ValueError('credits_to_allocate is required and must be > 0 for approval')
        return v


class CreditRequestResponse(BaseModel):
    """Response model for a single credit request."""
    request_id: str
    team_id: str
    team_name: Optional[str] = None
    organization_id: str
    requester_id: str
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    requested_credits: int
    reason: Optional[str] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    credits_allocated: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreditRequestListResponse(BaseModel):
    """Response model for listing credit requests."""
    requests: List[CreditRequestResponse]
    total_count: int
    pending_count: int
    page: int = 1
    page_size: int = 20


class CreditRequestWithTeamMetrics(CreditRequestResponse):
    """Extended response with current team credit metrics."""
    current_team_credits: Optional[int] = None
    team_credits_allocated: Optional[int] = None
    team_credits_used: Optional[int] = None
    team_credits_remaining: Optional[int] = None


class CreditRequestCreateResponse(BaseModel):
    """Response model for successful credit request creation."""
    success: bool = True
    request_id: str
    team_id: str
    organization_id: str
    requested_credits: int
    status: str
    created_at: datetime
    message: str = "Credit request submitted successfully"


class CreditRequestReviewResponse(BaseModel):
    """Response model for successful credit request review."""
    success: bool = True
    request_id: str
    status: str
    credits_allocated: Optional[int] = None
    reviewed_by: str
    reviewed_at: datetime
    message: str


class CreditRequestCancelResponse(BaseModel):
    """Response model for successful credit request cancellation."""
    success: bool = True
    request_id: str
    message: str = "Credit request cancelled successfully"
