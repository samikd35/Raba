"""
Workflow API Endpoints - Separated from Monolithic Structure
============================================================

This module contains all workflow-related endpoints that were previously
embedded in the monolithic app.py file. This separation improves:

1. ✅ Code maintainability and readability
2. ✅ Testing capabilities (isolated endpoint testing)
3. ✅ Deployment flexibility (can be deployed separately)
4. ✅ Clear separation of concerns

Endpoints included:
- POST /workflow - Start new workflow
- GET /status/{session_id} - Get workflow status
- POST /answers/{session_id} - Submit clarification answers
- GET /report/{session_id} - Get final report
- Market validation specific endpoints
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, status)
from src.mint.api.auth_v2.utils import get_admin_user, get_current_user
from src.mint.api.credit.service import (CreditService,
                                         InsufficientCreditsError,
                                         InvalidConsumptionRequest)

# Credit system removed
# from ....api.credit.credit_service import CreditService
from ....models.workflow_models import (ClarificationAnswer, WorkflowReport,
                                        WorkflowRequest, WorkflowStatus)
from ....models.sharing_models import (
    CreateShareRequest, UpdateShareRequest, AccessShareRequest,
    RevokeShareRequest, CreateShareResponse, ShareListResponse,
    UpdateShareResponse, RevokeShareResponse, AccessShareResponse,
    ShareAnalyticsResponse, AccessLogsResponse
)
# Import business logic services (separated from endpoints)
from ....services.workflow_service import WorkflowService
from ....services.sharing_service import SharingService

# Import production auth system (compat shim at mint/api/production_auth_system.py)

# Configure logging
logger = logging.getLogger(__name__)

# Create router for workflow endpoints
router = APIRouter(tags=["workflow"])

# Initialize services
workflow_service = WorkflowService()
sharing_service = SharingService(use_service_role=True)

credit_service = CreditService()


# ==========================================
# WORKFLOW ENDPOINTS
# ==========================================


@router.post("/jobs", response_model=WorkflowStatus)
async def start_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Start a new market intelligence workflow.

    This endpoint initiates a new workflow session and returns immediately
    with a session ID. The actual workflow runs as a background task.
    """
    try:
        # Hardcoded feature for workflow system
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("Problem Validator")
        
        # Extract user info from authenticated JWT token (not from request body)
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user["tenant_type"]

        # ---- Pre-check: ensure sufficient credits for the feature ----
        # Super admins bypass credit checks
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Get user token for RLS enforcement
        user_token = getattr(fastapi_request.state, "raw_token", None)

        # Start workflow as background task
        background_tasks.add_task(
            workflow_service.run_workflow_task,
            session_id=session_id,
            query=request.query,
            user_id=user_id,
            user_token=user_token,
            interactive=request.interactive,
        )

        # Super admins bypass credit consumption
        if not is_super_admin:
            try:
                credit_service.consume_feature(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=session_id,  # unique (tenant_id, request_id) prevents double-charge on retries
                    reason="workflow_start",
                    project_id=None,
                    workflow_id=None,
                    metadata={
                        "session_id": session_id,
                        "source": "workflow_start",
                        "query_preview": (request.query or "")[:200],
                        "interactive": bool(request.interactive),
                    },
                )
            except InsufficientCreditsError:
                # Race: credits drained after pre-check. Try to mark/abort the workflow if your service supports it.
                try:
                    # Optional compensation if you have such a hook:
                    # workflow_service.mark_workflow_failed(session_id, "Insufficient credits at deduction step")
                    pass
                except Exception:
                    logger.warning(
                        "Failed to mark workflow as failed after credit deduction error"
                    )
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "insufficient_credits",
                        "message": "Not enough credits to complete this request.",
                    },
                )
            except InvalidConsumptionRequest as e:
                try:
                    # Optional compensation hook, if available.
                    # workflow_service.mark_workflow_failed(session_id, f"Credit consumption error: {str(e)}")
                    pass
                except Exception:
                    logger.warning(
                        "Failed to mark workflow as failed after invalid consumption error"
                    )
                raise HTTPException(
                    status_code=400,
                detail={
                    "code": "invalid_consumption_request",
                    "message": str(e),
                },
            )

        logger.info(f"Workflow started: session_id={session_id}, user_id={user_id}")

        return WorkflowStatus(
            session_id=session_id,
            status="started",
            message="Workflow started successfully. Check status for progress.",
            last_updated=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "workflow_start_error",
                "message": "Failed to start workflow",
            },
        )


