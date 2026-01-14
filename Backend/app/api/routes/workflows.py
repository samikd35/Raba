"""RABA Workflows API Routes.

Endpoints for retrieving workflow status and results.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.workflow import WorkflowOutput, WorkflowStatus
from app.services.supabase import get_workflow_repository
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/{workflow_id}",
    response_model=WorkflowOutput,
    summary="Get workflow status",
    description="Retrieve the current status and outputs of a workflow.",
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
    logger.info("=" * 60)
    logger.info("GET WORKFLOW - Starting")
    logger.info(f"  Workflow ID: {workflow_id}")
    logger.info("=" * 60)
    
    try:
        repo = get_workflow_repository()
        workflow = await repo.get_by_id(workflow_id)
    except ValueError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    if not workflow:
        logger.warning(f"Workflow not found: {workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}"
        )
    
    logger.info(f"Workflow found: {workflow_id}")
    logger.info(f"  Status: {workflow.get('status')}")
    logger.info(f"  Topic: {workflow.get('topic', '')[:50]}...")
    
    generation_time = None
    if workflow.get("completed_at") and workflow.get("created_at"):
        pass
    
    logger.info("GET WORKFLOW - Completed")
    
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
        generated_images=workflow.get("generated_images"),
        video_url=workflow.get("video_output", {}).get("video_url") if workflow.get("video_output") else None,
        error=workflow.get("error"),
        created_at=workflow["created_at"],
        updated_at=workflow["updated_at"],
        completed_at=workflow.get("completed_at"),
        generation_time_seconds=generation_time,
    )


@router.get(
    "",
    summary="List workflows",
    description="List all workflows (paginated).",
)
async def list_workflows(limit: int = 20, offset: int = 0):
    """
    List workflows with pagination.
    
    Args:
        limit: Maximum number of workflows to return
        offset: Number of workflows to skip
        
    Returns:
        List of workflows
    """
    logger.info("=" * 60)
    logger.info("LIST WORKFLOWS - Starting")
    logger.info(f"  Limit: {limit}, Offset: {offset}")
    logger.info("=" * 60)
    
    logger.info("LIST WORKFLOWS - Completed (stub response)")
    
    return {
        "workflows": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "message": "List endpoint - full implementation in Phase 2"
    }
