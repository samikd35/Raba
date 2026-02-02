"""RABA Video Generator Agent.

Generates final YouTube Shorts (8-25 seconds) using Veo 3.1 with native audio
from script, reference images, and workflow state.

Key Features:
- Multi-segment video generation for videos >8s
- Seamless video extension (single combined output)
- Tool-specific video vocabulary and prompts
- Reference image selection (max 3)
- Supabase Storage upload and persistence

Reference:
- PHASE3_2_VIDEO_GENERATOR_PLAN.md
- RABA_Architecture.md Section 2.7
- Backend/Documentations/veo_doc.md
- Backend/Documentations/veo_prompting_guide.md
"""

import time
from datetime import datetime
from typing import Any, Optional

from app.graph.state import VideoGenerationState
from app.models.audio import AudioManifest
from app.models.video import (
    GeneratedVideo,
    HITLVideoFeedback,
    ReferenceImageSelection,
    VideoAspectRatio,
    VideoGenerationConfig,
    VideoGenerationRequest,
    VideoGeneratorOutput,
    VideoModel,
    VideoResolution,
    VideoSegment,
    VideoSegmentType,
)
from app.services.veo import get_veo_service, VeoServiceError
from app.services.prompt_builder import get_prompt_builder
from app.services.segment_splitter import compute_segment_context_blocks
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_SEGMENT_DURATION = 8
EXTENSION_DURATION = 7
MAX_REFERENCE_IMAGES = 3

ASPECT_RATIO_MAP = {
    "9:16": VideoAspectRatio.PORTRAIT_9_16,
    "16:9": VideoAspectRatio.LANDSCAPE_16_9,
}

RESOLUTION_MAP = {
    "720p": VideoResolution.RES_720P,
    "1080p": VideoResolution.RES_1080P,
}


def _storyboard_reference_note(segment_index: int, total_segments: int, is_storyboard: bool) -> str:
    """Build a compact note to guide Veo to the correct storyboard panel."""
    if not is_storyboard:
        return ""
    idx = max(1, segment_index + 1)
    tot = max(1, total_segments)
    return (
        "\n[STORYBOARD REFERENCE] Reference the master storyboard image. "
        f"This is segment {idx} of {tot}. Focus on panel {idx} for visual guidance. "
        "Animate the moment in that panel while preserving overall storyboard style.\n"
    )


def calculate_segments_needed(duration_seconds: int) -> int:
    """Calculate number of segments needed for target duration.

    Args:
        duration_seconds: Target video duration (8-25s)

    Returns:
        Number of segments needed

    Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md Section 2.3
    """
    if duration_seconds <= MAX_SEGMENT_DURATION:
        return 1

    remaining = duration_seconds - MAX_SEGMENT_DURATION
    extensions_needed = (remaining + EXTENSION_DURATION - 1) // EXTENSION_DURATION

    return 1 + extensions_needed


def plan_video_segments(
    duration_seconds: int,
    audio_manifest: Optional[AudioManifest] = None,
) -> list[dict]:
    """Plan video segments for target duration.

    Args:
        duration_seconds: Target video duration

    Returns:
        List of segment plans with timing info
    """
    if audio_manifest and audio_manifest.segments:
        segments = []
        current_time = 0.0
        for idx, audio_segment in enumerate(audio_manifest.segments):
            duration = float(audio_segment.duration_seconds)
            segment_type = "initial" if idx == 0 else "extension"
            segments.append(
                {
                    "segment_number": idx,
                    "type": segment_type,
                    "start_time": current_time,
                    "end_time": current_time + duration,
                    "duration": duration,
                }
            )
            current_time += duration
        logger.info(
            f"Planned {len(segments)} segments from audio manifest ({current_time:.2f}s total)"
        )
        return segments

    segments = []
    current_time = 0.0

    initial_duration = min(duration_seconds, MAX_SEGMENT_DURATION)
    segments.append(
        {
            "segment_number": 0,
            "type": "initial",
            "start_time": 0.0,
            "end_time": initial_duration,
            "duration": initial_duration,
        }
    )
    current_time = initial_duration

    segment_num = 1
    while current_time < duration_seconds:
        remaining = duration_seconds - current_time
        segment_duration = min(remaining, EXTENSION_DURATION)

        segments.append(
            {
                "segment_number": segment_num,
                "type": "extension",
                "start_time": current_time,
                "end_time": current_time + segment_duration,
                "duration": segment_duration,
            }
        )

        current_time += EXTENSION_DURATION
        segment_num += 1

    logger.info(f"Planned {len(segments)} segments for {duration_seconds}s video")
    return segments


def select_reference_images(
    generated_images: list[str],
    image_metadata: list[dict] | None = None,
    max_count: int = MAX_REFERENCE_IMAGES,
) -> list[str]:
    """Select reference images from ONLY generated images (Nano Banana Pro).

    IMPORTANT: Video Generator uses ONLY generated images from Image Generator.
    Research images (Google Search + user uploads) are used as reference for
    Image Generator, NOT for Video Generator.

    Uses ALL generated images up to max_count (3 for Veo 3.1). If more than
    max_count are generated, selects first, middle, and last for optimal coverage.

    Args:
        generated_images: URLs of images generated by Nano Banana Pro
        max_count: Maximum images to select (default 3)

    Returns:
        List of selected generated image URLs (max 3)

    Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md Section 2.5
    """
    if not generated_images:
        logger.warning("No generated images available for video generation")
        return []

    # Filter out failed uploads
    valid_images = [
        img
        for img in generated_images
        if not (isinstance(img, str) and img.startswith("upload_failed://"))
    ]
    if len(valid_images) < len(generated_images):
        logger.warning(f"Filtered out {len(generated_images) - len(valid_images)} failed upload(s)")

    if not valid_images:
        logger.warning("No valid generated images after filtering failed uploads")
        return []

    selected: list[str] = []
    # Prefer ingredients ordering if metadata with roles is provided
    if image_metadata:
        try:
            role_order = ["subject", "environment", "object"]
            role_to_url = {}
            for md in image_metadata:
                role = (md or {}).get("role")
                url = (md or {}).get("url")
                if role and url and role not in role_to_url:
                    role_to_url[role] = url
            for role in role_order:
                if role in role_to_url and len(selected) < max_count:
                    selected.append(role_to_url[role])
        except Exception as e:
            logger.warning(f"Ingredients-aware selection failed: {e}; falling back")
    # Fill remaining slots from valid_images order
    for url in valid_images:
        if len(selected) >= max_count:
            break
        if url not in selected:
            selected.append(url)
    logger.info(f"Reference images for Veo: {len(selected)} images selected")

    logger.info(f"Reference images for Veo: {len(selected)} images selected")
    if len(selected) < len(generated_images) and len(generated_images) <= max_count:
        logger.warning(
            f"Not all {len(generated_images)} generated images are being used (only {len(selected)} selected)"
        )

    return selected


