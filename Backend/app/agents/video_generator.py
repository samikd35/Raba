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
from app.models.video import (
    GeneratedVideo,
    HITLVideoFeedback,
    ReferenceImageSelection,
    VideoAspectRatio,
    VideoGenerationConfig,
    VideoGeneratorOutput,
    VideoModel,
    VideoResolution,
    VideoSegment,
    VideoSegmentType,
)
from app.services.veo import get_veo_service, VeoServiceError
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_SEGMENT_DURATION = 8
EXTENSION_DURATION = 7
MAX_REFERENCE_IMAGES = 3

TOOL_VIDEO_VOCABULARY = {
    "surreal_realism": {
        "style_keywords": [
            "photorealistic", "cinematic", "hyperreal",
            "flowing liquid-glass aesthetic", "impossible physics",
            "dreamlike atmosphere", "tangible phenomenon"
        ],
        "camera_movements": [
            "slow dolly", "smooth tracking", "floating perspective",
            "subtle push-in", "cinematic crane", "gentle orbit"
        ],
        "audio_cues": [
            "ambient atmospheric sounds", "subtle ethereal music",
            "gentle whooshing", "resonant bass tones", "soft reverb"
        ],
        "lighting": [
            "soft volumetric lighting", "golden hour glow",
            "subtle rim lighting", "natural diffused light"
        ]
    },
    "high_octane_anime": {
        "style_keywords": [
            "Sakuga-style animation", "dynamic action",
            "ink-splash effects", "speed lines", "impact frames",
            "calligraphic combat", "high-energy aesthetic"
        ],
        "camera_movements": [
            "rapid cuts", "dynamic tracking", "whip pan",
            "dramatic zoom", "rotating camera", "impact shake"
        ],
        "audio_cues": [
            "intense orchestral", "dramatic sound effects",
            "swooshing impacts", "epic crescendo", "battle cries"
        ],
        "lighting": [
            "dramatic backlighting", "high contrast",
            "energy glow effects", "stark shadows"
        ]
    },
    "stylized_3d": {
        "style_keywords": [
            "clean 3D render", "isometric perspective",
            "miniature diorama", "tilt-shift effect",
            "stylized materials", "low-poly charm"
        ],
        "camera_movements": [
            "orbital rotation", "smooth dolly", "subtle tilt-shift",
            "steady pan", "gentle zoom", "floating overview"
        ],
        "audio_cues": [
            "clean electronic", "subtle clicks and beeps",
            "ambient informative tone", "gentle chimes", "soft synth"
        ],
        "lighting": [
            "soft ambient lighting", "studio lighting",
            "even illumination", "gentle shadows"
        ]
    }
}

ASPECT_RATIO_MAP = {
    "9:16": VideoAspectRatio.PORTRAIT_9_16,
    "16:9": VideoAspectRatio.LANDSCAPE_16_9,
}

RESOLUTION_MAP = {
    "720p": VideoResolution.RES_720P,
    "1080p": VideoResolution.RES_1080P,
}


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


def plan_video_segments(duration_seconds: int) -> list[dict]:
    """Plan video segments for target duration.
    
    Args:
        duration_seconds: Target video duration
        
    Returns:
        List of segment plans with timing info
    """
    segments = []
    current_time = 0.0
    
    initial_duration = min(duration_seconds, MAX_SEGMENT_DURATION)
    segments.append({
        "segment_number": 0,
        "type": "initial",
        "start_time": 0.0,
        "end_time": initial_duration,
        "duration": initial_duration,
    })
    current_time = initial_duration
    
    segment_num = 1
    while current_time < duration_seconds:
        remaining = duration_seconds - current_time
        segment_duration = min(remaining, EXTENSION_DURATION)
        
        segments.append({
            "segment_number": segment_num,
            "type": "extension",
            "start_time": current_time,
            "end_time": current_time + segment_duration,
            "duration": segment_duration,
        })
        
        current_time += EXTENSION_DURATION
        segment_num += 1
    
    logger.info(f"Planned {len(segments)} segments for {duration_seconds}s video")
    return segments


