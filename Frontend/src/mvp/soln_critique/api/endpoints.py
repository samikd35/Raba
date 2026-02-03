"""
API endpoints for Solution Critique feature
"""
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any

from src.mint.api.auth_v2.utils import get_current_user
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter
from ..models.response_models import (
    CritiqueGenerateRequest,
    CritiqueGenerateResponse,
    CritiqueStatusResponse,
    CritiqueResultsResponse,
    CritiqueMetadata,
    ErrorResponse
)
from ..services.critique_workflow import SolutionCritiqueWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/mvp/projects",
    tags=["MVP - Value Proposition"]
)


# ==================== ENDPOINT 1: Generate Critique ====================

@router.post(
    "/{project_id}/solution-critique/generate",
    response_model=CritiqueGenerateResponse,
    responses={
        202: {"description": "Critique generation started (async)"},
        400: {"model": ErrorResponse, "description": "Missing required data"},
        404: {"model": ErrorResponse, "description": "Project not found"}
    }
)
async def generate_solution_critique(
    project_id: str,
    request: CritiqueGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate solution critique with web research and AI analysis
    
    This endpoint triggers async critique generation using:
    - VPC v2 (Value Proposition Canvas)
    - VPS (Value Proposition Statement)
    - BMC (Business Model Canvas)
    - Web research via Brave Search
    - 5 parallel critique dimensions
    - Synthesized JSON report with citations
    
    **Process:**
    1. Validates all required data exists
    2. Starts async background processing
    3. Returns immediately with session_id
    4. Use status endpoint to check progress
    5. Use results endpoint to get final report
    
    **Estimated completion:** 45-60 seconds
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("user_id")
        plan_type = current_user.get("tenant_type", "individual")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        logger.info(f"🚀 Solution critique requested for project {project_id}")
        logger.info(f"   User: {user_id}, Tenant: {tenant_id}")
        logger.info(f"   Force regenerate: {request.force_regenerate}")
        
        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id
        from src.mint.api.credit.service import CreditService
        credit_service = CreditService()
        feature_id = await resolve_feature_id("solution_critique")
        
        if not is_super_admin:
            if not credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            ):
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits for solution critique generation"
                )
        
        # Check if critique already exists (unless force_regenerate)
        if not request.force_regenerate:
            db_adapter = MVPDatabaseAdapter(use_service_role=True)
            project_data = db_adapter.get_project(project_id, tenant_id)
            
            if project_data and project_data.get('soln_critique_data'):
                critique_data = project_data['soln_critique_data']
                if critique_data.get('status') == 'completed':
                    logger.info("   ✅ Critique already exists, returning existing session")
                    return CritiqueGenerateResponse(
                        success=True,
                        session_id=critique_data.get('session_id', 'existing'),
                        status='completed',
                        message='Solution critique already exists. Use force_regenerate=true to regenerate.',
                        estimated_completion_seconds=0
                    )
        
        # Validate project exists and has required data
        validation_error = _validate_project_data(project_id, tenant_id)
        if validation_error:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "missing_required_data",
                    "message": validation_error,
                    "details": {"missing": _extract_missing_data(validation_error)}
                }
            )
        
        # Generate session_id
        import uuid
        from datetime import datetime
        session_id = str(uuid.uuid4())
        
        # CRITICAL: ALWAYS mark critique as "processing" BEFORE starting background task
        # This prevents /status and /results endpoints from returning stale data
        # This is MANDATORY - if this fails, we must abort the request
        try:
            db_adapter = MVPDatabaseAdapter(use_service_role=True)
            
            # Build the new critique state - clears old report completely
            new_critique_state = {
                'session_id': session_id,
                'status': 'processing',
                'started_at': datetime.utcnow().isoformat(),
                'regeneration_requested': request.force_regenerate,
                'critique_report': None,  # CRITICAL: Clear old report to prevent stale data
                'completed_at': None,
                'error': None
            }
            
            response = db_adapter.supabase.client.table('vmp_projects').update({
                'soln_critique_data': new_critique_state,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                raise Exception("Database update returned no data - update may have failed")
            
            logger.info(f"   ✅ Database marked as 'processing', old critique cleared")
            logger.info(f"   Session ID: {session_id}")
            
        except Exception as e:
            logger.error(f"   ❌ CRITICAL: Failed to clear existing critique data: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "database_update_failed",
                    "message": f"Failed to prepare for regeneration: {str(e)}. Please try again."
                }
            )
        
        # Start background task
        background_tasks.add_task(
            _run_critique_workflow,
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            plan_type=plan_type,
            is_super_admin=is_super_admin,
            feature_id=feature_id
        )
        
        logger.info(f"   ✅ Background task started with session {session_id}")
        
        return CritiqueGenerateResponse(
            success=True,
            session_id=session_id,
            status='processing',
            message='Solution critique generation started',
            estimated_completion_seconds=60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Generate critique failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "generation_failed",
                "message": f"Failed to start critique generation: {str(e)}"
            }
        )


