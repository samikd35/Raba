"""RABA Workflows API Routes.

Endpoints for retrieving workflow status and results.
Includes full CRUD operations with pagination and filtering.

Reference: RABA_Architecture.md Section 3 - Data Flow
Phase 4.5.2 Implementation
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.models.workflow import WorkflowOutput, WorkflowStatus
from app.services.supabase import get_workflow_repository
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
    
    # Extract generated image URLs
    generated_images = None
    if workflow.get("generated_images"):
        gen_images = workflow["generated_images"]
        if isinstance(gen_images, dict):
            generated_images = gen_images.get("image_urls", [])
        elif isinstance(gen_images, list):
            generated_images = gen_images
    
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
        current_hitl_gate=workflow.get("current_hitl_gate"),
        tool_selection=workflow.get("tool_selection"),
        research_output=workflow.get("research_output"),
        script_output=workflow.get("script_output"),
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
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """
    List workflows with pagination and filtering.
    
    Args:
        limit: Maximum number of workflows to return (1-100)
        offset: Number of workflows to skip
        status: Optional status filter (pending, running, completed, failed)
        
    Returns:
        Paginated list of workflows with metadata
    """
    start_time = time.time()
    log_request_start(logger, "GET", "/api/v1/workflows", {
        "limit": limit,
        "offset": offset,
        "status_filter": status or "all",
    })
    
    try:
        repo = get_workflow_repository()
        
        # Get workflows with optional status filter
        result = await repo.list(
            limit=limit,
            offset=offset,
            status_filter=status,
        )
        
        workflows = result.get("data", [])
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
    summary="Delete workflow",
    description="Delete a workflow and its associated media.",
    tags=["video-generation"],
)
async def delete_workflow(workflow_id: str):
    """
    Delete a workflow by ID.
    
    This performs a soft delete (marks as deleted) and removes
    associated media from storage.
    
    Args:
        workflow_id: Workflow UUID to delete
        
    Raises:
        HTTPException: If workflow not found
    """
    start_time = time.time()
    log_request_start(logger, "DELETE", f"/api/v1/workflows/{workflow_id}")
    
    try:
        repo = get_workflow_repository()
        
        with log_operation(logger, "Check workflow exists"):
            workflow = await repo.get_by_id(workflow_id)
        
        if not workflow:
            log_warning_msg(logger, f"Workflow not found: {workflow_id}")
            duration_ms = (time.time() - start_time) * 1000
            log_request_end(logger, "DELETE", f"/api/v1/workflows/{workflow_id}", 404, duration_ms)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {workflow_id}"
            )
        
        with log_operation(logger, "Delete workflow record"):
            await repo.delete(workflow_id)
        
        log_workflow_event(logger, workflow_id, "Workflow deleted")
        log_success(logger, f"Workflow {workflow_id} deleted successfully")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "DELETE", f"/api/v1/workflows/{workflow_id}", 204, duration_ms)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow"
        )
