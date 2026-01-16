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
    """Video category/style enum."""
    AUTO = "auto"
    SURREAL_REALISM = "surreal_realism"
    HIGH_OCTANE_ANIME = "high_octane_anime"
    STYLIZED_3D = "stylized_3d"


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


class WorkflowInput(BaseModel):
    """Input model for creating a new video generation workflow."""
    
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Video topic/subject (required)",
        examples=["How black holes work", "The history of the Roman Empire"]
    )
    
    duration_seconds: int = Field(
        default=18,
        ge=8,
        le=60,
        description="Video duration in seconds (8-60)"
    )
    
    aspect_ratio: AspectRatioEnum = Field(
        default=AspectRatioEnum.VERTICAL,
        description="Video aspect ratio"
    )
    
    resolution: ResolutionEnum = Field(
        default=ResolutionEnum.FULL_HD,
        description="Video resolution"
    )
    
    category: CategoryEnum = Field(
        default=CategoryEnum.AUTO,
        description="Visual style category"
    )
    
    hitl_mode: HITLModeEnum = Field(
        default=HITLModeEnum.AUTO,
        description="Human-in-the-loop mode"
    )
    
    enable_audio: bool = Field(
        default=True,
        description="Generate audio with video"
    )
    
    enable_subtitles: bool = Field(
        default=False,
        description="Generate subtitles"
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
    
    current_hitl_gate: Optional[str] = Field(default=None, description="Current HITL gate if paused")
    
    tool_selection: Optional[dict[str, Any]] = Field(default=None, description="Tool selection output")
    research_output: Optional[dict[str, Any]] = Field(default=None, description="Research output")
    script_output: Optional[dict[str, Any]] = Field(default=None, description="Script output")
    generated_images: Optional[list[str]] = Field(default=None, description="Generated image URLs")
    video_url: Optional[str] = Field(default=None, description="Final video URL")
    
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    
    generation_time_seconds: Optional[float] = Field(default=None, description="Total generation time")


class WorkflowCreateResponse(BaseModel):
    """Response model for workflow creation."""
    
    workflow_id: str = Field(..., description="Created workflow ID")
    status: WorkflowStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Status message")
