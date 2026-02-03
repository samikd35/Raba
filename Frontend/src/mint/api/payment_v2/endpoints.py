import os
import uuid
from decimal import Decimal

import httpx
from dotenv import load_dotenv
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, Response)

from ..auth_v2.utils import get_current_user
from ..credit.service import CreditService
from ..payment_invites.service import PaymentInviteDispatcher
from .models import CreatePaymentBody, CreatePaymentResp, VerifyResp
from .service import PaymentService

load_dotenv()

router = APIRouter(tags=["payments"])

service = PaymentService()
credit_service = CreditService()


FLW_SECRET = os.getenv("FLW_SECRET")
FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH")
if not FLW_SECRET or not FLW_SECRET_HASH:
    raise RuntimeError("Missing FLW_SECRET_KEY or FLW_SECRET_HASH")

FLW_API = "https://api.flutterwave.com/v3"
HTTPX_TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def flw_headers():
    return {"Authorization": f"Bearer {FLW_SECRET}"}


@router.post("/payments/create", response_model=CreatePaymentResp)
async def create_payment(
    body: CreatePaymentBody, current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    tenant_id = current_user["tenant_id"]
    tx_ref = f"pay_{uuid.uuid4().hex[:12]}"
    service.save_payment_intent(
        tx_ref, body.amount, body.currency, body.email, user_id, tenant_id
    )

    frontend_url = os.getenv("FRONTEND_URL", "")

    payload = {
        "tx_ref": tx_ref,
        "amount": str(body.amount),
        "currency": body.currency,
        "redirect_url": f"{frontend_url}/payments/complete",
        "customer": {"email": body.email, "name": body.name},
        "payment_options": "card,banktransfer,ussd",
    }
    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        r = await client.post(
            f"{FLW_API}/payments", json=payload, headers=flw_headers()
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Flutterwave error: {r.text}")

    link = (r.json().get("data") or {}).get("link")
    if not link:
        raise HTTPException(502, f"Unexpected Flutterwave response: {r.text}")
    service.mark_payment_status(tx_ref, "pending", None, {"create": r.json()})
    return CreatePaymentResp(checkout_link=link, tx_ref=tx_ref)


@router.get("/payments/verify", response_model=VerifyResp)
async def verify(
    transaction_id: int, tx_ref: str, current_user: dict = Depends(get_current_user)
):
    # Check if already processed (idempotency check)
    if service.already_processed_transaction(transaction_id):
        # Already processed, return success without re-processing
        try:
            expected_amount, expected_currency, _ = (
                service.get_order_expectations_by_tx_ref(tx_ref)
            )
            return VerifyResp(
                ok=True,
                message="verified (already processed)",
                tx_id=transaction_id,
                tx_ref=tx_ref,
                raw={"note": "Transaction already processed successfully"},
            )
        except Exception:
            return VerifyResp(
                ok=True,
                message="verified (already processed)",
                tx_id=transaction_id,
                tx_ref=tx_ref,
                raw={"note": "Transaction already processed successfully"},
            )

    expected_amount, expected_currency, _ = service.get_order_expectations_by_tx_ref(
        tx_ref
    )
    tenant_id = current_user["tenant_id"]
    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        r = await client.get(
            f"{FLW_API}/transactions/{transaction_id}/verify", headers=flw_headers()
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Flutterwave error: {r.text}")

    data = r.json().get("data", {})
    ok = (
        str(data.get("status")).lower() == "successful"
        and Decimal(str(data.get("amount"))) == expected_amount
        and str(data.get("currency")).upper() == expected_currency
        and str(data.get("tx_ref")) == tx_ref
    )
    service.mark_payment_status(
        tx_ref, "successful" if ok else "failed", data.get("id"), {"verify": data}
    )

    if ok and tenant_id:
        # Idempotency: grant only once
        if not service.has_grant_for_tx_ref(tx_ref):
            credits = service.compute_credits(expected_amount, expected_currency)
            valid_from, expires_at = service.default_validity()
            meta = {
                "tx_ref": tx_ref,
                "tx_id": data.get("id"),
                "currency": expected_currency,
                "amount": str(expected_amount),
                "rate": str(service.get_credits_per_unit(expected_currency)),
                "source": "flutterwave",
            }
            credit_service.create_credit_lot(
                tenant_id=tenant_id,
                source="purchase",
                credit_amount=credits,
                valid_from=valid_from,
                expires_at=expires_at,
                metadata=meta,
                original_tenant_id=tenant_id,
            )
            service.record_grant(
                tx_ref=tx_ref,
                tenant_id=tenant_id,
                currency=expected_currency,
                rate=service.get_credits_per_unit(expected_currency),
                credits_assigned=credits,
            )

        # Mark transaction as processed to prevent duplicate processing from webhook
        service.mark_transaction_processed(transaction_id, tx_ref)

    return VerifyResp(
        ok=ok,
        message="verified" if ok else "mismatch or not successful",
        tx_id=data.get("id"),
        tx_ref=data.get("tx_ref"),
        raw=data,
    )


@router.post("/webhooks/flutterwave")
async def flutterwave_webhook(request: Request):
    signature = request.headers.get("verif-hash")
    if not signature or signature != FLW_SECRET_HASH:
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    data = payload.get("data") or {}
    tx_id = data.get("id")
    tx_ref = data.get("tx_ref")
    if tx_id is None or not tx_ref:
        return Response(status_code=200)

    if service.already_processed_transaction(int(tx_id)):
        return Response(status_code=200)

    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        r = await client.get(
            f"{FLW_API}/transactions/{tx_id}/verify", headers=flw_headers()
        )
    if r.status_code != 200:
        service.mark_payment_status(
            tx_ref, "failed", int(tx_id), {"webhook_verify_failed": r.text}
        )
        service.mark_transaction_processed(int(tx_id), tx_ref)
        return Response(status_code=200)

    verify_data = r.json().get("data", {})
    try:
        expected_amount, expected_currency, tenant_id = (
            service.get_order_expectations_by_tx_ref(tx_ref)
        )
    except Exception:
        service.mark_payment_status(
            tx_ref, "failed", int(tx_id), {"unknown_tx_ref": payload}
        )
        service.mark_transaction_processed(int(tx_id), tx_ref)
        return Response(status_code=200)

    ok = (
        str(verify_data.get("status")).lower() == "successful"
        and Decimal(str(verify_data.get("amount"))) == expected_amount
        and str(verify_data.get("currency")).upper() == expected_currency
        and str(verify_data.get("tx_ref")) == tx_ref
    )
    service.mark_payment_status(
        tx_ref,
        "successful" if ok else "failed",
        int(tx_id),
        {"webhook": payload, "verify": verify_data},
    )

    if ok and tenant_id:
        if not service.has_grant_for_tx_ref(tx_ref):
            credits = service.compute_credits(expected_amount, expected_currency)
            valid_from, expires_at = service.default_validity()
            meta = {
                "tx_ref": tx_ref,
                "tx_id": tx_id,
                "currency": expected_currency,
                "amount": str(expected_amount),
                "rate": str(service.get_credits_per_unit(expected_currency)),
                "source": "flutterwave",
            }
            credit_service.create_credit_lot(
                tenant_id=tenant_id,
                source="purchase",
                credit_amount=credits,
                valid_from=valid_from,
                expires_at=expires_at,
                metadata=meta,
                original_tenant_id=tenant_id,
            )
            service.record_grant(
                tx_ref=tx_ref,
                tenant_id=tenant_id,
                currency=expected_currency,
                rate=service.get_credits_per_unit(expected_currency),
                credits_assigned=credits,
            )

    service.mark_transaction_processed(int(tx_id), tx_ref)
    return Response(status_code=200)


@router.get("/payments-org/verify", response_model=VerifyResp)
async def verify_org(
    transaction_id: int,
    tx_ref: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    # Check if already processed (idempotency check)
    if service.already_processed_transaction(transaction_id):
        # Already processed, return success without re-processing
        try:
            expected_amount, expected_currency, _ = (
                service.get_order_expectations_by_tx_ref(tx_ref)
            )
            return VerifyResp(
                ok=True,
                message="verified (already processed)",
                tx_id=transaction_id,
                tx_ref=tx_ref,
                raw={"note": "Transaction already processed successfully"},
            )
        except Exception:
            return VerifyResp(
                ok=True,
                message="verified (already processed)",
                tx_id=transaction_id,
                tx_ref=tx_ref,
                raw={"note": "Transaction already processed successfully"},
            )

    expected_amount, expected_currency, _ = service.get_order_expectations_by_tx_ref(
        tx_ref
    )
    tenant_id = current_user["tenant_id"]
    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        r = await client.get(
            f"{FLW_API}/transactions/{transaction_id}/verify", headers=flw_headers()
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Flutterwave error: {r.text}")

    data = r.json().get("data", {})
    ok = (
        str(data.get("status")).lower() == "successful"
        and Decimal(str(data.get("amount"))) == expected_amount
        and str(data.get("currency")).upper() == expected_currency
        and str(data.get("tx_ref")) == tx_ref
    )
    service.mark_payment_status(
        tx_ref, "successful" if ok else "failed", data.get("id"), {"verify": data}
    )

    if ok and tenant_id:
        dispatcher = PaymentInviteDispatcher()
        await dispatcher.dispatch_after_payment(tx_ref, background_tasks)

        # Mark transaction as processed to prevent duplicate processing from webhook
        service.mark_transaction_processed(transaction_id, tx_ref)

    return VerifyResp(
        ok=ok,
        message="verified" if ok else "mismatch or not successful",
        tx_id=data.get("id"),
        tx_ref=data.get("tx_ref"),
        raw=data,
    )


@router.post("/webhooks-org/flutterwave")
async def flutterwave_webhook_org(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("verif-hash")
    if not signature or signature != FLW_SECRET_HASH:
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    data = payload.get("data") or {}
    tx_id = data.get("id")
    tx_ref = data.get("tx_ref")
    if tx_id is None or not tx_ref:
        return Response(status_code=200)

    if service.already_processed_transaction(int(tx_id)):
        return Response(status_code=200)

    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        r = await client.get(
            f"{FLW_API}/transactions/{tx_id}/verify", headers=flw_headers()
        )
    if r.status_code != 200:
        service.mark_payment_status(
            tx_ref, "failed", int(tx_id), {"webhook_verify_failed": r.text}
        )
        service.mark_transaction_processed(int(tx_id), tx_ref)
        return Response(status_code=200)

    verify_data = r.json().get("data", {})
    try:
        expected_amount, expected_currency, tenant_id = (
            service.get_order_expectations_by_tx_ref(tx_ref)
        )
    except Exception:
        service.mark_payment_status(
            tx_ref, "failed", int(tx_id), {"unknown_tx_ref": payload}
        )
        service.mark_transaction_processed(int(tx_id), tx_ref)
        return Response(status_code=200)

    ok = (
        str(verify_data.get("status")).lower() == "successful"
        and Decimal(str(verify_data.get("amount"))) == expected_amount
        and str(verify_data.get("currency")).upper() == expected_currency
        and str(verify_data.get("tx_ref")) == tx_ref
    )
    service.mark_payment_status(
        tx_ref,
        "successful" if ok else "failed",
        int(tx_id),
        {"webhook": payload, "verify": verify_data},
    )

    if ok and tenant_id:
        dispatcher = PaymentInviteDispatcher()
        await dispatcher.dispatch_after_payment(tx_ref, background_tasks)

    service.mark_transaction_processed(int(tx_id), tx_ref)
    return Response(status_code=200)
