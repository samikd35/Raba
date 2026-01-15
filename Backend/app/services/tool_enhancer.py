"""RABA Tool Enhancement Service.

Uses Gemini 3 Flash to enhance user tool ideas into properly structured tools.
Also handles tool improvement for existing tools.
"""

from typing import Optional

from app.models.tool import (
    ToolCapabilities,
    ToolCreate,
    ToolEnhancementResponse,
    ToolImproveRequest,
    ToolResponse,
)
from app.models.workflow import CategoryEnum
from app.services.gemini import GeminiService, GEMINI_3_FLASH, get_gemini_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

TOOL_ENHANCEMENT_SYSTEM_PROMPT = """You are an expert video generation tool designer for RABA, a system that creates viral YouTube Shorts (8-25 seconds).

Your task is to transform user ideas into properly structured video generation tools with PROFESSIONAL-GRADE prompt templates.

## RABA Visual Categories

1. **surreal_realism**: Photorealistic visuals with impossible/surreal elements. Best for physics, science, nature visualization.
2. **high_octane_anime**: Sakuga-style anime with dynamic action. Best for debates, philosophy, history, dramatic narratives.
3. **stylized_3d**: Stylized 3D graphics and miniatures. Best for data visualization, statistics, comparisons.

## REQUIREMENTS

1. **tool_id**: Unique slug (lowercase, underscores, 3-50 chars). Example: "quantum_flow_visualizer"
2. **category**: Exactly one of: surreal_realism, high_octane_anime, stylized_3d
3. **description**: 2-3 sentences explaining visual style and use cases
4. **capabilities**: Set relevant boolean flags
5. **parameters_schema**: JSON Schema with "tone" and "duration_seconds" properties (include enums with valid values)

## PROMPT TEMPLATE REQUIREMENTS (CRITICAL)

### script_prompt_template
Must include: {topic}, {tone}, {duration}
Write a DETAILED script generation prompt that:
- Opens with a HOOK requirement (first 2-3 seconds must grab attention)
- Specifies the narrative structure and pacing
- Includes VIRAL SIGNAL patterns (pattern interrupts every 3-5 seconds)
- Defines the emotional arc and climax
- Specifies word count guidance (45-60 words for 18-25s videos)
- Include tone-specific direction

### image_prompt_template (for Nano Banana / Gemini Image Generation)
Must include: {scene_description}, {style}
Write a DETAILED keyframe image prompt that includes:
- **Subject**: Specific character/object descriptions with details (clothing, expression, pose)
- **Artistic Style**: Specific art direction (e.g., "sakuga-style anime", "tilt-shift miniature", "liquid-glass photorealism")
- **Lighting**: Specific lighting direction (e.g., "dramatic rim lighting", "soft diffused daylight", "neon glow")
- **Color Palette**: Define the color scheme
- **Composition**: Camera framing guidance (close-up, wide shot, etc.)
- **Technical specs**: Include "high detail", "8K resolution", "cinematic composition"
- **Atmosphere**: Mood and ambiance descriptors

### video_prompt_template (for Veo Video Generation)
Must include: {script}, {duration}
Write a DETAILED video generation prompt that specifies:
- **Camera Movement**: Specific movements (dolly in, pan left, crane shot, arc shot, static, handheld)
- **Camera Angle**: Shot types (eye-level, low-angle, bird's-eye, Dutch angle)
- **Pacing/Temporal**: Speed and rhythm (slow-motion, time-lapse, fast cuts)
- **Transitions**: How scenes connect
- **Visual Effects**: Motion effects, particle systems, light rays
- **Lens Effects**: Depth of field, lens flare, rack focus
- **Audio Direction**: Sound effects, ambient noise, music style
- **Consistency**: Maintain character/style consistency across frames

## TEMPLATE LENGTH
Each template should be 150-300 words. Be hyper-specific - vague prompts produce generic results.

## EXAMPLE QUALITY (Image Template)
BAD: "Epic anime style, {scene_description}, dramatic lighting"
GOOD: "Dynamic sakuga-style anime keyframe depicting {scene_description}. Art direction: Bold ink-black outlines, speed lines radiating from action focal point, calligraphic splash effects on impacts. {style} aesthetic influence. Lighting: High-contrast dramatic side lighting with deep shadows and vibrant highlight pops. Color palette: Saturated primary colors (deep crimson, electric blue) against ink-black shadows. Composition: Dynamic diagonal lines, character positioned using rule of thirds, clear visual hierarchy. Include motion blur on fast elements. Cinematic 16:9 aspect ratio, 8K resolution quality."

Be creative but practical. Focus on viral engagement potential."""


TOOL_IMPROVEMENT_SYSTEM_PROMPT = """You are an expert at improving video generation tools for RABA (viral YouTube Shorts, 8-25 seconds).

Given an existing tool and user feedback, improve the tool following these guidelines:

## IMPROVEMENT PRINCIPLES
1. Preserve what already works well
2. Address the user's specific suggestions
3. Maintain valid prompt template placeholders
4. Keep the same category unless explicitly asked to change

## TEMPLATE QUALITY STANDARDS

### script_prompt_template (placeholders: {topic}, {tone}, {duration})
- Must specify HOOK requirement for first 2-3 seconds
- Include viral signal patterns (pattern interrupts every 3-5 seconds)
- Define narrative structure, emotional arc, and word count guidance (45-60 words)

### image_prompt_template (placeholders: {scene_description}, {style})
Must be detailed with:
- Subject specifics (character details, clothing, expression, pose)
- Artistic style direction (sakuga, tilt-shift, liquid-glass, etc.)
- Lighting (rim lighting, diffused daylight, neon glow)
- Color palette definition
- Composition/framing guidance
- Technical specs (8K, cinematic composition)

### video_prompt_template (placeholders: {script}, {duration})
Must specify:
- Camera movements (dolly, pan, crane, arc, static, handheld)
- Camera angles (eye-level, low-angle, bird's-eye, Dutch angle)
- Pacing/temporal (slow-motion, time-lapse, rhythm)
- Visual effects and lens effects
- Audio direction (sound effects, ambient, music style)

Each template should be 150-300 words. Be hyper-specific - vague prompts produce generic results.

Return the improved tool configuration."""


