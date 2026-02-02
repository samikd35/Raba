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
    ImageGenerationRequest,
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
from app.utils.prompt_sanitizer import clean_visual_prompt, sanitize_scene

logger = get_logger(__name__)

# Limit generated images to align with Veo reference cap
MIN_GENERATED_IMAGES = 1  # Always generate at least 1 image
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
    enable_ingredients_mode: bool = True,
) -> int:
    """Calculate how many images to generate with Nano Banana.

    INGREDIENTS MODE (Veo 3.1 Best Practice):
    Generate exactly 3 distinct "ingredient" images:
    1. Subject - The main character/host/actor
    2. Environment - The background/setting
    3. Object/Concept - The key diagram/element

    This prevents style poisoning and supports Veo 3.1 multi-reference compositing.

    Args:
        scene_count: Number of scenes in the script (informational)
        user_has_reference: Whether user provided a reference image
        research_image_count: Number of images from research
        enable_ingredients_mode: If True, always generate 3 ingredient images

    Returns:
        Number of images to generate (3 in ingredients mode, else 1 legacy)
    """
    if enable_ingredients_mode:
        to_generate = min(VEO_MAX_REFERENCE_IMAGES, 3)
        logger.info(
            f"Ingredients mode enabled: generating {to_generate} reference images (Subject, Environment, Object)"
        )
        return to_generate

    # Legacy storyboard mode: fall back to single composite
    to_generate = MIN_GENERATED_IMAGES
    logger.info("Legacy storyboard mode: generating 1 composite image")
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
    parts.append(
        "Create a single MASTER STYLE FRAME image that defines overall style and character consistency for the entire video.\n\n"
    )
    parts.append(f"TOPIC CONTEXT: {topic}. Duration: {duration_seconds}s.\n\n")
    parts.append("VISUAL DESCRIPTION (representative opening moment):\n")
    description = clean_visual_prompt(scene.get("description", ""))
    if description:
        parts.append(f"{description}\n\n")
    parts.append("STYLE REQUIREMENTS:\n")
    if anchor:
        parts.append(f"- Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n")
        parts.append(f"- Materials: {', '.join(anchor.get('materials', [])[:6])}\n")
        parts.append(f"- Motion Language: {', '.join(anchor.get('motion_language', [])[:6])}\n")
        if anchor.get("lighting"):
            parts.append(f"- Lighting: {anchor.get('lighting')}\n")
        if anchor.get("camera"):
            parts.append(f"- Camera: {anchor.get('camera')}\n")
    parts.append("\nTECHNICAL: High resolution, sharp details, professional quality.")
    return "".join(parts)


# -----------------------------
# Storyboard composition helpers
# -----------------------------


def select_key_scenes(scenes: list[dict], max_count: int) -> list[dict]:
    """Select most visually important scenes for storyboard.

    Priority: First scene, last scene, scenes with highest visual keyword density.
    """
    if not scenes:
        return []
    if len(scenes) <= max_count:
        return scenes

    selected: list[dict] = []
    selected.append(scenes[0])
    if len(scenes) > 1:
        selected.append(scenes[-1])

    remaining = [s for s in scenes[1:-1]]
    remaining.sort(key=lambda s: len(s.get("visual_keywords", []) or []), reverse=True)

    for scene in remaining:
        if len(selected) >= max_count:
            break
        if scene not in selected:
            selected.append(scene)

    selected.sort(key=lambda s: s.get("scene_number", 0))
    return selected


def aggregate_scene_descriptions(scenes: list[dict], max_scenes: int = 6) -> str:
    """Aggregate scene descriptions into a storyboard brief."""
    if not scenes:
        return ""
    selected = select_key_scenes(scenes, max_scenes)
    parts: list[str] = []
    for i, scene in enumerate(selected):
        desc = clean_visual_prompt((scene.get("description", "") or "")[:200])
        keywords = scene.get("visual_keywords", []) or []
        scene_num = scene.get("scene_number", i + 1)
        kw = (" | Keywords: " + ", ".join(keywords[:4])) if keywords else ""
        parts.append(f"[SCENE {scene_num}]: {desc}{kw}")
    return "\n".join(parts)


