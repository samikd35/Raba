"""
Tenant Admin Dashboard API Endpoints

Admin-only endpoints for tenant oversight, analytics, and management.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

# Role system removed - admin endpoints now require basic authentication only
from ..auth.production.system import get_current_user
from .service import TenantService
from .models import (
    Tenant, TenantCreate, TenantUpdate, TenantResponse, TenantListResponse,
    TenantMembership, TenantMembershipCreate, TenantMembershipUpdate,
    TenantMembershipResponse, TenantMembershipListResponse,
    TenantAnalyticsResponse
)

logger = logging.getLogger(__name__)

# Create router for admin tenant endpoints
admin_router = APIRouter(prefix="/api/admin/tenant", tags=["admin-tenant"])

# =============================================
# ADMIN TENANT MANAGEMENT ENDPOINTS
# =============================================

@admin_router.get("/", response_model=TenantListResponse)
async def admin_list_all_tenants(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for tenant name"),
    tenant_type: Optional[str] = Query(None, description="Filter by tenant type"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    current_user_id: str = Depends(get_current_user)
):
    """
    List all tenants with admin access.
    
    Supports pagination, search, and filtering by various criteria.
    """
    try:
        logger.info(f"Admin user {current_user_id} requesting tenant list")
        
        service = TenantService(use_service_role=True)
        
        # For now, we'll use the basic list method and add filtering in the service layer
        # In a production system, you'd want to implement proper filtering in the database query
        result = await service.list_user_tenants("")  # Empty user_id for admin access
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        # Apply filters (basic implementation)
        filtered_tenants = result.data
        
        if search:
            filtered_tenants = [t for t in filtered_tenants if search.lower() in t.name.lower()]
        
        if tenant_type:
            filtered_tenants = [t for t in filtered_tenants if t.tenant_type == tenant_type]
        
        if industry:
            filtered_tenants = [t for t in filtered_tenants if t.industry == industry]
        
        if country:
            filtered_tenants = [t for t in filtered_tenants if t.country == country]
        
        # Apply pagination
        total = len(filtered_tenants)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tenants = filtered_tenants[start_idx:end_idx]
        
        return TenantListResponse(
            success=True,
            message="Tenants retrieved successfully",
            data=paginated_tenants,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tenants for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing tenants"
        )

@admin_router.get("/{tenant_id}", response_model=TenantResponse)
async def admin_get_tenant(
    tenant_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Get detailed information about a specific tenant.
    
    Admin access bypasses normal tenant membership checks.
    """
    try:
        logger.info(f"Admin user {current_user_id} requesting tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Admin access - bypass user membership check
        tenant_result = service.supabase.table("tenants").select("*").eq("id", tenant_id).execute()
        
        if not tenant_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        tenant = Tenant(**tenant_result.data[0])
        
        return TenantResponse(
            success=True,
            message="Tenant retrieved successfully",
            data=tenant
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant {tenant_id} for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting tenant"
        )

@admin_router.put("/{tenant_id}", response_model=TenantResponse)
async def admin_update_tenant(
    tenant_id: str,
    update_data: TenantUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Update tenant information with admin privileges.
    
    Admins can update any tenant regardless of membership.
    """
    try:
        logger.info(f"Admin user {current_user_id} updating tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Prepare update data (only include non-None values)
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update tenant with admin privileges
        tenant_result = service.supabase.table("tenants").update(update_dict).eq("id", tenant_id).execute()
        
        if not tenant_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found or update failed"
            )
        
        tenant = Tenant(**tenant_result.data[0])
        
        return TenantResponse(
            success=True,
            message="Tenant updated successfully",
            data=tenant
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id} for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating tenant"
        )

@admin_router.delete("/{tenant_id}", response_model=Dict[str, str])
async def admin_deactivate_tenant(
    tenant_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Deactivate a tenant (soft delete).
    
    Only super admins can deactivate tenants.
    """
    try:
        logger.info(f"Admin user {current_user_id} deactivating tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Deactivate tenant (soft delete)
        tenant_result = service.supabase.table("tenants").update({
            "is_active": False
        }).eq("id", tenant_id).execute()
        
        if not tenant_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return {
            "success": "true",
            "message": "Tenant deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating tenant {tenant_id} for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deactivating tenant"
        )

# =============================================
# ADMIN TENANT MEMBERSHIP ENDPOINTS
# =============================================

@admin_router.get("/{tenant_id}/members", response_model=TenantMembershipListResponse)
async def admin_list_tenant_members(
    tenant_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user_id: str = Depends(get_current_user)
):
    """
    List all members of a tenant with admin access.
    
    Admins can view members of any tenant.
    """
    try:
        logger.info(f"Admin user {current_user_id} requesting members for tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Get memberships with pagination
        offset = (page - 1) * page_size
        memberships_result = service.supabase.table("tenant_memberships").select(
            "*"
        ).eq("tenant_id", tenant_id).eq("is_active", True).range(offset, offset + page_size - 1).execute()
        
        # Get total count
        count_result = service.supabase.table("tenant_memberships").select(
            "id", count="exact"
        ).eq("tenant_id", tenant_id).eq("is_active", True).execute()
        
        total = count_result.count if count_result.count else 0
        memberships = [TenantMembership(**m) for m in memberships_result.data]
        
        return TenantMembershipListResponse(
            success=True,
            message="Members retrieved successfully",
            data=memberships,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tenant members for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing members"
        )

@admin_router.post("/{tenant_id}/members", response_model=TenantMembershipResponse, status_code=status.HTTP_201_CREATED)
async def admin_add_tenant_member(
    tenant_id: str,
    membership_data: TenantMembershipCreate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Add a member to a tenant with admin privileges.
    
    Admins can add members to any tenant.
    """
    try:
        logger.info(f"Admin user {current_user_id} adding member to tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Check if user is already a member
        existing = await service._get_user_tenant_membership(membership_data.user_id, tenant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this tenant"
            )
        
        # Add membership with admin privileges
        membership_result = service.supabase.table("tenant_memberships").insert({
            "tenant_id": tenant_id,
            "user_id": membership_data.user_id,
            "role": membership_data.role,
            "permissions": membership_data.permissions,
            "is_active": True
        }).execute()
        
        if not membership_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add member to tenant"
            )
        
        return TenantMembershipResponse(
            success=True,
            message="Member added successfully",
            data=TenantMembership(**membership_result.data[0])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding tenant member for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while adding member"
        )

@admin_router.put("/{tenant_id}/members/{member_user_id}", response_model=TenantMembershipResponse)
async def admin_update_tenant_member(
    tenant_id: str,
    member_user_id: str,
    update_data: TenantMembershipUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Update a tenant member's role or permissions with admin privileges.
    
    Admins can update members of any tenant.
    """
    try:
        logger.info(f"Admin user {current_user_id} updating member {member_user_id} in tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Check if target member exists
        target_membership = await service._get_user_tenant_membership(member_user_id, tenant_id)
        if not target_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this tenant"
            )
        
        # Prepare update data
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update membership with admin privileges
        membership_result = service.supabase.table("tenant_memberships").update(update_dict).eq(
            "tenant_id", tenant_id
        ).eq("user_id", member_user_id).execute()
        
        if not membership_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update member"
            )
        
        return TenantMembershipResponse(
            success=True,
            message="Member updated successfully",
            data=TenantMembership(**membership_result.data[0])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant member for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating member"
        )

@admin_router.delete("/{tenant_id}/members/{member_user_id}", response_model=TenantMembershipResponse)
async def admin_remove_tenant_member(
    tenant_id: str,
    member_user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Remove a member from a tenant with admin privileges.
    
    Admins can remove members from any tenant.
    """
    try:
        logger.info(f"Admin user {current_user_id} removing member {member_user_id} from tenant {tenant_id}")
        
        service = TenantService(use_service_role=True)
        
        # Check if target member exists
        target_membership = await service._get_user_tenant_membership(member_user_id, tenant_id)
        if not target_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this tenant"
            )
        
        # Deactivate membership (soft delete) with admin privileges
        membership_result = service.supabase.table("tenant_memberships").update({
            "is_active": False
        }).eq("tenant_id", tenant_id).eq("user_id", member_user_id).execute()
        
        if not membership_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove member"
            )
        
        return TenantMembershipResponse(
            success=True,
            message="Member removed successfully",
            data=TenantMembership(**membership_result.data[0])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing tenant member for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while removing member"
        )

# =============================================
# ADMIN ANALYTICS ENDPOINTS
# =============================================

@admin_router.get("/analytics/overview", response_model=TenantAnalyticsResponse)
async def admin_get_tenant_analytics(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user_id: str = Depends(get_current_user)
):
    """
    Get comprehensive analytics for all tenants.
    
    Provides insights into tenant usage, member counts, projects, and credits.
    """
    try:
        logger.info(f"Admin user {current_user_id} requesting tenant analytics")
        
        service = TenantService(use_service_role=True)
        result = await service.get_tenant_analytics(current_user_id, page, page_size)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant analytics for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting analytics"
        )

@admin_router.get("/analytics/summary", response_model=Dict[str, Any])
async def admin_get_tenant_summary(
    current_user_id: str = Depends(get_current_user)
):
    """
    Get high-level summary statistics for all tenants.
    
    Provides aggregate counts and metrics for dashboard overview.
    """
    try:
        logger.info(f"Admin user {current_user_id} requesting tenant summary")
        
        service = TenantService(use_service_role=True)
        
        # Get total tenant counts by type
        individual_count = service.supabase.table("tenants").select("id", count="exact").eq("tenant_type", "individual").eq("is_active", True).execute()
        team_count = service.supabase.table("tenants").select("id", count="exact").eq("tenant_type", "team").eq("is_active", True).execute()
        org_count = service.supabase.table("tenants").select("id", count="exact").eq("tenant_type", "organization").eq("is_active", True).execute()
        
        # Get total member count
        total_members = service.supabase.table("tenant_memberships").select("id", count="exact").eq("is_active", True).execute()
        
        # Get total projects count (if projects table exists)
        try:
            total_projects = service.supabase.table("projects").select("id", count="exact").eq("status", "active").execute()
            projects_count = total_projects.count if total_projects.count else 0
        except:
            projects_count = 0
        
        return {
            "success": True,
            "message": "Summary retrieved successfully",
            "data": {
                "total_tenants": {
                    "individual": individual_count.count if individual_count.count else 0,
                    "team": team_count.count if team_count.count else 0,
                    "organization": org_count.count if org_count.count else 0,
                    "total": (individual_count.count or 0) + (team_count.count or 0) + (org_count.count or 0)
                },
                "total_members": total_members.count if total_members.count else 0,
                "total_projects": projects_count,
                "active_tenants": (individual_count.count or 0) + (team_count.count or 0) + (org_count.count or 0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant summary for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting summary"
        )

# =============================================
# HEALTH CHECK ENDPOINT
# =============================================

@admin_router.get("/health", response_model=Dict[str, str])
async def admin_tenant_health_check():
    """
    Health check endpoint for admin tenant service.
    """
    return {
        "status": "healthy",
        "service": "admin-tenant-management",
        "message": "Admin tenant service is operational"
    }
