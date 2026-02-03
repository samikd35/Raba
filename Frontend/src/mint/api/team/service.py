import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..credit.service import CreditService
from ..services.communication.email_service import email_service
from ..system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class TeamService:
    def __init__(self, use_service_role: bool = True):
        self.supabase = get_supabase_client(use_service_role=use_service_role).client

    # -------------------
    # Team creation
    # -------------------
    def create_team(
        self, user_id: str, body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new team tenant and link to an org tenant."""

        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "name": body["name"],
            "tenant_type": "team",
            "description": body.get("description"),
            "website": body.get("website"),
            "industry": body.get("industry"),
            "size": body.get("size"),
            "country": body.get("country"),
            "settings": body.get("settings") or {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        res = self.supabase.table("tenants").insert(payload).execute()
        if not res.data:
            return None
        team = res.data[0]

        permissions = self._get_default_permissions("owner")
        payload = {
            "tenant_id": team["id"],
            "user_id": user_id,
            "role": "owner",
            "is_active": True,
            "joined_at": now,
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
        }
        self.supabase.table("tenant_memberships").insert(payload).execute()

        return team

    def _has_team_leader_invite(self, org_id: str, email: str) -> bool:
        """
        True if the user has (or had) a team_leader invitation for this org.
        We allow status in ('queued','sent','accepted') to cover pre- and post-join.
        """
        try:
            # First, let's check all invitations for this user and org for debugging
            all_invites = (
                self.supabase.table("organization_invitations")
                .select("*")
                .eq("organization_id", org_id)
                .eq("email", (email or "").strip())
                .execute()
            )
            logger.info(
                f"🔍 DEBUG: All invitations for {email} in org {org_id}: {all_invites.data}"
            )

            # Now check specifically for team leader invitations
            res = (
                self.supabase.table("organization_invitations")
                .select("*")  # Select all fields for debugging
                .eq("organization_id", org_id)
                .eq("email", (email or "").strip())
                .eq("is_team_leader", True)
                .in_("status", ["queued", "sent", "accepted"])
                .limit(1)
                .execute()
            )
            logger.info(f"🔍 DEBUG: Team leader invitations for {email}: {res.data}")
            logger.info(f"🔍 DEBUG: Has team leader invite: {bool(res.data)}")
            return bool(res.data)
        except Exception as e:
            logger.error(f"Failed to check team_leader invitation for {email}: {e}")
            return False

    def create_team_tenant(
        self, org_id: str, user_id: str, user_email: str, body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new team tenant and link to an org tenant."""
        # --- NEW: enforce team_leader invitation gate ---
        if not self._has_team_leader_invite(org_id, user_email):
            raise ValueError(
                "Only members with a team leader invitation can create teams"
            )

        org = (
            self.supabase.table("tenants")
            .select("id, tenant_type")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        if not org.data or org.data[0]["tenant_type"] != "organization":
            raise ValueError("Invalid organization tenant")

        # 2. Check for duplicate team name inside org
        org_teams = (
            self.supabase.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .execute()
        )

        team_ids = [t["team_id"] for t in org_teams.data]

        # 2. Check for duplicate name or if user already owns a team within this organization
        if team_ids:
            owned_team = (
                self.supabase.table("tenant_memberships")
                .select("tenant_id")
                .in_("tenant_id", team_ids)
                .eq("user_id", user_id)
                .eq("role", "owner")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if owned_team.data:
                raise ValueError("You already own a team within this organization")

            existing_team = (
                self.supabase.table("tenants")
                .select("id")
                .in_("id", team_ids)
                .eq("name", body["name"])
                .limit(1)
                .execute()
            )
        else:
            existing_team = None

        if existing_team and existing_team.data:
            raise ValueError(
                f"Team with name '{body['name']}' already exists in this organization"
            )

        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "name": body["name"],
            "tenant_type": "team",
            "description": body.get("description"),
            "website": body.get("website"),
            "industry": body.get("industry"),
            "size": body.get("size"),
            "country": body.get("country"),
            "settings": body.get("settings") or {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        res = self.supabase.table("tenants").insert(payload).execute()
        if not res.data:
            return None
        team = res.data[0]

        permissions = self._get_default_permissions("owner")
        payload = {
            "tenant_id": team["id"],
            "user_id": user_id,
            "role": "owner",
            "is_active": True,
            "joined_at": now,
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
        }
        logger.info(
            f"✅ Creating team leader membership for user {user_id} in team {team['id']}"
        )
        logger.info(f"📋 Membership payload: {payload}")
        membership_result = (
            self.supabase.table("tenant_memberships").insert(payload).execute()
        )
        logger.info(f"✅ Team leader membership created: {membership_result.data}")

        self.supabase.table("org_teams").insert(
            {
                "organization_id": org_id,
                "team_id": team["id"],
                "created_by": user_id,
                "created_at": now,
            }
        ).execute()

        pending = (
            self.supabase.table("pending_team_credits")
            .select("*")
            .eq("organization_id", org_id)
            .eq("admin_email", user_email)
            .eq("assigned", False)
            .limit(1)
            .execute()
        )

        if pending.data:
            record = pending.data[0]
            admin_email = record["admin_email"]
            credit_amount = Decimal(str(record["credit_amount"]))

            logger.info(
                f"Found pending admin credits ({credit_amount}) for {admin_email}"
            )

            # Get organization type to determine allocation strategy
            org_config_response = self.supabase.table('organization_billing_config') \
                .select('organization_type') \
                .eq('tenant_id', org_id) \
                .limit(1) \
                .execute()

            org_type = 'grant_org'  # default
            if org_config_response.data and len(org_config_response.data) > 0:
                org_type = org_config_response.data[0].get('organization_type', 'grant_org')

            credit_service = CreditService()

            if org_type == 'postpay_org':
                # For postpay orgs, create credit lot without deducting from org
                # No expiry for postpay credits
                created_lot = credit_service.create_credit_lot(
                    tenant_id=team["id"],
                    source="purchase",
                    credit_amount=credit_amount,
                    valid_from=now,
                    expires_at=None,  # No expiry
                    metadata={
                        "source": "organization_transfer",
                        "organization_id": org_id,
                        "assigned_by_admin": True,
                        "admin_email": admin_email,
                    },
                    original_tenant_id=org_id,
                )

                # Record allocation for billing
                try:
                    self.supabase.table('organization_credit_allocations').insert({
                        'tenant_id': org_id,
                        'allocation_type': 'allocation_to_team',
                        'credit_amount': float(credit_amount),
                        'credit_lot_id': created_lot.get('id') if created_lot else None,
                        'allocated_to_tenant_id': team["id"],
                        'allocated_to_user_id': None,
                        'allocated_by_user_id': user_id,
                        'allocated_at': now,
                        'metadata': {
                            "source": "team_creation",
                            "admin_email": admin_email
                        },
                    }).execute()
                    logger.info(
                        f"Recorded postpay team allocation for org {org_id}: "
                        f"{credit_amount} credits to team {team['id']}"
                    )
                except Exception as e:
                    logger.error(f"Failed to record postpay team allocation: {e}", exc_info=True)

                self.supabase.table("pending_team_credits").update(
                    {"assigned": True, "assigned_at": now}
                ).eq("id", record["id"]).execute()

                logger.info(
                    f"Allocated {credit_amount} credits to team {team['id']} "
                    f"for postpay org {org_id}"
                )
            else:
                # For grant_org and prepay_org, deduct from org lots
                # Fetch org lots with appropriate filtering
                # Note: Removed .or_() as Supabase Python client doesn't support it
                # Expiration and reservation filtering is done in Python below
                lots_query = (
                    self.supabase.table("credit_lots")
                    .select("id, credit_amount, expires_at, source, reserved_until")
                    .eq("tenant_id", org_id)
                    .eq("is_active", True)
                    .lte("valid_from", now)
                    .order("expires_at", desc=False)
                )

                # Filter by source based on organization type
                if org_type == 'grant_org':
                    lots_query = lots_query.eq("source", "grant")
                elif org_type == 'prepay_org':
                    lots_query = lots_query.in_("source", ["purchase", "payment", "top_up"])

                all_lots = lots_query.execute().data or []

                # Filter out expired and reserved lots in Python
                org_lots = []
                for lot in all_lots:
                    expires_at = lot.get("expires_at")
                    reserved_until = lot.get("reserved_until")

                    # Check if expired
                    is_expired = expires_at is not None and str(expires_at) <= now

                    # Check if reserved
                    is_reserved = reserved_until is not None and str(reserved_until) > now

                    if not is_expired and not is_reserved:
                        org_lots.append(lot)

                total_available = sum(float(lot["credit_amount"]) for lot in org_lots)
                if total_available < credit_amount:
                    logger.warning(
                        f"Organization {org_id} has insufficient credits for team allocation."
                    )
                else:
                    remaining = credit_amount

                    for lot in org_lots:
                        if remaining <= 0:
                            break

                        lot_credits = Decimal(str(lot["credit_amount"]))
                        deduct = min(lot_credits, remaining)
                        new_balance = lot_credits - deduct

                        # Deduct from org lot
                        self.supabase.table("credit_lots").update(
                            {"credit_amount": float(new_balance)}
                        ).eq("id", lot["id"]).execute()

                        # Determine expiry: grant_org uses lot expiry, prepay_org has no expiry
                        lot_expires_at = lot["expires_at"] if org_type == 'grant_org' else None

                        # Allocate new credit lot to the team
                        credit_service.create_credit_lot(
                            tenant_id=team["id"],
                            source=lot["source"],
                            credit_amount=deduct,
                            valid_from=now,
                            expires_at=lot_expires_at,
                            metadata={
                                "source": "organization_transfer",
                                "organization_id": org_id,
                                "origin_lot_id": lot["id"],
                                "assigned_by_admin": True,
                                "admin_email": admin_email,
                            },
                            original_tenant_id=org_id,
                        )

                        remaining -= deduct

                    self.supabase.table("pending_team_credits").update(
                        {"assigned": True, "assigned_at": now}
                    ).eq("id", record["id"]).execute()

                    logger.info(
                        f"Allocated {credit_amount} credits from org {org_id} "
                        f"to team {team['id']} and marked pending record as assigned."
                    )

        return team

    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.supabase.table("tenants")
            .select("*")
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def update_team(self, team_id: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update team details."""
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in body.items() if v is not None}

        if not update_data:
            raise ValueError("No fields to update")

        # Add updated_at timestamp
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Update the team
        res = (
            self.supabase.table("tenants")
            .update(update_data)
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .execute()
        )

        if not res.data:
            return None

        return res.data[0]

    def get_teams_by_org(self, org_id: str) -> List[Dict[str, Any]]:
        res = (
            self.supabase.table("org_teams")
            .select("*")
            .eq("organization_id", org_id)
            .execute()
        )
        return res.data or []

    def list_org_teams(self, org_id: str) -> list[Dict[str, Any]]:
        res = (
            self.supabase.table("org_teams")
            .select("team_id, tenants!org_teams_team_id_fkey(*)")
            .eq("organization_id", org_id)
            .execute()
        )
        return res.data or []

    # -------------------
    # Membership handling
    # -------------------
    def add_or_update_team_membership(
        self, team_id: str, user_id: str, user_email: str, role: str = "member"
    ) -> Dict[str, Any]:
        """Insert or update a user's membership in a team with correct permissions."""
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing membership
        existing = (
            self.supabase.table("tenant_memberships")
            .select("*")
            .eq("tenant_id", team_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        permissions = self._get_default_permissions(role)

        if existing.data:
            membership = existing.data[0]
            updates: Dict[str, Any] = {}

            if not membership.get("is_active", True):
                updates["is_active"] = True
                updates["joined_at"] = now

            if membership.get("role") != role:
                updates["role"] = role
                updates["permissions"] = permissions

            if updates:
                updates["updated_at"] = now
                updated = (
                    self.supabase.table("tenant_memberships")
                    .update(updates)
                    .eq("id", membership["id"])
                    .execute()
                )
                return updated.data[0] if updated.data else membership

            return membership

        # Insert new membership
        payload = {
            "tenant_id": team_id,
            "user_id": user_id,
            "role": role,
            "is_active": True,
            "joined_at": now,
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self.supabase.table("tenant_memberships").insert(payload).execute()

        payload = {"status": "accepted", "accepted_by": user_id, "accepted_at": now}
        self.supabase.table("team_invitations").update(payload).eq(
            "team_id", team_id
        ).eq("email", user_email).execute()
        return inserted.data[0] if inserted.data else None

    # ----------------------
    # Invitations
    # ----------------------
    def record_invitation(
        self,
        team_id: str,
        email: str,
        role: str,
        invited_by: str,
        invited_by_email: str,
        allow_resend: bool = False,
    ) -> Dict[str, Any]:
        # Check for existing invitation
        existing = (
            self.supabase.table("team_invitations")
            .select("id, status")
            .eq("team_id", team_id)
            .eq("email", email)
            .limit(1)
            .execute()
        )

        if existing.data:
            inv = existing.data[0]
            # If invitation is "queued", "failed", or "sent", allow automatic resend
            if inv["status"] in ["queued", "failed", "sent"]:
                logger.info(
                    f"🔄 Resending invitation (status: {inv['status']}) for {email}"
                )
                # Update the existing invitation
                self.supabase.table("team_invitations").update(
                    {
                        "status": "queued",
                        "invited_at": datetime.now(timezone.utc).isoformat(),
                        "invited_by": invited_by,
                        "invited_by_email": invited_by_email,
                    }
                ).eq("id", inv["id"]).execute()
                return inv
            # If accepted, user is already a member
            elif inv["status"] == "accepted":
                raise HTTPException(
                    status_code=409,
                    detail="User has already accepted the invitation and is a team member.",
                )

        # Create new invitation
        payload = {
            "team_id": team_id,
            "email": email,
            "role": "admin" if role else "member",
            "invited_by": invited_by,
            "invited_by_email": invited_by_email,
            "status": "queued",
            "invited_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self.supabase.table("team_invitations").insert(payload).execute()
        if not res or not res.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create invitation",
            )
        return res.data[0]

    def update_invitation_status(
        self,
        invitation_id: str,
        status: str,
        error: Optional[str] = None,
        sent_at: Optional[datetime] = None,
    ):
        payload = {"status": status}
        if error:
            payload["error"] = error
        self.supabase.table("team_invitations").update(payload).eq(
            "id", invitation_id
        ).execute()

    def _is_team_org_associated(self, team_id: str) -> bool:
        """
        Check if a team is associated with an organization.

        Args:
            team_id: The team ID to check

        Returns:
            bool: True if team is linked to an organization, False otherwise
        """
        try:
            org_link = (
                self.supabase.table("org_teams")
                .select("organization_id")
                .eq("team_id", team_id)
                .limit(1)
                .execute()
            )
            return bool(org_link.data)
        except Exception as e:
            logger.error(f"Failed to check team org association for {team_id}: {e}")
            return False

    def _send_team_invite_and_update(
        self,
        invitation_id: str,
        to_email: str,
        team_id: str,
        invite_link: str,
        inviter_name: str = None,
    ):
        try:
            team = self.get_team(team_id)
            team_name = team["name"]

            # Check if team is associated with an organization
            is_org_associated = self._is_team_org_associated(team_id)

            if is_org_associated:
                # Use the organization team invite email for org-associated teams
                email_sent = email_service.send_org_team_invite_email(
                    to_email=to_email,
                    team_name=team_name,
                    inviter_name=inviter_name or "Team Admin",
                    invite_link=invite_link
                )
            else:
                # Use the independent team invite email
                email_sent = email_service.send_independent_team_invite_email(
                    to_email=to_email, team_name=team_name, invite_link=invite_link
                )

            if email_sent:
                self.update_invitation_status(
                    invitation_id=invitation_id,
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong trying to send the message",
                )
        except Exception as e:
            logger.error(f"Team invite email failed for {to_email}: {e}")
            self.update_invitation_status(
                invitation_id=invitation_id, status="failed", error=str(e)
            )

    def is_org_member(self, org_id: str, user_id: str) -> bool:
        res = (
            self.supabase.table("tenant_memberships")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return bool(res.data)

    def get_team_metrics(self, team_id: str) -> Dict[str, Any]:
        """Get invitations and membership metrics for an organization."""

        # --- Invitations ---
        invites = (
            self.supabase.table("team_invitations")
            .select("id, status")
            .eq("team_id", team_id)
            .execute()
        ).data or []

        num_sent = sum(
            1
            for inv in invites
            if inv["status"] != "failed" and inv["status"] != "queued"
        )
        num_accepted = sum(1 for inv in invites if inv["status"] == "accepted")

        # --- All members of the organization ---
        team_memberships = (
            self.supabase.table("tenant_memberships")
            .select("user_id")
            .eq("tenant_id", team_id)
            .execute()
        ).data or []

        return {
            "invitations": {
                "sent": num_sent,
                "accepted": num_accepted,
            },
            "membership": {
                "total": len(team_memberships),
            },
        }

    def delete_team_tenant(self, team_id: str, user_id: str) -> bool:
        """
        Delete a team tenant.
        Cascading deletes will clean up memberships and invitations.
        """
        try:
            # Ensure team exists
            res = (
                self.supabase.table("tenants")
                .select("id, tenant_type")
                .eq("id", team_id)
                .limit(1)
                .execute()
            )
            if not res.data:
                raise HTTPException(status_code=404, detail="Team not found")

            team = res.data[0]
            self.supabase.table("tenants").delete().eq("id", team_id).execute()
        except Exception as e:
            logger.error(f"Failed to delete team tenant: {e}")
            logger.error(f"🔍 PAYLOAD DEBUG: {team_id}")

            # Check if it's a constraint violation
            if hasattr(e, "json") and callable(e.json):
                error_details = e.json()
                logger.error(f"🔍 CONSTRAINT ERROR: {error_details}")

            raise HTTPException(
                status_code=500, detail=f"Failed to delete team: {str(e)}"
            )

        return True

    def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get all members of a team with their details.
        Returns a list of team members with user profile information.
        """
        try:
            # Fetch team memberships with user profile data
            memberships = (
                self.supabase.table("tenant_memberships")
                .select(
                    "*, user_profiles!tenant_memberships_user_id_fkey(id, email, full_name)"
                )
                .eq("tenant_id", team_id)
                .eq("is_active", True)
                .execute()
            ).data or []

            # Transform the data to match the expected format
            members = []
            for membership in memberships:
                user_profile = membership.get("user_profiles", {})
                members.append(
                    {
                        "id": membership.get("id"),
                        "user_id": membership.get("user_id"),
                        "name": user_profile.get("full_name", "Unknown"),
                        "email": user_profile.get("email", ""),
                        "role": membership.get("role", "member"),
                        "team_id": team_id,
                        "status": (
                            "active" if membership.get("is_active") else "inactive"
                        ),
                        "joined_date": membership.get("joined_at")
                        or membership.get("created_at"),
                        "permissions": membership.get("permissions", {}),
                    }
                )

            return members
        except Exception as e:
            logger.error(f"Failed to get team members for team {team_id}: {e}")
            return []

    def delete_team_member(
        self, team_id: str, user_id: str, admin_user_id: str
    ) -> Dict[str, Any]:
        """
        Remove a member from a team.
        
        Steps:
        1. Verify the membership exists
        2. Prevent deletion of team owner
        3. Delete the tenant_membership record
        4. Delete any pending invitations for this user
        
        Args:
            team_id: Team tenant ID
            user_id: User ID to remove
            admin_user_id: Admin performing the action
            
        Returns:
            Success response with details
        """
        try:
            # 1. Verify membership exists
            membership = (
                self.supabase.table("tenant_memberships")
                .select("id, role")
                .eq("tenant_id", team_id)
                .eq("user_id", user_id)
                .execute()
            ).data

            if not membership:
                raise HTTPException(
                    status_code=404, detail="Member not found in this team"
                )

            membership = membership[0]

            # 2. Prevent deletion of team owner
            if membership.get("role") == "owner":
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove the team owner. Transfer ownership first or delete the team.",
                )

            # 3. Delete the tenant_membership record
            self.supabase.table("tenant_memberships").delete().eq(
                "id", membership["id"]
            ).execute()

            # 4. Update any pending invitations to allow re-invite
            try:
                # Get user email for invitation cleanup
                user_profile = (
                    self.supabase.table("user_profiles")
                    .select("email")
                    .eq("id", user_id)
                    .execute()
                ).data
                
                if user_profile:
                    user_email = user_profile[0].get("email")
                    if user_email:
                        # Mark invitation as removed (allows re-invite)
                        self.supabase.table("team_invitations").update(
                            {"status": "removed"}
                        ).eq("team_id", team_id).eq("email", user_email).execute()
            except Exception as e:
                logger.warning(f"Could not update team invitations: {e}")

            logger.info(
                f"Deleted member {user_id} from team {team_id}. Admin: {admin_user_id}"
            )

            return {
                "success": True,
                "message": "Member removed from team successfully",
                "user_id": user_id,
                "team_id": team_id,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting team member: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to remove member: {str(e)}"
            )

    def _get_default_permissions(self, role: str) -> Dict[str, Any]:
        """Get default permissions for a team role"""
        if role == "owner":
            return {
                "can_manage_team": True,
                "can_invite": True,
                "can_edit": True,
                "can_delete": True,
            }
        elif role == "admin":
            return {
                "can_manage_team": True,
                "can_invite": True,
                "can_edit": True,
                "can_delete": False,
            }
        else:  # member
            return {
                "can_manage_team": False,
                "can_invite": False,
                "can_edit": False,
                "can_delete": False,
            }
