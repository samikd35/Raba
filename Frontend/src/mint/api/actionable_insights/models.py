#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pydantic models for Actionable Insights API.

This module contains all the request and response models used by the
actionable insights endpoints.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field


class GenerateInsightsRequest(BaseModel):
    """Request model for generating insights."""
    force_regenerate: bool = False


class InsightStatusResponse(BaseModel):
    """Response model for insight status."""
    status: str  # 'not_generated', 'generating', 'completed', 'failed'
    insights_count: int = 0
    progress: Optional[float] = None
    estimated_time_remaining: Optional[int] = None
    error_message: Optional[str] = None


class InsightResponse(BaseModel):
    """Response model for insight data."""
    id: str
    insight_type: str
    title: str
    content: Union[str, Dict[str, Any]]  # Support both string and structured content
    supporting_chunks: List[str]
    confidence_score: float
    generation_metadata: Dict[str, Any]
    created_at: str


class InsightsListResponse(BaseModel):
    """Response model for insights list."""
    success: bool
    insights: List[InsightResponse]
    report_id: str
    total_insights: int
    generation_time: Optional[float] = None
    metadata: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ActionableInsight(BaseModel):
    """Model for a single actionable insight."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    insight_type: str = Field(..., description="Type of insight: market_entry, product_development, risk_mitigation, competitive_advantage")
    title: str = Field(..., description="Brief title for the insight")
    content: Union[str, Dict[str, Any]] = Field(..., description="Detailed actionable content - can be string or structured sections")
    supporting_chunks: List[str] = Field(default_factory=list, description="Report chunks supporting this insight")
    confidence_score: float = Field(default=0.8, description="Confidence score for the insight")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User context used for generation")
    generation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about generation process")


class InsightGenerationResult(BaseModel):
    """Result of insight generation process."""
    success: bool
    insights: List[ActionableInsight] = Field(default_factory=list)
    total_insights: int = 0
    generation_time_seconds: float = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)