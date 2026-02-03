"""
Organization API endpoints for admin management and public access.

This module provides REST API endpoints for organization CRUD operations
and public access for signup forms.
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from dotenv import load_dotenv
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException, Path,
                     Query, Request, status)
from src.mint.utils.url_safe_serializer import (create_invite_token,
                                                verify_invite_token)

# Removed unused import: get_current_user_context
from ..auth_v2.utils import (get_admin_user, get_current_user,
                             get_global_admin_or_tenant_admin,
                             get_global_admin_or_tenant_owner,
                             get_global_admin_or_tenant_member,
                             get_global_admin_or_org_owner,
                             get_super_admin_or_tenant_owner,
                             get_super_admin_user, get_tenant_admin,
                             get_tenant_owner, create_access_token)
from ..auth_v2.service import AuthService
from ..auth_v2.async_service import get_async_auth_service
from ..cache.redis_service import get_cache_service
from ..credit.async_service import get_async_credit_service
from ..services.communication.email_service import email_service
from ..tenant.models import (JoinOrganizationHTTPResponse,
                             TenantMembershipResponse, JoinAuthPayload)
from ..tenant.service import TenantService
from .models import (AllocateCreditsBody, AppInvitationCreateRequest,
                     AppInvitationResponse, InviteUsersRequest,
                     JoinOrganizationRequest, OrganizationCreateRequest,
                     OrganizationResponse, OrganizationUpdateRequest,
                     OrgMetricsResponse, SuperAdminOrganizationListResponse,
                     SuperAdminOrganizationSummaryResponse,
                     MemberProjectsListResponse, TenantProjectsResponse,
                     MemberProjectDetailResponse,
                     OrgChatCreateThreadRequest, OrgChatPostMessageRequest,
                     OrgChatThreadResponse, OrgChatThreadListResponse,
                     OrgChatMessageResponse, OrgChatAssistantResponse,
                     OrgChatMessageListResponse, OrgChatCitation,
                     CreditRequestCreate, CreditRequestUpdate,
                     TeamMemberCreditRequestCreate, IndividualMemberCreditRequestCreate,
                     OrgAdminCreditRequestCreate)
from .async_service import get_async_org_service

from src.mav.chat.adapters.database_adapter import get_chat_database_adapter
from src.mav.chat.workflow import run_chat_workflow
from src.mav.chat.models import ThreadStatus, MessageRole

logger = logging.getLogger(__name__)

# ============================================================================
# Cache Configuration for Member Projects Endpoints
# ============================================================================
MEMBER_PROJECTS_CACHE_TTL = 180  # 3 minutes
TENANT_PROJECTS_CACHE_TTL = 180  # 3 minutes
PROJECT_DETAIL_CACHE_TTL = 120   # 2 minutes (shorter due to audit logging)

load_dotenv()

# Create router for organization endpoints
router = APIRouter()


# NOTE: Organization invitation email sending is now handled by async_service.send_org_invite_and_update()
# The _send_invite_and_update_payed function is kept for backward compatibility with payment_invites
# which uses it in sync background tasks.


def _send_invite_and_update_payed(
    service,  # Not used but kept for backward compatibility
    invitation_id: str,
    to_email: str,
    org_name: str,
    invite_link: str,
    is_team_leader: bool,
    credit_amount: int,
) -> None:
    """
    Send a paid organization invitation email.

    This is a sync function used by payment_invites background tasks.
    Uses the appropriate email template based on whether the invitee is a team leader.
    """
    try:
        if is_team_leader:
            success = email_service.send_org_team_leader_invite_email(
                to_email=to_email,
                org_name=org_name,
                credit_amount=credit_amount,
                invite_link=invite_link,
            )
        else:
            success = email_service.send_org_individual_member_invite_email(
                to_email=to_email,
                org_name=org_name,
                credit_amount=credit_amount,
                invite_link=invite_link,
            )

        if success:
            logger.info(f"Sent paid invite email to {to_email} for org {org_name}")
        else:
            logger.error(f"Failed to send paid invite email to {to_email}")

    except Exception as e:
        logger.error(f"Error sending paid invite email to {to_email}: {e}")


@router.post("/admin/{organization_id}/invite")
async def invite_users_to_organization(
    organization_id: str,
    request: InviteUsersRequest,
    background_tasks: BackgroundTasks,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Invite users to join an organization (org admins + super/support admins only).
    Each invite may include its own admin flag and credit allocation.
    Emails are sent in the background. Also records invitation metrics.

    OPTIMIZED: Uses async service with batch invitation recording.
    """
    try:
        logger.info(
            f"Inviting users to organization {organization_id} - Inviter: {admin_user.get('email')}"
        )

        async_org_svc = get_async_org_service()

        # --- Validate organization & permissions (async) ---
        is_valid, org_data, error_msg = await async_org_svc.validate_organization(organization_id)
        if not is_valid:
            status_code = 404 if error_msg == "Organization not found" else 403
            raise HTTPException(status_code=status_code, detail={"message": error_msg})

        org_name = org_data.get("name", "Organization")

        # Check organization type to determine if payment is required
        org_type = await async_org_svc.get_org_type(organization_id)

        # Calculate total user credits for validation (admin seat costs handled on join)
        total_user_credits = sum(inv.credit_allocated for inv in request.invites)

        # For prepay_org and grant_org, check available credits for user allocations
        if org_type in ['prepay_org', 'grant_org']:
            available_credits = await async_org_svc.get_available_credits(organization_id)

            if total_user_credits > available_credits:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "insufficient_credits",
                        "message": (
                            f"Total credits requested ({total_user_credits}) exceed "
                            f"organization's available credits ({available_credits}). "
                            f"Note: Admin seat costs will be charged when users join."
                        ),
                    },
                )

        # Get inviter details for invitation tracking
        inviter_user_id = admin_user.get("user_id")
        inviter_email = admin_user.get("email")

        frontend_url = os.getenv("FRONTEND_URL", "")

        # --- Normalize, dedupe, and skip inviter ---
        unique_emails = set()
        clean_invites = []
        for invite in request.invites:
            em = invite.email.strip().lower()
            if not em or em == inviter_email or em in unique_emails:
                continue
            unique_emails.add(em)
            clean_invites.append(invite)

        if not clean_invites:
            return {
                "success": True,
                "message": "No valid invites to send",
                "invites": [],
            }

        # --- OPTIMIZED: Batch record all invitations ---
        invite_data = [
            {
                "email": inv.email.strip().lower(),
                "is_admin": inv.is_admin,
                "is_team_leader": inv.is_team_leader,
                "credits": inv.credit_allocated,
                "cohort_id": inv.cohort_id,
                "can_skip_modules": inv.can_skip_modules,
            }
            for inv in clean_invites
        ]

        recorded_invitations = await async_org_svc.batch_record_invitations(
            organization_id=organization_id,
            invites=invite_data,
            invited_by_user_id=inviter_user_id,
            invited_by_email=inviter_email,
        )

        # --- Queue email tasks for all recorded invitations ---
        sent = []
        for inv in recorded_invitations:
            inv_id = inv.get("id")
            inv_email = inv.get("email")
            is_team_leader = inv.get("is_team_leader", False)
            # DB record uses 'credits' column, not 'credit_allocated'
            credit_allocated = inv.get("credits", 0)

            if inv_id and inv_email:
                # Create unique invite token
                token = create_invite_token(
                    tenant_id=organization_id,
                    is_admin=inv.get("is_admin", False),
                    credit=credit_allocated,
                    is_team_leader=is_team_leader,
                )
                invite_link = f"{frontend_url}/invite/{token}?org_id={organization_id}"

                # Queue async email task
                background_tasks.add_task(
                    async_org_svc.send_org_invite_and_update,
                    inv_id,
                    inv_email,
                    org_name,
                    invite_link,
                    is_team_leader,
                    credit_allocated,
                )

                sent.append({
                    "email": inv_email,
                    "is_admin": inv.get("is_admin", False),
                    "is_team_leader": is_team_leader,
                    "credits": credit_allocated,
                    "token": token,
                })

        logger.info(f"✅ Queued {len(sent)} org invites for organization {organization_id}")

        return {
            "success": True,
            "message": f"Invites queued for {len(sent)} users",
            "invites": sent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting users to organization {organization_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "invite_failed",
                "message": "Failed to send invites",
                "error": str(e),
            },
        )


