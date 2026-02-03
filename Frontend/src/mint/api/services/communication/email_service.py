"""
Email Service for sending authentication-related emails.

This module provides functionality for sending emails for authentication
purposes such as account verification, password reset, etc.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending authentication-related emails."""

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        smtp_username: str = None,
        smtp_password: str = None,
        email_from: str = None,
        default_from_email: str = None,
    ):
        """
        Initialize the Email Service.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            smtp_username: SMTP username
            smtp_password: SMTP password
            email_from: Email address to send from
            default_from_email: Default display name for from address
        """
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER")
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT", 587))
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.email_from = email_from or os.getenv("EMAIL_FROM")
        self.default_from_email = default_from_email or os.getenv(
            "DEFAULT_FROM_EMAIL", "noreply@example.com"
        )

        # Validate required settings
        if not all(
            [
                self.smtp_server,
                self.smtp_port,
                self.smtp_username,
                self.smtp_password,
                self.email_from,
            ]
        ):
            logger.warning(
                "Email service not fully configured. Some settings are missing."
            )

    def is_configured(self) -> bool:
        """
        Check if the email service is properly configured.

        Returns:
            bool: True if all required settings are provided, False otherwise
        """
        return all(
            [
                self.smtp_server,
                self.smtp_port,
                self.smtp_username,
                self.smtp_password,
                self.email_from,
            ]
        )

    def send_invite_email(self, to_email: str, org_name: str, invite_link: str, org_email: Optional[str] = None) -> bool:
        """
        Send an organization invite email.

        Args:
            to_email: Recipient email address
            org_name: Name of the organization
            invite_link: Invitation link
            org_email: Organization contact email (optional)
        """
        subject = f"You're invited to join {org_name}"

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a90e2; color: white; padding: 10px 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ display: inline-block; background-color: #4a90e2; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>You're Invited!</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You've been invited to join <strong>{org_name}</strong> on our platform.</p>
                    <p>You have <strong>48 hours</strong> to accept this invitation.</p>
                    <p style="text-align: center;">
                        <a href="{invite_link}" class="button">Join Now</a>
                    </p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        You're invited to join {org_name}!

        Please use the link below to join:

        {invite_link}
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,  # ✅ CRITICAL: Include plain text to avoid spam
            reply_to=org_email,  # Allow replies to organization
        )

    def send_independent_team_invite_email(self, to_email: str, team_name: str, invite_link: str) -> bool:
        """
        Send an independent team invite email (team without organization).

        Args:
            to_email: Recipient email address
            team_name: Name of the team
            invite_link: Invitation link
        """
        subject = f"Join the {team_name} team on Yuba"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Join the {team_name} team on Yuba</title>
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

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">You've been invited to join the <strong>Team {team_name}</strong> on Yuba.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Click <strong>Join Now</strong> to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{invite_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Join Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This invitation expires within 48hrs.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got a question or need further help? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Join the {team_name} team on Yuba

Hello,

You've been invited to join the Team {team_name} on Yuba.

Click the link below to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user:

{invite_link}

This invitation expires within 48hrs.

Got a question or need further help? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_org_individual_member_invite_email(self, to_email: str, org_name: str, credit_amount: int, invite_link: str) -> bool:
        """
        Send an organization individual member invite email (is_team_leader = false).

        Args:
            to_email: Recipient email address
            org_name: Name of the organization
            credit_amount: Amount of credits allocated
            invite_link: Invitation link
        """
        subject = f"Invitation to Join {org_name} on Yuba"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Invitation to Join {org_name} on Yuba</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;"><strong>{org_name}</strong> has invited you to join their Workspace on Yuba.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Click <a href="{invite_link}" style="color: #128AA3; text-decoration: none;"><strong>Join Now</strong></a> to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{invite_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Join Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Upon accepting your invitation, please select the <strong>{org_name}</strong> workspace in which you have been allocated <strong>{credit_amount}</strong> for you to get started right away.</p>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This invitation expires within 48hrs.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you need assistance, reply to this message or contact us at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Invitation to Join {org_name} on Yuba

Hello,

{org_name} has invited you to join their Workspace on Yuba.

Upon accepting your invitation, you have been allocated {credit_amount} credits for you to get started right away.

Click the link below to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user:

{invite_link}

This invitation expires within 48hrs.

If you need assistance, reply to this message or contact us at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_org_team_leader_invite_email(self, to_email: str, org_name: str, credit_amount: int, invite_link: str) -> bool:
        """
        Send an organization team leader invite email (is_team_leader = true).

        Args:
            to_email: Recipient email address
            org_name: Name of the organization
            credit_amount: Amount of credits allocated
            invite_link: Invitation link
        """
        subject = "Invitation to Join Yuba as a Team Admin"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Invitation to Join Yuba as a Team Admin</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">You've been invited to join Yuba as a <strong>Team Admin</strong> within <strong>{org_name}</strong>'s Workspace.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Upon creating your Team, <strong>{credit_amount} credits</strong> have been allocated to your team so as to get started right away.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Click <strong>Create Now</strong> to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{invite_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Create Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Upon accepting your invitation, create your team, configure settings, and invite your teammate/s.</p>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This invitation expires within 48hrs.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got a question or need further help? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Invitation to Join Yuba as a Team Admin

Hello,

You've been invited to join Yuba as a Team Admin within {org_name}'s Workspace.

Upon creating your Team, {credit_amount} credits have been allocated to your team so as to get started right away.

Click the link below to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user:

{invite_link}

Upon accepting your invitation, create your team, configure settings, and invite your teammate/s.

This invitation expires within 48hrs.