def extract_key_entities(scenes: list[dict], topic: str) -> str:
    """Extract primary visual entities from all scenes."""
    entities: set[str] = set()
    topic_lower = (topic or "").lower()
    for scene in scenes or []:
        keywords = scene.get("visual_keywords", []) or []
        for k in keywords[:3]:
            if isinstance(k, str) and k.strip():
                entities.add(k.strip())
    prioritized = [e for e in entities if e.lower() in topic_lower]
    others = [e for e in entities if e not in prioritized]
    return ", ".join(prioritized[:5] + others[:5])


def extract_transformation_flow(scenes: list[dict]) -> str:
    """Extract entity transformation sequence from scenes."""
    if not scenes or len(scenes) < 2:
        return ""
    flow_parts: list[str] = []
    for scene in scenes:
        desc = (scene.get("description", "") or "").lower()
        keywords = scene.get("visual_keywords", []) or []
        if any(w in desc for w in ["morph", "transform", "evolve", "become", "change"]):
            if keywords:
                flow_parts.append(str(keywords[0]))
    if len(flow_parts) >= 2:
        return " → ".join(flow_parts)
    first_kw = (scenes[0].get("visual_keywords", ["Start"]) or ["Start"])[0]
    last_kw = (scenes[-1].get("visual_keywords", ["End"]) or ["End"])[0]
    return f"{first_kw} → ... → {last_kw}"


def extract_environment_from_scenes(scenes: list[dict]) -> str:
    """Extract primary environment/setting from scenes."""
    environments = set()
    for scene in scenes or []:
        desc = (scene.get("description", "") or "").lower()
        for keyword in [
            "laboratory",
            "studio",
            "office",
            "forest",
            "space",
            "underwater",
            "city",
            "desert",
        ]:
            if keyword in desc:
                environments.add(keyword)
    if environments:
        return ", ".join(list(environments)[:2])
    return ""


def determine_composition_layout(scene_count: int, has_character: bool) -> str:
    """Determine optimal storyboard layout based on content."""
    if scene_count <= 3:
        layout = "horizontal triptych (3 panels left-to-right)"
    elif scene_count <= 6:
        layout = "2x3 grid (6 panels, left-to-right, top-to-bottom)"
    else:
        layout = "horizontal timeline strip with key moments"
    if has_character and scene_count <= 4:
        layout = "central character with surrounding scene vignettes"
    return layout


def build_character_reference_context(
    character_sheet: dict | None, script_output: dict
) -> tuple[str, str]:
    """Build character reference context for image prompt."""
    char_name = script_output.get("lead_character", "") or ""
    char_desc = script_output.get("lead_character_description", "") or ""
    char_ref = ""
    cs = character_sheet or {}
    if cs:
        sheet_name = cs.get("character_name", "") or ""
        sheet_desc = cs.get("character_description", "") or ""
        ref_images = cs.get("reference_images", []) or []
        if sheet_name:
            char_name = sheet_name
        parts: list[str] = []
        if sheet_desc:
            parts.append(f"Character: {sheet_desc}")
        elif char_desc:
            parts.append(f"Character: {char_desc}")
        if ref_images:
            views = [
                img.get("view", "")
                for img in ref_images
                if isinstance(img, dict) and img.get("view")
            ]
            if views:
                parts.append(f"Reference views available: {', '.join(views)}")
            parts.append("Maintain exact character appearance across all storyboard panels.")
        char_ref = " ".join(parts)
    elif char_desc:
        char_ref = f"Lead character: {char_desc}. Maintain consistent appearance across all panels."
    return char_name, char_ref


