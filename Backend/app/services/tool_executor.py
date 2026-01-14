"""RABA Tool Executor Service.

Executes tools by rendering prompt templates with user-provided topics and parameters.
"""

import re
from typing import Any, Optional

from app.models.tool import (
    ToolExecutionRequest,
    ToolExecutionResponse,
    ToolPrompts,
    ToolResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ToolExecutionError(Exception):
    """Error during tool execution."""
    pass


class TemplateRenderError(ToolExecutionError):
    """Error rendering a prompt template."""
    pass


class ParameterValidationError(ToolExecutionError):
    """Error validating execution parameters."""
    pass


class ToolExecutor:
    """
    Executes tools by rendering prompt templates.
    
    Takes a tool configuration and user request, then produces
    ready-to-use prompts for script, image, and video generation.
    """
    
    def __init__(self):
        """Initialize tool executor."""
        self._logger = get_logger(f"{__name__}.ToolExecutor")
    
    async def execute(
        self,
        tool: ToolResponse,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResponse:
        """
        Execute a tool with the given topic and parameters.
        
        Args:
            tool: Tool configuration
            request: Execution request with topic and parameters
            
        Returns:
            Execution response with generated prompts
            
        Raises:
            ToolExecutionError: If execution fails
        """
        self._logger.info(f"Executing tool: {tool.tool_id} for topic: {request.topic[:50]}...")
        
        # Validate parameters against schema
        if tool.parameters_schema and request.parameters:
            self._validate_parameters(request.parameters, tool.parameters_schema)
        
        # Build context for template rendering
        context = self._build_context(tool, request)
        
        # Render prompts
        prompts = self._render_prompts(tool, context)
        
        # Estimate generation time based on tool
        estimated_time = self._estimate_generation_time(tool, request)
        
        self._logger.info(f"Tool executed successfully: {tool.tool_id}")
        
        return ToolExecutionResponse(
            tool_id=tool.tool_id,
            topic=request.topic,
            generated_prompts=prompts,
            estimated_generation_time=estimated_time,
        )
    
    def _build_context(
        self,
        tool: ToolResponse,
        request: ToolExecutionRequest,
    ) -> dict[str, Any]:
        """
        Build context dictionary for template rendering.
        
        Args:
            tool: Tool configuration
            request: Execution request
            
        Returns:
            Context dictionary with all template variables
        """
        # Default parameters
        context = {
            "topic": request.topic,
            "tone": "engaging",
            "duration": 18,
            "duration_seconds": 18,
            "style": tool.category,
            "tool_name": tool.tool_name,
            "category": tool.category,
        }
        
        # Override with user-provided parameters
        if request.parameters:
            context.update(request.parameters)
            
            # Ensure duration is set in both formats
            if "duration_seconds" in request.parameters:
                context["duration"] = request.parameters["duration_seconds"]
            elif "duration" in request.parameters:
                context["duration_seconds"] = request.parameters["duration"]
        
        # Add scene description placeholder (can be overridden later)
        if "scene_description" not in context:
            context["scene_description"] = f"A scene about {request.topic}"
        
        # Add script placeholder (for video template)
        if "script" not in context:
            context["script"] = f"Script for {request.topic}"
        
        return context
    
    def _render_prompts(
        self,
        tool: ToolResponse,
        context: dict[str, Any],
    ) -> ToolPrompts:
        """
        Render all prompt templates with context.
        
        Args:
            tool: Tool with templates
            context: Context dictionary
            
        Returns:
            Rendered prompts
        """
        # Render each template
        script_prompt = self._render_template(
            tool.script_prompt_template or self._default_script_template(),
            context,
            "script",
        )
        
        image_prompt = self._render_template(
            tool.image_prompt_template or self._default_image_template(),
            context,
            "image",
        )
        
        video_prompt = self._render_template(
            tool.video_prompt_template or self._default_video_template(),
            context,
            "video",
        )
        
        return ToolPrompts(
            script_prompt=script_prompt,
            image_prompt=image_prompt,
            video_prompt=video_prompt,
        )
    
    def _render_template(
        self,
        template: str,
        context: dict[str, Any],
        template_name: str,
    ) -> str:
        """
        Render a single template with context.
        
        Handles missing placeholders gracefully by leaving them as-is
        or using defaults.
        
        Args:
            template: Template string with {placeholders}
            context: Context dictionary
            template_name: Name for error messages
            
        Returns:
            Rendered template string
        """
        try:
            # Find all placeholders in template
            placeholders = re.findall(r"\{(\w+)\}", template)
            
            # Build safe context with defaults for missing keys
            safe_context = {}
            for placeholder in placeholders:
                if placeholder in context:
                    safe_context[placeholder] = context[placeholder]
                else:
                    # Use placeholder name as default
                    safe_context[placeholder] = f"[{placeholder}]"
                    self._logger.warning(
                        f"Missing placeholder '{placeholder}' in {template_name} template"
                    )
            
            # Render template
            rendered = template.format(**safe_context)
            return rendered
            
        except Exception as e:
            self._logger.error(f"Failed to render {template_name} template: {e}")
            raise TemplateRenderError(f"Failed to render {template_name} template: {e}")
    
    def _validate_parameters(
        self,
        parameters: dict[str, Any],
        schema: dict[str, Any],
    ) -> None:
        """
        Validate parameters against JSON schema.
        
        Basic validation - checks types and constraints.
        
        Args:
            parameters: User-provided parameters
            schema: JSON Schema from tool
            
        Raises:
            ParameterValidationError: If validation fails
        """
        properties = schema.get("properties", {})
        
        for key, value in parameters.items():
            if key not in properties:
                # Allow extra parameters
                continue
            
            prop_schema = properties[key]
            prop_type = prop_schema.get("type")
            
            # Type validation
            if prop_type == "integer" and not isinstance(value, int):
                raise ParameterValidationError(
                    f"Parameter '{key}' must be an integer"
                )
            elif prop_type == "string" and not isinstance(value, str):
                raise ParameterValidationError(
                    f"Parameter '{key}' must be a string"
                )
            elif prop_type == "boolean" and not isinstance(value, bool):
                raise ParameterValidationError(
                    f"Parameter '{key}' must be a boolean"
                )
            
            # Range validation for integers
            if prop_type == "integer":
                minimum = prop_schema.get("minimum")
                maximum = prop_schema.get("maximum")
                if minimum is not None and value < minimum:
                    raise ParameterValidationError(
                        f"Parameter '{key}' must be >= {minimum}"
                    )
                if maximum is not None and value > maximum:
                    raise ParameterValidationError(
                        f"Parameter '{key}' must be <= {maximum}"
                    )
            
            # Enum validation
            if "enum" in prop_schema and value not in prop_schema["enum"]:
                raise ParameterValidationError(
                    f"Parameter '{key}' must be one of: {prop_schema['enum']}"
                )
    
    def _estimate_generation_time(
        self,
        tool: ToolResponse,
        request: ToolExecutionRequest,
    ) -> float:
        """
        Estimate total generation time in seconds.
        
        Based on typical times for each step:
        - Script generation: ~10s
        - Image generation: ~15s per image (assume 3 images)
        - Video generation: ~60s per 8s segment
        
        Args:
            tool: Tool configuration
            request: Execution request
            
        Returns:
            Estimated time in seconds
        """
        duration = 18
        if request.parameters and "duration_seconds" in request.parameters:
            duration = request.parameters["duration_seconds"]
        
        # Calculate segments (8s max per segment)
        segments = (duration + 7) // 8
        
        # Estimate times
        script_time = 10.0
        image_time = 45.0  # 3 images * 15s
        video_time = 60.0 * segments
        
        return script_time + image_time + video_time
    
    def _default_script_template(self) -> str:
        """Default script prompt template."""
        return """Create a viral YouTube Shorts script about: {topic}

Tone: {tone}
Duration: {duration} seconds

Requirements:
- Strong hook in first 2 seconds
- Pattern interrupts every 3-5 seconds
- Clear call-to-action at end
- Engaging and shareable content"""
    
    def _default_image_template(self) -> str:
        """Default image prompt template."""
        return """Generate a reference image for: {scene_description}

Style: {style}
Category: {category}

Requirements:
- High quality, detailed
- Suitable for video generation
- Visually engaging"""
    
    def _default_video_template(self) -> str:
        """Default video prompt template."""
        return """Create a {duration} second video based on:

Script: {script}

Style: {style}
Category: {category}

Requirements:
- Follow script timing
- Maintain visual consistency
- Include audio and dialogue"""


# Singleton instance
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get singleton tool executor instance."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
