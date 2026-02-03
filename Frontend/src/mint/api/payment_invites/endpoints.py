import os
import uuid
from decimal import ROUND_UP, Decimal
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ..auth_v2.utils import get_tenant_owner
from ..credit.service import CreditService
from ..payment_v2.service import PaymentService
from .models import PaymentInviteItem, PaymentInviteRequest
from .service import PaymentInviteStore

router = APIRouter()

service = PaymentService()
credit_service = CreditService()

FLW_SECRET = os.getenv("FLW_SECRET")
FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH")
if not FLW_SECRET or not FLW_SECRET_HASH:
    raise RuntimeError("Missing FLW_SECRET or FLW_SECRET_HASH")

FLW_API = "https://api.flutterwave.com/v3"
HTTPX_TIMEOUT = httpx.Timeout(15.0, connect=10.0)
FRONTEND_URL = os.getenv("FRONTEND_URL", "")


def flw_headers():
    return {"Authorization": f"Bearer {FLW_SECRET}"}


INVITE_DEFAULT_CURRENCY = "USD"


# ---------- Helpers ----------
def _amount_from_credits(
    total_credits: int, currency: str, payment_svc: PaymentService
) -> Decimal:
    # credits per currency unit
    rate = Decimal(str(payment_svc.get_credits_per_unit(currency)))
    if rate <= 0:
        raise HTTPException(
            status_code=400, detail=f"Invalid credit rate for {currency}"
        )
    # amount = credits / (credits per unit)
    amount = (Decimal(total_credits) / rate).quantize(
        Decimal("0.01"), rounding=ROUND_UP
    )
    return amount if amount > 0 else Decimal("1.00")


@router.post("/{organization_id}/payment-invites")
async def create_payment_gated_invites(
    organization_id: str,
    body: PaymentInviteRequest,
    admin_user: dict = Depends(get_tenant_owner),
):
    """
    Stores org invites in organization_payment_invitations as 'pending_payment',
    creates a Flutterwave checkout, and returns the checkout link + tx_ref.
    """
    inviter_user_id = admin_user.get("user_id")
    inviter_email = admin_user.get("email")

    # Normalize & dedupe
    seen = set()
    invites: List[PaymentInviteItem] = []
    for inv in body.invites:
        em = inv.email.strip()
        if (
            em
            and em != (inviter_email or "").lower()
            and em not in seen
            and inv.credit_allocated > 0
        ):
            seen.add(em)
            invites.append(inv)
    if not invites:
        raise HTTPException(status_code=400, detail="No valid invite emails provided.")

    total_credits = sum(i.credit_allocated for i in invites)
    currency = (body.currency or INVITE_DEFAULT_CURRENCY).upper()

    amount = _amount_from_credits(total_credits, currency, service)

    # linkage ids
    batch_id = f"inv_{uuid.uuid4().hex[:10]}"
    tx_ref = f"invpay_{uuid.uuid4().hex[:12]}"

    # IMPORTANT: Create payment intent FIRST to satisfy FK constraint
    try:
        service.save_payment_intent(
            tx_ref, amount, currency, inviter_email, inviter_user_id, organization_id
        )
    except Exception as e:
        print(f"[payment-invites] save_payment_intent failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment intent: {str(e)}")

    # Now create invitations (FK constraint satisfied)
    store = PaymentInviteStore()
    created = []
    for i in invites:
        row = {
            "organization_id": organization_id,
            "email": i.email,
            "is_admin": i.is_admin,
            "is_team_leader": i.is_team_leader,
            "credits": i.credit_allocated,
            "invited_by_user_id": inviter_user_id,
            "invited_by_email": inviter_email,
            "status": "pending_payment",
            "tx_ref": tx_ref,
            "batch_id": batch_id,
        }
        try:
            created.append(store.insert_invite(row))
        except Exception as e:
            # continue but log
            print(f"[payment-invites] failed to insert {i.email}: {e}")

    if not created:
        raise HTTPException(status_code=500, detail="Failed to persist invitations.")

    # Create Flutterwave payment
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": currency,
        "redirect_url": f"{FRONTEND_URL}/payments/complete",
        "customer": {"email": inviter_email, "name": "Organization Admin"},
        "payment_options": "card,banktransfer,ussd",
        "meta": {
            "purpose": "organization_payment_invitations",
            "organization_id": organization_id,
            "batch_id": batch_id,
            "total_credits": str(total_credits),
            "invite_count": len(created),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
            r = await client.post(
                f"{FLW_API}/payments", json=payload, headers=flw_headers()
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach payment provider: {e}"
        )

    if r.status_code not in (200, 201):
        raise HTTPException(r.status_code, f"Flutterwave error: {r.text}")

    link = (r.json().get("data") or {}).get("link")
    if not link:
        raise HTTPException(
            status_code=502, detail=f"Unexpected Flutterwave response: {r.text}"
        )

    return {
        "success": True,
        "message": f"Payment created for {len(created)} invite(s) / {total_credits} credits",
        "checkout_link": link,
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": currency,
        "batch_id": batch_id,
        "invites": [
            {
                "email": r["email"],
                "credits": r["credits"],
                "is_admin": r["is_admin"],
                "is_team_leader": r["is_team_leader"],
            }
            for r in created
        ],
    }
