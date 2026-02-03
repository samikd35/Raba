from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth_v2.utils import get_admin_user, get_super_admin_user
from .models import CreditRateCreate, CreditRateOut, CreditRateUpdate
from .service import CreditExchangeService

router = APIRouter(
    prefix="/credit-exchange-rates",
    tags=["Credit Exchange Rates"],
)

service = CreditExchangeService()


@router.get("/", response_model=List[CreditRateOut])
async def list_credit_rates(
    active: Optional[bool] = Query(None, description="Filter by is_active if provided"),
    admin_ctx: dict = Depends(get_admin_user),
):
    rows = service.list_rates(active=active)
    return rows


@router.get("/{currency}", response_model=CreditRateOut)
async def get_credit_rate(
    currency: str,
    admin_ctx: dict = Depends(get_admin_user),
):
    row = service.get_rate(currency)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Rate for '{currency.upper()}' not found"
        )
    return row


@router.post("/", response_model=CreditRateOut, status_code=status.HTTP_201_CREATED)
async def create_credit_rate(
    payload: CreditRateCreate,
    admin_ctx: dict = Depends(get_admin_user),
):
    row = {
        "currency": payload.currency.upper(),
        "credits_per_unit": float(payload.credits_per_unit),  # Convert Decimal to float
        "is_active": payload.is_active,
    }
    try:
        created = service.create_rate(row)
        return created
    except Exception as e:
        msg = str(getattr(e, "message", e))
        if "duplicate key" in msg or "unique constraint" in msg or "23505" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rate for '{payload.currency.upper()}' already exists",
            )
        raise


@router.patch("/{currency}", response_model=CreditRateOut)
async def update_credit_rate(
    currency: str,
    payload: CreditRateUpdate,
    admin_ctx: dict = Depends(get_admin_user),
):
    patch = {}
    if payload.credits_per_unit is not None:
        patch["credits_per_unit"] = float(payload.credits_per_unit)  # Convert Decimal to float
    if payload.is_active is not None:
        patch["is_active"] = payload.is_active

    updated = service.update_rate(currency, patch)
    if not updated:
        raise HTTPException(
            status_code=404, detail=f"Rate for '{currency.upper()}' not found"
        )
    return updated


@router.delete("/{currency}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credit_rate(
    currency: str,
    admin_ctx: dict = Depends(get_super_admin_user),
):
    deleted_count = service.delete_rate(currency)
    if deleted_count == 0:
        # If nothing deleted, return 404
        raise HTTPException(
            status_code=404, detail=f"Rate for '{currency.upper()}' not found"
        )
    return None
