#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ID Logging Service for MINT.

This module provides comprehensive logging for ID operations throughout
the MINT system to help debug ID consistency issues.
"""

import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from contextlib import contextmanager
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

# Create a dedicated logger for ID operations
id_logger = logging.getLogger("mint.id_operations")
id_logger.setLevel(logging.INFO)

# Create a formatter for ID operations
id_formatter = logging.Formatter(
    '%(asctime)s - ID_OPS - %(levelname)s - %(message)s'
)

# Add a handler if one doesn't exist
if not id_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(id_formatter)
    id_logger.addHandler(handler)
    id_logger.propagate = False


class IDOperationTracker:
    """Context manager for tracking ID operations through the system."""
    
    def __init__(self, operation: str, **initial_ids):
        """Initialize the ID operation tracker.
        
        Args:
            operation: Name of the operation being tracked
            **initial_ids: Initial ID values to track
        """
        self.operation = operation
        self.operation_id = str(uuid.uuid4())[:8]  # Short ID for this operation
        self.start_time = time.time()
        self.ids = initial_ids.copy()
        self.stages = []
        
    def __enter__(self):
        """Start tracking the operation."""
        id_logger.info(f"[{self.operation_id}] STARTING {self.operation}")
        self._log_current_ids("INITIAL")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking the operation."""
        duration = time.time() - self.start_time
        if exc_type:
            id_logger.error(f"[{self.operation_id}] FAILED {self.operation} after {duration:.2f}s: {exc_val}")
        else:
            id_logger.info(f"[{self.operation_id}] COMPLETED {self.operation} in {duration:.2f}s")
        self._log_current_ids("FINAL")
        
    def update_ids(self, stage: str, **new_ids):
        """Update tracked IDs at a specific stage.
        
        Args:
            stage: Name of the current stage
            **new_ids: New or updated ID values
        """
        self.ids.update(new_ids)
        self.stages.append(stage)
        self._log_current_ids(stage)
        
    def validate_id(self, id_name: str, id_value: Union[str, None], required: bool = True) -> bool:
        """Validate an ID and log the result.
        
        Args:
            id_name: Name of the ID being validated
            id_value: The ID value to validate
            required: Whether the ID is required
            
        Returns:
            bool: True if valid, False otherwise
        """
        if id_value is None:
            if required:
                id_logger.error(f"[{self.operation_id}] VALIDATION FAILED: {id_name} is required but None")
                return False
            else:
                id_logger.info(f"[{self.operation_id}] VALIDATION OK: {id_name} is None (optional)")
                return True
        
        try:
            uuid.UUID(str(id_value))
            id_logger.info(f"[{self.operation_id}] VALIDATION OK: {id_name}={id_value} is valid UUID")
            return True
        except (ValueError, TypeError):
            id_logger.error(f"[{self.operation_id}] VALIDATION FAILED: {id_name}={id_value} is NOT a valid UUID")
            return False
            
    def log_database_query(self, table: str, operation: str, filters: Dict[str, Any], result_count: Optional[int] = None):
        """Log a database query with ID information.
        
        Args:
            table: Database table being queried
            operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
            filters: Filter conditions used in the query
            result_count: Number of results returned (if known)
        """
        filter_str = ", ".join([f"{k}={v}" for k, v in filters.items()])
        result_info = f", returned {result_count} rows" if result_count is not None else ""
        id_logger.info(f"[{self.operation_id}] DB_QUERY: {operation} {table} WHERE {filter_str}{result_info}")
        
    def log_id_transformation(self, from_id: str, to_id: str, transformation: str):
        """Log an ID transformation.
        
        Args:
            from_id: Original ID
            to_id: Transformed ID
            transformation: Description of the transformation
        """
        id_logger.info(f"[{self.operation_id}] ID_TRANSFORM: {transformation} - {from_id} -> {to_id}")
        
    def log_error(self, error_type: str, message: str, **context):
        """Log an error with ID context.
        
        Args:
            error_type: Type of error
            message: Error message
            **context: Additional context information
        """
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
        id_logger.error(f"[{self.operation_id}] ERROR [{error_type}]: {message} | Context: {context_str}")
        
    def _log_current_ids(self, stage: str):
        """Log the current state of all tracked IDs.
        
        Args:
            stage: Current stage name
        """
        if not self.ids:
            id_logger.info(f"[{self.operation_id}] {stage}: No IDs tracked")
            return
            
        id_info = []
        for id_name, id_value in self.ids.items():
            id_type = type(id_value).__name__
            id_info.append(f"{id_name}={id_value} ({id_type})")
        
        id_logger.info(f"[{self.operation_id}] {stage}: {', '.join(id_info)}")


