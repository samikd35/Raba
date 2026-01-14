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
        default=25,
        ge=8,
        le=25,
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
        le=25,
        description="Validated video duration (8-25 seconds)"
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
