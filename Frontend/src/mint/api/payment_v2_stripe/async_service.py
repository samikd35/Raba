"""
Async PaymentService for high-performance payment operations.

This service provides async versions of all payment database operations,
enabling true concurrent request handling without blocking the event loop.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import ROUND_FLOOR, Decimal
from typing import Optional, Tuple, Dict, Any

from fastapi import HTTPException

from ..system.core.async_supabase_client import get_async_service_role_client

logger = logging.getLogger(__name__)


class AsyncPaymentService:
    """
    Async payment service for non-blocking database operations.

    All methods are async and use the async Supabase client.
    Exchange rate is fetched once per request and passed to methods that need it.
    """

    # ── Payment Intents / Records ──────────────────────────────────────────────

    async def save_payment_intent(
        self,
        tx_ref: str,
        amount: Decimal,
        currency: str,
        email: Optional[str],
        user_id: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Create a payment-intent row asynchronously.
        """
        db = await get_async_service_role_client()
        row = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency.upper(),
            "email": email,
            "status": "created",
            "user_id": user_id,
            "tenant_id": tenant_id,
        }
        if metadata:
            row["metadata"] = metadata

        try:
            res = await db.table("payments").insert(row).execute()
            if not getattr(res, "data", None):
                raise HTTPException(
                    status_code=500,
                    detail="Unable to create payment. Please try again or contact support."
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save payment intent: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to create payment. Please try again or contact support."
            )

    async def mark_payment_status(
        self,
        tx_ref: str,
        status: str,
        tx_id: Optional[str],
        payload: dict,
    ) -> dict:
        """
        Update a payment row by tx_ref asynchronously.
        """
        db = await get_async_service_role_client()
        update_row = {
            "status": status,
            "tx_id": tx_id,
            "provider_payload": payload or {},
        }
        try:
            res = await db.table("payments").update(update_row).eq("tx_ref", tx_ref).execute()
            if not getattr(res, "data", None):
                raise HTTPException(
                    status_code=500,
                    detail="Unable to update payment status. Please try again or contact support."
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update payment status: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to update payment status. Please try again or contact support."
            )

    async def get_order_expectations_by_tx_ref(self, tx_ref: str) -> Tuple[Decimal, str, str]:
        """
        Return (expected_amount, expected_currency, tenant_id) for the tx_ref asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("payments") \
                .select("amount,currency,tenant_id") \
                .eq("tx_ref", tx_ref) \
                .limit(1) \
                .execute()

            rows = getattr(res, "data", None) or []
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail="Payment not found. The payment reference may be invalid or expired."
                )

            row = rows[0]
            amount = Decimal(str(row["amount"]))
            currency = str(row["currency"]).upper()
            return (amount, currency, row["tenant_id"])
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get order expectations: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to retrieve payment details. Please try again or contact support."
            )

    async def get_metadata_by_tx_ref(self, tx_ref: str) -> Dict[str, Any]:
        """
        Get metadata for a tx_ref asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("payments") \
                .select("metadata") \
                .eq("tx_ref", tx_ref) \
                .limit(1) \
                .execute()

            rows = getattr(res, "data", None) or []
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail="Payment not found. The payment reference may be invalid or expired."
                )

            return rows[0].get("metadata") or {}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to retrieve payment details. Please try again or contact support."
            )

    # ── Webhook Dedupe ────────────────────────────────────────────────────────

    async def already_processed_transaction(self, tx_id: str) -> bool:
        """
        Check if transaction was already processed asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("processed_transactions") \
                .select("transaction_id") \
                .eq("transaction_id", tx_id) \
                .execute()
            rows = getattr(res, "data", None) or []
            return len(rows) > 0
        except Exception as e:
            logger.error(f"Failed to check processed transaction: {e}")
            # Return False to allow processing - better to risk duplicate than block
            return False

    async def mark_transaction_processed(self, tx_id: str, tx_ref: str) -> dict:
        """
        Record a processed transaction asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("processed_transactions") \
                .upsert({"transaction_id": str(tx_id), "tx_ref": tx_ref}) \
                .execute()
            return (getattr(res, "data", None) or [{}])[0]
        except Exception as e:
            logger.error(f"Failed to mark transaction processed: {e}")
            # Don't raise - this is a safety mechanism, not critical path
            return {}

    # ── Credit exchange rates ─────────────────────────────────────────────────

    async def get_credits_per_unit(self, currency: str) -> Decimal:
        """
        Look up how many credits are granted per 1 unit of the currency asynchronously.

        Note: Call this ONCE per request and pass the rate to other methods.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("credit_exchange_rates") \
                .select("credits_per_unit") \
                .eq("currency", currency.upper()) \
                .eq("is_active", True) \
                .limit(1) \
                .execute()

            rows = getattr(res, "data", None) or []
            if not rows:
                raise HTTPException(
                    status_code=400,
                    detail=f"The currency '{currency.upper()}' is not currently supported. "
                           f"Please select a different currency or contact support."
                )

            return Decimal(str(rows[0]["credits_per_unit"]))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get exchange rate: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to retrieve currency exchange rate. Please try again or contact support."
            )

    # ── Idempotent grant ledger ───────────────────────────────────────────────

    async def has_grant_for_tx_ref(self, tx_ref: str) -> bool:
        """
        Check if a grant exists for tx_ref asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("payment_credit_grants") \
                .select("tx_ref") \
                .eq("tx_ref", tx_ref) \
                .execute()
            rows = getattr(res, "data", None) or []
            return len(rows) > 0
        except Exception as e:
            logger.error(f"Failed to check grant: {e}")
            # Return False to allow grant - idempotency check will handle duplicates
            return False

    async def record_grant(
        self,
        *,
        tx_ref: str,
        tenant_id: str,
        currency: str,
        rate: Decimal,
        credits_assigned: Decimal,
    ) -> dict:
        """
        Record a credit grant asynchronously.
        """
        db = await get_async_service_role_client()
        payload = {
            "tx_ref": tx_ref,
            "tenant_id": tenant_id,
            "currency": currency.upper(),
            "credits_per_unit": str(rate),
            "credits_assigned": str(credits_assigned),
        }
        try:
            res = await db.table("payment_credit_grants").insert(payload).execute()
            return res.data[0]
        except Exception as e:
            logger.error(f"Failed to record grant: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to record credit grant. Please contact support if credits were not added."
            )

    # ── High-level: compute & grant credits ───────────────────────────────────

    def compute_credits(self, amount: Decimal, rate: Decimal) -> Decimal:
        """
        Compute credits from amount and rate.

        This is synchronous as it's just math, no DB call.
        Pass the rate that was already fetched.
        """
        raw = amount * rate
        return raw.quantize(Decimal("1"), rounding=ROUND_FLOOR)

    def default_validity(self) -> Tuple[str, str]:
        """
        Return (valid_from_iso, expires_at_iso).
        Purchased credits: now -> +365 days.
        """
        now = datetime.now(timezone.utc)
        return now.isoformat(), (now + timedelta(days=365)).isoformat()

    # ── Invoice Operations ────────────────────────────────────────────────────

    async def get_invoice_by_stripe_id(self, stripe_invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get invoice by Stripe invoice ID asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table("invoices") \
                .select("*") \
                .eq("stripe_invoice_id", stripe_invoice_id) \
                .limit(1) \
                .execute()

            rows = getattr(res, "data", None) or []
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Failed to get invoice by stripe_id: {e}")
            return None

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_intent: Optional[str],
    ) -> bool:
        """
        Mark an invoice as paid asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            now = datetime.now(timezone.utc)
            update_data = {
                "status": "paid",
                "paid_at": now.isoformat(),
                "payment_method": "stripe",
                "payment_reference": payment_intent,
                "updated_at": now.isoformat(),
            }

            await db.table("invoices") \
                .update(update_data) \
                .eq("id", invoice_id) \
                .execute()

            return True
        except Exception as e:
            logger.error(f"Failed to mark invoice paid: {e}")
            return False


class AsyncPaymentInviteStore:
    """
    Async store for organization payment invitations.
    """

    TABLE = "organization_payment_invitations"

    async def insert_invites_batch(self, rows: list) -> list:
        """
        Insert multiple invites in a single batch operation asynchronously.
        """
        if not rows:
            return []

        db = await get_async_service_role_client()
        try:
            res = await db.table(self.TABLE).insert(rows).execute()
            return getattr(res, "data", None) or []
        except Exception as e:
            logger.error(f"Failed to insert invites batch: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to create invitations. Please try again or contact support."
            )

    async def list_by_tx_ref_and_status(self, tx_ref: str, status_val: str) -> list:
        """
        Get invites by tx_ref and status asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            res = await db.table(self.TABLE) \
                .select("*") \
                .eq("tx_ref", tx_ref) \
                .eq("status", status_val) \
                .execute()
            return getattr(res, "data", None) or []
        except Exception as e:
            logger.error(f"Failed to list invites: {e}")
            return []

    async def mark_paid_by_tx_ref(self, tx_ref: str) -> None:
        """
        Mark all invites for tx_ref as paid asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            await db.table(self.TABLE) \
                .update({"status": "paid"}) \
                .eq("tx_ref", tx_ref) \
                .execute()
        except Exception as e:
            logger.error(f"Failed to mark invites as paid: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unable to update invitation status. Please contact support."
            )

    async def mark_sent(self, invite_id: str) -> None:
        """
        Mark a single invite as sent asynchronously.
        """
        db = await get_async_service_role_client()
        try:
            ts = datetime.now(timezone.utc).isoformat()
            await db.table(self.TABLE) \
                .update({"status": "sent", "email_sent_at": ts}) \
                .eq("id", invite_id) \
                .execute()
        except Exception as e:
            logger.error(f"Failed to mark invite as sent: {e}")
            # Don't raise - email was sent, just status update failed

    async def has_pending_invites(self, tx_ref: str) -> bool:
        """
        Check if there are pending invites for tx_ref that haven't been dispatched.

        Returns True if there are invites still in "pending_payment" status.
        Used for idempotency - if no pending invites, dispatch was already handled.
        """
        pending = await self.list_by_tx_ref_and_status(tx_ref, "pending_payment")
        return len(pending) > 0
