"""
FastAPI Endpoints for GTM Strategy Generator

Provides endpoints to:
- Trigger GTM generation (async)
- Get generated GTM strategy
- List GTM versions
- Get generation status
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from src.mint.api.auth_v2.utils import get_current_user

from ..models import (
    GenerateGTMRequest,
    GenerateGTMResponse,
    GTMPackResponse,
    GTMVersionListResponse,
    GTMVersionSummary,
    GTMStatusResponse,
    GTMStepContent,
    ProjectCitation,
    WebCitation,
)
from ..adapters.database_adapter import GTMDatabaseAdapter, get_gtm_database_adapter
from ..workflow.gtm_workflow import run_gtm_generation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mav/projects", tags=["GTM Strategy Generator"])


# ============================================================================
# BACKGROUND TASK
# ============================================================================

async def _generate_gtm_background(
    project_id: str,
    tenant_id: str,
    user_id: str,
    context_constraints: dict
):
    """Background task for GTM generation."""
    try:
        logger.info(f"🚀 GTM API: Starting background generation for project {project_id}")
        
        # Update status to processing
        db_adapter = get_gtm_database_adapter()
        await db_adapter.update_gtm_status(project_id, tenant_id, "processing")
        
        # Run generation
        result = await run_gtm_generation(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            context_constraints=context_constraints
        )
        
        if result.get("generation_status") == "completed":
            logger.info(f"✅ GTM API: Generation completed for project {project_id}")
            
            # Trigger background chunking for the GTM output
            await _trigger_gtm_chunking(project_id, tenant_id, result.get("gtm_pack"))
        else:
            logger.error(f"❌ GTM API: Generation failed for project {project_id}: {result.get('error_message')}")
            await db_adapter.update_gtm_status(
                project_id, tenant_id, "failed", result.get("error_message")
            )
            
    except Exception as e:
        logger.error(f"❌ GTM API: Background generation error: {e}")
        try:
            db_adapter = get_gtm_database_adapter()
            await db_adapter.update_gtm_status(project_id, tenant_id, "failed", str(e))
        except:
            pass


async def _trigger_gtm_chunking(
    project_id: str,
    tenant_id: str,
    gtm_pack: Optional[Dict[str, Any]]
):
    """Trigger background chunking for the GTM output."""
    if not gtm_pack:
        return
    
    try:
        from src.vpm.services.project_chunking_service import (
            VMPProjectChunkingService,
            VMPFeatureType
        )
        
        chunking_service = VMPProjectChunkingService()
        
        # Check if GTM feature type exists
        if hasattr(VMPFeatureType, 'GTM'):
            await chunking_service.chunk_feature_background(
                project_id=project_id,
                tenant_id=tenant_id,
                feature_type=VMPFeatureType.GTM,
                feature_data={"gtm_pack": gtm_pack}
            )
            logger.info(f"🔄 GTM API: Triggered background chunking for project {project_id}")
        else:
            logger.info(f"ℹ️ GTM API: GTM chunking not available (VMPFeatureType.GTM not defined)")
            
    except Exception as e:
        logger.warning(f"⚠️ GTM API: Failed to trigger chunking: {e}")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/{project_id}/gtm/generate",
    response_model=GenerateGTMResponse,
    summary="Generate GTM Strategy",
    description="Trigger GTM strategy generation for a project. All parameters are optional - context is inferred from project artifacts via RAG."
)
async def generate_gtm_strategy(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    request: Optional[GenerateGTMRequest] = None
):
    """
    Trigger GTM strategy generation.
    
    All request parameters are **optional**. The generator will use RAG to infer:
    - Geography focus from personas/market research
    - Timeline from project stage/MVP requirements
    - Target segments from customer profiles
    - Product stage from project artifacts
    
    Optional constraints can be provided to override or refine the inferred values.
    """
    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    # Verify project access
    db_adapter = get_gtm_database_adapter()
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get next version number
    next_version = await db_adapter.get_next_version(project_id, tenant_id)
    
    # Build context constraints from request (all optional overrides)
    context_constraints = {}
    if request:
        if request.geography_focus:
            context_constraints["geography_focus"] = request.geography_focus
        if request.launch_timeline:
            context_constraints["launch_timeline"] = request.launch_timeline
        if request.budget_band:
            context_constraints["budget_band"] = request.budget_band
        if request.target_segment_priority:
            context_constraints["target_segment_priority"] = request.target_segment_priority
        if request.deck_purpose_alignment:
            context_constraints["deck_purpose_alignment"] = request.deck_purpose_alignment
        if request.product_stage:
            context_constraints["product_stage"] = request.product_stage
    
    # Update status and start background task
    await db_adapter.update_gtm_status(project_id, tenant_id, "processing")
    
    background_tasks.add_task(
        _generate_gtm_background,
        project_id,
        tenant_id,
        user_id,
        context_constraints
    )
    
    logger.info(f"🚀 GTM API: Triggered generation for project {project_id}, version {next_version}")
    
    return GenerateGTMResponse(
        gtm_id=project_id,
        version=next_version,
        status="processing",
        message=f"GTM strategy generation started. Version {next_version} will be created."
    )


@router.get(
    "/{project_id}/gtm",
    response_model=GTMPackResponse,
    summary="Get GTM Strategy",
    description="Get the latest or a specific version of the GTM strategy."
)
async def get_gtm_strategy(
    project_id: str,
    version: Optional[int] = Query(None, description="Specific version number, or latest if not provided"),
    current_user: dict = Depends(get_current_user)
):
    """Get GTM strategy content."""
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = get_gtm_database_adapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get GTM version
    gtm = await db_adapter.get_gtm_version(project_id, tenant_id, version)
    
    if not gtm:
        raise HTTPException(
            status_code=404,
            detail="No GTM strategy found. Generate one first."
        )
    
    # Convert steps to response model
    steps = []
    for s in gtm.get("steps", []):
        steps.append(GTMStepContent(
            step=s.get("step", 0),
            name=s.get("name", ""),
            content=s.get("content", {}),
            description=s.get("description", ""),
            sources_used=s.get("sources_used", []),
            assumptions_applied=s.get("assumptions_applied", [])
        ))
    
    # Convert sources
    sources: List[Union[ProjectCitation, WebCitation]] = []
    for src in gtm.get("sources", []):
        if src.get("type") == "project":
            sources.append(ProjectCitation(
                id=src.get("id", ""),
                artifact_ref=src.get("artifact_ref", ""),
                artifact_version=src.get("artifact_version"),
                chunk_ref=src.get("chunk_ref", ""),
                snippet=src.get("snippet", "")
            ))
        elif src.get("type") == "web":
            sources.append(WebCitation(
                id=src.get("id", ""),
                url=src.get("url", ""),
                title=src.get("title", ""),
                domain=src.get("domain", ""),
                snippet=src.get("snippet", ""),
                fetched_at=src.get("fetched_at", "")
            ))
    
    return GTMPackResponse(
        project_id=project_id,
        version=gtm.get("version", 1),
        summary=gtm.get("summary", ""),
        steps=steps,
        channel_plan=gtm.get("channel_plan", {}),
        customer_success_motion=gtm.get("customer_success_motion", {}),
        metrics_plan=gtm.get("metrics_plan", {}),
        execution_plan_30_60_90=gtm.get("execution_plan_30_60_90", {}),
        experiment_backlog=gtm.get("experiment_backlog", {}),
        sources=sources,
        created_at=gtm.get("created_at", ""),
        created_by=gtm.get("created_by"),
        run_trace=gtm.get("run_trace")
    )


@router.get(
    "/{project_id}/gtm/versions",
    response_model=GTMVersionListResponse,
    summary="List GTM Versions",
    description="List all GTM strategy versions for a project."
)
async def list_gtm_versions(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all GTM versions."""
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = get_gtm_database_adapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get versions
    versions = await db_adapter.list_gtm_versions(project_id, tenant_id)
    gtm_data = await db_adapter.get_gtm_data(project_id, tenant_id)
    
    return GTMVersionListResponse(
        project_id=project_id,
        current_version=gtm_data.get("current_version", 0),
        versions=[GTMVersionSummary(**v) for v in versions],
        total_count=len(versions)
    )