# ==================== ENDPOINT 2: Check Status ====================

@router.get(
    "/{project_id}/solution-critique/status",
    response_model=CritiqueStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Critique not found"}
    }
)
async def get_critique_status(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check solution critique generation status
    
    Returns:
    - **processing**: Critique is being generated
    - **completed**: Critique is ready (use results endpoint)
    - **failed**: Generation failed (check error field)
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"📊 Status check for project {project_id}")
        
        # Load project data
        db_adapter = MVPDatabaseAdapter(use_service_role=True)
        project_data = db_adapter.get_project(project_id, tenant_id)
        
        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if critique exists
        critique_data = project_data.get('soln_critique_data')
        
        if not critique_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "critique_not_found",
                    "message": "No solution critique found for this project. Generate one first."
                }
            )
        
        # Extract status info
        status = critique_data.get('status', 'unknown')
        session_id = critique_data.get('session_id', 'unknown')
        started_at = critique_data.get('generated_at')
        completed_at = critique_data.get('completed_at')
        error = critique_data.get('error')
        
        logger.info(f"   Status: {status}")
        
        return CritiqueStatusResponse(
            success=True,
            status=status,
            session_id=session_id,
            started_at=started_at,
            completed_at=completed_at,
            error=error
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "status_check_failed",
                "message": str(e)
            }
        )


# ==================== ENDPOINT 3: Get Results ====================

@router.get(
    "/{project_id}/solution-critique/results",
    response_model=CritiqueResultsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Critique not found or not completed"}
    }
)
async def get_critique_results(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete solution critique results
    
    Returns structured JSON report with:
    - Executive summary with overall viability assessment
    - Critiques by dimension (5 dimensions)
    - All critiques with citations [1][2][3]
    - Global sources list (numbered)
    - Prioritized actions (immediate/short_term/long_term)
    - Metadata (queries executed, sources analyzed, etc.)
    
    **Note:** Only available when status is 'completed'
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"📄 Results request for project {project_id}")
        
        # Load project data
        db_adapter = MVPDatabaseAdapter(use_service_role=True)
        project_data = db_adapter.get_project(project_id, tenant_id)
        
        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if critique exists
        critique_data = project_data.get('soln_critique_data')
        
        if not critique_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "critique_not_found",
                    "message": "No solution critique found. Generate one first."
                }
            )
        
        # Check if completed
        status = critique_data.get('status')
        if status != 'completed':
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "critique_not_ready",
                    "message": f"Critique is not ready. Current status: {status}. Wait for completion."
                }
            )
        
        # Extract report
        report = critique_data.get('critique_report')
        
        if not report:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "report_missing",
                    "message": "Critique completed but report data is missing"
                }
            )
        
        # Build metadata
        metadata = CritiqueMetadata(
            generated_at=report.get('generated_at', ''),
            total_sources=report.get('metadata', {}).get('total_sources', 0),
            total_citations=report.get('metadata', {}).get('total_citations', 0),
            ai_model=report.get('metadata', {}).get('ai_model', 'Azure OpenAI gpt-5-mini'),
            processing_time_seconds=None
        )
        
        logger.info(f"   ✅ Returning complete critique report")
        logger.info(f"      Total critiques: {len(report.get('all_critiques', []))}")
        logger.info(f"      Total sources: {metadata.total_sources}")
        logger.info(f"      Total citations: {metadata.total_citations}")
        
        return CritiqueResultsResponse(
            success=True,
            data=report,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Results retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "results_retrieval_failed",
                "message": str(e)
            }
        )


