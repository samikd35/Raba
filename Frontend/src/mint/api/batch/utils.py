#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Processing Utility Functions.

This module provides utility functions for batch processing operations,
including data validation, formatting, and helper functions.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timezone, timedelta

from .models import (
    BatchOperation, BatchOperationType, BatchResult, BatchStatus,
    BatchProcessorConfig, BatchError, BATCH_ERROR_CODES
)

# Configure logging
logger = logging.getLogger(__name__)


def generate_operation_id(table_name: str, operation_type: BatchOperationType) -> str:
    """
    Generate a unique operation ID.
    
    Args:
        table_name: Table name
        operation_type: Operation type
        
    Returns:
        Unique operation ID
    """
    timestamp = datetime.now(timezone.utc).timestamp()
    unique_id = str(uuid.uuid4())[:8]
    return f"{table_name}_{operation_type.value}_{timestamp}_{unique_id}"


def validate_batch_data(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[str]:
    """
    Validate batch operation data.
    
    Args:
        data: Data to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not data:
        errors.append("Data cannot be empty")
        return errors
    
    if isinstance(data, list):
        if not data:
            errors.append("Data list cannot be empty")
            return errors
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {i} must be a dictionary")
            elif not item:
                errors.append(f"Item {i} cannot be empty")
    elif isinstance(data, dict):
        if not data:
            errors.append("Data dictionary cannot be empty")
    else:
        errors.append("Data must be a dictionary or list of dictionaries")
    
    return errors


def validate_filters(filters: Optional[Dict[str, Any]]) -> List[str]:
    """
    Validate batch operation filters.
    
    Args:
        filters: Filters to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if filters is not None:
        if not isinstance(filters, dict):
            errors.append("Filters must be a dictionary")
        elif not filters:
            errors.append("Filters cannot be empty")
        else:
            for key, value in filters.items():
                if not isinstance(key, str):
                    errors.append(f"Filter key '{key}' must be a string")
                if value is None:
                    errors.append(f"Filter value for '{key}' cannot be None")
    
    return errors


def format_batch_result(result: BatchResult) -> Dict[str, Any]:
    """
    Format a batch result for display.
    
    Args:
        result: Batch result to format
        
    Returns:
        Formatted result dictionary
    """
    return {
        "operation_id": result.operation_id,
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "execution_time": f"{result.execution_time:.3f}s",
        "retry_count": result.retry_count,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None
    }


def format_batch_operation(operation: BatchOperation) -> Dict[str, Any]:
    """
    Format a batch operation for display.
    
    Args:
        operation: Batch operation to format
        
    Returns:
        Formatted operation dictionary
    """
    return {
        "operation_id": operation.operation_id,
        "operation_type": operation.operation_type.value,
        "table_name": operation.table_name,
        "data": operation.data,
        "filters": operation.filters,
        "priority": operation.priority,
        "status": operation.status.value,
        "retry_count": operation.retry_count,
        "max_retries": operation.max_retries,
        "created_at": operation.created_at.isoformat()
    }


def calculate_batch_size(operations: List[BatchOperation], max_batch_size: int) -> int:
    """
    Calculate optimal batch size for operations.
    
    Args:
        operations: List of operations
        max_batch_size: Maximum batch size
        
    Returns:
        Optimal batch size
    """
    if not operations:
        return 0
    
    # Group by table and operation type
    groups = {}
    for op in operations:
        key = f"{op.table_name}_{op.operation_type.value}"
        if key not in groups:
            groups[key] = []
        groups[key].append(op)
    
    # Calculate size for each group
    total_size = 0
    for group_operations in groups.values():
        group_size = min(len(group_operations), max_batch_size)
        total_size += group_size
    
    return total_size


def estimate_processing_time(operations: List[BatchOperation]) -> float:
    """
    Estimate processing time for operations.
    
    Args:
        operations: List of operations
        
    Returns:
        Estimated processing time in seconds
    """
    if not operations:
        return 0.0
    
    # Base time per operation type
    base_times = {
        BatchOperationType.INSERT: 0.01,
        BatchOperationType.UPDATE: 0.02,
        BatchOperationType.DELETE: 0.015,
        BatchOperationType.UPSERT: 0.012
    }
    
    total_time = 0.0
    for op in operations:
        base_time = base_times.get(op.operation_type, 0.01)
        
        # Adjust for data size
        data_size = len(str(op.data)) if op.data else 0
        size_factor = 1 + (data_size / 1000) * 0.1  # 10% increase per KB
        
        # Adjust for priority
        priority_factor = 1 + (op.priority * 0.1)  # 10% increase per priority level
        
        operation_time = base_time * size_factor * priority_factor
        total_time += operation_time
    
    return total_time


def group_operations_by_priority(operations: List[BatchOperation]) -> Dict[int, List[BatchOperation]]:
    """
    Group operations by priority level.
    
    Args:
        operations: List of operations
        
    Returns:
        Dictionary of operations grouped by priority
    """
    groups = {}
    for op in operations:
        priority = op.priority
        if priority not in groups:
            groups[priority] = []
        groups[priority].append(op)
    
    return groups


def sort_operations_by_priority(operations: List[BatchOperation]) -> List[BatchOperation]:
    """
    Sort operations by priority (highest first).
    
    Args:
        operations: List of operations
        
    Returns:
        Sorted list of operations
    """
    return sorted(operations, key=lambda x: x.priority, reverse=True)


def filter_operations_by_age(
    operations: List[BatchOperation],
    max_age_seconds: int
) -> List[BatchOperation]:
    """
    Filter operations by age.
    
    Args:
        operations: List of operations
        max_age_seconds: Maximum age in seconds
        
    Returns:
        Filtered list of operations
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    
    return [
        op for op in operations
        if op.created_at >= cutoff_time
    ]


def create_batch_error(
    error_code: str,
    message: str,
    operation_id: Optional[str] = None,
    table_name: Optional[str] = None,
    operation_type: Optional[BatchOperationType] = None,
    details: Optional[Dict[str, Any]] = None
) -> BatchError:
    """
    Create a batch error object.
    
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
    return BatchError(
        error_code=error_code,
        message=message,
        operation_id=operation_id,
        table_name=table_name,
        operation_type=operation_type,
        details=details or {}
    )


def retry_operation_with_backoff(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> Any:
    """
    Retry an operation with exponential backoff.
    
    Args:
        operation: Operation to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential base for backoff
        
    Returns:
        Operation result
        
    Raises:
        Exception: If all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                break
            
            # Calculate delay
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            
            logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            logger.info(f"Retrying in {delay:.2f} seconds...")
            
            asyncio.sleep(delay)
    
    raise last_exception


def validate_batch_config(config: BatchProcessorConfig) -> List[str]:
    """
    Validate batch processor configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if config.batch_size <= 0:
        errors.append("Batch size must be positive")
    
    if config.max_wait_time <= 0:
        errors.append("Max wait time must be positive")
    
    if config.max_queue_size <= 0:
        errors.append("Max queue size must be positive")
    
    if config.max_retries < 0:
        errors.append("Max retries cannot be negative")
    
    if config.retry_delay <= 0:
        errors.append("Retry delay must be positive")
    
    if config.batch_size > config.max_queue_size:
        errors.append("Batch size cannot be greater than max queue size")
    
    return errors


def format_batch_statistics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format batch statistics for display.
    
    Args:
        stats: Statistics to format
        
    Returns:
        Formatted statistics
    """
    formatted = {}
    
    for key, value in stats.items():
        if isinstance(value, float):
            if key in ["success_rate", "avg_batch_size", "avg_processing_time"]:
                formatted[key] = f"{value:.2f}"
            else:
                formatted[key] = f"{value:.3f}"
        elif isinstance(value, datetime):
            formatted[key] = value.isoformat()
        else:
            formatted[key] = value
    
    return formatted


def calculate_success_rate(successful: int, failed: int) -> float:
    """
    Calculate success rate percentage.
    
    Args:
        successful: Number of successful operations
        failed: Number of failed operations
        
    Returns:
        Success rate percentage
    """
    total = successful + failed
    if total == 0:
        return 0.0
    
    return (successful / total) * 100


def format_processing_time(seconds: float) -> str:
    """
    Format processing time for display.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def create_operation_summary(operations: List[BatchOperation]) -> Dict[str, Any]:
    """
    Create a summary of operations.
    
    Args:
        operations: List of operations
        
    Returns:
        Operation summary
    """
    if not operations:
        return {
            "total_operations": 0,
            "operations_by_type": {},
            "operations_by_table": {},
            "priority_distribution": {},
            "avg_priority": 0.0
        }
    
    # Count by type
    operations_by_type = {}
    for op in operations:
        op_type = op.operation_type.value
        operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1
    
    # Count by table
    operations_by_table = {}
    for op in operations:
        table = op.table_name
        operations_by_table[table] = operations_by_table.get(table, 0) + 1
    
    # Priority distribution
    priority_distribution = {}
    for op in operations:
        priority = op.priority
        priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
    
    # Average priority
    total_priority = sum(op.priority for op in operations)
    avg_priority = total_priority / len(operations)
    
    return {
        "total_operations": len(operations),
        "operations_by_type": operations_by_type,
        "operations_by_table": operations_by_table,
        "priority_distribution": priority_distribution,
        "avg_priority": avg_priority
    }


