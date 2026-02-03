"""
Tenant Management API Endpoints

REST API endpoints for tenant management operations including Individual, Team, and Organization types.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status

# Import will be done at runtime to avoid circular imports
from .service import TenantService
from .models import (
    TenantCreate, TenantUpdate, TenantResponse, TenantListResponse,
    TenantMembershipCreate, TenantMembershipUpdate,
    TenantMembershipResponse, TenantMembershipListResponse
)

logger = logging.getLogger(__name__)

# Create router for tenant endpoints
router = APIRouter(prefix="/api/v1/tenant", tags=["tenant"])

# =============================================
# TENANT CRUD ENDPOINTS
# =============================================

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: Dict[str, Any] = Depends(lambda: None)  # Will be replaced at runtime
):
    """
    Create a new tenant (Individual, Team, or Organization).
    
    The current user becomes the owner of the created tenant.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=True)
        result = await service.create_tenant(tenant_data, user_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating tenant"
        )

@router.get("/", response_model=TenantListResponse)
async def list_user_tenants(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all tenants that the current user belongs to.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.list_user_tenants(user_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing user tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing tenants"
        )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get tenant details by ID.
    
    User must be a member of the tenant to access its details.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.get_tenant(tenant_id, user_id)
        
        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.message
                )
            elif "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting tenant"
        )

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update tenant information.
    
    Only tenant owners and admins can update tenant details.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.update_tenant(tenant_id, user_id, update_data)
        
        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.message
                )
            elif "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating tenant"
        )

# =============================================
# TENANT MEMBERSHIP ENDPOINTS
# =============================================

@router.post("/{tenant_id}/members", response_model=TenantMembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_tenant_member(
    tenant_id: str,
    membership_data: TenantMembershipCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add a member to a tenant.
    
    Only tenant owners and admins can add members.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=True)
        result = await service.add_tenant_member(tenant_id, user_id, membership_data)
        
        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding tenant member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while adding member"
        )

@router.get("/{tenant_id}/members", response_model=TenantMembershipListResponse)
async def list_tenant_members(
    tenant_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all members of a tenant.
    
    User must be a member of the tenant to view its members.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.list_tenant_members(tenant_id, user_id, page, page_size)
        
        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tenant members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing members"
        )

@router.put("/{tenant_id}/members/{member_user_id}", response_model=TenantMembershipResponse)
async def update_tenant_member(
    tenant_id: str,
    member_user_id: str,
    update_data: TenantMembershipUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a tenant member's role or permissions.
    
    Only tenant owners and admins can update member details.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=True)
        result = await service.update_tenant_member(tenant_id, member_user_id, user_id, update_data)
        
        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.message
                )
            elif "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating member"
        )

@router.delete("/{tenant_id}/members/{member_user_id}", response_model=TenantMembershipResponse)
async def remove_tenant_member(
    tenant_id: str,
    member_user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Remove a member from a tenant.
    
    Only tenant owners and admins can remove members.
    Cannot remove the last owner of a tenant.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=True)
        result = await service.remove_tenant_member(tenant_id, member_user_id, user_id)
        
        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.message
                )
            elif "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing tenant member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while removing member"
        )

# =============================================
# TENANT TYPE SPECIFIC ENDPOINTS
# =============================================

@router.get("/types/individual", response_model=TenantListResponse)
async def list_individual_tenants(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all individual tenants that the current user belongs to.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.list_user_tenants(user_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        # Filter for individual tenants only
        individual_tenants = [t for t in result.data if t.tenant_type == "individual"]
        
        return TenantListResponse(
            success=True,
            message="Individual tenants retrieved successfully",
            data=individual_tenants,
            total=len(individual_tenants),
            page=1,
            page_size=len(individual_tenants)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing individual tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing individual tenants"
        )

@router.get("/types/team", response_model=TenantListResponse)
async def list_team_tenants(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all team tenants that the current user belongs to.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.list_user_tenants(user_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        # Filter for team tenants only
        team_tenants = [t for t in result.data if t.tenant_type == "team"]
        
        return TenantListResponse(
            success=True,
            message="Team tenants retrieved successfully",
            data=team_tenants,
            total=len(team_tenants),
            page=1,
            page_size=len(team_tenants)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing team tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing team tenants"
        )

@router.get("/types/organization", response_model=TenantListResponse)
async def list_organization_tenants(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all organization tenants that the current user belongs to.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        service = TenantService(use_service_role=False)
        result = await service.list_user_tenants(user_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        # Filter for organization tenants only
        org_tenants = [t for t in result.data if t.tenant_type == "organization"]
        
        return TenantListResponse(
            success=True,
            message="Organization tenants retrieved successfully",
            data=org_tenants,
            total=len(org_tenants),
            page=1,
            page_size=len(org_tenants)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing organization tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing organization tenants"
        )

# =============================================
# HEALTH CHECK ENDPOINT
# =============================================

@router.get("/health", response_model=Dict[str, str])
async def tenant_health_check():
    """
    Health check endpoint for tenant service.
    """
    return {
        "status": "healthy",
        "service": "tenant-management",
        "message": "Tenant service is operational"
    }