def build_video_prompt(
    script_output: dict,
    tool_category: str,
    topic: str,
    segment_info: dict,
    is_extension: bool = False,
    previous_segment_end: Optional[str] = None,
    anchor: Optional[dict] = None,
    segment_ctx: Optional[dict] = None,
    audio_segment: Optional[dict] = None,
    enable_audio: bool = False,
    enable_subtitles: bool = False,
) -> str:
    """Build Veo prompt from script and tool vocabulary.

    Args:
        script_output: Script with hook, scenes, CTA
        tool_category: Tool category for visual style
        topic: Video topic
        segment_info: Current segment timing info
        is_extension: Whether this is an extension segment
        previous_segment_end: Description of how previous segment ended

    Returns:
        Formatted Veo prompt

    Reference: veo_prompting_guide.md - Anatomy of a Veo prompt
    """
    parts = []

    # USER INTENT BLOCK - HIGHEST PRIORITY (placed first for maximum impact)
    parts.append("[USER REQUEST - MUST FOLLOW EXACTLY]\n")
    parts.append(f"Topic: {topic}\n")
    if not enable_audio:
        parts.append("Audio: SILENT VIDEO - No speaking, no dialogue, no voice-over, no talking\n")
    if not enable_subtitles:
        parts.append("Text: NO TEXT OVERLAYS, no subtitles, no captions, no on-screen text\n")
    duration = segment_info.get("end_time", 8) - segment_info.get("start_time", 0)
    parts.append(f"Duration: {duration:.2f} seconds\n")
    parts.append(f"Style: {tool_category}\n")
    parts.append("[END USER REQUEST]\n\n")

    # Veo 3.1 prompt structure elements (subject, action, style, camera, composition)
    parts.append("[VEO 3.1 GENERATION REQUIREMENTS]\n")
    try:
        parts.append(f"Subject: {extract_subject_from_script(script_output)}\n")
    except Exception:
        parts.append("Subject: main subject\n")
    try:
        parts.append(f"Action: {extract_action_from_segment(script_output, segment_info)}\n")
    except Exception:
        parts.append("Action: moving\n")
    parts.append(f"Style: {tool_category}\n")
    camera_position = (anchor.get("camera") if anchor else None) or "eye-level"
    parts.append(f"Camera: {camera_position}\n")
    composition = "medium shot" if not is_extension else "continuous from previous"
    parts.append(f"Composition: {composition}\n")
    if anchor and anchor.get("color_palette"):
        parts.append(f"Ambiance: {', '.join(anchor.get('color_palette')[:3])} tones\n")
    parts.append("[END VEO REQUIREMENTS]\n\n")

    if is_extension and previous_segment_end:
        parts.append(f"[CONTINUATION] Seamlessly continue from: {previous_segment_end}\n\n")

    # Style and lighting are handled through anchor if available, otherwise omitted
    # The tool category and scene descriptions provide sufficient style context
    if anchor:
        if anchor.get("color_palette"):
            parts.append(f"[STYLE] {', '.join(anchor.get('color_palette', [])[:4])}\n")
        if anchor.get("lighting"):
            parts.append(f"[LIGHTING] {anchor.get('lighting', '')}\n\n")

    hook = script_output.get("hook", {})
    scenes = script_output.get("scenes", [])
    cta = script_output.get("call_to_action", {})

    start_time = segment_info.get("start_time", 0)
    end_time = segment_info.get("end_time", 8)

    audio_dialogue = ""
    if audio_segment:
        audio_dialogue = audio_segment.get("text_transcript", "")

    if not is_extension and hook:
        hook_text = hook.get("text", "")
        hook_visual = hook.get("visual_direction", "")
        if hook_text:
            parts.append(f"[00:00-00:02] HOOK\n")
            parts.append(f'Dialogue: "{hook_text}"\n')
            if hook_visual:
                parts.append(f"Visual: {hook_visual}\n")
            cam = ""
            if anchor and anchor.get("motion_language"):
                cam = ", ".join(anchor.get("motion_language", [])[:2])
            elif anchor and anchor.get("camera"):
                cam = anchor.get("camera")
            if cam:
                parts.append(f"Camera: {cam}\n\n")
            else:
                parts.append("\n")

    relevant_scenes = []
    for scene in scenes:
        scene_start = scene.get("start_time", 0)
        scene_end = scene.get("end_time", scene_start + 3)

        if scene_end > start_time and scene_start < end_time:
            relevant_scenes.append(scene)

    for i, scene in enumerate(relevant_scenes[:3]):
        scene_num = scene.get("scene_number", i + 1)
        description = scene.get("description", "")
        dialogue = scene.get("dialogue", "")
        camera = scene.get(
            "camera_direction",
            (
                ", ".join(anchor.get("motion_language", [])[:2])
                if anchor and anchor.get("motion_language")
                else ""
            ),
        )
        mood = scene.get("mood", "")

        parts.append(f"[SCENE {scene_num}]\n")
        if description:
            parts.append(f"Visual: {description}\n")
        if audio_dialogue:
            parts.append(f'Dialogue: "{audio_dialogue}"\n')
        elif dialogue:
            parts.append(f'Dialogue: "{dialogue}"\n')
        parts.append(f"Camera: {camera}\n")
        if mood:
            parts.append(f"Mood: {mood}\n")
        parts.append("\n")

    if not is_extension and cta and end_time >= script_output.get("duration_seconds", 18) - 3:
        cta_text = cta.get("text", "")
        cta_visual = cta.get("visual_direction", "")
        if cta_text:
            parts.append(f"[CALL TO ACTION]\n")
            parts.append(f'Dialogue: "{cta_text}"\n')
            if cta_visual:
                parts.append(f"Visual: {cta_visual}\n")
            parts.append("\n")

    # Optional, structured audio block (event-anchored)
    if enable_audio and segment_ctx:
        dlg = segment_ctx.get("dialogue_cue") or ""
        sfx = segment_ctx.get("sfx_cue") or ""
        amb = segment_ctx.get("ambient_cue") or ""
        mus = segment_ctx.get("music_cue") or ""
        visual_anchor = segment_ctx.get("segment_action") or "scene action"
        # Provide compact segment context for continuity and action
        parts.append("[SEGMENT CONTEXT]\n")
        parts.append(
            f"Segment: {segment_ctx.get('segment_index', 0)} of {segment_ctx.get('total_segments', 1)}\n"
        )
        if segment_ctx.get("anchor_state"):
            parts.append(f"Previous State: {segment_ctx.get('anchor_state')}\n")
        if segment_ctx.get("segment_action"):
            parts.append(f"Action: {segment_ctx.get('segment_action')}\n")
        if segment_ctx.get("goal_state"):
            parts.append(f"Goal State: {segment_ctx.get('goal_state')}\n")
        parts.append("\n")
        parts.append("[AUDIO - EVENT ANCHORED]\n")
        if audio_dialogue:
            parts.append(f'Dialogue: "{audio_dialogue}" (spoken DURING: {visual_anchor})\n')
        elif dlg:
            parts.append(f'Dialogue: "{dlg}" (spoken DURING: {visual_anchor})\n')
        if sfx:
            parts.append(f"SFX: {sfx} (triggered BY: {visual_anchor})\n")
        if amb:
            parts.append(f"Ambient: {amb} (continuous)\n")
        if mus:
            parts.append(f"Music: {mus} (intensity follows visual pacing)\n")
        parts.append("\n")
    else:
        # Provide segment context even when audio is disabled
        if segment_ctx:
            parts.append("[SEGMENT CONTEXT]\n")
            parts.append(
                f"Segment: {segment_ctx.get('segment_index', 0)} of {segment_ctx.get('total_segments', 1)}\n"
            )
            if segment_ctx.get("anchor_state"):
                parts.append(f"Previous State: {segment_ctx.get('anchor_state')}\n")
            if segment_ctx.get("segment_action"):
                parts.append(f"Action: {segment_ctx.get('segment_action')}\n")
            if segment_ctx.get("goal_state"):
                parts.append(f"Goal State: {segment_ctx.get('goal_state')}\n")
            parts.append("\n")
        parts.append(f"Synchronize dialogue with visuals precisely.\n\n")

    parts.append("[REQUIREMENTS]\n")
    parts.append("- Maintain visual consistency throughout\n")
    parts.append("- Smooth, cinematic transitions between shots\n")
    parts.append("- Professional quality, no artifacts\n")
    parts.append("- No text overlays or watermarks\n")

    if is_extension:
        parts.append("- CRITICAL: Seamless continuation from previous segment\n")
        parts.append("- Match exact visual style, characters, and atmosphere\n")

    if not enable_audio:
        parts.append("- Audio: no audio, silent video\n")
    if not enable_subtitles:
        parts.append("- (no subtitles, no text overlays)\n")

    return "".join(parts)


