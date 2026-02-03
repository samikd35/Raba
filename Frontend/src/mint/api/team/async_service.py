"""
Async Team service for high-performance API operations.

This is an optimized async version that uses:
- asyncio.gather() for parallel database queries
- Async Supabase client for non-blocking operations
- Async credit service for credit calculations
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..system.core.async_supabase_client import get_async_supabase_client
from ..credit.async_service import get_async_credit_service

logger = logging.getLogger(__name__)


class AsyncTeamService:
    """Async service class for team operations with optimized parallel queries."""

    def __init__(self):
        self.credit_service = get_async_credit_service()

    # =========================================================================
    # Team Details (Async with Parallel Queries)
    # =========================================================================

    async def get_team_details(
        self,
        team_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a team including name, organization, credits, etc.

        OPTIMIZED: Uses asyncio.gather for 6 parallel queries instead of sequential.
        """
        client = await get_async_supabase_client()

        # Phase 1: Get team and org_link in parallel (need org_id for next phase)
        team_task = (
            client.table("tenants")
            .select("*")
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .limit(1)
            .execute()
        )
        org_link_task = (
            client.table("org_teams")
            .select("organization_id")
            .eq("team_id", team_id)
            .limit(1)
            .execute()
        )

        team_result, org_link_result = await asyncio.gather(team_task, org_link_task)

        if not team_result.data:
            raise HTTPException(status_code=404, detail="Team not found")

        team_data = team_result.data[0]
        org_id = (
            org_link_result.data[0]["organization_id"] if org_link_result.data else None
        )

        # Phase 2: Run remaining queries in parallel
        tasks = [
            # Task 1: Get leader info
            client.table("tenant_memberships")
            .select(
                "user_id, user_profiles!tenant_memberships_user_id_fkey(email, full_name)"
            )
            .eq("tenant_id", team_id)
            .eq("role", "owner")
            .limit(1)
            .execute(),
            # Task 2: Get member count
            client.table("tenant_memberships")
            .select("id")
            .eq("tenant_id", team_id)
            .eq("is_active", True)
            .execute(),
            # Task 3: Get current user's role
            client.table("tenant_memberships")
            .select("role")
            .eq("tenant_id", team_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute(),
            # Task 4: Get credit summary (async)
            self.credit_service.get_credit_summary(team_id),
        ]

        # Add org name lookup if we have org_id
        if org_id:
            tasks.append(
                client.table("tenants")
                .select("name")
                .eq("id", org_id)
                .limit(1)
                .execute()
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract results
        leader_result = results[0] if not isinstance(results[0], Exception) else None
        members_result = results[1] if not isinstance(results[1], Exception) else None
        user_role_result = results[2] if not isinstance(results[2], Exception) else None
        credit_summary = results[3] if not isinstance(results[3], Exception) else {}

        leader_data = {}
        if leader_result and leader_result.data:
            leader_data = leader_result.data[0]
        leader_profile = leader_data.get("user_profiles", {})

        member_count = (
            len(members_result.data) if members_result and members_result.data else 0
        )
        user_role = (
            user_role_result.data[0]["role"]
            if user_role_result and user_role_result.data
            else "member"
        )

        org_name = ""
        if org_id and len(results) > 4:
            org_result = results[4]
            if not isinstance(org_result, Exception) and org_result.data:
                org_name = org_result.data[0].get("name", "")

        # Handle credit summary
        if isinstance(credit_summary, Exception):
            logger.warning(f"Failed to get credit summary: {credit_summary}")
            credit_summary = {
                "total_credits": 0,
                "consumed_credits": 0,
                "remaining_credits": 0,
            }

        return {
            "id": team_data["id"],
            "name": team_data["name"],
            "description": team_data.get("description"),
            "organization_id": org_id or "",
            "organization_name": org_name,
            "team_leader_id": leader_data.get("user_id", ""),
            "team_leader_name": leader_profile.get("full_name", ""),
            "team_leader_email": leader_profile.get("email", ""),
            "member_count": member_count,
            "user_role": user_role,
            "credit_pool_total": credit_summary.get("total_credits", 0),
            "credit_pool_used": credit_summary.get("consumed_credits", 0),
            "credit_pool_remaining": credit_summary.get("remaining_credits", 0),
            "pool_reset_date": "",
            "status": "active" if team_data.get("is_active") else "inactive",
            "created_at": team_data.get("created_at"),
        }

    # =========================================================================
    # Team Listing
    # =========================================================================

    async def get_teams_by_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all teams in an organization."""
        client = await get_async_supabase_client()

        result = await (
            client.table("org_teams")
            .select("*")
            .eq("organization_id", org_id)
            .execute()
        )

        return result.data or []

    async def list_org_teams(self, org_id: str) -> List[Dict[str, Any]]:
        """List all teams with tenant details for an organization."""
        client = await get_async_supabase_client()

        result = await (
            client.table("org_teams")
            .select("team_id, tenants!org_teams_team_id_fkey(*)")
            .eq("organization_id", org_id)
            .execute()
        )

        return result.data or []

    # =========================================================================
    # Team CRUD
    # =========================================================================

    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get a team by ID."""
        client = await get_async_supabase_client()

        result = await (
            client.table("tenants")
            .select("*")
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def update_team(
        self,
        team_id: str,
        body: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update team details."""
        client = await get_async_supabase_client()

        # Filter out None values
        update_data = {k: v for k, v in body.items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Some async client versions don't support chaining .select() after update
        await (
            client.table("tenants")
            .update(update_data)
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .execute()
        )

        # Fetch updated team row
        result = await (
            client.table("tenants")
            .select("*")
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    # =========================================================================
    # Team Members
    # =========================================================================

    async def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get all members of a team with their details.
        """
        client = await get_async_supabase_client()

        memberships_result = await (
            client.table("tenant_memberships")
            .select(
                "*, user_profiles!tenant_memberships_user_id_fkey(id, email, full_name)"
            )
            .eq("tenant_id", team_id)
            .eq("is_active", True)
            .execute()
        )

        members = []
        for membership in memberships_result.data or []:
            user_profile = membership.get("user_profiles", {})
            members.append(
                {
                    "id": membership.get("id"),
                    "user_id": membership.get("user_id"),
                    "name": user_profile.get("full_name", "Unknown"),
                    "email": user_profile.get("email", ""),
                    "role": membership.get("role", "member"),
                    "team_id": team_id,
                    "status": "active" if membership.get("is_active") else "inactive",
                    "joined_date": membership.get("joined_at")
                    or membership.get("created_at"),
                    "permissions": membership.get("permissions", {}),
                }
            )

        return members

    async def delete_team_member(
        self,
        team_id: str,
        user_id: str,
        admin_user_id: str,
    ) -> Dict[str, Any]:
        """Remove a member from a team."""
        client = await get_async_supabase_client()

        # Verify membership exists
        membership_result = await (
            client.table("tenant_memberships")
            .select("id, role")
            .eq("tenant_id", team_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not membership_result.data:
            raise HTTPException(status_code=404, detail="Member not found in this team")

        membership = membership_result.data[0]

        # Prevent deletion of team owner
        if membership.get("role") == "owner":
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the team owner. Transfer ownership first or delete the team.",
            )

        # Delete membership and get user email in parallel
        delete_task = (
            client.table("tenant_memberships")
            .delete()
            .eq("id", membership["id"])
            .execute()
        )
        user_task = (
            client.table("user_profiles")
            .select("email")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        _, user_result = await asyncio.gather(delete_task, user_task)

        # Update invitation status if user email found
        if user_result.data:
            user_email = user_result.data[0].get("email")
            if user_email:
                await (
                    client.table("team_invitations")
                    .update({"status": "removed"})
                    .eq("team_id", team_id)
                    .eq("email", user_email)
                    .execute()
                )

        logger.info(
            f"Deleted member {user_id} from team {team_id}. Admin: {admin_user_id}"
        )

        return {
            "success": True,
            "message": "Member removed from team successfully",
            "user_id": user_id,
            "team_id": team_id,
        }

    # =========================================================================
    # Team Metrics
    # =========================================================================

    async def get_team_metrics(self, team_id: str) -> Dict[str, Any]:
        """Get invitations and membership metrics for a team."""
        client = await get_async_supabase_client()

        # Run both queries in parallel
        invites_task = (
            client.table("team_invitations")
            .select("id, status")
            .eq("team_id", team_id)
            .execute()
        )
        memberships_task = (
            client.table("tenant_memberships")
            .select("user_id")
            .eq("tenant_id", team_id)
            .eq("is_active", True)
            .execute()
        )

        invites_result, memberships_result = await asyncio.gather(
            invites_task, memberships_task
        )

        invites = invites_result.data or []
        memberships = memberships_result.data or []

        num_sent = sum(
            1 for inv in invites if inv["status"] not in ["failed", "queued"]
        )
        num_accepted = sum(1 for inv in invites if inv["status"] == "accepted")

        return {
            "invitations": {
                "sent": num_sent,
                "accepted": num_accepted,
            },
            "membership": {
                "total": len(memberships),
            },
        }

    # =========================================================================
    # Invitations
    # =========================================================================

    async def get_team_invitations(self, team_id: str) -> List[Dict[str, Any]]:
        """Get all invitations for a team."""
        client = await get_async_supabase_client()

        result = await (
            client.table("team_invitations")
            .select("*")
            .eq("team_id", team_id)
            .execute()
        )

        return result.data or []

    async def get_invitation(
        self,
        invitation_id: str,
        team_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific invitation."""
        client = await get_async_supabase_client()

        result = await (
            client.table("team_invitations")
            .select("*")
            .eq("id", invitation_id)
            .eq("team_id", team_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def update_invitation_status(
        self,
        invitation_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """Update invitation status."""
        client = await get_async_supabase_client()

        payload = {"status": status}
        if error:
            payload["error"] = error

        await (
            client.table("team_invitations")
            .update(payload)
            .eq("id", invitation_id)
            .execute()
        )

    # =========================================================================
    # Join Team
    # =========================================================================

    async def get_team_org_link(self, team_id: str) -> Optional[str]:
        """Get the organization ID linked to a team, if any."""
        client = await get_async_supabase_client()

        result = await (
            client.table("org_teams")
            .select("organization_id")
            .eq("team_id", team_id)
            .limit(1)
            .execute()
        )

        return result.data[0]["organization_id"] if result.data else None

    async def check_team_join_eligibility(
        self,
        team_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Check if user can join a team and get org membership status.
        Runs org_link and org_membership check in parallel.

        Returns:
            {org_id: str|None, is_org_member: bool}
        """
        client = await get_async_supabase_client()

        # Get org_link first (required to check membership)
        org_link_result = await (
            client.table("org_teams")
            .select("organization_id")
            .eq("team_id", team_id)
            .limit(1)
            .execute()
        )

        org_id = (
            org_link_result.data[0]["organization_id"] if org_link_result.data else None
        )

        if not org_id:
            return {"org_id": None, "is_org_member": False}

        # Check org membership
        membership_result = await (
            client.table("tenant_memberships")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        return {
            "org_id": org_id,
            "is_org_member": bool(membership_result.data),
        }

    async def is_org_member(self, org_id: str, user_id: str) -> bool:
        """Check if user is a member of the organization."""
        client = await get_async_supabase_client()

        result = await (
            client.table("tenant_memberships")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def add_org_membership(
        self,
        org_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Add a user to an organization as a member."""
        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "tenant_id": org_id,
            "user_id": user_id,
            "role": "member",
            "is_active": True,
            "joined_at": now,
            "created_at": now,
            "updated_at": now,
        }

        # Some async client versions don't support chaining .select() after insert
        result = await client.table("tenant_memberships").insert(payload).execute()

        if result.data:
            return result.data[0]

        # Fallback: fetch the inserted membership explicitly
        fetch = await (
            client.table("tenant_memberships")
            .select("*")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return fetch.data[0] if fetch.data else None

    async def add_or_update_team_membership(
        self,
        team_id: str,
        user_id: str,
        user_email: str,
        role: str = "member",
    ) -> Optional[Dict[str, Any]]:
        """Insert or update a user's membership in a team."""
        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing membership
        existing = await (
            client.table("tenant_memberships")
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
                # Some async client versions don't support chaining .select() after update
                await (
                    client.table("tenant_memberships")
                    .update(updates)
                    .eq("id", membership["id"])
                    .execute()
                )
                # Fetch updated row to return latest state
                refreshed = await (
                    client.table("tenant_memberships")
                    .select("*")
                    .eq("id", membership["id"])
                    .limit(1)
                    .execute()
                )
                return refreshed.data[0] if refreshed.data else {**membership, **updates}

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
        # Some async client versions don't support chaining .select() after insert
        inserted = await client.table("tenant_memberships").insert(payload).execute()

        # If insert didn't return representation, fetch it
        if not inserted.data:
            inserted = await (
                client.table("tenant_memberships")
                .select("*")
                .eq("tenant_id", team_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

        # Update invitation status
        await (
            client.table("team_invitations")
            .update({"status": "accepted", "accepted_by": user_id, "accepted_at": now})
            .eq("team_id", team_id)
            .eq("email", user_email)
            .execute()
        )

        return inserted.data[0] if inserted.data else None

    def _get_default_permissions(self, role: str) -> Dict[str, Any]:
        """Get default permissions for a team role."""
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

    # =========================================================================
    # Team Creation
    # =========================================================================

    async def create_team(
        self,
        user_id: str,
        body: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create a new independent team tenant."""
        client = await get_async_supabase_client()
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

        result = await client.table("tenants").insert(payload).execute()
        if not result.data:
            return None

        team = result.data[0]

        # Create owner membership
        permissions = self._get_default_permissions("owner")
        membership_payload = {
            "tenant_id": team["id"],
            "user_id": user_id,
            "role": "owner",
            "is_active": True,
            "joined_at": now,
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
        }
        await client.table("tenant_memberships").insert(membership_payload).execute()

        return team

    async def _has_team_leader_invite(
        self,
        org_id: str,
        email: str,
    ) -> bool:
        """Check if user has a team leader invitation for this org."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("organization_invitations")
                .select("id")
                .eq("organization_id", org_id)
                .eq("email", (email or "").strip())
                .eq("is_team_leader", True)
                .in_("status", ["queued", "sent", "accepted"])
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to check team_leader invitation for {email}: {e}")
            return False

    async def create_team_tenant(
        self,
        org_id: str,
        user_id: str,
        user_email: str,
        body: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create a new team tenant linked to an organization."""
        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        # Fetch team leader invitation to get can_skip_modules
        invitation_result = await (
            client.table("organization_invitations")
            .select("id, can_skip_modules")
            .eq("organization_id", org_id)
            .eq("email", (user_email or "").strip())
            .eq("is_team_leader", True)
            .in_("status", ["queued", "sent", "accepted"])
            .limit(1)
            .execute()
        )

        # Enforce team_leader invitation gate
        if not invitation_result.data:
            raise ValueError(
                "Only members with a team leader invitation can create teams"
            )

        # Extract can_skip_modules from invitation (default to False)
        invitation = invitation_result.data[0]
        can_skip_modules = invitation.get("can_skip_modules", False)

        # Verify org exists and is an organization
        org_result = await (
            client.table("tenants")
            .select("id, tenant_type")
            .eq("id", org_id)
            .eq("tenant_type", "organization")
            .limit(1)
            .execute()
        )
        if not org_result.data:
            raise ValueError("Invalid organization tenant")

        # Get existing team IDs for this org
        org_teams_result = await (
            client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .execute()
        )
        team_ids = [t["team_id"] for t in (org_teams_result.data or [])]

        # Check for duplicate name or if user already owns a team
        if team_ids:
            # Check if user already owns a team in parallel
            owned_task = (
                client.table("tenant_memberships")
                .select("tenant_id")
                .in_("tenant_id", team_ids)
                .eq("user_id", user_id)
                .eq("role", "owner")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            duplicate_task = (
                client.table("tenants")
                .select("id")
                .in_("id", team_ids)
                .eq("name", body["name"])
                .limit(1)
                .execute()
            )

            owned_result, duplicate_result = await asyncio.gather(
                owned_task, duplicate_task
            )

            if owned_result.data:
                raise ValueError("You already own a team within this organization")
            if duplicate_result.data:
                raise ValueError(
                    f"Team with name '{body['name']}' already exists in this organization"
                )

        # Create team tenant
        team_payload = {
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
        team_result = await client.table("tenants").insert(team_payload).execute()
        if not team_result.data:
            return None

        team = team_result.data[0]

        # Create owner membership and org_teams link in parallel
        permissions = self._get_default_permissions("owner")
        membership_payload = {
            "tenant_id": team["id"],
            "user_id": user_id,
            "role": "owner",
            "is_active": True,
            "joined_at": now,
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
        }
        org_teams_payload = {
            "organization_id": org_id,
            "team_id": team["id"],
            "created_by": user_id,
            "created_at": now,
            "can_skip_modules": can_skip_modules,
        }

        await asyncio.gather(
            client.table("tenant_memberships").insert(membership_payload).execute(),
            client.table("org_teams").insert(org_teams_payload).execute(),
        )

        # Check for pending team credits
        pending_result = await (
            client.table("pending_team_credits")
            .select("*")
            .eq("organization_id", org_id)
            .eq("admin_email", user_email)
            .eq("assigned", False)
            .limit(1)
            .execute()
        )

        if pending_result.data:
            await self._allocate_pending_credits(
                client, org_id, team["id"], user_id, pending_result.data[0], now
            )

        logger.info(f"Created team {team['id']} in organization {org_id}")
        return team

    async def _allocate_pending_credits(
        self,
        client,
        org_id: str,
        team_id: str,
        user_id: str,
        pending_record: Dict[str, Any],
        now: str,
    ) -> None:
        """
        Allocate pending credits to a newly created team.

        Credits were already deducted from the org when the team leader joined.
        This just creates the lot for the team from the stored pending_team_credits.
        """
        from decimal import Decimal

        admin_email = pending_record["admin_email"]
        credit_amount = Decimal(str(pending_record["credit_amount"]))
        lot_source = pending_record.get("source", "grant")
        lot_expires_at = pending_record.get("expires_at")  # Preserved from original lot

        logger.info(f"Found pending credits ({credit_amount}) for {admin_email}")

        # Get organization type for postpay billing tracking
        org_config_result = await (
            client.table("organization_billing_config")
            .select("organization_type")
            .eq("tenant_id", org_id)
            .limit(1)
            .execute()
        )

        org_type = "grant_org"
        if org_config_result.data:
            org_type = org_config_result.data[0].get("organization_type", "grant_org")

        # Create credit lot for the team
        # Credits were already deducted from org when team leader joined (for grant/prepay)
        # or will be invoiced later (for postpay)
        created_lot = await self.credit_service.create_credit_lot(
            tenant_id=team_id,
            source=lot_source,
            credit_amount=credit_amount,
            valid_from=now,
            expires_at=lot_expires_at,  # Use preserved expiry from pending_team_credits
            metadata={
                "source": "team_creation",
                "organization_id": org_id,
                "from_pending_team_credits": pending_record["id"],
                "admin_email": admin_email,
            },
            original_tenant_id=org_id,
        )

        # Mark pending record as assigned (and record allocation for postpay in parallel)
        tasks = [
            client.table("pending_team_credits")
            .update({"assigned": True, "assigned_at": now})
            .eq("id", pending_record["id"])
            .execute()
        ]

        # For postpay orgs: also record allocation for billing
        if org_type == "postpay_org":
            tasks.append(
                client.table("organization_credit_allocations")
                .insert(
                    {
                        "tenant_id": org_id,
                        "allocation_type": "allocation_to_team",
                        "credit_amount": float(credit_amount),
                        "credit_lot_id": created_lot.get("id") if created_lot else None,
                        "allocated_to_tenant_id": team_id,
                        "allocated_to_user_id": None,
                        "allocated_by_user_id": user_id,
                        "allocated_at": now,
                        "metadata": {
                            "source": "team_creation",
                            "admin_email": admin_email,
                        },
                    }
                )
                .execute()
            )

        await asyncio.gather(*tasks)

        logger.info(
            f"Created credit lot for team {team_id}: {credit_amount} credits "
            f"(source: {lot_source}, expires: {lot_expires_at})"
        )

        # Assign team to cohort if specified in pending_team_credits metadata
        metadata = pending_record.get("metadata") or {}
        cohort_id = metadata.get("cohort_id")
        if cohort_id:
            await self._assign_team_to_cohort(cohort_id, team_id)

    async def _assign_team_to_cohort(self, cohort_id: str, team_id: str) -> None:
        """
        Assign a team to a cohort.
        Silently fails if assignment fails (cohort assignment shouldn't block team creation).
        """
        try:
            from ..billing.cohort_service import CohortService

            cohort_service = CohortService(use_service_role=True)
            cohort_service.assign_member_to_cohort(
                cohort_id=cohort_id, member_tenant_id=team_id
            )
            logger.info(f"Assigned team {team_id} to cohort {cohort_id}")
        except Exception as e:
            # Don't fail team creation if cohort assignment fails
            logger.error(f"Failed to assign team {team_id} to cohort {cohort_id}: {e}")

    # =========================================================================
    # Invitations (Extended)
    # =========================================================================

    async def record_invitation(
        self,
        team_id: str,
        email: str,
        is_admin: bool,
        invited_by: str,
        invited_by_email: str,
    ) -> Dict[str, Any]:
        """Record a team invitation."""
        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing invitation
        existing = await (
            client.table("team_invitations")
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
                    f"Resending invitation (status: {inv['status']}) for {email}"
                )
                await (
                    client.table("team_invitations")
                    .update(
                        {
                            "status": "queued",
                            "invited_at": now,
                            "invited_by": invited_by,
                            "invited_by_email": invited_by_email,
                        }
                    )
                    .eq("id", inv["id"])
                    .execute()
                )
                return inv
            elif inv["status"] == "accepted":
                raise HTTPException(
                    status_code=409,
                    detail="User has already accepted the invitation and is a team member.",
                )

        # Create new invitation
        payload = {
            "team_id": team_id,
            "email": email,
            "role": "admin" if is_admin else "member",
            "invited_by": invited_by,
            "invited_by_email": invited_by_email,
            "status": "queued",
            "invited_at": now,
        }
        result = await client.table("team_invitations").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create invitation")

        return result.data[0]

    async def record_invitations_batch(
        self,
        team_id: str,
        emails: List[str],
        is_admin: bool,
        invited_by: str,
        invited_by_email: str,
    ) -> List[Dict[str, Any]]:
        """
        Record multiple team invitations in parallel.
        Returns list of created/updated invitations.
        """
        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        # Fetch all existing invitations for these emails in one query
        existing_result = await (
            client.table("team_invitations")
            .select("id, email, status")
            .eq("team_id", team_id)
            .in_("email", emails)
            .execute()
        )

        existing_by_email = {inv["email"]: inv for inv in (existing_result.data or [])}

        results = []
        to_insert = []
        to_update = []

        for email in emails:
            if email in existing_by_email:
                inv = existing_by_email[email]
                if inv["status"] in ["queued", "failed", "sent"]:
                    to_update.append(inv["id"])
                    results.append(inv)
                elif inv["status"] == "accepted":
                    # Skip - user already a member
                    continue
            else:
                to_insert.append(
                    {
                        "team_id": team_id,
                        "email": email,
                        "role": "admin" if is_admin else "member",
                        "invited_by": invited_by,
                        "invited_by_email": invited_by_email,
                        "status": "queued",
                        "invited_at": now,
                    }
                )

        # Batch operations in parallel
        tasks = []
        if to_update:
            tasks.append(
                client.table("team_invitations")
                .update(
                    {
                        "status": "queued",
                        "invited_at": now,
                        "invited_by": invited_by,
                        "invited_by_email": invited_by_email,
                    }
                )
                .in_("id", to_update)
                .execute()
            )
        if to_insert:
            tasks.append(client.table("team_invitations").insert(to_insert).execute())

        if tasks:
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            # Extract inserted invitations
            for res in batch_results:
                if not isinstance(res, Exception) and res.data:
                    results.extend(res.data)

        return results

    async def send_team_invite_and_update(
        self,
        invitation_id: str,
        to_email: str,
        team_id: str,
        invite_link: str,
        inviter_name: str,
    ) -> None:
        """Send team invite email and update invitation status (async)."""
        from ..services.communication.email_service import email_service

        try:
            # Fetch team and org_link in parallel
            team_task = self.get_team(team_id)
            org_link_task = self.get_team_org_link(team_id)
            team, org_id = await asyncio.gather(team_task, org_link_task)

            if not team:
                raise ValueError("Team not found")

            team_name = team["name"]
            is_org_associated = org_id is not None

            if is_org_associated:
                email_sent = email_service.send_org_team_invite_email(
                    to_email=to_email,
                    team_name=team_name,
                    inviter_name=inviter_name or "Team Admin",
                    invite_link=invite_link,
                )
            else:
                email_sent = email_service.send_independent_team_invite_email(
                    to_email=to_email,
                    team_name=team_name,
                    invite_link=invite_link,
                )

            if email_sent:
                await self.update_invitation_status(
                    invitation_id=invitation_id,
                    status="sent",
                )
            else:
                raise Exception("Email service returned False")

        except Exception as e:
            logger.error(f"Team invite email failed for {to_email}: {e}")
            await self.update_invitation_status(
                invitation_id=invitation_id,
                status="failed",
                error=str(e),
            )

    # =========================================================================
    # Team Deletion
    # =========================================================================

    async def delete_team_tenant(
        self,
        team_id: str,
        user_id: str,
    ) -> bool:
        """Delete a team tenant."""
        client = await get_async_supabase_client()

        # Ensure team exists
        result = await (
            client.table("tenants")
            .select("id, tenant_type")
            .eq("id", team_id)
            .eq("tenant_type", "team")
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Team not found")

        try:
            await client.table("tenants").delete().eq("id", team_id).execute()
            logger.info(f"Deleted team {team_id} by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete team tenant: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete team: {str(e)}"
            )


# Singleton instance
_async_team_service: Optional[AsyncTeamService] = None


def get_async_team_service() -> AsyncTeamService:
    """Get singleton async team service instance."""
    global _async_team_service
    if _async_team_service is None:
        _async_team_service = AsyncTeamService()
    return _async_team_service