def build_storyboard_prompt(
    scenes: list[dict],
    topic: str,
    duration_seconds: int,
    tool_category: str,
    anchor: dict | None = None,
    character_sheet: dict | None = None,
    script_output: dict | None = None,
) -> str:
    """Build storyboard-style master image prompt."""
    script_output = script_output or {}
    scene_descriptions = aggregate_scene_descriptions(scenes)
    scene_count = len(scenes)
    key_entities = extract_key_entities(scenes, topic)
    transformation_flow = extract_transformation_flow(scenes)
    composition_layout = determine_composition_layout(scene_count, bool(character_sheet))
    _char_name, char_ref = build_character_reference_context(character_sheet, script_output)

    parts: list[str] = []
    parts.append(
        "Create a STORYBOARD MASTER IMAGE that shows the complete visual narrative "
        "in a single composite frame. This image defines the visual DNA for video generation.\n\n"
    )
    parts.append(f"VIDEO CONCEPT: {topic}\n")
    parts.append(f"DURATION: {duration_seconds} seconds | SCENES: {scene_count}\n\n")
    parts.append(f"STORYBOARD LAYOUT: {composition_layout}\n\n")
    if key_entities:
        parts.append(f"KEY VISUAL ENTITIES (must all appear): {key_entities}\n\n")
    if transformation_flow:
        parts.append(f"VISUAL FLOW/TRANSFORMATION: {transformation_flow}\n\n")
    parts.append("SCENE BREAKDOWN:\n")
    parts.append(scene_descriptions)
    parts.append("\n\n")
    if char_ref:
        parts.append(f"CHARACTER CONSISTENCY: {char_ref}\n\n")
    if anchor:
        parts.append("STYLE REQUIREMENTS:\n")
        parts.append(f"- Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n")
        parts.append(f"- Materials: {', '.join(anchor.get('materials', [])[:6])}\n")
        parts.append(f"- Lighting: {anchor.get('lighting', '')}\n")
        parts.append(f"- Camera: {anchor.get('camera', '')}\n\n")
    parts.append(
        "CRITICAL: Generate a SINGLE composite image showing ALL listed scenes/entities. "
        "Each panel or section should represent a different scene moment. "
        "Maintain unified style treatment across all panels. This storyboard will guide video generation.\n"
    )
    return "".join(parts)


