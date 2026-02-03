from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from ..auth_v2.utils import get_admin_user
from .enum_suggestions_service import EnumSuggestionsService
from .models import (
    EnumSuggestionListResponse,
    EnumSuggestion,
    ApproveEnumSuggestionRequest,
    RejectEnumSuggestionRequest,
    EnumSuggestionStats
)

router = APIRouter(prefix="/profiles/admin/enum-suggestions", tags=["profiles.admin.enum-suggestions"])

suggestions_service = EnumSuggestionsService()


@router.get("/", response_model=EnumSuggestionListResponse)
def list_suggestions(
    enum_type: Optional[str] = Query(None, description="Filter by enum type"),
    status: Optional[str] = Query("pending", description="Filter by status (pending, approved, rejected)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    order_by: str = Query("times_suggested", description="Field to order by"),
    current_user: dict = Depends(get_admin_user),
):
    """
    List enum suggestions with filters.
    Only pending suggestions are shown by default.
    """
    offset = (page - 1) * page_size
    result = suggestions_service.list_suggestions(
        enum_type=enum_type,
        status=status,
        limit=page_size,
        offset=offset,
        order_by=order_by,
        order_desc=True
    )
    return result


@router.get("/stats")
def get_suggestion_stats(current_user: dict = Depends(get_admin_user)):
    """Get statistics about suggestions by type and status"""
    stats = suggestions_service.get_suggestion_stats()
    return {"items": stats}


@router.get("/top", response_model=EnumSuggestionListResponse)
def get_top_suggestions(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_admin_user),
):
    """Get the most frequently suggested values (pending only)"""
    items = suggestions_service.get_top_suggestions(limit=limit)
    return {"total": len(items), "items": items}


@router.get("/by-type/{enum_type}", response_model=EnumSuggestionListResponse)
def get_suggestions_by_type(
    enum_type: str,
    status: str = Query("pending"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_admin_user),
):
    """Get suggestions for a specific enum type"""
    items = suggestions_service.get_suggestions_by_type(
        enum_type=enum_type,
        status=status,
        limit=limit
    )
    return {"total": len(items), "items": items}


@router.get("/{suggestion_id}", response_model=EnumSuggestion)
def get_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(get_admin_user),
):
    """Get details of a specific suggestion"""
    suggestion = suggestions_service.get_suggestion(suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return suggestion


@router.post("/{suggestion_id}/approve")
def approve_suggestion(
    suggestion_id: str,
    request: ApproveEnumSuggestionRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Approve a suggestion and create the official enum entry.

    This will:
    1. Create a new entry in the appropriate enum table (profile_industries, etc.)
    2. Update the suggestion status to 'approved'
    3. Update all profile_versions that used this "other" value with the official enum name
    """
    try:
        enum_id = suggestions_service.approve_and_create_enum(
            suggestion_id=suggestion_id,
            enum_name=request.enum_name,
            reviewed_by=current_user.get("user_id"),
            enum_description=request.enum_description,
            admin_notes=request.admin_notes
        )

        if not enum_id:
            raise HTTPException(
                status_code=400,
                detail="Failed to approve suggestion. It may have already been processed."
            )

        return {
            "ok": True,
            "enum_id": enum_id,
            "message": f"Suggestion approved and '{request.enum_name}' added to enum options"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error approving suggestion: {str(e)}"
        )


@router.post("/{suggestion_id}/reject")
def reject_suggestion(
    suggestion_id: str,
    request: RejectEnumSuggestionRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Reject a suggestion with a reason.
    The "other" values in profiles will remain unchanged.
    """
    try:
        success = suggestions_service.reject_suggestion(
            suggestion_id=suggestion_id,
            reviewed_by=current_user.get("user_id"),
            admin_notes=request.admin_notes
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to reject suggestion. It may have already been processed or not found."
            )

        return {
            "ok": True,
            "message": "Suggestion rejected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error rejecting suggestion: {str(e)}"
        )
