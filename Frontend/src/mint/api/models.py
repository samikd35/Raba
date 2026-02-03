#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MINT API Models

Pydantic models for the MINT API endpoints.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator


class WorkflowRequest(BaseModel):
    """Request model for starting a new workflow."""
    query: str = Field(..., min_length=10, max_length=2000, description="The market research query")
    interactive: bool = Field(default=True, description="Whether to enable interactive clarifications")


class ClarificationAnswer(BaseModel):
    """Model for submitting clarification answers."""
    answers: Dict[str, Any] = Field(..., description="Dictionary of question IDs to answers")


class WorkflowStatus(BaseModel):
    """Model for workflow status response."""
    session_id: str
    status: str
    progress: Optional[int] = None
    questions: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    message: Optional[str] = None
    completed_at: Optional[datetime] = None


class WorkflowReport(BaseModel):
    """Model for the final workflow report."""
    session_id: str
    query: str
    report: Dict[str, Any]
    questions: List[Dict[str, Any]]
    answers: Dict[str, Any]
    created_at: datetime
    status: str


class ResearchProgress(BaseModel):
    """Model for research progress tracking."""
    stage: str
    progress: int
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class CreditStatusResponse(BaseModel):
    """Model for credit status response."""
    user_id: str
    total_credits: int
    used_credits: int
    remaining_credits: int
    weekly_reset_date: datetime
    last_reset_at: Optional[datetime] = None


class ProblemGeneratorCreditStatusResponse(BaseModel):
    """Model for problem generator credit status response."""
    user_id: str
    pg_total_credits: int
    pg_used_credits: int
    pg_remaining_credits: int
    pg_weekly_reset_date: datetime
    last_reset_at: Optional[datetime] = None


class CreditRequestModel(BaseModel):
    """Model for credit request."""
    user_id: str = Field(..., description="User ID requesting additional credits")
    reason: Optional[str] = Field(None, description="Optional reason for the request")


class CreditRequestResponse(BaseModel):
    """Model for credit request response."""
    success: bool
    message: str
    request_id: Optional[str] = None
    credits_granted: Optional[int] = None
    waiting_period_seconds: Optional[int] = None


class CreditRequestStatus(BaseModel):
    """Model for credit request status."""
    can_request: bool
    reason: str
    next_request_available_at: Optional[datetime] = None
    requests_this_week: int
    max_requests_per_week: int


class UserCreditRequests(BaseModel):
    """Model for user credit requests history."""
    user_id: str
    requests: List[Dict[str, Any]]
    total_requests: int
    requests_this_week: int


class ProcessCreditRequestModel(BaseModel):
    """Model for processing credit requests."""
    process_all: Optional[bool] = Field(False, description="Process all pending requests")
    user_id: Optional[str] = Field(None, description="Process requests for specific user")


class ProcessCreditRequestResponse(BaseModel):
    """Model for credit request processing response."""
    success: bool
    message: str
    processed_count: int
    failed_count: int
    details: List[Dict[str, Any]]


class StopWorkflowRequest(BaseModel):
    """Model for stopping a workflow."""
    reason: Optional[str] = Field(None, description="Optional reason for stopping")


class StopWorkflowResponse(BaseModel):
    """Model for stop workflow response."""
    success: bool
    message: str
    session_id: str
    stopped_at: datetime