def select_reference_images(
    generated_images: list[str],
    max_count: int = MAX_REFERENCE_IMAGES,
) -> list[str]:
    """Select reference images from ONLY generated images (Nano Banana Pro).
    
    IMPORTANT: Video Generator uses ONLY generated images from Image Generator.
    Research images (Google Search + user uploads) are used as reference for
    Image Generator, NOT for Video Generator.
    
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
    
    selected = []
    
    if len(generated_images) <= max_count:
        selected = generated_images[:max_count]
    else:
        selected.append(generated_images[0])
        if max_count >= 2:
            selected.append(generated_images[-1])
        if max_count >= 3 and len(generated_images) > 2:
            mid_idx = len(generated_images) // 2
            selected.insert(1, generated_images[mid_idx])
    
    logger.info(f"Selected {len(selected)} generated images for Veo (from {len(generated_images)} total)")
    
    return selected


def build_video_prompt(
    script_output: dict,
    tool_category: str,
    topic: str,
    segment_info: dict,
    is_extension: bool = False,
    previous_segment_end: Optional[str] = None,
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
    vocab = TOOL_VIDEO_VOCABULARY.get(tool_category, TOOL_VIDEO_VOCABULARY["surreal_realism"])
    
    parts = []
    
    if is_extension and previous_segment_end:
        parts.append(f"[CONTINUATION] Seamlessly continue from: {previous_segment_end}\n\n")
    
    parts.append(f"[STYLE] {', '.join(vocab['style_keywords'][:4])}\n")
    parts.append(f"[LIGHTING] {', '.join(vocab['lighting'][:2])}\n\n")
    
    hook = script_output.get("hook", {})
    scenes = script_output.get("scenes", [])
    cta = script_output.get("call_to_action", {})
    
    start_time = segment_info.get("start_time", 0)
    end_time = segment_info.get("end_time", 8)
    
    if not is_extension and hook:
        hook_text = hook.get("text", "")
        hook_visual = hook.get("visual_direction", "")
        if hook_text:
            parts.append(f"[00:00-00:02] HOOK\n")
            parts.append(f"Dialogue: \"{hook_text}\"\n")
            if hook_visual:
                parts.append(f"Visual: {hook_visual}\n")
            parts.append(f"Camera: {vocab['camera_movements'][0]}\n\n")
    
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
        camera = scene.get("camera_direction", vocab['camera_movements'][min(i, len(vocab['camera_movements']) - 1)])
        mood = scene.get("mood", "")
        
        parts.append(f"[SCENE {scene_num}]\n")
        if description:
            parts.append(f"Visual: {description}\n")
        if dialogue:
            parts.append(f"Dialogue: \"{dialogue}\"\n")
        parts.append(f"Camera: {camera}\n")
        if mood:
            parts.append(f"Mood: {mood}\n")
        parts.append("\n")
    
    if not is_extension and cta and end_time >= script_output.get("duration_seconds", 18) - 3:
        cta_text = cta.get("text", "")
        cta_visual = cta.get("visual_direction", "")
        if cta_text:
            parts.append(f"[CALL TO ACTION]\n")
            parts.append(f"Dialogue: \"{cta_text}\"\n")
            if cta_visual:
                parts.append(f"Visual: {cta_visual}\n")
            parts.append("\n")
    
    parts.append(f"[AUDIO] {', '.join(vocab['audio_cues'][:3])}\n")
    parts.append(f"Synchronize all dialogue exactly with visuals.\n\n")
    
    parts.append("[REQUIREMENTS]\n")
    parts.append("- Maintain visual consistency throughout\n")
    parts.append("- Smooth, cinematic transitions between shots\n")
    parts.append("- Professional quality, no artifacts\n")
    parts.append("- No text overlays or watermarks\n")
    
    if is_extension:
        parts.append("- CRITICAL: Seamless continuation from previous segment\n")
        parts.append("- Match exact visual style, characters, and atmosphere\n")
    
    return "".join(parts)


def build_extension_prompt(
    script_output: dict,
    tool_category: str,
    segment_info: dict,
    previous_end_description: str,
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
        logger.info("VideoGeneratorAgent initialized")
    
    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        """Run the video generation process.
        
        Args:
            state: Current workflow state
            
        Returns:
            State update dict with generated video
        """
        start_time = time.time()
        workflow_id = state.get("workflow_id", "unknown")
        
        logger.info(f"Starting video generation for workflow: {workflow_id}")
        
        try:
            script_output = state.get("script_output", {})
            topic = state.get("topic", "")
            tool_category = self._get_tool_category(state)
            duration_seconds = state.get("duration_seconds", 18)
            aspect_ratio = state.get("aspect_ratio", "9:16")
            resolution = state.get("resolution", "720p")
            enable_audio = state.get("enable_audio", True)
            
            generated_images = state.get("generated_images", []) or []
            research_images = state.get("research_images", []) or []
            user_reference_url = state.get("user_reference_image_url", None)
            
            if duration_seconds > MAX_SEGMENT_DURATION:
                resolution = "720p"
                logger.info(f"Using 720p resolution for {duration_seconds}s video (extension required)")
            
            config = VideoGenerationConfig(
                model=VideoModel.VEO_3_1,
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
            )
            
            reference_image_bytes = []
            for url in selected_images:
                try:
                    img_bytes = await self._download_image(url)
                    reference_image_bytes.append(img_bytes)
                except Exception as e:
                    logger.warning(f"Failed to download reference image {url}: {e}")
            
            logger.info(f"Downloaded {len(reference_image_bytes)} reference images for Veo")
            
            segment_plans = plan_video_segments(duration_seconds)
            
            initial_prompt = build_video_prompt(
                script_output=script_output,
                tool_category=tool_category,
                topic=topic,
                segment_info=segment_plans[0],
                is_extension=False,
            )
            
            extension_prompts = []
            for i, seg_plan in enumerate(segment_plans[1:], 1):
                prev_scenes = script_output.get("scenes", [])
                prev_end = ""
                if prev_scenes:
                    prev_idx = min(i - 1, len(prev_scenes) - 1)
                    prev_end = prev_scenes[prev_idx].get("description", "scene continues")
                
                ext_prompt = build_extension_prompt(
                    script_output=script_output,
                    tool_category=tool_category,
                    segment_info=seg_plan,
                    previous_end_description=prev_end,
                )
                extension_prompts.append(ext_prompt)
            
            if len(segment_plans) == 1:
                video_object, gen_time = await self.veo_service.generate_video(
                    prompt=initial_prompt,
                    config=config,
                    reference_images=reference_image_bytes if reference_image_bytes else None,
                )
                segments = [VideoSegment(
                    segment_number=0,
                    segment_type=VideoSegmentType.INITIAL,
                    duration_seconds=duration_seconds,
                    start_time=0.0,
                    end_time=float(duration_seconds),
                    prompt=initial_prompt[:500],
                    generation_time_ms=gen_time,
                    used_reference_images=bool(reference_image_bytes),
                )]
                total_generation_time_ms = gen_time
            else:
                video_object, segments, total_generation_time_ms = await self.veo_service.generate_multi_segment_video(
                    initial_prompt=initial_prompt,
                    extension_prompts=extension_prompts,
                    config=config,
                    reference_images=reference_image_bytes if reference_image_bytes else None,
                )
            
            logger.info("Downloading final video...")
            video_bytes = await self.veo_service.download_video(video_object)
            
            storage_path = f"videos/{workflow_id}/final_{int(time.time())}.mp4"
            video_url = await self._upload_to_storage(video_bytes, storage_path)
            
            generated_video = GeneratedVideo(
                url=video_url,
                storage_path=storage_path,
                duration_seconds=float(duration_seconds),
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
                total_duration_seconds=float(duration_seconds),
                total_generation_time_ms=total_generation_time_ms,
                model_used=config.model,
                fallback_used=False,
                reference_images=reference_selection,
                prompt_used=initial_prompt[:1000],
            )
            
            await self._persist_to_database(workflow_id, output)
            
            from app.utils.helpers import utc_now_iso
            
            state_update = {
                "video_output": output.model_dump(),
                "final_video_url": video_url,
                "video_metadata": {
                    "duration_seconds": duration_seconds,
                    "segments": len(segments),
                    "resolution": config.resolution.value,
                    "aspect_ratio": config.aspect_ratio.value,
                    "model_used": config.model.value,
                    "generation_time_ms": total_generation_time_ms,
                },
                "phase_timestamps": {
                    **state.get("phase_timestamps", {}),
                    "video_generator_completed": utc_now_iso(),
                },
            }
            
            total_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"Video generation completed: {duration_seconds}s video, "
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
            }
    
    def _get_tool_category(self, state: VideoGenerationState) -> str:
        """Extract tool category from state."""
        selected_tool = state.get("selected_tool", {})
        if selected_tool:
            return selected_tool.get("category", "surreal_realism")
        return state.get("category", "surreal_realism")
    
    async def _download_image(self, url: str) -> bytes:
        """Download image from URL.
        
        Args:
            url: Image URL
            
        Returns:
            Image bytes
        """
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download image: {response.status}")
                return await response.read()
    
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
                path=full_path,
                file=video_bytes,
                file_options={"content-type": "video/mp4"}
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
            
            self.supabase.table("workflows").update({
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
            }).eq("id", workflow_id).execute()
            
            self.supabase.table("media").insert({
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
            }).execute()
            
            logger.info(f"Persisted video output to database for workflow: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Database persistence failed: {e}")


async def video_generator_node(state: VideoGenerationState) -> dict[str, Any]:
    """LangGraph node for video generation.
    
    Args:
        state: Current workflow state
        
    Returns:
        State update dict
    """
    agent = VideoGeneratorAgent()
    return await agent.run(state)
