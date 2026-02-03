from datetime import datetime, timedelta, timezone
from decimal import ROUND_FLOOR, Decimal
from typing import Optional, Tuple

from ..system.core.supabase_client import (get_service_role_client,
                                           get_standard_client)


class PaymentService:
    """
    Centralizes all database interactions for payments.
    Provider-agnostic service that works with both Flutterwave and Stripe.
    """

    def __init__(self, use_service_role: bool = True):
        self.db = (
            get_service_role_client().client
            if use_service_role
            else get_standard_client().client
        )

    # ── Payment Intents / Records ──────────────────────────────────────────────

    def save_payment_intent(
        self,
        tx_ref: str,
        amount: Decimal,
        currency: str,
        email: Optional[str],
        user_id: str,
        tenant_id: str,
    ) -> dict:
        """
        Create a payment-intent row:
          - tx_ref (UNIQUE), amount (Decimal->numeric), currency, email, status='created'
        """
        row = {
            "tx_ref": tx_ref,
            "amount": str(amount),  # keep Decimal precision
            "currency": currency.upper(),
            "email": email,
            "status": "created",
            "user_id": user_id,
            "tenant_id": tenant_id,
        }
        res = self.db.table("payments").insert(row).execute()
        if not getattr(res, "data", None):
            raise RuntimeError(f"Failed to insert payment intent for tx_ref={tx_ref}")
        return res.data[0]

    def mark_payment_status(
        self,
        tx_ref: str,
        status: str,
        tx_id: Optional[str],
        payload: dict,
    ) -> dict:
        """
        Update a payment row by tx_ref:
          - status in {'created','pending','successful','failed'}
          - store tx_id (provider transaction/session id)
          - append/replace provider_payload (last seen)
        """
        update_row = {
            "status": status,
            "tx_id": tx_id,
            "provider_payload": payload or {},
        }
        res = (
            self.db.table("payments").update(update_row).eq("tx_ref", tx_ref).execute()
        )
        if not getattr(res, "data", None):
            raise RuntimeError(f"Failed to update status for tx_ref={tx_ref}")
        return res.data[0]

    def get_order_expectations_by_tx_ref(self, tx_ref: str) -> Tuple[Decimal, str, str]:
        """
        Return (expected_amount, expected_currency, tenant_id) for the tx_ref.
        Raises if not found.
        """
        res = (
            self.db.table("payments")
            .select("amount,currency,tenant_id")
            .eq("tx_ref", tx_ref)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        if not rows:
            raise LookupError(f"tx_ref not found: {tx_ref}")

        row = rows[0]
        amount = Decimal(str(row["amount"]))
        currency = str(row["currency"]).upper()
        return (amount, currency, row["tenant_id"])

    # ── Webhook Dedupe ────────────────────────────────────────────────────────

    def already_processed_transaction(self, tx_id: str) -> bool:
        """
        True if this provider transaction_id/session_id was already processed.
        Uses a dedicated table for dedupe (processed_transactions).
        Note: For Stripe, tx_id is the session_id.
        """
        res = (
            self.db.table("processed_transactions")
            .select("transaction_id")
            .eq("transaction_id", tx_id)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        return len(rows) > 0

    def mark_transaction_processed(self, tx_id: str, tx_ref: str) -> dict:
        """
        Record a processed transaction_id/session_id to guard against webhook retries.
        Idempotent via PK/unique constraint.
        Note: For Stripe, tx_id can be session_id or payment_intent (both are strings)
        """
        # upsert ensures idempotency (no error if it already exists)
        res = (
            self.db.table("processed_transactions")
            .upsert({"transaction_id": str(tx_id), "tx_ref": tx_ref})
            .execute()
        )
        return (getattr(res, "data", None) or [{}])[0]

    # ── Credit exchange rates ─────────────────────────────────────────────────

    def get_credits_per_unit(self, currency: str) -> Decimal:
        """
        Look up how many credits are granted per 1 unit of the currency.
        Expects one active row per currency.
        """
        res = (
            self.db.table("credit_exchange_rates")
            .select("credits_per_unit")
            .eq("currency", currency.upper())
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        if not rows:
            raise LookupError(
                f"Payment currency '{currency.upper()}' is not currently supported. "
                f"Please contact support to enable this currency or choose a different payment currency."
            )

        return Decimal(str(rows[0]["credits_per_unit"]))

    # ── Idempotent grant ledger ───────────────────────────────────────────────

    def has_grant_for_tx_ref(self, tx_ref: str) -> bool:
        rows = (
            self.db.table("payment_credit_grants")
            .select("tx_ref")
            .eq("tx_ref", tx_ref)
            .execute()
            .data
            or []
        )
        return len(rows) > 0

    def record_grant(
        self,
        *,
        tx_ref: str,
        tenant_id: str,
        currency: str,
        rate: Decimal,
        credits_assigned: Decimal,
    ) -> dict:
        payload = {
            "tx_ref": tx_ref,
            "tenant_id": tenant_id,
            "currency": currency.upper(),
            "credits_per_unit": str(rate),
            "credits_assigned": str(credits_assigned),
        }
        return self.db.table("payment_credit_grants").insert(payload).execute().data[0]

    # ── High-level: compute & grant credits ───────────────────────────────────

    def compute_credits(self, amount: Decimal, currency: str) -> Decimal:
        rate = self.get_credits_per_unit(currency)
        # Default: floor to whole credits. Adjust if you allow fractional credits.
        raw = amount * rate
        return raw.quantize(Decimal("1"), rounding=ROUND_FLOOR)

    def default_validity(self) -> tuple[str, str]:
        """Return (valid_from_iso, expires_at_iso). Here: now → +365 days."""
        now = datetime.now(timezone.utc)
        return now.isoformat(), (now + timedelta(days=365)).isoformat()
