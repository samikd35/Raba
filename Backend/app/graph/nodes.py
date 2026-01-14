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
    
    Routes between factual, creative, and hybrid research strategies based on
    content type determined from intent_type and topic analysis.
    
    Input from state:
        - topic: User's video topic
        - intent_metadata: From Intent/Tool Selector (includes intent_type, tone)
        - selected_tool: Selected tool with category
        - duration_seconds: Video duration
        - workflow_id: For storage organization
        
    Output to state:
        - research_data: Research output (factual, creative, or hybrid)
        - research_images: List of image URLs from search
        
    Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md
    """
    logger.info("=" * 60)
    logger.info("NODE: Deep Research - Starting")
    logger.info("=" * 60)
    
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Topic: {topic[:50]}...")
    
    try:
        from app.agents.deep_research import get_deep_research_agent
        agent = get_deep_research_agent()
        updated_state = await agent.research(state)
        
        research_data = updated_state.get("research_data", {})
        research_images = updated_state.get("research_images", [])
        strategy = research_data.get("strategy_used", "unknown")
        
        logger.info(f"Strategy used: {strategy}")
        logger.info(f"Images found: {len(research_images)}")
        logger.info(f"Is fictional: {research_data.get('is_fictional', False)}")
        
        state_update = {
            "research_data": research_data,
            "research_images": research_images,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "deep_research_completed": utc_now_iso(),
            },
        }
        
        logger.info("NODE: Deep Research - Complete")
        logger.info("=" * 60)
        
        return state_update
        
    except Exception as e:
        logger.error(f"Deep Research failed: {e}")
        
        return {
            "error": f"Deep Research failed: {str(e)}",
            "error_details": {
                "node": "deep_research",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "deep_research_failed": utc_now_iso(),
            },
        }


async def script_writer_node(state: VideoGenerationState) -> dict:
    """
    LangGraph node for Script Writer.
    
    Generates a viral-optimized script from research data using the selected
    tool's style specifications.
    
    Input from state:
        - topic: User's video topic
        - research_data: From Deep Research (factual/creative/hybrid)
        - selected_tool: Tool metadata with style specs
        - intent_metadata: Intent type, tone, target audience
        - duration_seconds: Video duration
        
    Output to state:
        - script_output: Complete script as dict
        - hook: Hook section extracted
        - scenes: List of scenes extracted
        - call_to_action: CTA section extracted
        - viral_score: Calculated viral score
        
    Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md
    """
    logger.info("=" * 60)
    logger.info("NODE: Script Writer - Starting")
    logger.info("=" * 60)
    
    workflow_id = state.get("workflow_id", "unknown")
    topic = state.get("topic", "")
    duration = state.get("duration_seconds", 18)
    
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Topic: {topic[:50]}...")
    logger.info(f"Duration: {duration}s")
    
    try:
        from app.agents.script_writer import get_script_writer_agent
        
        agent = get_script_writer_agent()
        result = await agent.run(state)
        
        script_output = result.get("script_output", {})
        viral_score = result.get("viral_score", 0.0)
        scenes_count = len(result.get("scenes", []))
        
        logger.info(f"Script generated successfully")
        logger.info(f"Viral score: {viral_score:.2f}")
        logger.info(f"Scenes: {scenes_count}")
        
        state_update = {
            "script_output": script_output,
            "hook": result.get("hook"),
            "scenes": result.get("scenes"),
            "call_to_action": result.get("call_to_action"),
            "viral_score": viral_score,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "script_writer_completed": utc_now_iso(),
            },
        }
        
        logger.info("NODE: Script Writer - Complete")
        logger.info("=" * 60)
        
        return state_update
        
    except Exception as e:
        logger.error(f"Script Writer failed: {e}")
        
        return {
            "error": f"Script Writer failed: {str(e)}",
            "error_details": {
                "node": "script_writer",
                "exception": str(e),
                "timestamp": utc_now_iso(),
            },
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "script_writer_failed": utc_now_iso(),
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
