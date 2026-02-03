#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Operation Handlers.

This module provides handlers for different types of batch operations,
including insert, update, delete, and upsert operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..supabase_client import SupabaseClient
from .models import (
    BatchOperation, BatchOperationType, BatchResult, BatchError,
    BATCH_ERROR_CODES
)

# Configure logging
logger = logging.getLogger(__name__)


class BatchOperationHandler:
    """Handler for batch operations."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize the batch operation handler.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client
    
    async def process_operation_group(self, operations: List[BatchOperation]) -> List[BatchResult]:
        """
        Process a group of similar operations.
        
        Args:
            operations: List of batch operations to process
            
        Returns:
            List of batch results
        """
        if not operations:
            return []
        
        operation_type = operations[0].operation_type
        table_name = operations[0].table_name
        
        try:
            if operation_type == BatchOperationType.INSERT:
                return await self._process_insert_batch(table_name, operations)
            elif operation_type == BatchOperationType.UPDATE:
                return await self._process_update_batch(table_name, operations)
            elif operation_type == BatchOperationType.DELETE:
                return await self._process_delete_batch(table_name, operations)
            elif operation_type == BatchOperationType.UPSERT:
                return await self._process_upsert_batch(table_name, operations)
            else:
                raise ValueError(f"Unknown operation type: {operation_type}")
                
        except Exception as e:
            logger.error(f"Error processing {operation_type.value} batch for {table_name}: {str(e)}")
            # Return failed results for all operations
            return [
                BatchResult(
                    operation_id=op.operation_id,
                    success=False,
                    error=str(e),
                    retry_count=op.retry_count
                )
                for op in operations
            ]
    
    async def _process_insert_batch(self, table_name: str, operations: List[BatchOperation]) -> List[BatchResult]:
        """
        Process a batch of insert operations.
        
        Args:
            table_name: Target table name
            operations: List of insert operations
            
        Returns:
            List of batch results
        """
        data_list = [op.data for op in operations]
        
        try:
            response = self.client.client.table(table_name).insert(data_list).execute()
            
            # Create results for all operations
            results = []
            for i, operation in enumerate(operations):
                result_data = response.data[i] if i < len(response.data) else None
                results.append(BatchResult(
                    operation_id=operation.operation_id,
                    success=True,
                    data=result_data,
                    retry_count=operation.retry_count,
                    completed_at=datetime.now(timezone.utc)
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing insert batch for {table_name}: {str(e)}")
            # Return failed results for all operations
            return [
                BatchResult(
                    operation_id=op.operation_id,
                    success=False,
                    error=str(e),
                    retry_count=op.retry_count,
                    completed_at=datetime.now(timezone.utc)
                )
                for op in operations
            ]
    
    async def _process_update_batch(self, table_name: str, operations: List[BatchOperation]) -> List[BatchResult]:
        """
        Process a batch of update operations.
        
        Args:
            table_name: Target table name
            operations: List of update operations
            
        Returns:
            List of batch results
        """
        results = []
        
        # Updates are processed individually since they typically have different filters
        for operation in operations:
            try:
                query = self.client.client.table(table_name).update(operation.data)
                
                # Apply filters
                if operation.filters:
                    for key, value in operation.filters.items():
                        query = query.eq(key, value)
                
                response = query.execute()
                results.append(BatchResult(
                    operation_id=operation.operation_id,
                    success=True,
                    data=response.data,
                    retry_count=operation.retry_count,
                    completed_at=datetime.now(timezone.utc)
                ))
                
            except Exception as e:
                logger.error(f"Error processing update operation {operation.operation_id}: {str(e)}")
                results.append(BatchResult(
                    operation_id=operation.operation_id,
                    success=False,
                    error=str(e),
                    retry_count=operation.retry_count,
                    completed_at=datetime.now(timezone.utc)
                ))
        
        return results
    
    async def _process_delete_batch(self, table_name: str, operations: List[BatchOperation]) -> List[BatchResult]:
        """
        Process a batch of delete operations.
        
        Args:
            table_name: Target table name
            operations: List of delete operations
            
        Returns:
            List of batch results
        """
        results = []
        
        # Deletes are processed individually since they typically have different filters
        for operation in operations:
            try:
                query = self.client.client.table(table_name).delete()
                
                # Apply filters
                if operation.filters:
                    for key, value in operation.filters.items():
                        query = query.eq(key, value)
                
                response = query.execute()
                results.append(BatchResult(
                    operation_id=operation.operation_id,
                    success=True,
                    data=response.data,
                    retry_count=operation.retry_count,
                    completed_at=datetime.now(timezone.utc)
                ))
                
            except Exception as e:
                logger.error(f"Error processing delete operation {operation.operation_id}: {str(e)}")
                results.append(BatchResult(
                    operation_id=operation.operation_id,
                    success=False,
                    error=str(e),
                    retry_count=operation.retry_count,
                    completed_at=datetime.now(timezone.utc)
                ))
        
        return results
    
    async def _process_upsert_batch(self, table_name: str, operations: List[BatchOperation]) -> List[BatchResult]:
        """
        Process a batch of upsert operations.
        
        Args:
            table_name: Target table name
            operations: List of upsert operations
            
        Returns:
            List of batch results
        """
        data_list = [op.data for op in operations]
        
        try:
            response = self.client.client.table(table_name).upsert(data_list).execute()
            
            # Create results for all operations
            results = []
            for i, operation in enumerate(operations):
                result_data = response.data[i] if i < len(response.data) else None
                results.append(BatchResult(
                    operation_id=operation.operation_id,
                    success=True,
                    data=result_data,
                    retry_count=operation.retry_count,
                    completed_at=datetime.now(timezone.utc)
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing upsert batch for {table_name}: {str(e)}")
            # Return failed results for all operations
            return [
                BatchResult(
                    operation_id=op.operation_id,
                    success=False,
                    error=str(e),
                    retry_count=op.retry_count,
                    completed_at=datetime.now(timezone.utc)
                )
                for op in operations
            ]
    
    async def validate_operation(self, operation: BatchOperation) -> List[str]:
        """
        Validate a batch operation.
        
        Args:
            operation: Batch operation to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate operation type
        if not operation.operation_type:
            errors.append("Operation type is required")
        
        # Validate table name
        if not operation.table_name:
            errors.append("Table name is required")
        
        # Validate data
        if not operation.data:
            errors.append("Operation data is required")
        
        # Validate filters for update/delete operations
        if operation.operation_type in [BatchOperationType.UPDATE, BatchOperationType.DELETE]:
            if not operation.filters:
                errors.append("Filters are required for update/delete operations")
        
        # Validate data structure
        if operation.data and not isinstance(operation.data, dict):
            errors.append("Operation data must be a dictionary")
        
        # Validate filters structure
        if operation.filters and not isinstance(operation.filters, dict):
            errors.append("Operation filters must be a dictionary")
        
        return errors
    
    def group_operations(self, operations: List[BatchOperation]) -> Dict[str, List[BatchOperation]]:
        """
        Group operations by table and operation type.
        
        Args:
            operations: List of operations to group
            
        Returns:
            Dictionary of grouped operations
        """
        grouped = {}
        
        for operation in operations:
            key = f"{operation.table_name}_{operation.operation_type.value}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(operation)
        
        return grouped
    
    def sort_operations_by_priority(self, operations: List[BatchOperation]) -> List[BatchOperation]:
        """
        Sort operations by priority (highest first).
        
        Args:
            operations: List of operations to sort
            
        Returns:
            Sorted list of operations
        """
        return sorted(operations, key=lambda x: x.priority, reverse=True)
    
    def filter_operations(
        self,
        operations: List[BatchOperation],
        table_name: Optional[str] = None,
        operation_type: Optional[BatchOperationType] = None,
        priority_min: Optional[int] = None,
        priority_max: Optional[int] = None
    ) -> List[BatchOperation]:
        """
        Filter operations based on criteria.
        
        Args:
            operations: List of operations to filter
            table_name: Filter by table name
            operation_type: Filter by operation type
            priority_min: Minimum priority
            priority_max: Maximum priority
            
        Returns:
            Filtered list of operations
        """
        filtered = operations
        
        if table_name:
            filtered = [op for op in filtered if op.table_name == table_name]
        
        if operation_type:
            filtered = [op for op in filtered if op.operation_type == operation_type]
        
        if priority_min is not None:
            filtered = [op for op in filtered if op.priority >= priority_min]
        
        if priority_max is not None:
            filtered = [op for op in filtered if op.priority <= priority_max]
        
        return filtered
    
    def calculate_batch_metrics(self, operations: List[BatchOperation]) -> Dict[str, Any]:
        """
        Calculate metrics for a batch of operations.
        
        Args:
            operations: List of operations
            
        Returns:
            Dictionary of metrics
        """
        if not operations:
            return {
                "total_operations": 0,
                "operations_by_type": {},
                "operations_by_table": {},
                "avg_priority": 0.0,
                "priority_distribution": {}
            }
        
        # Count operations by type
        operations_by_type = {}
        for op in operations:
            op_type = op.operation_type.value
            operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1
        
        # Count operations by table
        operations_by_table = {}
        for op in operations:
            table = op.table_name
            operations_by_table[table] = operations_by_table.get(table, 0) + 1
        
        # Calculate average priority
        total_priority = sum(op.priority for op in operations)
        avg_priority = total_priority / len(operations) if operations else 0.0
        
        # Priority distribution
        priority_distribution = {}
        for op in operations:
            priority = op.priority
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        return {
            "total_operations": len(operations),
            "operations_by_type": operations_by_type,
            "operations_by_table": operations_by_table,
            "avg_priority": avg_priority,
            "priority_distribution": priority_distribution
        }


