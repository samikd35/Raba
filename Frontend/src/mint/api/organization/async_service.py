"""
Async Organization service for high-performance API operations.

This is an optimized async version that uses:
- asyncio.gather() for parallel database queries
- Batch operations to minimize round trips
- Non-blocking async Supabase client

Optimized endpoints:
- get_individual_members: 7 queries → 3 parallel batched queries
- get_team_overview: 5 queries → 2 parallel batched queries
- get_team_member_management: 5 queries → 2 parallel batched queries
- get_membership_details: 3 queries → 1 parallel batch
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from ..system.core.async_supabase_client import get_async_supabase_client
from ..credit.async_service import get_async_credit_service, InsufficientCreditsError

logger = logging.getLogger(__name__)


class AsyncOrganizationService:
    """Async service class for organization operations with optimized parallel queries."""

    def __init__(self):
        """Initialize the async organization service."""
        self.credit_service = get_async_credit_service()

    @staticmethod
    def _month_window() -> Tuple[str, str]:
        """Get month start and now as ISO strings."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return month_start.isoformat(), now.isoformat()

    async def get_individual_members(
        self,
        org_id: str,
        current_month_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Get individual members - users who have an individual tenant within this organization.

        OPTIMIZED: Uses asyncio.gather for parallel queries, reducing 7+ sequential queries
        to 3 parallel batched queries.

        Args:
            org_id: Organization ID
            current_month_only: If True, only fetch consumption for current month (faster).
                              If False, fetch all consumption records (slower but complete).

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
        client = await get_async_supabase_client()
        month_start_iso, now_iso = self._month_window()

        # PHASE 1: Get individual members (required for subsequent queries)
        org_individuals_result = await (
            client.table("org_individuals")
            .select("user_id, individual_tenant_id")
            .eq("organization_id", org_id)
            .execute()
        )
        org_individuals = org_individuals_result.data or []

        # Map: user_id -> individual_tenant_id
        user_to_individual_tenant: Dict[str, str] = {
            item["user_id"]: item["individual_tenant_id"] for item in org_individuals
        }

        individual_user_ids = list(user_to_individual_tenant.keys())
        individual_tenant_ids = list(user_to_individual_tenant.values())

        logger.info(
            f"Found {len(individual_user_ids)} individual members in org {org_id}"
        )

        # PHASE 2: Parallel queries for member data, credits, and invitations
        tasks = []
        task_names = []

        # Task 1: Get org memberships for roles
        if individual_user_ids:
            tasks.append(
                client.table("tenant_memberships")
                .select("user_id, role, is_active, created_at")
                .eq("tenant_id", org_id)
                .in_("user_id", individual_user_ids)
                .execute()
            )
            task_names.append("memberships")
        else:
            tasks.append(self._make_empty_result())
            task_names.append("memberships")

        # Task 2: Get user profiles
        if individual_user_ids:
            tasks.append(
                client.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", individual_user_ids)
                .execute()
            )
            task_names.append("profiles")
        else:
            tasks.append(self._make_empty_result())
            task_names.append("profiles")

        # Task 3: Get ALL credit lots for individuals (including expired, for total allocated)
        if individual_tenant_ids:
            tasks.append(
                client.table("credit_lots")
                .select("tenant_id, credit_amount, expires_at, valid_from")
                .in_("tenant_id", individual_tenant_ids)
                .eq("is_active", True)
                .execute()
            )
            task_names.append("credit_lots")
        else:
            tasks.append(self._make_empty_result())
            task_names.append("credit_lots")

        # Task 4: Get credit consumptions
        if individual_tenant_ids:
            consumption_query = (
                client.table("tenant_credit_consumptions")
                .select("tenant_id, cost")
                .in_("tenant_id", individual_tenant_ids)
            )
            if current_month_only:
                # Filter to current month for better performance
                consumption_query = (
                    consumption_query.gte("created_at", month_start_iso)
                    .lte("created_at", now_iso)
                    .limit(50000)
                )
            # No limit when fetching all - but still safe due to tenant filter
            tasks.append(consumption_query.execute())
            task_names.append("consumptions")
        else:
            tasks.append(self._make_empty_result())
            task_names.append("consumptions")

        # Task 5: Get pending invitations
        tasks.append(
            client.table("organization_invitations")
            .select("id, email, credits, sent_at, created_at, is_admin, is_team_leader")
            .eq("organization_id", org_id)
            .in_("status", ["sent", "queued"])
            .execute()
        )
        task_names.append("invitations")

        # Task 6: Get pending credit requests
        if individual_user_ids:
            tasks.append(
                client.table("credit_requests")
                .select("id, user_id, requested_amount, created_at, status")
                .eq("organization_id", org_id)
                .in_("user_id", individual_user_ids)
                .eq("status", "pending")
                .execute()
            )
            task_names.append("credit_requests")
        else:
            tasks.append(self._make_empty_result())
            task_names.append("credit_requests")

        # Execute all queries in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results (handle any exceptions)
        def get_data(result):
            if isinstance(result, Exception):
                logger.warning(f"Query failed: {result}")
                return []
            return result.data or []

        org_memberships = get_data(results[0])
        users = get_data(results[1])
        credit_lots = get_data(results[2])
        consumptions = get_data(results[3])
        all_pending_invitations = get_data(results[4])
        pending_credit_requests = get_data(results[5])

        # Build lookup maps
        membership_by_user: Dict[str, Dict[str, Any]] = {
            m["user_id"]: m for m in org_memberships
        }
        user_display: Dict[str, Dict[str, Any]] = {u["id"]: u for u in users}

        # Sum credits by tenant
        # total_allocated = ALL credits ever allocated (including expired)
        # remaining = only non-expired credits
        # expired = credits that expired without being used (counts as consumed)
        total_allocated_by_tenant: Dict[str, int] = {}
        remaining_by_tenant: Dict[str, int] = {}
        expired_by_tenant: Dict[str, int] = {}

        for lot in credit_lots:
            tid = lot["tenant_id"]
            amount = int(float(lot.get("credit_amount") or 0))
            valid_from = lot.get("valid_from")
            expires_at = lot.get("expires_at")

            # Check if lot has started (valid_from <= now)
            lot_started = valid_from is None or valid_from <= now_iso

            # Check if lot is not expired (expires_at is null or > now)
            lot_not_expired = expires_at is None or expires_at > now_iso

            # Total allocated includes all lots that have started
            if lot_started:
                total_allocated_by_tenant[tid] = (
                    total_allocated_by_tenant.get(tid, 0) + amount
                )

            # Remaining only includes non-expired lots
            if lot_started and lot_not_expired:
                remaining_by_tenant[tid] = remaining_by_tenant.get(tid, 0) + amount

            # Expired credits = remaining balance of expired lots (counts as consumed)
            if lot_started and not lot_not_expired:
                expired_by_tenant[tid] = expired_by_tenant.get(tid, 0) + amount

        # Sum consumptions by tenant (actual usage from consumption records)
        actual_used_by_tenant: Dict[str, int] = {}
        for c in consumptions:
            tid = c["tenant_id"]
            actual_used_by_tenant[tid] = actual_used_by_tenant.get(tid, 0) + int(
                float(c.get("cost") or 0)
            )

        # Calculate per-user credit totals
        # total_allocated = remaining (current balance) + expired + actual consumed
        # This represents the true total credits allocated from org to member
        # credits_used = actual consumed + expired (expired credits count as consumed)
        total_allocated_by_user: Dict[str, int] = {}
        remaining_by_user: Dict[str, int] = {}
        used_by_user: Dict[str, int] = {}
        for user_id, tenant_id in user_to_individual_tenant.items():
            remaining = remaining_by_tenant.get(tenant_id, 0)
            expired = expired_by_tenant.get(tenant_id, 0)
            actual_used = actual_used_by_tenant.get(tenant_id, 0)

            # Total allocated = used + remaining + expired (all credits ever given)
            total_allocated_by_user[user_id] = remaining + expired + actual_used
            remaining_by_user[user_id] = remaining
            # Total used = actual consumption + expired (expired credits count as consumed)
            used_by_user[user_id] = actual_used + expired

        # Credit request status by user
        credit_request_by_user: Dict[str, Dict[str, Any]] = {}
        for req in pending_credit_requests:
            user_id = req["user_id"]
            credit_request_by_user[user_id] = {
                "has_pending_request": True,
                "pending_request_id": req["id"],
                "pending_request_amount": req["requested_amount"],
                "pending_request_date": req["created_at"],
            }

        # Build member rows
        rows: List[Dict[str, Any]] = []
        for uid in individual_user_ids:
            m = membership_by_user.get(uid, {})
            role = m.get("role") or "member"
            is_active = m.get("is_active", True)
            u = user_display.get(uid, {})

            total_allocated = total_allocated_by_user.get(uid, 0)
            used_credits = used_by_user.get(uid, 0)

            credit_req_status = credit_request_by_user.get(
                uid,
                {
                    "has_pending_request": False,
                    "pending_request_id": None,
                    "pending_request_amount": None,
                    "pending_request_date": None,
                },
            )

            rows.append(
                {
                    "user_id": uid,
                    "individual_tenant_id": user_to_individual_tenant.get(uid),
                    "name": u.get("full_name") or u.get("email") or uid,
                    "email": u.get("email") or "",
                    "role": role,
                    "credits_allocated": total_allocated,
                    "credits_used": used_credits,
                    "status": "Active" if is_active else "Inactive",
                    "joined_at": m.get("created_at") or "",
                    "credit_request": credit_req_status,
                }
            )

        # Sort by name
        rows.sort(key=lambda r: r["name"].lower())

        # Add pending invitations (individual members only)
        pending_invitations = [
            inv
            for inv in all_pending_invitations
            if not inv.get("is_team_leader", False)
        ]

        joined_emails = {r["email"].lower() for r in rows if r.get("email")}
        now_utc = datetime.now(timezone.utc)
        expiration_threshold = now_utc - timedelta(hours=48)

        for inv in pending_invitations:
            inv_email = inv.get("email", "").lower()
            if inv_email in joined_emails:
                continue

            timestamp_str = inv.get("sent_at") or inv.get("created_at")
            invitation_status = "Pending"

            if timestamp_str:
                try:
                    ts_str = str(timestamp_str)
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    elif "+" not in ts_str and "-" not in ts_str[-6:]:
                        ts_str = ts_str + "+00:00"

                    invitation_dt = datetime.fromisoformat(ts_str)
                    if invitation_dt.tzinfo is None:
                        invitation_dt = invitation_dt.replace(tzinfo=timezone.utc)

                    if invitation_dt < expiration_threshold:
                        invitation_status = "Expired"
                except (ValueError, TypeError):
                    pass
            else:
                invitation_status = "Expired"

            rows.append(
                {
                    "user_id": f"pending-{inv['id']}",
                    "individual_tenant_id": None,
                    "invitation_id": inv["id"],
                    "name": inv_email.split("@")[0].title(),
                    "email": inv["email"],
                    "role": "admin" if inv.get("is_admin") else "member",
                    "credits_allocated": inv.get("credits") or 0,
                    "credits_used": 0,
                    "status": invitation_status,
                    "joined_at": inv.get("sent_at") or inv.get("created_at") or "",
                }
            )

        # Re-sort to include pending members (active first, then by name)
        rows.sort(key=lambda r: (r["status"].lower() != "active", r["name"].lower()))

        logger.info(
            f"Returning {len(rows)} members for org {org_id} "
            f"(async, current_month_only={current_month_only})"
        )
        return {"members": rows}

    async def get_team_overview(
        self,
        org_id: str,
        current_month_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Get team overview with credit information.

        OPTIMIZED: Uses asyncio.gather for parallel queries.

        Args:
            org_id: Organization ID
            current_month_only: If True, only fetch consumption for current month.

        Returns:
        {
          "teams": [
              {
                "team_id": "...",
                "team_name": "...",
                "team_leader": {...} | None,
                "members_count": 12,
                "credit_pool": {"total": X, "used": Y, "remaining": Z}
              }, ...
          ]
        }
        """
        client = await get_async_supabase_client()
        month_start_iso, now_iso = self._month_window()

        # PHASE 1: Get teams for this org
        org_teams_result = await (
            client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .execute()
        )
        team_ids = [t["team_id"] for t in (org_teams_result.data or [])]

        if not team_ids:
            return {"teams": []}

        # PHASE 2: Parallel queries for team data
        # Build consumption query with optional month filter
        consumption_query = (
            client.table("tenant_credit_consumptions")
            .select("tenant_id, cost")
            .in_("tenant_id", team_ids)
        )
        if current_month_only:
            consumption_query = (
                consumption_query.gte("created_at", month_start_iso)
                .lte("created_at", now_iso)
                .limit(50000)
            )

        tasks = [
            # Task 1: Get team names (active teams only)
            client.table("tenants")
            .select("id, name, is_active")
            .in_("id", team_ids)
            .eq("is_active", True)
            .execute(),
            # Task 2: Get all memberships for all teams
            client.table("tenant_memberships")
            .select("user_id, tenant_id, role, is_active")
            .in_("tenant_id", team_ids)
            .eq("is_active", True)
            .execute(),
            # Task 3: Get ALL credit lots for teams (including expired, for total allocated)
            client.table("credit_lots")
            .select("tenant_id, credit_amount, expires_at, valid_from")
            .in_("tenant_id", team_ids)
            .eq("is_active", True)
            .execute(),
            # Task 4: Get consumptions
            consumption_query.execute(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        def get_data(result):
            if isinstance(result, Exception):
                logger.warning(f"Query failed: {result}")
                return []
            return result.data or []

        team_rows = get_data(results[0])
        team_memberships = get_data(results[1])
        credit_lots = get_data(results[2])
        consumptions = get_data(results[3])

        # Filter to active teams only
        active_team_ids = {r["id"] for r in team_rows}
        name_by_team = {r["id"]: r.get("name") or r["id"] for r in team_rows}

        # Build membership maps
        members_count_by_team: Dict[str, int] = {}
        leader_user_by_team: Dict[str, str] = {}

        for m in team_memberships:
            tid = m["tenant_id"]
            if tid not in active_team_ids:
                continue
            members_count_by_team[tid] = members_count_by_team.get(tid, 0) + 1
            if m["role"] == "owner":
                leader_user_by_team[tid] = m["user_id"]

        # Get leader profiles (parallel with aggregation)
        leader_user_ids = list(set(leader_user_by_team.values()))
        leader_profiles: Dict[str, Dict[str, Any]] = {}

        if leader_user_ids:
            profiles_result = await (
                client.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", leader_user_ids)
                .execute()
            )
            leader_profiles = {p["id"]: p for p in (profiles_result.data or [])}

        # Aggregate credits by team
        # total_allocated = ALL credits ever allocated (including expired)
        # remaining = only non-expired credits
        # expired = credits that expired without being used (counts as consumed)
        total_allocated_by_team: Dict[str, int] = {}
        remaining_by_team: Dict[str, int] = {}
        expired_by_team: Dict[str, int] = {}

        for lot in credit_lots:
            tid = lot["tenant_id"]
            if tid not in active_team_ids:
                continue

            amount = int(float(lot.get("credit_amount") or 0))
            valid_from = lot.get("valid_from")
            expires_at = lot.get("expires_at")

            # Check if lot has started (valid_from <= now)
            lot_started = valid_from is None or valid_from <= now_iso

            # Check if lot is not expired (expires_at is null or > now)
            lot_not_expired = expires_at is None or expires_at > now_iso

            # Total allocated includes all lots that have started
            if lot_started:
                total_allocated_by_team[tid] = (
                    total_allocated_by_team.get(tid, 0) + amount
                )

            # Remaining only includes non-expired lots
            if lot_started and lot_not_expired:
                remaining_by_team[tid] = remaining_by_team.get(tid, 0) + amount

            # Expired credits = remaining balance of expired lots (counts as consumed)
            if lot_started and not lot_not_expired:
                expired_by_team[tid] = expired_by_team.get(tid, 0) + amount

        # Actual consumption from consumption records
        actual_used_by_team: Dict[str, int] = {}
        for c in consumptions:
            tid = c["tenant_id"]
            if tid in active_team_ids:
                actual_used_by_team[tid] = actual_used_by_team.get(tid, 0) + int(
                    float(c.get("cost") or 0)
                )

        # Total used = actual consumption + expired credits (expired credits count as consumed)
        used_by_team: Dict[str, int] = {}
        for tid in active_team_ids:
            actual_used = actual_used_by_team.get(tid, 0)
            expired = expired_by_team.get(tid, 0)
            used_by_team[tid] = actual_used + expired

        # Build team list
        teams = []
        for tid in active_team_ids:
            # Total allocated = remaining + expired + actual consumed (all credits ever given)
            remaining = remaining_by_team.get(tid, 0)
            expired = expired_by_team.get(tid, 0)
            actual_used = actual_used_by_team.get(tid, 0)
            total_allocated = remaining + expired + actual_used
            used = used_by_team.get(tid, 0)

            leader_info = None
            leader_uid = leader_user_by_team.get(tid)
            if leader_uid and leader_uid in leader_profiles:
                p = leader_profiles[leader_uid]
                leader_info = {
                    "user_id": leader_uid,
                    "full_name": p.get("full_name"),
                    "email": p.get("email"),
                }

            teams.append(
                {
                    "team_id": tid,
                    "team_name": name_by_team.get(tid, tid),
                    "team_leader": leader_info,
                    "members_count": members_count_by_team.get(tid, 0),
                    "credit_pool": {
                        "total": total_allocated,
                        "used": used,
                        "remaining": remaining,
                    },
                }
            )

        teams.sort(key=lambda t: t["team_name"].lower())
        return {"teams": teams}

    async def get_team_member_management(
        self,
        org_id: str,
        current_month_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Get team members with credit and request info for management.

        OPTIMIZED: Uses asyncio.gather for parallel queries.

        Args:
            org_id: Organization ID
            current_month_only: If True, only fetch consumption for current month.

        Returns:
        {
          "members": [...]
        }
        """
        client = await get_async_supabase_client()
        month_start_iso, now_iso = self._month_window()

        # PHASE 1: Get teams for this org
        org_teams_result = await (
            client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .execute()
        )
        team_ids = [t["team_id"] for t in (org_teams_result.data or [])]

        if not team_ids:
            return {"members": []}

        # Build consumption query with optional month filter
        consumption_query = (
            client.table("tenant_credit_consumptions")
            .select("tenant_id, cost")
            .in_("tenant_id", team_ids)
        )
        if current_month_only:
            consumption_query = (
                consumption_query.gte("created_at", month_start_iso)
                .lte("created_at", now_iso)
                .limit(50000)
            )

        # PHASE 2: Parallel queries
        tasks = [
            # Task 1: Get team names (active only)
            client.table("tenants")
            .select("id, name")
            .in_("id", team_ids)
            .eq("is_active", True)
            .execute(),
            # Task 2: Get memberships
            client.table("tenant_memberships")
            .select("user_id, tenant_id, role, is_active, created_at")
            .in_("tenant_id", team_ids)
            .eq("is_active", True)
            .execute(),
            # Task 3: Get ALL credit lots (including expired, for total allocated and expired calculation)
            client.table("credit_lots")
            .select("tenant_id, credit_amount, expires_at, valid_from")
            .in_("tenant_id", team_ids)
            .eq("is_active", True)
            .execute(),
            # Task 4: Get consumptions
            consumption_query.execute(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        def get_data(result):
            if isinstance(result, Exception):
                logger.warning(f"Query failed: {result}")
                return []
            return result.data or []

        team_rows = get_data(results[0])
        memberships = get_data(results[1])
        credit_lots = get_data(results[2])
        consumptions = get_data(results[3])

        active_team_ids = {r["id"] for r in team_rows}
        name_by_team = {r["id"]: r.get("name") or r["id"] for r in team_rows}

        # Get user profiles for all members
        user_ids = list(
            {m["user_id"] for m in memberships if m["tenant_id"] in active_team_ids}
        )
        user_profiles: Dict[str, Dict[str, Any]] = {}
        credit_request_by_user: Dict[str, Dict[str, Any]] = {}

        if user_ids:
            # Parallel: user profiles and credit requests
            profiles_task = (
                client.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", user_ids)
                .execute()
            )
            requests_task = (
                client.table("credit_requests")
                .select("id, user_id, requested_amount, created_at, status")
                .eq("organization_id", org_id)
                .in_("user_id", user_ids)
                .eq("status", "pending")
                .execute()
            )

            profiles_result, requests_result = await asyncio.gather(
                profiles_task, requests_task
            )
            user_profiles = {p["id"]: p for p in (profiles_result.data or [])}

            for req in requests_result.data or []:
                credit_request_by_user[req["user_id"]] = {
                    "has_pending_request": True,
                    "pending_request_id": req["id"],
                    "pending_request_amount": req["requested_amount"],
                    "pending_request_date": req["created_at"],
                }

        # Aggregate credits by team
        # total_allocated = ALL credits ever allocated (including expired)
        # remaining = only non-expired credits
        # expired = credits that expired without being used (counts as consumed)
        total_allocated_by_team: Dict[str, int] = {}
        remaining_by_team: Dict[str, int] = {}
        expired_by_team: Dict[str, int] = {}

        for lot in credit_lots:
            tid = lot["tenant_id"]
            if tid not in active_team_ids:
                continue

            amount = int(float(lot.get("credit_amount") or 0))
            valid_from = lot.get("valid_from")
            expires_at = lot.get("expires_at")

            # Check if lot has started (valid_from <= now)
            lot_started = valid_from is None or valid_from <= now_iso

            # Check if lot is not expired (expires_at is null or > now)
            lot_not_expired = expires_at is None or expires_at > now_iso

            # Total allocated includes all lots that have started
            if lot_started:
                total_allocated_by_team[tid] = (
                    total_allocated_by_team.get(tid, 0) + amount
                )

            # Remaining only includes non-expired lots
            if lot_started and lot_not_expired:
                remaining_by_team[tid] = remaining_by_team.get(tid, 0) + amount

            # Expired credits = remaining balance of expired lots (counts as consumed)
            if lot_started and not lot_not_expired:
                expired_by_team[tid] = expired_by_team.get(tid, 0) + amount

        # Actual consumption from consumption records
        actual_used_by_team: Dict[str, int] = {}
        for c in consumptions:
            tid = c["tenant_id"]
            if tid in active_team_ids:
                actual_used_by_team[tid] = actual_used_by_team.get(tid, 0) + int(
                    float(c.get("cost") or 0)
                )

        # Total used = actual consumption + expired credits (expired credits count as consumed)
        used_by_team: Dict[str, int] = {}
        for tid in active_team_ids:
            actual_used = actual_used_by_team.get(tid, 0)
            expired = expired_by_team.get(tid, 0)
            used_by_team[tid] = actual_used + expired

        # Build member rows
        rows = []
        for m in memberships:
            tid = m["tenant_id"]
            if tid not in active_team_ids:
                continue

            uid = m["user_id"]
            u = user_profiles.get(uid, {})

            # Total allocated = remaining + expired + actual consumed (all credits ever given)
            remaining = remaining_by_team.get(tid, 0)
            expired = expired_by_team.get(tid, 0)
            actual_used = actual_used_by_team.get(tid, 0)
            total_allocated = remaining + expired + actual_used
            used = used_by_team.get(tid, 0)

            credit_req_status = credit_request_by_user.get(
                uid,
                {
                    "has_pending_request": False,
                    "pending_request_id": None,
                    "pending_request_amount": None,
                    "pending_request_date": None,
                },
            )

            rows.append(
                {
                    "user_id": uid,
                    "team_id": tid,
                    "team_name": name_by_team.get(tid, tid),
                    "name": u.get("full_name") or u.get("email") or uid,
                    "email": u.get("email") or "",
                    "role": m.get("role") or "member",
                    "credits_allocated": total_allocated,
                    "credits_used": used,
                    "status": "Active" if m.get("is_active", True) else "Inactive",
                    "joined_at": m.get("created_at") or "",
                    "credit_request": credit_req_status,
                }
            )

        rows.sort(key=lambda r: (r["team_name"].lower(), r["name"].lower()))
        return {"members": rows}

    async def get_membership_details(
        self,
        user_id: str,
        org_id: str,
    ) -> Dict[str, Any]:
        """
        Get membership details for a user in an organization.

        OPTIMIZED: Uses asyncio.gather for parallel queries.
        """
        client = await get_async_supabase_client()

        # Parallel queries
        tasks = [
            # Task 1: Get membership
            client.table("tenant_memberships")
            .select("id, user_id, tenant_id, role, is_active, created_at")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute(),
            # Task 2: Get organization details
            client.table("tenants")
            .select("id, name, contact_email, is_active")
            .eq("id", org_id)
            .execute(),
            # Task 3: Get billing config
            client.table("organization_billing_config")
            .select("organization_type")
            .eq("tenant_id", org_id)
            .limit(1)
            .execute(),
            # Task 4: Get user profile for email lookup
            client.table("user_profiles")
            .select("id, email")
            .eq("id", user_id)
            .limit(1)
            .execute(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        def get_data(result):
            if isinstance(result, Exception):
                logger.warning(f"Query failed: {result}")
                return []
            return result.data or []

        membership_data = get_data(results[0])
        org_data = get_data(results[1])
        config_data = get_data(results[2])
        user_data = get_data(results[3])

        membership = membership_data[0] if membership_data else None
        org = org_data[0] if org_data else None
        config = config_data[0] if config_data else {}
        user_profile = user_data[0] if user_data else {}

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check for pending invitation if we have user email (case-insensitive)
        user_invitation = None
        user_email = user_profile.get("email", "").lower()

        if user_email:
            invitations_result = await (
                client.table("organization_invitations")
                .select(
                    "id, email, credits, is_admin, is_team_leader, status, created_at"
                )
                .eq("organization_id", org_id)
                .in_("status", ["sent", "queued"])
                .limit(50)
                .execute()
            )
            for inv in invitations_result.data or []:
                if inv.get("email", "").lower() == user_email:
                    user_invitation = inv
                    break

        return {
            "membership": membership,
            "organization": {
                "id": org["id"],
                "name": org.get("name"),
                "contact_email": org.get("contact_email"),
                "is_active": org.get("is_active", True),
                "organization_type": config.get("organization_type", "grant_org"),
            },
            "pending_invitation": user_invitation,
        }

    async def get_user_membership_in_org(
        self,
        user_id: str,
        user_email: str,
        org_id: str,
    ) -> Dict[str, Any]:
        """
        Get a user's membership details in an organization including accepted invitation data.

        OPTIMIZED: Uses asyncio.gather for parallel queries.

        Returns:
            Dict with membership, organization, and invitation data.
        """
        client = await get_async_supabase_client()
        normalized_email = user_email.lower().strip()

        # Run all queries in parallel
        membership_task = (
            client.table("tenant_memberships")
            .select("*")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        org_task = (
            client.table("tenants")
            .select("id, name, description, industry, size, country, tenant_type")
            .eq("id", org_id)
            .eq("tenant_type", "organization")
            .limit(1)
            .execute()
        )
        invitation_task = (
            client.table("organization_invitations")
            .select("credits, invited_by_email, accepted_at, is_team_leader, is_admin")
            .eq("organization_id", org_id)
            .eq("email", normalized_email)
            .eq("status", "accepted")
            .order("accepted_at", desc=True)
            .limit(1)
            .execute()
        )

        membership_result, org_result, invitation_result = await asyncio.gather(
            membership_task, org_task, invitation_task
        )

        if not membership_result.data:
            raise HTTPException(
                status_code=404, detail="Membership not found in this organization"
            )

        membership_data = membership_result.data[0]

        if not org_result.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        org_data = org_result.data[0]

        invitation_data = invitation_result.data[0] if invitation_result.data else None

        return {
            "membership": {
                "id": str(membership_data.get("id")),
                "tenant_id": str(membership_data.get("tenant_id")),
                "user_id": str(membership_data.get("user_id")),
                "role": membership_data.get("role"),
                "joined_at": membership_data.get("joined_at"),
                "is_active": membership_data.get("is_active"),
                "permissions": membership_data.get("permissions", {}),
            },
            "organization": {
                "id": str(org_data.get("id")),
                "name": org_data.get("name"),
                "description": org_data.get("description"),
                "industry": org_data.get("industry"),
                "size": org_data.get("size"),
                "country": org_data.get("country"),
            },
            "invitation": {
                "credits_allocated": (
                    float(invitation_data.get("credits", 0)) if invitation_data else 0
                ),
                "invited_by_email": (
                    invitation_data.get("invited_by_email") if invitation_data else None
                ),
                "accepted_at": (
                    invitation_data.get("accepted_at")
                    if invitation_data
                    else membership_data.get("joined_at")
                ),
                "is_team_leader": (
                    invitation_data.get("is_team_leader", False)
                    if invitation_data
                    else False
                ),
                "is_admin": (
                    invitation_data.get("is_admin", False) if invitation_data else False
                ),
            },
        }

    async def get_organization_basic_info(self, org_id: str) -> Dict[str, Any]:
        """
        Get basic organization info (name, email).
        Used for email sending and simple lookups.
        """
        client = await get_async_supabase_client()

        result = await (
            client.table("tenants")
            .select("id, name, contact_email, tenant_type")
            .eq("id", org_id)
            .eq("tenant_type", "organization")
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        return result.data[0]

    async def get_organization_details(self, org_id: str) -> Dict[str, Any]:
        """
        Get organization details including billing config.

        OPTIMIZED: Uses asyncio.gather for parallel queries.
        Returns all tenant fields plus billing config data.
        """
        client = await get_async_supabase_client()

        # Parallel queries
        tenant_task = (
            client.table("tenants")
            .select("*")
            .eq("id", org_id)
            .eq("tenant_type", "organization")
            .limit(1)
            .execute()
        )
        billing_task = (
            client.table("organization_billing_config")
            .select("*")
            .eq("tenant_id", org_id)
            .limit(1)
            .execute()
        )

        tenant_result, billing_result = await asyncio.gather(tenant_task, billing_task)

        if not tenant_result.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org_data = dict(tenant_result.data[0])
        billing_config = billing_result.data[0] if billing_result.data else None

        # Add billing config fields to org data
        if billing_config:
            org_data["organization_type"] = billing_config.get(
                "organization_type", "grant_org"
            )
            org_data["billing_settings"] = billing_config.get("billing_settings")
            org_data["billing_config_created_at"] = billing_config.get("created_at")
            org_data["billing_config_updated_at"] = billing_config.get("updated_at")

        return org_data

    async def get_available_credits(self, org_id: str) -> float:
        """
        Get available credits for an organization.
        Uses the async credit service.
        """
        return await self.credit_service.get_available_credits(org_id)

    # =========================================================================
    # Organization Validation & Config Methods
    # =========================================================================

    async def validate_organization(
        self, org_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Validate organization exists and is active.
        Returns: (is_valid, org_data, error_message)
        """
        client = await get_async_supabase_client()
        result = await (
            client.table("tenants")
            .select("id, name, tenant_type, is_active, contact_email")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return False, None, "Organization not found"

        org = result.data[0]
        if org.get("tenant_type") != "organization":
            return False, None, "Not an organization tenant"

        if not org.get("is_active", True):
            return False, None, "Organization is inactive"

        return True, org, ""

    async def get_org_billing_config(self, org_id: str) -> Dict[str, Any]:
        """Get organization billing configuration asynchronously."""
        client = await get_async_supabase_client()
        result = await (
            client.table("organization_billing_config")
            .select("*")
            .eq("tenant_id", org_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return {"organization_type": "grant_org"}

    async def get_org_type(self, org_id: str) -> str:
        """Get organization type (grant_org, prepay_org, postpay_org)."""
        config = await self.get_org_billing_config(org_id)
        return config.get("organization_type", "grant_org")

    # =========================================================================
    # Invitation Methods
    # =========================================================================

    async def has_invite(self, org_id: str, email: str) -> bool:
        """Check if user has an outstanding invite."""
        client = await get_async_supabase_client()
        normalized_email = email.strip().lower()

        result = await (
            client.table("organization_invitations")
            .select("id")
            .eq("organization_id", org_id)
            .eq("email", normalized_email)
            .in_("status", ["queued", "sent", "accepted"])
            .limit(1)
            .execute()
        )
        return bool(result.data)

    async def has_admin_invite(self, org_id: str, email: str) -> bool:
        """Check if user has an admin invite."""
        client = await get_async_supabase_client()
        normalized_email = email.strip().lower()

        result = await (
            client.table("organization_invitations")
            .select("id")
            .eq("organization_id", org_id)
            .eq("email", normalized_email)
            .eq("is_admin", True)
            .in_("status", ["queued", "sent", "accepted"])
            .limit(1)
            .execute()
        )
        return bool(result.data)

    async def has_team_leader_invite(self, org_id: str, email: str) -> bool:
        """Check if user has a team leader invite."""
        client = await get_async_supabase_client()
        normalized_email = email.strip().lower()

        result = await (
            client.table("organization_invitations")
            .select("id")
            .eq("organization_id", org_id)
            .eq("email", normalized_email)
            .eq("is_team_leader", True)
            .in_("status", ["queued", "sent", "accepted"])
            .limit(1)
            .execute()
        )
        return bool(result.data)

    async def record_invitation(
        self,
        organization_id: str,
        email: str,
        is_admin: bool,
        is_team_leader: bool,
        invited_by_user_id: Optional[str],
        invited_by_email: Optional[str],
        credits: int = 0,
        cohort_id: Optional[str] = None,
        can_skip_modules: bool = False,
    ) -> Dict[str, Any]:
        """
        Record invitation in database asynchronously.
        Updates existing invitation or creates new one.

        For grant/prepay orgs with credits > 0, reserves the credits from the org's pool.
        The reservation expires after 48 hours if not accepted.
        """
        client = await get_async_supabase_client()
        normalized_email = email.strip().lower()

        # Check for existing invitation (and fetch billing config in parallel if credits > 0)
        existing_task = (
            client.table("organization_invitations")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("email", normalized_email)
            .in_("status", ["queued", "sent", "accepted"])
            .limit(1)
            .execute()
        )

        if credits > 0:
            # Fetch billing config in parallel since we'll need it later
            existing, billing_config = await asyncio.gather(
                existing_task,
                self.get_org_billing_config(organization_id),
            )
        else:
            existing = await existing_task
            billing_config = None

        invitation = None

        if existing.data:
            # Update existing invitation
            existing_inv = existing.data[0]
            old_credits = existing_inv.get("credits", 0)

            update_payload = {
                "is_admin": is_admin,
                "is_team_leader": is_team_leader,
                "credits": credits,
                "invited_by": invited_by_user_id,
                "invited_by_email": invited_by_email,
                "status": "queued",
                "cohort_id": cohort_id,
                "can_skip_modules": can_skip_modules,
            }

            updated = await (
                client.table("organization_invitations")
                .update(update_payload)
                .eq("id", existing_inv["id"])
                .execute()
            )
            invitation = updated.data[0] if updated.data else existing_inv

            # Handle credit reservation changes for existing invitation
            if credits != old_credits:
                # Release old reservation if any
                await self.credit_service.release_reservation(existing_inv["id"])

        else:
            # Create new invitation
            payload = {
                "organization_id": organization_id,
                "email": normalized_email,  # Store lowercase for consistent lookups
                "is_admin": is_admin,
                "is_team_leader": is_team_leader,
                "invited_by": invited_by_user_id,
                "invited_by_email": invited_by_email,
                "status": "queued",
                "credits": credits,
                "cohort_id": cohort_id,
                "can_skip_modules": can_skip_modules,
            }

            result = (
                await client.table("organization_invitations").insert(payload).execute()
            )

            if not result.data:
                raise HTTPException(
                    status_code=500, detail="Failed to record invitation"
                )

            invitation = result.data[0]

        # Reserve credits if applicable (billing_config already fetched in parallel earlier)
        # Only reserve for:
        # - New invitations with credits > 0, OR
        # - Existing invitations where credits changed (old reservation was already released above)
        is_new_invitation = not existing.data
        credits_changed = existing.data and credits != existing.data[0].get(
            "credits", 0
        )
        should_reserve = (
            credits > 0 and billing_config and (is_new_invitation or credits_changed)
        )

        if should_reserve and billing_config:
            org_type = billing_config.get("organization_type", "grant_org")

            # Only reserve for grant/prepay orgs (postpay has unlimited capacity)
            if org_type != "postpay_org":
                try:
                    await self.credit_service.reserve_credits_for_invitation(
                        organization_id=organization_id,
                        invitation_id=invitation["id"],
                        amount=Decimal(str(credits)),
                        reservation_hours=48,
                    )
                except InsufficientCreditsError as e:
                    # Rollback invitation creation/update
                    if is_new_invitation:
                        # Delete newly created invitation
                        await (
                            client.table("organization_invitations")
                            .delete()
                            .eq("id", invitation["id"])
                            .execute()
                        )
                    else:
                        # Restore old credits value
                        await (
                            client.table("organization_invitations")
                            .update({"credits": existing.data[0].get("credits", 0)})
                            .eq("id", invitation["id"])
                            .execute()
                        )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits to reserve {credits} for invitation: {str(e)}",
                    )

        return invitation

    async def update_invitation_status(
        self,
        invitation_id: str,
        status: str,
        sent_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update invitation status asynchronously."""
        if not invitation_id:
            return

        client = await get_async_supabase_client()
        update: Dict[str, Any] = {"status": status}

        if sent_at:
            update["sent_at"] = sent_at.isoformat()
        if error:
            update["error"] = error

        await (
            client.table("organization_invitations")
            .update(update)
            .eq("id", invitation_id)
            .execute()
        )

    async def accept_matching_invites(
        self,
        org_id: str,
        email: str,
        role: str,
        user_id: str,
        membership_id: str,
    ) -> None:
        """Mark matching invitations as accepted."""
        client = await get_async_supabase_client()
        normalized_email = email.strip().lower()
        now = datetime.now(timezone.utc).isoformat()

        await (
            client.table("organization_invitations")
            .update(
                {
                    "status": "accepted",
                    "accepted_by": user_id,
                    "accepted_at": now,
                    "accepted_role": role,
                }
            )
            .eq("organization_id", org_id)
            .eq("email", normalized_email)
            .in_("status", ["queued", "sent"])
            .execute()
        )

    async def batch_record_invitations(
        self,
        organization_id: str,
        invites: List[Dict[str, Any]],
        invited_by_user_id: Optional[str],
        invited_by_email: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Record multiple invitations using efficient batch DB operations.

        Optimizations:
        - Single query to fetch all existing invitations
        - Single query to batch insert new invitations
        - Parallel updates for existing invitations (Supabase doesn't support
          batch updates with different values per row)
        - Batch credit reservation handling

        Returns list of created/updated invitation records.

        Raises:
            HTTPException: If cohort_id is invalid or doesn't belong to the organization.
        """
        if not invites:
            return []

        client = await get_async_supabase_client()

        # Validate cohort_ids before processing
        cohort_ids = set()
        for inv in invites:
            cohort_id = inv.get("cohort_id")
            if cohort_id:
                cohort_ids.add(cohort_id)

        if cohort_ids:
            # Fetch all cohorts that belong to this organization
            cohort_result = await (
                client.table("cohorts")
                .select("id")
                .eq("tenant_id", organization_id)
                .in_("id", list(cohort_ids))
                .execute()
            )
            valid_cohort_ids = {c["id"] for c in (cohort_result.data or [])}

            # Check for invalid cohort_ids
            invalid_cohorts = cohort_ids - valid_cohort_ids
            if invalid_cohorts:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "invalid_cohort",
                        "message": f"The following cohort IDs do not exist or do not belong to this organization: {list(invalid_cohorts)}",
                    }
                )

        # Normalize all emails and build lookup map
        normalized_invites = []
        email_to_invite: Dict[str, Dict[str, Any]] = {}
        for inv in invites:
            normalized_email = inv["email"].strip().lower()
            normalized_inv = {**inv, "email": normalized_email}
            normalized_invites.append(normalized_inv)
            email_to_invite[normalized_email] = normalized_inv

        emails = list(email_to_invite.keys())

        # Determine if we need billing config (any invites have credits > 0)
        any_credits = any(inv.get("credits", 0) > 0 for inv in normalized_invites)

        # Phase 1: Batch fetch existing invitations and billing config in parallel
        existing_task = (
            client.table("organization_invitations")
            .select("*")
            .eq("organization_id", organization_id)
            .in_("email", emails)
            .in_("status", ["queued", "sent", "accepted"])
            .execute()
        )

        if any_credits:
            existing_result, billing_config = await asyncio.gather(
                existing_task,
                self.get_org_billing_config(organization_id),
            )
        else:
            existing_result = await existing_task
            billing_config = None

        # Build map of existing invitations by email
        existing_by_email: Dict[str, Dict[str, Any]] = {}
        for existing in existing_result.data or []:
            existing_by_email[existing["email"]] = existing

        # Separate into updates and inserts
        to_update: List[tuple] = []  # (existing_record, new_invite_data)
        to_insert: List[Dict[str, Any]] = []  # new_invite_data

        for inv in normalized_invites:
            email = inv["email"]
            if email in existing_by_email:
                to_update.append((existing_by_email[email], inv))
            else:
                to_insert.append(inv)

        results: List[Dict[str, Any]] = []

        # Phase 2: Handle updates
        if to_update:
            # Release old reservations for invites where credits changed (parallel)
            release_tasks = []
            for existing, inv in to_update:
                old_credits = existing.get("credits", 0)
                new_credits = inv.get("credits", 0)
                if old_credits != new_credits:
                    release_tasks.append(
                        self.credit_service.release_reservation(existing["id"])
                    )
            if release_tasks:
                await asyncio.gather(*release_tasks, return_exceptions=True)

            # Update existing invitations in parallel
            # (Supabase doesn't support batch update with different values per row)
            update_tasks = []
            for existing, inv in to_update:
                update_payload = {
                    "is_admin": inv.get("is_admin", False),
                    "is_team_leader": inv.get("is_team_leader", False),
                    "credits": inv.get("credits", 0),
                    "invited_by": invited_by_user_id,
                    "invited_by_email": invited_by_email,
                    "status": "queued",
                    "cohort_id": inv.get("cohort_id"),
                    "can_skip_modules": inv.get("can_skip_modules", False),
                }
                update_tasks.append(
                    client.table("organization_invitations")
                    .update(update_payload)
                    .eq("id", existing["id"])
                    .execute()
                )

            update_results = await asyncio.gather(*update_tasks, return_exceptions=True)

            for i, (existing, inv) in enumerate(to_update):
                result = update_results[i]
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to update invitation for {inv['email']}: {result}"
                    )
                else:
                    updated_inv = result.data[0] if result.data else existing
                    results.append(updated_inv)

        # Phase 3: Batch insert new invitations (single DB call)
        if to_insert:
            insert_payloads = [
                {
                    "organization_id": organization_id,
                    "email": inv["email"],
                    "is_admin": inv.get("is_admin", False),
                    "is_team_leader": inv.get("is_team_leader", False),
                    "invited_by": invited_by_user_id,
                    "invited_by_email": invited_by_email,
                    "status": "queued",
                    "credits": inv.get("credits", 0),
                    "cohort_id": inv.get("cohort_id"),
                    "can_skip_modules": inv.get("can_skip_modules", False),
                }
                for inv in to_insert
            ]

            try:
                insert_result = await (
                    client.table("organization_invitations")
                    .insert(insert_payloads)
                    .execute()
                )
                if insert_result.data:
                    results.extend(insert_result.data)
            except Exception as e:
                logger.error(f"Failed to batch insert invitations: {e}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "invitation_insert_failed",
                        "message": f"Failed to create invitations: {str(e)}",
                    }
                )

        # Phase 4: Handle credit reservations for grant/prepay orgs
        if any_credits and billing_config:
            org_type = billing_config.get("organization_type", "grant_org")

            if org_type != "postpay_org":
                # Build map of results by email for credit reservation
                results_by_email = {r["email"]: r for r in results}

                reserve_tasks = []
                reserve_contexts = []  # Track context for error handling
                for inv in normalized_invites:
                    credits = inv.get("credits", 0)
                    if credits > 0:
                        email = inv["email"]
                        result_inv = results_by_email.get(email)
                        if result_inv:
                            existing = existing_by_email.get(email)
                            is_new = existing is None
                            credits_changed = existing and credits != existing.get(
                                "credits", 0
                            )

                            if is_new or credits_changed:
                                reserve_tasks.append(
                                    self._reserve_credits_for_batch_invite(
                                        organization_id=organization_id,
                                        invitation=result_inv,
                                        amount=credits,
                                        is_new=is_new,
                                        existing=existing,
                                    )
                                )
                                reserve_contexts.append(
                                    (email, result_inv, is_new, existing)
                                )

                if reserve_tasks:
                    reserve_results = await asyncio.gather(
                        *reserve_tasks, return_exceptions=True
                    )

                    # Handle any reservation failures
                    for i, res in enumerate(reserve_results):
                        if isinstance(res, Exception):
                            email, result_inv, is_new, existing = reserve_contexts[i]
                            logger.error(
                                f"Credit reservation failed for {email}: {res}"
                            )
                            # Remove failed invitation from results
                            results = [r for r in results if r.get("email") != email]

        return results

    async def _reserve_credits_for_batch_invite(
        self,
        organization_id: str,
        invitation: Dict[str, Any],
        amount: int,
        is_new: bool,
        existing: Optional[Dict[str, Any]],
    ) -> None:
        """
        Reserve credits for a single invitation in batch context.
        Handles rollback on insufficient credits.
        """
        client = await get_async_supabase_client()

        try:
            await self.credit_service.reserve_credits_for_invitation(
                organization_id=organization_id,
                invitation_id=invitation["id"],
                amount=Decimal(str(amount)),
                reservation_hours=48,
            )
        except InsufficientCreditsError as e:
            # Rollback invitation creation/update
            if is_new:
                await (
                    client.table("organization_invitations")
                    .delete()
                    .eq("id", invitation["id"])
                    .execute()
                )
            elif existing:
                await (
                    client.table("organization_invitations")
                    .update({"credits": existing.get("credits", 0)})
                    .eq("id", invitation["id"])
                    .execute()
                )
            # Re-raise to signal failure
            raise e

    async def send_org_invite_and_update(
        self,
        invitation_id: str,
        to_email: str,
        org_name: str,
        invite_link: str,
        is_team_leader: bool = False,
        credit_amount: int = 0,
    ) -> None:
        """Send organization invite email and update status (async)."""
        from ..services.communication.email_service import email_service

        try:
            # Send different email based on whether user is team leader or individual member
            if is_team_leader:
                email_sent = email_service.send_org_team_leader_invite_email(
                    to_email=to_email,
                    org_name=org_name,
                    credit_amount=credit_amount,
                    invite_link=invite_link,
                )
            else:
                email_sent = email_service.send_org_individual_member_invite_email(
                    to_email=to_email,
                    org_name=org_name,
                    credit_amount=credit_amount,
                    invite_link=invite_link,
                )

            if email_sent:
                await self.update_invitation_status(
                    invitation_id=invitation_id,
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                raise Exception("Email service returned False")

        except Exception as e:
            logger.error(f"Org invite email failed for {to_email}: {e}")
            await self.update_invitation_status(
                invitation_id=invitation_id,
                status="failed",
                error=str(e),
            )

    # =========================================================================
    # Organization Metrics
    # =========================================================================

    async def get_org_metrics(self, org_id: str) -> Dict[str, Any]:
        """
        Get organization metrics with parallel queries.

        Returns structure matching OrgMetricsResponse model.
        """
        client = await get_async_supabase_client()

        # Phase 1: Get team IDs and other metrics in parallel
        phase1_tasks = [
            # Teams in this org
            client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .execute(),
            # Individual members count
            client.table("org_individuals")
            .select("id", count="exact")
            .eq("organization_id", org_id)
            .execute(),
            # All invitations (to calculate sent, accepted, and pending counts)
            # Include sent_at for expiration checking (>48 hours = expired)
            client.table("organization_invitations")
            .select("id, status, is_team_leader, sent_at, created_at")
            .eq("organization_id", org_id)
            .execute(),
            # Credit summary (available + consumed)
            self.credit_service.get_credit_summary(org_id),
        ]

        results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

        def safe_count(result, default=0):
            if isinstance(result, Exception):
                return default
            if hasattr(result, "count") and result.count is not None:
                return result.count
            if hasattr(result, "data"):
                return len(result.data or [])
            return default

        def safe_data(result, default=None):
            if isinstance(result, Exception):
                return default
            if hasattr(result, "data"):
                return result.data
            return default

        teams_data = safe_data(results[0], [])
        individuals_count = safe_count(results[1])
        all_invitations = safe_data(results[2], [])
        credit_summary = results[3] if not isinstance(results[3], Exception) else {}

        # Helper function to check if invitation is expired (>48 hours old)
        # Must match the logic in get_individual_members for consistency
        now_utc = datetime.now(timezone.utc)
        expiration_threshold = now_utc - timedelta(hours=48)

        def is_invitation_expired(inv: Dict[str, Any]) -> bool:
            """Check if invitation is expired based on sent_at timestamp."""
            timestamp_str = inv.get("sent_at") or inv.get("created_at")
            if not timestamp_str:
                return True  # No timestamp = expired
            try:
                ts_str = str(timestamp_str)
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                elif "+" not in ts_str and "-" not in ts_str[-6:]:
                    ts_str = ts_str + "+00:00"
                invitation_dt = datetime.fromisoformat(ts_str)
                if invitation_dt.tzinfo is None:
                    invitation_dt = invitation_dt.replace(tzinfo=timezone.utc)
                return invitation_dt < expiration_threshold
            except (ValueError, TypeError):
                return True  # Parse error = expired

        # Calculate invitation metrics from all invitations
        # Match the sync service.py logic for consistency
        sent_invites = sum(
            1 for inv in all_invitations
            if inv.get("status") not in ("failed", "queued")
        )
        accepted_invites = sum(
            1 for inv in all_invitations
            if inv.get("status") == "accepted"
        )
        # Pending individual member invitations (is_team_leader = False or NULL)
        # Only count non-expired invitations as pending
        pending_individual = sum(
            1 for inv in all_invitations
            if inv.get("status") in ("sent", "queued") 
            and not inv.get("is_team_leader", False)
            and not is_invitation_expired(inv)
        )
        # Pending team leader invitations (is_team_leader = True explicitly)
        # Only count non-expired invitations as pending
        pending_team_leader = sum(
            1 for inv in all_invitations
            if inv.get("status") in ("sent", "queued") 
            and inv.get("is_team_leader") is True
            and not is_invitation_expired(inv)
        )

        logger.info(
            f"📊 get_org_metrics: org={org_id} invitations(sent={sent_invites}, "
            f"accepted={accepted_invites}, pending_individual={pending_individual}, "
            f"pending_team_leader={pending_team_leader})"
        )

        # Phase 2: Count team members if there are teams
        team_ids = [t["team_id"] for t in (teams_data or [])]
        team_members_count = 0

        if team_ids:
            team_members_result = await (
                client.table("tenant_memberships")
                .select("id", count="exact")
                .in_("tenant_id", team_ids)
                .eq("is_active", True)
                .execute()
            )
            team_members_count = safe_count(team_members_result)

        total_members = individuals_count + team_members_count

        # Return structure matching OrgMetricsResponse model
        return {
            "invitations": {
                "sent": sent_invites,
                "accepted": accepted_invites,
                "pending_individual": pending_individual,
                "pending_team_leader": pending_team_leader,
            },
            "membership": {
                "total": total_members,
                "team_members": team_members_count,
                "individual_members": individuals_count,
            },
            "credits": {
                "total": credit_summary.get("total_credits", 0)
                if isinstance(credit_summary, dict)
                else 0,
                "used": int(credit_summary.get("consumed_credits", 0))
                if isinstance(credit_summary, dict)
                else 0,
                "remaining": credit_summary.get("remaining_credits", 0)
                if isinstance(credit_summary, dict)
                else 0,
                "monthly_limit": None,
            },
        }

    # =========================================================================
    # Organization CRUD Operations
    # =========================================================================

    async def update_organization(
        self,
        org_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update organization details asynchronously."""
        client = await get_async_supabase_client()

        # Filter allowed fields
        allowed_fields = {"name", "contact_email", "contact_phone", "description"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = await (
            client.table("tenants")
            .update(filtered_updates)
            .eq("id", org_id)
            .eq("tenant_type", "organization")
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        return result.data[0]

    async def delete_organization_member(
        self,
        org_id: str,
        user_id: str,
        admin_user_id: str,
    ) -> Dict[str, Any]:
        """
        Remove a member from the organization.
        Returns any allocated credits to the org pool.
        """
        client = await get_async_supabase_client()

        # Parallel: get membership, individual tenant, and org type
        tasks = [
            client.table("tenant_memberships")
            .select("id, role")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute(),
            client.table("org_individuals")
            .select("individual_tenant_id")
            .eq("organization_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute(),
            self.get_org_type(org_id),
        ]

        results = await asyncio.gather(*tasks)
        membership_result, individual_result, org_type = results

        if not membership_result.data:
            raise HTTPException(status_code=404, detail="Member not found")

        membership = membership_result.data[0]
        individual_tenant_id = (
            individual_result.data[0]["individual_tenant_id"]
            if individual_result.data
            else None
        )

        credits_returned = 0

        # Return credits if individual has any
        if individual_tenant_id and org_type != "postpay_org":
            # Get user's credit balance
            user_credits = await self.credit_service.get_available_credits(
                individual_tenant_id
            )

            if user_credits > 0:
                now_iso = datetime.now(timezone.utc).isoformat()

                # Deactivate user lots and create lot for org in parallel
                deactivate_task = (
                    client.table("credit_lots")
                    .update({"is_active": False})
                    .eq("tenant_id", individual_tenant_id)
                    .eq("is_active", True)
                    .execute()
                )

                from decimal import Decimal

                create_lot_task = self.credit_service.create_credit_lot(
                    tenant_id=org_id,
                    source="grant",  # Use "grant" since "returned" is not a valid enum value
                    credit_amount=Decimal(str(user_credits)),
                    valid_from=now_iso,
                    expires_at=None,
                    metadata={
                        "returned_from_user": user_id,
                        "returned_by": admin_user_id,
                        "reason": "member_removed",
                    },
                    original_tenant_id=org_id,
                )

                await asyncio.gather(deactivate_task, create_lot_task)
                credits_returned = user_credits

        # Delete membership and org_individuals record in parallel
        delete_tasks = [
            client.table("tenant_memberships")
            .delete()
            .eq("id", membership["id"])
            .execute(),
        ]

        if individual_tenant_id:
            delete_tasks.append(
                client.table("org_individuals")
                .delete()
                .eq("organization_id", org_id)
                .eq("user_id", user_id)
                .execute()
            )

        await asyncio.gather(*delete_tasks)

        return {
            "success": True,
            "message": "Member removed successfully",
            "credits_returned": credits_returned,
        }

    async def delete_pending_invitation(
        self,
        org_id: str,
        invitation_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a pending invitation.

        Releases any reserved credits back to the organization's available pool.
        """
        client = await get_async_supabase_client()

        # Release reserved credits BEFORE delete (sequential required)
        # FK has ON DELETE SET NULL which clears reserved_for_invitation_id,
        # but we also need to clear reserved_until for credits to be available
        lots_released = await self.credit_service.release_reservation(invitation_id)

        result = await (
            client.table("organization_invitations")
            .delete()
            .eq("id", invitation_id)
            .eq("organization_id", org_id)
            .in_("status", ["sent", "queued"])
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Invitation not found")

        message = "Invitation deleted"
        if lots_released > 0:
            message += f" and {lots_released} credit lot(s) released"

        return {"success": True, "message": message, "lots_released": lots_released}

    async def resend_invitation(
        self,
        org_id: str,
        invitation_id: str,
        admin_user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Resend an invitation by updating its status to queued.

        Also refreshes the credit reservation for the new 48h window.
        Returns the data required for email sending (email, invite_link, flags).
        """
        client = await get_async_supabase_client()

        # Get invitation
        result = await (
            client.table("organization_invitations")
            .select("id, email, credits, is_admin, is_team_leader, status, organization_id")
            .eq("id", invitation_id)
            .eq("organization_id", org_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Invitation not found")

        invitation = result.data[0]
        credits = invitation.get("credits", 0)

        # Validate resendable statuses
        resendable_statuses = ["sent", "queued", "failed"]
        if invitation.get("status") not in resendable_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resend invitation with status '{invitation.get('status')}'.",
            )

        # Handle credit reservation refresh
        if credits > 0:
            # Fetch billing config and release old reservation in parallel
            billing_config, _ = await asyncio.gather(
                self.get_org_billing_config(org_id),
                self.credit_service.release_reservation(invitation_id),
            )
            org_type = billing_config.get("organization_type", "grant_org")

            if org_type != "postpay_org":
                # Create new reservation for 48h
                try:
                    await self.credit_service.reserve_credits_for_invitation(
                        organization_id=org_id,
                        invitation_id=invitation_id,
                        amount=Decimal(str(credits)),
                        reservation_hours=48,
                    )
                except InsufficientCreditsError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits to reserve {credits} for resend: {str(e)}",
                    )

        # Create a new invite token and link
        from src.mint.utils.url_safe_serializer import create_invite_token
        import os

        token = create_invite_token(
            tenant_id=org_id,
            is_admin=bool(invitation.get("is_admin", False)),
            credit=int(invitation.get("credits") or 0),
            is_team_leader=bool(invitation.get("is_team_leader", False)),
        )
        frontend_url = os.getenv("FRONTEND_URL", "")
        invite_link = f"{frontend_url}/invite/{token}?org_id={org_id}"

        # Update status to queued and clear previous send info
        await (
            client.table("organization_invitations")
            .update({"status": "queued", "sent_at": None, "error": None})
            .eq("id", invitation_id)
            .execute()
        )

        return {
            "success": True,
            "message": "Invitation prepared for resend",
            "invitation_id": invitation_id,
            "email": invitation.get("email"),
            "invite_link": invite_link,
            "is_team_leader": bool(invitation.get("is_team_leader", False)),
            "credits": int(invitation.get("credits") or 0),
            "organization_id": org_id,
        }

    # =========================================================================
    # Credit Allocation Methods (using AsyncCreditService)
    # =========================================================================

    async def allocate_credits_to_member(
        self,
        org_id: str,
        user_id: str,
        amount: float,
        allocated_by_user_id: str,
    ) -> Dict[str, Any]:
        """
        Allocate credits from organization to an individual member.

        For postpay orgs: Records allocation for later invoicing (no deduction).
        For grant/prepay orgs: Checks balance and deducts from org lots.
        """
        client = await get_async_supabase_client()

        # Get user's individual tenant and org billing config in parallel
        individual_task = (
            client.table("org_individuals")
            .select("individual_tenant_id")
            .eq("organization_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        billing_task = self.get_org_billing_config(org_id)

        individual_result, billing_config = await asyncio.gather(
            individual_task, billing_task
        )

        if not individual_result.data:
            raise HTTPException(
                status_code=404,
                detail="User does not have an individual tenant in this organization",
            )

        individual_tenant_id = individual_result.data[0]["individual_tenant_id"]
        org_type = billing_config.get("organization_type", "grant_org")
        is_postpay = org_type == "postpay_org"

        now_iso = datetime.now(timezone.utc).isoformat()
        from decimal import Decimal

        if is_postpay:
            # Postpay org: Create credit lot without deducting from org
            created_lot = await self.credit_service.create_credit_lot(
                tenant_id=individual_tenant_id,
                source="purchase",  # Use "purchase" like team service
                credit_amount=Decimal(str(amount)),
                valid_from=now_iso,
                expires_at=None,  # No expiry for postpay
                metadata={
                    "source": "organization_allocation",
                    "organization_id": org_id,
                    "allocated_by": allocated_by_user_id,
                },
                original_tenant_id=org_id,
            )

            # Record allocation for billing - if this fails, rollback the credit lot
            try:
                await (
                    client.table("organization_credit_allocations")
                    .insert(
                        {
                            "tenant_id": org_id,
                            "allocation_type": "allocation_to_member",
                            "credit_amount": float(amount),
                            "credit_lot_id": created_lot.get("id")
                            if created_lot
                            else None,
                            "allocated_to_tenant_id": individual_tenant_id,
                            "allocated_to_user_id": user_id,
                            "allocated_by_user_id": allocated_by_user_id,
                            "allocated_at": now_iso,
                            "metadata": {
                                "source": "member_allocation",
                            },
                        }
                    )
                    .execute()
                )
                logger.info(
                    f"Recorded postpay member allocation for org {org_id}: "
                    f"{amount} credits to user {user_id}"
                )
            except Exception as e:
                # Rollback: delete the credit lot we just created
                if created_lot and created_lot.get("id"):
                    await (
                        client.table("credit_lots")
                        .delete()
                        .eq("id", created_lot["id"])
                        .execute()
                    )
                logger.error(
                    f"Failed to record postpay member allocation: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to record allocation for billing: {str(e)}",
                )

            return {
                "success": True,
                "message": f"Allocated {amount} credits to user (postpay - will be invoiced)",
                "allocated_amount": amount,
                "billing_type": "postpay",
            }
        else:
            # Grant/prepay org: Check unreserved credits and deduct
            # Use unreserved credits to exclude credits reserved for pending invitations
            available = await self.credit_service.get_unreserved_available_credits(
                org_id
            )
            if available < amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient credits. Available: {available}, Requested: {amount}",
                )

            # Deduct from org's credit lots (excludes reserved lots)
            remaining = await self._deduct_from_org_lots(
                client, org_id, amount, now_iso
            )
            if remaining > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to deduct full amount. Remaining: {remaining}",
                )

            # Create lot for user - source based on org type
            lot_source = "grant" if org_type == "grant_org" else "purchase"
            await self.credit_service.create_credit_lot(
                tenant_id=individual_tenant_id,
                source=lot_source,
                credit_amount=Decimal(str(amount)),
                valid_from=now_iso,
                expires_at=None,
                metadata={
                    "source": "organization_allocation",
                    "organization_id": org_id,
                    "allocated_by": allocated_by_user_id,
                },
                original_tenant_id=org_id,
            )

            return {
                "success": True,
                "message": f"Allocated {amount} credits to user",
                "allocated_amount": amount,
                "billing_type": org_type,
            }

    async def allocate_credits_to_team(
        self,
        org_id: str,
        team_id: str,
        amount: float,
        allocated_by_user_id: str,
    ) -> Dict[str, Any]:
        """
        Allocate credits from organization to a team.

        For postpay orgs: Records allocation for later invoicing (no deduction).
        For grant/prepay orgs: Checks balance and deducts from org lots.
        """
        client = await get_async_supabase_client()

        # Verify team belongs to org and get billing config in parallel
        team_task = (
            client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .eq("team_id", team_id)
            .limit(1)
            .execute()
        )
        billing_task = self.get_org_billing_config(org_id)

        team_check, billing_config = await asyncio.gather(team_task, billing_task)

        if not team_check.data:
            raise HTTPException(
                status_code=404, detail="Team not found in organization"
            )

        org_type = billing_config.get("organization_type", "grant_org")
        is_postpay = org_type == "postpay_org"

        now_iso = datetime.now(timezone.utc).isoformat()
        from decimal import Decimal

        if is_postpay:
            # Postpay org: Create credit lot without deducting from org
            created_lot = await self.credit_service.create_credit_lot(
                tenant_id=team_id,
                source="purchase",  # Use "purchase" like team service
                credit_amount=Decimal(str(amount)),
                valid_from=now_iso,
                expires_at=None,  # No expiry for postpay
                metadata={
                    "source": "organization_allocation",
                    "organization_id": org_id,
                    "allocated_by": allocated_by_user_id,
                },
                original_tenant_id=org_id,
            )

            # Record allocation for billing - if this fails, rollback the credit lot
            try:
                await (
                    client.table("organization_credit_allocations")
                    .insert(
                        {
                            "tenant_id": org_id,
                            "allocation_type": "allocation_to_team",
                            "credit_amount": float(amount),
                            "credit_lot_id": created_lot.get("id")
                            if created_lot
                            else None,
                            "allocated_to_tenant_id": team_id,
                            "allocated_to_user_id": None,
                            "allocated_by_user_id": allocated_by_user_id,
                            "allocated_at": now_iso,
                            "metadata": {
                                "source": "team_allocation",
                            },
                        }
                    )
                    .execute()
                )
                logger.info(
                    f"Recorded postpay team allocation for org {org_id}: "
                    f"{amount} credits to team {team_id}"
                )
            except Exception as e:
                # Rollback: delete the credit lot we just created
                if created_lot and created_lot.get("id"):
                    await (
                        client.table("credit_lots")
                        .delete()
                        .eq("id", created_lot["id"])
                        .execute()
                    )
                logger.error(
                    f"Failed to record postpay team allocation: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to record allocation for billing: {str(e)}",
                )

            return {
                "success": True,
                "message": f"Allocated {amount} credits to team (postpay - will be invoiced)",
                "allocated_amount": amount,
                "billing_type": "postpay",
            }
        else:
            # Grant/prepay org: Check unreserved credits and deduct
            # Use unreserved credits to exclude credits reserved for pending invitations
            available = await self.credit_service.get_unreserved_available_credits(
                org_id
            )
            if available < amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient credits. Available: {available}, Requested: {amount}",
                )

            # Deduct from org's credit lots
            remaining = await self._deduct_from_org_lots(
                client, org_id, amount, now_iso
            )
            if remaining > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to deduct full amount. Remaining: {remaining}",
                )

            # Create lot for team - source based on org type
            lot_source = "grant" if org_type == "grant_org" else "purchase"
            await self.credit_service.create_credit_lot(
                tenant_id=team_id,
                source=lot_source,
                credit_amount=Decimal(str(amount)),
                valid_from=now_iso,
                expires_at=None,
                metadata={
                    "source": "organization_allocation",
                    "organization_id": org_id,
                    "allocated_by": allocated_by_user_id,
                },
                original_tenant_id=org_id,
            )

            return {
                "success": True,
                "message": f"Allocated {amount} credits to team",
                "allocated_amount": amount,
                "billing_type": org_type,
            }

    async def _deduct_from_org_lots(
        self,
        client,
        org_id: str,
        amount: float,
        now_iso: str,
    ) -> float:
        """
        Deduct credits from organization's active lots.
        Returns remaining amount if not fully deducted.

        OPTIMIZED: Uses batch update instead of N+1 queries.
        NOTE: Excludes reserved lots (reserved_until > now) to prevent
        deducting credits that are reserved for pending invitations.
        """
        # Get active, non-expired, non-reserved lots ordered by expiry (soonest first)
        lots_result = await (
            client.table("credit_lots")
            .select("id, credit_amount, expires_at")
            .eq("tenant_id", org_id)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            .or_(f"reserved_until.is.null,reserved_until.lte.{now_iso}")
            .order("expires_at", desc=False, nullsfirst=False)
            .execute()
        )

        lots = lots_result.data or []
        remaining = amount

        # Calculate all deductions upfront
        deduction_updates = []
        for lot in lots:
            if remaining <= 0:
                break

            lot_amount = float(lot.get("credit_amount", 0))
            deduct = min(lot_amount, remaining)
            new_balance = lot_amount - deduct

            deduction_updates.append(
                {
                    "lot_id": lot["id"],
                    "new_balance": new_balance,
                }
            )

            remaining -= deduct

        # Batch update all lots
        if deduction_updates:
            await self.credit_service.batch_update_lot_balances(deduction_updates)

        return remaining

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    async def validate_user_is_org_member(
        self,
        org_id: str,
        user_id: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if user is a member of the organization."""
        client = await get_async_supabase_client()

        result = await (
            client.table("tenant_memberships")
            .select("id, role, is_active")
            .eq("tenant_id", org_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if result.data:
            return True, result.data[0]
        return False, None

    async def get_user_individual_tenant(
        self,
        org_id: str,
        user_id: str,
    ) -> Optional[str]:
        """Get user's individual tenant ID within an organization."""
        client = await get_async_supabase_client()

        result = await (
            client.table("org_individuals")
            .select("individual_tenant_id")
            .eq("organization_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]["individual_tenant_id"]
        return None

    @staticmethod
    async def _make_empty_result():
        """Return an empty result object for conditional queries (awaitable for asyncio.gather)."""

        class EmptyResult:
            data: List[Any] = []

        return EmptyResult()

    async def _assign_to_cohort(self, cohort_id: str, member_tenant_id: str) -> None:
        """
        Assign a tenant (individual or team) to a cohort.
        Silently fails if assignment fails (cohort assignment shouldn't block org join).
        """
        try:
            from ..billing.cohort_service import CohortService

            cohort_service = CohortService(use_service_role=True)
            cohort_service.assign_member_to_cohort(
                cohort_id=cohort_id, member_tenant_id=member_tenant_id
            )
            logger.info(f"Assigned tenant {member_tenant_id} to cohort {cohort_id}")
        except Exception as e:
            # Don't fail org join if cohort assignment fails
            logger.error(
                f"Failed to assign tenant {member_tenant_id} to cohort {cohort_id}: {e}"
            )

    # =========================================================================
    # Soft Delete Team (Async)
    # =========================================================================

    async def soft_delete_team(
        self,
        org_id: str,
        team_id: str,
        admin_user_id: str,
        return_credits_to_org: bool = True,
    ) -> Dict[str, Any]:
        """
        Soft delete a team from the organization with parallel operations.

        - Sets team tenant's is_active = False
        - Deactivates all team memberships
        - Optionally returns remaining credits to the organization
        - Deactivates team credit lots
        """
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Phase 1: Validate team belongs to org and get team data in parallel
        tasks = [
            client.table("org_teams")
            .select("team_id")
            .eq("organization_id", org_id)
            .eq("team_id", team_id)
            .limit(1)
            .execute(),
            client.table("tenants")
            .select("id, name, is_active")
            .eq("id", team_id)
            .limit(1)
            .execute(),
            client.table("tenant_memberships")
            .select("id", count="exact")
            .eq("tenant_id", team_id)
            .eq("is_active", True)
            .execute(),
        ]

        results = await asyncio.gather(*tasks)
        org_team_result, team_result, members_result = results

        if not org_team_result.data:
            raise HTTPException(
                status_code=404, detail="Team not found in organization"
            )

        if not team_result.data:
            raise HTTPException(status_code=404, detail="Team tenant not found")

        team = team_result.data[0]
        if not team.get("is_active", True):
            raise HTTPException(status_code=400, detail="Team is already deleted")

        members_deactivated = members_result.count or 0
        credits_returned = 0

        # Phase 2: Get credits and deactivate in parallel
        if return_credits_to_org:
            team_credits = await self.credit_service.get_available_credits(team_id)
            if team_credits > 0:
                from decimal import Decimal

                # Deactivate team lots and create org lot
                deactivate_task = (
                    client.table("credit_lots")
                    .update({"is_active": False})
                    .eq("tenant_id", team_id)
                    .eq("is_active", True)
                    .execute()
                )
                create_lot_task = self.credit_service.create_credit_lot(
                    tenant_id=org_id,
                    source="grant",  # Use "grant" since "returned" is not a valid enum value
                    credit_amount=Decimal(str(team_credits)),
                    valid_from=now_iso,
                    expires_at=None,
                    metadata={
                        "returned_from_team": team_id,
                        "returned_by": admin_user_id,
                        "reason": "team_deleted",
                    },
                    original_tenant_id=org_id,
                )
                await asyncio.gather(deactivate_task, create_lot_task)
                credits_returned = team_credits

        # Phase 3: Soft delete operations in parallel
        delete_tasks = [
            # Deactivate team tenant
            client.table("tenants")
            .update({"is_active": False, "updated_at": now_iso})
            .eq("id", team_id)
            .execute(),
            # Deactivate all memberships
            client.table("tenant_memberships")
            .update({"is_active": False})
            .eq("tenant_id", team_id)
            .eq("is_active", True)
            .execute(),
            # Remove from org_teams
            client.table("org_teams")
            .delete()
            .eq("organization_id", org_id)
            .eq("team_id", team_id)
            .execute(),
        ]

        # If not returning credits, just deactivate lots
        if not return_credits_to_org:
            delete_tasks.append(
                client.table("credit_lots")
                .update({"is_active": False})
                .eq("tenant_id", team_id)
                .eq("is_active", True)
                .execute()
            )

        await asyncio.gather(*delete_tasks)

        return {
            "success": True,
            "message": f"Team '{team.get('name', team_id)}' has been deleted",
            "team_id": team_id,
            "members_deactivated": members_deactivated,
            "credits_returned": credits_returned,
            "deleted_at": now_iso,
        }

    # =========================================================================
    # Join Organization (Async)
    # =========================================================================

    async def join_organization(
        self,
        tenant_id: str,
        user_id: str,
        user_email: str,
        request_admin: bool = False,
        credit_amount: int = 0,
    ) -> Dict[str, Any]:
        """
        Join an organization with optimized parallel queries.
        """
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        normalized_email = user_email.strip().lower()

        # Phase 1: Parallel validation queries
        tasks = [
            # Check org exists and is active
            client.table("tenants")
            .select("id, name, tenant_type, is_active")
            .eq("id", tenant_id)
            .limit(1)
            .execute(),
            # Check if user already a member
            client.table("tenant_memberships")
            .select("id, role, is_active")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute(),
            # Get matching invitation
            client.table("organization_invitations")
            .select(
                "id, is_admin, is_team_leader, credits, cohort_id, can_skip_modules"
            )
            .eq("organization_id", tenant_id)
            .eq("email", normalized_email)
            .in_("status", ["queued", "sent"])
            .limit(1)
            .execute(),
            # Get org billing config
            self.get_org_billing_config(tenant_id),
            # Check if user has org_individuals record (for partial join recovery)
            client.table("org_individuals")
            .select("individual_tenant_id")
            .eq("organization_id", tenant_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute(),
            # Get user profile for naming
            client.table("user_profiles")
            .select("full_name")
            .eq("id", user_id)
            .limit(1)
            .execute(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        def safe_data(result):
            if isinstance(result, Exception):
                return []
            return result.data if hasattr(result, "data") else result

        org_data = safe_data(results[0])
        membership_data = safe_data(results[1])
        invitation_data = safe_data(results[2])
        billing_config = results[3] if not isinstance(results[3], Exception) else {}
        org_individuals_data = safe_data(results[4])
        user_profile_data = safe_data(results[5])

        logger.info(
            "Join org precheck: tenant_id=%s user_id=%s email=%s org_found=%s membership=%s invite=%s org_individuals=%s",
            tenant_id,
            user_id,
            normalized_email,
            bool(org_data),
            membership_data[0] if membership_data else None,
            invitation_data[0] if invitation_data else None,
            org_individuals_data[0] if org_individuals_data else None,
        )

        user_full_name = None
        if user_profile_data:
            user_full_name = user_profile_data[0].get("full_name")

        display_name = (user_full_name or user_email or "user").strip()
        individual_tenant_name = f"{display_name}-{user_id[:6]}-{tenant_id[:8]}-org-ind"
        individual_tenant_description = (
            f"Personal tenant for {user_full_name or user_email} in organization"
        )

        # Validate organization
        if not org_data:
            return {"success": False, "message": "Organization not found"}

        org = org_data[0]
        if org.get("tenant_type") != "organization":
            return {"success": False, "message": "Not an organization tenant"}
        if not org.get("is_active", True):
            return {"success": False, "message": "Organization is inactive"}

        # Get invitation details
        invitation = invitation_data[0] if invitation_data else None
        is_admin = request_admin or (
            invitation.get("is_admin") if invitation else False
        )
        is_team_leader = (
            invitation.get("is_team_leader", False) if invitation else False
        )
        credits_to_allocate = credit_amount or (
            invitation.get("credits", 0) if invitation else 0
        )
        cohort_id = invitation.get("cohort_id") if invitation else None
        can_skip_modules = (
            invitation.get("can_skip_modules", False) if invitation else False
        )

        # Check existing membership - allow partial join recovery
        # A complete membership requires BOTH tenant_memberships AND org_individuals records
        has_membership = membership_data and membership_data[0].get("is_active")
        has_org_individual = bool(org_individuals_data)
        is_partial_join = has_membership and not has_org_individual

        if has_membership and has_org_individual and not is_team_leader:
            # Fully complete membership - reject retry
            logger.info(
                "Join org blocked: already member tenant_id=%s user_id=%s membership_id=%s org_individual_id=%s",
                tenant_id,
                user_id,
                membership_data[0].get("id") if membership_data else None,
                org_individuals_data[0].get("individual_tenant_id")
                if org_individuals_data
                else None,
            )
            return {
                "success": False,
                "message": "Already a member of this organization",
            }

        if is_partial_join:
            logger.info(
                f"Detected partial join for user {user_id} - recovering by completing org_individuals setup"
            )

        if has_membership and has_org_individual and is_team_leader:
            logger.info(
                "Join org continuing for team leader invite tenant_id=%s user_id=%s membership_id=%s",
                tenant_id,
                user_id,
                membership_data[0].get("id") if membership_data else None,
            )

        # Determine role
        role = "admin" if is_admin else "member"
        logger.info(
            "Join org invite resolved: tenant_id=%s user_id=%s is_admin=%s is_team_leader=%s credits=%s cohort_id=%s",
            tenant_id,
            user_id,
            is_admin,
            is_team_leader,
            credits_to_allocate,
            cohort_id,
        )

        # Phase 2: Create membership and individual tenant in parallel
        membership_id = None
        individual_tenant_id = None

        # Create or reactivate membership (skip if partial join - membership already exists)
        if is_partial_join:
            # Use existing active membership from partial join
            membership_id = membership_data[0]["id"]
            logger.info(
                f"Partial join recovery: using existing membership {membership_id}"
            )
        elif membership_data and membership_data[0].get("is_active"):
            membership_id = membership_data[0]["id"]
            logger.info(
                "Join org: using existing membership tenant_id=%s user_id=%s membership_id=%s",
                tenant_id,
                user_id,
                membership_id,
            )
        elif membership_data and not membership_data[0].get("is_active"):
            # Reactivate existing membership
            update_result = await (
                client.table("tenant_memberships")
                .update({"is_active": True, "role": role, "joined_at": now_iso})
                .eq("id", membership_data[0]["id"])
                .execute()
            )
            membership_id = membership_data[0]["id"]
            logger.info(
                "Join org: reactivated membership tenant_id=%s user_id=%s membership_id=%s",
                tenant_id,
                user_id,
                membership_id,
            )
        else:
            # Create new membership
            insert_result = await (
                client.table("tenant_memberships")
                .insert(
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "role": role,
                        "is_active": True,
                        "joined_at": now_iso,
                    }
                )
                .execute()
            )
            if insert_result.data:
                membership_id = insert_result.data[0]["id"]
                logger.info(
                    "Join org: created membership tenant_id=%s user_id=%s membership_id=%s",
                    tenant_id,
                    user_id,
                    membership_id,
                )

        # Create individual tenant for non-team-leader members
        if not is_team_leader:
            # Use already-fetched org_individuals_data instead of querying again
            if org_individuals_data:
                individual_tenant_id = org_individuals_data[0]["individual_tenant_id"]

                # Ensure membership exists for the individual tenant
                # (may be missing from a previous partial join failure)
                existing_ind_membership = await (
                    client.table("tenant_memberships")
                    .select("id")
                    .eq("tenant_id", individual_tenant_id)
                    .eq("user_id", user_id)
                    .limit(1)
                    .execute()
                )

                if not existing_ind_membership.data:
                    logger.info(
                        "Join org: creating missing membership for existing individual tenant "
                        "tenant_id=%s user_id=%s individual_tenant_id=%s",
                        tenant_id,
                        user_id,
                        individual_tenant_id,
                    )
                    await (
                        client.table("tenant_memberships")
                        .insert(
                            {
                                "tenant_id": individual_tenant_id,
                                "user_id": user_id,
                                "role": "owner",
                                "is_active": True,
                                "joined_at": now_iso,
                            }
                        )
                        .execute()
                    )

                # Assign to cohort if specified (user rejoining or re-invited)
                if cohort_id:
                    await self._assign_to_cohort(cohort_id, individual_tenant_id)
            else:
                existing_tenant_query = await (
                    client.table("tenants")
                    .select("id")
                    .eq("name", individual_tenant_name)
                    .eq("tenant_type", "individual")
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

                if existing_tenant_query.data:
                    individual_tenant_id = existing_tenant_query.data[0]["id"]
                    logger.info(
                        "Join org: reused individual tenant tenant_id=%s user_id=%s individual_tenant_id=%s",
                        tenant_id,
                        user_id,
                        individual_tenant_id,
                    )

                    # Check if membership exists for this reused tenant
                    existing_membership = await (
                        client.table("tenant_memberships")
                        .select("id")
                        .eq("tenant_id", individual_tenant_id)
                        .eq("user_id", user_id)
                        .limit(1)
                        .execute()
                    )

                    # Create org_individuals link and membership (if missing) in parallel
                    link_tasks = [
                        client.table("org_individuals")
                        .insert(
                            {
                                "organization_id": tenant_id,
                                "user_id": user_id,
                                "individual_tenant_id": individual_tenant_id,
                                "can_skip_modules": can_skip_modules,
                            }
                        )
                        .execute(),
                    ]

                    if not existing_membership.data:
                        logger.info(
                            "Join org: creating missing membership for reused tenant "
                            "tenant_id=%s user_id=%s individual_tenant_id=%s",
                            tenant_id,
                            user_id,
                            individual_tenant_id,
                        )
                        link_tasks.append(
                            client.table("tenant_memberships")
                            .insert(
                                {
                                    "tenant_id": individual_tenant_id,
                                    "user_id": user_id,
                                    "role": "owner",
                                    "is_active": True,
                                    "joined_at": now_iso,
                                }
                            )
                            .execute()
                        )

                    await asyncio.gather(*link_tasks)

                    if cohort_id:
                        await self._assign_to_cohort(cohort_id, individual_tenant_id)
                elif is_partial_join:
                    # Partial join recovery: check for orphaned individual tenant
                    # (created during failed join but not linked via org_individuals)
                    orphan_check = await (
                        client.table("tenants")
                        .select("id")
                        .eq("tenant_type", "individual")
                        .eq("name", individual_tenant_name)
                        .eq("is_active", True)
                        .limit(1)
                        .execute()
                    )

                    if orphan_check.data:
                        # Use existing orphaned individual tenant
                        individual_tenant_id = orphan_check.data[0]["id"]
                        logger.info(
                            f"Partial join recovery: found orphaned individual tenant {individual_tenant_id}"
                        )
                    else:
                        # Create new individual tenant
                        ind_tenant_result = await (
                            client.table("tenants")
                            .insert(
                                {
                                    "name": individual_tenant_name,
                                    "tenant_type": "individual",
                                    "is_active": True,
                                    "created_at": now_iso,
                                    "description": individual_tenant_description,
                                }
                            )
                            .execute()
                        )
                        if ind_tenant_result.data:
                            individual_tenant_id = ind_tenant_result.data[0]["id"]
                            logger.info(
                                "Partial join recovery: created individual tenant tenant_id=%s user_id=%s individual_tenant_id=%s",
                                tenant_id,
                                user_id,
                                individual_tenant_id,
                            )

                    # Create the missing org_individuals link and ensure membership exists
                    if individual_tenant_id:
                        # Check if membership exists
                        existing_membership = await (
                            client.table("tenant_memberships")
                            .select("id")
                            .eq("tenant_id", individual_tenant_id)
                            .eq("user_id", user_id)
                            .limit(1)
                            .execute()
                        )

                        # Create org_individuals link and membership (if missing) in parallel
                        link_tasks = [
                            client.table("org_individuals")
                            .insert(
                                {
                                    "organization_id": tenant_id,
                                    "user_id": user_id,
                                    "individual_tenant_id": individual_tenant_id,
                                    "can_skip_modules": can_skip_modules,
                                }
                            )
                            .execute(),
                        ]

                        if not existing_membership.data:
                            logger.info(
                                f"Partial join recovery: creating missing membership for tenant {individual_tenant_id}"
                            )
                            link_tasks.append(
                                client.table("tenant_memberships")
                                .insert(
                                    {
                                        "tenant_id": individual_tenant_id,
                                        "user_id": user_id,
                                        "role": "owner",
                                        "is_active": True,
                                        "joined_at": now_iso,
                                    }
                                )
                                .execute()
                            )

                        await asyncio.gather(*link_tasks)
                        logger.info(
                            f"Partial join recovery: created org_individuals link for {individual_tenant_id}"
                        )

                        # Assign to cohort if specified
                        if cohort_id:
                            await self._assign_to_cohort(
                                cohort_id, individual_tenant_id
                            )
                else:
                    # Normal flow: Create individual tenant
                    ind_tenant_result = await (
                        client.table("tenants")
                        .insert(
                            {
                                "name": individual_tenant_name,
                                "tenant_type": "individual",
                                "is_active": True,
                                "created_at": now_iso,
                                "description": individual_tenant_description,
                            }
                        )
                        .execute()
                    )
                    if ind_tenant_result.data:
                        individual_tenant_id = ind_tenant_result.data[0]["id"]
                        logger.info(
                            "Join org: created individual tenant tenant_id=%s user_id=%s individual_tenant_id=%s",
                            tenant_id,
                            user_id,
                            individual_tenant_id,
                        )

                        # Create org_individuals link and membership in parallel
                        # Note: cohort_id is handled separately via _assign_to_cohort() below
                        link_tasks = [
                            client.table("org_individuals")
                            .insert(
                                {
                                    "organization_id": tenant_id,
                                    "user_id": user_id,
                                    "individual_tenant_id": individual_tenant_id,
                                    "can_skip_modules": can_skip_modules,
                                }
                            )
                            .execute(),
                            client.table("tenant_memberships")
                            .insert(
                                {
                                    "tenant_id": individual_tenant_id,
                                    "user_id": user_id,
                                    "role": "owner",
                                    "is_active": True,
                                    "joined_at": now_iso,
                                }
                            )
                            .execute(),
                        ]
                        await asyncio.gather(*link_tasks)
                        logger.info(
                            "Join org: created org_individuals link and individual membership tenant_id=%s user_id=%s individual_tenant_id=%s",
                            tenant_id,
                            user_id,
                            individual_tenant_id,
                        )

                        # Assign individual tenant to cohort if specified in invitation
                        if cohort_id:
                            await self._assign_to_cohort(
                                cohort_id, individual_tenant_id
                            )

        # Phase 3: Allocate credits if any
        org_type = billing_config.get("organization_type", "grant_org")
        is_postpay = org_type == "postpay_org"

        if credits_to_allocate > 0 and not is_team_leader and individual_tenant_id:
            # Individual member: claim reserved credits or create lot for postpay
            lot_source = "grant" if org_type == "grant_org" else "purchase"

            if is_postpay:
                # Postpay: create credit lot without deducting from org
                created_lot = await self.credit_service.create_credit_lot(
                    tenant_id=individual_tenant_id,
                    source=lot_source,
                    credit_amount=Decimal(str(credits_to_allocate)),
                    valid_from=now_iso,
                    expires_at=None,
                    metadata={
                        "source": "organization_join",
                        "organization_id": tenant_id,
                    },
                    original_tenant_id=tenant_id,
                )

                # Record allocation for billing
                try:
                    await (
                        client.table("organization_credit_allocations")
                        .insert(
                            {
                                "tenant_id": tenant_id,
                                "allocation_type": "allocation_to_member",
                                "credit_amount": float(credits_to_allocate),
                                "credit_lot_id": created_lot.get("id")
                                if created_lot
                                else None,
                                "allocated_to_tenant_id": individual_tenant_id,
                                "allocated_to_user_id": user_id,
                                "allocated_by_user_id": None,
                                "allocated_at": now_iso,
                                "metadata": {"source": "organization_join"},
                            }
                        )
                        .execute()
                    )
                except Exception as e:
                    if created_lot and created_lot.get("id"):
                        await (
                            client.table("credit_lots")
                            .delete()
                            .eq("id", created_lot["id"])
                            .execute()
                        )
                    logger.error(
                        f"Failed to record postpay join allocation: {e}", exc_info=True
                    )
                    raise HTTPException(
                        status_code=500, detail=f"Failed to record allocation: {str(e)}"
                    )
            else:
                # Grant/prepay: claim from reserved lots
                if invitation:
                    await self.credit_service.claim_reserved_credits(
                        invitation_id=invitation["id"],
                        target_tenant_id=individual_tenant_id,
                        source=lot_source,
                        expires_at=None,
                        metadata={
                            "source": "organization_join",
                            "organization_id": tenant_id,
                        },
                        original_tenant_id=tenant_id,
                    )
                    logger.info(
                        f"Claimed reserved credits for user {user_id} "
                        f"from invitation {invitation['id']}"
                    )

        elif credits_to_allocate > 0 and is_team_leader and invitation:
            # Team leader: deduct reserved credits and store in pending_team_credits
            lot_source = "grant" if org_type == "grant_org" else "purchase"
            expires_at = None

            if is_postpay:
                # Postpay: Record allocation and pending_team_credits in parallel
                try:
                    await asyncio.gather(
                        client.table("organization_credit_allocations")
                        .insert(
                            {
                                "tenant_id": tenant_id,
                                "allocation_type": "allocation_to_member",  # Team leader joins as member first
                                "credit_amount": float(credits_to_allocate),
                                "credit_lot_id": None,  # Lot created when team is created
                                "allocated_to_tenant_id": None,  # Team not yet created
                                "allocated_to_user_id": user_id,
                                "allocated_by_user_id": None,
                                "allocated_at": now_iso,
                                "metadata": {
                                    "source": "organization_join",
                                    "invitation_id": invitation["id"],
                                    "is_team_leader": True,  # Track that this is for a team leader
                                },
                            }
                        )
                        .execute(),
                        client.table("pending_team_credits")
                        .insert(
                            {
                                "organization_id": tenant_id,
                                "admin_email": user_email,
                                "credit_amount": float(credits_to_allocate),
                                "source": lot_source,
                                "expires_at": expires_at,
                                "metadata": {
                                    "invitation_id": invitation["id"],
                                    "org_type": org_type,
                                    "cohort_id": cohort_id,
                                },
                            }
                        )
                        .execute(),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to record postpay team leader allocation: {e}",
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500, detail=f"Failed to record allocation: {str(e)}"
                    )
            else:
                # Non-postpay: Deduct from reserved lots and get expiry info
                deduction_result = await self.credit_service.deduct_reserved_credits(
                    invitation_id=invitation["id"],
                )
                # For grant_org, preserve the expiry date from the original lot
                if org_type == "grant_org":
                    expires_at = deduction_result.get("expires_at")
                    lot_source = deduction_result.get("source", "grant")

                # Record in pending_team_credits for later team creation
                await (
                    client.table("pending_team_credits")
                    .insert(
                        {
                            "organization_id": tenant_id,
                            "admin_email": user_email,
                            "credit_amount": float(credits_to_allocate),
                            "source": lot_source,
                            "expires_at": expires_at,
                            "metadata": {
                                "invitation_id": invitation["id"],
                                "org_type": org_type,
                                "cohort_id": cohort_id,
                            },
                        }
                    )
                    .execute()
                )

            logger.info(
                f"Stored {credits_to_allocate} credits in pending_team_credits "
                f"for team leader {user_email} (org: {tenant_id})"
            )

        # Phase 4: Accept invitation if exists
        if invitation:
            await self.accept_matching_invites(
                org_id=tenant_id,
                email=user_email,
                role=role,
                user_id=user_id,
                membership_id=str(membership_id) if membership_id else "",
            )

        return {
            "success": True,
            "message": f"Successfully joined organization as {role}",
            "data": {
                "membership_id": membership_id,
                "individual_tenant_id": individual_tenant_id,
                "role": role,
            },
            "is_team_leader": is_team_leader,
        }

    # =========================================================================
    # Credit Allocation (Async)
    # =========================================================================

    async def allocate_from_org_to_user(
        self,
        organization_id: str,
        user_tenant_id: str,
        amount: float,
        valid_from: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Allocate credits from organization to a user tenant.

        For postpay orgs: Records allocation for later invoicing (no deduction).
        For grant/prepay orgs: Checks balance and deducts from org lots.

        Credit source is determined by org type:
        - grant_org -> "grant"
        - prepay_org/postpay_org -> "purchase"
        """
        client = await get_async_supabase_client()
        now_iso = valid_from or datetime.now(timezone.utc).isoformat()

        # Get org billing config to determine if postpay
        billing_config = await self.get_org_billing_config(organization_id)
        org_type = billing_config.get("organization_type", "grant_org")
        is_postpay = org_type == "postpay_org"

        from decimal import Decimal

        if is_postpay:
            # Postpay org: Create credit lot without deducting from org
            lot_metadata = metadata or {}
            lot_metadata.update(
                {
                    "source": "organization_allocation",
                    "organization_id": organization_id,
                }
            )

            created_lot = await self.credit_service.create_credit_lot(
                tenant_id=user_tenant_id,
                source="purchase",  # Use "purchase" like team service
                credit_amount=Decimal(str(amount)),
                valid_from=now_iso,
                expires_at=None,  # No expiry for postpay
                metadata=lot_metadata,
                original_tenant_id=organization_id,
            )

            # Record allocation for billing - if this fails, rollback the credit lot
            try:
                await (
                    client.table("organization_credit_allocations")
                    .insert(
                        {
                            "tenant_id": organization_id,
                            "allocation_type": "allocation_to_member",
                            "credit_amount": float(amount),
                            "credit_lot_id": created_lot.get("id")
                            if created_lot
                            else None,
                            "allocated_to_tenant_id": user_tenant_id,
                            "allocated_to_user_id": None,
                            "allocated_by_user_id": None,
                            "allocated_at": now_iso,
                            "metadata": lot_metadata,
                        }
                    )
                    .execute()
                )
                logger.info(
                    f"Recorded postpay allocation for org {organization_id}: "
                    f"{amount} credits to tenant {user_tenant_id}"
                )
            except Exception as e:
                # Rollback: delete the credit lot we just created
                if created_lot and created_lot.get("id"):
                    await (
                        client.table("credit_lots")
                        .delete()
                        .eq("id", created_lot["id"])
                        .execute()
                    )
                logger.error(f"Failed to record postpay allocation: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to record allocation for billing: {str(e)}",
                )

            return {
                "success": True,
                "message": f"Allocated {amount} credits (postpay - will be invoiced)",
                "lot": created_lot,
                "billing_type": "postpay",
            }
        else:
            # Grant/prepay org: Check unreserved credits and deduct from org lots
            # Use unreserved credits to exclude credits reserved for pending invitations
            available = await self.credit_service.get_unreserved_available_credits(
                organization_id
            )
            if available < amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient credits. Available: {available}, Requested: {amount}",
                )

            # Deduct from org's credit lots (excludes reserved lots)
            remaining = await self._deduct_from_org_lots(
                client, organization_id, amount, now_iso
            )
            if remaining > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to deduct full amount. Remaining: {remaining}",
                )

            # Create lot for user - source based on org type
            lot_source = "grant" if org_type == "grant_org" else "purchase"
            lot_metadata = metadata or {}
            lot_metadata.update(
                {
                    "source": "organization_allocation",
                    "organization_id": organization_id,
                }
            )

            lot = await self.credit_service.create_credit_lot(
                tenant_id=user_tenant_id,
                source=lot_source,
                credit_amount=Decimal(str(amount)),
                valid_from=now_iso,
                expires_at=expires_at,
                metadata=lot_metadata,
                original_tenant_id=organization_id,
            )

            return {
                "success": True,
                "message": f"Allocated {amount} credits",
                "lot": lot,
                "billing_type": org_type,
            }

    async def suspend_user_lot_back_to_org(
        self,
        org_tenant_id: str,
        lot_id: str,
        return_source: str = "org_suspend_return",
    ) -> Dict[str, Any]:
        """
        Return a user's credit lot back to the org and delete the user's lot.
        If an org lot already exists with the same (original_tenant_id, tenant_id),
        add the credits to that lot instead of creating a new one.
        """
        client = await get_async_supabase_client()

        # Fetch the lot
        lot_res = await (
            client.table("credit_lots").select("*").eq("id", lot_id).limit(1).execute()
        )
        lot = lot_res.data[0] if lot_res.data else None
        if not lot:
            raise HTTPException(status_code=404, detail="lot_not_found")

        if lot.get("original_tenant_id") != org_tenant_id:
            raise HTTPException(
                status_code=403, detail="forbidden: lot not issued by this org"
            )

        amount = Decimal(str(lot.get("credit_amount", 0)))
        returned_lot = None

        if amount > 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            # Try to find an existing ACTIVE org lot with the same (original_tenant_id, tenant_id)
            existing_res = await (
                client.table("credit_lots")
                .select("id, credit_amount, expires_at")
                .eq("tenant_id", org_tenant_id)
                .eq("original_tenant_id", org_tenant_id)
                .eq("is_active", True)
                .lte("valid_from", now_iso)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            existing = existing_res.data[0] if existing_res.data else None

            if existing:
                # Add to existing lot
                new_amount = Decimal(str(existing["credit_amount"] or 0)) + amount
                update_res = await (
                    client.table("credit_lots")
                    .update({"credit_amount": float(new_amount)})
                    .eq("id", existing["id"])
                    .select("*")
                    .limit(1)
                    .execute()
                )
                returned_lot = update_res.data[0] if update_res.data else None
            else:
                # Create a new org lot
                return_payload = {
                    "tenant_id": org_tenant_id,
                    "original_tenant_id": org_tenant_id,
                    "source": return_source,
                    "credit_amount": float(amount),
                    "valid_from": lot.get("valid_from") or now_iso,
                    "expires_at": lot.get("expires_at"),
                    "metadata": {
                        "suspended_from_lot_id": lot_id,
                        "suspended_from_tenant_id": lot.get("tenant_id"),
                    },
                    "created_at": now_iso,
                    "is_active": True,
                }
                insert_res = await (
                    client.table("credit_lots")
                    .insert(return_payload)
                    .select("*")
                    .limit(1)
                    .execute()
                )
                returned_lot = insert_res.data[0] if insert_res.data else None

        # Delete the user lot
        await client.table("credit_lots").delete().eq("id", lot_id).execute()

        return {
            "deleted_lot_id": lot_id,
            "returned_org_lot": returned_lot,
        }

    async def freeze_lot(
        self,
        lot_id: str,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set is_active = false on a lot.
        If organization_id is provided, validate that the lot was issued by the org.
        """
        client = await get_async_supabase_client()

        # Optionally validate ownership
        if organization_id:
            lot_res = await (
                client.table("credit_lots")
                .select("id, original_tenant_id")
                .eq("id", lot_id)
                .limit(1)
                .execute()
            )
            lot = lot_res.data[0] if lot_res.data else None
            if not lot:
                raise HTTPException(status_code=404, detail="lot_not_found")
            if lot.get("original_tenant_id") != organization_id:
                raise HTTPException(
                    status_code=403, detail="forbidden: lot not issued by this org"
                )

        res = await (
            client.table("credit_lots")
            .update({"is_active": False})
            .eq("id", lot_id)
            .select("*")
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    # =========================================================================
    # Credit Request Methods (Async)
    # =========================================================================

    async def create_credit_request(
        self,
        user_id: str,
        organization_id: str,
        requested_amount: int,
        reason: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a credit request asynchronously."""
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check for existing pending request
        existing = await (
            client.table("credit_requests")
            .select("id")
            .eq("organization_id", organization_id)
            .eq("user_id", user_id)
            .eq("status", "pending")
            .limit(1)
            .execute()
        )

        if existing.data:
            raise HTTPException(
                status_code=400, detail="You already have a pending credit request"
            )

        payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "requested_amount": requested_amount,
            "reason": reason,
            "team_id": team_id,
            "status": "pending",
            "created_at": now_iso,
        }

        result = await client.table("credit_requests").insert(payload).execute()

        if not result.data:
            raise HTTPException(
                status_code=500, detail="Failed to create credit request"
            )

        return result.data[0]

    async def get_credit_requests_for_org(
        self,
        organization_id: str,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get credit requests for organization with parallel user profile lookup."""
        client = await get_async_supabase_client()

        query = (
            client.table("credit_requests")
            .select("*")
            .eq("organization_id", organization_id)
            .order("created_at", desc=True)
        )

        if status_filter:
            query = query.eq("status", status_filter)

        result = await query.execute()
        requests = result.data or []

        # Get user profiles in parallel
        user_ids = list({r["user_id"] for r in requests})
        if user_ids:
            profiles_result = await (
                client.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", user_ids)
                .execute()
            )
            profiles = {p["id"]: p for p in (profiles_result.data or [])}

            for req in requests:
                profile = profiles.get(req["user_id"], {})
                req["user_name"] = (
                    profile.get("full_name") or profile.get("email") or req["user_id"]
                )
                req["user_email"] = profile.get("email")

        pending_count = sum(1 for r in requests if r.get("status") == "pending")

        return {
            "requests": requests,
            "total_count": len(requests),
            "pending_count": pending_count,
        }

    async def update_credit_request(
        self,
        request_id: str,
        reviewer_id: str,
        new_status: str,
        review_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update credit request status with optional credit allocation."""
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Get request details
        request_result = await (
            client.table("credit_requests")
            .select("*")
            .eq("id", request_id)
            .limit(1)
            .execute()
        )

        if not request_result.data:
            raise HTTPException(status_code=404, detail="Credit request not found")

        request_data = request_result.data[0]

        if request_data.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Request is not pending")

        # Update request status
        update_payload = {
            "status": new_status,
            "reviewed_by": reviewer_id,
            "reviewed_at": now_iso,
            "review_notes": review_notes,
        }

        await (
            client.table("credit_requests")
            .update(update_payload)
            .eq("id", request_id)
            .execute()
        )

        # If approved, allocate credits
        if new_status == "approved":
            org_id = request_data["organization_id"]
            user_id = request_data["user_id"]
            amount = request_data["requested_amount"]

            # Get user's individual tenant
            individual = await (
                client.table("org_individuals")
                .select("individual_tenant_id")
                .eq("organization_id", org_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

            if individual.data:
                try:
                    await self.allocate_credits_to_member(
                        org_id=org_id,
                        user_id=user_id,
                        amount=amount,
                        allocated_by_user_id=reviewer_id,
                    )
                    # Mark as fulfilled
                    await (
                        client.table("credit_requests")
                        .update({"status": "fulfilled"})
                        .eq("id", request_id)
                        .execute()
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to allocate credits for approved request: {e}"
                    )

        return {**request_data, **update_payload}

    async def get_user_credit_requests(
        self,
        user_id: str,
        organization_id: str,
    ) -> List[Dict[str, Any]]:
        """Get credit requests for a specific user."""
        client = await get_async_supabase_client()

        result = await (
            client.table("credit_requests")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    # =========================================================================
    # Super Admin Methods (Async with Parallel Queries)
    # =========================================================================

    async def list_organizations_for_admin(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        size: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        List all organizations with parallel batch queries for metrics.
        """
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build base query
        query = (
            client.table("tenants")
            .select("*", count="exact")
            .eq("tenant_type", "organization")
        )

        if search:
            query = query.ilike("name", f"%{search}%")
        if industry:
            query = query.eq("industry", industry)
        if country:
            query = query.eq("country", country)
        if size:
            query = query.eq("size", size)
        if is_active is not None:
            query = query.eq("is_active", is_active)

        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(
            offset, offset + page_size - 1
        )

        result = await query.execute()

        if not result.data:
            return {
                "organizations": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_next": False,
            }

        org_ids = [org["id"] for org in result.data]

        # Parallel batch queries for all metrics
        tasks = [
            # Members count
            client.table("tenant_memberships")
            .select("tenant_id")
            .in_("tenant_id", org_ids)
            .eq("is_active", True)
            .execute(),
            # Teams count
            client.table("org_teams")
            .select("organization_id")
            .in_("organization_id", org_ids)
            .execute(),
            # Credit lots (active, non-expired)
            client.table("credit_lots")
            .select("tenant_id, credit_amount")
            .in_("tenant_id", org_ids)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            .execute(),
            # Credit consumptions
            client.table("tenant_credit_consumptions")
            .select("tenant_id, cost")
            .in_("tenant_id", org_ids)
            .execute(),
        ]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        def safe_data(r):
            if isinstance(r, Exception):
                return []
            return r.data or []

        members_data = safe_data(batch_results[0])
        teams_data = safe_data(batch_results[1])
        credits_data = safe_data(batch_results[2])
        consumption_data = safe_data(batch_results[3])

        # Build lookup maps
        member_counts = {}
        for m in members_data:
            tid = m["tenant_id"]
            member_counts[tid] = member_counts.get(tid, 0) + 1

        team_counts = {}
        for t in teams_data:
            oid = t["organization_id"]
            team_counts[oid] = team_counts.get(oid, 0) + 1

        credit_totals = {}
        for c in credits_data:
            tid = c["tenant_id"]
            credit_totals[tid] = credit_totals.get(tid, 0) + float(
                c.get("credit_amount", 0)
            )

        credit_used = {}
        for c in consumption_data:
            tid = c["tenant_id"]
            credit_used[tid] = credit_used.get(tid, 0) + float(c.get("cost", 0))

        # Build response
        organizations = []
        for org in result.data:
            oid = org["id"]
            organizations.append(
                {
                    "id": oid,
                    "name": org["name"],
                    "description": org.get("description"),
                    "industry": org.get("industry"),
                    "country": org.get("country"),
                    "city": org.get("city"),
                    "contact_email": org.get("contact_email"),
                    "phone_number": org.get("phone_number"),
                    "website": org.get("website"),
                    "size": org.get("size"),
                    "is_active": org["is_active"],
                    "created_at": org["created_at"],
                    "updated_at": org["updated_at"],
                    "total_members": member_counts.get(oid, 0),
                    "total_teams": team_counts.get(oid, 0),
                    "total_credits": credit_totals.get(oid, 0),
                    "used_credits": credit_used.get(oid, 0),
                    "last_activity": None,
                }
            )

        total = result.count or 0
        has_next = (page * page_size) < total

        return {
            "organizations": organizations,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
        }

    async def get_organizations_summary(self) -> Dict[str, Any]:
        """
        Get organization summary statistics with parallel queries.
        """
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Get all organizations in one query
        orgs_result = await (
            client.table("tenants")
            .select("id, industry, size, country, is_active")
            .eq("tenant_type", "organization")
            .execute()
        )

        all_orgs = orgs_result.data or []
        org_ids = [o["id"] for o in all_orgs]

        if not org_ids:
            return {
                "total_organizations": 0,
                "active_organizations": 0,
                "inactive_organizations": 0,
                "total_members": 0,
                "total_teams": 0,
                "total_credits_allocated": 0,
                "total_credits_used": 0,
                "organizations_by_industry": {},
                "organizations_by_size": {},
                "organizations_by_country": {},
            }

        # Parallel queries for all metrics
        tasks = [
            client.table("tenant_memberships")
            .select("id", count="exact")
            .in_("tenant_id", org_ids)
            .eq("is_active", True)
            .execute(),
            client.table("org_teams")
            .select("team_id", count="exact")
            .in_("organization_id", org_ids)
            .execute(),
            client.table("credit_lots")
            .select("credit_amount")
            .in_("tenant_id", org_ids)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            .execute(),
            client.table("tenant_credit_consumptions")
            .select("cost")
            .in_("tenant_id", org_ids)
            .execute(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        def safe_count(r):
            if isinstance(r, Exception):
                return 0
            return r.count if hasattr(r, "count") and r.count else 0

        def safe_data(r):
            if isinstance(r, Exception):
                return []
            return r.data or []

        total_members = safe_count(results[0])
        total_teams = safe_count(results[1])

        total_credits = sum(
            float(c.get("credit_amount", 0)) for c in safe_data(results[2])
        )
        total_used = sum(float(c.get("cost", 0)) for c in safe_data(results[3]))

        # Calculate breakdowns
        by_industry = {}
        by_size = {}
        by_country = {}
        active_count = 0

        for org in all_orgs:
            if org.get("is_active", True):
                active_count += 1

            ind = org.get("industry") or "Unknown"
            by_industry[ind] = by_industry.get(ind, 0) + 1

            sz = org.get("size") or "Unknown"
            by_size[sz] = by_size.get(sz, 0) + 1

            ctr = org.get("country") or "Unknown"
            by_country[ctr] = by_country.get(ctr, 0) + 1

        return {
            "total_organizations": len(all_orgs),
            "active_organizations": active_count,
            "inactive_organizations": len(all_orgs) - active_count,
            "total_members": total_members,
            "total_teams": total_teams,
            "total_credits_allocated": int(total_credits),
            "total_credits_used": int(total_used),
            "organizations_by_industry": by_industry,
            "organizations_by_size": by_size,
            "organizations_by_country": by_country,
        }

    # =========================================================================
    # Project Management Methods (Async)
    # =========================================================================

    async def validate_tenant_belongs_to_org(
        self,
        organization_id: str,
        tenant_id: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify tenant belongs to the organization (async).

        Args:
            organization_id: Organization ID
            tenant_id: Tenant ID to validate

        Returns:
            (is_valid, tenant_info_dict)
        """
        client = await get_async_supabase_client()

        try:
            # Check in org_individuals and org_teams in parallel
            individual_task = (
                client.table("org_individuals")
                .select("user_id, individual_tenant_id")
                .eq("organization_id", organization_id)
                .eq("individual_tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            team_task = (
                client.table("org_teams")
                .select("team_id")
                .eq("organization_id", organization_id)
                .eq("team_id", tenant_id)
                .limit(1)
                .execute()
            )
            tenant_task = (
                client.table("tenants")
                .select("id, name, tenant_type")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )

            individual_result, team_result, tenant_result = await asyncio.gather(
                individual_task, team_task, tenant_task
            )

            tenant_info = tenant_result.data[0] if tenant_result.data else {}

            if individual_result.data:
                data = individual_result.data[0]
                return True, {
                    "tenant_id": tenant_id,
                    "tenant_type": "individual",
                    "tenant_name": tenant_info.get("name", ""),
                    "user_id": data.get("user_id"),
                }

            if team_result.data:
                return True, {
                    "tenant_id": tenant_id,
                    "tenant_type": "team",
                    "tenant_name": tenant_info.get("name", ""),
                }

            return False, None

        except Exception as e:
            logger.error(f"Error validating tenant: {e}")
            return False, None

    async def validate_project_belongs_to_org(
        self,
        organization_id: str,
        project_id: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify project belongs to an org member (async).

        Args:
            organization_id: Organization ID
            project_id: Project ID to validate

        Returns:
            (is_valid, project_owner_info_dict)
        """
        client = await get_async_supabase_client()

        try:
            # Get project tenant_id and user_id
            project_result = await (
                client.table("vmp_projects")
                .select("tenant_id, user_id")
                .eq("id", project_id)
                .limit(1)
                .execute()
            )

            if not project_result.data:
                return False, None

            project = project_result.data[0]
            tenant_id = project["tenant_id"]
            user_id = project["user_id"]

            # Validate tenant belongs to org
            is_valid, tenant_info = await self.validate_tenant_belongs_to_org(
                organization_id, tenant_id
            )

            if is_valid:
                # Get user info
                user_result = await (
                    client.table("user_profiles")
                    .select("email, full_name")
                    .eq("id", user_id)
                    .limit(1)
                    .execute()
                )

                user_info = user_result.data[0] if user_result.data else {}

                return True, {
                    "user_id": user_id,
                    "user_email": user_info.get("email"),
                    "user_name": user_info.get("full_name"),
                    "tenant_id": tenant_id,
                    "member_type": tenant_info.get("tenant_type")
                    if tenant_info
                    else None,
                }

            return False, None

        except Exception as e:
            logger.error(f"Error validating project: {e}")
            return False, None

    async def log_project_access(
        self,
        organization_id: str,
        accessed_by_user_id: str,
        target_user_id: str,
        project_id: str,
        access_type: str = "view",
    ) -> None:
        """
        Log project access for audit trail (async, non-blocking).

        Args:
            organization_id: Organization ID
            accessed_by_user_id: User who accessed the project
            target_user_id: User whose project was accessed
            project_id: Project ID
            access_type: Type of access (view, edit, export)
        """
        try:
            client = await get_async_supabase_client()

            await (
                client.table("project_access_logs")
                .insert(
                    {
                        "organization_id": organization_id,
                        "accessed_by_user_id": accessed_by_user_id,
                        "target_user_id": target_user_id,
                        "project_id": project_id,
                        "access_type": access_type,
                        "metadata": {},
                    }
                )
                .execute()
            )

            logger.info(
                f"Logged access: {accessed_by_user_id} accessed project {project_id} "
                f"of user {target_user_id} in org {organization_id}"
            )

        except Exception as e:
            logger.error(f"Failed to log project access: {e}")
            # Don't raise - logging failure shouldn't block the request

    async def get_organization_member_projects(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        member_type: str = "all",
    ) -> Dict[str, Any]:
        """
        Get all organization members with their project summaries (async).

        OPTIMIZED: Uses parallel queries for batch data fetching.

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
        client = await get_async_supabase_client()
        members = []

        try:
            # Phase 1: Fetch individuals and teams in parallel (if needed)
            individual_task = None
            team_task = None

            if member_type in ["individual", "all"]:
                individual_task = (
                    client.table("org_individuals")
                    .select("user_id, individual_tenant_id")
                    .eq("organization_id", organization_id)
                    .execute()
                )

            if member_type in ["team", "all"]:
                team_task = (
                    client.table("org_teams")
                    .select("team_id")
                    .eq("organization_id", organization_id)
                    .execute()
                )

            tasks = [t for t in [individual_task, team_task] if t is not None]
            if not tasks:
                return {
                    "members": [],
                    "total_count": 0,
                    "page": page,
                    "page_size": page_size,
                    "has_next": False,
                }

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Parse results based on what was requested
            individual_data = []
            team_data = []
            result_idx = 0

            if member_type in ["individual", "all"]:
                res = results[result_idx]
                if not isinstance(res, Exception):
                    individual_data = res.data or []
                result_idx += 1

            if member_type in ["team", "all"]:
                res = results[result_idx]
                if not isinstance(res, Exception):
                    team_data = res.data or []

            # Phase 2: Gather all needed IDs for batch queries
            individual_user_ids = [m["user_id"] for m in individual_data]
            individual_tenant_ids = [m["individual_tenant_id"] for m in individual_data]
            team_ids = [t["team_id"] for t in team_data]
            all_tenant_ids = individual_tenant_ids + team_ids

            if not all_tenant_ids:
                return {
                    "members": [],
                    "total_count": 0,
                    "page": page,
                    "page_size": page_size,
                    "has_next": False,
                }

            # Phase 3: Batch queries for all data
            batch_tasks = []
            task_names = []

            # User profiles for individuals
            if individual_user_ids:
                batch_tasks.append(
                    client.table("user_profiles")
                    .select("id, email, full_name")
                    .in_("id", individual_user_ids)
                    .execute()
                )
                task_names.append("user_profiles")

            # Tenant info for teams
            if team_ids:
                batch_tasks.append(
                    client.table("tenants")
                    .select("id, name, contact_email")
                    .in_("id", team_ids)
                    .execute()
                )
                task_names.append("team_tenants")

            # Project counts for all tenants (single query)
            batch_tasks.append(
                client.table("vmp_projects")
                .select("tenant_id")
                .in_("tenant_id", all_tenant_ids)
                .execute()
            )
            task_names.append("projects")

            # Recent projects for all tenants (limit to most recent)
            batch_tasks.append(
                client.table("vmp_projects")
                .select(
                    "id, name, description, current_step, created_at, updated_at, tenant_id"
                )
                .in_("tenant_id", all_tenant_ids)
                .order("updated_at", desc=True)
                .limit(len(all_tenant_ids) * 2)  # Get a few recent ones
                .execute()
            )
            task_names.append("recent_projects")

            # PV report counts for individuals (by created_by/user_id)
            if individual_user_ids:
                batch_tasks.append(
                    client.table("documents")
                    .select("created_by")
                    .in_("created_by", individual_user_ids)
                    .eq("source_type", "pv_report")
                    .execute()
                )
                task_names.append("individual_pv_reports")

            # Team memberships for PV report counting
            if team_ids:
                batch_tasks.append(
                    client.table("tenant_memberships")
                    .select("user_id, tenant_id")
                    .in_("tenant_id", team_ids)
                    .eq("is_active", True)
                    .execute()
                )
                task_names.append("team_memberships")

            # Team admins for contact info
            if team_ids:
                batch_tasks.append(
                    client.table("tenant_memberships")
                    .select("user_id, tenant_id, role")
                    .in_("tenant_id", team_ids)
                    .in_("role", ["owner", "admin"])
                    .eq("is_active", True)
                    .execute()
                )
                task_names.append("team_admins")

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results
            def get_data(r):
                return (
                    r.data
                    if not isinstance(r, Exception) and hasattr(r, "data")
                    else []
                )

            result_map = {}
            for i, name in enumerate(task_names):
                result_map[name] = get_data(batch_results[i])

            # Build lookup maps
            user_profiles = {p["id"]: p for p in result_map.get("user_profiles", [])}
            team_tenants = {t["id"]: t for t in result_map.get("team_tenants", [])}

            # Count projects by tenant
            project_count_by_tenant: Dict[str, int] = {}
            for p in result_map.get("projects", []):
                tid = p["tenant_id"]
                project_count_by_tenant[tid] = project_count_by_tenant.get(tid, 0) + 1

            # Recent projects by tenant (get first one per tenant)
            recent_project_by_tenant: Dict[str, Dict] = {}
            for p in result_map.get("recent_projects", []):
                tid = p["tenant_id"]
                if tid not in recent_project_by_tenant:
                    recent_project_by_tenant[tid] = p

            # Count PV reports for individuals
            pv_report_count_by_user: Dict[str, int] = {}
            for d in result_map.get("individual_pv_reports", []):
                uid = d["created_by"]
                pv_report_count_by_user[uid] = pv_report_count_by_user.get(uid, 0) + 1

            # Team member users (for PV report counting)
            team_member_users: Dict[str, List[str]] = {}
            for m in result_map.get("team_memberships", []):
                tid = m["tenant_id"]
                if tid not in team_member_users:
                    team_member_users[tid] = []
                team_member_users[tid].append(m["user_id"])

            # Team admins
            team_admin_users: Dict[str, List[str]] = {}
            for m in result_map.get("team_admins", []):
                tid = m["tenant_id"]
                if tid not in team_admin_users:
                    team_admin_users[tid] = []
                team_admin_users[tid].append(m["user_id"])

            # Additional query for team admin emails if needed
            all_admin_user_ids = list(
                set(uid for uids in team_admin_users.values() for uid in uids)
            )
            admin_profiles: Dict[str, Dict] = {}
            if all_admin_user_ids:
                admin_result = await (
                    client.table("user_profiles")
                    .select("id, email")
                    .in_("id", all_admin_user_ids)
                    .execute()
                )
                admin_profiles = {p["id"]: p for p in (admin_result.data or [])}

            # For teams: query PV reports by all team member user_ids
            all_team_member_ids = list(
                set(uid for uids in team_member_users.values() for uid in uids)
            )
            team_pv_counts: Dict[str, int] = {}
            if all_team_member_ids:
                team_pv_result = await (
                    client.table("documents")
                    .select("created_by")
                    .in_("created_by", all_team_member_ids)
                    .eq("source_type", "pv_report")
                    .execute()
                )
                pv_by_user: Dict[str, int] = {}
                for d in team_pv_result.data or []:
                    uid = d["created_by"]
                    pv_by_user[uid] = pv_by_user.get(uid, 0) + 1

                # Sum per team
                for tid, user_ids in team_member_users.items():
                    team_pv_counts[tid] = sum(
                        pv_by_user.get(uid, 0) for uid in user_ids
                    )

            # Build individual members
            for m in individual_data:
                user_id = m["user_id"]
                tenant_id = m["individual_tenant_id"]
                profile = user_profiles.get(user_id, {})

                recent_proj = recent_project_by_tenant.get(tenant_id)
                projects = [recent_proj] if recent_proj else []

                members.append(
                    {
                        "user_id": user_id,
                        "user_email": profile.get("email"),
                        "user_name": profile.get("full_name"),
                        "member_type": "individual",
                        "tenant_id": tenant_id,
                        "project_count": project_count_by_tenant.get(tenant_id, 0),
                        "pv_report_count": pv_report_count_by_user.get(user_id, 0),
                        "projects": projects,
                    }
                )

            # Build team members
            for t in team_data:
                team_id = t["team_id"]
                tenant = team_tenants.get(team_id, {})

                admin_user_ids = team_admin_users.get(team_id, [])
                team_admin_emails = [
                    admin_profiles.get(uid, {}).get("email")
                    for uid in admin_user_ids
                    if admin_profiles.get(uid, {}).get("email")
                ]

                recent_proj = recent_project_by_tenant.get(team_id)
                projects = [recent_proj] if recent_proj else []

                team_name = tenant.get("name", "")
                first_admin_email = team_admin_emails[0] if team_admin_emails else None

                members.append(
                    {
                        "user_id": team_id,  # Use tenant_id for consistency
                        "user_email": first_admin_email,
                        "user_name": team_name,
                        "team_name": team_name,
                        "team_contact_email": tenant.get("contact_email"),
                        "team_admin_emails": team_admin_emails
                        if team_admin_emails
                        else None,
                        "member_type": "team",
                        "tenant_id": team_id,
                        "project_count": project_count_by_tenant.get(team_id, 0),
                        "pv_report_count": team_pv_counts.get(team_id, 0),
                        "projects": projects,
                    }
                )

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
                "has_next": has_next,
            }

        except Exception as e:
            logger.error(f"Error getting organization member projects: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get member projects: {str(e)}"
            )

    async def get_tenant_projects(
        self,
        organization_id: str,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Get all projects for a specific tenant (async).

        OPTIMIZED: Uses parallel queries.

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
        client = await get_async_supabase_client()

        try:
            # Validate tenant belongs to org
            is_valid, tenant_info = await self.validate_tenant_belongs_to_org(
                organization_id, tenant_id
            )

            if not is_valid:
                raise HTTPException(
                    status_code=404, detail="Tenant not found in this organization"
                )

            # Parallel queries for tenant details, count, and projects
            offset = (page - 1) * page_size

            tasks = [
                # Tenant details
                client.table("tenants")
                .select("id, name, tenant_type, contact_email")
                .eq("id", tenant_id)
                .limit(1)
                .execute(),
                # Project count
                client.table("vmp_projects")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .execute(),
                # Paginated projects
                client.table("vmp_projects")
                .select("id, name, description, current_step, created_at, updated_at")
                .eq("tenant_id", tenant_id)
                .order("updated_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute(),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            def get_data(r):
                return (
                    r.data
                    if not isinstance(r, Exception) and hasattr(r, "data")
                    else []
                )

            def get_count(r):
                if isinstance(r, Exception):
                    return 0
                return (
                    r.count
                    if hasattr(r, "count") and r.count is not None
                    else len(r.data or [])
                )

            tenant_data = get_data(results[0])
            total_count = get_count(results[1])
            projects = get_data(results[2])

            if not tenant_data:
                raise HTTPException(status_code=404, detail="Tenant not found")

            tenant = tenant_data[0]

            # Build member info
            member_info = {
                "tenant_id": tenant_id,
                "tenant_type": tenant["tenant_type"],
                "tenant_name": tenant["name"],
            }

            # Add user or team specific info
            if (
                tenant["tenant_type"] == "individual"
                and tenant_info
                and tenant_info.get("user_id")
            ):
                user_result = await (
                    client.table("user_profiles")
                    .select("id, email, full_name")
                    .eq("id", tenant_info["user_id"])
                    .limit(1)
                    .execute()
                )
                if user_result.data:
                    user = user_result.data[0]
                    member_info.update(
                        {
                            "user_id": user["id"],
                            "user_email": user["email"],
                            "user_name": user["full_name"],
                        }
                    )
            elif tenant["tenant_type"] == "team":
                # Get team admins
                admins_result = await (
                    client.table("tenant_memberships")
                    .select("user_id")
                    .eq("tenant_id", tenant_id)
                    .in_("role", ["owner", "admin"])
                    .eq("is_active", True)
                    .execute()
                )
                admin_ids = [a["user_id"] for a in (admins_result.data or [])]

                team_admin_emails = []
                if admin_ids:
                    profiles_result = await (
                        client.table("user_profiles")
                        .select("id, email")
                        .in_("id", admin_ids)
                        .execute()
                    )
                    team_admin_emails = [
                        p["email"]
                        for p in (profiles_result.data or [])
                        if p.get("email")
                    ]

                team_name = tenant["name"]
                first_admin_email = team_admin_emails[0] if team_admin_emails else None

                member_info.update(
                    {
                        "user_id": tenant_id,
                        "user_email": first_admin_email,
                        "user_name": team_name,
                        "team_id": tenant_id,
                        "team_name": team_name,
                        "team_contact_email": tenant.get("contact_email"),
                        "team_admin_emails": team_admin_emails
                        if team_admin_emails
                        else None,
                    }
                )

            has_next = (offset + page_size) < total_count

            return {
                "member": member_info,
                "projects": projects,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting tenant projects: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get tenant projects: {str(e)}"
            )

    async def get_member_project_detail(
        self,
        organization_id: str,
        project_id: str,
        accessed_by_user_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed project data including all generated artifacts (async).

        OPTIMIZED: Uses parallel queries and non-blocking access logging.

        Args:
            organization_id: Organization ID
            project_id: Project ID
            accessed_by_user_id: User ID accessing the project

        Returns:
            Complete project data with PV report and access log
        """
        client = await get_async_supabase_client()
        import json

        try:
            # Validate project belongs to org
            is_valid, owner_info = await self.validate_project_belongs_to_org(
                organization_id, project_id
            )

            if not is_valid:
                raise HTTPException(
                    status_code=404, detail="Project not found in this organization"
                )

            # Get complete project data
            project_result = await (
                client.table("vmp_projects")
                .select("*")
                .eq("id", project_id)
                .limit(1)
                .execute()
            )

            if not project_result.data:
                raise HTTPException(status_code=404, detail="Project not found")

            project = project_result.data[0]

            # Get PV Report if linked (async)
            pv_report = None
            if project.get("pv_report_id"):
                pv_result = await (
                    client.table("documents")
                    .select("id, title, content")
                    .eq("id", project["pv_report_id"])
                    .limit(1)
                    .execute()
                )

                if pv_result.data:
                    pv_report = pv_result.data[0]
                    # Parse content if it's a JSON string
                    if pv_report.get("content") and isinstance(
                        pv_report["content"], str
                    ):
                        try:
                            pv_report["content"] = json.loads(pv_report["content"])
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse PV report content as JSON "
                                f"for report {pv_report['id']}"
                            )
                            pv_report["content"] = None

            # Log access asynchronously (don't wait)
            asyncio.create_task(
                self.log_project_access(
                    organization_id=organization_id,
                    accessed_by_user_id=accessed_by_user_id,
                    target_user_id=owner_info["user_id"] if owner_info else "",
                    project_id=project_id,
                    access_type="view",
                )
            )

            # Build response
            return {
                "project": project,
                "owner": owner_info,
                "pv_report": pv_report,
                "access_log": {
                    "accessed_by": accessed_by_user_id,
                    "accessed_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting project detail: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get project detail: {str(e)}"
            )

    # =========================================================================
    # Organization Tenant Management (Async)
    # =========================================================================

    async def verify_invitation(
        self,
        token: str,
        max_age: int = 172800,
    ) -> Dict[str, Any]:
        """
        Verify invitation token and return invitation data (async).

        Args:
            token: The signed invitation token
            max_age: Maximum age of token in seconds (default 48 hours)

        Returns:
            The invitation record from database
        """
        from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
        import os

        SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
        serializer = URLSafeTimedSerializer(SECRET_KEY)
        client = await get_async_supabase_client()

        try:
            data = serializer.loads(token, max_age=max_age)
            if data.get("type") != "org_invitation":
                raise ValueError("Invalid invitation token type")

            # Check DB for invitation
            result = await (
                client.table("app_invitations")
                .select("*")
                .eq("id", data["invite_id"])
                .limit(1)
                .execute()
            )

            if not result.data:
                raise ValueError("Invitation not found")

            invite = result.data[0]

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
                    f"Invitation validation failed: status={invite['status']}, "
                    f"type={invite['type']}"
                )
                raise ValueError("Invitation already used or invalid")

            return invite

        except SignatureExpired:
            raise ValueError("Invitation has expired")
        except BadSignature:
            raise ValueError("Invalid invitation token")

    def _get_default_permissions(self, role: str) -> Dict[str, Any]:
        """Get default permissions for a role."""
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

    async def create_organization_tenant(
        self,
        user_id: str,
        body: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Create an org only if user has a valid app invitation (async).

        OPTIMIZED: Uses parallel queries where possible.

        Args:
            user_id: The user creating the organization
            body: Organization details including invite_token

        Returns:
            The created organization record or None
        """
        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        # Step 1: Verify invitation
        invite = await self.verify_invitation(body["invite_token"])

        # Step 2: Create org tenant
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

        org_result = await client.table("tenants").insert(org_payload).execute()

        if not org_result.data:
            return None

        org = org_result.data[0]
        org_type = invite.get("metadata", {}).get("organization_type", "grant_org")

        # Step 3: Create billing config and membership in parallel
        permissions = self._get_default_permissions("owner")
        billing_config_payload = {
            "tenant_id": org["id"],
            "organization_type": org_type,
            "billing_settings": {
                "billing_day_of_month": 1,
                "timezone": "UTC",
            },
            "created_at": now,
            "updated_at": now,
        }
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

        parallel_tasks = [
            client.table("organization_billing_config")
            .insert(billing_config_payload)
            .execute(),
            client.table("tenant_memberships").insert(membership_payload).execute(),
        ]

        try:
            await asyncio.gather(*parallel_tasks)
            logger.info(
                f"Created billing config for organization {org['id']} with type {org_type}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create billing config/membership for org {org['id']}: {e}"
            )
            # Don't fail organization creation

        # Step 4: Create credit lot if credits are specified
        credits = invite.get("credits")
        if credits is not None and credits > 0:
            # grant_org gets 1 year expiry, others get no expiry
            expires_at = None
            if org_type == "grant_org":
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(days=365)
                ).isoformat()

            credit_lot_payload = {
                "tenant_id": org["id"],
                "original_tenant_id": org["id"],
                "source": "grant" if org_type == "grant_org" else "purchase",
                "credit_amount": float(credits),
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
                credit_result = await (
                    client.table("credit_lots").insert(credit_lot_payload).execute()
                )
                logger.info(f"Allocated {credits} credits to organization {org['id']}")

                # For postpay_org, record this initial grant allocation
                if org_type == "postpay_org" and credit_result.data:
                    try:
                        created_lot = credit_result.data[0]
                        allocation_payload = {
                            "tenant_id": org["id"],
                            "allocation_type": "grant",
                            "credit_amount": float(credits),
                            "credit_lot_id": created_lot.get("id"),
                            "allocated_at": now,
                            "metadata": {
                                "source": "invitation",
                                "invitation_id": invite["id"],
                                "invited_by": invite.get("created_by"),
                                "email": invite["email"],
                            },
                        }

                        await (
                            client.table("organization_credit_allocations")
                            .insert(allocation_payload)
                            .execute()
                        )
                        logger.info(
                            f"Recorded initial grant allocation for postpay_org "
                            f"{org['id']}: {credits} credits"
                        )
                    except Exception as track_error:
                        logger.error(
                            f"Failed to record initial grant allocation for "
                            f"postpay_org {org['id']}: {track_error}",
                            exc_info=True,
                        )

            except Exception as e:
                logger.error(f"Failed to create credit lot for org {org['id']}: {e}")
                raise e

        # Step 5: Mark invitation as used
        await (
            client.table("app_invitations")
            .update({"status": "used", "updated_at": now})
            .eq("id", invite["id"])
            .execute()
        )

        return org

    async def generate_invitation(
        self,
        email: str,
        created_by: str,
        credits: Optional[int] = None,
        org_type: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create or reuse a pending invitation row + signed token (async).

        Args:
            email: Email address to invite
            created_by: User ID of the inviter
            credits: Credits to allocate (for grant organizations)
            org_type: Organization type ('grant_org', 'prepay_org', or 'postpay_org')

        Returns:
            Tuple of (token, invitation_record)
        """
        from itsdangerous import URLSafeTimedSerializer
        import os

        from ..services.communication.email_service import email_service

        SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
        serializer = URLSafeTimedSerializer(SECRET_KEY)

        client = await get_async_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        norm_email = email.strip().lower()

        requested_credits = Decimal(str(credits if credits is not None else 0))
        org_type_value = org_type or "grant_org"

        # 1) Try to find an existing pending invite
        existing = await (
            client.table("app_invitations")
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

            # Update if credits or org_type differ
            if (
                current_credits != requested_credits
                or current_org_type != org_type_value
            ):
                update_payload = {
                    "credits": float(requested_credits),
                    "metadata": {
                        **current_metadata,
                        "organization_type": org_type_value,
                    },
                    "updated_at": now,
                }
                await (
                    client.table("app_invitations")
                    .update(update_payload)
                    .eq("id", invite["id"])
                    .execute()
                )
                invite.update(update_payload)
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
                    "organization_type": org_type_value,
                },
            }
            res = await client.table("app_invitations").insert(payload).execute()
            invite = res.data[0]

        # 3) Build token from the stored row
        token_payload = {
            "invite_id": invite["id"],
            "email": norm_email,
            "type": "org_invitation",
            "credits": invite.get("credits"),
            "org_type": org_type or "grant_org",
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

        return token, invite

    async def delete_organization_tenant(
        self,
        org_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete an organization tenant (async).

        Cascading deletes will clean up memberships, org_teams, invitations, and teams.

        Args:
            org_id: Organization ID to delete
            user_id: User performing the deletion

        Returns:
            True if successful
        """
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("tenants")
                .select("id, tenant_type")
                .eq("id", org_id)
                .limit(1)
                .execute()
            )

            if not result.data:
                raise HTTPException(status_code=404, detail="Organization not found")

            org = result.data[0]
            if org.get("tenant_type") != "organization":
                raise HTTPException(status_code=400, detail="Invalid tenant type")

            await client.table("tenants").delete().eq("id", org_id).execute()
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"delete_organization_tenant error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete organization: {e}"
            )


# Singleton instance
_async_org_service: Optional[AsyncOrganizationService] = None


def get_async_org_service() -> AsyncOrganizationService:
    """Get or create the async organization service singleton."""
    global _async_org_service
    if _async_org_service is None:
        _async_org_service = AsyncOrganizationService()
    return _async_org_service