Got a question or need further help? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_org_admin_creation_invite_email(self, to_email: str, invite_link: str) -> bool:
        """
        Send an organization admin creation invite email (app-level invitation).

        Args:
            to_email: Recipient email address
            invite_link: Invitation link
        """
        subject = "Invitation to join Yuba as Organization Admin"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Invitation to join Yuba as Organization Admin</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">You've been invited to join Yuba as an <strong>Organization Admin</strong>.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">As an Admin, you'll be able to:</p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li>Create your organization workspace on Yuba</li>
                                <li>Invite individual members and team admins</li>
                                <li>Assign and manage credits for your members</li>
                                <li>Oversee the organization's portfolio</li>
                            </ul>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Click <strong>Create Now</strong> to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{invite_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Create Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This invitation expires within 48hr.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you need any help while setting things up, you can contact us at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Invitation to join Yuba as Organization Admin

Hello,

You've been invited to join Yuba as an Organization Admin.

As an Admin, you'll be able to:
- Create your organization workspace on Yuba
- Invite individual members and team admins
- Assign and manage credits for your members
- Oversee the organization's portfolio

Click the link below to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user:

{invite_link}

This invitation expires within 48hr.

If you need any help while setting things up, you can contact us at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_waitlist_confirmation_email(self, to_email: str) -> bool:
        """
        Send a waitlist confirmation email when a user joins the waitlist.

        Args:
            to_email: Recipient email address
        """
        subject = "You're on Yuba's Waitlist!"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>You're on Yuba's Waitlist!</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Thanks for joining <strong>Yuba's Waitlist</strong>! We're excited to have you on board.</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">We're working hard to open access to everyone. You'll be among the first to know when we're ready for you!</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">What to expect:</p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li>We'll email you as soon as access opens</li>
                                <li>Waitlist members get <strong>bonus credits</strong> when signing up</li>
                                <li>Early access to new features and updates</li>
                            </ul>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">In the meantime, follow us on social media to stay updated on our progress.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got questions? Reach out to us at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = """You're on Yuba's Waitlist!

Hello,

Thanks for joining Yuba's Waitlist! We're excited to have you on board.

We're working hard to open access to everyone. You'll be among the first to know when we're ready for you!

What to expect:
- We'll email you as soon as access opens
- Waitlist members get bonus credits when signing up
- Early access to new features and updates

In the meantime, follow us on social media to stay updated on our progress.

Got questions? Reach out to us at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_vb_invite_email(self, to_email: str, invite_link: str) -> bool:
        """
        Send a Venture Builder invitation email.

        Args:
            to_email: Recipient email address
            invite_link: Invitation link
        """
        subject = "Invitation to Join Yuba as a Venture Builder"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Invitation to Join Yuba as a Venture Builder</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">You've been invited to join Yuba as a <strong>Venture Builder</strong>.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">As a Venture Builder, you'll be able to:</p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li>Share your expertise with entrepreneurs and innovators</li>
                                <li>Provide one-on-one coaching sessions</li>
                                <li>Access project portfolios and track progress</li>
                                <li>Earn credits for your valuable insights</li>
                            </ul>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Click <strong>Join Now</strong> to create your Yuba account if you're new, or sign in to accept your invitation if you are already a user.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{invite_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Join Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This invitation expires within 48 hours.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you need any help while setting things up, you can contact us at <a href="mailto:office@yubanow.com" style="color: #128AA3; text-decoration: none;">office@yubanow.com</a>.</p>

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

        text_content = f"""Invitation to Join Yuba as a Venture Builder

Hello,

You've been invited to join Yuba as a Venture Builder.

As a Venture Builder, you'll be able to:
- Share your expertise with entrepreneurs and innovators
- Provide one-on-one coaching sessions
- Access project portfolios and track progress
- Earn credits for your valuable insights

Click the link below to create your Yuba account if you're new, or sign in to accept your invitation if you are already a user:

{invite_link}

This invitation expires within 48 hours.

If you need any help while setting things up, you can contact us at office@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_vb_interest_rejection_email(
        self, to_email: str, applicant_name: str, admin_notes: Optional[str] = None
    ) -> bool:
        """
        Send a Venture Builder interest submission rejection email.

        Args:
            to_email: Applicant's email address
            applicant_name: Applicant's full name
            admin_notes: Optional feedback/notes from admin to include in email
        """
        subject = "Update on Your Venture Builder Application"

        # Build optional admin note section for HTML (simple paragraph style)
        admin_note_html = ""
        if admin_notes:
            admin_note_html = f"""
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">{admin_notes}</p>
"""

        # Build optional admin note section for plain text
        admin_note_text = ""
        if admin_notes:
            admin_note_text = f"""
{admin_notes}
"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Update on Your Venture Builder Application</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello {applicant_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Thank you for your interest in joining Yuba as a Venture Builder. We truly appreciate the time and effort you put into your application.</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">After careful review, we regret to inform you that we are unable to move forward with your application at this time. This decision was not easy, as we received many strong applications.</p>
{admin_note_html}
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">We encourage you to continue developing your expertise and consider reapplying in the future as our platform grows and evolves.</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you have any questions or would like feedback on your application, please don't hesitate to reach out to us at <a href="mailto:office@yubanow.com" style="color: #128AA3; text-decoration: none;">office@yubanow.com</a>.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">We wish you all the best in your future endeavors.</p>

                            <p style="margin: 20px 0 0 0; color: #333333; font-size: 16px; line-height: 1.6;">Warm regards,<br>The Yuba Team</p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px 30px 40px; text-align: center; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; color: #999999; font-size: 14px;">© Yuba Holdings INC</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        text_content = f"""Update on Your Venture Builder Application

Hello {applicant_name},

Thank you for your interest in joining Yuba as a Venture Builder. We truly appreciate the time and effort you put into your application.

After careful review, we regret to inform you that we are unable to move forward with your application at this time. This decision was not easy, as we received many strong applications.
{admin_note_text}
We encourage you to continue developing your expertise and consider reapplying in the future as our platform grows and evolves.

If you have any questions or would like feedback on your application, please don't hesitate to reach out to us at office@yubanow.com.

We wish you all the best in your future endeavors.

Warm regards,
The Yuba Team

© Yuba Holdings INC"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_vb_approval_email(
        self, to_email: str, vb_name: str, vb_id: str, credit_price_per_hour: int
    ) -> bool:
        """
        Send a Venture Builder profile approval notification email.

        Args:
            to_email: Venture Builder's contact email address
            vb_name: Venture Builder's name
            vb_id: Venture Builder's profile ID
            credit_price_per_hour: Credit rate set for the VB
        """
        subject = "Your Venture Builder Profile Has Been Approved!"

        # Build profile URL
        frontend_url = os.getenv("FRONTEND_URL", "")
        profile_url = f"{frontend_url}/venture-builder/{vb_id}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Your Venture Builder Profile Has Been Approved</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello {vb_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Congratulations! Your Venture Builder profile has been <strong>approved</strong> and is now live on Yuba.</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">You can now start accepting bookings from entrepreneurs and innovators who need your expertise.</p>

                            <!-- Pricing info box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 20px 0; background-color: #f8f9fa; border-radius: 6px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Your Rate</p>
                                        <p style="margin: 0; color: #128AA3; font-size: 24px; font-weight: 700;">{credit_price_per_hour} credits/hour</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">What's next:</p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li>Your profile is now visible to all Yuba users</li>
                                <li>Users can book sessions with you based on your availability</li>
                                <li>You'll receive email notifications for new bookings</li>
                                <li>Track your earnings through your VB dashboard</li>
                            </ul>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding: 20px 0;">
                                        <a href="{profile_url}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">View Your Profile</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 20px 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you have any questions or need assistance, feel free to contact us at <a href="mailto:office@yubanow.com" style="color: #128AA3; text-decoration: none;">office@yubanow.com</a>.</p>

                            <p style="margin: 20px 0 0 0; color: #333333; font-size: 16px; line-height: 1.6;">Welcome to the Yuba community!<br>The Yuba Team</p>
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

        text_content = f"""Your Venture Builder Profile Has Been Approved

Hello {vb_name},

Congratulations! Your Venture Builder profile has been approved and is now live on Yuba.

You can now start accepting bookings from entrepreneurs and innovators who need your expertise.

YOUR RATE
{credit_price_per_hour} credits/hour

What's next:
- Your profile is now visible to all Yuba users
- Users can book sessions with you based on your availability
- You'll receive email notifications for new bookings
- Track your earnings through your VB dashboard

View your profile: {profile_url}

If you have any questions or need assistance, feel free to contact us at office@yubanow.com.

Welcome to the Yuba community!
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_vb_booking_confirmation_to_user(
        self,
        to_email: str,
        user_name: str,
        vb_name: str,
        vb_email: str,
        session_datetime: str,
        project_name: str,
        credits_charged: int,
    ) -> bool:
        """
        Send booking confirmation email to the user who booked the session.

        Args:
            to_email: User's email address
            user_name: User's full name
            vb_name: Venture Builder's name
            vb_email: Venture Builder's email
            session_datetime: Session date and time
            project_name: Project name
            credits_charged: Credits charged for the session
        """
        subject = f"Venture Builder Session Confirmed - {vb_name}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Venture Builder Session Confirmed</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hi {user_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Your Venture Builder coaching session has been <strong>confirmed</strong>!</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;"><strong>Session Details:</strong></p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li><strong>Venture Builder:</strong> {vb_name}</li>
                                <li><strong>Contact:</strong> {vb_email}</li>
                                <li><strong>Date & Time:</strong> {session_datetime}</li>
                                <li><strong>Project:</strong> {project_name}</li>
                                <li><strong>Credits Charged:</strong> {credits_charged}</li>
                            </ul>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Your Venture Builder will reach out to you soon to coordinate the session logistics. Please check your calendar and be prepared to discuss your project goals.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you need any help, you can contact us at <a href="mailto:office@yubanow.com" style="color: #128AA3; text-decoration: none;">office@yubanow.com</a>.</p>

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

        text_content = f"""Venture Builder Session Confirmed

