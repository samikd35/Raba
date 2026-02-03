#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Performance Monitoring Service for MINT.

This module provides functionality for monitoring and optimizing API performance.
"""

import logging
import time
import asyncio
import functools
from typing import Dict, List, Any, Optional, Callable, TypeVar, Awaitable
import statistics
from datetime import datetime, timedelta
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables for function signatures
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Awaitable[Any]])


class PerformanceMetric:
    """Class for tracking performance metrics for a specific operation."""
    
    def __init__(self, name: str, max_samples: int = 100):
        """Initialize the performance metric.
        
        Args:
            name: Name of the operation
            max_samples: Maximum number of samples to keep
        """
        self.name = name
        self.max_samples = max_samples
        self.durations = []
        self.start_times = {}
        self.error_count = 0
        self.success_count = 0
        self.last_updated = datetime.now()
        self.lock = threading.RLock()
    
    def start(self, operation_id: str = None) -> str:
        """Start timing an operation.
        
        Args:
            operation_id: Optional ID for the operation
            
        Returns:
            str: ID for the operation
        """
        with self.lock:
            if operation_id is None:
                operation_id = f"{self.name}_{time.time()}"
            
            self.start_times[operation_id] = time.time()
            return operation_id
    
    def end(self, operation_id: str, success: bool = True) -> Optional[float]:
        """End timing an operation and record the duration.
        
        Args:
            operation_id: ID of the operation
            success: Whether the operation was successful
            
        Returns:
            float: Duration of the operation in seconds, or None if not found
        """
        with self.lock:
            if operation_id not in self.start_times:
                return None
            
            start_time = self.start_times.pop(operation_id)
            duration = time.time() - start_time
            
            # Update metrics
            self.durations.append(duration)
            if len(self.durations) > self.max_samples:
                self.durations.pop(0)
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            
            self.last_updated = datetime.now()
            
            return duration
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this metric.
        
        Returns:
            Dict[str, Any]: Statistics for this metric
        """
        with self.lock:
            if not self.durations:
                return {
                    "name": self.name,
                    "count": 0,
                    "success_count": self.success_count,
                    "error_count": self.error_count,
                    "error_rate": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "median": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                    "last_updated": self.last_updated.isoformat()
                }
            
            total = self.success_count + self.error_count
            error_rate = self.error_count / total if total > 0 else 0.0
            
            # Calculate percentiles
            sorted_durations = sorted(self.durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p99_index = int(len(sorted_durations) * 0.99)
            
            return {
                "name": self.name,
                "count": len(self.durations),
                "success_count": self.success_count,
                "error_count": self.error_count,
                "error_rate": error_rate,
                "min": min(self.durations),
                "max": max(self.durations),
                "mean": statistics.mean(self.durations),
                "median": statistics.median(self.durations),
                "p95": sorted_durations[p95_index] if p95_index < len(sorted_durations) else sorted_durations[-1],
                "p99": sorted_durations[p99_index] if p99_index < len(sorted_durations) else sorted_durations[-1],
                "last_updated": self.last_updated.isoformat()
            }


class PerformanceMonitoringService:
    """Service for monitoring and optimizing API performance."""
    
    def __init__(self):
        """Initialize the performance monitoring service."""
        self.metrics = {}
        self.lock = threading.RLock()
    
    def get_metric(self, name: str) -> PerformanceMetric:
        """Get or create a performance metric.
        
        Args:
            name: Name of the metric
            
        Returns:
            PerformanceMetric: The performance metric
        """
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = PerformanceMetric(name)
            
            return self.metrics[name]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all metrics.
        
        Returns:
            Dict[str, Dict[str, Any]]: Statistics for all metrics
        """
        with self.lock:
            return {name: metric.get_stats() for name, metric in self.metrics.items()}
    
    def clear_metrics(self, older_than: Optional[timedelta] = None) -> int:
        """Clear metrics that haven't been updated recently.
        
        Args:
            older_than: Clear metrics older than this duration
            
        Returns:
            int: Number of metrics cleared
        """
        with self.lock:
            if older_than is None:
                count = len(self.metrics)
                self.metrics.clear()
                return count
            
            now = datetime.now()
            to_remove = []
            
            for name, metric in self.metrics.items():
                if now - metric.last_updated > older_than:
                    to_remove.append(name)
            
            for name in to_remove:
                del self.metrics[name]
            
            return len(to_remove)


# Singleton instance
_performance_monitoring_service = None


def get_performance_monitoring_service() -> PerformanceMonitoringService:
    """Get the singleton instance of the performance monitoring service.
    
    Returns:
        PerformanceMonitoringService: The performance monitoring service
    """
    global _performance_monitoring_service
    if _performance_monitoring_service is None:
        _performance_monitoring_service = PerformanceMonitoringService()
    return _performance_monitoring_service


def monitor_performance(name: Optional[str] = None):
    """Decorator for monitoring the performance of a function.
    
    Args:
        name: Name of the metric (defaults to function name)
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        metric_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            service = get_performance_monitoring_service()
            metric = service.get_metric(metric_name)
            
            operation_id = metric.start()
            try:
                result = func(*args, **kwargs)
                metric.end(operation_id, success=True)
                return result
            except Exception as e:
                metric.end(operation_id, success=False)
                raise e
        
        return wrapper
    
    return decorator


def monitor_async_performance(name: Optional[str] = None):
    """Decorator for monitoring the performance of an async function.
    
    Args:
        name: Name of the metric (defaults to function name)
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: AsyncF) -> AsyncF:
        metric_name = name or func.__name__
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            service = get_performance_monitoring_service()
            metric = service.get_metric(metric_name)
            
            operation_id = metric.start()
            try:
                result = await func(*args, **kwargs)
                metric.end(operation_id, success=True)
                return result
            except Exception as e:
                metric.end(operation_id, success=False)
                raise e
        
        return wrapper
    
    return decorator