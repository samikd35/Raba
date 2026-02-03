#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Processing Monitoring.

This module provides monitoring and health check functionality for batch processing,
including statistics tracking, performance monitoring, and alerting.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from .models import (
    BatchStatistics, BatchHealthCheck, BatchQueueInfo, BatchProcessingMetrics,
    BatchProcessorInfo, BatchError, BATCH_ERROR_CODES
)

# Configure logging
logger = logging.getLogger(__name__)


class BatchMonitor:
    """Monitor for batch processing operations."""
    
    def __init__(self):
        """Initialize the batch monitor."""
        self.metrics_history: List[BatchProcessingMetrics] = []
        self.error_history: List[BatchError] = []
        self.alert_thresholds = {
            "success_rate_min": 95.0,
            "avg_processing_time_max": 10.0,
            "queue_size_max": 500,
            "error_rate_max": 5.0
        }
    
    def update_statistics(
        self,
        stats: BatchStatistics,
        operation_queues: Dict[str, List[Any]],
        processing_time: float
    ) -> BatchStatistics:
        """
        Update batch processing statistics.
        
        Args:
            stats: Current statistics
            operation_queues: Current operation queues
            processing_time: Time taken for processing
            
        Returns:
            Updated statistics
        """
        # Update basic stats
        stats.last_process_time = datetime.now(timezone.utc)
        stats.pending_operations = sum(len(queue) for queue in operation_queues.values())
        
        # Calculate success rate
        total_ops = stats.successful_operations + stats.failed_operations
        if total_ops > 0:
            stats.success_rate = (stats.successful_operations / total_ops) * 100
        
        # Update averages
        if stats.batches_processed > 0:
            # Update average batch size
            current_avg = stats.avg_batch_size
            new_batch_size = stats.pending_operations
            stats.avg_batch_size = (
                (current_avg * (stats.batches_processed - 1) + new_batch_size) / 
                stats.batches_processed
            )
            
            # Update average processing time
            current_avg_time = stats.avg_processing_time
            stats.avg_processing_time = (
                (current_avg_time * (stats.batches_processed - 1) + processing_time) / 
                stats.batches_processed
            )
        
        return stats
    
    def create_health_check(
        self,
        stats: BatchStatistics,
        operation_queues: Dict[str, List[Any]],
        is_processing: bool
    ) -> BatchHealthCheck:
        """
        Create a health check result.
        
        Args:
            stats: Current statistics
            operation_queues: Current operation queues
            is_processing: Whether processor is currently processing
            
        Returns:
            Health check result
        """
        healthy = True
        errors = []
        warnings = []
        
        # Check success rate
        if stats.success_rate < self.alert_thresholds["success_rate_min"]:
            healthy = False
            errors.append(f"Success rate {stats.success_rate:.1f}% is below threshold {self.alert_thresholds['success_rate_min']}%")
        
        # Check average processing time
        if stats.avg_processing_time > self.alert_thresholds["avg_processing_time_max"]:
            warnings.append(f"Average processing time {stats.avg_processing_time:.2f}s exceeds threshold {self.alert_thresholds['avg_processing_time_max']}s")
        
        # Check queue size
        if stats.pending_operations > self.alert_thresholds["queue_size_max"]:
            warnings.append(f"Queue size {stats.pending_operations} exceeds threshold {self.alert_thresholds['queue_size_max']}")
        
        # Check error rate
        total_ops = stats.successful_operations + stats.failed_operations
        if total_ops > 0:
            error_rate = (stats.failed_operations / total_ops) * 100
            if error_rate > self.alert_thresholds["error_rate_max"]:
                healthy = False
                errors.append(f"Error rate {error_rate:.1f}% exceeds threshold {self.alert_thresholds['error_rate_max']}%")
        
        # Check if processor is stuck
        if is_processing and stats.last_process_time:
            time_since_last = (datetime.now(timezone.utc) - stats.last_process_time).total_seconds()
            if time_since_last > 300:  # 5 minutes
                healthy = False
                errors.append(f"Processor appears to be stuck - no activity for {time_since_last:.0f} seconds")
        
        # Create queue info
        queue_sizes = {
            queue_key: len(operations)
            for queue_key, operations in operation_queues.items()
        }
        
        return BatchHealthCheck(
            healthy=healthy,
            stats=stats,
            queue_sizes=queue_sizes,
            errors=errors,
            warnings=warnings
        )
    
    def get_queue_info(self, operation_queues: Dict[str, List[Any]]) -> List[BatchQueueInfo]:
        """
        Get information about operation queues.
        
        Args:
            operation_queues: Current operation queues
            
        Returns:
            List of queue information
        """
        queue_info = []
        
        for queue_key, operations in operation_queues.items():
            if not operations:
                continue
            
            # Parse queue key (format: table_name_operation_type)
            parts = queue_key.split('_', 1)
            table_name = parts[0] if len(parts) > 0 else "unknown"
            operation_type = parts[1] if len(parts) > 1 else "unknown"
            
            # Calculate queue metrics
            priorities = [op.priority for op in operations if hasattr(op, 'priority')]
            avg_priority = sum(priorities) / len(priorities) if priorities else 0.0
            
            timestamps = [op.created_at for op in operations if hasattr(op, 'created_at')]
            oldest_operation = min(timestamps) if timestamps else None
            newest_operation = max(timestamps) if timestamps else None
            
            queue_info.append(BatchQueueInfo(
                queue_key=queue_key,
                table_name=table_name,
                operation_type=operation_type,
                operation_count=len(operations),
                oldest_operation=oldest_operation,
                newest_operation=newest_operation,
                avg_priority=avg_priority
            ))
        
        return queue_info
    
    def record_metrics(
        self,
        period_start: datetime,
        period_end: datetime,
        stats: BatchStatistics,
        operations_by_type: Dict[str, int],
        operations_by_table: Dict[str, int],
        error_summary: Dict[str, int]
    ) -> BatchProcessingMetrics:
        """
        Record metrics for a time period.
        
        Args:
            period_start: Start of the period
            period_end: End of the period
            stats: Current statistics
            operations_by_type: Operations by type
            operations_by_table: Operations by table
            error_summary: Error summary
            
        Returns:
            Processing metrics
        """
        metrics = BatchProcessingMetrics(
            period_start=period_start,
            period_end=period_end,
            total_operations=stats.total_operations,
            successful_operations=stats.successful_operations,
            failed_operations=stats.failed_operations,
            avg_processing_time=stats.avg_processing_time,
            max_processing_time=stats.avg_processing_time,  # This would be tracked separately
            min_processing_time=0.0,  # This would be tracked separately
            operations_by_type=operations_by_type,
            operations_by_table=operations_by_table,
            error_summary=error_summary
        )
        
        # Add to history
        self.metrics_history.append(metrics)
        
        # Keep only last 100 entries
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return metrics
    
    def record_error(
        self,
        error_code: str,
        message: str,
        operation_id: Optional[str] = None,
        table_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> BatchError:
        """
        Record a batch processing error.
        
        Args:
            error_code: Error code
            message: Error message
            operation_id: Operation ID
            table_name: Table name
            operation_type: Operation type
            details: Additional details
            
        Returns:
            Batch error object
        """
        error = BatchError(
            error_code=error_code,
            message=message,
            operation_id=operation_id,
            table_name=table_name,
            operation_type=operation_type,
            details=details or {}
        )
        
        # Add to history
        self.error_history.append(error)
        
        # Keep only last 1000 entries
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        return error
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, int]:
        """
        Get error summary for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Error summary by error code
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_errors = [
            error for error in self.error_history
            if error.timestamp >= cutoff_time
        ]
        
        error_summary = {}
        for error in recent_errors:
            error_summary[error.error_code] = error_summary.get(error.error_code, 0) + 1
        
        return error_summary
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance trends for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Performance trends
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_metrics = [
            metrics for metrics in self.metrics_history
            if metrics.period_start >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "trend": "no_data",
                "avg_processing_time": 0.0,
                "success_rate": 0.0,
                "total_operations": 0
            }
        
        # Calculate trends
        avg_processing_times = [m.avg_processing_time for m in recent_metrics]
        success_rates = [
            (m.successful_operations / m.total_operations * 100) if m.total_operations > 0 else 0
            for m in recent_metrics
        ]
        
        # Determine trend
        if len(avg_processing_times) >= 2:
            if avg_processing_times[-1] > avg_processing_times[0]:
                trend = "degrading"
            elif avg_processing_times[-1] < avg_processing_times[0]:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "avg_processing_time": sum(avg_processing_times) / len(avg_processing_times),
            "success_rate": sum(success_rates) / len(success_rates),
            "total_operations": sum(m.total_operations for m in recent_metrics),
            "data_points": len(recent_metrics)
        }
    
    def check_alerts(self, health_check: BatchHealthCheck) -> List[Dict[str, Any]]:
        """
        Check for alerts based on health check.
        
        Args:
            health_check: Health check result
            
        Returns:
            List of alerts
        """
        alerts = []
        
        # Check for errors
        for error in health_check.errors:
            alerts.append({
                "type": "error",
                "message": error,
                "timestamp": datetime.now(timezone.utc),
                "severity": "high"
            })
        
        # Check for warnings
        for warning in health_check.warnings:
            alerts.append({
                "type": "warning",
                "message": warning,
                "timestamp": datetime.now(timezone.utc),
                "severity": "medium"
            })
        
        # Check for queue size alerts
        for queue_key, size in health_check.queue_sizes.items():
            if size > self.alert_thresholds["queue_size_max"]:
                alerts.append({
                    "type": "queue_size",
                    "message": f"Queue {queue_key} has {size} operations (threshold: {self.alert_thresholds['queue_size_max']})",
                    "timestamp": datetime.now(timezone.utc),
                    "severity": "medium",
                    "queue_key": queue_key,
                    "queue_size": size
                })
        
        return alerts
    
    def update_alert_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        """
        Update alert thresholds.
        
        Args:
            new_thresholds: New threshold values
        """
        self.alert_thresholds.update(new_thresholds)
        logger.info(f"Updated alert thresholds: {new_thresholds}")
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for monitoring dashboard.
        
        Returns:
            Dashboard data
        """
        # Get recent metrics
        recent_metrics = self.metrics_history[-10:] if self.metrics_history else []
        
        # Get recent errors
        recent_errors = self.error_history[-50:] if self.error_history else []
        
        # Calculate summary statistics
        total_operations = sum(m.total_operations for m in recent_metrics)
        total_successful = sum(m.successful_operations for m in recent_metrics)
        total_failed = sum(m.failed_operations for m in recent_metrics)
        
        success_rate = (total_successful / total_operations * 100) if total_operations > 0 else 0
        
        # Get performance trends
        trends = self.get_performance_trends(24)
        
        return {
            "summary": {
                "total_operations": total_operations,
                "successful_operations": total_successful,
                "failed_operations": total_failed,
                "success_rate": success_rate,
                "avg_processing_time": trends["avg_processing_time"],
                "trend": trends["trend"]
            },
            "recent_metrics": [
                {
                    "period_start": m.period_start.isoformat(),
                    "period_end": m.period_end.isoformat(),
                    "total_operations": m.total_operations,
                    "success_rate": (m.successful_operations / m.total_operations * 100) if m.total_operations > 0 else 0,
                    "avg_processing_time": m.avg_processing_time
                }
                for m in recent_metrics
            ],
            "recent_errors": [
                {
                    "error_code": e.error_code,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat(),
                    "operation_id": e.operation_id,
                    "table_name": e.table_name
                }
                for e in recent_errors
            ],
            "alert_thresholds": self.alert_thresholds
        }


