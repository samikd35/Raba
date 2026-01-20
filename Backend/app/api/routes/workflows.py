"""RABA Workflows API Routes.

Endpoints for retrieving workflow status and results.
Includes full CRUD operations with pagination and filtering.

Reference: RABA_Architecture.md Section 3 - Data Flow
Phase 4.5.2 Implementation
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.models.workflow import WorkflowOutput, WorkflowStatus
from app.services.supabase import get_workflow_repository, get_supabase_service
from app.services.workflow_runner import run_workflow_continue_background
from app.utils.helpers import utc_now_iso
from app.utils.logging import (
    get_logger,
    log_header,
    log_key_value,
    log_request_start,
    log_request_end,
    log_success,
    log_error_msg,
    log_warning_msg,
    log_workflow_event,
    log_operation,
    log_subheader,
)
import time

logger = get_logger(__name__)
router = APIRouter()


def _calculate_generation_time(created_at: str, completed_at: Optional[str]) -> Optional[float]:
    """Calculate generation time in seconds from timestamps."""
    if not completed_at or not created_at:
        return None
    
    try:
        # Parse ISO format timestamps
        if isinstance(created_at, str):
            start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            start = created_at
            
        if isinstance(completed_at, str):
            end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        else:
            end = completed_at
            
        delta = end - start
        return round(delta.total_seconds(), 2)
    except Exception:
        return None


@router.get(
    "/{workflow_id}",
    response_model=WorkflowOutput,
    summary="Get workflow status",
    description="Retrieve the current status and outputs of a workflow.",
    tags=["video-generation"],
)
async def get_workflow(workflow_id: str) -> WorkflowOutput:
    """
    Get workflow status and results by ID.
    
    Args:
        workflow_id: Workflow UUID
        
    Returns:
        Workflow status and available outputs
        
    Raises:
        HTTPException: If workflow not found
    """
    start_time = time.time()
    log_request_start(logger, "GET", f"/api/v1/workflows/{workflow_id}")
    
    try:
        with log_operation(logger, "Fetch workflow from database"):
            repo = get_workflow_repository()
            workflow = await repo.get_by_id(workflow_id)
    except ValueError as e:
        log_error_msg(logger, f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    if not workflow:
        log_warning_msg(logger, f"Workflow not found: {workflow_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}", 404, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}"
        )
    
    log_workflow_event(logger, workflow_id, "Workflow retrieved", {
        "status": workflow.get('status'),
        "has_video": bool(workflow.get('video_output')),
        "has_images": bool(workflow.get('generated_images')),
    })
    
    # Prevent access to soft-deleted workflows
    if workflow.get("deleted_at"):
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}", 404, duration_ms)
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Calculate generation time
    generation_time = _calculate_generation_time(
        workflow.get("created_at"),
        workflow.get("completed_at"),
    )
    
    # Extract video URL from video_output
    video_url = None
    if workflow.get("video_output"):
        video_output = workflow["video_output"]
        if isinstance(video_output, dict):
            video_url = video_output.get("video_url")
    
    # Extract generated image URLs - handle multiple nested structures
    generated_images = None
    if workflow.get("generated_images"):
        gen_images = workflow["generated_images"]
        if isinstance(gen_images, list):
            # Direct array of URLs or objects
            generated_images = []
            for img in gen_images:
                if isinstance(img, str):
                    generated_images.append(img)
                elif isinstance(img, dict):
                    # Try various URL fields
                    url = img.get("url") or img.get("image_url") or img.get("storage_url")
                    if url:
                        generated_images.append(url)
        elif isinstance(gen_images, dict):
            # Check for nested arrays
            if "image_urls" in gen_images:
                generated_images = gen_images["image_urls"]
            elif "all_image_urls" in gen_images:
                generated_images = gen_images["all_image_urls"]
            elif "images" in gen_images:
                # Array of image objects
                images = gen_images["images"]
                if isinstance(images, list):
                    generated_images = []
                    for img in images:
                        if isinstance(img, str):
                            generated_images.append(img)
                        elif isinstance(img, dict):
                            url = img.get("url") or img.get("image_url") or img.get("storage_url")
                            if url:
                                generated_images.append(url)
    
    # Extract character_reference_sheet
    character_reference_sheet = workflow.get("character_reference_sheet")
    
    # Extract tool_selection - check multiple sources
    tool_selection = workflow.get("tool_selection")
    
    # If not in tool_selection field, check hitl_gate_outputs
    if not tool_selection:
        hitl_gate_outputs = workflow.get("hitl_gate_outputs", {})
        if isinstance(hitl_gate_outputs, dict):
            gate_output = hitl_gate_outputs.get("tool_selection")
            if gate_output and isinstance(gate_output, dict):
                # Reconstruct tool_selection from gate output structure
                tool_selection = {
                    "selected_tool": gate_output.get("selected_tool"),
                    "intent_metadata": gate_output.get("intent_metadata"),
                    "tool_execution_params": gate_output.get("tool_execution_params"),
                    "confidence": gate_output.get("confidence"),
                    "selection_reasoning": gate_output.get("selection_reasoning"),
                }
                # Also check if selected_tool is nested
                if not tool_selection.get("selected_tool") and gate_output.get("selected_tool"):
                    tool_selection["selected_tool"] = gate_output.get("selected_tool")
    
    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}", 200, duration_ms)
    
    return WorkflowOutput(
        workflow_id=workflow["id"],
        status=WorkflowStatus(workflow["status"]),
        topic=workflow["topic"],
        duration_seconds=workflow["duration_seconds"],
        aspect_ratio=workflow["aspect_ratio"],
        resolution=workflow["resolution"],
        category=workflow["category"],
        hitl_mode=workflow["hitl_mode"],
        enable_audio=workflow.get("enable_audio", True),
        enable_subtitles=workflow.get("enable_subtitles", False),
        current_hitl_gate=workflow.get("current_hitl_gate"),
        tool_selection=tool_selection,
        research_output=workflow.get("research_output"),
        script_output=workflow.get("script_output"),
        character_reference_sheet=character_reference_sheet,
        generated_images=generated_images,
        video_url=video_url,
        error=workflow.get("error"),
        created_at=workflow["created_at"],
        updated_at=workflow["updated_at"],
        completed_at=workflow.get("completed_at"),
        generation_time_seconds=generation_time,
    )


@router.get(
    "",
    summary="List workflows",
    description="List all workflows with pagination and optional filtering.",
    tags=["video-generation"],
)
async def list_workflows(
    limit: int = Query(default=20, ge=1, le=100, description="Max workflows to return"),
    offset: int = Query(default=0, ge=0, description="Number to skip"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    include_deleted: bool = Query(default=False, description="Include soft-deleted workflows"),
):
    """
    List workflows with pagination and filtering.
    
    Args:
        limit: Maximum number of workflows to return (1-100)
        offset: Number of workflows to skip
        status_filter: Optional status filter (pending, running, completed, failed)
        
    Returns:
        Paginated list of workflows with metadata
    """
    start_time = time.time()
    log_request_start(logger, "GET", "/api/v1/workflows", {
        "limit": limit,
        "offset": offset,
        "status_filter": status_filter or "all",
        "include_deleted": include_deleted,
    })
    
    try:
        repo = get_workflow_repository()
        
        # Get workflows with optional status filter
        result = await repo.list(
            limit=limit,
            offset=offset,
            status_filter=status_filter,
        )
        
        workflows = result.get("data", [])
        # Exclude soft-deleted records unless requested
        if not include_deleted:
            workflows = [w for w in workflows if not w.get("deleted_at")]
        total = result.get("count", len(workflows))
        
        # Transform to output format
        workflow_list = []
        for w in workflows:
            generation_time = _calculate_generation_time(
                w.get("created_at"),
                w.get("completed_at"),
            )
            
            workflow_list.append({
                "workflow_id": w["id"],
                "status": w["status"],
                "topic": w["topic"][:100] + "..." if len(w.get("topic", "")) > 100 else w.get("topic", ""),
                "category": w.get("category"),
                "created_at": w["created_at"],
                "completed_at": w.get("completed_at"),
                "generation_time_seconds": generation_time,
                "has_video": bool(w.get("video_output")),
            })
        
        log_success(logger, f"Listed {len(workflow_list)} workflows (total: {total})")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", "/api/v1/workflows", 200, duration_ms)
        
        return {
            "workflows": workflow_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }
        
    except ValueError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workflows"
        )


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow (soft)",
    description="Soft delete the workflow and optionally purge associated media.",
    tags=["video-generation"],
)
async def delete_workflow(
    workflow_id: str,
    purge_media: bool = Query(default=True, description="Also delete stored media files and media records"),
):
    """Soft delete a workflow by ID, with optional media purge."""
    start_time = time.time()
    log_request_start(logger, "DELETE", f"/api/v1/workflows/{workflow_id}", {"purge_media": purge_media})

    repo = get_workflow_repository()
    svc = get_supabase_service()

    # Ensure workflow exists
    workflow = await repo.get_by_id(workflow_id)
    if not workflow:
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "DELETE", f"/api/v1/workflows/{workflow_id}", 404, duration_ms)
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Purge media first so DB record still holds references if needed
    if purge_media:
        try:
            with log_operation(logger, "Purge workflow storage"):
                purge_result = await svc.purge_workflow_storage(workflow_id)
                log_success(logger, f"Storage purged: {sum(purge_result.values())} files")
            with log_operation(logger, "Delete media records"):
                deleted_rows = await svc.delete_media_records(workflow_id)
                log_success(logger, f"Media records deleted: {deleted_rows}")
        except Exception as e:
            log_warning_msg(logger, f"Media purge failed (continuing with soft delete): {e}")

    # Soft delete: mark deleted_at timestamp
    try:
        await repo.update(workflow_id, {"deleted_at": utc_now_iso()})
    except Exception as e:
        log_error_msg(logger, f"Failed to mark workflow deleted: {e}")
        raise HTTPException(status_code=503, detail="Database service unavailable")

    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "DELETE", f"/api/v1/workflows/{workflow_id}", 204, duration_ms)
    return None


@router.post(
    "/{workflow_id}/continue",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Continue failed workflow",
    description="Resume a failed workflow from the last successfully persisted step. "
    "Persisted outputs (tool_selection, research_output, script_output, character_reference_sheet, "
    "generated_images, video_output) are loaded into state; nodes skip work when their output exists.",
    tags=["video-generation"],
)
async def continue_workflow(workflow_id: str, background_tasks: BackgroundTasks):
    """Start a continue-from-failed run for a workflow. Only allowed when status is 'failed'."""
    start_time = time.time()
    log_request_start(logger, "POST", f"/api/v1/workflows/{workflow_id}/continue")

    repo = get_workflow_repository()
    workflow = await repo.get_by_id(workflow_id)
    if not workflow:
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/continue", 404, duration_ms)
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.get("deleted_at"):
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/continue", 404, duration_ms)
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.get("status") != "failed":
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/continue", 400, duration_ms)
        raise HTTPException(
            status_code=400,
            detail=f"Only failed workflows can be continued. Current status: {workflow.get('status')}",
        )

    background_tasks.add_task(run_workflow_continue_background, workflow_id)
    log_workflow_event(logger, workflow_id, "Continue from failed started")
    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/continue", 202, duration_ms)
    return {"workflow_id": workflow_id, "message": "Continue started", "status": "running"}


@router.post(
    "/{workflow_id}/purge-media",
    summary="Purge workflow media",
    description="Delete all stored media files and media table records for a workflow.",
    tags=["video-generation"],
)
async def purge_workflow_media(workflow_id: str):
    """Purge stored media for a workflow without deleting the workflow record."""
    start_time = time.time()
    log_request_start(logger, "POST", f"/api/v1/workflows/{workflow_id}/purge-media")

    repo = get_workflow_repository()
    svc = get_supabase_service()

    workflow = await repo.get_by_id(workflow_id)
    if not workflow:
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/purge-media", 404, duration_ms)
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        storage_result = await svc.purge_workflow_storage(workflow_id)
        media_deleted = await svc.delete_media_records(workflow_id)
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/purge-media", 200, duration_ms)
        return {
            "workflow_id": workflow_id,
            "storage_deleted": storage_result,
            "media_records_deleted": media_deleted,
        }
    except Exception as e:
        log_error_msg(logger, f"Failed to purge media: {e}")
        raise HTTPException(status_code=500, detail="Failed to purge media")
