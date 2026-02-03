"""
Performance Optimizer

Advanced performance optimization service for report history functionality.
Implements database query optimization, caching strategies, and performance monitoring.

Requirements addressed:
- 2.4: Efficient historical report retrieval
- 4.5: Chat functionality performance with historical reports
"""

import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from functools import wraps
import json
import hashlib

from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..cache.enhanced import get_cache_service, cache_result
from ..services.utilities.query_optimizer import get_query_optimizer, monitor_query
from ...utils.circuit_breaker import circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    operation_name: str
    execution_time: float
    cache_hit: bool
    rows_processed: int
    memory_usage: Optional[int]
    timestamp: datetime
    user_id: str
    
    
@dataclass
class OptimizationResult:
    """Result of a performance optimization."""
    operation: str
    original_time: float
    optimized_time: float
    improvement_percent: float
    cache_enabled: bool
    batch_size: Optional[int]


class PerformanceOptimizer:
    """
    Advanced performance optimizer for report history operations.
    
    Provides:
    - Database query optimization
    - Intelligent caching strategies
    - Batch processing optimization
    - Performance monitoring and metrics
    """
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the performance optimizer.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.cache_service = get_cache_service()
        self.query_optimizer = get_query_optimizer()
        self.metrics: List[PerformanceMetrics] = []
        
        # Performance thresholds
        self.slow_query_threshold = 1.0  # 1 second
        self.cache_ttl_short = 300  # 5 minutes for frequently changing data
        self.cache_ttl_medium = 1800  # 30 minutes for stable data
        self.cache_ttl_long = 3600  # 1 hour for rarely changing data
        
        # Batch processing settings
        self.optimal_batch_sizes = {
            'report_retrieval': 50,
            'metadata_processing': 100,
            'cache_warming': 25,
            'index_optimization': 20
        }
        
    def record_metrics(self, metrics: PerformanceMetrics):
        """Record performance metrics."""
        self.metrics.append(metrics)
        
        # Keep only recent metrics to prevent memory bloat
        if len(self.metrics) > 10000:
            self.metrics = self.metrics[-5000:]
            
        # Log slow operations
        if metrics.execution_time > self.slow_query_threshold:
            logger.warning(
                f"Slow operation detected: {metrics.operation_name} took {metrics.execution_time:.2f}s "
                f"for user {metrics.user_id} (cache_hit: {metrics.cache_hit})"
            )
    
    @circuit_breaker(
        name="performance_optimizer_batch_retrieve",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=20
    )
    async def optimize_batch_report_retrieval(
        self,
        report_ids: List[str],
        user_id: str,
        user_token: str = None,
        include_metadata: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Optimized batch retrieval of reports with intelligent caching and query optimization.
        
        Args:
            report_ids: List of report IDs to retrieve
            user_id: User ID for access control
            user_token: JWT token for RLS
            include_metadata: Whether to include metadata
            
        Returns:
            Dict mapping report_id to report data
        """
        start_time = time.time()
        
        try:
            logger.info(f"Optimizing batch retrieval of {len(report_ids)} reports for user {user_id}")
            
            # Step 1: Check cache for existing reports
            cached_reports = {}
            uncached_ids = []
            
            for report_id in report_ids:
                cache_key = f"report_{'metadata' if include_metadata else 'display'}:{report_id}:{user_id}"
                cached_data = await self.cache_service.get(cache_key)
                
                if cached_data:
                    cached_reports[report_id] = cached_data
                else:
                    uncached_ids.append(report_id)
            
            logger.info(f"Cache hit for {len(cached_reports)} reports, need to fetch {len(uncached_ids)}")
            
            # Step 2: Batch retrieve uncached reports
            fresh_reports = {}
            if uncached_ids:
                fresh_reports = await self._batch_retrieve_reports(
                    uncached_ids, user_id, user_token, include_metadata
                )
                
                # Cache the fresh results
                cache_tasks = []
                for report_id, report_data in fresh_reports.items():
                    cache_key = f"report_{'metadata' if include_metadata else 'display'}:{report_id}:{user_id}"
                    ttl = self.cache_ttl_medium if include_metadata else self.cache_ttl_short
                    cache_tasks.append(
                        self.cache_service.set(cache_key, report_data, ttl=ttl)
                    )
                
                # Execute cache operations in parallel
                if cache_tasks:
                    await asyncio.gather(*cache_tasks, return_exceptions=True)
            
            # Step 3: Combine results
            all_reports = {**cached_reports, **fresh_reports}
            
            # Record performance metrics
            execution_time = time.time() - start_time
            metrics = PerformanceMetrics(
                operation_name="batch_report_retrieval",
                execution_time=execution_time,
                cache_hit=len(cached_reports) > 0,
                rows_processed=len(all_reports),
                memory_usage=None,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id
            )
            self.record_metrics(metrics)
            
            logger.info(f"Batch retrieval completed in {execution_time:.2f}s, returned {len(all_reports)} reports")
            return all_reports
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Batch retrieval optimization failed after {execution_time:.2f}s: {e}")
            raise
    
    async def _batch_retrieve_reports(
        self,
        report_ids: List[str],
        user_id: str,
        user_token: str = None,
        include_metadata: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Internal method for batch retrieving reports from database.
        
        Args:
            report_ids: List of report IDs to retrieve
            user_id: User ID for access control
            user_token: JWT token for RLS
            include_metadata: Whether to include metadata
            
        Returns:
            Dict mapping report_id to report data
        """
        if not report_ids:
            return {}
        
        # Use service role client with user_id filtering for security
        from ..system.core.supabase_client import get_service_role_client
        service_client = get_service_role_client()
        
        # Determine optimal batch size
        batch_size = self.optimal_batch_sizes['report_retrieval']
        results = {}
        
        # Process in batches to avoid query size limits
        for i in range(0, len(report_ids), batch_size):
            batch_ids = report_ids[i:i + batch_size]
            
            # Choose appropriate view and fields
            if include_metadata:
                view_name = "report_metadata_view"
                select_fields = "id,title,report_type,initial_query,clarification_questions,clarification_answers,workflow_metadata,created_at"
            else:
                view_name = "report_display_view"
                select_fields = "id,title,summary,report_type,content,created_at,updated_at"
            
            # Execute optimized query
            query = service_client.client.from_(view_name) \
                .select(select_fields) \
                .in_("id", batch_ids) \
                .eq("user_id", user_id)
            
            response = query.execute()
            
            # Process batch results
            for report_data in response.data:
                report_id = report_data["id"]
                
                if include_metadata:
                    processed_data = self._process_metadata_for_performance(report_data)
                else:
                    processed_data = self._extract_clean_content_for_performance(report_data)
                
                results[report_id] = processed_data
        
        return results
    
    def _extract_clean_content_for_performance(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performance-optimized version of clean content extraction.
        
        Args:
            report_data: Raw report data from database
            
        Returns:
            Clean report structure optimized for performance
        """
        try:
            # Basic structure with minimal processing
            clean_report = {
                "id": report_data["id"],
                "title": report_data.get("title", "Untitled Report"),
                "summary": report_data.get("summary", ""),
                "report_type": report_data.get("report_type", "final"),
                "created_at": report_data.get("created_at"),
                "updated_at": report_data.get("updated_at")
            }
            
            # Fast content processing
            content = report_data.get("content", {})
            
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    clean_report["content"] = {"report": str(content)}
                    return clean_report
            
            # Optimized content extraction
            if isinstance(content, dict):
                if "reports" in content and isinstance(content["reports"], dict):
                    reports = content["reports"]
                    
                    # Priority order for final report
                    for report_type in ["final", "market_validation", "industry", "pestel"]:
                        if report_type in reports:
                            final_report = reports[report_type]
                            if isinstance(final_report, str):
                                try:
                                    final_report = json.loads(final_report)
                                except json.JSONDecodeError:
                                    pass
                            
                            clean_report["content"] = final_report if isinstance(final_report, dict) else {"report": final_report}
                            break
                    else:
                        # No final report found, use first available
                        first_report = next(iter(reports.values()), {})
                        clean_report["content"] = first_report if isinstance(first_report, dict) else {"report": first_report}
                else:
                    clean_report["content"] = content
            else:
                clean_report["content"] = {"report": str(content)}
            
            return clean_report
            
        except Exception as e:
            logger.error(f"Performance content extraction failed: {e}")
            return {
                "id": report_data.get("id", "unknown"),
                "title": "Error Loading Report",
                "summary": "",
                "report_type": "error",
                "created_at": report_data.get("created_at"),
                "updated_at": report_data.get("updated_at"),
                "content": {"error": "Content extraction failed"}
            }
    
    def _process_metadata_for_performance(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performance-optimized metadata processing.
        
        Args:
            metadata: Raw metadata from database
            
        Returns:
            Processed metadata optimized for performance
        """
        try:
            processed = {
                "report_id": metadata["id"],
                "title": metadata.get("title", "Untitled Report"),
                "report_type": metadata.get("report_type", "final"),
                "created_at": metadata.get("created_at"),
                "initial_query": metadata.get("initial_query"),
                "clarification_questions": [],
                "clarification_answers": {},
                "workflow_metadata": {}
            }
            
            # Fast JSON parsing with error handling
            for field in ["clarification_questions", "clarification_answers", "workflow_metadata"]:
                value = metadata.get(field)
                if value:
                    if isinstance(value, str):
                        try:
                            parsed_value = json.loads(value)
                            processed[field] = parsed_value
                        except json.JSONDecodeError:
                            processed[field] = {} if field != "clarification_questions" else []
                    else:
                        processed[field] = value
            
            # Create optimized chat context
            context_parts = []
            if processed["initial_query"]:
                context_parts.append(f"Query: {processed['initial_query']}")
            
            if processed["clarification_questions"] and processed["clarification_answers"]:
                context_parts.append("Q&A:")
                questions = processed["clarification_questions"]
                answers = processed["clarification_answers"]
                
                if isinstance(questions, list):
                    for q in questions[:3]:  # Limit to first 3 for performance
                        answer = answers.get(q, "No answer") if isinstance(answers, dict) else "No answer"
                        context_parts.append(f"Q: {q}\nA: {answer}")
            
            processed["chat_context"] = "\n".join(context_parts)
            
            return processed
            
        except Exception as e:
            logger.error(f"Performance metadata processing failed: {e}")
            return {
                "report_id": metadata.get("id", "unknown"),
                "title": "Error Loading Metadata",
                "report_type": "error",
                "created_at": metadata.get("created_at"),
                "initial_query": None,
                "clarification_questions": [],
                "clarification_answers": {},
                "workflow_metadata": {},
                "chat_context": "Metadata processing failed",
                "error": "Processing failed"
            }
    
    @circuit_breaker(
        name="performance_optimizer_cache_warm",
        failure_threshold=2,
        recovery_timeout=60,
        timeout=30
    )
    async def warm_user_cache(
        self,
        user_id: str,
        user_token: str = None,
        max_reports: int = 50
    ) -> Dict[str, Any]:
        """
        Warm cache with user's most frequently accessed reports.
        
        Args:
            user_id: User ID to warm cache for
            user_token: JWT token for RLS
            max_reports: Maximum number of reports to cache
            
        Returns:
            Dict with cache warming results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Warming cache for user {user_id} with up to {max_reports} reports")
            
            # Use service role client with user_id filtering for security
            from ..system.core.supabase_client import get_service_role_client
            service_client = get_service_role_client()
            
            # Get user's most recent reports for cache warming
            query = service_client.client.from_("report_display_view") \
                .select("id,title,created_at") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(max_reports)
            
            response = query.execute()
            recent_reports = response.data
            
            if not recent_reports:
                logger.info(f"No reports found for user {user_id} to warm cache")
                return {"reports_cached": 0, "execution_time": time.time() - start_time}
            
            # Batch retrieve and cache reports
            report_ids = [r["id"] for r in recent_reports]
            batch_size = self.optimal_batch_sizes['cache_warming']
            
            cached_count = 0
            for i in range(0, len(report_ids), batch_size):
                batch_ids = report_ids[i:i + batch_size]
                
                # Retrieve batch
                batch_reports = await self._batch_retrieve_reports(
                    batch_ids, user_id, user_token, include_metadata=False
                )
                
                # Cache each report
                cache_tasks = []
                for report_id, report_data in batch_reports.items():
                    cache_key = f"report_display:{report_id}:{user_id}"
                    cache_tasks.append(
                        self.cache_service.set(cache_key, report_data, ttl=self.cache_ttl_medium)
                    )
                
                # Execute cache operations
                if cache_tasks:
                    results = await asyncio.gather(*cache_tasks, return_exceptions=True)
                    cached_count += sum(1 for r in results if r is True)
            
            execution_time = time.time() - start_time
            
            # Record metrics
            metrics = PerformanceMetrics(
                operation_name="cache_warming",
                execution_time=execution_time,
                cache_hit=False,  # This is a cache population operation
                rows_processed=cached_count,
                memory_usage=None,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id
            )
            self.record_metrics(metrics)
            
            logger.info(f"Cache warming completed in {execution_time:.2f}s, cached {cached_count} reports")
            
            return {
                "reports_cached": cached_count,
                "execution_time": execution_time,
                "cache_hit_rate_expected": 0.8  # Expected hit rate after warming
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Cache warming failed after {execution_time:.2f}s: {e}")
            raise
    
    async def optimize_chat_context_preparation(
        self,
        report_id: str,
        user_id: str,
        user_token: str = None
    ) -> Dict[str, Any]:
        """
        Optimize chat context preparation for historical reports.
        
        Args:
            report_id: Report ID to prepare context for
            user_id: User ID for access control
            user_token: JWT token for RLS
            
        Returns:
            Optimized chat context data
        """
        start_time = time.time()
        
        try:
            logger.info(f"Optimizing chat context preparation for report {report_id}")
            
            # Check if context is already cached
            context_cache_key = f"chat_context:{report_id}:{user_id}"
            cached_context = await self.cache_service.get(context_cache_key)
            
            if cached_context:
                execution_time = time.time() - start_time
                logger.info(f"Chat context retrieved from cache in {execution_time:.2f}s")
                
                # Record metrics
                metrics = PerformanceMetrics(
                    operation_name="chat_context_preparation",
                    execution_time=execution_time,
                    cache_hit=True,
                    rows_processed=1,
                    memory_usage=None,
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id
                )
                self.record_metrics(metrics)
                
                return cached_context
            
            # Retrieve report content and metadata efficiently
            report_data = await self.optimize_batch_report_retrieval(
                [report_id], user_id, user_token, include_metadata=False
            )
            
            metadata = await self.optimize_batch_report_retrieval(
                [report_id], user_id, user_token, include_metadata=True
            )
            
            if report_id not in report_data or report_id not in metadata:
                raise ValueError(f"Report {report_id} not found or access denied")
            
            # Prepare optimized chat context
            report_content = report_data[report_id]
            report_metadata = metadata[report_id]
            
            chat_context = {
                "report_id": report_id,
                "title": report_content.get("title", ""),
                "summary": report_content.get("summary", ""),
                "content_preview": self._create_content_preview(report_content.get("content", {})),
                "initial_query": report_metadata.get("initial_query", ""),
                "clarification_context": report_metadata.get("chat_context", ""),
                "prepared_at": datetime.now(timezone.utc).isoformat(),
                "embedding_ready": True
            }
            
            # Cache the prepared context
            await self.cache_service.set(
                context_cache_key, 
                chat_context, 
                ttl=self.cache_ttl_long
            )
            
            execution_time = time.time() - start_time
            
            # Record metrics
            metrics = PerformanceMetrics(
                operation_name="chat_context_preparation",
                execution_time=execution_time,
                cache_hit=False,
                rows_processed=1,
                memory_usage=None,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id
            )
            self.record_metrics(metrics)
            
            logger.info(f"Chat context prepared in {execution_time:.2f}s")
            return chat_context
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Chat context optimization failed after {execution_time:.2f}s: {e}")
            raise
    
    def _create_content_preview(self, content: Dict[str, Any], max_length: int = 1000) -> str:
        """
        Create a preview of report content for chat context.
        
        Args:
            content: Report content dictionary
            max_length: Maximum length of preview
            
        Returns:
            Content preview string
        """
        try:
            preview_parts = []
            
            # Extract key sections
            if isinstance(content, dict):
                for key in ["executive_summary", "summary", "overview", "introduction"]:
                    if key in content and content[key]:
                        preview_parts.append(f"{key.title()}: {str(content[key])[:200]}")
                        break
                
                # Add other important sections
                for key in ["market_overview", "industry_analysis", "recommendations"]:
                    if key in content and content[key]:
                        preview_parts.append(f"{key.replace('_', ' ').title()}: {str(content[key])[:150]}")
            
            preview = "\n".join(preview_parts)
            
            # Truncate if too long
            if len(preview) > max_length:
                preview = preview[:max_length] + "..."
            
            return preview or "Content preview not available"
            
        except Exception as e:
            logger.error(f"Content preview creation failed: {e}")
            return "Content preview generation failed"
    
    async def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Performance report with metrics and recommendations
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {
                "period_hours": hours,
                "total_operations": 0,
                "performance_score": 100,
                "recommendations": ["No operations recorded in the specified period"]
            }
        
        # Calculate performance statistics
        total_operations = len(recent_metrics)
        avg_execution_time = sum(m.execution_time for m in recent_metrics) / total_operations
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        cache_hit_rate = cache_hits / total_operations * 100
        slow_operations = sum(1 for m in recent_metrics if m.execution_time > self.slow_query_threshold)
        slow_operation_rate = slow_operations / total_operations * 100
        
        # Group by operation type
        operations_by_type = {}
        for metric in recent_metrics:
            op_type = metric.operation_name
            if op_type not in operations_by_type:
                operations_by_type[op_type] = {
                    "count": 0,
                    "total_time": 0,
                    "cache_hits": 0,
                    "slow_operations": 0
                }
            
            stats = operations_by_type[op_type]
            stats["count"] += 1
            stats["total_time"] += metric.execution_time
            if metric.cache_hit:
                stats["cache_hits"] += 1
            if metric.execution_time > self.slow_query_threshold:
                stats["slow_operations"] += 1
        
        # Calculate averages and rates
        for op_type, stats in operations_by_type.items():
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["count"] * 100
            stats["slow_operation_rate"] = stats["slow_operations"] / stats["count"] * 100
        
        # Calculate performance score (0-100)
        performance_score = 100
        if slow_operation_rate > 10:
            performance_score -= min(slow_operation_rate, 40)
        if cache_hit_rate < 50:
            performance_score -= min(50 - cache_hit_rate, 30)
        if avg_execution_time > 0.5:
            performance_score -= min(avg_execution_time * 20, 20)
        
        performance_score = max(0, performance_score)
        
        # Generate recommendations
        recommendations = []
        if slow_operation_rate > 10:
            recommendations.append(f"High slow operation rate ({slow_operation_rate:.1f}%). Consider query optimization.")
        if cache_hit_rate < 50:
            recommendations.append(f"Low cache hit rate ({cache_hit_rate:.1f}%). Consider cache warming strategies.")
        if avg_execution_time > 0.5:
            recommendations.append(f"High average execution time ({avg_execution_time:.2f}s). Review batch sizes and query complexity.")
        
        # Add specific recommendations based on operation types
        for op_type, stats in operations_by_type.items():
            if stats["slow_operation_rate"] > 20:
                recommendations.append(f"Operation '{op_type}' has high slow rate ({stats['slow_operation_rate']:.1f}%). Needs optimization.")
            if stats["cache_hit_rate"] < 30:
                recommendations.append(f"Operation '{op_type}' has low cache hit rate ({stats['cache_hit_rate']:.1f}%). Consider caching strategy.")
        
        return {
            "period_hours": hours,
            "total_operations": total_operations,
            "avg_execution_time": avg_execution_time,
            "cache_hit_rate": cache_hit_rate,
            "slow_operation_rate": slow_operation_rate,
            "performance_score": performance_score,
            "operations_by_type": operations_by_type,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Global performance optimizer instance
_global_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _global_performance_optimizer
    if _global_performance_optimizer is None:
        _global_performance_optimizer = PerformanceOptimizer()
    return _global_performance_optimizer


def optimize_performance(operation_name: str = "unknown"):
    """
    Decorator to automatically optimize performance for operations.
    
    Args:
        operation_name: Name of the operation being optimized
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            optimizer = get_performance_optimizer()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Extract user_id from args/kwargs if available
                user_id = "unknown"
                if args and len(args) > 1 and isinstance(args[1], str):
                    user_id = args[1]
                elif "user_id" in kwargs:
                    user_id = kwargs["user_id"]
                
                # Record metrics
                metrics = PerformanceMetrics(
                    operation_name=operation_name,
                    execution_time=execution_time,
                    cache_hit=False,  # Would need to detect this
                    rows_processed=1,  # Would need to detect this
                    memory_usage=None,
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id
                )
                optimizer.record_metrics(metrics)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Optimized operation {operation_name} failed after {execution_time:.2f}s: {e}")
                raise
                
        return wrapper
    return decorator