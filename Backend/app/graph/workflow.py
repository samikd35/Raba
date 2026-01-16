"""RABA LangGraph Workflow Definition.

Defines the video generation workflow graph structure.

NOTE: This file defines the graph STRUCTURE only. Agent implementations
are added in Phase 2+. The graph cannot be compiled until agents are implemented.
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.graph.state import VideoGenerationState
from app.utils.logging import get_logger

logger = get_logger(__name__)

NODE_INTENT_TOOL_SELECTOR = "intent_tool_selector"
NODE_DEEP_RESEARCH = "deep_research"
NODE_SCRIPT_WRITER = "script_writer"
NODE_IMAGE_GENERATOR = "image_generator"
NODE_VIDEO_GENERATOR = "video_generator"
NODE_OUTPUT_PROCESSOR = "output_processor"

NODE_HITL_TOOL_GATE = "hitl_tool_gate"
NODE_HITL_RESEARCH_GATE = "hitl_research_gate"
NODE_HITL_SCRIPT_GATE = "hitl_script_gate"
NODE_HITL_IMAGE_GATE = "hitl_image_gate"
NODE_HITL_VIDEO_GATE = "hitl_video_gate"

NODE_ERROR_HANDLER = "error_handler"


def route_after_intent_tool_selection(
    state: VideoGenerationState,
) -> Literal["hitl_tool_gate", "deep_research", "error_handler"]:
    """
    Route after Intent/Tool Selection agent.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    logger.info("Routing after Intent/Tool Selection...")
    
    if state.get("error"):
        logger.warning(f"Error detected: {state.get('error')}")
        return NODE_ERROR_HANDLER
    
    if not state.get("selected_tool"):
        logger.warning("No tool selected - routing to error handler")
        return NODE_ERROR_HANDLER
    
    if state.get("hitl_mode") == "manual" and not state.get("hitl_approved", {}).get("tool_selection"):
        logger.info("Manual mode - routing to HITL tool gate")
        return NODE_HITL_TOOL_GATE
    
    logger.info("Routing to Deep Research")
    return NODE_DEEP_RESEARCH


def route_after_research(
    state: VideoGenerationState,
) -> Literal["hitl_research_gate", "script_writer", "error_handler"]:
    """Route after Deep Research agent."""
    logger.info("Routing after Deep Research...")
    
    if state.get("error"):
        return NODE_ERROR_HANDLER
    
    if state.get("hitl_mode") == "manual" and not state.get("hitl_approved", {}).get("research"):
        logger.info("Manual mode - routing to HITL research gate")
        return NODE_HITL_RESEARCH_GATE
    
    logger.info("Routing to Script Writer")
    return NODE_SCRIPT_WRITER


def route_after_script(
    state: VideoGenerationState,
) -> Literal["hitl_script_gate", "image_generator", "error_handler"]:
    """Route after Script Writer agent."""
    logger.info("Routing after Script Writer...")
    
    if state.get("error"):
        return NODE_ERROR_HANDLER
    
    if state.get("hitl_mode") == "manual" and not state.get("hitl_approved", {}).get("script"):
        logger.info("Manual mode - routing to HITL script gate")
        return NODE_HITL_SCRIPT_GATE
    
    logger.info("Routing to Image Generator")
    return NODE_IMAGE_GENERATOR


def route_after_images(
    state: VideoGenerationState,
) -> Literal["hitl_image_gate", "video_generator", "error_handler"]:
    """Route after Image Generator agent."""
    logger.info("Routing after Image Generator...")
    
    if state.get("error"):
        return NODE_ERROR_HANDLER
    
    if state.get("hitl_mode") == "manual" and not state.get("hitl_approved", {}).get("images"):
        logger.info("Manual mode - routing to HITL image gate")
        return NODE_HITL_IMAGE_GATE
    
    logger.info("Routing to Video Generator")
    return NODE_VIDEO_GENERATOR


