#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Actionable Insights Module for MINT.

This module provides a complete solution for generating and retrieving
actionable insights from completed reports.

Module Structure:
- models: Pydantic models for request/response validation
- helpers: Utility functions for business logic
- endpoints: FastAPI route definitions
"""

from .endpoints import router
from .service import (
    ActionableInsightsService,
    get_actionable_insights_service,
    InsightGenerationContext,
    ActionableInsight,
    InsightGenerationResult
)
from .models import (
    GenerateInsightsRequest,
    InsightStatusResponse,
    InsightResponse,
    InsightsListResponse,
    ErrorResponse
)
from .helpers import (
    format_insight_for_response,
    format_insights_response,
    get_report_owner_id,
    create_insight_generation_context,
    check_existing_insights,
    generate_new_insights
)

__all__ = [
    # Router
    "router",
    
    # Service
    "ActionableInsightsService",
    "get_actionable_insights_service",
    "InsightGenerationContext",
    "ActionableInsight",
    "InsightGenerationResult",
    
    # Models
    "GenerateInsightsRequest",
    "InsightStatusResponse", 
    "InsightResponse",
    "InsightsListResponse",
    "ErrorResponse",
    
    # Helpers
    "format_insight_for_response",
    "format_insights_response",
    "get_report_owner_id",
    "create_insight_generation_context",
    "check_existing_insights",
    "generate_new_insights"
]
