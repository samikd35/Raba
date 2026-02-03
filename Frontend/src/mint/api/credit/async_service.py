"""
Async Credit service for payment routes.

This is an optimized async version of CreditService specifically designed
for payment routes to avoid blocking the FastAPI event loop.

Other services should continue using the sync CreditService.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..system.core.async_supabase_client import get_async_supabase_client

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when organization doesn't have enough credits for an operation."""

    pass


def _get_credit_cache_service():
    """Get the credit cache service if available."""
    try:
        from ..cache.credit_cache_service import get_credit_cache_service

        return get_credit_cache_service()
    except ImportError:
        return None


class AsyncCreditService:
    """
    Async credit service for payment routes.

    Provides non-blocking database operations for credit allocation
    after payment verification.
    """

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_int_units(x: Decimal | float | int | str | None) -> int:
        """Coerce to integer credit units."""
        if x is None:
            return 0
        return int(Decimal(str(x)))

    async def create_credit_lot(
        self,
        tenant_id: str,
        source: str,
        credit_amount: Decimal,
        valid_from: str,
        expires_at: str | None,
        metadata: dict,
        original_tenant_id: str,
    ) -> Dict[str, Any]:
        """
        Create a new credit lot asynchronously.

        This is the async version used by payment routes after successful
        payment verification.

        Args:
            tenant_id: The tenant receiving the credits
            source: Source of credits (e.g., "purchase", "grant")
            credit_amount: Amount of credits to allocate
            valid_from: ISO datetime when credits become valid
            expires_at: ISO datetime when credits expire (optional)
            metadata: Additional metadata for the credit lot
            original_tenant_id: Original tenant that purchased/owns credits

        Returns:
            The created credit lot record
        """
        client = await get_async_supabase_client()

        payload = {
            "tenant_id": tenant_id,
            "original_tenant_id": original_tenant_id,
            "source": source,
            "credit_amount": float(credit_amount),
            "valid_from": valid_from,
            "expires_at": expires_at,
            "metadata": metadata or {},
            "created_at": self._now().isoformat(),
            "is_active": True,
        }

        result = await client.table("credit_lots").insert(payload).execute()

        # Invalidate credit balance cache after grant
        await self._invalidate_credit_cache(tenant_id)

        logger.info(
            f"Created credit lot for tenant {tenant_id}: "
            f"{credit_amount} credits from {source}"
        )

        return result.data[0] if result.data else payload

    async def get_available_credits(self, tenant_id: str) -> float:
        """
        Get total available credits for a tenant asynchronously.

        Args:
            tenant_id: The tenant ID

        Returns:
            Total available credits
        """
        # Try cache first
        cache_service = _get_credit_cache_service()
        if cache_service:
            try:
                cached_balance = await cache_service.get_credit_balance(tenant_id)
                if cached_balance is not None:
                    logger.debug(f"Cache hit for tenant {tenant_id}: {cached_balance}")
                    return cached_balance
            except Exception as e:
                logger.warning(f"Cache lookup failed for tenant {tenant_id}: {e}")

        # Fetch from database
        balance = await self._fetch_available_credits_from_db(tenant_id)

        # Cache the result
        if cache_service:
            try:
                await cache_service.set_credit_balance(tenant_id, balance)
                logger.debug(f"Cached balance for tenant {tenant_id}: {balance}")
            except Exception as e:
                logger.warning(f"Cache set failed for tenant {tenant_id}: {e}")

        return balance

    async def _fetch_available_credits_from_db(
        self,
        tenant_id: str,
        exclude_reserved: bool = False,
    ) -> float:
        """
        Fetch available credits directly from database asynchronously.

        Uses database-level SUM via RPC for efficiency.
        Falls back to row-by-row fetch if RPC is unavailable.

        Args:
            tenant_id: The tenant ID
            exclude_reserved: If True, exclude credits that are reserved for pending invitations
        """
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Note: RPC doesn't support exclude_reserved flag, so skip it when needed
        if not exclude_reserved:
            try:
                # Use database-level SUM via RPC (most efficient)
                result = await client.rpc(
                    "get_tenant_credit_balance", {"p_tenant_id": tenant_id}
                ).execute()

                if result.data is not None:
                    total = float(result.data)
                    logger.debug(f"Tenant {tenant_id}: {total} credits (via RPC)")
                    return total
            except Exception as e:
                logger.debug(f"RPC fallback for tenant {tenant_id}: {e}")

        # Fallback: fetch with database-level filtering
        query = (
            client.table("credit_lots")
            .select("credit_amount")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .gt("credit_amount", 0)
            .lte("valid_from", now_iso)
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
        )

        # Add reserved filter if needed
        if exclude_reserved:
            query = query.or_(f"reserved_until.is.null,reserved_until.lte.{now_iso}")

        result = await query.execute()

        total = sum(float(row.get("credit_amount", 0)) for row in (result.data or []))
        logger.debug(
            f"Tenant {tenant_id}: {total} credits (via fallback, exclude_reserved={exclude_reserved})"
        )
        return total

    async def _invalidate_credit_cache(self, tenant_id: str) -> None:
        """
        Invalidate the credit balance cache for a tenant.
        """
        cache_service = _get_credit_cache_service()
        if cache_service:
            try:
                await cache_service.invalidate_credit_balance(tenant_id)
                logger.info(f"Invalidated credit cache for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Cache invalidation failed for tenant {tenant_id}: {e}")

    async def get_total_allocated_credits(self, tenant_id: str) -> float:
        """
        Get total allocated credits for a tenant, INCLUDING expired credits.

        This returns ALL credits ever allocated regardless of expiry status.
        Use this for showing "total allocated" in UI.

        Args:
            tenant_id: The tenant ID

        Returns:
            Total credits ever allocated (including expired)
        """
        client = await get_async_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Fetch ALL credit lots (including expired, but only those that have started)
        result = await (
            client.table("credit_lots")
            .select("credit_amount")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .gt("credit_amount", 0)
            .lte("valid_from", now_iso)
            .execute()
        )

        total = sum(float(row.get("credit_amount", 0)) for row in (result.data or []))
        logger.debug(f"Tenant {tenant_id}: {total} total allocated credits")
        return total

    async def create_credit_lot_batch(
        self,
        allocations: List[Dict[str, Any]],
        source: str,
        valid_from: str,
        expires_at: str | None,
        base_metadata: dict,
    ) -> List[Dict[str, Any]]:
        """
        Create multiple credit lots in a single batch operation.

        Optimized for bulk credit allocation (e.g., organization member allocations).

        Args:
            allocations: List of dicts with tenant_id and credit_amount.
                         Each allocation can optionally include:
                         - expires_at: Per-lot expiry (overrides batch expires_at)
                         - source: Per-lot source (overrides batch source)
                         - metadata: Per-lot metadata (merged with base_metadata)
            source: Default source of credits (can be overridden per allocation)
            valid_from: ISO datetime when credits become valid
            expires_at: Default ISO datetime when credits expire (can be overridden per allocation)
            base_metadata: Base metadata to include in all lots

        Returns:
            List of created credit lot records
        """
        if not allocations:
            return []

        client = await get_async_supabase_client()
        created_at = self._now().isoformat()

        payloads = []
        tenant_ids = set()

        for alloc in allocations:
            tenant_id = alloc["tenant_id"]
            credit_amount = alloc.get("credit_amount", alloc.get("credits", 0))
            original_tenant_id = alloc.get("original_tenant_id", tenant_id)

            # Per-lot overrides
            lot_source = alloc.get("source", source)
            lot_expires_at = alloc.get("expires_at", expires_at)

            # Merge allocation-specific metadata with base metadata
            alloc_metadata = {**base_metadata}
            if "metadata" in alloc:
                alloc_metadata.update(alloc["metadata"])

            payloads.append(
                {
                    "tenant_id": tenant_id,
                    "original_tenant_id": original_tenant_id,
                    "source": lot_source,
                    "credit_amount": float(Decimal(str(credit_amount))),
                    "valid_from": valid_from,
                    "expires_at": lot_expires_at,
                    "metadata": alloc_metadata,
                    "created_at": created_at,
                    "is_active": True,
                }
            )
            tenant_ids.add(tenant_id)

        # Batch insert
        result = await client.table("credit_lots").insert(payloads).execute()

        # Invalidate cache for all affected tenants (parallel)
        if tenant_ids:
            await asyncio.gather(
                *[self._invalidate_credit_cache(tid) for tid in tenant_ids]
            )

        logger.info(
            f"Created {len(payloads)} credit lots in batch "
            f"for {len(tenant_ids)} tenants"
        )

        return result.data or payloads

    async def batch_update_lot_balances(
        self,
        updates: List[Dict[str, Any]],
    ) -> None:
        """
        Batch update credit lot balances.

        Uses parallel updates since Supabase doesn't support batch updates
        with different values per row. Wraps in asyncio.gather for efficiency.

        Args:
            updates: List of dicts with lot_id and new_balance
        """
        if not updates:
            return

        client = await get_async_supabase_client()

        tasks = [
            client.table("credit_lots")
            .update({"credit_amount": float(upd["new_balance"])})
            .eq("id", upd["lot_id"])
            .execute()
            for upd in updates
        ]

        await asyncio.gather(*tasks)

    async def has_grant_for_tx_ref(self, tx_ref: str) -> bool:
        """
        Check if credits have already been granted for a transaction reference.

        Used for idempotency in payment verification.

        Args:
            tx_ref: The transaction reference

        Returns:
            True if credits have already been allocated
        """
        client = await get_async_supabase_client()

        result = await (
            client.table("credit_lots")
            .select("id")
            .contains("metadata", {"tx_ref": tx_ref})
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def record_grant(
        self,
        tx_ref: str,
        tenant_id: str,
        currency: str,
        rate: Decimal,
        credits_assigned: int,
    ) -> Dict[str, Any]:
        """
        Record a credit grant from a payment.

        This creates a credit lot with payment metadata.

        Args:
            tx_ref: The transaction reference
            tenant_id: The tenant receiving credits
            currency: Payment currency
            rate: Credits per currency unit
            credits_assigned: Number of credits to assign

        Returns:
            The created credit lot record
        """
        return await self.create_credit_lot(
            tenant_id=tenant_id,
            source="purchase",
            credit_amount=Decimal(credits_assigned),
            valid_from=self._now().isoformat(),
            expires_at=None,  # Purchased credits don't expire
            metadata={
                "tx_ref": tx_ref,
                "currency": currency,
                "rate": str(rate),
                "via": "payment_verification",
            },
            original_tenant_id=tenant_id,
        )

    async def list_active_lots_for_tenant(
        self,
        tenant_id: str,
        as_of: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return tenant's active credit lots with positive balances.

        Uses database-level filtering for efficiency. Lots are ordered
        by earliest expiry first (FIFO consumption order).

        Args:
            tenant_id: The tenant ID
            as_of: Optional datetime to evaluate validity (defaults to now)

        Returns:
            List of active credit lot dicts with id, credit_amount, valid_from, expires_at
        """
        client = await get_async_supabase_client()
        now_iso = (as_of or self._now()).isoformat()

        result = await (
            client.table("credit_lots")
            .select("id, credit_amount, valid_from, expires_at")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .gt("credit_amount", 0)
            .lte("valid_from", now_iso)
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            .order("expires_at", desc=False, nullsfirst=False)
            .execute()
        )

        logger.debug(f"Tenant {tenant_id}: {len(result.data or [])} active lots")
        return result.data or []

    async def sum_user_consumed(
        self,
        *,
        user_id: str,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Sum of credits consumed by a user, optionally scoped to a tenant.

        Uses database-level SUM via RPC for efficiency.
        Falls back to row-by-row fetch if RPC is unavailable.

        Args:
            user_id: The user ID
            tenant_id: Optional tenant to scope consumption
            since: Optional datetime to filter consumption since

        Returns:
            Total credits consumed
        """
        client = await get_async_supabase_client()

        try:
            # Use database-level SUM via RPC (most efficient)
            result = await client.rpc(
                "get_user_consumed_credits",
                {
                    "p_user_id": user_id,
                    "p_tenant_id": tenant_id,
                    "p_since": since.isoformat() if since else None,
                },
            ).execute()

            if result.data is not None:
                total = int(result.data)
                logger.debug(f"User {user_id} consumed {total} credits (via RPC)")
                return total
        except Exception as e:
            logger.debug(f"RPC fallback for user consumption {user_id}: {e}")

        # Fallback: fetch rows and sum in Python
        query = (
            client.table("tenant_credit_consumptions")
            .select("cost")
            .eq("user_id", user_id)
        )

        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        if since:
            query = query.gte("created_at", since.isoformat())

        result = await query.execute()

        total = sum(int(r.get("cost") or 0) for r in (result.data or []))
        logger.debug(f"User {user_id} consumed {total} credits (via fallback)")
        return total

    async def get_user_consumptions(
        self,
        *,
        user_id: str,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch consumption rows for a user, optionally restricted to a tenant.

        Args:
            user_id: The user ID
            tenant_id: Optional tenant to scope consumptions
            since: Optional datetime to filter consumptions since
            limit: Maximum number of rows to return

        Returns:
            List of consumption records
        """
        client = await get_async_supabase_client()

        query = (
            client.table("tenant_credit_consumptions")
            .select(
                "id, created_at, tenant_id, user_id, feature_id, request_id, cost, reason, project_id, workflow_id, metadata"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
        )

        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        if since:
            query = query.gte("created_at", since.isoformat())

        result = await query.execute()
        return result.data or []

    async def get_allocations_for_consumptions(
        self,
        *,
        consumption_ids: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return allocation details for consumptions.

        Args:
            consumption_ids: List of consumption IDs to fetch allocations for

        Returns:
            Dict mapping consumption_id to list of {lot_id, amount_used}
        """
        if not consumption_ids:
            return {}

        client = await get_async_supabase_client()

        result = await (
            client.table("tenant_credit_consumption_lots")
            .select("consumption_id, lot_id, amount_used")
            .in_("consumption_id", consumption_ids)
            .execute()
        )

        by_id: Dict[str, List[Dict[str, Any]]] = {}
        for a in result.data or []:
            by_id.setdefault(a["consumption_id"], []).append(
                {"lot_id": a["lot_id"], "amount_used": int(a.get("amount_used") or 0)}
            )
        return by_id

    async def get_consumed_credits(self, tenant_id: str) -> float:
        """
        Get total credits consumed by this tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            Total credits consumed (from tenant_credit_consumptions)
        """
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("tenant_credit_consumptions")
                .select("cost")
                .eq("tenant_id", tenant_id)
                .execute()
            )
            return sum(float(r.get("cost") or 0) for r in (result.data or []))
        except Exception as e:
            logger.warning(
                f"Error getting consumed credits for tenant {tenant_id}: {e}"
            )
            return 0.0

    async def get_credit_summary(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive credit summary for a tenant.

        OPTIMIZED: Uses asyncio.gather for parallel queries.

        Returns:
            Dict with total_credits (all allocated including expired),
            remaining_credits, consumed_credits
        """
        # Run all queries in parallel
        total_allocated_task = self.get_total_allocated_credits(tenant_id)
        remaining_task = self.get_available_credits(tenant_id)
        consumed_task = self.get_consumed_credits(tenant_id)

        total_allocated, remaining_credits, consumed_credits = await asyncio.gather(
            total_allocated_task, remaining_task, consumed_task
        )

        return {
            "total_credits": total_allocated,  # All credits ever allocated (including expired)
            "remaining_credits": remaining_credits,  # Non-expired available credits
            "consumed_credits": consumed_credits,
        }

    async def list_org_issued_lots(
        self,
        organization_id: str,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List credit lots issued by an organization (original_tenant_id = organization_id).

        Args:
            organization_id: The organization ID
            is_active: Optional filter for active status
            limit: Max items to return
            offset: Pagination offset

        Returns:
            Dict with items and total count
        """
        client = await get_async_supabase_client()

        from postgrest.types import CountMethod

        q = (
            client.table("credit_lots")
            .select("*", count=CountMethod.exact)
            .eq("original_tenant_id", str(organization_id))
            .order("created_at", desc=False)
        )

        if is_active is not None:
            q = q.eq("is_active", is_active)

        resp = await q.range(offset, offset + limit - 1).execute()
        return {"items": resp.data or [], "total": resp.count or 0}

    async def get_org_credit_debug_info(
        self,
        organization_id: str,
    ) -> Dict[str, Any]:
        """
        Get comprehensive credit debug info for an organization.

        OPTIMIZED: Uses parallel queries for all data fetching.

        Args:
            organization_id: Organization ID

        Returns:
            Debug info with credit_lots, consumptions, and available credits
        """
        client = await get_async_supabase_client()

        # Parallel queries for all debug data
        tasks = [
            # Credit lots
            client.table("credit_lots")
            .select("*")
            .eq("tenant_id", organization_id)
            .execute(),
            # Credit consumptions
            client.table("tenant_credit_consumptions")
            .select("*")
            .eq("tenant_id", organization_id)
            .execute(),
            # Available credits calculation
            self.get_available_credits(organization_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        def get_data(r):
            if isinstance(r, Exception):
                return []
            return r.data if hasattr(r, "data") else []

        credit_lots = get_data(results[0])
        consumptions = get_data(results[1])
        available_credits = results[2] if not isinstance(results[2], Exception) else 0

        return {
            "credit_lots": credit_lots,
            "credit_consumptions": consumptions,
            "calculated_available_credits": available_credits,
            "total_lots_count": len(credit_lots),
            "total_consumptions_count": len(consumptions),
        }

    # =========================================================================
    # Credit Reservation Methods
    # =========================================================================

    async def reserve_credits_for_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        amount: Decimal,
        reservation_hours: int = 48,
    ) -> List[Dict[str, Any]]:
        """
        Reserve credits from org's lots for a pending invitation.

        Uses FIFO (earliest expiry first) to select lots to reserve.
        Returns list of lots that were reserved with amounts.

        Args:
            organization_id: The organization tenant ID
            invitation_id: The invitation ID to reserve for
            amount: Amount of credits to reserve
            reservation_hours: Hours until reservation expires (default 48)

        Returns:
            List of dicts with lot_id, reserved_amount, expires_at

        Raises:
            InsufficientCreditsError: If org doesn't have enough unreserved credits
        """
        client = await get_async_supabase_client()
        now = self._now()
        now_iso = now.isoformat()
        reserved_until = (now + timedelta(hours=reservation_hours)).isoformat()

        # Get available (non-reserved, non-expired) credit lots for org
        # Filter at database level:
        # - is_active = true
        # - credit_amount > 0
        # - valid_from <= now
        # - (expires_at is null OR expires_at > now)
        # - (reserved_until is null OR reserved_until <= now)
        result = await (
            client.table("credit_lots")
            .select(
                "id, credit_amount, expires_at, source, valid_from, original_tenant_id, metadata"
            )
            .eq("tenant_id", organization_id)
            .eq("is_active", True)
            .gt("credit_amount", 0)
            .lte("valid_from", now_iso)
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            .or_(f"reserved_until.is.null,reserved_until.lte.{now_iso}")
            .order("expires_at", desc=False, nullsfirst=False)
            .execute()
        )

        available_lots = result.data or []

        # Calculate total available
        total_available = sum(
            Decimal(str(lot["credit_amount"])) for lot in available_lots
        )

        if total_available < amount:
            raise InsufficientCreditsError(
                f"Insufficient credits. Available: {total_available}, Requested: {amount}"
            )

        # Reserve from lots (FIFO - earliest expiry first)
        # Split lots when reserving partial amounts to avoid over-allocation
        remaining = amount
        reserved_lots = []
        lot_ids_to_reserve = []
        lot_balance_updates = []
        reserved_payloads = []

        for lot in available_lots:
            if remaining <= 0:
                break

            lot_credits = Decimal(str(lot["credit_amount"]))
            reserve_amount = min(lot_credits, remaining)

            if reserve_amount == lot_credits:
                lot_ids_to_reserve.append(lot["id"])
                reserved_lots.append(
                    {
                        "lot_id": lot["id"],
                        "reserved_amount": float(reserve_amount),
                        "lot_total": float(lot_credits),
                        "expires_at": lot.get("expires_at"),
                        "source": lot.get("source"),
                    }
                )
            else:
                new_balance = lot_credits - reserve_amount
                lot_balance_updates.append(
                    {
                        "lot_id": lot["id"],
                        "new_balance": float(new_balance),
                    }
                )
                reserved_payloads.append(
                    {
                        "tenant_id": organization_id,
                        "original_tenant_id": lot.get("original_tenant_id")
                        or organization_id,
                        "source": lot.get("source"),
                        "credit_amount": float(reserve_amount),
                        "valid_from": lot.get("valid_from") or now_iso,
                        "expires_at": lot.get("expires_at"),
                        "metadata": {
                            **(lot.get("metadata") or {}),
                            "reservation_type": "invitation",
                        },
                        "created_at": now_iso,
                        "is_active": True,
                        "reserved_until": reserved_until,
                        "reserved_for_invitation_id": invitation_id,
                    }
                )
                reserved_lots.append(
                    {
                        "lot_id": "pending",
                        "reserved_amount": float(reserve_amount),
                        "lot_total": float(reserve_amount),
                        "expires_at": lot.get("expires_at"),
                        "source": lot.get("source"),
                    }
                )

            remaining -= reserve_amount

        tasks = []

        # Reserve whole lots
        if lot_ids_to_reserve:
            tasks.append(
                client.table("credit_lots")
                .update(
                    {
                        "reserved_until": reserved_until,
                        "reserved_for_invitation_id": invitation_id,
                    }
                )
                .in_("id", lot_ids_to_reserve)
                .execute()
            )

        # Reduce balances for partial reservations
        if lot_balance_updates:
            tasks.append(self.batch_update_lot_balances(lot_balance_updates))

        # Insert reserved lots for partial reservations
        if reserved_payloads:
            tasks.append(
                client.table("credit_lots").insert(reserved_payloads).execute()
            )

        if tasks:
            await asyncio.gather(*tasks)

        # Invalidate cache
        await self._invalidate_credit_cache(organization_id)

        logger.info(
            f"Reserved {amount} credits from {len(reserved_lots)} lots "
            f"for invitation {invitation_id} (org: {organization_id})"
        )

        return reserved_lots

    async def release_reservation(
        self,
        invitation_id: str,
    ) -> int:
        """
        Release all credits reserved for an invitation.

        Called when invitation is cancelled or manually released.

        Args:
            invitation_id: The invitation ID to release reservations for

        Returns:
            Number of lots updated
        """
        client = await get_async_supabase_client()

        # First get the org_id (must be before update clears the reservation field)
        lots_result = await (
            client.table("credit_lots")
            .select("tenant_id")
            .eq("reserved_for_invitation_id", invitation_id)
            .limit(1)
            .execute()
        )

        org_id = lots_result.data[0]["tenant_id"] if lots_result.data else None

        # Release reservations
        result = await (
            client.table("credit_lots")
            .update(
                {
                    "reserved_until": None,
                    "reserved_for_invitation_id": None,
                }
            )
            .eq("reserved_for_invitation_id", invitation_id)
            .execute()
        )

        count = len(result.data) if result.data else 0

        # Invalidate cache if we found the org
        if org_id:
            await self._invalidate_credit_cache(org_id)

        logger.info(
            f"Released reservation for invitation {invitation_id}: {count} lots updated"
        )

        return count

    async def get_active_reservations(
        self,
        organization_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all active credit reservations for an organization.

        Returns list of reserved lots with invitation IDs and expiry times.
        Used by admin endpoint to view current reservations.

        Args:
            organization_id: The organization tenant ID

        Returns:
            List of reserved lot info with invitation details
        """
        client = await get_async_supabase_client()
        now_iso = self._now().isoformat()

        result = await (
            client.table("credit_lots")
            .select(
                "id, credit_amount, expires_at, reserved_until, reserved_for_invitation_id"
            )
            .eq("tenant_id", organization_id)
            .eq("is_active", True)
            .gt("reserved_until", now_iso)
            .execute()
        )

        reservations = []
        for lot in result.data or []:
            reservations.append(
                {
                    "lot_id": lot["id"],
                    "credit_amount": float(lot["credit_amount"]),
                    "expires_at": lot.get("expires_at"),
                    "reserved_until": lot["reserved_until"],
                    "invitation_id": lot["reserved_for_invitation_id"],
                }
            )

        return reservations

    async def get_reserved_lots_for_invitation(
        self,
        invitation_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all lots currently reserved for an invitation.

        Used when processing invitation acceptance to know which lots to deduct from.

        Args:
            invitation_id: The invitation ID

        Returns:
            List of lot dicts with id, credit_amount, expires_at, source
        """
        client = await get_async_supabase_client()
        now_iso = self._now().isoformat()

        result = await (
            client.table("credit_lots")
            .select("id, credit_amount, expires_at, source, tenant_id")
            .eq("reserved_for_invitation_id", invitation_id)
            .gt("reserved_until", now_iso)
            .execute()
        )

        return result.data or []

    async def claim_reserved_credits(
        self,
        invitation_id: str,
        target_tenant_id: str,
        source: str,
        expires_at: Optional[str],
        metadata: Dict[str, Any],
        original_tenant_id: str,
    ) -> Dict[str, Any]:
        """
        Convert reserved credits into actual allocation for a user (individual members).

        1. Find reserved lots for invitation
        2. Batch deduct amounts from those lots and clear reservations
        3. Batch create new lot(s) for target tenant

        Args:
            invitation_id: The invitation being accepted
            target_tenant_id: The tenant receiving the credits
            source: Credit source ("grant" or "purchase")
            expires_at: Expiry date for new lot (None for no expiry)
            metadata: Metadata to attach to new lot
            original_tenant_id: The org that originally owns these credits

        Returns:
            Dict with total_claimed, lots_created, lots_affected
        """
        client = await get_async_supabase_client()
        now_iso = self._now().isoformat()

        # Get reserved lots
        reserved_lots = await self.get_reserved_lots_for_invitation(invitation_id)

        if not reserved_lots:
            logger.warning(f"No reserved lots found for invitation {invitation_id}")
            return {
                "total_claimed": 0,
                "lots_created": 0,
                "lots_affected": 0,
            }

        total_claimed = Decimal("0")
        allocations = []
        lot_ids = []

        for lot in reserved_lots:
            lot_amount = Decimal(str(lot["credit_amount"]))
            lot_expires_at = lot.get("expires_at") if source == "grant" else expires_at

            lot_ids.append(lot["id"])

            # Prepare allocation for batch creation
            allocations.append(
                {
                    "tenant_id": target_tenant_id,
                    "credit_amount": lot_amount,
                    "source": lot.get("source", source),
                    "expires_at": lot_expires_at,
                    "original_tenant_id": original_tenant_id,
                    "metadata": {
                        **metadata,
                        "origin_lot_id": lot["id"],
                    },
                }
            )

            total_claimed += lot_amount

        # Run deduction and creation in parallel (they're independent operations)
        org_id = reserved_lots[0]["tenant_id"] if reserved_lots else None
        tasks = []

        # Task 1: Batch update - deduct from org lots and clear reservations
        if lot_ids:
            tasks.append(
                client.table("credit_lots")
                .update(
                    {
                        "credit_amount": 0,
                        "reserved_until": None,
                        "reserved_for_invitation_id": None,
                    }
                )
                .in_("id", lot_ids)
                .execute()
            )

        # Task 2: Batch create credit lots for target tenant
        if allocations:
            tasks.append(
                self.create_credit_lot_batch(
                    allocations=allocations,
                    source=source,
                    valid_from=now_iso,
                    expires_at=expires_at,
                    base_metadata=metadata,
                )
            )

        if tasks:
            await asyncio.gather(*tasks)

        # Invalidate caches in parallel
        cache_tasks = [self._invalidate_credit_cache(target_tenant_id)]
        if org_id:
            cache_tasks.append(self._invalidate_credit_cache(org_id))
        await asyncio.gather(*cache_tasks)

        logger.info(
            f"Claimed {total_claimed} credits for invitation {invitation_id} "
            f"-> tenant {target_tenant_id}"
        )

        return {
            "total_claimed": float(total_claimed),
            "lots_created": len(allocations),
            "lots_affected": len(reserved_lots),
        }

    async def deduct_reserved_credits(
        self,
        invitation_id: str,
    ) -> Dict[str, Any]:
        """
        Deduct reserved credits from org's lots WITHOUT creating a new lot (for team leaders).

        Used when team leader joins - credits are deducted but stored in pending_team_credits
        for later team creation.

        1. Find reserved lots for invitation
        2. Batch deduct amounts from those lots (set to 0) and clear reservations
        3. Return deduction info including expires_at from earliest lot (for grant_org expiry)

        Args:
            invitation_id: The invitation being accepted

        Returns:
            Dict with total_deducted, expires_at (earliest from deducted lots), lots_affected
        """
        client = await get_async_supabase_client()

        # Get reserved lots
        reserved_lots = await self.get_reserved_lots_for_invitation(invitation_id)

        if not reserved_lots:
            logger.warning(f"No reserved lots found for invitation {invitation_id}")
            return {
                "total_deducted": 0,
                "expires_at": None,
                "lots_affected": 0,
            }

        total_deducted = Decimal("0")
        earliest_expiry = None
        lot_ids = []

        for lot in reserved_lots:
            lot_amount = Decimal(str(lot["credit_amount"]))
            lot_expires_at = lot.get("expires_at")

            lot_ids.append(lot["id"])

            # Track earliest expiry for grant_org
            if lot_expires_at:
                if earliest_expiry is None or str(lot_expires_at) < str(
                    earliest_expiry
                ):
                    earliest_expiry = lot_expires_at

            total_deducted += lot_amount

        # Batch update: deduct from org lots and clear reservations (single query with .in_)
        if lot_ids:
            await (
                client.table("credit_lots")
                .update(
                    {
                        "credit_amount": 0,
                        "reserved_until": None,
                        "reserved_for_invitation_id": None,
                    }
                )
                .in_("id", lot_ids)
                .execute()
            )

        # Invalidate org cache
        org_id = reserved_lots[0]["tenant_id"] if reserved_lots else None
        if org_id:
            await self._invalidate_credit_cache(org_id)

        logger.info(
            f"Deducted {total_deducted} reserved credits for invitation {invitation_id}"
        )

        return {
            "total_deducted": float(total_deducted),
            "expires_at": earliest_expiry,
            "lots_affected": len(reserved_lots),
            "source": reserved_lots[0].get("source") if reserved_lots else "grant",
        }

    async def get_unreserved_available_credits(
        self,
        tenant_id: str,
    ) -> float:
        """
        Get available credits excluding reserved amounts.

        This is the "true" available balance that can be spent or reserved.

        Args:
            tenant_id: The tenant ID

        Returns:
            Available credits excluding reserved amounts
        """
        # Just use _fetch_available_credits_from_db with exclude_reserved=True
        return await self._fetch_available_credits_from_db(
            tenant_id, exclude_reserved=True
        )


# Singleton instance for import convenience
_async_credit_service: Optional[AsyncCreditService] = None


def get_async_credit_service() -> AsyncCreditService:
    """Get or create the async credit service singleton."""
    global _async_credit_service
    if _async_credit_service is None:
        _async_credit_service = AsyncCreditService()
    return _async_credit_service
