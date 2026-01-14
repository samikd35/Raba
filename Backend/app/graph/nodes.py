"""RABA LangGraph Node Functions.

Node functions for each agent in the video generation workflow.
"""

from app.agents.intent_tool_selector import IntentToolSelectorAgent
from app.graph.state import VideoGenerationState
from app.utils.helpers import utc_now_iso
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def intent_tool_selector_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Intent/Tool Selection.
    
    This is the FIRST node in the workflow. It extracts intent from the topic
    and selects the optimal video generation tool.
    
    Input from state:
        - topic: User's video topic
        - duration_seconds: Requested duration
        - aspect_ratio: Video aspect ratio
        - resolution: Video resolution
        - category: Category preference
        - user_reference_image_url: Optional user reference image
        
    Output to state:
        - intent_metadata: Extracted intent information
        - selected_tool: Selected tool metadata
        - tool_execution_params: Tool-specific parameters
        
    Args:
        state: Current workflow state
        
    Returns:
        State update dict with intent/tool selection results
    """
    logger.info("=" * 60)
    logger.info("NODE: Intent/Tool Selector - Starting")
    logger.info("=" * 60)
    
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Topic: {topic[:50]}...")
    
    try:
        agent = IntentToolSelectorAgent()
        
        result = await agent.run(
            topic=topic,
            duration_seconds=state.get("duration_seconds", 18),
            aspect_ratio=state.get("aspect_ratio", "9:16"),
            resolution=state.get("resolution", "1080p"),
            category=state.get("category", "auto"),
            user_has_reference_image=bool(state.get("user_reference_image_url")),
        )
        
        logger.info(f"Intent extracted: {result.intent_metadata.intent_type.value}")
        logger.info(f"Tool selected: {result.selected_tool.tool_name}")
        logger.info(f"Confidence: {result.confidence:.2f}")
        
        state_update = {
            "intent_metadata": result.intent_metadata.model_dump(),
            "selected_tool": result.selected_tool.model_dump(),
            "tool_execution_params": result.tool_execution_params,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "intent_tool_completed": utc_now_iso(),
            },
        }
        
        logger.info("NODE: Intent/Tool Selector - Complete")
        logger.info("=" * 60)
        
        return state_update
        
    except Exception as e:
        logger.error(f"Intent/Tool Selection failed: {e}")
        
        return {
            "error": f"Intent/Tool Selection failed: {str(e)}",
            "error_details": {
                "node": "intent_tool_selector",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "intent_tool_failed": utc_now_iso(),
            },
        }


async def deep_research_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Deep Research.
    
    Placeholder - to be implemented in Phase 2.3.
    """
    logger.info("NODE: Deep Research - PLACEHOLDER")
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "deep_research_placeholder": utc_now_iso(),
        },
    }


async def script_writer_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Script Writer.
    
    Placeholder - to be implemented in Phase 2.4.
    """
    logger.info("NODE: Script Writer - PLACEHOLDER")
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "script_writer_placeholder": utc_now_iso(),
        },
    }


async def image_generator_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Image Generator.
    
    Placeholder - to be implemented in Phase 3.1.
    """
    logger.info("NODE: Image Generator - PLACEHOLDER")
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "image_generator_placeholder": utc_now_iso(),
        },
    }


async def video_generator_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Video Generator.
    
    Placeholder - to be implemented in Phase 3.2.
    """
    logger.info("NODE: Video Generator - PLACEHOLDER")
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "video_generator_placeholder": utc_now_iso(),
        },
    }


async def output_processor_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Output Processing.
    
    Placeholder - to be implemented in Phase 3.3.
    """
    logger.info("NODE: Output Processor - PLACEHOLDER")
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "output_processor_placeholder": utc_now_iso(),
        },
        "completed_at": utc_now_iso(),
    }


async def error_handler_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Error Handling.
    
    Handles errors from any node and prepares error response.
    """
    logger.error("NODE: Error Handler - Processing error")
    logger.error(f"Error: {state.get('error')}")
    
    return {
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "error_handled": utc_now_iso(),
        },
        "completed_at": utc_now_iso(),
    }


async def hitl_tool_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after tool selection - pauses for user approval."""
    logger.info("NODE: HITL Tool Gate - Awaiting approval")
    return {
        "current_hitl_gate": "tool_selection",
    }


async def hitl_research_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after research - pauses for user approval."""
    logger.info("NODE: HITL Research Gate - Awaiting approval")
    return {
        "current_hitl_gate": "research",
    }


async def hitl_script_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after script - pauses for user approval."""
    logger.info("NODE: HITL Script Gate - Awaiting approval")
    return {
        "current_hitl_gate": "script",
    }


async def hitl_image_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after images - pauses for user approval."""
    logger.info("NODE: HITL Image Gate - Awaiting approval")
    return {
        "current_hitl_gate": "images",
    }


async def hitl_video_gate_node(state: VideoGenerationState) -> dict:
    """HITL gate after video - pauses for user approval."""
    logger.info("NODE: HITL Video Gate - Awaiting approval")
    return {
        "current_hitl_gate": "video",
    }
