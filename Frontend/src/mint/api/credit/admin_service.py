"""
Service layer for admin credit granting and organization credit allocation.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from fastapi import HTTPException

from ..system.core.supabase_client import get_service_role_client
from .service import CreditService
from ..services.communication.email_service import email_service

logger = logging.getLogger(__name__)


class AdminCreditService:
    """Service for admin credit granting operations."""

    def __init__(self):
        """Initialize the admin credit service."""
        self.client = get_service_role_client()
        self.credit_service = CreditService(use_service_role=True)

    def _get_admin_name(self, admin_user_id: str) -> str:
        """Get the admin's display name from their user profile."""
        try:
            user_query = (
                self.client.client.table("user_profiles")
                .select("full_name, email")
                .eq("id", admin_user_id)
                .execute()
            )
            if user_query.data:
                user = user_query.data[0]
                return user.get("full_name") or user.get("email", "Yuba Admin")
            return "Yuba Admin"
        except Exception as e:
            logger.warning(f"Could not fetch admin name: {e}")
            return "Yuba Admin"

    def grant_credits_to_organization(
        self,
        organization_id: str,
        admin_user_id: str,
        credit_amount: int,
    ) -> Dict[str, Any]:
        """
        Grant credits to an organization. Credits expire 2 months from now.
        Sends email notification to the organization's contact email.

        Args:
            organization_id: Organization tenant ID
            admin_user_id: Admin/super admin user ID performing the grant
            credit_amount: Number of credits to grant

        Returns:
            Dictionary with grant details including lot_id and expiry

        Raises:
            HTTPException: If validation fails or operation fails
        """
        try:
            # Validate organization exists and is active (include contact_email for notification)
            org_query = (
                self.client.client.table("tenants")
                .select("id, name, contact_email")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )

            if not org_query.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_query.data[0]
            org_name = org.get("name", "Organization")
            org_contact_email = org.get("contact_email")

            # Validate credit amount
            if credit_amount < 1:
                raise HTTPException(
                    status_code=400,
                    detail="Credit amount must be at least 1"
                )

            # Determine expiry based on organization type
            now = datetime.now(timezone.utc)

            # Get organization billing config to check org type
            org_config = self.client.client.table('organization_billing_config') \
                .select('organization_type') \
                .eq('tenant_id', organization_id) \
                .limit(1) \
                .execute()

            org_type = 'grant_org'  # default
            if org_config.data and len(org_config.data) > 0:
                org_type = org_config.data[0].get('organization_type', 'grant_org')

            # Only grant_org has expiry (1 year)
            expires_at = None
            if org_type == 'grant_org':
                expires_at = (now + timedelta(days=365)).isoformat()  # 1 year

            # Create credit lot for the organization using CreditService
            self.credit_service.create_credit_lot(
                tenant_id=organization_id,
                source="grant",
                credit_amount=Decimal(str(credit_amount)),
                valid_from=now.isoformat(),
                expires_at=expires_at,
                metadata={
                    "granted_by": admin_user_id,
                    "grant_type": "admin_manual_grant",
                    "granted_at": now.isoformat()
                },
                original_tenant_id=organization_id
            )

            logger.info(
                f"Admin {admin_user_id} granted {credit_amount} credits to organization {organization_id}, "
                f"expires: {expires_at if expires_at else 'never'}"
            )

            # Send email notification to organization
            email_sent = False
            if org_contact_email:
                try:
                    admin_name = self._get_admin_name(admin_user_id)
                    # Format expiry date for email
                    if expires_at:
                        try:
                            expiry_dt = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00'))
                            expires_at_formatted = expiry_dt.strftime("%B %d, %Y")
                        except Exception:
                            expires_at_formatted = "N/A"
                    else:
                        expires_at_formatted = "No expiry"
                    
                    email_sent = email_service.send_credit_grant_notification_email(
                        to_email=org_contact_email,
                        org_name=org_name,
                        credit_amount=credit_amount,
                        expires_at=expires_at_formatted,
                        granted_by_name=admin_name
                    )
                    
                    if email_sent:
                        logger.info(f"Credit grant notification email sent to {org_contact_email}")
                    else:
                        logger.warning(f"Failed to send credit grant notification email to {org_contact_email}")
                except Exception as email_error:
                    logger.error(f"Error sending credit grant notification email: {email_error}")
            else:
                logger.info(f"No contact email for organization {organization_id}, skipping notification")

            return {
                "success": True,
                "organization_id": organization_id,
                "organization_name": org_name,
                "credit_amount": credit_amount,
                "expires_at": expires_at,
                "granted_by": admin_user_id,
                "granted_at": now,
                "email_sent": email_sent,
                "email_recipient": org_contact_email
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to grant credits to organization: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to grant credits: {str(e)}"
            )

    def toggle_organization_credits_suspension(
        self,
        organization_id: str,
        admin_user_id: str,
        is_active: bool,
    ) -> Dict[str, Any]:
        """
        Set suspension state of all credits from an organization.
        Updates credit lots where original_tenant_id matches the organization.

        When suspending: Marks ACTIVE lots as suspended and adds suspension marker to metadata.
        When unsuspending: Only unsuspends lots that were suspended by this operation
                          (have suspension marker in metadata).

        Args:
            organization_id: Organization tenant ID
            admin_user_id: Admin user ID performing the operation
            is_active: True to activate credits, False to suspend them

        Returns:
            Dictionary with operation details

        Raises:
            HTTPException: If validation fails or operation fails
        """
        try:
            # Validate organization exists and is active
            org_query = (
                self.client.client.table("tenants")
                .select("id, name")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )

            if not org_query.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_query.data[0]
            org_name = org.get("name", "Organization")
            now = datetime.now(timezone.utc)

            if is_active:
                # UNSUSPEND: Only activate lots that have the suspension marker
                # Use RPC to execute raw SQL for bulk JSONB operations
                result = self.client.client.rpc('toggle_org_credits_unsuspend', {
                    'org_id': organization_id
                }).execute()

                affected_count = result.data if result.data else 0

            else:
                # SUSPEND: Mark all ACTIVE lots as suspended and add suspension marker
                # Use RPC to execute raw SQL for bulk JSONB operations
                result = self.client.client.rpc('toggle_org_credits_suspend', {
                    'org_id': organization_id,
                    'admin_id': admin_user_id,
                    'suspended_at_ts': now.isoformat()
                }).execute()

                affected_count = result.data if result.data else 0

            state_name = "active" if is_active else "suspended"
            action = "activated" if is_active else "suspended"

            logger.info(
                f"Admin {admin_user_id} {action} {affected_count} credit lots "
                f"from organization {organization_id}"
            )

            return {
                "success": True,
                "organization_id": organization_id,
                "organization_name": org_name,
                "affected_lot_count": affected_count,
                "new_state": state_name,
                "toggled_by": admin_user_id,
                "toggled_at": now,
                "message": f"Successfully {action} {affected_count} credit lots"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to toggle organization credits suspension: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to toggle credits suspension: {str(e)}"
            )


