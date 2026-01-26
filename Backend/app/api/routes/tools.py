"""RABA Tools API Routes.

Full CRUD operations for video generation tools with AI-enhanced creation.
"""

from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Query

from app.models.tool import (
    DeleteResponse,
    ToolCreate,
    ToolEnhancementResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
    ToolImproveRequest,
    ToolListResponse,
    ToolResponse,
    ToolUpdate,
    PromptBulkUpdateRequest,
    PromptBulkUpdateResponse,
    ToolPromptUpdateRequest,
    ToolPromptUpdateResponse,
    PromptUpdateType,
)
from app.services.tool_enhancer import get_tool_enhancer
from app.services.tool_executor import get_tool_executor, ParameterValidationError
from app.tools.registry import get_tool_registry, ToolNotFoundError
from app.utils.logging import (
    get_logger,
    log_header,
    log_key_value,
    log_request_start,
    log_request_end,
    log_success,
    log_error_msg,
    log_warning_msg,
    log_operation,
    log_subheader,
)
import time
from app.services.prompt_builder import get_prompt_builder
from app.services.template_validation import get_template_validator
from app.utils.security import validate_uuid

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ToolListResponse)
async def list_tools(
    category: Optional[str] = Query(
        None, description="Filter by category (surreal_realism, high_octane_anime, stylized_3d)"
    ),
    is_active: bool = Query(True, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> ToolListResponse:
    """
    List all tools with optional filters.

    Returns paginated list of tools sorted by priority (descending).
    """
    start_time = time.time()
    log_request_start(
        logger,
        "GET",
        "/api/v1/tools",
        {
            "category": category or "all",
            "is_active": is_active,
            "limit": limit,
            "offset": offset,
        },
    )

    registry = get_tool_registry()
    result = await registry.list_tools(
        category=category,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

    log_success(logger, f"Listed {len(result.tools)} tools (total: {result.total})")
    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "GET", "/api/v1/tools", 200, duration_ms)
    return result


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: str) -> ToolResponse:
    """
    Get a tool by its unique identifier.

    Args:
        tool_id: Unique tool slug (e.g., "surreal_impossible_sims")
    """
    start_time = time.time()
    log_request_start(logger, "GET", f"/api/v1/tools/{tool_id}")

    registry = get_tool_registry()
    tool = await registry.get_by_tool_id(tool_id)

    if not tool:
        log_warning_msg(logger, f"Tool not found: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/tools/{tool_id}", 404, duration_ms)
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

    log_success(logger, f"Tool retrieved: {tool_id}")
    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "GET", f"/api/v1/tools/{tool_id}", 200, duration_ms)
    return tool


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(request: ToolCreate) -> ToolResponse:
    """
    Create a new tool from user idea.

    The idea is enhanced by Gemini 2.5 Flash to generate:
    - Proper tool_id slug
    - Category classification
    - Enhanced description
    - Capabilities
    - Prompt templates
    - Parameters schema

    **Request Body:**
    - `tool_name`: Display name for the tool
    - `idea`: Description of what the tool should do
    - `category`: Optional category hint
    """
    start_time = time.time()
    log_header(logger, f"CREATE TOOL: {request.tool_name}")
    log_request_start(
        logger,
        "POST",
        "/api/v1/tools",
        {
            "tool_name": request.tool_name,
            "idea_length": len(request.idea),
            "category_hint": request.category.value if request.category else "auto",
        },
    )

    try:
        enhancer = get_tool_enhancer()
        validator = get_template_validator()
        builder = get_prompt_builder()

        # Retry logic for validation failures
        max_retries = 2
        enhanced = None
        validation_errors = None

        for attempt in range(max_retries + 1):
            with log_operation(logger, f"Enhance tool idea with Gemini (attempt {attempt + 1})"):
                enhanced = await enhancer.enhance_tool_idea(
                    request,
                    retry_count=attempt,
                    max_retries=max_retries,
                    validation_errors=validation_errors,
                )

            # Validate templates
            temp_errors: list[str] = []
            if enhanced.script_prompt_template:
                ok, errs = builder.quality_validate(
                    enhanced.script_prompt_template, ["topic", "tone", "duration"], 150
                )
                if not ok:
                    temp_errors.extend([f"script: {e}" for e in errs])
                ok2, errs2 = validator.validate_script(enhanced.script_prompt_template)
                if not ok2:
                    temp_errors.extend([f"script: {e}" for e in errs2])

            if enhanced.image_prompt_template:
                ok, errs = builder.quality_validate(
                    enhanced.image_prompt_template, ["scene_description", "style"], 150
                )
                if not ok:
                    temp_errors.extend([f"image: {e}" for e in errs])
                ok2, errs2 = validator.validate_image(enhanced.image_prompt_template)
                if not ok2:
                    temp_errors.extend([f"image: {e}" for e in errs2])

            if enhanced.video_prompt_template:
                ok, errs = builder.quality_validate(
                    enhanced.video_prompt_template, ["script", "duration"], 150
                )
                if not ok:
                    temp_errors.extend([f"video: {e}" for e in errs])
                ok2, errs2 = validator.validate_video(enhanced.video_prompt_template)
                if not ok2:
                    temp_errors.extend([f"video: {e}" for e in errs2])

            if not temp_errors:
                # Validation passed, break out of retry loop
                break
            else:
                validation_errors = temp_errors
                if attempt < max_retries:
                    log_warning_msg(
                        logger,
                        f"Validation failed on attempt {attempt + 1}, retrying with fixes: {validation_errors}",
                    )
                else:
                    log_warning_msg(
                        logger,
                        f"Validation failed after all retries: {validation_errors}",
                    )
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Tool template validation failed",
                            "errors": validation_errors,
                        },
                    )

        if not enhanced:
            raise HTTPException(status_code=500, detail="Tool enhancement failed")

        log_key_value(logger, "Generated tool_id", enhanced.tool_id)
        log_key_value(logger, "Category", enhanced.category.value)

        with log_operation(logger, "Save tool to database"):
            registry = get_tool_registry()
            tool = await registry.create(
                enhanced_tool=enhanced,
                original_idea=request.idea,
            )

        log_success(logger, f"Tool created: {tool.tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", "/api/v1/tools", 201, duration_ms)
        return tool

    except Exception as e:
        log_error_msg(logger, f"Failed to create tool: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", "/api/v1/tools", 500, duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=ToolEnhancementResponse)
