"""
API endpoints for admin credit granting and organization credit allocation.

Optimized with async services and background email dispatch for high performance.
"""

import logging
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..auth_v2.utils import (
    get_super_admin_user,
    get_admin_user,
    get_global_admin_or_tenant_admin,
    get_tenant_id
)
from .admin_models import (
    AdminCreditGrantRequest,
    AdminCreditGrantResponse,
    OrganizationCreditAllocationRequest,
    OrganizationCreditAllocationResponse,
    BulkAllocationRequest,
    BulkAllocationResponse,
    ToggleOrganizationCreditsRequest,
    ToggleOrganizationCreditsResponse
)
from .async_admin_service import (
    AsyncAdminCreditService,
    AsyncOrganizationCreditAllocationService
)
from .async_email_dispatcher import (
    dispatch_credit_grant_email,
    dispatch_credit_allocation_email
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/credits", tags=["credits"])


# =============================================
# ADMIN/SUPER ADMIN ENDPOINTS
# =============================================

@router.post(
    "/admin/grant",
    response_model=AdminCreditGrantResponse,
    summary="Grant credits to organization (Admin/Super Admin only)"
)
async def grant_credits_to_organization(
    request: AdminCreditGrantRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_user),
) -> AdminCreditGrantResponse:
    """
    Grant credits to an organization.

    Only admins and super admins can grant credits.
    - grant_org: Credits expire 1 year from the grant date
    - prepay_org/postpay_org: No expiry

    **Required Role:** admin or super_admin
    """
    try:
        service = AsyncAdminCreditService()

        result = await service.grant_credits_to_organization(
            organization_id=request.organization_id,
            admin_user_id=current_user["user_id"],
            credit_amount=request.credit_amount
        )

        # Queue email notification in background (non-blocking)
        email_recipient = result.get("email_recipient")
        if email_recipient:
            background_tasks.add_task(
                dispatch_credit_grant_email,
                to_email=email_recipient,
                org_name=result["organization_name"],
                credit_amount=result["credit_amount"],
                expires_at_formatted=result["expires_at"].strftime("%B %d, %Y"),
                granted_by_name=result.get("admin_name", "Yuba Admin"),
            )

        return AdminCreditGrantResponse(
            success=result["success"],
            message=f"Successfully granted {result['credit_amount']} credits to {result['organization_name']}",
            organization_id=result["organization_id"],
            organization_name=result["organization_name"],
            credit_amount=result["credit_amount"],
            expires_at=result["expires_at"],
            granted_by=result["granted_by"],
            granted_at=result["granted_at"],
            lot_id=result.get("lot_id"),
            email_sent=bool(email_recipient),
            email_recipient=email_recipient
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting credits: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grant credits: {str(e)}"
        )


@router.post(
    "/admin/orgs/{organization_id}/toggle-suspension",
    response_model=ToggleOrganizationCreditsResponse,
    summary="Toggle suspension of all organization credits (Admin/Super Admin only)"
)
async def toggle_organization_credits_suspension(
    organization_id: str,
    request: ToggleOrganizationCreditsRequest,
    current_user: dict = Depends(get_admin_user),
) -> ToggleOrganizationCreditsResponse:
    """
    Toggle suspension state of all credits from an organization.

    Sets is_active on all credit lots where original_tenant_id matches the organization.
    This affects both the organization's own credits and credits allocated to members/teams.

    **Required Role:** admin or super_admin

    Args:
        organization_id: Organization tenant ID
        request: Contains is_active (True to activate, False to suspend)
    """
    try:
        service = AsyncAdminCreditService()

        result = await service.toggle_organization_credits_suspension(
            organization_id=organization_id,
            admin_user_id=current_user["user_id"],
            is_active=request.is_active
        )

        action = "activated" if request.is_active else "suspended"
        message = f"Successfully {action} {result['affected_lot_count']} credit lots for {result['organization_name']}"

        return ToggleOrganizationCreditsResponse(
            success=result["success"],
            message=message,
            organization_id=result["organization_id"],
            organization_name=result["organization_name"],
            affected_lot_count=result["affected_lot_count"],
            new_state=result["new_state"],
            toggled_by=result["toggled_by"],
            toggled_at=result["toggled_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling organization credits suspension: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to toggle credits suspension: {str(e)}"
        )


# =============================================
# ORGANIZATION ADMIN ENDPOINTS
# =============================================

@router.post(
    "/orgs/{organization_id}/allocate",
    response_model=OrganizationCreditAllocationResponse,
    summary="Allocate credits to tenant (Organization Admin)"
)
async def allocate_credits_to_tenant(
    organization_id: str,
    request: OrganizationCreditAllocationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_global_admin_or_tenant_admin),
) -> OrganizationCreditAllocationResponse:
    """
    Allocate credits from organization to a tenant (individual or team).

    The tenant must belong to the organization.
    Credits are deducted from the organization's balance.
    Email notification is sent asynchronously in the background.

    **Required Role:** Organization admin/owner OR global admin/super_admin
    """
    try:
        # Verify the organization_id from path matches the current user's context
        # (unless they're a global admin/super_admin)
        if current_user["roles"][0] not in ["admin", "super_admin"]:
            if current_user.get("tenant_id") != organization_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot allocate credits for a different organization"
                )

        service = AsyncOrganizationCreditAllocationService()

        result = await service.allocate_credits_to_tenant(
            organization_id=organization_id,
            tenant_id=request.tenant_id,
            tenant_type=request.tenant_type,
            allocated_by_user_id=current_user["user_id"],
            credit_amount=request.credit_amount
        )

        # Queue email notification in background (non-blocking)
        email_recipient = result.get("email_recipient")
        if email_recipient:
            background_tasks.add_task(
                dispatch_credit_allocation_email,
                to_email=email_recipient,
                tenant_name=result.get("tenant_name") or result["tenant_type"].capitalize(),
                credit_amount=result["credit_amount"],
                expires_at_formatted=result["expires_at"].strftime("%B %d, %Y"),
                allocator_name=result.get("allocator_name", "Organization Admin"),
                org_name=result.get("organization_name", "Organization"),
            )

        tenant_name = result.get("tenant_name") or result["tenant_type"].capitalize()
        return OrganizationCreditAllocationResponse(
            success=result["success"],
            message=f"Successfully allocated {result['credit_amount']} credits to {tenant_name}",
            organization_id=result["organization_id"],
            organization_name=result.get("organization_name"),
            tenant_id=result["tenant_id"],
            tenant_name=result.get("tenant_name"),
            tenant_type=result["tenant_type"],
            credit_amount=result["credit_amount"],
            expires_at=result["expires_at"],
            allocated_by=result["allocated_by"],
            allocated_at=result["allocated_at"],
            remaining_org_credits=result["remaining_org_credits"],
            email_sent=bool(email_recipient),
            email_recipient=email_recipient
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error allocating credits: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to allocate credits: {str(e)}"
        )


