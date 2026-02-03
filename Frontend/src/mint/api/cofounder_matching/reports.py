import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth_v2.utils import get_admin_user, get_current_user
from .report_models import (
    CreateMessageReportRequest,
    CreateProfileReportRequest,
    CreateReportResponse,
    ListReportsResponse,
    ReportResponse,
    ReportStatsResponse,
    ResolveReportRequest,
    ResolveReportResponse,
)
from .reports_service import ReportsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles/reports", tags=["profiles.reports"])


# ============================================================
# User Endpoints - Create Reports
# ============================================================


@router.post("/profile", response_model=CreateReportResponse)
async def report_profile(
    payload: CreateProfileReportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Report a profile for policy violations.

    Any authenticated user can report a profile.
    """
    service = ReportsService()

    try:
        report = await service.create_profile_report(
            reporter_user_id=current_user["user_id"],
            reported_profile_id=payload.reported_profile_id,
            reason=payload.reason,
            description=payload.description,
        )

        return CreateReportResponse(
            success=True,
            message="Profile reported successfully",
            data=ReportResponse(**report),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/message", response_model=CreateReportResponse)
async def report_message(
    payload: CreateMessageReportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Report a message for policy violations.

    Any authenticated user can report a message.
    """
    service = ReportsService()

    try:
        report = await service.create_message_report(
            reporter_user_id=current_user["user_id"],
            message_id=payload.message_id,
            reason=payload.reason,
            description=payload.description,
        )

        return CreateReportResponse(
            success=True,
            message="Message reported successfully",
            data=ReportResponse(**report),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Admin Endpoints - View and Resolve Reports
# ============================================================


@router.get("/", response_model=ListReportsResponse)
async def list_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    report_type: Optional[str] = Query(None, description="Filter by type (PROFILE, MESSAGE)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    List all reports (admin only).

    Supports filtering by status and report type.
    """
    service = ReportsService()

    total, items = await service.list_reports(
        status=status,
        report_type=report_type,
        page=page,
        page_size=page_size,
    )

    return ListReportsResponse(
        success=True,
        message="Reports retrieved successfully",
        data=[ReportResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=ReportStatsResponse)
async def get_report_stats(
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    Get statistics about reports (admin only).

    Returns counts by status and reason.
    """
    service = ReportsService()

    stats = await service.get_report_stats()

    return ReportStatsResponse(**stats)


@router.get("/by-user/{user_id}", response_model=ListReportsResponse)
async def get_reports_by_user(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    Get all reports against a specific user (admin only).

    Returns all reports across all profiles and messages from this user.
    """
    service = ReportsService()

    total, items = await service.get_reports_by_user(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return ListReportsResponse(
        success=True,
        message=f"Reports for user {user_id} retrieved successfully",
        data=[ReportResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/by-profile/{profile_id}", response_model=ListReportsResponse)
async def get_reports_by_profile(
    profile_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    Get all reports against a specific profile (admin only).

    Returns all reports for this particular profile.
    """
    service = ReportsService()

    total, items = await service.get_reports_by_profile(
        profile_id=profile_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return ListReportsResponse(
        success=True,
        message=f"Reports for profile {profile_id} retrieved successfully",
        data=[ReportResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=CreateReportResponse)
async def get_report(
    report_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    Get a specific report by ID (admin only).
    """
    service = ReportsService()

    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return CreateReportResponse(
        success=True,
        message="Report retrieved successfully",
        data=ReportResponse(**report),
    )


@router.post("/{report_id}/resolve", response_model=ResolveReportResponse)
async def resolve_report(
    report_id: str,
    payload: ResolveReportRequest,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    Resolve a report (admin only).

    Updates the report status and adds admin notes.
    """
    service = ReportsService()

    try:
        report = await service.resolve_report(
            report_id=report_id,
            admin_user_id=admin_user["user_id"],
            status=payload.status,
            admin_notes=payload.admin_notes,
            action_taken=payload.action_taken,
        )

        return ResolveReportResponse(
            success=True,
            message="Report resolved successfully",
            data=ReportResponse(**report),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
