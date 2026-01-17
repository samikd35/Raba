"""RABA Tool and Intent Models.

Pydantic models for Intent/Tool Selector Agent output schemas.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.workflow import AspectRatioEnum, CategoryEnum, ResolutionEnum


class IntentType(str, Enum):
    """Video intent classification."""
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    INSPIRATIONAL = "inspirational"
    TUTORIAL = "tutorial"


class ToneType(str, Enum):
    """Video tone for engagement optimization."""
    SERIOUS = "serious"
    HUMOROUS = "humorous"
    DRAMATIC = "dramatic"
    CASUAL = "casual"


class TargetAudience(str, Enum):
    """Target audience classification."""
    GENERAL = "general"
    TECH = "tech"
    SCIENCE = "science"
    BUSINESS = "business"


class UserReferenceMode(str, Enum):
    """Whether user provided a reference image upfront."""
    NO_REFERENCE = "no_reference"
    WITH_REFERENCE = "with_reference"


class ToolCapabilities(BaseModel):
    """Capabilities a video generation tool supports."""
    
    flow_visualization: bool = Field(
        default=False,
        description="Supports visualizing flows, forces, fields"
    )
    invisible_forces: bool = Field(
        default=False,
        description="Can render invisible phenomena visually"
    )
    photorealistic_grounding: bool = Field(
        default=False,
        description="Maintains photorealistic base aesthetics"
    )
    philosophical_debates: bool = Field(
        default=False,
        description="Suited for abstract philosophical content"
    )
    sakuga_style: bool = Field(
        default=False,
        description="High-energy anime sakuga animation style"
    )
    calligraphic_combat: bool = Field(
        default=False,
        description="Ink-splash, calligraphic visual effects"
    )
    miniature_worlds: bool = Field(
        default=False,
        description="Creates miniature diorama-style visuals"
    )
    data_visualization: bool = Field(
        default=False,
        description="Transforms data into visual landscapes"
    )
    viral_signal: str = Field(
        default="",
        description="Primary viral engagement signal"
    )


class ToolMetadata(BaseModel):
    """Metadata for a video generation tool."""
    
    tool_id: str = Field(
        ...,
        description="Unique tool identifier"
    )
    tool_name: str = Field(
        ...,
        description="Human-readable tool name"
    )
    category: CategoryEnum = Field(
        ...,
        description="Tool category (surreal_realism, high_octane_anime, stylized_3d)"
    )
    description: str = Field(
        ...,
        description="Detailed description of tool's visual style and use cases"
    )
    capabilities: ToolCapabilities = Field(
        default_factory=ToolCapabilities,
        description="Tool capability flags"
    )
    supported_aspect_ratios: list[str] = Field(
        default=["9:16", "16:9"],
        description="Supported video aspect ratios"
    )
    supported_resolutions: list[str] = Field(
        default=["720p", "1080p"],
        description="Supported video resolutions"
    )
    max_duration_seconds: int = Field(
        default=60,
        ge=8,
        le=60,
        description="Maximum video duration this tool supports"
    )
    cost_per_request: float = Field(
        default=0.5,
        ge=0,
        description="Estimated cost per generation in USD"
    )
    estimated_quality: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Quality score (0-1)"
    )
    script_prompt_template: Optional[str] = Field(
        default=None,
        description="Template for script generation prompts"
    )
    video_prompt_template: Optional[str] = Field(
        default=None,
        description="Template for video generation prompts"
    )
    image_prompt_template: Optional[str] = Field(
        default=None,
        description="Template for image generation prompts"
    )
    example_topics: list[str] = Field(
        default_factory=list,
        description="Example topics this tool excels at"
    )


class ValidatedParams(BaseModel):
    """Validated and normalized video generation parameters."""
    
    duration_seconds: int = Field(
        ...,
        ge=8,
        le=60,
        description="Validated video duration (8-60 seconds)"
    )
    aspect_ratio: AspectRatioEnum = Field(
        ...,
        description="Validated aspect ratio"
    )
    resolution: ResolutionEnum = Field(
        ...,
        description="Validated resolution"
    )
    user_reference_mode: UserReferenceMode = Field(
        default=UserReferenceMode.NO_REFERENCE,
        description="Whether user provided a reference image"
    )


class IntentMetadata(BaseModel):
    """Extracted intent information from user topic."""
    
    topic: str = Field(
        ...,
        description="Cleaned and normalized topic"
    )
    intent_type: IntentType = Field(
        ...,
        description="Classified intent type"
    )
    target_audience: TargetAudience = Field(
        ...,
        description="Inferred target audience"
    )
    tone: ToneType = Field(
        ...,
        description="Optimal tone for viral engagement"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Key terms extracted for tool matching"
    )
    complexity_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Topic complexity score (0=simple, 1=complex)"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="LLM reasoning for classifications"
    )


class IntentToolOutput(BaseModel):
    """
    Complete output from Intent/Tool Selector Agent.
    
    This is the main output schema passed to downstream agents.
    """
    
    topic: str = Field(
        ...,
        description="Original user topic"
    )
    intent_metadata: IntentMetadata = Field(
        ...,
        description="Extracted intent information"
    )
    validated_params: ValidatedParams = Field(
        ...,
        description="Validated generation parameters"
    )
    selected_tool: ToolMetadata = Field(
        ...,
        description="Selected video generation tool"
    )
    tool_execution_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific execution parameters"
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Overall confidence in selection (0-1)"
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback tool was used"
    )
    selection_reasoning: Optional[str] = Field(
        default=None,
        description="Reasoning for tool selection"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within bounds."""
        return max(0.0, min(1.0, v))