def route_after_video(
    state: VideoGenerationState,
) -> Literal["hitl_video_gate", "output_processor", "error_handler"]:
    """Route after Video Generator agent."""
    logger.info("Routing after Video Generator...")
    
    if state.get("error"):
        return NODE_ERROR_HANDLER
    
    if state.get("hitl_mode") == "manual" and not state.get("hitl_approved", {}).get("video"):
        logger.info("Manual mode - routing to HITL video gate")
        return NODE_HITL_VIDEO_GATE
    
    logger.info("Routing to Output Processor")
    return NODE_OUTPUT_PROCESSOR


def route_after_hitl_tool_gate(
    state: VideoGenerationState,
) -> Literal["intent_tool_selector", "deep_research"]:
    """Route after HITL Tool Gate - support regeneration.
    
    If pending_regeneration is set for this gate, route back to agent.
    Otherwise continue to next step.
    """
    if state.get("pending_regeneration") == "tool_selection":
        logger.info("Regeneration requested - routing back to Intent/Tool Selector")
        return NODE_INTENT_TOOL_SELECTOR
    return NODE_DEEP_RESEARCH


def route_after_hitl_research_gate(
    state: VideoGenerationState,
) -> Literal["deep_research", "script_writer"]:
    """Route after HITL Research Gate - support regeneration."""
    if state.get("pending_regeneration") == "research":
        logger.info("Regeneration requested - routing back to Deep Research")
        return NODE_DEEP_RESEARCH
    return NODE_SCRIPT_WRITER


def route_after_hitl_script_gate(
    state: VideoGenerationState,
) -> Literal["script_writer", "image_generator"]:
    """Route after HITL Script Gate - support regeneration."""
    if state.get("pending_regeneration") == "script":
        logger.info("Regeneration requested - routing back to Script Writer")
        return NODE_SCRIPT_WRITER
    return NODE_IMAGE_GENERATOR


def route_after_hitl_image_gate(
    state: VideoGenerationState,
) -> Literal["image_generator", "video_generator"]:
    """Route after HITL Image Gate - support regeneration."""
    if state.get("pending_regeneration") == "images":
        logger.info("Regeneration requested - routing back to Image Generator")
        return NODE_IMAGE_GENERATOR
    return NODE_VIDEO_GENERATOR


def route_after_hitl_video_gate(
    state: VideoGenerationState,
) -> Literal["video_generator", "output_processor"]:
    """Route after HITL Video Gate - support regeneration."""
    if state.get("pending_regeneration") == "video":
        logger.info("Regeneration requested - routing back to Video Generator")
        return NODE_VIDEO_GENERATOR
    return NODE_OUTPUT_PROCESSOR


