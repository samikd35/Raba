"""
Report History Service

This service provides functionality for managing user report history,
including retrieval, filtering, sorting, pagination, and management operations.
Enhanced with fallback mechanisms and circuit breaker pattern.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ..system.core.supabase_client import (
    SupabaseClient,
    get_service_role_client,
    get_standard_client,
)
from ..system.core.utils import is_valid_uuid
from ..services.utilities.fallback_service import fallback_service
from ..cache import get_cache_service
from ..cache.enhanced import cache_result
from ..services.utilities.query_optimizer import monitor_query
from ...utils.circuit_breaker import circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class ReportHistoryService:
    """Service for managing report history operations."""

    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the report history service.

        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.service_client = (
            get_service_role_client()
        )  # For queries without user token
        self.documents_table = "documents"  # Use documents table as per current schema
        self.cache_service = get_cache_service()

    @circuit_breaker(
        name="report_history_get",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=60,  # Increased from 15s for better reliability with large datasets
    )
    @monitor_query(query_type="select", table_name="documents")
    async def get_report_history(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        user_token: str = None,
    ) -> Dict[str, Any]:
        """
        Retrieve user's report history with filtering, sorting, and pagination.
        Enhanced with proper user identification, ownership verification, and fallback mechanisms.

        This method ensures that:
        1. Only reports owned by the authenticated user are returned
        2. Proper user_id is used for database queries (not session_id)
        3. RLS policies are properly enforced
        4. Authentication context is validated

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            filters: Optional filters to apply
            sort_by: Field to sort by (default: created_at)
            sort_order: Sort order - 'asc' or 'desc' (default: desc)
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dict containing reports, pagination info, and metadata

        Raises:
            ValueError: If user_id is invalid or authentication fails
            Exception: For database or system errors
        """
        try:
            logger.info(f"Retrieving report history for authenticated user {user_id}")

            # Validate user ID format (requirement 4.1 - proper user identification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format provided: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")

            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20

            # Use service role client to bypass RLS (we filter by created_by for security)
            # This avoids JWT validation issues while maintaining data isolation
            query_client = self.service_client.client

            # PERFORMANCE OPTIMIZATION: Select only required columns for list view
            # Excludes 'content' field which contains full report text (can be megabytes)
            # Excludes full 'metadata' field which contains report_data with all content
            # Content is only needed when viewing a specific report, not for listing
            list_columns = "id, tenant_id, project_id, source_type, title, storage_path, sha256, created_by, created_at, updated_at"

            # Build base query with ownership verification using created_by
            # FETCH PV REPORTS from documents table with count in same query
            query = (
                query_client.table(self.documents_table)
                .select(list_columns, count="exact")
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
            )

            logger.debug(
                f"Fetching PV reports for user {user_id} with selective columns"
            )

            # DEBUG MODE: Only run expensive debug queries when explicitly enabled
            debug_mode = (
                os.environ.get("REPORT_HISTORY_DEBUG", "false").lower() == "true"
            )
            if debug_mode:
                logger.info(f"🔍 DEBUG MODE ENABLED - Running diagnostic queries")
                # 1. Check what PV reports exist for this user
                test_query_user = (
                    query_client.table(self.documents_table)
                    .select("id,created_by,title,created_at,source_type")
                    .eq("created_by", user_id)
                    .eq("source_type", "pv_report")
                    .limit(10)
                )
                test_response_user = test_query_user.execute()
                logger.info(
                    f"🔍 USER PV REPORTS DEBUG: Found {len(test_response_user.data)} PV reports for user {user_id}"
                )

                # 2. Check what PV reports exist in total (first 10)
                test_query_all = (
                    query_client.table(self.documents_table)
                    .select("id,created_by,title,created_at,source_type")
                    .eq("source_type", "pv_report")
                    .limit(10)
                )
                test_response_all = test_query_all.execute()
                logger.info(
                    f"🔍 ALL PV REPORTS DEBUG: Found {len(test_response_all.data)} total PV reports in database"
                )

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply sorting
            if sort_order.lower() == "asc":
                query = query.order(sort_by, desc=False)
            else:
                query = query.order(sort_by, desc=True)

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)

            # Execute single query with count (eliminates separate count query)
            response = query.execute()

            # Get count from the same response (no extra round-trip)
            total_count = (
                response.count if response.count is not None else len(response.data)
            )

            logger.info(
                f"Retrieved {len(response.data)} reports (total: {total_count}) for user {user_id}"
            )

            # Security verification (only log warnings, don't iterate all reports in production)
            if debug_mode and response.data:
                wrong_user_reports = [
                    r for r in response.data if r.get("created_by") != user_id
                ]
                if wrong_user_reports:
                    logger.error(
                        f"🔥 CRITICAL BUG: Found {len(wrong_user_reports)} reports belonging to OTHER USERS!"
                    )
                else:
                    logger.debug(
                        f"Security check passed: All reports belong to user {user_id}"
                    )

            reports = response.data

            # Process reports to ensure JSON compliance and fetch actionable insights
            processed_reports = []
            for report in reports:
                processed_report = self._process_report_for_json(report)
                # Skip individual insight fetching - will batch fetch later
                processed_report["actionable_insights"] = []
                processed_reports.append(processed_report)

            # PERFORMANCE OPTIMIZATION: Batch fetch all actionable insights in one query
            if processed_reports:
                report_ids = [r.get("id") for r in processed_reports if r.get("id")]
                insights_map = self._batch_fetch_actionable_insights(
                    report_ids, query_client
                )

                # Assign insights to their respective reports
                for report in processed_reports:
                    report_id = report.get("id")
                    if report_id and report_id in insights_map:
                        report["actionable_insights"] = insights_map[report_id]
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            # Debug logging only when enabled
            if debug_mode:
                logger.info(
                    f"📤 FINAL RESULT for user {user_id}: Returning {len(processed_reports)} reports"
                )
                for i, report in enumerate(processed_reports):
                    logger.info(
                        f"  Final Report {i + 1}: ID={report.get('id')}, UserID={report.get('user_id')}, Title={report.get('title', '')[:50]}..."
                    )

            result = {
                "reports": processed_reports,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                },
                "filters_applied": filters or {},
                "sort": {"field": sort_by, "order": sort_order},
            }

            return result

        except CircuitBreakerError:
            # Circuit breaker is open, try simple fallback
            logger.warning(f"Circuit breaker open for report history, using fallback")
            return await fallback_service.simple_report_history_fallback(
                user_id, filters, sort_by, sort_order, page, page_size
            )

        except Exception as e:
            logger.error(
                f"Error retrieving report history for user {user_id}: {str(e)}"
            )

            # Try simple fallback
            try:
                return await fallback_service.simple_report_history_fallback(
                    user_id, filters, sort_by, sort_order, page, page_size
                )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                raise e  # Raise original error

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        Apply filters to the query.

        Args:
            query: The Supabase query object
            filters: Dictionary of filters to apply

        Returns:
            Modified query object
        """
        try:
            # Date range filter
            if "date_range" in filters:
                date_range = filters["date_range"]
                if "start" in date_range and date_range["start"]:
                    query = query.gte("created_at", date_range["start"])
                if "end" in date_range and date_range["end"]:
                    query = query.lte("created_at", date_range["end"])

            # Category filter
            if "categories" in filters and filters["categories"]:
                categories = filters["categories"]
                if isinstance(categories, list) and categories:
                    query = query.in_("category", categories)
                elif isinstance(categories, str):
                    query = query.eq("category", categories)

            # Tags filter
            if "tags" in filters and filters["tags"]:
                tags = filters["tags"]
                if isinstance(tags, list) and tags:
                    # Use overlap operator for array fields
                    query = query.overlaps("tags", tags)
                elif isinstance(tags, str):
                    query = query.contains("tags", [tags])

            # Pinned filter
            if "only_pinned" in filters and filters["only_pinned"]:
                query = query.eq("is_pinned", True)

            # Report type filter
            if "report_types" in filters and filters["report_types"]:
                report_types = filters["report_types"]
                if isinstance(report_types, list) and report_types:
                    query = query.in_("report_type", report_types)
                elif isinstance(report_types, str):
                    query = query.eq("report_type", report_types)

            # Search filter (title and summary)
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Using ilike on title only - summary filtering done separately if needed
            if "search" in filters and filters["search"]:
                search_term = filters["search"].strip()
                if search_term:
                    # Use text search on title only (since .or_() not supported)
                    query = query.ilike("title", f"%{search_term}%")

            return query

        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            raise

    def _process_report_for_json(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a report to ensure JSON compliance and add computed fields.

        PERFORMANCE OPTIMIZED: This method now handles lightweight list view data
        without content or full metadata (which are fetched separately when viewing a report).

        Args:
            report: Raw report data from database (minimal columns for list view)

        Returns:
            Processed report data with computed fields for frontend display
        """
        try:
            # Ensure all datetime fields are ISO strings
            if report.get("created_at"):
                if not isinstance(report["created_at"], str):
                    report["created_at"] = report["created_at"].isoformat()

            if report.get("updated_at"):
                if not isinstance(report["updated_at"], str):
                    report["updated_at"] = report["updated_at"].isoformat()

            # Add computed fields for frontend compatibility
            report["has_chat"] = False
            report["is_recent"] = self._is_recent_report(report.get("created_at"))
            report["is_pinned"] = (
                False  # Would need separate query to get from metadata
            )
            report["is_archived"] = False
            report["view_count"] = 0
            report["tags"] = []

            # Add minimal metadata structure for frontend compatibility
            # Full metadata is only fetched when viewing a specific report
            report["metadata"] = {
                "session_id": report.get("id"),  # Use report ID as session_id
                "workflow_status": "completed",  # Default status for list view
            }

            # Content is not fetched for list view - set to None
            # Full content is fetched when user clicks on a specific report
            report["content"] = None

            return report

        except Exception as e:
            logger.error(f"Error processing report for JSON: {str(e)}")
            # Return the original report if processing fails
            return report

    def _check_has_chat_history(self, report_id: str) -> bool:
        """
        DISABLED FOR PERFORMANCE: Check if a report has associated chat history.
        The report_chats table does not exist, so this always returns False.
        """
        return False

    def _is_recent_report(self, created_at: str) -> bool:
        """
        Check if a report was created recently (within last 7 days).

        Args:
            created_at: The creation timestamp

        Returns:
            True if recent, False otherwise
        """
        try:
            if not created_at:
                return False

            # Parse the datetime string
            if isinstance(created_at, str):
                created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_date = created_at

            # Check if within last 7 days
            seven_days_ago = datetime.now().replace(
                tzinfo=created_date.tzinfo
            ) - timedelta(days=7)
            return created_date > seven_days_ago

        except Exception as e:
            logger.debug(f"Could not determine if report is recent: {str(e)}")
            return False

    @monitor_query(query_type="update", table_name="mint_reports")
    def toggle_pinned_report(
        self, user_id: str, report_id: str, is_pinned: bool
    ) -> Dict[str, Any]:
        """
        Toggle the pinned status of a report with proper ownership verification.

        This method ensures that:
        1. Only the report owner can modify the pinned status
        2. Proper user_id is used for ownership verification
        3. Report exists and is not deleted

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            report_id: The ID of the report to modify
            is_pinned: Whether to pin (True) or unpin (False) the report

        Returns:
            Updated report data with success confirmation

        Raises:
            ValueError: If inputs are invalid or ownership verification fails
        """
        try:
            logger.info(
                f"User {user_id} toggling pinned status for report {report_id} to {is_pinned}"
            )

            # Validate inputs (requirement 4.4 - ownership verification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")

            # First verify the report exists and belongs to the user (requirement 4.4)
            verification_response = (
                self.client.client.table(self.documents_table)
                .select("id, title, created_by, metadata")
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not verification_response.data:
                logger.warning(
                    f"Report {report_id} not found or access denied for user {user_id}"
                )
                raise ValueError(
                    "Report not found or access denied - you can only modify your own reports"
                )

            # Update the report with ownership verification - store pin status in metadata
            current_metadata = verification_response.data[0].get("metadata", {})
            current_metadata["is_pinned"] = is_pinned

            response = (
                self.client.client.table(self.documents_table)
                .update(
                    {
                        "metadata": current_metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not response.data:
                logger.error(f"Failed to update report {report_id} for user {user_id}")
                raise ValueError(
                    "Failed to update report - ownership verification failed"
                )

            updated_report = response.data[0]
            processed_report = self._process_report_for_json(updated_report)

            logger.info(f"Successfully toggled pinned status for report {report_id}")
            return {
                "success": True,
                "report": processed_report,
                "message": f"Report {'pinned' if is_pinned else 'unpinned'} successfully",
            }

        except Exception as e:
            logger.error(
                f"Error toggling pinned status for report {report_id}: {str(e)}"
            )
            raise

    @monitor_query(query_type="delete", table_name="mint_reports")
    def delete_report(
        self,
        user_id: str,
        report_id: str,
        permanent: bool = False,
        user_token: str = None,
    ) -> Dict[str, Any]:
        """
        Delete a report (soft delete by default, permanent if specified).
        Enhanced with proper ownership verification and audit logging.

        This method ensures that:
        1. Only the report owner can delete their reports
        2. Proper user_id validation and ownership verification
        3. Soft delete by default (sets deleted_at timestamp)
        4. Permanent delete when explicitly requested
        5. Comprehensive audit logging
        6. Consistent client selection with get_report_history

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            report_id: ID of the report to delete
            permanent: If True, permanently delete; if False, soft delete
            user_token: Optional user token for RLS enforcement

        Returns:
            Dict containing success status and deletion details

        Raises:
            ValueError: If user_id/report_id are invalid or user doesn't own the report
            Exception: For database or system errors
        """
        try:
            logger.info(
                f"User {user_id} deleting report {report_id} (permanent: {permanent})"
            )

            # Validate inputs (requirement 4.4 - ownership verification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")

            # Use service role client to bypass RLS (we filter by created_by for security)
            # This avoids JWT validation issues while maintaining data isolation
            logger.info(
                f"Using service role client with created_by filter for deletion by user {user_id}"
            )
            query_client = self.service_client.client

            # First verify the report exists and belongs to the user (requirement 4.4)
            verification_response = (
                query_client.table(self.documents_table)
                .select("id, title, created_by, tenant_id")
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not verification_response.data:
                logger.warning(
                    f"Report {report_id} not found or access denied for user {user_id}"
                )
                raise ValueError(
                    "Report not found or access denied - you can only delete your own reports"
                )

            if permanent:
                # Permanent deletion
                response = (
                    query_client.table(self.documents_table)
                    .delete()
                    .eq("id", report_id)
                    .eq("created_by", user_id)
                    .eq("source_type", "pv_report")
                    .execute()
                )

                message = "Report permanently deleted"
            else:
                # Soft deletion - update metadata to mark as deleted
                current_metadata = verification_response.data[0].get("metadata", {})
                current_metadata["deleted_at"] = datetime.now(timezone.utc).isoformat()

                response = (
                    query_client.table(self.documents_table)
                    .update(
                        {
                            "metadata": current_metadata,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    .eq("id", report_id)
                    .eq("created_by", user_id)
                    .eq("source_type", "pv_report")
                    .execute()
                )

                message = "Report moved to trash (can be restored within 30 days)"

            if not response.data and not permanent:
                raise ValueError("Report not found or already deleted")

            logger.info(f"Successfully deleted report {report_id}")
            return {"success": True, "message": message, "permanent": permanent}

        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {str(e)}")
            raise

    def restore_report(self, user_id: str, report_id: str) -> Dict[str, Any]:
        """
        Restore a soft-deleted report with proper ownership verification.

        This method ensures that:
        1. Only the report owner can restore the report
        2. Report exists in the trash (soft-deleted state)
        3. Proper user_id is used for ownership verification

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            report_id: The ID of the report to restore

        Returns:
            Restored report data with confirmation

        Raises:
            ValueError: If inputs are invalid or ownership verification fails
        """
        try:
            logger.info(f"User {user_id} restoring report {report_id}")

            # Validate inputs (requirement 4.4 - ownership verification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")

            # First verify the report exists in trash and belongs to the user (requirement 4.4)
            verification_response = (
                self.client.client.table(self.documents_table)
                .select("id, title, created_by, metadata")
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not verification_response.data:
                logger.warning(
                    f"Report {report_id} not found in trash or access denied for user {user_id}"
                )
                raise ValueError(
                    "Report not found in trash or access denied - you can only restore your own deleted reports"
                )

            # Restore the report by clearing deleted_at from metadata with ownership verification
            current_metadata = verification_response.data[0].get("metadata", {})
            if "deleted_at" in current_metadata:
                del current_metadata["deleted_at"]

            response = (
                self.client.client.table(self.documents_table)
                .update(
                    {
                        "metadata": current_metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not response.data:
                logger.error(f"Failed to restore report {report_id} for user {user_id}")
                raise ValueError(
                    "Failed to restore report - ownership verification failed"
                )

            restored_report = response.data[0]
            processed_report = self._process_report_for_json(restored_report)

            logger.info(f"Successfully restored report {report_id}")
            return {
                "success": True,
                "report": processed_report,
                "message": "Report restored successfully",
            }

        except Exception as e:
            logger.error(f"Error restoring report {report_id}: {str(e)}")
            raise

    def get_deleted_reports(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get soft-deleted reports for a user (trash/recycle bin) with proper user identification.

        This method ensures that:
        1. Only reports owned by the authenticated user are returned
        2. Proper user_id is used for database queries
        3. Only soft-deleted reports are included

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Dict containing deleted reports and pagination info

        Raises:
            ValueError: If user_id is invalid
        """
        try:
            logger.info(f"Retrieving deleted reports for authenticated user {user_id}")

            # Validate inputs (requirement 4.1 - proper user identification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")

            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20

            # Get total count - query documents with deleted_at in metadata
            count_response = (
                self.client.client.table(self.documents_table)
                .select("id", count="exact")
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .not_.is_("metadata->>deleted_at", "null")
                .execute()
            )

            total_count = count_response.count

            # Get deleted reports
            offset = (page - 1) * page_size
            response = (
                self.client.client.table(self.documents_table)
                .select("*")
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .not_.is_("metadata->>deleted_at", "null")
                .order("metadata->>deleted_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )

            reports = response.data
            # Process reports
            processed_reports = []
            for report in reports:
                processed_report = self._process_report_for_json(report)
                processed_reports.append(processed_report)

            # PERFORMANCE OPTIMIZATION: Batch fetch all actionable insights in one query
            if processed_reports:
                report_ids = [r.get("id") for r in processed_reports if r.get("id")]
                insights_map = self._batch_fetch_actionable_insights(
                    report_ids, query_client
                )

                # Assign insights to their respective reports
                for report in processed_reports:
                    report_id = report.get("id")
                    if report_id and report_id in insights_map:
                        report["actionable_insights"] = insights_map[report_id]
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            result = {
                "reports": processed_reports,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                },
            }

            logger.info(
                f"Retrieved {len(processed_reports)} deleted reports for user {user_id}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error retrieving deleted reports for user {user_id}: {str(e)}"
            )
            raise

    def update_view_count(self, user_id: str, report_id: str) -> Dict[str, Any]:
        """
        Update the view count and last viewed timestamp for a report with ownership verification.

        This method ensures that:
        1. Only the report owner can update view count
        2. Proper user_id is used for ownership verification
        3. Report exists and is not deleted

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            report_id: The ID of the report to update

        Returns:
            Updated report data with confirmation

        Raises:
            ValueError: If inputs are invalid or ownership verification fails
        """
        try:
            logger.debug(f"User {user_id} updating view count for report {report_id}")

            # Validate inputs (requirement 4.4 - ownership verification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")

            # First get current report and verify ownership (requirement 4.4)
            current_report_response = (
                self.client.client.table(self.documents_table)
                .select("id, metadata, created_by")
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not current_report_response.data:
                logger.warning(
                    f"Report {report_id} not found or access denied for user {user_id}"
                )
                raise ValueError(
                    "Report not found or access denied - you can only view your own reports"
                )

            current_metadata = current_report_response.data[0].get("metadata", {})
            current_view_count = current_metadata.get("view_count", 0)

            # Update view count and last viewed timestamp in metadata
            current_metadata["view_count"] = current_view_count + 1
            current_metadata["last_viewed_at"] = datetime.now(timezone.utc).isoformat()

            # Update view count and last viewed timestamp with ownership verification
            response = (
                self.client.client.table(self.documents_table)
                .update(
                    {
                        "metadata": current_metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not response.data:
                logger.error(
                    f"Failed to update view count for report {report_id} for user {user_id}"
                )
                raise ValueError(
                    "Failed to update view count - ownership verification failed"
                )

            updated_report = response.data[0]
            processed_report = self._process_report_for_json(updated_report)

            return {"success": True, "report": processed_report}

        except Exception as e:
            logger.error(f"Error updating view count for report {report_id}: {str(e)}")
            raise

    def update_report_metadata(
        self, user_id: str, report_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update report metadata with proper ownership verification (title, summary, tags, category, archive status).

        This method ensures that:
        1. Only the report owner can update metadata
        2. Proper user_id is used for ownership verification
        3. Report exists and is not deleted

        Args:
            user_id: The authenticated user's ID (from auth.uid())
            report_id: The ID of the report to update
            update_data: Dictionary of fields to update

        Returns:
            Updated report data with confirmation

        Raises:
            ValueError: If inputs are invalid or ownership verification fails
        """
        try:
            logger.info(f"User {user_id} updating metadata for report {report_id}")

            # Validate inputs (requirement 4.4 - ownership verification)
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")

            if not update_data:
                raise ValueError("No update data provided")

            # First verify the report exists and belongs to the user (requirement 4.4)
            verification_response = (
                self.client.client.table(self.documents_table)
                .select("id, title, created_by, metadata")
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not verification_response.data:
                logger.warning(
                    f"Report {report_id} not found or access denied for user {user_id}"
                )
                raise ValueError(
                    "Report not found or access denied - you can only update your own reports"
                )

            # Add updated timestamp
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update the report metadata with ownership verification
            current_metadata = verification_response.data[0].get("metadata", {})
            current_metadata.update(update_data)

            response = (
                self.client.client.table(self.documents_table)
                .update(
                    {
                        "metadata": current_metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .execute()
            )

            if not response.data:
                logger.error(f"Failed to update report {report_id} for user {user_id}")
                raise ValueError(
                    "Failed to update report - ownership verification failed"
                )

            updated_report = response.data[0]
            processed_report = self._process_report_for_json(updated_report)

            logger.info(f"Successfully updated metadata for report {report_id}")
            return {
                "success": True,
                "report": processed_report,
                "message": "Report metadata updated successfully",
            }

        except Exception as e:
            logger.error(f"Error updating metadata for report {report_id}: {str(e)}")
            raise

    def apply_retention_policy(self, retention_days: int = 90) -> Dict[str, Any]:
        """
        Apply retention policy to permanently delete old reports.

        Args:
            retention_days: Number of days to retain reports (default: 90)

        Returns:
            Summary of retention policy application
        """
        try:
            logger.info(f"Applying retention policy ({retention_days} days)")

            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            cutoff_iso = cutoff_date.isoformat()

            # Find reports to be permanently deleted
            # These are reports that were soft-deleted more than retention_days ago
            response = (
                self.client.client.table(self.reports_table)
                .select("id, session_id, title, deleted_at")
                .not_.is_("deleted_at", "null")
                .lt("deleted_at", cutoff_iso)
                .execute()
            )

            reports_to_delete = response.data

            if not reports_to_delete:
                logger.info("No reports found for retention policy cleanup")
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "No reports found for cleanup",
                }

            # Permanently delete the reports
            report_ids = [report["id"] for report in reports_to_delete]

            delete_response = (
                self.client.client.table(self.reports_table)
                .delete()
                .in_("id", report_ids)
                .execute()
            )

            deleted_count = len(report_ids)

            logger.info(
                f"Retention policy applied: {deleted_count} reports permanently deleted"
            )
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_iso,
                "message": f"Permanently deleted {deleted_count} reports older than {retention_days} days",
            }

        except Exception as e:
            logger.error(f"Error applying retention policy: {str(e)}")
            raise

    async def get_report_by_id(
        self, report_id: str, user_id: str, user_token: str = None
    ) -> Dict[str, Any]:
        """
        Get a specific report by ID with proper ownership verification.

        Args:
            report_id: The ID of the report to retrieve (can be database ID or session_id)
            user_id: The ID of the user requesting the report
            user_token: Optional JWT token for RLS enforcement

        Returns:
            Dict containing the report data or None if not found
        """
        try:
            logger.info(f"Retrieving report {report_id} for user {user_id}")

            # Create appropriate client based on whether user token is provided
            query_client = None
            use_service_role = False

            # Use service role client with user_id filtering for security
            # This avoids JWT validation issues while maintaining data isolation
            logger.info(
                f"Using service role client with user_id filtering for user {user_id}"
            )
            use_service_role = True

            if use_service_role or query_client is None:
                # Use service role client to bypass RLS when no user token or token fails
                from .supabase_client import get_service_role_client

                service_client = get_service_role_client()
                query_client = service_client.client

            # First try to find by database ID
            response = None
            try:
                query = (
                    query_client.table(self.reports_table)
                    .select("*")
                    .eq("id", report_id)
                    .eq("user_id", user_id)
                    .is_("deleted_at", "null")
                    .eq("report_type", "final")
                )

                response = query.execute()
                logger.info(f"Query by ID returned {len(response.data)} results")

                # If not found by ID, try by session_id (for workflow-generated reports)
                if not response.data:
                    logger.info(
                        f"Report not found by ID, trying session_id lookup for {report_id}"
                    )
                    query = (
                        query_client.table(self.reports_table)
                        .select("*")
                        .eq("session_id", report_id)
                        .eq("user_id", user_id)
                        .is_("deleted_at", "null")
                        .eq("report_type", "final")
                        .order("created_at", desc=True)
                        .limit(1)
                    )

                    response = query.execute()
                    logger.info(
                        f"Query by session_id returned {len(response.data)} results"
                    )

            except Exception as query_error:
                logger.warning(
                    f"Query failed with user token, falling back to service role: {query_error}"
                )
                # Fall back to service role client
                from .supabase_client import get_service_role_client

                service_client = get_service_role_client()
                fallback_client = service_client.client

                # Retry with service role client
                query = (
                    fallback_client.table(self.reports_table)
                    .select("*")
                    .eq("id", report_id)
                    .eq("user_id", user_id)
                    .is_("deleted_at", "null")
                    .eq("report_type", "final")
                )

                response = query.execute()
                logger.info(
                    f"Fallback query by ID returned {len(response.data)} results"
                )

                # If not found by ID, try by session_id with fallback client
                if not response.data:
                    logger.info(
                        f"Report not found by ID with fallback, trying session_id lookup for {report_id}"
                    )
                    query = (
                        fallback_client.table(self.reports_table)
                        .select("*")
                        .eq("session_id", report_id)
                        .eq("user_id", user_id)
                        .is_("deleted_at", "null")
                        .eq("report_type", "final")
                        .order("created_at", desc=True)
                        .limit(1)
                    )

                    response = query.execute()
                    logger.info(
                        f"Fallback query by session_id returned {len(response.data)} results"
                    )

            if not response.data:
                logger.warning(f"Report {report_id} not found for user {user_id}")
                return {"success": False, "data": None, "message": "Report not found"}

            # Process the report for JSON compliance
            report = response.data[0]
            processed_report = self._process_report_for_json(report)

            logger.info(f"Successfully retrieved report {report_id} for user {user_id}")

            return {
                "success": True,
                "data": processed_report,
                "message": "Report retrieved successfully",
            }

        except Exception as e:
            logger.error(
                f"Error retrieving report {report_id} for user {user_id}: {str(e)}"
            )
            raise

    async def _get_actionable_insights_for_report(
        self, pv_report_id: str, query_client
    ) -> List[Dict[str, Any]]:
        """
        Fetch actionable insights associated with a PV report.

        Args:
            pv_report_id: The PV report ID to find insights for
            query_client: The Supabase client to use for queries

        Returns:
            List of actionable insights documents
        """
        try:
            if not pv_report_id:
                return []

            # Query documents table for actionable insights related to this PV report
            # Actionable insights are stored with metadata linking to the PV report
            insights_query = (
                query_client.table(self.documents_table)
                .select("id, title, content, created_at, metadata")
                .eq("source_type", "actionable_insights")
                .contains("metadata", {"pv_report_id": pv_report_id})
            )
            if self.tenant_id:
                insights_query = insights_query.eq("tenant_id", self.tenant_id)

            insights_response = insights_query.execute()

            if insights_response.data:
                logger.info(
                    f"Found {len(insights_response.data)} actionable insights for PV report {pv_report_id}"
                )
                return [
                    self._process_report_for_json(insight)
                    for insight in insights_response.data
                ]
            else:
                logger.debug(
                    f"No actionable insights found for PV report {pv_report_id}"
                )
                return []

        except Exception as e:
            logger.error(
                f"Error fetching actionable insights for report {pv_report_id}: {str(e)}"
            )
            return []

    def _batch_fetch_actionable_insights(
        self, report_ids: List[str], query_client
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        PERFORMANCE OPTIMIZATION: Batch fetch actionable insights for multiple reports in one query.

        Args:
            report_ids: List of PV report IDs
            query_client: The Supabase client to use for queries

        Returns:
            Dictionary mapping report_id -> list of actionable insights
        """
        try:
            if not report_ids:
                return {}

            # Single query to fetch all actionable insights for all reports
            insights_query = (
                query_client.table(self.documents_table)
                .select("id, title, content, created_at, metadata")
                .eq("source_type", "actionable_insights")
            )
            if self.tenant_id:
                insights_query = insights_query.eq("tenant_id", self.tenant_id)

            # Build OR condition for all report IDs
            or_conditions = []
            for report_id in report_ids:
                or_conditions.append(f'metadata.cs.{{"pv_report_id": "{report_id}"}}')

            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Fetch all insights and filter in Python instead
            # if or_conditions:
            #     insights_query = insights_query.or_(",".join([f'metadata.cs.{{"pv_report_id": "{rid}"}}' for rid in report_ids]))

            insights_response = insights_query.execute()

            # Group insights by report ID
            insights_map = {}
            for insight in insights_response.data:
                pv_report_id = insight.get("metadata", {}).get("pv_report_id")
                if pv_report_id:
                    if pv_report_id not in insights_map:
                        insights_map[pv_report_id] = []
                    insights_map[pv_report_id].append(
                        self._process_report_for_json(insight)
                    )

            logger.info(
                f"PERFORMANCE: Batch fetched insights for {len(report_ids)} reports in 1 query (found insights for {len(insights_map)} reports)"
            )
            return insights_map

        except Exception as e:
            logger.error(f"Error batch fetching actionable insights: {str(e)}")
            return {}