def build_ingredient_prompt(
    ingredient_type: str,
    scenes: list[dict],
    topic: str,
    tool_category: str,
    anchor: dict | None = None,
    character_sheet: dict | None = None,
    script_output: dict | None = None,
) -> str:
    """Build prompt for a specific ingredient type."""
    parts: list[str] = []

    if ingredient_type == "subject":
        parts.append(
            f"[INGREDIENT: SUBJECT - Character/Host Consistency]\n"
            f"Generate a REFERENCE SHEET showing the main character/host for: {topic}\n\n"
        )
        if character_sheet:
            _char_name, char_ref = build_character_reference_context(
                character_sheet, script_output or {}
            )
            if char_ref:
                parts.append(f"CHARACTER: {char_ref}\n\n")
        elif script_output and script_output.get("lead_character"):
            lead = script_output.get("lead_character")
            desc = script_output.get("lead_character_description", "")
            parts.append(f"CHARACTER: {lead}. {desc}\n\n")
        else:
            parts.append(
                f"CHARACTER: A professional host/presenter suitable for {topic}. "
                f"Clean, neutral appearance for maximum compositing flexibility.\n\n"
            )
        parts.append(
            "REQUIREMENTS:\n"
            "- Multiple views: Front, 3/4 profile, side view\n"
            "- Consistent appearance, clothing, proportions across all views\n"
            "- Clean background for easy compositing\n"
            "- High detail on face and distinguishing features\n"
        )
    elif ingredient_type == "environment":
        parts.append(
            f"[INGREDIENT: ENVIRONMENT - Background/Setting]\n"
            f"Generate a CLEAN, HIGH-QUALITY background environment for: {topic}\n\n"
        )
        key_settings = extract_environment_from_scenes(scenes)
        if key_settings:
            parts.append(f"SETTING: {key_settings}\n\n")
        else:
            parts.append(
                f"SETTING: Professional studio environment suitable for {topic}.\n"
                f"Neutral, clean, no distracting elements.\n\n"
            )
        parts.append(
            "REQUIREMENTS:\n"
            "- NO characters or objects (pure background)\n"
            "- High-resolution, clean composition\n"
            "- Neutral lighting that works with any foreground\n"
            f"- Style consistent with {tool_category}\n"
        )
    else:
        parts.append(
            f"[INGREDIENT: OBJECT/CONCEPT - Key Visual Element]\n"
            f"Generate a TECHNICAL DIAGRAM or KEY OBJECT for: {topic}\n\n"
        )
        key_entities = extract_key_entities(scenes, topic)
        if key_entities:
            parts.append(f"KEY ENTITIES: {key_entities}\n\n")
        parts.append(
            "SCIENTIFIC CINEMATOGRAPHER REQUIREMENTS:\n"
            "- [Subject]: The specific object/concept (e.g., 'red blood cell', 'DNA strand')\n"
            "- [Composition]: Extreme close-up OR technical cross-section\n"
            "- [Style]: Scientific infographic, 4K resolution, sharp focus\n"
            "- [Constraint]: Clean labels with sans-serif typography (if text_overlay_mode allows)\n"
            "- [Constraint]: Clinical white or neutral background for maximum clarity\n"
            "- NO artistic interpretation - FACTUAL ACCURACY REQUIRED\n"
        )

    if anchor:
        parts.append("\nSTYLE ANCHOR:\n")
        parts.append(f"- Palette: {', '.join(anchor.get('color_palette', [])[:4])}\n")
        if anchor.get("lighting"):
            parts.append(f"- Lighting: {anchor.get('lighting')}\n")

    parts.append(f"\nSTYLE CATEGORY: {tool_category}\n")
    parts.append("TECHNICAL: 8K resolution, sharp detail, professional quality.\n")

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
            script_output = state.get("script_output") or {}
            scenes = script_output.get("scenes", []) or state.get("scenes") or []

            if not scenes:
                logger.warning("No scenes found in state, using default scene")
                scenes = [{"description": state.get("topic", ""), "scene_number": 1}]

            tool_category = self._get_tool_category(state)
            user_reference_url = state.get("user_reference_image_url")
            research_images = state.get("research_images") or []
            aspect_ratio = state.get("aspect_ratio", "9:16")
            resolution = state.get("resolution", "1080p")
            topic = state.get("topic", "")
            duration_seconds = state.get("duration_seconds", 18)

            ImageGenerationRequest.model_validate(
                {
                    "workflow_id": workflow_id,
                    "scenes": scenes,
                    "tool_category": tool_category,
                    "tool_visual_vocabulary": {},
                    "user_reference_image_url": user_reference_url,
                    "research_images": research_images,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "topic": topic,
                    "duration_seconds": duration_seconds,
                }
            )

            # Enable Ingredients mode for Veo 3.1 optimization
            images_to_generate = calculate_images_to_generate(
                scene_count=len(scenes),
                user_has_reference=bool(user_reference_url),
                research_image_count=len(research_images),
                enable_ingredients_mode=True,
            )

            config = ImageGenerationConfig(
                model=ImageModel.NANO_BANANA_PRO,
                aspect_ratio=ASPECT_RATIO_MAP.get(aspect_ratio, ImageAspectRatio.PORTRAIT_9_16),
                resolution=RESOLUTION_MAP.get(resolution, ImageResolution.RES_2K),
                style_keywords=[],
                maintain_consistency=True,
            )

            prompts = []
            selected_scenes = scenes[:1] if scenes else [{"description": topic, "scene_number": 1}]
            selected_scenes = [sanitize_scene(s) for s in selected_scenes]
            anchor = state.get("global_style_anchor") or {}
            neg_default = (
                "The image must be free of text, watermarks, labels, lettering, and UI overlays. "
                "No artifacts, distorted elements, or unintended graphical additions."
            )
            tool = state.get("selected_tool") or {}
            neg_from_tool = tool.get("image_negative_constraint")
            negative_block = (
                neg_from_tool
                if (isinstance(neg_from_tool, str) and neg_from_tool.strip())
                else neg_default
            )
            # Build prompts according to Ingredients strategy (or legacy fallback)
            template = (state.get("selected_tool") or {}).get("image_prompt_template")
            character_sheet = state.get("character_reference_sheet") or None
            storyboard_ctx = {
                "scene_descriptions": aggregate_scene_descriptions(scenes),
                "scene_count": len(scenes),
                "key_entities": extract_key_entities(scenes, topic),
                "transformation_flow": extract_transformation_flow(scenes),
                "composition_layout": determine_composition_layout(
                    len(scenes), bool(character_sheet)
                ),
            }
            if template:
                try:
                    if images_to_generate == 3:
                        ingredient_types = ["subject", "environment", "object"]
                        for idx, ing in enumerate(ingredient_types, start=1):
                            scene = scenes[0] if scenes else {"description": topic, "scene_number": idx}
                            char_name, char_ref = build_character_reference_context(
                                character_sheet, script_output
                            )
                            ctx = {
                                "scene_description": clean_visual_prompt(scene.get("description", "")),
                                "style": tool_category,
                                "scene_number": idx,
                                "total_scenes": len(scenes),
                                "camera_direction": scene.get("camera_direction", ""),
                                "lighting": scene.get("lighting", ""),
                                "mood": scene.get("mood", ""),
                                "topic": topic,
                                "duration_seconds": duration_seconds,
                                # Ingredients placeholders
                                "ingredient_type": ing,
                                "ingredient_subject": "Character consistency, multiple views, clean background",
                                "ingredient_environment": "Clean background only, no characters/objects",
                                "ingredient_object": "Technical diagram/key object, scientific accuracy",
                                # Storyboard placeholders retained for compatibility
                                **storyboard_ctx,
                                "character_name": char_name,
                                "character_reference": char_ref,
                                # Global style anchor context
                                "global_color_palette": ", ".join(anchor.get("color_palette", [])[:6]),
                                "global_materials": ", ".join(anchor.get("materials", [])[:6]),
                                "global_motion_language": ", ".join(anchor.get("motion_language", [])[:6]),
                                "global_lighting": anchor.get("lighting", ""),
                                "global_camera": anchor.get("camera", ""),
                                "global_texture": anchor.get("texture", ""),
                                "image_negative_constraint": negative_block,
                                "user_topic": state.get("user_topic", topic),
                                "text_overlay_mode": "no_text" if not state.get("enable_subtitles", False) else "with_text",
                            }
                            ok, errs = self.prompt_builder.runtime_validate(
                                template, ["scene_description", "style"], min_words=50
                            )
                            if not ok:
                                logger.warning(
                                    f"Image template runtime validation failed: {errs}"
                                )
                            rr = self.prompt_builder.render(
                                template,
                                ctx,
                                required=["scene_description", "style"],
                                min_words=50,
                                fallback_prompt_builder=lambda ing=ing: build_ingredient_prompt(
                                    ingredient_type=ing,
                                    scenes=scenes,
                                    topic=topic,
                                    tool_category=tool_category,
                                    anchor=anchor,
                                    character_sheet=character_sheet,
                                    script_output=script_output,
                                ),
                            )
                            prompt_text = rr.prompt
                            if "image_negative_constraint" not in (template or ""):
                                prompt_text += "\n\nNEGATIVE CONSTRAINTS: " + negative_block
                            prompts.append(prompt_text)
                    else:
                        # Legacy storyboard single prompt
                        scene = selected_scenes[0]
                        char_name, char_ref = build_character_reference_context(
                            character_sheet, script_output
                        )
                        context = {
                            "scene_description": clean_visual_prompt(scene.get("description", "")),
                            "style": tool_category,
                            "scene_number": 1,
                            "total_scenes": len(scenes),
                            "camera_direction": scene.get("camera_direction", ""),
                            "lighting": scene.get("lighting", ""),
                            "mood": scene.get("mood", ""),
                            "topic": topic,
                            "duration_seconds": duration_seconds,
                            # Storyboard placeholders
                            **storyboard_ctx,
                            "character_name": char_name,
                            "character_reference": char_ref,
                            # Global style anchor context
                            "global_color_palette": ", ".join(anchor.get("color_palette", [])[:6]),
                            "global_materials": ", ".join(anchor.get("materials", [])[:6]),
                            "global_motion_language": ", ".join(anchor.get("motion_language", [])[:6]),
                            "global_lighting": anchor.get("lighting", ""),
                            "global_camera": anchor.get("camera", ""),
                            "global_texture": anchor.get("texture", ""),
                            "image_negative_constraint": negative_block,
                        }
                        ok, errs = self.prompt_builder.runtime_validate(
                            template, ["scene_description", "style"], min_words=50
                        )
                        if not ok:
                            logger.warning(
                                f"Image template runtime validation failed: {errs}"
                            )
                        rr = self.prompt_builder.render(
                            template,
                            context,
                            required=["scene_description", "style"],
                            min_words=50,
                            fallback_prompt_builder=lambda: build_storyboard_prompt(
                                scenes=scenes,
                                topic=topic,
                                duration_seconds=duration_seconds,
                                tool_category=tool_category,
                                anchor=anchor,
                                character_sheet=character_sheet,
                                script_output=script_output,
                            ),
                        )
                        prompt_text = rr.prompt
                        if "image_negative_constraint" not in (template or ""):
                            prompt_text += "\n\nNEGATIVE CONSTRAINTS: " + negative_block
                        prompts.append(prompt_text)
                except Exception as e:
                    logger.warning(
                        f"Image template rendering failed: {e}; using fallback"
                    )
                    if images_to_generate == 3:
                        prompts = [
                            build_ingredient_prompt(
                                ingredient_type=ing,
                                scenes=scenes,
                                topic=topic,
                                tool_category=tool_category,
                                anchor=anchor,
                                character_sheet=character_sheet,
                                script_output=script_output,
                            )
                            + "\n\nNEGATIVE CONSTRAINTS: "
                            + negative_block
                            for ing in ["subject", "environment", "object"]
                        ]
                    else:
                        prompt = build_storyboard_prompt(
                            scenes=scenes,
                            topic=topic,
                            duration_seconds=duration_seconds,
                            tool_category=tool_category,
                            anchor=anchor,
                            character_sheet=character_sheet,
                            script_output=script_output,
                        )
                        prompt += "\n\nNEGATIVE CONSTRAINTS: " + negative_block
                        prompts.append(prompt)
            else:
                if images_to_generate == 3:
                    prompts = [
                        build_ingredient_prompt(
                            ingredient_type=ing,
                            scenes=scenes,
                            topic=topic,
                            tool_category=tool_category,
                            anchor=anchor,
                            character_sheet=character_sheet,
                            script_output=script_output,
                        )
                        + "\n\nNEGATIVE CONSTRAINTS: "
                        + negative_block
                        for ing in ["subject", "environment", "object"]
                    ]
                else:
                    prompt = build_storyboard_prompt(
                        scenes=scenes,
                        topic=topic,
                        duration_seconds=duration_seconds,
                        tool_category=tool_category,
                        anchor=anchor,
                        character_sheet=character_sheet,
                        script_output=script_output,
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
                    user_ref_bytes = await self.nano_banana.download_image_as_bytes(
                        user_reference_url
                    )
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
                logger.info(
                    f"Downloaded {len(research_ref_bytes)} style reference images (research + character)"
                )

            logger.info(f"Generating {len(prompts)} images sequentially with style consistency")

            results = await self.nano_banana.generate_sequential_images(
                prompts=prompts,
                config=config,
                initial_style_reference=style_reference,
                user_reference_image=user_ref_bytes,
                research_reference_images=research_ref_bytes if research_ref_bytes else None,
            )

            generated_images = []
            ingredient_roles = (
                ["subject", "environment", "object"] if images_to_generate == 3 else ["master_style_frame"]
            )
            for i, (image_bytes, text_response, usage_metadata, retry_count) in enumerate(results):
                role = ingredient_roles[i] if i < len(ingredient_roles) else f"scene_{i+1}"
                storage_path = f"generated_images/{workflow_id}/{role}_{int(time.time())}.png"
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
                    role=role,
                )
                generated_images.append(generated_image)
                logger.info(f"Image {i + 1} uploaded: {image_url} as role={role}")

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
                fallback_used=any(
                    img.model_used == ImageModel.NANO_BANANA for img in generated_images
                ),
            )

            validated_output = ImageGeneratorOutput.model_validate(output.model_dump())

            await self._persist_to_database(workflow_id, validated_output)

            from app.utils.helpers import utc_now_iso

            # Prepare lightweight validation contract for downstream VLM checks
            try:
                required_entities = [
                    e.strip() for e in (storyboard_ctx.get("key_entities") or "").split(",") if e.strip()
                ]
            except Exception:
                required_entities = []
            image_validation_contract = {
                "required_entities": required_entities,
                "constraints": [
                    "No text overlays, labels, or watermarks",
                    "Adhere to global style anchor (palette, materials, lighting, camera)",
                ],
            }

            state_update = {
                "generated_images": [img.url for img in generated_images],
                "all_images": [img.url for img in all_images],
                "image_metadata": [img.model_dump() for img in generated_images],
                "storyboard_context": {**storyboard_ctx},
                "image_validation_contract": image_validation_contract,
                "master_image_type": "ingredients" if images_to_generate == 3 else "storyboard",
                "phase_timestamps": {
                    **state.get("phase_timestamps", {}),
                    "image_generator_completed": utc_now_iso(),
                },
            }

            logger.info(
                f"Image generation completed: {len(generated_images)} images in "
                f"{validated_output.total_generation_time_ms}ms"
            )

            # Monitoring: record aggregated image generation usage
            try:
                from app.services.monitoring import get_monitoring_service
                # Estimate tokens from prompts and text responses
                def est_tok(s: str) -> int:
                    try:
                        return max(0, int(len(s) / 4))
                    except Exception:
                        return 0
                input_tokens = sum(est_tok(p) for p in prompts)
                output_tokens = 0
                num_images = len(generated_images)
                duration_sec = float(validated_output.total_generation_time_ms) / 1000.0
                await get_monitoring_service().record_image_usage(
                    video_id=workflow_id,
                    model=config.model.value,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    num_images=num_images,
                    duration_seconds=duration_sec,
                    success=True,
                    metadata={"role": "master_style_frame", "estimated": True},
                )
            except Exception as me:
                logger.warning(f"Monitoring image usage failed: {me}")

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
                "character",
                "person",
                "player",
                "man",
                "woman",
                "child",
                "figure",
                "protagonist",
                "character",
                "individual",
                "subject",
                "moses",
                "pharaoh",
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
                path=full_path, file=image_bytes, file_options={"content-type": "image/png"}
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
            all_images.append(
                WorkflowImage(
                    url=user_reference_url,
                    source=ImageSource.USER_REFERENCE,
                    description="User-provided reference image",
                    is_style_reference=True,
                )
            )

        for i, url in enumerate(research_images[:2]):
            all_images.append(
                WorkflowImage(
                    url=url,
                    source=ImageSource.RESEARCH,
                    description=f"Research image {i + 1}",
                    is_style_reference=False,
                )
            )

        for img in generated_images:
            all_images.append(
                WorkflowImage(
                    url=img.url,
                    source=ImageSource.GENERATED,
                    scene_number=img.scene_number,
                    description=f"Generated image for scene {img.scene_number}",
                    is_style_reference=False,
                )
            )

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
            self.supabase.table("workflows").update(
                {
                    "generated_images": {
                        "images": [img.model_dump(mode="json") for img in output.generated_images],
                        "total_count": output.total_images_generated,
                        "generation_time_ms": output.total_generation_time_ms,
                        "model_used": output.model_used.value
                        if hasattr(output.model_used, "value")
                        else str(output.model_used),
                        "all_image_urls": output.all_image_urls,  # Store within generated_images JSON
                    },
                    "updated_at": utc_now_iso(),
                }
            ).eq("id", workflow_id).execute()

            for img in output.generated_images:
                self.supabase.table("media").insert(
                    {
                        "workflow_id": workflow_id,
                        "media_type": "image",  # Allowed: image, video, audio
                        "source": "generated",  # Allowed: user_upload, research, generated
                        "role": getattr(img, "role", None) or "generated",
                        "storage_url": img.url,
                        "storage_path": img.storage_path,
                        "metadata": {
                            "scene_number": img.scene_number,
                            "prompt": img.prompt[:500],
                            "model_used": img.model_used.value,
                            "aspect_ratio": img.aspect_ratio.value,
                            "resolution": img.resolution.value,
                            "role": getattr(img, "role", None) or "generated",
                        },
                    }
                ).execute()

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