class ToolScore(BaseModel):
    """Scoring result for a tool."""
    
    tool_id: str = Field(..., description="Tool identifier")
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Semantic relevance to topic (0-1)"
    )
    capability_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Capability match score (0-1)"
    )
    cost_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Cost efficiency score (0-1, higher=cheaper)"
    )
    recency_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Recent success rate (0-1)"
    )
    total_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Weighted total score"
    )
    
    @classmethod
    def calculate_total(
        cls,
        relevance: float,
        capability: float,
        cost: float,
        recency: float = 0.5
    ) -> float:
        """
        Calculate total score using weighted formula.
        
        Formula: 0.4*relevance + 0.3*capability + 0.2*cost + 0.1*recency
        """
        return (
            relevance * 0.4 +
            capability * 0.3 +
            cost * 0.2 +
            recency * 0.1
        )


class IntentExtractionRequest(BaseModel):
    """Request schema for LLM intent extraction."""
    
    topic: str = Field(..., description="User's video topic")
    duration_seconds: int = Field(default=18, description="Requested duration")
    category_preference: str = Field(default="auto", description="Category preference")


class IntentExtractionResponse(BaseModel):
    """Response schema from LLM intent extraction."""
    
    intent_type: IntentType = Field(
        ...,
        description="The primary intent type (educational, entertainment, inspirational, tutorial)"
    )
    target_audience: TargetAudience = Field(
        ...,
        description="The target audience (general, tech, science, business)"
    )
    tone: ToneType = Field(
        ...,
        description="The optimal tone for viral engagement (serious, humorous, dramatic, casual)"
    )
    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="3-7 key terms for tool matching"
    )
    complexity_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Topic complexity (0=simple, 1=complex)"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of classifications"
    )


class ToolRelevanceRequest(BaseModel):
    """Request schema for LLM tool relevance scoring."""
    
    tool_name: str = Field(..., description="Name of the tool")
    tool_description: str = Field(..., description="Tool description")
    tool_capabilities: str = Field(..., description="Comma-separated capabilities")
    topic: str = Field(..., description="User's topic")
    intent_type: str = Field(..., description="Classified intent type")
    keywords: list[str] = Field(..., description="Extracted keywords")


class ToolRelevanceResponse(BaseModel):
    """Response schema from LLM tool relevance scoring."""
    
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Relevance score from 0.0 to 1.0"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the score"
    )


