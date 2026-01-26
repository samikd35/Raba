"""Global Style Anchor Agent.

Extracts consistent visual anchors (palette, materials, motion language,
lighting, camera/framing) from topic + intent + selected tool + script.
Used to maintain cross-scene consistency for all content types, including
data/educational videos and realistic styles.
"""

from typing import Any

from pydantic import BaseModel, Field
from app.graph.state import VideoGenerationState
from app.utils.logging import get_logger
from app.services.gemini import get_gemini_service, GEMINI_3_FLASH

logger = get_logger(__name__)


class GlobalStyleAnchorOutput(BaseModel):
    """Output model for global style anchor extraction."""
    color_palette: list[str] = Field(default_factory=list, description="Color palette (4-6 colors)")
    materials: list[str] = Field(default_factory=list, description="Material descriptions")
    motion_language: list[str] = Field(default_factory=list, description="Camera motion descriptions")
    lighting: str = Field(default="", description="Lighting description")
    camera: str = Field(default="", description="Camera/framing description")
    texture: str = Field(default="", description="Texture description")
    style_description: str = Field(default="", description="Overall style description")


DEFAULT_ANCHORS = {
    "surreal_realism": {
        "color_palette": ["neutral whites", "soft grays", "deep blacks", "neon accents", "golden rims"],
        "materials": ["liquid glass", "polished metal", "water", "smoke/mist"],
        "motion_language": ["macro dolly", "slow push-in", "gentle orbit"],
        "lighting": "soft volumetric lighting with realistic falloff and subtle rim highlights",
        "camera": "cinematic lenses, shallow depth of field, real-world exposure",
        "texture": "photorealistic textures with micro detail",
    },
    "high_octane_anime": {
        "color_palette": ["electric blues", "deep crimson", "ink black", "neon magenta"],
        "materials": ["ink brush", "cel-shaded surfaces", "energy effects"],
        "motion_language": ["whip pans", "impact frames", "dynamic tracking", "speed lines"],
        "lighting": "high-contrast dramatic key with colored rim/glow",
        "camera": "dynamic angles (low/high), rapid arcs",
        "texture": "bold line work with stylized fills",
    },
    "stylized_3d": {
        "color_palette": ["soft neutrals", "pastel accents", "clean whites", "warm grays"],
        "materials": ["stylized plastic", "matte surfaces", "wood", "paper"],
        "motion_language": ["steady pans", "orbital rotation", "smooth dolly"],
        "lighting": "studio softboxes / even illumination",
        "camera": "isometric/orthographic-informed framing, clean composition",
        "texture": "minimal grain, clean edges",
    },
}


class GlobalStyleAnchorAgent:
    def __init__(self):
        self.gemini = get_gemini_service()
        logger.info("GlobalStyleAnchorAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        topic = state.get("topic", "")
        tool = state.get("selected_tool") or {}
        category = tool.get("category", state.get("category", "surreal_realism"))
        intent = (state.get("intent_metadata") or {}).get("intent_type", "educational")
        script = state.get("script_output", {})

        # Compose prompt for LLM extraction of anchors
        prompt = (
            "Extract a global style anchor for consistent video visuals. Return JSON with keys: "
            "color_palette (array of 4-6), materials (array), motion_language (array), lighting (string), "
            "camera (string), texture (string), style_description (string). The anchor must be usable across scenes "
            "for this topic/tool/intent. Avoid text overlays.\n\n"
            f"Topic: {topic}\n"
            f"Intent: {intent}\n"
            f"Tool Category: {category}\n"
            f"Selected Tool: {tool.get('tool_name','')}\n"
            f"Script (summary form): {str(script)[:1200]}\n"
        )

        try:
            resp = await self.gemini.generate_structured_output(
                prompt=prompt,
                response_model=GlobalStyleAnchorOutput,
                model=GEMINI_3_FLASH,
                temperature=0.5,
                video_id=state.get("workflow_id"),
            )
            anchors = resp.model_dump() if hasattr(resp, 'model_dump') else (resp if isinstance(resp, dict) else {})
            # Validate minimal keys; fallback to defaults for category
            base = DEFAULT_ANCHORS.get(category, DEFAULT_ANCHORS["surreal_realism"]).copy()
            base.update({k: v for k, v in anchors.items() if v})
            # Enforce optical presets per category (no anamorphic in stylized_3d)
            if category == "stylized_3d":
                base["camera"] = "tilt-shift miniature look, 35mm/50mm lens, shallow depth of field"
            elif category == "surreal_realism":
                base["camera"] = "wide-angle anamorphic 14–24mm, cinematic widescreen"
            elif category == "high_octane_anime":
                base["camera"] = "dynamic long lens 85–200mm, strong compression for action"
            # Build style_description if missing
            if not base.get("style_description"):
                base["style_description"] = (
                    f"Global style anchor for {category}: lighting={base['lighting']}, camera={base['camera']}, "
                    f"texture={base['texture']}, palette={', '.join(base.get('color_palette', [])[:5])}."
                )
            logger.info("Global style anchor extracted via Gemini")
            return {"global_style_anchor": base}
        except Exception as e:
            logger.warning(f"GlobalStyleAnchor fallback used due to error: {e}")
            base = DEFAULT_ANCHORS.get(category, DEFAULT_ANCHORS["surreal_realism"]).copy()
            # Enforce optical presets in fallback as well
            if category == "stylized_3d":
                base["camera"] = "tilt-shift miniature look, 35mm/50mm lens, shallow depth of field"
            elif category == "surreal_realism":
                base["camera"] = "wide-angle anamorphic 14–24mm, cinematic widescreen"
            elif category == "high_octane_anime":
                base["camera"] = "dynamic long lens 85–200mm, strong compression for action"
            base["style_description"] = (
                f"Global style anchor for {category}: lighting={base['lighting']}, camera={base['camera']}, "
                f"texture={base['texture']}, palette={', '.join(base.get('color_palette', [])[:5])}."
            )
            return {"global_style_anchor": base}


async def global_style_anchor_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = GlobalStyleAnchorAgent()
    return await agent.run(state)
