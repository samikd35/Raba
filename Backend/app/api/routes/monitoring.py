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
            
            # Get workflow counts from database
            from app.services.supabase import get_workflow_repository
            repo = get_workflow_repository()
            
            # Get all workflows in the period
            workflows_response = (
                repo.client.table("workflows")
                .select("id,status,created_at,completed_at")
                .gte("created_at", start_date.isoformat())
                .lte("created_at", end_date.isoformat())
                .execute()
            )
            workflows = workflows_response.data or []
            
            total_videos = len(workflows)
            completed_videos = sum(1 for w in workflows if w.get("status") == "completed")
            failed_videos = sum(1 for w in workflows if w.get("status") == "failed")
            
            # Calculate average generation time
            generation_times = []
            for w in workflows:
                if w.get("completed_at") and w.get("created_at"):
                    try:
                        start = datetime.fromisoformat(w["created_at"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(w["completed_at"].replace("Z", "+00:00"))
                        generation_times.append((end - start).total_seconds())
                    except Exception:
                        pass
            
            avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0.0
            avg_cost_per_video = summary.get("total_cost_usd", 0.0) / total_videos if total_videos > 0 else 0.0
            
            # Transform to frontend-expected format
            # success_rate and cache_hit_rate are already percentages (0-100), convert to decimal (0-1)
            success_rate = summary.get("success_rate", 0.0) / 100.0
            cache_hit_rate = summary.get("cache_hit_rate", 0.0) / 100.0
            
            # Transform by_type to by_generation_type
            by_generation_type = {}
            for gen_type, data in summary.get("by_type", {}).items():
                by_generation_type[gen_type] = {
                    "tokens": data.get("tokens", 0),
                    "cost_usd": data.get("cost_usd", 0.0),
                    "count": data.get("count", 0),
                }
            
            # Transform by_model
            by_model = {}
            for model, data in summary.get("by_model", {}).items():
                by_model[model] = {
                    "tokens": data.get("tokens", 0),
                    "cost_usd": data.get("cost_usd", 0.0),
                    "calls": data.get("count", 0),
                }
        
        log_success(logger, f"Usage summary retrieved for {days} days")
        log_key_value(logger, "Total cost", f"${summary.get('total_cost_usd', 0):.2f}")
        log_key_value(logger, "Total videos", total_videos)
        
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", "/api/v1/monitoring/summary", 200, duration_ms)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
            "totals": {
                "total_tokens": summary.get("total_tokens", 0),
                "total_cost_usd": summary.get("total_cost_usd", 0.0),
                "total_videos": total_videos,
                "completed_videos": completed_videos,
                "failed_videos": failed_videos,
            },
            "by_generation_type": by_generation_type,
            "by_model": by_model,
            "metrics": {
                "success_rate": success_rate,
                "cache_hit_rate": cache_hit_rate,
                "avg_generation_time_seconds": round(avg_generation_time, 2),
                "avg_cost_per_video_usd": round(avg_cost_per_video, 4),
            },
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
    
    # Transform pricing to frontend-expected format
    pricing_dict = {}
    for model, prices in CostCalculator.PRICING.items():
        if "per_second" in prices:
            pricing_dict[model] = {
                "unit": "per second",
                "price": prices["per_second"],
            }
        elif "per_query" in prices:
            pricing_dict[model] = {
                "unit": "per query",
                "price": prices["per_query"],
            }
        elif "per_image" in prices:
            pricing_dict[model] = {
                "unit": "per image + tokens",
                "price": prices.get("per_image", 0),
            }
        else:
            # Text models - use output price as primary
            pricing_dict[model] = {
                "unit": "per million tokens",
                "price": prices.get("output", prices.get("input", 0)),
            }
    
    log_success(logger, "Pricing information retrieved")
    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "GET", "/api/v1/monitoring/pricing", 200, duration_ms)
    
    return pricing_dict
