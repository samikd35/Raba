"""
Organization Payment Invites API - Async Implementation

High-performance async endpoints for payment-gated organization invitations.
Uses batch inserts and async Stripe API calls.
"""

import logging
import os
import uuid
from decimal import ROUND_UP, Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..auth_v2.utils import get_tenant_owner
from ..credit.service import CreditService
from ..payment_v2_stripe.async_service import AsyncPaymentService, AsyncPaymentInviteStore
from ..payment_v2_stripe.async_stripe import create_checkout_session_async
from .models import PaymentInviteItem, PaymentInviteRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Services
async_service = AsyncPaymentService()
async_invite_store = AsyncPaymentInviteStore()
credit_service = CreditService()

FRONTEND_URL = os.getenv("FRONTEND_URL", "")
INVITE_DEFAULT_CURRENCY = "USD"


async def _amount_from_credits(
    total_credits: int, currency: str, rate: Decimal
) -> Decimal:
    """
    Calculate fiat amount from credits using the provided rate.
    Rate is passed in to avoid redundant DB calls.
    """
    if rate <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid credit rate for {currency}. Please contact support."
        )
    # amount = credits / (credits per unit)
    amount = (Decimal(total_credits) / rate).quantize(
        Decimal("0.01"), rounding=ROUND_UP
    )
    return amount if amount > 0 else Decimal("1.00")


@router.post("/{organization_id}/payment-invites-stripe")
async def create_payment_gated_invites(
    organization_id: str,
    body: PaymentInviteRequest,
    admin_user: dict = Depends(get_tenant_owner),
):
    """
    Create payment-gated organization invites.

    1. Validates and deduplicates invite emails
    2. Creates a payment intent in the database
    3. Batch inserts all invitations (single DB call)
    4. Creates a Stripe checkout session with all payment methods
    5. Returns checkout link for payment
    """
    inviter_user_id = admin_user.get("user_id")
    inviter_email = admin_user.get("email")

    # Normalize & dedupe emails (preserve original case)
    seen = set()
    invites: List[PaymentInviteItem] = []
    for inv in body.invites:
        em = inv.email.strip()
        em_lower = em.lower()  # Only for deduplication check
        if (
            em
            and em_lower != (inviter_email or "").lower()
            and em_lower not in seen
            and inv.credit_allocated > 0
        ):
            seen.add(em_lower)
            invites.append(inv)

    if not invites:
        raise HTTPException(
            status_code=400,
            detail="No valid invite emails provided. Please add at least one valid email address."
        )

    total_credits = sum(i.credit_allocated for i in invites)
    currency = (body.currency or INVITE_DEFAULT_CURRENCY).upper()

    # Fetch exchange rate ONCE
    rate = await async_service.get_credits_per_unit(currency)
    amount = await _amount_from_credits(total_credits, currency, rate)

    # Generate linkage IDs
    batch_id = f"inv_{uuid.uuid4().hex[:10]}"
    tx_ref = f"invpay_{uuid.uuid4().hex[:12]}"

    # Create payment intent FIRST (FK constraint requirement)
    # Include purpose metadata for unified verify route
    await async_service.save_payment_intent(
        tx_ref=tx_ref,
        amount=amount,
        currency=currency,
        email=inviter_email,
        user_id=inviter_user_id,
        tenant_id=organization_id,
        metadata={
            "purpose": "organization_payment_invitations",
            "organization_id": organization_id,
            "batch_id": batch_id,
            "total_credits": total_credits,
            "invite_count": len(invites),
        },
    )

    # BATCH INSERT all invitations (single DB call instead of N calls)
    rows = [
        {
            "organization_id": organization_id,
            "email": i.email.strip(),
            "is_admin": i.is_admin,
            "is_team_leader": i.is_team_leader,
            "credits": i.credit_allocated,
            "invited_by_user_id": inviter_user_id,
            "invited_by_email": inviter_email,
            "status": "pending_payment",
            "tx_ref": tx_ref,
            "batch_id": batch_id,
            "can_skip_modules": i.can_skip_modules,
        }
        for i in invites
    ]

    created = await async_invite_store.insert_invites_batch(rows)

    if not created:
        raise HTTPException(
            status_code=500,
            detail="Failed to create invitations. Please try again or contact support."
        )

    # Create Stripe checkout session (all payment methods enabled automatically)
    checkout_session = await create_checkout_session_async(
        currency=currency.lower(),
        amount_cents=int(amount * 100),
        product_name="Organization Member Invitations",
        product_description=f"Payment for {len(created)} organization invite(s) with {total_credits} total credits",
        success_url=f"{FRONTEND_URL}/payments/complete?session_id={{CHECKOUT_SESSION_ID}}&tx_ref={tx_ref}",
        cancel_url=f"{FRONTEND_URL}/payments/cancelled?tx_ref={tx_ref}",
        client_reference_id=tx_ref,
        customer_email=inviter_email,
        metadata={
            "tx_ref": tx_ref,
            "purpose": "organization_payment_invitations",
            "organization_id": organization_id,
            "batch_id": batch_id,
            "total_credits": str(total_credits),
            "invite_count": str(len(created)),
        },
    )

    return {
        "success": True,
        "message": f"Payment created for {len(created)} invite(s) with {total_credits} total credits",
        "checkout_link": checkout_session["url"],
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
