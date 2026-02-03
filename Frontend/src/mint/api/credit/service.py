"""
Credit service for managing credit operations and consumption tracking.

Integrates with CreditCacheService for:
- Credit balance caching with 1-minute TTL (Requirements 10.1, 10.2)
- Feature cost caching with 1-hour TTL (Requirements 10.4, 10.5)
- Cache invalidation on credit transactions (Requirement 10.3)

**Feature: redis-cache-service**
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ..features.service import FeatureCreditCostService
from ..system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
cost_service = FeatureCreditCostService()


def _get_credit_cache_service():
    """
    Get the credit cache service if available.
    
    Returns None if cache service is not initialized (graceful degradation).
    """
    try:
        from ..cache.credit_cache_service import get_credit_cache_service
        return get_credit_cache_service()
    except ImportError:
        return None


def _run_async(coro):
    """
    Run an async coroutine from sync code.
    
    Handles the case where we're already in an event loop.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, create a task
        return asyncio.ensure_future(coro)
    except RuntimeError:
        # No running loop, create one
        return asyncio.run(coro)


class InsufficientCreditsError(Exception):
    pass


class InvalidConsumptionRequest(Exception):
    pass


class CreditService:
    """Service for tenant management operations"""

    def __init__(self, use_service_role: bool = True):
        """Initialize tenant service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_int_units(x: Decimal | float | int | str | None) -> int:
        """Coerce to integer credit units."""
        if x is None:
            return 0
        return int(Decimal(str(x)))

    def _list_active_lots(
        self, tenant_id: str, as_of: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Return tenant's active lots (positive balance, valid_from <= now, not expired),
        ordered by earliest expiry first, non-expiring last.
        """
        now = (as_of or self._now()).isoformat()

        # Pull candidate lots ordered by expiry (NULLS LAST puts non-expiring at the end)
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering is done in Python below
        lots_res = (
            self.supabase.table("credit_lots")
            .select("id, credit_amount, valid_from, expires_at")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .lte("valid_from", now)
            .order("expires_at", desc=False, nullsfirst=False)
            .execute()
        )
        lots = lots_res.data or []

        active: List[Dict[str, Any]] = []
        for lot in lots:
            # Normalize datetimes
            vf = lot.get("valid_from")
            ea = lot.get("expires_at")
            valid_from_ok = (vf is None) or (str(vf) <= now)
            # Filter: expires_at is null OR expires_at > now (done in Python since .or_() not supported)
            not_expired = (ea is None) or (str(ea) > now)
            amount = Decimal(str(lot.get("credit_amount") or 0))
            if valid_from_ok and not_expired and amount > 0:
                active.append(lot)

        return active

    def _insert_consumption(
        self,
        *,
        tenant_id: str,
        user_id: str,
        cost: int,
        feature_id: Optional[str],
        request_id: Optional[str],
        reason: Optional[str],
        project_id: Optional[str],
        workflow_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Insert a row in tenant_credit_consumptions, return the row. Idempotent on (tenant_id, request_id)."""
        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "feature_id": feature_id,
            "request_id": request_id,
            "cost": int(cost),
            "reason": reason,
            "project_id": project_id,
            "workflow_id": workflow_id,
            "metadata": metadata or {},
        }

        # If request_id supplied, check idempotency up front
        if request_id:
            existing = (
                self.supabase.table("tenant_credit_consumptions")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("request_id", request_id)
                .execute()
            )
            if existing and existing.data:
                return existing.data[0]

        try:
            # Insert the record
            self.supabase.table("tenant_credit_consumptions").insert(payload).execute()

            # Query back the inserted record
            query = (
                self.supabase.table("tenant_credit_consumptions")
                .select("*")
                .eq("tenant_id", tenant_id)
            )
            if request_id:
                query = query.eq("request_id", request_id)
            else:
                # If no request_id, use other fields to identify the record
                query = query.eq("user_id", user_id).eq("cost", int(cost))
                if feature_id:
                    query = query.eq("feature_id", feature_id)

            result = query.order("created_at", desc=True).limit(1).execute()
            rows = (result.data or []) if result else []
            if not rows:
                # extremely rare, but don't return None
                raise RuntimeError("Insert did not return a row for tenant_credit_consumptions")
            return rows[0]
        except Exception as e:
            # A concurrent insert may have won the unique (tenant_id, request_id) race.
            if request_id:
                again = (
                    self.supabase.table("tenant_credit_consumptions")
                    .select("*")
                    .eq("tenant_id", tenant_id)
                    .eq("request_id", request_id)
                    .maybe_single()
                    .execute()
                )
                if again and again.data:
                    return again.data
            # Otherwise bubble up
            raise

    def _record_allocation(
        self, consumption_id: str, lot_id: str, amount_used: int
    ) -> None:
        self.supabase.table("tenant_credit_consumption_lots").insert(
            {
                "consumption_id": consumption_id,
                "lot_id": lot_id,
                "amount_used": int(amount_used),
            }
        ).execute()

    def get_available_credits(self, tenant_id: str, skip_cache: bool = False) -> float:
        """
        Sum of all non-expired credit lots for this tenant.
        
        Uses Redis cache with 1-minute TTL to reduce database queries.
        
        Args:
            tenant_id: The tenant ID
            skip_cache: If True, bypass cache and fetch from database
            
        Returns:
            Total available credits
            
        **Validates: Requirements 10.1, 10.2**
        """
        logger.debug(f"Getting available credits for tenant: {tenant_id}")
        
        # Try cache first (unless skip_cache is True)
        if not skip_cache:
            cache_service = _get_credit_cache_service()
            if cache_service:
                try:
                    # Run async cache lookup
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        # We're in an async context - this shouldn't happen in sync code
                        # Fall through to database query
                    except RuntimeError:
                        # No running loop, safe to use asyncio.run
                        cached_balance = asyncio.run(
                            cache_service.get_credit_balance(tenant_id)
                        )
                        if cached_balance is not None:
                            logger.debug(f"Cache hit for tenant {tenant_id}: {cached_balance}")
                            return cached_balance
                except Exception as e:
                    logger.warning(f"Cache lookup failed for tenant {tenant_id}: {e}")
        
        # Fetch from database
        balance = self._fetch_available_credits_from_db(tenant_id)
        
        # Cache the result
        if not skip_cache:
            cache_service = _get_credit_cache_service()
            if cache_service:
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        # We're in an async context - skip caching
                    except RuntimeError:
                        asyncio.run(
                            cache_service.set_credit_balance(tenant_id, balance)
                        )
                        logger.debug(f"Cached balance for tenant {tenant_id}: {balance}")
                except Exception as e:
                    logger.warning(f"Cache set failed for tenant {tenant_id}: {e}")
        
        return balance
    
    def _fetch_available_credits_from_db(self, tenant_id: str) -> float:
        """
        Fetch available credits directly from database.
        
        This is the internal method that performs the actual database query.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering is done in Python below
        res = (
            self.supabase.table("credit_lots")
            .select("id, credit_amount, expires_at, created_at, source, is_active")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)  # Only include active credit lots
            .lte("valid_from", now_iso)
            .execute()
        )
        
        logger.debug(f"Found {len(res.data or [])} credit lots for tenant {tenant_id}")
        
        total = 0
        valid_lots = 0
        expired_lots = 0
        for row in res.data or []:
            lot_id = row.get("id", "unknown")
            expires_at = row.get("expires_at")
            credit_amount = float(row.get("credit_amount", 0))
            source = row.get("source", "unknown")
            
            # Skip inactive lots (already filtered by query, but double-check)
            is_active = row.get("is_active", True)
            if not is_active:
                logger.debug(f"Skipping inactive lot {lot_id}")
                continue
                
            if not expires_at:
                # No expiration date, credit is valid
                total += credit_amount
                valid_lots += 1
                logger.debug(f"Lot {lot_id}: {credit_amount} credits (no expiry) - VALID")
            else:
                try:
                    # More robust datetime comparison
                    if isinstance(expires_at, str):
                        if expires_at.endswith('Z'):
                            expires_at = expires_at[:-1] + '+00:00'
                        elif '+' not in expires_at and 'T' in expires_at:
                            expires_at = expires_at + '+00:00'
                        expires_dt = datetime.fromisoformat(expires_at)
                    else:
                        expires_dt = expires_at
                    
                    if expires_dt > now:
                        total += credit_amount
                        valid_lots += 1
                        logger.debug(f"Lot {lot_id}: {credit_amount} credits (expires {expires_dt}) - VALID")
                    else:
                        expired_lots += 1
                        logger.debug(f"Lot {lot_id}: {credit_amount} credits (expires {expires_dt}) - EXPIRED")
                        
                except (ValueError, TypeError) as e:
                    # If datetime parsing fails, log and skip this credit lot
                    logger.warning(f"Could not parse expires_at '{expires_at}' for lot {lot_id}: {e}")
                    expired_lots += 1
                    continue
        
        logger.info(f"Tenant {tenant_id}: {total} total credits from {valid_lots} valid lots ({expired_lots} expired)")
        return total

    def get_unreserved_available_credits(self, tenant_id: str) -> float:
        """
        Get available credits excluding reserved amounts.

        This is the "true" available balance that can be spent or reserved.
        Excludes credits that are reserved for pending invitations.

        Args:
            tenant_id: The tenant ID

        Returns:
            Available credits excluding reserved amounts
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Fetch all active lots with reserved_until info
        res = (
            self.supabase.table("credit_lots")
            .select("id, credit_amount, expires_at, reserved_until")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .execute()
        )

        total = 0.0
        for row in res.data or []:
            expires_at = row.get("expires_at")
            reserved_until = row.get("reserved_until")
            credit_amount = float(row.get("credit_amount", 0))

            # Check if expired
            if expires_at is not None:
                try:
                    if isinstance(expires_at, str):
                        if expires_at.endswith('Z'):
                            expires_at = expires_at[:-1] + '+00:00'
                        elif '+' not in expires_at and 'T' in expires_at:
                            expires_at = expires_at + '+00:00'
                        expires_dt = datetime.fromisoformat(expires_at)
                    else:
                        expires_dt = expires_at

                    if expires_dt <= now:
                        continue  # Expired
                except (ValueError, TypeError):
                    continue  # Skip if parsing fails

            # Check if reserved
            if reserved_until is not None:
                try:
                    if isinstance(reserved_until, str):
                        if reserved_until.endswith('Z'):
                            reserved_until = reserved_until[:-1] + '+00:00'
                        elif '+' not in reserved_until and 'T' in reserved_until:
                            reserved_until = reserved_until + '+00:00'
                        reserved_dt = datetime.fromisoformat(reserved_until)
                    else:
                        reserved_dt = reserved_until

                    if reserved_dt > now:
                        continue  # Reserved
                except (ValueError, TypeError):
                    pass  # If parsing fails, assume not reserved

            total += credit_amount

        return total

    def consume_feature(
        self,
        *,
        tenant_id: str,
        user_id: str,
        feature_id: str,
        plan_type: str,
        request_id: Optional[str] = None,
        reason: Optional[str] = None,
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        as_of: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Resolve a feature's cost and consume credits accordingly.
        
        Uses cached feature costs when available.
        
        Returns: {"consumption": <row>, "allocations": [{"lot_id": ..., "amount_used": ...}, ...]}
        
        **Validates: Requirements 10.4**
        """
        as_of = as_of or self._now()
        
        # Use cached feature cost lookup
        resolved = self._get_feature_cost_cached(feature_id, plan_type, as_of)
        if not resolved:
            raise InvalidConsumptionRequest(
                f"Unknown feature_id={feature_id!r} for plan={plan_type!r}"
            )

        cost_int = self._to_int_units(resolved["credit_cost"])
        return self.deduct_credits(
            tenant_id=tenant_id,
            user_id=user_id,
            amount=Decimal(cost_int),
            feature_id=feature_id,
            request_id=request_id,
            reason=reason,
            project_id=project_id,
            workflow_id=workflow_id,
            metadata={**(metadata or {}), "cost_source": resolved.get("source")},
            as_of=as_of,
        )

    def deduct_credits(
        self,
        *,
        tenant_id: str,
        user_id: str,
        amount: Decimal,
        feature_id: Optional[str] = None,
        request_id: Optional[str] = None,
        reason: Optional[str] = None,
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        as_of: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Deduct `amount` credits from tenant's active lots (earliest expiry first),
        write a row into tenant_credit_consumptions, and record per-lot allocations
        in tenant_credit_consumption_lots.

        Idempotent when `request_id` is provided (unique (tenant_id, request_id)).
        Returns: {"consumption": <row>, "allocations": [{"lot_id": ..., "amount_used": ...}, ...]}
        """
        if amount is None:
            raise InvalidConsumptionRequest(
                "`amount` is required (use consume_feature() to resolve via feature/plan)."
            )

        as_of = as_of or self._now()
        cost_int = self._to_int_units(amount)
        if cost_int <= 0:
            raise InvalidConsumptionRequest(
                "`amount` must be a positive integer number of credits."
            )

        # Idempotency: if a consumption already exists for this request, return it and its allocations.
        if request_id:
            existing = (
                self.supabase.table("tenant_credit_consumptions")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("request_id", request_id)
                .execute()
            )
            if existing and existing.data:
                consumption = existing.data[0]
                allocations_res = (
                    self.supabase.table("tenant_credit_consumption_lots")
                    .select("lot_id, amount_used")
                    .eq("consumption_id", consumption["id"])
                    .execute()
                )
                allocations = allocations_res.data if allocations_res else []
                return {"consumption": consumption, "allocations": allocations}

        # Check availability before we start mutating
        available = self._to_int_units(self.get_available_credits(tenant_id))
        if available < cost_int:
            raise InsufficientCreditsError(
                f"Insufficient credits: have {available}, need {cost_int}."
            )

        # Create the consumption record (after availability check; still okay if concurrent insert races)
        consumption = self._insert_consumption(
            tenant_id=tenant_id,
            user_id=user_id,
            feature_id=feature_id,
            request_id=request_id,
            cost=cost_int,
            reason=reason,
            project_id=project_id,
            workflow_id=workflow_id,
            metadata=metadata,
        )

        # Allocate from lots
        remaining = cost_int
        allocations: List[Dict[str, Any]] = []
        active_lots = self._list_active_lots(tenant_id, as_of=as_of)

        for lot in active_lots:
            if remaining <= 0:
                break

            lot_id = lot["id"]
            lot_balance_dec = Decimal(str(lot.get("credit_amount") or 0))
            # Only integer units can be consumed
            lot_available_units = min(self._to_int_units(lot_balance_dec), remaining)
            if lot_available_units <= 0:
                continue

            new_balance = lot_balance_dec - Decimal(lot_available_units)

            # Update lot balance
            self.supabase.table("credit_lots").update(
                {"credit_amount": float(new_balance)}
            ).eq("id", lot_id).execute()

            # Record allocation
            self._record_allocation(
                consumption_id=consumption["id"],
                lot_id=lot_id,
                amount_used=lot_available_units,
            )

            allocations.append({"lot_id": lot_id, "amount_used": lot_available_units})
            remaining -= lot_available_units

        # Safety check
        if remaining > 0:
            # Shouldn't happen after availability check; surface clearly if it does.
            logger.error(
                "Credit allocation shortfall: tenant=%s expected_cost=%d remaining=%d",
                tenant_id,
                cost_int,
                remaining,
            )
            raise RuntimeError(f"Failed to allocate full cost. Remaining: {remaining}")

        # Invalidate credit balance cache after successful consumption
        # Requirement 10.3: Cache invalidation on credit consumption
        self._invalidate_credit_cache(tenant_id)

        return {"consumption": consumption, "allocations": allocations}
    
    def _invalidate_credit_cache(self, tenant_id: str) -> None:
        """
        Invalidate the credit balance cache for a tenant.
        
        Called after credit consumption or grant operations.
        
        **Validates: Requirements 10.3**
        """
        cache_service = _get_credit_cache_service()
        if cache_service:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context - skip cache invalidation
                    # The cache will expire naturally via TTL
                    logger.debug(f"Skipping cache invalidation in async context for tenant {tenant_id}")
                except RuntimeError:
                    asyncio.run(
                        cache_service.invalidate_credit_balance(tenant_id)
                    )
                    logger.info(f"Invalidated credit cache for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Cache invalidation failed for tenant {tenant_id}: {e}")

    def create_credit_lot(
        self,
        tenant_id: str,
        source: str,
        credit_amount: Decimal,
        valid_from: str,
        expires_at: str | None,
        metadata: dict,
        original_tenant_id: str,
    ):
        """
        Create a new credit lot.
        
        Invalidates the credit balance cache after creation.
        
        **Validates: Requirements 10.3**
        """
        payload = {
            "tenant_id": tenant_id,
            "original_tenant_id": original_tenant_id,
            "source": source,
            "credit_amount": float(credit_amount),
            "valid_from": valid_from,
            "expires_at": expires_at,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.supabase.table("credit_lots").insert(payload).execute()
        
        # Invalidate credit balance cache after grant
        # Requirement 10.3: Cache invalidation on credit grant
        self._invalidate_credit_cache(tenant_id)

    def has_sufficient_credits_for_feature(
        self,
        tenant_id: str,
        feature_id: str,
        plan_type: str,
        as_of: Optional[datetime] = None,
    ) -> bool:
        """
        Compare the tenant's available credits to the resolved feature cost.
        
        Uses caching for both credit balance and feature cost lookups.
        
        **Validates: Requirements 10.1, 10.4**
        """
        # Try to get feature cost from cache first
        resolved = self._get_feature_cost_cached(feature_id, plan_type, as_of)
        if not resolved:
            return False  # feature not found

        required = Decimal(str(resolved["credit_cost"]))
        available = Decimal(str(self.get_available_credits(tenant_id)))
        return available >= required
    
    def _get_feature_cost_cached(
        self,
        feature_id: str,
        plan_type: str,
        as_of: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get feature cost with caching.
        
        Uses 1-hour TTL for feature costs since they rarely change.
        
        **Validates: Requirements 10.4, 10.5**
        """
        cache_service = _get_credit_cache_service()
        
        # Try cache first
        if cache_service:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context - skip cache
                except RuntimeError:
                    cached_cost = asyncio.run(
                        cache_service.get_feature_cost(feature_id, plan_type)
                    )
                    if cached_cost is not None:
                        logger.debug(f"Feature cost cache hit for {feature_id}:{plan_type}")
                        return cached_cost
            except Exception as e:
                logger.warning(f"Feature cost cache lookup failed: {e}")
        
        # Fetch from database
        resolved = cost_service.resolve_cost(str(feature_id), plan_type, as_of)
        
        # Cache the result
        if resolved and cache_service:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context - skip caching
                except RuntimeError:
                    asyncio.run(
                        cache_service.set_feature_cost(feature_id, plan_type, resolved)
                    )
                    logger.debug(f"Cached feature cost for {feature_id}:{plan_type}")
            except Exception as e:
                logger.warning(f"Feature cost cache set failed: {e}")
        
        return resolved

    def list_active_lots_for_tenant(
        self, tenant_id: str, as_of: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Public wrapper that returns active credit lots for a tenant (remaining balances)."""
        return self._list_active_lots(tenant_id=tenant_id, as_of=as_of)

    def get_tenant_active_total(self, tenant_id: str) -> float:
        """Convenience total of active (non-expired, active) credits for tenant."""
        # `get_available_credits` already aligns with remaining balances; keep using it.
        return float(self.get_available_credits(tenant_id))

    def get_consumed_credits(self, tenant_id: str) -> float:
        """
        Get total credits consumed by this tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Total credits consumed (from tenant_credit_consumptions)
        """
        try:
            res = (
                self.supabase.table("tenant_credit_consumptions")
                .select("cost")
                .eq("tenant_id", tenant_id)
                .execute()
            )
            return sum(float(r.get("cost") or 0) for r in (res.data or []))
        except Exception as e:
            logger.warning(f"Error getting consumed credits for tenant {tenant_id}: {e}")
            return 0.0

    def get_credits_allocated_out(self, tenant_id: str) -> Dict[str, float]:
        """
        Get credits that this tenant has allocated OUT to other tenants (for organizations).
        
        This tracks credits that were transferred from this organization to members/teams.
        
        Args:
            tenant_id: The organization tenant ID
            
        Returns:
            Dict with:
            - allocated_out_remaining: Credits still remaining with recipients
            - allocated_out_consumed: Credits consumed by recipients
            - total_allocated_out: Total originally allocated out
        """
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            # Find credit lots where this tenant is the original source but current owner is different
            # These are credits transferred OUT to members/teams
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Expiration filtering is done in Python below
            allocated_lots = (
                self.supabase.table("credit_lots")
                .select("id, tenant_id, credit_amount, is_active, expires_at")
                .eq("original_tenant_id", tenant_id)
                .neq("tenant_id", tenant_id)
                .eq("is_active", True)
                .lte("valid_from", now_iso)
                .execute()
            )
            
            allocated_out_remaining = 0.0
            recipient_tenant_ids = set()
            
            for lot in (allocated_lots.data or []):
                # Filter: expires_at is null OR expires_at > now
                expires_at = lot.get("expires_at")
                if expires_at is not None and str(expires_at) <= now_iso:
                    continue  # Skip expired lots
                # Sum current remaining in allocated lots
                allocated_out_remaining += float(lot.get("credit_amount") or 0)
                recipient_tenant_ids.add(lot["tenant_id"])
            
            # Get consumptions from recipients (credits they've used from allocated lots)
            allocated_out_consumed = 0.0
            if recipient_tenant_ids:
                for recipient_id in recipient_tenant_ids:
                    consumed = self.get_consumed_credits(recipient_id)
                    allocated_out_consumed += consumed
            
            total_allocated_out = allocated_out_remaining + allocated_out_consumed
            
            return {
                "allocated_out_remaining": allocated_out_remaining,
                "allocated_out_consumed": allocated_out_consumed,
                "total_allocated_out": total_allocated_out,
                "recipient_count": len(recipient_tenant_ids)
            }
        except Exception as e:
            logger.warning(f"Error getting allocated out credits for tenant {tenant_id}: {e}")
            return {
                "allocated_out_remaining": 0.0,
                "allocated_out_consumed": 0.0,
                "total_allocated_out": 0.0,
                "recipient_count": 0
            }

    def get_credit_summary(self, tenant_id: str, is_organization: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive credit summary for a tenant.
        
        This is the CORRECT way to calculate credits:
        - remaining_credits: Current balance in credit_lots (available to use)
        - consumed_credits: Credits used by this tenant (from consumptions table)
        - allocated_out_credits: For orgs, credits sent to members (NOT counted as consumed)
        - total_credits: Original total = remaining + consumed + allocated_out
        
        Args:
            tenant_id: The tenant ID
            is_organization: Whether this is an organization (affects allocated_out calculation)
            
        Returns:
            Dict with total_credits, remaining_credits, consumed_credits, allocated_out_credits
        """
        # Get remaining credits (current balance in lots)
        remaining_credits = self.get_available_credits(tenant_id)
        
        # Get consumed credits
        consumed_credits = self.get_consumed_credits(tenant_id)
        
        # For organizations, also get credits allocated to members
        allocated_out_credits = 0.0
        allocated_out_details = None
        
        if is_organization:
            allocated_out_details = self.get_credits_allocated_out(tenant_id)
            allocated_out_credits = allocated_out_details.get("total_allocated_out", 0.0)
        
        # Calculate total: what was originally granted to this tenant
        # Total = Remaining + Consumed + Allocated Out
        total_credits = remaining_credits + consumed_credits + allocated_out_credits
        
        summary = {
            "total_credits": total_credits,
            "remaining_credits": remaining_credits,
            "consumed_credits": consumed_credits,
            "allocated_out_credits": allocated_out_credits,
        }
        
        if allocated_out_details:
            summary["allocated_out_details"] = allocated_out_details
        
        logger.debug(
            f"Credit summary for tenant {tenant_id}: "
            f"total={total_credits}, remaining={remaining_credits}, "
            f"consumed={consumed_credits}, allocated_out={allocated_out_credits}"
        )
        
        return summary

    def get_credits_for_workspace_display(
        self, 
        tenant_id: str, 
        tenant_type: str = "individual"
    ) -> Dict[str, float]:
        """
        Get credits formatted for workspace display.
        
        This returns the correct total and remaining for UI display:
        - For individuals/teams: total = remaining + consumed
        - For organizations: total = remaining + consumed + allocated_to_members
        
        Args:
            tenant_id: The tenant ID
            tenant_type: "individual", "team", or "organization"
            
        Returns:
            Dict with total_credits and remaining_credits for display
        """
        is_org = tenant_type == "organization"
        summary = self.get_credit_summary(tenant_id, is_organization=is_org)
        
        return {
            "total_credits": summary["total_credits"],
            "remaining_credits": summary["remaining_credits"]
        }

    def sum_user_consumed(
        self,
        *,
        user_id: str,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Sum of costs the user has consumed, optionally scoped to a tenant and/or since timestamp."""
        q = (
            self.supabase.table("tenant_credit_consumptions")
            .select("cost")
            .eq("user_id", user_id)
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        if since:
            q = q.gte("created_at", since.isoformat())
        res = q.execute()
        return sum(int(r.get("cost") or 0) for r in (res.data or []))

    def get_user_consumptions(
        self,
        *,
        user_id: str,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch consumption rows for a user, optionally restricted to a tenant."""
        q = (
            self.supabase.table("tenant_credit_consumptions")
            .select(
                "id, created_at, tenant_id, user_id, feature_id, request_id, cost, reason, project_id, workflow_id, metadata"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        if since:
            q = q.gte("created_at", since.isoformat())
        res = q.execute()
        return res.data or []

    def get_allocations_for_consumptions(
        self, *, consumption_ids: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return {consumption_id: [{lot_id, amount_used}, ...]} for the given list."""
        if not consumption_ids:
            return {}
        res = (
            self.supabase.table("tenant_credit_consumption_lots")
            .select("consumption_id, lot_id, amount_used")
            .in_("consumption_id", consumption_ids)
            .execute()
        )
        by_id: Dict[str, List[Dict[str, Any]]] = {}
        for a in res.data or []:
            by_id.setdefault(a["consumption_id"], []).append(
                {"lot_id": a["lot_id"], "amount_used": int(a.get("amount_used") or 0)}
            )
        return by_id

    def refund_consumption(
        self,
        *,
        consumption_id: str,
        reason: str,
        refunded_by_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a credit consumption by restoring credits back to original lots.

        This preserves the original expiration dates of the credit lots.

        Args:
            consumption_id: ID of the consumption to refund
            reason: Reason for the refund
            refunded_by_user_id: User who initiated the refund

        Returns:
            Dict with refund details including total refunded and affected lots

        Raises:
            InvalidConsumptionRequest: If consumption not found or already refunded
        """
        # Get the consumption record
        consumption_res = (
            self.supabase.table("tenant_credit_consumptions")
            .select("*")
            .eq("id", consumption_id)
            .limit(1)
            .execute()
        )

        if not consumption_res.data:
            raise InvalidConsumptionRequest(f"Consumption {consumption_id} not found")

        consumption = consumption_res.data[0]

        # Check if already refunded (check metadata for refund flag)
        if consumption.get("metadata", {}).get("refunded"):
            raise InvalidConsumptionRequest(f"Consumption {consumption_id} already refunded")

        # Get allocations for this consumption
        allocations_res = (
            self.supabase.table("tenant_credit_consumption_lots")
            .select("lot_id, amount_used")
            .eq("consumption_id", consumption_id)
            .execute()
        )

        allocations = allocations_res.data or []
        total_refunded = 0

        # Restore credits to each original lot
        for allocation in allocations:
            lot_id = allocation["lot_id"]
            amount_used = int(allocation.get("amount_used") or 0)

            if amount_used <= 0:
                continue

            # Get current lot balance
            lot_res = (
                self.supabase.table("credit_lots")
                .select("credit_amount")
                .eq("id", lot_id)
                .limit(1)
                .execute()
            )

            if lot_res.data:
                current_balance = Decimal(str(lot_res.data[0].get("credit_amount") or 0))
                new_balance = current_balance + Decimal(amount_used)

                # Update lot balance
                self.supabase.table("credit_lots").update(
                    {"credit_amount": float(new_balance)}
                ).eq("id", lot_id).execute()

                total_refunded += amount_used
                logger.info(f"Refunded {amount_used} credits to lot {lot_id}")

        # Mark consumption as refunded in metadata
        existing_metadata = consumption.get("metadata") or {}
        existing_metadata["refunded"] = True
        existing_metadata["refund_reason"] = reason
        existing_metadata["refunded_at"] = self._now().isoformat()
        existing_metadata["refunded_by_user_id"] = refunded_by_user_id

        self.supabase.table("tenant_credit_consumptions").update(
            {"metadata": existing_metadata}
        ).eq("id", consumption_id).execute()

        logger.info(
            f"Refunded consumption {consumption_id}: {total_refunded} credits restored"
        )
        
        # Invalidate credit balance cache after refund
        # Requirement 10.3: Cache invalidation on credit transaction
        tenant_id = consumption.get("tenant_id")
        if tenant_id:
            self._invalidate_credit_cache(tenant_id)

        return {
            "consumption_id": consumption_id,
            "total_refunded": total_refunded,
            "allocations_refunded": len(allocations),
            "reason": reason,
        }

    def find_consumption_by_metadata(
        self,
        *,
        tenant_id: str,
        metadata_key: str,
        metadata_value: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a consumption record by matching a metadata field.

        Args:
            tenant_id: Tenant ID to search within
            metadata_key: Key in metadata JSON to match
            metadata_value: Value to match

        Returns:
            Consumption record or None if not found
        """
        # Use Supabase JSON containment filter
        res = (
            self.supabase.table("tenant_credit_consumptions")
            .select("*")
            .eq("tenant_id", tenant_id)
            .contains("metadata", {metadata_key: metadata_value})
            .limit(1)
            .execute()
        )

        return res.data[0] if res.data else None

    # ============================================================
    # PREMIUM FEATURE ACCESS - Credit Type Differentiation
    # ============================================================

    # Credit sources that allow premium feature access (download, etc.)
    PAID_CREDIT_SOURCES = ("purchase", "grant", "payment", "top_up", "transfer", "waitlist_bonus")

    def has_paid_credits(self, tenant_id: str) -> bool:
        """
        Check if tenant has any non-trial credits (purchased or granted).
        
        This is used to gate premium features like PDF downloads that are
        only available to users who have purchased credits or received grants,
        not to free trial users.
        
        Args:
            tenant_id: The tenant ID to check
            
        Returns:
            True if tenant has any active, non-expired, non-trial credits
        """
        logger.debug(f"Checking paid credits for tenant: {tenant_id}")
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering is done in Python below
        res = (
            self.supabase.table("credit_lots")
            .select("id, credit_amount, expires_at, source, is_active")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .execute()
        )

        for row in res.data or []:
            source = row.get("source", "")
            credit_amount = float(row.get("credit_amount", 0))
            
            # Skip trial credits
            if source == "trial":
                continue
            
            # Skip lots with zero balance
            if credit_amount <= 0:
                continue
            
            # Check expiration
            expires_at = row.get("expires_at")
            if not expires_at:
                # No expiration - this is a valid paid credit
                logger.info(f"Tenant {tenant_id} has paid credits (source: {source}, no expiry)")
                return True
            
            try:
                # Parse expiration datetime
                if isinstance(expires_at, str):
                    if expires_at.endswith('Z'):
                        expires_at = expires_at[:-1] + '+00:00'
                    elif '+' not in expires_at and 'T' in expires_at:
                        expires_at = expires_at + '+00:00'
                    expires_dt = datetime.fromisoformat(expires_at)
                else:
                    expires_dt = expires_at
                
                if expires_dt > now:
                    # Not expired - this is a valid paid credit
                    logger.info(f"Tenant {tenant_id} has paid credits (source: {source}, expires: {expires_dt})")
                    return True
                    
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse expires_at for lot: {e}")
                continue
        
        logger.info(f"Tenant {tenant_id} has NO paid credits (trial only or no credits)")
        return False

    def get_credit_breakdown(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of tenant's credits by source type.
        
        Args:
            tenant_id: The tenant ID to check
            
        Returns:
            Dictionary with credit breakdown:
            {
                "total_credits": float,
                "trial_credits": float,
                "paid_credits": float,
                "has_paid_credits": bool,
                "credit_sources": {"trial": float, "purchase": float, "grant": float, ...}
            }
        """
        logger.debug(f"Getting credit breakdown for tenant: {tenant_id}")
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering is done in Python below
        res = (
            self.supabase.table("credit_lots")
            .select("id, credit_amount, expires_at, source, is_active")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .lte("valid_from", now_iso)
            .execute()
        )

        breakdown = {
            "total_credits": 0.0,
            "trial_credits": 0.0,
            "paid_credits": 0.0,
            "has_paid_credits": False,
            "credit_sources": {}
        }
        
        for row in res.data or []:
            source = row.get("source", "unknown")
            credit_amount = float(row.get("credit_amount", 0))
            
            # Skip lots with zero balance
            if credit_amount <= 0:
                continue
            
            # Check expiration
            expires_at = row.get("expires_at")
            is_valid = False
            
            if not expires_at:
                is_valid = True
            else:
                try:
                    if isinstance(expires_at, str):
                        if expires_at.endswith('Z'):
                            expires_at = expires_at[:-1] + '+00:00'
                        elif '+' not in expires_at and 'T' in expires_at:
                            expires_at = expires_at + '+00:00'
                        expires_dt = datetime.fromisoformat(expires_at)
                    else:
                        expires_dt = expires_at
                    
                    is_valid = expires_dt > now
                except (ValueError, TypeError):
                    continue
            
            if not is_valid:
                continue
            
            # Add to totals
            breakdown["total_credits"] += credit_amount
            
            if source == "trial":
                breakdown["trial_credits"] += credit_amount
            else:
                breakdown["paid_credits"] += credit_amount
                breakdown["has_paid_credits"] = True
            
            # Track by source
            if source not in breakdown["credit_sources"]:
                breakdown["credit_sources"][source] = 0.0
            breakdown["credit_sources"][source] += credit_amount
        
        logger.info(
            f"Tenant {tenant_id} credit breakdown: "
            f"total={breakdown['total_credits']}, "
            f"trial={breakdown['trial_credits']}, "
            f"paid={breakdown['paid_credits']}"
        )
        
        return breakdown
