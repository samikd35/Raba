"""
Sync Prioritization Service

This service provides functionality for prioritizing synchronization of recent reports,
managing sync priorities, and handling user-initiated synchronization.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass, asdict

from ...report.report_synchronization_service import ReportSynchronizationService
from .offline_sync_service import OfflineSyncService, SyncPriority
from ...system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ...system.core.utils import is_valid_uuid

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Enumeration of priority levels for synchronization."""
    CRITICAL = "critical"  # User-initiated, immediate sync required
    HIGH = "high"         # Recent reports, important changes
    MEDIUM = "medium"     # Regular updates, moderate importance
    LOW = "low"          # Background sync, low importance
    DEFERRED = "deferred" # Can be delayed, sync when convenient


class SyncTrigger(Enum):
    """Enumeration of sync trigger types."""
    USER_INITIATED = "user_initiated"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"
    CONNECTIVITY_RESTORED = "connectivity_restored"
    PRIORITY_ESCALATION = "priority_escalation"


@dataclass
class PriorityRule:
    """Data class for priority rules."""
    id: str
    name: str
    description: str
    condition: str  # JSON string describing the condition
    priority: str
    weight: float = 1.0
    enabled: bool = True
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class SyncRequest:
    """Data class for sync requests."""
    id: str
    user_id: str
    device_id: str
    trigger: str
    priority: str
    report_ids: List[str]
    requested_at: str
    scheduled_for: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.report_ids:
            self.report_ids = []


