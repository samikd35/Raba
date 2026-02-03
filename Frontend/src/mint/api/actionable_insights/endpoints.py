#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Actionable Insights API Endpoints for MINT.

This module provides REST API endpoints for generating and retrieving
actionable insights from completed reports.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth_v2.utils import \
    get_current_user  # Import the unified auth dependency
from .helpers import (check_existing_insights, format_insights_response,
                      generate_new_insights)
from .models import (InsightResponse, InsightsListResponse,
                     InsightStatusResponse)
from .service import get_actionable_insights_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/insights", tags=["insights"])

# Log router creation
logger.info("🚀 ACTIONABLE INSIGHTS ROUTER: Router created with prefix '/api/insights'")
logger.info("🚀 ACTIONABLE INSIGHTS ROUTER: Available routes will be:")
logger.info(
    "🚀 ACTIONABLE INSIGHTS ROUTER: - GET /api/insights/{report_id}/actionable-insights"
)
logger.info(
    "🚀 ACTIONABLE INSIGHTS ROUTER: - GET /api/insights/{report_id}/actionable-insights/status"
)
logger.info(
    "🚀 ACTIONABLE INSIGHTS ROUTER: - POST /api/insights/{report_id}/actionable-insights/generate"
)


# Debug endpoint without auth to test if router works
@router.get("/debug/test")
async def debug_test():
    """Debug endpoint to test if actionable insights router is working."""
    logger.info("🧪 DEBUG: Actionable insights router test endpoint hit!")
    return {
        "status": "success",
        "message": "Actionable insights router is working",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/debug/docs/{report_id}")
async def debug_documents(
    report_id: str, current_user: dict = Depends(get_current_user)
):
    """Debug endpoint to test documents table queries."""
    user_id = current_user["user_id"]
    try:
        insights_service = get_actionable_insights_service()

        # Test basic document query
        result = (
            insights_service.supabase.client.table("documents")
            .select("id, source_type, created_by")
            .eq("id", report_id)
            .execute()
        )

        response = {
            "report_id": report_id,
            "user_id": user_id,
            "documents_query_result": {
                "success": True,
                "data_count": len(result.data) if result.data else 0,
                "data": result.data[:1] if result.data else [],  # First record only
            },
        }

        # Test insights query
        try:
            insights_result = (
                insights_service.supabase.client.table("documents")
                .select("*")
                .eq("source_document_id", report_id)
                .eq("source_type", "actionable_insights")
                .eq("created_by", user_id)
                .execute()
            )

            response["insights_query_result"] = {
                "success": True,
                "data_count": len(insights_result.data) if insights_result.data else 0,
                "data": (
                    insights_result.data[:1] if insights_result.data else []
                ),  # First record only
            }
        except Exception as e:
            response["insights_query_result"] = {"success": False, "error": str(e)}

        return response

    except Exception as e:
        return {
            "report_id": report_id,
            "user_id": user_id,
            "error": str(e),
            "success": False,
        }


@router.get(
    "/{report_id}/actionable-insights/status", response_model=InsightStatusResponse
)
async def get_insights_status(
    report_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),  # Use the unified auth dependency
):
    """Get the status of actionable insight generation for a report."""
    user_id = current_user["user_id"]
    try:
        logger.info(
            f"🎯 INSIGHT STATUS: Getting status for report {report_id} for user {user_id}"
        )

        insights_service = get_actionable_insights_service()
        existing_insights = await check_existing_insights(
            insights_service, report_id, user_id
        )  # Pass user_id

        insights_count = len(existing_insights) if existing_insights else 0
        status = "completed" if insights_count > 0 else "not_generated"

        logger.info(
            f"🎯 INSIGHT STATUS: Report {report_id} has {insights_count} insights, status: {status}"
        )

        return InsightStatusResponse(status=status, insights_count=insights_count)

    except Exception as e:
        logger.error(f"Error getting insight status for report {report_id}: {str(e)}")
        return InsightStatusResponse(
            status="error", insights_count=0, error_message=str(e)
        )


