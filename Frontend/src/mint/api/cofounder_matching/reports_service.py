import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from ..system.core.supabase_client import get_supabase_client
from .report_models import ReportReason, ReportStatus, ReportType

logger = logging.getLogger(__name__)


class ReportsService:
    """Service for managing profile and message reports."""

    def __init__(self):
        self.supabase = get_supabase_client(use_service_role=True).client

    async def create_profile_report(
        self,
        reporter_user_id: str,
        reported_profile_id: str,
        reason: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Create a report for a profile.

        Args:
            reporter_user_id: User ID of the person reporting
            reported_profile_id: Profile ID being reported
            reason: Reason for the report
            description: Optional additional context

        Returns:
            Created report data

        Raises:
            ValueError: If validation fails
        """
        # Validate that description is provided if reason is OTHER
        if reason == ReportReason.OTHER.value and not description:
            raise ValueError("Description is required when reason is OTHER")

        # Check if profile exists
        profile_result = (
            self.supabase.table("profiles")
            .select("id, user_id")
            .eq("id", reported_profile_id)
            .limit(1)
            .execute()
        )

        profile = profile_result.data[0] if profile_result.data else None

        if not profile:
            raise ValueError("Reported profile not found")

        # Prevent self-reporting
        if profile["user_id"] == reporter_user_id:
            raise ValueError("You cannot report your own profile")

        # Check for duplicate reports (same reporter, same profile, pending status)
        existing_result = (
            self.supabase.table("cofounder_reports")
            .select("id")
            .eq("reporter_user_id", reporter_user_id)
            .eq("reported_profile_id", reported_profile_id)
            .eq("status", ReportStatus.PENDING.value)
            .limit(1)
            .execute()
        )

        existing = existing_result.data[0] if existing_result.data else None

        if existing:
            raise ValueError("You have already reported this profile")

        # Create the report
        report_data = {
            "id": str(uuid4()),
            "report_type": ReportType.PROFILE.value,
            "reporter_user_id": reporter_user_id,
            "reported_profile_id": reported_profile_id,
            "reported_user_id": profile["user_id"],  # Store the user_id of the reported profile
            "reason": reason,
            "description": description,
            "status": ReportStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = (
            self.supabase.table("cofounder_reports")
            .insert(report_data)
            .execute()
        )

        return result.data[0] if result.data else None

    async def create_message_report(
        self,
        reporter_user_id: str,
        message_id: str,
        reason: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Create a report for a message.

        Args:
            reporter_user_id: User ID of the person reporting
            message_id: Message ID being reported
            reason: Reason for the report
            description: Optional additional context

        Returns:
            Created report data

        Raises:
            ValueError: If validation fails
        """
        # Validate that description is provided if reason is OTHER
        if reason == ReportReason.OTHER.value and not description:
            raise ValueError("Description is required when reason is OTHER")

        # Check if message exists and get sender info
        message_result = (
            self.supabase.table("messages")
            .select("id, sender_id, recipient_id")
            .eq("id", message_id)
            .limit(1)
            .execute()
        )

        message = message_result.data[0] if message_result.data else None

        if not message:
            raise ValueError("Message not found")

        # Verify the reporter has access to this message (is sender or recipient)
        if reporter_user_id not in [message["sender_id"], message["recipient_id"]]:
            raise ValueError("You do not have access to this message")

        # Prevent self-reporting (reporting your own message)
        if message["sender_id"] == reporter_user_id:
            raise ValueError("You cannot report your own message")

        # Determine the reported user (the sender of the message)
        reported_user_id = message["sender_id"]

        # Check for duplicate reports
        existing_result = (
            self.supabase.table("cofounder_reports")
            .select("id")
            .eq("reporter_user_id", reporter_user_id)
            .eq("reported_message_id", message_id)
            .eq("status", ReportStatus.PENDING.value)
            .limit(1)
            .execute()
        )

        existing = existing_result.data[0] if existing_result.data else None

        if existing:
            raise ValueError("You have already reported this message")

        # Create the report
        report_data = {
            "id": str(uuid4()),
            "report_type": ReportType.MESSAGE.value,
            "reporter_user_id": reporter_user_id,
            "reported_message_id": message_id,
            "reported_user_id": reported_user_id,  # Add the reported user ID
            "reason": reason,
            "description": description,
            "status": ReportStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = (
            self.supabase.table("cofounder_reports")
            .insert(report_data)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_reports(
        self,
        status: Optional[str] = None,
        report_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[int, List[Dict]]:
        """
        List reports with optional filters.

        Args:
            status: Filter by status (PENDING, REVIEWED, ACTIONED, NO_ACTION)
            report_type: Filter by type (PROFILE, MESSAGE)
            page: Page number
            page_size: Number of items per page

        Returns:
            Tuple of (total_count, reports_list)
        """
        query = self.supabase.table("cofounder_reports").select("*", count="exact")

        # Apply filters
        if status:
            query = query.eq("status", status)
        if report_type:
            query = query.eq("report_type", report_type)

        # Order by creation date (newest first)
        query = query.order("created_at", desc=True)

        # Pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = query.execute()

        total = result.count if hasattr(result, "count") else 0
        items = result.data if result.data else []

        return total, items

    async def get_reports_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[int, List[Dict]]:
        """
        Get all reports against a specific user (across all their profiles/messages).

        Args:
            user_id: User ID being reported
            status: Filter by status
            page: Page number
            page_size: Number of items per page

        Returns:
            Tuple of (total_count, reports_list)
        """
        query = self.supabase.table("cofounder_reports").select("*", count="exact")

        query = query.eq("reported_user_id", user_id)

        if status:
            query = query.eq("status", status)

        # Order by creation date (newest first)
        query = query.order("created_at", desc=True)

        # Pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = query.execute()

        total = result.count if hasattr(result, "count") else 0
        items = result.data if result.data else []

        return total, items

    async def get_reports_by_profile(
        self,
        profile_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[int, List[Dict]]:
        """
        Get all reports against a specific profile.

        Args:
            profile_id: Profile ID being reported
            status: Filter by status
            page: Page number
            page_size: Number of items per page

        Returns:
            Tuple of (total_count, reports_list)
        """
        query = self.supabase.table("cofounder_reports").select("*", count="exact")

        query = query.eq("reported_profile_id", profile_id)

        if status:
            query = query.eq("status", status)

        # Order by creation date (newest first)
        query = query.order("created_at", desc=True)

        # Pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = query.execute()

        total = result.count if hasattr(result, "count") else 0
        items = result.data if result.data else []

        return total, items

    async def get_report(self, report_id: str) -> Optional[Dict]:
        """
        Get a specific report by ID.

        Args:
            report_id: ID of the report

        Returns:
            Report data or None
        """
        result = (
            self.supabase.table("cofounder_reports")
            .select("*")
            .eq("id", report_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def resolve_report(
        self,
        report_id: str,
        admin_user_id: str,
        status: str,
        admin_notes: Optional[str] = None,
        action_taken: Optional[str] = None,
    ) -> Dict:
        """
        Resolve a report (admin only).

        Args:
            report_id: ID of the report to resolve
            admin_user_id: User ID of the admin resolving the report
            status: New status (REVIEWED, ACTIONED, NO_ACTION)
            admin_notes: Optional admin notes
            action_taken: Optional description of action taken

        Returns:
            Updated report data

        Raises:
            ValueError: If report not found or already resolved
        """
        # Get the report
        report = await self.get_report(report_id)
        if not report:
            raise ValueError("Report not found")

        # Check if already resolved
        if report["status"] != ReportStatus.PENDING.value:
            raise ValueError("Report has already been resolved")

        # Update the report
        update_data = {
            "status": status,
            "admin_notes": admin_notes,
            "action_taken": action_taken,
            "resolved_by": admin_user_id,
            "resolved_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = (
            self.supabase.table("cofounder_reports")
            .update(update_data)
            .eq("id", report_id)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_report_stats(self) -> Dict:
        """
        Get statistics about reports.

        Returns:
            Dictionary with report statistics
        """
        # Get total reports
        total_result = (
            self.supabase.table("cofounder_reports")
            .select("id", count="exact")
            .execute()
        )
        total_reports = total_result.count if hasattr(total_result, "count") else 0

        # Get counts by status
        pending_result = (
            self.supabase.table("cofounder_reports")
            .select("id", count="exact")
            .eq("status", ReportStatus.PENDING.value)
            .execute()
        )
        pending_reports = pending_result.count if hasattr(pending_result, "count") else 0

        reviewed_result = (
            self.supabase.table("cofounder_reports")
            .select("id", count="exact")
            .eq("status", ReportStatus.REVIEWED.value)
            .execute()
        )
        reviewed_reports = reviewed_result.count if hasattr(reviewed_result, "count") else 0

        actioned_result = (
            self.supabase.table("cofounder_reports")
            .select("id", count="exact")
            .eq("status", ReportStatus.ACTIONED.value)
            .execute()
        )
        actioned_reports = actioned_result.count if hasattr(actioned_result, "count") else 0

        no_action_result = (
            self.supabase.table("cofounder_reports")
            .select("id", count="exact")
            .eq("status", ReportStatus.NO_ACTION.value)
            .execute()
        )
        no_action_reports = no_action_result.count if hasattr(no_action_result, "count") else 0

        # Get counts by reason
        all_reports = (
            self.supabase.table("cofounder_reports")
            .select("reason")
            .execute()
            .data
        )

        reports_by_reason = {}
        for report in all_reports:
            reason = report["reason"]
            reports_by_reason[reason] = reports_by_reason.get(reason, 0) + 1

        return {
            "total_reports": total_reports,
            "pending_reports": pending_reports,
            "reviewed_reports": reviewed_reports,
            "actioned_reports": actioned_reports,
            "no_action_reports": no_action_reports,
            "reports_by_reason": reports_by_reason,
        }