@router.get("/status/{session_id}", response_model=WorkflowStatus)
async def get_workflow_status(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a workflow session.

    Returns the workflow progress, current status, and any clarification
    questions that need to be answered.
    """
    user_id = current_user["user_id"]
    try:
        # Get workflow status from service
        status = await workflow_service.get_workflow_status(session_id, user_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "session_not_found",
                    "message": f"Workflow session {session_id} not found",
                },
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "status_retrieval_error",
                "message": "Failed to retrieve workflow status",
            },
        )


@router.post("/answers/{session_id}", response_model=WorkflowStatus)
async def submit_clarification_answers(
    session_id: str,
    answers: ClarificationAnswer,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit answers to clarification questions and continue the workflow.

    This endpoint accepts answers to clarification questions and resumes
    the workflow processing as a background task.
    """
    user_id = current_user["user_id"]
    try:
        # Validate session ownership
        session_valid = await workflow_service.validate_session_ownership(
            session_id, user_id
        )
        if not session_valid:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "session_not_found",
                    "message": f"Workflow session {session_id} not found or access denied",
                },
            )

        # Submit answers and continue workflow
        background_tasks.add_task(
            workflow_service.process_clarification_answers,
            session_id=session_id,
            answers=answers.answers,
            user_id=user_id,
        )

        logger.info(
            f"Clarification answers submitted: session_id={session_id}, user_id={user_id}"
        )

        return WorkflowStatus(
            session_id=session_id,
            status="processing",
            message="Answers submitted successfully. Workflow continuing.",
            last_updated=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answers for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "answer_submission_error",
                "message": "Failed to submit clarification answers",
            },
        )


@router.get("/report/{session_id}", response_model=WorkflowReport)
async def get_workflow_report(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get the complete market intelligence report for a workflow session.

    Returns the final report with all components including analysis,
    insights, and recommendations.
    """
    user_id = current_user["user_id"]
    try:
        # Get complete workflow report
        report = await workflow_service.get_workflow_report(session_id, user_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "report_not_found",
                    "message": f"Report for session {session_id} not found or not ready",
                },
            )

        # Check if report is complete
        if report.status != "completed":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "report_not_ready",
                    "message": f"Report is not ready yet. Current status: {report.status}",
                },
            )

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "report_retrieval_error",
                "message": "Failed to retrieve workflow report",
            },
        )


@router.get("/debug/{session_id}")
async def debug_workflow(
    session_id: str,
    current_user: dict = Depends(get_admin_user),
):
    """
    Debug endpoint for workflow troubleshooting.

    Only available to admin users for debugging workflow issues.
    """
    user_id = current_user["user_id"]
    try:
        # Get detailed workflow debug information
        debug_info = await workflow_service.get_workflow_debug_info(session_id, user_id)

        return {
            "session_id": session_id,
            "debug_info": debug_info,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting debug info for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "debug_error",
                "message": "Failed to retrieve debug information",
            },
        )


# ==========================================
# UTILITY ENDPOINTS
# ==========================================


@router.get("/health")
async def workflow_health_check():
    """
    Health check endpoint for workflow service.

    Returns the current health status of the workflow system.
    """
    try:
        health_status = await workflow_service.get_health_status()

        return {
            "status": "healthy",
            "service": "workflow",
            "health_details": health_status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Workflow health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "workflow",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/metrics")
async def workflow_metrics(current_user: dict = Depends(get_admin_user)):
    """
    Get workflow system metrics.

    Available to admin users for monitoring and analytics.
    """
    try:
        metrics = await workflow_service.get_system_metrics()

        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting workflow metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "metrics_error",
                "message": "Failed to retrieve workflow metrics",
            },
        )


# ==========================================
# REPORT SHARING ENDPOINTS
# ==========================================


@router.post("/share", response_model=CreateShareResponse)
async def create_report_share(
    request: CreateShareRequest,
    fastapi_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a shareable link for a problem validation report.
    
    This endpoint allows users to share their PV reports with external stakeholders
    via a secure, optionally password-protected link.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        # Get frontend URL from environment variable, fallback to request base URL
        frontend_url = os.getenv("FRONTEND_URL")
        if frontend_url:
            base_url = frontend_url.rstrip('/')
            logger.info(f"Using frontend URL from environment: {base_url}")
        else:
            base_url = str(fastapi_request.base_url).rstrip('/')
            logger.warning(f"FRONTEND_URL not set, using request base URL: {base_url}")
        
        logger.info(f"Creating share link for session {request.session_id} by user {user_id}")
        logger.info(f"🔍 ENDPOINT DEBUG: user_id={user_id}, tenant_id={tenant_id}")
        
        result = await sharing_service.create_share(
            request=request,
            user_id=user_id,
            tenant_id=tenant_id,
            base_url=base_url
        )
        
        logger.info(f"🔍 ENDPOINT DEBUG: Share result success={result.success}, message={result.message}")
        
        if not result.success:
            logger.error(f"❌ ENDPOINT: Share creation failed: {result.message}")
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "share_creation_failed",
                    "message": result.message,
                },
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ENDPOINT EXCEPTION: {str(e)}")
        logger.error(f"❌ ENDPOINT EXCEPTION type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ ENDPOINT TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "share_creation_error",
                "message": f"Failed to create share link: {str(e)}",
            },
        )


@router.get("/shares", response_model=ShareListResponse)
async def list_report_shares(
    session_id: Optional[str] = None,
    include_revoked: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """
    List all share links created by the current user.
    
    Optionally filter by session ID or include revoked shares.
    """
    try:
        user_id = current_user["user_id"]
        
        result = await sharing_service.list_shares(
            user_id=user_id,
            session_id=session_id,
            include_revoked=include_revoked
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing shares: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "share_list_error",
                "message": "Failed to list shares",
            },
        )


@router.put("/share/{share_id}", response_model=UpdateShareResponse)
async def update_report_share(
    share_id: str,
    request: UpdateShareRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update settings for an existing share link.
    
    Allows updating access type, password, expiration, and other settings.
    """
    try:
        user_id = current_user["user_id"]
        
        result = await sharing_service.update_share(
            share_id=share_id,
            request=request,
            user_id=user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "share_update_failed",
                    "message": result.message,
                },
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating share: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "share_update_error",
                "message": "Failed to update share",
            },
        )