# ==================== HELPER FUNCTIONS ====================

def _validate_project_data(project_id: str, tenant_id: str) -> str | None:
    """
    Validate that project has all required data (VPC, VPS, BMC)
    Returns error message if validation fails, None if success
    """
    try:
        db_adapter = MVPDatabaseAdapter(use_service_role=True)
        
        # Load project
        project_data = db_adapter.get_project(project_id, tenant_id)
        if not project_data:
            return "Project not found"
        
        # Load MVP data
        mvp_data = db_adapter.get_mvp_data(project_id, tenant_id)
        if not mvp_data:
            return "MVP data not found. Please ensure VPS and BMC are generated."
        
        # Check VPS
        vps_v2 = mvp_data.get('vps_v2')
        vps_v1 = mvp_data.get('vps_v1')
        if not vps_v2 and not vps_v1:
            return "VPS not generated. Please generate VPS before running solution critique."
        
        # Check BMC
        bmc = mvp_data.get('bmc')
        if not bmc:
            return "BMC not generated. Please complete BMC before running solution critique."
        
        # Check VPC (VPC 2.0 support - flexible validation)
        # Note: VPC validation is lenient - we proceed even with incomplete VPC
        # as the critique can still be valuable based on VPS and BMC alone
        vpc_data = project_data.get('vpc_data', {})
        
        # Ensure vpc_data is a dict
        if not isinstance(vpc_data, dict):
            vpc_data = {}
        
        # VPC is optional - we log but don't fail if missing
        # The critique workflow will proceed with empty VPC data
        
        return None  # All validations passed
        
    except Exception as e:
        return f"Validation failed: {str(e)}"


def _extract_missing_data(error_message: str) -> list[str]:
    """Extract missing data types from error message"""
    missing = []
    if 'VPS' in error_message:
        missing.append('vps')
    if 'BMC' in error_message:
        missing.append('bmc')
    if 'VPC' in error_message:
        missing.append('vpc')
    return missing


async def _run_critique_workflow(
    project_id: str,
    tenant_id: str,
    user_id: str,
    session_id: str,
    plan_type: str = "individual",
    is_super_admin: bool = False,
    feature_id: str = None
):
    """Background task to run critique workflow"""
    try:
        logger.info(f"🔄 Starting critique workflow background task")
        logger.info(f"   Project: {project_id}, Session: {session_id}")
        
        # Initialize workflow
        workflow = SolutionCritiqueWorkflow()
        
        # Run workflow
        await workflow.run_critique(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        logger.info(f"✅ Critique workflow completed successfully")
        
        # Consume credits after successful completion (skip for super admins)
        if not is_super_admin and feature_id:
            try:
                import uuid
                from src.mint.api.credit.service import CreditService
                credit_service = CreditService()
                credit_service.consume_feature(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=str(uuid.uuid4()),
                    reason="Solution critique generation",
                    project_id=project_id,
                    metadata={"session_id": session_id}
                )
                logger.info(f"✅ Consumed 1 credit for solution critique")
            except Exception as credit_error:
                logger.error(f"❌ Failed to consume credits: {credit_error}")
        
    except Exception as e:
        logger.error(f"❌ Critique workflow failed: {e}")
        
        # Save error to database
        try:
            db_adapter = MVPDatabaseAdapter(use_service_role=True)
            from datetime import datetime
            error_data = {
                'session_id': session_id,
                'status': 'failed',
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }
            
            db_adapter.supabase.client.table('vmp_projects').update({
                'soln_critique_data': error_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
        except Exception as save_error:
            logger.error(f"Failed to save error to database: {save_error}")