Hi {user_name},

Your Venture Builder coaching session has been confirmed!

Session Details:
- Venture Builder: {vb_name}
- Contact: {vb_email}
- Date & Time: {session_datetime}
- Project: {project_name}
- Credits Charged: {credits_charged}

Your Venture Builder will reach out to you soon to coordinate the session logistics. Please check your calendar and be prepared to discuss your project goals.

If you need any help, you can contact us at office@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_vb_booking_confirmation_to_vb(
        self,
        to_email: str,
        vb_name: str,
        user_name: str,
        user_email: str,
        session_datetime: str,
        project_name: str,
        credits_charged: int,
    ) -> bool:
        """
        Send booking notification email to the Venture Builder.

        Args:
            to_email: VB's email address
            vb_name: VB's name
            user_name: User's full name
            user_email: User's email
            session_datetime: Session date and time
            project_name: Project name
            credits_charged: Credits charged for the session
        """
        subject = f"New Coaching Session Booked - {user_name}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>New Coaching Session Booked</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hi {vb_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">You have a new coaching session booked on the Yuba platform!</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;"><strong>Session Details:</strong></p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li><strong>Client:</strong> {user_name}</li>
                                <li><strong>Contact:</strong> {user_email}</li>
                                <li><strong>Date & Time:</strong> {session_datetime}</li>
                                <li><strong>Project:</strong> {project_name}</li>
                                <li><strong>Credits Earned:</strong> {credits_charged}</li>
                            </ul>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Please reach out to {user_name} at the email above to coordinate meeting logistics and prepare for a productive coaching session.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you need any help, you can contact us at <a href="mailto:office@yubanow.com" style="color: #128AA3; text-decoration: none;">office@yubanow.com</a>.</p>

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

        text_content = f"""New Coaching Session Booked

Hi {vb_name},

You have a new coaching session booked on the Yuba platform!

Session Details:
- Client: {user_name}
- Contact: {user_email}
- Date & Time: {session_datetime}
- Project: {project_name}
- Credits Earned: {credits_charged}

Please reach out to {user_name} at the email above to coordinate meeting logistics and prepare for a productive coaching session.

If you need any help, you can contact us at office@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_org_team_invite_email(self, to_email: str, team_name: str, inviter_name: str, invite_link: str) -> bool:
        """
        Send an organization-associated team invite email.

        Args:
            to_email: Recipient email address
            team_name: Name of the team
            inviter_name: Name of the person inviting
            invite_link: Invitation link
        """
        subject = f"Invitation to Join Your Team ({team_name}) on Yuba"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Invitation to Join Your Team ({team_name}) on Yuba</title>
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

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;"><strong>{inviter_name}</strong> is inviting you to join <strong>{team_name}</strong>, your team, on Yuba.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Click <strong>Join Now</strong> to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{invite_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Join Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>This invitation expires within 48hrs.</em></p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got a question or need further help? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Invitation to Join Your Team ({team_name}) on Yuba

Hello,

{inviter_name} is inviting you to join {team_name}, your team, on Yuba.

Click the link below to create a Yuba account if you're new, or sign in to accept your invitation if you are already a user:

{invite_link}

This invitation expires within 48hrs.

Got a question or need further help? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_credit_grant_notification_email(
        self,
        to_email: str,
        org_name: str,
        credit_amount: int,
        expires_at: str,
        granted_by_name: str = "Yuba Admin"
    ) -> bool:
        """
        Send a notification email when credits are granted to an organization.

        Args:
            to_email: Organization contact email address
            org_name: Name of the organization
            credit_amount: Number of credits granted
            expires_at: Credit expiration date (formatted string)
            granted_by_name: Name of the admin who granted the credits
        """
        subject = f"🎉 {credit_amount:,} Credits Granted to {org_name}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Credits Granted to {org_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header with gradient -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #10B981, #059669); padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 42px; font-weight: 700; letter-spacing: 1px;">Yuba</h1>
                            <p style="margin: 10px 0 0 0; color: #ffffff; font-size: 18px;">Credits Granted! 🎉</p>
                        </td>
                    </tr>

                    <!-- Main content -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px;">
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello,</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Great news! <strong>{org_name}</strong> has been granted additional credits on Yuba.</p>

                            <!-- Credit Details Box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #10B981, #059669); border-radius: 12px; padding: 30px; text-align: center;">
                                        <p style="margin: 0 0 10px 0; color: #ffffff; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Credits Granted</p>
                                        <p style="margin: 0; color: #ffffff; font-size: 48px; font-weight: 700;">{credit_amount:,}</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Details -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 20px 0; background-color: #f9fafb; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Organization:</td>
                                                <td style="padding: 8px 0; color: #111827; font-size: 14px; font-weight: 600; text-align: right;">{org_name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #6b7280; font-size: 14px; border-top: 1px solid #e5e7eb;">Credits Expire:</td>
                                                <td style="padding: 8px 0; color: #111827; font-size: 14px; font-weight: 600; text-align: right; border-top: 1px solid #e5e7eb;">{expires_at}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #6b7280; font-size: 14px; border-top: 1px solid #e5e7eb;">Granted By:</td>
                                                <td style="padding: 8px 0; color: #111827; font-size: 14px; font-weight: 600; text-align: right; border-top: 1px solid #e5e7eb;">{granted_by_name}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">These credits are now available for your organization to use. You can allocate them to team members or use them for your organization's projects.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you have any questions, contact us at <a href="mailto:info@yubanow.com" style="color: #10B981; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Credits Granted to {org_name}

Hello,

Great news! {org_name} has been granted additional credits on Yuba.

CREDIT DETAILS
--------------
Credits Granted: {credit_amount:,}
Organization: {org_name}
Credits Expire: {expires_at}
Granted By: {granted_by_name}

These credits are now available for your organization to use. You can allocate them to team members or use them for your organization's projects.

If you have any questions, contact us at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content of the email (optional)
            from_email: Sender email address (optional, uses default if not provided)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Email service not properly configured. Cannot send email.")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or f"{self.default_from_email} <{self.email_from}>"
            msg["To"] = to_email
            
            # ✅ CRITICAL ANTI-SPAM HEADERS
            msg["Message-ID"] = make_msgid(domain=self.email_from.split("@")[-1])
            msg["X-Mailer"] = "Yuba Platform v1.0"
            
            # Add Reply-To if provided (improves deliverability)
            if reply_to:
                msg["Reply-To"] = reply_to
            
            # Add List-Unsubscribe header for transactional emails (RFC 8058)
            # This helps with Gmail's spam filtering
            unsubscribe_url = os.getenv("UNSUBSCRIBE_URL", "")
            if unsubscribe_url:
                msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
                msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

            if cc:
                msg["Cc"] = ", ".join(cc)
            if bcc:
                msg["Bcc"] = ", ".join(bcc)

            # Add text content if provided
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))

            # Add HTML content
            msg.attach(MIMEText(html_content, "html"))

            # Connect to SMTP server and send email
            if self.smtp_port == 465:
                # Use SSL for port 465 (GoDaddy, etc.)
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.set_debuglevel(1)
                    server.login(self.smtp_username, self.smtp_password)

                    recipients = [to_email]
                    if cc:
                        recipients.extend(cc)
                    if bcc:
                        recipients.extend(bcc)

                    server.sendmail(self.email_from, recipients, msg.as_string())
            else:
                # Use STARTTLS for port 587 (Gmail, Outlook, etc.)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.set_debuglevel(1)
                    server.login(self.smtp_username, self.smtp_password)

                    recipients = [to_email]
                    if cc:
                        recipients.extend(cc)
                    if bcc:
                        recipients.extend(bcc)

                    server.sendmail(self.email_from, recipients, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def send_verification_email(self, to_email: str, verification_link: str) -> bool:
        """
        Send an email verification link.

        Args:
            to_email: Recipient email address
            verification_link: Link for email verification

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        subject = "Verify Your Email Address"

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a90e2; color: white; padding: 10px 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ display: inline-block; background-color: #4a90e2; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Verify Your Email Address</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email</a>
                    </p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                    <p>This link will expire in 24 hours.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Verify Your Email Address

        Hello,

        Thank you for signing up! Please verify your email address by clicking the link below:

        {verification_link}

        If you didn't create an account, you can safely ignore this email.

        This link will expire in 24 hours.

        This is an automated message, please do not reply to this email.
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_password_reset_email(self, to_email: str, reset_link: str) -> bool:
        """
        Send a password reset link.

        Args:
            to_email: Recipient email address
            reset_link: Link for password reset

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        subject = "Reset Your Password"

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a90e2; color: white; padding: 10px 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ display: inline-block; background-color: #4a90e2; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reset Your Password</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>If you didn't request a password reset, you can safely ignore this email.</p>
                    <p>This link will expire in 1 hour.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Reset Your Password

        Hello,

        We received a request to reset your password. Click the link below to create a new password:

        {reset_link}

        If you didn't request a password reset, you can safely ignore this email.

        This link will expire in 1 hour.

        This is an automated message, please do not reply to this email.
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_account_locked_notification(
        self, to_email: str, support_email: str = None
    ) -> bool:
        """
        Send a notification when an account is locked due to too many failed login attempts.

        Args:
            to_email: Recipient email address
            support_email: Support email address (optional)

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        subject = "Account Security Alert"

        support_contact = (
            f"Please contact {support_email}"
            if support_email
            else "Please contact support"
        )

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #e24a4a; color: white; padding: 10px 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Account Security Alert</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We've detected multiple failed login attempts on your account, and for security reasons, your account has been temporarily locked.</p>
                    <p>If this was you, you can reset your password using the "Forgot Password" option on the login page.</p>
                    <p>If you didn't attempt to log in, someone else might be trying to access your account. {support_contact} for assistance.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Account Security Alert

        Hello,

        We've detected multiple failed login attempts on your account, and for security reasons, your account has been temporarily locked.

        If this was you, you can reset your password using the "Forgot Password" option on the login page.

        If you didn't attempt to log in, someone else might be trying to access your account. {support_contact} for assistance.

        This is an automated message, please do not reply to this email.
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_security_alert_email(
        self, to_email: str, alert_type: str, details: Dict
    ) -> bool:
        """
        Send a security alert email.

        Args:
            to_email: Recipient email address
            alert_type: Type of security alert (e.g., "new_login", "password_changed")
            details: Additional details about the alert

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if alert_type == "new_login":
            subject = "New Login Detected"

            device = details.get("device", "Unknown device")
            location = details.get("location", "Unknown location")
            time = details.get("time", "Unknown time")
            ip_address = details.get("ip_address", "Unknown IP address")

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f39c12; color: white; padding: 10px 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .details {{ background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>New Login Detected</h1>
                    </div>
                    <div class="content">
                        <p>Hello,</p>
                        <p>We detected a new login to your account. If this was you, you can ignore this email.</p>
                        <div class="details">
                            <p><strong>Device:</strong> {device}</p>
                            <p><strong>Location:</strong> {location}</p>
                            <p><strong>Time:</strong> {time}</p>
                            <p><strong>IP Address:</strong> {ip_address}</p>
                        </div>
                        <p>If this wasn't you, please change your password immediately and contact support.</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            New Login Detected

            Hello,

            We detected a new login to your account. If this was you, you can ignore this email.

            Details:
            - Device: {device}
            - Location: {location}
            - Time: {time}
            - IP Address: {ip_address}

            If this wasn't you, please change your password immediately and contact support.

            This is an automated message, please do not reply to this email.
            """

        elif alert_type == "password_changed":
            subject = "Your Password Has Been Changed"

            time = details.get("time", "Unknown time")

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4a90e2; color: white; padding: 10px 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Changed</h1>
                    </div>
                    <div class="content">
                        <p>Hello,</p>
                        <p>Your password was changed on {time}.</p>
                        <p>If you made this change, you can ignore this email.</p>
                        <p>If you didn't change your password, please contact support immediately as your account may have been compromised.</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Password Changed

            Hello,

            Your password was changed on {time}.

            If you made this change, you can ignore this email.

            If you didn't change your password, please contact support immediately as your account may have been compromised.

            This is an automated message, please do not reply to this email.
            """

        else:
            logger.error(f"Unknown security alert type: {alert_type}")
            return False

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


    def send_cofounder_matches_email(
        self,
        to_email: str,
        user_name: str,
        match_count: int,
        matched_names: list,
        matches_url: str
    ) -> bool:
        """
        Send email to newly approved user with their matches.

        Args:
            to_email: User's email address
            user_name: User's first name
            match_count: Number of matches found
            matched_names: List of matched user names (max 5 for email)
            matches_url: URL to view all matches on frontend
        """
        subject = f"You have {match_count} Cofounder Match{'es' if match_count != 1 else ''}!"

        # Format matched names list
        names_list_html = "".join([f"<li style='margin: 8px 0; color: #333333; font-size: 15px;'>{name}</li>" for name in matched_names[:5]])
        names_list_text = "\n".join([f"- {name}" for name in matched_names[:5]])

        more_text = f" and {match_count - 5} more" if match_count > 5 else ""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>You have {match_count} Cofounder Match{'es' if match_count != 1 else ''}!</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello {user_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Great news! Your cofounder profile has been approved and we've found <strong>{match_count} potential cofounder match{'es' if match_count != 1 else ''}</strong> for you:</p>

                            <ul style="margin: 0 0 30px 0; padding-left: 20px; list-style-type: disc;">
                                {names_list_html}
                            </ul>

                            {f'<p style="margin: 0 0 30px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>{more_text}</em></p>' if match_count > 5 else ''}

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{matches_url}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">View All Matches</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got a question or need further help? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""You have {match_count} Cofounder Match{'es' if match_count != 1 else ''}!

Hello {user_name},

Great news! Your cofounder profile has been approved and we've found {match_count} potential cofounder match{'es' if match_count != 1 else ''} for you:

{names_list_text}
{more_text}

Click the link below to view all your matches:

{matches_url}

Got a question or need further help? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_new_cofounder_match_email(
        self,
        to_email: str,
        user_name: str,
        matched_user_name: str,
        matches_url: str
    ) -> bool:
        """
        Send email to existing user notifying them of a new match.

        Args:
            to_email: User's email address
            user_name: User's first name
            matched_user_name: Name of the newly matched user
            matches_url: URL to view matches on frontend
        """
        subject = f"New Cofounder Match: {matched_user_name}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>New Cofounder Match: {matched_user_name}</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello {user_name},</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">You have a new cofounder match: <strong>{matched_user_name}</strong>!</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{matches_url}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">View Match</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got a question or need further help? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""New Cofounder Match: {matched_user_name}

Hello {user_name},

You have a new cofounder match: {matched_user_name}!

Click the link below to view your match:

{matches_url}

Got a question or need further help? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_cofounder_profile_approved_email(
        self,
        to_email: str,
        user_name: str,
        matches_url: str
    ) -> bool:
        """
        Send email to user confirming their cofounder profile has been approved.

        Args:
            to_email: User's email address
            user_name: User's first name
            matches_url: URL to view matches on frontend
        """
        subject = "Your Cofounder Profile Has Been Approved!"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Your Cofounder Profile Has Been Approved!</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello {user_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Great news! Your cofounder profile has been <strong>approved</strong>.</p>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">We're now actively matching you with potential cofounders. You'll receive email notifications when new matches are found.</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{matches_url}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">View Your Matches</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">Got a question or need further help? We're here to help at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Your Cofounder Profile Has Been Approved!

Hello {user_name},

Great news! Your cofounder profile has been approved.

We're now actively matching you with potential cofounders. You'll receive email notifications when new matches are found.

Click the link below to view your matches:

{matches_url}

Got a question or need further help? We're here to help at info@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_cofounder_profile_rejected_email(
        self,
        to_email: str,
        user_name: str,
        rejection_reason: str
    ) -> bool:
        """
        Send email to user notifying them their cofounder profile has been rejected.

        Args:
            to_email: User's email address
            user_name: User's first name
            rejection_reason: Reason for rejection provided by admin
        """
        subject = "Your Cofounder Profile Needs Revision"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Your Cofounder Profile Needs Revision</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hello {user_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Thank you for submitting your cofounder profile. Unfortunately, we need you to make some revisions before we can approve it.</p>

                            <div style="background-color: #f8f9fa; border-left: 4px solid #244694; padding: 16px; margin: 0 0 30px 0; border-radius: 4px;">
                                <p style="margin: 0 0 8px 0; color: #244694; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Reason for Revision:</p>
                                <p style="margin: 0; color: #333333; font-size: 15px; line-height: 1.6;">{rejection_reason}</p>
                            </div>

                            <p style="margin: 0 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Please update your profile and resubmit it for review. We're here to help you find the perfect cofounder match!</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you have any questions about the feedback, please reach out to us at <a href="mailto:info@yubanow.com" style="color: #128AA3; text-decoration: none;">info@yubanow.com</a>.</p>

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

        text_content = f"""Your Cofounder Profile Needs Revision

