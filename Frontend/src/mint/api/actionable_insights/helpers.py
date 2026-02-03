#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper functions for Actionable Insights API.

This module contains utility functions used by the actionable insights endpoints
for formatting responses, handling data, and other common operations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import HTTPException

from .service import ActionableInsightsService, InsightGenerationContext
from ..system.core.supabase_client import get_supabase_client

# Configure logging
logger = logging.getLogger(__name__)


def format_insight_for_response(insight: Any) -> Dict[str, Any]:
    """Format a single insight object for API response."""
    return {
        "id": insight.id,
        "insight_type": insight.insight_type,
        "title": insight.title,
        "content": insight.content,
        "supporting_chunks": insight.supporting_chunks,
        "confidence_score": insight.confidence_score,
        "generation_metadata": insight.generation_metadata,
        "created_at": datetime.now().isoformat()
    }


def format_insights_response(
    insights: List[Any], 
    report_id: str, 
    success: bool = True, 
    error: Optional[str] = None
) -> Dict[str, Any]:
    """Format insights list for API response."""
    formatted_insights = [format_insight_for_response(insight) for insight in insights]
    
    response = {
        "success": success,
        "insights": formatted_insights,
        "report_id": report_id,
        "total_insights": len(formatted_insights),
        "metadata": {
            "generated_at": formatted_insights[0].get("created_at") if formatted_insights else None
        }
    }
    
    if error:
        response["error"] = error
        
    return response


async def get_report_owner_id(report_id: str) -> str:
    """Get the user_id of the report owner."""
    supabase = get_supabase_client(use_service_role=True)
    report_result = supabase.client.table("mint_reports").select("user_id").eq("id", report_id).execute()
    
    if not report_result.data:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
    return report_result.data[0].get("user_id")


def create_insight_generation_context(user_id: str, report_id: str, **kwargs) -> InsightGenerationContext:
    """Create insight generation context with default values."""
    return InsightGenerationContext(
        user_id=user_id,
        report_id=report_id,
        industry=kwargs.get("industry"),
        geography=kwargs.get("geography"),
        background=kwargs.get("background"),
        product_type=kwargs.get("product_type"),
        tenant_id=kwargs.get("tenant_id"),  # For AI usage monitoring
        project_id=kwargs.get("project_id")  # For AI usage monitoring
    )


async def check_existing_insights(insights_service: ActionableInsightsService, report_id: str, user_id: str) -> Optional[List[Any]]:
    """Check if insights already exist for a report and belong to the user."""
    # Assuming _get_existing_insights can take a user_id for RLS or ownership check
    existing_insights = await insights_service._get_existing_insights(report_id, user_id)
    return existing_insights if existing_insights and len(existing_insights) > 0 else None


async def generate_new_insights(insights_service: ActionableInsightsService, report_id: str, user_id: str) -> Any:
    """Generate new insights for a report."""
    user_context = create_insight_generation_context(user_id, report_id)
    logger.info(f"🎯 GENERATE INSIGHTS: Generating new insights for report {report_id}")
    
    result = await insights_service.generate_insights(report_id, user_context)
    
    if not result.success:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate insights: {result.error_message}"
        )
    
    return result