def create_workflow_graph() -> StateGraph:
    """
    Create the video generation workflow graph.
    
    Returns:
        StateGraph instance with nodes and edges configured
    """
    from app.graph.nodes import (
        intent_tool_selector_node,
        deep_research_node,
        script_writer_node,
        image_generator_node,
        video_generator_node,
        output_processor_node,
        error_handler_node,
        hitl_tool_gate_node,
        hitl_research_gate_node,
        hitl_script_gate_node,
        hitl_image_gate_node,
        hitl_video_gate_node,
    )
    
    logger.info("=" * 60)
    logger.info("WORKFLOW GRAPH - Creating and configuring")
    logger.info("=" * 60)
    
    workflow = StateGraph(VideoGenerationState)
    
    workflow.add_node(NODE_INTENT_TOOL_SELECTOR, intent_tool_selector_node)
    workflow.add_node(NODE_DEEP_RESEARCH, deep_research_node)
    workflow.add_node(NODE_SCRIPT_WRITER, script_writer_node)
    workflow.add_node(NODE_IMAGE_GENERATOR, image_generator_node)
    workflow.add_node(NODE_VIDEO_GENERATOR, video_generator_node)
    workflow.add_node(NODE_OUTPUT_PROCESSOR, output_processor_node)
    workflow.add_node(NODE_ERROR_HANDLER, error_handler_node)
    
    workflow.add_node(NODE_HITL_TOOL_GATE, hitl_tool_gate_node)
    workflow.add_node(NODE_HITL_RESEARCH_GATE, hitl_research_gate_node)
    workflow.add_node(NODE_HITL_SCRIPT_GATE, hitl_script_gate_node)
    workflow.add_node(NODE_HITL_IMAGE_GATE, hitl_image_gate_node)
    workflow.add_node(NODE_HITL_VIDEO_GATE, hitl_video_gate_node)
    
    logger.info("Added all nodes to graph")
    
    workflow.add_edge(START, NODE_INTENT_TOOL_SELECTOR)
    workflow.add_conditional_edges(
        NODE_INTENT_TOOL_SELECTOR,
        route_after_intent_tool_selection,
    )
    
    # HITL gates now use conditional edges to support regeneration
    workflow.add_conditional_edges(NODE_HITL_TOOL_GATE, route_after_hitl_tool_gate)
    workflow.add_conditional_edges(NODE_DEEP_RESEARCH, route_after_research)
    
    workflow.add_conditional_edges(NODE_HITL_RESEARCH_GATE, route_after_hitl_research_gate)
    workflow.add_conditional_edges(NODE_SCRIPT_WRITER, route_after_script)
    
    workflow.add_conditional_edges(NODE_HITL_SCRIPT_GATE, route_after_hitl_script_gate)
    workflow.add_conditional_edges(NODE_IMAGE_GENERATOR, route_after_images)
    
    workflow.add_conditional_edges(NODE_HITL_IMAGE_GATE, route_after_hitl_image_gate)
    workflow.add_conditional_edges(NODE_VIDEO_GENERATOR, route_after_video)
    
    workflow.add_conditional_edges(NODE_HITL_VIDEO_GATE, route_after_hitl_video_gate)
    workflow.add_edge(NODE_OUTPUT_PROCESSOR, END)
    
    workflow.add_edge(NODE_ERROR_HANDLER, END)
    
    logger.info("Added all edges to graph")
    logger.info("=" * 60)
    
    return workflow


def get_workflow_info() -> dict:
    """
    Get information about the workflow structure.
    
    Returns:
        Dictionary with workflow metadata
    """
    return {
        "name": "RABA Video Generation Workflow",
        "version": "0.2.0",
        "nodes": {
            "agents": [
                NODE_INTENT_TOOL_SELECTOR,
                NODE_DEEP_RESEARCH,
                NODE_SCRIPT_WRITER,
                NODE_IMAGE_GENERATOR,
                NODE_VIDEO_GENERATOR,
                NODE_OUTPUT_PROCESSOR,
            ],
            "hitl_gates": [
                NODE_HITL_TOOL_GATE,
                NODE_HITL_RESEARCH_GATE,
                NODE_HITL_SCRIPT_GATE,
                NODE_HITL_IMAGE_GATE,
                NODE_HITL_VIDEO_GATE,
            ],
            "error": [NODE_ERROR_HANDLER],
        },
        "edges": {
            "flow": [
                f"{START} -> {NODE_INTENT_TOOL_SELECTOR}",
                f"{NODE_INTENT_TOOL_SELECTOR} -> {NODE_DEEP_RESEARCH}",
                f"{NODE_DEEP_RESEARCH} -> {NODE_SCRIPT_WRITER}",
                f"{NODE_SCRIPT_WRITER} -> {NODE_IMAGE_GENERATOR}",
                f"{NODE_IMAGE_GENERATOR} -> {NODE_VIDEO_GENERATOR}",
                f"{NODE_VIDEO_GENERATOR} -> {NODE_OUTPUT_PROCESSOR}",
                f"{NODE_OUTPUT_PROCESSOR} -> {END}",
            ],
        },
        "status": "ready",
        "ready_to_compile": True,
        "implemented_agents": [NODE_INTENT_TOOL_SELECTOR],
        "placeholder_agents": [
            NODE_DEEP_RESEARCH,
            NODE_SCRIPT_WRITER,
            NODE_IMAGE_GENERATOR,
            NODE_VIDEO_GENERATOR,
            NODE_OUTPUT_PROCESSOR,
        ],
    }
