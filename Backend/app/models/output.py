"""RABA Output Processing Models.

Pydantic models for workflow completion and final output, including:
- Workflow completion output
- Video/Image output summaries
- Generation timing breakdown
- Final API response format

Reference: PHASE3_3_OUTPUT_PROCESSOR_PLAN.md, SRS.md Section 7.2
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field

from app.models.workflow import WorkflowStatus


class VideoOutputSummary(BaseModel):
    """Summary of video output for final response.
    
    Reference: SRS.md Section 7.2 - Output Data Schema
    """
    url: str = Field(
        ...,
        description="Public URL of the final video"
    )
    duration_seconds: float = Field(
        ...,
        gt=0,
        description="Total video duration"
    )
    resolution: str = Field(
        default="720p",
        description="Video resolution"
    )
    aspect_ratio: str = Field(
        default="9:16",
        description="Video aspect ratio"
    )
    segment_count: int = Field(
        default=1,
        ge=1,
        description="Number of video segments"
    )
    file_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Video file size in bytes"
    )
    audio_included: bool = Field(
        default=True,
        description="Whether audio was generated"
    )


class ImageOutputSummary(BaseModel):
    """Summary of image outputs for final response."""
    generated_count: int = Field(
        default=0,
        ge=0,
        description="Number of AI-generated images"
    )
    total_count: int = Field(
        default=0,
        ge=0,
        description="Total images (user + research + generated)"
    )
    urls: list[str] = Field(
        default_factory=list,
        description="All image URLs"
    )
    user_reference_included: bool = Field(
        default=False,
        description="Whether user provided a reference image"
    )
    research_images_count: int = Field(
        default=0,
        ge=0,
        description="Number of research images"
    )


class WorkflowMetadataSummary(BaseModel):
    """Metadata summary for the completed workflow."""
    tool_used: str = Field(
        default="",
        description="Name of the tool used"
    )
    tool_id: str = Field(
        default="",
        description="ID of the tool used"
    )
    category: str = Field(
        default="",
        description="Visual style category"
    )
    topic: str = Field(
        default="",
        description="Video topic (may be truncated)"
    )
    hitl_mode: str = Field(
        default="auto",
        description="Human-in-the-loop mode used"
    )
    audio_enabled: bool = Field(
        default=True,
        description="Whether audio generation was enabled"
    )
    subtitles_enabled: bool = Field(
        default=False,
        description="Whether subtitles were enabled"
    )
    viral_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Script viral score (0-1)"
    )


class GenerationTiming(BaseModel):
    """Timing breakdown for workflow generation.
    
    Reference: SRS.md FR-903 - Track generation time per step
    """
    total_seconds: float = Field(
        default=0.0,
        ge=0,
        description="Total generation time in seconds"
    )
    phase_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Time per phase in seconds"
    )
    started_at: datetime = Field(
        ...,
        description="Workflow start timestamp"
    )
    completed_at: datetime = Field(
        ...,
        description="Workflow completion timestamp"
    )
    
    @computed_field
    @property
    def formatted_total(self) -> str:
        """Human-readable total time."""
        minutes = int(self.total_seconds // 60)
        seconds = int(self.total_seconds % 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


class OutputURLs(BaseModel):
    """Collection of output URLs for easy access."""
    video_url: str = Field(
        ...,
        description="Final video URL"
    )
    all_image_urls: list[str] = Field(
        default_factory=list,
        description="All image URLs"
    )
    shareable_link: Optional[str] = Field(
        default=None,
        description="Shareable public link (if generated)"
    )


class WorkflowCompletionOutput(BaseModel):
    """Complete output from a finished workflow.
    
    Reference: SRS.md Section 7.2 - Output Data Schema
    """
    workflow_id: str = Field(
        ...,
        description="Unique workflow identifier"
    )
    status: WorkflowStatus = Field(
        default=WorkflowStatus.COMPLETED,
        description="Final workflow status"
    )
    
    video: VideoOutputSummary = Field(
        ...,
        description="Video output summary"
    )
    images: ImageOutputSummary = Field(
        default_factory=ImageOutputSummary,
        description="Image output summary"
    )
    metadata: WorkflowMetadataSummary = Field(
        default_factory=WorkflowMetadataSummary,
        description="Workflow metadata"
    )
    timing: GenerationTiming = Field(
        ...,
        description="Generation timing breakdown"
    )
    urls: OutputURLs = Field(
        ...,
        description="Output URLs collection"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    error_details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Detailed error information"
    )
    
    @computed_field
    @property
    def video_url(self) -> str:
        """Convenience accessor for video URL."""
        return self.video.url
    
    @computed_field
    @property
    def video_duration(self) -> float:
        """Convenience accessor for video duration."""
        return self.video.duration_seconds
    
    @computed_field
    @property
    def generation_time_seconds(self) -> float:
        """Convenience accessor for total generation time."""
        return self.timing.total_seconds
    
    @computed_field
    @property
    def all_image_urls(self) -> list[str]:
        """Convenience accessor for all image URLs."""
        return self.images.urls
    
    def to_api_response(self) -> dict[str, Any]:
        """Convert to SRS 7.2 compliant API response format.
        
        Returns:
            Dict matching SRS.md Section 7.2 Output Data Schema
        """
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "video_url": self.video.url,
            "video_duration": self.video.duration_seconds,
            "resolution": self.video.resolution,
            "aspect_ratio": self.video.aspect_ratio,
            "all_image_urls": self.images.urls,
            "generation_time_seconds": self.timing.total_seconds,
            "metadata": {
                "tool_used": self.metadata.tool_used,
                "category": self.metadata.category,
                "segment_count": self.video.segment_count,
                "topic": self.metadata.topic,
                "viral_score": self.metadata.viral_score,
            },
            "timing": {
                "total_seconds": self.timing.total_seconds,
                "breakdown": self.timing.phase_breakdown,
            },
            "created_at": self.timing.started_at.isoformat(),
            "completed_at": self.timing.completed_at.isoformat(),
        }


class WorkflowErrorOutput(BaseModel):
    """Output for failed workflows.
    
    Reference: PHASE3_3_OUTPUT_PROCESSOR_PLAN.md Section 6.2
    """
    workflow_id: str = Field(
        ...,
        description="Workflow identifier"
    )
    status: WorkflowStatus = Field(
        default=WorkflowStatus.FAILED,
        description="Failed status"
    )
    error: str = Field(
        ...,
        description="Error message"
    )
    error_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed error information"
    )
    partial_output: Optional[dict[str, Any]] = Field(
        default=None,
        description="Any partial output available"
    )
    
    def to_api_response(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "error": self.error,
            "error_details": self.error_details,
            "partial_output": self.partial_output,
        }
