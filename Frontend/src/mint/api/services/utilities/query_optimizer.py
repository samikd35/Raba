"""
Database Query Optimizer

Provides query optimization utilities for improved database performance,
including query analysis, index suggestions, and batch processing.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from functools import wraps
import asyncio

from ...system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a database query."""
    query_hash: str
    execution_time: float
    rows_returned: int
    rows_examined: int
    timestamp: datetime
    query_type: str
    table_name: str
    
    
@dataclass
class IndexSuggestion:
    """Suggestion for database index optimization."""
    table_name: str
    columns: List[str]
    index_type: str
    estimated_benefit: float
    reason: str


class QueryOptimizer:
    """
    Database query optimizer for Supabase/PostgreSQL queries.
    Provides query analysis, performance monitoring, and optimization suggestions.
    """
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the query optimizer.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.query_metrics: List[QueryMetrics] = []
        self.slow_query_threshold = 1.0  # 1 second
        self.max_metrics_history = 1000
        
    def monitor_query(self, query_type: str = "unknown", table_name: str = "unknown"):
        """
        Decorator to monitor query performance.
        
        Args:
            query_type: Type of query (select, insert, update, delete)
            table_name: Name of the primary table being queried
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Extract metrics from result if possible
                    rows_returned = 0
                    rows_examined = 0
                    
                    if hasattr(result, 'data') and result.data:
                        rows_returned = len(result.data)
                    elif isinstance(result, (list, tuple)):
                        rows_returned = len(result)
                    elif isinstance(result, dict) and 'reports' in result:
                        rows_returned = len(result['reports'])
                        
                    # Create query hash for tracking
                    query_hash = hash(f"{func.__name__}:{str(args)}:{str(kwargs)}")
                    
                    # Record metrics
                    metrics = QueryMetrics(
                        query_hash=str(query_hash),
                        execution_time=execution_time,
                        rows_returned=rows_returned,
                        rows_examined=rows_examined,  # Would need EXPLAIN to get this
                        timestamp=datetime.now(timezone.utc),
                        query_type=query_type,
                        table_name=table_name
                    )
                    
                    self._record_metrics(metrics)
                    
                    # Log slow queries
                    if execution_time > self.slow_query_threshold:
                        logger.warning(
                            f"Slow query detected: {func.__name__} took {execution_time:.2f}s "
                            f"(returned {rows_returned} rows)"
                        )
                        
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"Query failed after {execution_time:.2f}s: {str(e)}")
                    raise
                    
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Extract metrics from result if possible
                    rows_returned = 0
                    rows_examined = 0
                    
                    if hasattr(result, 'data') and result.data:
                        rows_returned = len(result.data)
                    elif isinstance(result, (list, tuple)):
                        rows_returned = len(result)
                    elif isinstance(result, dict) and 'reports' in result:
                        rows_returned = len(result['reports'])
                        
                    # Create query hash for tracking
                    query_hash = hash(f"{func.__name__}:{str(args)}:{str(kwargs)}")
                    
                    # Record metrics
                    metrics = QueryMetrics(
                        query_hash=str(query_hash),
                        execution_time=execution_time,
                        rows_returned=rows_returned,
                        rows_examined=rows_examined,  # Would need EXPLAIN to get this
                        timestamp=datetime.now(timezone.utc),
                        query_type=query_type,
                        table_name=table_name
                    )
                    
                    self._record_metrics(metrics)
                    
                    # Log slow queries
                    if execution_time > self.slow_query_threshold:
                        logger.warning(
                            f"Slow query detected: {func.__name__} took {execution_time:.2f}s "
                            f"(returned {rows_returned} rows)"
                        )
                        
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"Query failed after {execution_time:.2f}s: {str(e)}")
                    raise
                    
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
                
        return decorator
        
    def _record_metrics(self, metrics: QueryMetrics):
        """Record query metrics."""
        self.query_metrics.append(metrics)
        
        # Keep only recent metrics to prevent memory bloat
        if len(self.query_metrics) > self.max_metrics_history:
            self.query_metrics = self.query_metrics[-self.max_metrics_history:]
            
    def get_slow_queries(self, threshold: float = None) -> List[QueryMetrics]:
        """
        Get queries that exceed the slow query threshold.
        
        Args:
            threshold: Custom threshold in seconds
            
        Returns:
            List of slow query metrics
        """
        threshold = threshold or self.slow_query_threshold
        return [m for m in self.query_metrics if m.execution_time > threshold]
        
    def get_query_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get query statistics for the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with query statistics
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_metrics = [m for m in self.query_metrics if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {
                "total_queries": 0,
                "avg_execution_time": 0,
                "slow_queries": 0,
                "queries_by_type": {},
                "queries_by_table": {}
            }
            
        total_time = sum(m.execution_time for m in recent_metrics)
        slow_queries = len([m for m in recent_metrics if m.execution_time > self.slow_query_threshold])
        
        # Group by query type
        queries_by_type = {}
        for metric in recent_metrics:
            if metric.query_type not in queries_by_type:
                queries_by_type[metric.query_type] = {
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0
                }
            queries_by_type[metric.query_type]["count"] += 1
            queries_by_type[metric.query_type]["total_time"] += metric.execution_time
            
        # Calculate averages
        for query_type in queries_by_type:
            stats = queries_by_type[query_type]
            stats["avg_time"] = stats["total_time"] / stats["count"]
            
        # Group by table
        queries_by_table = {}
        for metric in recent_metrics:
            if metric.table_name not in queries_by_table:
                queries_by_table[metric.table_name] = {
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0
                }
            queries_by_table[metric.table_name]["count"] += 1
            queries_by_table[metric.table_name]["total_time"] += metric.execution_time
            
        # Calculate averages
        for table_name in queries_by_table:
            stats = queries_by_table[table_name]
            stats["avg_time"] = stats["total_time"] / stats["count"]
            
        return {
            "total_queries": len(recent_metrics),
            "avg_execution_time": total_time / len(recent_metrics),
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / len(recent_metrics)) * 100,
            "queries_by_type": queries_by_type,
            "queries_by_table": queries_by_table,
            "time_period_hours": hours
        }
        
    def suggest_indexes(self) -> List[IndexSuggestion]:
        """
        Suggest database indexes based on query patterns.
        
        Returns:
            List of index suggestions
        """
        suggestions = []
        
        # Analyze query patterns
        table_queries = {}
        for metric in self.query_metrics:
            if metric.table_name not in table_queries:
                table_queries[metric.table_name] = []
            table_queries[metric.table_name].append(metric)
            
        # Generate suggestions based on common patterns
        for table_name, queries in table_queries.items():
            if table_name == "unknown":
                continue
                
            slow_queries = [q for q in queries if q.execution_time > self.slow_query_threshold]
            
            if len(slow_queries) >= 3:  # If we have many slow queries on this table
                # Suggest common indexes based on table name and query patterns
                if table_name == "mint_reports":
                    suggestions.extend(self._suggest_reports_indexes(slow_queries))
                elif table_name == "report_chats":
                    suggestions.extend(self._suggest_chats_indexes(slow_queries))
                elif table_name == "report_views":
                    suggestions.extend(self._suggest_views_indexes(slow_queries))
                    
        return suggestions
        
    def _suggest_reports_indexes(self, slow_queries: List[QueryMetrics]) -> List[IndexSuggestion]:
        """Suggest indexes for mint_reports table."""
        suggestions = []
        
        # Common query patterns for reports
        suggestions.append(IndexSuggestion(
            table_name="mint_reports",
            columns=["session_id", "created_at"],
            index_type="btree",
            estimated_benefit=0.8,
            reason="Optimize user report history queries with date sorting"
        ))
        
        suggestions.append(IndexSuggestion(
            table_name="mint_reports",
            columns=["session_id", "is_pinned"],
            index_type="btree",
            estimated_benefit=0.6,
            reason="Optimize pinned reports filtering"
        ))
        
        suggestions.append(IndexSuggestion(
            table_name="mint_reports",
            columns=["session_id", "deleted_at"],
            index_type="btree",
            estimated_benefit=0.7,
            reason="Optimize active/deleted reports filtering"
        ))
        
        suggestions.append(IndexSuggestion(
            table_name="mint_reports",
            columns=["tags"],
            index_type="gin",
            estimated_benefit=0.5,
            reason="Optimize tag-based filtering with GIN index"
        ))
        
        return suggestions
        
    def _suggest_chats_indexes(self, slow_queries: List[QueryMetrics]) -> List[IndexSuggestion]:
        """Suggest indexes for report_chats table."""
        suggestions = []
        
        suggestions.append(IndexSuggestion(
            table_name="report_chats",
            columns=["report_id", "created_at"],
            index_type="btree",
            estimated_benefit=0.8,
            reason="Optimize chat history retrieval with chronological order"
        ))
        
        suggestions.append(IndexSuggestion(
            table_name="report_chats",
            columns=["user_id", "created_at"],
            index_type="btree",
            estimated_benefit=0.6,
            reason="Optimize user chat history queries"
        ))
        
        return suggestions
        
    def _suggest_views_indexes(self, slow_queries: List[QueryMetrics]) -> List[IndexSuggestion]:
        """Suggest indexes for report_views table."""
        suggestions = []
        
        suggestions.append(IndexSuggestion(
            table_name="report_views",
            columns=["user_id", "viewed_at"],
            index_type="btree",
            estimated_benefit=0.7,
            reason="Optimize recent views tracking"
        ))
        
        suggestions.append(IndexSuggestion(
            table_name="report_views",
            columns=["report_id", "user_id"],
            index_type="btree",
            estimated_benefit=0.8,
            reason="Optimize view count queries and uniqueness checks"
        ))
        
        return suggestions
        
    async def optimize_batch_operations(
        self,
        operations: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[Any]:
        """
        Optimize batch database operations.
        
        Args:
            operations: List of database operations
            batch_size: Size of each batch
            
        Returns:
            List of operation results
        """
        results = []
        
        # Group operations by type and table
        operation_groups = {}
        for i, op in enumerate(operations):
            key = f"{op.get('type', 'unknown')}:{op.get('table', 'unknown')}"
            if key not in operation_groups:
                operation_groups[key] = []
            operation_groups[key].append((i, op))
            
        # Process each group in batches
        for group_key, group_ops in operation_groups.items():
            logger.info(f"Processing {len(group_ops)} operations for {group_key}")
            
            for i in range(0, len(group_ops), batch_size):
                batch = group_ops[i:i + batch_size]
                batch_results = await self._process_batch(batch)
                results.extend(batch_results)
                
        # Sort results by original order
        results.sort(key=lambda x: x[0])
        return [result[1] for result in results]
        
    async def _process_batch(self, batch: List[Tuple[int, Dict[str, Any]]]) -> List[Tuple[int, Any]]:
        """Process a batch of operations."""
        results = []
        
        for original_index, operation in batch:
            try:
                # This is a simplified example - in practice, you'd implement
                # specific batch processing for different operation types
                result = await self._execute_operation(operation)
                results.append((original_index, result))
            except Exception as e:
                logger.error(f"Batch operation failed: {str(e)}")
                results.append((original_index, {"error": str(e)}))
                
        return results
        
    async def _execute_operation(self, operation: Dict[str, Any]) -> Any:
        """Execute a single database operation."""
        # This is a placeholder - implement actual operation execution
        # based on your specific needs
        op_type = operation.get('type')
        table = operation.get('table')
        data = operation.get('data', {})
        
        if op_type == 'insert':
            response = self.client.client.table(table).insert(data).execute()
            return response.data
        elif op_type == 'update':
            response = self.client.client.table(table).update(data).execute()
            return response.data
        elif op_type == 'delete':
            response = self.client.client.table(table).delete().execute()
            return response.data
        else:
            raise ValueError(f"Unknown operation type: {op_type}")
            
    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Performance report with statistics and recommendations
        """
        stats = self.get_query_stats()
        slow_queries = self.get_slow_queries()
        index_suggestions = self.suggest_indexes()
        
        # Performance score (0-100)
        performance_score = 100
        if stats["slow_query_percentage"] > 10:
            performance_score -= min(stats["slow_query_percentage"], 50)
        if stats["avg_execution_time"] > 0.5:
            performance_score -= min(stats["avg_execution_time"] * 20, 30)
            
        performance_score = max(0, performance_score)
        
        # Recommendations
        recommendations = []
        if stats["slow_query_percentage"] > 10:
            recommendations.append("High percentage of slow queries detected. Consider optimizing frequent queries.")
        if stats["avg_execution_time"] > 0.5:
            recommendations.append("Average query time is high. Review query complexity and database indexes.")
        if len(index_suggestions) > 0:
            recommendations.append(f"Consider adding {len(index_suggestions)} suggested database indexes.")
            
        return {
            "performance_score": performance_score,
            "statistics": stats,
            "slow_queries_count": len(slow_queries),
            "index_suggestions": [
                {
                    "table": s.table_name,
                    "columns": s.columns,
                    "type": s.index_type,
                    "benefit": s.estimated_benefit,
                    "reason": s.reason
                }
                for s in index_suggestions
            ],
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Global query optimizer instance
_global_optimizer = None


def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer instance."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = QueryOptimizer()
    return _global_optimizer


def monitor_query(query_type: str = "unknown", table_name: str = "unknown"):
    """
    Decorator to monitor query performance using the global optimizer.
    
    Args:
        query_type: Type of query (select, insert, update, delete)
        table_name: Name of the primary table being queried
        
    Returns:
        Decorator function
    """
    optimizer = get_query_optimizer()
    return optimizer.monitor_query(query_type, table_name)