@router.get(
    "/{project_id}/gtm/status",
    response_model=GTMStatusResponse,
    summary="Get Generation Status",
    description="Get the current status of GTM strategy generation."
)
async def get_gtm_status(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get GTM generation status."""
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = get_gtm_database_adapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get project to check status
    project = await db_adapter.load_project_context(project_id, tenant_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    status = project.get("gtm_status", "not_started")
    gtm_data = project.get("gtm_data", {})
    current_version = gtm_data.get("current_version", 0) if gtm_data else 0
    
    # Get progress info if processing
    progress = None
    if status == "processing":
        progress = {"message": "Generating GTM strategy..."}
    
    # Build message
    if status == "not_started":
        message = "No GTM strategy has been generated yet."
    elif status == "processing":
        message = "GTM strategy generation is in progress."
    elif status == "completed":
        message = f"GTM strategy generation completed. Latest version: {current_version}"
    else:
        message = "GTM strategy generation failed."
    
    return GTMStatusResponse(
        project_id=project_id,
        version=current_version,
        status=status,
        message=message,
        progress=progress
    )


@router.get(
    "/{project_id}/gtm/summary",
    summary="Get GTM Summary",
    description="Get a summary of the latest GTM strategy (lightweight)."
)
async def get_gtm_summary(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a lightweight summary of the GTM strategy.
    
    Returns just the summary and step names without full content.
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = get_gtm_database_adapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get latest GTM
    gtm = await db_adapter.get_gtm_version(project_id, tenant_id)
    
    if not gtm:
        raise HTTPException(
            status_code=404,
            detail="No GTM strategy found."
        )
    
    # Build lightweight summary
    steps_summary = []
    for s in gtm.get("steps", []):
        steps_summary.append({
            "step": s.get("step"),
            "name": s.get("name"),
            "decisions_count": len(s.get("content", {}).get("decisions", [])),
            "has_experiments": len(s.get("content", {}).get("experiments", [])) > 0
        })
    
    return {
        "project_id": project_id,
        "version": gtm.get("version", 1),
        "summary": gtm.get("summary", ""),
        "steps_summary": steps_summary,
        "has_channel_plan": bool(gtm.get("channel_plan")),
        "has_execution_plan": bool(gtm.get("execution_plan_30_60_90")),
        "has_metrics_plan": bool(gtm.get("metrics_plan")),
        "sources_count": len(gtm.get("sources", [])),
        "created_at": gtm.get("created_at"),
        "status": gtm.get("status", "completed")
    }
