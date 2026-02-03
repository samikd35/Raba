"""
Tenant Management Module

This module provides comprehensive tenant management functionality for Individual, Team, and Organization types.
"""

from .simple_endpoints import router as tenant_router
# from .endpoints import router as tenant_router
# from .admin_endpoints import admin_router as admin_tenant_router
from .service import TenantService
from .models import (
    Tenant, TenantCreate, TenantUpdate, TenantResponse, TenantListResponse,
    TenantMembership, TenantMembershipCreate, TenantMembershipUpdate,
    TenantMembershipResponse, TenantMembershipListResponse,
    Group, GroupCreate, GroupUpdate, GroupResponse, GroupListResponse,
    TenantAnalytics, TenantAnalyticsResponse,
    TenantInvitation, TenantInvitationCreate, TenantInvitationResponse,
    TenantInvitationListResponse
)

__all__ = [
    # Routers
    "tenant_router",
    # "admin_tenant_router",
    
    # Service
    "TenantService",
    
    # Models
    "Tenant", "TenantCreate", "TenantUpdate", "TenantResponse", "TenantListResponse",
    "TenantMembership", "TenantMembershipCreate", "TenantMembershipUpdate",
    "TenantMembershipResponse", "TenantMembershipListResponse",
    "Group", "GroupCreate", "GroupUpdate", "GroupResponse", "GroupListResponse",
    "TenantAnalytics", "TenantAnalyticsResponse",
    "TenantInvitation", "TenantInvitationCreate", "TenantInvitationResponse",
    "TenantInvitationListResponse"
]
