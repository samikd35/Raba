"""
Tenant Management Service

Business logic layer for tenant management operations including Individual, Team, and Organization types.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

from ..system.core.supabase_client import get_supabase_client
from .models import (
    Tenant,
    TenantAnalytics,
    TenantAnalyticsResponse,
    TenantCreate,
    TenantListResponse,
    TenantMembership,
    TenantMembershipCreate,
    TenantMembershipListResponse,
    TenantMembershipResponse,
    TenantMembershipUpdate,
    TenantResponse,
    TenantUpdate,
)

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant management operations"""

    def __init__(self, use_service_role: bool = True):
        """Initialize tenant service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role)
        self.use_service_role = use_service_role

    # =============================================
    # TENANT CRUD OPERATIONS
    # =============================================

    async def create_tenant(
        self, tenant_data: TenantCreate, owner_user_id: str
    ) -> TenantResponse:
        """Create a new tenant with the specified owner"""
        try:
            logger.info(
                f"Creating tenant: {tenant_data.name} (type: {tenant_data.tenant_type})"
            )

            # Create tenant
            tenant_result = (
                self.supabase.client.table("tenants")
                .insert(
                    {
                        "name": tenant_data.name,
                        "tenant_type": tenant_data.tenant_type,  # Use the actual tenant_type from request
                        "description": tenant_data.description,
                        "website": tenant_data.website,
                        "industry": tenant_data.industry,
                        "size": tenant_data.size,
                        "country": tenant_data.country,
                        "settings": tenant_data.settings,
                        "is_active": True,
                    }
                )
                .execute()
            )

            if not tenant_result.data:
                raise Exception("Failed to create tenant")

            tenant = tenant_result.data[0]
            tenant_id = tenant["id"]

            # Create owner membership
            membership_result = (
                self.supabase.client.table("tenant_memberships")
                .insert(
                    {
                        "tenant_id": tenant_id,
                        "user_id": owner_user_id,
                        "role": "owner",
                        "is_active": True,
                        "permissions": self._get_default_permissions("owner"),
                    }
                )
                .execute()
            )

            if not membership_result.data:
                # Rollback tenant creation
                self.supabase.client.table("tenants").delete().eq(
                    "id", tenant_id
                ).execute()
                raise Exception("Failed to create owner membership")

            logger.info(
                f"Successfully created tenant {tenant_id} with owner {owner_user_id}"
            )

            return TenantResponse(
                success=True,
                message="Tenant created successfully",
                data=Tenant(**tenant),
            )

        except Exception as e:
            logger.error(f"Error creating tenant: {str(e)}")
            return TenantResponse(
                success=False, message=f"Failed to create tenant: {str(e)}", data=None
            )

    async def get_admin_org_tenant(
        self, tenant_id: str, user_id: str
    ) -> TenantResponse:
        """Get tenant by ID (with access control)"""
        try:
            # Check if user has access to this tenant
            membership = await self._get_user_tenant_membership(user_id, tenant_id)
            if not membership:
                return TenantResponse(
                    success=False,
                    message="Access denied: User is not a member of this tenant",
                    data=None,
                )

            if membership["role"] not in ["admin", "owner"]:
                return TenantResponse(
                    success=False,
                    message="Access denied: User is not admin of this organization",
                    data=None,
                )

            # Get tenant data
            tenant_result = (
                self.supabase.client.table("tenants")
                .select("*")
                .eq("id", tenant_id)
                .execute()
            )

            if (
                not tenant_result.data
                or tenant_result.data[0]["tenant_type"] != "organization"
            ):
                return TenantResponse(
                    success=False, message="Organization not found", data=None
                )

            return TenantResponse(
                success=True,
                message="Tenant retrieved successfully",
                data=Tenant(**tenant_result.data[0]),
            )

        except Exception as e:
            logger.error(f"Error getting tenant {tenant_id}: {str(e)}")
            return TenantResponse(
                success=False, message=f"Failed to get tenant: {str(e)}", data=None
            )

    async def get_tenant(self, tenant_id: str) -> TenantResponse:
        """Get tenant by ID (with access control)"""
        try:
            # Get tenant data
            tenant_result = (
                self.supabase.client.table("tenants")
                .select("*")
                .eq("id", tenant_id)
                .execute()
            )

            if not tenant_result.data:
                return TenantResponse(
                    success=False, message="Tenant not found", data=None
                )

            return TenantResponse(
                success=True,
                message="Tenant retrieved successfully",
                data=Tenant(**tenant_result.data[0]),
            )

        except Exception as e:
            logger.error(f"Error getting tenant {tenant_id}: {str(e)}")
            return TenantResponse(
                success=False, message=f"Failed to get tenant: {str(e)}", data=None
            )

    async def update_tenant(
        self, tenant_id: str, user_id: str, update_data: TenantUpdate
    ) -> TenantResponse:
        """Update tenant information (admin/owner only)"""
        try:
            # Prepare update data (only include non-None values)
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

            if not update_dict:
                return TenantResponse(
                    success=False, message="No valid fields to update", data=None
                )

            # Update tenant
            tenant_result = (
                self.supabase.client.table("tenants")
                .update(update_dict)
                .eq("id", tenant_id)
                .execute()
            )

            if not tenant_result.data:
                return TenantResponse(
                    success=False,
                    message="Tenant not found or update failed",
                    data=None,
                )

            return TenantResponse(
                success=True,
                message="Tenant updated successfully",
                data=Tenant(**tenant_result.data[0]),
            )

        except Exception as e:
            logger.error(f"Error updating tenant {tenant_id}: {str(e)}")
            return TenantResponse(
                success=False, message=f"Failed to update tenant: {str(e)}", data=None
            )

    async def list_user_tenants(self, user_id: str) -> TenantListResponse:
        """List all tenants that a user belongs to"""
        try:
            # Get user's tenant memberships
            memberships_result = (
                self.supabase.client.table("tenant_memberships")
                .select("tenant_id, role, joined_at, is_active")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )

            print("----------------------------------")
            print(memberships_result)
            print("----------------------------------")

            if not memberships_result.data:
                return TenantListResponse(
                    success=True,
                    message="No tenants found",
                    data=[],
                    total=0,
                    page=1,
                    page_size=20,
                )

            # Get tenant details for each membership
            tenant_ids = [m["tenant_id"] for m in memberships_result.data]
            tenants_result = (
                self.supabase.client.table("tenants")
                .select("*")
                .in_("id", tenant_ids)
                .execute()
            )

            tenants = [Tenant(**tenant) for tenant in tenants_result.data]

            return TenantListResponse(
                success=True,
                message="Tenants retrieved successfully",
                data=tenants,
                total=len(tenants),
                page=1,
                page_size=len(tenants),
            )

        except Exception as e:
            logger.error(f"Error listing user tenants: {str(e)}")
            return TenantListResponse(
                success=False,
                message=f"Failed to list tenants: {str(e)}",
                data=[],
                total=0,
                page=1,
                page_size=20,
            )

    # =============================================
    # TENANT MEMBERSHIP OPERATIONS
    # =============================================

    async def add_tenant_member(
        self,
        tenant_id: str,
        admin_user_id: str,
        membership_data: TenantMembershipCreate,
    ) -> TenantMembershipResponse:
        """Add a member to a tenant (admin/owner only)"""
        try:
            # Check if admin has permission
            admin_membership = await self._get_user_tenant_membership(
                admin_user_id, tenant_id
            )
            if not admin_membership or admin_membership["role"] not in [
                "owner",
                "admin",
            ]:
                return TenantMembershipResponse(
                    success=False,
                    message="Access denied: Admin or owner role required",
                    data=None,
                )

            # Check if user is already a member
            existing = await self._get_user_tenant_membership(
                membership_data.user_id, tenant_id
            )
            if existing:
                return TenantMembershipResponse(
                    success=False,
                    message="User is already a member of this tenant",
                    data=None,
                )

            # Add membership
            membership_result = (
                self.supabase.client.table("tenant_memberships")
                .insert(
                    {
                        "tenant_id": tenant_id,
                        "user_id": membership_data.user_id,
                        "role": membership_data.role,
                        "permissions": membership_data.permissions,
                        "is_active": True,
                    }
                )
                .execute()
            )

            if not membership_result.data:
                return TenantMembershipResponse(
                    success=False, message="Failed to add member to tenant", data=None
                )

            return TenantMembershipResponse(
                success=True,
                message="Member added successfully",
                data=TenantMembership(**membership_result.data[0]),
            )

        except Exception as e:
            logger.error(f"Error adding tenant member: {str(e)}")
            return TenantMembershipResponse(
                success=False, message=f"Failed to add member: {str(e)}", data=None
            )

    async def list_tenant_members(
        self, tenant_id: str, user_id: str, page: int = 1, page_size: int = 20
    ) -> TenantMembershipListResponse:
        """List all members of a tenant"""
        try:
            # Get memberships with pagination
            offset = (page - 1) * page_size
            memberships_result = (
                self.supabase.client.table("tenant_memberships")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("is_active", True)
                .range(offset, offset + page_size - 1)
                .execute()
            )

            # Get total count
            count_result = (
                self.supabase.client.table("tenant_memberships")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("is_active", True)
                .execute()
            )

            total = count_result.count if count_result.count else 0
            memberships = [TenantMembership(**m) for m in memberships_result.data]

            return TenantMembershipListResponse(
                success=True,
                message="Members retrieved successfully",
                data=memberships,
                total=total,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.error(f"Error listing tenant members: {str(e)}")
            return TenantMembershipListResponse(
                success=False,
                message=f"Failed to list members: {str(e)}",
                data=[],
                total=0,
                page=page,
                page_size=page_size,
            )

    async def update_tenant_member(
        self,
        tenant_id: str,
        member_user_id: str,
        admin_user_id: str,
        update_data: TenantMembershipUpdate,
    ) -> TenantMembershipResponse:
        """Update a tenant member's role or permissions (admin/owner only)"""
        try:
            # Check if admin has permission
            admin_membership = await self._get_user_tenant_membership(
                admin_user_id, tenant_id
            )
            if not admin_membership or admin_membership["role"] not in [
                "owner",
                "admin",
            ]:
                return TenantMembershipResponse(
                    success=False,
                    message="Access denied: Admin or owner role required",
                    data=None,
                )

            # Check if target member exists
            target_membership = await self._get_user_tenant_membership(
                member_user_id, tenant_id
            )
            if not target_membership:
                return TenantMembershipResponse(
                    success=False, message="Member not found in this tenant", data=None
                )

            # Prevent demoting the last owner
            if (
                target_membership["role"] == "owner"
                and update_data.role
                and update_data.role != "owner"
            ):
                owners_count = await self._count_tenant_owners(tenant_id)
                if owners_count <= 1:
                    return TenantMembershipResponse(
                        success=False,
                        message="Cannot demote the last owner of the tenant",
                        data=None,
                    )

            # Prepare update data
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

            if not update_dict:
                return TenantMembershipResponse(
                    success=False, message="No valid fields to update", data=None
                )

            # Update membership
            membership_result = (
                self.supabase.client.table("tenant_memberships")
                .update(update_dict)
                .eq("tenant_id", tenant_id)
                .eq("user_id", member_user_id)
                .execute()
            )

            if not membership_result.data:
                return TenantMembershipResponse(
                    success=False, message="Failed to update member", data=None
                )

            return TenantMembershipResponse(
                success=True,
                message="Member updated successfully",
                data=TenantMembership(**membership_result.data[0]),
            )

        except Exception as e:
            logger.error(f"Error updating tenant member: {str(e)}")
            return TenantMembershipResponse(
                success=False, message=f"Failed to update member: {str(e)}", data=None
            )

    async def remove_tenant_member(
        self, tenant_id: str, user_id: str
    ) -> TenantMembershipResponse:
        """Remove a member from a tenant (admin/owner only)"""
        try:
            # Prevent removing the last owner
            target_membership = await self._get_user_tenant_membership(
                user_id, tenant_id
            )
            if target_membership["role"] == "owner":
                owners_count = await self._count_tenant_owners(tenant_id)
                if owners_count <= 1:
                    return TenantMembershipResponse(
                        success=False,
                        message="Cannot remove the last owner of the tenant",
                        data=None,
                    )

            membership_result = (
                self.supabase.client.table("tenant_memberships")
                .delete()
                .eq("tenant_id", tenant_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not membership_result.data:
                return TenantMembershipResponse(
                    success=False, message="Failed to remove member", data=None
                )

            return TenantMembershipResponse(
                success=True,
                message="Member removed successfully",
                data=TenantMembership(**membership_result.data[0]),
            )

        except Exception as e:
            logger.error(f"Error removing tenant member: {str(e)}")
            return TenantMembershipResponse(
                success=False, message=f"Failed to remove member: {str(e)}", data=None
            )

    # =============================================
    # ADMIN DASHBOARD OPERATIONS
    # =============================================

    async def get_tenant_analytics(
        self, admin_user_id: str, page: int = 1, page_size: int = 20
    ) -> TenantAnalyticsResponse:
        """Get analytics for all tenants (admin only)"""
        try:
            if not self.use_service_role:
                return TenantAnalyticsResponse(
                    success=False, message="Admin access required", data=[]
                )

            # Get all tenants with pagination
            offset = (page - 1) * page_size
            tenants_result = (
                self.supabase.client.table("tenants")
                .select("*")
                .eq("is_active", True)
                .range(offset, offset + page_size - 1)
                .execute()
            )

            analytics_data = []
            for tenant in tenants_result.data:
                # Get member count
                members_count = await self._count_tenant_members(tenant["id"])

                # Get project count (if projects table exists)
                projects_count = await self._count_tenant_projects(tenant["id"])

                # Get reports count (if reports table exists)
                reports_count = await self._count_tenant_reports(tenant["id"])

                # Get credits usage (if credit system exists)
                credits_used, credits_remaining = await self._get_tenant_credits(
                    tenant["id"]
                )

                # Get last activity
                last_activity = await self._get_tenant_last_activity(tenant["id"])

                analytics_data.append(
                    TenantAnalytics(
                        tenant_id=tenant["id"],
                        tenant_name=tenant["name"],
                        tenant_type=tenant["tenant_type"],
                        member_count=members_count,
                        active_projects=projects_count,
                        total_reports=reports_count,
                        credits_used=credits_used,
                        credits_remaining=credits_remaining,
                        last_activity=last_activity,
                    )
                )

            # Get total count
            count_result = (
                self.supabase.client.table("tenants")
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            total = count_result.count if count_result.count else 0

            return TenantAnalyticsResponse(
                success=True,
                message="Analytics retrieved successfully",
                data=analytics_data,
            )

        except Exception as e:
            logger.error(f"Error getting tenant analytics: {str(e)}")
            return TenantAnalyticsResponse(
                success=False, message=f"Failed to get analytics: {str(e)}", data=[]
            )

    # =============================================
    # HELPER METHODS
    # =============================================

    async def _get_user_tenant_membership(
        self, user_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user's membership in a specific tenant"""
        try:
            result = (
                self.supabase.client.table("tenant_memberships")
                .select("*")
                .eq("user_id", user_id)
                .eq("tenant_id", tenant_id)
                .eq("is_active", True)
                .execute()
            )

            return result.data[0] if result.data else None
        except Exception:
            return None

    async def _count_tenant_owners(self, tenant_id: str) -> int:
        """Count the number of owners in a tenant"""
        try:
            result = (
                self.supabase.client.table("tenant_memberships")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("role", "owner")
                .eq("is_active", True)
                .execute()
            )

            return result.count if result.count else 0
        except Exception:
            return 0

    async def _count_tenant_members(self, tenant_id: str) -> int:
        """Count the number of active members in a tenant"""
        try:
            result = (
                self.supabase.client.table("tenant_memberships")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("is_active", True)
                .execute()
            )

            return result.count if result.count else 0
        except Exception:
            return 0

    async def _count_tenant_projects(self, tenant_id: str) -> int:
        """Count the number of active projects in a tenant"""
        try:
            result = (
                self.supabase.client.table("projects")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("status", "active")
                .execute()
            )

            return result.count if result.count else 0
        except Exception:
            return 0

    async def _count_tenant_reports(self, tenant_id: str) -> int:
        """Count the number of reports generated in a tenant"""
        try:
            # This would depend on your reports table structure
            # For now, return 0 as placeholder
            return 0
        except Exception:
            return 0

    async def _get_tenant_credits(self, tenant_id: str) -> Tuple[int, int]:
        """Get tenant's credit usage and remaining credits"""
        try:
            # This would integrate with your credit system
            # For now, return placeholder values
            return 0, 0
        except Exception:
            return 0, 0

    async def _get_tenant_last_activity(self, tenant_id: str) -> Optional[datetime]:
        """Get the last activity timestamp for a tenant"""
        try:
            # This would depend on your activity tracking system
            # For now, return None as placeholder
            return None
        except Exception:
            return None

    async def delete_tenant(self, tenant_id: str, user_id: str) -> bool:
        """
        Delete a tenant (organization or team) if the user is the owner.
        Cascading deletes will clean up memberships, invitations, and mappings.
        """
        try:
            # Ensure tenant exists
            res = (
                self.supabase.client.table("tenants")
                .select("id, tenant_type, created_at")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            if not res.data:
                raise HTTPException(status_code=404, detail="Tenant not found")

            tenant = res.data[0]

            # Check if user is owner of this tenant (for non-super-admin users)
            if not self.use_service_role:
                membership = await self._get_user_tenant_membership(user_id, tenant_id)
                if not membership or membership["role"] != "owner":
                    raise HTTPException(
                        status_code=403, 
                        detail="Access denied: Only tenant owners can delete tenants"
                    )

            # Delete related data first (to avoid foreign key constraints)
            # Order is critical due to foreign key dependencies
            
            logger.info(f"Starting cascading delete for tenant {tenant_id}")
            
            # 1. Get VMP project IDs for this tenant first
            vmp_project_ids = []
            try:
                vmp_projects_result = self.supabase.client.table("vmp_projects").select("id").eq("tenant_id", tenant_id).execute()
                vmp_project_ids = [project["id"] for project in vmp_projects_result.data] if vmp_projects_result.data else []
                logger.info(f"Found {len(vmp_project_ids)} VMP projects for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to get VMP project IDs: {e}")
                
            # 2. Delete VMP project artifacts first (they reference vmp_projects)
            if vmp_project_ids:
                try:
                    for project_id in vmp_project_ids:
                        self.supabase.client.table("vmp_vpc_artifacts").delete().eq("project_id", project_id).execute()
                    logger.info(f"Deleted VMP VPC artifacts for tenant {tenant_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete VMP VPC artifacts: {e}")
                    pass
                    
            # 3. Delete VMP project contexts (they reference vmp_projects and documents)
            if vmp_project_ids:
                try:
                    for project_id in vmp_project_ids:
                        self.supabase.client.table("vmp_project_contexts").delete().eq("project_id", project_id).execute()
                    logger.info(f"Deleted VMP project contexts for tenant {tenant_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete VMP project contexts: {e}")
                    pass
            
            # 4. Delete VMP projects (they reference documents via pv_report_id)
            try:
                vmp_delete_result = self.supabase.client.table("vmp_projects").delete().eq("tenant_id", tenant_id).execute()
                logger.info(f"Deleted {len(vmp_delete_result.data) if vmp_delete_result.data else 0} VMP projects for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete VMP projects: {e}")
                pass
                
            # 5. Delete regular projects
            try:
                projects_delete_result = self.supabase.client.table("projects").delete().eq("tenant_id", tenant_id).execute()
                logger.info(f"Deleted {len(projects_delete_result.data) if projects_delete_result.data else 0} regular projects for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete regular projects: {e}")
                pass

            # 6. Delete documents owned by this tenant (only if not referenced by other VMP projects)
            try:
                # Get all documents owned by this tenant
                tenant_documents_result = self.supabase.client.table("documents").select("id").eq("tenant_id", tenant_id).execute()
                tenant_document_ids = [doc["id"] for doc in tenant_documents_result.data] if tenant_documents_result.data else []
                
                deleted_count = 0
                for doc_id in tenant_document_ids:
                    # Check if this document is referenced by any VMP projects (across all tenants)
                    vmp_refs_result = self.supabase.client.table("vmp_projects").select("id").eq("pv_report_id", doc_id).execute()
                    
                    if not vmp_refs_result.data:  # No VMP projects reference this document
                        # Safe to delete
                        self.supabase.client.table("documents").delete().eq("id", doc_id).execute()
                        deleted_count += 1
                    else:
                        logger.warning(f"Skipping document {doc_id} - still referenced by {len(vmp_refs_result.data)} VMP projects")
                
                logger.info(f"Deleted {deleted_count} documents for tenant {tenant_id} (skipped shared documents)")
            except Exception as e:
                logger.warning(f"Failed to delete documents: {e}")
                pass

            # 7. Delete credit lots for this tenant
            try:
                credits_delete_result = self.supabase.client.table("credit_lots").delete().eq("tenant_id", tenant_id).execute()
                logger.info(f"Deleted {len(credits_delete_result.data) if credits_delete_result.data else 0} credit lots for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete credit lots: {e}")
                pass
            
            # 8. Delete tenant memberships
            try:
                memberships_delete_result = self.supabase.client.table("tenant_memberships").delete().eq("tenant_id", tenant_id).execute()
                logger.info(f"Deleted {len(memberships_delete_result.data) if memberships_delete_result.data else 0} tenant memberships for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete tenant memberships: {e}")
                pass
            
            # 9. Delete tenant invitations (if exists)
            try:
                invitations_delete_result = self.supabase.client.table("tenant_invitations").delete().eq("tenant_id", tenant_id).execute()
                logger.info(f"Deleted tenant invitations for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete tenant invitations: {e}")
                pass
            
            # 10. Delete organization-team mappings (if exists)
            try:
                org_mappings_delete_result = self.supabase.client.table("organization_team_mappings").delete().eq("organization_id", tenant_id).execute()
                logger.info(f"Deleted organization-team mappings for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete organization-team mappings: {e}")
                pass
                
            # 11. Delete team-user mappings (if exists)
            try:
                team_mappings_delete_result = self.supabase.client.table("team_user_mappings").delete().eq("team_id", tenant_id).execute()
                logger.info(f"Deleted team-user mappings for tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to delete team-user mappings: {e}")
                pass

            # Check if tenant still owns any documents (shared documents that couldn't be deleted)
            remaining_docs_result = self.supabase.client.table("documents").select("id").eq("tenant_id", tenant_id).execute()
            remaining_docs = remaining_docs_result.data if remaining_docs_result.data else []
            
            if remaining_docs:
                # Transfer ownership of remaining documents to a system tenant or mark them as orphaned
                logger.warning(f"Tenant {tenant_id} still owns {len(remaining_docs)} shared documents. Transferring ownership to system.")
                
                # Option 1: Transfer to system tenant (you'll need to define a system tenant ID)
                # system_tenant_id = "00000000-0000-0000-0000-000000000000"  # Define your system tenant
                
                # Option 2: Set tenant_id to null (orphaned documents)
                for doc in remaining_docs:
                    try:
                        self.supabase.client.table("documents").update({"tenant_id": None}).eq("id", doc["id"]).execute()
                        logger.info(f"Orphaned document {doc['id']} (removed tenant ownership)")
                    except Exception as e:
                        logger.warning(f"Failed to orphan document {doc['id']}: {e}")

            # Finally delete the tenant itself
            delete_result = self.supabase.client.table("tenants").delete().eq("id", tenant_id).execute()
            
            if not delete_result.data:
                raise HTTPException(status_code=500, detail="Failed to delete tenant")

            logger.info(f"Successfully deleted tenant {tenant_id} by user {user_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"delete_tenant error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete tenant: {e}")

    def _get_default_permissions(self, role: str) -> Dict[str, Any]:
        """Get default permissions for a role"""
        permissions = {
            "owner": {
                "can_manage_tenant": True,
                "can_manage_members": True,
                "can_manage_billing": True,
                "can_view_analytics": True,
                "can_manage_projects": True,
            },
            "admin": {
                "can_manage_tenant": False,
                "can_manage_members": True,
                "can_manage_billing": False,
                "can_view_analytics": True,
                "can_manage_projects": True,
            },
            "member": {
                "can_manage_tenant": False,
                "can_manage_members": False,
                "can_manage_billing": False,
                "can_view_analytics": False,
                "can_manage_projects": True,
            },
        }
        return permissions.get(role, permissions["member"])
