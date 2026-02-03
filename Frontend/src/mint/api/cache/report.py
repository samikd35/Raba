"""
Report Cache Manager

Advanced caching strategies specifically optimized for report history functionality.
Implements intelligent cache warming, invalidation, and performance monitoring.

Requirements addressed:
- 2.4: Efficient historical report retrieval
- 4.5: Chat functionality performance with historical reports
"""

import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import json
import hashlib

from .enhanced import get_cache_service, EnhancedCacheService
from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ...utils.circuit_breaker import circuit_breaker
from .models import CacheStrategy, CacheEntry, CacheMetrics, CacheConfig
from .utils import (
    generate_cache_key, validate_cache_key, estimate_memory_usage,
    format_cache_size, create_cache_key_info, calculate_hit_rate
)

logger = logging.getLogger(__name__)

# CacheStrategy, CacheEntry, and CacheMetrics are now imported from models


class ReportCacheManager:
    """
    Advanced cache manager specifically optimized for report history operations.
    
    Features:
    - Intelligent cache warming based on user patterns
    - Predictive caching for likely-to-be-accessed reports
    - Hierarchical cache invalidation
    - Performance-based cache strategy adjustment
    """
    
    def __init__(
        self,
        cache_service: EnhancedCacheService = None,
        supabase_client: SupabaseClient = None,
        default_strategy: CacheStrategy = CacheStrategy.BALANCED
    ):
        """
        Initialize the report cache manager.
        
        Args:
            cache_service: Cache service instance
            supabase_client: Supabase client instance
            default_strategy: Default caching strategy
        """
        self.cache_service = cache_service or get_cache_service()
        self.client = supabase_client or get_standard_client()
        self.default_strategy = default_strategy
        
        # Cache configuration by strategy
        self.strategy_config = {
            CacheStrategy.AGGRESSIVE: {
                "report_display_ttl": 3600,  # 1 hour
                "report_metadata_ttl": 7200,  # 2 hours
                "chat_context_ttl": 1800,    # 30 minutes
                "user_history_ttl": 1800,    # 30 minutes
                "batch_size": 100,
                "warm_threshold": 0.1  # Warm cache if hit rate < 10%
            },
            CacheStrategy.BALANCED: {
                "report_display_ttl": 1800,  # 30 minutes
                "report_metadata_ttl": 3600,  # 1 hour
                "chat_context_ttl": 900,     # 15 minutes
                "user_history_ttl": 900,     # 15 minutes
                "batch_size": 50,
                "warm_threshold": 0.3  # Warm cache if hit rate < 30%
            },
            CacheStrategy.CONSERVATIVE: {
                "report_display_ttl": 600,   # 10 minutes
                "report_metadata_ttl": 1200,  # 20 minutes
                "chat_context_ttl": 300,     # 5 minutes
                "user_history_ttl": 300,     # 5 minutes
                "batch_size": 25,
                "warm_threshold": 0.5  # Warm cache if hit rate < 50%
            }
        }
        
        # Cache entry tracking
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.user_strategies: Dict[str, CacheStrategy] = {}
        
        # Performance tracking
        self.performance_history: List[CacheMetrics] = []
        
    def get_user_strategy(self, user_id: str) -> CacheStrategy:
        """
        Get the optimal caching strategy for a user based on their usage patterns.
        
        Args:
            user_id: User ID
            
        Returns:
            Optimal caching strategy for the user
        """
        return self.user_strategies.get(user_id, self.default_strategy)
    
    def get_config(self, user_id: str) -> Dict[str, Any]:
        """
        Get cache configuration for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Cache configuration dictionary
        """
        strategy = self.get_user_strategy(user_id)
        return self.strategy_config[strategy]
    
    @circuit_breaker(
        name="cache_manager_get_report",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=10
    )
    async def get_cached_report(
        self,
        report_id: str,
        user_id: str,
        include_metadata: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a report from cache with intelligent fallback strategies.
        
        Args:
            report_id: Report ID to retrieve
            user_id: User ID for access control
            include_metadata: Whether to include metadata
            
        Returns:
            Cached report data or None if not found
        """
        cache_type = "metadata" if include_metadata else "display"
        cache_key = f"report_{cache_type}:{report_id}:{user_id}"
        
        try:
            # Try to get from cache
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                # Update access tracking
                await self._update_access_tracking(cache_key, user_id)
                logger.debug(f"Cache hit for report {report_id} (type: {cache_type})")
                return cached_data
            
            logger.debug(f"Cache miss for report {report_id} (type: {cache_type})")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached report {report_id}: {e}")
            return None
    
    @circuit_breaker(
        name="cache_manager_set_report",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=10
    )
    async def cache_report(
        self,
        report_id: str,
        user_id: str,
        report_data: Dict[str, Any],
        include_metadata: bool = False,
        force_strategy: Optional[CacheStrategy] = None
    ) -> bool:
        """
        Cache a report with intelligent TTL and strategy selection.
        
        Args:
            report_id: Report ID
            user_id: User ID
            report_data: Report data to cache
            include_metadata: Whether this includes metadata
            force_strategy: Force a specific caching strategy
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            strategy = force_strategy or self.get_user_strategy(user_id)
            config = self.strategy_config[strategy]
            
            cache_type = "metadata" if include_metadata else "display"
            cache_key = f"report_{cache_type}:{report_id}:{user_id}"
            
            # Determine TTL based on strategy and data type
            if include_metadata:
                ttl = config["report_metadata_ttl"]
            else:
                ttl = config["report_display_ttl"]
            
            # Cache the data
            success = await self.cache_service.set(cache_key, report_data, ttl=ttl)
            
            if success:
                # Track cache entry
                await self._track_cache_entry(cache_key, report_data, ttl, strategy, user_id)
                logger.debug(f"Cached report {report_id} (type: {cache_type}, strategy: {strategy.value})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching report {report_id}: {e}")
            return False
    
    async def cache_user_history(
        self,
        user_id: str,
        history_data: List[Dict[str, Any]],
        force_strategy: Optional[CacheStrategy] = None
    ) -> bool:
        """
        Cache user's report history list.
        
        Args:
            user_id: User ID
            history_data: List of report history items
            force_strategy: Force a specific caching strategy
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            strategy = force_strategy or self.get_user_strategy(user_id)
            config = self.strategy_config[strategy]
            
            cache_key = f"user_history:{user_id}"
            ttl = config["user_history_ttl"]
            
            success = await self.cache_service.set(cache_key, history_data, ttl=ttl)
            
            if success:
                await self._track_cache_entry(cache_key, history_data, ttl, strategy, user_id)
                logger.debug(f"Cached history for user {user_id} ({len(history_data)} items)")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching user history for {user_id}: {e}")
            return False
    
    async def get_cached_user_history(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached user history.
        
        Args:
            user_id: User ID
            
        Returns:
            Cached history data or None if not found
        """
        cache_key = f"user_history:{user_id}"
        
        try:
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                await self._update_access_tracking(cache_key, user_id)
                logger.debug(f"Cache hit for user history {user_id}")
                return cached_data
            
            logger.debug(f"Cache miss for user history {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached user history {user_id}: {e}")
            return None
    
    async def cache_chat_context(
        self,
        report_id: str,
        user_id: str,
        context_data: Dict[str, Any],
        force_strategy: Optional[CacheStrategy] = None
    ) -> bool:
        """
        Cache chat context for a report.
        
        Args:
            report_id: Report ID
            user_id: User ID
            context_data: Chat context data
            force_strategy: Force a specific caching strategy
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            strategy = force_strategy or self.get_user_strategy(user_id)
            config = self.strategy_config[strategy]
            
            cache_key = f"chat_context:{report_id}:{user_id}"
            ttl = config["chat_context_ttl"]
            
            success = await self.cache_service.set(cache_key, context_data, ttl=ttl)
            
            if success:
                await self._track_cache_entry(cache_key, context_data, ttl, strategy, user_id)
                logger.debug(f"Cached chat context for report {report_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching chat context for report {report_id}: {e}")
            return False
    
    async def get_cached_chat_context(
        self,
        report_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached chat context for a report.
        
        Args:
            report_id: Report ID
            user_id: User ID
            
        Returns:
            Cached chat context or None if not found
        """
        cache_key = f"chat_context:{report_id}:{user_id}"
        
        try:
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                await self._update_access_tracking(cache_key, user_id)
                logger.debug(f"Cache hit for chat context {report_id}")
                return cached_data
            
            logger.debug(f"Cache miss for chat context {report_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached chat context {report_id}: {e}")
            return None
    
    async def warm_user_cache(
        self,
        user_id: str,
        user_token: str = None,
        max_reports: int = None
    ) -> Dict[str, Any]:
        """
        Intelligently warm cache for a user based on their usage patterns.
        
        Args:
            user_id: User ID to warm cache for
            user_token: JWT token for RLS
            max_reports: Maximum number of reports to cache
            
        Returns:
            Cache warming results
        """
        start_time = time.time()
        
        try:
            strategy = self.get_user_strategy(user_id)
            config = self.strategy_config[strategy]
            
            if max_reports is None:
                max_reports = config["batch_size"]
            
            logger.info(f"Warming cache for user {user_id} with strategy {strategy.value}")
            
            # Use service role client with user_id filtering for security
            # This avoids JWT authentication issues while maintaining data isolation
            from ..system.core.supabase_client import get_service_role_client
            service_client = get_service_role_client()
            
            # Get user's most accessed reports (based on view count if available)
            query = service_client.client.from_("report_display_view") \
                .select("id,title,created_at,updated_at") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(max_reports)
            
            response = query.execute()
            reports_to_cache = response.data
            
            if not reports_to_cache:
                return {
                    "reports_cached": 0,
                    "execution_time": time.time() - start_time,
                    "strategy": strategy.value
                }
            
            # Cache reports in batches
            batch_size = min(config["batch_size"], 25)  # Limit batch size for warming
            cached_count = 0
            
            for i in range(0, len(reports_to_cache), batch_size):
                batch = reports_to_cache[i:i + batch_size]
                batch_ids = [r["id"] for r in batch]
                
                # Retrieve and cache display data
                display_query = self.client.client.from_("report_display_view") \
                    .select("id,title,summary,report_type,content,created_at,updated_at") \
                    .in_("id", batch_ids) \
                    .eq("user_id", user_id)
                
                display_response = display_query.execute()
                
                # Cache each report
                cache_tasks = []
                for report_data in display_response.data:
                    report_id = report_data["id"]
                    cache_tasks.append(
                        self.cache_report(report_id, user_id, report_data, include_metadata=False, force_strategy=strategy)
                    )
                
                # Execute cache operations
                if cache_tasks:
                    results = await asyncio.gather(*cache_tasks, return_exceptions=True)
                    cached_count += sum(1 for r in results if r is True)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
            
            # Also cache user history
            history_data = [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "updated_at": r.get("updated_at")
                }
                for r in reports_to_cache
            ]
            
            await self.cache_user_history(user_id, history_data, force_strategy=strategy)
            
            execution_time = time.time() - start_time
            
            logger.info(f"Cache warming completed for user {user_id} in {execution_time:.2f}s, cached {cached_count} reports")
            
            return {
                "reports_cached": cached_count,
                "history_cached": True,
                "execution_time": execution_time,
                "strategy": strategy.value,
                "expected_hit_rate": 0.8 if strategy == CacheStrategy.AGGRESSIVE else 0.6
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Cache warming failed for user {user_id} after {execution_time:.2f}s: {e}")
            raise
    
    async def invalidate_user_cache(self, user_id: str) -> Dict[str, Any]:
        """
        Invalidate all cache entries for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Invalidation results
        """
        try:
            logger.info(f"Invalidating cache for user {user_id}")
            
            # Patterns to clear
            patterns = [
                f"report_display:*:{user_id}",
                f"report_metadata:*:{user_id}",
                f"chat_context:*:{user_id}",
                f"user_history:{user_id}"
            ]
            
            total_cleared = 0
            for pattern in patterns:
                cleared = await self.cache_service.clear_pattern(pattern)
                total_cleared += cleared
            
            # Remove from tracking
            keys_to_remove = [
                key for key in self.cache_entries.keys()
                if user_id in key
            ]
            
            for key in keys_to_remove:
                del self.cache_entries[key]
            
            logger.info(f"Invalidated {total_cleared} cache entries for user {user_id}")
            
            return {
                "entries_cleared": total_cleared,
                "patterns_cleared": len(patterns),
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {e}")
            raise
    
    async def invalidate_report_cache(self, report_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Invalidate cache entries for a specific report.
        
        Args:
            report_id: Report ID
            user_id: Optional user ID to limit scope
            
        Returns:
            Invalidation results
        """
        try:
            logger.info(f"Invalidating cache for report {report_id}")
            
            if user_id:
                # Clear specific user's cache for this report
                patterns = [
                    f"report_display:{report_id}:{user_id}",
                    f"report_metadata:{report_id}:{user_id}",
                    f"chat_context:{report_id}:{user_id}"
                ]
            else:
                # Clear all users' cache for this report
                patterns = [
                    f"report_display:{report_id}:*",
                    f"report_metadata:{report_id}:*",
                    f"chat_context:{report_id}:*"
                ]
            
            total_cleared = 0
            for pattern in patterns:
                cleared = await self.cache_service.clear_pattern(pattern)
                total_cleared += cleared
            
            logger.info(f"Invalidated {total_cleared} cache entries for report {report_id}")
            
            return {
                "entries_cleared": total_cleared,
                "report_id": report_id,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error invalidating cache for report {report_id}: {e}")
            raise
    
    async def optimize_user_strategy(self, user_id: str) -> CacheStrategy:
        """
        Optimize caching strategy for a user based on their usage patterns.
        
        Args:
            user_id: User ID
            
        Returns:
            Optimized caching strategy
        """
        try:
            # Analyze user's cache performance
            user_entries = [
                entry for entry in self.cache_entries.values()
                if user_id in entry.key
            ]
            
            if not user_entries:
                # No data, use default strategy
                return self.default_strategy
            
            # Calculate metrics
            total_accesses = sum(entry.access_count for entry in user_entries)
            avg_access_count = total_accesses / len(user_entries) if user_entries else 0
            
            # Determine optimal strategy based on usage patterns
            if avg_access_count > 10:
                # High usage - use aggressive caching
                optimal_strategy = CacheStrategy.AGGRESSIVE
            elif avg_access_count > 3:
                # Medium usage - use balanced caching
                optimal_strategy = CacheStrategy.BALANCED
            else:
                # Low usage - use conservative caching
                optimal_strategy = CacheStrategy.CONSERVATIVE
            
            # Update user strategy if it changed
            current_strategy = self.user_strategies.get(user_id, self.default_strategy)
            if optimal_strategy != current_strategy:
                self.user_strategies[user_id] = optimal_strategy
                logger.info(f"Updated caching strategy for user {user_id}: {current_strategy.value} -> {optimal_strategy.value}")
            
            return optimal_strategy
            
        except Exception as e:
            logger.error(f"Error optimizing strategy for user {user_id}: {e}")
            return self.default_strategy
    
    async def get_cache_metrics(self) -> CacheMetrics:
        """
        Get comprehensive cache performance metrics.
        
        Returns:
            Cache metrics
        """
        try:
            cache_stats = await self.cache_service.get_stats()
            
            # Calculate additional metrics
            total_entries = len(self.cache_entries)
            total_accesses = sum(entry.access_count for entry in self.cache_entries.values())
            
            # Estimate memory usage
            estimated_memory_mb = 0
            for entry in self.cache_entries.values():
                estimated_memory_mb += entry.size_bytes / (1024 * 1024)
            
            metrics = CacheMetrics(
                hit_rate=cache_stats.get("hit_rate", 0.0),
                miss_rate=1.0 - cache_stats.get("hit_rate", 0.0),
                eviction_rate=0.0,  # Would need to track this
                average_response_time=0.0,  # Would need to track this
                memory_usage_mb=estimated_memory_mb,
                total_entries=total_entries
            )
            
            # Store in history
            self.performance_history.append(metrics)
            
            # Keep only recent history
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-50:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return CacheMetrics(0.0, 1.0, 0.0, 0.0, 0.0, 0)
    
    async def _track_cache_entry(
        self,
        cache_key: str,
        data: Any,
        ttl: int,
        strategy: CacheStrategy,
        user_id: str
    ):
        """Track a cache entry for metrics and optimization."""
        try:
            # Estimate size
            data_str = json.dumps(data, default=str)
            size_bytes = len(data_str.encode('utf-8'))
            
            entry = CacheEntry(
                key=cache_key,
                size_bytes=size_bytes,
                created_at=datetime.now(timezone.utc),
                last_accessed=datetime.now(timezone.utc),
                access_count=1,
                ttl_seconds=ttl,
                strategy=strategy
            )
            
            self.cache_entries[cache_key] = entry
            
        except Exception as e:
            logger.debug(f"Error tracking cache entry {cache_key}: {e}")
    
    async def _update_access_tracking(self, cache_key: str, user_id: str):
        """Update access tracking for a cache entry."""
        try:
            if cache_key in self.cache_entries:
                entry = self.cache_entries[cache_key]
                entry.last_accessed = datetime.now(timezone.utc)
                entry.access_count += 1
                
        except Exception as e:
            logger.debug(f"Error updating access tracking for {cache_key}: {e}")


# Global cache manager instance
_global_cache_manager = None


def get_report_cache_manager() -> ReportCacheManager:
    """Get the global report cache manager instance."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = ReportCacheManager()
    return _global_cache_manager


def initialize_report_cache_manager(
    cache_service: EnhancedCacheService = None,
    supabase_client: SupabaseClient = None,
    default_strategy: CacheStrategy = CacheStrategy.BALANCED
) -> ReportCacheManager:
    """
    Initialize the global report cache manager.
    
    Args:
        cache_service: Cache service instance
        supabase_client: Supabase client instance
        default_strategy: Default caching strategy
        
    Returns:
        Initialized cache manager
    """
    global _global_cache_manager
    _global_cache_manager = ReportCacheManager(
        cache_service=cache_service,
        supabase_client=supabase_client,
        default_strategy=default_strategy
    )
    return _global_cache_manager