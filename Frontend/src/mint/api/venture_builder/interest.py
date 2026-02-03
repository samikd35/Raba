"""
Venture Builder Interest Submissions API

Handles VB Declaration of Interest form submissions:
- Public endpoint for submitting interest
- Public endpoint for checking submission status
- Admin endpoints for listing, viewing, approving, and rejecting submissions
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.mint.api.auth_v2.utils import get_admin_user

from .exceptions import VBAlreadyExistsError, VBBaseException, VBNotFoundError, VBValidationError
from .interest_models import (
    InterestSubmissionStatus,
    VBInterestApproveRequest,
    VBInterestApproveResponse,
    VBInterestNotesUpdate,
    VBInterestRejectRequest,
    VBInterestRejectResponse,
    VBInterestStatusResponse,
    VBInterestSubmissionCreate,
    VBInterestSubmissionListItem,
    VBInterestSubmissionListResponse,
    VBInterestSubmissionResponse,
    VBInterestSubmitResponse,
)
from .service import get_vb_service
from .utils import handle_vb_exception

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Interest"])

vb_service = get_vb_service()


# =====================================================
# PUBLIC ENDPOINTS (No Auth Required)
# =====================================================

@router.post(
    "/interest",
    status_code=status.HTTP_201_CREATED,
    summary="Submit VB Declaration of Interest",
    description="Public endpoint for potential venture builders to submit their interest in joining the platform.",
)
async def submit_interest(
    request: VBInterestSubmissionCreate,
):
    """
    Submit a VB Declaration of Interest form.
    
    This is a public endpoint - no authentication required.
    
    The submission will be reviewed by admins and the applicant will be
    contacted within 3-5 business days.
    """
    try:
        result = vb_service.create_interest_submission(request.model_dump())
        
        return {
            "success": True,
            "data": VBInterestSubmitResponse(
                id=result["id"],
                full_name=result["full_name"],
                work_email=result["work_email"],
                status=result["status"],
                message=result["message"],
                created_at=result["created_at"],
            ).model_dump(),
            "error": None,
        }
    except VBAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.message),
        )
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit interest: {str(e)}",
        )


@router.get(
    "/interest/status/{email}",
    summary="Check Submission Status",
    description="Public endpoint to check the status of an interest submission by email.",
)
async def check_submission_status(
    email: str,
):
    """
    Check the status of an interest submission by email.
    
    This is a public endpoint - no authentication required.
    Returns limited information (email, status, submitted date).
    """
    try:
        result = vb_service.get_interest_submission_status(email)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No submission found for email: {email}",
            )
        
        return {
            "success": True,
            "data": VBInterestStatusResponse(
                email=result["email"],
                status=result["status"],
                submitted_at=result["submitted_at"],
            ).model_dump(),
            "error": None,
        }
    except HTTPException:
        raise
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check status: {str(e)}",
        )


# =====================================================
# ADMIN ENDPOINTS (Admin Auth Required)
# =====================================================

@router.get(
    "/admin/interest",
    summary="List Interest Submissions",
    description="Admin endpoint to list all interest submissions with filtering and pagination.",
)
async def list_interest_submissions(
    status_filter: Optional[InterestSubmissionStatus] = Query(
        None, alias="status", description="Filter by submission status"
    ),
    search: Optional[str] = Query(None, max_length=200, description="Search by name or email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_admin_user),
):
    """
    List all VB interest submissions with optional filtering.
    
    Admin only endpoint.
    
    Filters:
    - status: pending, approved, rejected, invited
    - search: Search by name or email
    """
    try:
        status_value = status_filter.value if status_filter else None
        items, total_count, has_next = vb_service.list_interest_submissions(
            status=status_value,
            search=search,
            page=page,
            page_size=page_size,
        )
        
        # Convert to list items
        list_items = [
            VBInterestSubmissionListItem(
                id=item["id"],
                full_name=item["full_name"],
                work_email=item["work_email"],
                primary_role=item["primary_role"],
                coaching_experience=item["coaching_experience"],
                support_areas=item.get("support_areas", []),
                industries_of_focus=item.get("industries_of_focus", []),
                weekly_availability=item["weekly_availability"],
                hourly_rate_usd=item["hourly_rate_usd"],
                status=item["status"],
                created_at=item["created_at"],
            )
            for item in items
        ]
        
        return {
            "success": True,
            "data": VBInterestSubmissionListResponse(
                items=list_items,
                total=total_count,
                page=page,
                page_size=page_size,
                has_next=has_next,
            ).model_dump(),
            "error": None,
        }
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list submissions: {str(e)}",
        )


@router.get(
    "/admin/interest/{submission_id}",
    summary="Get Submission Details",
    description="Admin endpoint to get full details of an interest submission.",
)
async def get_interest_submission(
    submission_id: UUID,
    current_user: dict = Depends(get_admin_user),
):
    """
    Get full details of a VB interest submission.
    
    Admin only endpoint.
    """
    try:
        submission = vb_service.get_interest_submission_by_id(str(submission_id))
        
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submission {submission_id} not found",
            )
        
        return {
            "success": True,
            "data": VBInterestSubmissionResponse(
                id=submission["id"],
                full_name=submission["full_name"],
                work_email=submission["work_email"],
                phone_country_code=submission["phone_country_code"],
                phone_number=submission["phone_number"],
                country=submission["country"],
                city=submission["city"],
                primary_role=submission["primary_role"],
                company_organization=submission.get("company_organization"),
                linkedin_url=submission["linkedin_url"],
                personal_website=submission.get("personal_website"),
                has_founded_venture=submission["has_founded_venture"],
                ventures_founded_count=submission.get("ventures_founded_count"),
                ventures_stage_reached=submission.get("ventures_stage_reached"),
                ventures_outcome=submission.get("ventures_outcome"),
                coaching_experience=submission["coaching_experience"],
                programs_worked_with=submission.get("programs_worked_with"),
                support_areas=submission.get("support_areas", []),
                support_areas_other=submission.get("support_areas_other"),
                industries_of_focus=submission.get("industries_of_focus", []),
                industries_other=submission.get("industries_other"),
                founder_stages=submission.get("founder_stages", []),
                founder_stages_other=submission.get("founder_stages_other"),
                geographies=submission.get("geographies", []),
                geographies_specific_countries=submission.get("geographies_specific_countries"),
                languages=submission.get("languages", []),
                languages_other=submission.get("languages_other"),
                weekly_availability=submission["weekly_availability"],
                weekly_availability_other=submission.get("weekly_availability_other"),
                hourly_rate_usd=submission["hourly_rate_usd"],
                status=submission["status"],
                reviewed_by=submission.get("reviewed_by"),
                reviewed_at=submission.get("reviewed_at"),
                admin_notes=submission.get("admin_notes"),
                rejection_reason=submission.get("rejection_reason"),
                vb_invitation_id=submission.get("vb_invitation_id"),
                created_at=submission["created_at"],
                updated_at=submission["updated_at"],
            ).model_dump(),
            "error": None,
        }
    except HTTPException:
        raise
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get submission: {str(e)}",
        )


@router.post(
    "/admin/interest/{submission_id}/approve",
    summary="Approve Submission",
    description="Admin endpoint to approve an interest submission and send VB invitation.",
)
async def approve_interest_submission(
    submission_id: UUID,
    request: VBInterestApproveRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Approve a VB interest submission and send invitation.
    
    Admin only endpoint.
    
    This will:
    1. Update submission status to 'approved'
    2. Create and send a VB invitation email
    3. Update submission status to 'invited'
    4. Link the invitation to the submission
    """
    try:
        result = vb_service.approve_interest_submission(
            submission_id=str(submission_id),
            admin_user_id=current_user["user_id"],
            admin_notes=request.admin_notes,
        )
        
        return {
            "success": True,
            "data": VBInterestApproveResponse(
                submission_id=result["submission_id"],
                status=result["status"],
                invitation_sent=result["invitation_sent"],
                invitation_token=result.get("invitation_token"),
                message=result["message"],
            ).model_dump(),
            "error": None,
        }
    except VBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except VBValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve submission: {str(e)}",
        )