@router.delete("/share", response_model=RevokeShareResponse)
async def revoke_report_share(
    request: RevokeShareRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Revoke a share link, preventing further access.
    
    This action cannot be undone.
    """
    try:
        user_id = current_user["user_id"]
        
        result = await sharing_service.revoke_share(
            request=request,
            user_id=user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "share_revoke_failed",
                    "message": result.message,
                },
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking share: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "share_revoke_error",
                "message": "Failed to revoke share",
            },
        )


@router.post("/share/access", response_model=AccessShareResponse)
async def access_shared_report(
    request: AccessShareRequest,
    fastapi_request: Request,
):
    """
    Access a shared report using a share token.
    
    This endpoint is public (no authentication required) and allows
    anyone with a valid share token to access the report.
    """
    try:
        # Get accessor IP and user agent for logging
        accessor_ip = fastapi_request.client.host if fastapi_request.client else None
        user_agent = fastapi_request.headers.get("user-agent")
        
        result = await sharing_service.access_shared_report(
            request=request,
            accessor_ip=accessor_ip,
            user_agent=user_agent
        )
        
        if not result.success:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "access_denied",
                    "message": result.message,
                },
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing shared report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "share_access_error",
                "message": "Failed to access shared report",
            },
        )


@router.get("/share/{share_id}/analytics", response_model=ShareAnalyticsResponse)
async def get_share_analytics(
    share_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get analytics for a share link.
    
    Returns view counts, unique accessors, and access patterns.
    """
    try:
        user_id = current_user["user_id"]
        
        result = await sharing_service.get_share_analytics(
            share_id=share_id,
            user_id=user_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "analytics_not_found",
                    "message": result.message,
                },
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting share analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "analytics_error",
                "message": "Failed to retrieve analytics",
            },
        )


@router.get("/share/{share_id}/logs", response_model=AccessLogsResponse)
async def get_share_access_logs(
    share_id: str,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """
    Get access logs for a share link.
    
    Returns detailed logs of who accessed the shared report and when.
    """
    try:
        user_id = current_user["user_id"]
        
        result = await sharing_service.get_access_logs(
            share_id=share_id,
            user_id=user_id,
            limit=limit
        )
        
        if not result.success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "logs_not_found",
                    "message": result.message,
                },
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting access logs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "logs_error",
                "message": "Failed to retrieve access logs",
            },
        )


