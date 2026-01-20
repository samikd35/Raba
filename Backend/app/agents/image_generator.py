"""RABA Image Generator Agent.

Generates up to 3 reference images using Nano Banana Pro/Flash for video generation.
Maintains visual consistency across all images in a workflow.

Key Features:
- Smart image count calculation based on external images
- Tool-specific visual vocabulary in prompts
- Sequential generation with style consistency
- Supabase Storage upload and persistence

Reference: 
- PHASE3_1_IMAGE_GENERATOR_PLAN.md
- RABA_Architecture.md Section 2.6
- Backend/Documentations/nano_prompt_guide.md
"""

import time
from datetime import datetime
from typing import Any, Optional

from app.graph.state import VideoGenerationState
from app.models.image import (
    GeneratedImage,
    ImageAspectRatio,
    ImageGenerationConfig,
    ImageGeneratorOutput,
    ImageModel,
    ImageResolution,
    ImageSource,
    StyleReference,
    WorkflowImage,
)
from app.services.nano_banana import get_nano_banana_service
from app.services.prompt_builder import get_prompt_builder
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Limit generated images to align with Veo reference cap
MIN_GENERATED_IMAGES = 1  # Always generate at least 1 image
MAX_GENERATED_IMAGES = 1  # CRITIC: Master Style Frame only (single image)
VEO_MAX_REFERENCE_IMAGES = 3  # Veo 3.1 accepts max 3 reference images

ASPECT_RATIO_MAP = {
    "9:16": ImageAspectRatio.PORTRAIT_9_16,
    "16:9": ImageAspectRatio.LANDSCAPE_16_9,
    "1:1": ImageAspectRatio.SQUARE,
}

RESOLUTION_MAP = {
    "720p": ImageResolution.RES_1K,
    "1080p": ImageResolution.RES_2K,
    "4k": ImageResolution.RES_4K,
}


def calculate_images_to_generate(
    scene_count: int,
    user_has_reference: bool = False,
    research_image_count: int = 0,
) -> int:
    """Calculate how many images to generate with Nano Banana.
    
    IMPORTANT: User reference and research images are used as STYLE REFERENCES
    during image generation, NOT as final reference images for Veo. We should
    ALWAYS generate up to 3 images regardless of user/research images.
    
    All generated images (up to 3) are then used as references for Veo video generation.
    User reference and research images help maintain style consistency but don't
    reduce the number of images we generate.
    
    Logic:
    - Always generate up to MAX_GENERATED_IMAGES (3) images
    - Respect scene_count limit (don't generate more images than scenes)
    - Generate at least MIN_GENERATED_IMAGES (1) image
    - User reference and research images are used as style references, not counted
    
    Args:
        scene_count: Number of scenes in the script
        user_has_reference: Whether user provided a reference image (used for style, not counted)
        research_image_count: Number of images from research (used for style, not counted)
        
    Returns:
        Number of images to generate (1-3)
    """
    # CRITIC: Master Style Frame only – always generate 1 image
    to_generate = 1
    
    # Ensure at least 1 image is generated
    to_generate = max(MIN_GENERATED_IMAGES, to_generate)
    
    logger.info(
        f"Image count calculation: scenes={scene_count}, user_ref={user_has_reference} "
        f"(style reference only), research={research_image_count} (style reference only), "
        f"generating={to_generate} images"
    )
    
    return to_generate


