from typing import Any, Dict, List, Optional

from ..system.core.supabase_client import get_supabase_client

TABLE = "credit_exchange_rates"


class CreditExchangeService:
    """All DB interactions for credit exchange rates (Supabase/PostgREST)."""

    def __init__(self, use_service_role: bool = True):
        self.client = get_supabase_client(use_service_role=use_service_role).client

    # ----- Reads -----

    def list_rates(self, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        q = self.client.table(TABLE).select("*")
        if active is not None:
            q = q.eq("is_active", active)
        res = q.order("currency", desc=False).execute()
        return res.data or []

    def get_rate(self, currency: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table(TABLE)
            .select("*")
            .eq("currency", currency.upper())
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    # ----- Mutations -----

    def create_rate(self, row: Dict[str, Any]) -> Dict[str, Any]:
        # Do NOT chain .select() on insert; Supabase returns inserted rows already.
        ins = self.client.table(TABLE).insert(row).execute()
        rows = ins.data or []
        return rows[0] if rows else self.get_rate(row["currency"])

    def update_rate(
        self, currency: str, patch: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not patch:
            return self.get_rate(currency)
        upd = (
            self.client.table(TABLE)
            .update(patch)
            .eq("currency", currency.upper())
            .execute()
        )
        rows = upd.data or []
        return rows[0] if rows else self.get_rate(currency)

    def delete_rate(self, currency: str) -> int:
        # Hard delete (use with care; soft-deactivate via update is preferred).
        res = (
            self.client.table(TABLE).delete().eq("currency", currency.upper()).execute()
        )
        if res and isinstance(res.data, list):
            return len(res.data)
        # Some setups return None for delete; fall back to presence check.
        return 0
