"""
Invitation validation endpoints
Handles server-side token validation for invitation links
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.mint.utils.url_safe_serializer import verify_invite_token
import logging

logger = logging.getLogger(__name__)

invitations_router = APIRouter(prefix="/api/invitations", tags=["invitations"])


class InvitationValidateRequest(BaseModel):
    token: str
    org_id: Optional[str] = None
    team_id: Optional[str] = None


class InvitationValidateResponse(BaseModel):
    tenant_id: str
    is_admin: bool
    credits: int
    is_team_leader: bool
    valid: bool
    org_name: Optional[str] = None  # Organization/Team name for display


@invitations_router.post("/test-token")
async def test_token_creation():
    """
    Test endpoint to verify token creation and validation works properly.
    This helps debug token expiration issues.
    """
    try:
        from src.mint.utils.url_safe_serializer import create_invite_token, verify_invite_token
        
        # Create a test token
        test_tenant_id = "test-tenant-123"
        test_token = create_invite_token(
            tenant_id=test_tenant_id,
            is_admin=False,
            credit=100,
            is_team_leader=True
        )
        
        # Immediately try to validate it
        validated_data = verify_invite_token(test_token, test_tenant_id)
        
        return {
            "success": True,
            "token_created": test_token,
            "token_validated": validated_data,
            "message": "Token creation and validation working properly"
        }
        
    except Exception as e:
        logger.error(f"Token test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Token system has issues"
        }


@invitations_router.post("/fix-existing-team-leader-invite")
async def fix_existing_team_leader_invite():
    """
    Fix the existing invitation to set is_team_leader=True
    """
    try:
        from supabase import create_client
        import os
        
        # Create supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        # Update the most recent invitation for samuel.weyesa35@gmail.com
        update_result = (
            supabase.table("organization_invitations")
            .update({"is_team_leader": True})
            .eq("id", "4e3d2414-fab0-4efc-a509-95cb7d9fdf1d")  # The most recent invitation ID
            .execute()
        )
        
        logger.info(f"🔍 FIXING: Update result: {update_result.data}")
        
        # Query it back to confirm
        query_result = (
            supabase.table("organization_invitations")
            .select("*")
            .eq("id", "4e3d2414-fab0-4efc-a509-95cb7d9fdf1d")
            .execute()
        )
        
        logger.info(f"🔍 FIXING: Updated record: {query_result.data}")
        
        return {
            "success": True,
            "message": "Fixed existing invitation to set is_team_leader=True",
            "updated_record": query_result.data[0] if query_result.data else None
        }
        
    except Exception as e:
        logger.error(f"Failed to fix invitation: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@invitations_router.get("/debug/{org_id}/{email}")
async def debug_team_leader_invitation(org_id: str, email: str):
    """
    Debug endpoint to check team leader invitation status in database
    """
    try:
        from supabase import create_client
        import os
        
        # Create supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        # Query all invitations for this user and org
        all_invites = supabase.table("organization_invitations").select("*").eq("organization_id", org_id).eq("email", email.strip()).execute()
        
        # Query specifically team leader invitations
        team_leader_invites = (
            supabase.table("organization_invitations")
            .select("*")
            .eq("organization_id", org_id)
            .eq("email", email.strip())
            .eq("is_team_leader", True)
            .execute()
        )
        
        return {
            "org_id": org_id,
            "email": email,
            "all_invitations": all_invites.data,
            "team_leader_invitations": team_leader_invites.data,
            "team_leader_count": len(team_leader_invites.data),
            "has_team_leader_invite": len(team_leader_invites.data) > 0
        }
        
    except Exception as e:
        logger.error(f"Debug query failed: {str(e)}")
        return {
            "error": str(e),
            "org_id": org_id,
            "email": email
        }


@invitations_router.post("/validate", response_model=InvitationValidateResponse)
async def validate_invitation_token(request: InvitationValidateRequest):
    """
    Validate an invitation token and return its decoded contents.
    This endpoint handles both organization and team invitation tokens.
    """
    try:
        # Determine which tenant_id to validate against
        tenant_id = request.team_id or request.org_id
        
        if not tenant_id:
            raise HTTPException(
                status_code=400, 
                detail="Either org_id or team_id must be provided"
            )

        # Validate the token using the backend serializer
        token_data = verify_invite_token(request.token, tenant_id)
        
        logger.info(f"Token validated successfully for tenant {tenant_id}")
        
        # Fetch tenant name for display
        tenant_name = ""
        try:
            from src.mint.api.tenant.service import TenantService
            tenant_service = TenantService(use_service_role=True)
            tenant_result = await tenant_service.get_tenant(tenant_id=tenant_id)
            if tenant_result.success and tenant_result.data:
                # tenant_result.data is a Tenant object, access name attribute directly
                tenant_name = getattr(tenant_result.data, 'name', '') or tenant_result.data.get('name', '') if isinstance(tenant_result.data, dict) else ''
        except Exception as e:
            logger.warning(f"Could not fetch tenant name: {e}")
            tenant_name = ""
        
        return InvitationValidateResponse(
            tenant_id=token_data.get("tenant_id", ""),
            is_admin=token_data.get("is_admin", False),
            credits=token_data.get("credits") or 0,  # Ensure it's never None
            is_team_leader=token_data.get("is_team_leader", False),
            valid=True,
            org_name=tenant_name  # Add organization name
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (from verify_invite_token)
        logger.warning(f"Token validation failed: {e.detail}")
        raise e
        
    except Exception as e:
        logger.error(f"Unexpected error validating token: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid invitation token"
        )
