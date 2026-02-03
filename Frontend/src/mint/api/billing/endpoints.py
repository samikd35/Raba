"""
API endpoints for billing operations.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal

import stripe
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse

from ..auth_v2.utils import get_current_user, get_super_admin_user, get_global_admin_or_tenant_admin
from ..credit.service import CreditService
from ..payment_v2_stripe.service import PaymentService
from .service import BillingService, BillingError, InvoiceNotFoundError, InvalidPricingConfigError
from .models import (
    PricingConfigResponse,
    UpdatePricingConfigRequest,
    InvoiceResponse,
    InvoiceWithLineItemsResponse,
    MarkInvoicePaidRequest,
    BulkPurchaseRequest,
    BulkPurchaseResponse,
    BulkPurchaseVerifyResponse,
    BulkPurchaseDirectRequest,
    BulkPurchaseDirectResponse,
    BulkPurchaseDirectVerifyResponse,
    TenantAllocation,
    AdminSeatBillingHistoryResponse,
    SuccessResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_API_KEY')


# ============================================================================
# Dependencies
# ============================================================================

def get_billing_service() -> BillingService:
    """Dependency to get BillingService instance"""
    return BillingService(use_service_role=True)


def get_payment_service() -> PaymentService:
    """Dependency to get PaymentService instance"""
    return PaymentService(use_service_role=True)


def get_credit_service() -> CreditService:
    """Dependency to get CreditService instance"""
    return CreditService(use_service_role=True)


# ============================================================================
# Pricing Configuration Endpoints
# ============================================================================

@router.get("/pricing-config", response_model=PricingConfigResponse)
async def get_pricing_config(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service)
):
    """
    Get active pricing configuration.

    Accessible to all authenticated users.
    """
    try:
        config = service.get_pricing_config()
        return config
    except InvalidPricingConfigError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting pricing config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve pricing configuration")


@router.put("/pricing-config", response_model=PricingConfigResponse)
async def update_pricing_config(
    request: UpdatePricingConfigRequest,
    current_user: Dict[str, Any] = Depends(get_super_admin_user),
    service: BillingService = Depends(get_billing_service)
):
    """
    Update pricing configuration (super admin only).

    Deactivates current config and creates new one.
    """
    try:
        created_by = current_user.get("user_id")

        config = service.update_pricing_config(
            admin_seat_price_credits=request.admin_seat_price_credits,
            estimated_credits_per_user=request.estimated_credits_per_user,
            created_by=created_by
        )
        return config
    except InvalidPricingConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating pricing config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update pricing configuration")


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.get("/{tenant_id}/invoices/pending", response_model=List[InvoiceResponse])
async def get_pending_invoices(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    service: BillingService = Depends(get_billing_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Get all pending invoices for an organization.

    Returns invoices with status 'pending' or 'overdue'.
    Requires organization admin/owner access.
    """
    try:
        response = service.supabase.table('invoices') \
            .select('*') \
            .eq('tenant_id', tenant_id) \
            .in_('status', ['pending', 'overdue']) \
            .order('created_at', desc=True) \
            .execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error getting pending invoices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve pending invoices")


