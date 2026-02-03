"""
API Endpoints for MVP Requirements Generator (AMRG)

Endpoints:
- POST /projects/{project_id}/amrg/runs - Start PRD generation
- POST /amrg/runs/{run_id}/answers - Submit answers to questions
- GET /amrg/runs/{run_id} - Get run status
- GET /projects/{project_id}/amrg/results - Get PRD results
- GET /projects/{project_id}/amrg/history - Get PRD version history
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel

from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.features.dependencies import resolve_feature_id
from src.mint.api.credit.service import CreditService

from ..models.enums import ResearchMode, RunStatus
from ..models.response_models import (
    AMRGGenerateRequest,
    AMRGGenerateResponse,
    AMRGAnswersRequest,
    AMRGStatusResponse,
    AMRGResultsResponse,
    AMRGHistoryResponse,
    ErrorResponse,
    EligibilityErrorResponse
)
from ..services.amrg_workflow import get_amrg_workflow
from ..services.database_adapter import get_amrg_database_adapter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mvp",
    tags=["MVP Requirements Generator"]
)


# ==================== ENDPOINT 1: Start PRD Generation ====================

@router.post(
    "/projects/{project_id}/amrg/runs",
    response_model=AMRGGenerateResponse,
    responses={
        200: {"description": "Run started, questions returned"},
        400: {"model": EligibilityErrorResponse, "description": "Missing required artifacts"},
        402: {"description": "Insufficient credits"},
        404: {"description": "Project not found"}
    }
)
async def start_amrg_run(
    project_id: str,
    request: AMRGGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start MVP Requirements Generator run.
    
    This endpoint:
    1. Validates project has required artifacts (VPS v1/v2, BMC v1/v2, Critique)
    2. Performs coarse template routing
    3. Generates 3 clarifying questions
    4. Returns questions for user to answer
    
    Use the /answers endpoint to submit answers and continue generation.
    """
    try:
        project_id = project_id.strip()
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("user_id")
        plan_type = current_user.get("tenant_type", "individual")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        logger.info(f"🚀 AMRG run requested for project {project_id}")
        logger.info(f"   User: {user_id}, Tenant: {tenant_id}")
        
        # Credit check
        credit_service = CreditService()
        try:
            feature_id = await resolve_feature_id("mvp_requirements")
        except HTTPException:
            # Feature not registered yet - allow for development
            feature_id = None
            logger.warning("mvp_requirements feature not registered, skipping credit check")
        
        if feature_id and not is_super_admin:
            if not credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            ):
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits for MVP requirements generation"
                )
        
        # Check for existing run if not force regenerate
        if not request.force_regenerate:
            db_adapter = get_amrg_database_adapter()
            current_run = db_adapter.get_current_amrg_run(project_id, tenant_id)
            
            if current_run and current_run.get("status") == RunStatus.COMPLETED.value:
                logger.info("   ✅ PRD already exists, returning existing run")
                return AMRGGenerateResponse(
                    success=True,
                    run_id=current_run.get("run_id"),
                    status=RunStatus.COMPLETED.value,
                    message="PRD already exists. Use force_regenerate=true to regenerate."
                )
        
        # Start workflow
        workflow = get_amrg_workflow()
        result = await workflow.start_run(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            research_mode=request.research_mode
        )
        
        if not result.get("success"):
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            
            if error_code == "MISSING_REQUIRED_ARTIFACTS":
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_code": error_code,
                        "message": "Project is missing required artifacts",
                        "missing_artifacts": result.get("missing_artifacts", []),
                        "artifact_details": result.get("artifact_details", [])
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error_code": error_code,
                        "message": result.get("message", "Unknown error")
                    }
                )
        
        logger.info(f"   ✅ Run {result['run_id']} started")
        
        return AMRGGenerateResponse(
            success=True,
            run_id=result["run_id"],
            status=result["status"],
            message=result["message"],
            coarse_routing=result.get("coarse_routing"),
            questions=result.get("questions"),
            estimated_completion_seconds=result.get("estimated_completion_seconds", 60)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Start AMRG run failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error_code": "START_FAILED", "message": str(e)}
        )


# ==================== ENDPOINT 2: Submit Answers ====================