def extract_subject_from_script(script_output: dict) -> str:
    """Extract the main subject for Veo prompt."""
    try:
        lead = script_output.get("lead_character")
        if lead:
            return str(lead)
        scenes = script_output.get("scenes", [])
        if scenes and isinstance(scenes[0].get("visual_keywords"), list) and scenes[0]["visual_keywords"]:
            return str(scenes[0]["visual_keywords"][0])
    except Exception:
        pass
    return "main subject"


def extract_action_from_segment(script_output: dict, segment_info: dict) -> str:
    """Extract primary action for this segment."""
    try:
        start = segment_info.get("start_time", 0)
        end = segment_info.get("end_time", 8)
        scenes = script_output.get("scenes", [])
        relevant = [
            s for s in scenes if s.get("start_time", 0) < end and s.get("end_time", 0) > start
        ]
        if relevant:
            desc = (relevant[0].get("description", "") or "").lower()
            for verb in [
                "walking",
                "running",
                "explaining",
                "demonstrating",
                "showing",
                "pointing",
            ]:
                if verb in desc:
                    return verb
    except Exception:
        pass
    return "moving"


def build_extension_prompt(
    script_output: dict,
    tool_category: str,
    segment_info: dict,
    previous_end_description: str,
    anchor: Optional[dict] = None,
    segment_ctx: Optional[dict] = None,
    audio_segment: Optional[dict] = None,
    enable_audio: bool = False,
    enable_subtitles: bool = False,
) -> str:
    """Build continuation prompt for video extension.

    Args:
        script_output: Full script output
        tool_category: Tool category for style
        segment_info: Current segment timing
        previous_end_description: How the previous segment ended

    Returns:
        Extension prompt optimized for seamless continuation
    """
    return build_video_prompt(
        script_output=script_output,
        tool_category=tool_category,
        topic=script_output.get("topic", ""),
        segment_info=segment_info,
        is_extension=True,
        previous_segment_end=previous_end_description,
        anchor=anchor,
        segment_ctx=segment_ctx,
        audio_segment=audio_segment,
        enable_audio=enable_audio,
        enable_subtitles=enable_subtitles,
    )


