"""RABA Metadata Utilities.

Helper functions for calculating generation timing, building workflow
summaries, and aggregating metadata for output processing.

Reference: PHASE3_3_OUTPUT_PROCESSOR_PLAN.md Section 4 (Step 3)
"""

from datetime import datetime
from typing import Any, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


def parse_iso_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse ISO format timestamp string to datetime.
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        datetime object or None if parsing fails
    """
    if not timestamp_str:
        return None
    
    try:
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def calculate_phase_durations(phase_timestamps: dict[str, str]) -> dict[str, float]:
    """Calculate duration of each phase from timestamp pairs.
    
    Expects timestamps in format: {phase}_started, {phase}_completed
    or just {phase}_completed (calculates from previous phase end).
    
    Args:
        phase_timestamps: Dict of phase timestamps
        
    Returns:
        Dict of phase names to duration in seconds
        
    Reference: SRS.md FR-903 - Track generation time per step
    
    Example output:
        {
            "intent_tool_selector": 2.3,
            "deep_research": 15.2,
            "script_writer": 8.1,
            "image_generator": 45.3,
            "video_generator": 180.5,
            "output_processor": 1.2
        }
    """
    durations = {}
    
    phase_order = [
        "intent_tool",
        "deep_research",
        "script_writer",
        "image_generator",
        "video_generator",
        "output_processor",
    ]
    
    completed_times = {}
    for key, value in phase_timestamps.items():
        if "completed" in key:
            phase_name = key.replace("_completed", "")
            completed_times[phase_name] = parse_iso_timestamp(value)
    
    previous_end = None
    
    for phase in phase_order:
        end_time = completed_times.get(phase)
        
        if end_time:
            if previous_end:
                duration = (end_time - previous_end).total_seconds()
                durations[phase] = max(0.0, duration)
            previous_end = end_time
    
    for phase_name, end_time in completed_times.items():
        if phase_name not in durations and phase_name not in phase_order:
            durations[phase_name] = 0.0
    
    return durations


def calculate_total_generation_time(
    started_at: str,
    completed_at: Optional[str] = None,
) -> float:
    """Calculate total generation time in seconds.
    
    Args:
        started_at: Workflow start timestamp (ISO format)
        completed_at: Workflow completion timestamp (ISO format), defaults to now
        
    Returns:
        Total time in seconds
    """
    start = parse_iso_timestamp(started_at)
    if not start:
        logger.warning("Could not parse started_at, returning 0")
        return 0.0
    
    if completed_at:
        end = parse_iso_timestamp(completed_at)
    else:
        end = datetime.utcnow()
    
    if not end:
        end = datetime.utcnow()
    
    if start.tzinfo is not None and end.tzinfo is None:
        start = start.replace(tzinfo=None)
    elif start.tzinfo is None and end.tzinfo is not None:
        end = end.replace(tzinfo=None)
    
    duration = (end - start).total_seconds()
    return max(0.0, duration)


def build_workflow_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Build summary metadata for API response.
    
    Args:
        state: Workflow state dict
        
    Returns:
        Summary dict with tool, category, topic, etc.
    """
    selected_tool = state.get("selected_tool", {}) or {}
    script_output = state.get("script_output", {}) or {}
    video_output = state.get("video_output", {}) or {}
    video_metadata = state.get("video_metadata", {}) or {}
    
    topic = state.get("topic", "")
    if len(topic) > 100:
        topic = topic[:97] + "..."
    
    segment_count = 1
    if video_metadata.get("segments"):
        segment_count = video_metadata.get("segments")
    elif video_output.get("segments"):
        segment_count = len(video_output.get("segments", []))
    
    return {
        "tool_used": selected_tool.get("tool_name", "Unknown"),
        "tool_id": selected_tool.get("tool_id", ""),
        "category": selected_tool.get("category", state.get("category", "")),
        "topic": topic,
        "segment_count": segment_count,
        "viral_score": script_output.get("viral_score") or state.get("viral_score"),
        "hitl_mode": state.get("hitl_mode", "auto"),
        "audio_enabled": state.get("enable_audio", False),
        "subtitles_enabled": state.get("enable_subtitles", False),
    }


def consolidate_media_urls(state: dict[str, Any]) -> dict[str, Any]:
    """Consolidate all media URLs from workflow state.
    
    Args:
        state: Workflow state dict
        
    Returns:
        Dict with video_url, all_image_urls, and counts
        
    Reference: SRS.md FR-804 - Track all media
    """
    video_url = state.get("final_video_url", "")
    if not video_url:
        video_output = state.get("video_output", {}) or {}
        if isinstance(video_output, dict):
            video_url = video_output.get("video", {}).get("url", "")
            if not video_url:
                video_url = video_output.get("url", "")
    
    all_images = []
    user_ref = state.get("user_reference_image_url")
    if user_ref:
        all_images.append(user_ref)
    
    research_images = state.get("research_images", []) or []
    all_images.extend(research_images)
    
    generated_images = state.get("generated_images", []) or []
    all_images.extend(generated_images)
    
    if state.get("all_images"):
        for img in state.get("all_images", []):
            if img not in all_images:
                all_images.append(img)
    
    return {
        "video_url": video_url,
        "all_image_urls": all_images,
        "generated_count": len(generated_images),
        "research_count": len(research_images),
        "user_reference_included": bool(user_ref),
        "total_count": len(all_images),
    }


def extract_video_metadata(state: dict[str, Any]) -> dict[str, Any]:
    """Extract video metadata from state.
    
    Args:
        state: Workflow state dict
        
    Returns:
        Video metadata dict
    """
    video_output = state.get("video_output", {}) or {}
    video_metadata = state.get("video_metadata", {}) or {}
    
    video_data = video_output.get("video", {}) if isinstance(video_output, dict) else {}
    
    duration = state.get("duration_seconds", 18)
    if video_data.get("duration_seconds"):
        duration = video_data.get("duration_seconds")
    elif video_metadata.get("duration_seconds"):
        duration = video_metadata.get("duration_seconds")
    
    resolution = state.get("resolution", "720p")
    if video_data.get("resolution"):
        resolution = video_data.get("resolution")
        if hasattr(resolution, "value"):
            resolution = resolution.value
    elif video_metadata.get("resolution"):
        resolution = video_metadata.get("resolution")
    
    aspect_ratio = state.get("aspect_ratio", "9:16")
    if video_data.get("aspect_ratio"):
        aspect_ratio = video_data.get("aspect_ratio")
        if hasattr(aspect_ratio, "value"):
            aspect_ratio = aspect_ratio.value
    elif video_metadata.get("aspect_ratio"):
        aspect_ratio = video_metadata.get("aspect_ratio")
    
    segment_count = 1
    if video_data.get("total_segments"):
        segment_count = video_data.get("total_segments")
    elif video_metadata.get("segments"):
        segment_count = video_metadata.get("segments")
    elif video_output.get("segments"):
        segment_count = len(video_output.get("segments", []))
    
    file_size = video_data.get("file_size_bytes", 0)
    audio_included = video_data.get("audio_included", state.get("enable_audio", True))
    
    return {
        "duration_seconds": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "segment_count": segment_count,
        "file_size_bytes": file_size,
        "audio_included": audio_included,
    }


def generate_shareable_link(workflow_id: str, video_url: str) -> str:
    """Generate a shareable link for the video.
    
    For now, returns the direct video URL.
    Future: Could generate shortened URLs or embed links.
    
    Args:
        workflow_id: Workflow identifier
        video_url: Direct video URL
        
    Returns:
        Shareable link
    """
    return video_url