def build_image_prompt(
    scene: dict,
    scene_number: int,
    total_scenes: int,
    tool_category: str,
    topic: str,
    duration_seconds: int,
    anchor: dict | None = None,
) -> str:
    """Build image generation prompt from scene description.
    
    Uses tool-specific visual vocabulary for consistent style.
    
    Args:
        scene: Scene dict from script output
        scene_number: Current scene number (1-indexed)
        total_scenes: Total number of scenes
        tool_category: Tool category for visual style
        topic: Video topic for context
        duration_seconds: Video duration
        
    Returns:
        Formatted prompt for image generation
    """
    parts = []
    parts.append("Create a single MASTER STYLE FRAME image that defines overall style and character consistency for the entire video.\n\n")
    parts.append(f"TOPIC CONTEXT: {topic}. Duration: {duration_seconds}s.\n\n")
    parts.append("VISUAL DESCRIPTION (representative opening moment):\n")
    description = scene.get("description", "")
    if description:
        parts.append(f"{description}\n\n")
    parts.append("STYLE REQUIREMENTS:\n")
    if anchor:
        parts.append(f"- Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n")
        parts.append(f"- Materials: {', '.join(anchor.get('materials', [])[:6])}\n")
        parts.append(f"- Motion Language: {', '.join(anchor.get('motion_language', [])[:6])}\n")
        if anchor.get('lighting'):
            parts.append(f"- Lighting: {anchor.get('lighting')}\n")
        if anchor.get('camera'):
            parts.append(f"- Camera: {anchor.get('camera')}\n")
    parts.append("\nTECHNICAL: High resolution, sharp details, professional quality.")
    return "".join(parts)