# =============================================================================
# Phase 2.2: Tool Repository System Models
# =============================================================================

class ToolCreate(BaseModel):
    """
    Request schema for creating a new tool.
    
    User provides a simple idea and optional hints.
    Gemini 2.5 Flash will enhance this into a full tool structure.
    """
    
    tool_name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Display name for the tool"
    )
    idea: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Description of what this tool should do and its visual style"
    )
    category: Optional[CategoryEnum] = Field(
        default=None,
        description="Optional category hint. If not provided, AI will classify."
    )


class ToolUpdate(BaseModel):
    """
    Request schema for updating an existing tool.
    
    All fields are optional - only provided fields will be updated.
    If 'idea' is changed, tool will be re-enhanced by Gemini.
    """
    
    tool_name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Updated display name"
    )
    idea: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=2000,
        description="Updated idea - will trigger re-enhancement"
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated description (manual override)"
    )
    capabilities: Optional[ToolCapabilities] = Field(
        default=None,
        description="Updated capabilities"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Enable/disable tool"
    )
    script_prompt_template: Optional[str] = Field(
        default=None,
        description="Updated script prompt template"
    )
    image_prompt_template: Optional[str] = Field(
        default=None,
        description="Updated image prompt template"
    )
    video_prompt_template: Optional[str] = Field(
        default=None,
        description="Updated video prompt template"
    )
    priority: Optional[int] = Field(
        default=None,
        ge=0,
        le=1000,
        description="Selection priority (higher = preferred)"
    )


class ToolImproveRequest(BaseModel):
    """
    Request schema for improving an existing tool.
    
    User provides feedback/suggestions, and Gemini will
    enhance the tool while preserving what works.
    """
    
    improvement_suggestion: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="What should be improved about this tool"
    )
    preserve_templates: bool = Field(
        default=False,
        description="If true, keep existing prompt templates and only update description/capabilities"
    )


class ImprovementRecord(BaseModel):
    """Record of a tool improvement."""
    
    timestamp: str = Field(..., description="ISO timestamp of improvement")
    previous_version: int = Field(..., description="Version before improvement")
    suggestion: str = Field(..., description="User's improvement suggestion")
    changes_made: str = Field(..., description="Summary of changes applied")


class ToolEnhancementResponse(BaseModel):
    """
    Response schema from Gemini tool enhancement.
    
    This is what Gemini returns when enhancing a tool idea.
    """
    
    tool_id: str = Field(
        ...,
        description="Generated unique slug identifier (lowercase, underscores)"
    )
    tool_name: str = Field(
        ...,
        description="Polished display name"
    )
    category: CategoryEnum = Field(
        ...,
        description="Classified category"
    )
    description: str = Field(
        ...,
        description="Enhanced description (2-3 sentences)"
    )
    capabilities: ToolCapabilities = Field(
        ...,
        description="Generated capability flags"
    )
    script_prompt_template: str = Field(
        ...,
        description="Template for script generation with {topic}, {tone}, {duration} placeholders"
    )
    image_prompt_template: str = Field(
        ...,
        description="Template for image generation with {scene_description}, {style} placeholders"
    )
    video_prompt_template: str = Field(
        ...,
        description="Template for video generation with {script}, {duration} placeholders"
    )
    parameters_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for tool parameters"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of design choices"
    )


