"""
Venture Builder Earnings API

Handles earnings and reconciliation management including:
- VB earnings dashboard
- Admin earnings configuration
- Payment reconciliation
- Reconciliation history
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .exceptions import VBBaseException, VBNotFoundError
from .models import (
    EarningsConfigResponse,
    EarningsConfigUpdate,
    VBEarningsResponse,
    VBReconciliationCreate,
    VBReconciliationHistoryResponse,
    VBReconciliationResponse,
)
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_admin_user, get_vb_or_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Earnings"])

# Singleton service instance
vb_service = get_vb_service()


@router.get("/earnings")
async def get_my_earnings(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Get earnings dashboard for the current VB.
    """
    try:
        # Get VB profile
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found")

        earnings = vb_service.get_vb_earnings(
            vb_id=vb_profile["id"],
            start_date=start_date,
            end_date=end_date,
        )
        return {"success": True, "data": VBEarningsResponse(**earnings).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/earnings/config")
async def get_earnings_config(
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Get current earnings configuration.
    """
    try:
        config = vb_service.get_earnings_config()
        return {"success": True, "data": EarningsConfigResponse(**config).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/admin/earnings/config")
async def update_earnings_config(
    data: EarningsConfigUpdate,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Update earnings configuration (credit-to-USD rate and commission).
    """
    try:
        config = vb_service.update_earnings_config(
            credit_to_usd_rate=data.credit_to_usd_rate,
            commission_rate=data.commission_rate,
            updated_by=current_user["user_id"],
        )
        return {"success": True, "data": EarningsConfigResponse(**config).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/admin/vb/{vb_id}/reconcile")
async def reconcile_vb_payments(
    vb_id: UUID,
    data: VBReconciliationCreate,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Reconcile pending payments for a Venture Builder.

    This marks pending earnings as settled and updates the VB's total reconciled payments.
    - If no date range is provided, reconciles ALL pending earnings (pending amount becomes 0)
    - If date range is provided, reconciles only earnings from sessions within that range

    Args:
        vb_id: Venture Builder ID
        data: Reconciliation request with optional date range and notes
        current_user: Authenticated admin user

    Returns:
        Reconciliation details including amounts before/after and total reconciled lifetime
    """
    try:
        result = vb_service.reconcile_vb_payments(
            vb_id=str(vb_id),
            reconciled_by_user_id=current_user["user_id"],
            start_date=data.start_date,
            end_date=data.end_date,
            notes=data.notes,
        )
        return {"success": True, "data": VBReconciliationResponse(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/vb/{vb_id}/reconciliations")
async def get_vb_reconciliation_history(
    vb_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Get reconciliation history for a specific Venture Builder.

    Returns paginated list of all reconciliation events for the VB.
    """
    try:
        result = vb_service.get_reconciliation_history(
            vb_id=str(vb_id),
            page=page,
            page_size=page_size,
        )
        return {"success": True, "data": VBReconciliationHistoryResponse(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/reconciliations")
async def get_all_reconciliations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Get all reconciliation records across all Venture Builders.

    Returns paginated list of all reconciliation events in the system.
    Useful for admin oversight and financial reporting.
    """
    try:
        result = vb_service.get_all_reconciliations(
            page=page,
            page_size=page_size,
        )
        return {"success": True, "data": VBReconciliationHistoryResponse(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
