"""
API endpoints for cohort management.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ..auth_v2.utils import get_current_user, get_global_admin_or_tenant_admin
from .cohort_service import (
    CohortError,
    CohortMembershipError,
    CohortNotFoundError,
    CohortService,
    CohortTenantMismatchError,
    DuplicateCohortNameError,
)
from .models import (
    AssignMemberToCohortRequest,
    BulkAssignMembersRequest,
    BulkAssignMembersResponse,
    BulkMoveMembersRequest,
    BulkMoveMembersResponse,
    BulkRemoveMembersRequest,
    BulkRemoveMembersResponse,
    CohortMemberResponse,
    CohortMembersListResponse,
    CohortProjectsListResponse,
    CohortResponse,
    CohortWithMembersResponse,
    CreateCohortRequest,
    MoveMemberToCohortRequest,
    SuccessResponse,
    UpdateCohortRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])


# ============================================================================
# Dependencies
# ============================================================================


def get_cohort_service() -> CohortService:
    """Dependency to get CohortService instance"""
    return CohortService(use_service_role=True)


# ============================================================================
# Cohort CRUD Endpoints
# ============================================================================


@router.post("/{tenant_id}", response_model=CohortResponse, status_code=201)
async def create_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    request: CreateCohortRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Create a new cohort in an organization.

    Cohort names must be unique within an organization.
    Requires organization admin/owner access.
    Only organizations can have cohorts.
    """
    try:
        created_by = current_user.get("user_id")

        cohort = service.create_cohort(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            color=request.color,
            settings=request.settings,
            created_by=created_by,
            current_user_tenant_type=current_user.get("tenant_type"),
            current_user_roles=current_user.get("roles", []),
        )

        logger.info(
            f"Created cohort {cohort['id']} ('{request.name}') for tenant {tenant_id}"
        )
        return cohort

    except HTTPException:
        raise
    except DuplicateCohortNameError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create cohort")