# ============================================================================
# Organization Type Endpoint (Must be before /{organization_id} routes)
# ============================================================================

@router.get("/my/type")
async def get_my_organization_type(
    current_user: dict = Depends(get_current_user),
):
    """
    Get the organization type for the currently authenticated org owner/admin.
    
    No parameters required - uses the tenant_id from the authenticated user's token.
    The user must be signed into an organization (tenant_type = 'organization').
    
    Returns:
        - organization_type: 'grant_org', 'prepay_org', or 'postpay_org'
    
    Organization Types:
        - grant_org: Monthly credit grants, no admin seat billing (default)
        - prepay_org: Pay upfront, admin seats charged immediately
        - postpay_org: Allocate freely, invoice at month-end
    """
    try:
        tenant_id = current_user.get("tenant_id")
        tenant_type = current_user.get("tenant_type")
        
        # Verify user is signed into an organization
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="No organization context found. Please sign in to an organization."
            )
        
        if tenant_type != "organization":
            raise HTTPException(
                status_code=400,
                detail=f"Current tenant is not an organization (type: {tenant_type}). "
                       "This endpoint is only for organization owners/admins."
            )
        
        logger.info(f"Fetching organization type for tenant {tenant_id} - User: {current_user.get('email')}")

        # Fetch organization type from billing config (async)
        svc = get_async_org_service()
        organization_type = await svc.get_org_type(tenant_id)
        
        return {
            "success": True,
            "organization_type": organization_type,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching organization type: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve organization type"
        )


