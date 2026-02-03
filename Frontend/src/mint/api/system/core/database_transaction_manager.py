"""
Database Transaction Manager

This service provides transaction management and rollback mechanisms
for database operations, ensuring data consistency and proper error handling.

Requirements addressed:
- 5.2: Proper rollback mechanisms for failed database operations
- 5.3: Graceful error handling for database operations
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from .supabase_client import SupabaseClient, get_service_role_client
from ...report.report_error_handler import get_report_error_handler, ReportError, ReportErrorType

logger = logging.getLogger(__name__)


@dataclass
class TransactionState:
    """State information for a database transaction."""
    
    transaction_id: str
    started_at: datetime
    operations: List[Dict[str, Any]]
    rollback_data: List[Dict[str, Any]]
    is_committed: bool = False
    is_rolled_back: bool = False
    
    def __post_init__(self):
        if not hasattr(self, 'operations') or self.operations is None:
            self.operations = []
        if not hasattr(self, 'rollback_data') or self.rollback_data is None:
            self.rollback_data = []


class DatabaseTransactionManager:
    """
    Manager for database transactions with rollback capabilities.
    
    This service provides transaction management for report operations,
    ensuring data consistency and proper rollback mechanisms for failed
    database operations.
    """
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the transaction manager.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_service_role_client()
        self.error_handler = get_report_error_handler()
        self._active_transactions: Dict[str, TransactionState] = {}
    
    @asynccontextmanager
    async def transaction(
        self,
        transaction_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Context manager for database transactions with automatic rollback.
        
        Args:
            transaction_id: Optional transaction ID, generates one if not provided
            
        Yields:
            Transaction ID for tracking operations
            
        Example:
            async with transaction_manager.transaction() as tx_id:
                await transaction_manager.update_report(tx_id, report_id, data)
                await transaction_manager.insert_backup(tx_id, backup_data)
                # Automatically commits on success, rolls back on exception
        """
        if transaction_id is None:
            transaction_id = str(uuid4())
        
        # Initialize transaction state
        transaction_state = TransactionState(
            transaction_id=transaction_id,
            started_at=datetime.utcnow(),
            operations=[],
            rollback_data=[]
        )
        
        self._active_transactions[transaction_id] = transaction_state
        
        try:
            logger.info(f"Starting transaction {transaction_id}")
            yield transaction_id
            
            # Commit transaction if no exceptions occurred
            await self._commit_transaction(transaction_id)
            logger.info(f"Transaction {transaction_id} committed successfully")
            
        except Exception as e:
            logger.error(f"Transaction {transaction_id} failed: {str(e)}")
            
            # Attempt rollback
            rollback_success = await self._rollback_transaction(transaction_id)
            if rollback_success:
                logger.info(f"Transaction {transaction_id} rolled back successfully")
            else:
                logger.error(f"Rollback failed for transaction {transaction_id}")
            
            # Re-raise the original exception
            raise
            
        finally:
            # Clean up transaction state
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]
    
    async def update_report(
        self,
        transaction_id: str,
        report_id: str,
        update_data: Dict[str, Any],
        table_name: str = "mint_reports"
    ) -> bool:
        """
        Update a report within a transaction.
        
        Args:
            transaction_id: Transaction ID
            report_id: ID of the report to update
            update_data: Data to update
            table_name: Name of the table to update
            
        Returns:
            True if successful, False otherwise
        """
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction_state = self._active_transactions[transaction_id]
        
        try:
            # First, fetch current data for rollback
            current_response = self.client.client.table(table_name) \
                .select("*") \
                .eq("id", report_id) \
                .single() \
                .execute()
            
            if not current_response.data:
                logger.error(f"Report {report_id} not found for update")
                return False
            
            current_data = current_response.data
            
            # Store rollback data
            rollback_info = {
                "operation": "update",
                "table": table_name,
                "record_id": report_id,
                "original_data": current_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            transaction_state.rollback_data.append(rollback_info)
            
            # Perform the update
            update_response = self.client.client.table(table_name) \
                .update(update_data) \
                .eq("id", report_id) \
                .execute()
            
            if update_response.data:
                # Record the operation
                operation_info = {
                    "operation": "update",
                    "table": table_name,
                    "record_id": report_id,
                    "data": update_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
                transaction_state.operations.append(operation_info)
                
                logger.debug(f"Updated report {report_id} in transaction {transaction_id}")
                return True
            else:
                logger.error(f"Failed to update report {report_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating report {report_id} in transaction {transaction_id}: {str(e)}")
            return False
    
    async def insert_record(
        self,
        transaction_id: str,
        table_name: str,
        insert_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Insert a record within a transaction.
        
        Args:
            transaction_id: Transaction ID
            table_name: Name of the table to insert into
            insert_data: Data to insert
            
        Returns:
            ID of inserted record if successful, None otherwise
        """
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return None
        
        transaction_state = self._active_transactions[transaction_id]
        
        try:
            # Perform the insert
            insert_response = self.client.client.table(table_name) \
                .insert(insert_data) \
                .execute()
            
            if insert_response.data:
                inserted_record = insert_response.data[0]
                record_id = inserted_record.get("id")
                
                # Store rollback data
                rollback_info = {
                    "operation": "insert",
                    "table": table_name,
                    "record_id": record_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                transaction_state.rollback_data.append(rollback_info)
                
                # Record the operation
                operation_info = {
                    "operation": "insert",
                    "table": table_name,
                    "record_id": record_id,
                    "data": insert_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
                transaction_state.operations.append(operation_info)
                
                logger.debug(f"Inserted record {record_id} in transaction {transaction_id}")
                return record_id
            else:
                logger.error(f"Failed to insert record in table {table_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error inserting record in transaction {transaction_id}: {str(e)}")
            return None
    
    async def delete_record(
        self,
        transaction_id: str,
        table_name: str,
        record_id: str
    ) -> bool:
        """
        Delete a record within a transaction.
        
        Args:
            transaction_id: Transaction ID
            table_name: Name of the table to delete from
            record_id: ID of the record to delete
            
        Returns:
            True if successful, False otherwise
        """
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction_state = self._active_transactions[transaction_id]
        
        try:
            # First, fetch current data for rollback
            current_response = self.client.client.table(table_name) \
                .select("*") \
                .eq("id", record_id) \
                .single() \
                .execute()
            
            if not current_response.data:
                logger.error(f"Record {record_id} not found for deletion")
                return False
            
            current_data = current_response.data
            
            # Store rollback data
            rollback_info = {
                "operation": "delete",
                "table": table_name,
                "record_id": record_id,
                "original_data": current_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            transaction_state.rollback_data.append(rollback_info)
            
            # Perform the deletion
            delete_response = self.client.client.table(table_name) \
                .delete() \
                .eq("id", record_id) \
                .execute()
            
            # Record the operation
            operation_info = {
                "operation": "delete",
                "table": table_name,
                "record_id": record_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            transaction_state.operations.append(operation_info)
            
            logger.debug(f"Deleted record {record_id} in transaction {transaction_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error deleting record {record_id} in transaction {transaction_id}: {str(e)}")
            return False
    
    async def _commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a transaction (mark as committed).
        
        Note: Since Supabase doesn't support traditional transactions,
        this mainly serves as a marker for successful completion.
        
        Args:
            transaction_id: Transaction ID to commit
            
        Returns:
            True if successful
        """
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found for commit")
            return False
        
        transaction_state = self._active_transactions[transaction_id]
        transaction_state.is_committed = True
        
        logger.info(f"Transaction {transaction_id} marked as committed with {len(transaction_state.operations)} operations")
        return True
    
    async def _rollback_transaction(self, transaction_id: str) -> bool:
        """
        Rollback a transaction by reversing all operations.
        
        Args:
            transaction_id: Transaction ID to rollback
            
        Returns:
            True if rollback was successful
        """
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found for rollback")
            return False
        
        transaction_state = self._active_transactions[transaction_id]
        
        if transaction_state.is_committed:
            logger.warning(f"Attempting to rollback committed transaction {transaction_id}")
            return False
        
        if transaction_state.is_rolled_back:
            logger.warning(f"Transaction {transaction_id} already rolled back")
            return True
        
        rollback_success = True
        
        # Reverse operations in reverse order
        for rollback_info in reversed(transaction_state.rollback_data):
            try:
                operation = rollback_info["operation"]
                table = rollback_info["table"]
                record_id = rollback_info["record_id"]
                
                if operation == "update":
                    # Restore original data
                    original_data = rollback_info["original_data"]
                    restore_response = self.client.client.table(table) \
                        .update(original_data) \
                        .eq("id", record_id) \
                        .execute()
                    
                    if not restore_response.data:
                        logger.error(f"Failed to restore record {record_id} during rollback")
                        rollback_success = False
                    else:
                        logger.debug(f"Restored record {record_id} during rollback")
                
                elif operation == "insert":
                    # Delete the inserted record
                    delete_response = self.client.client.table(table) \
                        .delete() \
                        .eq("id", record_id) \
                        .execute()
                    
                    logger.debug(f"Deleted inserted record {record_id} during rollback")
                
                elif operation == "delete":
                    # Restore the deleted record
                    original_data = rollback_info["original_data"]
                    restore_response = self.client.client.table(table) \
                        .insert(original_data) \
                        .execute()
                    
                    if not restore_response.data:
                        logger.error(f"Failed to restore deleted record {record_id} during rollback")
                        rollback_success = False
                    else:
                        logger.debug(f"Restored deleted record {record_id} during rollback")
                
            except Exception as e:
                logger.error(f"Error during rollback operation: {str(e)}")
                rollback_success = False
        
        transaction_state.is_rolled_back = True
        
        if rollback_success:
            logger.info(f"Transaction {transaction_id} rolled back successfully")
        else:
            logger.error(f"Transaction {transaction_id} rollback completed with errors")
        
        return rollback_success
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a transaction.
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            Transaction status information or None if not found
        """
        if transaction_id not in self._active_transactions:
            return None
        
        transaction_state = self._active_transactions[transaction_id]
        
        return {
            "transaction_id": transaction_id,
            "started_at": transaction_state.started_at.isoformat(),
            "operations_count": len(transaction_state.operations),
            "rollback_data_count": len(transaction_state.rollback_data),
            "is_committed": transaction_state.is_committed,
            "is_rolled_back": transaction_state.is_rolled_back,
            "operations": transaction_state.operations
        }
    
    async def cleanup_old_transactions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old transaction data from memory.
        
        Args:
            max_age_hours: Maximum age of transactions to keep in hours
            
        Returns:
            Number of transactions cleaned up
        """
        cutoff_time = datetime.utcnow().replace(microsecond=0) - timedelta(hours=max_age_hours)
        
        transactions_to_remove = []
        for tx_id, tx_state in self._active_transactions.items():
            if tx_state.started_at < cutoff_time:
                transactions_to_remove.append(tx_id)
        
        for tx_id in transactions_to_remove:
            del self._active_transactions[tx_id]
        
        if transactions_to_remove:
            logger.info(f"Cleaned up {len(transactions_to_remove)} old transactions")
        
        return len(transactions_to_remove)


# Global transaction manager instance
_transaction_manager = None


def get_database_transaction_manager(supabase_client: SupabaseClient = None) -> DatabaseTransactionManager:
    """
    Get the global DatabaseTransactionManager instance.
    
    Args:
        supabase_client: Optional Supabase client instance
        
    Returns:
        DatabaseTransactionManager instance
    """
    global _transaction_manager
    if _transaction_manager is None:
        _transaction_manager = DatabaseTransactionManager(supabase_client)
    return _transaction_manager