class ToolResponse(BaseModel):
    """
    Full tool response for API endpoints.
    
    Includes all tool data from database.
    """
    
    id: str = Field(..., description="Database UUID")
    tool_id: str = Field(..., description="Unique slug identifier")
    tool_name: str = Field(..., description="Display name")
    category: str = Field(..., description="Visual style category")
    description: Optional[str] = Field(default=None, description="Tool description")
    capabilities: Optional[dict[str, Any]] = Field(default=None, description="Capability flags")
    script_prompt_template: Optional[str] = Field(default=None, description="Script prompt template")
    image_prompt_template: Optional[str] = Field(default=None, description="Image prompt template")
    video_prompt_template: Optional[str] = Field(default=None, description="Video prompt template")
    parameters_schema: Optional[dict[str, Any]] = Field(default=None, description="Parameters JSON Schema")
    original_idea: Optional[str] = Field(default=None, description="Original user idea")
    is_active: bool = Field(default=True, description="Whether tool is available")
    priority: int = Field(default=0, description="Selection priority")
    version: int = Field(default=1, description="Tool version")
    usage_count: int = Field(default=0, description="Times used")
    success_rate: float = Field(default=0.0, description="Success rate 0-1")
    improvement_history: Optional[list[dict[str, Any]]] = Field(default=None, description="Improvement records")
    created_by: Optional[str] = Field(default=None, description="Creator UUID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_improved_at: Optional[str] = Field(default=None, description="Last improvement timestamp")

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Paginated list of tools."""
    
    tools: list[ToolResponse] = Field(..., description="List of tools")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


# =============================================================================
# Phase 2: Prompt Management System Models
# =============================================================================

class PromptUpdateType(str, Enum):
    ALL = "all"
    SCRIPT_ONLY = "script_only"
    IMAGE_ONLY = "image_only"
    VIDEO_ONLY = "video_only"
    SCRIPT_AND_IMAGE = "script_and_image"
    SCRIPT_AND_VIDEO = "script_and_video"
    IMAGE_AND_VIDEO = "image_and_video"


class PromptTemplates(BaseModel):
    script_prompt_template: Optional[str] = None
    image_prompt_template: Optional[str] = None
    video_prompt_template: Optional[str] = None


class PromptBulkUpdateRequest(BaseModel):
    tool_ids: Optional[list[str]] = Field(default=None, description="Tool IDs to update. Ignored when update_type is 'all'")
    update_type: PromptUpdateType = Field(..., description="Which templates to update. Use 'all' to update all tools in database")
    improvement_reason: Optional[str] = Field(default="System-wide prompt quality improvement to match latest standards", description="Reason for bulk improvement")
    prompts: Optional[PromptTemplates] = Field(default=None, description="Templates to apply when not using AI enhancement")
    use_ai_enhancement: bool = Field(default=True, description="Use Gemini to enhance prompts based on tool context. Must be True when update_type is 'all'")


class PromptBulkUpdateResponse(BaseModel):
    updated_count: int
    failed_updates: list[dict[str, Any]]
    updated_tools: list[ToolResponse]
    improvement_summary: Optional[str] = None
    details: list[dict[str, Any]] = Field(default_factory=list, description="Per-tool processing details")


class ToolPromptUpdateRequest(BaseModel):
    update_type: PromptUpdateType = Field(..., description="Which templates to update")
    improvement_reason: str = Field(..., description="Reason for improvement")
    prompts: Optional[PromptTemplates] = Field(default=None, description="Templates to apply when not using AI enhancement")
    use_ai_enhancement: bool = Field(default=False)


class ToolPromptUpdateResponse(BaseModel):
    tool_id: str
    updated_templates: dict[str, bool]
    improvement_summary: Optional[str] = None
    new_version: int


class ToolExecutionRequest(BaseModel):
    """Request schema for executing a tool with a topic."""
    
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Topic to generate prompts for"
    )
    parameters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Tool-specific parameters (validated against tool's parameters_schema)"
    )


class ToolPrompts(BaseModel):
    """Generated prompts from tool execution."""
    
    script_prompt: str = Field(..., description="Prompt for script generation")
    image_prompt: str = Field(..., description="Prompt for image generation")
    video_prompt: str = Field(..., description="Prompt for video generation")


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    
    tool_id: str = Field(..., description="Executed tool ID")
    topic: str = Field(..., description="Topic used")
    generated_prompts: ToolPrompts = Field(..., description="Generated prompts")
    estimated_generation_time: float = Field(..., description="Estimated time in seconds")


class DeleteResponse(BaseModel):
    """Response for delete operations."""
    
    success: bool = Field(..., description="Whether deletion succeeded")
    tool_id: str = Field(..., description="Deleted tool ID")