@router.post("/{organization_id}/join", response_model=JoinOrganizationHTTPResponse)
async def join_organization(
    organization_id: str,
    body: JoinOrganizationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Join an organization tenant as admin or member.

    OPTIMIZED: Uses async service with parallel queries.
    """
    user_id = current_user.get("user_id")
    user_email = current_user.get("email")
    if not user_id or not user_email:
        raise HTTPException(status_code=401, detail="Authentication required")

    data = verify_invite_token(body.invite_token, organization_id)
    request_admin = bool(data.get("is_admin"))
    credit_amount = data.get("credits")

    svc = get_async_org_service()
    result = await svc.join_organization(
        tenant_id=organization_id,
        user_id=user_id,
        user_email=user_email,
        request_admin=request_admin,
        credit_amount=credit_amount if credit_amount else 0,
    )

    if not result.get("success"):
        message = result.get("message", "Failed to join organization")
        # Determine appropriate status code based on error type
        if "Organization not found" in message:
            status_code = 404
        elif "Already a member" in message:
            status_code = 409  # Conflict - user already joined
        elif "inactive" in message.lower() or "invalid" in message.lower():
            status_code = 400
        else:
            status_code = 500
        raise HTTPException(status_code=status_code, detail=message)

    # === Build auth payload (mirror tenant_login behavior) ===
    # Wrap in try-except to ensure join success is returned even if auth payload fails
    result_data = result.get("data", {})
    membership_role = result_data.get("role", "member")
    global_role = current_user["roles"][0] if current_user.get("roles") else "user"
    
    try:
        auth_svc = get_async_auth_service()

        # Fetch tenant details and user profile in parallel
        tenant_task = auth_svc.get_tenant_details(organization_id)
        user_task = auth_svc.get_user_by_id(user_id)
        tenant, safe_user = await asyncio.gather(tenant_task, user_task)

        if not tenant:
            # Join succeeded but can't build auth - return success with minimal auth
            logger.warning(f"Join succeeded but tenant not found for auth payload: {organization_id}")
            return JoinOrganizationHTTPResponse(
                success=True,
                message=result.get("message", "Joined organization successfully. Please log in again."),
                data=result_data,
                auth=None,
            )

        # can_skip_module is None when joining the organization tenant directly
        # It only applies when logging into a team or individual tenant that's part of an org
        access_token = create_access_token(
            email=user_email,
            roles=[global_role, membership_role],
            user_id=user_id,
            tenant_id=organization_id,
            tenant_type=tenant["tenant_type"],
            can_skip_module=None,
        )

        return JoinOrganizationHTTPResponse(
            success=True,
            message=result.get("message", "Joined organization successfully"),
            data=result_data,
            auth=JoinAuthPayload(
                access_token=access_token,
                tenant_id=organization_id,
                tenant_type=tenant["tenant_type"],
                user_id=user_id,
                email=user_email,
                roles=[global_role, membership_role],
                user=safe_user,
                is_team_leader=result.get("is_team_leader", False),
                can_skip_module=None,
            ),
        )
    except Exception as e:
        # Join succeeded but auth payload creation failed
        # Return success anyway - user can log in again to get proper token
        logger.error(f"Join succeeded but auth payload failed: {e}", exc_info=True)
        return JoinOrganizationHTTPResponse(
            success=True,
            message=result.get("message", "Joined organization successfully. Please log in again to access."),
            data=result_data,
            auth=None,
        )


@router.get("/{organization_id}/membership")
async def get_user_membership_details(
    organization_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get current user's membership details in an organization.
    Returns membership info, organization details, and invitation data including credits allocated.
    """
    user_id = current_user.get("user_id")
    user_email = current_user.get("email")

    if not user_id or not user_email:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        logger.info(
            f"🔍 MEMBERSHIP ENDPOINT: Fetching membership details for user {user_email} (ID: {user_id}) in org {organization_id}"
        )

        # OPTIMIZED: Use async service with parallel queries
        svc = get_async_org_service()
        response_data = await svc.get_user_membership_in_org(
            user_id=user_id,
            user_email=user_email,
            org_id=organization_id,
        )

        logger.info(f"✅ Successfully fetched membership details for {user_email}")

        return {
            "success": True,
            "message": "Membership details retrieved successfully",
            "data": response_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching membership details: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve membership details"
        )


@router.get("/{organization_id}")
async def get_organization_details(
    organization_id: str,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Get organization details for organization owners and system admins.

    Organization owners can only access their own organization.
    System admins can access any organization.
    """
    try:
        logger.info(
            f"Getting organization details for {organization_id} - User: {admin_user.get('email')}"
        )

        # OPTIMIZED: Use async service with parallel queries
        svc = get_async_org_service()
        org_data = await svc.get_organization_details(organization_id)

        return {
            "success": True,
            "message": "Organization details retrieved successfully",
            "data": org_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting organization details for {organization_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving organization details",
        )


@router.get("/{organization_id}/metrics", response_model=OrgMetricsResponse)
async def get_org_metrics(
    organization_id: str,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Get organization metrics with parallel queries.

    OPTIMIZED: Uses async parallel queries for better performance under load.
    """
    svc = get_async_org_service()
    try:
        return await svc.get_org_metrics(org_id=organization_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching org metrics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=OrganizationResponse)
async def create_org_tenant(
    body: OrganizationCreateRequest,
    current_user: dict = Depends(get_current_user),  # anyone can create an org
):
    svc = get_async_org_service()
    try:
        org = await svc.create_organization_tenant(
            user_id=current_user["user_id"], body=body.dict()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not org:
        raise HTTPException(status_code=500, detail="Failed to create organization")

    return OrganizationResponse(
        success=True, message="Organization created successfully", data=org
    )


@router.post("/invite", response_model=AppInvitationResponse)
async def create_app_invitation(
    body: AppInvitationCreateRequest,
    current_user: dict = Depends(get_admin_user),
):
    svc = get_async_org_service()

    try:
        token, invite = await svc.generate_invitation(
            email=body.email,
            created_by=current_user["user_id"],
            credits=body.credit,
            org_type=body.organization_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create invitation: {str(e)}"
        )

    # Generate the correct invitation URL
    frontend_url = os.getenv("FRONTEND_URL", "")
    org_type_param = body.organization_type or "grant_org"
    invite_url = f"{frontend_url}/onboarding?token={token}&type={org_type_param}"

    return AppInvitationResponse(
        id=invite["id"],
        email=invite["email"],
        status=invite["status"],
        type=invite["type"],
        created_at=invite["created_at"],
        invite_url=invite_url,
    )


@router.put("/{organization_id}")
async def update_organization(
    organization_id: str,
    body: OrganizationUpdateRequest,
    current_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Update an organization's details.
    Only organization owners and global admins can perform this.

    OPTIMIZED: Uses async service for non-blocking updates.
    """
    svc = get_async_org_service()

    # Convert Pydantic model to dict, excluding unset fields
    update_data = body.dict(exclude_unset=True)

    try:
        updated_org = await svc.update_organization(
            org_id=organization_id, updates=update_data
        )
        return {
            "success": True,
            "message": "Organization updated successfully",
            "data": updated_org,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: dict = Depends(get_super_admin_or_tenant_owner),
):
    """
    Delete an organization tenant and all its related data.
    Only the org owner can perform this.
    """
    svc = get_async_org_service()
    deleted = await svc.delete_organization_tenant(
        org_id=organization_id, user_id=current_user["user_id"]
    )
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete organization")

    return {"success": True, "message": "Organization deleted successfully"}


@router.get("/{organization_id}/teams/overview")
async def get_team_overview(
    organization_id: str,
    current_month_only: bool = Query(False, description="If True, only fetch consumption for current month (faster). If False, fetch all consumption."),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Get team overview with credit information.

    OPTIMIZED: Uses async parallel queries for better performance under load.
    """
    svc = get_async_org_service()
    try:
        return await svc.get_team_overview(
            org_id=organization_id,
            current_month_only=current_month_only,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team overview: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{organization_id}/teams/members")
async def get_team_member_management(
    organization_id: str,
    current_month_only: bool = Query(False, description="If True, only fetch consumption for current month (faster). If False, fetch all consumption."),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Get team members with credit and request info for management.

    OPTIMIZED: Uses async parallel queries for better performance under load.
    """
    svc = get_async_org_service()
    try:
        return await svc.get_team_member_management(
            org_id=organization_id,
            current_month_only=current_month_only,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team members: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{organization_id}/teams/{team_id}")
async def soft_delete_team(
    organization_id: str,
    team_id: str,
    return_credits: bool = Query(True, description="Return remaining credits to organization"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Soft delete a team from the organization.

    This endpoint performs a soft delete by:
    - Setting the team tenant's is_active = False
    - Deactivating all team memberships
    - Optionally returning remaining credits to the organization
    - Deactivating team credit lots

    The team data is preserved for audit purposes but becomes inaccessible
    through normal API endpoints.

    OPTIMIZED: Uses async service with parallel queries.
    """
    svc = get_async_org_service()
    try:
        result = await svc.soft_delete_team(
            org_id=organization_id,
            team_id=team_id,
            admin_user_id=admin_user["user_id"],
            return_credits_to_org=return_credits,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error soft deleting team {team_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{organization_id}/individual-members")
async def get_individual_members(
    organization_id: str,
    current_month_only: bool = Query(False, description="If True, only fetch consumption for current month (faster). If False, fetch all consumption."),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Get individual members (organization members who are NOT part of any team).
    Returns member details including credits allocated and used.

    OPTIMIZED: Uses async parallel queries for better performance under load.
    """
    svc = get_async_org_service()
    try:
        return await svc.get_individual_members(
            org_id=organization_id,
            current_month_only=current_month_only,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching individual members: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{organization_id}/members/{user_id}")
async def delete_organization_member(
    organization_id: str,
    user_id: str,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Remove a member from the organization completely.
    This deletes their membership, allowing them to be re-invited.

    - Deletes tenant_membership record
    - Returns any allocated credits back to the organization
    - Allows the user to be re-invited to the organization

    For pending/expired invitations (user_id starts with "pending-"):
    - Deletes the invitation record from organization_invitations table

    OPTIMIZED: Uses async service with parallel queries.
    """
    svc = get_async_org_service()
    try:
        # Check if this is a pending/expired invitation (user_id starts with "pending-")
        if user_id.startswith("pending-"):
            invitation_id = user_id.replace("pending-", "")
            result = await svc.delete_pending_invitation(
                org_id=organization_id,
                invitation_id=invitation_id,
            )
        else:
            result = await svc.delete_organization_member(
                org_id=organization_id,
                user_id=user_id,
                admin_user_id=admin_user["user_id"],
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization member: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{organization_id}/invitations/{invitation_id}/resend")
async def resend_invitation(
    organization_id: str,
    invitation_id: str,
    background_tasks: BackgroundTasks,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Resend an invitation email for a pending or expired invitation.
    
    This endpoint:
    - Creates a new invite token
    - Updates the invitation status back to 'queued'
    - Sends a new invitation email
    - Updates the status to 'sent' after email is sent
    """
    try:
        # OPTIMIZED: Use async service with parallel queries
        import asyncio
        svc = get_async_org_service()

        # Get organization details and resend invitation in parallel
        org_task = svc.get_organization_basic_info(organization_id)
        resend_task = svc.resend_invitation(
            org_id=organization_id,
            invitation_id=invitation_id,
            admin_user_id=admin_user["user_id"],
        )

        org_data, result = await asyncio.gather(org_task, resend_task)

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Failed to resend invitation")
            )

        # Get organization name for email
        org_name = org_data.get("name", "Organization")

        # Send the email in the background using async service
        background_tasks.add_task(
            svc.send_org_invite_and_update,
            invitation_id,
            result["email"],
            org_name,
            result["invite_link"],
            result.get("is_team_leader", False),
            result.get("credits", 0),
        )
        
        return {
            "success": True,
            "message": f"Invitation resent to {result['email']}",
            "email": result["email"],
            "invitation_id": invitation_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resend invitation: {str(e)}"
        )


@router.post(
    "/{organization_id}/allocate",
    status_code=status.HTTP_201_CREATED,
)
async def allocate_credits_to_user(
    organization_id: str = Path(..., description="Organization tenant ID"),
    body: AllocateCreditsBody = ...,
    _user=Depends(get_global_admin_or_tenant_owner),
):
    """
    Org owner/admin allocates credits from the org to a user tenant.
    - Checks org has enough credits
    - Deducts from org lots (earliest expiry first)
    - Creates a user credit_lot with original_tenant_id = organization_id

    OPTIMIZED: Uses async service with parallel queries.
    """
    try:
        svc = get_async_org_service()
        created = await svc.allocate_from_org_to_user(
            organization_id=str(organization_id),
            user_tenant_id=str(body.user_tenant_id),
            amount=float(body.amount),
            valid_from=body.valid_from,
            expires_at=body.expires_at,
            metadata=body.metadata,
        )
        return created
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("allocate_credits_to_user failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{organization_id}/lots/{lot_id}/suspend",
    status_code=status.HTTP_200_OK,
)
async def suspend_user_lot_and_return_to_org(
    organization_id: str,
    lot_id: str,
    _user=Depends(get_global_admin_or_tenant_owner),
):
    """
    Return a user's credit lot back to the org (creates an org lot with the remaining amount)
    and delete the user lot.

    OPTIMIZED: Uses async service.
    """
    try:
        svc = get_async_org_service()
        result = await svc.suspend_user_lot_back_to_org(
            org_tenant_id=str(organization_id),
            lot_id=str(lot_id),
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("suspend_user_lot_and_return_to_org failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{organization_id}/lots/{lot_id}/freeze",
    status_code=status.HTTP_200_OK,
)
async def freeze_credit_lot(
    organization_id: str,
    lot_id: str,
    _user=Depends(get_global_admin_or_tenant_owner),
):
    """
    Set is_active=false on a user lot (must have been issued by this org).

    OPTIMIZED: Uses async service.
    """
    try:
        svc = get_async_org_service()
        updated = await svc.freeze_lot(
            lot_id=str(lot_id), organization_id=str(organization_id)
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("freeze_credit_lot failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{organization_id}/lots/issued",
    summary="List credit lots issued by the org (original_tenant_id = organization_id)",
)
async def list_org_issued_lots(
    organization_id: str,
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(get_global_admin_or_tenant_owner),
):
    credit_svc = get_async_credit_service()
    return await credit_svc.list_org_issued_lots(
        organization_id=organization_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


# =============================================
# SUPER ADMIN ENDPOINTS
# =============================================


@router.get("/admin/list", response_model=SuperAdminOrganizationListResponse)
async def list_all_organizations_for_super_admin(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search term for organization name"
    ),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    size: Optional[str] = Query(None, description="Filter by organization size"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    super_admin: dict = Depends(get_super_admin_user),
):
    """
    List all organizations with detailed information for Super Admin dashboard.

    Only Super Admins can access this endpoint.
    Provides comprehensive organization data including member counts, credit usage, and activity metrics.

    OPTIMIZED: Uses async service with parallel batch queries.
    """
    try:
        logger.info(
            f"Super Admin {super_admin.get('email')} requesting organization list"
        )

        svc = get_async_org_service()
        result = await svc.list_organizations_for_admin(
            page=page,
            page_size=page_size,
            search=search,
            industry=industry,
            country=country,
            size=size,
            is_active=is_active,
        )

        return SuperAdminOrganizationListResponse(
            success=True,
            message=f"Retrieved {len(result['organizations'])} organizations (async optimized)",
            data=result["organizations"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            has_next=result["has_next"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing organizations for super admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing organizations",
        )


@router.get("/admin/summary", response_model=SuperAdminOrganizationSummaryResponse)
async def get_organizations_summary_for_super_admin(
    super_admin: dict = Depends(get_super_admin_user),
):
    """
    Get comprehensive summary statistics of all organizations for Super Admin dashboard.

    Only Super Admins can access this endpoint.
    Provides aggregate statistics and breakdowns by industry, size, and country.

    OPTIMIZED: Uses async service with parallel queries.
    """
    try:
        logger.info(
            f"Super Admin {super_admin.get('email')} requesting organization summary"
        )

        svc = get_async_org_service()
        summary_data = await svc.get_organizations_summary()

        logger.info(
            f"Summary calculated: {summary_data['total_organizations']} orgs, "
            f"{summary_data['total_credits_allocated']} credits allocated"
        )

        return SuperAdminOrganizationSummaryResponse(
            success=True,
            message="Organization summary retrieved successfully (async optimized)",
            data=summary_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization summary for super admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting organization summary",
        )


@router.get("/admin/debug-credits/{organization_id}")
async def debug_organization_credits(
    organization_id: str,
    super_admin: dict = Depends(get_super_admin_user),
):
    """
    Debug endpoint to help diagnose credit calculation issues.
    Only available to Super Admins.

    OPTIMIZED: Uses async credit service with parallel queries.
    """
    try:
        logger.info(
            f"Super Admin {super_admin.get('email')} debugging credits for org {organization_id}"
        )

        # Get org info and credit debug info in parallel
        org_svc = get_async_org_service()
        credit_svc = get_async_credit_service()

        org_task = org_svc.validate_organization(organization_id)
        credit_task = credit_svc.get_org_credit_debug_info(organization_id)

        (is_valid, org, error_msg), credit_debug = await asyncio.gather(
            org_task, credit_task
        )

        if not is_valid:
            raise HTTPException(status_code=404, detail=error_msg or "Organization not found")

        debug_info = {
            "organization": org,
            **credit_debug,
        }

        return {
            "success": True,
            "message": f"Debug info for organization {org['name']}",
            "data": debug_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error debugging credits for organization {organization_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error debugging credits: {str(e)}",
        )


# ============================================================================
# Member Projects Access Endpoints
# ============================================================================

@router.get(
    "/{organization_id}/member-projects",
    response_model=MemberProjectsListResponse,
    summary="List organization members with their projects",
    description="Get all organization members (individual + team) with their project summaries. Only accessible by organization owners/admins."
)
async def get_organization_member_projects(
    request: Request,
    organization_id: str = Path(..., description="Organization ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Number of items per page"),
    member_type: str = Query(
        "all",
        regex="^(individual|team|all)$",
        description="Filter by member type: 'individual', 'team', or 'all'"
    ),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> MemberProjectsListResponse:
    """
    List all organization members with their projects.
    
    This endpoint provides an overview of all members (both individual and team)
    in the organization along with their project counts and latest projects.
    
    **Authorization:** Organization owner/admin only
    
    **Caching:** Results cached for 3 minutes per organization/page/filter combination
    
    **Use case:** Dashboard view showing all members and their activity
    """
    try:
        # Verify admin is accessing their own organization
        user_tenant_id = admin_user.get("tenant_id")
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's member projects"
            )
        
        # Check for cache bypass header
        skip_cache = request.headers.get("X-Skip-Cache", "").lower() == "true"
        
        # Generate cache key
        cache_key_data = f"org_member_projects:{organization_id}:{page}:{page_size}:{member_type}"
        cache_key = f"member_projects:{hashlib.md5(cache_key_data.encode()).hexdigest()}"
        
        # Try to get from cache (unless bypass requested)
        if not skip_cache:
            try:
                cache_service = get_cache_service()
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for member projects: {organization_id}")
                    return MemberProjectsListResponse(**cached_result)
            except Exception as cache_err:
                logger.warning(f"Cache read error: {cache_err}")
        
        # Get member projects using async service
        svc = get_async_org_service()
        result = await svc.get_organization_member_projects(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            member_type=member_type
        )
        
        # Cache the result
        try:
            cache_service = get_cache_service()
            await cache_service.set(cache_key, result, ttl=MEMBER_PROJECTS_CACHE_TTL)
            logger.debug(f"Cached member projects for org {organization_id}")
        except Exception as cache_err:
            logger.warning(f"Cache write error: {cache_err}")
        
        return MemberProjectsListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting member projects for org {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get member projects: {str(e)}"
        )


@router.get(
    "/{organization_id}/tenants/{tenant_id}/projects",
    response_model=TenantProjectsResponse,
    summary="Get projects for a specific member/team",
    description="Get all projects for a specific tenant (individual member or team). Only accessible by organization owners/admins."
)
async def get_organization_tenant_projects(
    request: Request,
    organization_id: str = Path(..., description="Organization ID"),
    tenant_id: str = Path(..., description="Tenant ID (individual or team)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Number of items per page"),
    admin_user: dict = Depends(get_global_admin_or_org_owner),
) -> TenantProjectsResponse:
    """
    Get all projects for a specific tenant (individual or team).
    
    This endpoint is used when clicking on a specific member's profile to view
    their complete list of projects.
    
    **Authorization:** Organization owner/admin only
    
    **Caching:** Results cached for 3 minutes per tenant/page combination
    
    **Use case:** Drill-down view when clicking on a specific member
    """
    try:
        # Note: Tenant verification is already done by get_global_admin_or_org_owner
        # which checks that user's tenant_id matches organization_id
        
        # Check for cache bypass header
        skip_cache = request.headers.get("X-Skip-Cache", "").lower() == "true"
        
        # Generate cache key
        cache_key_data = f"tenant_projects:{organization_id}:{tenant_id}:{page}:{page_size}"
        cache_key = f"tenant_projects:{hashlib.md5(cache_key_data.encode()).hexdigest()}"
        
        # Try to get from cache (unless bypass requested)
        if not skip_cache:
            try:
                cache_service = get_cache_service()
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for tenant projects: {tenant_id}")
                    return TenantProjectsResponse(**cached_result)
            except Exception as cache_err:
                logger.warning(f"Cache read error: {cache_err}")
        
        # Get tenant projects using async service
        svc = get_async_org_service()
        result = await svc.get_tenant_projects(
            organization_id=organization_id,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size
        )
        
        # Cache the result
        try:
            cache_service = get_cache_service()
            await cache_service.set(cache_key, result, ttl=TENANT_PROJECTS_CACHE_TTL)
            logger.debug(f"Cached tenant projects for tenant {tenant_id}")
        except Exception as cache_err:
            logger.warning(f"Cache write error: {cache_err}")
        
        return TenantProjectsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant projects for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant projects: {str(e)}"
        )


@router.get(
    "/{organization_id}/member-projects/{project_id}",
    response_model=MemberProjectDetailResponse,
    summary="Get detailed project data",
    description="Get complete project data including all generated artifacts and PV report. Only accessible by organization owners/admins. Access is logged for audit trail."
)
async def get_member_project_detail(
    request: Request,
    organization_id: str = Path(..., description="Organization ID"),
    project_id: str = Path(..., description="Project ID"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> MemberProjectDetailResponse:
    """
    Get detailed project data including all generated artifacts.
    
    This endpoint returns complete project information including:
    - All project data up to current progress
    - Linked PV report (if any)
    - Project owner information
    - Access audit log
    
    **Authorization:** Organization owner/admin only
    
    **Caching:** Results cached for 2 minutes (shorter TTL due to audit logging)
    
    **Audit:** All access is logged with timestamp and accessor information
    
    **Use case:** View complete project details when clicking on a specific project
    """
    try:
        # Verify admin is accessing their own organization
        user_tenant_id = admin_user.get("tenant_id")
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's projects"
            )
        
        # Check for cache bypass header
        skip_cache = request.headers.get("X-Skip-Cache", "").lower() == "true"
        
        # Generate cache key (includes user_id since audit log is user-specific)
        cache_key_data = f"project_detail:{organization_id}:{project_id}"
        cache_key = f"project_detail:{hashlib.md5(cache_key_data.encode()).hexdigest()}"
        
        # Try to get from cache (unless bypass requested)
        # Note: We still log access even on cache hits for audit purposes
        svc = get_async_org_service()

        if not skip_cache:
            try:
                cache_service = get_cache_service()
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for project detail: {project_id}")
                    # Log access even on cache hit for audit trail (async, non-blocking)
                    asyncio.create_task(
                        svc.log_project_access(
                            organization_id=organization_id,
                            accessed_by_user_id=admin_user["user_id"],
                            target_user_id=cached_result.get("owner", {}).get("user_id", "unknown"),
                            project_id=project_id,
                            access_type="view"
                        )
                    )
                    return MemberProjectDetailResponse(**cached_result)
            except Exception as cache_err:
                logger.warning(f"Cache read error: {cache_err}")

        # Get project detail using async service (includes audit logging)
        result = await svc.get_member_project_detail(
            organization_id=organization_id,
            project_id=project_id,
            accessed_by_user_id=admin_user["user_id"]
        )
        
        # Cache the result
        try:
            cache_service = get_cache_service()
            await cache_service.set(cache_key, result, ttl=PROJECT_DETAIL_CACHE_TTL)
            logger.debug(f"Cached project detail for project {project_id}")
        except Exception as cache_err:
            logger.warning(f"Cache write error: {cache_err}")
        
        return MemberProjectDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project detail for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project detail: {str(e)}"
        )


# ============================================================================
# Organization Owner Chat with Member Projects Endpoints
# ============================================================================

@router.post(
    "/{organization_id}/member-projects/{project_id}/chat/threads",
    response_model=OrgChatThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create chat thread for member project",
    description="Create a new chat thread for a member's project. Only accessible by organization owners/admins."
)
async def create_org_chat_thread(
    organization_id: str = Path(..., description="Organization ID"),
    project_id: str = Path(..., description="Project ID"),
    request: OrgChatCreateThreadRequest = None,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> OrgChatThreadResponse:
    """
    Create a new chat thread for an organization owner to chat with a member's project.
    
    This allows org owners/admins to have AI-assisted conversations about member projects
    using the same RAG-based chat functionality available to project owners.
    
    **Authorization:** Organization owner/admin only
    
    **Audit:** Thread creation is logged with org owner information
    """
    try:
        user_id = admin_user.get("user_id")
        user_tenant_id = admin_user.get("tenant_id")
        
        # Verify admin is accessing their own organization
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's projects"
            )
        
        # Validate project belongs to organization
        svc = get_async_org_service()
        is_valid, owner_info = await svc.validate_project_belongs_to_org(organization_id, project_id)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in this organization"
            )

        # Get the project's tenant_id for RAG to work correctly
        project_tenant_id = owner_info.get("tenant_id") if owner_info else None

        # Create thread using chat database adapter
        db_adapter = get_chat_database_adapter()

        thread = await db_adapter.create_org_owner_thread(
            project_id=project_id,
            project_tenant_id=project_tenant_id or "",
            org_owner_user_id=user_id or "",
            organization_id=organization_id,
            title=request.title if request else None,
            metadata=request.metadata if request else None
        )

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat thread"
            )

        # Log access for audit (async, non-blocking)
        asyncio.create_task(
            svc.log_project_access(
                organization_id=organization_id,
                accessed_by_user_id=user_id or "",
                target_user_id=owner_info.get("user_id", "unknown") if owner_info else "unknown",
                project_id=project_id,
                access_type="chat_thread_created"
            )
        )
        
        logger.info(f"✅ Org owner {user_id} created chat thread {thread.id} for project {project_id}")
        
        return OrgChatThreadResponse(
            id=thread.id,
            project_id=thread.project_id,
            title=thread.title,
            status=thread.status.value,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            last_message_at=thread.last_message_at,
            org_owner_access=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating org chat thread for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat thread: {str(e)}"
        )


@router.get(
    "/{organization_id}/member-projects/{project_id}/chat/threads",
    response_model=OrgChatThreadListResponse,
    summary="List chat threads for member project",
    description="List all chat threads created by org owner for a member's project."
)
async def list_org_chat_threads(
    organization_id: str = Path(..., description="Organization ID"),
    project_id: str = Path(..., description="Project ID"),
    limit: int = Query(20, ge=1, le=100, description="Max threads to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> OrgChatThreadListResponse:
    """
    List all chat threads created by organization owners for a specific member project.
    
    **Authorization:** Organization owner/admin only
    """
    try:
        user_tenant_id = admin_user.get("tenant_id")
        
        # Verify admin is accessing their own organization
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's projects"
            )
        
        # Validate project belongs to organization
        svc = get_async_org_service()
        is_valid, _ = await svc.validate_project_belongs_to_org(organization_id, project_id)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in this organization"
            )

        db_adapter = get_chat_database_adapter()

        threads, total_count = await db_adapter.list_org_owner_threads(
            project_id=project_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset
        )
        
        return OrgChatThreadListResponse(
            threads=[
                OrgChatThreadResponse(
                    id=t.id,
                    project_id=t.project_id,
                    title=t.title,
                    status=t.status.value,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                    last_message_at=t.last_message_at,
                    org_owner_access=True
                )
                for t in threads
            ],
            total_count=total_count,
            has_more=offset + len(threads) < total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing org chat threads for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chat threads: {str(e)}"
        )


@router.get(
    "/{organization_id}/chat/threads/{thread_id}",
    response_model=OrgChatThreadResponse,
    summary="Get chat thread details",
    description="Get details of a specific org owner chat thread."
)
async def get_org_chat_thread(
    organization_id: str = Path(..., description="Organization ID"),
    thread_id: str = Path(..., description="Thread ID"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> OrgChatThreadResponse:
    """
    Get details of a specific chat thread created by org owner.
    
    **Authorization:** Organization owner/admin only
    """
    try:
        user_tenant_id = admin_user.get("tenant_id")
        
        # Verify admin is accessing their own organization
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's chat threads"
            )
        
        db_adapter = get_chat_database_adapter()
        
        thread = await db_adapter.get_org_owner_thread(thread_id, organization_id)
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )
        
        # Get message count
        message_count = await db_adapter.get_message_count(thread_id)
        
        return OrgChatThreadResponse(
            id=thread.id,
            project_id=thread.project_id,
            title=thread.title,
            status=thread.status.value,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            last_message_at=thread.last_message_at,
            message_count=message_count,
            org_owner_access=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org chat thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat thread: {str(e)}"
        )


@router.post(
    "/{organization_id}/chat/threads/{thread_id}/messages",
    response_model=OrgChatAssistantResponse,
    summary="Post message to chat thread",
    description="Post a message to an org owner chat thread and get AI response."
)
async def post_org_chat_message(
    organization_id: str = Path(..., description="Organization ID"),
    thread_id: str = Path(..., description="Thread ID"),
    request: OrgChatPostMessageRequest = ...,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> OrgChatAssistantResponse:
    """
    Post a user message to an org owner chat thread and get the assistant's response.
    
    This triggers the full chat workflow:
    1. Load thread context
    2. Route intent
    3. Retrieve project evidence (RAG)
    4. Grade evidence sufficiency
    5. Web search if needed
    6. Compose answer with citations
    7. Update thread memory
    8. Persist messages
    
    **Authorization:** Organization owner/admin only
    
    **Audit:** All chat interactions are logged
    """
    try:
        user_id = admin_user.get("user_id")
        user_tenant_id = admin_user.get("tenant_id")
        
        # Verify admin is accessing their own organization
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's chat threads"
            )
        
        db_adapter = get_chat_database_adapter()
        
        # Verify thread exists and belongs to this organization
        thread = await db_adapter.get_org_owner_thread(thread_id, organization_id)
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )
        
        if thread.status != ThreadStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot post to archived or deleted thread"
            )
        
        logger.info(f"📨 Org owner {user_id} posting message to thread {thread_id}: {request.content[:50]}...")
        
        # Run the chat workflow using the project's tenant_id for RAG
        final_state = await run_chat_workflow(
            project_id=thread.project_id,
            thread_id=thread_id,
            user_id=user_id,
            tenant_id=thread.tenant_id,  # Use project's tenant for RAG
            user_message=request.content
        )
        
        # Check for errors
        if final_state.get("error"):
            logger.error(f"Workflow error at {final_state.get('error_stage')}: {final_state.get('error')}")
        
        # Get the messages we just created
        messages, _, _ = await db_adapter.get_messages(
            thread_id=thread_id,
            tenant_id=thread.tenant_id,
            limit=2,
            order="desc"
        )
        
        # Find user and assistant messages
        user_msg = None
        assistant_msg = None
        for msg in messages:
            if msg.role == MessageRole.USER and user_msg is None:
                user_msg = msg
            elif msg.role == MessageRole.ASSISTANT and assistant_msg is None:
                assistant_msg = msg
        
        if not user_msg or not assistant_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve messages"
            )
        
        # Convert citations to OrgChatCitation format
        citations = []
        for cit in final_state.get("citations", []):
            if isinstance(cit, dict):
                citations.append(OrgChatCitation(
                    id=cit.get("id", ""),
                    source_type=cit.get("source_type", "project"),
                    title=cit.get("title"),
                    content_preview=cit.get("content_preview"),
                    url=cit.get("url")
                ))
        
        # Log chat interaction for audit (async, non-blocking)
        svc = get_async_org_service()
        asyncio.create_task(
            svc.log_project_access(
                organization_id=organization_id,
                accessed_by_user_id=user_id or "",
                target_user_id=thread.metadata.get("accessed_by_user_id", "unknown") if thread.metadata else "unknown",
                project_id=thread.project_id,
                access_type="chat_message"
            )
        )
        
        return OrgChatAssistantResponse(
            user_message=OrgChatMessageResponse(
                id=user_msg.id,
                thread_id=user_msg.thread_id,
                role=user_msg.role.value,
                content=user_msg.content,
                citations=[],
                created_at=user_msg.created_at,
                metadata=user_msg.metadata
            ),
            assistant_message=OrgChatMessageResponse(
                id=assistant_msg.id,
                thread_id=assistant_msg.thread_id,
                role=assistant_msg.role.value,
                content=assistant_msg.content,
                citations=[
                    OrgChatCitation(
                        id=c.get("id", "") if isinstance(c, dict) else getattr(c, "id", ""),
                        source_type=c.get("source_type", "project") if isinstance(c, dict) else getattr(c, "source_type", "project"),
                        title=c.get("title") if isinstance(c, dict) else getattr(c, "title", None),
                        content_preview=c.get("content_preview") if isinstance(c, dict) else getattr(c, "content_preview", None),
                        url=c.get("url") if isinstance(c, dict) else getattr(c, "url", None)
                    )
                    for c in (assistant_msg.citations or [])
                ],
                created_at=assistant_msg.created_at,
                metadata=assistant_msg.metadata
            ),
            thread_id=thread_id,
            citations=citations,
            follow_ups=final_state.get("follow_ups", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting org chat message to thread {thread_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.get(
    "/{organization_id}/chat/threads/{thread_id}/messages",
    response_model=OrgChatMessageListResponse,
    summary="Get chat message history",
    description="Get paginated message history for an org owner chat thread."
)
async def get_org_chat_messages(
    organization_id: str = Path(..., description="Organization ID"),
    thread_id: str = Path(..., description="Thread ID"),
    limit: int = Query(50, ge=1, le=200, description="Max messages to return"),
    cursor: Optional[str] = Query(None, description="Message ID for pagination"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
) -> OrgChatMessageListResponse:
    """
    Get message history for an org owner chat thread with cursor-based pagination.
    
    **Authorization:** Organization owner/admin only
    """
    try:
        user_tenant_id = admin_user.get("tenant_id")
        
        # Verify admin is accessing their own organization
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's chat threads"
            )
        
        db_adapter = get_chat_database_adapter()
        
        messages, next_cursor, has_more = await db_adapter.get_org_owner_messages(
            thread_id=thread_id,
            organization_id=organization_id,
            limit=limit,
            cursor=cursor,
            order=order
        )
        
        return OrgChatMessageListResponse(
            messages=[
                OrgChatMessageResponse(
                    id=m.id,
                    thread_id=m.thread_id,
                    role=m.role.value if hasattr(m.role, 'value') else str(m.role),
                    content=m.content,
                    citations=[
                        OrgChatCitation(
                            id=c.get("id", "") if isinstance(c, dict) else getattr(c, "id", ""),
                            source_type=c.get("source_type", "project") if isinstance(c, dict) else getattr(c, "source_type", "project"),
                            title=c.get("title") if isinstance(c, dict) else getattr(c, "title", None),
                            content_preview=c.get("content_preview") if isinstance(c, dict) else getattr(c, "content_preview", None),
                            url=c.get("url") if isinstance(c, dict) else getattr(c, "url", None)
                        )
                        for c in (m.citations or [])
                    ] if m.citations else [],
                    created_at=m.created_at,
                    metadata=m.metadata
                )
                for m in messages
            ],
            has_more=has_more,
            next_cursor=next_cursor
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org chat messages for thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )


@router.delete(
    "/{organization_id}/chat/threads/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/archive chat thread",
    description="Archive or soft-delete an org owner chat thread."
)
async def delete_org_chat_thread(
    organization_id: str = Path(..., description="Organization ID"),
    thread_id: str = Path(..., description="Thread ID"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Archive (soft-delete) an org owner chat thread.
    
    **Authorization:** Organization owner/admin only
    """
    try:
        user_tenant_id = admin_user.get("tenant_id")
        
        # Verify admin is accessing their own organization
        if user_tenant_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own organization's chat threads"
            )
        
        db_adapter = get_chat_database_adapter()
        
        # Verify thread exists and belongs to this organization
        thread = await db_adapter.get_org_owner_thread(thread_id, organization_id)
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )
        
        # Soft delete using the project's tenant_id
        success = await db_adapter.update_thread_status(
            thread_id=thread_id,
            tenant_id=thread.tenant_id,
            status=ThreadStatus.DELETED
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete thread"
            )
        
        logger.info(f"✅ Org owner deleted chat thread {thread_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting org chat thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete thread: {str(e)}"
        )


# =============================================================================
# CREDIT REQUEST ENDPOINTS
# =============================================================================

@router.post(
    "/{organization_id}/credit-requests/team",
    summary="Create a team member credit request",
    description="Submit a credit request for a team member. The request goes to the org admin for approval."
)
async def create_team_member_credit_request(
    organization_id: str = Path(..., description="Organization ID"),
    request: TeamMemberCreditRequestCreate = None,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Create a credit request for a team member.

    OPTIMIZED: Uses async service.
    """
    try:
        user_id = current_user.get("user_id")

        svc = get_async_org_service()

        # Create the credit request with team_id
        result = await svc.create_credit_request(
            user_id=user_id,
            organization_id=organization_id,
            requested_amount=request.requested_amount,
            reason=request.reason,
            team_id=request.team_id,
        )

        return {
            "success": True,
            "message": "Team member credit request submitted successfully",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team member credit request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credit request: {str(e)}"
        )


@router.post(
    "/{organization_id}/credit-requests/individual",
    summary="Create an individual member credit request",
    description="Submit a credit request for an individual member. The request goes to the org admin for approval."
)
async def create_individual_member_credit_request(
    organization_id: str = Path(..., description="Organization ID"),
    request: IndividualMemberCreditRequestCreate = None,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Create a credit request for an individual member (not part of a team).

    OPTIMIZED: Uses async service.
    """
    try:
        user_id = current_user.get("user_id")

        svc = get_async_org_service()

        # Create the credit request without team_id (individual member)
        result = await svc.create_credit_request(
            user_id=user_id,
            organization_id=organization_id,
            requested_amount=request.requested_amount,
            reason=request.reason,
            team_id=None,  # Individual member - no team
        )

        return {
            "success": True,
            "message": "Individual member credit request submitted successfully",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating individual member credit request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credit request: {str(e)}"
        )


@router.get(
    "/{organization_id}/credit-requests",
    summary="List credit requests for organization",
    description="Get all credit requests for an organization. Org admins/owners only."
)
async def list_credit_requests(
    organization_id: str = Path(..., description="Organization ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, fulfilled"),
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    List all credit requests for an organization.

    OPTIMIZED: Uses async service with parallel user profile lookup.
    """
    try:
        svc = get_async_org_service()
        result = await svc.get_credit_requests_for_org(
            organization_id=organization_id,
            status_filter=status_filter,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing credit requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list credit requests: {str(e)}"
        )


@router.get(
    "/{organization_id}/credit-requests/my-requests",
    summary="Get my credit requests",
    description="Get credit requests for the current user in this organization."
)
async def get_my_credit_requests(
    organization_id: str = Path(..., description="Organization ID"),
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Get credit requests for the current user.

    OPTIMIZED: Uses async service.
    """
    try:
        user_id = current_user.get("user_id")
        svc = get_async_org_service()

        requests = await svc.get_user_credit_requests(
            user_id=user_id,
            organization_id=organization_id,
        )

        return {
            "requests": requests,
            "total_count": len(requests),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user credit requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credit requests: {str(e)}"
        )


@router.patch(
    "/{organization_id}/credit-requests/{request_id}",
    summary="Update credit request status",
    description="Approve or reject a credit request. Org admins/owners only."
)
async def update_credit_request(
    organization_id: str = Path(..., description="Organization ID"),
    request_id: str = Path(..., description="Credit request ID"),
    update_data: CreditRequestUpdate = None,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Update a credit request status (approve/reject).

    OPTIMIZED: Uses async service with automatic credit allocation on approval.
    """
    try:
        reviewer_id = admin_user.get("user_id")
        svc = get_async_org_service()

        result = await svc.update_credit_request(
            request_id=request_id,
            reviewer_id=reviewer_id,
            new_status=update_data.status,
            review_notes=update_data.review_notes,
        )

        return {
            "success": True,
            "message": f"Credit request {update_data.status}",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credit request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credit request: {str(e)}"
        )


@router.post(
    "/{organization_id}/request-credits-from-yuba",
    summary="Request credits from Yuba (grant orgs only)",
    description="Submit a credit request to Yuba admin (info@yubanow.com). Only available for grant organizations."
)
async def request_credits_from_yuba(
    organization_id: str = Path(..., description="Organization ID"),
    request: OrgAdminCreditRequestCreate = None,
    background_tasks: BackgroundTasks = None,
    admin_user: dict = Depends(get_global_admin_or_tenant_owner),
):
    """
    Request additional credits from Yuba admin.
    This endpoint sends an email to info@yubanow.com with the credit request.
    
    **ONLY available for grant organizations.**
    
    **Authorization:** Organization owner/admin only
    """
    import uuid

    try:
        svc = get_async_org_service()
        tenant_service = TenantService(use_service_role=True)

        # Check if organization is a grant organization
        org_type = await svc.get_org_type(organization_id)
        is_grant = org_type == "grant_org"

        if not is_grant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "not_grant_organization",
                    "message": "This feature is only available for grant organizations. Your organization type does not support requesting credits from Yuba."
                }
            )
        
        # Get organization details
        org_response = await tenant_service.get_tenant(tenant_id=organization_id)
        if not org_response.success:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org = org_response.data
        org_name = org.name
        org_email = getattr(org, "contact_email", None) or getattr(org, "email", None)
        
        # Get requester details
        requester_email = admin_user.get("email")
        requester_name = admin_user.get("full_name") or requester_email
        
        # Generate a reference ID
        reference_id = f"CR-{uuid.uuid4().hex[:8].upper()}"
        
        # Send email to info@yubanow.com
        background_tasks.add_task(
            _send_org_credit_request_email,
            org_id=organization_id,
            org_name=org_name,
            org_email=org_email,
            requester_name=requester_name,
            requester_email=requester_email,
            requested_amount=request.requested_amount,
            reason=request.reason,
            urgency=request.urgency,
            reference_id=reference_id,
        )
        
        logger.info(
            f"Credit request from Yuba submitted: org={org_name}, "
            f"amount={request.requested_amount}, ref={reference_id}"
        )
        
        return {
            "success": True,
            "message": "Your credit request has been submitted. The Yuba team will review your request and respond via email.",
            "request_reference": reference_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting credit request to Yuba: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit credit request: {str(e)}"
        )


def _send_org_credit_request_email(
    org_id: str,
    org_name: str,
    org_email: Optional[str],
    requester_name: str,
    requester_email: str,
    requested_amount: int,
    reason: str,
    urgency: str,
    reference_id: str,
):
    """Background task: Send credit request email to Yuba admin."""
    try:
        success = email_service.send_org_admin_credit_request_email(
            org_id=org_id,
            org_name=org_name,
            org_email=org_email,
            requester_name=requester_name,
            requester_email=requester_email,
            requested_amount=requested_amount,
            reason=reason,
            urgency=urgency,
            reference_id=reference_id,
        )
        
        if success:
            logger.info(f"Credit request email sent successfully: ref={reference_id}")
        else:
            logger.error(f"Failed to send credit request email: ref={reference_id}")
            
    except Exception as e:
        logger.error(f"Error sending credit request email: {e}")
