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
from app.utils.logging import get_logger

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
    logger.info(f"Listing tools: category={category}, is_active={is_active}")
    
    registry = get_tool_registry()
    return await registry.list_tools(
        category=category,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: str) -> ToolResponse:
    """
    Get a tool by its unique identifier.
    
    Args:
        tool_id: Unique tool slug (e.g., "surreal_impossible_sims")
    """
    logger.info(f"Getting tool: {tool_id}")
    
    registry = get_tool_registry()
    tool = await registry.get_by_tool_id(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
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
    logger.info(f"Creating tool: {request.tool_name}")
    
    try:
        # Enhance the idea with Gemini
        enhancer = get_tool_enhancer()
        enhanced = await enhancer.enhance_tool_idea(request)
        
        # Save to database
        registry = get_tool_registry()
        tool = await registry.create(
            enhanced_tool=enhanced,
            original_idea=request.idea,
        )
        
        logger.info(f"Tool created: {tool.tool_id}")
        return tool
        
    except Exception as e:
        logger.error(f"Failed to create tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=ToolEnhancementResponse)
async def preview_enhancement(request: ToolCreate) -> ToolEnhancementResponse:
    """
    Preview AI enhancement without saving.
    
    Use this to see what Gemini will generate before committing.
    Returns the enhanced tool configuration without persisting.
    """
    logger.info(f"Previewing tool enhancement: {request.tool_name}")
    
    try:
        enhancer = get_tool_enhancer()
        enhanced = await enhancer.enhance_tool_idea(request)
        return enhanced
        
    except Exception as e:
        logger.error(f"Failed to preview enhancement: {e}")
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
    logger.info(f"Updating tool: {tool_id}")
    
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
        logger.info(f"Tool updated: {tool_id}")
        return tool
        
    except ToolNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        logger.error(f"Failed to update tool: {e}")
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
    logger.info(f"Improving tool: {tool_id}")
    
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
        
        logger.info(f"Tool improved: {tool_id} (v{tool.version})")
        return tool
        
    except ToolNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        logger.error(f"Failed to improve tool: {e}")
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
    logger.info(f"Deleting tool: {tool_id}")
    
    try:
        registry = get_tool_registry()
        await registry.delete(tool_id)
        
        logger.info(f"Tool deleted: {tool_id}")
        return DeleteResponse(success=True, tool_id=tool_id)
        
    except ToolNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        logger.error(f"Failed to delete tool: {e}")
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
    logger.info(f"Executing tool: {tool_id} for topic: {request.topic[:50]}...")
    
    try:
        # Get tool
        registry = get_tool_registry()
        tool = await registry.get_by_tool_id(tool_id)
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
        
        if not tool.is_active:
            raise HTTPException(status_code=400, detail=f"Tool is not active: {tool_id}")
        
        # Execute
        executor = get_tool_executor()
        result = await executor.execute(tool, request)
        
        # Update usage stats (non-blocking)
        await registry.increment_usage(tool_id)
        
        logger.info(f"Tool executed: {tool_id}")
        return result
        
    except ParameterValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ToolNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    except Exception as e:
        logger.error(f"Failed to execute tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