Hello {user_name},

Thank you for submitting your cofounder profile. Unfortunately, we need you to make some revisions before we can approve it.

REASON FOR REVISION:
{rejection_reason}

Please update your profile and resubmit it for review. We're here to help you find the perfect cofounder match!

If you have any questions about the feedback, please reach out to us at office@yubanow.com.

Best,
The Yuba Team

© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_vb_cancellation_email_to_user(
        self,
        to_email: str,
        user_name: str,
        vb_name: str,
        session_datetime: str,
        project_name: str,
        cancellation_reason: str,
        credits_refunded: int,
        booking_link: str,
    ) -> bool:
        """
        Send cancellation notification email to the user when VB cancels a session.

        Args:
            to_email: User's email address
            user_name: User's full name
            vb_name: Venture Builder's name
            session_datetime: Session date and time that was cancelled
            project_name: Project name
            cancellation_reason: VB's reason for cancelling
            credits_refunded: Credits refunded to the user
            booking_link: Link to book another session
        """
        subject = f"Session Cancelled - {vb_name}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Venture Builder Session Cancelled</title>
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
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Hi {user_name},</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">We're sorry to inform you that your Venture Builder session has been <strong>cancelled</strong> by {vb_name}.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;"><strong>Cancelled Session Details:</strong></p>

                            <ul style="margin: 0 0 20px 0; padding-left: 20px; color: #333333; font-size: 16px; line-height: 1.8;">
                                <li><strong>Venture Builder:</strong> {vb_name}</li>
                                <li><strong>Scheduled Time:</strong> {session_datetime}</li>
                                <li><strong>Project:</strong> {project_name}</li>
                                <li><strong>Credits Refunded:</strong> {credits_refunded}</li>
                            </ul>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;"><strong>Reason for Cancellation:</strong></p>
                            <p style="margin: 0 0 20px 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #128AA3; color: #333333; font-size: 16px; line-height: 1.6; font-style: italic;">"{cancellation_reason}"</p>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Your {credits_refunded} credits have been fully refunded to your account. We apologize for any inconvenience this may have caused.</p>

                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{booking_link}" style="display: inline-block; padding: 14px 32px; background-color: #128AA3; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Book Another Session</a>
                            </div>

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">We'd love to help you find another Venture Builder who can support your project. Browse our available experts and schedule a new session at your convenience.</p>

                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">If you have any questions or need assistance, please contact us at <a href="mailto:office@yubanow.com" style="color: #128AA3; text-decoration: none;">office@yubanow.com</a>.</p>

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

        text_content = f"""Venture Builder Session Cancelled

Hi {user_name},

We're sorry to inform you that your Venture Builder session has been cancelled by {vb_name}.

Cancelled Session Details:
- Venture Builder: {vb_name}
- Scheduled Time: {session_datetime}
- Project: {project_name}
- Credits Refunded: {credits_refunded}

Reason for Cancellation:
"{cancellation_reason}"

Your {credits_refunded} credits have been fully refunded to your account. We apologize for any inconvenience this may have caused.

Book Another Session:
{booking_link}

We'd love to help you find another Venture Builder who can support your project. Browse our available experts and schedule a new session at your convenience.

If you have any questions or need assistance, please contact us at office@yubanow.com.

Best,
The Yuba Team

---
© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_invoice_email(
        self,
        to_email: str,
        org_name: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: str,
        payment_link: str
    ) -> bool:
        """
        Send a new invoice notification email with payment link.

        Args:
            to_email: Recipient email address
            org_name: Name of the organization
            invoice_number: Invoice number (e.g., INV-202501-000001)
            invoice_amount: Total invoice amount in USD
            due_date: Invoice due date (formatted string)
            payment_link: Stripe hosted invoice URL for payment
        """
        subject = f"New Invoice {invoice_number} from Yuba"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>New Invoice {invoice_number}</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">A new invoice has been generated for <strong>{org_name}</strong>.</p>

                            <!-- Invoice Details Box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8f9fa; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Invoice Number:</strong></p>
                                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; font-weight: 600;">{invoice_number}</p>

                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Amount Due:</strong></p>
                                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 24px; font-weight: 700;">${invoice_amount:,.2f} USD</p>

                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Due Date:</strong></p>
                                        <p style="margin: 0; color: #333333; font-size: 16px; font-weight: 600;">{due_date}</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 20px 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">Please review and pay your invoice by clicking the button below:</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{payment_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">View & Pay Invoice</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;">If you have any questions about this invoice, please contact us at <a href="mailto:billing@yubanow.com" style="color: #128AA3; text-decoration: none;">billing@yubanow.com</a>.</p>

                            <p style="margin: 20px 0 0 0; color: #333333; font-size: 16px; line-height: 1.6;">Best regards,<br>The Yuba Team</p>
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

        text_content = f"""New Invoice {invoice_number} from Yuba

