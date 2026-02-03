import os
import logging
from datetime import datetime

from ..system.core.supabase_client import get_supabase_client
from .matching_service import MatchingService
from ..services.communication.email_service import email_service

logger = logging.getLogger(__name__)


class AdminService:

    def __init__(self, use_service_role: bool = True):
        """Initialize tenant service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role
        self.matching_service = MatchingService(use_service_role=use_service_role)
        self.matches_url = os.getenv("FRONTEND_MATCHES_URL", "https://yubanow.com/workspace/cofounder/your-matches")

    def list_submissions(self, status: str = "submitted", limit: int = 50):
        rows = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("status", status)
            .order("submitted_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        # Enrich languages for each submission
        for row in rows:
            if row.get("preferred_languages"):
                try:
                    enriched = self.supabase.rpc(
                        "enrich_language_preferences",
                        {"prefs": row["preferred_languages"]}
                    ).execute()
                    row["preferred_languages"] = enriched.data if enriched.data else []
                except Exception as e:
                    logger.warning(f"Failed to enrich languages for version {row.get('id')}: {str(e)}")
        return rows

    def approve(self, version_id: str):
        # Update profile version status
        self.supabase.table("profile_versions").update(
            {"status": "approved", "reviewed_at": datetime.utcnow().isoformat()}
        ).eq("id", version_id).execute()

        # Activate the profile version (adds to approved_candidates)
        self.supabase.rpc(
            "activate_profile_version", {"p_version_id": version_id}
        ).execute()

        # Get the profile_id and user info for this version
        version_data = (
            self.supabase.table("profile_versions")
            .select("profile_id, first_name, last_name, email")
            .eq("id", version_id)
            .limit(1)
            .execute()
        )

        if not version_data.data:
            return {"ok": True, "matches_created": 0}

        profile_id = version_data.data[0].get("profile_id")
        approved_user_first_name = version_data.data[0].get("first_name")
        approved_user_last_name = version_data.data[0].get("last_name")
        approved_user_full_name = f"{approved_user_first_name} {approved_user_last_name}"
        approved_user_email = version_data.data[0].get("email")

        # Always send approval email
        if approved_user_email and approved_user_first_name:
            email_service.send_cofounder_profile_approved_email(
                to_email=approved_user_email,
                user_name=approved_user_first_name,
                matches_url=self.matches_url
            )

        # Run automatic matching for the newly approved profile
        if profile_id:
            matches = self.matching_service.create_matches_for_profile(profile_id)
            match_count = len(matches) if matches else 0

            # Send match notification emails if matches were created
            if match_count > 0:
                self._send_match_notification_emails(
                    profile_id=profile_id,
                    approved_user_first_name=approved_user_first_name,
                    approved_user_full_name=approved_user_full_name,
                    approved_user_email=approved_user_email,
                    matches=matches
                )

            return {"ok": True, "matches_created": match_count}

        return {"ok": True, "matches_created": 0}

    def _send_match_notification_emails(
        self,
        profile_id: str,
        approved_user_first_name: str,
        approved_user_full_name: str,
        approved_user_email: str,
        matches: list
    ):
        """Send email notifications to newly approved user and all matched users"""
        try:
            # Get matched profile IDs
            matched_profile_ids = [m["matched_profile_id"] for m in matches]

            if not matched_profile_ids:
                return

            # Get matched users' info from profiles
            matched_profiles = (
                self.supabase.table("profiles")
                .select("id, user_id, last_approved_version_id")
                .in_("id", matched_profile_ids)
                .execute()
                .data
            )

            # Get version IDs
            version_ids = [p["last_approved_version_id"] for p in matched_profiles if p.get("last_approved_version_id")]

            if not version_ids:
                return

            # Get user details from profile_versions
            versions = (
                self.supabase.table("profile_versions")
                .select("id, first_name, last_name, email")
                .in_("id", version_ids)
                .execute()
                .data
            )

            # Create a lookup dict: version_id -> user info
            version_lookup = {v["id"]: v for v in versions}

            # Collect matched user names for the approved user's email
            matched_full_names = []

            # Send individual emails to each matched user
            for profile in matched_profiles:
                version_id = profile.get("last_approved_version_id")
                if version_id and version_id in version_lookup:
                    user_info = version_lookup[version_id]
                    matched_user_first_name = user_info.get("first_name")
                    matched_user_last_name = user_info.get("last_name")
                    matched_user_full_name = f"{matched_user_first_name} {matched_user_last_name}"
                    matched_user_email = user_info.get("email")

                    matched_full_names.append(matched_user_full_name)

                    # Send email to matched user
                    if matched_user_email and matched_user_first_name:
                        email_service.send_new_cofounder_match_email(
                            to_email=matched_user_email,
                            user_name=matched_user_first_name,
                            matched_user_name=approved_user_full_name,
                            matches_url=self.matches_url
                        )

            # Send email to newly approved user with all their matches
            if approved_user_email and matched_full_names:
                email_service.send_cofounder_matches_email(
                    to_email=approved_user_email,
                    user_name=approved_user_first_name,
                    match_count=len(matched_full_names),
                    matched_names=matched_full_names,
                    matches_url=self.matches_url
                )

        except Exception as e:
            # Log error but don't fail the approval process
            print(f"Error sending match notification emails: {str(e)}")

    def reject(self, version_id: str, reason: str):
        # Update profile version status
        self.supabase.table("profile_versions").update(
            {
                "status": "rejected",
                "review_reason": reason,
                "reviewed_at": datetime.utcnow().isoformat(),
            }
        ).eq("id", version_id).execute()

        # Get user info for this version to send rejection email
        version_data = (
            self.supabase.table("profile_versions")
            .select("first_name, email")
            .eq("id", version_id)
            .limit(1)
            .execute()
        )

        if version_data.data:
            user_first_name = version_data.data[0].get("first_name")
            user_email = version_data.data[0].get("email")

            # Send rejection email with reason
            if user_email and user_first_name and reason:
                email_service.send_cofounder_profile_rejected_email(
                    to_email=user_email,
                    user_name=user_first_name,
                    rejection_reason=reason
                )

        return {"ok": True}