@router.post(
    "/amrg/runs/{run_id}/answers",
    response_model=AMRGResultsResponse,
    responses={
        200: {"description": "PRD generated successfully"},
        400: {"description": "Invalid answers or run state"},
        404: {"description": "Run not found"}
    }
)
async def submit_amrg_answers(
    run_id: str,
    request: AMRGAnswersRequest,
    project_id: str = Query(..., description="Project ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit answers to clarifying questions and generate PRD.
    
    Requires exactly 3 answers corresponding to the 3 questions.
    After submission, PRD generation begins immediately.
    """
    try:
        run_id = run_id.strip()
        project_id = project_id.strip()
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"📝 Submitting answers for run {run_id}")
        
        # Validate answer count
        if len(request.answers) != 3:
            raise HTTPException(
                status_code=400,
                detail={"error": "Exactly 3 answers required"}
            )
        
        # Continue workflow with answers
        workflow = get_amrg_workflow()
        result = await workflow.continue_with_answers(
            project_id=project_id,
            tenant_id=tenant_id,
            run_id=run_id,
            answers=request.answers
        )
        
        if not result.get("success"):
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            
            if error_code == "RUN_NOT_FOUND":
                raise HTTPException(status_code=404, detail=result)
            elif error_code == "INVALID_STATUS":
                raise HTTPException(status_code=400, detail=result)
            else:
                raise HTTPException(status_code=500, detail=result)
        
        logger.info(f"   ✅ PRD generated for run {run_id}")
        
        # Build prd_metadata with defaults for missing fields
        prd_metadata = result.get("prd_metadata") or {}
        prd_json = result.get("prd_json") or {}
        
        return AMRGResultsResponse(
            success=True,
            run_id=run_id,
            project_id=project_id,
            status=result["status"],
            prd_json=prd_json,
            prd_metadata={
                "template_code": prd_metadata.get("template_code") or prd_json.get("template_code", "unknown"),
                "template_name": prd_metadata.get("template_name") or prd_json.get("template_code"),
                "template_version": prd_metadata.get("template_version") or prd_json.get("template_version"),
                "schema_version": prd_metadata.get("schema_version") or prd_json.get("schema_version"),
                "generated_at": datetime.fromisoformat(prd_metadata["generated_at"]) if prd_metadata.get("generated_at") else datetime.utcnow(),
                "research_used": prd_metadata.get("research_used", False),
                "research_sources_count": prd_metadata.get("research_sources_count")
            },
            validation_status=result.get("validation_status"),
            validation_warnings=result.get("validation_warnings"),
            version=result.get("version", 1),
            completed_at=datetime.fromisoformat(result["completed_at"]) if result.get("completed_at") else datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Submit answers failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error_code": "ANSWERS_FAILED", "message": str(e)}
        )


# ==================== ENDPOINT 3: Get Run Status ====================

@router.get(
    "/amrg/runs/{run_id}",
    response_model=AMRGStatusResponse,
    responses={
        200: {"description": "Run status retrieved"},
        404: {"description": "Run not found"}
    }
)
async def get_amrg_status(
    run_id: str,
    project_id: str = Query(..., description="Project ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of an AMRG run.
    """
    try:
        run_id = run_id.strip()
        project_id = project_id.strip()
        tenant_id = current_user.get("tenant_id")
        
        workflow = get_amrg_workflow()
        result = workflow.get_run_status(project_id, tenant_id, run_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result)
        
        return AMRGStatusResponse(
            run_id=run_id,
            project_id=project_id,
            status=result["status"],
            created_at=datetime.fromisoformat(result["created_at"]),
            updated_at=datetime.fromisoformat(result["updated_at"]),
            completed_at=datetime.fromisoformat(result["completed_at"]) if result.get("completed_at") else None,
            prd_available=result.get("prd_available", False),
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get status failed: {e}")
        raise HTTPException(status_code=500, detail={"message": str(e)})


# ==================== ENDPOINT 4: Get PRD Results ====================

@router.get(
    "/projects/{project_id}/amrg/results",
    response_model=AMRGResultsResponse,
    responses={
        200: {"description": "PRD results retrieved"},
        404: {"description": "No PRD found"}
    }
)
async def get_amrg_results(
    project_id: str,
    version: Optional[str] = Query(None, description="PRD version number or run_id (latest if not specified)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get generated PRD results.
    
    Returns the latest PRD by default, or specific version/run if specified.
    Accepts either version number (e.g., "1") or run_id UUID.
    """
    try:
        project_id = project_id.strip()
        tenant_id = current_user.get("tenant_id")
        
        db_adapter = get_amrg_database_adapter()
        
        # Determine if version is an int or a run_id UUID
        version_int = None
        run_id = None
        
        if version:
            try:
                version_int = int(version)
            except ValueError:
                # Not an int, treat as run_id
                run_id = version
        
        output = db_adapter.get_amrg_output(project_id, tenant_id, version=version_int, run_id=run_id)
        
        if not output:
            raise HTTPException(
                status_code=404,
                detail={"message": "No PRD found for this project"}
            )
        
        prd_json = output.get("prd_json", {})
        validation_report = output.get("validation_report", {})
        
        return AMRGResultsResponse(
            success=True,
            run_id=output.get("run_id"),
            project_id=project_id,
            status=RunStatus.COMPLETED.value,
            prd_json=prd_json,
            prd_metadata={
                "template_code": prd_json.get("template_code"),
                "template_name": prd_json.get("template_code"),  # Could enhance with spec lookup
                "template_version": prd_json.get("template_version"),
                "schema_version": prd_json.get("schema_version"),
                "generated_at": datetime.fromisoformat(output.get("created_at")) if output.get("created_at") else None,
                "research_used": prd_json.get("research") is not None
            },
            validation_status=validation_report.get("status"),
            validation_warnings=validation_report.get("warnings", []),
            version=output.get("version", 1),
            completed_at=datetime.fromisoformat(output.get("created_at")) if output.get("created_at") else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get results failed: {e}")
        raise HTTPException(status_code=500, detail={"message": str(e)})


# ==================== ENDPOINT 5: Get PRD History ====================

@router.get(
    "/projects/{project_id}/amrg/history",
    response_model=AMRGHistoryResponse,
    responses={
        200: {"description": "PRD history retrieved"}
    }
)
async def get_amrg_history(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get PRD version history for a project.
    """
    try:
        project_id = project_id.strip()
        tenant_id = current_user.get("tenant_id")
        
        db_adapter = get_amrg_database_adapter()
        history = db_adapter.get_amrg_history(project_id, tenant_id)
        
        return AMRGHistoryResponse(
            project_id=project_id,
            total_versions=len(history),
            versions=[
                {
                    "version": h["version"],
                    "template_code": h.get("template_code", "unknown"),
                    "generated_at": datetime.fromisoformat(h["created_at"]) if h.get("created_at") else datetime.utcnow(),
                    "validation_status": h.get("validation_status", "unknown"),
                    "is_current": h.get("is_current", False)
                }
                for h in history
            ]
        )
        
    except Exception as e:
        logger.error(f"❌ Get history failed: {e}")
        raise HTTPException(status_code=500, detail={"message": str(e)})
