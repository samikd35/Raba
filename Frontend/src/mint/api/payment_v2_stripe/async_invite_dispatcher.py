"""
Async Payment Invite Dispatcher for organization invitations.

Handles dispatching invites after successful payment verification.
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import BackgroundTasks

from ..system.core.async_supabase_client import get_async_service_role_client
from ..organization.service import OrganizationService
from ..organization.endpoints import _send_invite_and_update_payed
from src.mint.utils.url_safe_serializer import create_invite_token

logger = logging.getLogger(__name__)

TABLE = "organization_payment_invitations"
FRONTEND_URL = os.getenv("FRONTEND_URL", "")


class AsyncPaymentInviteDispatcher:
    """
    Async dispatcher for payment-gated organization invitations.
    """

    async def _get_org_name(self, organization_id: str) -> str:
        """Fetch organization name from tenants table."""
        try:
            db = await get_async_service_role_client()
            res = await db.table("tenants") \
                .select("name") \
                .eq("id", organization_id) \
                .limit(1) \
                .execute()
            if res.data:
                return res.data[0].get("name") or "Your Organization"
        except Exception as e:
            logger.error(f"[payment-invites] failed to fetch org name: {e}")
        return "Your Organization"

    async def _mark_paid(self, tx_ref: str) -> None:
        """Mark all invites for tx_ref as paid."""
        try:
            db = await get_async_service_role_client()
            await db.table(TABLE) \
                .update({"status": "paid"}) \
                .eq("tx_ref", tx_ref) \
                .execute()
        except Exception as e:
            logger.error(f"[payment-invites] mark_paid failed: {e}")

    async def _mark_sent(self, invite_id: str) -> None:
        """Mark a single invite as sent."""
        try:
            db = await get_async_service_role_client()
            ts = datetime.now(timezone.utc).isoformat()
            await db.table(TABLE) \
                .update({"status": "sent", "email_sent_at": ts}) \
                .eq("id", invite_id) \
                .execute()
        except Exception as e:
            logger.error(f"[payment-invites] mark_sent failed: {e}")

    async def _list_pending_invites(self, tx_ref: str) -> list:
        """Get pending invites for tx_ref."""
        try:
            db = await get_async_service_role_client()
            res = await db.table(TABLE) \
                .select("*") \
                .eq("tx_ref", tx_ref) \
                .eq("status", "pending_payment") \
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"[payment-invites] list_pending failed: {e}")
            return []

    async def dispatch_after_payment(
        self, tx_ref: str, background_tasks: BackgroundTasks
    ) -> None:
        """
        Dispatch invites after successful payment.

        1. Get all pending invites for tx_ref
        2. Mark them as paid
        3. Create canonical organization_invitations records
        4. Generate invite tokens
        5. Queue emails in background tasks
        """
        pending = await self._list_pending_invites(tx_ref)
        if not pending:
            return

        await self._mark_paid(tx_ref)

        org_service = OrganizationService(use_service_role=True)
        org_id = pending[0]["organization_id"]
        org_name = await self._get_org_name(org_id)

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

            # 2) Generate invite token
            token = create_invite_token(
                tenant_id=inv["organization_id"],
                is_admin=bool(inv.get("is_admin")),
                credit=int(inv.get("credits") or 0),
            )
            invite_link = f"{FRONTEND_URL}/payed-invite?token={token}&org_id={inv['organization_id']}"

            # 3) Queue email sending in background
            # We need to capture variables for the closure
            invite_id = inv["id"]
            to_email = inv["email"]
            is_team_leader = bool(inv.get("is_team_leader", False))
            credit_amount = int(inv.get("credits") or 0)

            def _send_and_mark(
                _invite_id: str,
                _org_inv_id: str | None,
                _to_email: str,
                _org_name: str,
                _link: str,
                _is_team_leader: bool,
                _credit_amount: int,
                _dispatcher: "AsyncPaymentInviteDispatcher",
            ):
                """Background task to send email and mark as sent."""
                try:
                    _send_invite_and_update_payed(
                        service=OrganizationService(),
                        invitation_id=_invite_id,
                        to_email=_to_email,
                        org_name=_org_name,
                        invite_link=_link,
                        is_team_leader=_is_team_leader,
                        credit_amount=_credit_amount,
                    )

                    # Mark payment invite as sent (sync call in background)
                    from ..system.core.supabase_client import get_supabase_client
                    client = get_supabase_client().client
                    ts = datetime.now(timezone.utc).isoformat()
                    client.table(TABLE) \
                        .update({"status": "sent", "email_sent_at": ts}) \
                        .eq("id", _invite_id) \
                        .execute()

                    # Also mark the canonical org invitation as sent (if created)
                    if _org_inv_id:
                        try:
                            org_svc = OrganizationService(use_service_role=True)
                            org_svc.update_invitation_status(
                                invitation_id=_org_inv_id,
                                status="sent",
                                sent_at=datetime.now(timezone.utc),
                            )
                        except Exception as e:
                            logger.error(
                                f"[payment-invites] failed to mark org invitation sent: {e}"
                            )
                except Exception as e:
                    logger.error(f"[payment-invites] failed to send invite to {_to_email}: {e}")

            background_tasks.add_task(
                _send_and_mark,
                invite_id,
                org_inv_id,
                to_email,
                org_name,
                invite_link,
                is_team_leader,
                credit_amount,
                self,
            )
