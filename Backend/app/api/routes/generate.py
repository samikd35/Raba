"""RABA Generate API Routes.

Endpoints for creating new video generation workflows.
Includes file upload support for reference images.

Reference: SRS.md FR-101 to FR-110 - User Input Requirements
Phase 4.5.1 Implementation
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.workflow import (
    AspectRatioEnum,
    CategoryEnum,
    HITLModeEnum,
    ResolutionEnum,
    VideoModelOption,
    WorkflowCreateResponse,
    WorkflowInput,
    WorkflowStatus,
)
from app.models.video import VideoModel
from app.services.supabase import get_supabase_client, get_workflow_repository
from app.utils.helpers import generate_workflow_id, utc_now_iso
from app.utils.logging import (
    get_logger,
    log_header,
    log_key_value,
    log_request_start,
    log_success,
    log_error_msg,
    log_workflow_event,
    log_operation,
)

logger = get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

MAX_FILE_SIZE_MB = 10
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _validate_and_upload_image(
    file: UploadFile,
    workflow_id: str,
) -> Optional[str]:
    """
    Validate and upload reference image to Supabase Storage.
    
    Args:
        file: Uploaded file
        workflow_id: Workflow ID for storage path
        
    Returns:
        Public URL of uploaded image, or None if no file
        
    Raises:
        HTTPException: If validation fails
    """
    if file is None or file.filename == "":
        return None
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    
    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    # Validate file size (FR-109: max 10MB)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
        )
    
    # Determine file extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        ext = "jpg"
    
    # Upload to Supabase Storage
    storage_path = f"reference_images/{workflow_id}/user_reference.{ext}"
    
    try:
        supabase = get_supabase_client()
        result = supabase.storage.from_("media").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("media").get_public_url(storage_path)
        logger.info(f"Reference image uploaded: {storage_path}")
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload reference image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload reference image"
        )


@router.post(
    "",
    response_model=WorkflowCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create video generation workflow",
    description="Start a new video generation workflow with the given parameters.",
    tags=["video-generation"],
)
@limiter.limit("5/minute")
async def create_workflow(
    request: Request,
    background_tasks: BackgroundTasks,
    input_data: WorkflowInput,
) -> WorkflowCreateResponse:
    """
    Create a new video generation workflow (JSON body).
    
    This endpoint validates the input and creates a workflow record.
    The actual generation is handled asynchronously by the LangGraph workflow.
    
    Args:
        input_data: Workflow input parameters
        
    Returns:
        Workflow creation response with ID and status
    """
    return await _create_workflow_internal(
        background_tasks=background_tasks,
        topic=input_data.topic,
        duration_seconds=input_data.duration_seconds,
        aspect_ratio=input_data.aspect_ratio,
        resolution=input_data.resolution,
        category=input_data.category,
        hitl_mode=input_data.hitl_mode,
        enable_audio=input_data.enable_audio,
        enable_subtitles=input_data.enable_subtitles,
        reference_image_url=None,
        tool_id=input_data.tool_id,
        video_model=input_data.video_model,
    )


@router.post(
    "/with-image",
    response_model=WorkflowCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow with reference image",
    description="Start a new workflow with an optional reference image upload (max 10MB).",
    tags=["video-generation"],
)
@limiter.limit("5/minute")
async def create_workflow_with_image(
    request: Request,
    background_tasks: BackgroundTasks,
    topic: str = Form(..., min_length=3, max_length=2000, description="Video topic"),
    duration_seconds: int = Form(default=18, ge=8, le=60, description="Duration (8-60s)"),
    aspect_ratio: AspectRatioEnum = Form(default=AspectRatioEnum.VERTICAL),
    resolution: ResolutionEnum = Form(default=ResolutionEnum.FULL_HD),
    category: CategoryEnum = Form(default=CategoryEnum.AUTO),
    hitl_mode: HITLModeEnum = Form(default=HITLModeEnum.AUTO),
    enable_audio: bool = Form(default=False),
    enable_subtitles: bool = Form(default=False),
    video_model: VideoModelOption = Form(default=VideoModelOption.VEO_3_1, description="Veo model: veo_3_1 or veo_3_1_fast"),
    tool_id: Optional[str] = Form(default=None, description="Optional specific tool_id under the selected category"),
    reference_image: Optional[UploadFile] = File(default=None, description="Reference image (max 10MB, jpg/png/webp)"),
) -> WorkflowCreateResponse:
    """
    Create a new video generation workflow with optional reference image.
    
    This endpoint accepts multipart form data for file upload.
    Reference: SRS.md FR-109 - Optional reference image upload
    
    Args:
        topic: Video topic (required)
        duration_seconds: Video duration 8-25s (default: 18)
        aspect_ratio: Video aspect ratio (default: 9:16)
        resolution: Video resolution (default: 1080p)
        category: Visual style category (default: auto)
        hitl_mode: Human-in-the-loop mode (default: auto)
        enable_audio: Generate audio (default: false; requires explicit enable)
        enable_subtitles: Generate subtitles (default: false)
        reference_image: Optional reference image file
        
    Returns:
        Workflow creation response with ID and status
    """
    workflow_id = generate_workflow_id()
    
    # Validate and upload reference image if provided
    reference_image_url = None
    if reference_image and reference_image.filename:
        reference_image_url = await _validate_and_upload_image(
            file=reference_image,
            workflow_id=workflow_id,
        )
    
    return await _create_workflow_internal(
        background_tasks=background_tasks,
        topic=topic.strip(),
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        category=category,
        hitl_mode=hitl_mode,
        enable_audio=enable_audio,
        enable_subtitles=enable_subtitles,
        reference_image_url=reference_image_url,
        workflow_id=workflow_id,
        tool_id=tool_id,
        video_model=video_model,
    )


async def _create_workflow_internal(
    background_tasks: BackgroundTasks,
    topic: str,
    duration_seconds: int,
    aspect_ratio: AspectRatioEnum,
    resolution: ResolutionEnum,
    category: CategoryEnum,
    hitl_mode: HITLModeEnum,
    enable_audio: bool,
    enable_subtitles: bool,
    reference_image_url: Optional[str],
    workflow_id: Optional[str] = None,
    video_model: VideoModelOption = VideoModelOption.VEO_3_1,
    tool_id: Optional[str] = None,
) -> WorkflowCreateResponse:
    """
    Internal workflow creation logic.
    
    Shared by both JSON and multipart form endpoints.
    """
    if workflow_id is None:
        workflow_id = generate_workflow_id()
    
    # Detailed logging for terminal monitoring
    log_header(logger, f"CREATE WORKFLOW: {workflow_id}")
    log_request_start(logger, "POST", "/api/v1/generate", {
        "workflow_id": workflow_id,
        "topic": topic[:80] + "..." if len(topic) > 80 else topic,
        "duration": f"{duration_seconds}s",
        "aspect_ratio": aspect_ratio.value,
        "resolution": resolution.value,
        "category": category.value,
        "hitl_mode": hitl_mode.value,
        "audio": "enabled" if enable_audio else "disabled",
        "subtitles": "enabled" if enable_subtitles else "disabled",
        "reference_image": "provided" if reference_image_url else "none",
        "video_model": video_model.value,
    })
    
    # Optional: validate tool_id (must exist and match category if category != auto)
    if tool_id:
        from app.tools.registry import get_tool_registry
        registry = get_tool_registry()
        tool = await registry.get_by_tool_id(tool_id)
        if not tool:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tool not found: {tool_id}")
        if not tool.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tool is inactive: {tool_id}")
        # If category is fixed (not auto), enforce match
        if category != CategoryEnum.AUTO and tool.category != category.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool '{tool_id}' does not belong to category '{category.value}'",
            )

    workflow_data = {
        "id": workflow_id,
        "status": WorkflowStatus.PENDING.value,
        "topic": topic,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio.value,
        "resolution": resolution.value,
        "category": category.value,
        "hitl_mode": hitl_mode.value,
        "enable_audio": enable_audio,
        "enable_subtitles": enable_subtitles,
        "user_reference_image_url": reference_image_url,
        "user_selected_tool_id": tool_id,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    
    try:
        with log_operation(logger, "Save workflow to database"):
            repo = get_workflow_repository()
            await repo.create(workflow_data)
        
        log_workflow_event(logger, workflow_id, "Workflow created successfully", {
            "status": WorkflowStatus.PENDING.value,
            "hitl_mode": hitl_mode.value,
            "expected_duration": f"{duration_seconds}s",
        })
        log_success(logger, f"Workflow {workflow_id} ready for processing")
        
        # Trigger background workflow execution
        from app.services.workflow_runner import run_workflow_background
        # Map user-friendly option to actual Veo model string (see Documentations/veo_doc.md)
        selected_model = (
            VideoModel.VEO_3_1.value if video_model == VideoModelOption.VEO_3_1 else VideoModel.VEO_3_1_FAST.value
        )
        background_tasks.add_task(run_workflow_background, workflow_id, video_model=selected_model)
        log_workflow_event(logger, workflow_id, "Background execution scheduled")
        
    except ValueError as e:
        log_error_msg(logger, f"Database error: {e}")
        log_workflow_event(logger, workflow_id, "Creation failed - Database unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        log_error_msg(logger, f"Unexpected error: {e}")
        log_workflow_event(logger, workflow_id, f"Creation failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow"
        )
    
    return WorkflowCreateResponse(
        workflow_id=workflow_id,
        status=WorkflowStatus.PENDING,
        message="Workflow created successfully. Video generation will start shortly.",
    )
