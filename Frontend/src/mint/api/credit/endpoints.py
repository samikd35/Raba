import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth_v2.utils import get_current_user
from .models import (ConsumptionAllocationOut, ConsumptionOut,
                     ConsumptionsResponse, CreditLotOut,
                     CreditsSummaryResponse)
from .service import CreditService
from .async_service import get_async_credit_service

router = APIRouter(prefix="/me", tags=["credits"])

service = CreditService()


@router.get("/credits", response_model=CreditsSummaryResponse)
async def get_my_credits(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Current tenant's remaining credits (by lot with expiration) + this user's total consumed in this tenant.

    Optimized with parallel async queries for better performance.
    """
    user_id = current_user.get("user_id") or current_user.get("id")
    tenant_id = current_user.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=401, detail="Missing user_id or tenant_id in auth context"
        )

    # Get async service and execute both queries in parallel
    async_service = get_async_credit_service()

    lots, user_total_consumed = await asyncio.gather(
        async_service.list_active_lots_for_tenant(tenant_id=tenant_id),
        async_service.sum_user_consumed(user_id=user_id, tenant_id=tenant_id),
    )

    # Process lots
    lots_out: List[CreditLotOut] = []
    tenant_total = 0.0
    for lot in lots:
        amt = float(lot.get("credit_amount") or 0.0)
        tenant_total += amt
        lots_out.append(
            CreditLotOut(
                id=lot["id"],
                credit_amount=amt,
                valid_from=lot.get("valid_from"),
                expires_at=lot.get("expires_at"),
            )
        )

    return CreditsSummaryResponse(
        tenant_id=tenant_id,
        lots=lots_out,
        tenant_total_active_credits=tenant_total,
        user_total_consumed_in_tenant=user_total_consumed,
    )


@router.get("/consumptions", response_model=ConsumptionsResponse)
async def get_my_consumptions_in_current_tenant(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    include_allocations: bool = Query(default=True),
    since: Optional[datetime] = Query(
        default=None, description="Filter: created_at >= since"
    ),
):
    """
    This user's consumption rows in the *current tenant* (from current_user.tenant_id).

    Optimized with async database queries.
    """
    user_id = current_user.get("user_id") or current_user.get("id")
    tenant_id = current_user.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=401, detail="Missing user_id or tenant_id in auth context"
        )

    async_service = get_async_credit_service()

    rows = await async_service.get_user_consumptions(
        user_id=user_id, tenant_id=tenant_id, since=since, limit=limit
    )

    allocations_by = {}
    if include_allocations and rows:
        ids = [r["id"] for r in rows]
        allocations_by = await async_service.get_allocations_for_consumptions(consumption_ids=ids)

    items: List[ConsumptionOut] = []
    for r in rows:
        items.append(
            ConsumptionOut(
                id=r["id"],
                created_at=r["created_at"],
                tenant_id=r["tenant_id"],
                user_id=r["user_id"],
                feature_id=r.get("feature_id"),
                request_id=r.get("request_id"),
                cost=int(r.get("cost") or 0),
                reason=r.get("reason"),
                project_id=r.get("project_id"),
                workflow_id=r.get("workflow_id"),
                metadata=r.get("metadata") or {},
                allocations=(
                    [
                        ConsumptionAllocationOut(**a)
                        for a in allocations_by.get(r["id"], [])
                    ]
                    if include_allocations
                    else None
                ),
            )
        )
    return ConsumptionsResponse(items=items)


@router.get("/consumptions/all", response_model=ConsumptionsResponse)
async def get_my_consumptions_across_all_tenants(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    include_allocations: bool = Query(default=True),
    since: Optional[datetime] = Query(
        default=None, description="Filter: created_at >= since"
    ),
):
    """
    This user's consumption rows across *all tenants* (no tenant filter).

    Optimized with async database queries.
    """
    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id in auth context")

    async_service = get_async_credit_service()

    rows = await async_service.get_user_consumptions(
        user_id=user_id, tenant_id=None, since=since, limit=limit
    )

    allocations_by = {}
    if include_allocations and rows:
        ids = [r["id"] for r in rows]
        allocations_by = await async_service.get_allocations_for_consumptions(consumption_ids=ids)

    items: List[ConsumptionOut] = []
    for r in rows:
        items.append(
            ConsumptionOut(
                id=r["id"],
                created_at=r["created_at"],
                tenant_id=r["tenant_id"],
                user_id=r["user_id"],
                feature_id=r.get("feature_id"),
                request_id=r.get("request_id"),
                cost=int(r.get("cost") or 0),
                reason=r.get("reason"),
                project_id=r.get("project_id"),
                workflow_id=r.get("workflow_id"),
                metadata=r.get("metadata") or {},
                allocations=(
                    [
                        ConsumptionAllocationOut(**a)
                        for a in allocations_by.get(r["id"], [])
                    ]
                    if include_allocations
                    else None
                ),
            )
        )
    return ConsumptionsResponse(items=items)
