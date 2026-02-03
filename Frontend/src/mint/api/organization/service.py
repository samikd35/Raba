"""
Organization service for CRUD operations and business logic.

This service handles all organization-related operations including
admin management and public access for signup forms.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv
from fastapi import HTTPException
from itsdangerous import BadSignature, SignatureExpired
from src.mint.utils.url_safe_serializer import serializer

from ..auth_v2.service import AuthService
from ..credit.service import CreditService
from ..services.communication.email_service import email_service
from ..system.core.supabase_client import (get_service_role_client,
                                           get_standard_client)
from ..tenant.models import TenantMembership, TenantMembershipResponse
from ..tenant.service import TenantService

logger = logging.getLogger(__name__)
load_dotenv()


class OrganizationService:
    """Service class for organization operations."""

    _PURCHASE_SOURCES = ("purchase", "payment", "top_up")

    def __init__(self, use_service_role: bool = False):
        """
        Initialize the organization service.

        Args:
            use_service_role: Whether to use service role client (for admin operations)
        """
        self.client = (
            get_service_role_client() if use_service_role else get_standard_client()
        )

    def record_invitation(
        self,
        organization_id: str,
        email: str,
        is_admin: bool,
        is_team_leader: bool,
        invited_by_user_id: Optional[str],
        invited_by_email: Optional[str],
        credits: Optional[int] = 0,
        cohort_id: Optional[str] = None,
        can_skip_modules: bool = False,
    ) -> Dict[str, Any]:
        """
        Insert invitation row with status='queued'.
        Uses service role client in this service to bypass RLS.
        """
        try:
            existing = (
                self.client.client.table("organization_invitations")
                .select("*")
                .eq("organization_id", organization_id)
                .eq("email", email)
                .in_("status", ["queued", "sent", "accepted"])
                .limit(1)
                .execute()
            )
            if existing.data:
                # ✅ UPDATE existing invitation with new values instead of returning old one
                existing_invitation = existing.data[0]
                update_payload = {
                    "is_admin": is_admin,
                    "is_team_leader": is_team_leader,
                    "credits": credits,
                    "invited_by": invited_by_user_id,
                    "invited_by_email": invited_by_email,
                    "status": "queued",  # Reset to queued for re-sending
                    "cohort_id": cohort_id,
                    "can_skip_modules": can_skip_modules,
                }

                logger.info(
                    f"🔍 UPDATING existing invitation {existing_invitation['id']} with: is_team_leader={is_team_leader}"
                )

                updated = (
                    self.client.client.table("organization_invitations")
                    .update(update_payload)
                    .eq("id", existing_invitation["id"])
                    .execute()
                )

                if updated.data:
                    return updated.data[0]
                else:
                    return existing_invitation
        except Exception as e:
            logger.error(f"record_invitation: lookup failed: {e}")

        payload = {
            "organization_id": organization_id,
            "email": email,
            "is_admin": is_admin,
            "is_team_leader": is_team_leader,
            "invited_by": invited_by_user_id,
            "invited_by_email": invited_by_email,
            "status": "queued",
            "credits": credits,
            "cohort_id": cohort_id,
            "can_skip_modules": can_skip_modules,
        }
        
        logger.info(f"📧 INSERTING NEW INVITATION: org={organization_id}, email={email}")
        
        res = (
            self.client.client.table("organization_invitations")
            .insert(payload)
            .execute()
        )

        # FIXED: Inverted condition - should raise if insert FAILED (no data), not if it succeeded
        if not res or not res.data:
            logger.error(f"❌ INVITATION INSERT FAILED: org={organization_id}, email={email}, res={res}")
            raise HTTPException(
                status_code=500,
                detail="Failed to record invitation in database.",
            )
        
        logger.info(f"✅ INVITATION INSERTED: id={res.data[0].get('id')}, status={res.data[0].get('status')}")
        return res.data[0]

    def update_invitation_status(
        self,
        invitation_id: Optional[str],
        status: str,
        sent_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update status/sent_at/error for an invitation row.
        Safe to no-op if invitation_id is None.
        """
        if not invitation_id:
            return
        update: Dict[str, Any] = {"status": status}
        if sent_at is not None:
            # keep explicit UTC
            update["sent_at"] = (
                sent_at.isoformat() if isinstance(sent_at, datetime) else str(sent_at)
            )
        if error:
            update["error"] = error
        self.client.client.table("organization_invitations").update(update).eq(
            "id", invitation_id
        ).execute()

    def update_payed_invitation_status(
        self,
        invitation_id: Optional[str],
        status: str,
        sent_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update status/email_sent_at/error for an invitation row.
        Safe to no-op if invitation_id is None.
        """
        if not invitation_id:
            return
        update: Dict[str, Any] = {"status": status}
        if sent_at is not None:
            # keep explicit UTC
            update["email_sent_at"] = (
                sent_at.isoformat() if isinstance(sent_at, datetime) else str(sent_at)
            )
        if error:
            update["error"] = error
        self.client.client.table("organization_payment_invitations").update(update).eq(
            "id", invitation_id
        ).execute()

    def _norm_email(self, email: str) -> str:
        return (email or "").strip()

    def _has_invite(self, tenant_id: str, email: str) -> bool:
        """Check if user has an outstanding invite."""
        try:
            normalized_email = self._norm_email(email)
            logger.info(
                f"🔍 Checking invite for org {tenant_id}, email: '{email}' -> normalized: '{normalized_email}'"
            )

            res = (
                self.client.client.table("organization_invitations")
                .select("id")
                .eq("organization_id", tenant_id)
                .eq("email", normalized_email)
                .in_("status", ["queued", "sent"])
                .limit(1)
                .execute()
            )

            logger.info(
                f"🔍 Invite check result: {len(res.data) if res.data else 0} invitations found"
            )
            return bool(res.data)
        except Exception as e:
            logger.error(f"Failed to check invite: {e}")
            return False

    def _has_admin_invite(self, tenant_id: str, email: str) -> bool:
        """Check if user has an outstanding admin invite."""
        try:
            res = (
                self.client.client.table("organization_invitations")
                .select("id")
                .eq("organization_id", tenant_id)
                .eq("email", self._norm_email(email))
                .eq("is_admin", True)
                .in_("status", ["queued", "sent"])
                .limit(1)
                .execute()
            )
            return bool(res.data)
        except Exception as e:
            logger.error(f"Failed to check admin invite: {e}")
            return False

    def _accept_matching_invites(
        self, tenant_id: str, email: str, role: str, user_id: str
    ) -> Optional[str]:
        """
        Mark outstanding invites as accepted when user joins.
        Returns the cohort_id if one was specified in the invitation, for later assignment.
        """
        try:
            # First, fetch the invitation to get cohort_id
            invitation_res = (
                self.client.client.table("organization_invitations")
                .select("id, cohort_id")
                .eq("organization_id", tenant_id)
                .eq("email", self._norm_email(email))
                .in_("status", ["queued", "sent"])
                .limit(1)
                .execute()
            )

            cohort_id = None
            if invitation_res.data and invitation_res.data[0].get("cohort_id"):
                cohort_id = invitation_res.data[0].get("cohort_id")

            # Mark invitation as accepted
            now = datetime.now(timezone.utc).isoformat()
            (
                self.client.client.table("organization_invitations")
                .update(
                    {
                        "status": "accepted",
                        "accepted_at": now,
                        "accepted_by": user_id,
                        "accepted_role": role,
                    }
                )
                .eq("organization_id", tenant_id)
                .eq("email", self._norm_email(email))
                .in_("status", ["queued", "sent"])
                .execute()
            )

            # Return cohort_id for later assignment (after individual tenant is created)
            return cohort_id

        except Exception as e:
            logger.error(f"Failed to accept invites for {email}: {e}")
            return None

    def _assign_to_cohort_if_needed(
        self, cohort_id: Optional[str], individual_tenant_id: str, user_id: str
    ) -> None:
        """
        Assign an individual tenant to a cohort if a cohort_id was specified.
        This should be called after the individual tenant is created.
        """
        if not cohort_id:
            return

        try:
            from ..billing.cohort_service import CohortService
            cohort_service = CohortService(use_service_role=True)

            # Assign tenant to cohort using the individual tenant ID
            cohort_service.assign_member_to_cohort(
                cohort_id=cohort_id,
                member_tenant_id=individual_tenant_id
            )
            logger.info(f"Assigned tenant {individual_tenant_id} (user {user_id}) to cohort {cohort_id} from invitation")
        except Exception as cohort_err:
            # Don't fail the join if cohort assignment fails - just log it
            logger.error(f"Failed to assign tenant {individual_tenant_id} to cohort {cohort_id}: {cohort_err}", exc_info=True)

    def _has_team_leader_invite(self, tenant_id: str, email: str) -> bool:
        """Check if user has an outstanding team_leader invite."""
        try:
            res = (
                self.client.client.table("organization_invitations")
                .select("id")
                .eq("organization_id", tenant_id)
                .eq("email", self._norm_email(email))
                .eq("is_team_leader", True)
                .in_("status", ["queued", "sent"])
                .limit(1)
                .execute()
            )
            return bool(res.data)
        except Exception as e:
            logger.error(f"Failed to check team_leader invite: {e}")
            return False

    async def join_organization(
        self,
        tenant_id: str,
        user_id: str,
        user_email: str,
        request_admin: bool,
        credit_amount: Optional[int] = 0,
    ) -> TenantMembershipResponse:
        """Create or update membership for user in an org tenant."""
        logger.info(
            f"🚀 Starting join_organization: tenant_id={tenant_id}, user_id={user_id}, user_email={user_email}, request_admin={request_admin}, credit_amount={credit_amount}"
        )
        try:
            # Verify tenant exists
            t_res = (
                self.client.client.table("tenants")
                .select("id, tenant_type")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            if not t_res.data or t_res.data[0].get("tenant_type") != "organization":
                return TenantMembershipResponse(
                    success=False, message="Organization not found", data=None
                )

            logger.info(
                f"🔍 About to check invite for user {user_email} in org {tenant_id}"
            )
            has_invite = self._has_invite(tenant_id, user_email)
            logger.info(f"🔍 Invite check result: {has_invite}")

            if not has_invite:
                logger.error(
                    f"❌ User {user_email} doesn't have an invite to join org {tenant_id}"
                )
                return TenantMembershipResponse(
                    success=False,
                    message="User doesn't have an invite to join this org",
                    data=None,
                )

            # Determine role
            is_team_leader_invited = self._has_team_leader_invite(tenant_id, user_email)
            can_admin = request_admin and self._has_admin_invite(tenant_id, user_email)
            target_role = "admin" if can_admin else "member"
            tenant_service = TenantService()
            auth_service = AuthService()

            now = datetime.now(timezone.utc).isoformat()

            # Check for existing membership first to determine if admin seat charge needed
            existing = (
                self.client.client.table("tenant_memberships")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

            # Check organization type for admin seat billing
            org_config_response = self.client.client.table('organization_billing_config') \
                .select('organization_type') \
                .eq('tenant_id', tenant_id) \
                .limit(1) \
                .execute()

            org_type = 'grant_org'  # default
            if org_config_response.data and len(org_config_response.data) > 0:
                org_type = org_config_response.data[0].get('organization_type', 'grant_org')

            # Handle admin seat costs if joining/upgrading to admin
            # Only charge if: (1) joining as admin AND (2) not already an admin
            admin_seat_cost = 0
            is_upgrading_to_admin = (
                target_role == "admin" and
                (not existing.data or existing.data[0].get("role") != "admin")
            )

            if is_upgrading_to_admin:
                from ..billing.service import BillingService
                billing_service = BillingService()
                pricing_config = billing_service.get_pricing_config()
                admin_seat_cost = pricing_config['admin_seat_price_credits']

                if org_type == 'postpay_org':
                    # Track admin seat cost for later billing
                    try:
                        allocation_payload = {
                            'tenant_id': tenant_id,
                            'allocation_type': 'admin_seat_allocation',
                            'credit_amount': float(admin_seat_cost),
                            'allocated_to_user_id': user_id,
                            'allocated_by_user_id': user_id,
                            'allocated_at': now,
                            'metadata': {
                                'reason': 'admin_seat_cost',
                                'user_email': user_email,
                                'seat_price': admin_seat_cost
                            }
                        }

                        self.client.client.table('organization_credit_allocations') \
                            .insert(allocation_payload) \
                            .execute()

                        logger.info(f"Tracked admin seat cost ({admin_seat_cost} credits) for user {user_email} in postpay_org {tenant_id}")
                    except Exception as e:
                        logger.error(f"Failed to track admin seat cost for postpay_org: {e}", exc_info=True)
                        # Don't fail the join if tracking fails

                elif org_type == 'prepay_org':
                    # Deduct admin seat cost immediately for prepay orgs
                    try:
                        credit_service = CreditService()
                        available = credit_service.get_available_credits(tenant_id)

                        if available < admin_seat_cost:
                            return TenantMembershipResponse(
                                success=False,
                                message=f"Organization has insufficient credits for admin seat (need {admin_seat_cost}, have {available})",
                                data=None,
                            )

                        self.deduct_credits(tenant_id, admin_seat_cost)
                        logger.info(f"Deducted admin seat cost ({admin_seat_cost} credits) for user {user_email} from prepay_org {tenant_id}")
                    except Exception as e:
                        logger.error(f"Failed to deduct admin seat cost: {e}", exc_info=True)
                        return TenantMembershipResponse(
                            success=False,
                            message="Failed to process admin seat cost",
                            data=None,
                        )

                # grant_org: no admin seat charges

            membership_existed = bool(existing.data)
            pending_cohort_id = None  # Will be set from invitation if applicable

            if existing.data:
                membership = existing.data[0]
                updates: Dict[str, Any] = {}

                if not membership.get("is_active", True):
                    updates["is_active"] = True
                    updates["joined_at"] = now

                if membership.get("role") != "admin" and target_role == "admin":
                    updates["role"] = "admin"
                    updates["permissions"] = tenant_service._get_default_permissions(
                        "admin"
                    )

                if updates:
                    updated = (
                        self.client.client.table("tenant_memberships")
                        .update(updates)
                        .eq("id", membership["id"])
                        .execute()
                    )
                    membership = updated.data[0] if updated.data else membership

                pending_cohort_id = self._accept_matching_invites(
                    tenant_id, user_email, membership.get("role"), user_id
                )

                logger.info(
                    f"✅ Updated existing membership for user {user_email} in org {tenant_id}"
                )
            else:
                # Insert new membership
                payload = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "role": target_role,
                    "is_active": True,
                    "permissions": tenant_service._get_default_permissions(target_role),
                }

                inserted = (
                    self.client.client.table("tenant_memberships").insert(payload).execute()
                )

                if not inserted.data:
                    return TenantMembershipResponse(
                        success=False, message="Failed to create membership", data=None
                    )

                membership = inserted.data[0]
                pending_cohort_id = self._accept_matching_invites(tenant_id, user_email, target_role, user_id)

                logger.info(
                    f"✅ Created new membership for user {user_email} in org {tenant_id}"
                )

            # Create individual tenant and allocate credits for members and admins
            # This runs for BOTH new and existing memberships (e.g., user was team member first)
            # Only skip for team leaders (their credits go to pending_team_credits)
            if not is_team_leader_invited and credit_amount and credit_amount > 0:
                credit_service = CreditService()
                
                # Check if user already has an individual tenant for this org
                # If they do, we should NOT allocate credits again (avoid double allocation)
                existing_individual = (
                    self.client.client.table("org_individuals")
                    .select("individual_tenant_id")
                    .eq("organization_id", tenant_id)
                    .eq("user_id", user_id)
                    .limit(1)
                    .execute()
                )
                
                if existing_individual.data:
                    # User already has individual tenant - skip credit allocation
                    # This happens if they were invited again after already being onboarded
                    logger.info(
                        f"⚠️ User {user_email} already has individual tenant in org {tenant_id}, "
                        f"skipping credit allocation to avoid duplicates"
                    )
                    # But still assign to cohort if specified in invitation
                    if pending_cohort_id:
                        existing_tenant_id = existing_individual.data[0]['individual_tenant_id']
                        self._assign_to_cohort_if_needed(pending_cohort_id, existing_tenant_id, user_id)
                else:
                    # User doesn't have individual tenant yet - create and allocate credits
                    logger.info(
                        f"🔨 Creating individual tenant and allocating {credit_amount} credits "
                        f"for user {user_email} in org {tenant_id}"
                    )

                    # For non-postpay orgs, fetch and validate credit lots
                    org_lots = []
                    if org_type != 'postpay_org':
                        # Fetch active lots sorted by expiry, filtered by org type
                        # Note: Removed .or_() as Supabase Python client doesn't support it
                        # Expiration and reservation filtering done in Python
                        lots_query = (
                            self.client.client.table("credit_lots")
                            .select("id, credit_amount, expires_at, source, reserved_until")
                            .eq("tenant_id", tenant_id)
                            .eq("is_active", True)
                            .lte("valid_from", now)
                            .order("expires_at", desc=False)
                        )

                        # Filter by source based on organization type
                        if org_type == 'grant_org':
                            # Grant organizations: only use granted credits
                            lots_query = lots_query.eq("source", "grant")
                        elif org_type == 'prepay_org':
                            # Prepay organizations: only use purchased credits
                            lots_query = lots_query.in_("source", list(self._PURCHASE_SOURCES))

                        org_lots = lots_query.execute().data or []

                        # Filter out expired and reserved lots in Python
                        valid_lots = []
                        for lot in org_lots:
                            expires_at = lot.get("expires_at")
                            reserved_until = lot.get("reserved_until")

                            # Check if expired
                            is_expired = False
                            if expires_at is not None:
                                try:
                                    exp_str = str(expires_at).replace("Z", "+00:00")
                                    is_expired = exp_str <= now
                                except:
                                    pass

                            # Check if reserved
                            is_reserved = False
                            if reserved_until is not None:
                                try:
                                    res_str = str(reserved_until).replace("Z", "+00:00")
                                    is_reserved = res_str > now
                                except:
                                    pass

                            if not is_expired and not is_reserved:
                                valid_lots.append(lot)

                        total_available = sum(float(lot["credit_amount"]) for lot in valid_lots)
                        if total_available < credit_amount:
                            return TenantMembershipResponse(
                                success=False,
                                message="Organization has insufficient credits to allocate",
                                data=None,
                            )

                    user = auth_service.get_user_by_email(user_email)
                    if not user:
                        raise HTTPException(
                            status_code=401, detail="Invalid email or password"
                        )

                    # Get or create the user's individual tenant for this organization
                    individual_tenant = await self.create_individual_tenant_for_org(
                        org_id=tenant_id,
                        user_id=user_id,
                        user_email=user_email,
                        user_full_name=user.get("full_name", "user"),
                    )

                    if not individual_tenant:
                        return TenantMembershipResponse(
                            success=False,
                            message="Failed to create individual tenant",
                            data=None,
                        )

                    user_tenant_id = individual_tenant["id"]

                    if org_type == 'postpay_org':
                        # For postpay orgs, create credit lot without deducting from org
                        # No expiry for postpay credits
                        created_lot = credit_service.create_credit_lot(
                            tenant_id=user_tenant_id,
                            source="purchase",
                            credit_amount=Decimal(str(credit_amount)),
                            valid_from=now,
                            expires_at=None,  # No expiry
                            metadata={
                                "source": "organization_transfer",
                                "organization_id": tenant_id,
                                "transferred_by_invite": True,
                            },
                            original_tenant_id=tenant_id,
                        )

                        # Record allocation for billing
                        try:
                            self.client.client.table('organization_credit_allocations').insert({
                                'tenant_id': tenant_id,
                                'allocation_type': 'allocation_to_member',
                                'credit_amount': float(credit_amount),
                                'credit_lot_id': created_lot.get('id') if created_lot else None,
                                'allocated_to_tenant_id': user_tenant_id,
                                'allocated_to_user_id': user_id,
                                'allocated_by_user_id': user_id,
                                'allocated_at': now,
                                'metadata': {
                                    "source": "join_organization",
                                    "invite_redemption": True
                                },
                            }).execute()
                            logger.info(
                                f"Recorded postpay member allocation for org {tenant_id}: "
                                f"{credit_amount} credits to user {user_id}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to record postpay allocation: {e}", exc_info=True)
                    else:
                        # For grant_org and prepay_org, deduct from org lots
                        remaining = Decimal(str(credit_amount))

                        for lot in org_lots:
                            if remaining <= 0:
                                break
                            lot_credits = Decimal(str(lot["credit_amount"]))
                            deduct = min(lot_credits, remaining)
                            new_balance = lot_credits - deduct

                            # Update org lot balance
                            self.client.client.table("credit_lots").update(
                                {"credit_amount": float(new_balance)}
                            ).eq("id", lot["id"]).execute()

                            # Determine expiry based on org type
                            # grant_org: use lot's expiry; prepay_org: no expiry
                            lot_expires_at = lot["expires_at"] if org_type == 'grant_org' else None

                            # Create new credit lot for user
                            credit_service.create_credit_lot(
                                tenant_id=user_tenant_id,
                                source=lot["source"],
                                credit_amount=deduct,
                                valid_from=now,
                                expires_at=lot_expires_at,
                                metadata={
                                    "source": "organization_transfer",
                                    "organization_id": tenant_id,
                                    "origin_lot_id": lot["id"],
                                    "transferred_by_invite": True,
                                },
                                original_tenant_id=tenant_id,
                            )

                            remaining -= deduct

                    logger.info(
                        f"✅ Successfully created individual tenant {user_tenant_id} "
                        f"and allocated {credit_amount} credits for user {user_email}"
                    )

                    # Assign to cohort if specified in invitation (now that we have the individual tenant)
                    if pending_cohort_id:
                        self._assign_to_cohort_if_needed(pending_cohort_id, user_tenant_id, user_id)

            elif is_team_leader_invited and credit_amount and credit_amount > 0:
                # --- Team leader credit record logic (store for future team creation) ---
                try:
                    self.client.client.table("pending_team_credits").insert(
                        {
                            "organization_id": tenant_id,
                            "admin_email": user_email,
                            "credit_amount": float(credit_amount),
                            "created_at": now,
                            "metadata": {
                                "source": "admin_invitation",
                                "note": "Credits reserved for future team creation",
                            },
                        }
                    ).execute()

                    logger.info(
                        f"Recorded pending admin credits for {user_email} "
                        f"({credit_amount} credits) under org {tenant_id}"
                    )
                except Exception as db_e:
                    logger.error(
                        f"Failed to record pending admin credits for {user_email}: {db_e}"
                    )

            return TenantMembershipResponse(
                success=True,
                message="Joined organization",
                data=TenantMembership(**membership),
                is_team_leader=is_team_leader_invited
            )

        except Exception as e:
            logger.error(f"❌ join_organization_tenant error: {e}")
            logger.error(f"❌ Error type: {type(e)}")
            logger.error(f"❌ Error details: {str(e)}")
            import traceback

            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            return TenantMembershipResponse(
                success=False, message=f"Failed to join organization: {e}", data=None
            )

    def get_org_metrics(self, org_id: str) -> Dict[str, Any]:
        """Get invitations and membership metrics for an organization."""

        # --- Invitations ---
        try:
            invites = (
                self.client.client.table("organization_invitations")
                .select("id, status, is_team_leader")
                .eq("organization_id", org_id)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_org_metrics: failed fetching organization_invitations: {e}")
            invites = []

        num_sent = sum(
            1
            for inv in invites
            if inv["status"] != "failed" and inv["status"] != "queued"
        )
        num_accepted = sum(1 for inv in invites if inv["status"] == "accepted")
        
        # Count pending individual member invitations (is_team_leader = False or NULL)
        # Treat NULL as False (individual member)
        num_pending_individual = sum(
            1
            for inv in invites
            if inv["status"] in ["sent", "queued"] and not inv.get("is_team_leader", False)
        )
        
        # Count pending team leader invitations (is_team_leader = True explicitly)
        num_pending_team_leader = sum(
            1
            for inv in invites
            if inv["status"] in ["sent", "queued"] and inv.get("is_team_leader") is True
        )

        # --- All ACTIVE members of the organization ---
        try:
            org_memberships = (
                self.client.client.table("tenant_memberships")
                .select("user_id")
                .eq("tenant_id", org_id)
                .eq("is_active", True)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_org_metrics: failed fetching org tenant_memberships: {e}")
            org_memberships = []
        org_user_ids = {m["user_id"] for m in org_memberships}

        # --- All team_ids under this org (only active teams) ---
        try:
            org_teams = (
                self.client.client.table("org_teams")
                .select("team_id")
                .eq("organization_id", org_id)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_org_metrics: failed fetching org_teams: {e}")
            org_teams = []
        all_team_ids = [t["team_id"] for t in org_teams]
        
        # Filter to only active teams
        active_teams = []
        if all_team_ids:
            try:
                active_teams = (
                    self.client.client.table("tenants")
                    .select("id")
                    .in_("id", all_team_ids)
                    .eq("is_active", True)
                    .execute()
                ).data or []
            except Exception as e:
                logger.warning(f"get_org_metrics: failed fetching active team tenants: {e}")
                active_teams = []
        team_ids = {t["id"] for t in active_teams}

        # --- All memberships for those teams ---
        team_memberships = []
        if team_ids:
            try:
                team_memberships = (
                    self.client.client.table("tenant_memberships")
                    .select("user_id, tenant_id")
                    .in_("tenant_id", list(team_ids))
                    .execute()
                ).data or []
            except Exception as e:
                logger.warning(f"get_org_metrics: failed fetching team tenant_memberships: {e}")
                team_memberships = []

        team_user_ids = {
            m["user_id"] for m in team_memberships if m["user_id"] in org_user_ids
        }

        # Classify org users
        team_members = len(team_user_ids)
        individuals = len(org_user_ids) - len(team_user_ids)
        total_members = len(org_user_ids)

        # -----------------------------
        # Credit Summary Card
        # -----------------------------
        now_utc = datetime.now(timezone.utc)
        month_start_utc = now_utc.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        now_iso = now_utc.isoformat()
        month_start_iso = month_start_utc.isoformat()

        # Current balance from active lots (valid now and not expired)
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering done in Python below
        try:
            lots = (
                self.client.client.table("credit_lots")
                .select("credit_amount, valid_from, expires_at, is_active")
                .eq("tenant_id", org_id)
                .eq("is_active", True)
                .lte("valid_from", now_iso)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_org_metrics: failed fetching credit_lots: {e}")
            lots = []

        balance_dec = Decimal("0")

        for lot in lots:
            vf = lot.get("valid_from")
            ea = lot.get("expires_at")
            credit_amount = lot.get("credit_amount", 0)
            is_active = lot.get("is_active", True)

            # Skip inactive lots
            if not is_active:
                continue

            # More robust datetime comparison
            valid_now = True
            if vf is not None:
                try:
                    vf_dt = datetime.fromisoformat(str(vf).replace("Z", "+00:00"))
                    valid_now = vf_dt <= now_utc
                except (ValueError, TypeError):
                    valid_now = str(vf) <= now_iso  # fallback to string comparison

            not_expired = True
            if ea is not None:
                try:
                    ea_dt = datetime.fromisoformat(str(ea).replace("Z", "+00:00"))
                    not_expired = ea_dt > now_utc
                except (ValueError, TypeError):
                    not_expired = str(ea) > now_iso  # fallback to string comparison

            if valid_now and not_expired:
                balance_dec += Decimal(str(credit_amount))

        balance = float(balance_dec)

        # Used this month (sum of costs for the tenant in the current month)
        try:
            monthly_consumptions = (
                self.client.client.table("tenant_credit_consumptions")
                .select("cost, created_at")
                .eq("tenant_id", org_id)
                .gte("created_at", month_start_iso)
                .lte("created_at", now_iso)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_org_metrics: failed fetching monthly consumptions: {e}")
            monthly_consumptions = []
        used_this_month = int(
            sum(int(c.get("cost") or 0) for c in monthly_consumptions)
        )

        # Lifetime used (optional but useful if you want to expose later)
        try:
            lifetime_consumptions = (
                self.client.client.table("tenant_credit_consumptions")
                .select("cost")
                .eq("tenant_id", org_id)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_org_metrics: failed fetching lifetime consumptions: {e}")
            lifetime_consumptions = []
        used_lifetime = int(sum(int(c.get("cost") or 0) for c in lifetime_consumptions))

        # Monthly limit: try to fetch from tenants.monthly_credit_limit or tenants.preferences JSON
        monthly_limit = None
        try:
            tenant_row = (
                self.client.client.table("tenants")
                .select("monthly_credit_limit, preferences")
                .eq("id", org_id)
                .single()
                .execute()
            ).data
            if tenant_row:
                if tenant_row.get("monthly_credit_limit") is not None:
                    monthly_limit = int(tenant_row["monthly_credit_limit"])
                else:
                    prefs = tenant_row.get("preferences") or {}
                    if isinstance(prefs, dict):
                        ml = prefs.get("monthly_credit_limit") or (
                            prefs.get("credits") or {}
                        ).get("monthly_limit")
                        if ml is not None:
                            monthly_limit = int(ml)
        except Exception:
            # If schema differs, just leave monthly_limit as None
            pass

        # Derive remaining + total for the card
        if monthly_limit is not None:
            remaining_for_card = max(monthly_limit - used_this_month, 0)
            total_for_card = monthly_limit
        else:
            # No known monthly limit → fall back to "current balance" semantics
            remaining_for_card = balance
            total_for_card = (
                balance + used_this_month
            )  # approximate monthly "total" for UI

        # Compose response
        response = {
            "invitations": {
                "sent": num_sent,
                "accepted": num_accepted,
                "pending_individual": num_pending_individual,  # Pending individual member invitations
                "pending_team_leader": num_pending_team_leader,  # Pending team leader invitations
            },
            "membership": {
                "total": total_members,
                "team_members": team_members,
                "individual_members": individuals,
            },
            "credits": {
                "total": (
                    int(total_for_card)
                    if monthly_limit is not None
                    else float(total_for_card)
                ),
                "used": used_this_month,
                "remaining": (
                    int(remaining_for_card)
                    if monthly_limit is not None
                    else float(remaining_for_card)
                ),
                "monthly_limit": monthly_limit,  # may be None if not configured
                # (optional extras, keep if your response model allows)
                # "balance_now": balance,
                # "used_lifetime": used_lifetime,
                # "month_start": month_start_iso,
            },
        }

        return response

    def get_organization_billing_config(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization billing configuration including organization type and billing settings.

        Args:
            organization_id: The tenant/organization ID

        Returns:
            Dictionary with organization_type and billing_settings, or None if not found
        """
        try:
            result = (
                self.client.client.table('organization_billing_config')
                .select('organization_type, billing_settings, created_at, updated_at')
                .eq('tenant_id', organization_id)
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                logger.warning(f"No billing config found for organization {organization_id}, returning default")
                return {
                    'organization_type': 'grant_org',
                    'billing_settings': None
                }

        except Exception as e:
            logger.error(f"Error fetching billing config for organization {organization_id}: {str(e)}")
            return {
                'organization_type': 'grant_org',
                'billing_settings': None
            }

    def generate_invitation(
        self,
        email: str,
        created_by: str,
        credits: Optional[int] = None,
        org_type: Optional[str] = None,
    ) -> str:
        """Create or reuse a pending invitation row + signed token.

        If a pending invitation for (email, type='organization') already exists:
          - If credits differ, update the existing row's credits.
          - Otherwise, reuse it as-is.
        If none exists, create a new row.

        Args:
            email: Email address to invite
            created_by: User ID of the inviter
            credits: Credits to allocate (for grant organizations)
            org_type: Organization type ('grant_org', 'prepay_org', or 'postpay_org')
        """
        now = datetime.now(timezone.utc).isoformat()
        norm_email = self._norm_email(email)

        # Normalize requested credits to a Decimal to avoid float compare issues
        requested_credits = Decimal(str(credits if credits is not None else 0))
        org_type_value = org_type or "grant_org"

        # 1) Try to find an existing pending invite for this email + type
        existing = (
            self.client.client.table("app_invitations")
            .select("*")
            .eq("email", norm_email)
            .eq("type", "organization")
            .eq("status", "pending")
            .limit(1)
            .execute()
        )

        if existing.data:
            invite = existing.data[0]

            current_credits = Decimal(str(invite.get("credits") or 0))
            current_metadata = invite.get("metadata") or {}
            current_org_type = current_metadata.get("organization_type")

            # 1a) Update credits or org_type if different
            if current_credits != requested_credits or current_org_type != org_type_value:
                update_payload = {
                    "credits": float(requested_credits),
                    "metadata": {
                        **current_metadata,
                        "organization_type": org_type_value
                    },
                    "updated_at": now,
                }
                self.client.client.table("app_invitations").update(update_payload).eq(
                    "id", invite["id"]
                ).execute()
                invite.update(update_payload)
            # else: reuse as-is
        else:
            # 2) Create DB row if none exists
            payload = {
                "email": norm_email,
                "status": "pending",
                "type": "organization",
                "created_by": created_by,
                "created_at": now,
                "updated_at": now,
                "credits": float(requested_credits),
                "metadata": {
                    "organization_type": org_type_value
                },
            }
            res = self.client.client.table("app_invitations").insert(payload).execute()
            invite = res.data[0]

        # 3) Build token from the stored row to satisfy verify_invitation
        token_payload = {
            "invite_id": invite["id"],
            "email": norm_email,
            "type": "org_invitation",
            "credits": invite.get("credits"),
            "org_type": org_type
            or "grant_org",  # Default to grant_org if not specified
        }
        token = serializer.dumps(token_payload)

        # 4) Send email with correct onboarding URL
        frontend_url = os.getenv("FRONTEND_URL", "")
        org_type_param = org_type or "grant_org"
        link = f"{frontend_url}/onboarding?token={token}&type={org_type_param}"

        email_sent = email_service.send_org_admin_creation_invite_email(
            to_email=norm_email, invite_link=link
        )
        if not email_sent:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong trying to send the message",
            )

        return token

    def verify_invitation(self, token: str, max_age: int = 172800) -> Dict[str, Any]:
        """Verify token + ensure invitation exists and is valid in DB."""
        try:
            data = serializer.loads(token, max_age=max_age)
            if data.get("type") != "org_invitation":
                raise ValueError("Invalid invitation token type")

            # Check DB for invitation
            res = (
                self.client.client.table("app_invitations")
                .select("*")
                .eq("id", data["invite_id"])
                .execute()
            )
            if not res.data:
                raise ValueError("Invitation not found")

            invite = res.data[0]

            db_credits = invite.get("credits")
            token_credits = data.get("credits")

            if (
                invite["status"] != "pending"
                or invite["type"] != "organization"
                or (
                    (db_credits is not None and token_credits is not None)
                    and Decimal(str(db_credits)) != Decimal(str(token_credits))
                )
            ):
                logger.warning(
                    f"Invitation validation failed: status={invite['status']}, type={invite['type']}"
                )
                raise ValueError("Invitation already used or invalid")

            return invite

        except SignatureExpired:
            raise ValueError("Invitation has expired")
        except BadSignature:
            raise ValueError("Invalid invitation token")

    def _get_default_permissions(self, role: str) -> Dict[str, Any]:
        """Get default permissions for a role"""
        permissions = {
            "owner": {
                "can_manage_tenant": True,
                "can_manage_members": True,
                "can_manage_billing": True,
                "can_view_analytics": True,
                "can_manage_projects": True,
            },
            "admin": {
                "can_manage_tenant": False,
                "can_manage_members": True,
                "can_manage_billing": False,
                "can_view_analytics": True,
                "can_manage_projects": True,
            },
            "member": {
                "can_manage_tenant": False,
                "can_manage_members": False,
                "can_manage_billing": False,
                "can_view_analytics": False,
                "can_manage_projects": True,
            },
        }
        return permissions.get(role, permissions["member"])

    def create_organization_tenant(
        self, user_id: str, body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create an org only if user has a valid app invitation."""

        now = datetime.now(timezone.utc).isoformat()

        # --- Step 1: Verify invitation ---
        invite = self.verify_invitation(body["invite_token"])

        # --- Step 2: Create org tenant ---
        org_payload = {
            "name": body["name"],
            "tenant_type": "organization",
            "city": body["city"],
            "contact_email": body["contact_email"],
            "phone_number": body["phone_number"],
            "description": body.get("description"),
            "website": body.get("website"),
            "industry": body.get("industry"),
            "size": body.get("size"),
            "country": body.get("country"),
            "settings": body.get("settings") or {},
            "is_active": True,
        }

        res = self.client.client.table("tenants").insert(org_payload).execute()
        if not res.data:
            return None
        org = res.data[0]

        # --- Step 2.5: Create organization billing config ---
        # Extract organization type from invitation metadata
        org_type = invite.get("metadata", {}).get("organization_type", "grant_org")

        billing_config_payload = {
            "tenant_id": org["id"],
            "organization_type": org_type,
            "billing_settings": {
                "billing_day_of_month": 1,
                "timezone": "UTC"
            },
            "created_at": now,
            "updated_at": now
        }

        try:
            billing_config_res = (
                self.client.client.table("organization_billing_config")
                .insert(billing_config_payload)
                .execute()
            )
            logger.info(f"Created billing config for organization {org['id']} with type {org_type}")
        except Exception as e:
            logger.error(f"Failed to create billing config for org {org['id']}: {e}")
            # Don't fail organization creation if billing config fails
            # This can be fixed manually by admin

        # --- Step 3: Add creator as owner ---
        permissions = self._get_default_permissions("owner")
        membership_payload = {
            "tenant_id": org["id"],
            "user_id": user_id,
            "role": "owner",
            "is_active": True,
            "joined_at": now,
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
        }
        self.client.client.table("tenant_memberships").insert(
            membership_payload
        ).execute()

        credits = invite.get("credits")

        if credits is not None and credits > 0:
            # grant_org gets 1 year expiry, prepay_org/postpay_org get no expiry
            expires_at = None
            if org_type == 'grant_org':
                expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()  # 1 year

            credit_lot_payload = {
                "tenant_id": org["id"],
                "original_tenant_id": org["id"],
                "source": "grant" if org_type == 'grant_org' else "purchase",
                "credit_amount": float(credits),  # Ensure it's a float
                "valid_from": now,
                "expires_at": expires_at,
                "metadata": {
                    "source": "invitation",
                    "invitation_id": invite["id"],
                    "invited_by": invite.get("created_by"),
                    "email": invite["email"],
                },
                "created_at": now,
            }

            try:
                credit_result = (
                    self.client.client.table("credit_lots")
                    .insert(credit_lot_payload)
                    .execute()
                )
                logger.info(f"Allocated {credits} credits to organization {org['id']}")

                # For postpay_org, record this initial grant allocation
                if org_type == 'postpay_org' and credit_result.data and len(credit_result.data) > 0:
                    try:
                        created_lot = credit_result.data[0]
                        allocation_payload = {
                            'tenant_id': org["id"],
                            'allocation_type': 'grant',
                            'credit_amount': float(credits),
                            'credit_lot_id': created_lot.get('id'),
                            'allocated_at': now,
                            'metadata': {
                                'source': 'invitation',
                                'invitation_id': invite["id"],
                                'invited_by': invite.get("created_by"),
                                'email': invite["email"],
                            }
                        }

                        self.client.client.table('organization_credit_allocations') \
                            .insert(allocation_payload) \
                            .execute()

                        logger.info(f"Recorded initial grant allocation for postpay_org {org['id']}: {credits} credits")
                    except Exception as track_error:
                        logger.error(f"Failed to record initial grant allocation for postpay_org {org['id']}: {track_error}", exc_info=True)
                        # Don't fail org creation if tracking fails

            except Exception as e:
                logger.error(f"Failed to create credit lot for org {org['id']}: {e}")
                raise e

        # --- Step 4: Mark invitation as used ---
        self.client.client.table("app_invitations").update(
            {"status": "used", "updated_at": now}
        ).eq("id", invite["id"]).execute()

        return org

    def update_organization_tenant(
        self, org_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an organization tenant's details.
        Only updates fields that are provided in update_data.
        """
        try:
            # Verify organization exists and is of type organization
            res = (
                self.client.client.table("tenants")
                .select("id, tenant_type")
                .eq("id", org_id)
                .limit(1)
                .execute()
            )
            if not res.data:
                raise HTTPException(status_code=404, detail="Organization not found")

            org = res.data[0]
            if org.get("tenant_type") != "organization":
                raise HTTPException(status_code=400, detail="Invalid tenant type")

            # Filter out None values to only update provided fields
            update_fields = {k: v for k, v in update_data.items() if v is not None}

            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            # Add updated_at timestamp
            update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update the organization
            result = (
                self.client.client.table("tenants")
                .update(update_fields)
                .eq("id", org_id)
                .execute()
            )

            if not result.data:
                raise HTTPException(
                    status_code=500, detail="Failed to update organization"
                )

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"update_organization_tenant error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to update organization: {e}"
            )

    def delete_organization_tenant(self, org_id: str, user_id: str) -> bool:
        """
        Delete an organization tenant.
        Cascading deletes will clean up memberships, org_teams, invitations, and teams.
        """
        try:
            res = (
                self.client.client.table("tenants")
                .select("id, tenant_type")
                .eq("id", org_id)
                .limit(1)
                .execute()
            )
            if not res.data:
                raise HTTPException(status_code=404, detail="Organization not found")

            org = res.data[0]
            if org.get("tenant_type") != "organization":
                raise HTTPException(status_code=400, detail="Invalid tenant type")

            self.client.client.table("tenants").delete().eq("id", org_id).execute()
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"delete_organization_tenant error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete organization: {e}"
            )

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _month_window(cls) -> Tuple[str, str]:
        now_utc = cls._now_utc()
        month_start_utc = now_utc.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return month_start_utc.isoformat(), now_utc.isoformat()

    def _tenant_monthly_limit(self, tenant_id: str) -> Optional[int]:
        """Read a monthly limit if your schema stores it (tenants.monthly_credit_limit or preferences JSON)."""
        try:
            # Try to get monthly_credit_limit first
            row = (
                self.client.client.table("tenants")
                .select("id")
                .eq("id", tenant_id)
                .single()
                .execute()
            ).data
            if not row:
                return None

            # Try to get monthly_credit_limit if column exists
            try:
                limit_row = (
                    self.client.client.table("tenants")
                    .select("monthly_credit_limit")
                    .eq("id", tenant_id)
                    .single()
                    .execute()
                ).data
                if limit_row and limit_row.get("monthly_credit_limit") is not None:
                    return int(limit_row["monthly_credit_limit"])
            except Exception:
                # Column might not exist
                pass

            # Try to get preferences if column exists
            try:
                prefs_row = (
                    self.client.client.table("tenants")
                    .select("preferences")
                    .eq("id", tenant_id)
                    .single()
                    .execute()
                ).data
                if prefs_row:
                    prefs = prefs_row.get("preferences") or {}
                    if isinstance(prefs, dict):
                        ml = prefs.get("monthly_credit_limit") or (
                            prefs.get("credits") or {}
                        ).get("monthly_limit")
                        if ml is not None:
                            return int(ml)
            except Exception:
                # Column might not exist
                pass
        except Exception as e:
            logger.warning(
                f"Error fetching monthly limit for tenant {tenant_id}: {str(e)}"
            )
        return None

    def _credit_summary_multiple_tenants(
        self, tenant_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute credit summary for many tenants at once, returning:
        {
          tenant_id: {
            "total": int|float,
            "used": int,
            "remaining": int|float,
            "monthly_limit": Optional[int],
            "balance_now": float,          # (informational)
            "used_this_month": int         # (informational)
          },
          ...
        }
        Semantics:
          - If monthly_limit known: total=monthly_limit, used=used_this_month, remaining=max(monthly_limit-used,0)
          - Else: total=balance_now+used_this_month, used=used_this_month, remaining=balance_now
        """
        if not tenant_ids:
            return {}

        month_start_iso, now_iso = self._month_window()

        # credit_lots for all teams (only active lots)
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering done in Python below
        lots = (
            self.client.client.table("credit_lots")
            .select("tenant_id, credit_amount, valid_from, expires_at, is_active")
            .in_("tenant_id", tenant_ids)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .execute()
        ).data or []

        logger.warning(
            f"🔍 CREDIT DEBUG: Fetched {len(lots)} credit lots for {len(tenant_ids)} tenants"
        )
        logger.warning(f"🔍 CREDIT DEBUG: Tenant IDs: {tenant_ids}")
        logger.warning(f"🔍 CREDIT DEBUG: Lots data: {lots}")

        balance_by_tenant: Dict[str, Decimal] = {
            tid: Decimal("0") for tid in tenant_ids
        }
        for lot in lots:
            tid = lot.get("tenant_id")
            if tid not in balance_by_tenant:
                continue
            vf = lot.get("valid_from")
            ea = lot.get("expires_at")
            valid_now = (vf is None) or (str(vf) <= now_iso)
            not_expired = (ea is None) or (str(ea) > now_iso)
            if valid_now and not_expired:
                balance_by_tenant[tid] += Decimal(str(lot.get("credit_amount") or 0))

        # consumptions this month for all teams
        consumptions = (
            self.client.client.table("tenant_credit_consumptions")
            .select("tenant_id, cost, created_at")
            .in_("tenant_id", tenant_ids)
            .gte("created_at", month_start_iso)
            .lte("created_at", now_iso)
            .execute()
        ).data or []

        used_this_month_by_tenant: Dict[str, int] = {tid: 0 for tid in tenant_ids}
        for row in consumptions:
            tid = row.get("tenant_id")
            if tid in used_this_month_by_tenant:
                used_this_month_by_tenant[tid] += int(row.get("cost") or 0)

        # Combine with monthly limit per tenant
        result: Dict[str, Dict[str, Any]] = {}
        for tid in tenant_ids:
            balance_now = float(balance_by_tenant[tid])
            used_month = used_this_month_by_tenant[tid]
            monthly_limit = self._tenant_monthly_limit(tid)

            if monthly_limit is not None:
                remaining = max(monthly_limit - used_month, 0)
                total = monthly_limit
            else:
                remaining = balance_now
                total = balance_now + used_month

            result[tid] = {
                "total": int(total) if monthly_limit is not None else float(total),
                "used": used_month,
                "remaining": (
                    int(remaining) if monthly_limit is not None else float(remaining)
                ),
                "monthly_limit": monthly_limit,
                "balance_now": balance_now,
                "used_this_month": used_month,
            }

        logger.warning(f"🔍 CREDIT DEBUG: Final credit summary result: {result}")
        return result

    # ---------- Route 1: Team Overview ----------

    def get_team_overview(self, org_id: str) -> Dict[str, Any]:
        """
        Returns:
        {
          "teams": [
              {
                "team_id": "...",
                "team_name": "...",
                "team_leader": {"user_id": "...", "full_name": "...", "email": "..."} | None,
                "members_count": 12,
                "credit_pool": {"total": X, "used": Y, "remaining": Z, "monthly_limit": Optional[int]}
              }, ...
          ]
        }
        """

        # Teams for this organization
        try:
            org_teams = (
                self.client.client.table("org_teams")
                .select("team_id")
                .eq("organization_id", org_id)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning(f"get_team_overview: failed fetching org_teams: {e}")
            org_teams = []
        team_ids: List[str] = [t["team_id"] for t in org_teams]

        # Names for teams (assuming 'tenants' stores team display names)
        # Filter out soft-deleted teams (is_active = False)
        team_rows = []
        if team_ids:
            try:
                team_rows = (
                    self.client.client.table("tenants")
                    .select("id, name, is_active")
                    .in_("id", team_ids)
                    .eq("is_active", True)  # Only include active teams
                    .execute()
                ).data or []
            except Exception as e:
                logger.warning(f"get_team_overview: failed fetching team tenants: {e}")
                team_rows = []
        
        # Update team_ids to only include active teams
        team_ids = [r["id"] for r in team_rows]
        
        name_by_team: Dict[str, str] = {
            r["id"]: (r.get("name") or r["id"]) for r in team_rows
        }

        # Memberships for those teams (for counts and leader detection)
        team_memberships = []
        if team_ids:
            try:
                team_memberships = (
                    self.client.client.table("tenant_memberships")
                    .select("user_id, tenant_id, role, is_active")
                    .in_("tenant_id", team_ids)
                    .execute()
                ).data or []
            except Exception as e:
                logger.warning(f"get_team_overview: failed fetching team memberships: {e}")
                team_memberships = []

        # Member counts (only count active members)
        members_count_by_team: Dict[str, int] = {tid: 0 for tid in team_ids}
        for m in team_memberships:
            tid = m["tenant_id"]
            is_active = m.get("is_active", True)
            if is_active:
                members_count_by_team[tid] += 1

        # Leaders: pick a user with role in priority order
        ROLE_PRIORITY = ["team_leader", "leader", "owner", "admin"]
        leader_by_team: Dict[str, Optional[str]] = {tid: None for tid in team_ids}
        for tid in team_ids:
            candidates = [m for m in team_memberships if m["tenant_id"] == tid]

            # Sort candidates by priority of role
            def role_rank(r: Optional[str]) -> int:
                if r is None:
                    return 999
                r_low = r.lower()
                return ROLE_PRIORITY.index(r_low) if r_low in ROLE_PRIORITY else 998

            candidates.sort(key=lambda m: role_rank(m.get("role")))
            leader_by_team[tid] = candidates[0]["user_id"] if candidates else None

        # Fetch leader user profiles
        leader_ids = [uid for uid in leader_by_team.values() if uid]
        leaders: Dict[str, Dict[str, Any]] = {}
        if leader_ids:
            try:
                leader_rows = (
                    self.client.client.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", leader_ids)
                    .execute()
                ).data or []
                leaders = {r["id"]: r for r in leader_rows}
            except Exception as e:
                logger.warning(f"get_team_overview: failed fetching leader profiles: {e}")
                leaders = {}

        # Credit pools for all teams at once
        try:
            credit_by_team = self._credit_summary_multiple_tenants(team_ids)
        except Exception as e:
            logger.warning(f"get_team_overview: failed credit summary computation: {e}")
            credit_by_team = {}

        logger.info(f"Team credit summary for org {org_id}: {credit_by_team}")

        # Build result
        items: List[Dict[str, Any]] = []
        for tid in team_ids:
            leader_profile = (
                leaders.get(leader_by_team.get(tid))
                if leader_by_team.get(tid)
                else None
            )
            leader_payload = None
            if leader_profile:
                leader_payload = {
                    "user_id": leader_profile["id"],
                    "full_name": leader_profile.get("full_name"),
                    "email": leader_profile.get("email"),
                }
            cp = credit_by_team.get(
                tid, {"total": 0, "used": 0, "remaining": 0, "monthly_limit": None}
            )

            logger.info(f"Team {tid} ({name_by_team.get(tid)}): credits = {cp}")

            items.append(
                {
                    "team_id": tid,
                    "team_name": name_by_team.get(tid, tid),
                    "team_leader": leader_payload,
                    "members_count": members_count_by_team.get(tid, 0),
                    "credit_pool": {
                        "total": cp["total"],
                        "used": cp["used"],
                        "remaining": cp["remaining"],
                        "monthly_limit": cp.get("monthly_limit"),
                    },
                }
            )

        return {"teams": items}

    # ---------- Route 2: Member Management ----------

    def get_team_member_management(self, org_id: str) -> Dict[str, Any]:
        """
        Returns:
        {
          "members": [
            {
              "user_id": "...",
              "name": "...",
              "role": "member|team_leader|admin|owner|...",
              "credits_allocated": <int or 0>,
              "credits_used": <int>,       # this month (consistent with other summaries)
              "status": "Active|Frozen",
              "team_id": "...",
              "team_name": "..."
            }, ...
          ]
        }
        """

        # Determine teams under this org
        org_teams = (
            self.client.client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .execute()
        ).data or []
        team_ids: List[str] = [t["team_id"] for t in org_teams]
        if not team_ids:
            return {"members": []}

        # Team names
        team_rows = (
            self.client.client.table("tenants")
            .select("id, name")
            .in_("id", team_ids)
            .execute()
        ).data or []
        team_name_by_id: Dict[str, str] = {
            r["id"]: (r.get("name") or r["id"]) for r in team_rows
        }

        # Memberships across those teams
        memberships = (
            self.client.client.table("tenant_memberships")
            .select("user_id, tenant_id, role, is_active")
            .in_("tenant_id", team_ids)
            .execute()
        ).data or []

        user_ids: List[str] = list({m["user_id"] for m in memberships})
        # User profiles for display names
        users = []
        if user_ids:
            users = (
                self.client.client.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", user_ids)
                .execute()
            ).data or []
        user_display: Dict[str, Dict[str, Any]] = {u["id"]: u for u in users}

        # Credits used (this month) per user per team
        month_start_iso, now_iso = self._month_window()
        consumptions = (
            self.client.client.table("tenant_credit_consumptions")
            .select("tenant_id, user_id, cost, created_at")
            .in_("tenant_id", team_ids)
            .gte("created_at", month_start_iso)
            .lte("created_at", now_iso)
            .execute()
        ).data or []
        used_by_team_user: Dict[Tuple[str, str], int] = {}
        for c in consumptions:
            key = (c["tenant_id"], c["user_id"])
            used_by_team_user[key] = used_by_team_user.get(key, 0) + int(
                c.get("cost") or 0
            )

        # Credits allocated per user per team (optional table; fallback to 0 if missing)
        allocated_by_team_user: Dict[Tuple[str, str], int] = {}
        try:
            allocations = (
                self.client.client.table("member_credit_allocations")
                .select("team_id, user_id, credits_allocated")
                .in_("team_id", team_ids)
                .execute()
            ).data or []
            for a in allocations:
                key = (a["team_id"], a["user_id"])
                allocated_by_team_user[key] = allocated_by_team_user.get(key, 0) + int(
                    a.get("credits_allocated") or 0
                )
        except Exception:
            # Table not present or permission denied — default to 0
            pass

        # Get credit request status for all team users
        credit_request_status_by_user = self.get_pending_credit_requests_by_users(
            user_ids=user_ids,
            organization_id=org_id,
        )

        # Build rows
        rows: List[Dict[str, Any]] = []
        for m in memberships:
            tid = m["tenant_id"]
            uid = m["user_id"]
            role = m.get("role") or "member"
            is_active = m.get("is_active", True)
            u = user_display.get(uid, {})
            
            # Get credit request status for this user
            credit_req_status = credit_request_status_by_user.get(uid, {})
            
            rows.append(
                {
                    "user_id": uid,
                    "name": u.get("full_name") or u.get("email") or uid,
                    "role": role,
                    "credits_allocated": allocated_by_team_user.get((tid, uid), 0),
                    "credits_used": used_by_team_user.get((tid, uid), 0),
                    "status": "Active" if is_active else "Inactive",
                    "team_id": tid,
                    "team_name": team_name_by_id.get(tid, tid),
                    "credit_request": credit_req_status,  # Include credit request status
                }
            )

        # Optional: stable sort (team, then name)
        rows.sort(key=lambda r: (r["team_name"].lower(), r["name"].lower()))
        return {"members": rows}

    def get_individual_members(self, org_id: str) -> Dict[str, Any]:
        """
        Get individual members - users who have an individual tenant within this organization.
        
        NOTE: A user can be BOTH a team member AND have an individual membership.
        This method returns all users with entries in org_individuals table,
        regardless of whether they're also in a team.
        
        Returns:
        {
          "members": [
            {
              "user_id": "...",
              "individual_tenant_id": "..." or None,
              "name": "...",
              "email": "...",
              "role": "member|admin|owner|...",
              "credits_allocated": <int or 0>,
              "credits_used": <int>,
              "status": "Active|Inactive",
              "joined_at": "..."
            }, ...
          ]
        }
        """
        # Get individual members from org_individuals table
        # This is the source of truth for who has an individual tenant in this org
        org_individuals = (
            self.client.client.table("org_individuals")
            .select("user_id, individual_tenant_id")
            .eq("organization_id", org_id)
            .execute()
        ).data or []
        
        # NOTE: Don't return early if org_individuals is empty!
        # We still need to check for pending invitations below
        if not org_individuals:
            logger.info(f"🔍 No active individual members found in org_individuals for org {org_id}, checking for pending invitations...")
        
        # Map: user_id -> individual_tenant_id
        user_to_individual_tenant: Dict[str, str] = {
            item["user_id"]: item["individual_tenant_id"]
            for item in org_individuals
        }
        
        individual_user_ids = set(user_to_individual_tenant.keys())
        individual_tenant_ids = list(user_to_individual_tenant.values())
        
        logger.info(
            f"🔍 Found {len(individual_user_ids)} individual members in org {org_id}"
        )
        
        # Get organization memberships for these users (for role and status)
        # Only query if we have individual users
        org_memberships = []
        if individual_user_ids:
            org_memberships = (
                self.client.client.table("tenant_memberships")
                .select("user_id, role, is_active, created_at")
                .eq("tenant_id", org_id)
                .in_("user_id", list(individual_user_ids))
                .execute()
            ).data or []
        
        # Map: user_id -> membership data
        membership_by_user: Dict[str, Dict[str, Any]] = {
            m["user_id"]: m for m in org_memberships
        }

        # Get user profiles - only query if we have individual users
        users = []
        if individual_user_ids:
            users = (
                self.client.client.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", list(individual_user_ids))
                .execute()
            ).data or []
        user_display: Dict[str, Dict[str, Any]] = {u["id"]: u for u in users}

        # Get credits allocated per user (from their individual tenant's credit_lots)
        allocated_by_user: Dict[str, int] = {}
        if individual_tenant_ids:
            now_iso = datetime.now(timezone.utc).isoformat()
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Expiration filtering should be done in Python if needed
            credit_lots = (
                self.client.client.table("credit_lots")
                .select("id, tenant_id, credit_amount, expires_at, source, metadata")
                .in_("tenant_id", individual_tenant_ids)
                .eq("is_active", True)
                .lte("valid_from", now_iso)
                .execute()
            ).data or []
            
            # DEBUG: Log raw credit lots data
            logger.info(f"🔍 RAW CREDIT LOTS: Found {len(credit_lots)} active lots for {len(individual_tenant_ids)} individual tenants")
            for lot in credit_lots:
                logger.info(
                    f"🔍 CREDIT LOT: tenant={lot.get('tenant_id')[:8]}..., "
                    f"amount={lot.get('credit_amount')}, "
                    f"source={lot.get('source')}, "
                    f"expires={lot.get('expires_at')}"
                )
            
            # Sum credits by tenant_id, then map back to user_id
            credits_by_tenant: Dict[str, int] = {}
            for lot in credit_lots:
                tid = lot["tenant_id"]
                credits_by_tenant[tid] = credits_by_tenant.get(tid, 0) + int(
                    float(lot.get("credit_amount") or 0)
                )
            
            # Map tenant credits to user
            for user_id, tenant_id in user_to_individual_tenant.items():
                allocated_by_user[user_id] = credits_by_tenant.get(tenant_id, 0)

        # Get credits used THIS MONTH per user from their individual tenant
        # OPTIMIZATION: Added date filtering and limit to prevent unbounded queries
        used_by_user: Dict[str, int] = {}
        if individual_tenant_ids:
            month_start_iso, now_iso = self._month_window()
            consumptions = (
                self.client.client.table("tenant_credit_consumptions")
                .select("tenant_id, cost")
                .in_("tenant_id", individual_tenant_ids)
                .gte("created_at", month_start_iso)
                .lte("created_at", now_iso)
                .limit(50000)  # Safety limit to prevent runaway queries
                .execute()
            ).data or []

            # DEBUG: Log raw consumptions summary
            logger.info(f"🔍 RAW CONSUMPTIONS: Found {len(consumptions)} consumption records for {len(individual_tenant_ids)} individual tenants (this month)")
            
            # Sum consumptions by tenant_id, then map back to user_id
            used_by_tenant: Dict[str, int] = {}
            consumption_count_by_tenant: Dict[str, int] = {}
            for c in consumptions:
                tid = c["tenant_id"]
                used_by_tenant[tid] = used_by_tenant.get(tid, 0) + int(
                    float(c.get("cost") or 0)
                )
                consumption_count_by_tenant[tid] = consumption_count_by_tenant.get(tid, 0) + 1
            
            # DEBUG: Log consumption totals per tenant
            for tid, total_used in used_by_tenant.items():
                logger.info(
                    f"🔍 CONSUMPTION TOTAL: tenant={tid[:8]}..., "
                    f"total_cost={total_used}, "
                    f"num_records={consumption_count_by_tenant.get(tid, 0)}"
                )
            
            # Map tenant usage to user
            for user_id, tenant_id in user_to_individual_tenant.items():
                used_by_user[user_id] = used_by_tenant.get(tenant_id, 0)

        # Get credit request status for all individual users
        credit_request_status_by_user = self.get_pending_credit_requests_by_users(
            user_ids=list(individual_user_ids),
            organization_id=org_id,
        )

        # Build rows - iterate over individual_user_ids (from org_individuals)
        rows: List[Dict[str, Any]] = []
        for uid in individual_user_ids:
            # Get membership data (may not exist if user only has individual tenant)
            m = membership_by_user.get(uid, {})
            role = m.get("role") or "member"
            is_active = m.get("is_active", True)
            u = user_display.get(uid, {})
            
            # credits_allocated from credit_lots is the REMAINING balance, not total
            # Total allocated = remaining balance + used credits
            remaining_balance = allocated_by_user.get(uid, 0)
            used_credits = used_by_user.get(uid, 0)
            total_allocated = remaining_balance + used_credits
            
            # DEBUG: Log credit calculation details for troubleshooting
            user_email = u.get("email") or ""
            logger.info(
                f"🔍 CREDIT DEBUG [{user_email}]: "
                f"credit_lots_remaining={remaining_balance}, "
                f"consumptions_total={used_credits}, "
                f"calculated_total={total_allocated}, "
                f"display_remaining={total_allocated - used_credits}"
            )
            
            # Get credit request status for this user
            credit_req_status = credit_request_status_by_user.get(uid, {})

            rows.append(
                {
                    "user_id": uid,
                    "individual_tenant_id": user_to_individual_tenant.get(uid),
                    "name": u.get("full_name") or u.get("email") or uid,
                    "email": u.get("email") or "",
                    "role": role,
                    "credits_allocated": total_allocated,  # Total = remaining + used
                    "credits_used": used_credits,
                    "status": "Active" if is_active else "Inactive",
                    "joined_at": m.get("created_at") or "",
                    "credit_request": credit_req_status,  # Include credit request status
                }
            )

        # Sort by name
        rows.sort(key=lambda r: r["name"].lower())
        
        # --- Add pending invitations (sent but not yet accepted) ---
        # These are users who have been invited but haven't joined yet
        # First, get ALL pending invitations for this org
        all_pending_invitations = (
            self.client.client.table("organization_invitations")
            .select("id, email, credits, sent_at, created_at, is_admin, is_team_leader")
            .eq("organization_id", org_id)
            .in_("status", ["sent", "queued"])  # Pending = sent or queued, not accepted
            .execute()
        ).data or []
        
        # Filter to only individual member invitations (is_team_leader = False or NULL)
        # Some invitations may have NULL for is_team_leader, which should be treated as False
        pending_invitations = [
            inv for inv in all_pending_invitations 
            if not inv.get("is_team_leader", False)  # Treat NULL as False
        ]
        
        logger.info(
            f"📧 Found {len(all_pending_invitations)} total pending invitations, "
            f"{len(pending_invitations)} are individual members for org {org_id}"
        )
        
        # Get emails of already-joined members to avoid duplicates (case-insensitive)
        joined_emails = {r["email"].lower() for r in rows if r.get("email")}

        # Calculate expiration threshold (48 hours ago)
        now_utc = datetime.now(timezone.utc)
        expiration_threshold = now_utc - timedelta(hours=48)

        for inv in pending_invitations:
            inv_email = inv.get("email", "").lower()
            # Skip if this email already joined (shouldn't happen, but safety check)
            if inv_email in joined_emails:
                continue
            
            # Determine if invitation is expired (older than 48 hours)
            # Use sent_at if available, otherwise fall back to created_at
            timestamp_str = inv.get("sent_at") or inv.get("created_at")
            invitation_status = "Pending"
            
            if timestamp_str:
                try:
                    # Parse the timestamp (handle both ISO format and Z suffix)
                    ts_str = str(timestamp_str)
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    elif "+" not in ts_str and "-" not in ts_str[-6:]:
                        # No timezone info, assume UTC
                        ts_str = ts_str + "+00:00"
                    
                    invitation_dt = datetime.fromisoformat(ts_str)
                    
                    # Ensure timezone-aware comparison
                    if invitation_dt.tzinfo is None:
                        invitation_dt = invitation_dt.replace(tzinfo=timezone.utc)
                    
                    if invitation_dt < expiration_threshold:
                        invitation_status = "Expired"
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse timestamp for invitation {inv['id']}: {e}")
            else:
                # No timestamp at all - this shouldn't happen, but mark as expired to be safe
                logger.warning(f"Invitation {inv['id']} has no sent_at or created_at timestamp")
                invitation_status = "Expired"
            
            rows.append({
                "user_id": f"pending-{inv['id']}",  # Prefix to indicate pending/expired
                "individual_tenant_id": None,  # No tenant yet
                "invitation_id": inv["id"],  # Store invitation ID for resend/delete operations
                "name": inv_email.split("@")[0].title(),  # Use email prefix as name
                "email": inv["email"],
                "role": "admin" if inv.get("is_admin") else "member",
                "credits_allocated": inv.get("credits") or 0,
                "credits_used": 0,
                "status": invitation_status,
                "joined_at": inv.get("sent_at") or inv.get("created_at") or "",
            })
        
        # Re-sort to include pending members
        rows.sort(key=lambda r: (r["status"].lower() != "active", r["name"].lower()))
        
        logger.info(
            f"✅ Returning {len(rows)} members ({len(rows) - len(pending_invitations)} active, {len(pending_invitations)} pending) for org {org_id}"
        )
        return {"members": rows}

    def delete_organization_member(
        self, org_id: str, user_id: str, admin_user_id: str
    ) -> Dict[str, Any]:
        """
        Delete a member from the organization completely.
        This allows them to be re-invited.

        Steps:
        1. Verify the user has an org_individuals entry (is an individual member)
        2. Cancel any pending invitations for the user and reclaim credits
        3. Check if user is in any teams (prevent deletion if in teams)
        4. Return any allocated credits back to the organization
        5. Delete the org_individuals entry
        6. Delete the individual tenant and its membership
        7. Delete the org tenant_membership record (if exists)
        8. Delete any credit allocations
        """
        try:
            # 1. Check if user has an org_individuals entry (individual member)
            org_individual = (
                self.client.client.table("org_individuals")
                .select("id, individual_tenant_id")
                .eq("organization_id", org_id)
                .eq("user_id", user_id)
                .execute()
            ).data

            if not org_individual:
                raise HTTPException(
                    status_code=404, detail="Member not found in this organization"
                )

            org_individual = org_individual[0]
            individual_tenant_id = org_individual["individual_tenant_id"]

            # Get user's email to check for pending invitations
            user_profile = (
                self.client.client.table("user_profiles")
                .select("email")
                .eq("id", user_id)
                .execute()
            ).data

            if not user_profile:
                raise HTTPException(
                    status_code=404, detail="User profile not found"
                )

            user_email = user_profile[0]["email"]

            # Cancel any pending invitations for this user
            pending_invitations = (
                self.client.client.table("organization_invitations")
                .select("id, credits, status")
                .eq("organization_id", org_id)
                .eq("email", user_email)
                .in_("status", ["queued", "sent"])
                .execute()
            ).data or []

            total_pending_credits = 0
            cancelled_invitations = []

            for invitation in pending_invitations:
                invitation_credits = invitation.get("credits", 0) or 0
                total_pending_credits += invitation_credits

                # Update invitation status to cancelled
                self.client.client.table("organization_invitations").update({
                    "status": "cancelled",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", invitation["id"]).execute()

                cancelled_invitations.append({
                    "invitation_id": invitation["id"],
                    "credits": invitation_credits,
                    "previous_status": invitation["status"]
                })

            # 2. Check if user is in any teams within this org
            org_teams = (
                self.client.client.table("org_teams")
                .select("team_id")
                .eq("organization_id", org_id)
                .execute()
            ).data or []
            team_ids = [t["team_id"] for t in org_teams]

            if team_ids:
                team_memberships = (
                    self.client.client.table("tenant_memberships")
                    .select("tenant_id")
                    .in_("tenant_id", team_ids)
                    .eq("user_id", user_id)
                    .execute()
                ).data or []

                if team_memberships:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot delete member who is part of a team. Remove them from the team first.",
                    )

            # 3. Return allocated credits back to organization (if any)
            # Get credit lots from the user's INDIVIDUAL TENANT (not user_id)
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Expiration filtering done in Python below
            # Define current timestamp before using in filters
            now = datetime.now(timezone.utc).isoformat()
            user_lots = (
                self.client.client.table("credit_lots")
                .select("*")
                .eq("tenant_id", individual_tenant_id)  # Individual tenant ID
                .eq("original_tenant_id", org_id)  # Allocated from this org
                .eq("is_active", True)
                .lte("valid_from", now)
                .execute()
            ).data or []

            total_returned = 0
            
            for lot in user_lots:
                # Return remaining credits to organization
                remaining = lot.get("credit_amount", 0)
                if remaining > 0:
                    # Create a new lot for the organization with the returned credits
                    # Use "grant" as source since "returned" is not a valid enum value
                    returned_lot = {
                        "tenant_id": org_id,
                        "original_tenant_id": org_id,
                        "credit_amount": remaining,
                        "source": "grant",  # Valid enum values: grant, purchase
                        "valid_from": now,
                        "expires_at": lot.get("expires_at"),
                        "is_active": True,
                        "metadata": {
                            "type": "member_credit_return",
                            "returned_from_user": user_id,
                            "returned_from_tenant": individual_tenant_id,
                            "returned_at": now,
                            "reason": "member_deleted",
                        },
                    }
                    self.client.client.table("credit_lots").insert(
                        returned_lot
                    ).execute()
                    total_returned += remaining

                # Deactivate the user's lot
                self.client.client.table("credit_lots").update({"is_active": False}).eq(
                    "id", lot["id"]
                ).execute()

            # 4. Delete credit allocations (if member_credit_allocations table exists)
            try:
                self.client.client.table("member_credit_allocations").delete().eq(
                    "user_id", user_id
                ).eq("team_id", org_id).execute()
            except Exception:
                # Table might not exist
                pass

            # 5. Delete the org tenant_membership record (user's membership in org tenant)
            org_membership = (
                self.client.client.table("tenant_memberships")
                .select("id")
                .eq("tenant_id", org_id)
                .eq("user_id", user_id)
                .execute()
            ).data
            
            if org_membership:
                self.client.client.table("tenant_memberships").delete().eq(
                    "id", org_membership[0]["id"]
                ).execute()

            # 6. Delete the individual tenant membership
            individual_membership = (
                self.client.client.table("tenant_memberships")
                .select("id")
                .eq("tenant_id", individual_tenant_id)
                .eq("user_id", user_id)
                .execute()
            ).data
            
            if individual_membership:
                self.client.client.table("tenant_memberships").delete().eq(
                    "id", individual_membership[0]["id"]
                ).execute()

            # 7. Delete the org_individuals entry (THIS IS THE KEY FIX)
            self.client.client.table("org_individuals").delete().eq(
                "id", org_individual["id"]
            ).execute()

            # 8. Optionally delete the individual tenant itself
            # (or keep it for audit purposes - commenting out for now)
            # self.client.client.table("tenants").delete().eq(
            #     "id", individual_tenant_id
            # ).execute()

            logger.info(
                f"Deleted individual member {user_id} from organization {org_id}. "
                f"Individual tenant: {individual_tenant_id}. "
                f"Returned {total_returned} credits from allocated lots. "
                f"Reclaimed {total_pending_credits} credits from {len(cancelled_invitations)} cancelled pending invitation(s). "
                f"Admin: {admin_user_id}"
            )

            return {
                "success": True,
                "message": "Member deleted successfully",
                "credits_returned": total_returned,
                "pending_invitation_credits_reclaimed": total_pending_credits,
                "cancelled_invitations": cancelled_invitations,
                "user_id": user_id,
                "individual_tenant_id": individual_tenant_id,
                "organization_id": org_id,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting organization member: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete member: {str(e)}"
            )

    def delete_pending_invitation(
        self, org_id: str, invitation_id: str, admin_user_id: str
    ) -> Dict[str, Any]:
        """
        Delete a pending or expired invitation from the organization.
        This removes the invitation record from organization_invitations table.

        Args:
            org_id: Organization ID
            invitation_id: Invitation ID to delete
            admin_user_id: Admin user performing the deletion

        Returns:
            Dict with success status and message
        """
        try:
            # 1. Verify the invitation exists and belongs to this organization
            invitation = (
                self.client.client.table("organization_invitations")
                .select("id, email, status, organization_id")
                .eq("id", invitation_id)
                .eq("organization_id", org_id)
                .execute()
            ).data

            if not invitation:
                raise HTTPException(
                    status_code=404, detail="Invitation not found in this organization"
                )

            invitation = invitation[0]
            
            # 2. Check if invitation is in a deletable state (sent, queued, or failed)
            deletable_statuses = ["sent", "queued", "failed"]
            if invitation.get("status") not in deletable_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete invitation with status '{invitation.get('status')}'. Only pending/expired invitations can be deleted.",
                )

            # 3. Delete the invitation
            self.client.client.table("organization_invitations").delete().eq(
                "id", invitation_id
            ).execute()

            logger.info(
                f"Deleted pending invitation {invitation_id} (email: {invitation.get('email')}) "
                f"from organization {org_id}. Admin: {admin_user_id}"
            )

            return {
                "success": True,
                "message": "Invitation deleted successfully",
                "invitation_id": invitation_id,
                "email": invitation.get("email"),
                "organization_id": org_id,
                "credits_returned": 0,  # No credits allocated yet for pending invitations
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting pending invitation: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete invitation: {str(e)}"
            )

    def resend_invitation(
        self, org_id: str, invitation_id: str, admin_user_id: str
    ) -> Dict[str, Any]:
        """
        Resend an invitation email for a pending or expired invitation.
        
        This method:
        - Verifies the invitation exists and is in a resendable state
        - Creates a new invite token
        - Updates the invitation status back to 'queued'
        - Returns the data needed to send the email
        
        Args:
            org_id: Organization ID
            invitation_id: Invitation ID to resend
            admin_user_id: Admin user performing the resend
            
        Returns:
            Dict with success status, email, invite_link, and other data
        """
        try:
            # 1. Verify the invitation exists and belongs to this organization
            invitation = (
                self.client.client.table("organization_invitations")
                .select("id, email, credits, is_admin, is_team_leader, status, organization_id")
                .eq("id", invitation_id)
                .eq("organization_id", org_id)
                .execute()
            ).data

            if not invitation:
                return {
                    "success": False,
                    "message": "Invitation not found in this organization"
                }

            invitation = invitation[0]
            
            # 2. Check if invitation is in a resendable state (sent, queued, or failed)
            resendable_statuses = ["sent", "queued", "failed"]
            if invitation.get("status") not in resendable_statuses:
                return {
                    "success": False,
                    "message": f"Cannot resend invitation with status '{invitation.get('status')}'. Only pending/expired invitations can be resent."
                }

            # 3. Create a new invite token
            from src.mint.utils.url_safe_serializer import create_invite_token
            
            token = create_invite_token(
                tenant_id=org_id,
                is_admin=invitation.get("is_admin", False),
                credit=invitation.get("credits") or 0,
                is_team_leader=invitation.get("is_team_leader", False),
            )
            
            # 4. Build the invite link
            frontend_url = os.getenv("FRONTEND_URL", "")
            invite_link = f"{frontend_url}/invite/{token}?org_id={org_id}"
            
            # 5. Update the invitation status back to 'queued'
            self.client.client.table("organization_invitations").update({
                "status": "queued",
            }).eq("id", invitation_id).execute()

            logger.info(
                f"Prepared resend for invitation {invitation_id} (email: {invitation.get('email')}) "
                f"in organization {org_id}. Admin: {admin_user_id}"
            )

            return {
                "success": True,
                "message": "Invitation prepared for resend",
                "invitation_id": invitation_id,
                "email": invitation.get("email"),
                "invite_link": invite_link,
                "is_team_leader": invitation.get("is_team_leader", False),
                "credits": invitation.get("credits") or 0,
                "organization_id": org_id,
            }

        except Exception as e:
            logger.error(f"Error preparing invitation resend: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to prepare invitation resend: {str(e)}"
            }

    def allocate_from_org_to_user(
        self,
        *,
        organization_id: str,
        user_tenant_id: str,
        amount: Decimal,
        source: str = "grant",
        valid_from: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Move credits from an org tenant to a user tenant by:
          1) For prepay/grant orgs: Verifying org has enough available credits and deducting
          2) For postpay orgs: Creating credit lot without deduction (billed later)
          3) Creating a credit_lot for the user with original_tenant_id set to the org
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("amount must be > 0")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Check organization type
        org_config_response = self.client.client.table('organization_billing_config') \
            .select('organization_type') \
            .eq('tenant_id', organization_id) \
            .limit(1) \
            .execute()

        org_type = 'grant_org'  # default
        if org_config_response.data and len(org_config_response.data) > 0:
            org_type = org_config_response.data[0].get('organization_type', 'grant_org')

        # Determine source based on org type if not explicitly provided
        if source == "grant" and org_type != 'grant_org':
            actual_source = "purchase"
        else:
            actual_source = source

        created_lot = None
        created_lots = []
        lot_valid_from = valid_from or now_iso

        if org_type == 'postpay_org':
            payload = {
                "tenant_id": user_tenant_id,
                "original_tenant_id": organization_id,
                "source": actual_source,
                "credit_amount": float(amount),
                "valid_from": lot_valid_from,
                "expires_at": None,
                "metadata": (metadata or {}) | {"allocation_from_org": organization_id},
                "created_at": now_iso,
                "is_active": True,
            }
            res = (
                self.client.client.table("credit_lots")
                .insert(payload)
                .select("*")
                .limit(1)
                .execute()
            )
            created_lot = res.data[0] if res.data and len(res.data) > 0 else None
        else:
            # Fetch active org lots ordered by expiry (non-expiring last)
            lots_query = (
                self.client.client.table("credit_lots")
                .select("id, credit_amount, expires_at, source")
                .eq("tenant_id", organization_id)
                .eq("is_active", True)
                .lte("valid_from", now_iso)
                .order("expires_at", desc=False, nullsfirst=False)
            )

            if org_type == 'grant_org':
                lots_query = lots_query.eq("source", "grant")
            elif org_type == 'prepay_org':
                lots_query = lots_query.in_("source", list(self._PURCHASE_SOURCES))

            org_lots = lots_query.execute().data or []

            # Filter out expired lots in Python (since .or_() not supported)
            valid_lots = []
            for lot in org_lots:
                expires_at_value = lot.get("expires_at")
                if expires_at_value is None:
                    valid_lots.append(lot)
                else:
                    try:
                        exp_str = str(expires_at_value).replace("Z", "+00:00")
                        if exp_str > now_iso:
                            valid_lots.append(lot)
                    except Exception:
                        continue

            total_available = sum(Decimal(str(lot.get("credit_amount") or 0)) for lot in valid_lots)
            if total_available < amount:
                raise Exception("insufficient_org_credits")

            remaining = amount

            if org_type == 'grant_org':
                # Deduct from org lots and create user lots with matching expiry
                for lot in valid_lots:
                    if remaining <= 0:
                        break
                    lot_credits = Decimal(str(lot.get("credit_amount") or 0))
                    if lot_credits <= 0:
                        continue

                    deduct = min(lot_credits, remaining)
                    new_balance = lot_credits - deduct

                    self.client.client.table("credit_lots").update(
                        {"credit_amount": float(new_balance)}
                    ).eq("id", lot["id"]).execute()

                    payload = {
                        "tenant_id": user_tenant_id,
                        "original_tenant_id": organization_id,
                        "source": lot.get("source", actual_source),
                        "credit_amount": float(deduct),
                        "valid_from": lot_valid_from,
                        "expires_at": lot.get("expires_at"),
                        "metadata": (metadata or {}) | {
                            "allocation_from_org": organization_id,
                            "origin_lot_id": lot["id"],
                        },
                        "created_at": now_iso,
                        "is_active": True,
                    }
                    res = (
                        self.client.client.table("credit_lots")
                        .insert(payload)
                        .select("*")
                        .limit(1)
                        .execute()
                    )
                    created = res.data[0] if res.data and len(res.data) > 0 else None
                    if created:
                        created_lots.append(created)

                    remaining -= deduct

            else:
                # prepay_org: deduct from org lots, create one user lot with no expiry
                for lot in valid_lots:
                    if remaining <= 0:
                        break
                    lot_credits = Decimal(str(lot.get("credit_amount") or 0))
                    if lot_credits <= 0:
                        continue

                    deduct = min(lot_credits, remaining)
                    new_balance = lot_credits - deduct

                    self.client.client.table("credit_lots").update(
                        {"credit_amount": float(new_balance)}
                    ).eq("id", lot["id"]).execute()

                    remaining -= deduct

                payload = {
                    "tenant_id": user_tenant_id,
                    "original_tenant_id": organization_id,
                    "source": actual_source,
                    "credit_amount": float(amount),
                    "valid_from": lot_valid_from,
                    "expires_at": None,
                    "metadata": (metadata or {}) | {"allocation_from_org": organization_id},
                    "created_at": now_iso,
                    "is_active": True,
                }
                res = (
                    self.client.client.table("credit_lots")
                    .insert(payload)
                    .select("*")
                    .limit(1)
                    .execute()
                )
                created_lot = res.data[0] if res.data and len(res.data) > 0 else None

            if not created_lot and created_lots:
                created_lot = created_lots[0]

        if not created_lot:
            raise Exception("failed_to_create_credit_lot")

        # For postpay_org, record this allocation for billing
        if org_type == 'postpay_org':
            try:
                # Get user_id for the allocated member
                user_tenant_response = self.client.client.table('tenant_memberships') \
                    .select('user_id') \
                    .eq('tenant_id', user_tenant_id) \
                    .limit(1) \
                    .execute()

                user_id = None
                if user_tenant_response.data and len(user_tenant_response.data) > 0:
                    user_id = user_tenant_response.data[0].get('user_id')

                allocation_payload = {
                    'tenant_id': organization_id,
                    'allocation_type': 'allocation_to_member',
                    'credit_amount': float(amount),
                    'credit_lot_id': created_lot.get('id'),
                    'allocated_to_tenant_id': user_tenant_id,
                    'allocated_to_user_id': user_id,
                    'allocated_at': datetime.now(timezone.utc).isoformat(),
                    'metadata': metadata or {},
                }

                self.client.client.table('organization_credit_allocations') \
                    .insert(allocation_payload) \
                    .execute()

                logger.info(f"Recorded member credit allocation for postpay_org {organization_id}: {amount} credits to {user_tenant_id}")
            except Exception as e:
                logger.error(f"Failed to record member credit allocation for postpay_org {organization_id}: {e}", exc_info=True)
                # Don't fail the allocation if tracking fails

        return created_lot

    # Replace your previous suspend method with this version
    def suspend_user_lot_back_to_org(
        self,
        *,
        org_tenant_id: str,
        lot_id: str,
        return_source: str = "org_suspend_return",
    ):
        """
        Return a user's credit lot back to the org and delete the user's lot.
        If an org lot already exists with the same (original_tenant_id, tenant_id),
        add the credits to that lot instead of creating a new one.
        """
        # Fetch the lot
        lot_res = (
            self.cleint.client.table("credit_lots")
            .select("*")
            .eq("id", lot_id)
            .single()
            .execute()
        )
        lot = lot_res.data
        if not lot:
            raise Exception("lot_not_found")

        if lot.get("original_tenant_id") != org_tenant_id:
            raise Exception("forbidden: lot not issued by this org")

        amount = Decimal(str(lot.get("credit_amount", 0)))
        returned_lot = None

        if amount > 0:
            # Try to find an existing ACTIVE org lot with the same (original_tenant_id, tenant_id)
            now_iso = datetime.now(timezone.utc).isoformat()
            # Note: Removed .or_() as Supabase Python client doesn't support it
            existing_res = (
                self.cleint.client.table("credit_lots")
                .select("id, credit_amount, expires_at")
                .eq("tenant_id", org_tenant_id)
                .eq("original_tenant_id", org_tenant_id)
                .eq("is_active", True)
                .lte("valid_from", now_iso)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            existing = (existing_res.data or [None])[0]

            if existing:
                # Add to existing lot
                new_amount = Decimal(str(existing["credit_amount"] or 0)) + amount
                returned_lot = (
                    self.cleint.client.table("credit_lots")
                    .update({"credit_amount": float(new_amount)})
                    .eq("id", existing["id"])
                    .select("*")
                    .single()
                    .execute()
                ).data
            else:
                # Create a new org lot
                return_payload = {
                    "tenant_id": org_tenant_id,
                    "original_tenant_id": org_tenant_id,
                    "source": return_source,
                    "credit_amount": float(amount),
                    # keep original window if desired; adjust if policy differs
                    "valid_from": lot.get("valid_from")
                    or datetime.now(timezone.utc).isoformat(),
                    "expires_at": lot.get("expires_at"),
                    "metadata": {
                        "suspended_from_lot_id": lot_id,
                        "suspended_from_tenant_id": lot.get("tenant_id"),
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                }
                returned_lot = (
                    self.cleint.client.table("credit_lots")
                    .insert(return_payload)
                    .select("*")
                    .single()
                    .execute()
                ).data

        # Delete the user lot
        self.cleint.client.table("credit_lots").delete().eq("id", lot_id).execute()

        return {
            "deleted_lot_id": lot_id,
            "returned_org_lot": returned_lot,
        }

    def freeze_lot(
        self, *, lot_id: str, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set is_active = false on a lot.
        If organization_id is provided, validate that the lot was issued by the org.
        """
        # Optionally validate ownership
        if organization_id:
            lot_res = (
                self.client.client.table("credit_lots")
                .select("id, original_tenant_id")
                .eq("id", lot_id)
                .single()
                .execute()
            )
            lot = lot_res.data
            if not lot:
                raise Exception("lot_not_found")
            if lot.get("original_tenant_id") != organization_id:
                raise Exception("forbidden: lot not issued by this org")

        res = (
            self.client.client.table("credit_lots")
            .update({"is_active": False})
            .eq("id", lot_id)
            .select("*")
            .single()
            .execute()
        )
        return res.data

    def deduct_credits(self, tenant_id: str, amount: Decimal):
        """
        Deduct credits from the tenant’s ACTIVE lots, earliest expiry first.
        Non-expiring lots are consumed last. Only lots in their valid window
        (valid_from <= now and (expires_at is null or > now)) are considered.
        """
        amt = Decimal(str(amount))
        if amt <= 0:
            return

        now_iso = datetime.now(timezone.utc).isoformat()

        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering done in Python below
        lots = (
            self.client.client.table("credit_lots")
            .select("id, credit_amount, expires_at")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .order("expires_at", desc=False, nullsfirst=False)  # null (no expiry) last
            .execute()
        )

        remaining = amt
        for lot in lots.data or []:
            if remaining <= 0:
                break
            
            # Filter out expired lots in Python (since .or_() not supported)
            expires_at = lot.get("expires_at")
            if expires_at is not None:
                try:
                    exp_str = str(expires_at).replace("Z", "+00:00")
                    if exp_str <= now_iso:
                        continue  # Skip expired lot
                except:
                    continue  # Skip if can't parse
            
            lot_amount = Decimal(str(lot.get("credit_amount", 0)))
            if lot_amount <= 0:
                continue
            deduct = min(lot_amount, remaining)
            new_balance = lot_amount - deduct
            self.client.client.table("credit_lots").update(
                {"credit_amount": float(new_balance)}
            ).eq("id", lot["id"]).execute()
            remaining -= deduct

        if remaining > 0:
            raise Exception("insufficient_credits")

    async def create_individual_tenant_for_org(
        self, org_id: str, user_id: str, user_email: str, user_full_name: str = "user"
    ) -> Optional[Dict[str, Any]]:
        """
        Get or create an individual tenant for a user within an organization.

        This creates a SEPARATE individual tenant specifically for the organization,
        distinct from the user's personal individual tenant. If the user already has
        an individual tenant for this org, it returns that existing tenant.

        Args:
            org_id: Organization tenant ID
            user_id: User ID
            user_email: User email
            user_full_name: User's full name for tenant naming

        Returns:
            Individual tenant data

        Raises:
            ValueError: If org_id is not a valid organization tenant
        """
        from ..tenant.models import TenantCreate

        logger.info(
            f"🚀 create_individual_tenant_for_org called: "
            f"org_id={org_id}, user_id={user_id}, user_email={user_email}"
        )

        # 1. Validate that org_id is actually an organization
        org = (
            self.client.client.table("tenants")
            .select("id, tenant_type")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        if not org.data or org.data[0]["tenant_type"] != "organization":
            raise ValueError("Invalid organization tenant")

        # 2. Check if user already has an individual tenant linked to this organization
        org_individuals = (
            self.client.client.table("org_individuals")
            .select(
                "individual_tenant_id, tenants!org_individuals_individual_tenant_id_fkey(*)"
            )
            .eq("organization_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if org_individuals.data:
            # User already has an individual tenant for this org - return it
            individual_tenant = org_individuals.data[0].get("tenants")
            if individual_tenant and individual_tenant.get("is_active"):
                logger.info(
                    f"✅ Found existing individual tenant {individual_tenant['id']} "
                    f"for user {user_id} in org {org_id} - returning existing tenant"
                )
                return individual_tenant
            else:
                logger.warning(
                    f"⚠️ Found org_individuals entry but tenant is inactive or missing: "
                    f"org_id={org_id}, user_id={user_id}"
                )

        # 3. Create a NEW individual tenant for this user within the org
        logger.info(f"🔨 Creating new individual tenant for user {user_id} in org {org_id}")
        
        # CRITICAL: Include org_id in tenant name to ensure uniqueness across organizations
        tenant_data = TenantCreate(
            name=f"{user_full_name or 'user'}-{user_id[:6]}-{org_id[:8]}-org-ind",
            tenant_type="individual",
            description=f"Personal tenant for {user_full_name or user_email} in organization",
            settings={},
        )

        tenant_service = TenantService()
        tenant_response = await tenant_service.create_tenant(
            tenant_data, owner_user_id=user_id
        )

        if (
            not tenant_response
            or not tenant_response.success
            or not tenant_response.data
        ):
            logger.error(
                f"❌ Failed to create individual tenant for user {user_id} in org {org_id}"
            )
            return None
        
        logger.info(
            f"✅ Individual tenant created successfully: {tenant_response.data.id}"
        )

        # Convert Tenant Pydantic object to dict with UUIDs as strings
        individual_tenant = tenant_response.data.model_dump(mode='json')

        # 4. Link the individual tenant to the organization
        try:
            self.client.client.table("org_individuals").insert(
                {
                    "organization_id": org_id,
                    "individual_tenant_id": individual_tenant["id"],
                    "user_id": user_id,
                    "created_by": user_id,
                }
            ).execute()
            
            logger.info(
                f"✅ Successfully linked individual tenant {individual_tenant['id']} "
                f"to organization {org_id} for user {user_id}"
            )
        except Exception as e:
            logger.error(
                f"❌ CRITICAL: Failed to insert org_individuals entry: {e}"
            )
            logger.error(f"   organization_id: {org_id}")
            logger.error(f"   individual_tenant_id: {individual_tenant['id']}")
            logger.error(f"   user_id: {user_id}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error details: {str(e)}")
            
            # Re-raise to prevent silent failure and ensure transaction rollback
            raise Exception(
                f"Failed to link individual tenant to organization: {str(e)}"
            ) from e

        logger.info(
            f"Created new individual tenant {individual_tenant['id']} "
            f"for user {user_id} in org {org_id}"
        )

        return individual_tenant

    # ============================================================================
    # Member Projects Access Methods
    # ============================================================================

    def get_member_tenant_ids(
        self, organization_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Get all org-specific tenant IDs for a user (individual + teams).
        
        Args:
            organization_id: Organization ID
            user_id: User ID
            
        Returns:
            {
                "individual_tenant_id": "...",  # From org_individuals
                "team_ids": ["...", "..."]  # From org_teams memberships
            }
        """
        try:
            result = {
                "individual_tenant_id": None,
                "team_ids": []
            }
            
            # Get individual tenant
            individual_response = (
                self.client.client.table("org_individuals")
                .select("individual_tenant_id")
                .eq("organization_id", organization_id)
                .eq("user_id", user_id)
                .execute()
            )
            
            if individual_response.data and len(individual_response.data) > 0:
                result["individual_tenant_id"] = individual_response.data[0]["individual_tenant_id"]
            
            # Get team tenants
            team_memberships = (
                self.client.client.table("tenant_memberships")
                .select("tenant_id, tenants!tenant_memberships_tenant_id_fkey(tenant_type)")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            
            if team_memberships.data:
                # Filter for team tenants and check if they belong to this org
                for membership in team_memberships.data:
                    tenant_data = membership.get("tenants", {})
                    if tenant_data and tenant_data.get("tenant_type") == "team":
                        tenant_id = membership["tenant_id"]
                        
                        # Verify team belongs to this organization
                        org_team_check = (
                            self.client.client.table("org_teams")
                            .select("team_id")
                            .eq("organization_id", organization_id)
                            .eq("team_id", tenant_id)
                            .execute()
                        )
                        
                        if org_team_check.data:
                            result["team_ids"].append(tenant_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting member tenant IDs: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get tenant IDs: {str(e)}")

    def validate_tenant_belongs_to_org(
        self, organization_id: str, tenant_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify tenant belongs to the organization.
        
        Args:
            organization_id: Organization ID
            tenant_id: Tenant ID to validate
            
        Returns:
            (is_valid, tenant_info_dict)
        """
        try:
            # Check in org_individuals
            individual_check = (
                self.client.client.table("org_individuals")
                .select("user_id, individual_tenant_id, tenants!org_individuals_individual_tenant_id_fkey(name, tenant_type)")
                .eq("organization_id", organization_id)
                .eq("individual_tenant_id", tenant_id)
                .execute()
            )
            
            if individual_check.data:
                data = individual_check.data[0]
                tenant_info = data.get("tenants", {})
                return True, {
                    "tenant_id": tenant_id,
                    "tenant_type": "individual",
                    "tenant_name": tenant_info.get("name", ""),
                    "user_id": data.get("user_id"),
                }
            
            # Check in org_teams
            team_check = (
                self.client.client.table("org_teams")
                .select("team_id, tenants!org_teams_team_id_fkey(name, tenant_type)")
                .eq("organization_id", organization_id)
                .eq("team_id", tenant_id)
                .execute()
            )
            
            if team_check.data:
                data = team_check.data[0]
                tenant_info = data.get("tenants", {})
                return True, {
                    "tenant_id": tenant_id,
                    "tenant_type": "team",
                    "tenant_name": tenant_info.get("name", ""),
                }
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error validating tenant: {e}")
            return False, None

    def validate_project_belongs_to_org(
        self, organization_id: str, project_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify project belongs to an org member.
        
        Args:
            organization_id: Organization ID
            project_id: Project ID to validate
            
        Returns:
            (is_valid, project_owner_info_dict)
        """
        try:
            # Get project tenant_id
            project_response = (
                self.client.client.table("vmp_projects")
                .select("tenant_id, user_id")
                .eq("id", project_id)
                .execute()
            )
            
            if not project_response.data:
                return False, None
            
            project = project_response.data[0]
            tenant_id = project["tenant_id"]
            user_id = project["user_id"]
            
            # Validate tenant belongs to org
            is_valid, tenant_info = self.validate_tenant_belongs_to_org(organization_id, tenant_id)
            
            if is_valid:
                # Get user info
                user_response = (
                    self.client.client.table("user_profiles")
                    .select("email, full_name")
                    .eq("id", user_id)
                    .execute()
                )
                
                user_info = user_response.data[0] if user_response.data else {}
                
                return True, {
                    "user_id": user_id,
                    "user_email": user_info.get("email"),
                    "user_name": user_info.get("full_name"),
                    "tenant_id": tenant_id,
                    "member_type": tenant_info.get("tenant_type"),
                }
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error validating project: {e}")
            return False, None

    def validate_user_is_org_member(
        self, organization_id: str, user_id: str
    ) -> bool:
        """
        Check if user is a member of the organization.
        
        Args:
            organization_id: Organization ID
            user_id: User ID to check
            
        Returns:
            True if user is a member, False otherwise
        """
        try:
            # Check org_individuals
            individual_check = (
                self.client.client.table("org_individuals")
                .select("user_id")
                .eq("organization_id", organization_id)
                .eq("user_id", user_id)
                .execute()
            )
            
            if individual_check.data:
                return True
            
            # Check if user is in any team belonging to this org
            # First get all team tenants in this org
            org_teams = (
                self.client.client.table("org_teams")
                .select("team_id")
                .eq("organization_id", organization_id)
                .execute()
            )
            
            if org_teams.data:
                team_ids = [team["team_id"] for team in org_teams.data]
                
                # Check if user is member of any of these teams
                team_membership = (
                    self.client.client.table("tenant_memberships")
                    .select("tenant_id")
                    .eq("user_id", user_id)
                    .in_("tenant_id", team_ids)
                    .eq("is_active", True)
                    .execute()
                )
                
                if team_membership.data:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating user membership: {e}")
            return False

    def log_project_access(
        self,
        organization_id: str,
        accessed_by_user_id: str,
        target_user_id: str,
        project_id: str,
        access_type: str = "view"
    ) -> None:
        """
        Log project access for audit trail.
        
        Args:
            organization_id: Organization ID
            accessed_by_user_id: User who accessed the project
            target_user_id: User whose project was accessed
            project_id: Project ID
            access_type: Type of access (view, edit, export)
        """
        try:
            self.client.client.table("project_access_logs").insert({
                "organization_id": organization_id,
                "accessed_by_user_id": accessed_by_user_id,
                "target_user_id": target_user_id,
                "project_id": project_id,
                "access_type": access_type,
                "metadata": {}
            }).execute()
            
            logger.info(
                f"Logged access: {accessed_by_user_id} accessed project {project_id} "
                f"of user {target_user_id} in org {organization_id}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log project access: {e}")
            # Don't raise - logging failure shouldn't block the request

    def get_organization_member_projects(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        member_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Get all organization members with their project summaries.
        
        Args:
            organization_id: Organization ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            member_type: Filter by type: "individual", "team", or "all"
            
        Returns:
            {
                "members": [...],
                "total_count": int,
                "page": int,
                "page_size": int,
                "has_next": bool
            }
        """
        try:
            members = []
            
            # Get individual members if requested
            if member_type in ["individual", "all"]:
                individual_members = (
                    self.client.client.table("org_individuals")
                    .select("user_id, individual_tenant_id, user_profiles!org_individuals_user_id_fkey(email, full_name)")
                    .eq("organization_id", organization_id)
                    .execute()
                )
                
                for member_data in individual_members.data or []:
                    user_profile = member_data.get("user_profiles", {})
                    tenant_id = member_data["individual_tenant_id"]
                    
                    # Get projects for this tenant (only 1 for recent projects display)
                    projects_response = (
                        self.client.client.table("vmp_projects")
                        .select("id, name, description, current_step, created_at, updated_at")
                        .eq("tenant_id", tenant_id)
                        .order("updated_at", desc=True)
                        .limit(1)  # Show only 1 most recent project
                        .execute()
                    )
                    
                    projects = projects_response.data or []
                    
                    # Get PV report count for this user (PV reports use created_by, not tenant_id)
                    user_id = member_data["user_id"]
                    pv_report_count_response = (
                        self.client.client.table("documents")
                        .select("id", count="exact")
                        .eq("created_by", user_id)
                        .eq("source_type", "pv_report")
                        .execute()
                    )
                    pv_report_count = pv_report_count_response.count if hasattr(pv_report_count_response, 'count') else 0
                    
                    # Get total project count (projects use tenant_id)
                    count_response = (
                        self.client.client.table("vmp_projects")
                        .select("id", count="exact")
                        .eq("tenant_id", tenant_id)
                        .execute()
                    )
                    
                    project_count = count_response.count if hasattr(count_response, 'count') else len(projects)
                    
                    members.append({
                        "user_id": user_id,
                        "user_email": user_profile.get("email"),
                        "user_name": user_profile.get("full_name"),
                        "member_type": "individual",
                        "tenant_id": tenant_id,
                        "project_count": project_count,
                        "pv_report_count": pv_report_count,
                        "projects": projects
                    })
            
            # Get team members if requested
            if member_type in ["team", "all"]:
                team_tenants = (
                    self.client.client.table("org_teams")
                    .select("team_id, tenants!org_teams_team_id_fkey(name, contact_email)")
                    .eq("organization_id", organization_id)
                    .execute()
                )
                
                for team_data in team_tenants.data or []:
                    tenant_id = team_data["team_id"]
                    tenant_info = team_data.get("tenants", {})
                    
                    # Get team admins from tenant_memberships
                    team_admins_response = (
                        self.client.client.table("tenant_memberships")
                        .select("user_id, user_profiles!tenant_memberships_user_id_fkey(email)")
                        .eq("tenant_id", tenant_id)
                        .in_("role", ["owner", "admin"])
                        .eq("is_active", True)
                        .execute()
                    )
                    
                    # Extract admin emails
                    team_admin_emails = []
                    if team_admins_response.data:
                        for admin_data in team_admins_response.data:
                            user_profile = admin_data.get("user_profiles", {})
                            if user_profile and user_profile.get("email"):
                                team_admin_emails.append(user_profile["email"])
                    
                    # Get all team member user_ids for PV report counting
                    team_members_response = (
                        self.client.client.table("tenant_memberships")
                        .select("user_id")
                        .eq("tenant_id", tenant_id)
                        .eq("is_active", True)
                        .execute()
                    )
                    team_member_ids = [m["user_id"] for m in team_members_response.data] if team_members_response.data else []
                    
                    # Get projects for this team (only 1 for recent projects display)
                    projects_response = (
                        self.client.client.table("vmp_projects")
                        .select("id, name, description, current_step, created_at, updated_at")
                        .eq("tenant_id", tenant_id)
                        .order("updated_at", desc=True)
                        .limit(1)  # Show only 1 most recent project
                        .execute()
                    )
                    
                    projects = projects_response.data or []
                    
                    # Get PV report count for this team (PV reports use created_by, not tenant_id)
                    pv_report_count = 0
                    if team_member_ids:
                        pv_report_count_response = (
                            self.client.client.table("documents")
                            .select("id", count="exact")
                            .in_("created_by", team_member_ids)
                            .eq("source_type", "pv_report")
                            .execute()
                        )
                        pv_report_count = pv_report_count_response.count if hasattr(pv_report_count_response, 'count') else 0
                    
                    # Get total project count
                    count_response = (
                        self.client.client.table("vmp_projects")
                        .select("id", count="exact")
                        .eq("tenant_id", tenant_id)
                        .execute()
                    )
                    
                    project_count = count_response.count if hasattr(count_response, 'count') else len(projects)
                    
                    # Populate user fields with team data for consistency
                    team_name = tenant_info.get("name")
                    first_admin_email = team_admin_emails[0] if team_admin_emails else None
                    
                    members.append({
                        # Consistency fields (populated with team data)
                        "user_id": tenant_id,  # Use tenant_id for consistency
                        "user_email": first_admin_email,  # Use first admin email
                        "user_name": team_name,  # Use team name
                        # Team-specific fields (preserved)
                        "team_name": team_name,
                        "team_contact_email": tenant_info.get("contact_email"),
                        "team_admin_emails": team_admin_emails if team_admin_emails else None,
                        "member_type": "team",
                        "tenant_id": tenant_id,
                        "project_count": project_count,
                        "pv_report_count": pv_report_count,
                        "projects": projects
                    })
            
            # Pagination
            total_count = len(members)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_members = members[start_idx:end_idx]
            has_next = end_idx < total_count
            
            return {
                "members": paginated_members,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": has_next
            }
            
        except Exception as e:
            logger.error(f"Error getting organization member projects: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get member projects: {str(e)}"
            )

    def get_tenant_projects(
        self,
        organization_id: str,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get all projects for a specific tenant (individual or team).
        
        Args:
            organization_id: Organization ID
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            {
                "member": {...tenant info...},
                "projects": [...],
                "total_count": int,
                "page": int,
                "page_size": int,
                "has_next": bool
            }
        """
        try:
            # Validate tenant belongs to org
            is_valid, tenant_info = self.validate_tenant_belongs_to_org(organization_id, tenant_id)
            
            if not is_valid:
                raise HTTPException(
                    status_code=404,
                    detail="Tenant not found in this organization"
                )
            
            # Get tenant details
            tenant_response = (
                self.client.client.table("tenants")
                .select("id, name, tenant_type, contact_email")
                .eq("id", tenant_id)
                .execute()
            )
            
            if not tenant_response.data:
                raise HTTPException(status_code=404, detail="Tenant not found")
            
            tenant = tenant_response.data[0]
            
            # Build member info
            member_info = {
                "tenant_id": tenant_id,
                "tenant_type": tenant["tenant_type"],
                "tenant_name": tenant["name"]
            }
            
            # Add user info if individual
            if tenant["tenant_type"] == "individual" and tenant_info.get("user_id"):
                user_response = (
                    self.client.client.table("user_profiles")
                    .select("id, email, full_name")
                    .eq("id", tenant_info["user_id"])
                    .execute()
                )
                
                if user_response.data:
                    user = user_response.data[0]
                    member_info.update({
                        "user_id": user["id"],
                        "user_email": user["email"],
                        "user_name": user["full_name"]
                    })
            
            # Add team info if team
            elif tenant["tenant_type"] == "team":
                # Get team admins from tenant_memberships
                team_admins_response = (
                    self.client.client.table("tenant_memberships")
                    .select("user_id, user_profiles!tenant_memberships_user_id_fkey(email)")
                    .eq("tenant_id", tenant_id)
                    .in_("role", ["owner", "admin"])
                    .eq("is_active", True)
                    .execute()
                )
                
                # Extract admin emails
                team_admin_emails = []
                if team_admins_response.data:
                    for admin_data in team_admins_response.data:
                        user_profile = admin_data.get("user_profiles", {})
                        if user_profile and user_profile.get("email"):
                            team_admin_emails.append(user_profile["email"])
                
                # Populate user fields with team data for consistency
                team_name = tenant["name"]
                first_admin_email = team_admin_emails[0] if team_admin_emails else None
                
                member_info.update({
                    # Consistency fields (populated with team data)
                    "user_id": tenant_id,  # Use tenant_id for consistency
                    "user_email": first_admin_email,  # Use first admin email
                    "user_name": team_name,  # Use team name
                    # Team-specific fields (preserved)
                    "team_id": tenant_id,
                    "team_name": team_name,
                    "team_contact_email": tenant.get("contact_email"),
                    "team_admin_emails": team_admin_emails if team_admin_emails else None
                })
            
            # Get total project count
            count_response = (
                self.client.client.table("vmp_projects")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .execute()
            )
            
            total_count = count_response.count if hasattr(count_response, 'count') else 0
            
            # Get paginated projects
            offset = (page - 1) * page_size
            projects_response = (
                self.client.client.table("vmp_projects")
                .select("id, name, description, current_step, created_at, updated_at")
                .eq("tenant_id", tenant_id)
                .order("updated_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            
            projects = projects_response.data or []
            has_next = (offset + page_size) < total_count
            
            return {
                "member": member_info,
                "projects": projects,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": has_next
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting tenant projects: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get tenant projects: {str(e)}"
            )

    def get_member_project_detail(
        self,
        organization_id: str,
        project_id: str,
        accessed_by_user_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed project data including all generated artifacts.
        
        Args:
            organization_id: Organization ID
            project_id: Project ID
            accessed_by_user_id: User ID accessing the project
            
        Returns:
            Complete project data with PV report and access log
        """
        try:
            # Validate project belongs to org
            is_valid, owner_info = self.validate_project_belongs_to_org(organization_id, project_id)
            
            if not is_valid:
                raise HTTPException(
                    status_code=404,
                    detail="Project not found in this organization"
                )
            
            # Get complete project data
            project_response = (
                self.client.client.table("vmp_projects")
                .select("*")
                .eq("id", project_id)
                .execute()
            )
            
            if not project_response.data:
                raise HTTPException(status_code=404, detail="Project not found")
            
            project = project_response.data[0]
            
            # Get PV Report if linked
            pv_report = None
            if project.get("pv_report_id"):
                pv_report_response = (
                    self.client.client.table("documents")
                    .select("id, title, content")
                    .eq("id", project["pv_report_id"])
                    .execute()
                )
                
                if pv_report_response.data:
                    pv_report = pv_report_response.data[0]
                    # Parse content if it's a JSON string
                    if pv_report.get("content") and isinstance(pv_report["content"], str):
                        try:
                            pv_report["content"] = json.loads(pv_report["content"])
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse PV report content as JSON for report {pv_report['id']}")
                            pv_report["content"] = None
            
            # Log access
            self.log_project_access(
                organization_id=organization_id,
                accessed_by_user_id=accessed_by_user_id,
                target_user_id=owner_info["user_id"],
                project_id=project_id,
                access_type="view"
            )
            
            # Build response
            return {
                "project": project,
                "owner": owner_info,
                "pv_report": pv_report,
                "access_log": {
                    "accessed_by": accessed_by_user_id,
                    "accessed_at": datetime.now(timezone.utc)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting project detail: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get project detail: {str(e)}"
            )

    # ============================================================================
    # Team Soft Delete Methods
    # ============================================================================

    def soft_delete_team(
        self,
        org_id: str,
        team_id: str,
        admin_user_id: str,
        return_credits_to_org: bool = True,
    ) -> Dict[str, Any]:
        """
        Soft delete a team from an organization.
        
        This method:
        1. Verifies the team exists and belongs to the organization
        2. Sets the team tenant's is_active = False
        3. Deactivates all team memberships
        4. Optionally returns remaining credits to the organization
        5. Deactivates team credit lots
        
        Args:
            org_id: Organization tenant ID
            team_id: Team tenant ID to soft delete
            admin_user_id: Admin user performing the deletion
            return_credits_to_org: Whether to return remaining credits to org (default True)
            
        Returns:
            Dict with success status, message, and details about the operation
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            # 1. Verify team exists and is of type 'team'
            team_result = (
                self.client.client.table("tenants")
                .select("id, name, tenant_type, is_active")
                .eq("id", team_id)
                .limit(1)
                .execute()
            )
            
            if not team_result.data:
                raise HTTPException(status_code=404, detail="Team not found")
            
            team = team_result.data[0]
            
            if team.get("tenant_type") != "team":
                raise HTTPException(
                    status_code=400,
                    detail="Invalid tenant type. Only teams can be deleted via this endpoint."
                )
            
            if not team.get("is_active"):
                raise HTTPException(
                    status_code=400,
                    detail="Team is already inactive/deleted"
                )
            
            # 2. Verify the team belongs to this organization
            org_team_link = (
                self.client.client.table("org_teams")
                .select("id")
                .eq("organization_id", org_id)
                .eq("team_id", team_id)
                .limit(1)
                .execute()
            )
            
            if not org_team_link.data:
                raise HTTPException(
                    status_code=403,
                    detail="Team does not belong to this organization"
                )
            
            # 3. Get team members before deactivation (for logging)
            team_memberships = (
                self.client.client.table("tenant_memberships")
                .select("id, user_id, role")
                .eq("tenant_id", team_id)
                .eq("is_active", True)
                .execute()
            ).data or []
            
            members_count = len(team_memberships)
            
            # 4. Handle credit return to organization if requested
            total_credits_returned = 0
            deactivated_lots = []
            
            if return_credits_to_org:
                # Get all active credit lots for this team
                # Note: Removed .or_() as Supabase Python client doesn't support it
                # Expiration filtering done in Python below
                team_lots = (
                    self.client.client.table("credit_lots")
                    .select("id, credit_amount, expires_at, source")
                    .eq("tenant_id", team_id)
                    .eq("is_active", True)
                    .lte("valid_from", now)
                    .execute()
                ).data or []
                
                for lot in team_lots:
                    lot_amount = float(lot.get("credit_amount", 0))
                    
                    if lot_amount > 0:
                        # Create a return lot for the organization
                        return_lot_payload = {
                            "tenant_id": org_id,
                            "original_tenant_id": org_id,
                            "credit_amount": lot_amount,
                            "source": "grant",  # Use grant as it's a valid enum value
                            "valid_from": now,
                            "expires_at": lot.get("expires_at"),
                            "is_active": True,
                            "metadata": {
                                "type": "team_deletion_return",
                                "returned_from_team_id": team_id,
                                "returned_from_team_name": team.get("name"),
                                "original_lot_id": lot["id"],
                                "returned_at": now,
                                "returned_by": admin_user_id,
                            },
                            "created_at": now,
                        }
                        
                        self.client.client.table("credit_lots").insert(
                            return_lot_payload
                        ).execute()
                        
                        total_credits_returned += lot_amount
                    
                    # Deactivate the team's lot
                    self.client.client.table("credit_lots").update({
                        "is_active": False,
                    }).eq("id", lot["id"]).execute()
                    
                    deactivated_lots.append(lot["id"])
            
            # 5. Deactivate all team memberships
            if team_memberships:
                membership_ids = [m["id"] for m in team_memberships]
                self.client.client.table("tenant_memberships").update({
                    "is_active": False,
                    "updated_at": now,
                }).in_("id", membership_ids).execute()
            
            # 6. Deactivate org memberships for users who are ONLY in this deleted team
            # (not in any other active teams and not individual members)
            org_memberships_deactivated = 0
            if team_memberships:
                team_user_ids = [m["user_id"] for m in team_memberships]
                
                # Get all OTHER active teams in this organization
                other_active_teams = (
                    self.client.client.table("org_teams")
                    .select("team_id")
                    .eq("organization_id", org_id)
                    .neq("team_id", team_id)
                    .execute()
                ).data or []
                
                other_team_ids = [t["team_id"] for t in other_active_teams]
                
                # Filter to only active teams
                active_other_team_ids = []
                if other_team_ids:
                    active_teams_result = (
                        self.client.client.table("tenants")
                        .select("id")
                        .in_("id", other_team_ids)
                        .eq("is_active", True)
                        .execute()
                    ).data or []
                    active_other_team_ids = [t["id"] for t in active_teams_result]
                
                # Get users who are in other active teams
                users_in_other_teams = set()
                if active_other_team_ids:
                    other_team_memberships = (
                        self.client.client.table("tenant_memberships")
                        .select("user_id")
                        .in_("tenant_id", active_other_team_ids)
                        .eq("is_active", True)
                        .execute()
                    ).data or []
                    users_in_other_teams = {m["user_id"] for m in other_team_memberships}
                
                # Get users who are individual members (have org_individuals entry)
                individual_members = (
                    self.client.client.table("org_individuals")
                    .select("user_id")
                    .eq("organization_id", org_id)
                    .execute()
                ).data or []
                individual_user_ids = {m["user_id"] for m in individual_members}
                
                # Users to remove from org: in deleted team, NOT in other teams, NOT individual members
                users_to_remove_from_org = [
                    uid for uid in team_user_ids 
                    if uid not in users_in_other_teams and uid not in individual_user_ids
                ]
                
                if users_to_remove_from_org:
                    # Deactivate their organization memberships
                    for user_id in users_to_remove_from_org:
                        org_membership = (
                            self.client.client.table("tenant_memberships")
                            .select("id")
                            .eq("tenant_id", org_id)
                            .eq("user_id", user_id)
                            .eq("is_active", True)
                            .limit(1)
                            .execute()
                        ).data
                        
                        if org_membership:
                            self.client.client.table("tenant_memberships").update({
                                "is_active": False,
                                "updated_at": now,
                            }).eq("id", org_membership[0]["id"]).execute()
                            org_memberships_deactivated += 1
                    
                    logger.info(
                        f"Deactivated {org_memberships_deactivated} organization memberships for users "
                        f"who were only in deleted team {team_id}"
                    )
            
            # 7. Soft delete the team (set is_active = False)
            self.client.client.table("tenants").update({
                "is_active": False,
                "updated_at": now,
                "settings": {
                    **(team.get("settings") or {}),
                    "deleted_at": now,
                    "deleted_by": admin_user_id,
                    "deletion_type": "soft_delete",
                }
            }).eq("id", team_id).execute()
            
            logger.info(
                f"Soft deleted team {team_id} ({team.get('name')}) from organization {org_id}. "
                f"Team members deactivated: {members_count}. "
                f"Org memberships deactivated: {org_memberships_deactivated}. "
                f"Credits returned to org: {total_credits_returned}. "
                f"Credit lots deactivated: {len(deactivated_lots)}. "
                f"Admin: {admin_user_id}"
            )
            
            return {
                "success": True,
                "message": f"Team '{team.get('name')}' has been successfully deleted",
                "team_id": team_id,
                "team_name": team.get("name"),
                "organization_id": org_id,
                "members_deactivated": members_count,
                "org_memberships_deactivated": org_memberships_deactivated,
                "credits_returned_to_org": total_credits_returned,
                "credit_lots_deactivated": len(deactivated_lots),
                "deleted_at": now,
                "deleted_by": admin_user_id,
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error soft deleting team {team_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete team: {str(e)}"
            )

    # =========================================================================
    # CREDIT REQUEST METHODS
    # =========================================================================

    def create_credit_request(
        self,
        user_id: str,
        organization_id: str,
        requested_amount: int,
        reason: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a credit request for a user.
        
        Args:
            user_id: The requesting user's ID
            organization_id: The organization ID
            requested_amount: Amount of credits requested
            reason: Optional reason for the request
            team_id: Optional team ID if user is a team member
            
        Returns:
            The created credit request record
        """
        try:
            # Check if user already has a pending request for this org
            existing = (
                self.client.client.table("credit_requests")
                .select("id, status, requested_amount, created_at")
                .eq("user_id", user_id)
                .eq("organization_id", organization_id)
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            
            if existing.data:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "pending_request_exists",
                        "message": "You already have a pending credit request. Please wait for it to be reviewed.",
                        "existing_request_id": existing.data[0]["id"],
                    }
                )
            
            # Create the credit request
            payload = {
                "user_id": user_id,
                "organization_id": organization_id,
                "requested_amount": requested_amount,
                "reason": reason,
                "team_id": team_id,
                "status": "pending",
            }
            
            result = (
                self.client.client.table("credit_requests")
                .insert(payload)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create credit request"
                )
            
            logger.info(
                f"Credit request created: user={user_id}, org={organization_id}, "
                f"amount={requested_amount}, team={team_id}"
            )
            
            return result.data[0]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating credit request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create credit request: {str(e)}"
            )

    def get_credit_requests_for_org(
        self,
        organization_id: str,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Get all credit requests for an organization.
        
        This fetches credit requests by:
        1. Direct organization_id match
        2. Team_id match (where team belongs to this organization)
        
        This ensures we catch all requests even if organization_id was stored incorrectly.
        
        Args:
            organization_id: The organization ID
            status_filter: Optional status to filter by (pending, approved, rejected, fulfilled)
            limit: Maximum number of requests to return
            
        Returns:
            Dict with requests list and counts
        """
        try:
            # First, get all team IDs that belong to this organization
            try:
                org_teams = (
                    self.client.client.table("org_teams")
                    .select("team_id")
                    .eq("organization_id", organization_id)
                    .execute()
                ).data or []
            except Exception as e:
                logger.warning(f"get_credit_requests_for_org: failed fetching org_teams: {e}")
                org_teams = []
            team_ids = [t["team_id"] for t in org_teams]
            
            # Also get individual member tenant IDs (org_individuals table)
            try:
                org_individuals = (
                    self.client.client.table("org_individuals")
                    .select("individual_tenant_id")
                    .eq("organization_id", organization_id)
                    .execute()
                ).data or []
            except Exception as e:
                logger.warning(f"get_credit_requests_for_org: failed fetching org_individuals: {e}")
                org_individuals = []
            individual_tenant_ids = [m["individual_tenant_id"] for m in org_individuals]
            
            # Query credit requests by organization_id OR team_id in org's teams
            # This handles cases where organization_id might have been stored incorrectly
            all_requests = []
            
            # 1. Get requests with correct organization_id
            try:
                query1 = (
                    self.client.client.table("credit_requests")
                    .select("*")
                    .eq("organization_id", organization_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                )
                if status_filter:
                    query1 = query1.eq("status", status_filter)
                result1 = query1.execute()
                all_requests.extend(result1.data or [])
            except Exception as e:
                logger.warning(f"get_credit_requests_for_org: failed primary credit_requests fetch: {e}")
            
            # 2. Get requests where team_id is in org's teams (but org_id might be wrong)
            if team_ids:
                try:
                    query2 = (
                        self.client.client.table("credit_requests")
                        .select("*")
                        .in_("team_id", team_ids)
                        .order("created_at", desc=True)
                        .limit(limit)
                    )
                    if status_filter:
                        query2 = query2.eq("status", status_filter)
                    result2 = query2.execute()
                    all_requests.extend(result2.data or [])
                except Exception as e:
                    logger.warning(f"get_credit_requests_for_org: failed team_id credit_requests fetch: {e}")
            
            # 3. Get requests where organization_id is a team's tenant_id (incorrectly stored)
            if team_ids:
                try:
                    query3 = (
                        self.client.client.table("credit_requests")
                        .select("*")
                        .in_("organization_id", team_ids)
                        .order("created_at", desc=True)
                        .limit(limit)
                    )
                    if status_filter:
                        query3 = query3.eq("status", status_filter)
                    result3 = query3.execute()
                    all_requests.extend(result3.data or [])
                except Exception as e:
                    logger.warning(f"get_credit_requests_for_org: failed org_id-in-team_ids credit_requests fetch: {e}")
            
            # 4. Get requests where organization_id is an individual tenant_id (incorrectly stored)
            if individual_tenant_ids:
                try:
                    query4 = (
                        self.client.client.table("credit_requests")
                        .select("*")
                        .in_("organization_id", individual_tenant_ids)
                        .order("created_at", desc=True)
                        .limit(limit)
                    )
                    if status_filter:
                        query4 = query4.eq("status", status_filter)
                    result4 = query4.execute()
                    all_requests.extend(result4.data or [])
                except Exception as e:
                    logger.warning(f"get_credit_requests_for_org: failed org_id-in-individual_ids credit_requests fetch: {e}")
            
            # Deduplicate by request ID
            seen_ids = set()
            requests = []
            for req in all_requests:
                if req["id"] not in seen_ids:
                    seen_ids.add(req["id"])
                    requests.append(req)
            
            # Sort by created_at descending and limit
            requests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            requests = requests[:limit]
            
            # Get pending count (same logic - check all possible sources)
            pending_count = sum(1 for r in requests if r.get("status") == "pending")
            
            # Enrich with user info
            user_ids = list({r["user_id"] for r in requests})
            team_ids = list({r["team_id"] for r in requests if r.get("team_id")})
            
            users_map = {}
            if user_ids:
                users = (
                    self.client.client.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", user_ids)
                    .execute()
                ).data or []
                users_map = {u["id"]: u for u in users}
            
            teams_map = {}
            if team_ids:
                teams = (
                    self.client.client.table("tenants")
                    .select("id, name")
                    .in_("id", team_ids)
                    .execute()
                ).data or []
                teams_map = {t["id"]: t for t in teams}
            
            # Enrich requests
            enriched = []
            for req in requests:
                user = users_map.get(req["user_id"], {})
                team = teams_map.get(req.get("team_id"), {}) if req.get("team_id") else {}
                enriched.append({
                    **req,
                    "user_name": user.get("full_name"),
                    "user_email": user.get("email"),
                    "team_name": team.get("name"),
                })
            
            return {
                "requests": enriched,
                "total_count": len(enriched),
                "pending_count": pending_count,
            }
            
        except Exception as e:
            logger.error(f"Error fetching credit requests for org {organization_id}: {str(e)}")
            # Return empty result instead of raising to keep UI functional
            return {"requests": [], "total_count": 0, "pending_count": 0}

    def get_user_credit_requests(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get credit requests for a specific user.
        
        Args:
            user_id: The user's ID
            organization_id: Optional organization ID to filter by
            
        Returns:
            List of credit requests
        """
        try:
            query = (
                self.client.client.table("credit_requests")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
            )
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error fetching credit requests for user {user_id}: {str(e)}")
            return []

    def update_credit_request(
        self,
        request_id: str,
        reviewer_id: str,
        new_status: str,
        review_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a credit request status (approve/reject).
        
        Args:
            request_id: The credit request ID
            reviewer_id: The reviewer's user ID
            new_status: New status (approved, rejected)
            review_notes: Optional notes from reviewer
            
        Returns:
            Updated credit request record
        """
        try:
            if new_status not in ["approved", "rejected"]:
                raise HTTPException(
                    status_code=400,
                    detail="Status must be 'approved' or 'rejected'"
                )
            
            # Get current request
            current = (
                self.client.client.table("credit_requests")
                .select("*")
                .eq("id", request_id)
                .limit(1)
                .execute()
            )
            
            if not current.data:
                raise HTTPException(status_code=404, detail="Credit request not found")
            
            request = current.data[0]
            
            if request["status"] != "pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot update request with status '{request['status']}'. Only pending requests can be updated."
                )
            
            # Update the request
            now = datetime.now(timezone.utc).isoformat()
            update_payload = {
                "status": new_status,
                "reviewed_by": reviewer_id,
                "reviewed_at": now,
                "review_notes": review_notes,
                "updated_at": now,
            }
            
            result = (
                self.client.client.table("credit_requests")
                .update(update_payload)
                .eq("id", request_id)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update credit request"
                )
            
            logger.info(
                f"Credit request {request_id} updated to {new_status} by {reviewer_id}"
            )
            
            return result.data[0]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating credit request {request_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update credit request: {str(e)}"
            )

    def get_pending_credit_requests_by_users(
        self,
        user_ids: List[str],
        organization_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get pending credit requests for a list of users.
        Used for enriching member lists with credit request status.
        
        Args:
            user_ids: List of user IDs
            organization_id: The organization ID
            
        Returns:
            Dict mapping user_id to their pending request info
        """
        if not user_ids:
            return {}
        
        try:
            # Get pending requests for these users
            pending = (
                self.client.client.table("credit_requests")
                .select("id, user_id, requested_amount, created_at, status")
                .eq("organization_id", organization_id)
                .in_("user_id", user_ids)
                .eq("status", "pending")
                .execute()
            ).data or []
            
            # Also get most recent request for users who don't have pending
            all_recent = (
                self.client.client.table("credit_requests")
                .select("id, user_id, status, created_at")
                .eq("organization_id", organization_id)
                .in_("user_id", user_ids)
                .order("created_at", desc=True)
                .execute()
            ).data or []
            
            # Build mapping
            result = {}
            pending_by_user = {r["user_id"]: r for r in pending}
            
            # Track most recent request per user
            recent_by_user = {}
            for r in all_recent:
                if r["user_id"] not in recent_by_user:
                    recent_by_user[r["user_id"]] = r
            
            for user_id in user_ids:
                pending_req = pending_by_user.get(user_id)
                recent_req = recent_by_user.get(user_id)
                
                result[user_id] = {
                    "has_pending_request": pending_req is not None,
                    "pending_request_id": pending_req["id"] if pending_req else None,
                    "pending_request_amount": pending_req["requested_amount"] if pending_req else None,
                    "pending_request_date": pending_req["created_at"] if pending_req else None,
                    "last_request_status": recent_req["status"] if recent_req else None,
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching pending credit requests: {str(e)}")
            return {}

    def is_grant_organization(self, organization_id: str) -> bool:
        """
        Check if an organization is a grant organization.
        
        Args:
            organization_id: The organization ID
            
        Returns:
            True if the organization is a grant_org, False otherwise
        """
        try:
            config = (
                self.client.client.table("organization_billing_config")
                .select("organization_type")
                .eq("tenant_id", organization_id)
                .limit(1)
                .execute()
            )
            
            if config.data:
                return config.data[0].get("organization_type") == "grant_org"
            
            # Default to grant_org if no config exists
            return True
            
        except Exception as e:
            logger.error(f"Error checking org type for {organization_id}: {str(e)}")
            return True  # Default to grant_org
