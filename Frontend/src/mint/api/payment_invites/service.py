import logging
import os
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from fastapi import BackgroundTasks, HTTPException
from src.mint.api.system.core.supabase_client import get_supabase_client
from src.mint.utils.url_safe_serializer import create_invite_token

from ..organization.endpoints import _send_invite_and_update_payed
from ..organization.service import OrganizationService

load_dotenv()

logger = logging.getLogger(__name__)

TABLE = "organization_payment_invitations"


class PaymentInviteStore:
    def __init__(self):
        self.client = get_supabase_client().client

    def insert_invite(self, row: dict) -> dict:
        res = self.client.table(TABLE).insert(row, returning="representation").execute()
        data = res.data
        if not data:
            return {}
        return data[0] if isinstance(data, list) else data

    def list_by_tx_ref_and_status(self, tx_ref: str, status_val: str) -> List[dict]:
        res = (
            self.client.table(TABLE)
            .select("*")
            .eq("tx_ref", tx_ref)
            .eq("status", status_val)
            .execute()
        )
        return res.data or []

    def mark_paid_by_tx_ref(self, tx_ref: str) -> None:
        self.client.table(TABLE).update({"status": "paid"}).eq(
            "tx_ref", tx_ref
        ).execute()

    def mark_sent(self, invite_id: str) -> None:
        # Use an explicit UTC timestamp instead of a SQL literal string like "now()"
        ts = datetime.now(timezone.utc).isoformat()
        self.client.table(TABLE).update({"status": "sent", "email_sent_at": ts}).eq(
            "id", invite_id
        ).execute()


class PaymentInviteDispatcher:
    def __init__(self):
        self.store = PaymentInviteStore()

    def _mark_paid(self, tx_ref: str):
        try:
            self.store.mark_paid_by_tx_ref(tx_ref)
        except Exception as e:
            print(f"[payment-invites] mark_paid failed: {e}")

    async def dispatch_after_payment(
        self, tx_ref: str, background_tasks: BackgroundTasks
    ):
        pending = self.store.list_by_tx_ref_and_status(tx_ref, "pending_payment")
        if not pending:
            return

        self._mark_paid(tx_ref)

        frontend_url = os.getenv("FRONTEND_URL", "")
        org_service = OrganizationService(use_service_role=True)

        for inv in pending:
            # 1) Create a canonical organization_invitations row so join flow can see it
            try:
                org_inv = org_service.record_invitation(
                    organization_id=inv["organization_id"],
                    email=inv["email"],
                    is_admin=bool(inv.get("is_admin")),
                    is_team_leader=bool(inv.get("is_team_leader", False)),
                    invited_by_user_id=inv.get("invited_by_user_id"),
                    invited_by_email=inv.get("invited_by_email"),
                    credits=int(inv.get("credits") or 0),
                    can_skip_modules=bool(inv.get("can_skip_modules", False)),
                )
                org_inv_id = org_inv.get("id") if isinstance(org_inv, dict) else None
            except Exception as e:
                logger.error(
                    f"[payment-invites] failed to record org invitation for {inv['email']}: {e}"
                )
                org_inv_id = None
            token = create_invite_token(
                tenant_id=inv["organization_id"],
                is_admin=bool(inv.get("is_admin")),
                credit=int(inv.get("credits") or 0),
            )
            invite_link = f"{frontend_url}/payed-invite?token={token}&org_id={inv['organization_id']}"

            # queue email and mark row sent inside the email job
            def _send_and_mark(
                invitation_id: str,
                org_invitation_id: str | None,
                to_email: str,
                org_name: str,
                link: str,
                is_team_leader: bool,
                credit_amount: int,
            ):
                _send_invite_and_update_payed(
                    service=OrganizationService(),
                    invitation_id=invitation_id,
                    to_email=to_email,
                    org_name=org_name or "Your Organization",
                    invite_link=link,
                    is_team_leader=is_team_leader,
                    credit_amount=credit_amount,
                )
                self.store.mark_sent(invitation_id)

                # Also mark the canonical org invitation as sent (if created)
                if org_invitation_id:
                    try:
                        org_service.update_invitation_status(
                            invitation_id=org_invitation_id,
                            status="sent",
                            sent_at=datetime.now(timezone.utc),
                        )
                    except Exception as e:
                        logger.error(
                            f"[payment-invites] failed to mark org invitation sent: {e}"
                        )

            background_tasks.add_task(
                _send_and_mark,
                inv["id"],
                org_inv_id,
                inv["email"],
                inv.get("organization_name"),
                invite_link,
                bool(inv.get("is_team_leader", False)),
                int(inv.get("credits") or 0),
            )