@router.get("/{tenant_id}/invoices/paid", response_model=List[InvoiceResponse])
async def get_paid_invoices(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of invoices to return"),
    service: BillingService = Depends(get_billing_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Get paid invoices for an organization.

    Returns invoices with status 'paid', ordered by payment date (newest first).
    Requires organization admin/owner access.
    """
    try:
        response = service.supabase.table('invoices') \
            .select('*') \
            .eq('tenant_id', tenant_id) \
            .eq('status', 'paid') \
            .order('paid_at', desc=True) \
            .limit(limit) \
            .execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error getting paid invoices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve paid invoices")


@router.get("/{tenant_id}/invoices/{invoice_id}", response_model=InvoiceWithLineItemsResponse)
async def get_invoice_details(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    invoice_id: str = Path(..., description="Invoice ID"),
    service: BillingService = Depends(get_billing_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Get invoice details with line items.

    Returns complete invoice information including all line items.
    Requires organization admin/owner access.
    """
    try:
        # Get invoice
        invoice_response = service.supabase.table('invoices') \
            .select('*') \
            .eq('id', invoice_id) \
            .eq('tenant_id', tenant_id) \
            .single() \
            .execute()

        if not invoice_response.data:
            raise HTTPException(status_code=404, detail="Invoice not found")

        invoice = invoice_response.data

        # Get line items
        line_items_response = service.supabase.table('invoice_line_items') \
            .select('*') \
            .eq('invoice_id', invoice_id) \
            .order('created_at', desc=False) \
            .execute()

        line_items = line_items_response.data or []

        return {
            'invoice': invoice,
            'line_items': line_items
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve invoice details")


@router.post("/{tenant_id}/invoices/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    invoice_id: str = Path(..., description="Invoice ID"),
    request: MarkInvoicePaidRequest = None,
    service: BillingService = Depends(get_billing_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Manually mark an invoice as paid.

    Used for non-Stripe payments (manual, bank transfer, check, etc.).
    Requires organization admin/owner access.
    """
    try:
        marked_by = current_user.get("user_id")

        invoice = service.mark_invoice_paid(
            invoice_id=invoice_id,
            payment_method=request.payment_method,
            payment_reference=request.payment_reference,
            payment_notes=request.payment_notes,
            marked_by=marked_by
        )
        return invoice
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BillingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error marking invoice paid: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to mark invoice as paid")


# ============================================================================
# Bulk Purchase Endpoint
# ============================================================================

@router.post("/{tenant_id}/bulk-purchase", response_model=BulkPurchaseResponse)
async def bulk_credit_purchase(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    request: BulkPurchaseRequest = None,
    service: BillingService = Depends(get_billing_service),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Calculate bulk credit purchase and allocate credits.

    Formula: (members × credits_per_member) + (admin_seats × seat_price)

    For prepay_org: Creates a Stripe Checkout Session for payment.
    For postpay_org: Allocates credits immediately and tracks for month-end billing.
    Requires prepay_org or postpay_org organization admin/owner access.
    """
    try:
        # Get organization config
        org_config = service.supabase.table('organization_billing_config') \
            .select('organization_type, tenants!inner(name)') \
            .eq('tenant_id', tenant_id) \
            .limit(1) \
            .execute()

        if not org_config.data or len(org_config.data) == 0:
            raise HTTPException(status_code=404, detail="Organization billing config not found")

        org_type = org_config.data[0]['organization_type']
        tenant_name = org_config.data[0]['tenants']['name']

        # Only prepay_org and postpay_org can use bulk purchase
        if org_type not in ['prepay_org', 'postpay_org']:
            raise HTTPException(
                status_code=400,
                detail="Bulk purchase is only available for prepay and postpay organizations"
            )

        # Get pricing
        pricing = service.get_pricing_config()
        admin_seat_price = pricing['admin_seat_price_credits']
        credits_per_member = request.credits_per_member or pricing['estimated_credits_per_user']

        # Count admin seats
        admin_seats_response = service.supabase.table('tenant_memberships') \
            .select('id', count='exact') \
            .eq('tenant_id', tenant_id) \
            .eq('role', 'admin') \
            .eq('is_active', True) \
            .execute()

        admin_seats_count = admin_seats_response.count or 0

        # Calculate totals
        member_credits_total = request.member_count * credits_per_member
        admin_seats_total = admin_seats_count * admin_seat_price
        total_credits = member_credits_total + admin_seats_total

        # Get exchange rate for currency
        currency = request.currency
        rate = payment_service.get_credits_per_unit(currency)
        total_amount = float(Decimal(str(total_credits)) / Decimal(str(rate)))

        # Get org owner email for Stripe
        owner_response = service.supabase.table('tenant_memberships') \
            .select('user_profiles!inner(email)') \
            .eq('tenant_id', tenant_id) \
            .eq('role', 'owner') \
            .eq('is_active', True) \
            .limit(1) \
            .execute()

        customer_email = owner_response.data[0]['user_profiles']['email'] if owner_response.data else None
        user_id = current_user.get("user_id")

        # Generate transaction reference
        tx_ref = f"bulk_{uuid.uuid4().hex[:12]}"

        # Build line items description
        line_items_description = []
        if member_credits_total > 0:
            line_items_description.append(
                f"{request.member_count} members × {credits_per_member} credits"
            )
        if admin_seats_total > 0:
            line_items_description.append(
                f"{admin_seats_count} admin seats × {admin_seat_price} credits"
            )

        description = f"Bulk Credit Purchase for {tenant_name}"
        if line_items_description:
            description += f" ({', '.join(line_items_description)})"

        if org_type == 'prepay_org':
            # For prepay_org: Create Stripe Checkout Session for payment
            # Save payment intent
            payment_service.save_payment_intent(
                tx_ref=tx_ref,
                amount=Decimal(str(total_amount)),
                currency=currency,
                email=customer_email,
                user_id=user_id,
                tenant_id=tenant_id
            )

            # Get frontend URL for redirect
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

            # Create Stripe Checkout Session
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=None,  # Stripe automatically determines available methods
                    payment_method_options={
                        "us_bank_account": {"verification_method": "instant"},
                    },
                    automatic_tax={"enabled": False},
                    line_items=[
                        {
                            "price_data": {
                                "currency": currency.lower(),
                                "unit_amount": int(total_amount * 100),  # Convert to cents
                                "product_data": {
                                    "name": f"Bulk Credit Purchase - {total_credits} Credits",
                                    "description": description,
                                },
                            },
                            "quantity": 1,
                        }
                    ],
                    mode="payment",
                    success_url=f"{frontend_url}/billing/bulk-purchase/complete?session_id={{CHECKOUT_SESSION_ID}}&tx_ref={tx_ref}",
                    cancel_url=f"{frontend_url}/billing/bulk-purchase/cancelled?tx_ref={tx_ref}",
                    client_reference_id=tx_ref,
                    customer_email=customer_email,
                    metadata={
                        "tx_ref": tx_ref,
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "purpose": "bulk_credit_purchase",
                        "tenant_name": tenant_name,
                        "member_count": request.member_count,
                        "credits_per_member": credits_per_member,
                        "admin_seats_count": admin_seats_count,
                        "total_credits": total_credits,
                    },
                )
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error creating checkout session: {e}")
                raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

            # Mark payment as pending
            payment_service.mark_payment_status(
                tx_ref=tx_ref,
                status="pending",
                tx_id=checkout_session.id,
                payload={"create": checkout_session.to_dict()}
            )

            logger.info(
                f"Created bulk purchase checkout session for {tenant_name}: "
                f"{total_credits} credits ({currency} {total_amount}), tx_ref={tx_ref}"
            )

            return BulkPurchaseResponse(
                tenant_id=tenant_id,
                member_count=request.member_count,
                credits_per_member=credits_per_member,
                member_credits_total=member_credits_total,
                admin_seats_count=admin_seats_count,
                admin_seat_price_credits=admin_seat_price,
                admin_seats_total=admin_seats_total,
                total_credits=total_credits,
                total_amount=total_amount,
                currency=currency,
                tx_ref=tx_ref,
                checkout_url=checkout_session.url,
                session_id=checkout_session.id
            )

        elif org_type == 'postpay_org':
            # For postpay_org: Allocate credits immediately and track for billing
            from ..credit.service import CreditService
            credit_service = CreditService()

            now = datetime.now(timezone.utc)

            # Create credit lot for organization
            # Purchased credits never expire
            try:
                credit_lot = credit_service.create_credit_lot(
                    tenant_id=tenant_id,
                    source="purchase",
                    credit_amount=Decimal(str(total_credits)),
                    valid_from=now.isoformat(),
                    expires_at=None,  # Purchased credits never expire
                    metadata={
                        "tx_ref": tx_ref,
                        "purchase_type": "bulk",
                        "org_type": "postpay",
                        "member_count": request.member_count,
                        "credits_per_member": credits_per_member,
                        "admin_seats_count": admin_seats_count,
                        "admin_seat_price": admin_seat_price,
                        "description": description
                    },
                    original_tenant_id=tenant_id
                )

                logger.info(f"Created credit lot for postpay_org {tenant_name}: {total_credits} credits")

                # Track allocation in organization_credit_allocations
                allocation_payload = {
                    'tenant_id': tenant_id,
                    'allocation_type': 'purchase',
                    'credit_amount': float(total_credits),
                    'credit_lot_id': credit_lot.get('id') if credit_lot else None,
                    'allocated_by_user_id': user_id,
                    'allocated_at': now.isoformat(),
                    'metadata': {
                        'tx_ref': tx_ref,
                        'purchase_type': 'bulk',
                        'member_count': request.member_count,
                        'credits_per_member': credits_per_member,
                        'admin_seats_count': admin_seats_count,
                        'admin_seat_price': admin_seat_price,
                        'description': description
                    }
                }

                service.supabase.table('organization_credit_allocations') \
                    .insert(allocation_payload) \
                    .execute()

                logger.info(
                    f"Tracked bulk purchase allocation for postpay_org {tenant_name}: "
                    f"{total_credits} credits, tx_ref={tx_ref}"
                )

                # Return response without checkout_url (not needed for postpay)
                return BulkPurchaseResponse(
                    tenant_id=tenant_id,
                    member_count=request.member_count,
                    credits_per_member=credits_per_member,
                    member_credits_total=member_credits_total,
                    admin_seats_count=admin_seats_count,
                    admin_seat_price_credits=admin_seat_price,
                    admin_seats_total=admin_seats_total,
                    total_credits=total_credits,
                    total_amount=total_amount,
                    currency=currency,
                    tx_ref=tx_ref,
                    checkout_url=None,  # No payment required for postpay
                    session_id=None
                )

            except Exception as e:
                logger.error(f"Failed to allocate credits for postpay_org {tenant_name}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to allocate credits: {str(e)}"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bulk purchase: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create bulk purchase")


@router.get("/{tenant_id}/bulk-purchase/verify", response_model=BulkPurchaseVerifyResponse)
async def verify_bulk_purchase(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    session_id: str = Query(..., description="Stripe checkout session ID"),
    tx_ref: str = Query(..., description="Transaction reference"),
    payment_service: PaymentService = Depends(get_payment_service),
    credit_service: CreditService = Depends(get_credit_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Verify bulk purchase payment and allocate credits.

    Called by frontend after user completes Stripe checkout.
    Idempotent - safe to call multiple times.
    """
    try:
        # Check if already processed (idempotency check)
        if payment_service.already_processed_transaction(session_id):
            try:
                expected_amount, expected_currency, _ = payment_service.get_order_expectations_by_tx_ref(tx_ref)
                return BulkPurchaseVerifyResponse(
                    ok=True,
                    message="verified (already processed)",
                    tx_ref=tx_ref,
                    session_id=session_id,
                    credits_allocated=None  # Already allocated previously
                )
            except Exception:
                return BulkPurchaseVerifyResponse(
                    ok=True,
                    message="verified (already processed)",
                    tx_ref=tx_ref,
                    session_id=session_id
                )

        # Get expected payment details
        expected_amount, expected_currency, payment_tenant_id = payment_service.get_order_expectations_by_tx_ref(tx_ref)

        # Verify tenant matches
        if payment_tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")

        # Retrieve session from Stripe
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

        # Verify payment was successful
        ok = (
            session.payment_status == "paid"
            and Decimal(str(session.amount_total / 100)) == expected_amount
            and str(session.currency).upper() == expected_currency
            and str(session.client_reference_id) == tx_ref
        )

        # Mark payment status
        payment_service.mark_payment_status(
            tx_ref=tx_ref,
            status="successful" if ok else "failed",
            tx_id=session.payment_intent,
            payload={"verify": session.to_dict()}
        )

        credits_allocated = None

        if ok:
            # Allocate credits if not already granted
            if not payment_service.has_grant_for_tx_ref(tx_ref):
                # Get exchange rate from database
                rate = payment_service.get_credits_per_unit(expected_currency)
                credits = payment_service.compute_credits(expected_amount, expected_currency)
                valid_from, _ = payment_service.default_validity()

                meta = {
                    "tx_ref": tx_ref,
                    "session_id": session_id,
                    "payment_intent": session.payment_intent,
                    "currency": expected_currency,
                    "amount": str(expected_amount),
                    "rate": str(rate),
                    "source": "stripe",
                    "verify": True,
                    "purchase_type": "bulk",
                    "tenant_name": session.metadata.get('tenant_name'),
                    "member_count": session.metadata.get('member_count'),
                    "credits_per_member": session.metadata.get('credits_per_member'),
                    "admin_seats_count": session.metadata.get('admin_seats_count'),
                    "total_credits_requested": session.metadata.get('total_credits'),
                }

                # Create credit lot - purchased credits never expire
                credit_service.create_credit_lot(
                    tenant_id=tenant_id,
                    source="purchase",
                    credit_amount=credits,
                    valid_from=valid_from,
                    expires_at=None,  # Purchased credits never expire
                    metadata=meta,
                    original_tenant_id=tenant_id,
                )

                # Record grant
                payment_service.record_grant(
                    tx_ref=tx_ref,
                    tenant_id=tenant_id,
                    currency=expected_currency,
                    rate=rate,
                    credits_assigned=credits,
                )

                credits_allocated = int(credits)

                logger.info(f"Allocated {credits} credits to tenant {tenant_id} for bulk purchase tx_ref={tx_ref}")

            # Mark transaction as processed to prevent duplicate processing from webhook
            payment_service.mark_transaction_processed(session_id, tx_ref)

        return BulkPurchaseVerifyResponse(
            ok=ok,
            message="verified and credits allocated" if ok else "payment not successful",
            tx_ref=tx_ref,
            session_id=session_id,
            payment_intent=session.payment_intent,
            credits_allocated=credits_allocated
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying bulk purchase: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify bulk purchase")


# ============================================================================
# Direct Allocation Bulk Purchase Endpoints
# ============================================================================

@router.post("/{tenant_id}/bulk-purchase-direct", response_model=BulkPurchaseDirectResponse)
async def bulk_purchase_direct_allocation(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    request: BulkPurchaseDirectRequest = None,
    service: BillingService = Depends(get_billing_service),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Create bulk purchase with direct allocation to specific tenants.

    Unlike regular bulk purchase, this endpoint:
    - Does NOT calculate credits automatically
    - Accepts explicit list of tenants and credit amounts
    - Allocates credits DIRECTLY to specified tenants (not to org first)

    For prepay_org: Creates Stripe Checkout Session for payment.
    For postpay_org: Allocates credits immediately and tracks for month-end billing.
    """
    try:
        # Get organization config
        org_config = service.supabase.table('organization_billing_config') \
            .select('organization_type, tenants!inner(name)') \
            .eq('tenant_id', tenant_id) \
            .limit(1) \
            .execute()

        if not org_config.data:
            raise HTTPException(status_code=404, detail="Organization billing config not found")

        org_type = org_config.data[0]['organization_type']
        tenant_name = org_config.data[0]['tenants']['name']

        # Only prepay_org and postpay_org can use this
        if org_type not in ['prepay_org', 'postpay_org']:
            raise HTTPException(
                status_code=400,
                detail="Direct bulk purchase is only available for prepay and postpay organizations"
            )

        # Calculate total credits
        total_credits = sum(alloc.credit_amount for alloc in request.allocations)

        # Get exchange rate and calculate amount in requested currency
        currency = request.currency
        rate = payment_service.get_credits_per_unit(currency)  # credits per unit of currency
        total_amount = float(Decimal(str(total_credits)) / Decimal(str(rate)))  # amount = credits / rate

        # Generate transaction reference
        tx_ref = f"bulk-direct-{uuid.uuid4()}"
        user_id = current_user.get("user_id")

        # Store allocation plan for later retrieval
        allocation_metadata = {
            "allocations": [{"tenant_id": a.tenant_id, "credit_amount": a.credit_amount} for a in request.allocations],
            "org_tenant_id": tenant_id,
            "org_name": tenant_name,
            "org_type": org_type,
            "created_by": user_id,
            "total_credits": total_credits,
            "currency": currency,
            "rate": str(rate)
        }

        if org_type == 'prepay_org':
            # Create Stripe checkout session
            try:
                frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
                customer_email = current_user.get("email")

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[
                        {
                            "price_data": {
                                "currency": currency.lower(),
                                "product_data": {
                                    "name": f"{tenant_name} - Direct Credit Allocation",
                                    "description": f"Allocating {total_credits} credits to {len(request.allocations)} tenant(s)",
                                },
                                "unit_amount": int(total_amount * 100),  # Convert to cents
                            },
                            "quantity": 1,
                        }
                    ],
                    mode="payment",
                    success_url=f"{frontend_url}/billing/bulk-purchase-direct/complete?session_id={{CHECKOUT_SESSION_ID}}&tx_ref={tx_ref}",
                    cancel_url=f"{frontend_url}/billing/bulk-purchase-direct/cancelled?tx_ref={tx_ref}",
                    client_reference_id=tx_ref,
                    customer_email=customer_email,
                    metadata={
                        "tx_ref": tx_ref,
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "purpose": "bulk_direct_allocation",
                        "tenant_name": tenant_name,
                        "total_credits": total_credits,
                        "allocation_count": len(request.allocations),
                        "currency": currency,
                        "allocation_data": str(allocation_metadata)
                    },
                )
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error creating checkout session: {e}")
                raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

            # Store payment expectation
            payment_service.set_order_expectations(
                tx_ref=tx_ref,
                amount=Decimal(str(total_amount)),
                currency=currency,
                tenant_id=tenant_id,
                metadata=allocation_metadata
            )

            # Mark payment as pending
            payment_service.mark_payment_status(
                tx_ref=tx_ref,
                status="pending",
                tx_id=checkout_session.id,
                payload={"create": checkout_session.to_dict()}
            )

            logger.info(
                f"Created direct allocation checkout session for {tenant_name}: "
                f"{total_credits} credits ({currency} {total_amount}) to {len(request.allocations)} tenants, tx_ref={tx_ref}"
            )

            return BulkPurchaseDirectResponse(
                tenant_id=tenant_id,
                allocations=request.allocations,
                total_credits=total_credits,
                total_amount=total_amount,
                currency=currency,
                tx_ref=tx_ref,
                checkout_url=checkout_session.url,
                session_id=checkout_session.id
            )

        else:  # postpay_org
            # Allocate credits immediately and track for billing
            credit_service = CreditService()
            now = datetime.now(timezone.utc).isoformat()

            # Allocate to each tenant directly
            for allocation in request.allocations:
                # Create credit lot for the tenant
                credit_service.create_credit_lot(
                    tenant_id=allocation.tenant_id,
                    source="purchase",
                    credit_amount=Decimal(str(allocation.credit_amount)),
                    valid_from=now,
                    expires_at=None,  # No expiry for postpay
                    metadata={
                        "source": "bulk_direct_allocation",
                        "organization_id": tenant_id,
                        "tx_ref": tx_ref,
                        "postpay": True,
                        "currency": currency,
                        "rate": str(rate)
                    },
                    original_tenant_id=tenant_id
                )

                # Track allocation for billing
                try:
                    service.supabase.table('organization_credit_allocations').insert({
                        'tenant_id': tenant_id,
                        'allocation_type': 'bulk_direct_allocation',
                        'credit_amount': allocation.credit_amount,
                        'allocated_to_tenant_id': allocation.tenant_id,
                        'allocated_by_user_id': user_id,
                        'allocated_at': now,
                        'metadata': {
                            "source": "bulk_direct_allocation_postpay",
                            "tx_ref": tx_ref,
                            "total_in_batch": total_credits,
                            "currency": currency,
                            "rate": str(rate)
                        },
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to track postpay allocation: {e}", exc_info=True)

            logger.info(
                f"Allocated {total_credits} credits directly to {len(request.allocations)} "
                f"tenants for postpay org {tenant_name}, tx_ref={tx_ref}"
            )

            return BulkPurchaseDirectResponse(
                tenant_id=tenant_id,
                allocations=request.allocations,
                total_credits=total_credits,
                total_amount=total_amount,
                currency=currency,
                tx_ref=tx_ref,
                checkout_url=None,
                session_id=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating direct bulk purchase: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create direct bulk purchase")


@router.get("/{tenant_id}/bulk-purchase-direct/verify", response_model=BulkPurchaseDirectVerifyResponse)
async def verify_bulk_purchase_direct(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    session_id: str = Query(..., description="Stripe checkout session ID"),
    tx_ref: str = Query(..., description="Transaction reference"),
    payment_service: PaymentService = Depends(get_payment_service),
    credit_service: CreditService = Depends(get_credit_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Verify direct allocation bulk purchase payment and allocate credits to specified tenants.

    Called by frontend after user completes Stripe checkout.
    Idempotent - safe to call multiple times.
    """
    try:
        # Check if already processed
        if payment_service.already_processed_transaction(session_id):
            return BulkPurchaseDirectVerifyResponse(
                ok=True,
                message="verified (already processed)",
                tx_ref=tx_ref,
                session_id=session_id,
                allocations_completed=None
            )

        # Get expected payment details
        expected_amount, expected_currency, payment_tenant_id = payment_service.get_order_expectations_by_tx_ref(tx_ref)

        # Verify tenant matches
        if payment_tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")

        # Retrieve Stripe session
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving session: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve payment session")

        # Verify payment details match
        ok = (
            session.payment_status == "paid"
            and Decimal(str(session.amount_total / 100)) == expected_amount
            and str(session.currency).upper() == expected_currency
            and str(session.client_reference_id) == tx_ref
        )

        if ok:
            # Get allocation metadata from payment expectations
            try:
                metadata = payment_service.get_metadata_by_tx_ref(tx_ref)
                allocations = metadata.get("allocations", [])
                currency = metadata.get("currency", "USD")
                rate = metadata.get("rate")
            except Exception as e:
                logger.error(f"Failed to retrieve allocation metadata: {e}")
                raise HTTPException(status_code=500, detail="Failed to retrieve allocation plan")

            if not allocations:
                raise HTTPException(status_code=400, detail="No allocation plan found")

            # Allocate credits to each tenant
            now = datetime.now(timezone.utc).isoformat()
            allocations_count = 0

            for allocation in allocations:
                alloc_tenant_id = allocation["tenant_id"]
                alloc_credits = allocation["credit_amount"]

                # Create credit lot for the tenant
                credit_service.create_credit_lot(
                    tenant_id=alloc_tenant_id,
                    source="purchase",
                    credit_amount=Decimal(str(alloc_credits)),
                    valid_from=now,
                    expires_at=None,  # Purchased credits never expire
                    metadata={
                        "source": "bulk_direct_allocation",
                        "organization_id": tenant_id,
                        "tx_ref": tx_ref,
                        "session_id": session_id,
                        "verified": True,
                        "currency": currency,
                        "rate": rate
                    },
                    original_tenant_id=tenant_id
                )

                allocations_count += 1

            # Mark transaction as processed
            payment_service.mark_transaction_processed(session_id, tx_ref)

            logger.info(
                f"Completed direct allocation: {allocations_count} tenants received credits, tx_ref={tx_ref}"
            )

            return BulkPurchaseDirectVerifyResponse(
                ok=True,
                message="verified and credits allocated",
                tx_ref=tx_ref,
                session_id=session_id,
                payment_intent=session.payment_intent,
                allocations_completed=allocations_count
            )
        else:
            return BulkPurchaseDirectVerifyResponse(
                ok=False,
                message="payment not successful",
                tx_ref=tx_ref,
                session_id=session_id,
                payment_intent=session.payment_intent,
                allocations_completed=0
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying direct bulk purchase: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify direct bulk purchase")


# ============================================================================
# Admin Seat Billing History Endpoint
# ============================================================================

@router.get("/{tenant_id}/admin-seat-history", response_model=List[AdminSeatBillingHistoryResponse])
async def get_admin_seat_history(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    service: BillingService = Depends(get_billing_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin)
):
    """
    Get admin seat billing history for an organization.

    Returns historical records of monthly admin seat billing.
    Requires organization admin/owner access.
    """
    try:
        response = service.supabase.table('admin_seat_billing_history') \
            .select('*') \
            .eq('tenant_id', tenant_id) \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error getting admin seat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve admin seat billing history")