class ImageGeneratorAgent:
    """Agent for generating reference images with style consistency.
    
    Generates up to 3 images based on script scenes, maintaining visual
    consistency across all images for a cohesive video.
    """
    
    def __init__(self):
        """Initialize the Image Generator Agent."""
        self.nano_banana = get_nano_banana_service()
        self.supabase = get_supabase_client()
        self.prompt_builder = get_prompt_builder()
        logger.info("ImageGeneratorAgent initialized")
    
    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        """Run the image generation process.
        
        Args:
            state: Current workflow state
            
        Returns:
            State update dict with generated images
        """
        start_time = time.time()
        workflow_id = state.get("workflow_id", "unknown")
        
        logger.info(f"Starting image generation for workflow: {workflow_id}")
        
        try:
            script_output = state.get("script_output", {})
            scenes = script_output.get("scenes", []) or state.get("scenes", [])
            
            if not scenes:
                logger.warning("No scenes found in state, using default scene")
                scenes = [{"description": state.get("topic", ""), "scene_number": 1}]
            
            tool_category = self._get_tool_category(state)
            user_reference_url = state.get("user_reference_image_url")
            research_images = state.get("research_images", []) or []
            aspect_ratio = state.get("aspect_ratio", "9:16")
            resolution = state.get("resolution", "1080p")
            topic = state.get("topic", "")
            duration_seconds = state.get("duration_seconds", 18)
            
            # CRITIC: Always generate a single Master Style Frame
            images_to_generate = 1
            
            config = ImageGenerationConfig(
                model=ImageModel.NANO_BANANA_PRO,
                aspect_ratio=ASPECT_RATIO_MAP.get(aspect_ratio, ImageAspectRatio.PORTRAIT_9_16),
                resolution=RESOLUTION_MAP.get(resolution, ImageResolution.RES_2K),
                style_keywords=[],
                maintain_consistency=True,
            )
            
            prompts = []
            selected_scenes = scenes[:1] if scenes else [{"description": topic, "scene_number": 1}]
            anchor = state.get("global_style_anchor") or {}
            neg_default = (
                "The image must be free of text, watermarks, labels, lettering, and UI overlays. "
                "No artifacts, distorted elements, or unintended graphical additions."
            )
            tool = state.get("selected_tool") or {}
            neg_from_tool = tool.get("image_negative_constraint")
            negative_block = neg_from_tool if (isinstance(neg_from_tool, str) and neg_from_tool.strip()) else neg_default
            for i, scene in enumerate(selected_scenes):
                # Template-based prompt if available
                template = (state.get("selected_tool") or {}).get("image_prompt_template")
                if template:
                    try:
                        context = {
                            "scene_description": scene.get("description", ""),
                            "style": tool_category,
                            "scene_number": i + 1,
                            "total_scenes": len(selected_scenes),
                            "camera_direction": scene.get("camera_direction", ""),
                            "lighting": scene.get("lighting", ""),
                            "mood": scene.get("mood", ""),
                            "topic": topic,
                            "duration_seconds": duration_seconds,
                            # Global style anchor context
                            "global_color_palette": ", ".join(anchor.get("color_palette", [])[:6]),
                            "global_materials": ", ".join(anchor.get("materials", [])[:6]),
                            "global_motion_language": ", ".join(anchor.get("motion_language", [])[:6]),
                            "global_lighting": anchor.get("lighting", ""),
                            "global_camera": anchor.get("camera", ""),
                            "global_texture": anchor.get("texture", ""),
                            "image_negative_constraint": negative_block,
                        }
                        rr = self.prompt_builder.render(
                            template,
                            context,
                            required=["scene_description", "style"],
                            min_words=50,
                            fallback_prompt_builder=lambda: build_image_prompt(
                                scene=scene,
                                scene_number=i + 1,
                                total_scenes=len(selected_scenes),
                                tool_category=tool_category,
                                topic=topic,
                                duration_seconds=duration_seconds,
                                anchor=anchor,
                            ),
                        )
                        # Append Negative Constraint Block if template didn't include it
                        prompt_text = rr.prompt
                        if "image_negative_constraint" not in (template or ""):
                            prompt_text += "\n\nNEGATIVE CONSTRAINTS: " + negative_block
                        prompts.append(prompt_text)
                        if rr.fallback_used:
                            logger.warning(f"Image template fallback used for scene {i+1}")
                        else:
                            logger.info(f"Rendered image template for scene {i+1}")
                    except Exception as e:
                        logger.warning(f"Image template rendering failed for scene {i+1}: {e}; using fallback")
                        prompts.append(
                            build_image_prompt(
                                scene=scene,
                                scene_number=i + 1,
                                total_scenes=len(selected_scenes),
                                tool_category=tool_category,
                                topic=topic,
                                duration_seconds=duration_seconds,
                            )
                        )
                else:
                    prompt = build_image_prompt(
                        scene=scene,
                        scene_number=i + 1,
                        total_scenes=len(selected_scenes),
                        tool_category=tool_category,
                        topic=topic,
                        duration_seconds=duration_seconds,
                    )
                    # Append anchor to fallback prompt
                    if anchor:
                        prompt += (
                            "\n\n[GLOBAL STYLE ANCHOR]\n"
                            f"Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n"
                            f"Materials: {', '.join(anchor.get('materials', [])[:6])}\n"
                            f"Motion: {', '.join(anchor.get('motion_language', [])[:6])}\n"
                            f"Lighting: {anchor.get('lighting','')}\n"
                            f"Camera: {anchor.get('camera','')}\n"
                        )
                    prompt += "\n\nNEGATIVE CONSTRAINTS: " + negative_block
                    prompts.append(prompt)
            
            style_reference = self._build_style_reference(
                tool_category=tool_category,
                scenes=scenes,
            )
            # Apply global style anchor into style reference for consistency
            if anchor:
                try:
                    if anchor.get("style_description"):
                        style_reference.style_description = anchor["style_description"]
                    if anchor.get("color_palette"):
                        style_reference.color_palette = list(anchor["color_palette"])[:5]
                except Exception:
                    pass
            
            # Download user reference image if provided
            user_ref_bytes = None
            if user_reference_url:
                try:
                    user_ref_bytes = await self.nano_banana.download_image_as_bytes(user_reference_url)
                    logger.info("Downloaded user reference image")
                except Exception as e:
                    logger.warning(f"Failed to download user reference: {e}")
            
            # Download research images to use as style reference for Nano Banana Pro
            # These images guide the visual style but are NOT used in Video Generator
            research_ref_bytes = []
            for img_url in research_images[:3]:  # Use up to 3 research images
                try:
                    img_bytes = await self.nano_banana.download_image_as_bytes(img_url)
                    research_ref_bytes.append(img_bytes)
                except Exception as e:
                    logger.warning(f"Failed to download research image: {e}")
            # Add character reference images (if available) as high-priority style references
            char_sheet = state.get("character_reference_sheet") or {}
            char_refs = char_sheet.get("reference_images") or []
            for ref in char_refs[:3]:
                try:
                    url = ref.get("url") if isinstance(ref, dict) else None
                    if url:
                        img_bytes = await self.nano_banana.download_image_as_bytes(url)
                        research_ref_bytes.append(img_bytes)
                except Exception as e:
                    logger.warning(f"Failed to download character ref image: {e}")
            
            if research_ref_bytes:
                logger.info(f"Downloaded {len(research_ref_bytes)} style reference images (research + character)")
            
            logger.info(f"Generating {len(prompts)} images sequentially with style consistency")
            
            results = await self.nano_banana.generate_sequential_images(
                prompts=prompts,
                config=config,
                initial_style_reference=style_reference,
                user_reference_image=user_ref_bytes,
                research_reference_images=research_ref_bytes if research_ref_bytes else None,
            )
            
            generated_images = []
            for i, (image_bytes, text_response, retry_count) in enumerate(results):
                scene = selected_scenes[i]
                
                storage_path = f"generated_images/{workflow_id}/scene_{i + 1}_{int(time.time())}.png"
                image_url = await self._upload_to_storage(image_bytes, storage_path)
                
                generated_image = GeneratedImage(
                    url=image_url,
                    storage_path=storage_path,
                    prompt=prompts[i],
                    scene_number=i + 1,
                    model_used=config.model,
                    aspect_ratio=config.aspect_ratio,
                    resolution=config.resolution,
                    generation_time_ms=0,
                    used_style_reference=(i > 0 or user_ref_bytes is not None),
                    style_reference_url=user_reference_url if i == 0 else None,
                    retry_count=retry_count,
                    role="master_style_frame",
                )
                generated_images.append(generated_image)
                logger.info(f"Image {i + 1} uploaded: {image_url}")
            
            all_images = self._combine_all_images(
                user_reference_url=user_reference_url,
                research_images=research_images,
                generated_images=generated_images,
            )
            
            output = ImageGeneratorOutput(
                generated_images=generated_images,
                all_images=all_images,
                style_reference=style_reference,
                total_images_generated=len(generated_images),
                total_generation_time_ms=int((time.time() - start_time) * 1000),
                model_used=config.model,
                fallback_used=any(img.model_used == ImageModel.NANO_BANANA for img in generated_images),
            )
            
            await self._persist_to_database(workflow_id, output)
            
            from app.utils.helpers import utc_now_iso
            
            state_update = {
                "generated_images": [img.url for img in generated_images],
                "all_images": [img.url for img in all_images],
                "image_metadata": [img.model_dump() for img in generated_images],
                "phase_timestamps": {
                    **state.get("phase_timestamps", {}),
                    "image_generator_completed": utc_now_iso(),
                },
            }
            
            logger.info(
                f"Image generation completed: {len(generated_images)} images in "
                f"{output.total_generation_time_ms}ms"
            )
            
            return state_update
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {
                "error": f"Image generation failed: {str(e)}",
                "error_details": {
                    "phase": "image_generator",
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
    
    def _build_style_reference(
        self,
        tool_category: str,
        scenes: list[dict],
    ) -> StyleReference:
        """Build comprehensive style reference for consistency.
        
        Extracts character descriptions, builds detailed style instructions,
        and creates color palette hints based on tool category.
        """
        # The prompt-building phase passes anchors explicitly; keep this reference generic.
        
        # Extract character descriptions more thoroughly
        character_descriptions = []
        for scene in scenes:
            desc = scene.get("description", "")
            dialogue = scene.get("dialogue", "")
            
            # Look for character mentions with broader keywords
            char_keywords = [
                "character", "person", "player", "man", "woman", "child", "figure",
                "protagonist", "character", "individual", "subject", "moses", "pharaoh"
            ]
            if any(keyword in desc.lower() for keyword in char_keywords):
                # Extract longer, more detailed character description
                char_desc = desc[:300]  # Longer description for better consistency
                if dialogue:
                    char_desc += f" Dialogue style: {dialogue[:100]}"
                character_descriptions.append(char_desc)
        
        # Build comprehensive style description with detailed requirements
        style_description = (
            "VISUAL STYLE REQUIREMENTS (CONSISTENCY):\n"
            "- Maintain identical color grading, lighting approach, and rendering quality across all images.\n"
            "- Keep camera treatment and composition consistent for coherent sequencing.\n"
            "- Characters (if any) must look identical across scenes (appearance, clothing, proportions).\n"
        )
        
        # Extract color palette hints based on tool category
        color_palette = []
        
        return StyleReference(
            style_description=style_description,
            character_descriptions=character_descriptions[:3],  # Up to 3 characters
            color_palette=color_palette,
        )
    
    async def _upload_to_storage(self, image_bytes: bytes, storage_path: str) -> str:
        """Upload image to Supabase Storage.
        
        Args:
            image_bytes: Image data
            storage_path: Path in storage bucket
            
        Returns:
            Public URL of uploaded image
        """
        try:
            bucket_name = "media"  # Use existing 'media' bucket
            full_path = f"generated_images/{storage_path}"
            
            result = self.supabase.storage.from_(bucket_name).upload(
                path=full_path,
                file=image_bytes,
                file_options={"content-type": "image/png"}
            )
            
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(full_path)
            
            return public_url
            
        except Exception as e:
            logger.error(f"Storage upload failed: {e}")
            return f"upload_failed://{storage_path}"
    
    def _combine_all_images(
        self,
        user_reference_url: Optional[str],
        research_images: list[str],
        generated_images: list[GeneratedImage],
    ) -> list[WorkflowImage]:
        """Combine all image sources into unified list.
        
        Order: user_reference -> research -> generated
        """
        all_images = []
        
        if user_reference_url:
            all_images.append(WorkflowImage(
                url=user_reference_url,
                source=ImageSource.USER_REFERENCE,
                description="User-provided reference image",
                is_style_reference=True,
            ))
        
        for i, url in enumerate(research_images[:2]):
            all_images.append(WorkflowImage(
                url=url,
                source=ImageSource.RESEARCH,
                description=f"Research image {i + 1}",
                is_style_reference=False,
            ))
        
        for img in generated_images:
            all_images.append(WorkflowImage(
                url=img.url,
                source=ImageSource.GENERATED,
                scene_number=img.scene_number,
                description=f"Generated image for scene {img.scene_number}",
                is_style_reference=False,
            ))
        
        return all_images
    
    async def _persist_to_database(
        self,
        workflow_id: str,
        output: ImageGeneratorOutput,
    ) -> None:
        """Persist image output to Supabase."""
        try:
            from app.utils.helpers import utc_now_iso
            
            # Use mode='json' for proper serialization of enums and datetimes
            # Note: all_image_urls column doesn't exist in workflows table
            self.supabase.table("workflows").update({
                "generated_images": {
                    "images": [img.model_dump(mode='json') for img in output.generated_images],
                    "total_count": output.total_images_generated,
                    "generation_time_ms": output.total_generation_time_ms,
                    "model_used": output.model_used.value if hasattr(output.model_used, 'value') else str(output.model_used),
                    "all_image_urls": output.all_image_urls,  # Store within generated_images JSON
                },
                "updated_at": utc_now_iso(),
            }).eq("id", workflow_id).execute()
            
            for img in output.generated_images:
                self.supabase.table("media").insert({
                    "workflow_id": workflow_id,
                    "media_type": "image",  # Allowed: image, video, audio
                    "source": "generated",  # Allowed: user_upload, research, generated
                    "storage_url": img.url,
                    "storage_path": img.storage_path,
                    "metadata": {
                        "scene_number": img.scene_number,
                        "prompt": img.prompt[:500],
                        "model_used": img.model_used.value,
                        "aspect_ratio": img.aspect_ratio.value,
                        "resolution": img.resolution.value,
                    },
                }).execute()
            
            logger.info(f"Persisted {len(output.generated_images)} images to database")
            
        except Exception as e:
            logger.error(f"Database persistence failed: {e}")


async def image_generator_node(state: VideoGenerationState) -> dict[str, Any]:
    """LangGraph node for image generation.
    
    Args:
        state: Current workflow state
        
    Returns:
        State update dict
    """
    agent = ImageGeneratorAgent()
    return await agent.run(state)
