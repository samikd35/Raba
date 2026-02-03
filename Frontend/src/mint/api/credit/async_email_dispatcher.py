"""
Background email dispatcher for credit operations.

These functions are designed to be called via FastAPI's BackgroundTasks.add_task().
They run after the HTTP response is returned, so they don't block the request.
"""

import logging

from ..services.communication.email_service import email_service

logger = logging.getLogger(__name__)


def dispatch_credit_grant_email(
    to_email: str,
    org_name: str,
    credit_amount: int,
    expires_at_formatted: str,
    granted_by_name: str,
) -> None:
    """
    Background task to send credit grant notification email.

    Called via BackgroundTasks.add_task() - runs after response is returned.

    Args:
        to_email: Recipient email address
        org_name: Organization name
        credit_amount: Number of credits granted
        expires_at_formatted: Human-readable expiry date
        granted_by_name: Name of admin who granted credits
    """
    try:
        email_sent = email_service.send_credit_grant_notification_email(
            to_email=to_email,
            org_name=org_name,
            credit_amount=credit_amount,
            expires_at=expires_at_formatted,
            granted_by_name=granted_by_name,
        )

        if email_sent:
            logger.info(f"Credit grant notification email sent to {to_email}")
        else:
            logger.warning(f"Failed to send credit grant notification email to {to_email}")
    except Exception as e:
        logger.error(f"Error sending credit grant notification email to {to_email}: {e}")


def dispatch_credit_allocation_email(
    to_email: str,
    tenant_name: str,
    credit_amount: float,
    expires_at_formatted: str,
    allocator_name: str,
    org_name: str,
) -> None:
    """
    Background task to send credit allocation notification email.

    Called via BackgroundTasks.add_task() - runs after response is returned.

    Args:
        to_email: Recipient email address
        tenant_name: Name of tenant receiving credits
        credit_amount: Number of credits allocated
        expires_at_formatted: Human-readable expiry date
        allocator_name: Name of user who allocated credits
        org_name: Organization name
    """
    try:
        email_sent = email_service.send_credit_grant_notification_email(
            to_email=to_email,
            org_name=tenant_name,
            credit_amount=int(credit_amount),
            expires_at=expires_at_formatted,
            granted_by_name=f"{allocator_name} ({org_name})",
        )

        if email_sent:
            logger.info(f"Credit allocation notification email sent to {to_email}")
        else:
            logger.warning(f"Failed to send credit allocation notification email to {to_email}")
    except Exception as e:
        logger.error(f"Error sending credit allocation notification email to {to_email}: {e}")