Hello,

A new invoice has been generated for {org_name}.

Invoice Details:
-----------------
Invoice Number: {invoice_number}
Amount Due: ${invoice_amount:,.2f} USD
Due Date: {due_date}

Please review and pay your invoice by visiting:
{payment_link}

If you have any questions about this invoice, please contact us at billing@yubanow.com.

Best regards,
The Yuba Team

---
© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_invoice_reminder_email(
        self,
        to_email: str,
        org_name: str,
        invoice_number: str,
        invoice_amount: float,
        due_date: str,
        payment_link: str
    ) -> bool:
        """
        Send an invoice reminder email (typically 3 days before due date).

        Args:
            to_email: Recipient email address
            org_name: Name of the organization
            invoice_number: Invoice number (e.g., INV-202501-000001)
            invoice_amount: Total invoice amount in USD
            due_date: Invoice due date (formatted string)
            payment_link: Stripe hosted invoice URL for payment
        """
        subject = f"Reminder: Invoice {invoice_number} Due Soon"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Invoice Reminder - {invoice_number}</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">This is a friendly reminder that invoice <strong>{invoice_number}</strong> for <strong>{org_name}</strong> is due soon.</p>

                            <!-- Invoice Details Box with warning color -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #fff8e6; border-left: 4px solid #ffa726; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Invoice Number:</strong></p>
                                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; font-weight: 600;">{invoice_number}</p>

                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Amount Due:</strong></p>
                                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 24px; font-weight: 700;">${invoice_amount:,.2f} USD</p>

                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Due Date:</strong></p>
                                        <p style="margin: 0; color: #d84315; font-size: 16px; font-weight: 600;">{due_date}</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 20px 0 30px 0; color: #333333; font-size: 16px; line-height: 1.6;">To avoid any service interruption, please pay your invoice before the due date:</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{payment_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Pay Invoice Now</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;">If you have already paid this invoice, please disregard this reminder. If you have any questions, please contact us at <a href="mailto:billing@yubanow.com" style="color: #128AA3; text-decoration: none;">billing@yubanow.com</a>.</p>

                            <p style="margin: 20px 0 0 0; color: #333333; font-size: 16px; line-height: 1.6;">Best regards,<br>The Yuba Team</p>
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

        text_content = f"""Reminder: Invoice {invoice_number} Due Soon

Hello,

This is a friendly reminder that invoice {invoice_number} for {org_name} is due soon.

Invoice Details:
-----------------
Invoice Number: {invoice_number}
Amount Due: ${invoice_amount:,.2f} USD
Due Date: {due_date}

To avoid any service interruption, please pay your invoice before the due date by visiting:
{payment_link}

If you have already paid this invoice, please disregard this reminder. If you have any questions, please contact us at billing@yubanow.com.

Best regards,
The Yuba Team

---
© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_low_credit_warning_email(
        self,
        to_email: str,
        org_name: str,
        current_balance: int,
        required_credits: int,
        admin_seats_count: int,
        purchase_link: str
    ) -> bool:
        """
        Send a low credit warning email when insufficient credits for admin seat billing.

        Args:
            to_email: Recipient email address
            org_name: Name of the organization
            current_balance: Current credit balance
            required_credits: Credits required for admin seat billing
            admin_seats_count: Number of admin seats
            purchase_link: Link to purchase more credits
        """
        subject = f"Low Credit Balance Alert - {org_name}"
        deficit = required_credits - current_balance

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Low Credit Balance Alert</title>
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

                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">Your organization <strong>{org_name}</strong> has insufficient credits to cover the monthly admin seat billing charges.</p>

                            <!-- Alert Box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #fff3e0; border-left: 4px solid #ff6f00; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Current Credit Balance:</strong></p>
                                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 20px; font-weight: 700;">{current_balance:,} credits</p>

                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Required for Admin Seats:</strong></p>
                                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 20px; font-weight: 700;">{required_credits:,} credits</p>

                                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;"><strong>Deficit:</strong></p>
                                        <p style="margin: 0; color: #d84315; font-size: 24px; font-weight: 700;">{deficit:,} credits</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 20px 0 10px 0; color: #333333; font-size: 16px; line-height: 1.6;">You have <strong>{admin_seats_count}</strong> admin seat(s) that require monthly billing. Please purchase additional credits to ensure uninterrupted service.</p>

                            <p style="margin: 0 0 30px 0; color: #666666; font-size: 14px; line-height: 1.6;"><em>Note: Admin seat billing will be retried once sufficient credits are available.</em></p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding-bottom: 30px;">
                                        <a href="{purchase_link}" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Purchase Credits</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 14px; line-height: 1.6;">If you have any questions about your billing or need assistance, please contact us at <a href="mailto:billing@yubanow.com" style="color: #128AA3; text-decoration: none;">billing@yubanow.com</a>.</p>

                            <p style="margin: 20px 0 0 0; color: #333333; font-size: 16px; line-height: 1.6;">Best regards,<br>The Yuba Team</p>
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

        text_content = f"""Low Credit Balance Alert - {org_name}

