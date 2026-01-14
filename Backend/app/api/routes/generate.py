"""RABA Generate API Routes.

Endpoints for creating new video generation workflows.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.workflow import (
    WorkflowCreateResponse,
    WorkflowInput,
    WorkflowStatus,
)
from app.services.supabase import get_workflow_repository
from app.utils.helpers import generate_workflow_id, utc_now_iso
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=WorkflowCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create video generation workflow",
    description="Start a new video generation workflow with the given parameters.",
)
async def create_workflow(input_data: WorkflowInput) -> WorkflowCreateResponse:
    """
    Create a new video generation workflow.
    
    This endpoint validates the input and creates a workflow record.
    The actual generation is handled asynchronously by the LangGraph workflow.
    
    Args:
        input_data: Workflow input parameters
        
    Returns:
        Workflow creation response with ID and status
    """
    logger.info("=" * 60)
    logger.info("CREATE WORKFLOW - Starting")
    logger.info(f"  Topic: {input_data.topic[:50]}...")
    logger.info(f"  Duration: {input_data.duration_seconds}s")
    logger.info(f"  Aspect Ratio: {input_data.aspect_ratio.value}")
    logger.info(f"  Resolution: {input_data.resolution.value}")
    logger.info(f"  Category: {input_data.category.value}")
    logger.info(f"  HITL Mode: {input_data.hitl_mode.value}")
    logger.info("=" * 60)
    
    workflow_id = generate_workflow_id()
    logger.info(f"Generated workflow ID: {workflow_id}")
    
    workflow_data = {
        "id": workflow_id,
        "status": WorkflowStatus.PENDING.value,
        "topic": input_data.topic,
        "duration_seconds": input_data.duration_seconds,
        "aspect_ratio": input_data.aspect_ratio.value,
        "resolution": input_data.resolution.value,
        "category": input_data.category.value,
        "hitl_mode": input_data.hitl_mode.value,
        "enable_audio": input_data.enable_audio,
        "enable_subtitles": input_data.enable_subtitles,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    
    try:
        logger.info("Saving workflow to database...")
        repo = get_workflow_repository()
        await repo.create(workflow_data)
        logger.info(f"Workflow saved successfully: {workflow_id}")
    except ValueError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error creating workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow"
        )
    
    logger.info("CREATE WORKFLOW - Completed")
    logger.info(f"  Workflow ID: {workflow_id}")
    logger.info(f"  Status: {WorkflowStatus.PENDING.value}")
    
    return WorkflowCreateResponse(
        workflow_id=workflow_id,
        status=WorkflowStatus.PENDING,
        message="Workflow created successfully. Video generation will start shortly.",
    )
