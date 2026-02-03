"""
Fallback Service

This service provides fallback mechanisms for when primary services fail,
including simplified queries, cached responses, and graceful degradation.
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Callable
from functools import wraps

from ...system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ...system.core.utils import is_valid_uuid
from ....utils.circuit_breaker import circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class FallbackService:
    """Service providing fallback mechanisms for failed operations."""
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the fallback service.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.reports_table = "mint_reports"
        self._cache = {}  # Simple in-memory cache for fallbacks
        
    def with_fallback(self, fallback_func: Callable = None):
        """
        Decorator to add fallback functionality to service methods.
        
        Args:
            fallback_func: Function to call if primary function fails
        """
        def decorator(primary_func):
            @wraps(primary_func)
            async def wrapper(*args, **kwargs):
                try:
                    # Try primary function
                    return await primary_func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Primary function {primary_func.__name__} failed: {str(e)}")
                    
                    # Try fallback function if provided
                    if fallback_func:
                        try:
                            logger.info(f"Attempting fallback for {primary_func.__name__}")
                            return await fallback_func(*args, **kwargs)
                        except Exception as fallback_error:
                            logger.error(f"Fallback also failed: {str(fallback_error)}")
                    
                    # If no fallback or fallback failed, return graceful degradation
                    return await self._graceful_degradation(primary_func.__name__, *args, **kwargs)
                    
            return wrapper
        return decorator
        
    async def _graceful_degradation(self, operation_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Provide graceful degradation when both primary and fallback fail.
        
        Args:
            operation_name: Name of the failed operation
            *args: Arguments passed to the original function
            **kwargs: Keyword arguments passed to the original function
            
        Returns:
            Minimal response structure
        """
        logger.info(f"Providing graceful degradation for {operation_name}")
        
        # Return appropriate minimal response based on operation
        if "history" in operation_name.lower():
            return {
                "reports": [],
                "pagination": {
                    "current_page": 1,
                    "page_size": 20,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                },
                "error": "Service temporarily unavailable. Please try again later.",
                "fallback_mode": True
            }
        elif "search" in operation_name.lower():
            return {
                "reports": [],
                "search_metadata": {
                    "query": kwargs.get("query", ""),
                    "total_matches": 0,
                    "search_time_ms": 0
                },
                "pagination": {
                    "current_page": 1,
                    "page_size": 20,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                },
                "error": "Search temporarily unavailable. Please try again later.",
                "fallback_mode": True
            }
        elif "analytics" in operation_name.lower():
            return {
                "creation_frequency": [],
                "topic_distribution": [],
                "industry_distribution": [],
                "summary_metrics": {
                    "total_reports": 0,
                    "reports_this_month": 0,
                    "avg_reports_per_day": 0.0
                },
                "error": "Analytics temporarily unavailable. Please try again later.",
                "fallback_mode": True
            }
        else:
            return {
                "success": False,
                "error": "Service temporarily unavailable. Please try again later.",
                "fallback_mode": True
            }
            
    async def simple_report_history_fallback(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Simplified fallback for report history retrieval.
        Uses basic query without complex filtering or processing.
        
        Args:
            user_id: The ID of the user
            filters: Optional filters (simplified)
            sort_by: Field to sort by
            sort_order: Sort order
            page: Page number
            page_size: Number of items per page
            
        Returns:
            Simplified report history response
        """
        try:
            logger.info(f"Using simple fallback for report history - user {user_id}")
            
            # Validate basic inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            # Use very basic query - just get reports for user
            query = self.client.client.table(self.reports_table) \
                .select("id, title, created_at, is_pinned") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .order("created_at", desc=True) \
                .limit(page_size)
                
            response = query.execute()
            reports = response.data
            
            # Minimal processing
            processed_reports = []
            for report in reports:
                processed_reports.append({
                    "id": report.get("id"),
                    "title": report.get("title", "Untitled Report"),
                    "created_at": report.get("created_at"),
                    "is_pinned": bool(report.get("is_pinned", False)),
                    "summary": "Summary unavailable in fallback mode",
                    "view_count": 0,
                    "has_chat": False,
                    "is_recent": False,
                    "tags": [],
                    "category": None
                })
                
            return {
                "reports": processed_reports,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": len(processed_reports),
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False
                },
                "fallback_mode": True,
                "message": "Using simplified view due to service issues"
            }
            
        except Exception as e:
            logger.error(f"Simple fallback also failed: {str(e)}")
            raise
            
    async def simple_search_fallback(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Simplified fallback for report search.
        Uses basic title matching instead of full-text search.
        
        Args:
            user_id: The ID of the user
            query: Search query
            filters: Optional filters (ignored in fallback)
            sort_by: Field to sort by
            sort_order: Sort order
            page: Page number
            page_size: Number of items per page
            
        Returns:
            Simplified search response
        """
        try:
            logger.info(f"Using simple search fallback - user {user_id}, query: '{query}'")
            
            # Validate inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            if not query or not query.strip():
                raise ValueError("Search query cannot be empty")
                
            # Simple title-only search
            search_query = self.client.client.table(self.reports_table) \
                .select("id, title, created_at, is_pinned") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .ilike("title", f"%{query.strip()}%") \
                .order("created_at", desc=True) \
                .limit(page_size)
                
            response = search_query.execute()
            reports = response.data
            
            # Minimal processing
            processed_reports = []
            for report in reports:
                processed_reports.append({
                    "id": report.get("id"),
                    "title": report.get("title", "Untitled Report"),
                    "created_at": report.get("created_at"),
                    "is_pinned": bool(report.get("is_pinned", False)),
                    "summary": "Summary unavailable in fallback mode",
                    "relevance_score": 0.5,  # Default relevance
                    "highlights": {
                        "title": [report.get("title", "")],
                        "summary": [],
                        "content": []
                    },
                    "view_count": 0,
                    "has_chat": False,
                    "tags": [],
                    "category": None
                })
                
            return {
                "reports": processed_reports,
                "search_metadata": {
                    "query": query,
                    "total_matches": len(processed_reports),
                    "search_time_ms": 0
                },
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": len(processed_reports),
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False
                },
                "fallback_mode": True,
                "message": "Using simplified search due to service issues"
            }
            
        except Exception as e:
            logger.error(f"Simple search fallback also failed: {str(e)}")
            raise
            
    async def simple_analytics_fallback(
        self,
        user_id: str,
        time_range: str = "month"
    ) -> Dict[str, Any]:
        """
        Simplified fallback for analytics.
        Provides basic statistics without complex processing.
        
        Args:
            user_id: The ID of the user
            time_range: Time range for analytics
            
        Returns:
            Simplified analytics response
        """
        try:
            logger.info(f"Using simple analytics fallback - user {user_id}")
            
            # Validate inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            # Get basic report count
            count_response = self.client.client.table(self.reports_table) \
                .select("id", count="exact") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .execute()
                
            total_reports = count_response.count or 0
            
            # Get recent reports for basic frequency
            recent_response = self.client.client.table(self.reports_table) \
                .select("created_at") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .gte("created_at", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()) \
                .execute()
                
            recent_reports = len(recent_response.data) if recent_response.data else 0
            
            return {
                "creation_frequency": [
                    {"date": datetime.now().strftime("%Y-%m-%d"), "count": recent_reports}
                ],
                "topic_distribution": [
                    {"topic": "General", "count": total_reports, "percentage": 100.0}
                ],
                "industry_distribution": [
                    {"industry": "Various", "count": total_reports, "percentage": 100.0}
                ],
                "summary_metrics": {
                    "total_reports": total_reports,
                    "reports_this_month": recent_reports,
                    "avg_reports_per_day": recent_reports / 30.0,
                    "most_active_day": "N/A",
                    "top_topic": "General",
                    "top_industry": "Various"
                },
                "fallback_mode": True,
                "message": "Using simplified analytics due to service issues"
            }
            
        except Exception as e:
            logger.error(f"Simple analytics fallback also failed: {str(e)}")
            raise
            
    async def cached_response_fallback(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Try to return a cached response as fallback.
        
        Args:
            cache_key: Key for the cached response
            
        Returns:
            Cached response if available, None otherwise
        """
        try:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                # Check if cache is still valid (e.g., less than 1 hour old)
                if time.time() - cached_data.get("timestamp", 0) < 3600:
                    logger.info(f"Returning cached response for {cache_key}")
                    response = cached_data["data"].copy()
                    response["from_cache"] = True
                    response["cache_timestamp"] = cached_data["timestamp"]
                    return response
                else:
                    # Remove expired cache
                    del self._cache[cache_key]
                    
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached response: {str(e)}")
            return None
            
    def cache_response(self, cache_key: str, response: Dict[str, Any]):
        """
        Cache a response for potential fallback use.
        
        Args:
            cache_key: Key for caching
            response: Response to cache
        """
        try:
            # Simple cache management - remove old entries if cache gets too large
            if len(self._cache) > 100:
                # Remove oldest entries
                sorted_cache = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].get("timestamp", 0)
                )
                for key, _ in sorted_cache[:50]:  # Remove oldest 50 entries
                    del self._cache[key]
                    
            self._cache[cache_key] = {
                "data": response.copy(),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
            
    def clear_cache(self):
        """Clear all cached responses."""
        self._cache.clear()
        logger.info("Fallback cache cleared")
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "oldest_entry": min(
                (entry["timestamp"] for entry in self._cache.values()),
                default=None
            ),
            "newest_entry": max(
                (entry["timestamp"] for entry in self._cache.values()),
                default=None
            )
        }


# Global fallback service instance
fallback_service = FallbackService()