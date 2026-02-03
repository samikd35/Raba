"""
Waitlist Service for managing waitlist operations.

This service handles:
- Adding emails to the waitlist
- Checking waitlist status
- Applying bonus credits when waitlist users sign up
- Admin operations (stats, listing entries)
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from ..system.core.supabase_client import get_supabase_client
from ..services.communication.email_service import email_service

logger = logging.getLogger(__name__)


class WaitlistService:
    """Service for managing waitlist operations."""

    # Configuration
    WAITLIST_BONUS_CREDITS = 70  # Bonus credits for waitlist users
    WAITLIST_BONUS_EXPIRY_DAYS = 60  # Bonus credits expire in 60 days
    WAITLIST_MAX_ENTRIES = 1000  # Maximum number of waitlist entries allowed

    def __init__(self, use_service_role: bool = True):
        self.supabase = get_supabase_client(use_service_role=use_service_role).client

    def add_to_waitlist(
        self,
        email: str,
        source: str = "website",
        referral_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add email to waitlist.

        Args:
            email: User's email address
            source: Where they signed up (website, landing_page, referral)
            referral_code: Optional referral tracking code
            ip_address: Client IP for fraud prevention
            user_agent: Browser info
            metadata: Additional flexible data

        Returns:
            Dict with success status, message, position, and already_registered flag
        """
        email = email.lower().strip()

        # Check if already on waitlist
        existing = self._get_by_email(email)
        if existing:
            return {
                "success": True,
                "message": "You're already on our waitlist!",
                "already_registered": True,
                "position": self._get_position(existing["id"]),
            }

        # Check if already a registered user
        user_check = (
            self.supabase.table("user_profiles")
            .select("id")
            .eq("email", email)
            .execute()
        )
        if user_check.data:
            return {
                "success": False,
                "message": "This email is already registered. Please sign in instead.",
                "already_registered": True,
                "position": None,
            }

        # Check waitlist capacity (only count pending entries)
        current_count = self._get_pending_count()
        if current_count >= self.WAITLIST_MAX_ENTRIES:
            logger.warning(f"Waitlist is full ({current_count}/{self.WAITLIST_MAX_ENTRIES})")
            return {
                "success": False,
                "message": "Our waitlist is currently full. Please check back later.",
                "already_registered": False,
                "position": None,
            }

        # Add to waitlist
        payload = {
            "email": email,
            "status": "pending",
            "source": source,
            "referral_code": referral_code,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.supabase.table("waitlist_entries").insert(payload).execute()

        if result.data:
            entry = result.data[0]
            position = self._get_position(entry["id"])
            logger.info(f"Added {email} to waitlist (position: {position})")
            
            # Send waitlist confirmation email
            try:
                email_sent = email_service.send_waitlist_confirmation_email(
                    to_email=email,
                )
                if email_sent:
                    logger.info(f"Waitlist confirmation email sent to {email}")
                else:
                    logger.warning(f"Failed to send waitlist confirmation email to {email}")
            except Exception as e:
                # Don't fail the waitlist signup if email fails
                logger.error(f"Error sending waitlist confirmation email to {email}: {e}")
            
            return {
                "success": True,
                "message": "You've been added to our waitlist! We'll notify you when it's your turn.",
                "already_registered": False,
                "position": position,
            }

        raise Exception("Failed to add to waitlist")

    def _get_pending_count(self) -> int:
        """Get count of pending waitlist entries."""
        result = (
            self.supabase.table("waitlist_entries")
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        return result.count or 0

    def _get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get waitlist entry by email."""
        result = (
            self.supabase.table("waitlist_entries")
            .select("*")
            .eq("email", email.lower().strip())
            .execute()
        )
        return result.data[0] if result.data else None

    def _get_position(self, entry_id: str) -> int:
        """Get position in waitlist queue (count of pending entries before this one)."""
        # Get the entry's created_at
        entry = (
            self.supabase.table("waitlist_entries")
            .select("created_at")
            .eq("id", entry_id)
            .execute()
        )

        if not entry.data:
            return 1

        created_at = entry.data[0]["created_at"]

        # Count entries created before this one that are still pending
        result = (
            self.supabase.table("waitlist_entries")
            .select("id", count="exact")
            .eq("status", "pending")
            .lte("created_at", created_at)
            .execute()
        )

        return result.count or 1

    def check_waitlist_status(self, email: str) -> Dict[str, Any]:
        """
        Check if email is on waitlist.

        Args:
            email: Email to check

        Returns:
            Dict with on_waitlist, status, and position
        """
        entry = self._get_by_email(email)
        if entry:
            return {
                "on_waitlist": True,
                "status": entry["status"],
                "position": (
                    self._get_position(entry["id"])
                    if entry["status"] == "pending"
                    else None
                ),
            }
        return {"on_waitlist": False, "status": None, "position": None}

    def check_and_apply_waitlist_bonus(
        self,
        email: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if email was on waitlist and apply bonus credits.
        Called during signup completion.

        Args:
            email: User's email
            tenant_id: The tenant ID to grant credits to
            user_id: The user ID being created

        Returns:
            Bonus credit info if applied, None otherwise
        """
        # Import here to avoid circular imports
        from ..credit.service import CreditService

        email = email.lower().strip()
        logger.info(f"🎁 WAITLIST BONUS: Checking if {email} is on waitlist...")

        try:
            entry = self._get_by_email(email)
            if not entry:
                logger.info(f"🎁 WAITLIST BONUS: Email {email} not found in waitlist - no bonus")
                return None

            logger.info(f"🎁 WAITLIST BONUS: Found entry for {email} with status '{entry['status']}'")

            if entry["status"] == "converted":
                logger.warning(f"🎁 WAITLIST BONUS: Entry for {email} already converted - skipping")
                return None

            # Apply bonus credits
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=self.WAITLIST_BONUS_EXPIRY_DAYS)

            logger.info(f"🎁 WAITLIST BONUS: Creating {self.WAITLIST_BONUS_CREDITS} bonus credits for {email}...")

            credit_service = CreditService(use_service_role=True)
            # Use "grant" as source (valid enum value) and mark as waitlist_bonus in metadata
            # This avoids needing to modify the credit_lots source enum
            credit_service.create_credit_lot(
                tenant_id=tenant_id,
                original_tenant_id=tenant_id,
                source="grant",  # Use existing valid enum value
                credit_amount=Decimal(str(self.WAITLIST_BONUS_CREDITS)),
                valid_from=now.isoformat(),
                expires_at=expires_at.isoformat(),
                metadata={
                    "reason": "waitlist_bonus",  # This identifies it as waitlist bonus
                    "credit_type": "waitlist_bonus",  # Additional marker
                    "waitlist_entry_id": entry["id"],
                    "waitlist_joined_at": entry["created_at"],
                    "signup_source": entry.get("source", "website"),
                    "referral_code": entry.get("referral_code"),
                },
            )

            logger.info(f"🎁 WAITLIST BONUS: Credit lot created successfully for {email}")

            # Mark entry as converted
            self.supabase.table("waitlist_entries").update(
                {
                    "status": "converted",
                    "converted_at": now.isoformat(),
                    "converted_user_id": user_id,
                    "updated_at": now.isoformat(),
                }
            ).eq("id", entry["id"]).execute()

            logger.info(
                f"✅ WAITLIST BONUS: Applied {self.WAITLIST_BONUS_CREDITS} credits to {email} (expires: {expires_at.date()})"
            )

            return {
                "bonus_applied": True,
                "bonus_credits": self.WAITLIST_BONUS_CREDITS,
                "expires_at": expires_at.isoformat(),
                "waitlist_joined_at": entry["created_at"],
            }
            
        except Exception as e:
            # Log the specific error for debugging
            logger.error(
                f"❌ WAITLIST BONUS FAILED for {email}: {type(e).__name__}: {str(e)}"
            )
            logger.exception("Full traceback for waitlist bonus failure:")
            # Re-raise so calling code can handle it appropriately
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get waitlist statistics (admin only)."""
        all_entries = (
            self.supabase.table("waitlist_entries").select("status").execute()
        )

        stats = {
            "total_entries": len(all_entries.data or []),
            "pending": 0,
            "invited": 0,
            "converted": 0,
            "unsubscribed": 0,
            "max_capacity": self.WAITLIST_MAX_ENTRIES,
        }

        for entry in all_entries.data or []:
            status = entry.get("status", "pending")
            if status in stats:
                stats[status] += 1

        stats["conversion_rate"] = (
            round((stats["converted"] / stats["total_entries"] * 100), 2)
            if stats["total_entries"] > 0
            else 0.0
        )

        return stats

    def list_entries(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List waitlist entries (admin only)."""
        query = self.supabase.table("waitlist_entries").select("*")

        if status:
            query = query.eq("status", status)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return result.data or []


    def send_batch_signup_invitations(
        self,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send signup invitation emails to all pending waitlist users.
        Only sends to users who have status='pending' (not yet invited or converted).
        
        Args:
            batch_size: Optional limit on how many emails to send (None = all pending)
            
        Returns:
            Dict with sent_count, failed_count, failed_emails, and skipped_count
        """
        import os
        from src.mint.utils.url_safe_serializer import serializer
        from ..services.communication.email_service import email_service
        
        # Get all pending waitlist entries
        query = (
            self.supabase.table("waitlist_entries")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)  # Oldest first (FIFO)
        )
        
        if batch_size:
            query = query.limit(batch_size)
        
        result = query.execute()
        pending_entries = result.data or []
        
        if not pending_entries:
            return {
                "sent_count": 0,
                "failed_count": 0,
                "failed_emails": [],
                "skipped_count": 0,
                "message": "No pending waitlist entries to invite.",
            }
        
        frontend_url = os.getenv("FRONTEND_URL", "")
        sent_count = 0
        failed_count = 0
        failed_emails = []
        now = datetime.now(timezone.utc)
        
        for entry in pending_entries:
            email = entry["email"]
            entry_id = entry["id"]
            
            try:
                # Generate signup token for this email
                token = serializer.dumps({"email": email, "waitlist_id": entry_id})
                signup_link = f"{frontend_url}/signup-verify?token={token}"
                
                # Send the invitation email
                email_sent = self._send_waitlist_invitation_email(
                    email_service=email_service,
                    to_email=email,
                    signup_link=signup_link,
                )
                
                if email_sent:
                    # Update status to 'invited'
                    self.supabase.table("waitlist_entries").update(
                        {
                            "status": "invited",
                            "invited_at": now.isoformat(),
                            "updated_at": now.isoformat(),
                        }
                    ).eq("id", entry_id).execute()
                    
                    sent_count += 1
                    logger.info(f"Sent waitlist invitation to {email}")
                else:
                    failed_count += 1
                    failed_emails.append(email)
                    logger.error(f"Failed to send waitlist invitation to {email}")
                    
            except Exception as e:
                failed_count += 1
                failed_emails.append(email)
                logger.exception(f"Error sending waitlist invitation to {email}: {e}")
        
        return {
            "sent_count": sent_count,
            "failed_count": failed_count,
            "failed_emails": failed_emails,
            "total_pending": len(pending_entries),
            "message": f"Sent {sent_count} invitations, {failed_count} failed.",
        }

    def _send_waitlist_invitation_email(
        self,
        email_service,
        to_email: str,
        signup_link: str,
    ) -> bool:
        """
        Send waitlist invitation email to a single user.
        
        Args:
            email_service: The email service instance
            to_email: Recipient email address
            signup_link: The signup verification link
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        subject = "You're Invited to Join Yuba! 🎉"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>You're Invited to Join Yuba!</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header with gradient -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #128AA3, #244694); padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 42px; font-weight: 700; letter-spacing: 1px;">Yuba</h1>
                        </td>
                    </tr>

                    <!-- Main content -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px;">
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello,</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Great news! <strong>You're off the waitlist!</strong> 🎉</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Thank you for your patience. We're excited to invite you to create your Yuba account.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">As a thank you for waiting, you'll receive <strong style="color: #128AA3;">100 bonus credits</strong> when you sign up — on top of your free trial credits!</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{signup_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Complete Your Signup</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This link expires in 1 hour.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got questions? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

                            <p style="margin: 20px 0 0 0; color: #333333; font-size: 16px; line-height: 1.6;">Best,<br>The Yuba Team</p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px 30px 40px; text-align: center; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; color: #999999; font-size: 14px;">© Yuba Labs Ltd</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        text_content = f"""You're Invited to Join Yuba! 🎉

Hello,

Great news! You're off the waitlist!

Thank you for your patience. We're excited to invite you to create your Yuba account.

As a thank you for waiting, you'll receive 100 bonus credits when you sign up — on top of your free trial credits!

Complete your signup here:
{signup_link}

This link expires in 1 hour.

Got questions? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


# Singleton instance for convenience
waitlist_service = WaitlistService()
