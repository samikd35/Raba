"""
Stripe Payment API Endpoints - Async Implementation

High-performance async endpoints for payment processing.
All database and Stripe API calls are non-blocking.

Unified verify and webhook handlers that route based on payment purpose.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)

from ..auth_v2.utils import get_current_user
from ..credit.async_service import get_async_credit_service
from .async_service import AsyncPaymentService, AsyncPaymentInviteStore
from .async_stripe import (
    create_checkout_session_async,
    retrieve_checkout_session_async,
    verify_webhook_signature,
)
from .models import CreatePaymentBody, CreatePaymentResp, VerifyResp

logger = logging.getLogger(__name__)
router = APIRouter(tags=["payments-stripe"])

# Services
async_service = AsyncPaymentService()
async_credit_service = get_async_credit_service()

FRONTEND_URL = os.getenv("FRONTEND_URL", "")


@router.post("/payments-stripe/create", response_model=CreatePaymentResp)
async def create_payment(
    body: CreatePaymentBody, current_user: dict = Depends(get_current_user)
):
    """
    Create a Stripe checkout session for credit purchase.

    All payment methods are automatically enabled by Stripe based on
    currency and customer location.
    """
    user_id = current_user["user_id"]
    tenant_id = current_user["tenant_id"]
    tx_ref = f"pay_{uuid.uuid4().hex[:12]}"

    # Fetch exchange rate ONCE and reuse
    rate = await async_service.get_credits_per_unit(body.currency)
    amount = Decimal(str(body.credit_amount)) / rate

    # Save payment intent with purpose metadata
    await async_service.save_payment_intent(
        tx_ref=tx_ref,
        amount=amount,
        currency=body.currency,
        email=body.email,
        user_id=user_id,
        tenant_id=tenant_id,
        metadata={
            "purpose": "credit_purchase",
            "credits_requested": body.credit_amount,
        },
    )

    # Create Stripe checkout session (all payment methods enabled)
    checkout_session = await create_checkout_session_async(
        currency=body.currency.lower(),
        amount_cents=int(amount * 100),
        product_name=f"Credit Purchase - {body.credit_amount} Credits",
        product_description=f"Purchase {body.credit_amount} credits for your account",
        success_url=f"{FRONTEND_URL}/payments/complete?session_id={{CHECKOUT_SESSION_ID}}&tx_ref={tx_ref}",
        cancel_url=f"{FRONTEND_URL}/payments/cancelled?tx_ref={tx_ref}",
        client_reference_id=tx_ref,
        customer_email=body.email,
        metadata={
            "tx_ref": tx_ref,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "purpose": "credit_purchase",
        },
    )

    # Mark as pending
    await async_service.mark_payment_status(
        tx_ref, "pending", None, {"create": checkout_session}
    )

    return CreatePaymentResp(checkout_link=checkout_session["url"], tx_ref=tx_ref)


@router.get("/payments-stripe/verify", response_model=VerifyResp)
async def verify_payment(
    session_id: str,
    tx_ref: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Unified payment verification endpoint.

    Handles all payment types based on the purpose metadata:
    - credit_purchase: Allocate credits to user
    - bulk_credit_purchase: Allocate bulk credits to organization
    - bulk_direct_allocation: Batch allocate to multiple tenants
    - organization_payment_invitations: Dispatch invites after payment

    Idempotent - safe to call multiple times for the same session.
    """
    from .async_invite_dispatcher import AsyncPaymentInviteDispatcher

    # Idempotency check - already processed?
    if await async_service.already_processed_transaction(session_id):
        return VerifyResp(
            ok=True,
            message="Payment already verified and processed",
            tx_id=None,
            tx_ref=tx_ref,
            raw={"note": "Transaction already processed successfully"},
        )

    # Get expected values and exchange rate
    expected_amount, expected_currency, tenant_id = (
        await async_service.get_order_expectations_by_tx_ref(tx_ref)
    )
    rate = await async_service.get_credits_per_unit(expected_currency)

    # Retrieve session from Stripe
    session = await retrieve_checkout_session_async(session_id)

    # Validate payment
    ok = (
        session["payment_status"] == "paid"
        and Decimal(str(session["amount_total"] / 100)) == expected_amount
        and str(session["currency"]).upper() == expected_currency
        and str(session["client_reference_id"]) == tx_ref
    )

    # Update payment status
    await async_service.mark_payment_status(
        tx_ref,
        "successful" if ok else "failed",
        session.get("payment_intent"),
        {"verify": session, "via": "verify"},
    )

    message = "Payment verification failed. Please contact support."

    if ok and tenant_id:
        # Get purpose from session metadata
        purpose = session.get("metadata", {}).get("purpose")
        session_id_str = session.get("id")
        payment_intent = session.get("payment_intent")

        if purpose in ["credit_purchase", "bulk_credit_purchase"]:
            # Handle credit purchases
            if not await async_service.has_grant_for_tx_ref(tx_ref):
                credits = async_service.compute_credits(expected_amount, rate)
                valid_from, _ = async_service.default_validity()

                meta = {
                    "tx_ref": tx_ref,
                    "session_id": session_id_str,
                    "payment_intent": payment_intent,
                    "currency": expected_currency,
                    "amount": str(expected_amount),
                    "rate": str(rate),
                    "source": "stripe",
                    "via": "verify",
                }

                if purpose == "bulk_credit_purchase":
                    meta.update({
                        "purchase_type": "bulk",
                        "tenant_name": session.get("metadata", {}).get("tenant_name"),
                        "member_count": session.get("metadata", {}).get("member_count"),
                        "credits_per_member": session.get("metadata", {}).get("credits_per_member"),
                        "admin_seats_count": session.get("metadata", {}).get("admin_seats_count"),
                        "total_credits_requested": session.get("metadata", {}).get("total_credits"),
                    })

                await async_credit_service.create_credit_lot(
                    tenant_id=tenant_id,
                    source="purchase",
                    credit_amount=credits,
                    valid_from=valid_from,
                    expires_at=None,
                    metadata=meta,
                    original_tenant_id=tenant_id,
                )

                await async_service.record_grant(
                    tx_ref=tx_ref,
                    tenant_id=tenant_id,
                    currency=expected_currency,
                    rate=rate,
                    credits_assigned=credits,
                )

            message = "Payment verified and credits allocated successfully"

        elif purpose == "bulk_direct_allocation":
            # Handle direct allocation with batch insert
            if not await async_service.has_grant_for_tx_ref(tx_ref):
                allocations: list = []
                currency = expected_currency
                alloc_rate = rate

                try:
                    metadata = await async_service.get_metadata_by_tx_ref(tx_ref)
                    allocations = metadata.get("allocations", [])
                    currency = metadata.get("currency", expected_currency)
                    alloc_rate = Decimal(str(metadata.get("rate", rate)))
                except Exception as e:
                    logger.error(f"Failed to retrieve allocation metadata: {e}")

                if allocations:
                    valid_from, _ = async_service.default_validity()

                    batch_allocations = [
                        {
                            "tenant_id": alloc["tenant_id"],
                            "credit_amount": alloc["credit_amount"],
                            "original_tenant_id": tenant_id,
                        }
                        for alloc in allocations
                    ]

                    await async_credit_service.create_credit_lot_batch(
                        allocations=batch_allocations,
                        source="purchase",
                        valid_from=valid_from,
                        expires_at=None,
                        base_metadata={
                            "tx_ref": tx_ref,
                            "session_id": session_id_str,
                            "payment_intent": payment_intent,
                            "currency": currency,
                            "amount": str(expected_amount),
                            "rate": str(alloc_rate),
                            "source": "stripe",
                            "via": "verify",
                            "purchase_type": "bulk_direct_allocation",
                            "organization_id": tenant_id,
                        },
                    )

                    total_credits = sum(a["credit_amount"] for a in allocations)
                    await async_service.record_grant(
                        tx_ref=tx_ref,
                        tenant_id=tenant_id,
                        currency=currency,
                        rate=alloc_rate,
                        credits_assigned=total_credits,
                    )

                    logger.info(
                        f"Verify: Batch allocated {total_credits} credits to {len(allocations)} tenants"
                    )

            message = "Payment verified and credits allocated to members"

        elif purpose == "organization_payment_invitations":
            # Handle organization payment invites
            invite_store = AsyncPaymentInviteStore()
            if await invite_store.has_pending_invites(tx_ref):
                dispatcher = AsyncPaymentInviteDispatcher()
                await dispatcher.dispatch_after_payment(tx_ref, background_tasks)
            message = "Payment verified and invitations sent"

        else:
            # Unknown purpose - log warning but still mark as processed
            logger.warning(f"Verify received unknown purpose: {purpose} for tx_ref: {tx_ref}")
            message = "Payment verified successfully"

        # Mark as processed
        await async_service.mark_transaction_processed(session_id, tx_ref)

    return VerifyResp(
        ok=ok,
        message=message,
        tx_id=session.get("payment_intent"),
        tx_ref=session.get("client_reference_id"),
        raw=session,
    )


