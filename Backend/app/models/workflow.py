"""RABA Workflow Models.

Pydantic models for workflow input, output, and status.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class WorkflowStatus(str, Enum):
    """Workflow status enum."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_TOOL_APPROVAL = "awaiting_tool_approval"
    AWAITING_RESEARCH_APPROVAL = "awaiting_research_approval"
    AWAITING_SCRIPT_APPROVAL = "awaiting_script_approval"
    AWAITING_IMAGE_APPROVAL = "awaiting_image_approval"
    AWAITING_VIDEO_APPROVAL = "awaiting_video_approval"
    RESEARCH_COMPLETE = "research_complete"
    SCRIPT_COMPLETE = "script_complete"
    IMAGE_COMPLETE = "image_complete"
    COMPLETED = "completed"
    FAILED = "failed"


class CategoryEnum(str, Enum):
    """Video category/style enum - simplified parent categories.

    New simplified categories (recommended):
    - realistic: Live-action, photorealistic, documentary styles
    - anime: 2D animated, anime-inspired styles (any energy level)
    - animation: 3D animated, motion graphics, stylized visuals

    Legacy categories (deprecated, mapped to new):
    - surreal_realism → realistic
    - high_octane_anime → anime
    - stylized_3d → animation
    """

    AUTO = "auto"
    # New simplified categories
    REALISTIC = "realistic"
    ANIME = "anime"
    ANIMATION = "animation"
    # Legacy categories (deprecated but supported for backward compatibility)
    SURREAL_REALISM = "surreal_realism"
    HIGH_OCTANE_ANIME = "high_octane_anime"
    STYLIZED_3D = "stylized_3d"

    @classmethod
    def normalize(cls, value: str) -> "CategoryEnum":
        """Normalize legacy category values to new simplified categories.

        Args:
            value: Category string (old or new)

        Returns:
            Normalized CategoryEnum (new simplified category)
        """
        legacy_mapping = {
            "surreal_realism": cls.REALISTIC,
            "high_octane_anime": cls.ANIME,
            "stylized_3d": cls.ANIMATION,
        }
        if value in legacy_mapping:
            return legacy_mapping[value]
        return cls(value)

    @property
    def is_legacy(self) -> bool:
        """Check if this is a legacy (deprecated) category."""
        return self in (self.SURREAL_REALISM, self.HIGH_OCTANE_ANIME, self.STYLIZED_3D)

    @property
    def normalized(self) -> "CategoryEnum":
        """Get the normalized (new) category value."""
        if self == self.SURREAL_REALISM:
            return self.REALISTIC
        elif self == self.HIGH_OCTANE_ANIME:
            return self.ANIME
        elif self == self.STYLIZED_3D:
            return self.ANIMATION
        return self


class HITLModeEnum(str, Enum):
    """Human-in-the-loop mode enum."""

    AUTO = "auto"
    MANUAL = "manual"


class AspectRatioEnum(str, Enum):
    """Video aspect ratio enum."""

    VERTICAL = "9:16"
    HORIZONTAL = "16:9"


class ResolutionEnum(str, Enum):
    """Video resolution enum."""

    HD = "720p"
    FULL_HD = "1080p"


class VideoModelOption(str, Enum):
    """User-selectable Veo model option.

    Reference: Documentations/veo_doc.md - Model Versions
    """

    VEO_3_1 = "veo_3_1"  # Maps to veo-3.1-generate-preview
    VEO_3_1_FAST = "veo_3_1_fast"  # Maps to veo-3.1-fast-generate-preview


class WorkflowInput(BaseModel):
    """Input model for creating a new video generation workflow."""

    topic: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Video topic/subject (required)",
        examples=["How black holes work", "The history of the Roman Empire"],
    )

    duration_seconds: int = Field(
        default=18, ge=8, le=60, description="Video duration in seconds (8-60)"
    )

    aspect_ratio: AspectRatioEnum = Field(
        default=AspectRatioEnum.VERTICAL, description="Video aspect ratio"
    )

    resolution: ResolutionEnum = Field(
        default=ResolutionEnum.FULL_HD, description="Video resolution"
    )

    category: CategoryEnum = Field(default=CategoryEnum.AUTO, description="Visual style category")

    hitl_mode: HITLModeEnum = Field(default=HITLModeEnum.AUTO, description="Human-in-the-loop mode")

    enable_audio: bool = Field(default=False, description="Generate audio with video")

    enable_subtitles: bool = Field(default=False, description="Generate subtitles")

    # Optional model selection between Veo 3.1 and Veo 3.1 Fast
    video_model: VideoModelOption = Field(
        default=VideoModelOption.VEO_3_1,
        description="Veo model variant: veo_3_1 (default) or veo_3_1_fast",
        examples=["veo_3_1", "veo_3_1_fast"],
    )

    # Optional specific tool selection under a category
    tool_id: Optional[str] = Field(
        default=None,
        description="Optional tool_id to force a specific tool from the repository. If provided, agents must use this tool. If only category is provided (not 'auto'), agents will select among tools in that category.",
        examples=["surreal_impossible_sims", "anime_concept_combat"],
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate and clean topic."""
        return v.strip()


class WorkflowOutput(BaseModel):
    """Output model for workflow status and results."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    topic: str = Field(..., description="Video topic")

    duration_seconds: int = Field(..., description="Requested duration")
    aspect_ratio: str = Field(..., description="Video aspect ratio")
    resolution: str = Field(..., description="Video resolution")
    category: str = Field(..., description="Selected category")
    hitl_mode: str = Field(..., description="HITL mode")
    enable_audio: bool = Field(..., description="Generate audio (from user input at creation)")
    enable_subtitles: bool = Field(
        ..., description="Generate subtitles (from user input at creation)"
    )

    current_hitl_gate: Optional[str] = Field(
        default=None, description="Current HITL gate if paused"
    )

    tool_selection: Optional[dict[str, Any]] = Field(
        default=None, description="Tool selection output"
    )
    research_output: Optional[dict[str, Any]] = Field(default=None, description="Research output")
    script_output: Optional[dict[str, Any]] = Field(default=None, description="Script output")
    audio_output: Optional[dict[str, Any]] = Field(
        default=None,
        description="Audio manifest output",
    )
    character_reference_sheet: Optional[dict[str, Any]] = Field(
        default=None, description="Character reference sheet with images"
    )
    generated_images: Optional[list[str]] = Field(default=None, description="Generated image URLs")
    video_url: Optional[str] = Field(default=None, description="Final video URL")

    error: Optional[str] = Field(default=None, description="Error message if failed")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")

    generation_time_seconds: Optional[float] = Field(
        default=None, description="Total generation time"
    )


class WorkflowCreateResponse(BaseModel):
    """Response model for workflow creation."""

    workflow_id: str = Field(..., description="Created workflow ID")
    status: WorkflowStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Status message")