async def preview_enhancement(request: ToolCreate) -> ToolEnhancementResponse:
    """
    Preview AI enhancement without saving.

    Use this to see what Gemini will generate before committing.
    Returns the enhanced tool configuration without persisting.
    """
    start_time = time.time()
    log_request_start(
        logger,
        "POST",
        "/api/v1/tools/preview",
        {
            "tool_name": request.tool_name,
        },
    )

    try:
        with log_operation(logger, "Preview tool enhancement"):
            enhancer = get_tool_enhancer()
            enhanced = await enhancer.enhance_tool_idea(request)

        log_success(logger, f"Preview generated: {enhanced.tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", "/api/v1/tools/preview", 200, duration_ms)
        return enhanced

    except Exception as e:
        log_error_msg(logger, f"Failed to preview enhancement: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", "/api/v1/tools/preview", 500, duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(tool_id: str, request: ToolUpdate) -> ToolResponse:
    """
    Update an existing tool.

    All fields are optional - only provided fields will be updated.
    If `idea` is changed, the tool will be re-enhanced by Gemini.

    Args:
        tool_id: Tool to update
        request: Fields to update
    """
    start_time = time.time()
    log_request_start(
        logger,
        "PUT",
        f"/api/v1/tools/{tool_id}",
        {
            "has_name_update": bool(request.tool_name),
            "has_idea_update": bool(request.idea),
            "has_active_update": request.is_active is not None,
        },
    )

    try:
        registry = get_tool_registry()

        # Check if idea changed - need to re-enhance
        if request.idea:
            existing = await registry.get_by_tool_id(tool_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

            if request.idea != existing.original_idea:
                # Re-enhance with new idea
                enhancer = get_tool_enhancer()
                enhanced = await enhancer.enhance_tool_idea(
                    ToolCreate(
                        tool_name=request.tool_name or existing.tool_name,
                        idea=request.idea,
                        category=None,  # Let AI re-classify
                    )
                )

                # Update request with enhanced values
                request.description = enhanced.description
                request.script_prompt_template = enhanced.script_prompt_template
                request.image_prompt_template = enhanced.image_prompt_template
                request.video_prompt_template = enhanced.video_prompt_template

        tool = await registry.update(tool_id, request)
        log_success(logger, f"Tool updated: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "PUT", f"/api/v1/tools/{tool_id}", 200, duration_ms)
        return tool

    except ToolNotFoundError:
        log_warning_msg(logger, f"Tool not found: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "PUT", f"/api/v1/tools/{tool_id}", 404, duration_ms)
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        log_error_msg(logger, f"Failed to update tool: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "PUT", f"/api/v1/tools/{tool_id}", 500, duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tool_id}/improve", response_model=ToolResponse)
async def improve_tool(tool_id: str, request: ToolImproveRequest) -> ToolResponse:
    """
    Improve an existing tool based on feedback.

    Gemini will analyze the existing tool and user suggestions,
    then generate an improved version while preserving what works.

    The improvement is recorded in the tool's improvement_history.

    Args:
        tool_id: Tool to improve
        request: Improvement suggestion and options
    """
    start_time = time.time()
    log_header(logger, f"IMPROVE TOOL: {tool_id}")
    log_request_start(
        logger,
        "POST",
        f"/api/v1/tools/{tool_id}/improve",
        {
            "suggestion_length": len(request.improvement_suggestion),
            "preserve_templates": request.preserve_templates,
        },
    )

    try:
        registry = get_tool_registry()

        # Get existing tool
        existing = await registry.get_by_tool_id(tool_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

        # Enhance with improvement
        enhancer = get_tool_enhancer()
        improved = await enhancer.improve_tool(existing, request)

        # Apply improvement
        tool = await registry.apply_improvement(
            tool_id=tool_id,
            enhanced_tool=improved,
            improvement_suggestion=request.improvement_suggestion,
        )

        log_success(logger, f"Tool improved: {tool_id} (v{tool.version})")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/improve", 200, duration_ms)
        return tool

    except ToolNotFoundError:
        log_warning_msg(logger, f"Tool not found: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/improve", 404, duration_ms)
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        log_error_msg(logger, f"Failed to improve tool: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/improve", 500, duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tool_id}", response_model=DeleteResponse)
async def delete_tool(tool_id: str) -> DeleteResponse:
    """
    Soft delete a tool.

    Sets is_active = false. The tool data is preserved but
    won't appear in active tool lists.

    Args:
        tool_id: Tool to delete
    """
    start_time = time.time()
    log_request_start(logger, "DELETE", f"/api/v1/tools/{tool_id}")

    try:
        with log_operation(logger, "Delete tool"):
            registry = get_tool_registry()
            await registry.delete(tool_id)

        log_success(logger, f"Tool deleted: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "DELETE", f"/api/v1/tools/{tool_id}", 200, duration_ms)
        return DeleteResponse(success=True, tool_id=tool_id)

    except ToolNotFoundError:
        log_warning_msg(logger, f"Tool not found: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "DELETE", f"/api/v1/tools/{tool_id}", 404, duration_ms)
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        log_error_msg(logger, f"Failed to delete tool: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "DELETE", f"/api/v1/tools/{tool_id}", 500, duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tool_id}/execute", response_model=ToolExecutionResponse)
async def execute_tool(tool_id: str, request: ToolExecutionRequest) -> ToolExecutionResponse:
    """
    Execute a tool with a topic to generate prompts.

    Renders the tool's prompt templates with the provided topic
    and parameters, producing ready-to-use prompts for:
    - Script generation
    - Image generation
    - Video generation

    Args:
        tool_id: Tool to execute
        request: Topic and optional parameters
    """
    start_time = time.time()
    log_subheader(logger, f"EXECUTE TOOL: {tool_id}")
    log_request_start(
        logger,
        "POST",
        f"/api/v1/tools/{tool_id}/execute",
        {
            "topic": request.topic[:60] + "..." if len(request.topic) > 60 else request.topic,
            "has_params": bool(request.parameters),
        },
    )

    try:
        # Get tool
        registry = get_tool_registry()
        tool = await registry.get_by_tool_id(tool_id)

        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

        if not tool.is_active:
            raise HTTPException(status_code=400, detail=f"Tool is not active: {tool_id}")

        with log_operation(logger, "Execute tool"):
            executor = get_tool_executor()
            result = await executor.execute(tool, request)

        # Update usage stats (non-blocking)
        await registry.increment_usage(tool_id)

        log_success(logger, f"Tool executed: {tool_id}")
        log_key_value(
            logger, "Estimated generation time", f"{result.estimated_generation_time:.1f}s"
        )
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/execute", 200, duration_ms)
        return result

    except ParameterValidationError as e:
        log_warning_msg(logger, f"Parameter validation error: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/execute", 422, duration_ms)
        raise HTTPException(status_code=422, detail=str(e))
    except ToolNotFoundError:
        log_warning_msg(logger, f"Tool not found: {tool_id}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/execute", 404, duration_ms)
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        log_error_msg(logger, f"Failed to execute tool: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/tools/{tool_id}/execute", 500, duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts/bulk-update", response_model=PromptBulkUpdateResponse)
async def bulk_update_prompts(request: PromptBulkUpdateRequest) -> PromptBulkUpdateResponse:
    """Bulk update prompt templates for multiple tools.

    - Supports AI enhancement using existing tool context
    - Validates placeholders and minimum quality (150 words)
    - Updates only specified templates per update_type
    - When update_type is 'all' and tool_ids is None/empty, updates all tools in database
    """
    start_time = time.time()
    log_header(logger, "BULK PROMPT UPDATE")

    registry = get_tool_registry()
    enhancer = get_tool_enhancer()
    builder = get_prompt_builder()
    validator = get_template_validator()

    # Determine which tools to update
    tools_to_process: list[ToolResponse] = []

    # When update_type is "all", fetch ALL tools from database (ignore tool_ids completely)
    if request.update_type == PromptUpdateType.ALL:
        # Validate: when update_type is "all", use_ai_enhancement must be True
        # (can't provide manual prompts for all tools)
        if not request.use_ai_enhancement:
            raise HTTPException(
                status_code=400,
                detail="use_ai_enhancement must be True when update_type is 'all' (cannot provide manual prompts for all tools)",
            )

        log_key_value(logger, "Update mode", "ALL tools in database")
        # Fetch all active tools from database - no tool_ids needed
        all_tools_result = await registry.list_tools(is_active=True, limit=1000, offset=0)
        tools_to_process = all_tools_result.tools
        log_key_value(logger, "Fetched tools from DB", len(tools_to_process))
    else:
        # For specific update types, tool_ids must be provided
        if not request.tool_ids or len(request.tool_ids) == 0:
            raise HTTPException(
                status_code=400, detail="tool_ids must be provided when update_type is not 'all'"
            )

        # Process specific tool IDs
        log_key_value(logger, "Update mode", f"Specific tools: {len(request.tool_ids)}")
        for tool_id in request.tool_ids:
            tool = await registry.get_by_tool_id(tool_id)
            if not tool:
                # Only try get_by_id if it looks like a UUID
                if validate_uuid(tool_id):
                    tool = await registry.get_by_id(tool_id)
                if not tool:
                    log_warning_msg(logger, f"Tool not found: {tool_id}")
                    continue
            tools_to_process.append(tool)

    log_request_start(
        logger,
        "POST",
        "/api/v1/tools/prompts/bulk-update",
        {
            "tool_count": len(tools_to_process),
            "update_type": request.update_type.value,
            "use_ai_enhancement": request.use_ai_enhancement,
        },
    )

    updated_tools: list[ToolResponse] = []
    failed_updates: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    def validate_set(tpl: Optional[str], req: list[str], which: str) -> list[str]:
        if not tpl:
            return []
        ok, errs = builder.quality_validate(tpl, req, 150)
        errors = list(errs)
        if which == "script":
            ok2, errs2 = validator.validate_script(tpl)
        elif which == "image":
            ok2, errs2 = validator.validate_image(tpl)
        else:
            ok2, errs2 = validator.validate_video(tpl)
        if not ok2:
            errors.extend(errs2)
        return [] if ok and ok2 else errors

    for tool in tools_to_process:
        try:
            tool_id = tool.tool_id
            match_type = "tool_id"

            # Build proposed templates
            script_tpl = image_tpl = video_tpl = None
            t0 = time.time()
            log_key_value(logger, "Processing tool", tool_id)
            if request.use_ai_enhancement:
                # Retry logic for validation failures
                max_retries = 2
                improved = None
                validation_errors = None

                for attempt in range(max_retries + 1):
                    with log_operation(
                        logger, f"AI enhance templates ({tool_id}) - attempt {attempt + 1}"
                    ):
                        # Use tool enhancer to regenerate prompts (same system as tool creation)
                        # This uses the system-wide prompt builder/enhancer to improve prompts
                        # Ensure improvement_reason meets minimum length requirement (10 chars)
                        default_reason = (
                            "System-wide prompt quality improvement to match latest standards"
                        )
                        improvement_reason = request.improvement_reason or default_reason
                        # If provided reason is too short, use default
                        if improvement_reason and len(improvement_reason.strip()) < 10:
                            improvement_reason = default_reason

                        improved = await enhancer.improve_tool(
                            tool,
                            ToolImproveRequest(
                                improvement_suggestion=improvement_reason,
                                preserve_templates=False,
                            ),
                            retry_count=attempt,
                            max_retries=max_retries,
                            validation_errors=validation_errors,
                        )

                    script_tpl = improved.script_prompt_template
                    image_tpl = improved.image_prompt_template
                    video_tpl = improved.video_prompt_template

                    # Filter by update_type before validation
                    if request.update_type == PromptUpdateType.SCRIPT_ONLY:
                        image_tpl = None
                        video_tpl = None
                    elif request.update_type == PromptUpdateType.IMAGE_ONLY:
                        script_tpl = None
                        video_tpl = None
                    elif request.update_type == PromptUpdateType.VIDEO_ONLY:
                        script_tpl = None
                        image_tpl = None
                    elif request.update_type == PromptUpdateType.SCRIPT_AND_IMAGE:
                        video_tpl = None
                    elif request.update_type == PromptUpdateType.SCRIPT_AND_VIDEO:
                        image_tpl = None
                    elif request.update_type == PromptUpdateType.IMAGE_AND_VIDEO:
                        script_tpl = None

                    # Validate templates
                    temp_errors: list[str] = []
                    temp_errors += [
                        e for e in validate_set(script_tpl, ["topic", "tone", "duration"], "script")
                    ]
                    temp_errors += [
                        e for e in validate_set(image_tpl, ["scene_description", "style"], "image")
                    ]
                    temp_errors += [
                        e for e in validate_set(video_tpl, ["script", "duration"], "video")
                    ]

                    if not temp_errors:
                        # Validation passed, break out of retry loop
                        log_key_value(logger, "AI enhancement", "completed and validated")
                        break
                    else:
                        validation_errors = temp_errors
                        if attempt < max_retries:
                            log_warning_msg(
                                logger,
                                f"Validation failed on attempt {attempt + 1}, retrying with fixes: {validation_errors}",
                            )
                        else:
                            log_key_value(
                                logger,
                                "AI enhancement",
                                "completed but validation failed after all retries",
                            )
                            raise HTTPException(
                                status_code=400,
                                detail={
                                    "message": "Tool template validation failed",
                                    "errors": validation_errors,
                                },
                            )
            else:
                if request.prompts:
                    script_tpl = request.prompts.script_prompt_template
                    image_tpl = request.prompts.image_prompt_template
                    video_tpl = request.prompts.video_prompt_template
                log_key_value(logger, "Using provided prompts", bool(request.prompts))

                # Filter by update_type for manual prompts
                if request.update_type == PromptUpdateType.SCRIPT_ONLY:
                    image_tpl = None
                    video_tpl = None
                elif request.update_type == PromptUpdateType.IMAGE_ONLY:
                    script_tpl = None
                    video_tpl = None
                elif request.update_type == PromptUpdateType.VIDEO_ONLY:
                    script_tpl = None
                    image_tpl = None
                elif request.update_type == PromptUpdateType.SCRIPT_AND_IMAGE:
                    video_tpl = None
                elif request.update_type == PromptUpdateType.SCRIPT_AND_VIDEO:
                    image_tpl = None
                elif request.update_type == PromptUpdateType.IMAGE_AND_VIDEO:
                    script_tpl = None

            # Validate prompts
            errors: list[str] = []
            errors += [
                f"script: {e}"
                for e in validate_set(script_tpl, ["topic", "tone", "duration"], "script")
            ]
            errors += [
                f"image: {e}"
                for e in validate_set(image_tpl, ["scene_description", "style"], "image")
            ]
            errors += [
                f"video: {e}" for e in validate_set(video_tpl, ["script", "duration"], "video")
            ]

            # Final validation check (for AI-enhanced prompts that failed after retries)
            if request.use_ai_enhancement:
                errors = []
                errors += [
                    f"script: {e}"
                    for e in validate_set(script_tpl, ["topic", "tone", "duration"], "script")
                ]
                errors += [
                    f"image: {e}"
                    for e in validate_set(image_tpl, ["scene_description", "style"], "image")
                ]
                errors += [
                    f"video: {e}" for e in validate_set(video_tpl, ["script", "duration"], "video")
                ]

            if errors:
                err_msg = "; ".join(errors)
                failed_updates.append({"tool_id": tool_id, "error": err_msg, "stage": "validation"})
                log_key_value(logger, "Validation failed", err_msg)
                details.append(
                    {
                        "input": tool_id,
                        "match_type": match_type,
                        "used_ai": request.use_ai_enhancement,
                        "status": "failed",
                        "stage": "validation",
                        "errors": errors,
                    }
                )
                continue

            with log_operation(logger, f"Persist update ({tool_id})"):
                saved = await registry.update(
                    tool_id,
                    ToolUpdate(
                        script_prompt_template=script_tpl,
                        image_prompt_template=image_tpl,
                        video_prompt_template=video_tpl,
                    ),
                )
            updated_tools.append(saved)
            log_key_value(logger, "Updated tool", f"{tool_id} -> v{saved.version}")
            elapsed = int((time.time() - t0) * 1000)
            log_key_value(logger, "Elapsed (ms)", elapsed)
            details.append(
                {
                    "input": tool_id,
                    "match_type": match_type,
                    "used_ai": request.use_ai_enhancement,
                    "status": "updated",
                    "new_version": saved.version,
                    "elapsed_ms": elapsed,
                }
            )
        except Exception as e:
            tool_id_for_error = tool.tool_id if tool else "unknown"
            failed_updates.append(
                {"tool_id": tool_id_for_error, "error": str(e), "stage": "unexpected"}
            )
            log_error_msg(logger, f"Failed updating {tool_id_for_error}: {e}")

    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "POST", "/api/v1/tools/prompts/bulk-update", 200, duration_ms)
    summary = PromptBulkUpdateResponse(
        updated_count=len(updated_tools),
        failed_updates=failed_updates,
        updated_tools=updated_tools,
        improvement_summary=request.improvement_reason,
        details=details,
    )
    log_success(
        logger,
        f"Bulk prompt update complete: updated={summary.updated_count}, failed={len(summary.failed_updates)}",
    )
    return summary


@router.put("/{tool_id}/prompts", response_model=ToolPromptUpdateResponse)
async def update_tool_prompts(
    tool_id: str, request: ToolPromptUpdateRequest
) -> ToolPromptUpdateResponse:
    """Update prompt templates for a single tool with validation and AI option."""
    start_time = time.time()
    log_request_start(
        logger,
        "PUT",
        f"/api/v1/tools/{tool_id}/prompts",
        {
            "update_type": request.update_type.value,
            "use_ai_enhancement": request.use_ai_enhancement,
        },
    )

    registry = get_tool_registry()
    enhancer = get_tool_enhancer()
    builder = get_prompt_builder()
    validator = get_template_validator()

    tool = await registry.get_by_tool_id(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

    script_tpl = image_tpl = video_tpl = None
    if request.use_ai_enhancement:
        t0 = time.time()
        with log_operation(logger, f"AI enhance templates ({tool_id})"):
            improved = await enhancer.improve_tool(
                tool,
                ToolImproveRequest(
                    improvement_suggestion=request.improvement_reason,
                    preserve_templates=False,
                ),
            )
        script_tpl = improved.script_prompt_template
        image_tpl = improved.image_prompt_template
        video_tpl = improved.video_prompt_template
        log_key_value(logger, "AI enhancement", f"completed in {int((time.time() - t0) * 1000)}ms")
    else:
        if not request.prompts:
            raise HTTPException(
                status_code=400, detail="prompts must be provided when use_ai_enhancement=false"
            )
        script_tpl = request.prompts.script_prompt_template
        image_tpl = request.prompts.image_prompt_template
        video_tpl = request.prompts.video_prompt_template

    # Filter by update_type
    if request.update_type == PromptUpdateType.SCRIPT_ONLY:
        image_tpl = None
        video_tpl = None
    elif request.update_type == PromptUpdateType.IMAGE_ONLY:
        script_tpl = None
        video_tpl = None
    elif request.update_type == PromptUpdateType.VIDEO_ONLY:
        script_tpl = None
        image_tpl = None
    elif request.update_type == PromptUpdateType.SCRIPT_AND_IMAGE:
        video_tpl = None
    elif request.update_type == PromptUpdateType.SCRIPT_AND_VIDEO:
        image_tpl = None
    elif request.update_type == PromptUpdateType.IMAGE_AND_VIDEO:
        script_tpl = None

    # Validate
    def qual(tpl: Optional[str], req: list[str], which: str) -> list[str]:
        if not tpl:
            return []
        ok, errs = builder.quality_validate(tpl, req, 150)
        if which == "script":
            ok2, errs2 = validator.validate_script(tpl)
        elif which == "image":
            ok2, errs2 = validator.validate_image(tpl)
        else:
            ok2, errs2 = validator.validate_video(tpl)
        errors = list(errs)
        if not ok2:
            errors.extend(errs2)
        return [] if ok and ok2 else errors

    errors: list[str] = []
    errors += [f"script: {e}" for e in qual(script_tpl, ["topic", "tone", "duration"], "script")]
    errors += [f"image: {e}" for e in qual(image_tpl, ["scene_description", "style"], "image")]
    errors += [f"video: {e}" for e in qual(video_tpl, ["script", "duration"], "video")]
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    with log_operation(logger, f"Persist update ({tool_id})"):
        saved = await registry.update(
            tool_id,
            ToolUpdate(
                script_prompt_template=script_tpl,
                image_prompt_template=image_tpl,
                video_prompt_template=video_tpl,
            ),
        )
    log_key_value(logger, "Updated tool", f"{tool_id} -> v{saved.version}")

    duration_ms = (time.time() - start_time) * 1000
    log_request_end(logger, "PUT", f"/api/v1/tools/{tool_id}/prompts", 200, duration_ms)
    return ToolPromptUpdateResponse(
        tool_id=tool_id,
        updated_templates={
            "script": bool(script_tpl),
            "image": bool(image_tpl),
            "video": bool(video_tpl),
        },
        improvement_summary=request.improvement_reason,
        new_version=saved.version,
    )
