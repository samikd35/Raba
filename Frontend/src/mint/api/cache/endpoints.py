"""
Cache Health Check and Statistics Endpoints.

Provides endpoints for monitoring Redis cache health and performance metrics.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .redis_service import get_cache_service, RedisCacheService

logger = logging.getLogger(__name__)

# Create router for cache endpoints
cache_router = APIRouter(
    prefix="/api/cache",
    tags=["cache"],
)


class CacheHealthResponse(BaseModel):
    """Response model for cache health check."""
    healthy: bool
    backend: str
    using_fallback: bool
    timestamp: float
    ping_latency_ms: float | None = None
    redis_info: Dict[str, Any] | None = None
    memory_stats: Dict[str, Any] | None = None
    error: str | None = None


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    hits: int
    misses: int
    sets: int
    deletes: int
    errors: int
    fallback_activations: int
    total_operations: int
    hit_rate_percent: float
    backend: str
    using_fallback: bool
    key_count: int | None = None
    redis_memory: Dict[str, Any] | None = None
    memory_stats: Dict[str, Any] | None = None
    redis_stats_error: str | None = None
    hit_rate_warning: str | None = None


def get_cache() -> RedisCacheService:
    """Dependency to get the cache service."""
    return get_cache_service()


@cache_router.get(
    "/health",
    response_model=CacheHealthResponse,
    summary="Cache Health Check",
    description="Check the health status of the Redis cache service. Returns connectivity status, latency, and memory information."
)
async def cache_health_check(
    cache: RedisCacheService = Depends(get_cache)
) -> CacheHealthResponse:
    """
    Perform health check on the cache service.
    
    Returns:
        CacheHealthResponse with health status and diagnostics
        
    Requirements: 13.2
    """
    try:
        health = await cache.health_check()
        return CacheHealthResponse(**health)
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return CacheHealthResponse(
            healthy=False,
            backend="unknown",
            using_fallback=True,
            timestamp=datetime.utcnow().timestamp(),
            error=str(e)
        )


@cache_router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="Cache Statistics",
    description="Get detailed cache statistics including hit rate, operations count, and memory usage."
)
async def cache_statistics(
    cache: RedisCacheService = Depends(get_cache)
) -> CacheStatsResponse:
    """
    Get cache statistics and performance metrics.
    
    Returns:
        CacheStatsResponse with detailed statistics
        
    Requirements: 13.1, 13.3, 13.4, 13.5, 13.6
    """
    try:
        stats = await cache.get_stats()
        
        # Add warning if hit rate is below 50% (Requirement 13.4)
        hit_rate_warning = None
        total_ops = stats.get("total_operations", 0)
        hit_rate = stats.get("hit_rate_percent", 0)
        
        if total_ops > 100 and hit_rate < 50:
            hit_rate_warning = f"Cache hit rate is low ({hit_rate:.1f}%). Consider reviewing cache configuration."
            logger.warning(f"Cache hit rate warning: {hit_rate:.1f}%")
        
        return CacheStatsResponse(
            hits=stats.get("hits", 0),
            misses=stats.get("misses", 0),
            sets=stats.get("sets", 0),
            deletes=stats.get("deletes", 0),
            errors=stats.get("errors", 0),
            fallback_activations=stats.get("fallback_activations", 0),
            total_operations=stats.get("total_operations", 0),
            hit_rate_percent=stats.get("hit_rate_percent", 0.0),
            backend=stats.get("backend", "unknown"),
            using_fallback=stats.get("using_fallback", True),
            key_count=stats.get("key_count"),
            redis_memory=stats.get("redis_memory"),
            memory_stats=stats.get("memory_stats"),
            redis_stats_error=stats.get("redis_stats_error"),
            hit_rate_warning=hit_rate_warning
        )
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cache statistics: {str(e)}"
        )


@cache_router.post(
    "/reconnect",
    summary="Reconnect to Redis",
    description="Attempt to reconnect to Redis if currently using fallback mode."
)
async def cache_reconnect(
    cache: RedisCacheService = Depends(get_cache)
) -> Dict[str, Any]:
    """
    Attempt to reconnect to Redis.
    
    Returns:
        Status of reconnection attempt
    """
    try:
        if not cache._using_fallback:
            return {
                "success": True,
                "message": "Already connected to Redis",
                "backend": "redis"
            }
        
        connected = await cache.reconnect()
        
        if connected:
            return {
                "success": True,
                "message": "Successfully reconnected to Redis",
                "backend": "redis"
            }
        else:
            return {
                "success": False,
                "message": "Failed to reconnect to Redis, still using fallback",
                "backend": "memory"
            }
    except Exception as e:
        logger.error(f"Cache reconnection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reconnection failed: {str(e)}"
        )