@router.get("/{tenant_id}", response_model=List[CohortResponse])
async def list_cohorts(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    include_inactive: bool = Query(False, description="Include inactive cohorts"),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    List all cohorts for an organization.

    By default, only returns active cohorts.
    Requires organization admin/owner access.
    """
    try:
        cohorts = service.list_cohorts(
            tenant_id=tenant_id, include_inactive=include_inactive
        )
        return cohorts
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing cohorts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list cohorts")


@router.get("/{tenant_id}/{cohort_id}", response_model=CohortResponse)
async def get_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Get a specific cohort by ID.

    Returns cohort details.
    Requires organization admin/owner access.
    """
    try:
        cohort = service.get_cohort(cohort_id)

        # Verify cohort belongs to the specified tenant
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        return cohort
    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cohort")


@router.put("/{tenant_id}/{cohort_id}", response_model=CohortResponse)
async def update_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    request: UpdateCohortRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Update a cohort's properties.

    Can update name, description, color, and settings.
    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        existing_cohort = service.get_cohort(cohort_id)
        if existing_cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        cohort = service.update_cohort(
            cohort_id=cohort_id,
            name=request.name,
            description=request.description,
            color=request.color,
            settings=request.settings,
        )

        logger.info(f"Updated cohort {cohort_id}")
        return cohort

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateCohortNameError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update cohort")


@router.delete("/{tenant_id}/{cohort_id}", response_model=CohortResponse)
async def delete_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Deactivate a cohort (soft delete).

    This will also deactivate all credit_lots associated with this cohort
    via the database trigger.

    Requires organization admin/owner access.
    """
    try:
        cohort = service.delete_cohort(cohort_id, tenant_id)
        logger.info(f"Deactivated cohort {cohort_id} ('{cohort['name']}')")
        return cohort

    except (CohortNotFoundError, CohortTenantMismatchError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete cohort")


@router.patch("/{tenant_id}/{cohort_id}/status", response_model=CohortResponse)
async def set_cohort_status(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    is_active: bool = Query(
        ..., description="Set active status (true to activate, false to deactivate)"
    ),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Set a cohort's active status.

    Use this to activate or deactivate a cohort.
    Deactivating will also deactivate associated credit_lots via database trigger.

    Requires organization admin/owner access.
    """
    try:
        cohort = service.set_cohort_active_status(cohort_id, tenant_id, is_active)
        status = "activated" if is_active else "deactivated"
        logger.info(f"Cohort {cohort_id} ('{cohort['name']}') {status}")
        return cohort

    except (CohortNotFoundError, CohortTenantMismatchError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting cohort status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update cohort status")


# ============================================================================
# Bulk Cohort Membership Endpoints
# ============================================================================
# NOTE: Bulk endpoints must be defined BEFORE dynamic path endpoints
# (e.g., /members/bulk before /members/{member_tenant_id})
# to ensure FastAPI matches the specific route first.


@router.post(
    "/{tenant_id}/{cohort_id}/members/bulk",
    response_model=BulkAssignMembersResponse,
    status_code=200,
    summary="Bulk assign members to cohort",
    description="Assign multiple tenants (individuals or teams) to a cohort in a single operation."
)
async def bulk_assign_members_to_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    request: BulkAssignMembersRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Bulk assign multiple tenants to a cohort.

    Efficiently processes multiple member assignments in a single operation.
    Returns detailed results for each member including success/failure status.

    Note: A tenant can only belong to ONE cohort per organization.

    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        cohort = service.get_cohort(cohort_id)
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        result = service.bulk_assign_members_to_cohort(
            cohort_id=cohort_id,
            member_tenant_ids=request.member_tenant_ids,
            assigned_by=current_user.get("user_id")
        )

        logger.info(
            f"Bulk assigned {result['successful']}/{result['total_requested']} "
            f"members to cohort {cohort_id}"
        )
        return result

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk assigning members to cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to bulk assign members to cohort")


@router.delete(
    "/{tenant_id}/{cohort_id}/members/bulk",
    response_model=BulkRemoveMembersResponse,
    status_code=200,
    summary="Bulk remove members from cohort",
    description="Remove multiple tenants from a cohort in a single operation."
)
async def bulk_remove_members_from_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    request: BulkRemoveMembersRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Bulk remove multiple tenants from a cohort.

    Efficiently processes multiple member removals in a single operation.
    Returns detailed results for each member including success/failure status.

    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        cohort = service.get_cohort(cohort_id)
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        result = service.bulk_remove_members_from_cohort(
            cohort_id=cohort_id,
            member_tenant_ids=request.member_tenant_ids
        )

        logger.info(
            f"Bulk removed {result['successful']}/{result['total_requested']} "
            f"members from cohort {cohort_id}"
        )
        return result

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk removing members from cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to bulk remove members from cohort")


@router.put(
    "/{tenant_id}/{cohort_id}/members/bulk/move",
    response_model=BulkMoveMembersResponse,
    status_code=200,
    summary="Bulk move members between cohorts",
    description="Move multiple tenants from one cohort to another in a single operation."
)
async def bulk_move_members_between_cohorts(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Source cohort ID"),
    request: BulkMoveMembersRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Bulk move multiple tenants from one cohort to another.

    Efficiently processes multiple member moves in a single operation.
    Both cohorts must belong to the specified organization.
    Target cohort must be active.

    Returns detailed results for each member including success/failure status.

    Requires organization admin/owner access.
    """
    try:
        result = service.bulk_move_members_between_cohorts(
            member_tenant_ids=request.member_tenant_ids,
            source_cohort_id=cohort_id,
            target_cohort_id=request.target_cohort_id,
            tenant_id=tenant_id,
            assigned_by=current_user.get("user_id")
        )

        logger.info(
            f"Bulk moved {result['successful']}/{result['total_requested']} "
            f"members from cohort {cohort_id} to {request.target_cohort_id}"
        )
        return result

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk moving members between cohorts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to bulk move members between cohorts")


# ============================================================================
# Single Cohort Membership Endpoints
# ============================================================================


@router.post("/{tenant_id}/{cohort_id}/members", status_code=201)
async def assign_member_to_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    request: AssignMemberToCohortRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Assign a tenant (individual or team) to a cohort.

    Note: A tenant can only belong to ONE cohort per organization.
    If the tenant is already in another cohort, this will fail with 409 Conflict.

    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        cohort = service.get_cohort(cohort_id)
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        if not request.member_tenant_id:
            raise HTTPException(
                status_code=400,
                detail="member_tenant_id is required"
            )

        membership = service.assign_member_to_cohort(
            cohort_id=cohort_id,
            member_tenant_id=request.member_tenant_id,
            assigned_by=current_user.get("user_id")
        )
        logger.info(f"Assigned tenant {request.member_tenant_id} to cohort {cohort_id}")

        return membership

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortMembershipError as e:
        # Tenant already in a cohort or not a member of the organization
        raise HTTPException(status_code=409, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning member to cohort: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign member to cohort")


@router.delete(
    "/{tenant_id}/{cohort_id}/members/{member_tenant_id}", response_model=SuccessResponse
)
async def remove_member_from_cohort(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    member_tenant_id: str = Path(..., description="Tenant ID (individual or team) to remove"),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Remove a tenant (individual or team) from a cohort.

    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        cohort = service.get_cohort(cohort_id)
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        result = service.remove_member_from_cohort(cohort_id=cohort_id, member_tenant_id=member_tenant_id)

        logger.info(f"Removed tenant {member_tenant_id} from cohort {cohort_id}")
        return result

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortMembershipError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing member from cohort: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to remove member from cohort"
        )


@router.put("/{tenant_id}/{cohort_id}/members/{member_tenant_id}/move", status_code=200)
async def move_member_between_cohorts(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Source cohort ID (current cohort)"),
    member_tenant_id: str = Path(..., description="Tenant ID (individual or team) to move"),
    request: MoveMemberToCohortRequest = None,
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
):
    """
    Move a tenant (individual or team) from one cohort to another within the same organization.

    This is an atomic operation that:
    1. Removes the tenant from the source cohort (cohort_id in path)
    2. Adds the tenant to the target cohort (target_cohort_id in body)

    Both cohorts must belong to the specified organization.
    Target cohort must be active.
    Tenant must be a member of the source cohort.

    Requires organization admin/owner access.
    """
    try:
        membership = service.move_member_between_cohorts(
            member_tenant_id=member_tenant_id,
            source_cohort_id=cohort_id,
            target_cohort_id=request.target_cohort_id,
            tenant_id=tenant_id,
            assigned_by=current_user.get("user_id"),
        )

        logger.info(
            f"Moved tenant {member_tenant_id} from cohort {cohort_id} to {request.target_cohort_id} in org {tenant_id}"
        )
        return membership

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CohortMembershipError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CohortError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error moving member between cohorts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to move member between cohorts"
        )


@router.get(
    "/{tenant_id}/{cohort_id}/members",
    response_model=CohortMembersListResponse,
    summary="List cohort members with pagination",
    description="Get paginated list of cohort members with user/tenant details. Requires organization admin/owner access."
)
async def get_cohort_members(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Number of items per page"),
    member_type: str = Query(
        "all",
        regex="^(individual|team|all)$",
        description="Filter by member type: 'individual', 'team', or 'all'"
    ),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
) -> CohortMembersListResponse:
    """
    Get paginated members of a cohort.

    Returns list of cohort memberships with tenant info and user details.
    For individuals: includes user_id, user_email, user_name, user_role.
    For teams: includes team_name, team_contact_email, team_admin_emails.

    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        cohort = service.get_cohort(cohort_id)
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        result = service.get_cohort_members(
            cohort_id=cohort_id,
            page=page,
            page_size=page_size,
            member_type=member_type
        )

        return CohortMembersListResponse(**result)

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting cohort members: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cohort members")


@router.get(
    "/{tenant_id}/{cohort_id}/projects",
    response_model=CohortProjectsListResponse,
    summary="List all projects in a cohort",
    description="Get paginated list of all projects belonging to members of a cohort. Requires organization admin/owner access."
)
async def get_cohort_projects(
    tenant_id: str = Path(..., description="Organization tenant ID"),
    cohort_id: str = Path(..., description="Cohort ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Number of items per page"),
    service: CohortService = Depends(get_cohort_service),
    current_user: Dict[str, Any] = Depends(get_global_admin_or_tenant_admin),
) -> CohortProjectsListResponse:
    """
    Get paginated list of all projects belonging to members of a cohort.

    Returns project details including:
    - Project info: id, name, description, current_step, status, timestamps
    - Owner info: tenant_id, tenant_name, tenant_type, owner_email, owner_name

    Projects are sorted by most recently updated first.

    Requires organization admin/owner access.
    """
    try:
        # Verify cohort belongs to the specified tenant
        cohort = service.get_cohort(cohort_id)
        if cohort["tenant_id"] != tenant_id:
            raise HTTPException(status_code=404, detail="Cohort not found")

        result = service.get_cohort_projects(
            cohort_id=cohort_id,
            page=page,
            page_size=page_size,
        )

        return CohortProjectsListResponse(**result)

    except HTTPException:
        raise
    except CohortNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting cohort projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cohort projects")
