"""
Database utilities for Problem Generator module.

This module provides transaction handling, data validation, and consistency checks
to ensure reliable database operations without fallback mechanisms.
"""

import uuid
import logging
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from src.mint.api.system.core.supabase_client import get_supabase_client, get_service_role_client

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass


class ValidationError(Exception):
    """Custom exception for data validation errors."""
    pass


class TransactionError(Exception):
    """Custom exception for transaction errors."""
    pass


@dataclass
class DatabaseOperation:
    """Represents a database operation for transaction handling."""
    table: str
    operation: str  # 'insert', 'update', 'delete', 'select'
    data: Dict[str, Any]
    conditions: Optional[Dict[str, Any]] = None
    
    
class DatabaseValidator:
    """Validates data before database operations."""
    
    @staticmethod
    def validate_uuid(value: Any, field_name: str) -> str:
        """Validate UUID field."""
        if not value:
            raise ValidationError(f"{field_name} is required")
            
        try:
            if isinstance(value, str):
                uuid_obj = uuid.UUID(value)
                return str(uuid_obj)
            elif isinstance(value, uuid.UUID):
                return str(value)
            else:
                raise ValidationError(f"{field_name} must be a valid UUID string or UUID object")
        except ValueError:
            raise ValidationError(f"{field_name} must be a valid UUID format")
    
    @staticmethod
    def validate_required_string(value: Any, field_name: str, max_length: Optional[int] = None) -> str:
        """Validate required string field."""
        if not value:
            raise ValidationError(f"{field_name} is required")
            
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
            
        value = value.strip()
        if not value:
            raise ValidationError(f"{field_name} cannot be empty")
            
        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters")
            
        return value
    
    @staticmethod
    def validate_enum_value(value: Any, field_name: str, valid_values: List[str]) -> str:
        """Validate enum field."""
        if not value:
            raise ValidationError(f"{field_name} is required")
            
        if value not in valid_values:
            raise ValidationError(f"{field_name} must be one of: {', '.join(valid_values)}")
            
        return value
    
    @staticmethod
    def validate_json_data(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate JSON data structure."""
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
            
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Required field '{field}' is missing")
                
        return data


class DatabaseTransactionManager:
    """Manages database transactions and ensures data consistency."""
    
    def __init__(self, use_service_role: bool = True):
        self.client = get_service_role_client() if use_service_role else get_supabase_client(use_service_role=False)
        self.operations: List[DatabaseOperation] = []
    
    def add_operation(self, operation: DatabaseOperation) -> None:
        """Add an operation to the transaction."""
        self.operations.append(operation)
    
    def execute_transaction(self) -> List[Any]:
        """
        Execute all operations as a transaction.
        Note: Supabase doesn't support true transactions via the client,
        so we implement atomic operations with rollback capability.
        """
        results = []
        executed_operations = []
        
        try:
            for operation in self.operations:
                result = self._execute_single_operation(operation)
                results.append(result)
                executed_operations.append((operation, result))
                
            logger.info(f"Successfully executed {len(self.operations)} database operations")
            return results
            
        except Exception as e:
            logger.error(f"Transaction failed, attempting rollback: {str(e)}")
            self._rollback_operations(executed_operations)
            raise TransactionError(f"Transaction failed: {str(e)}")
    
    def _execute_single_operation(self, operation: DatabaseOperation) -> Any:
        """Execute a single database operation."""
        try:
            if operation.operation == 'insert':
                result = self.client.client.table(operation.table).insert(operation.data).execute()
                
            elif operation.operation == 'update':
                query = self.client.client.table(operation.table).update(operation.data)
                if operation.conditions:
                    for key, value in operation.conditions.items():
                        query = query.eq(key, value)
                result = query.execute()
                
            elif operation.operation == 'delete':
                query = self.client.client.table(operation.table)
                if operation.conditions:
                    for key, value in operation.conditions.items():
                        query = query.eq(key, value)
                result = query.delete().execute()
                
            elif operation.operation == 'select':
                query = self.client.client.table(operation.table).select(operation.data.get('select', '*'))
                if operation.conditions:
                    for key, value in operation.conditions.items():
                        query = query.eq(key, value)
                result = query.execute()
                
            else:
                raise DatabaseError(f"Unsupported operation: {operation.operation}")
            
            if not result.data and operation.operation in ['insert', 'update']:
                raise DatabaseError(f"Operation {operation.operation} on {operation.table} returned no data")
                
            return result.data
            
        except Exception as e:
            logger.error(f"Database operation failed: {operation.operation} on {operation.table}: {str(e)}")
            raise DatabaseError(f"Failed to {operation.operation} in {operation.table}: {str(e)}")
    
    def _rollback_operations(self, executed_operations: List[tuple]) -> None:
        """Attempt to rollback executed operations."""
        logger.warning("Attempting to rollback database operations")
        
        # Reverse the order for rollback
        for operation, result in reversed(executed_operations):
            try:
                if operation.operation == 'insert' and result:
                    # Delete the inserted record
                    for record in result:
                        if 'id' in record:
                            self.client.client.table(operation.table).delete().eq('id', record['id']).execute()
                            
                elif operation.operation == 'update':
                    # This is complex - we'd need to store original values
                    logger.warning(f"Cannot rollback update operation on {operation.table}")
                    
                elif operation.operation == 'delete':
                    # Cannot rollback delete without backup
                    logger.warning(f"Cannot rollback delete operation on {operation.table}")
                    
            except Exception as rollback_error:
                logger.error(f"Rollback failed for {operation.table}: {str(rollback_error)}")


def execute_with_retry(operation: Callable[[], T], max_retries: int = 3, 
                      retry_delay: float = 1.0) -> T:
    """
    Execute a database operation with retry logic.
    
    Args:
        operation: Function to execute
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Result of the operation
        
    Raises:
        DatabaseError: If all retries fail
    """
    import time
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                logger.error(f"Database operation failed after {max_retries + 1} attempts: {str(e)}")
    
    raise DatabaseError(f"Operation failed after {max_retries + 1} attempts: {str(last_error)}")


def validate_database_connection() -> bool:
    """
    Validate database connection is working.
    
    Returns:
        bool: True if connection is working
        
    Raises:
        DatabaseError: If connection fails
    """
    try:
        client = get_supabase_client(use_service_role=True)
        # Simple query to test connection
        result = client.client.table("tenants").select("id").limit(1).execute()
        logger.debug("Database connection validated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database connection validation failed: {str(e)}")
        raise DatabaseError(f"Database connection failed: {str(e)}")


def ensure_data_consistency(table: str, record_id: str, expected_fields: Dict[str, Any]) -> bool:
    """
    Verify data consistency by checking if a record has expected values.
    
    Args:
        table: Table name
        record_id: Record ID to check
        expected_fields: Dictionary of field names and expected values
        
    Returns:
        bool: True if data is consistent
        
    Raises:
        DatabaseError: If consistency check fails
    """
    try:
        client = get_supabase_client(use_service_role=True)
        result = client.client.table(table).select("*").eq("id", record_id).execute()
        
        if not result.data:
            raise DatabaseError(f"Record {record_id} not found in {table}")
            
        record = result.data[0]
        
        for field, expected_value in expected_fields.items():
            if field not in record:
                logger.error(f"Field {field} missing from record {record_id}")
                return False
                
            if record[field] != expected_value:
                logger.error(f"Field {field} has value {record[field]}, expected {expected_value}")
                return False
        
        logger.debug(f"Data consistency verified for record {record_id} in {table}")
        return True
        
    except Exception as e:
        logger.error(f"Data consistency check failed: {str(e)}")
        raise DatabaseError(f"Consistency check failed: {str(e)}")


@contextmanager
def database_transaction(use_service_role: bool = True):
    """
    Context manager for database transactions.
    
    Usage:
        with database_transaction() as tx:
            tx.add_operation(DatabaseOperation(...))
            tx.add_operation(DatabaseOperation(...))
            # Operations are executed when exiting the context
    """
    tx_manager = DatabaseTransactionManager(use_service_role)
    try:
        yield tx_manager
        # Execute all operations when exiting successfully
        tx_manager.execute_transaction()
        
    except Exception as e:
        logger.error(f"Transaction context failed: {str(e)}")
        raise
