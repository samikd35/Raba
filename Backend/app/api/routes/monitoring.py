"""RABA Monitoring API Routes.

Endpoints for viewing token usage and cost metrics.

Reference: Phase 5 - Production Readiness
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.services.monitoring import get_monitoring_service
from app.utils.logging import (
    get_logger,
    log_request_start,
    log_request_end,
    log_success,
    log_error_msg,
    log_key_value,
    log_operation,
)
import time

logger = get_logger(__name__)
router = APIRouter(tags=["monitoring"])


@router.get(
    "/summary",
    summary="Get usage summary",
    description="Get aggregated token usage and cost summary for a time period.",
)
async def get_usage_summary(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
):
    """
    Get usage summary for the specified time period.
    
    Returns aggregated metrics including:
    - Total tokens used
    - Total cost in USD
    - Breakdown by generation type (text, image, video, research)
    - Breakdown by model
    - Success rate and cache hit rate
    """
    start_time = time.time()
    log_request_start(logger, "GET", "/api/v1/monitoring/summary", {
        "days": days,
    })
    
    try:
        with log_operation(logger, f"Fetch usage summary for {days} days"):
            service = get_monitoring_service()
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            summary = await service.get_usage_summary(
                start_date=start_date,
                end_date=end_date,
            )
        
        log_success(logger, f"Usage summary retrieved for {days} days")
        if summary.get("totals"):
            log_key_value(logger, "Total cost", f"${summary['totals'].get('total_cost_usd', 0):.2f}")
            log_key_value(logger, "Total videos", summary['totals'].get('total_videos', 0))
        
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", "/api/v1/monitoring/summary", 200, duration_ms)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
            **summary,
        }
        
    except Exception as e:
        log_error_msg(logger, f"Failed to get usage summary: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", "/api/v1/monitoring/summary", 500, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage summary"
        )


@router.get(
    "/video/{video_id}",
    summary="Get video usage",
    description="Get token usage and cost breakdown for a specific video.",
)
async def get_video_usage(video_id: str):
    """
    Get detailed usage metrics for a video.
    
    Returns:
    - Token usage per generation step
    - Cost breakdown
    - Duration metrics
    """
    start_time = time.time()
    log_request_start(logger, "GET", f"/api/v1/monitoring/video/{video_id}")
    
    try:
        with log_operation(logger, f"Fetch usage for video {video_id[:12]}"):
            service = get_monitoring_service()
            usage = await service.get_workflow_usage(video_id)
        
        log_success(logger, f"Video usage retrieved: {video_id[:12]}")
        if usage.get("total_cost_usd"):
            log_key_value(logger, "Total cost", f"${usage['total_cost_usd']:.4f}")
        
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/monitoring/video/{video_id}", 200, duration_ms)
        
        return {
            "video_id": video_id,
            **usage,
        }
        
    except Exception as e:
        log_error_msg(logger, f"Failed to get workflow usage: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/monitoring/video/{video_id}", 500, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow usage"
        )


@router.get(
    "/pricing",
    summary="Get current pricing",
    description="Get current model pricing information.",
)
async def get_pricing():
    """Get current pricing for all models."""
    start_time = time.time()
    log_request_start(logger, "GET", "/api/v1/monitoring/pricing")
    
    from app.services.monitoring import CostCalculator
    
    log_success(logger, "Pricing information retrieved")
    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "GET", "/api/v1/monitoring/pricing", 200, duration_ms)
    
    return {
        "pricing": CostCalculator.PRICING,
        "notes": {
            "text_models": "Prices are per million tokens",
            "image_models": "Includes per-image charge plus token cost",
            "video_models": "Price is per second of generated video",
            "research": "Flat rate per research query",
        },
        "currency": "USD",
        "last_updated": "2026-01-15",
    }
