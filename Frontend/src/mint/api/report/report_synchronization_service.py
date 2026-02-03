"""
Report Synchronization Service

This service provides functionality for synchronizing report history across devices,
including conflict resolution strategies and offline change queuing.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID, uuid4
from enum import Enum

from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..system.core.utils import is_valid_uuid

logger = logging.getLogger(__name__)


class SyncConflictResolution(Enum):
    """Enumeration of conflict resolution strategies."""
    LATEST_WINS = "latest_wins"
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    MERGE = "merge"


class SyncStatus(Enum):
    """Enumeration of synchronization statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncOperation(Enum):
    """Enumeration of synchronization operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PIN = "pin"
    UNPIN = "unpin"
    VIEW = "view"


class ReportSynchronizationService:
    """Service for managing cross-device report synchronization."""
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the synchronization service.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.reports_table = "mint_reports"
        self.sync_queue_table = "report_sync_queue"
        self.sync_log_table = "report_sync_log"
        self.device_sessions_table = "device_sessions"
        
    def sync_report_changes(
        self,
        user_id: str,
        device_id: str,
        changes: List[Dict[str, Any]],
        last_sync_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize report changes from a device.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device making the sync request
            changes: List of changes to synchronize
            last_sync_timestamp: Timestamp of last successful sync
            
        Returns:
            Dict containing sync results and any conflicts
        """
        try:
            logger.info(f"Starting sync for user {user_id} from device {device_id}")
            
            # Validate inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            if not changes:
                logger.info("No changes to sync")
                return {
                    "success": True,
                    "conflicts": [],
                    "applied_changes": 0,
                    "server_changes": [],
                    "sync_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            # Update device session
            self._update_device_session(user_id, device_id)
            
            # Get server changes since last sync
            server_changes = self._get_server_changes_since(user_id, last_sync_timestamp)
            
            # Process client changes and detect conflicts
            sync_results = {
                "success": True,
                "conflicts": [],
                "applied_changes": 0,
                "failed_changes": [],
                "server_changes": server_changes,
                "sync_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            for change in changes:
                try:
                    result = self._process_sync_change(user_id, device_id, change, server_changes)
                    
                    if result["status"] == "applied":
                        sync_results["applied_changes"] += 1
                    elif result["status"] == "conflict":
                        sync_results["conflicts"].append(result)
                    elif result["status"] == "failed":
                        sync_results["failed_changes"].append(result)
                        
                except Exception as change_error:
                    logger.error(f"Error processing change {change.get('id', 'unknown')}: {str(change_error)}")
                    sync_results["failed_changes"].append({
                        "change": change,
                        "error": str(change_error),
                        "status": "failed"
                    })
                    
            # Log sync operation
            self._log_sync_operation(user_id, device_id, sync_results)
            
            logger.info(f"Sync completed for user {user_id}: {sync_results['applied_changes']} applied, "
                       f"{len(sync_results['conflicts'])} conflicts, {len(sync_results['failed_changes'])} failed")
            
            return sync_results
            
        except Exception as e:
            logger.error(f"Error during sync for user {user_id}: {str(e)}")
            raise
            
    def _process_sync_change(
        self,
        user_id: str,
        device_id: str,
        change: Dict[str, Any],
        server_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a single sync change and handle conflicts.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            change: The change to process
            server_changes: Recent server changes for conflict detection
            
        Returns:
            Dict containing the result of processing the change
        """
        try:
            change_id = change.get("id", str(uuid4()))
            operation = change.get("operation")
            report_id = change.get("report_id")
            timestamp = change.get("timestamp")
            data = change.get("data", {})
            
            # Validate change structure
            if not operation or not report_id:
                return {
                    "change_id": change_id,
                    "status": "failed",
                    "error": "Invalid change structure: missing operation or report_id"
                }
                
            # Check for conflicts with server changes
            conflict = self._detect_conflict(change, server_changes)
            if conflict:
                resolved_change = self._resolve_conflict(change, conflict)
                if resolved_change:
                    change = resolved_change
                else:
                    return {
                        "change_id": change_id,
                        "status": "conflict",
                        "conflict": conflict,
                        "change": change
                    }
                    
            # Apply the change based on operation type
            if operation == SyncOperation.CREATE.value:
                result = self._apply_create_change(user_id, change)
            elif operation == SyncOperation.UPDATE.value:
                result = self._apply_update_change(user_id, change)
            elif operation == SyncOperation.DELETE.value:
                result = self._apply_delete_change(user_id, change)
            elif operation == SyncOperation.PIN.value:
                result = self._apply_pin_change(user_id, change)
            elif operation == SyncOperation.UNPIN.value:
                result = self._apply_unpin_change(user_id, change)
            elif operation == SyncOperation.VIEW.value:
                result = self._apply_view_change(user_id, change)
            else:
                return {
                    "change_id": change_id,
                    "status": "failed",
                    "error": f"Unknown operation: {operation}"
                }
                
            return {
                "change_id": change_id,
                "status": "applied",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing sync change: {str(e)}")
            return {
                "change_id": change.get("id", "unknown"),
                "status": "failed",
                "error": str(e)
            }
            
    def _detect_conflict(
        self,
        change: Dict[str, Any],
        server_changes: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect conflicts between client change and server changes.
        
        Args:
            change: The client change
            server_changes: Recent server changes
            
        Returns:
            Conflict information if detected, None otherwise
        """
        try:
            report_id = change.get("report_id")
            operation = change.get("operation")
            timestamp = change.get("timestamp")
            
            # Look for conflicting server changes on the same report
            for server_change in server_changes:
                if server_change.get("report_id") == report_id:
                    server_timestamp = server_change.get("updated_at")
                    
                    # Check if server change is more recent
                    if self._is_timestamp_newer(server_timestamp, timestamp):
                        # Determine conflict type
                        conflict_type = self._determine_conflict_type(operation, server_change)
                        
                        if conflict_type:
                            return {
                                "type": conflict_type,
                                "client_change": change,
                                "server_change": server_change,
                                "resolution_strategy": SyncConflictResolution.LATEST_WINS.value
                            }
                            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting conflict: {str(e)}")
            return None
            
    def _resolve_conflict(
        self,
        client_change: Dict[str, Any],
        conflict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a synchronization conflict using the specified strategy.
        
        Args:
            client_change: The client change
            conflict: The conflict information
            
        Returns:
            Resolved change if successful, None if unresolvable
        """
        try:
            strategy = conflict.get("resolution_strategy", SyncConflictResolution.LATEST_WINS.value)
            server_change = conflict.get("server_change")
            
            if strategy == SyncConflictResolution.LATEST_WINS.value:
                # Compare timestamps and use the latest
                client_timestamp = client_change.get("timestamp")
                server_timestamp = server_change.get("updated_at")
                
                if self._is_timestamp_newer(client_timestamp, server_timestamp):
                    return client_change
                else:
                    # Server wins, return None to skip client change
                    return None
                    
            elif strategy == SyncConflictResolution.SERVER_WINS.value:
                # Server always wins
                return None
                
            elif strategy == SyncConflictResolution.CLIENT_WINS.value:
                # Client always wins
                return client_change
                
            elif strategy == SyncConflictResolution.MERGE.value:
                # Attempt to merge changes
                return self._merge_changes(client_change, server_change)
                
            else:
                logger.warning(f"Unknown conflict resolution strategy: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"Error resolving conflict: {str(e)}")
            return None
            
    def _merge_changes(
        self,
        client_change: Dict[str, Any],
        server_change: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Merge client and server changes when possible.
        
        Args:
            client_change: The client change
            server_change: The server change
            
        Returns:
            Merged change if successful, None otherwise
        """
        try:
            # For now, implement simple field-level merging
            # This can be enhanced based on specific requirements
            
            merged_data = {}
            client_data = client_change.get("data", {})
            server_data = server_change.get("data", {})
            
            # Merge non-conflicting fields
            all_fields = set(client_data.keys()) | set(server_data.keys())
            
            for field in all_fields:
                client_value = client_data.get(field)
                server_value = server_data.get(field)
                
                if client_value == server_value:
                    merged_data[field] = client_value
                elif client_value is None:
                    merged_data[field] = server_value
                elif server_value is None:
                    merged_data[field] = client_value
                else:
                    # Field conflict - use latest timestamp logic
                    client_timestamp = client_change.get("timestamp")
                    server_timestamp = server_change.get("updated_at")
                    
                    if self._is_timestamp_newer(client_timestamp, server_timestamp):
                        merged_data[field] = client_value
                    else:
                        merged_data[field] = server_value
                        
            # Create merged change
            merged_change = client_change.copy()
            merged_change["data"] = merged_data
            merged_change["merged"] = True
            
            return merged_change
            
        except Exception as e:
            logger.error(f"Error merging changes: {str(e)}")
            return None
            
    def _apply_create_change(self, user_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a create operation change."""
        try:
            data = change.get("data", {})
            data["user_id"] = user_id
            data["created_at"] = change.get("timestamp")
            data["updated_at"] = change.get("timestamp")
            
            response = self.client.client.table(self.reports_table) \
                .insert(data) \
                .execute()
                
            return {"operation": "create", "result": response.data[0] if response.data else None}
            
        except Exception as e:
            logger.error(f"Error applying create change: {str(e)}")
            raise
            
    def _apply_update_change(self, user_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an update operation change."""
        try:
            report_id = change.get("report_id")
            data = change.get("data", {})
            data["updated_at"] = change.get("timestamp")
            
            response = self.client.client.table(self.reports_table) \
                .update(data) \
                .eq("id", report_id) \
                .eq("user_id", user_id) \
                .execute()
                
            return {"operation": "update", "result": response.data[0] if response.data else None}
            
        except Exception as e:
            logger.error(f"Error applying update change: {str(e)}")
            raise
            
    def _apply_delete_change(self, user_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a delete operation change."""
        try:
            report_id = change.get("report_id")
            permanent = change.get("data", {}).get("permanent", False)
            
            if permanent:
                response = self.client.client.table(self.reports_table) \
                    .delete() \
                    .eq("id", report_id) \
                    .eq("user_id", user_id) \
                    .execute()
            else:
                response = self.client.client.table(self.reports_table) \
                    .update({
                        "deleted_at": change.get("timestamp"),
                        "updated_at": change.get("timestamp")
                    }) \
                    .eq("id", report_id) \
                    .eq("user_id", user_id) \
                    .execute()
                    
            return {"operation": "delete", "permanent": permanent, "result": response.data}
            
        except Exception as e:
            logger.error(f"Error applying delete change: {str(e)}")
            raise
            
    def _apply_pin_change(self, user_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a pin operation change."""
        try:
            report_id = change.get("report_id")
            
            response = self.client.client.table(self.reports_table) \
                .update({
                    "is_pinned": True,
                    "updated_at": change.get("timestamp")
                }) \
                .eq("id", report_id) \
                .eq("user_id", user_id) \
                .execute()
                
            return {"operation": "pin", "result": response.data[0] if response.data else None}
            
        except Exception as e:
            logger.error(f"Error applying pin change: {str(e)}")
            raise
            
    def _apply_unpin_change(self, user_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an unpin operation change."""
        try:
            report_id = change.get("report_id")
            
            response = self.client.client.table(self.reports_table) \
                .update({
                    "is_pinned": False,
                    "updated_at": change.get("timestamp")
                }) \
                .eq("id", report_id) \
                .eq("user_id", user_id) \
                .execute()
                
            return {"operation": "unpin", "result": response.data[0] if response.data else None}
            
        except Exception as e:
            logger.error(f"Error applying unpin change: {str(e)}")
            raise
            
    def _apply_view_change(self, user_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a view operation change."""
        try:
            report_id = change.get("report_id")
            
            # Update view count and last viewed timestamp
            response = self.client.client.table(self.reports_table) \
                .update({
                    "last_viewed_at": change.get("timestamp"),
                    "view_count": self.client.client.rpc("increment_view_count", {"report_id": report_id}).execute().data,
                    "updated_at": change.get("timestamp")
                }) \
                .eq("id", report_id) \
                .eq("user_id", user_id) \
                .execute()
                
            return {"operation": "view", "result": response.data[0] if response.data else None}
            
        except Exception as e:
            logger.error(f"Error applying view change: {str(e)}")
            raise
            
    def _get_server_changes_since(
        self,
        user_id: str,
        last_sync_timestamp: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Get server changes since the last sync timestamp.
        
        Args:
            user_id: The ID of the user
            last_sync_timestamp: Timestamp of last sync
            
        Returns:
            List of server changes
        """
        try:
            if not last_sync_timestamp:
                # If no last sync timestamp, return recent changes (last 24 hours)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                last_sync_timestamp = cutoff_time.isoformat()
                
            response = self.client.client.table(self.reports_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .gt("updated_at", last_sync_timestamp) \
                .order("updated_at", desc=False) \
                .execute()
                
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting server changes: {str(e)}")
            return []
            
    def _update_device_session(self, user_id: str, device_id: str) -> None:
        """
        Update device session information.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
        """
        try:
            session_data = {
                "user_id": user_id,
                "device_id": device_id,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert device session
            self.client.client.table(self.device_sessions_table) \
                .upsert(session_data, on_conflict="user_id,device_id") \
                .execute()
                
        except Exception as e:
            logger.debug(f"Could not update device session: {str(e)}")
            # Non-critical operation, continue without failing
            
    def _log_sync_operation(
        self,
        user_id: str,
        device_id: str,
        sync_results: Dict[str, Any]
    ) -> None:
        """
        Log synchronization operation for debugging and monitoring.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            sync_results: Results of the sync operation
        """
        try:
            log_entry = {
                "user_id": user_id,
                "device_id": device_id,
                "sync_timestamp": sync_results["sync_timestamp"],
                "applied_changes": sync_results["applied_changes"],
                "conflicts_count": len(sync_results["conflicts"]),
                "failed_changes_count": len(sync_results["failed_changes"]),
                "server_changes_count": len(sync_results["server_changes"]),
                "success": sync_results["success"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.client.client.table(self.sync_log_table) \
                .insert(log_entry) \
                .execute()
                
        except Exception as e:
            logger.debug(f"Could not log sync operation: {str(e)}")
            # Non-critical operation, continue without failing
            
    def _is_timestamp_newer(self, timestamp1: str, timestamp2: str) -> bool:
        """
        Compare two timestamps to determine which is newer.
        
        Args:
            timestamp1: First timestamp
            timestamp2: Second timestamp
            
        Returns:
            True if timestamp1 is newer than timestamp2
        """
        try:
            if not timestamp1 or not timestamp2:
                return timestamp1 is not None
                
            dt1 = datetime.fromisoformat(timestamp1.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(timestamp2.replace('Z', '+00:00'))
            
            return dt1 > dt2
            
        except Exception as e:
            logger.debug(f"Error comparing timestamps: {str(e)}")
            return False
            
    def _determine_conflict_type(
        self,
        client_operation: str,
        server_change: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine the type of conflict between client and server changes.
        
        Args:
            client_operation: The client operation
            server_change: The server change
            
        Returns:
            Conflict type if there is a conflict, None otherwise
        """
        try:
            # Simple conflict detection - any concurrent modification is a conflict
            # This can be enhanced with more sophisticated logic
            
            if client_operation in [SyncOperation.UPDATE.value, SyncOperation.DELETE.value]:
                return "concurrent_modification"
            elif client_operation == SyncOperation.CREATE.value:
                # Check if report already exists on server
                if server_change.get("created_at"):
                    return "duplicate_creation"
                    
            return None
            
        except Exception as e:
            logger.debug(f"Error determining conflict type: {str(e)}")
            return "unknown_conflict"
            
    def get_sync_status(self, user_id: str, device_id: str) -> Dict[str, Any]:
        """
        Get synchronization status for a device.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            
        Returns:
            Dict containing sync status information
        """
        try:
            logger.debug(f"Getting sync status for user {user_id}, device {device_id}")
            
            # Get device session info
            session_response = self.client.client.table(self.device_sessions_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("device_id", device_id) \
                .execute()
                
            session_data = session_response.data[0] if session_response.data else None
            
            # Get recent sync logs
            log_response = self.client.client.table(self.sync_log_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("device_id", device_id) \
                .order("created_at", desc=True) \
                .limit(10) \
                .execute()
                
            sync_logs = log_response.data or []
            
            # Get pending sync queue items
            queue_response = self.client.client.table(self.sync_queue_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("device_id", device_id) \
                .eq("status", SyncStatus.PENDING.value) \
                .execute()
                
            pending_items = queue_response.data or []
            
            return {
                "user_id": user_id,
                "device_id": device_id,
                "last_sync_at": session_data.get("last_sync_at") if session_data else None,
                "pending_changes": len(pending_items),
                "recent_sync_logs": sync_logs,
                "sync_enabled": True,
                "status": "active" if session_data else "inactive"
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            raise
            
    def queue_offline_change(
        self,
        user_id: str,
        device_id: str,
        change: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Queue a change for later synchronization when offline.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            change: The change to queue
            
        Returns:
            Dict containing queue operation result
        """
        try:
            logger.debug(f"Queuing offline change for user {user_id}, device {device_id}")
            
            queue_item = {
                "id": str(uuid4()),
                "user_id": user_id,
                "device_id": device_id,
                "change_data": json.dumps(change),
                "operation": change.get("operation"),
                "report_id": change.get("report_id"),
                "status": SyncStatus.PENDING.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "retry_count": 0
            }
            
            response = self.client.client.table(self.sync_queue_table) \
                .insert(queue_item) \
                .execute()
                
            return {
                "success": True,
                "queue_item_id": queue_item["id"],
                "message": "Change queued for synchronization"
            }
            
        except Exception as e:
            logger.error(f"Error queuing offline change: {str(e)}")
            raise
            
    def process_sync_queue(self, user_id: str, device_id: str) -> Dict[str, Any]:
        """
        Process pending synchronization queue items.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            
        Returns:
            Dict containing processing results
        """
        try:
            logger.info(f"Processing sync queue for user {user_id}, device {device_id}")
            
            # Get pending queue items
            response = self.client.client.table(self.sync_queue_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("device_id", device_id) \
                .eq("status", SyncStatus.PENDING.value) \
                .order("created_at", desc=False) \
                .execute()
                
            queue_items = response.data or []
            
            if not queue_items:
                return {
                    "success": True,
                    "processed_count": 0,
                    "message": "No pending items in sync queue"
                }
                
            # Process each queue item
            processed_count = 0
            failed_count = 0
            
            for item in queue_items:
                try:
                    # Parse change data
                    change_data = json.loads(item["change_data"])
                    
                    # Process the change
                    result = self._process_sync_change(user_id, device_id, change_data, [])
                    
                    if result["status"] == "applied":
                        # Mark as completed
                        self.client.client.table(self.sync_queue_table) \
                            .update({
                                "status": SyncStatus.COMPLETED.value,
                                "processed_at": datetime.now(timezone.utc).isoformat()
                            }) \
                            .eq("id", item["id"]) \
                            .execute()
                        processed_count += 1
                    else:
                        # Mark as failed and increment retry count
                        retry_count = item.get("retry_count", 0) + 1
                        max_retries = 3
                        
                        if retry_count >= max_retries:
                            status = SyncStatus.FAILED.value
                        else:
                            status = SyncStatus.PENDING.value
                            
                        self.client.client.table(self.sync_queue_table) \
                            .update({
                                "status": status,
                                "retry_count": retry_count,
                                "last_error": result.get("error", "Unknown error"),
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }) \
                            .eq("id", item["id"]) \
                            .execute()
                        failed_count += 1
                        
                except Exception as item_error:
                    logger.error(f"Error processing queue item {item['id']}: {str(item_error)}")
                    failed_count += 1
                    
            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_items": len(queue_items),
                "message": f"Processed {processed_count} items, {failed_count} failed"
            }
            
        except Exception as e:
            logger.error(f"Error processing sync queue: {str(e)}")
            raise