class SyncPrioritizationService:
    """Service for managing synchronization priorities and scheduling."""
    
    def __init__(
        self,
        sync_service: ReportSynchronizationService = None,
        offline_service: OfflineSyncService = None,
        supabase_client: SupabaseClient = None
    ):
        """
        Initialize the prioritization service.
        
        Args:
            sync_service: Optional synchronization service instance
            offline_service: Optional offline sync service instance
            supabase_client: Optional Supabase client instance
        """
        self.sync_service = sync_service or ReportSynchronizationService(supabase_client)
        self.offline_service = offline_service or OfflineSyncService(sync_service, supabase_client)
        self.client = supabase_client or get_standard_client()
        
        # Priority rules storage (in production, this would be in database)
        self.priority_rules: Dict[str, PriorityRule] = {}
        self.sync_requests: Dict[str, SyncRequest] = {}
        
        # Configuration
        self.recent_report_threshold_hours = 24  # Reports created/updated in last 24 hours are high priority
        self.critical_operations = ["delete", "pin", "unpin"]  # Operations that need immediate sync
        self.batch_size = 50  # Maximum number of changes to sync in one batch
        
        # Initialize default priority rules
        self._initialize_default_rules()
        
    def _initialize_default_rules(self) -> None:
        """Initialize default priority rules."""
        try:
            default_rules = [
                PriorityRule(
                    id="recent_reports",
                    name="Recent Reports",
                    description="Prioritize reports created or updated in the last 24 hours",
                    condition='{"type": "time_based", "field": "updated_at", "threshold_hours": 24}',
                    priority=PriorityLevel.HIGH.value,
                    weight=2.0
                ),
                PriorityRule(
                    id="critical_operations",
                    name="Critical Operations",
                    description="Prioritize delete, pin, and unpin operations",
                    condition='{"type": "operation_based", "operations": ["delete", "pin", "unpin"]}',
                    priority=PriorityLevel.CRITICAL.value,
                    weight=3.0
                ),
                PriorityRule(
                    id="user_initiated",
                    name="User Initiated",
                    description="Prioritize user-initiated synchronization requests",
                    condition='{"type": "trigger_based", "trigger": "user_initiated"}',
                    priority=PriorityLevel.CRITICAL.value,
                    weight=5.0
                ),
                PriorityRule(
                    id="pinned_reports",
                    name="Pinned Reports",
                    description="Prioritize changes to pinned reports",
                    condition='{"type": "report_property", "property": "is_pinned", "value": true}',
                    priority=PriorityLevel.HIGH.value,
                    weight=2.5
                ),
                PriorityRule(
                    id="view_operations",
                    name="View Operations",
                    description="Lower priority for view count updates",
                    condition='{"type": "operation_based", "operations": ["view"]}',
                    priority=PriorityLevel.LOW.value,
                    weight=0.5
                )
            ]
            
            for rule in default_rules:
                self.priority_rules[rule.id] = rule
                
            logger.info(f"Initialized {len(default_rules)} default priority rules")
            
        except Exception as e:
            logger.error(f"Error initializing default priority rules: {str(e)}")
            
    def calculate_sync_priority(
        self,
        user_id: str,
        change: Dict[str, Any],
        trigger: SyncTrigger = SyncTrigger.AUTOMATIC
    ) -> Tuple[PriorityLevel, float]:
        """
        Calculate the sync priority for a change based on priority rules.
        
        Args:
            user_id: The ID of the user
            change: The change to prioritize
            trigger: The sync trigger type
            
        Returns:
            Tuple of (priority_level, weight_score)
        """
        try:
            total_weight = 0.0
            max_priority = PriorityLevel.LOW
            
            # Evaluate each priority rule
            for rule in self.priority_rules.values():
                if not rule.enabled:
                    continue
                    
                if self._evaluate_priority_rule(rule, change, trigger):
                    rule_priority = PriorityLevel(rule.priority)
                    total_weight += rule.weight
                    
                    # Use the highest priority found
                    if self._is_higher_priority(rule_priority, max_priority):
                        max_priority = rule_priority
                        
            # If no rules matched, use default priority
            if total_weight == 0:
                max_priority = PriorityLevel.MEDIUM
                total_weight = 1.0
                
            logger.debug(f"Calculated priority {max_priority.value} (weight: {total_weight}) for change {change.get('id', 'unknown')}")
            
            return max_priority, total_weight
            
        except Exception as e:
            logger.error(f"Error calculating sync priority: {str(e)}")
            return PriorityLevel.MEDIUM, 1.0
            
    def _evaluate_priority_rule(
        self,
        rule: PriorityRule,
        change: Dict[str, Any],
        trigger: SyncTrigger
    ) -> bool:
        """
        Evaluate if a priority rule applies to a change.
        
        Args:
            rule: The priority rule to evaluate
            change: The change to evaluate
            trigger: The sync trigger type
            
        Returns:
            True if the rule applies, False otherwise
        """
        try:
            import json
            condition = json.loads(rule.condition)
            condition_type = condition.get("type")
            
            if condition_type == "time_based":
                return self._evaluate_time_based_condition(condition, change)
            elif condition_type == "operation_based":
                return self._evaluate_operation_based_condition(condition, change)
            elif condition_type == "trigger_based":
                return self._evaluate_trigger_based_condition(condition, trigger)
            elif condition_type == "report_property":
                return self._evaluate_report_property_condition(condition, change)
            else:
                logger.warning(f"Unknown condition type: {condition_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating priority rule {rule.id}: {str(e)}")
            return False
            
    def _evaluate_time_based_condition(self, condition: Dict[str, Any], change: Dict[str, Any]) -> bool:
        """Evaluate time-based priority condition."""
        try:
            field = condition.get("field", "updated_at")
            threshold_hours = condition.get("threshold_hours", 24)
            
            timestamp_str = change.get(field) or change.get("timestamp")
            if not timestamp_str:
                return False
                
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            threshold_time = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)
            
            return timestamp > threshold_time
            
        except Exception as e:
            logger.debug(f"Error evaluating time-based condition: {str(e)}")
            return False
            
    def _evaluate_operation_based_condition(self, condition: Dict[str, Any], change: Dict[str, Any]) -> bool:
        """Evaluate operation-based priority condition."""
        try:
            target_operations = condition.get("operations", [])
            change_operation = change.get("operation")
            
            return change_operation in target_operations
            
        except Exception as e:
            logger.debug(f"Error evaluating operation-based condition: {str(e)}")
            return False
            
    def _evaluate_trigger_based_condition(self, condition: Dict[str, Any], trigger: SyncTrigger) -> bool:
        """Evaluate trigger-based priority condition."""
        try:
            target_trigger = condition.get("trigger")
            return trigger.value == target_trigger
            
        except Exception as e:
            logger.debug(f"Error evaluating trigger-based condition: {str(e)}")
            return False
            
    def _evaluate_report_property_condition(self, condition: Dict[str, Any], change: Dict[str, Any]) -> bool:
        """Evaluate report property-based priority condition."""
        try:
            property_name = condition.get("property")
            expected_value = condition.get("value")
            
            # Check in change data first, then in report data if available
            change_data = change.get("data", {})
            actual_value = change_data.get(property_name)
            
            return actual_value == expected_value
            
        except Exception as e:
            logger.debug(f"Error evaluating report property condition: {str(e)}")
            return False
            
    def _is_higher_priority(self, priority1: PriorityLevel, priority2: PriorityLevel) -> bool:
        """Check if priority1 is higher than priority2."""
        priority_order = {
            PriorityLevel.CRITICAL: 0,
            PriorityLevel.HIGH: 1,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 3,
            PriorityLevel.DEFERRED: 4
        }
        
        return priority_order[priority1] < priority_order[priority2]
        
    def prioritize_sync_queue(self, user_id: str, device_id: str) -> List[Dict[str, Any]]:
        """
        Prioritize the sync queue for a user and device.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            
        Returns:
            List of prioritized changes
        """
        try:
            logger.info(f"Prioritizing sync queue for user {user_id}, device {device_id}")
            
            # Get offline changes
            changes = self.offline_service.get_offline_changes(user_id, device_id)
            
            if not changes:
                return []
                
            # Calculate priority for each change
            prioritized_changes = []
            for change in changes:
                priority, weight = self.calculate_sync_priority(user_id, change)
                
                prioritized_change = change.copy()
                prioritized_change["calculated_priority"] = priority.value
                prioritized_change["priority_weight"] = weight
                prioritized_changes.append(prioritized_change)
                
            # Sort by priority and weight
            priority_order = {
                PriorityLevel.CRITICAL.value: 0,
                PriorityLevel.HIGH.value: 1,
                PriorityLevel.MEDIUM.value: 2,
                PriorityLevel.LOW.value: 3,
                PriorityLevel.DEFERRED.value: 4
            }
            
            prioritized_changes.sort(key=lambda x: (
                priority_order.get(x["calculated_priority"], 2),
                -x["priority_weight"],  # Higher weight first
                x["timestamp"]  # Earlier timestamp first for same priority
            ))
            
            logger.info(f"Prioritized {len(prioritized_changes)} changes")
            return prioritized_changes
            
        except Exception as e:
            logger.error(f"Error prioritizing sync queue: {str(e)}")
            return []
            
    def request_user_sync(
        self,
        user_id: str,
        device_id: str,
        report_ids: List[str] = None,
        immediate: bool = True
    ) -> str:
        """
        Request user-initiated synchronization.
        
        Args:
            user_id: The ID of the user
            device_id: The ID of the device
            report_ids: Optional list of specific report IDs to sync
            immediate: Whether to sync immediately or schedule
            
        Returns:
            The ID of the sync request
        """
        try:
            logger.info(f"User sync requested for user {user_id}, device {device_id}")
            
            request_id = str(uuid4())
            
            sync_request = SyncRequest(
                id=request_id,
                user_id=user_id,
                device_id=device_id,
                trigger=SyncTrigger.USER_INITIATED.value,
                priority=PriorityLevel.CRITICAL.value,
                report_ids=report_ids or [],
                requested_at=datetime.now(timezone.utc).isoformat(),
                scheduled_for=datetime.now(timezone.utc).isoformat() if immediate else None
            )
            
            self.sync_requests[request_id] = sync_request
            
            if immediate:
                # Execute sync immediately
                self._execute_sync_request(sync_request)
            else:
                # Schedule for later execution
                logger.info(f"Sync request {request_id} scheduled for later execution")
                
            return request_id
            
        except Exception as e:
            logger.error(f"Error requesting user sync: {str(e)}")
            raise
            
    def _execute_sync_request(self, sync_request: SyncRequest) -> None:
        """
        Execute a sync request.
        
        Args:
            sync_request: The sync request to execute
        """
        try:
            logger.info(f"Executing sync request {sync_request.id}")
            
            sync_request.status = "in_progress"
            
            # If specific report IDs are requested, filter changes
            if sync_request.report_ids:
                # Get only changes for specified reports
                all_changes = self.offline_service.get_offline_changes(
                    sync_request.user_id, 
                    sync_request.device_id
                )
                
                filtered_changes = [
                    change for change in all_changes
                    if change.get("report_id") in sync_request.report_ids
                ]
                
                # Update offline service to only sync these changes
                # This is a simplified approach - in production, you'd want more sophisticated filtering
                changes_to_sync = filtered_changes
            else:
                # Sync all changes with prioritization
                changes_to_sync = self.prioritize_sync_queue(
                    sync_request.user_id, 
                    sync_request.device_id
                )
                
            if not changes_to_sync:
                sync_request.status = "completed"
                sync_request.completed_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Sync request {sync_request.id} completed - no changes to sync")
                return
                
            # Execute the sync using offline service
            result = self.offline_service.force_sync(
                sync_request.user_id,
                sync_request.device_id
            )
            
            if result["success"]:
                sync_request.status = "completed"
                sync_request.completed_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Sync request {sync_request.id} completed successfully")
            else:
                sync_request.status = "failed"
                sync_request.error_message = result.get("error", "Unknown error")
                logger.error(f"Sync request {sync_request.id} failed: {sync_request.error_message}")
                
        except Exception as e:
            sync_request.status = "failed"
            sync_request.error_message = str(e)
            logger.error(f"Error executing sync request {sync_request.id}: {str(e)}")
            
    def get_sync_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a sync request.
        
        Args:
            request_id: The ID of the sync request
            
        Returns:
            Sync request status or None if not found
        """
        try:
            if request_id not in self.sync_requests:
                return None
                
            sync_request = self.sync_requests[request_id]
            return asdict(sync_request)
            
        except Exception as e:
            logger.error(f"Error getting sync request status: {str(e)}")
            return None
            
    def cancel_sync_request(self, request_id: str) -> bool:
        """
        Cancel a pending sync request.
        
        Args:
            request_id: The ID of the sync request
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            if request_id not in self.sync_requests:
                return False
                
            sync_request = self.sync_requests[request_id]
            
            if sync_request.status in ["completed", "failed"]:
                logger.warning(f"Cannot cancel sync request {request_id} - already {sync_request.status}")
                return False
                
            sync_request.status = "cancelled"
            sync_request.completed_at = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Sync request {request_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling sync request: {str(e)}")
            return False
            
    def add_priority_rule(self, rule: PriorityRule) -> None:
        """
        Add a custom priority rule.
        
        Args:
            rule: The priority rule to add
        """
        try:
            self.priority_rules[rule.id] = rule
            logger.info(f"Added priority rule: {rule.name}")
            
        except Exception as e:
            logger.error(f"Error adding priority rule: {str(e)}")
            raise
            
    def remove_priority_rule(self, rule_id: str) -> bool:
        """
        Remove a priority rule.
        
        Args:
            rule_id: The ID of the rule to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            if rule_id in self.priority_rules:
                del self.priority_rules[rule_id]
                logger.info(f"Removed priority rule: {rule_id}")
                return True
            else:
                logger.warning(f"Priority rule not found: {rule_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing priority rule: {str(e)}")
            return False
            
    def get_priority_rules(self) -> List[Dict[str, Any]]:
        """
        Get all priority rules.
        
        Returns:
            List of priority rules
        """
        try:
            return [asdict(rule) for rule in self.priority_rules.values()]
            
        except Exception as e:
            logger.error(f"Error getting priority rules: {str(e)}")
            return []
            
    def update_priority_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a priority rule.
        
        Args:
            rule_id: The ID of the rule to update
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if rule_id not in self.priority_rules:
                logger.warning(f"Priority rule not found: {rule_id}")
                return False
                
            rule = self.priority_rules[rule_id]
            
            # Update allowed fields
            allowed_fields = ["name", "description", "condition", "priority", "weight", "enabled"]
            for field, value in updates.items():
                if field in allowed_fields and hasattr(rule, field):
                    setattr(rule, field, value)
                    
            logger.info(f"Updated priority rule: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating priority rule: {str(e)}")
            return False
            
    def get_sync_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get synchronization statistics including priority breakdown.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dict containing sync statistics
        """
        try:
            # Get base statistics from offline service
            base_stats = self.offline_service.get_sync_statistics(user_id)
            
            # Add prioritization-specific statistics
            user_requests = [
                req for req in self.sync_requests.values()
                if req.user_id == user_id
            ]
            
            # Count requests by status
            request_status_counts = {}
            for request in user_requests:
                status = request.status
                request_status_counts[status] = request_status_counts.get(status, 0) + 1
                
            # Get priority breakdown of current changes
            all_changes = self.offline_service.get_offline_changes(user_id)
            priority_breakdown = {}
            
            for change in all_changes:
                priority, _ = self.calculate_sync_priority(user_id, change)
                priority_breakdown[priority.value] = priority_breakdown.get(priority.value, 0) + 1
                
            # Enhance base statistics
            base_stats.update({
                "prioritization_enabled": True,
                "active_priority_rules": len([r for r in self.priority_rules.values() if r.enabled]),
                "total_priority_rules": len(self.priority_rules),
                "sync_requests": {
                    "total": len(user_requests),
                    "status_breakdown": request_status_counts
                },
                "priority_breakdown": priority_breakdown,
                "recent_threshold_hours": self.recent_report_threshold_hours
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {str(e)}")
            return {"error": str(e)}
            
    def cleanup_completed_requests(self, older_than_hours: int = 24) -> int:
        """
        Clean up completed sync requests older than specified hours.
        
        Args:
            older_than_hours: Remove requests completed more than this many hours ago
            
        Returns:
            Number of requests cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            cutoff_iso = cutoff_time.isoformat()
            
            requests_to_remove = []
            
            for request_id, request in self.sync_requests.items():
                if (request.status in ["completed", "failed", "cancelled"] and
                    request.completed_at and
                    request.completed_at < cutoff_iso):
                    requests_to_remove.append(request_id)
                    
            for request_id in requests_to_remove:
                del self.sync_requests[request_id]
                
            logger.info(f"Cleaned up {len(requests_to_remove)} completed sync requests")
            return len(requests_to_remove)
            
        except Exception as e:
            logger.error(f"Error cleaning up completed requests: {str(e)}")
            return 0