class OrganizationCreditAllocationService:
    """Service for organization credit allocation to tenants."""

    def __init__(self):
        """Initialize the organization credit allocation service."""
        self.client = get_service_role_client()
        self.credit_service = CreditService(use_service_role=True)

    def _get_allocator_name(self, user_id: str) -> str:
        """Get the allocator's display name from their user profile."""
        try:
            user_query = (
                self.client.client.table("user_profiles")
                .select("full_name, email")
                .eq("id", user_id)
                .execute()
            )
            if user_query.data:
                user = user_query.data[0]
                return user.get("full_name") or user.get("email", "Organization Admin")
            return "Organization Admin"
        except Exception as e:
            logger.warning(f"Could not fetch allocator name: {e}")
            return "Organization Admin"

    def _get_tenant_contact_info(self, tenant_id: str, tenant_type: str) -> tuple:
        """
        Get contact email and name for a tenant.
        
        Returns:
            Tuple of (email, name) or (None, None) if not found
        """
        try:
            if tenant_type == "individual":
                # For individuals, get the user's email from org_individuals -> user_profiles
                ind_query = (
                    self.client.client.table("org_individuals")
                    .select("user_id")
                    .eq("individual_tenant_id", tenant_id)
                    .execute()
                )
                if ind_query.data:
                    user_id = ind_query.data[0].get("user_id")
                    if user_id:
                        user_query = (
                            self.client.client.table("user_profiles")
                            .select("email, full_name")
                            .eq("id", user_id)
                            .execute()
                        )
                        if user_query.data:
                            user = user_query.data[0]
                            return (user.get("email"), user.get("full_name", "Member"))
            
            elif tenant_type == "team":
                # For teams, get the team leader's email
                team_query = (
                    self.client.client.table("tenants")
                    .select("name, contact_email")
                    .eq("id", tenant_id)
                    .execute()
                )
                if team_query.data:
                    team = team_query.data[0]
                    team_name = team.get("name", "Team")
                    contact_email = team.get("contact_email")
                    
                    # If no contact_email, try to get team leader's email
                    if not contact_email:
                        leader_query = (
                            self.client.client.table("tenant_memberships")
                            .select("user_id")
                            .eq("tenant_id", tenant_id)
                            .eq("role", "owner")
                            .eq("is_active", True)
                            .execute()
                        )
                        if leader_query.data:
                            leader_user_id = leader_query.data[0].get("user_id")
                            if leader_user_id:
                                user_query = (
                                    self.client.client.table("user_profiles")
                                    .select("email")
                                    .eq("id", leader_user_id)
                                    .execute()
                                )
                                if user_query.data:
                                    contact_email = user_query.data[0].get("email")
                    
                    return (contact_email, team_name)
            
            return (None, None)
        except Exception as e:
            logger.warning(f"Could not fetch tenant contact info: {e}")
            return (None, None)

    def _verify_tenant_belongs_to_org(
        self,
        organization_id: str,
        tenant_id: str,
        tenant_type: str
    ) -> bool:
        """
        Verify that a tenant belongs to the organization.

        Args:
            organization_id: Organization tenant ID
            tenant_id: Tenant ID to check
            tenant_type: Type of tenant ('individual' or 'team')

        Returns:
            True if tenant belongs to organization, False otherwise
        """
        try:
            if tenant_type == "individual":
                # Check org_individuals table
                result = (
                    self.client.client.table("org_individuals")
                    .select("id")
                    .eq("organization_id", organization_id)
                    .eq("individual_tenant_id", tenant_id)
                    .execute()
                )
                return bool(result.data)

            elif tenant_type == "team":
                # Check org_teams table
                result = (
                    self.client.client.table("org_teams")
                    .select("id")
                    .eq("organization_id", organization_id)
                    .eq("team_id", tenant_id)
                    .execute()
                )
                return bool(result.data)

            return False

        except Exception as e:
            logger.error(f"Error verifying tenant membership: {e}")
            return False

    def allocate_credits_to_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        tenant_type: str,
        allocated_by_user_id: str,
        credit_amount: float,
    ) -> Dict[str, Any]:
        """
        Allocate credits from organization to a tenant (individual or team).

        Args:
            organization_id: Organization tenant ID
            tenant_id: Target tenant ID
            tenant_type: Type of target tenant ('individual' or 'team')
            allocated_by_user_id: User ID performing the allocation
            credit_amount: Number of credits to allocate (supports decimals)

        Returns:
            Dictionary with allocation details

        Raises:
            HTTPException: If validation fails or operation fails
        """
        try:
            # Validate tenant_type
            if tenant_type not in ["individual", "team"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid tenant_type. Must be 'individual' or 'team'"
                )

            # Validate organization exists and is active
            org_query = (
                self.client.client.table("tenants")
                .select("id, name")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )

            if not org_query.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_query.data[0]

            # Verify tenant belongs to organization
            if not self._verify_tenant_belongs_to_org(
                organization_id,
                tenant_id,
                tenant_type
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"Tenant does not belong to this organization"
                )

            # Validate credit amount
            if credit_amount < 1:
                raise HTTPException(
                    status_code=400,
                    detail="Credit amount must be at least 1"
                )

            now = datetime.now(timezone.utc)

            # Check organization type
            org_config_response = self.client.client.table('organization_billing_config') \
                .select('organization_type') \
                .eq('tenant_id', organization_id) \
                .limit(1) \
                .execute()

            org_type = 'grant_org'  # default
            if org_config_response.data and len(org_config_response.data) > 0:
                org_type = org_config_response.data[0].get('organization_type', 'grant_org')

            created_lot_id = None
            response_expiry = None

            if org_type == 'grant_org':
                # grant_org: Check available credits, deduct from org lots, create tenant lots with expiry
                available_credits = self.credit_service.get_available_credits(organization_id)

                if available_credits < credit_amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits. Organization has {available_credits} credits, tried to allocate {credit_amount}"
                    )

                # Fetch organization's active credit lots (ordered by expiry)
                all_org_lots = (
                    self.client.client.table("credit_lots")
                    .select("id, credit_amount, expires_at, source, reserved_until")
                    .eq("tenant_id", organization_id)
                    .eq("is_active", True)
                    .lte("valid_from", now.isoformat())
                    .order("expires_at", desc=False)
                    .execute()
                ).data or []

                # Filter: (expires_at is null OR expires_at > now) AND (reserved_until is null OR reserved_until <= now)
                now_iso = now.isoformat()
                org_lots = []
                for lot in all_org_lots:
                    expires_at = lot.get("expires_at")
                    reserved_until = lot.get("reserved_until")

                    is_expired = expires_at is not None and str(expires_at) <= now_iso
                    is_reserved = reserved_until is not None and str(reserved_until) > now_iso

                    if not is_expired and not is_reserved:
                        org_lots.append(lot)

                if not org_lots:
                    raise HTTPException(
                        status_code=400,
                        detail="No active credit lots available for organization"
                    )

                # Deduct from org lots and create tenant lots with same expiry
                remaining = Decimal(str(credit_amount))

                for lot in org_lots:
                    if remaining <= 0:
                        break

                    lot_credits = Decimal(str(lot["credit_amount"]))
                    if lot_credits <= 0:
                        continue

                    deduct = min(lot_credits, remaining)
                    new_balance = lot_credits - deduct

                    # Update org lot balance
                    self.client.client.table("credit_lots").update(
                        {"credit_amount": float(new_balance)}
                    ).eq("id", lot["id"]).execute()

                    # Create tenant lot with same expiry as source org lot
                    self.credit_service.create_credit_lot(
                        tenant_id=tenant_id,
                        source=lot.get("source", "grant"),
                        credit_amount=deduct,
                        valid_from=now.isoformat(),
                        expires_at=lot.get("expires_at"),  # Use lot's expiry
                        metadata={
                            "organization_id": organization_id,
                            "allocated_by": allocated_by_user_id,
                            "allocation_type": "manual",
                            "allocated_at": now.isoformat(),
                            "source_lot_id": lot["id"]
                        },
                        original_tenant_id=organization_id
                    )
                    # Track expiry from the first created tenant lot
                    if response_expiry is None:
                        response_expiry = lot.get("expires_at")

                    remaining -= deduct

            elif org_type == 'prepay_org':
                # prepay_org: Deduct from org lots but create ONE tenant lot with no expiry
                available_credits = self.credit_service.get_available_credits(organization_id)

                if available_credits < credit_amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits. Organization has {available_credits} credits, tried to allocate {credit_amount}"
                    )

                # Fetch organization's active credit lots
                all_org_lots = (
                    self.client.client.table("credit_lots")
                    .select("id, credit_amount, expires_at, reserved_until")
                    .eq("tenant_id", organization_id)
                    .eq("is_active", True)
                    .lte("valid_from", now.isoformat())
                    .order("expires_at", desc=False)
                    .execute()
                ).data or []

                # Filter: (expires_at is null OR expires_at > now) AND (reserved_until is null OR reserved_until <= now)
                now_iso = now.isoformat()
                org_lots = []
                for lot in all_org_lots:
                    expires_at = lot.get("expires_at")
                    reserved_until = lot.get("reserved_until")

                    is_expired = expires_at is not None and str(expires_at) <= now_iso
                    is_reserved = reserved_until is not None and str(reserved_until) > now_iso

                    if not is_expired and not is_reserved:
                        org_lots.append(lot)

                if not org_lots:
                    raise HTTPException(
                        status_code=400,
                        detail="No active credit lots available for organization"
                    )

                # Deduct from org lots
                remaining = Decimal(str(credit_amount))

                for lot in org_lots:
                    if remaining <= 0:
                        break

                    lot_credits = Decimal(str(lot["credit_amount"]))
                    if lot_credits <= 0:
                        continue

                    deduct = min(lot_credits, remaining)
                    new_balance = lot_credits - deduct

                    # Update org lot balance
                    self.client.client.table("credit_lots").update(
                        {"credit_amount": float(new_balance)}
                    ).eq("id", lot["id"]).execute()

                    remaining -= deduct

                # Create ONE tenant lot with no expiry
                self.credit_service.create_credit_lot(
                    tenant_id=tenant_id,
                    source="purchase",
                    credit_amount=Decimal(str(credit_amount)),
                    valid_from=now.isoformat(),
                    expires_at=None,  # No expiry for prepay_org
                    metadata={
                        "organization_id": organization_id,
                        "allocated_by": allocated_by_user_id,
                        "allocation_type": "manual",
                        "allocated_at": now.isoformat()
                    },
                    original_tenant_id=organization_id
                )
                response_expiry = None

            else:
                # postpay_org: Create ONE tenant lot with no expiry (no deduction from org)
                self.credit_service.create_credit_lot(
                    tenant_id=tenant_id,
                    source="purchase",
                    credit_amount=Decimal(str(credit_amount)),
                    valid_from=now.isoformat(),
                    expires_at=None,  # No expiry for postpay_org
                    metadata={
                        "organization_id": organization_id,
                        "allocated_by": allocated_by_user_id,
                        "allocation_type": "manual",
                        "allocated_at": now.isoformat()
                    },
                    original_tenant_id=organization_id
                )
                response_expiry = None

            # Note: created_lot_id is not available as create_credit_lot doesn't return the row
            # response_expiry is set above based on the first created lot for grant_org

            # For postpay_org, record this allocation for billing
            if org_type == 'postpay_org':
                try:
                    # Determine allocation type based on tenant_type
                    allocation_type = 'allocation_to_team' if tenant_type == 'team' else 'allocation_to_member'

                    # Get user_id if it's an individual allocation
                    user_id = None
                    if tenant_type == 'individual':
                        user_tenant_response = self.client.client.table('tenant_memberships') \
                            .select('user_id') \
                            .eq('tenant_id', tenant_id) \
                            .limit(1) \
                            .execute()

                        if user_tenant_response.data and len(user_tenant_response.data) > 0:
                            user_id = user_tenant_response.data[0].get('user_id')

                    allocation_payload = {
                        'tenant_id': organization_id,
                        'allocation_type': allocation_type,
                        'credit_amount': float(credit_amount),
                        'credit_lot_id': created_lot_id,
                        'allocated_to_tenant_id': tenant_id,
                        'allocated_to_user_id': user_id,
                        'allocated_by_user_id': allocated_by_user_id,
                        'allocated_at': now.isoformat(),
                        'metadata': {
                            "organization_id": organization_id,
                            "allocated_by": allocated_by_user_id,
                            "allocation_type": "manual",
                            "tenant_type": tenant_type
                        },
                    }

                    self.client.client.table('organization_credit_allocations') \
                        .insert(allocation_payload) \
                        .execute()

                    logger.info(f"Recorded {tenant_type} credit allocation for postpay_org {organization_id}: {credit_amount} credits to {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to record {tenant_type} credit allocation for postpay_org {organization_id}: {e}", exc_info=True)
                    # Don't fail the allocation if tracking fails

            # Get remaining organization credits
            remaining_org_credits = self.credit_service.get_available_credits(organization_id) if org_type != 'postpay_org' else 0

            logger.info(
                f"Organization {organization_id} allocated {credit_amount} credits to "
                f"{tenant_type} {tenant_id}, remaining org credits: {remaining_org_credits}"
            )

            # Send email notification to tenant
            email_sent = False
            tenant_email, tenant_name = self._get_tenant_contact_info(tenant_id, tenant_type)
            
            if tenant_email:
                try:
                    allocator_name = self._get_allocator_name(allocated_by_user_id)
                    org_name = org.get("name", "Organization")

                    # Format expiry (grant_org has expiry, prepay/postpay don't)
                    if response_expiry:
                        try:
                            expiry_dt = datetime.fromisoformat(str(response_expiry).replace('Z', '+00:00'))
                            expires_at_formatted = expiry_dt.strftime("%B %d, %Y")
                        except Exception:
                            expires_at_formatted = "N/A"
                    else:
                        expires_at_formatted = "No expiry"

                    email_sent = email_service.send_credit_grant_notification_email(
                        to_email=tenant_email,
                        org_name=tenant_name or tenant_type.capitalize(),
                        credit_amount=int(credit_amount),
                        expires_at=expires_at_formatted,
                        granted_by_name=f"{allocator_name} ({org_name})"
                    )
                    
                    if email_sent:
                        logger.info(f"Credit allocation notification email sent to {tenant_email}")
                    else:
                        logger.warning(f"Failed to send credit allocation notification email to {tenant_email}")
                except Exception as email_error:
                    logger.error(f"Error sending credit allocation notification email: {email_error}")
            else:
                logger.info(f"No contact email for {tenant_type} {tenant_id}, skipping notification")

            return {
                "success": True,
                "organization_id": organization_id,
                "organization_name": org.get("name"),
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                "tenant_type": tenant_type,
                "credit_amount": credit_amount,
                "expires_at": response_expiry,  # None for prepay/postpay, lot expiry for grant_org
                "allocated_by": allocated_by_user_id,
                "allocated_at": now,
                "remaining_org_credits": remaining_org_credits,
                "email_sent": email_sent,
                "email_recipient": tenant_email
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to allocate credits to tenant: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to allocate credits: {str(e)}"
            )

    def bulk_allocate_credits_to_tenants(
        self,
        organization_id: str,
        allocations: list,
        allocated_by_user_id: str,
    ) -> Dict[str, Any]:
        """
        Allocate credits to multiple tenants in a single operation.

        Args:
            organization_id: Organization tenant ID
            allocations: List of dicts with keys: tenant_id, tenant_type, credit_amount
            allocated_by_user_id: User ID performing the allocations

        Returns:
            Dictionary with bulk allocation results

        Raises:
            HTTPException: If validation fails
        """
        try:
            # Validate organization exists and is active
            org_query = (
                self.client.client.table("tenants")
                .select("id, name")
                .eq("id", organization_id)
                .eq("tenant_type", "organization")
                .eq("is_active", True)
                .execute()
            )

            if not org_query.data:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive"
                )

            org = org_query.data[0]
            now = datetime.now(timezone.utc)

            # Check organization type
            org_config_response = self.client.client.table('organization_billing_config') \
                .select('organization_type') \
                .eq('tenant_id', organization_id) \
                .limit(1) \
                .execute()

            org_type = 'grant_org'  # default
            if org_config_response.data and len(org_config_response.data) > 0:
                org_type = org_config_response.data[0].get('organization_type', 'grant_org')

            # Calculate total credits needed
            total_credits_needed = sum(alloc['credit_amount'] for alloc in allocations)

            # For non-postpay orgs, verify sufficient unreserved credits upfront
            if org_type != 'postpay_org':
                available_credits = self.credit_service.get_unreserved_available_credits(organization_id)
                if available_credits < total_credits_needed:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient credits. Organization has {available_credits} credits, but {total_credits_needed} requested"
                    )

            # Process each allocation
            results = []
            successful_count = 0
            failed_count = 0

            for alloc in allocations:
                try:
                    result = self.allocate_credits_to_tenant(
                        organization_id=organization_id,
                        tenant_id=alloc['tenant_id'],
                        tenant_type=alloc['tenant_type'],
                        allocated_by_user_id=allocated_by_user_id,
                        credit_amount=alloc['credit_amount']
                    )

                    results.append({
                        "tenant_id": alloc['tenant_id'],
                        "tenant_name": result.get("tenant_name"),
                        "tenant_type": alloc['tenant_type'],
                        "credit_amount": alloc['credit_amount'],
                        "success": True,
                        "error": None
                    })
                    successful_count += 1

                except Exception as e:
                    logger.error(f"Failed to allocate {alloc['credit_amount']} credits to {alloc['tenant_id']}: {e}")
                    results.append({
                        "tenant_id": alloc['tenant_id'],
                        "tenant_name": None,
                        "tenant_type": alloc['tenant_type'],
                        "credit_amount": alloc['credit_amount'],
                        "success": False,
                        "error": str(e)
                    })
                    failed_count += 1

            # Get final remaining credits
            remaining_org_credits = self.credit_service.get_available_credits(organization_id) if org_type != 'postpay_org' else 0

            logger.info(
                f"Bulk allocation completed for organization {organization_id}: "
                f"{successful_count} succeeded, {failed_count} failed"
            )

            return {
                "success": failed_count == 0,
                "message": f"Bulk allocation completed: {successful_count} succeeded, {failed_count} failed",
                "organization_id": organization_id,
                "organization_name": org.get("name"),
                "total_requested": len(allocations),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "results": results,
                "remaining_org_credits": remaining_org_credits,
                "allocated_by": allocated_by_user_id,
                "allocated_at": now
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to perform bulk allocation: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to perform bulk allocation: {str(e)}"
            )