def track_id_operation(operation_name: str):
    """Decorator to automatically track ID operations in functions.
    
    Args:
        operation_name: Name of the operation being tracked
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract common ID parameters from function arguments
            initial_ids = {}
            for key, value in kwargs.items():
                if 'id' in key.lower() and value is not None:
                    initial_ids[key] = value
            
            with IDOperationTracker(f"{operation_name}:{func.__name__}", **initial_ids) as tracker:
                try:
                    result = await func(*args, **kwargs)
                    
                    # Try to extract IDs from the result if it's a dict
                    if isinstance(result, dict):
                        for key, value in result.items():
                            if 'id' in key.lower() and value is not None:
                                tracker.update_ids("RESULT", **{key: value})
                    
                    return result
                except Exception as e:
                    tracker.log_error("FUNCTION_ERROR", str(e))
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract common ID parameters from function arguments
            initial_ids = {}
            for key, value in kwargs.items():
                if 'id' in key.lower() and value is not None:
                    initial_ids[key] = value
            
            with IDOperationTracker(f"{operation_name}:{func.__name__}", **initial_ids) as tracker:
                try:
                    result = func(*args, **kwargs)
                    
                    # Try to extract IDs from the result if it's a dict
                    if isinstance(result, dict):
                        for key, value in result.items():
                            if 'id' in key.lower() and value is not None:
                                tracker.update_ids("RESULT", **{key: value})
                    
                    return result
                except Exception as e:
                    tracker.log_error("FUNCTION_ERROR", str(e))
                    raise
        
        # Return the appropriate wrapper based on whether the function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_report_generation_pipeline(stage: str, report_id: str, user_id: Optional[str] = None, 
                                 session_id: Optional[str] = None, **additional_info):
    """Log report generation pipeline stages with ID tracking.
    
    Args:
        stage: Current stage in the pipeline
        report_id: Report ID being processed
        user_id: User ID associated with the report
        session_id: Session ID associated with the report
        **additional_info: Additional information to log
    """
    info_parts = [f"report_id={report_id}"]
    
    if user_id:
        info_parts.append(f"user_id={user_id}")
    if session_id:
        info_parts.append(f"session_id={session_id}")
    
    for key, value in additional_info.items():
        info_parts.append(f"{key}={value}")
    
    id_logger.info(f"REPORT_PIPELINE [{stage}]: {', '.join(info_parts)}")


def log_vector_search_operation(operation: str, report_id: str, query: Optional[str] = None,
                               chunk_count: Optional[int] = None, **additional_info):
    """Log vector search operations with ID tracking.
    
    Args:
        operation: Type of vector search operation
        report_id: Report ID being searched
        query: Search query (truncated for logging)
        chunk_count: Number of chunks found
        **additional_info: Additional information to log
    """
    info_parts = [f"report_id={report_id}"]
    
    if query:
        # Truncate query for logging
        query_preview = query[:50] + "..." if len(query) > 50 else query
        info_parts.append(f"query='{query_preview}'")
    
    if chunk_count is not None:
        info_parts.append(f"chunks_found={chunk_count}")
    
    for key, value in additional_info.items():
        info_parts.append(f"{key}={value}")
    
    id_logger.info(f"VECTOR_SEARCH [{operation}]: {', '.join(info_parts)}")


def log_chat_operation(operation: str, report_id: str, user_id: str, message_id: Optional[str] = None,
                      **additional_info):
    """Log chat operations with ID tracking.
    
    Args:
        operation: Type of chat operation
        report_id: Report ID being chatted with
        user_id: User ID performing the chat
        message_id: Message ID (if applicable)
        **additional_info: Additional information to log
    """
    info_parts = [f"report_id={report_id}", f"user_id={user_id}"]
    
    if message_id:
        info_parts.append(f"message_id={message_id}")
    
    for key, value in additional_info.items():
        info_parts.append(f"{key}={value}")
    
    id_logger.info(f"CHAT_OPS [{operation}]: {', '.join(info_parts)}")


def log_chunking_operation(operation: str, report_id: str, chunk_count: Optional[int] = None,
                          embedding_count: Optional[int] = None, **additional_info):
    """Log chunking and embedding operations with ID tracking.
    
    Args:
        operation: Type of chunking operation
        report_id: Report ID being processed
        chunk_count: Number of chunks created
        embedding_count: Number of embeddings generated
        **additional_info: Additional information to log
    """
    info_parts = [f"report_id={report_id}"]
    
    if chunk_count is not None:
        info_parts.append(f"chunks={chunk_count}")
    
    if embedding_count is not None:
        info_parts.append(f"embeddings={embedding_count}")
    
    for key, value in additional_info.items():
        info_parts.append(f"{key}={value}")
    
    id_logger.info(f"CHUNKING [{operation}]: {', '.join(info_parts)}")


def log_database_operation(operation: str, table: str, record_id: Optional[str] = None,
                          filters: Optional[Dict[str, Any]] = None, result_count: Optional[int] = None,
                          **additional_info):
    """Log database operations with ID tracking.
    
    Args:
        operation: Type of database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Database table being operated on
        record_id: Primary key of the record (if applicable)
        filters: Filter conditions used
        result_count: Number of records affected/returned
        **additional_info: Additional information to log
    """
    info_parts = [f"table={table}"]
    
    if record_id:
        info_parts.append(f"record_id={record_id}")
    
    if filters:
        filter_str = ", ".join([f"{k}={v}" for k, v in filters.items()])
        info_parts.append(f"filters=({filter_str})")
    
    if result_count is not None:
        info_parts.append(f"affected_rows={result_count}")
    
    for key, value in additional_info.items():
        info_parts.append(f"{key}={value}")
    
    id_logger.info(f"DB_OPS [{operation}]: {', '.join(info_parts)}")


def log_id_validation_result(id_name: str, id_value: Union[str, None], is_valid: bool, 
                           operation: str, **additional_context):
    """Log ID validation results.
    
    Args:
        id_name: Name of the ID being validated
        id_value: The ID value
        is_valid: Whether the ID is valid
        operation: Operation context
        **additional_context: Additional context information
    """
    status = "VALID" if is_valid else "INVALID"
    context_str = ", ".join([f"{k}={v}" for k, v in additional_context.items()])
    context_part = f" | Context: {context_str}" if context_str else ""
    
    log_level = id_logger.info if is_valid else id_logger.error
    log_level(f"ID_VALIDATION [{operation}]: {id_name}={id_value} is {status}{context_part}")


def log_report_not_found_scenario(report_identifier: str, search_method: str, user_id: Optional[str] = None):
    """Log scenarios where reports are not found to help debug ID mismatches.
    
    Args:
        report_identifier: The identifier used to search for the report
        search_method: How the report was searched (by_id, by_session_id, etc.)
        user_id: User ID context (if available)
    """
    user_context = f", user_id={user_id}" if user_id else ""
    id_logger.warning(f"REPORT_NOT_FOUND: identifier={report_identifier}, method={search_method}{user_context}")


def log_chunk_not_found_scenario(report_id: str, user_id: Optional[str] = None, 
                                chunk_table_count: Optional[int] = None):
    """Log scenarios where report chunks are not found.
    
    Args:
        report_id: Report ID that was searched
        user_id: User ID context (if available)
        chunk_table_count: Number of chunks found in the table (if checked)
    """
    user_context = f", user_id={user_id}" if user_id else ""
    chunk_context = f", chunks_in_table={chunk_table_count}" if chunk_table_count is not None else ""
    id_logger.warning(f"CHUNKS_NOT_FOUND: report_id={report_id}{user_context}{chunk_context}")


# Singleton instance for global use
_global_tracker = None

def get_global_tracker() -> Optional[IDOperationTracker]:
    """Get the current global ID operation tracker."""
    return _global_tracker

def set_global_tracker(tracker: IDOperationTracker):
    """Set the global ID operation tracker."""
    global _global_tracker
    _global_tracker = tracker

@contextmanager
def global_id_tracking(operation: str, **initial_ids):
    """Context manager for global ID tracking across multiple functions."""
    tracker = IDOperationTracker(operation, **initial_ids)
    set_global_tracker(tracker)
    try:
        with tracker:
            yield tracker
    finally:
        set_global_tracker(None)