"""RABA Tools API Routes.

Full CRUD operations for video generation tools with AI-enhanced creation.
"""

from typing import Optional

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

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ToolListResponse)
async def list_tools(
    category: Optional[str] = Query(
        None,
        description="Filter by category (surreal_realism, high_octane_anime, stylized_3d)"
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
    log_request_start(logger, "GET", "/api/v1/tools", {
        "category": category or "all",
        "is_active": is_active,
        "limit": limit,
        "offset": offset,
    })
    
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
    log_request_start(logger, "POST", "/api/v1/tools", {
        "tool_name": request.tool_name,
        "idea_length": len(request.idea),
        "category_hint": request.category.value if request.category else "auto",
    })
    
    try:
        with log_operation(logger, "Enhance tool idea with Gemini"):
            enhancer = get_tool_enhancer()
            enhanced = await enhancer.enhance_tool_idea(request)
        
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
    log_request_start(logger, "POST", "/api/v1/tools/preview", {
        "tool_name": request.tool_name,
    })
    
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
    log_request_start(logger, "PUT", f"/api/v1/tools/{tool_id}", {
        "has_name_update": bool(request.tool_name),
        "has_idea_update": bool(request.idea),
        "has_active_update": request.is_active is not None,
    })
    
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
    log_request_start(logger, "POST", f"/api/v1/tools/{tool_id}/improve", {
        "suggestion_length": len(request.improvement_suggestion),
        "preserve_templates": request.preserve_templates,
    })
    
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
    log_request_start(logger, "POST", f"/api/v1/tools/{tool_id}/execute", {
        "topic": request.topic[:60] + "..." if len(request.topic) > 60 else request.topic,
        "has_params": bool(request.parameters),
    })
    
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
        log_key_value(logger, "Estimated generation time", f"{result.estimated_generation_time:.1f}s")
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