# ==========================================
# REPORT DOWNLOAD ENDPOINTS (PREMIUM FEATURE)
# ==========================================

from fastapi.responses import StreamingResponse


@router.get("/report/{session_id}/download")
async def download_pv_report_pdf(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Download Problem Validation Report as a branded PDF.
    
    **PREMIUM FEATURE**: This endpoint is only available to users with purchased
    or granted credits. Users on free trial CANNOT download PDF reports.
    
    The PDF includes:
    - Yuba logo in header
    - Brand colors throughout
    - yubanow.com link in footer
    - Professional formatting of all report sections
    
    Args:
        session_id: The workflow session ID for the PV report
        
    Returns:
        StreamingResponse: PDF file download
        
    Raises:
        403 Forbidden: If user only has trial credits (free trial users)
        404 Not Found: If report doesn't exist or workflow not completed
        500 Internal Server Error: If PDF generation fails
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        logger.info(f"📥 PDF Download request: session_id={session_id}, user_id={user_id}")
        
        # ===== ACCESS CHECK: Admins, org members, or paid credits =====
        user_roles = current_user.get("roles", [])
        tenant_type = current_user.get("tenant_type", "individual")
        is_super_admin = len(user_roles) > 0 and user_roles[0] in ["super_admin", "admin"]
        
        # Check if user is part of an ACTUAL organization (not individual tenant)
        # Only organization/team tenants grant download access - individual tenants do NOT
        is_org_member = (
            tenant_type in ["organization", "team"] and 
            tenant_id is not None and 
            len(user_roles) > 1 and 
            user_roles[1] in ["owner", "admin", "member", "team_leader"]
        )
        
        if is_super_admin:
            logger.info(f"✅ PDF Download access granted for admin user {user_id} (role: {user_roles[0]})")
        elif is_org_member:
            logger.info(f"✅ PDF Download access granted for org member {user_id} (tenant_type: {tenant_type}, org role: {user_roles[1]})")
        else:
            # ===== CREDIT CHECK: Only paid/granted credits allow download =====
            has_paid = credit_service.has_paid_credits(tenant_id)
            
            if not has_paid:
                # Get credit breakdown for detailed error message
                breakdown = credit_service.get_credit_breakdown(tenant_id)
                logger.warning(f"⛔ PDF Download denied - trial credits only. User: {user_id}, Breakdown: {breakdown}")
                
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "premium_feature_restricted",
                        "message": "PDF download is a premium feature. You need purchased or granted credits to download reports.",
                        "credit_info": {
                            "total_credits": breakdown.get("total_credits", 0),
                            "trial_credits": breakdown.get("trial_credits", 0),
                            "paid_credits": breakdown.get("paid_credits", 0),
                            "has_paid_credits": False
                        },
                        "action_required": "Purchase credits or request a grant from your organization admin to unlock this feature."
                    }
                )
            
            logger.info(f"✅ PDF Download access granted for user {user_id} (has paid credits)")
        
        # ===== FETCH REPORT DATA =====
        # Get workflow report to verify completion and get report data
        report = await workflow_service.get_workflow_report(session_id, user_id)
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "report_not_found",
                    "message": f"Report for session {session_id} not found",
                },
            )
        
        # Check if report is complete
        if report.status != "completed":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "report_not_ready",
                    "message": f"Report is not ready for download. Current status: {report.status}",
                },
            )
        
        # ===== PREPARE REPORT DATA FOR PDF =====
        # Extract report data from the workflow report
        report_data = {
            "title": getattr(report, 'title', None) or "Problem Validation Report",
            "executive_summary": getattr(report, 'executive_summary', None) or "",
            "industry_analysis": "",
            "challenges_analysis": "",  # PESTEL Analysis
            "recommendations": getattr(report, 'recommendations', None) or "",
            "sources": [],
            "industry": getattr(report, 'industry', None) or "",
            "geography": getattr(report, 'geography', None) or "",
            "target_audience": getattr(report, 'target_audience', None) or "",
            "created_at": getattr(report, 'created_at', None) or datetime.now().isoformat(),
        }
        
        # If report has a 'report' attribute (structured report), extract all fields
        if hasattr(report, 'report') and report.report:
            structured_report = report.report
            if isinstance(structured_report, dict):
                # Extract executive summary
                if not report_data["executive_summary"]:
                    report_data["executive_summary"] = structured_report.get("executive_summary", "") or structured_report.get("summary", "")
                
                # Extract industry analysis (with dynamic subsections)
                report_data["industry_analysis"] = structured_report.get("industry_analysis", "")
                
                # Extract PESTEL/challenges analysis (with dynamic subsections)
                report_data["challenges_analysis"] = structured_report.get("challenges_analysis", "")
                
                # Extract recommendations
                if not report_data["recommendations"]:
                    report_data["recommendations"] = structured_report.get("recommendations", "")
                
                # Extract sources (list of references with URLs)
                sources = structured_report.get("sources", [])
                if isinstance(sources, list):
                    report_data["sources"] = sources
                
                # Extract title
                if structured_report.get("title"):
                    report_data["title"] = structured_report.get("title")
                
                logger.info(f"📊 Extracted report sections: exec_summary={len(report_data['executive_summary'])} chars, "
                           f"industry={len(report_data['industry_analysis'])} chars, "
                           f"pestel={len(report_data['challenges_analysis'])} chars, "
                           f"recommendations={len(report_data['recommendations'])} chars, "
                           f"sources={len(report_data['sources'])} refs")
        
        # ===== GENERATE PDF =====
        from src.vpm.services.document_generator import YubaDocumentGenerator
        generator = YubaDocumentGenerator()
        
        report_title = report_data.get('title', 'Problem Validation Report')
        
        logger.info(f"📄 Generating PDF for session {session_id}")
        pdf_buffer = await generator.generate_pv_report_pdf(
            report_data=report_data,
            report_title=report_title
        )
        
        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in report_title)
        safe_title = safe_title[:50]  # Limit length
        filename = f"Yuba_PV_Report_{safe_title}_{session_id[:8]}.pdf"
        
        logger.info(f"✅ PDF generated successfully: {filename}")
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Session-Id": session_id,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF for session {session_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_generation_error",
                "message": "Failed to generate PDF report",
            },
        )


