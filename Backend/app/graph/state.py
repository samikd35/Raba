"""RABA LangGraph State Definition.

Defines the VideoGenerationState TypedDict that is passed between all agents.
"""

from typing import Any, Optional, TypedDict

from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoGenerationState(TypedDict, total=False):
    """
    State schema for the video generation workflow.

    This state is passed between all agents in the LangGraph workflow.
    All fields are optional (total=False) to allow incremental updates.
    """

    workflow_id: str

    topic: str
    duration_seconds: int
    aspect_ratio: str
    resolution: str
    category: str
    hitl_mode: str
    enable_audio: bool
    enable_subtitles: bool
    user_reference_image_url: Optional[str]

    # User-selected tool (repository tool_id) to enforce
    user_selected_tool_id: Optional[str]

    # User-selected Veo model (string value from app.models.video.VideoModel)
    video_model: Optional[str]

    selected_tool: Optional[dict[str, Any]]
    intent_metadata: Optional[dict[str, Any]]
    tool_execution_params: Optional[dict[str, Any]]

    research_data: Optional[dict[str, Any]]
    research_images: Optional[list[str]]
    research_citations: Optional[list[dict[str, Any]]]

    script_output: Optional[dict[str, Any]]
    hook: Optional[dict[str, Any]]
    scenes: Optional[list[dict[str, Any]]]
    call_to_action: Optional[dict[str, Any]]
    viral_score: Optional[float]

    generated_images: Optional[list[str]]
    all_images: Optional[list[str]]
    image_metadata: Optional[list[dict[str, Any]]]

    # Storyboard context (computed in image_generator)
    storyboard_context: Optional[
        dict[str, Any]
    ]  # key_entities, transformation_flow, composition_layout
    master_image_type: Optional[str]  # "storyboard" | "single_scene"

    segment_contexts: Optional[list[dict[str, Any]]]
    segment_context_status: Optional[str]

    video_url: Optional[str]
    video_metadata: Optional[dict[str, Any]]
    video_segments: Optional[list[dict[str, Any]]]
    video_output: Optional[dict[str, Any]]
    final_video_url: Optional[str]
    clean_video_url: Optional[str]
    subtitle_overlays: Optional[list[dict[str, Any]]]
    character_reference_sheet: Optional[dict[str, Any]]
    visual_validation: Optional[dict[str, Any]]
    global_style_anchor: Optional[dict[str, Any]]

    status: Optional[str]
    final_output: Optional[dict[str, Any]]
    generation_time_seconds: Optional[float]

    hitl_approved: dict[str, bool]
    hitl_feedback: list[dict[str, Any]]
    current_hitl_gate: Optional[str]
    regeneration_counts: dict[str, int]
    hitl_gate_outputs: dict[str, dict[str, Any]]  # Cached outputs for review
    pending_regeneration: Optional[str]  # Gate requesting regeneration
    regeneration_feedback: Optional[str]  # User feedback for regeneration

    error: Optional[str]
    error_details: Optional[dict[str, Any]]

    started_at: str
    phase_timestamps: dict[str, str]
    completed_at: Optional[str]


def create_initial_state(
    workflow_id: str,
    topic: str,
    duration_seconds: int = 18,
    aspect_ratio: str = "9:16",
    resolution: str = "1080p",
    category: str = "auto",
    hitl_mode: str = "auto",
    enable_audio: bool = False,
    enable_subtitles: bool = False,
    user_reference_image_url: Optional[str] = None,
) -> VideoGenerationState:
    """
    Create initial state for a new workflow.

    Args:
        workflow_id: Unique workflow identifier
        topic: Video topic
        duration_seconds: Video duration (8-25)
        aspect_ratio: Video aspect ratio
        resolution: Video resolution
        category: Visual style category
        hitl_mode: Human-in-the-loop mode
        enable_audio: Generate audio
        enable_subtitles: Generate subtitles
        user_reference_image_url: User-uploaded reference image

    Returns:
        Initial VideoGenerationState
    """
    from app.utils.helpers import utc_now_iso

    logger.info(f"Creating initial state for workflow: {workflow_id}")
    logger.info(f"  Topic: {topic[:50]}...")
    logger.info(f"  Duration: {duration_seconds}s")
    logger.info(f"  HITL Mode: {hitl_mode}")

    state: VideoGenerationState = {
        "workflow_id": workflow_id,
        "topic": topic,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "category": category,
        "hitl_mode": hitl_mode,
        "enable_audio": enable_audio,
        "enable_subtitles": enable_subtitles,
        "user_reference_image_url": user_reference_image_url,
        "selected_tool": None,
        "intent_metadata": None,
        "tool_execution_params": None,
        "research_data": None,
        "research_images": None,
        "research_citations": None,
        "script_output": None,
        "hook": None,
        "scenes": None,
        "call_to_action": None,
        "viral_score": None,
        "generated_images": None,
        "all_images": None,
        "image_metadata": None,
        "segment_contexts": None,
        "segment_context_status": None,
        "video_url": None,
        "video_metadata": None,
        "video_segments": None,
        "hitl_approved": {},
        "hitl_feedback": [],
        "current_hitl_gate": None,
        "regeneration_counts": {},
        "hitl_gate_outputs": {},
        "pending_regeneration": None,
        "regeneration_feedback": None,
        "error": None,
        "error_details": None,
        "started_at": utc_now_iso(),
        "phase_timestamps": {},
        "completed_at": None,
    }

    logger.info(f"Initial state created for workflow: {workflow_id}")

    return state
