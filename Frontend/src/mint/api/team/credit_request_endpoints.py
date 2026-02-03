"""
API endpoints for Team Credit Request system.
Enables Team Leaders to request additional credits from Organization Admins.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from ..auth_v2.utils import (
    get_current_user,
    get_global_admin_or_tenant_member,
    get_tenant_admin_only,
)
from .credit_request_models import (
    CreditRequestCreate,
    CreditRequestReview,
    CreditRequestCreateResponse,
    CreditRequestListResponse,
    CreditRequestReviewResponse,
    CreditRequestCancelResponse,
)
from .credit_request_service import CreditRequestService

logger = logging.getLogger(__name__)

credit_request_router = APIRouter(prefix="/api/teams", tags=["team-credit-requests"])


@credit_request_router.post(
    "/{team_id}/request-credits",
    response_model=CreditRequestCreateResponse,
    summary="Request Additional Credits",
    description="Team Leader or member requests additional credits from Organization Admin"
)
async def request_credits(
    team_id: str = Path(..., description="Team ID"),
    body: CreditRequestCreate = ...,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new credit request.
    
    Team Leaders or members can request additional credits when their team pool is running low.
    The request will be sent to Organization Admins for review.
    
    **Business Logic:**
    - Verifies team exists and is active
    - Verifies user is a team member
    - Creates pending request
    - Notifies Organization Admins (TODO)
    
    **Returns:**
    - Request ID and details
    - Status will be 'pending' until reviewed
    """
    try:
        service = CreditRequestService(use_service_role=True)
        
        result = service.create_request(
            team_id=team_id,
            requester_id=current_user["user_id"],
            requested_credits=body.requested_credits,
            reason=body.reason
        )
        
        return CreditRequestCreateResponse(
            request_id=result["id"],
            team_id=result["team_id"],
            organization_id=result["organization_id"],
            requested_credits=result["requested_credits"],
            status=result["status"],
            created_at=result["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in request_credits endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create credit request: {str(e)}"
        )


@credit_request_router.get(
    "/{team_id}/credit-requests",
    response_model=CreditRequestListResponse,
    summary="View Team Credit Requests",
    description="Team members can view all credit requests for their team"
)
async def get_team_credit_requests(
    team_id: str = Path(..., description="Team ID"),
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, cancelled"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_global_admin_or_tenant_member),
):
    """
    Get all credit requests for a team.
    
    Team members can view the status of all credit requests submitted by their team.
    Includes request history with approval/rejection details.
    
    **Query Parameters:**
    - `status`: Filter by request status
    - `page`, `page_size`: Pagination
    
    **Returns:**
    - List of requests with details
    - Total count and pending count
    """
    try:
        service = CreditRequestService(use_service_role=True)
        
        result = service.get_team_requests(
            team_id=team_id,
            status=status,
            page=page,
            page_size=page_size
        )
        
        return CreditRequestListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_team_credit_requests endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch credit requests: {str(e)}"
        )


@credit_request_router.delete(
    "/{team_id}/credit-requests/{request_id}",
    response_model=CreditRequestCancelResponse,
    summary="Cancel Credit Request",
    description="Team Leader cancels a pending credit request"
)
async def cancel_credit_request(
    team_id: str = Path(..., description="Team ID"),
    request_id: str = Path(..., description="Request ID"),
    current_user: dict = Depends(get_current_user),
):
    """
    Cancel a pending credit request.
    
    Only the requester can cancel their own pending request.
    Cannot cancel approved or rejected requests.
    
    **Business Logic:**
    - Verifies request exists and is pending
    - Verifies user is the requester
    - Updates status to 'cancelled'
    - Notifies Organization Admins (TODO)
    
    **Returns:**
    - Success confirmation
    """
    try:
        service = CreditRequestService(use_service_role=True)
        
        result = service.cancel_request(
            request_id=request_id,
            user_id=current_user["user_id"]
        )
        
        return CreditRequestCancelResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_credit_request endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel credit request: {str(e)}"
        )


# Organization Admin Endpoints

@credit_request_router.get(
    "/organization/{organization_id}/credit-requests",
    response_model=CreditRequestListResponse,
    summary="View All Organization Credit Requests",
    description="Organization Admins can view all credit requests from their teams"
)
async def get_organization_credit_requests(
    organization_id: str = Path(..., description="Organization ID"),
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, cancelled"),
    team_id: Optional[str] = Query(None, description="Filter by specific team"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_tenant_admin_only),
):
    """
    Get all credit requests for an organization.
    
    Organization Admins can view all credit requests from all teams in their organization.
    Includes current team metrics for context.
    
    **Query Parameters:**
    - `status`: Filter by request status
    - `team_id`: Filter by specific team
    - `page`, `page_size`: Pagination
    
    **Returns:**
    - List of requests with team metrics
    - Total count and pending count
    """
    try:
        service = CreditRequestService(use_service_role=True)
        
        result = service.get_organization_requests(
            organization_id=organization_id,
            status=status,
            team_id=team_id,
            page=page,
            page_size=page_size
        )
        
        return CreditRequestListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_organization_credit_requests endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch organization credit requests: {str(e)}"
        )


@credit_request_router.post(
    "/organization/{organization_id}/credit-requests/{request_id}/review",
    response_model=CreditRequestReviewResponse,
    summary="Approve or Reject Credit Request",
    description="Organization Admin approves or rejects a credit request"
)
async def review_credit_request(
    organization_id: str = Path(..., description="Organization ID"),
    request_id: str = Path(..., description="Request ID"),
    body: CreditRequestReview = ...,
    current_user: dict = Depends(get_tenant_admin_only),
):
    """
    Approve or reject a credit request.
    
    Organization Admins can approve or reject pending credit requests from their teams.
    
    **Approval:**
    - Verifies organization has sufficient credits
    - Allocates credits to team leader using existing credit allocation system
    - Updates request status to 'approved'
    - Notifies team leader (TODO)
    
    **Rejection:**
    - Updates request status to 'rejected'
    - Notifies team leader with reason (TODO)
    
    **Business Logic:**
    - Request must be in 'pending' status
    - For approval: credits_to_allocate is required
    - For approval: Organization must have sufficient credits
    - Admin can allocate different amount than requested
    
    **Returns:**
    - Updated request status
    - Credits allocated (if approved)
    """
    try:
        service = CreditRequestService(use_service_role=True)
        
        result = service.review_request(
            request_id=request_id,
            reviewer_id=current_user["user_id"],
            action=body.action,
            credits_to_allocate=body.credits_to_allocate,
            review_notes=body.review_notes
        )
        
        return CreditRequestReviewResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in review_credit_request endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to review credit request: {str(e)}"
        )
