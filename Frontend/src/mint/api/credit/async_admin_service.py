"""
Async service layer for admin credit granting and organization credit allocation.

This is an optimized async version that avoids blocking the FastAPI event loop.
Email notifications are returned as metadata for BackgroundTasks to handle.

Optimizations:
- Uses asyncio.gather() to parallelize independent database queries
- Batch updates for credit lot deductions
- Minimizes round trips to database
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..system.core.async_supabase_client import get_async_supabase_client
from .async_service import AsyncCreditService

logger = logging.getLogger(__name__)


class AsyncAdminCreditService:
    """Async service for admin credit granting operations."""

    def __init__(self):
        """Initialize the async admin credit service."""
        self.credit_service = AsyncCreditService()

    async def _get_admin_name(self, admin_user_id: str) -> str:
        """Get the admin's display name from their user profile."""
        try:
            client = await get_async_supabase_client()
            result = await (
                client.table("user_profiles")
                .select("full_name, email")
                .eq("id", admin_user_id)
                .execute()
            )
            if result.data:
                user = result.data[0]
                return user.get("full_name") or user.get("email", "Yuba Admin")
            return "Yuba Admin"
        except Exception as e:
            logger.warning(f"Could not fetch admin name: {e}")
            return "Yuba Admin"

    async def grant_credits_to_organization(
        self,
        organization_id: str,
        admin_user_id: str,
        credit_amount: int,
    ) -> Dict[str, Any]:
        """
        Grant credits to an organization. Credits expire 1 year from now.

        Returns email metadata for BackgroundTasks to send notification.
        Does NOT send email synchronously - caller should queue email via BackgroundTasks.

        Optimized with parallel queries where possible.

        Args:
            organization_id: Organization tenant ID
            admin_user_id: Admin/super admin user ID performing the grant
            credit_amount: Number of credits to grant

        Returns:
            Dictionary with grant details including email_recipient for notification

        Raises:
            HTTPException: If validation fails or operation fails
        """
        try:
            client = await get_async_supabase_client()

            # Validate credit amount early (no DB needed)
            if credit_amount < 1:
                raise HTTPException(
                    status_code=400,
                    detail="Credit amount must be at least 1"
                )

            # Parallel: validate org AND get admin name at the same time
            org_task = (
                client.table("tenants")
                .select("id, name, contact_email")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )
            admin_name_task = self._get_admin_name(admin_user_id)

            org_result, admin_name = await asyncio.gather(org_task, admin_name_task)

            if not org_result.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_result.data[0]
            org_name = org.get("name", "Organization")
            org_contact_email = org.get("contact_email")

            # Calculate expiry (1 year from now)
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=365)

            # Create credit lot (must happen after validation)
            await self.credit_service.create_credit_lot(
                tenant_id=organization_id,
                source="grant",
                credit_amount=Decimal(str(credit_amount)),
                valid_from=now.isoformat(),
                expires_at=expires_at.isoformat(),
                metadata={
                    "granted_by": admin_user_id,
                    "grant_type": "admin_manual_grant",
                    "granted_at": now.isoformat()
                },
                original_tenant_id=organization_id
            )

            logger.info(
                f"Admin {admin_user_id} granted {credit_amount} credits to organization {organization_id}, "
                f"expires: {expires_at.isoformat()}"
            )

            return {
                "success": True,
                "organization_id": organization_id,
                "organization_name": org_name,
                "credit_amount": credit_amount,
                "expires_at": expires_at,
                "granted_by": admin_user_id,
                "granted_at": now,
                "admin_name": admin_name,
                "email_recipient": org_contact_email
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to grant credits to organization: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to grant credits: {str(e)}"
            )

    async def toggle_organization_credits_suspension(
        self,
        organization_id: str,
        admin_user_id: str,
        is_active: bool,
    ) -> Dict[str, Any]:
        """
        Set suspension state of all credits from an organization.

        Args:
            organization_id: Organization tenant ID
            admin_user_id: Admin user ID performing the operation
            is_active: True to activate credits, False to suspend them

        Returns:
            Dictionary with operation details

        Raises:
            HTTPException: If validation fails or operation fails
        """
        try:
            client = await get_async_supabase_client()

            # Validate organization exists and is active
            org_result = await (
                client.table("tenants")
                .select("id, name")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )

            if not org_result.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_result.data[0]
            org_name = org.get("name", "Organization")
            now = datetime.now(timezone.utc)

            if is_active:
                result = await client.rpc('toggle_org_credits_unsuspend', {
                    'org_id': organization_id
                }).execute()
                affected_count = result.data if result.data else 0
            else:
                result = await client.rpc('toggle_org_credits_suspend', {
                    'org_id': organization_id,
                    'admin_id': admin_user_id,
                    'suspended_at_ts': now.isoformat()
                }).execute()
                affected_count = result.data if result.data else 0

            state_name = "active" if is_active else "suspended"
            action = "activated" if is_active else "suspended"

            logger.info(
                f"Admin {admin_user_id} {action} {affected_count} credit lots "
                f"from organization {organization_id}"
            )

            return {
                "success": True,
                "organization_id": organization_id,
                "organization_name": org_name,
                "affected_lot_count": affected_count,
                "new_state": state_name,
                "toggled_by": admin_user_id,
                "toggled_at": now,
                "message": f"Successfully {action} {affected_count} credit lots"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to toggle organization credits suspension: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to toggle credits suspension: {str(e)}"
            )