@router.post("/webhooks-stripe/payment")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Unified Stripe webhook handler for all payment types.

    Routes based on payment purpose metadata:
    - credit_purchase: Allocate credits to user
    - bulk_credit_purchase: Allocate bulk credits to organization
    - bulk_direct_allocation: Batch allocate to multiple tenants
    - organization_payment_invitations: Dispatch invites after payment
    - invoice.paid: Handle B2B invoice payments

    This provides backup processing in case client-side verification fails.
    """
    from .async_invite_dispatcher import AsyncPaymentInviteDispatcher

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    event = verify_webhook_signature(payload, sig_header)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tx_ref = session.get("client_reference_id")
        session_id = session.get("id")
        payment_intent = session.get("payment_intent")

        if not tx_ref or not session_id:
            return Response(status_code=200)

        # Already processed?
        if await async_service.already_processed_transaction(session_id):
            return Response(status_code=200)

        # Payment failed?
        if session.get("payment_status") != "paid":
            await async_service.mark_payment_status(
                tx_ref, "failed", payment_intent, {"webhook_failed": session}
            )
            await async_service.mark_transaction_processed(session_id, tx_ref)
            return Response(status_code=200)

        # Get expectations
        try:
            expected_amount, expected_currency, tenant_id = (
                await async_service.get_order_expectations_by_tx_ref(tx_ref)
            )
            rate = await async_service.get_credits_per_unit(expected_currency)
        except HTTPException:
            await async_service.mark_payment_status(
                tx_ref, "failed", payment_intent, {"unknown_tx_ref": session}
            )
            await async_service.mark_transaction_processed(session_id, tx_ref)
            return Response(status_code=200)

        # Validate
        ok = (
            session.get("payment_status") == "paid"
            and Decimal(str(session.get("amount_total") / 100)) == expected_amount
            and str(session.get("currency")).upper() == expected_currency
            and str(session.get("client_reference_id")) == tx_ref
        )

        await async_service.mark_payment_status(
            tx_ref,
            "successful" if ok else "failed",
            payment_intent,
            {"webhook": session, "event_type": event["type"]},
        )

        if ok and tenant_id:
            purpose = session.get("metadata", {}).get("purpose")

            if purpose in ["credit_purchase", "bulk_credit_purchase"]:
                # Handle credit purchases
                if not await async_service.has_grant_for_tx_ref(tx_ref):
                    credits = async_service.compute_credits(expected_amount, rate)
                    valid_from, _ = async_service.default_validity()

                    meta = {
                        "tx_ref": tx_ref,
                        "session_id": session_id,
                        "payment_intent": payment_intent,
                        "currency": expected_currency,
                        "amount": str(expected_amount),
                        "rate": str(rate),
                        "source": "stripe",
                        "via": "webhook",
                    }

                    if purpose == "bulk_credit_purchase":
                        meta.update({
                            "purchase_type": "bulk",
                            "tenant_name": session.get("metadata", {}).get("tenant_name"),
                            "member_count": session.get("metadata", {}).get("member_count"),
                            "credits_per_member": session.get("metadata", {}).get("credits_per_member"),
                            "admin_seats_count": session.get("metadata", {}).get("admin_seats_count"),
                            "total_credits_requested": session.get("metadata", {}).get("total_credits"),
                        })

                    await async_credit_service.create_credit_lot(
                        tenant_id=tenant_id,
                        source="purchase",
                        credit_amount=credits,
                        valid_from=valid_from,
                        expires_at=None,
                        metadata=meta,
                        original_tenant_id=tenant_id,
                    )

                    await async_service.record_grant(
                        tx_ref=tx_ref,
                        tenant_id=tenant_id,
                        currency=expected_currency,
                        rate=rate,
                        credits_assigned=credits,
                    )

            elif purpose == "bulk_direct_allocation":
                # Handle direct allocation with batch insert
                if not await async_service.has_grant_for_tx_ref(tx_ref):
                    allocations: list = []
                    currency = expected_currency
                    alloc_rate = rate

                    try:
                        metadata = await async_service.get_metadata_by_tx_ref(tx_ref)
                        allocations = metadata.get("allocations", [])
                        currency = metadata.get("currency", expected_currency)
                        alloc_rate = Decimal(str(metadata.get("rate", rate)))
                    except Exception as e:
                        logger.error(f"Failed to retrieve allocation metadata: {e}")

                    if allocations:
                        valid_from, _ = async_service.default_validity()

                        batch_allocations = [
                            {
                                "tenant_id": alloc["tenant_id"],
                                "credit_amount": alloc["credit_amount"],
                                "original_tenant_id": tenant_id,
                            }
                            for alloc in allocations
                        ]

                        await async_credit_service.create_credit_lot_batch(
                            allocations=batch_allocations,
                            source="purchase",
                            valid_from=valid_from,
                            expires_at=None,
                            base_metadata={
                                "tx_ref": tx_ref,
                                "session_id": session_id,
                                "payment_intent": payment_intent,
                                "currency": currency,
                                "amount": str(expected_amount),
                                "rate": str(alloc_rate),
                                "source": "stripe",
                                "via": "webhook",
                                "purchase_type": "bulk_direct_allocation",
                                "organization_id": tenant_id,
                            },
                        )

                        total_credits = sum(a["credit_amount"] for a in allocations)
                        await async_service.record_grant(
                            tx_ref=tx_ref,
                            tenant_id=tenant_id,
                            currency=currency,
                            rate=alloc_rate,
                            credits_assigned=total_credits,
                        )

                        logger.info(
                            f"Webhook: Batch allocated {total_credits} credits to {len(allocations)} tenants"
                        )

            elif purpose == "organization_payment_invitations":
                # Handle organization payment invites
                # Only dispatch if not already handled by verify route
                invite_store = AsyncPaymentInviteStore()
                if await invite_store.has_pending_invites(tx_ref):
                    dispatcher = AsyncPaymentInviteDispatcher()
                    await dispatcher.dispatch_after_payment(tx_ref, background_tasks)
                else:
                    logger.info(f"Invites for tx_ref {tx_ref} already dispatched by verify route")

            else:
                # Unknown purpose - log for debugging
                logger.warning(f"Webhook received unknown purpose: {purpose} for tx_ref: {tx_ref}")

        await async_service.mark_transaction_processed(session_id, tx_ref)

    elif event["type"] in ["invoice.paid", "invoice.payment_succeeded"]:
        # Handle invoice payments for B2B
        invoice_data = event["data"]["object"]
        stripe_invoice_id = invoice_data.get("id")
        payment_intent = invoice_data.get("payment_intent")

        logger.info(f"Processing invoice payment: {stripe_invoice_id}")

        invoice = await async_service.get_invoice_by_stripe_id(stripe_invoice_id)

        if not invoice:
            logger.warning(f"No invoice found for Stripe invoice {stripe_invoice_id}")
            return Response(status_code=200)

        if invoice["status"] != "paid":
            success = await async_service.mark_invoice_paid(
                invoice_id=invoice["id"],
                payment_intent=payment_intent,
            )
            if success:
                logger.info(f"Updated invoice {invoice.get('invoice_number')} status to paid")

    return Response(status_code=200)
