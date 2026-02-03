"""
Batch Processing Service

Provides batch processing capabilities for database operations
to improve performance and reduce database load.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json

from ..supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..enhanced_cache_service import get_cache_service
from .models import (
    BatchOperation, BatchOperationType, BatchResult, BatchStatus,
    BatchProcessorConfig, BatchStatistics, BatchHealthCheck
)
from .operations import BatchOperationHandler
from .monitoring import BatchMonitor
from .utils import (
    generate_operation_id, validate_batch_data, validate_filters,
    format_batch_result, calculate_batch_size, estimate_processing_time
)

logger = logging.getLogger(__name__)


# BatchOperationType, BatchOperation, and BatchResult are now imported from models


class BatchProcessor:
    """
    Batch processor for database operations.
    Collects operations and processes them in optimized batches.
    """
    
    def __init__(
        self,
        supabase_client: SupabaseClient = None,
        config: BatchProcessorConfig = None
    ):
        """
        Initialize the batch processor.
        
        Args:
            supabase_client: Supabase client instance
            config: Batch processor configuration
        """
        self.client = supabase_client or get_standard_client()
        self.cache_service = get_cache_service()
        self.config = config or BatchProcessorConfig()
        
        # Initialize components
        self.operation_handler = BatchOperationHandler(self.client)
        self.monitor = BatchMonitor()
        
        # Operation queues by table and operation type
        self.operation_queues: Dict[str, List[BatchOperation]] = {}
        self.pending_results: Dict[str, asyncio.Future] = {}
        
        # Processing state
        self.is_processing = False
        self.last_process_time = datetime.now(timezone.utc)
        
        # Statistics
        self.stats = BatchStatistics()
        
    def add_operation(
        self,
        operation_type: BatchOperationType,
        table_name: str,
        data: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> asyncio.Future:
        """
        Add an operation to the batch queue.
        
        Args:
            operation_type: Type of operation
            table_name: Target table name
            data: Operation data
            filters: Optional filters for update/delete operations
            priority: Operation priority (higher = more important)
            
        Returns:
            Future that will contain the operation result
        """
        # Generate unique operation ID
        operation_id = generate_operation_id(table_name, operation_type)
        
        # Create operation
        operation = BatchOperation(
            operation_type=operation_type,
            table_name=table_name,
            data=data,
            filters=filters,
            operation_id=operation_id,
            priority=priority
        )
        
        # Create future for result
        future = asyncio.Future()
        self.pending_results[operation_id] = future
        
        # Add to appropriate queue
        queue_key = f"{table_name}_{operation_type.value}"
        if queue_key not in self.operation_queues:
            self.operation_queues[queue_key] = []
            
        self.operation_queues[queue_key].append(operation)
        
        # Sort by priority (highest first)
        self.operation_queues[queue_key].sort(key=lambda x: x.priority, reverse=True)
        
        # Check if we need to process immediately
        if self._should_process_now():
            asyncio.create_task(self._process_batches())
            
        return future
        
    def _should_process_now(self) -> bool:
        """Check if we should process batches now."""
        # Check if any queue is full
        for queue in self.operation_queues.values():
            if len(queue) >= self.config.batch_size:
                return True
                
        # Check if max wait time has passed
        time_since_last = (datetime.now(timezone.utc) - self.last_process_time).total_seconds()
        if time_since_last >= self.config.max_wait_time:
            return True
            
        # Check total queue size
        total_operations = sum(len(queue) for queue in self.operation_queues.values())
        if total_operations >= self.config.max_queue_size:
            return True
            
        return False
        
    async def _process_batches(self):
        """Process all pending batches."""
        if self.is_processing:
            return
            
        self.is_processing = True
        start_time = datetime.now(timezone.utc)
        
        try:
            processed_operations = 0
            
            # Process each queue
            for queue_key, operations in list(self.operation_queues.items()):
                if not operations:
                    continue
                    
                # Process operations in batches
                while operations:
                    batch = operations[:self.config.batch_size]
                    operations = operations[self.config.batch_size:]
                    
                    if batch:
                        await self._process_batch(batch)
                        processed_operations += len(batch)
                        
                # Update queue
                if operations:
                    self.operation_queues[queue_key] = operations
                else:
                    del self.operation_queues[queue_key]
                    
            # Update statistics
            if processed_operations > 0:
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                self.stats.batches_processed += 1
                self.stats.total_operations += processed_operations
                
                # Update statistics using monitor
                self.stats = self.monitor.update_statistics(
                    self.stats, self.operation_queues, processing_time
                )
                
            self.last_process_time = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error processing batches: {str(e)}")
        finally:
            self.is_processing = False
            
    async def _process_batch(self, batch: List[BatchOperation]):
        """Process a single batch of operations."""
        if not batch:
            return
            
        # Group by table and operation type
        grouped_operations = self.operation_handler.group_operations(batch)
            
        # Process each group
        for group_key, operations in grouped_operations.items():
            results = await self.operation_handler.process_operation_group(operations)
            
            # Complete operations with results
            for result in results:
                self._complete_operation(
                    result.operation_id,
                    result.success,
                    result.data,
                    result.error
                )
            
    # Operation group processing is now handled by BatchOperationHandler
                
    def _complete_operation(
        self,
        operation_id: str,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[str] = None
    ):
        """Complete an operation and notify waiting code."""
        if operation_id in self.pending_results:
            future = self.pending_results[operation_id]
            
            result = BatchResult(
                operation_id=operation_id,
                success=success,
                data=data,
                error=error
            )
            
            if not future.done():
                future.set_result(result)
                
            del self.pending_results[operation_id]
            
            # Update statistics
            if success:
                self.stats.successful_operations += 1
            else:
                self.stats.failed_operations += 1
                
    async def flush(self):
        """Process all pending operations immediately."""
        if self.operation_queues:
            await self._process_batches()
            
    def get_stats(self) -> BatchStatistics:
        """Get batch processing statistics."""
        # Update pending operations count
        self.stats.pending_operations = sum(len(queue) for queue in self.operation_queues.values())
        self.stats.pending_results = len(self.pending_results)
        self.stats.is_processing = self.is_processing
        
        return self.stats
        
    async def health_check(self) -> BatchHealthCheck:
        """Perform a health check on the batch processor."""
        return self.monitor.create_health_check(
            self.get_stats(),
            self.operation_queues,
            self.is_processing
        )


# Global batch processor instance
_global_batch_processor = None


def get_batch_processor() -> BatchProcessor:
    """Get the global batch processor instance."""
    global _global_batch_processor
    if _global_batch_processor is None:
        _global_batch_processor = BatchProcessor()
    return _global_batch_processor


async def batch_insert(
    table_name: str,
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    priority: int = 0
) -> Union[BatchResult, List[BatchResult]]:
    """
    Batch insert operation.
    
    Args:
        table_name: Target table name
        data: Data to insert (single dict or list of dicts)
        priority: Operation priority
        
    Returns:
        BatchResult or list of BatchResults
    """
    processor = get_batch_processor()
    
    if isinstance(data, list):
        # Multiple inserts
        futures = []
        for item in data:
            future = processor.add_operation(
                BatchOperationType.INSERT,
                table_name,
                item,
                priority=priority
            )
            futures.append(future)
            
        results = await asyncio.gather(*futures)
        return results
    else:
        # Single insert
        future = processor.add_operation(
            BatchOperationType.INSERT,
            table_name,
            data,
            priority=priority
        )
        return await future


async def batch_update(
    table_name: str,
    data: Dict[str, Any],
    filters: Dict[str, Any],
    priority: int = 0
) -> BatchResult:
    """
    Batch update operation.
    
    Args:
        table_name: Target table name
        data: Data to update
        filters: Update filters
        priority: Operation priority
        
    Returns:
        BatchResult
    """
    processor = get_batch_processor()
    future = processor.add_operation(
        BatchOperationType.UPDATE,
        table_name,
        data,
        filters=filters,
        priority=priority
    )
    return await future


async def batch_delete(
    table_name: str,
    filters: Dict[str, Any],
    priority: int = 0
) -> BatchResult:
    """
    Batch delete operation.
    
    Args:
        table_name: Target table name
        filters: Delete filters
        priority: Operation priority
        
    Returns:
        BatchResult
    """
    processor = get_batch_processor()
    future = processor.add_operation(
        BatchOperationType.DELETE,
        table_name,
        {},
        filters=filters,
        priority=priority
    )
    return await future