Hello,

Your organization {org_name} has insufficient credits to cover the monthly admin seat billing charges.

Credit Status:
-----------------
Current Credit Balance: {current_balance:,} credits
Required for Admin Seats: {required_credits:,} credits
Deficit: {deficit:,} credits

You have {admin_seats_count} admin seat(s) that require monthly billing. Please purchase additional credits to ensure uninterrupted service.

Note: Admin seat billing will be retried once sufficient credits are available.

Purchase credits here:
{purchase_link}

If you have any questions about your billing or need assistance, please contact us at billing@yubanow.com.

Best regards,
The Yuba Team

---
© Yuba Labs Ltd"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def send_enterprise_demo_request_email(
        self,
        full_name: str,
        email: str,
        phone_number: str,
        job_title: str,
        org_name: str,
        org_type: str,
        org_size: str,
        country: str,
        city: str,
        expected_users: str,
        additional_notes: str,
        requested_tier: str,
        source: str,
        submitted_at: str,
    ) -> bool:
        """
        Send an enterprise demo request notification email to the sales team.

        Args:
            full_name: Requester's full name
            email: Requester's email address
            phone_number: Requester's phone number
            job_title: Requester's job title
            org_name: Organization name
            org_type: Organization type
            org_size: Organization size
            country: Organization country
            city: Organization city
            expected_users: Expected number of users
            additional_notes: Additional notes from the requester
            requested_tier: Requested pricing tier
            source: Source of the request
            submitted_at: Submission timestamp
        """
        subject = f"🎯 New Enterprise Demo Request from {org_name}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>New Enterprise Demo Request</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header with gradient -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #128AA3, #244694); padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">🎯 New Enterprise Demo Request</h1>
                        </td>
                    </tr>

                    <!-- Main content -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px;">
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">A new enterprise demo request has been submitted through the pricing page.</p>

                            <!-- Contact Information -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8f9fa; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 15px 0; color: #128AA3; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Contact Information</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Name:</strong> {full_name}</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Email:</strong> <a href="mailto:{email}" style="color: #128AA3; text-decoration: none;">{email}</a></p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Phone:</strong> {phone_number}</p>
                                        <p style="margin: 0; color: #333333; font-size: 15px;"><strong>Job Title:</strong> {job_title}</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Organization Information -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #e8f4f8; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 15px 0; color: #128AA3; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Organization Details</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Organization:</strong> {org_name}</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Type:</strong> {org_type}</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Size:</strong> {org_size}</p>
                                        <p style="margin: 0; color: #333333; font-size: 15px;"><strong>Location:</strong> {city}, {country}</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Request Details -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #fff8e6; border-left: 4px solid #ffa726; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 15px 0; color: #e65100; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Request Details</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Expected Users:</strong> {expected_users}</p>
                                        <p style="margin: 0 0 8px 0; color: #333333; font-size: 15px;"><strong>Requested Tier:</strong> {requested_tier}</p>
                                        <p style="margin: 0; color: #333333; font-size: 15px;"><strong>Source:</strong> {source}</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Additional Notes -->
                            {f'''<div style="background-color: #f8f9fa; border-left: 4px solid #244694; padding: 16px; margin: 20px 0; border-radius: 4px;">
                                <p style="margin: 0 0 8px 0; color: #244694; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Additional Notes:</p>
                                <p style="margin: 0; color: #333333; font-size: 15px; line-height: 1.6;">{additional_notes}</p>
                            </div>''' if additional_notes else ''}

                            <p style="margin: 20px 0 10px 0; color: #666666; font-size: 14px; line-height: 1.6;"><strong>Submitted at:</strong> {submitted_at}</p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding: 20px 0;">
                                        <a href="mailto:{email}?subject=Re: Your Yuba Enterprise Demo Request" style="display: inline-block; background: linear-gradient(135deg, #128AA3, #244694); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Reply to Request</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px 30px 40px; text-align: center; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; color: #999999; font-size: 14px;">© Yuba Labs Ltd - Internal Sales Notification</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        text_content = f"""New Enterprise Demo Request

A new enterprise demo request has been submitted through the pricing page.

CONTACT INFORMATION
-------------------
Name: {full_name}
Email: {email}
Phone: {phone_number}
Job Title: {job_title}

ORGANIZATION DETAILS
--------------------
Organization: {org_name}
Type: {org_type}
Size: {org_size}
Location: {city}, {country}

REQUEST DETAILS
---------------
Expected Users: {expected_users}
Requested Tier: {requested_tier}
Source: {source}

{f"ADDITIONAL NOTES:{chr(10)}{additional_notes}" if additional_notes else ""}

Submitted at: {submitted_at}

---
© Yuba Labs Ltd - Internal Sales Notification"""

        return self.send_email(
            to_email="info@yubanow.com",
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            reply_to=email,
        )

    def send_org_admin_credit_request_email(
        self,
        org_id: str,
        org_name: str,
        org_email: Optional[str],
        requester_name: str,
        requester_email: str,
        requested_amount: int,
        reason: str,
        urgency: str,
        reference_id: str,
    ) -> bool:
        """
        Send a credit request email from org admin to Yuba (info@yubanow.com).
        
        This is used by grant organizations to request additional credits from Yuba.

        Args:
            org_id: Organization ID
            org_name: Organization name
            org_email: Organization contact email
            requester_name: Name of the person requesting
            requester_email: Email of the requester
            requested_amount: Amount of credits requested
            reason: Reason for the request
            urgency: Urgency level (normal, high, urgent)
            reference_id: Reference ID for tracking
        """
        urgency_badge = {
            "normal": "🟢 Normal",
            "high": "🟡 High Priority",
            "urgent": "🔴 Urgent",
        }.get(urgency, "🟢 Normal")
        
        urgency_color = {
            "normal": "#10B981",
            "high": "#F59E0B",
            "urgent": "#EF4444",
        }.get(urgency, "#10B981")

        subject = f"[Credit Request] {org_name} - {requested_amount:,} Credits ({reference_id})"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Credit Request from {org_name}</title>
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
                            <p style="margin: 10px 0 0 0; color: #ffffff; font-size: 18px;">Credit Request Received</p>
                        </td>
                    </tr>

                    <!-- Urgency Badge -->
                    <tr>
                        <td style="padding: 20px 40px 0 40px; text-align: center;">
                            <span style="display: inline-block; background-color: {urgency_color}; color: #ffffff; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: 600;">{urgency_badge}</span>
                        </td>
                    </tr>

                    <!-- Main content -->
                    <tr>
                        <td style="padding: 30px 40px;">
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.6;">A grant organization has submitted a credit request.</p>

                            <!-- Reference ID -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 20px 0; background-color: #f0f9ff; border-radius: 8px; border-left: 4px solid #128AA3;">
                                <tr>
                                    <td style="padding: 15px 20px;">
                                        <p style="margin: 0; color: #666666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Reference ID</p>
                                        <p style="margin: 5px 0 0 0; color: #128AA3; font-size: 20px; font-weight: 700;">{reference_id}</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Credit Amount Box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 20px 0;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #10B981, #059669); border-radius: 12px; padding: 25px; text-align: center;">
                                        <p style="margin: 0 0 5px 0; color: #ffffff; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Credits Requested</p>
                                        <p style="margin: 0; color: #ffffff; font-size: 42px; font-weight: 700;">{requested_amount:,}</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Organization Details -->
                            <h3 style="margin: 25px 0 15px 0; color: #333333; font-size: 16px; font-weight: 600; border-bottom: 1px solid #eeeeee; padding-bottom: 10px;">Organization Details</h3>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 8px 0; color: #666666; font-size: 14px; width: 35%;">Organization:</td>
                                    <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: 600;">{org_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666666; font-size: 14px;">Org ID:</td>
                                    <td style="padding: 8px 0; color: #333333; font-size: 14px; font-family: monospace;">{org_id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666666; font-size: 14px;">Org Email:</td>
                                    <td style="padding: 8px 0; color: #333333; font-size: 14px;">{org_email or 'Not provided'}</td>
                                </tr>
                            </table>

                            <!-- Requester Details -->
                            <h3 style="margin: 25px 0 15px 0; color: #333333; font-size: 16px; font-weight: 600; border-bottom: 1px solid #eeeeee; padding-bottom: 10px;">Requester Details</h3>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 8px 0; color: #666666; font-size: 14px; width: 35%;">Name:</td>
                                    <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: 600;">{requester_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #666666; font-size: 14px;">Email:</td>
                                    <td style="padding: 8px 0; color: #333333; font-size: 14px;"><a href="mailto:{requester_email}" style="color: #128AA3; text-decoration: none;">{requester_email}</a></td>
                                </tr>
                            </table>

                            <!-- Reason -->
                            <h3 style="margin: 25px 0 15px 0; color: #333333; font-size: 16px; font-weight: 600; border-bottom: 1px solid #eeeeee; padding-bottom: 10px;">Reason for Request</h3>
                            <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin: 15px 0;">
                                <p style="margin: 0; color: #333333; font-size: 14px; line-height: 1.8; white-space: pre-wrap;">{reason}</p>
                            </div>

                            <!-- Action Required -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 25px 0; background-color: #fffbeb; border-radius: 8px; border-left: 4px solid #F59E0B;">
                                <tr>
                                    <td style="padding: 15px 20px;">
                                        <p style="margin: 0; color: #92400e; font-size: 14px; font-weight: 600;">Action Required</p>
                                        <p style="margin: 5px 0 0 0; color: #78350f; font-size: 14px;">Please review this credit request and grant credits via the Yuba Admin dashboard if approved.</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px 30px 40px; text-align: center; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; color: #999999; font-size: 14px;">© Yuba Labs Ltd - Internal Credit Request</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        text_content = f"""CREDIT REQUEST FROM ORGANIZATION

Reference ID: {reference_id}
Urgency: {urgency_badge}

CREDITS REQUESTED
-----------------
{requested_amount:,} credits

ORGANIZATION DETAILS
--------------------
Organization: {org_name}
Org ID: {org_id}
Org Email: {org_email or 'Not provided'}

REQUESTER DETAILS
-----------------
Name: {requester_name}
Email: {requester_email}

REASON FOR REQUEST
------------------
{reason}

ACTION REQUIRED
---------------
Please review this credit request and grant credits via the Yuba Admin dashboard if approved.

---
© Yuba Labs Ltd - Internal Credit Request"""

        return self.send_email(
            to_email=os.getenv("YUBA_ADMIN_EMAIL", "info@yubanow.com"),
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            reply_to=requester_email,
        )


# Create a singleton instance of the email service
email_service = EmailService()
