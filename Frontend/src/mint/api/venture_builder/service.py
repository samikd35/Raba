"""
Venture Builder business logic service layer.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from uuid import UUID

from fastapi import UploadFile
from itsdangerous import BadSignature, SignatureExpired

from src.mint.api.credit.service import CreditService
from src.mint.api.services.communication.email_service import email_service
from src.mint.utils.url_safe_serializer import serializer

from .data_access import VBDataAccess, get_vb_data_access
from .exceptions import (
    VBAccessDeniedError,
    VBAlreadyExistsError,
    VBDisputeAlreadyExistsError,
    VBDisputeNotEligibleError,
    VBInsufficientCreditsError,
    VBNotFoundError,
    VBProfileIncompleteError,
    VBStatusError,
    VBValidationError,
)
from .google_calendar_service import (
    GoogleCalendarService,
    GoogleCalendarError,
    GoogleCalendarAuthError,
    get_google_calendar_service,
)
from .storage_service import get_vb_storage_service
from .models import AvailabilitySlotCreate, AvailabilitySlotIdentifier, DisputeStatus, SessionStatus, VBStatus

logger = logging.getLogger(__name__)


class VBService:
    """Business logic service for Venture Builder operations"""

    def __init__(
        self,
        data_access: Optional[VBDataAccess] = None,
        credit_service: Optional[CreditService] = None,
    ):
        self.data_access = data_access or get_vb_data_access()
        self.credit_service = credit_service or CreditService()
        self.serializer = serializer  # Reuse existing serializer

    # =====================================================
    # EXPERTISE AREAS (Admin Only)
    # =====================================================

    def list_expertise_areas(self, active_only: bool = True) -> List[dict]:
        """Get all expertise areas (alias for consistency)"""
        return self.data_access.get_all_expertise_areas(active_only=active_only)

    def get_all_expertise_areas(self, active_only: bool = True) -> List[dict]:
        """Get all expertise areas"""
        return self.data_access.get_all_expertise_areas(active_only=active_only)

    def get_expertise_by_id(self, expertise_id: str) -> dict:
        """Get expertise area by ID"""
        expertise = self.data_access.get_expertise_by_id(expertise_id)
        if not expertise:
            raise VBNotFoundError(f"Expertise area {expertise_id} not found")
        return expertise

    def create_expertise_area(
        self, name: str, description: Optional[str], display_order: int
    ) -> dict:
        """Create new expertise area (Admin only)"""
        logger.info(f"Creating expertise area: {name}")
        return self.data_access.create_expertise_area(name, description, display_order)

    def update_expertise_area(
        self,
        expertise_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        display_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> dict:
        """Update expertise area (Admin only)"""
        logger.info(f"Updating expertise area {expertise_id}")

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if display_order is not None:
            update_data["display_order"] = display_order
        if is_active is not None:
            update_data["is_active"] = is_active

        return self.data_access.update_expertise_area(expertise_id, update_data)

    def activate_expertise_area(self, expertise_id: str) -> dict:
        """Activate expertise area (Admin only)"""
        return self.data_access.activate_expertise_area(expertise_id)

    def deactivate_expertise_area(self, expertise_id: str) -> dict:
        """Deactivate expertise area (Admin only)"""
        return self.data_access.deactivate_expertise_area(expertise_id)

    def delete_expertise_area(self, expertise_id: str) -> None:
        """Permanently delete expertise area (Admin only)"""
        return self.data_access.delete_expertise_area(expertise_id)

    # =====================================================
    # VB INVITATIONS
    # =====================================================

    def send_vb_invitation(
        self,
        email: str,
        invited_by_user_id: str,
        invited_by_email: str,
    ) -> dict:
        """
        Send VB invitation via email
        Returns success response with token
        """
        token = self.generate_vb_invitation(
            email=email,
            invited_by_user_id=invited_by_user_id,
            invited_by_email=invited_by_email,
        )
        return {
            "success": True,
            "message": f"Invitation sent to {email}",
            "token": token,
        }

    def validate_invitation_token(self, token: str) -> dict:
        """
        Validate VB invitation token
        Returns validation result
        """
        try:
            invite = self.verify_vb_invitation(token)
            return {
                "valid": True,
                "email": invite["email"],
                "error": None,
            }
        except ValueError as e:
            return {
                "valid": False,
                "email": None,
                "error": str(e),
            }

    def mark_invitation_accepted(self, token: str, accepted_by_user_id: str) -> dict:
        """Mark invitation as accepted"""
        try:
            invite = self.verify_vb_invitation(token)
            return self.update_invitation_status(
                invite["id"],
                status="accepted",
                accepted_at=datetime.now(timezone.utc).isoformat(),
                accepted_by=accepted_by_user_id,
            )
        except ValueError as e:
            raise VBValidationError(str(e))

    def record_vb_invitation(
        self,
        email: str,
        invited_by_user_id: str,
        invited_by_email: str,
    ) -> dict:
        """
        Record VB invitation in database
        Returns existing pending invitation if found, creates new one otherwise
        """
        now = datetime.now(timezone.utc).isoformat()

        # Check if pending invitation exists
        existing = (
            self.data_access.supabase.table("vb_invitations")
            .select("*")
            .eq("email", email)
            .in_("status", ["queued", "sent"])
            .limit(1)
            .execute()
        )

        if existing.data:
            # Update existing invitation
            invite = existing.data[0]
            update_data = {
                "invited_by_user_id": invited_by_user_id,
                "invited_by_email": invited_by_email,
                "status": "queued",
                "updated_at": now,
            }
            result = (
                self.data_access.supabase.table("vb_invitations")
                .update(update_data)
                .eq("id", invite["id"])
                .execute()
            )
            return result.data[0]
        else:
            # Create new invitation
            payload = {
                "email": email,
                "invited_by_user_id": invited_by_user_id,
                "invited_by_email": invited_by_email,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
            }
            result = (
                self.data_access.supabase.table("vb_invitations")
                .insert(payload)
                .execute()
            )
            return result.data[0]

    def generate_vb_invitation(
        self,
        email: str,
        invited_by_user_id: str,
        invited_by_email: str,
    ) -> str:
        """
        Generate VB invitation token and send email
        Returns the invitation token
        """
        logger.info(f"Generating VB invitation for {email}")

        # Record invitation in DB
        invite = self.record_vb_invitation(
            email=email,
            invited_by_user_id=invited_by_user_id,
            invited_by_email=invited_by_email,
        )
        try:
            logger.debug(
                "VB invitation recorded",
                extra={
                    "invite_id": invite.get("id"),
                    "status": invite.get("status"),
                    "email": email,
                },
            )
        except Exception:
            # Defensive: avoid breaking flow due to logging extra
            logger.debug("VB invitation recorded for %s", email)

        # Create signed token (expertise_ids NOT included - user provides them later)
        token_payload = {
            "invite_id": invite["id"],
            "email": email,
            "type": "vb_invitation",
        }
        token = self.serializer.dumps(token_payload)
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:8]
            logger.debug(
                "VB invitation token generated",
                extra={"invite_id": invite.get("id"), "token_hash": token_hash},
            )
        except Exception:
            pass

        # Build invitation link
        frontend_url = os.getenv("FRONTEND_URL", "")
        if not frontend_url:
            logger.warning(
                "FRONTEND_URL is empty; invite link will not be absolute",
                extra={"email": email, "invite_id": invite.get("id")},
            )
        invite_link = f"{frontend_url}/vb-onboarding?{urlencode({'token': token, 'email': email})}"
        try:
            logger.debug(
                "Prepared invite link",
                extra={
                    "invite_id": invite.get("id"),
                    "has_frontend_url": bool(frontend_url),
                    "link_length": len(invite_link),
                },
            )
        except Exception:
            pass

        # Send email
        # Trace email service configuration (without sensitive data)
        try:
            logger.debug(
                "Email service configuration status",
                extra={
                    "configured": email_service.is_configured(),
                    "smtp_server_set": bool(getattr(email_service, "smtp_server", None)),
                    "smtp_port": getattr(email_service, "smtp_port", None),
                    "email_from": getattr(email_service, "email_from", None),
                },
            )
        except Exception:
            pass

        email_sent = email_service.send_vb_invite_email(
            to_email=email,
            invite_link=invite_link,
        )

        # Update status to sent (or failed if email fails)
        if email_sent:
            self.update_invitation_status(
                invite["id"],
                status="sent",
                sent_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info("VB invitation email sent", extra={"email": email, "invite_id": invite.get("id")})
        else:
            self.update_invitation_status(
                invite["id"],
                status="failed",
                error="Failed to send invitation email",
            )
            logger.error(
                "VB invitation email failed to send",
                extra={"email": email, "invite_id": invite.get("id")},
            )
            from .exceptions import VBValidationError
            raise VBValidationError("Failed to send invitation email")

        logger.info(f"VB invitation sent to {email}")
        return token

    def verify_vb_invitation(self, token: str, max_age: int = 48 * 3600) -> dict:
        """
        Verify VB invitation token
        Returns invitation data if valid
        Raises ValueError if invalid/expired
        """
        try:
            # Decode token (48-hour expiration)
            data = self.serializer.loads(token, max_age=max_age)

            if data.get("type") != "vb_invitation":
                raise ValueError("Invalid invitation type")

        except SignatureExpired:
            raise ValueError("Invitation has expired (48 hours)")
        except BadSignature:
            raise ValueError("Invalid invitation token")

        # Verify invitation exists in DB and is still pending
        result = (
            self.data_access.supabase.table("vb_invitations")
            .select("*")
            .eq("id", data["invite_id"])
            .limit(1)
            .execute()
        )

        if not result.data:
            raise ValueError("Invitation not found")

        invite = result.data[0]

        if invite["status"] not in ["queued", "sent"]:
            raise ValueError("Invitation already used or invalid")

        return invite

    def update_invitation_status(
        self,
        invite_id: str,
        status: str,
        sent_at: Optional[str] = None,
        accepted_at: Optional[str] = None,
        accepted_by: Optional[str] = None,
        error: Optional[str] = None,
    ) -> dict:
        """Update invitation status"""
        update_data = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}

        if sent_at:
            update_data["sent_at"] = sent_at
        if accepted_at:
            update_data["accepted_at"] = accepted_at
        if accepted_by:
            update_data["accepted_by"] = accepted_by
        if error:
            update_data["error"] = error

        result = (
            self.data_access.supabase.table("vb_invitations")
            .update(update_data)
            .eq("id", invite_id)
            .execute()
        )

        if not result.data:
            raise VBNotFoundError(f"Invitation {invite_id} not found")

        return result.data[0]

    # =====================================================
    # VB PROFILE MANAGEMENT
    # =====================================================

    def get_vb_profile(self, vb_id: str) -> dict:
        """Get VB profile by ID"""
        vb = self.data_access.get_vb_by_id(vb_id)
        if not vb:
            raise VBNotFoundError(f"Venture Builder {vb_id} not found")
        return vb

    def get_vb_by_user_id(self, user_id: str) -> Optional[dict]:
        """Get VB profile by user_id (returns None if not found)"""
        return self.data_access.get_vb_by_user_id(user_id)

    def get_vb_profile_by_user_id(self, user_id: str) -> dict:
        """Get VB profile by user_id (raises exception if not found)"""
        vb = self.data_access.get_vb_by_user_id(user_id)
        if not vb:
            raise VBNotFoundError(f"Venture Builder profile not found for user {user_id}")
        return vb

    async def create_vb_profile(
        self,
        user_id: str,
        name: str,
        contact_email: str,
        main_expertise: str,
        short_intro: str,
        work_experience: List[dict],
        biography: str,
        linkedin_url: Optional[str],
        expertise_ids: List[str],
        other_expertise: Optional[List[str]] = None,
        profile_picture: Optional[UploadFile] = None,
    ) -> dict:
        """
        Create VB profile with optional profile picture upload.

        Args:
            user_id: User ID creating the profile
            name: Display name for the VB
            contact_email: Contact email
            main_expertise: Primary expertise summary
            short_intro: Short intro/summary for the VB
            work_experience: List of work experience entries
            biography: VB biography
            linkedin_url: LinkedIn profile URL
            expertise_ids: List of expertise area IDs
            other_expertise: List of custom expertise not in predefined list
            profile_picture: Optional profile picture file to upload

        Returns:
            Created VB profile
        """
        logger.info(f"Creating VB profile for user {user_id}")

        # Validate expertise areas
        if len(expertise_ids) > 5:
            raise VBValidationError("Maximum 5 expertise areas allowed")

        for exp_id in expertise_ids:
            exp = self.data_access.get_expertise_by_id(exp_id)
            if not exp or not exp.get("is_active"):
                raise VBValidationError(f"Invalid expertise area: {exp_id}")

        # Check if profile already exists
        existing_vb = self.data_access.get_vb_by_user_id(user_id)
        if existing_vb:
            raise VBValidationError("VB profile already exists for this user")

        contact_email_value = contact_email
        if not contact_email_value:
            raise VBValidationError("contact_email is required")
        if not name or not str(name).strip():
            raise VBValidationError("name is required")
        if not main_expertise or not str(main_expertise).strip():
            raise VBValidationError("main_expertise is required")
        if not short_intro or not str(short_intro).strip():
            raise VBValidationError("short_intro is required")

        # Handle profile picture upload
        profile_picture_url = None
        if profile_picture:
            storage_service = get_vb_storage_service()
            try:
                # Validate file type
                allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
                file_ext = os.path.splitext(profile_picture.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    raise VBValidationError(
                        f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
                    )

                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024  # 5MB
                contents = await profile_picture.read()
                if len(contents) > max_size:
                    raise VBValidationError("File size exceeds 5MB limit")

                # Upload to Supabase Storage
                profile_picture_url = storage_service.upload_profile_picture(
                    contents, profile_picture.filename, user_id
                )
                logger.info(f"Profile picture uploaded for user {user_id}: {profile_picture_url}")

            except VBValidationError:
                # Re-raise validation errors
                raise
            except Exception as e:
                logger.error(f"Failed to upload profile picture: {str(e)}")
                raise VBValidationError(f"Failed to upload profile picture: {str(e)}")

        # Create profile
        profile_data = {
            "name": name,
            "contact_email": contact_email_value,
            "main_expertise": main_expertise,
            "short_intro": short_intro,
            "profile_picture_url": profile_picture_url or "",
            "work_experience": work_experience,
            "biography": biography,
            "linkedin_url": linkedin_url,
            "other_expertise": other_expertise,
        }

        vb = self.data_access.create_vb_profile(user_id, profile_data)
        vb_id = vb["id"]

        # Process custom expertise areas if provided (bulk operation)
        custom_expertise_ids = []
        if other_expertise:
            logger.info(f"Bulk creating {len(other_expertise)} custom expertise areas for VB {vb_id}")
            custom_expertise_list = self.data_access.bulk_create_custom_expertise(other_expertise)
            custom_expertise_ids = [str(exp["id"]) for exp in custom_expertise_list]
            logger.info(f"Created/found {len(custom_expertise_ids)} custom expertise areas")

        # Combine predefined and custom expertise IDs
        all_expertise_ids = expertise_ids + custom_expertise_ids

        # Add expertise mapping
        if all_expertise_ids:
            self.data_access.add_vb_expertise(vb_id, all_expertise_ids)
            logger.info(f"Mapped {len(all_expertise_ids)} expertise areas to VB {vb_id} ({len(expertise_ids)} predefined, {len(custom_expertise_ids)} custom)")

        # Move to pending admin review
        vb = self.data_access.update_vb_status(vb_id, VBStatus.PENDING_ADMIN_REVIEW)

        logger.info(f"VB profile created for {user_id}, status: {vb['status']}")
        return self.get_vb_profile(vb_id)

    async def update_vb_profile(
        self,
        vb_id: str,
        user_id: str,
        name: Optional[str] = None,
        contact_email: Optional[str] = None,
        main_expertise: Optional[str] = None,
        short_intro: Optional[str] = None,
        work_experience: Optional[List[dict]] = None,
        biography: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        expertise_ids: Optional[List[str]] = None,
        other_expertise: Optional[List[str]] = None,
        profile_picture: Optional[UploadFile] = None,
    ) -> dict:
        """
        Update VB profile with optional profile picture upload and custom expertise.

        Args:
            vb_id: VB profile ID to update
            user_id: User ID for file organization
            name: Optional display name
            contact_email: Optional contact email
            main_expertise: Optional primary expertise summary
            short_intro: Optional short intro/summary
            work_experience: Optional work experience entries
            biography: Optional biography
            linkedin_url: Optional LinkedIn URL
            expertise_ids: Optional expertise area IDs
            other_expertise: Optional custom expertise names to create
            profile_picture: Optional new profile picture file to upload

        Returns:
            Updated VB profile
        """
        logger.info(f"Updating VB profile {vb_id}")

        # Validate VB exists
        vb = self.get_vb_profile(vb_id)

        # Validate expertise areas if provided
        if expertise_ids is not None:
            if len(expertise_ids) > 5:
                raise VBValidationError("Maximum 5 expertise areas allowed")

            for exp_id in expertise_ids:
                exp = self.data_access.get_expertise_by_id(exp_id)
                if not exp or not exp.get("is_active"):
                    raise VBValidationError(f"Invalid expertise area: {exp_id}")

        # Handle profile picture upload
        if profile_picture:
            storage_service = get_vb_storage_service()
            try:
                # Validate file type
                allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
                file_ext = os.path.splitext(profile_picture.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    raise VBValidationError(
                        f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
                    )

                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024  # 5MB
                contents = await profile_picture.read()
                if len(contents) > max_size:
                    raise VBValidationError("File size exceeds 5MB limit")

                # Upload new picture
                new_picture_url = storage_service.upload_profile_picture(
                    contents, profile_picture.filename, user_id
                )

                # Delete old picture if exists
                old_picture_url = vb.get("profile_picture_url")
                if old_picture_url:
                    storage_service.delete_file(old_picture_url)

                logger.info(f"Profile picture updated for VB {vb_id}: {new_picture_url}")

            except VBValidationError:
                # Re-raise validation errors
                raise
            except Exception as e:
                logger.error(f"Failed to upload profile picture: {str(e)}")
                raise VBValidationError(f"Failed to upload profile picture: {str(e)}")

        # Build update data
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if contact_email is not None:
            update_data["contact_email"] = contact_email
        if main_expertise is not None:
            update_data["main_expertise"] = main_expertise
        if short_intro is not None:
            update_data["short_intro"] = short_intro
        if profile_picture:
            update_data["profile_picture_url"] = new_picture_url
        if work_experience is not None:
            update_data["work_experience"] = work_experience
        if biography is not None:
            update_data["biography"] = biography
        if linkedin_url is not None:
            update_data["linkedin_url"] = linkedin_url

        # Update profile if there are changes
        if update_data:
            self.data_access.update_vb_profile(vb_id, update_data)

        # Process expertise updates if provided
        if expertise_ids is not None or other_expertise is not None:
            # Process custom expertise areas if provided (bulk operation)
            custom_expertise_ids = []
            if other_expertise:
                logger.info(f"Bulk creating {len(other_expertise)} custom expertise areas for VB {vb_id}")
                custom_expertise_list = self.data_access.bulk_create_custom_expertise(other_expertise)
                custom_expertise_ids = [str(exp["id"]) for exp in custom_expertise_list]
                logger.info(f"Created/found {len(custom_expertise_ids)} custom expertise areas")

            # Combine predefined and custom expertise IDs
            all_expertise_ids = (expertise_ids or []) + custom_expertise_ids

            # Update expertise mapping (replaces existing)
            if all_expertise_ids:
                self.data_access.add_vb_expertise(vb_id, all_expertise_ids)
                logger.info(f"Updated expertise areas for VB {vb_id}: {len(all_expertise_ids)} total ({len(expertise_ids or [])} predefined, {len(custom_expertise_ids)} custom)")

        # Reset status to pending admin review if profile is currently active or inactive
        # This ensures all profile changes are reviewed before going live
        if vb["status"] in [VBStatus.ACTIVE.value, VBStatus.INACTIVE.value]:
            self.data_access.update_vb_status(vb_id, VBStatus.PENDING_ADMIN_REVIEW)
            logger.info(f"VB profile {vb_id} status reset to PENDING_ADMIN_REVIEW for re-approval")
            try:
                vb_user = self.data_access.get_user_profile(vb["user_id"])
                vb_user_role = vb_user.get("role") if vb_user else None
                if vb_user_role in ["admin", "super_admin"]:
                    logger.info(
                        f"Preserved {vb_user_role} role for user {vb['user_id']} after profile update"
                    )
                else:
                    self.data_access.update_user_role(vb["user_id"], "user")
                    logger.info(
                        f"Removed venture_builder role from user {vb['user_id']} after profile update"
                    )
            except Exception as e:
                logger.error(f"Failed to update user role after profile update: {e}")

        logger.info(f"VB profile {vb_id} updated")
        return self.get_vb_profile(vb_id)

    def create_or_update_vb_profile(
        self,
        user_id: str,
        profile_data: dict,
        expertise_ids: List[str],
    ) -> dict:
        """Create or update VB profile (VB completes their profile)"""
        logger.info(f"Creating/updating VB profile for user {user_id}")

        # Validate expertise areas
        if len(expertise_ids) > 5:
            raise VBValidationError("Maximum 5 expertise areas allowed")

        for exp_id in expertise_ids:
            exp = self.data_access.get_expertise_by_id(exp_id)
            if not exp or not exp.get("is_active"):
                raise VBValidationError(f"Invalid expertise area: {exp_id}")

        # Check if profile exists
        existing_vb = self.data_access.get_vb_by_user_id(user_id)

        if existing_vb:
            # Update existing profile
            vb_id = existing_vb["id"]
            vb = self.data_access.update_vb_profile(vb_id, profile_data)
        else:
            # Create new profile
            vb = self.data_access.create_vb_profile(user_id, profile_data)
            vb_id = vb["id"]

        # Update expertise mapping
        self.data_access.add_vb_expertise(vb_id, expertise_ids)

        # Move to pending admin review
        vb = self.data_access.update_vb_status(vb_id, VBStatus.PENDING_ADMIN_REVIEW)

        logger.info(f"VB profile updated for {user_id}, status: {vb['status']}")
        return self.get_vb_profile(vb_id)

    def browse_vbs(
        self,
        expertise_ids: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        require_calendar: bool = True,
        exclude_vb_id: Optional[str] = None,
    ) -> dict:
        """
        List active VBs for browse page.

        Args:
            expertise_ids: Filter by expertise areas
            search_query: Search query string
            page: Page number
            page_size: Items per page
            require_calendar: If True, only return VBs with calendar connectivity
                (either Google Calendar connected OR legacy calendar_booking_url set)
            exclude_vb_id: Optional VB ID to exclude from results

        Returns:
            Paginated list of active VBs
        """
        offset = (page - 1) * page_size
        items, total = self.data_access.list_active_vbs(
            expertise_ids=expertise_ids,
            search_query=search_query,
            limit=page_size,
            offset=offset,
            exclude_vb_id=exclude_vb_id,
        )

        # Filter by calendar connectivity if required
        if require_calendar:
            # Get VBs with Google Calendar connections
            vbs_with_google_calendar = self.data_access.get_vbs_with_calendar_connectivity()
            google_calendar_vb_ids = set(vbs_with_google_calendar)

            # Filter items to only include VBs with calendar connectivity
            filtered_items = [
                vb for vb in items
                if (
                    str(vb["id"]) in google_calendar_vb_ids or  # Has Google Calendar
                    vb.get("calendar_booking_url")  # Or has legacy calendar URL
                )
            ]

            # Update total count based on filtering
            # Note: This is an approximation - for accurate pagination,
            # the filtering should be done at the data access layer
            filtered_total = len(filtered_items)

            return {
                "items": filtered_items,
                "total": filtered_total,
                "page": page,
                "page_size": page_size,
            }

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_pending_vbs(self) -> List[dict]:
        """List VBs pending admin review (Admin only)"""
        return self.data_access.list_pending_vbs()

    # =====================================================
    # ADMIN VB MANAGEMENT
    # =====================================================

    def approve_vb(
        self,
        vb_id: str,
        credit_price_per_hour: int,
        calendar_booking_url: Optional[str] = None,
    ) -> dict:
        """Approve VB and set pricing (Admin only)"""
        logger.info(f"Approving VB {vb_id}")

        vb = self.get_vb_profile(vb_id)

        if vb["status"] != VBStatus.PENDING_ADMIN_REVIEW.value:
            raise VBStatusError(
                f"VB must be in pending_admin_review status to approve, current: {vb['status']}"
            )

        # Validate profile completeness
        if not vb.get("biography") or not vb.get("work_experience"):
            raise VBProfileIncompleteError("VB profile is incomplete")

        # Update with pricing and calendar
        update_data = {
            "credit_price_per_hour": credit_price_per_hour,
            "status": VBStatus.ACTIVE.value,
        }
        if calendar_booking_url is not None:
            update_data["calendar_booking_url"] = calendar_booking_url

        self.data_access.update_vb_profile(vb_id, update_data)

        # Assign venture_builder role to the VB user unless they are already admin/super_admin.
        try:
            vb_user = self.data_access.get_user_profile(vb["user_id"])
            vb_user_role = vb_user.get("role") if vb_user else None
            if vb_user_role in ["admin", "super_admin"]:
                logger.info(
                    f"Preserved {vb_user_role} role for user {vb['user_id']}"
                )
            else:
                self.data_access.update_user_role(vb["user_id"], "venture_builder")
                logger.info(f"Assigned venture_builder role to user {vb['user_id']}")
        except Exception as e:
            logger.error(f"Failed to assign venture_builder role: {e}")
            # Don't fail the approval if role assignment fails, just log it
            # The admin can manually assign the role if needed

        # Send approval notification email
        try:
            email_sent = email_service.send_vb_approval_email(
                to_email=vb["contact_email"],
                vb_name=vb["name"],
                vb_id=vb_id,
                credit_price_per_hour=credit_price_per_hour,
            )
            if email_sent:
                logger.info(f"Sent approval notification email to {vb['contact_email']}")
            else:
                logger.warning(f"Failed to send approval email to {vb['contact_email']}")
        except Exception as e:
            logger.error(f"Exception while sending approval email: {e}")
            # Don't fail the approval if email sending fails, just log it

        logger.info(f"VB {vb_id} approved and activated")
        return self.get_vb_profile(vb_id)

    def list_active_vb_role_mismatches(self) -> List[dict]:
        """List active VBs whose user role is not venture_builder (Admin only)"""
        return self.data_access.list_active_vbs_with_role_mismatch()

    def list_pending_vb_role_mismatches(self) -> List[dict]:
        """List pending VBs whose user role is venture_builder (Admin only)"""
        return self.data_access.list_pending_vbs_with_vb_role()

    def assign_vb_roles(self, user_ids: List[UUID]) -> dict:
        """Assign venture_builder role to the provided user IDs (Admin only)"""
        unique_user_ids = list(dict.fromkeys(user_ids))
        user_id_map = {str(user_id): user_id for user_id in unique_user_ids}

        user_roles = self.data_access.get_user_roles(list(user_id_map.values()))
        found_ids = {str(user["id"]) for user in user_roles}

        missing_user_ids = [
            user_id_map[user_id]
            for user_id in user_id_map.keys()
            if user_id not in found_ids
        ]

        admin_user_ids = [
            user_id_map[str(user["id"])]
            for user in user_roles
            if user.get("role") in ["admin", "super_admin"]
        ]

        to_update_ids = [
            user_id_map[str(user["id"])]
            for user in user_roles
            if user.get("role") not in ["admin", "super_admin", "venture_builder"]
        ]

        updated_rows = self.data_access.update_user_roles(to_update_ids, "venture_builder")
        updated_user_ids = [
            UUID(row["id"]) for row in updated_rows
        ] if updated_rows else to_update_ids

        return {
            "updated_user_ids": updated_user_ids,
            "skipped_admin_user_ids": admin_user_ids,
            "missing_user_ids": missing_user_ids,
        }

    def revert_vb_roles(self, user_ids: List[UUID]) -> dict:
        """Revert venture_builder role to user for the provided user IDs (Admin only)"""
        unique_user_ids = list(dict.fromkeys(user_ids))
        user_id_map = {str(user_id): user_id for user_id in unique_user_ids}

        user_roles = self.data_access.get_user_roles(list(user_id_map.values()))
        found_ids = {str(user["id"]) for user in user_roles}

        missing_user_ids = [
            user_id_map[user_id]
            for user_id in user_id_map.keys()
            if user_id not in found_ids
        ]

        to_update_ids = [
            user_id_map[str(user["id"])]
            for user in user_roles
            if user.get("role") == "venture_builder"
        ]

        skipped_non_vb_user_ids = [
            user_id_map[str(user["id"])]
            for user in user_roles
            if user.get("role") != "venture_builder"
        ]

        updated_rows = self.data_access.update_user_roles(to_update_ids, "user")
        updated_user_ids = [
            UUID(row["id"]) for row in updated_rows
        ] if updated_rows else to_update_ids

        return {
            "updated_user_ids": updated_user_ids,
            "skipped_non_vb_user_ids": skipped_non_vb_user_ids,
            "missing_user_ids": missing_user_ids,
        }

    def update_vb_pricing(self, vb_id: str, credit_price_per_hour: int) -> dict:
        """Update VB pricing (Admin only)"""
        logger.info(f"Updating VB {vb_id} pricing to {credit_price_per_hour}")
        self.data_access.update_vb_profile(
            vb_id, {"credit_price_per_hour": credit_price_per_hour}
        )
        return self.get_vb_profile(vb_id)

    def activate_vb(self, vb_id: str, user_role: Optional[str] = None) -> dict:
        """Activate VB (Admin only)"""
        logger.info(f"Activating VB {vb_id}")
        vb = self.get_vb_profile(vb_id)
        self.data_access.update_vb_status(vb_id, VBStatus.ACTIVE)

        # Assign venture_builder role when activating (but preserve admin/super_admin roles)
        if user_role not in ["admin", "super_admin"]:
            try:
                self.data_access.update_user_role(vb["user_id"], "venture_builder")
                logger.info(f"Assigned venture_builder role to user {vb['user_id']}")
            except Exception as e:
                logger.error(f"Failed to assign venture_builder role: {e}")
        else:
            logger.info(f"Preserved {user_role} role for user {vb['user_id']}")

        return self.get_vb_profile(vb_id)

    def deactivate_vb(self, vb_id: str, user_role: Optional[str] = None) -> dict:
        """Deactivate VB (Admin only)"""
        logger.info(f"Deactivating VB {vb_id}")
        vb = self.get_vb_profile(vb_id)
        self.data_access.update_vb_status(vb_id, VBStatus.INACTIVE)

        # Remove venture_builder role when deactivating (but preserve admin/super_admin roles)
        try:
            vb_user = self.data_access.get_user_profile(vb["user_id"])
            vb_user_role = vb_user.get("role") if vb_user else None
            if vb_user_role in ["admin", "super_admin"]:
                logger.info(
                    f"Preserved {vb_user_role} role for user {vb['user_id']} during deactivation"
                )
            else:
                self.data_access.update_user_role(vb["user_id"], "user")
                logger.info(f"Removed venture_builder role from user {vb['user_id']}")
        except Exception as e:
            logger.error(f"Failed to remove venture_builder role: {e}")

        return self.get_vb_profile(vb_id)

    def publish_vb(self, vb_id: str, is_active: bool) -> dict:
        """Publish/unpublish VB (Admin only)"""
        status = VBStatus.ACTIVE if is_active else VBStatus.INACTIVE
        logger.info(f"Setting VB {vb_id} status to {status.value}")
        self.data_access.update_vb_status(vb_id, status)
        return self.get_vb_profile(vb_id)

    def delete_vb_profile(self, vb_id: str, user_role: Optional[str] = None) -> None:
        """
        Delete VB profile (VB or Super Admin only).

        Cascading deletes will automatically remove:
        - VB expertise mappings
        - VB sessions
        - VB session notes
        - VB terms acceptances

        Args:
            vb_id: ID of the VB profile to delete
            user_role: Current user's role (to preserve admin/super_admin roles)

        Raises:
            VBNotFoundError: If VB profile doesn't exist
        """
        logger.info(f"Deleting VB profile {vb_id}")

        # Verify VB exists
        vb = self.get_vb_profile(vb_id)

        # Remove venture_builder role before deleting profile (but preserve admin/super_admin roles)
        try:
            vb_user = self.data_access.get_user_profile(vb["user_id"])
            vb_user_role = vb_user.get("role") if vb_user else None
            if vb_user_role in ["admin", "super_admin"]:
                logger.info(
                    f"Preserved {vb_user_role} role for user {vb['user_id']} during deletion"
                )
            else:
                self.data_access.update_user_role(vb["user_id"], "user")
                logger.info(f"Removed venture_builder role from user {vb['user_id']}")
        except Exception as e:
            logger.error(f"Failed to remove venture_builder role: {e}")

        # Delete the VB profile (cascading deletes handle related records)
        self.data_access.delete_vb_profile(vb_id)

        logger.info(f"VB profile {vb_id} deleted successfully")

    # =====================================================
    # BOOKING FLOW
    # =====================================================

    def check_credits(
        self, tenant_id: str, user_id: str, venture_builder_id: str
    ) -> dict:
        """Check if user has sufficient credits for booking"""
        vb = self.get_vb_profile(venture_builder_id)

        if vb["status"] != VBStatus.ACTIVE.value:
            raise VBStatusError("Venture Builder is not available for booking")

        required_credits = vb["credit_price_per_hour"]

        # Get available credits from credit service
        available = self.credit_service.get_available_credits(tenant_id=tenant_id)
        current_balance = int(available)

        has_sufficient = current_balance >= required_credits

        return {
            "has_sufficient_credits": has_sufficient,
            "current_balance": current_balance,
            "required_credits": required_credits,
            "vb_credit_price": required_credits,
        }

    def get_tenant_projects(self, tenant_id: str) -> List[dict]:
        """Get projects for tenant to select from"""
        return self.data_access.get_tenant_projects(tenant_id)

    def accept_terms(
        self,
        user_id: str,
        tenant_id: str,
        venture_builder_id: str,
        accepted_terms_version: str,
    ) -> dict:
        """Log terms acceptance"""
        logger.info(f"User {user_id} accepted VB terms for {venture_builder_id}")
        return self.data_access.log_terms_acceptance(
            user_id, tenant_id, venture_builder_id, accepted_terms_version
        )

    def create_booking(
        self,
        user_id: str,
        tenant_id: str,
        venture_builder_id: str,
        project_id: str,
        session_datetime: datetime,
        accepted_terms_version: str,
        agenda: Optional[str] = None,
    ) -> dict:
        """Create VB session booking"""
        logger.info(
            f"Creating booking for VB {venture_builder_id} by user {user_id} on {session_datetime}"
        )

        # Validate VB is active and check credits
        credit_check = self.check_credits(tenant_id, user_id, venture_builder_id)

        if not credit_check["has_sufficient_credits"]:
            raise VBInsufficientCreditsError(
                "Insufficient credits for booking",
                details={
                    "required_credits": credit_check["required_credits"],
                    "current_balance": credit_check["current_balance"],
                },
            )

        vb = self.get_vb_profile(venture_builder_id)

        # Validate project exists and belongs to tenant
        project = self.data_access.get_project_by_id(project_id)
        if not project:
            raise VBNotFoundError(f"Project {project_id} not found")
        if str(project.get("tenant_id")) != str(tenant_id):
            raise VBAccessDeniedError("Project does not belong to your tenant")

        # Validate session is in the future
        if session_datetime <= datetime.now(timezone.utc):
            raise VBValidationError("Session datetime must be in the future")

        credits_required = vb["credit_price_per_hour"]

        # Generate deterministic request_id for idempotency
        # Prevents double-charging if request is retried
        # Format as UUID (database expects UUID type)
        components = f"{tenant_id}:{user_id}:{venture_builder_id}:{session_datetime.isoformat()}"
        md5_hash = hashlib.md5(components.encode()).hexdigest()
        # Format MD5 (32 hex chars) as UUID: 8-4-4-4-12
        request_id = f"{md5_hash[:8]}-{md5_hash[8:12]}-{md5_hash[12:16]}-{md5_hash[16:20]}-{md5_hash[20:32]}"

        # Deduct credits using credit service
        try:
            deduction_result = self.credit_service.deduct_credits(
                tenant_id=tenant_id,
                user_id=user_id,
                amount=Decimal(credits_required),
                request_id=request_id,  # Idempotency: same booking params = same request_id
                reason=f"VB Session booking with {vb['contact_email']}",
                metadata={
                    "venture_builder_id": venture_builder_id,
                    "session_datetime": session_datetime.isoformat(),
                    "project_id": project_id,
                },
                project_id=project_id,
            )
            consumption_id = deduction_result["consumption"]["id"]
            logger.info(f"Credits deducted successfully, consumption_id: {consumption_id}")
        except KeyError as e:
            logger.error(f"Credit deduction succeeded but consumption_id not returned: {e}")
            raise VBValidationError(
                "Credit deduction succeeded but failed to track consumption. Please contact support."
            )
        except Exception as e:
            logger.error(f"Failed to deduct credits: {e}")
            raise VBInsufficientCreditsError(
                "Failed to deduct credits",
                details={
                    "required_credits": credits_required,
                    "error": str(e),
                },
            )

        # Log terms acceptance
        self.data_access.log_terms_acceptance(
            user_id, tenant_id, venture_builder_id, accepted_terms_version
        )

        # Create session
        session_data = {
            "tenant_id": tenant_id,
            "booked_by_user_id": user_id,
            "venture_builder_id": venture_builder_id,
            "project_id": project_id,
            "session_datetime": session_datetime.isoformat(),
            "session_duration_minutes": 60,
            "credits_charged": credits_required,
            "status": SessionStatus.CONFIRMED.value,
            "credit_consumption_id": consumption_id,
        }
        if agenda:
            session_data["agenda"] = agenda

        session = self.data_access.create_session(session_data)

        logger.info(f"Booking created successfully: {session['id']}")

        # Send confirmation emails to both user and VB
        try:
            # Get user profile for name and email
            user_profile = self.data_access.get_user_profile(user_id)
            user_full_name = user_profile.get("full_name", "User") if user_profile else "User"
            user_email_addr = user_profile.get("email", "") if user_profile else ""

            # Format session datetime for email
            session_datetime_str = session_datetime.strftime("%B %d, %Y at %I:%M %p UTC")

            # Send email to user
            if user_email_addr:
                email_service.send_vb_booking_confirmation_to_user(
                    to_email=user_email_addr,
                    user_name=user_full_name,
                    vb_name=vb.get("contact_email", "Venture Builder"),
                    vb_email=vb["contact_email"],
                    session_datetime=session_datetime_str,
                    project_name=project.get("name", "Your Project"),
                    credits_charged=credits_required,
                )
                logger.info(f"Sent booking confirmation email to user {user_id}")

            # Send email to VB
            email_service.send_vb_booking_confirmation_to_vb(
                to_email=vb["contact_email"],
                vb_name=vb.get("contact_email", "Venture Builder"),
                user_name=user_full_name,
                user_email=user_email_addr,
                session_datetime=session_datetime_str,
                project_name=project.get("name", "Project"),
                credits_charged=credits_required,
            )
            logger.info(f"Sent booking confirmation email to VB {venture_builder_id}")

        except Exception as e:
            logger.error(f"Failed to send confirmation emails: {e}")
            # Don't fail the booking if email sending fails

        # Create Google Calendar event if VB has connected calendar
        try:
            google_connection = self.data_access.get_google_connection(venture_builder_id)
            if google_connection and google_connection.get("is_valid") and google_connection.get("calendar_id"):
                calendar_service = get_google_calendar_service()

                # Get user profile for attendee info (reuse from email sending above)
                user_email_for_calendar = user_email_addr if user_email_addr else None

                # Calculate end time
                session_end = session_datetime + timedelta(minutes=60)

                # Create calendar event
                event_id = calendar_service.create_event(
                    vb_id=venture_builder_id,
                    summary=f"Yuba Session: {user_full_name} - {project.get('name', 'Project')}",
                    start=session_datetime,
                    end=session_end,
                    attendee_email=user_email_for_calendar,
                    description=f"Venture Builder session with {user_full_name}\n\nProject: {project.get('name', 'Project')}",
                    agenda=agenda,
                )

                if event_id:
                    # Store calendar_event_id in session
                    self.data_access.update_session(
                        session["id"],
                        {"calendar_event_id": event_id}
                    )
                    logger.info(f"Google Calendar event created: {event_id}")
        except GoogleCalendarAuthError as e:
            logger.warning(f"Google Calendar auth error for VB {venture_builder_id}: {e}")
            # Don't fail the booking, just log the error
        except GoogleCalendarError as e:
            logger.error(f"Failed to create Google Calendar event: {e}")
            # Don't fail the booking if calendar event creation fails
        except Exception as e:
            logger.error(f"Unexpected error creating Google Calendar event: {e}")
            # Don't fail the booking

        return session

    # =====================================================
    # SESSION MANAGEMENT
    # =====================================================

    def get_session_by_id(self, session_id: str, requesting_user_id: str) -> dict:
        """Get session details with access control"""
        session = self.data_access.get_session_by_id(session_id)
        if not session:
            raise VBNotFoundError(f"Session {session_id} not found")

        # Check access: user who booked it or the VB
        vb = self.data_access.get_vb_by_user_id(requesting_user_id)
        is_vb = vb and str(vb["id"]) == str(session["venture_builder_id"])
        is_booker = str(session["booked_by_user_id"]) == str(requesting_user_id)

        if not (is_vb or is_booker):
            raise VBAccessDeniedError("You don't have access to this session")

        return session

    def get_vb_sessions(
        self,
        venture_builder_id: str,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[dict]:
        """Get sessions for a VB (VB Portal)"""
        offset = (page - 1) * page_size

        # Convert status string to enum if provided
        status_enum = None
        if status:
            try:
                status_enum = SessionStatus(status)
            except ValueError:
                logger.warning(f"Invalid session status: {status}")

        sessions, _ = self.data_access.get_vb_sessions(
            vb_id=venture_builder_id,
            status=status_enum,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )
        return sessions

    def get_user_sessions(
        self,
        user_id: str,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[dict]:
        """Get sessions booked by a user"""
        offset = (page - 1) * page_size
        sessions, _ = self.data_access.get_user_sessions(
            user_id=user_id, tenant_id=None, limit=page_size, offset=offset
        )
        return sessions

    def update_session_status(
        self, session_id: str, status: SessionStatus, updated_by_user_id: str
    ) -> dict:
        """Update session status (VB or Admin)"""
        session = self.get_session_by_id(session_id, updated_by_user_id)

        logger.info(f"Updating session {session_id} status to {status.value}")
        return self.data_access.update_session(session_id, {"status": status.value})

    def complete_session(
        self,
        session_id: str,
        completed_by_user_id: str,
        is_admin: bool = False,
    ) -> dict:
        """
        Mark a session as completed. Can only be done by the VB or admin after the session ends.

        Args:
            session_id: Session to complete
            completed_by_user_id: User marking it complete (must be VB or admin)
            is_admin: Whether the requester is an admin

        Returns:
            Completed session details

        Raises:
            VBNotFoundError: Session not found
            VBAccessDeniedError: User not authorized to complete
            VBValidationError: Session cannot be completed (wrong status or hasn't ended yet)
        """
        logger.info(f"Completing session {session_id} by user {completed_by_user_id}")

        # Get session
        session = self.data_access.get_session_by_id(session_id)
        if not session:
            raise VBNotFoundError(f"Session {session_id} not found")

        # Check access: only VB or admin can mark as complete
        if not is_admin:
            vb = self.data_access.get_vb_by_user_id(completed_by_user_id)
            is_vb = vb and str(vb["id"]) == str(session["venture_builder_id"])

            if not is_vb:
                raise VBAccessDeniedError(
                    "Only the venture builder or admin can mark a session as complete"
                )

        # Validate session can be completed
        non_completable_statuses = [
            SessionStatus.COMPLETED.value,
            SessionStatus.CANCELED.value,
            SessionStatus.SETTLED.value,
        ]
        if session["status"] in non_completable_statuses:
            raise VBValidationError(
                f"Cannot complete session with status '{session['status']}'"
            )

        # Check if session has ended
        session_datetime_str = session.get("session_datetime")
        session_duration = session.get("session_duration_minutes", 60)

        if session_datetime_str:
            session_datetime = datetime.fromisoformat(
                session_datetime_str.replace("Z", "+00:00")
            )
            session_end_time = session_datetime + timedelta(minutes=session_duration)
            now = datetime.now(timezone.utc)

            # Session must have ended (or be very close to ending)
            # Allow 10 min early completion for VB convenience
            if now < (session_end_time - timedelta(minutes=10)):
                raise VBValidationError(
                    f"Session has not ended yet. Session ends at {session_end_time.isoformat()}"
                )

        # Update session status to completed
        completed_session = self.data_access.update_session(
            session_id,
            {"status": SessionStatus.COMPLETED.value}
        )

        logger.info(f"Session {session_id} marked as completed")

        return completed_session

    def cancel_session(
        self,
        session_id: str,
        requesting_user_id: str,
        cancellation_reason: str,
        is_admin: bool = False,
    ) -> dict:
        """
        Cancel a session and clean up Google Calendar event if exists.
        Only VBs and admins can cancel sessions.

        Args:
            session_id: Session to cancel
            requesting_user_id: User requesting cancellation (must be VB or admin)
            cancellation_reason: Reason for cancellation (sent to user via email)
            is_admin: Whether the requester is an admin

        Returns:
            Cancelled session details

        Raises:
            VBNotFoundError: Session not found
            VBAccessDeniedError: User not authorized to cancel (only VB or admin)
            VBValidationError: Session cannot be cancelled (already completed/cancelled)
        """
        logger.info(f"Cancelling session {session_id} by user {requesting_user_id}")

        # Get session
        session = self.data_access.get_session_by_id(session_id)
        if not session:
            raise VBNotFoundError(f"Session {session_id} not found")

        # Check access: ONLY admin or the VB (not the user who booked it)
        if not is_admin:
            vb = self.data_access.get_vb_by_user_id(requesting_user_id)
            is_vb = vb and str(vb["id"]) == str(session["venture_builder_id"])

            if not is_vb:
                raise VBAccessDeniedError(
                    "Only the venture builder or admin can cancel a session"
                )

        # Validate session can be cancelled
        non_cancellable_statuses = [
            SessionStatus.COMPLETED.value,
            SessionStatus.CANCELED.value,
            SessionStatus.SETTLED.value,
        ]
        if session["status"] in non_cancellable_statuses:
            raise VBValidationError(
                f"Cannot cancel session with status '{session['status']}'"
            )

        # Check if session has already started
        session_datetime_str = session.get("session_datetime")
        if session_datetime_str:
            session_datetime = datetime.fromisoformat(
                session_datetime_str.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            if session_datetime <= now:
                raise VBValidationError(
                    "Cannot cancel a session that has already started or passed"
                )

        # Delete Google Calendar event if exists
        calendar_event_id = session.get("calendar_event_id")
        if calendar_event_id:
            try:
                vb_id = str(session["venture_builder_id"])
                google_connection = self.data_access.get_google_connection(vb_id)

                if google_connection and google_connection.get("is_valid") and google_connection.get("calendar_id"):
                    calendar_service = get_google_calendar_service()
                    calendar_service.delete_event(vb_id, calendar_event_id)
                    logger.info(f"Deleted Google Calendar event {calendar_event_id}")
            except GoogleCalendarAuthError as e:
                logger.warning(f"Google Calendar auth error during cancellation: {e}")
            except GoogleCalendarError as e:
                logger.error(f"Failed to delete Google Calendar event: {e}")
            except Exception as e:
                logger.error(f"Unexpected error deleting calendar event: {e}")

        # Refund credits by restoring them to original lots
        credit_consumption_id = session.get("credit_consumption_id")
        refund_result = None
        if credit_consumption_id:
            try:
                refund_result = self.credit_service.refund_consumption(
                    consumption_id=str(credit_consumption_id),
                    reason=f"VB session cancelled (session_id: {session_id})",
                    refunded_by_user_id=requesting_user_id,
                )
                logger.info(
                    f"Credits refunded for session {session_id}: "
                    f"{refund_result.get('total_refunded', 0)} credits restored"
                )
            except Exception as e:
                logger.error(f"Failed to refund credits for session {session_id}: {e}")
                # Don't fail the cancellation if refund fails
                # Admin can manually handle refund if needed

        # Update session status to cancelled
        cancelled_session = self.data_access.update_session(
            session_id,
            {
                "status": SessionStatus.CANCELED.value,
                "calendar_event_id": None,  # Clear the event ID
            }
        )

        logger.info(f"Session {session_id} cancelled successfully")

        # Send cancellation email to user
        try:
            # Get VB profile
            vb_profile = self.data_access.get_vb_by_id(str(session["venture_builder_id"]))
            vb_name = vb_profile.get("name", "Venture Builder") if vb_profile else "Venture Builder"

            # Get user profile
            user_profile = self.data_access.get_user_profile(session["booked_by_user_id"])
            user_name = user_profile.get("full_name", "User") if user_profile else "User"
            user_email = user_profile.get("email", "") if user_profile else ""

            # Get project info
            project = self.data_access.get_project_by_id(session["project_id"])
            project_name = project.get("name", "Your Project") if project else "Your Project"

            # Format session datetime
            session_datetime_str = session.get("session_datetime")
            if session_datetime_str:
                session_dt = datetime.fromisoformat(session_datetime_str.replace("Z", "+00:00"))
                formatted_datetime = session_dt.strftime("%B %d, %Y at %I:%M %p UTC")
            else:
                formatted_datetime = "the scheduled time"

            # Build booking link
            frontend_url = os.getenv("FRONTEND_URL", "")
            booking_link = f"{frontend_url}/venture-builder/browse"

            # Send email to user
            if user_email:
                email_service.send_vb_cancellation_email_to_user(
                    to_email=user_email,
                    user_name=user_name,
                    vb_name=vb_name,
                    session_datetime=formatted_datetime,
                    project_name=project_name,
                    cancellation_reason=cancellation_reason,
                    credits_refunded=session.get("credits_charged", 0),
                    booking_link=booking_link,
                )
                logger.info(f"Sent cancellation email to user {session['booked_by_user_id']}")
        except Exception as e:
            logger.error(f"Failed to send cancellation email: {e}")
            # Don't fail the cancellation if email sending fails

        # Include refund info in response
        if refund_result:
            cancelled_session["credits_refunded"] = refund_result.get("total_refunded", 0)

        return cancelled_session

    # =====================================================
    # SESSION NOTES
    # =====================================================

    def create_session_note(
        self,
        vb_session_id: str,
        venture_builder_id: str,
        created_by_user_id: str,
        main_outcomes: str,
        key_takeaways: str,
        next_steps: Optional[str],
        visible_to_user: bool,
    ) -> dict:
        """Create session note (VB only)"""
        logger.info(f"Creating note for session {vb_session_id}")

        # Verify session exists and get details
        session = self.data_access.get_session_by_id(vb_session_id)
        if not session:
            raise VBNotFoundError(f"Session {vb_session_id} not found")

        # Verify VB ownership
        if str(session["venture_builder_id"]) != str(venture_builder_id):
            raise VBAccessDeniedError("VB ID does not match session")

        # Check if note already exists
        existing_note = self.data_access.get_note_by_session_id(vb_session_id)
        if existing_note:
            raise VBValidationError("Note already exists for this session")

        note = self.data_access.create_session_note(
            {
                "vb_session_id": vb_session_id,
                "venture_builder_id": venture_builder_id,
                "tenant_id": session["tenant_id"],
                "project_id": session["project_id"],
                "created_by_user_id": created_by_user_id,
                "main_outcomes": main_outcomes,
                "key_takeaways": key_takeaways,
                "next_steps": next_steps,
                "visible_to_user": visible_to_user,
            }
        )

        logger.info(f"Session note created: {note['id']}")
        return note

    def update_session_note(
        self,
        note_id: str,
        venture_builder_id: str,
        main_outcomes: Optional[str] = None,
        key_takeaways: Optional[str] = None,
        next_steps: Optional[str] = None,
        visible_to_user: Optional[bool] = None,
    ) -> dict:
        """Update session note (VB only)"""
        logger.info(f"Updating note {note_id}")

        # Verify note exists and belongs to this VB
        note = self.data_access.get_note_by_id(note_id)
        if not note:
            raise VBNotFoundError(f"Session note {note_id} not found")

        if str(note["venture_builder_id"]) != str(venture_builder_id):
            raise VBAccessDeniedError("Note does not belong to this Venture Builder")

        # Build update data
        update_data = {}
        if main_outcomes is not None:
            update_data["main_outcomes"] = main_outcomes
        if key_takeaways is not None:
            update_data["key_takeaways"] = key_takeaways
        if next_steps is not None:
            update_data["next_steps"] = next_steps
        if visible_to_user is not None:
            update_data["visible_to_user"] = visible_to_user

        return self.data_access.update_session_note(note_id, update_data)

    def get_session_note(self, session_id: str) -> Optional[dict]:
        """Get session note by session ID (VB view - no filtering)"""
        return self.data_access.get_note_by_session_id(session_id)

    def get_session_note_for_user(
        self, session_id: str, requesting_user_id: str
    ) -> Optional[dict]:
        """Get session note with visibility control for regular users"""
        note = self.data_access.get_note_by_session_id(session_id)
        if not note:
            return None

        # Check if user booked this session
        session = self.data_access.get_session_by_id(session_id)
        if not session or str(session["booked_by_user_id"]) != str(requesting_user_id):
            return None

        # Only return if visible to user
        if not note.get("visible_to_user"):
            return None

        return note

    def get_user_coaching_notes(
        self,
        tenant_id: str,
        requesting_user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int]:
        """
        Get coaching notes for a user's tenant
        Only returns notes where visible_to_user=true (unless user is the VB)
        """
        offset = (page - 1) * page_size

        # Check if requesting user is a VB
        vb = self.data_access.get_vb_by_user_id(requesting_user_id)

        notes, total = self.data_access.get_user_coaching_notes(
            tenant_id=tenant_id, limit=page_size, offset=offset
        )

        # Filter notes based on visibility unless user is the VB
        if not vb:
            # For regular users, only show notes marked as visible
            notes = [note for note in notes if note.get("visible_to_user", False)]
        else:
            # For VBs, show all their own notes regardless of visibility flag
            notes = [
                note
                for note in notes
                if str(note.get("venture_builder_id")) == str(vb["id"])
                or note.get("visible_to_user", False)
            ]

        return notes, total

    def get_tenant_coaching_notes(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> List[dict]:
        """
        Get all coaching notes for a tenant (Admin/VB view - no filtering)
        """
        offset = (page - 1) * page_size
        notes, _ = self.data_access.get_user_coaching_notes(
            tenant_id=tenant_id, limit=page_size, offset=offset
        )
        return notes

    # =====================================================
    # VB PORTAL - PROJECT VIEW
    # =====================================================

    def get_vb_accessible_projects(self, vb_id: str) -> List[dict]:
        """Get all projects where VB has active or completed sessions"""
        logger.info(f"Getting accessible projects for VB {vb_id}")

        # Get all sessions for this VB
        sessions, _ = self.data_access.get_vb_sessions(
            vb_id=vb_id, status=None, start_date=None, end_date=None, limit=1000, offset=0
        )

        # Extract unique project IDs
        project_ids = list(set(str(s.get("project_id")) for s in sessions if s.get("project_id")))

        # Fetch project details
        projects = []
        for project_id in project_ids:
            project = self.data_access.get_project_by_id(project_id)
            if project:
                projects.append(project)

        return projects

    def get_project_for_vb(self, vb_user_id: str, project_id: str) -> dict:
        """Get read-only project details for VB (if they have a session for it)"""
        vb = self.data_access.get_vb_by_user_id(vb_user_id)
        if not vb:
            raise VBAccessDeniedError("User is not a Venture Builder")

        # Check if VB has any session for this project
        sessions, _ = self.data_access.get_vb_sessions(
            vb_id=vb["id"], status=None, start_date=None, end_date=None, limit=1000, offset=0
        )

        has_access = any(str(s.get("project_id")) == str(project_id) for s in sessions)
        if not has_access:
            raise VBAccessDeniedError(
                "You don't have access to this project. Book a session first."
            )

        project = self.data_access.get_project_by_id(project_id)
        if not project:
            raise VBNotFoundError(f"Project {project_id} not found")

        return project

    # =====================================================
    # EARNINGS DASHBOARD
    # =====================================================

    def get_vb_earnings(
        self,
        vb_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get VB earnings dashboard data"""
        logger.info(f"Getting earnings for VB {vb_id}")

        # Get earnings config
        config = self.data_access.get_earnings_config()
        credit_to_usd = Decimal(str(config.get("credit_to_usd_rate", 1.0)))
        commission_rate = Decimal(str(config.get("commission_rate", 0.15)))

        # Get completed sessions
        sessions = self.data_access.get_completed_sessions_for_earnings(
            vb_id, start_date, end_date, include_settled=True
        )

        # Calculate earnings for the period
        total_credits = sum(s.get("credits_charged", 0) for s in sessions)
        total_usd = Decimal(total_credits) * credit_to_usd
        commission = total_usd * commission_rate
        net_usd = total_usd - commission

        # Get total sessions count (all time)
        total_sessions_all_time = self.data_access.get_completed_sessions_count(vb_id)

        # Get reconciliation data
        total_reconciled = self.data_access.get_vb_total_reconciled(vb_id)

        # Calculate pending amount
        # For this, we need ALL completed sessions to get total net earnings
        all_sessions = self.data_access.get_completed_sessions_for_earnings(
            vb_id, include_settled=True
        )
        all_credits = sum(s.get("credits_charged", 0) for s in all_sessions)
        all_usd = Decimal(all_credits) * credit_to_usd
        all_commission = all_usd * commission_rate
        all_net_earnings = all_usd - all_commission
        pending_amount = all_net_earnings - total_reconciled

        # Build session details
        session_details = []
        for session in sessions:
            credits = Decimal(session.get("credits_charged", 0))
            gross = credits * credit_to_usd
            comm = gross * commission_rate
            net = gross - comm

            # Get tenant and project names
            tenant_name = self.data_access.get_tenant_name(session.get("tenant_id"))
            project_name = self.data_access.get_project_name(session.get("project_id"))

            session_details.append(
                {
                    "session_id": session["id"],
                    "session_datetime": session["session_datetime"],
                    "tenant_name": tenant_name,
                    "project_name": project_name,
                    "credits_charged": int(credits),
                    "gross_usd": gross,
                    "commission_usd": comm,
                    "net_usd": net,
                }
            )

        return {
            "total_earned_credits": total_credits,
            "total_earnings_usd": total_usd,
            "commission_amount_usd": commission,
            "net_earnings_usd": net_usd,
            "total_reconciled_payments": total_reconciled,
            "pending_amount_usd": pending_amount,
            "completed_sessions_period": len(sessions),
            "total_sessions_all_time": total_sessions_all_time,
            "sessions": session_details,
            "date_range_start": start_date,
            "date_range_end": end_date,
        }

    def get_earnings_config(self) -> dict:
        """Get earnings configuration"""
        return self.data_access.get_earnings_config()

    def update_earnings_config(
        self,
        updated_by: str,
        credit_to_usd_rate: Optional[Decimal] = None,
        commission_rate: Optional[Decimal] = None,
    ) -> dict:
        """Update earnings configuration (Admin only)"""
        logger.info(f"Updating earnings config by {updated_by}")

        config_data = {}
        if credit_to_usd_rate is not None:
            config_data["credit_to_usd_rate"] = float(credit_to_usd_rate)
        if commission_rate is not None:
            config_data["commission_rate"] = float(commission_rate)

        return self.data_access.update_earnings_config(config_data, updated_by)

    # =====================================================
    # DISPUTES
    # =====================================================

    def check_can_open_dispute(self, session_id: str, user_id: str) -> dict:
        """
        Check if user can open a dispute for a session.

        Returns:
            dict with can_open_dispute (bool) and reason (str) if cannot
        """
        # Get session
        session = self.data_access.get_session_by_id(session_id)
        if not session:
            return {"can_open_dispute": False, "reason": "Session not found"}

        # Verify session belongs to user
        if str(session["booked_by_user_id"]) != str(user_id):
            return {"can_open_dispute": False, "reason": "Session does not belong to you"}

        # Check if session is completed
        if session["status"] != SessionStatus.COMPLETED.value:
            return {"can_open_dispute": False, "reason": "Only completed sessions can be disputed"}

        # Check if dispute already exists
        existing_dispute = self.data_access.get_dispute_by_session_id(session_id)
        if existing_dispute:
            return {"can_open_dispute": False, "reason": "A dispute already exists for this session"}

        return {"can_open_dispute": True, "reason": None}

    def create_dispute(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        reason: str,
        custom_reason: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Create a dispute for a session.

        Args:
            session_id: Session to dispute
            user_id: User creating the dispute
            tenant_id: Tenant ID
            reason: Dispute reason (missed_session, time_theft, other)
            custom_reason: Required if reason is 'other'
            description: Optional detailed explanation

        Returns:
            Created dispute

        Raises:
            VBNotFoundError: Session not found
            VBAccessDeniedError: Session doesn't belong to user
            VBDisputeNotEligibleError: Session is not completed
            VBDisputeAlreadyExistsError: Dispute already exists
            VBValidationError: Missing custom_reason when reason is 'other'
        """
        logger.info(f"Creating dispute for session {session_id} by user {user_id}")

        # Get session and validate
        session = self.data_access.get_session_by_id(session_id)
        if not session:
            raise VBNotFoundError(f"Session {session_id} not found")

        # Verify ownership
        if str(session["booked_by_user_id"]) != str(user_id):
            raise VBAccessDeniedError("You can only dispute your own sessions")

        # Verify session is completed
        if session["status"] != SessionStatus.COMPLETED.value:
            raise VBDisputeNotEligibleError(
                "Only completed sessions can be disputed"
            )

        # Check for existing dispute
        existing_dispute = self.data_access.get_dispute_by_session_id(session_id)
        if existing_dispute:
            raise VBDisputeAlreadyExistsError(
                "A dispute already exists for this session"
            )

        # Validate custom_reason if reason is 'other'
        if reason == "other" and not custom_reason:
            raise VBValidationError(
                "custom_reason is required when reason is 'other'"
            )

        # Create dispute
        dispute_data = {
            "session_id": session_id,
            "user_id": user_id,
            "vb_id": str(session["venture_builder_id"]),
            "tenant_id": tenant_id,
            "reason": reason,
            "custom_reason": custom_reason,
            "description": description,
            "status": DisputeStatus.SUBMITTED.value,
        }

        dispute = self.data_access.create_dispute(dispute_data)
        logger.info(f"Dispute {dispute['id']} created for session {session_id}")

        return dispute

    def get_user_disputes(
        self,
        user_id: str,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all disputes created by a user with pagination"""
        logger.info(f"Fetching disputes for user {user_id}")

        offset = (page - 1) * page_size
        disputes, total_count = self.data_access.get_disputes_for_user(
            user_id, tenant_id, limit=page_size, offset=offset
        )

        return {
            "disputes": disputes,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
        }

    def get_dispute_by_id(self, dispute_id: str, user_id: str) -> dict:
        """Get a specific dispute (user must be the creator)"""
        dispute = self.data_access.get_dispute_by_id(dispute_id)
        if not dispute:
            raise VBNotFoundError(f"Dispute {dispute_id} not found")

        # Verify ownership
        if str(dispute["user_id"]) != str(user_id):
            raise VBAccessDeniedError("You can only view your own disputes")

        return dispute

    def get_admin_disputes(
        self,
        status: Optional[str] = None,
        vb_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all disputes with filters (admin only)"""
        logger.info("Fetching disputes for admin")

        offset = (page - 1) * page_size
        disputes, total_count = self.data_access.get_disputes_for_admin(
            status=status,
            vb_id=vb_id,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            limit=page_size,
            offset=offset,
        )

        return {
            "disputes": disputes,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
        }

    def update_dispute_status(
        self,
        dispute_id: str,
        admin_user_id: str,
        status: Optional[str] = None,
        admin_notes: Optional[str] = None,
    ) -> dict:
        """Update dispute status (admin only)"""
        logger.info(f"Updating dispute {dispute_id} by admin {admin_user_id}")

        dispute = self.data_access.get_dispute_by_id(dispute_id)
        if not dispute:
            raise VBNotFoundError(f"Dispute {dispute_id} not found")

        update_data = {}
        if status is not None:
            update_data["status"] = status
        if admin_notes is not None:
            update_data["admin_notes"] = admin_notes

        # If marking as resolved, add resolved metadata
        if status == DisputeStatus.RESOLVED.value:
            update_data["resolved_by"] = admin_user_id
            update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

        return self.data_access.update_dispute(dispute_id, update_data)

    # =====================================================
    # RECONCILIATION
    # =====================================================

    def reconcile_vb_payments(
        self,
        vb_id: str,
        reconciled_by_user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Reconcile pending payments for a Venture Builder.
        Marks pending earnings as settled and updates cumulative reconciled total.

        Args:
            vb_id: Venture Builder ID
            reconciled_by_user_id: Admin user performing reconciliation
            start_date: Optional start date filter for sessions to reconcile
            end_date: Optional end date filter for sessions to reconcile
            notes: Optional admin notes

        Returns:
            Reconciliation response with amounts and details
        """
        logger.info(f"Reconciling payments for VB {vb_id} by admin {reconciled_by_user_id}")

        # Verify VB exists
        vb = self.get_vb_profile(vb_id)
        if not vb:
            raise VBNotFoundError(f"Venture Builder {vb_id} not found")

        # Get earnings config
        config = self.data_access.get_earnings_config()
        credit_to_usd = Decimal(str(config.get("credit_to_usd_rate", 1.0)))
        commission_rate = Decimal(str(config.get("commission_rate", 0.15)))

        # Get ALL completed sessions for total net earnings calculation
        all_sessions = self.data_access.get_completed_sessions_for_earnings(
            vb_id, include_settled=True
        )

        # Calculate total net earnings from ALL sessions
        total_credits_all = sum(s.get("credits_charged", 0) for s in all_sessions)
        total_usd_all = Decimal(total_credits_all) * credit_to_usd
        commission_all = total_usd_all * commission_rate
        total_net_earnings = total_usd_all - commission_all

        # Get current total reconciled
        current_reconciled = self.data_access.get_vb_total_reconciled(vb_id)

        # Calculate pending amount (before this reconciliation)
        pending_amount_before = total_net_earnings - current_reconciled

        if pending_amount_before <= 0:
            raise VBValidationError("No pending amount to reconcile")

        # Determine amount to reconcile based on date filters
        if start_date or end_date:
            # Partial reconciliation: only sessions within date range
            period_sessions = self.data_access.get_completed_sessions_for_earnings(
                vb_id, start_date, end_date
            )
            session_count = len(period_sessions)

            # Calculate net earnings for this period
            period_credits = sum(s.get("credits_charged", 0) for s in period_sessions)
            period_usd = Decimal(period_credits) * credit_to_usd
            period_commission = period_usd * commission_rate
            amount_to_reconcile = period_usd - period_commission

            if amount_to_reconcile <= 0:
                raise VBValidationError("No earnings in the specified date range")

            # Can't reconcile more than pending
            if amount_to_reconcile > pending_amount_before:
                amount_to_reconcile = pending_amount_before
        else:
            # Full reconciliation: all pending amount
            amount_to_reconcile = pending_amount_before
            session_count = len(all_sessions)

        # Create reconciliation record
        reconciliation = self.data_access.create_reconciliation(
            vb_id=vb_id,
            reconciled_by=reconciled_by_user_id,
            amount_reconciled_usd=amount_to_reconcile,
            pending_amount_before=pending_amount_before,
            session_count=session_count,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )

        # Update VB's total reconciled payments
        new_total_reconciled = current_reconciled + amount_to_reconcile
        self.data_access.update_vb_total_reconciled(vb_id, new_total_reconciled)

        # Mark the reconciled sessions as settled
        sessions_marked = self.data_access.mark_sessions_as_settled(
            vb_id=vb_id,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate pending amount after reconciliation
        pending_amount_after = pending_amount_before - amount_to_reconcile

        logger.info(
            f"Reconciliation complete: {amount_to_reconcile} USD reconciled for VB {vb_id}. "
            f"Marked {sessions_marked} sessions as settled. "
            f"Pending after: {pending_amount_after}, Total reconciled lifetime: {new_total_reconciled}"
        )

        return {
            "reconciliation_id": reconciliation["id"],
            "venture_builder_id": vb_id,
            "amount_reconciled_usd": amount_to_reconcile,
            "pending_amount_before": pending_amount_before,
            "pending_amount_after": pending_amount_after,
            "session_count": session_count,
            "sessions_marked_settled": sessions_marked,
            "total_reconciled_lifetime": new_total_reconciled,
            "created_at": reconciliation["created_at"],
        }

    def get_reconciliation_history(
        self, vb_id: str, page: int = 1, page_size: int = 20
    ) -> dict:
        """Get reconciliation history for a VB"""
        logger.info(f"Getting reconciliation history for VB {vb_id}")

        reconciliations, total_count = self.data_access.get_reconciliation_history(
            vb_id, page, page_size
        )

        return {
            "reconciliations": reconciliations,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        }

    def get_all_reconciliations(self, page: int = 1, page_size: int = 20) -> dict:
        """Get all reconciliations (admin view)"""
        logger.info("Getting all reconciliations (admin view)")

        reconciliations, total_count = self.data_access.get_all_reconciliations(
            page, page_size
        )

        return {
            "reconciliations": reconciliations,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        }

    # =====================================================
    # GOOGLE CALENDAR INTEGRATION
    # =====================================================

    def get_calendar_auth_url(self, vb_id: str) -> dict:
        """
        Generate OAuth authorization URL for VB to connect Google Calendar.

        Args:
            vb_id: Venture builder ID.

        Returns:
            Dict with auth_url and state token.
        """
        calendar_service = get_google_calendar_service()
        auth_url, state = calendar_service.create_auth_url(vb_id)
        return {"auth_url": auth_url, "state": state}

    def handle_calendar_oauth_callback(self, code: str, state: str) -> dict:
        """
        Handle OAuth callback from Google.

        Args:
            code: Authorization code from Google.
            state: State token for validation.

        Returns:
            Connection status dict.
        """
        calendar_service = get_google_calendar_service()
        return calendar_service.handle_oauth_callback(code, state)

    def get_calendar_status(self, vb_id: str) -> dict:
        """
        Get Google Calendar connection status for a VB.

        Args:
            vb_id: Venture builder ID.

        Returns:
            Dict with connection status.
        """
        calendar_service = get_google_calendar_service()
        return calendar_service.get_connection_status(vb_id)

    def list_calendars(self, vb_id: str) -> List[dict]:
        """
        List all Google Calendars available to a VB.

        Args:
            vb_id: Venture builder ID.

        Returns:
            List of calendar items.
        """
        calendar_service = get_google_calendar_service()
        calendars = calendar_service.list_calendars(vb_id)
        return [{"id": c.id, "summary": c.summary, "primary": c.primary} for c in calendars]

    def select_calendar(
        self, vb_id: str, calendar_id: str, time_zone: str
    ) -> None:
        """
        Select which Google Calendar to use for bookings.

        Args:
            vb_id: Venture builder ID.
            calendar_id: Google Calendar ID.
            time_zone: Timezone string.
        """
        calendar_service = get_google_calendar_service()
        calendar_service.select_calendar(vb_id, calendar_id, time_zone)

    def disconnect_calendar(self, vb_id: str) -> None:
        """
        Disconnect Google Calendar integration for a VB.

        Args:
            vb_id: Venture builder ID.
        """
        calendar_service = get_google_calendar_service()
        calendar_service.disconnect(vb_id)

    # =====================================================
    # AVAILABILITY SLOTS
    # =====================================================

    def create_availability_slots(
        self, vb_id: str, slots: List[AvailabilitySlotCreate]
    ) -> List[dict]:
        """
        Create availability slots for a VB.

        Args:
            vb_id: Venture builder ID.
            slots: List of availability slot configurations.

        Returns:
            List of created/updated slots.
        """
        logger.info(f"Creating availability slots for VB {vb_id}")
        slot_data = [s.model_dump(mode='json') for s in slots]
        return self.data_access.create_availability_slots(vb_id, slot_data)

    def get_availability_slots(self, vb_id: str) -> List[dict]:
        """
        Get availability slots for a VB.

        Args:
            vb_id: Venture builder ID.

        Returns:
            List of availability slots.
        """
        return self.data_access.get_availability_slots(vb_id)

    def delete_availability_slots(
        self, vb_id: str, slots: List[AvailabilitySlotIdentifier]
    ) -> int:
        """
        Delete specific availability slots for a VB.

        Args:
            vb_id: Venture builder ID.
            slots: List of slot identifiers (day_of_week + session_start).

        Returns:
            Number of deleted slots.
        """
        slot_data = [s.model_dump(mode='json') for s in slots]
        return self.data_access.delete_availability_slots(vb_id, slot_data)

    def get_available_slots(
        self, vb_id: str, start_date: datetime, end_date: datetime
    ) -> List[dict]:
        """
        Get available booking slots for a VB.

        Combines configured slots, Yuba sessions, and Google Calendar busy times.

        Args:
            vb_id: Venture builder ID.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            List of available time slots.
        """
        calendar_service = get_google_calendar_service()
        slots = calendar_service.compute_available_slots(vb_id, start_date, end_date)
        return [{"start": s.start.isoformat(), "end": s.end.isoformat(), "available": s.available} for s in slots]

    # =====================================================
    # VB INTEREST SUBMISSIONS
    # =====================================================

    def create_interest_submission(self, submission_data: dict) -> dict:
        """
        Create a new VB interest submission (public endpoint).
        
        Args:
            submission_data: Dict containing all form fields from VBInterestSubmissionCreate
            
        Returns:
            Dict with submission info and confirmation message
            
        Raises:
            VBAlreadyExistsError: If email already has a submission
        """
        email = submission_data.get("work_email", "").lower()
        
        # Check for duplicate email
        if self.data_access.check_interest_email_exists(email):
            raise VBAlreadyExistsError(f"A submission with email {email} already exists")
        
        # Prepare data for database
        db_data = {
            # Personal Information
            "full_name": submission_data["full_name"],
            "work_email": email,
            "phone_country_code": submission_data["phone_country_code"].upper(),
            "phone_number": submission_data["phone_number"],
            "country": submission_data["country"],
            "city": submission_data["city"],
            
            # Professional Profile
            "primary_role": submission_data["primary_role"],
            "company_organization": submission_data.get("company_organization"),
            "linkedin_url": submission_data["linkedin_url"],
            "personal_website": submission_data.get("personal_website"),
            
            # Venture Building Experience
            "has_founded_venture": submission_data["has_founded_venture"],
            "ventures_founded_count": submission_data.get("ventures_founded_count"),
            "ventures_stage_reached": submission_data.get("ventures_stage_reached"),
            "ventures_outcome": submission_data.get("ventures_outcome"),
            "coaching_experience": submission_data["coaching_experience"],
            "programs_worked_with": submission_data.get("programs_worked_with"),
            
            # Expertise & Coverage (convert enums to their .value strings for JSONB)
            "support_areas": [a.value if hasattr(a, 'value') else a for a in submission_data["support_areas"]],
            "support_areas_other": submission_data.get("support_areas_other"),
            "industries_of_focus": [i.value if hasattr(i, 'value') else i for i in submission_data["industries_of_focus"]],
            "industries_other": submission_data.get("industries_other"),
            "founder_stages": [f.value if hasattr(f, 'value') else f for f in submission_data["founder_stages"]],
            "founder_stages_other": submission_data.get("founder_stages_other"),
            "geographies": [g.value if hasattr(g, 'value') else g for g in submission_data["geographies"]],
            "geographies_specific_countries": submission_data.get("geographies_specific_countries"),
            "languages": [l.value if hasattr(l, 'value') else l for l in submission_data["languages"]],
            "languages_other": submission_data.get("languages_other"),
            "weekly_availability": submission_data["weekly_availability"].value if hasattr(submission_data["weekly_availability"], 'value') else submission_data["weekly_availability"],
            "weekly_availability_other": submission_data.get("weekly_availability_other"),
            "hourly_rate_usd": float(submission_data["hourly_rate_usd"]),
            
            # Status
            "status": "pending",
        }
        
        # Create submission
        submission = self.data_access.create_interest_submission(db_data)
        
        return {
            "id": submission["id"],
            "full_name": submission["full_name"],
            "work_email": submission["work_email"],
            "status": submission["status"],
            "message": "Thank you for your interest! Our team will review your submission and get back to you within 3-5 business days.",
            "created_at": submission["created_at"],
        }

    def get_interest_submission_by_id(self, submission_id: str) -> Optional[dict]:
        """
        Get full submission details by ID (admin only).
        
        Args:
            submission_id: UUID of the submission
            
        Returns:
            Full submission record or None
        """
        return self.data_access.get_interest_submission_by_id(submission_id)

    def get_interest_submission_status(self, email: str) -> Optional[dict]:
        """
        Get submission status by email (public, limited fields).
        
        Args:
            email: Email to look up
            
        Returns:
            Dict with email, status, and submitted_at or None
        """
        submission = self.data_access.get_interest_submission_by_email(email)
        
        if not submission:
            return None
        
        return {
            "email": submission["work_email"],
            "status": submission["status"],
            "submitted_at": submission["created_at"],
        }

    def list_interest_submissions(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int, bool]:
        """
        List interest submissions with filters (admin only).
        
        Args:
            status: Filter by status
            search: Search by name or email
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Tuple of (items, total_count, has_next)
        """
        offset = (page - 1) * page_size
        items, total_count = self.data_access.list_interest_submissions(
            status=status,
            search=search,
            limit=page_size,
            offset=offset,
        )
        
        has_next = (offset + len(items)) < total_count
        
        return items, total_count, has_next

    def approve_interest_submission(
        self,
        submission_id: str,
        admin_user_id: str,
        admin_notes: Optional[str] = None,
    ) -> dict:
        """
        Approve a submission and send VB invitation.
        
        Args:
            submission_id: UUID of the submission
            admin_user_id: ID of the admin approving
            admin_notes: Optional notes
            
        Returns:
            Dict with approval result and invitation info
            
        Raises:
            VBNotFoundError: If submission not found
            VBValidationError: If submission is not pending
        """
        # Get submission
        submission = self.data_access.get_interest_submission_by_id(submission_id)
        
        if not submission:
            raise VBNotFoundError(f"Interest submission {submission_id} not found")
        
        if submission["status"] != "pending":
            raise VBValidationError(f"Submission is already {submission['status']}, cannot approve")
        
        # Update status to approved
        self.data_access.update_interest_submission(
            submission_id,
            {
                "status": "approved",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.utcnow().isoformat(),
                "admin_notes": admin_notes,
            }
        )
        
        # Send VB invitation using existing method
        try:
            invitation_result = self.send_vb_invitation(
                email=submission["work_email"],
                invited_by_user_id=admin_user_id,
                invited_by_email="system@yuba.ai",  # System-generated invitation
            )
            
            # Update status to invited and link invitation
            self.data_access.update_interest_submission(
                submission_id,
                {
                    "status": "invited",
                    "vb_invitation_id": invitation_result.get("invitation_id"),
                }
            )
            
            return {
                "submission_id": submission_id,
                "status": "invited",
                "invitation_sent": True,
                "invitation_token": invitation_result.get("token"),
                "message": f"Submission approved and invitation sent to {submission['work_email']}",
            }
        except Exception as e:
            # If invitation fails, keep as approved
            logger.error(f"Failed to send invitation for submission {submission_id}: {e}")
            return {
                "submission_id": submission_id,
                "status": "approved",
                "invitation_sent": False,
                "invitation_token": None,
                "message": f"Submission approved but invitation failed: {str(e)}",
            }

    def reject_interest_submission(
        self,
        submission_id: str,
        admin_user_id: str,
        admin_notes: Optional[str] = None,
    ) -> dict:
        """
        Reject a submission and send rejection notification email.
        
        Args:
            submission_id: UUID of the submission
            admin_user_id: ID of the admin rejecting
            admin_notes: Optional internal admin notes
            
        Returns:
            Dict with rejection result
            
        Raises:
            VBNotFoundError: If submission not found
            VBValidationError: If submission is not pending
        """
        # Get submission
        submission = self.data_access.get_interest_submission_by_id(submission_id)
        
        if not submission:
            raise VBNotFoundError(f"Interest submission {submission_id} not found")
        
        if submission["status"] != "pending":
            raise VBValidationError(f"Submission is already {submission['status']}, cannot reject")
        
        # Update status to rejected
        self.data_access.update_interest_submission(
            submission_id,
            {
                "status": "rejected",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.utcnow().isoformat(),
                "admin_notes": admin_notes,
            }
        )
        
        # Send rejection notification email (include admin_notes as feedback if provided)
        email_sent = False
        try:
            email_sent = email_service.send_vb_interest_rejection_email(
                to_email=submission["work_email"],
                applicant_name=submission["full_name"],
                admin_notes=admin_notes,
            )
            if email_sent:
                logger.info(f"VB interest rejection email sent to {submission['work_email']}")
            else:
                logger.warning(f"Failed to send VB interest rejection email to {submission['work_email']}")
        except Exception as e:
            logger.error(f"Error sending VB interest rejection email: {e}")
        
        return {
            "submission_id": submission_id,
            "status": "rejected",
            "email_sent": email_sent,
            "message": "Submission rejected",
        }

    def update_interest_submission_notes(
        self,
        submission_id: str,
        admin_notes: str,
    ) -> dict:
        """
        Update admin notes on a submission.
        
        Args:
            submission_id: UUID of the submission
            admin_notes: New admin notes
            
        Returns:
            Updated submission
            
        Raises:
            VBNotFoundError: If submission not found
        """
        # Check submission exists
        submission = self.data_access.get_interest_submission_by_id(submission_id)
        
        if not submission:
            raise VBNotFoundError(f"Interest submission {submission_id} not found")
        
        # Update notes
        updated = self.data_access.update_interest_submission(
            submission_id,
            {"admin_notes": admin_notes}
        )
        
        return updated


# Singleton instance
_service_instance: Optional[VBService] = None


def get_vb_service() -> VBService:
    """Get VB service singleton"""
    global _service_instance
    if _service_instance is None:
        _service_instance = VBService()
    return _service_instance
