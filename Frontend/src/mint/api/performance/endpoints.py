#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Performance Monitoring Endpoints for MINT.

This module provides API endpoints for monitoring and optimizing API performance.
"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .monitoring import get_performance_monitoring_service
# Role system removed - require_admin no longer available
from ..auth.production.system import get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/performance", tags=["performance"])


class PerformanceMetricResponse(BaseModel):
    """Response model for a performance metric."""
    name: str = Field(..., description="Name of the metric")
    count: int = Field(..., description="Number of samples")
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    error_rate: float = Field(..., description="Error rate")
    min: float = Field(..., description="Minimum duration in seconds")
    max: float = Field(..., description="Maximum duration in seconds")
    mean: float = Field(..., description="Mean duration in seconds")
    median: float = Field(..., description="Median duration in seconds")
    p95: float = Field(..., description="95th percentile duration in seconds")
    p99: float = Field(..., description="99th percentile duration in seconds")
    last_updated: str = Field(..., description="Last updated timestamp")


class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""
    metrics: Dict[str, PerformanceMetricResponse] = Field(..., description="Performance metrics")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    hits: int = Field(..., description="Number of cache hits")
    misses: int = Field(..., description="Number of cache misses")
    hit_ratio: float = Field(..., description="Cache hit ratio")
    evictions: int = Field(..., description="Number of cache evictions")
    expirations: int = Field(..., description="Number of cache expirations")
    size: int = Field(..., description="Current cache size")
    max_size: int = Field(..., description="Maximum cache size")
    tag_count: int = Field(..., description="Number of tags")
    memory_usage_estimate: int = Field(..., description="Estimated memory usage")
    total_cache_time_saved: float = Field(..., description="Total time saved by cache in seconds")


@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    current_user_id: str = Depends(get_current_user)
):
    """
    Get performance metrics for all operations.
    
    Args:
        current_user_id: The authenticated user ID
        is_admin_user: Whether the user is an admin
        
    Returns:
        PerformanceMetricsResponse: The performance metrics
    """
    # Only allow admins to access this endpoint
    if not is_admin_user:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "permission_denied",
                "message": "Only administrators can access performance metrics."
            }
        )
    
    try:
        # Get the performance monitoring service
        perf_service = get_performance_monitoring_service()
        
        # Get all metrics
        metrics = perf_service.get_all_metrics()
        
        return PerformanceMetricsResponse(metrics=metrics)
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "metrics_retrieval_error",
                "message": f"An error occurred while retrieving performance metrics: {str(e)}"
            }
        )


@router.get("/cache", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_user_id: str = Depends(get_current_user)
):
    """
    Get cache statistics.
    
    Args:
        current_user_id: The authenticated user ID
        is_admin_user: Whether the user is an admin
        
    Returns:
        CacheStatsResponse: The cache statistics
    """
    # Only allow admins to access this endpoint
    if not is_admin_user:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "permission_denied",
                "message": "Only administrators can access cache statistics."
            }
        )
    
    try:
        # Get cache statistics
        from .enhanced_cache_service import get_cache_stats
        stats = get_cache_stats()
        
        return CacheStatsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cache_stats_retrieval_error",
                "message": f"An error occurred while retrieving cache statistics: {str(e)}"
            }
        )


@router.post("/cache/clear", response_model=Dict[str, Any])
async def clear_cache(
    current_user_id: str = Depends(get_current_user),
    tag: Optional[str] = Query(None, description="Tag to clear (optional)")
):
    """
    Clear the cache.
    
    Args:
        current_user_id: The authenticated user ID
        is_admin_user: Whether the user is an admin
        tag: Tag to clear (optional)
        
    Returns:
        Dict[str, Any]: Result of the operation
    """
    # Only allow admins to access this endpoint
    if not is_admin_user:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "permission_denied",
                "message": "Only administrators can clear the cache."
            }
        )
    
    try:
        # Clear cache
        if tag:
            from .enhanced_cache_service import invalidate_by_tag
            count = invalidate_by_tag(tag)
            return {"success": True, "message": f"Cleared {count} items with tag '{tag}'"}
        else:
            from .enhanced_cache_service import tiered_cache
            tiered_cache.clear()
            return {"success": True, "message": "Cache cleared successfully"}
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cache_clear_error",
                "message": f"An error occurred while clearing the cache: {str(e)}"
            }
        )