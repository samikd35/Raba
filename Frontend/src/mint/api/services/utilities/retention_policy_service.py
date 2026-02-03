"""
Retention Policy Service

This service handles the application of retention policies for reports,
including scheduled cleanup and archiving of old data.
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

# from ...report.report_history_service import ReportHistoryService  # Circular import - will be injected
from ...system.core.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class RetentionPolicyService:
    """Service for managing report retention policies and cleanup tasks."""
    
    def __init__(self, history_service = None):
        """
        Initialize the retention policy service.
        
        Args:
            history_service: Optional ReportHistoryService instance
        """
        self.history_service = history_service  # Will be injected to avoid circular import
        self.scheduler = None  # Placeholder for future scheduler implementation
        self.default_retention_days = 90
        self.cleanup_enabled = True
        
    def start_scheduler(self):
        """Start the scheduled retention policy tasks."""
        logger.info("Scheduler functionality not implemented yet - requires apscheduler")
        # TODO: Implement with apscheduler when available
        
    def stop_scheduler(self):
        """Stop the scheduled retention policy tasks."""
        logger.info("Scheduler functionality not implemented yet - requires apscheduler")
        # TODO: Implement with apscheduler when available
            
    async def run_daily_cleanup(self):
        """Run daily cleanup of expired reports."""
        try:
            logger.info("Starting daily retention policy cleanup")
            
            result = await self.apply_retention_policy_async(
                retention_days=self.default_retention_days
            )
            
            logger.info(f"Daily cleanup completed: {result['message']}")
            
            # Log metrics for monitoring
            if result['deleted_count'] > 0:
                logger.warning(f"Permanently deleted {result['deleted_count']} expired reports")
            
        except Exception as e:
            logger.error(f"Daily cleanup failed: {str(e)}")
            
    async def run_weekly_archiving(self):
        """Run weekly archiving of old reports."""
        try:
            logger.info("Starting weekly report archiving")
            
            # Archive reports older than 60 days but not yet deleted
            result = await self.archive_old_reports_async(archive_days=60)
            
            logger.info(f"Weekly archiving completed: {result['message']}")
            
        except Exception as e:
            logger.error(f"Weekly archiving failed: {str(e)}")
            
    async def apply_retention_policy_async(self, retention_days: int = 90) -> Dict[str, Any]:
        """
        Apply retention policy asynchronously.
        
        Args:
            retention_days: Number of days to retain reports
            
        Returns:
            Dict with cleanup results
        """
        try:
            # Run the retention policy in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.history_service.apply_retention_policy,
                retention_days
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Async retention policy failed: {str(e)}")
            raise
            
    async def archive_old_reports_async(self, archive_days: int = 60) -> Dict[str, Any]:
        """
        Archive old reports asynchronously.
        
        Args:
            archive_days: Number of days after which to archive reports
            
        Returns:
            Dict with archiving results
        """
        try:
            logger.info(f"Archiving reports older than {archive_days} days")
            
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=archive_days)
            cutoff_iso = cutoff_date.isoformat()
            
            # Find reports to archive (not deleted, older than cutoff)
            client = self.history_service.client
            response = client.client.table(client.reports_table) \
                .select("id, session_id, title, created_at") \
                .is_("deleted_at", "null") \
                .eq("is_archived", False) \
                .lt("created_at", cutoff_iso) \
                .execute()
                
            reports_to_archive = response.data
            
            if not reports_to_archive:
                logger.info("No reports found for archiving")
                return {
                    "success": True,
                    "archived_count": 0,
                    "message": "No reports found for archiving"
                }
                
            # Archive the reports
            report_ids = [report["id"] for report in reports_to_archive]
            
            archive_response = client.client.table(client.reports_table) \
                .update({
                    "is_archived": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }) \
                .in_("id", report_ids) \
                .execute()
                
            archived_count = len(report_ids)
            
            logger.info(f"Archived {archived_count} reports older than {archive_days} days")
            return {
                "success": True,
                "archived_count": archived_count,
                "cutoff_date": cutoff_iso,
                "message": f"Archived {archived_count} reports older than {archive_days} days"
            }
            
        except Exception as e:
            logger.error(f"Error archiving old reports: {str(e)}")
            raise
            
    def get_retention_stats(self) -> Dict[str, Any]:
        """
        Get statistics about retention policy application.
        
        Returns:
            Dict with retention statistics
        """
        try:
            client = self.history_service.client
            
            # Get counts of different report states
            total_response = client.client.table(client.reports_table) \
                .select("id", count="exact") \
                .execute()
                
            active_response = client.client.table(client.reports_table) \
                .select("id", count="exact") \
                .is_("deleted_at", "null") \
                .eq("is_archived", False) \
                .execute()
                
            archived_response = client.client.table(client.reports_table) \
                .select("id", count="exact") \
                .is_("deleted_at", "null") \
                .eq("is_archived", True) \
                .execute()
                
            deleted_response = client.client.table(client.reports_table) \
                .select("id", count="exact") \
                .not_.is_("deleted_at", "null") \
                .execute()
                
            # Calculate retention cutoff dates
            retention_cutoff = datetime.now(timezone.utc) - timedelta(days=self.default_retention_days)
            archive_cutoff = datetime.now(timezone.utc) - timedelta(days=60)
            
            # Get reports approaching retention limit
            approaching_retention_response = client.client.table(client.reports_table) \
                .select("id", count="exact") \
                .not_.is_("deleted_at", "null") \
                .lt("deleted_at", retention_cutoff.isoformat()) \
                .execute()
                
            stats = {
                "total_reports": total_response.count,
                "active_reports": active_response.count,
                "archived_reports": archived_response.count,
                "deleted_reports": deleted_response.count,
                "reports_approaching_retention": approaching_retention_response.count,
                "retention_policy": {
                    "retention_days": self.default_retention_days,
                    "archive_days": 60,
                    "cleanup_enabled": self.cleanup_enabled
                },
                "cutoff_dates": {
                    "retention_cutoff": retention_cutoff.isoformat(),
                    "archive_cutoff": archive_cutoff.isoformat()
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting retention stats: {str(e)}")
            raise
            
    def configure_retention_policy(
        self,
        retention_days: int = None,
        cleanup_enabled: bool = None
    ) -> Dict[str, Any]:
        """
        Configure retention policy settings.
        
        Args:
            retention_days: Number of days to retain reports
            cleanup_enabled: Whether to enable automatic cleanup
            
        Returns:
            Dict with updated configuration
        """
        try:
            if retention_days is not None:
                if retention_days < 1 or retention_days > 365:
                    raise ValueError("Retention days must be between 1 and 365")
                self.default_retention_days = retention_days
                
            if cleanup_enabled is not None:
                self.cleanup_enabled = cleanup_enabled
                
                # Restart scheduler with new settings
                if self.scheduler and hasattr(self.scheduler, 'running') and self.scheduler.running:
                    self.stop_scheduler()
                    
                if cleanup_enabled:
                    self.start_scheduler()
                    
            config = {
                "retention_days": self.default_retention_days,
                "cleanup_enabled": self.cleanup_enabled,
                "scheduler_running": False,  # Placeholder until scheduler is implemented
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Retention policy configured: {config}")
            return {
                "success": True,
                "configuration": config,
                "message": "Retention policy configuration updated"
            }
            
        except Exception as e:
            logger.error(f"Error configuring retention policy: {str(e)}")
            raise
            
    def force_cleanup(self, retention_days: int = None) -> Dict[str, Any]:
        """
        Force immediate cleanup of expired reports.
        
        Args:
            retention_days: Optional override for retention days
            
        Returns:
            Dict with cleanup results
        """
        try:
            days = retention_days or self.default_retention_days
            logger.info(f"Forcing immediate cleanup with {days} day retention")
            
            result = self.history_service.apply_retention_policy(retention_days=days)
            
            logger.info(f"Force cleanup completed: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"Force cleanup failed: {str(e)}")
            raise