@router.get("/{report_id}/actionable-insights", response_model=InsightsListResponse)
async def get_report_insights(
    report_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve existing actionable insights for a report."""
    user_id = current_user["user_id"]
    logger.info(
        f"🎯 GET INSIGHTS: Retrieving insights for report {report_id} for user {user_id}"
    )

    try:
        insights_service = get_actionable_insights_service()
        existing_insights = await check_existing_insights(
            insights_service, report_id, user_id
        )  # Pass user_id

        if not existing_insights:
            logger.info(f"🎯 GET INSIGHTS: No insights found for report {report_id}, triggering background generation")
            
            # Trigger background generation automatically
            import asyncio
            from .service import InsightGenerationContext
            
            # Extract tenant_id from current_user for monitoring
            tenant_id = current_user.get("tenant_id")
            
            async def auto_generate_insights():
                try:
                    logger.info(f"🎯 AUTO-GENERATE: Starting background insight generation for report {report_id}")
                    context = InsightGenerationContext(
                        user_id=user_id,
                        report_id=report_id,
                        tenant_id=tenant_id  # For AI usage monitoring
                    )
                    result = await insights_service.generate_insights(report_id, context)
                    if result.success:
                        logger.info(f"🎯 AUTO-GENERATE: Successfully generated {result.total_insights} insights for report {report_id}")
                    else:
                        logger.error(f"🎯 AUTO-GENERATE: Failed to generate insights for report {report_id}: {result.error_message}")
                except Exception as gen_error:
                    logger.error(f"🎯 AUTO-GENERATE: Error generating insights for report {report_id}: {str(gen_error)}")
            
            # Fire and forget - don't await
            asyncio.create_task(auto_generate_insights())
            
            return InsightsListResponse(
                success=True,
                insights=[],
                report_id=report_id,
                total_insights=0,
                metadata={"status": "generating", "message": "Insights are being generated in the background. Please check back shortly."},
            )

        logger.info(
            f"🎯 GET INSIGHTS: Found {len(existing_insights)} insights for report {report_id}"
        )

        # Convert ActionableInsight objects to InsightResponse objects
        insight_responses = []
        for insight in existing_insights:
            insight_response = InsightResponse(
                id=insight.id,
                insight_type=insight.insight_type,
                title=insight.title,
                content=insight.content,
                supporting_chunks=insight.supporting_chunks,  # This should be List[str]
                confidence_score=insight.confidence_score,
                generation_metadata=insight.generation_metadata,
                created_at=datetime.now().isoformat(),
            )
            insight_responses.append(insight_response)

        return InsightsListResponse(
            success=True,
            insights=insight_responses,
            report_id=report_id,
            total_insights=len(insight_responses),
            metadata={
                "generated_at": (
                    insight_responses[0].created_at if insight_responses else None
                )
            },
        )

    except Exception as e:
        logger.error(f"Error getting insights for report {report_id}: {str(e)}")
        return format_insights_response([], report_id, success=False, error=str(e))


@router.post(
    "/{report_id}/actionable-insights/generate", response_model=InsightsListResponse
)
async def generate_insights(
    report_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Generate actionable insights for a completed report."""
    user_id = current_user["user_id"]
    try:
        # Parse request body safely
        try:
            request_body = await request.json()
            force_regenerate = request_body.get("force_regenerate", False)
        except Exception:
            # Handle empty or invalid JSON body
            force_regenerate = False

        logger.info(
            f"🎯 GENERATE INSIGHTS: Called for report {report_id}, force_regenerate: {force_regenerate} by user {user_id}"
        )

        insights_service = get_actionable_insights_service()

        # Check for existing insights if not forcing regeneration
        if not force_regenerate:
            existing_insights = await check_existing_insights(
                insights_service, report_id, user_id
            )  # Pass user_id
            if existing_insights:
                logger.info(
                    f"🎯 GENERATE INSIGHTS: Returning existing insights for report {report_id}"
                )
                # Convert existing insights to proper response format
                insight_responses = []
                for insight in existing_insights:
                    insight_response = InsightResponse(
                        id=insight.id,
                        insight_type=insight.insight_type,
                        title=insight.title,
                        content=insight.content,
                        supporting_chunks=insight.supporting_chunks,
                        confidence_score=insight.confidence_score,
                        generation_metadata=insight.generation_metadata,
                        created_at=datetime.now().isoformat(),
                    )
                    insight_responses.append(insight_response)

                return InsightsListResponse(
                    success=True,
                    insights=insight_responses,
                    report_id=report_id,
                    total_insights=len(insight_responses),
                    metadata={
                        "generated_at": (
                            insight_responses[0].created_at
                            if insight_responses
                            else None
                        )
                    },
                )

        # Get report owner and generate new insights
        # user_id is already available from Depends(get_current_user)
        result = await generate_new_insights(insights_service, report_id, user_id)

        logger.info(
            f"🎯 GENERATE INSIGHTS: Successfully generated {len(result.insights)} insights for report {report_id}"
        )

        # Convert ActionableInsight objects to InsightResponse objects
        insight_responses = []
        for insight in result.insights:
            insight_response = InsightResponse(
                id=insight.id,
                insight_type=insight.insight_type,
                title=insight.title,
                content=insight.content,
                supporting_chunks=insight.supporting_chunks,  # This should be List[str]
                confidence_score=insight.confidence_score,
                generation_metadata=insight.generation_metadata,
                created_at=datetime.now().isoformat(),
            )
            insight_responses.append(insight_response)

        return InsightsListResponse(
            success=True,
            insights=insight_responses,
            report_id=report_id,
            total_insights=len(insight_responses),
            generation_time=result.generation_time_seconds,
            metadata={
                "generated_at": (
                    insight_responses[0].created_at if insight_responses else None
                )
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insights for report {report_id}: {str(e)}")
        return format_insights_response([], report_id, success=False, error=str(e))