@router.get("/report/{session_id}/download/check")
async def check_download_eligibility(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Check if current user is eligible to download a PV report PDF.
    
    This endpoint allows the frontend to check eligibility before showing
    the download button, providing a better user experience.
    
    Args:
        session_id: The workflow session ID
        
    Returns:
        Dict with eligibility status and credit information
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        tenant_type = current_user.get("tenant_type", "individual")
        
        # Check for super admin bypass
        user_roles = current_user.get("roles", [])
        is_admin = len(user_roles) > 0 and user_roles[0] in ["super_admin", "admin"]
        
        # Check if user is part of an ACTUAL organization (not individual tenant)
        # Only organization/team tenants grant download access - individual tenants do NOT
        is_org_member = (
            tenant_type in ["organization", "team"] and 
            tenant_id is not None and 
            len(user_roles) > 1 and 
            user_roles[1] in ["owner", "admin", "member", "team_leader"]
        )
        
        # Check paid credits (admins and org members bypass this)
        has_paid = is_admin or is_org_member or credit_service.has_paid_credits(tenant_id)
        breakdown = credit_service.get_credit_breakdown(tenant_id)
        
        # Check if report exists and is completed
        report_ready = False
        report_exists = False
        
        try:
            report = await workflow_service.get_workflow_report(session_id, user_id)
            if report:
                report_exists = True
                report_ready = report.status == "completed"
        except Exception:
            pass
        
        return {
            "success": True,
            "session_id": session_id,
            "can_download": has_paid and report_ready,
            "eligibility": {
                "has_paid_credits": has_paid,
                "is_admin": is_admin,
                "is_org_member": is_org_member,
                "report_exists": report_exists,
                "report_ready": report_ready,
            },
            "credit_info": {
                "total_credits": breakdown.get("total_credits", 0),
                "trial_credits": breakdown.get("trial_credits", 0),
                "paid_credits": breakdown.get("paid_credits", 0),
                "credit_sources": breakdown.get("credit_sources", {}),
            },
            "message": (
                "You can download this report as PDF." if (has_paid and report_ready)
                else "PDF download requires purchased or granted credits." if not has_paid
                else "Report is not ready for download yet." if not report_ready
                else "Report not found."
            )
        }
        
    except Exception as e:
        logger.error(f"Error checking download eligibility: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "eligibility_check_error",
                "message": "Failed to check download eligibility",
            },
        )