@router.post(
    "/admin/interest/{submission_id}/reject",
    summary="Reject Submission",
    description="Admin endpoint to reject an interest submission and send rejection email.",
)
async def reject_interest_submission(
    submission_id: UUID,
    request: VBInterestRejectRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Reject a VB interest submission.
    
    Admin only endpoint.
    
    This will update the submission status to 'rejected' and send a 
    rejection notification email to the applicant.
    """
    try:
        result = vb_service.reject_interest_submission(
            submission_id=str(submission_id),
            admin_user_id=current_user["user_id"],
            admin_notes=request.admin_notes,
        )
        
        return {
            "success": True,
            "data": VBInterestRejectResponse(
                submission_id=result["submission_id"],
                status=result["status"],
                message=result["message"],
            ).model_dump(),
            "error": None,
        }
    except VBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except VBValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject submission: {str(e)}",
        )


@router.patch(
    "/admin/interest/{submission_id}/notes",
    summary="Update Admin Notes",
    description="Admin endpoint to update notes on an interest submission.",
)
async def update_submission_notes(
    submission_id: UUID,
    request: VBInterestNotesUpdate,
    current_user: dict = Depends(get_admin_user),
):
    """
    Update admin notes on a VB interest submission.
    
    Admin only endpoint.
    
    Can be used to add follow-up notes or internal comments.
    """
    try:
        result = vb_service.update_interest_submission_notes(
            submission_id=str(submission_id),
            admin_notes=request.admin_notes,
        )
        
        return {
            "success": True,
            "data": {
                "submission_id": str(submission_id),
                "admin_notes": result.get("admin_notes"),
                "message": "Notes updated successfully",
            },
            "error": None,
        }
    except VBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.message),
        )
    except VBBaseException as e:
        handle_vb_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notes: {str(e)}",
        )
