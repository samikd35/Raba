import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from src.mint.utils.url_safe_serializer import (create_invite_token,
                                                verify_invite_token)

from ..auth_v2.async_service import get_async_auth_service
from ..auth_v2.utils import (get_current_user,
                             get_global_admin_or_tenant_admin,
                             get_global_admin_or_tenant_member,
                             get_super_admin_or_tenant_owner,
                             get_tenant_member)
from .models import (TeamCreateRequest, TeamIndResponse, TeamInviteRequest,
                     TeamInviteResponse, TeamJoinRequest,
                     TeamMembersListResponse, TeamResponse, TeamUpdateRequest)
from .async_service import get_async_team_service

load_dotenv()

logger = logging.getLogger(__name__)


teams_router = APIRouter(prefix="/api/teams", tags=["teams"])


@teams_router.get("/{organization_id}")
async def list_org_teams(
    organization_id: str,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """List all teams in an organization."""
    svc = get_async_team_service()
    return await svc.get_teams_by_org(organization_id)


@teams_router.post("/create", response_model=TeamIndResponse)
async def create_team(
    body: TeamCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    svc = get_async_team_service()
    try:
        team = await svc.create_team(user_id=current_user["user_id"], body=body.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not team:
        raise HTTPException(status_code=500, detail="Failed to create team")

    return TeamIndResponse(
        id=team["id"],
        name=team["name"],
        description=team.get("description"),
        website=team.get("website"),
        industry=team.get("industry"),
        size=team.get("size"),
        country=team.get("country"),
        settings=team.get("settings"),
        created_at=team.get("created_at"),
    )


@teams_router.post("/{organization_id}/create", response_model=TeamResponse)
async def create_team_tenant(
    organization_id: str,
    body: TeamCreateRequest,
    current_user: dict = Depends(get_tenant_member),
):
    svc = get_async_team_service()
    try:
        team = await svc.create_team_tenant(
            org_id=organization_id,
            user_id=current_user["user_id"],
            user_email=current_user["email"],
            body=body.dict(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not team:
        raise HTTPException(status_code=500, detail="Failed to create team")

    return TeamResponse(
        id=team["id"],
        organization_id=organization_id,
        name=team["name"],
        description=team.get("description"),
        website=team.get("website"),
        industry=team.get("industry"),
        size=team.get("size"),
        country=team.get("country"),
        settings=team.get("settings"),
        created_at=team.get("created_at"),
    )


@teams_router.patch("/{team_id}", response_model=TeamIndResponse)
async def update_team(
    team_id: str,
    body: TeamUpdateRequest,
    current_user: dict = Depends(get_global_admin_or_tenant_admin),
):
    """Update team details. Only provided fields will be updated."""
    svc = get_async_team_service()

    # Verify team exists
    team_check = await svc.get_team(team_id)
    if not team_check:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        updated_team = await svc.update_team(
            team_id=team_id, body=body.dict(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated_team:
        raise HTTPException(status_code=500, detail="Failed to update team")

    return TeamIndResponse(
        id=updated_team["id"],
        name=updated_team["name"],
        description=updated_team.get("description"),
        website=updated_team.get("website"),
        industry=updated_team.get("industry"),
        size=updated_team.get("size"),
        country=updated_team.get("country"),
        settings=updated_team.get("settings"),
        created_at=updated_team.get("created_at"),
    )


@teams_router.get("/{team_id}/invitations")
async def get_team_invitations(
    team_id: str,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """Get all invitations for a team"""
    svc = get_async_team_service()
    invitations = await svc.get_team_invitations(team_id)
    return {"invitations": invitations}


@teams_router.post("/{team_id}/invitations/{invitation_id}/resend")
async def resend_team_invitation(
    team_id: str,
    invitation_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """Resend a team invitation"""
    svc = get_async_team_service()
    auth_svc = get_async_auth_service()

    # Get invitation
    inv = await svc.get_invitation(invitation_id, team_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Fetch inviter's full name from database (async)
    inviter_id = inv.get("invited_by")
    inviter_name = None
    if inviter_id:
        try:
            inviter_profile = await auth_svc.get_user_by_id(inviter_id)
            inviter_name = inviter_profile.get("full_name") if inviter_profile else None
        except Exception as e:
            logger.warning(f"Failed to fetch inviter profile: {e}")

    # Fallback to invited_by_email or current user's email
    if not inviter_name:
        fallback_email = inv.get("invited_by_email") or current_user.get("email", "")
        inviter_name = fallback_email.split("@")[0] if fallback_email else "Team Admin"

    # Generate new token and link
    frontend_url = os.getenv("FRONTEND_URL", "")
    token = create_invite_token(team_id, inv["role"] == "admin")
    invite_link = f"{frontend_url}/invite/{token}?team_id={team_id}"

    # Reset status to queued
    await svc.update_invitation_status(invitation_id=invitation_id, status="queued")

    # Queue async email task
    logger.info(f"📧 Resending team invite email for {inv['email']}")
    background_tasks.add_task(
        svc.send_team_invite_and_update,
        invitation_id,
        inv["email"],
        team_id,
        invite_link,
        inviter_name,
    )

    return {"success": True, "message": f"Invitation resent to {inv['email']}"}


@teams_router.post("/{team_id}/invite", response_model=TeamInviteResponse)
async def invite_to_team(
    team_id: str,
    body: TeamInviteRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Invite users to a team.
    OPTIMIZED: Uses batch invitation recording instead of N+1 queries.
    """
    svc = get_async_team_service()
    auth_svc = get_async_auth_service()

    inviter_id = current_user["user_id"]
    inviter_email = current_user["email"]

    # Fetch inviter's full name (async)
    try:
        inviter_profile = await auth_svc.get_user_by_id(inviter_id)
        inviter_name = inviter_profile.get("full_name") if inviter_profile else None
        if not inviter_name:
            inviter_name = inviter_email.split("@")[0]
    except Exception as e:
        logger.warning(f"Failed to fetch inviter profile: {e}, using email as fallback")
        inviter_name = inviter_email.split("@")[0]

    frontend_url = os.getenv("FRONTEND_URL", "")
    unique_emails = list(set([e.strip().lower() for e in body.emails]))

    # Batch record all invitations (single query instead of N queries)
    try:
        recorded_invitations = await svc.record_invitations_batch(
            team_id=team_id,
            emails=unique_emails,
            is_admin=body.is_admin,
            invited_by=inviter_id,
            invited_by_email=inviter_email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch invitation recording failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create invitations: {str(e)}")

    # Queue email tasks for all recorded invitations
    invitation_ids = []
    for inv in recorded_invitations:
        inv_id = inv.get("id")
        inv_email = inv.get("email")
        if inv_id and inv_email:
            token = create_invite_token(team_id, body.is_admin)
            invite_link = f"{frontend_url}/invite/{token}?team_id={team_id}"
            background_tasks.add_task(
                svc.send_team_invite_and_update,
                inv_id,
                inv_email,
                team_id,
                invite_link,
                inviter_name,
            )
            invitation_ids.append(inv_id)

    logger.info(f"✅ Queued {len(invitation_ids)} team invites for team {team_id}")

    return TeamInviteResponse(
        success=True,
        message=f"{len(invitation_ids)} invites queued",
        invitations=invitation_ids,
    )


@teams_router.post("/{team_id}/join")
async def join_team(
    team_id: str,
    body: TeamJoinRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Join a team (supports both organization-associated and independent teams).
    Role is determined from the invite token.
    OPTIMIZED: Uses combined eligibility check instead of sequential queries.
    """
    svc = get_async_team_service()
    data = verify_invite_token(body.invite_token, team_id)
    requested_role = "admin" if data.get("is_admin") else "member"

    # Check org link and membership in optimized call
    eligibility = await svc.check_team_join_eligibility(team_id, current_user["user_id"])
    org_id = eligibility["org_id"]

    # If team is org-associated, ensure user is member of parent organization
    if org_id and not eligibility["is_org_member"]:
        logger.info(
            f"👤 User {current_user['email']} not in organization, adding them first"
        )
        try:
            await svc.add_org_membership(org_id, current_user["user_id"])
            logger.info(f"✅ Added {current_user['email']} to organization {org_id}")
        except Exception as e:
            logger.error(f"❌ Failed to add user to organization: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to add user to organization"
            )
    elif not org_id:
        logger.info(
            f"👤 User {current_user['email']} joining independent team {team_id}"
        )

    # Add user to team (works for both org-associated and independent teams)
    membership = await svc.add_or_update_team_membership(
        team_id, current_user["user_id"], current_user["email"], requested_role
    )
    if not membership:
        raise HTTPException(status_code=500, detail="Failed to join team")

    return {
        "team_id": team_id,
        "organization_id": org_id,  # None for independent teams
        "role": membership["role"],
        "permissions": membership.get("permissions"),
        "joined_at": membership.get("joined_at"),
    }


@teams_router.get("/{team_id}/details")
async def get_team_details(
    team_id: str,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Get detailed information about a team including name, organization, credits, etc.
    OPTIMIZED: Uses parallel async queries instead of sequential.
    """
    svc = get_async_team_service()
    try:
        return await svc.get_team_details(team_id, current_user["user_id"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in get_team_details: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=400, detail=str(e))


@teams_router.get("/{team_id}/metrics")
async def get_team_metrics(
    team_id: str,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """Get invitations and membership metrics for a team."""
    svc = get_async_team_service()
    try:
        return await svc.get_team_metrics(team_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@teams_router.get("/{team_id}/members", response_model=TeamMembersListResponse)
async def get_team_members(
    team_id: str,
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Get all members of a team.
    Returns a list of team members with their details.
    """
    svc = get_async_team_service()
    try:
        members = await svc.get_team_members(team_id)
        return TeamMembersListResponse(members=members, total=len(members))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@teams_router.delete("/{team_id}/members/{user_id}")
async def delete_team_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(get_global_admin_or_tenant_admin),
):
    """
    Remove a member from a team.
    Team admins and owners can remove members (except the owner).
    """
    svc = get_async_team_service()

    try:
        result = await svc.delete_team_member(
            team_id=team_id,
            user_id=user_id,
            admin_user_id=current_user["user_id"]
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing team member: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@teams_router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    current_user: dict = Depends(get_super_admin_or_tenant_owner),
):
    """
    Delete a team tenant and its related data.
    Only the team owner can perform this action.
    """
    svc = get_async_team_service()

    deleted = await svc.delete_team_tenant(
        team_id=team_id, user_id=current_user["user_id"]
    )
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete team")

    return {"success": True, "message": "Team deleted successfully"}