class AsyncOrganizationCreditAllocationService:
    """Async service for organization credit allocation to tenants."""

    def __init__(self):
        """Initialize the async organization credit allocation service."""
        self.credit_service = AsyncCreditService()

    async def _get_allocator_name(self, user_id: str) -> str:
        """Get the allocator's display name from their user profile."""
        try:
            client = await get_async_supabase_client()
            result = await (
                client.table("user_profiles")
                .select("full_name, email")
                .eq("id", user_id)
                .execute()
            )
            if result.data:
                user = result.data[0]
                return user.get("full_name") or user.get("email", "Organization Admin")
            return "Organization Admin"
        except Exception as e:
            logger.warning(f"Could not fetch allocator name: {e}")
            return "Organization Admin"

    async def _get_tenant_contact_info(self, tenant_id: str, tenant_type: str) -> tuple:
        """
        Get contact email and name for a tenant.

        Returns:
            Tuple of (email, name) or (None, None) if not found
        """
        try:
            client = await get_async_supabase_client()

            if tenant_type == "individual":
                ind_result = await (
                    client.table("org_individuals")
                    .select("user_id")
                    .eq("individual_tenant_id", tenant_id)
                    .execute()
                )
                if ind_result.data:
                    user_id = ind_result.data[0].get("user_id")
                    if user_id:
                        user_result = await (
                            client.table("user_profiles")
                            .select("email, full_name")
                            .eq("id", user_id)
                            .execute()
                        )
                        if user_result.data:
                            user = user_result.data[0]
                            return (user.get("email"), user.get("full_name", "Member"))

            elif tenant_type == "team":
                # Parallel: get team info AND owner info at once
                team_task = (
                    client.table("tenants")
                    .select("name, contact_email")
                    .eq("id", tenant_id)
                    .execute()
                )
                leader_task = (
                    client.table("tenant_memberships")
                    .select("user_id")
                    .eq("tenant_id", tenant_id)
                    .eq("role", "owner")
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

                team_result, leader_result = await asyncio.gather(team_task, leader_task)

                if team_result.data:
                    team = team_result.data[0]
                    team_name = team.get("name", "Team")
                    contact_email = team.get("contact_email")

                    # Only fetch user profile if no contact_email and we have a leader
                    if not contact_email and leader_result.data:
                        leader_user_id = leader_result.data[0].get("user_id")
                        if leader_user_id:
                            user_result = await (
                                client.table("user_profiles")
                                .select("email")
                                .eq("id", leader_user_id)
                                .execute()
                            )
                            if user_result.data:
                                contact_email = user_result.data[0].get("email")

                    return (contact_email, team_name)

            return (None, None)
        except Exception as e:
            logger.warning(f"Could not fetch tenant contact info: {e}")
            return (None, None)

    async def _verify_tenant_belongs_to_org(
        self,
        organization_id: str,
        tenant_id: str,
        tenant_type: str
    ) -> bool:
        """Verify that a tenant belongs to the organization."""
        try:
            client = await get_async_supabase_client()

            if tenant_type == "individual":
                result = await (
                    client.table("org_individuals")
                    .select("id")
                    .eq("organization_id", organization_id)
                    .eq("individual_tenant_id", tenant_id)
                    .execute()
                )
                return bool(result.data)

            elif tenant_type == "team":
                result = await (
                    client.table("org_teams")
                    .select("id")
                    .eq("organization_id", organization_id)
                    .eq("team_id", tenant_id)
                    .execute()
                )
                return bool(result.data)

            return False
        except Exception as e:
            logger.error(f"Error verifying tenant membership: {e}")
            return False

    async def allocate_credits_to_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        tenant_type: str,
        allocated_by_user_id: str,
        credit_amount: float,
    ) -> Dict[str, Any]:
        """
        Allocate credits from organization to a tenant (individual or team).

        Returns email metadata for BackgroundTasks to send notification.
        Does NOT send email synchronously.

        Optimized with:
        - Parallel initial queries (org, tenant verification, org config)
        - Parallel lot updates instead of sequential
        - Parallel final queries (contact info, allocator name)

        Args:
            organization_id: Organization tenant ID
            tenant_id: Target tenant ID
            tenant_type: Type of target tenant ('individual' or 'team')
            allocated_by_user_id: User ID performing the allocation
            credit_amount: Number of credits to allocate

        Returns:
            Dictionary with allocation details including email metadata

        Raises:
            HTTPException: If validation fails or operation fails
        """
        try:
            client = await get_async_supabase_client()

            # Validate inputs early (no DB needed)
            if tenant_type not in ["individual", "team"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid tenant_type. Must be 'individual' or 'team'"
                )
            if credit_amount < 1:
                raise HTTPException(
                    status_code=400,
                    detail="Credit amount must be at least 1"
                )

            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()

            # Parallel: org validation, tenant verification, org config, allocator name
            org_task = (
                client.table("tenants")
                .select("id, name")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )
            tenant_verify_task = self._verify_tenant_belongs_to_org(
                organization_id, tenant_id, tenant_type
            )
            org_config_task = (
                client.table('organization_billing_config')
                .select('organization_type')
                .eq('tenant_id', organization_id)
                .limit(1)
                .execute()
            )
            allocator_name_task = self._get_allocator_name(allocated_by_user_id)

            org_result, tenant_belongs, org_config_result, allocator_name = await asyncio.gather(
                org_task, tenant_verify_task, org_config_task, allocator_name_task
            )

            if not org_result.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )
            org = org_result.data[0]

            if not tenant_belongs:
                raise HTTPException(
                    status_code=403,
                    detail="Tenant does not belong to this organization"
                )

            org_type = 'grant_org'
            if org_config_result.data:
                org_type = org_config_result.data[0].get('organization_type', 'grant_org')

            lot_expires_at = None  # Only grant_org uses expiry from source lot
            available_credits = 0  # Initialize for postpay case

            if org_type != 'postpay_org':
                # Parallel: check unreserved credits AND fetch org lots (excluding reserved)
                available_task = self.credit_service.get_unreserved_available_credits(organization_id)
                lots_task = (
                    client.table("credit_lots")
                    .select("id, credit_amount, expires_at")
                    .eq("tenant_id", organization_id)
                    .eq("is_active", True)
                    .gt("credit_amount", 0)
                    .lte("valid_from", now_iso)
                    .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
                    .or_(f"reserved_until.is.null,reserved_until.lte.{now_iso}")
                    .order("expires_at", desc=False)
                    .execute()
                )

                available_credits, org_lots_result = await asyncio.gather(available_task, lots_task)

                if available_credits < credit_amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits. Organization has {available_credits} credits, tried to allocate {credit_amount}"
                    )

                org_lots = org_lots_result.data or []
                if not org_lots:
                    raise HTTPException(
                        status_code=400,
                        detail="No active credit lots available for organization"
                    )

                # For grant_org only: inherit expiry from source lot (if it has one)
                if org_type == 'grant_org':
                    earliest_expiry_str = org_lots[0].get("expires_at")
                    if earliest_expiry_str:
                        try:
                            if earliest_expiry_str.endswith('Z'):
                                earliest_expiry_str = earliest_expiry_str[:-1] + '+00:00'
                            lot_expires_at = datetime.fromisoformat(earliest_expiry_str)
                        except (ValueError, TypeError):
                            lot_expires_at = None  # Keep null if parsing fails

                # Calculate deductions first, then execute updates in parallel
                remaining = Decimal(str(credit_amount))
                lot_updates = []

                for lot in org_lots:
                    if remaining <= 0:
                        break
                    lot_credits = Decimal(str(lot["credit_amount"]))
                    deduct = min(lot_credits, remaining)
                    new_balance = lot_credits - deduct
                    lot_updates.append({"id": lot["id"], "new_balance": float(new_balance)})
                    remaining -= deduct

                # Batch lot updates
                if lot_updates:
                    await self.credit_service.batch_update_lot_balances([
                        {"lot_id": u["id"], "new_balance": u["new_balance"]}
                        for u in lot_updates
                    ])

            # For postpay + individual, start user_id lookup in parallel with create_credit_lot
            user_id_task = None
            if org_type == 'postpay_org' and tenant_type == 'individual':
                user_id_task = (
                    client.table('tenant_memberships')
                    .select('user_id')
                    .eq('tenant_id', tenant_id)
                    .limit(1)
                    .execute()
                )

            # Create credit lot for the tenant
            create_lot_task = self.credit_service.create_credit_lot(
                tenant_id=tenant_id,
                source="grant" if org_type == 'grant_org' else "purchase",
                credit_amount=Decimal(str(credit_amount)),
                valid_from=now_iso,
                expires_at=lot_expires_at.isoformat() if lot_expires_at else None,
                metadata={
                    "organization_id": organization_id,
                    "allocated_by": allocated_by_user_id,
                    "allocation_type": "manual",
                    "allocated_at": now_iso
                },
                original_tenant_id=organization_id
            )

            # Parallel: create lot + user_id lookup (if postpay individual)
            if user_id_task:
                created_lot, user_id_result = await asyncio.gather(create_lot_task, user_id_task)
                user_id = user_id_result.data[0].get('user_id') if user_id_result.data else None
            else:
                created_lot = await create_lot_task
                user_id = None

            # For postpay_org: record allocation in parallel with contact info lookup
            if org_type == 'postpay_org':
                allocation_type = 'allocation_to_team' if tenant_type == 'team' else 'allocation_to_member'

                insert_task = (
                    client.table('organization_credit_allocations')
                    .insert({
                        'tenant_id': organization_id,
                        'allocation_type': allocation_type,
                        'credit_amount': float(credit_amount),
                        'credit_lot_id': created_lot.get('id') if created_lot else None,
                        'allocated_to_tenant_id': tenant_id,
                        'allocated_to_user_id': user_id,
                        'allocated_by_user_id': allocated_by_user_id,
                        'allocated_at': now_iso,
                        'metadata': {
                            "organization_id": organization_id,
                            "allocated_by": allocated_by_user_id,
                            "allocation_type": "manual",
                            "tenant_type": tenant_type
                        },
                    })
                    .execute()
                )
                contact_task = self._get_tenant_contact_info(tenant_id, tenant_type)

                try:
                    _, contact_result = await asyncio.gather(insert_task, contact_task)
                    logger.info(f"Recorded {tenant_type} credit allocation for postpay_org {organization_id}")
                except Exception as e:
                    logger.error(f"Failed to record credit allocation for postpay_org: {e}")
                    contact_result = await self._get_tenant_contact_info(tenant_id, tenant_type)
            else:
                # Non-postpay: just get contact info
                contact_result = await self._get_tenant_contact_info(tenant_id, tenant_type)

            tenant_email, tenant_name = contact_result

            # Calculate remaining credits from earlier validation query
            # (avoids duplicate DB call)
            if org_type != 'postpay_org':
                remaining_org_credits = available_credits - credit_amount
            else:
                remaining_org_credits = 0

            logger.info(
                f"Organization {organization_id} allocated {credit_amount} credits to "
                f"{tenant_type} {tenant_id}, remaining org credits: {remaining_org_credits}"
            )

            return {
                "success": True,
                "organization_id": organization_id,
                "organization_name": org.get("name"),
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                "tenant_type": tenant_type,
                "credit_amount": credit_amount,
                "expires_at": lot_expires_at,
                "allocated_by": allocated_by_user_id,
                "allocated_at": now,
                "remaining_org_credits": remaining_org_credits,
                "allocator_name": allocator_name,
                "email_recipient": tenant_email
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to allocate credits to tenant: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to allocate credits: {str(e)}"
            )

    async def bulk_allocate_credits_to_tenants(
        self,
        organization_id: str,
        allocations: list,
        allocated_by_user_id: str,
    ) -> Dict[str, Any]:
        """
        Allocate credits to multiple tenants in a single operation.

        Optimized with true batch operations:
        - Single query to validate all tenants
        - Single deduction from org credit lots
        - Single batch insert for all credit lots
        - Single batch insert for postpay allocation records

        Args:
            organization_id: Organization tenant ID
            allocations: List of dicts with keys: tenant_id, tenant_type, credit_amount
            allocated_by_user_id: User ID performing the allocations

        Returns:
            Dictionary with bulk allocation results including email metadata for each

        Raises:
            HTTPException: If validation fails
        """
        try:
            client = await get_async_supabase_client()
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()

            # Parallel: org validation + org config + allocator name
            org_task = (
                client.table("tenants")
                .select("id, name")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )
            org_config_task = (
                client.table('organization_billing_config')
                .select('organization_type')
                .eq('tenant_id', organization_id)
                .limit(1)
                .execute()
            )
            allocator_name_task = self._get_allocator_name(allocated_by_user_id)

            org_result, org_config_result, allocator_name = await asyncio.gather(
                org_task, org_config_task, allocator_name_task
            )

            if not org_result.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_result.data[0]
            org_name = org.get("name", "Organization")

            org_type = 'grant_org'
            if org_config_result.data:
                org_type = org_config_result.data[0].get('organization_type', 'grant_org')

            # Calculate total credits needed
            total_credits_needed = sum(Decimal(str(alloc['credit_amount'])) for alloc in allocations)

            # Separate allocations by type for batch validation
            individual_tenant_ids = [a['tenant_id'] for a in allocations if a['tenant_type'] == 'individual']
            team_tenant_ids = [a['tenant_id'] for a in allocations if a['tenant_type'] == 'team']

            # Batch validate tenant memberships
            valid_individuals = set()
            valid_teams = set()

            if individual_tenant_ids:
                ind_result = await (
                    client.table("org_individuals")
                    .select("individual_tenant_id")
                    .eq("organization_id", organization_id)
                    .in_("individual_tenant_id", individual_tenant_ids)
                    .execute()
                )
                valid_individuals = {r["individual_tenant_id"] for r in (ind_result.data or [])}

            if team_tenant_ids:
                team_result = await (
                    client.table("org_teams")
                    .select("team_id")
                    .eq("organization_id", organization_id)
                    .in_("team_id", team_tenant_ids)
                    .execute()
                )
                valid_teams = {r["team_id"] for r in (team_result.data or [])}

            # Filter valid allocations
            valid_allocations = []
            invalid_results = []

            for alloc in allocations:
                tenant_id = alloc['tenant_id']
                tenant_type = alloc['tenant_type']

                if tenant_type == 'individual' and tenant_id not in valid_individuals:
                    invalid_results.append({
                        "tenant_id": tenant_id,
                        "tenant_name": None,
                        "tenant_type": tenant_type,
                        "credit_amount": alloc['credit_amount'],
                        "success": False,
                        "error": "Tenant does not belong to this organization",
                        "email_recipient": None
                    })
                elif tenant_type == 'team' and tenant_id not in valid_teams:
                    invalid_results.append({
                        "tenant_id": tenant_id,
                        "tenant_name": None,
                        "tenant_type": tenant_type,
                        "credit_amount": alloc['credit_amount'],
                        "success": False,
                        "error": "Tenant does not belong to this organization",
                        "email_recipient": None
                    })
                elif tenant_type not in ['individual', 'team']:
                    invalid_results.append({
                        "tenant_id": tenant_id,
                        "tenant_name": None,
                        "tenant_type": tenant_type,
                        "credit_amount": alloc['credit_amount'],
                        "success": False,
                        "error": "Invalid tenant_type",
                        "email_recipient": None
                    })
                else:
                    valid_allocations.append(alloc)

            if not valid_allocations:
                return {
                    "success": False,
                    "message": "No valid allocations to process",
                    "organization_id": organization_id,
                    "organization_name": org_name,
                    "total_requested": len(allocations),
                    "successful_count": 0,
                    "failed_count": len(invalid_results),
                    "results": invalid_results,
                    "remaining_org_credits": 0,
                    "allocated_by": allocated_by_user_id,
                    "allocated_at": now
                }

            # Recalculate total for valid allocations
            valid_total = sum(Decimal(str(a['credit_amount'])) for a in valid_allocations)

            # Only grant_org uses expiry (inherited from source lot)
            lot_expires_at = None
            available_credits = 0  # Initialize for postpay case

            # For non-postpay orgs, check unreserved credits and deduct (excluding reserved)
            if org_type != 'postpay_org':
                # Parallel: get unreserved credits AND fetch org lots
                available_task = self.credit_service.get_unreserved_available_credits(organization_id)
                lots_task = (
                    client.table("credit_lots")
                    .select("id, credit_amount, expires_at")
                    .eq("tenant_id", organization_id)
                    .eq("is_active", True)
                    .gt("credit_amount", 0)
                    .lte("valid_from", now_iso)
                    .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
                    .or_(f"reserved_until.is.null,reserved_until.lte.{now_iso}")
                    .order("expires_at", desc=False)
                    .execute()
                )

                available_credits, org_lots_result = await asyncio.gather(available_task, lots_task)

                if available_credits < float(valid_total):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits. Organization has {available_credits} credits, but {valid_total} requested"
                    )

                org_lots = org_lots_result.data or []

                if not org_lots:
                    raise HTTPException(
                        status_code=400,
                        detail="No active credit lots available for organization"
                    )

                # For grant_org only: inherit expiry from source lot (if it has one)
                if org_type == 'grant_org':
                    earliest_expiry_str = org_lots[0].get("expires_at")
                    if earliest_expiry_str:
                        try:
                            if earliest_expiry_str.endswith('Z'):
                                earliest_expiry_str = earliest_expiry_str[:-1] + '+00:00'
                            lot_expires_at = datetime.fromisoformat(earliest_expiry_str)
                        except (ValueError, TypeError):
                            lot_expires_at = None  # Keep null if parsing fails

                # Deduct total from organization lots (already filtered to positive balances)
                remaining = valid_total
                lot_updates = []

                for lot in org_lots:
                    if remaining <= 0:
                        break

                    lot_credits = Decimal(str(lot["credit_amount"]))
                    deduct = min(lot_credits, remaining)
                    new_balance = lot_credits - deduct
                    lot_updates.append({"id": lot["id"], "new_balance": float(new_balance)})
                    remaining -= deduct

                # Batch lot updates
                if lot_updates:
                    await self.credit_service.batch_update_lot_balances([
                        {"lot_id": u["id"], "new_balance": u["new_balance"]}
                        for u in lot_updates
                    ])

            # Batch create credit lots for all valid allocations
            credit_lot_payloads = []
            for alloc in valid_allocations:
                credit_lot_payloads.append({
                    "tenant_id": alloc['tenant_id'],
                    "original_tenant_id": organization_id,
                    "source": "grant" if org_type == 'grant_org' else "purchase",
                    "credit_amount": float(alloc['credit_amount']),
                    "valid_from": now_iso,
                    "expires_at": lot_expires_at.isoformat() if lot_expires_at else None,
                    "metadata": {
                        "organization_id": organization_id,
                        "allocated_by": allocated_by_user_id,
                        "allocation_type": "bulk_manual",
                        "allocated_at": now_iso
                    },
                    "created_at": now_iso,
                    "is_active": True,
                })

            # Single batch insert for all credit lots
            created_lots_result = await (
                client.table("credit_lots")
                .insert(credit_lot_payloads)
                .execute()
            )
            created_lots = created_lots_result.data or []

            # Map created lots back to allocations
            lot_by_tenant = {lot["tenant_id"]: lot for lot in created_lots}

            # For postpay_org, batch insert allocation records
            if org_type == 'postpay_org' and valid_allocations:
                # Get user_ids for individuals in batch
                individual_user_map = {}
                individual_ids = [a['tenant_id'] for a in valid_allocations if a['tenant_type'] == 'individual']
                if individual_ids:
                    membership_result = await (
                        client.table('tenant_memberships')
                        .select('tenant_id, user_id')
                        .in_('tenant_id', individual_ids)
                        .execute()
                    )
                    for m in (membership_result.data or []):
                        individual_user_map[m['tenant_id']] = m.get('user_id')

                allocation_payloads = []
                for alloc in valid_allocations:
                    tenant_id = alloc['tenant_id']
                    tenant_type = alloc['tenant_type']
                    allocation_type = 'allocation_to_team' if tenant_type == 'team' else 'allocation_to_member'
                    created_lot = lot_by_tenant.get(tenant_id, {})

                    allocation_payloads.append({
                        'tenant_id': organization_id,
                        'allocation_type': allocation_type,
                        'credit_amount': float(alloc['credit_amount']),
                        'credit_lot_id': created_lot.get('id'),
                        'allocated_to_tenant_id': tenant_id,
                        'allocated_to_user_id': individual_user_map.get(tenant_id),
                        'allocated_by_user_id': allocated_by_user_id,
                        'allocated_at': now_iso,
                        'metadata': {
                            "organization_id": organization_id,
                            "allocated_by": allocated_by_user_id,
                            "allocation_type": "bulk_manual",
                            "tenant_type": tenant_type
                        },
                    })

                # Single batch insert for postpay records
                if allocation_payloads:
                    await client.table('organization_credit_allocations').insert(allocation_payloads).execute()

            # Batch fetch tenant contact info - parallel queries for individuals and teams
            tenant_contact_map = {}
            valid_individual_ids = [a['tenant_id'] for a in valid_allocations if a['tenant_type'] == 'individual']
            valid_team_ids = [a['tenant_id'] for a in valid_allocations if a['tenant_type'] == 'team']

            # Build parallel tasks
            contact_tasks = []
            task_types = []

            if valid_individual_ids:
                contact_tasks.append(
                    client.table("org_individuals")
                    .select("individual_tenant_id, user_id")
                    .in_("individual_tenant_id", valid_individual_ids)
                    .execute()
                )
                task_types.append("individuals")

            if valid_team_ids:
                contact_tasks.append(
                    client.table("tenants")
                    .select("id, name, contact_email")
                    .in_("id", valid_team_ids)
                    .execute()
                )
                task_types.append("teams")

            # Execute in parallel
            if contact_tasks:
                contact_results = await asyncio.gather(*contact_tasks)

                for i, task_type in enumerate(task_types):
                    result = contact_results[i]
                    if task_type == "individuals" and result.data:
                        # Need to fetch user profiles for individuals
                        user_ids = [r["user_id"] for r in result.data if r.get("user_id")]
                        if user_ids:
                            profiles_result = await (
                                client.table("user_profiles")
                                .select("id, email, full_name")
                                .in_("id", user_ids)
                                .execute()
                            )
                            user_profile_map = {p["id"]: p for p in (profiles_result.data or [])}
                            for ind in result.data:
                                user_id = ind.get("user_id")
                                if user_id and user_id in user_profile_map:
                                    profile = user_profile_map[user_id]
                                    tenant_contact_map[ind["individual_tenant_id"]] = (
                                        profile.get("email"),
                                        profile.get("full_name", "Member")
                                    )
                    elif task_type == "teams" and result.data:
                        for team in result.data:
                            tenant_contact_map[team["id"]] = (
                                team.get("contact_email"),
                                team.get("name", "Team")
                            )

            # allocator_name already fetched at start

            # Invalidate credit caches for all affected tenants in parallel
            if valid_allocations:
                invalidate_tasks = [
                    self.credit_service._invalidate_credit_cache(alloc['tenant_id'])
                    for alloc in valid_allocations
                ]
                await asyncio.gather(*invalidate_tasks, return_exceptions=True)

            # Build success results
            success_results = []
            for alloc in valid_allocations:
                tenant_id = alloc['tenant_id']
                contact_info = tenant_contact_map.get(tenant_id, (None, None))
                success_results.append({
                    "tenant_id": tenant_id,
                    "tenant_name": contact_info[1],
                    "tenant_type": alloc['tenant_type'],
                    "credit_amount": alloc['credit_amount'],
                    "success": True,
                    "error": None,
                    "email_recipient": contact_info[0],
                    "allocator_name": allocator_name,
                    "expires_at": lot_expires_at,
                    "organization_name": org_name
                })

            # Combine results
            all_results = success_results + invalid_results
            successful_count = len(success_results)
            failed_count = len(invalid_results)

            # Get final remaining credits
            remaining_org_credits = 0
            if org_type != 'postpay_org':
                remaining_org_credits = await self.credit_service.get_available_credits(organization_id)

            logger.info(
                f"Bulk allocation completed for organization {organization_id}: "
                f"{successful_count} succeeded, {failed_count} failed (batch operations)"
            )

            return {
                "success": failed_count == 0,
                "message": f"Bulk allocation completed: {successful_count} succeeded, {failed_count} failed",
                "organization_id": organization_id,
                "organization_name": org_name,
                "total_requested": len(allocations),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "results": all_results,
                "remaining_org_credits": remaining_org_credits,
                "allocated_by": allocated_by_user_id,
                "allocated_at": now
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to perform bulk allocation: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to perform bulk allocation: {str(e)}"
            )