class VideoGeneratorAgent:
    """Agent for generating videos with Veo 3.1.

    Generates seamless multi-segment videos using Veo extension feature.
    Reference images are used for the initial segment only.
    """

    def __init__(self):
        """Initialize the Video Generator Agent."""
        self.veo_service = get_veo_service()
        self.supabase = get_supabase_client()
        self.prompt_builder = get_prompt_builder()
        logger.info("VideoGeneratorAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        """Run the video generation process.

        Args:
            state: Current workflow state

        Returns:
            State update dict with generated video
        """
        start_time = time.time()
        segment_contexts: list[dict[str, Any]] = []
        workflow_id = state.get("workflow_id", "unknown")

        logger.info(f"Starting video generation for workflow: {workflow_id}")

        try:
            script_output = state.get("script_output") or {}
            topic = state.get("topic", "")
            tool_category = self._get_tool_category(state)
            duration_seconds = state.get("duration_seconds", 18)
            aspect_ratio = state.get("aspect_ratio", "9:16")
            resolution = state.get("resolution", "720p")
            enable_audio = state.get("enable_audio", False)

            generated_images = state.get("generated_images") or []
            research_images = state.get("research_images") or []
            user_reference_url = state.get("user_reference_image_url", None)

            audio_manifest = state.get("audio_manifest")
            audio_manifest_model = None
            if audio_manifest:
                try:
                    audio_manifest_model = AudioManifest.model_validate(audio_manifest)
                    if audio_manifest_model.total_duration:
                        audio_total = float(audio_manifest_model.total_duration)
                        drift = abs(audio_total - float(duration_seconds))
                        if drift <= 0.35:
                            duration_seconds = int(round(audio_total))
                        else:
                            logger.warning(
                                "Audio/video duration drift exceeds tolerance: requested=%.2fs, audio=%.2fs",
                                float(duration_seconds),
                                audio_total,
                            )
                except Exception:
                    audio_manifest_model = None

            VideoGenerationRequest.model_validate(
                {
                    "workflow_id": workflow_id,
                    "script_output": script_output,
                    "all_images": state.get("all_images") or [],
                    "user_reference_image_url": user_reference_url,
                    "research_images": research_images,
                    "generated_images": generated_images,
                    "tool_category": tool_category,
                    "topic": topic,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "duration_seconds": duration_seconds,
                    "enable_audio": enable_audio,
                    "audio_manifest": audio_manifest_model,
                }
            )

            if duration_seconds > MAX_SEGMENT_DURATION:
                resolution = "720p"
                logger.info(
                    f"Using 720p resolution for {duration_seconds}s video (extension required)"
                )

            # Respect user-selected model if provided in state
            selected_model_value = state.get("video_model")
            try:
                selected_model_enum = (
                    VideoModel(selected_model_value) if selected_model_value else VideoModel.VEO_3_1
                )
            except Exception:
                selected_model_enum = VideoModel.VEO_3_1

            config = VideoGenerationConfig(
                model=selected_model_enum,
                aspect_ratio=ASPECT_RATIO_MAP.get(aspect_ratio, VideoAspectRatio.PORTRAIT_9_16),
                resolution=RESOLUTION_MAP.get(resolution, VideoResolution.RES_720P),
                duration_seconds=MAX_SEGMENT_DURATION,
                target_duration_seconds=duration_seconds,
                enable_audio=enable_audio,
            )

            # Video Generator uses ONLY generated images from Nano Banana Pro
            # Research images are used as reference for Image Generator, not here
            selected_images = select_reference_images(
                generated_images=generated_images,
                image_metadata=state.get("image_metadata") or None,
            )

            # Download reference images with MIME detection
            reference_images = []
            for url in selected_images:
                try:
                    img_bytes, mime_type = await self._download_image(url)
                    reference_images.append({"bytes": img_bytes, "mime_type": mime_type})
                except Exception as e:
                    logger.warning(f"Failed to download reference image {url}: {e}")

            logger.info(f"Downloaded {len(reference_images)} reference images for Veo")

            segment_plans = plan_video_segments(
                duration_seconds,
                audio_manifest=audio_manifest_model,
            )
            # Compute per-segment context blocks (segment-aware prompting)
            segment_contexts = compute_segment_context_blocks(
                script_output=script_output,
                segment_plans=segment_plans,
            )
            # Persist planned segment context early for debugging/circuit-breaker scenarios
            await self._persist_segment_context(
                workflow_id,
                segment_contexts,
                status="planned",
            )

            # Template-based prompt if available
            audio_segments = []
            if audio_manifest_model:
                audio_segments = [seg.model_dump() for seg in audio_manifest_model.segments]

            initial_prompt = None
            try:
                tpl = (state.get("selected_tool") or {}).get("video_prompt_template")
                if tpl:
                    logger.info("Rendering video_prompt_template for initial segment")
                    script_text = self._format_script_for_template(script_output)
                    # Prefer segment-specific fields if template supports them
                    ctx = {
                        "script": script_text,
                        "duration": duration_seconds,
                        "duration_seconds": duration_seconds,
                        "tool_category": tool_category,
                        "tool_name": (state.get("selected_tool") or {}).get("tool_name", ""),
                        "segment_info": segment_plans[0],
                        # New placeholders (segment-aware)
                        "segment_index": segment_contexts[0].get("segment_index", 0)
                        if segment_contexts
                        else 0,
                        "total_segments": len(segment_contexts),
                        "segment_action": segment_contexts[0].get("segment_action", "")
                        if segment_contexts
                        else "",
                        "previous_segment_state": segment_contexts[0].get("anchor_state", "")
                        if segment_contexts
                        else "",
                        "dialogue_cue": segment_contexts[0].get("dialogue_cue", "")
                        if segment_contexts
                        else "",
                        "sfx_cue": segment_contexts[0].get("sfx_cue", "")
                        if segment_contexts
                        else "",
                        "ambient_cue": segment_contexts[0].get("ambient_cue", "")
                        if segment_contexts
                        else "",
                        "music_cue": segment_contexts[0].get("music_cue", "")
                        if segment_contexts
                        else "",
                    }
                    ok, errs = self.prompt_builder.runtime_validate(
                        tpl, ["script", "duration"], min_words=50
                    )
                    if not ok:
                        logger.warning(f"Video template runtime validation failed: {errs}")
                    rr = self.prompt_builder.render(
                        tpl,
                        ctx,
                        required=["script", "duration"],
                        min_words=50,
                        fallback_prompt_builder=lambda: build_video_prompt(
                            script_output=script_output,
                            tool_category=tool_category,
                            topic=topic,
                            segment_info=segment_plans[0],
                            is_extension=False,
                            segment_ctx=segment_contexts[0] if segment_contexts else None,
                            audio_segment=audio_segments[0] if audio_segments else None,
                            enable_audio=enable_audio,
                            enable_subtitles=state.get("enable_subtitles", False),
                        ),
                    )
                    initial_prompt = rr.prompt
                    # Add storyboard guidance if master image is a storyboard
                    try:
                        initial_prompt += _storyboard_reference_note(
                            0, len(segment_plans), state.get("master_image_type") == "storyboard"
                        )
                    except Exception:
                        pass
                    if rr.fallback_used:
                        logger.warning("Video template fallback used for initial segment")
                if not initial_prompt:
                    initial_prompt = build_video_prompt(
                        script_output=script_output,
                        tool_category=tool_category,
                        topic=topic,
                        segment_info=segment_plans[0],
                        is_extension=False,
                        anchor=state.get("global_style_anchor") or None,
                        segment_ctx=segment_contexts[0] if segment_contexts else None,
                        audio_segment=audio_segments[0] if audio_segments else None,
                        enable_audio=enable_audio,
                        enable_subtitles=state.get("enable_subtitles", False),
                    )
                    initial_prompt += _storyboard_reference_note(
                        0, len(segment_plans), state.get("master_image_type") == "storyboard"
                    )
            except Exception as e:
                logger.warning(f"Initial video template rendering failed: {e}; using fallback")
                initial_prompt = build_video_prompt(
                    script_output=script_output,
                    tool_category=tool_category,
                    topic=topic,
                    segment_info=segment_plans[0],
                    is_extension=False,
                    segment_ctx=segment_contexts[0] if segment_contexts else None,
                    audio_segment=audio_segments[0] if audio_segments else None,
                    enable_audio=enable_audio,
                    enable_subtitles=state.get("enable_subtitles", False),
                )
                initial_prompt += _storyboard_reference_note(
                    0, len(segment_plans), state.get("master_image_type") == "storyboard"
                )

            # Apply voice reference (for audio continuity)
            if enable_audio:
                try:
                    voice_ref = ""
                    char_sheet = state.get("character_reference_sheet") or {}
                    if char_sheet.get("voice"):
                        voice_ref = str(char_sheet.get("voice"))
                    else:
                        lead_desc = (script_output or {}).get("lead_character_description") or ""
                        if lead_desc:
                            voice_ref = lead_desc
                    if voice_ref:
                        initial_prompt += "\n[VOICE REFERENCE] " + voice_ref[:300]
                except Exception:
                    pass
            # Append global style anchor details to increase consistency (including realistic videos)
            try:
                anchor = state.get("global_style_anchor") or {}
                if anchor:
                    initial_prompt += (
                        "\n[GLOBAL STYLE ANCHOR]\n"
                        f"Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n"
                        f"Materials: {', '.join(anchor.get('materials', [])[:6])}\n"
                        f"Motion: {', '.join(anchor.get('motion_language', [])[:6])}\n"
                        f"Lighting: {anchor.get('lighting', '')}\n"
                        f"Camera: {anchor.get('camera', '')}\n"
                        f"Texture: {anchor.get('texture', '')}\n"
                    )
            except Exception:
                pass
            # Append character reference URLs if available
            try:
                char_sheet = state.get("character_reference_sheet") or {}
                ref_urls = [
                    r.get("url")
                    for r in (char_sheet.get("reference_images") or [])
                    if isinstance(r, dict) and r.get("url")
                ]
                if ref_urls:
                    initial_prompt += (
                        "\n[REFERENCE IMAGES] Use character consistency from: "
                        + ", ".join(str(url) for url in ref_urls[:4])
                    )
            except Exception:
                pass

            extension_prompts = []
            for i, seg_plan in enumerate(segment_plans[1:], 1):
                prev_scenes = script_output.get("scenes", []) or []
                prev_end = ""
                if prev_scenes:
                    prev_idx = min(i - 1, len(prev_scenes) - 1)
                    prev_end = prev_scenes[prev_idx].get("description", "scene continues")
                try:
                    tpl = (state.get("selected_tool") or {}).get("video_prompt_template")
                    if tpl:
                        logger.info(f"Rendering video_prompt_template for extension {i}")
                        script_text = self._format_script_for_template(script_output)
                        ctx = {
                            "script": script_text,
                            "duration": duration_seconds,
                            "duration_seconds": duration_seconds,
                            "tool_category": tool_category,
                            "tool_name": (state.get("selected_tool") or {}).get("tool_name", ""),
                            "segment_info": seg_plan,
                            "previous_segment_end": prev_end,
                            "segment_index": segment_contexts[i].get("segment_index", i)
                            if i < len(segment_contexts)
                            else i,
                            "total_segments": len(segment_contexts),
                            "segment_action": segment_contexts[i].get("segment_action", "")
                            if i < len(segment_contexts)
                            else "",
                            "previous_segment_state": segment_contexts[i].get("anchor_state", "")
                            if i < len(segment_contexts)
                            else "",
                            "dialogue_cue": segment_contexts[i].get("dialogue_cue", "")
                            if i < len(segment_contexts)
                            else "",
                            "sfx_cue": segment_contexts[i].get("sfx_cue", "")
                            if i < len(segment_contexts)
                            else "",
                            "ambient_cue": segment_contexts[i].get("ambient_cue", "")
                            if i < len(segment_contexts)
                            else "",
                            "music_cue": segment_contexts[i].get("music_cue", "")
                            if i < len(segment_contexts)
                            else "",
                        }
                        ok, errs = self.prompt_builder.runtime_validate(
                            tpl, ["script", "duration"], min_words=50
                        )
                        if not ok:
                            logger.warning(
                                f"Extension video template runtime validation failed: {errs}"
                            )
                        rr = self.prompt_builder.render(
                            tpl,
                            ctx,
                            required=["script", "duration"],
                            min_words=50,
                            fallback_prompt_builder=lambda: build_extension_prompt(
                                script_output=script_output,
                                tool_category=tool_category,
                                segment_info=seg_plan,
                                previous_end_description=prev_end,
                                anchor=state.get("global_style_anchor") or None,
                                segment_ctx=segment_contexts[i]
                                if i < len(segment_contexts)
                                else None,
                                audio_segment=audio_segments[i]
                                if i < len(audio_segments)
                                else None,
                                enable_audio=enable_audio,
                                enable_subtitles=state.get("enable_subtitles", False),
                            ),
                        )
                        ext_prompt = rr.prompt
                        if enable_audio:
                            try:
                                voice_ref = ""
                                char_sheet = state.get("character_reference_sheet") or {}
                                if char_sheet.get("voice"):
                                    voice_ref = str(char_sheet.get("voice"))
                                else:
                                    lead_desc = (script_output or {}).get(
                                        "lead_character_description"
                                    ) or ""
                                    if lead_desc:
                                        voice_ref = lead_desc
                                if voice_ref:
                                    ext_prompt += "\n[VOICE REFERENCE] " + voice_ref[:300]
                            except Exception:
                                pass
                        try:
                            anchor = state.get("global_style_anchor") or {}
                            if anchor:
                                ext_prompt += (
                                    "\n[GLOBAL STYLE ANCHOR]\n"
                                    f"Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n"
                                    f"Materials: {', '.join(anchor.get('materials', [])[:6])}\n"
                                    f"Motion: {', '.join(anchor.get('motion_language', [])[:6])}\n"
                                    f"Lighting: {anchor.get('lighting', '')}\n"
                                    f"Camera: {anchor.get('camera', '')}\n"
                                    f"Texture: {anchor.get('texture', '')}\n"
                                )
                        except Exception:
                            pass
                        try:
                            char_sheet = state.get("character_reference_sheet") or {}
                            ref_urls = [
                                r.get("url")
                                for r in (char_sheet.get("reference_images") or [])
                                if isinstance(r, dict) and r.get("url")
                            ]
                            if ref_urls:
                                ext_prompt += (
                                    "\n[REFERENCE IMAGES] Use character consistency from: "
                                    + ", ".join(str(url) for url in ref_urls[:4])
                                )
                        except Exception:
                            pass
                        # Storyboard guidance
                        ext_prompt += _storyboard_reference_note(
                            i, len(segment_plans), state.get("master_image_type") == "storyboard"
                        )
                        extension_prompts.append(ext_prompt)
                    else:
                        ext_prompt = build_extension_prompt(
                            script_output=script_output,
                            tool_category=tool_category,
                            segment_info=seg_plan,
                            previous_end_description=prev_end,
                            anchor=state.get("global_style_anchor") or None,
                            segment_ctx=segment_contexts[i] if i < len(segment_contexts) else None,
                            audio_segment=audio_segments[i] if i < len(audio_segments) else None,
                            enable_audio=enable_audio,
                            enable_subtitles=state.get("enable_subtitles", False),
                        )
                        # Add voice reference when audio enabled
                        if enable_audio:
                            try:
                                voice_ref = ""
                                char_sheet = state.get("character_reference_sheet") or {}
                                if char_sheet.get("voice"):
                                    voice_ref = str(char_sheet.get("voice"))
                                else:
                                    lead_desc = (script_output or {}).get(
                                        "lead_character_description"
                                    ) or ""
                                    if lead_desc:
                                        voice_ref = lead_desc
                                if voice_ref:
                                    ext_prompt += "\n[VOICE REFERENCE] " + voice_ref[:300]
                            except Exception:
                                pass
                        try:
                            anchor = state.get("global_style_anchor") or {}
                            if anchor:
                                ext_prompt += (
                                    "\n[GLOBAL STYLE ANCHOR]\n"
                                    f"Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n"
                                    f"Materials: {', '.join(anchor.get('materials', [])[:6])}\n"
                                    f"Motion: {', '.join(anchor.get('motion_language', [])[:6])}\n"
                                    f"Lighting: {anchor.get('lighting', '')}\n"
                                    f"Camera: {anchor.get('camera', '')}\n"
                                    f"Texture: {anchor.get('texture', '')}\n"
                                )
                        except Exception:
                            pass
                        try:
                            char_sheet = state.get("character_reference_sheet") or {}
                            ref_urls = [
                                r.get("url")
                                for r in (char_sheet.get("reference_images") or [])
                                if isinstance(r, dict) and r.get("url")
                            ]
                            if ref_urls:
                                ext_prompt += (
                                    "\n[REFERENCE IMAGES] Use character consistency from: "
                                    + ", ".join(str(url) for url in ref_urls[:4])
                                )
                        except Exception:
                            pass
                        ext_prompt += _storyboard_reference_note(
                            i, len(segment_plans), state.get("master_image_type") == "storyboard"
                        )
                        extension_prompts.append(ext_prompt)
                except Exception as e:
                    logger.warning(
                        f"Extension video template rendering failed for segment {i}: {e}; using fallback"
                    )
                    ext_prompt = build_extension_prompt(
                        script_output=script_output,
                        tool_category=tool_category,
                        segment_info=seg_plan,
                        previous_end_description=prev_end,
                        anchor=state.get("global_style_anchor") or None,
                        segment_ctx=segment_contexts[i] if i < len(segment_contexts) else None,
                        audio_segment=audio_segments[i] if i < len(audio_segments) else None,
                        enable_audio=enable_audio,
                        enable_subtitles=state.get("enable_subtitles", False),
                    )
                    if enable_audio:
                        try:
                            voice_ref = ""
                            char_sheet = state.get("character_reference_sheet") or {}
                            if char_sheet.get("voice"):
                                voice_ref = str(char_sheet.get("voice"))
                            else:
                                lead_desc = (script_output or {}).get(
                                    "lead_character_description"
                                ) or ""
                                if lead_desc:
                                    voice_ref = lead_desc
                            if voice_ref:
                                ext_prompt += "\n[VOICE REFERENCE] " + voice_ref[:300]
                        except Exception:
                            pass
                    try:
                        anchor = state.get("global_style_anchor") or {}
                        if anchor:
                            ext_prompt += (
                                "\n[GLOBAL STYLE ANCHOR]\n"
                                f"Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n"
                                f"Materials: {', '.join(anchor.get('materials', [])[:6])}\n"
                                f"Motion: {', '.join(anchor.get('motion_language', [])[:6])}\n"
                                f"Lighting: {anchor.get('lighting', '')}\n"
                                f"Camera: {anchor.get('camera', '')}\n"
                                f"Texture: {anchor.get('texture', '')}\n"
                            )
                    except Exception:
                        pass
                    try:
                        char_sheet = state.get("character_reference_sheet") or {}
                        ref_urls = [
                            r.get("url")
                            for r in (char_sheet.get("reference_images") or [])
                            if isinstance(r, dict) and r.get("url")
                        ]
                        if ref_urls:
                            ext_prompt += (
                                "\n[REFERENCE IMAGES] Use character consistency from: "
                                + ", ".join(str(url) for url in ref_urls[:4])
                            )
                    except Exception:
                        pass
                    ext_prompt += _storyboard_reference_note(
                        i, len(segment_plans), state.get("master_image_type") == "storyboard"
                    )
                    extension_prompts.append(ext_prompt)

            if len(segment_plans) == 1:
                # Use retry wrapper for initial single-segment to handle 429 and other transient errors
                video_object, gen_time, _retry = await self.veo_service.generate_video_with_retry(
                    prompt=initial_prompt,
                    config=config,
                    reference_images=reference_images if reference_images else None,
                )
                segments = [
                    VideoSegment(
                        segment_number=0,
                        segment_type=VideoSegmentType.INITIAL,
                        duration_seconds=duration_seconds,
                        start_time=0.0,
                        end_time=float(duration_seconds),
                        prompt=initial_prompt[:500],
                        generation_time_ms=gen_time,
                        used_reference_images=bool(reference_images),
                    )
                ]
                total_generation_time_ms = gen_time
            else:
                # Define a progress callback to persist partial results after each segment
                async def on_progress(
                    current_video_obj: object, segs: list[VideoSegment], current_duration: float
                ) -> None:
                    try:
                        # Download current combined video and upload as partial
                        partial_bytes = await self.veo_service.download_video(current_video_obj)
                        partial_path = (
                            f"videos/{workflow_id}/partial_{len(segs)}_{int(time.time())}.mp4"
                        )
                        partial_url = await self._upload_to_storage(partial_bytes, partial_path)

                        # Build minimal video + output and persist
                        partial_generated = GeneratedVideo(
                            url=partial_url,
                            storage_path=partial_path,
                            duration_seconds=float(sum(s.duration_seconds for s in segs)),
                            resolution=config.resolution,
                            aspect_ratio=config.aspect_ratio,
                            model_used=config.model,
                            segments=segs,
                            total_segments=len(segs),
                            audio_included=enable_audio,
                            reference_images_used=selected_images,
                            generation_time_ms=0,
                            file_size_bytes=len(partial_bytes),
                        )
                        partial_selection = ReferenceImageSelection(
                            user_reference_url=user_reference_url,
                            generated_image_urls=generated_images,
                            research_image_urls=research_images,
                            selected_urls=selected_images,
                        )
                        partial_output = VideoGeneratorOutput(
                            video=partial_generated,
                            segments=segs,
                            total_duration_seconds=float(sum(s.duration_seconds for s in segs)),
                            total_generation_time_ms=0,
                            model_used=config.model,
                            fallback_used=False,
                            reference_images=partial_selection,
                            prompt_used=initial_prompt[:1000],
                        )
                        validated_partial = VideoGeneratorOutput.model_validate(
                            partial_output.model_dump()
                        )
                        await self._persist_to_database(workflow_id, validated_partial)
                        await self._persist_segment_context(
                            workflow_id,
                            segment_contexts,
                            status="partial",
                        )
                    except Exception as pe:
                        logger.warning(f"Failed to persist partial video progress: {pe}")

                (
                    video_object,
                    segments,
                    total_generation_time_ms,
                ) = await self.veo_service.generate_multi_segment_video(
                    initial_prompt=initial_prompt,
                    extension_prompts=extension_prompts,
                    config=config,
                    reference_images=reference_images if reference_images else None,
                    on_progress=on_progress,
                )

            logger.info("Downloading final video...")
            video_bytes = await self.veo_service.download_video(video_object)

            # Strip audio if user requested no audio (Veo always generates audio natively)
            if not enable_audio:
                from app.services.video_trimmer import strip_audio_from_video

                logger.info("User requested no audio - stripping audio track...")
                video_bytes = await strip_audio_from_video(video_bytes)
                logger.info("Audio stripped from video")

            storage_path = f"videos/{workflow_id}/final_{int(time.time())}.mp4"
            video_url = await self._upload_to_storage(video_bytes, storage_path)

            # Compute actual total duration from built segments
            actual_total_duration = (
                sum(seg.duration_seconds for seg in segments)
                if segments
                else float(duration_seconds)
            )

            generated_video = GeneratedVideo(
                url=video_url,
                storage_path=storage_path,
                duration_seconds=float(actual_total_duration),
                resolution=config.resolution,
                aspect_ratio=config.aspect_ratio,
                model_used=config.model,
                segments=segments,
                total_segments=len(segments),
                audio_included=enable_audio,
                reference_images_used=selected_images,
                generation_time_ms=total_generation_time_ms,
                file_size_bytes=len(video_bytes),
            )

            reference_selection = ReferenceImageSelection(
                user_reference_url=user_reference_url,
                generated_image_urls=generated_images,
                research_image_urls=research_images,
                selected_urls=selected_images,
            )

            output = VideoGeneratorOutput(
                video=generated_video,
                segments=segments,
                total_duration_seconds=float(actual_total_duration),
                total_generation_time_ms=total_generation_time_ms,
                model_used=config.model,
                fallback_used=False,
                reference_images=reference_selection,
                prompt_used=initial_prompt[:1000],
            )

            # Monitoring: record video generation usage
            try:
                from app.services.monitoring import get_monitoring_service

                await get_monitoring_service().record_video_usage(
                    video_id=workflow_id,
                    model=config.model.value,
                    video_duration_seconds=float(actual_total_duration),
                    generation_duration_seconds=float(total_generation_time_ms) / 1000.0,
                    success=True,
                    metadata={
                        "segments": len(segments),
                        "resolution": config.resolution.value,
                        "aspect_ratio": config.aspect_ratio.value,
                    },
                )
            except Exception as me:
                logger.warning(f"Monitoring video usage failed: {me}")

            validated_output = VideoGeneratorOutput.model_validate(output.model_dump())

            await self._persist_to_database(workflow_id, validated_output)
            await self._persist_segment_context(
                workflow_id,
                segment_contexts,
                status="completed",
            )

            from app.utils.helpers import utc_now_iso

            state_update = {
                "video_output": validated_output.model_dump(),
                "final_video_url": video_url,
                "clean_video_url": video_url,
                "video_metadata": {
                    "duration_seconds": actual_total_duration,
                    "segments": len(segments),
                    "resolution": config.resolution.value,
                    "aspect_ratio": config.aspect_ratio.value,
                    "model_used": config.model.value,
                    "generation_time_ms": total_generation_time_ms,
                },
                "segment_contexts": segment_contexts,
                "segment_context_status": "completed",
                "phase_timestamps": {
                    **state.get("phase_timestamps", {}),
                    "video_generator_completed": utc_now_iso(),
                },
            }

            total_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"Video generation completed: {actual_total_duration:.0f}s video, "
                f"{len(segments)} segments, {total_time}ms total"
            )

            return state_update

        except VeoServiceError as e:
            logger.error(f"Veo service error: {e}")
            return {
                "error": f"Video generation failed: {str(e)}",
                "error_details": {
                    "phase": "video_generator",
                    "workflow_id": workflow_id,
                    "error_type": type(e).__name__,
                },
                "segment_contexts": segment_contexts,
                "segment_context_status": "failed",
            }
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {
                "error": f"Video generation failed: {str(e)}",
                "error_details": {
                    "phase": "video_generator",
                    "workflow_id": workflow_id,
                    "error_type": type(e).__name__,
                },
                "segment_contexts": segment_contexts,
                "segment_context_status": "failed",
            }

    def _get_tool_category(self, state: VideoGenerationState) -> str:
        """Extract tool category from state.

        Returns normalized category name (realistic, anime, animation).
        Legacy category names are mapped to new simplified names.
        """
        # Legacy to new category mapping
        category_mapping = {
            "surreal_realism": "realistic",
            "high_octane_anime": "anime",
            "stylized_3d": "animation",
        }

        selected_tool = state.get("selected_tool", {})
        if selected_tool:
            category = selected_tool.get("category", "realistic")
        else:
            category = state.get("category", "realistic")

        # Normalize legacy category names to new simplified names
        return category_mapping.get(category, category)

    async def _download_image(self, url: str) -> tuple[bytes, str]:
        """Download image from URL.

        Args:
            url: Image URL

        Returns:
            Tuple of (image bytes, mime type)
        """
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download image: {response.status}")
                data = await response.read()
                # Prefer Content-Type header, else infer
                mime = response.headers.get("Content-Type", "").split(";")[0].strip()
                if not mime or not mime.startswith("image/"):
                    # Fallback guesses by magic bytes
                    if data.startswith(b"\x89PNG"):
                        mime = "image/png"
                    elif data.startswith(b"\xff\xd8\xff"):
                        mime = "image/jpeg"
                    elif data[:4] == b"RIFF" and b"WEBP" in data[:16]:
                        mime = "image/webp"
                    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
                        mime = "image/gif"
                    else:
                        mime = "image/png"  # safe default
                return data, mime

    async def _upload_to_storage(self, video_bytes: bytes, storage_path: str) -> str:
        """Upload video to Supabase Storage.

        Args:
            video_bytes: Video data
            storage_path: Path in storage bucket

        Returns:
            Public URL of uploaded video
        """
        try:
            bucket_name = "media"  # Use existing 'media' bucket
            full_path = f"generated_videos/{storage_path}"

            result = self.supabase.storage.from_(bucket_name).upload(
                path=full_path, file=video_bytes, file_options={"content-type": "video/mp4"}
            )

            public_url = self.supabase.storage.from_(bucket_name).get_public_url(full_path)

            logger.info(f"Video uploaded to storage: {storage_path}")
            return public_url

        except Exception as e:
            logger.error(f"Storage upload failed: {e}")
            return f"upload_failed://{storage_path}"

    async def _persist_to_database(
        self,
        workflow_id: str,
        output: VideoGeneratorOutput,
    ) -> None:
        """Persist video output to Supabase."""
        try:
            from app.utils.helpers import utc_now_iso

            self.supabase.table("workflows").update(
                {
                    "video_output": {
                        "video_url": output.video.url,
                        "storage_path": output.video.storage_path,
                        "duration_seconds": output.total_duration_seconds,
                        "resolution": output.video.resolution.value,
                        "aspect_ratio": output.video.aspect_ratio.value,
                        "segments": [seg.model_dump() for seg in output.segments],
                        "total_segments": len(output.segments),
                        "audio_included": output.video.audio_included,
                        "model_used": output.model_used.value,
                        "generation_time_ms": output.total_generation_time_ms,
                        "reference_images_used": output.reference_images.selected_urls,
                    },
                    "updated_at": utc_now_iso(),
                }
            ).eq("id", workflow_id).execute()

            self.supabase.table("media").insert(
                {
                    "workflow_id": workflow_id,
                    "media_type": "video",  # Allowed: image, video, audio
                    "source": "generated",  # Allowed: user_upload, research, generated
                    "storage_url": output.video.url,
                    "storage_path": output.video.storage_path,
                    "file_size_bytes": output.video.file_size_bytes,
                    "mime_type": "video/mp4",
                    "metadata": {
                        "duration_seconds": output.total_duration_seconds,
                        "segments": len(output.segments),
                        "resolution": output.video.resolution.value,
                        "aspect_ratio": output.video.aspect_ratio.value,
                        "model_used": output.model_used.value,
                    },
                }
            ).execute()

            logger.info(f"Persisted video output to database for workflow: {workflow_id}")

        except Exception as e:
            logger.error(f"Database persistence failed: {e}")

    async def _persist_segment_context(
        self,
        workflow_id: str,
        segment_contexts: list[dict[str, Any]],
        *,
        status: str,
    ) -> None:
        try:
            from app.utils.helpers import utc_now_iso

            if not segment_contexts:
                return
            self.supabase.table("workflows").update(
                {
                    "segment_contexts": segment_contexts,
                    "segment_context_status": status,
                    "updated_at": utc_now_iso(),
                }
            ).eq("id", workflow_id).execute()
        except Exception as e:
            logger.warning(f"Segment context persistence failed: {e}")

    def _format_script_for_template(self, script_output: dict) -> str:
        """Format structured script output into a compact textual form for templates.

        Includes hook, scenes, and CTA with timing, dialogue, and visual notes.
        """
        parts: list[str] = []
        if not script_output:
            return ""

        hook = script_output.get("hook") or {}
        if hook:
            text = hook.get("text") or hook.get("script") or ""
            vis = hook.get("visual_direction", "")
            if text:
                parts.append(f"HOOK: {text}")
            if vis:
                parts.append(f"Hook Visual: {vis}")

        scenes = script_output.get("scenes") or []
        for s in scenes:
            num = s.get("scene_number", "?")
            desc = s.get("description", "")
            dia = s.get("dialogue", "")
            cam = s.get("camera_direction", "")
            mood = s.get("mood", "")
            parts.append(f"SCENE {num}: {desc}")
            if dia:
                parts.append(f"Dialogue: {dia}")
            if cam:
                parts.append(f"Camera: {cam}")
            if mood:
                parts.append(f"Mood: {mood}")

        cta = script_output.get("call_to_action") or {}
        if cta:
            text = cta.get("text") or cta.get("script") or ""
            vis = cta.get("visual_direction", "")
            if text:
                parts.append(f"CTA: {text}")
            if vis:
                parts.append(f"CTA Visual: {vis}")

        return "\n".join(parts)


async def video_generator_node(state: VideoGenerationState) -> dict[str, Any]:
    """LangGraph node for video generation.

    Args:
        state: Current workflow state

    Returns:
        State update dict
    """
    agent = VideoGeneratorAgent()
    return await agent.run(state)
