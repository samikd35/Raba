#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Processing Models and Data Structures.

This module contains Pydantic models and data structures for batch processing functionality,
including batch operations, results, and monitoring data.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from dataclasses import dataclass, field


class BatchOperationType(str, Enum):
    """Types of batch operations."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    UPSERT = "upsert"


class BatchStatus(str, Enum):
    """Batch processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchPriority(str, Enum):
    """Batch operation priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BatchOperation:
    """Represents a single batch operation."""
    operation_type: BatchOperationType
    table_name: str
    data: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    operation_id: Optional[str] = None
    priority: int = 0  # Higher numbers = higher priority
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: BatchStatus = BatchStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class BatchResult:
    """Result of a batch operation."""
    operation_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    completed_at: Optional[datetime] = None


class BatchOperationRequest(BaseModel):
    """Request model for batch operations."""
    operation_type: BatchOperationType
    table_name: str
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    filters: Optional[Dict[str, Any]] = None
    priority: int = 0
    max_retries: int = 3


class BatchOperationResponse(BaseModel):
    """Response model for batch operations."""
    operation_id: str
    status: BatchStatus
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None


class BatchProcessorConfig(BaseModel):
    """Configuration for batch processor."""
    batch_size: int = 100
    max_wait_time: float = 5.0
    max_queue_size: int = 1000
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_monitoring: bool = True
    enable_caching: bool = True


class BatchStatistics(BaseModel):
    """Batch processing statistics."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    batches_processed: int = 0
    avg_batch_size: float = 0.0
    avg_processing_time: float = 0.0
    success_rate: float = 0.0
    pending_operations: int = 0
    pending_results: int = 0
    is_processing: bool = False
    last_process_time: Optional[datetime] = None


class BatchHealthCheck(BaseModel):
    """Batch processor health check result."""
    healthy: bool
    stats: BatchStatistics
    queue_sizes: Dict[str, int] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BatchQueueInfo(BaseModel):
    """Information about a batch queue."""
    queue_key: str
    table_name: str
    operation_type: BatchOperationType
    operation_count: int
    oldest_operation: Optional[datetime] = None
    newest_operation: Optional[datetime] = None
    avg_priority: float = 0.0


class BatchOperationGroup(BaseModel):
    """Group of similar batch operations."""
    table_name: str
    operation_type: BatchOperationType
    operations: List[BatchOperation]
    total_count: int
    avg_priority: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchProcessingMetrics(BaseModel):
    """Detailed batch processing metrics."""
    period_start: datetime
    period_end: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    avg_processing_time: float
    max_processing_time: float
    min_processing_time: float
    operations_by_type: Dict[str, int] = Field(default_factory=dict)
    operations_by_table: Dict[str, int] = Field(default_factory=dict)
    error_summary: Dict[str, int] = Field(default_factory=dict)


class BatchRetryConfig(BaseModel):
    """Configuration for batch operation retries."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class BatchError(BaseModel):
    """Batch processing error."""
    error_code: str
    message: str
    operation_id: Optional[str] = None
    table_name: Optional[str] = None
    operation_type: Optional[BatchOperationType] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


class BatchOperationFilter(BaseModel):
    """Filter for batch operations."""
    table_name: Optional[str] = None
    operation_type: Optional[BatchOperationType] = None
    status: Optional[BatchStatus] = None
    priority_min: Optional[int] = None
    priority_max: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class BatchOperationSearch(BaseModel):
    """Search parameters for batch operations."""
    query: str
    search_fields: List[str] = ["operation_id", "table_name", "error"]
    case_sensitive: bool = False


class BatchProcessorInfo(BaseModel):
    """Information about batch processor instance."""
    processor_id: str
    config: BatchProcessorConfig
    stats: BatchStatistics
    queues: List[BatchQueueInfo] = Field(default_factory=list)
    is_active: bool = True
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: Optional[datetime] = None


# Constants for batch processing
DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_WAIT_TIME = 5.0
DEFAULT_MAX_QUEUE_SIZE = 1000
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0

# Priority levels
PRIORITY_LEVELS = {
    BatchPriority.LOW: 0,
    BatchPriority.NORMAL: 1,
    BatchPriority.HIGH: 2,
    BatchPriority.CRITICAL: 3
}

# Operation type descriptions
OPERATION_DESCRIPTIONS = {
    BatchOperationType.INSERT: "Insert new records",
    BatchOperationType.UPDATE: "Update existing records",
    BatchOperationType.DELETE: "Delete records",
    BatchOperationType.UPSERT: "Insert or update records"
}

# Error codes
BATCH_ERROR_CODES = {
    "INVALID_OPERATION": "Invalid batch operation",
    "QUEUE_FULL": "Batch queue is full",
    "PROCESSING_ERROR": "Error during batch processing",
    "VALIDATION_ERROR": "Data validation failed",
    "DATABASE_ERROR": "Database operation failed",
    "TIMEOUT_ERROR": "Operation timed out",
    "RETRY_EXHAUSTED": "Maximum retries exceeded",
    "CONFIGURATION_ERROR": "Invalid configuration"
}

# Status descriptions
STATUS_DESCRIPTIONS = {
    BatchStatus.PENDING: "Operation is waiting to be processed",
    BatchStatus.PROCESSING: "Operation is currently being processed",
    BatchStatus.COMPLETED: "Operation completed successfully",
    BatchStatus.FAILED: "Operation failed",
    BatchStatus.CANCELLED: "Operation was cancelled"
}


# Batch Search Models
class BatchSearchRequest(BaseModel):
    """Schema for a batch search request."""
    report_id: str
    queries: List[str]
    options: Optional[Dict[str, Any]] = None
    max_batch_size: int = 20
    priority: int = 0


class BatchSearchResult(BaseModel):
    """Schema for a batch search result."""
    query_index: int
    query: str
    chunks: List[Dict[str, Any]] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    execution_time: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchSearchConfig(BaseModel):
    """Configuration for batch search operations."""
    max_batch_size: int = 20
    max_queries: int = 1000
    timeout_seconds: int = 300
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    enable_parallel_processing: bool = True
    max_concurrent_searches: int = 10


class BatchSearchStatistics(BaseModel):
    """Statistics for batch search operations."""
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    total_queries: int = 0
    avg_queries_per_search: float = 0.0
    avg_execution_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchSearchError(BaseModel):
    """Error information for batch search operations."""
    error_code: str
    message: str
    query_index: Optional[int] = None
    report_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


# Batch Search Constants
DEFAULT_MAX_BATCH_SIZE = 20
DEFAULT_MAX_QUERIES = 1000
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_MAX_CONCURRENT_SEARCHES = 10

BATCH_SEARCH_ERROR_CODES = {
    "EMBEDDING_FAILED": "Failed to generate embeddings for queries",
    "SEARCH_FAILED": "Vector search operation failed",
    "TIMEOUT": "Search operation timed out",
    "INVALID_QUERY": "Invalid search query",
    "REPORT_NOT_FOUND": "Report not found",
    "BATCH_SIZE_EXCEEDED": "Batch size exceeds maximum allowed",
    "QUERY_LIMIT_EXCEEDED": "Query limit exceeded",
    "CACHE_ERROR": "Cache operation failed"
}