class ToolEnhancerService:
    """
    Service for AI-enhanced tool creation and improvement.
    
    Uses Gemini 3 Flash to transform user ideas into structured tools,
    and to improve existing tools based on feedback.
    """
    
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        """
        Initialize the tool enhancer service.
        
        Args:
            gemini_service: Optional Gemini service instance. If None, uses singleton.
        """
        self._gemini = gemini_service or get_gemini_service()
    
    async def enhance_tool_idea(
        self,
        request: ToolCreate,
    ) -> ToolEnhancementResponse:
        """
        Enhance a user's tool idea into a full tool structure.
        
        Args:
            request: Tool creation request with name, idea, and optional category hint
            
        Returns:
            Enhanced tool configuration from Gemini
        """
        logger.info(f"Enhancing tool idea: {request.tool_name}")
        
        # Build the prompt
        category_hint = ""
        if request.category:
            category_hint = f"\nCategory hint from user: {request.category.value}"
        
        prompt = f"""Create a video generation tool based on this user idea:

Tool Name: {request.tool_name}
User's Idea: {request.idea}{category_hint}

Generate a complete tool configuration following the schema requirements."""

        # Call Gemini with structured output
        response = await self._gemini.generate_structured_output(
            prompt=prompt,
            response_model=ToolEnhancementResponse,
            model=GEMINI_3_FLASH,
            system_instruction=TOOL_ENHANCEMENT_SYSTEM_PROMPT,
        )
        
        # Ensure tool_id is properly formatted
        response.tool_id = self._sanitize_tool_id(response.tool_id)
        
        logger.info(f"Enhanced tool: {response.tool_id} -> {response.category}")
        return response
    
    async def improve_tool(
        self,
        existing_tool: ToolResponse,
        request: ToolImproveRequest,
    ) -> ToolEnhancementResponse:
        """
        Improve an existing tool based on user feedback.
        
        Args:
            existing_tool: The current tool configuration
            request: Improvement request with suggestions
            
        Returns:
            Improved tool configuration
        """
        logger.info(f"Improving tool: {existing_tool.tool_id}")
        
        # Build context about existing tool
        existing_context = f"""EXISTING TOOL:
- ID: {existing_tool.tool_id}
- Name: {existing_tool.tool_name}
- Category: {existing_tool.category}
- Description: {existing_tool.description}
- Capabilities: {existing_tool.capabilities}
"""
        
        if not request.preserve_templates:
            existing_context += f"""- Script Template: {existing_tool.script_prompt_template}
- Image Template: {existing_tool.image_prompt_template}
- Video Template: {existing_tool.video_prompt_template}
"""
        else:
            existing_context += "\n(User wants to preserve existing prompt templates)"
        
        prompt = f"""{existing_context}

USER'S IMPROVEMENT SUGGESTION:
{request.improvement_suggestion}

Generate an improved version of this tool. Keep the same tool_id."""

        # Call Gemini
        response = await self._gemini.generate_structured_output(
            prompt=prompt,
            response_model=ToolEnhancementResponse,
            model=GEMINI_3_FLASH,
            system_instruction=TOOL_IMPROVEMENT_SYSTEM_PROMPT,
        )
        
        # Keep the original tool_id
        response.tool_id = existing_tool.tool_id
        
        # If preserving templates, restore originals
        if request.preserve_templates:
            if existing_tool.script_prompt_template:
                response.script_prompt_template = existing_tool.script_prompt_template
            if existing_tool.image_prompt_template:
                response.image_prompt_template = existing_tool.image_prompt_template
            if existing_tool.video_prompt_template:
                response.video_prompt_template = existing_tool.video_prompt_template
        
        logger.info(f"Improved tool: {response.tool_id}")
        return response
    
    def _sanitize_tool_id(self, tool_id: str) -> str:
        """
        Sanitize tool_id to be a valid slug.
        
        - Lowercase
        - Replace spaces/dashes with underscores
        - Remove invalid characters
        - Limit length to 50 chars
        """
        import re
        
        # Lowercase and replace spaces/dashes
        sanitized = tool_id.lower().replace(" ", "_").replace("-", "_")
        
        # Remove invalid characters (keep only alphanumeric and underscore)
        sanitized = re.sub(r"[^a-z0-9_]", "", sanitized)
        
        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip("_")
        
        # Ensure minimum length
        if len(sanitized) < 3:
            sanitized = f"tool_{sanitized}"
        
        return sanitized


# Singleton instance
_tool_enhancer: Optional[ToolEnhancerService] = None


def get_tool_enhancer() -> ToolEnhancerService:
    """Get singleton tool enhancer service instance."""
    global _tool_enhancer
    if _tool_enhancer is None:
        _tool_enhancer = ToolEnhancerService()
    return _tool_enhancer
