#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Processing Module for MINT.

This module provides comprehensive batch processing functionality for database operations,
including batch operations, monitoring, and performance optimization.

Module Structure:
- models: Pydantic models and data structures
- processor: Main batch processor implementation
- operations: Batch operation handlers
- monitoring: Batch processing monitoring and health checks
- utils: Utility functions and helpers
"""

from .models import (
    # Enums
    BatchOperationType, BatchStatus, BatchPriority,
    
    # Core Models
    BatchOperation, BatchResult, BatchOperationRequest, BatchOperationResponse,
    BatchProcessorConfig, BatchStatistics, BatchHealthCheck, BatchQueueInfo,
    BatchOperationGroup, BatchProcessingMetrics, BatchRetryConfig, BatchError,
    BatchOperationFilter, BatchOperationSearch, BatchProcessorInfo,
    
    # Search Models
    BatchSearchRequest, BatchSearchResult, BatchSearchConfig,
    BatchSearchStatistics, BatchSearchError,
    
    # Constants
    DEFAULT_BATCH_SIZE, DEFAULT_MAX_WAIT_TIME, DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY, PRIORITY_LEVELS,
    OPERATION_DESCRIPTIONS, BATCH_ERROR_CODES, STATUS_DESCRIPTIONS,
    DEFAULT_MAX_BATCH_SIZE, DEFAULT_MAX_QUERIES, DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_CACHE_TTL_SECONDS, DEFAULT_MAX_CONCURRENT_SEARCHES,
    BATCH_SEARCH_ERROR_CODES
)
from .processor import BatchProcessor, get_batch_processor
from .operations import BatchOperationHandler
from .monitoring import BatchMonitor
from .search import BatchSearchService, get_batch_search_service, batch_search
from .utils import (
    # ID and Validation Functions
    generate_operation_id, validate_batch_data, validate_filters,
    validate_batch_config,
    
    # Formatting Functions
    format_batch_result, format_batch_operation, format_batch_statistics,
    format_processing_time,
    
    # Calculation Functions
    calculate_batch_size, estimate_processing_time, calculate_success_rate,
    create_operation_summary,
    
    # Grouping and Sorting Functions
    group_operations_by_priority, sort_operations_by_priority,
    filter_operations_by_age,
    
    # Error and Retry Functions
    create_batch_error, retry_operation_with_backoff
)

# Convenience functions for common operations
from .processor import batch_insert, batch_update, batch_delete

__all__ = [
    # Enums
    "BatchOperationType",
    "BatchStatus", 
    "BatchPriority",
    
    # Core Models
    "BatchOperation",
    "BatchResult",
    "BatchOperationRequest",
    "BatchOperationResponse",
    "BatchProcessorConfig",
    "BatchStatistics",
    "BatchHealthCheck",
    "BatchQueueInfo",
    "BatchOperationGroup",
    "BatchProcessingMetrics",
    "BatchRetryConfig",
    "BatchError",
    "BatchOperationFilter",
    "BatchOperationSearch",
    "BatchProcessorInfo",
    
    # Search Models
    "BatchSearchRequest",
    "BatchSearchResult",
    "BatchSearchConfig",
    "BatchSearchStatistics",
    "BatchSearchError",
    
    # Constants
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_MAX_WAIT_TIME",
    "DEFAULT_MAX_QUEUE_SIZE",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "PRIORITY_LEVELS",
    "OPERATION_DESCRIPTIONS",
    "BATCH_ERROR_CODES",
    "STATUS_DESCRIPTIONS",
    "DEFAULT_MAX_BATCH_SIZE",
    "DEFAULT_MAX_QUERIES",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_CACHE_TTL_SECONDS",
    "DEFAULT_MAX_CONCURRENT_SEARCHES",
    "BATCH_SEARCH_ERROR_CODES",
    
    # Main Classes
    "BatchProcessor",
    "BatchOperationHandler",
    "BatchMonitor",
    "BatchSearchService",
    
    # Utility Functions
    "generate_operation_id",
    "validate_batch_data",
    "validate_filters",
    "validate_batch_config",
    "format_batch_result",
    "format_batch_operation",
    "format_batch_statistics",
    "format_processing_time",
    "calculate_batch_size",
    "estimate_processing_time",
    "calculate_success_rate",
    "create_operation_summary",
    "group_operations_by_priority",
    "sort_operations_by_priority",
    "filter_operations_by_age",
    "create_batch_error",
    "retry_operation_with_backoff",
    
    # Convenience Functions
    "get_batch_processor",
    "batch_insert",
    "batch_update",
    "batch_delete",
    "get_batch_search_service",
    "batch_search"
]