@router.post(
    "/orgs/{organization_id}/allocate/bulk",
    response_model=BulkAllocationResponse,
    summary="Bulk allocate credits to multiple tenants (Organization Admin)"
)
async def bulk_allocate_credits_to_tenants(
    organization_id: str,
    request: BulkAllocationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_global_admin_or_tenant_admin),
) -> BulkAllocationResponse:
    """
    Allocate credits from organization to multiple tenants in a single operation.

    Allows organization admins to allocate credits to multiple individuals or teams at once.
    For non-postpay organizations, verifies sufficient credits upfront before processing allocations.
    For postpay organizations, allocations are recorded and will be billed at month-end.
    Email notifications are sent asynchronously in the background.

    **Required Role:** Organization admin/owner OR global admin/super_admin

    **Notes:**
    - Maximum 100 allocations per request
    - Individual allocation failures won't stop the batch
    - Returns detailed results for each allocation
    """
    try:
        service = AsyncOrganizationCreditAllocationService()

        # Convert Pydantic models to dicts for service layer
        allocations_dicts = [
            {
                "tenant_id": alloc.tenant_id,
                "tenant_type": alloc.tenant_type,
                "credit_amount": alloc.credit_amount
            }
            for alloc in request.allocations
        ]

        result = await service.bulk_allocate_credits_to_tenants(
            organization_id=organization_id,
            allocations=allocations_dicts,
            allocated_by_user_id=current_user["user_id"]
        )

        # Queue email notifications for successful allocations in background
        for alloc_result in result.get("results", []):
            if alloc_result.get("success") and alloc_result.get("email_recipient"):
                background_tasks.add_task(
                    dispatch_credit_allocation_email,
                    to_email=alloc_result["email_recipient"],
                    tenant_name=alloc_result.get("tenant_name") or alloc_result["tenant_type"].capitalize(),
                    credit_amount=alloc_result["credit_amount"],
                    expires_at_formatted=alloc_result["expires_at"].strftime("%B %d, %Y") if alloc_result.get("expires_at") else "N/A",
                    allocator_name=alloc_result.get("allocator_name", "Organization Admin"),
                    org_name=alloc_result.get("organization_name", "Organization"),
                )

        return BulkAllocationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing bulk allocation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform bulk allocation: {str(e)}"
        )


# =============================================
# CREDIT RESERVATION ENDPOINTS
# =============================================

@router.post(
    "/reservations/{invitation_id}/release",
    summary="Manually release credits reserved for an invitation (Admin only)"
)
async def release_credit_reservation(
    invitation_id: str,
    current_user: dict = Depends(get_admin_user),
) -> Dict:
    """
    Manually release credits reserved for an invitation.

    This returns the reserved credits to the organization's available pool
    without cancelling the invitation itself.

    Use cases:
    - Admin realizes wrong credit amount was specified
    - Need to free up credits for other purposes
    - Invitation will be resent with different terms

    **Required Role:** admin or super_admin
    """
    try:
        from .async_service import get_async_credit_service

        service = get_async_credit_service()
        lots_updated = await service.release_reservation(invitation_id)

        return {
            "success": True,
            "message": f"Released reservation for invitation {invitation_id}",
            "lots_updated": lots_updated,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error releasing credit reservation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to release reservation: {str(e)}"
        )


@router.get(
    "/orgs/{org_id}/reservations",
    summary="Get all active credit reservations for an organization (Admin only)"
)
async def get_org_credit_reservations(
    org_id: str,
    current_user: dict = Depends(get_admin_user),
) -> Dict:
    """
    Get all active credit reservations for an organization.

    Returns list of reserved lots with their invitation IDs and expiry times.
    Active reservations are those where reserved_until > now.

    **Required Role:** admin or super_admin
    """
    try:
        from .async_service import get_async_credit_service

        service = get_async_credit_service()
        reservations = await service.get_active_reservations(org_id)

        total_reserved = sum(r["credit_amount"] for r in reservations)

        return {
            "organization_id": org_id,
            "reservations": reservations,
            "total_reserved": total_reserved,
            "count": len(reservations),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org credit reservations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reservations: {str(e)}"
        )
