"""RABA Video Models.

Pydantic models for Video Generator Agent output, including:
- Video generation configuration
- Generated video metadata
- Segment tracking for multi-segment videos
- HITL feedback for video approval

Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md, RABA_Architecture.md Section 2.7
API Docs: Backend/Documentations/veo_doc.md
Prompting: Backend/Documentations/veo_prompting_guide.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class VideoModel(str, Enum):
    """Available video generation models.
    
    Reference: veo_doc.md - Model versions
    """
    VEO_3_1 = "veo-3.1-generate-preview"  # High-quality, 3-5 min generation
    VEO_3_1_FAST = "veo-3.1-fast-generate-preview"  # Faster, 1-2 min generation


class VideoResolution(str, Enum):
    """Supported video resolutions.
    
    Reference: veo_doc.md - Veo API parameters
    Note: 1080p only supports 8s duration (no extension)
          720p required for video extension
    """
    RES_720P = "720p"
    RES_1080P = "1080p"


class VideoAspectRatio(str, Enum):
    """Supported video aspect ratios.
    
    Reference: veo_doc.md - aspectRatio parameter
    """
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"


class VideoDuration(int, Enum):
    """Supported video segment durations.
    
    Reference: veo_doc.md - durationSeconds parameter
    """
    DURATION_4S = 4
    DURATION_6S = 6
    DURATION_8S = 8


class VideoSegmentType(str, Enum):
    """Type of video segment in multi-segment generation."""
    INITIAL = "initial"  # First 8s segment with reference images
    EXTENSION = "extension"  # Extended segment (~7s each)


class VideoSegment(BaseModel):
    """Metadata for a single video segment.
    
    Used to track multi-segment video generation for videos >8s.
    Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md Section 2.4
    """
    segment_number: int = Field(
        ...,
        ge=0,
        description="Segment number (0-indexed)"
    )
    segment_type: VideoSegmentType = Field(
        ...,
        description="Type of segment (initial or extension)"
    )
    duration_seconds: float = Field(
        ...,
        gt=0,
        description="Duration of this segment in seconds"
    )
    start_time: float = Field(
        default=0.0,
        ge=0,
        description="Start time in the final video"
    )
    end_time: float = Field(
        default=0.0,
        ge=0,
        description="End time in the final video"
    )
    prompt: str = Field(
        default="",
        description="Prompt used for this segment"
    )
    generation_time_ms: int = Field(
        default=0,
        ge=0,
        description="Time taken to generate this segment"
    )
    used_reference_images: bool = Field(
        default=False,
        description="Whether reference images were used (initial segment only)"
    )


class VideoGenerationConfig(BaseModel):
    """Configuration for video generation.
    
    Reference: veo_doc.md - Veo API parameters
    """
    model: VideoModel = Field(
        default=VideoModel.VEO_3_1,
        description="Video generation model to use"
    )
    aspect_ratio: VideoAspectRatio = Field(
        default=VideoAspectRatio.PORTRAIT_9_16,
        description="Output video aspect ratio"
    )
    resolution: VideoResolution = Field(
        default=VideoResolution.RES_720P,
        description="Output video resolution (720p required for extension)"
    )
    duration_seconds: int = Field(
        default=8,
        ge=4,
        le=8,
        description="Duration per segment (max 8s per Veo API)"
    )
    target_duration_seconds: int = Field(
        default=18,
        ge=8,
        le=60,
        description="Target total video duration"
    )
    enable_audio: bool = Field(
        default=True,
        description="Enable native audio generation"
    )
    negative_prompt: Optional[str] = Field(
        default="text overlays, watermarks, logos, UI elements, low quality, blurry",
        description="Elements to avoid in the video"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Max retry attempts on failure"
    )
    poll_interval_seconds: int = Field(
        default=10,
        ge=5,
        le=30,
        description="Interval for polling video generation status"
    )
    timeout_seconds: int = Field(
        default=360,
        ge=60,
        le=600,
        description="Timeout for video generation (6 min max per Veo docs)"
    )
    
    @field_validator("resolution")
    @classmethod
    def validate_resolution_for_extension(cls, v: VideoResolution, info) -> VideoResolution:
        """Ensure 720p is used when extension is needed."""
        target = info.data.get("target_duration_seconds", 18)
        if target > 8 and v == VideoResolution.RES_1080P:
            return VideoResolution.RES_720P
        return v


class ReferenceImageSelection(BaseModel):
    """Selection of reference images for video generation.
    
    Maximum 3 images per Veo 3.1 API limit.
    Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md Section 2.5
    """
    user_reference_url: Optional[str] = Field(
        default=None,
        description="User-provided reference image URL (highest priority)"
    )
    generated_image_urls: list[str] = Field(
        default_factory=list,
        description="URLs of generated images"
    )
    research_image_urls: list[str] = Field(
        default_factory=list,
        description="URLs of research images (lowest priority)"
    )
    selected_urls: list[str] = Field(
        default_factory=list,
        description="Final selected image URLs (max 3)"
    )
    
    @field_validator("selected_urls")
    @classmethod
    def validate_max_images(cls, v: list[str]) -> list[str]:
        """Ensure max 3 reference images."""
        if len(v) > 3:
            return v[:3]
        return v
    
    def select_images(self) -> list[str]:
        """Select up to 3 images with priority: user > generated > research.
        
        Returns:
            List of up to 3 image URLs
        """
        selected = []
        
        if self.user_reference_url:
            selected.append(self.user_reference_url)
        
        remaining = 3 - len(selected)
        if self.generated_image_urls and remaining > 0:
            if len(self.generated_image_urls) <= remaining:
                selected.extend(self.generated_image_urls)
            else:
                selected.append(self.generated_image_urls[0])
                if remaining > 1 and len(self.generated_image_urls) > 1:
                    selected.append(self.generated_image_urls[-1])
        
        remaining = 3 - len(selected)
        if self.research_image_urls and remaining > 0:
            selected.extend(self.research_image_urls[:remaining])
        
        self.selected_urls = selected[:3]
        return self.selected_urls


class GeneratedVideo(BaseModel):
    """Metadata for a generated video.
    
    Reference: RABA_Architecture.md Section 2.7
    """
    url: str = Field(
        ...,
        description="Public URL of the generated video"
    )
    storage_path: str = Field(
        default="",
        description="Path in Supabase Storage bucket"
    )
    duration_seconds: float = Field(
        ...,
        gt=0,
        description="Total duration of the video"
    )
    resolution: VideoResolution = Field(
        default=VideoResolution.RES_720P,
        description="Video resolution"
    )
    aspect_ratio: VideoAspectRatio = Field(
        default=VideoAspectRatio.PORTRAIT_9_16,
        description="Video aspect ratio"
    )
    model_used: VideoModel = Field(
        default=VideoModel.VEO_3_1,
        description="Model used for generation"
    )
    segments: list[VideoSegment] = Field(
        default_factory=list,
        description="Segment breakdown for multi-segment videos"
    )
    total_segments: int = Field(
        default=1,
        ge=1,
        description="Total number of segments"
    )
    audio_included: bool = Field(
        default=True,
        description="Whether native audio was generated"
    )
    reference_images_used: list[str] = Field(
        default_factory=list,
        description="Reference image URLs used for generation"
    )
    generation_time_ms: int = Field(
        default=0,
        ge=0,
        description="Total time for video generation"
    )
    file_size_bytes: int = Field(
        default=0,
        ge=0,
        description="File size in bytes"
    )
    mime_type: str = Field(
        default="video/mp4",
        description="Video MIME type"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )


class VideoGeneratorOutput(BaseModel):
    """Complete output from the Video Generator Agent.
    
    Reference: RABA_Architecture.md Section 2.7
    """
    video: GeneratedVideo = Field(
        ...,
        description="Generated video with metadata"
    )
    segments: list[VideoSegment] = Field(
        default_factory=list,
        description="All video segments"
    )
    total_duration_seconds: float = Field(
        default=0.0,
        gt=0,
        description="Total video duration"
    )
    total_generation_time_ms: int = Field(
        default=0,
        ge=0,
        description="Total time for all generation"
    )
    model_used: VideoModel = Field(
        default=VideoModel.VEO_3_1,
        description="Primary model used"
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback model was used"
    )
    reference_images: ReferenceImageSelection = Field(
        default_factory=ReferenceImageSelection,
        description="Reference images used"
    )
    prompt_used: str = Field(
        default="",
        description="Main prompt used for initial generation"
    )
    
    @property
    def video_url(self) -> str:
        """Get the final video URL."""
        return self.video.url


class VideoGenerationRequest(BaseModel):
    """Request to generate video for a workflow.
    
    Used as input to the Video Generator Agent.
    """
    workflow_id: str = Field(
        ...,
        description="Workflow ID for storage path"
    )
    script_output: dict = Field(
        ...,
        description="Script output with hook, scenes, CTA"
    )
    all_images: list[str] = Field(
        default_factory=list,
        description="All available image URLs"
    )
    user_reference_image_url: Optional[str] = Field(
        default=None,
        description="User-provided reference image URL"
    )
    research_images: list[str] = Field(
        default_factory=list,
        description="Research image URLs"
    )
    generated_images: list[str] = Field(
        default_factory=list,
        description="Generated image URLs"
    )
    tool_category: str = Field(
        default="surreal_realism",
        description="Tool category for visual style"
    )
    topic: str = Field(
        default="",
        description="Video topic for context"
    )
    aspect_ratio: str = Field(
        default="9:16",
        description="Video aspect ratio"
    )
    resolution: str = Field(
        default="720p",
        description="Video resolution"
    )
    duration_seconds: int = Field(
        default=18,
        ge=8,
        le=60,
        description="Target video duration"
    )
    enable_audio: bool = Field(
        default=True,
        description="Enable native audio generation"
    )


class HITLVideoAction(str, Enum):
    """User actions at HITL Gate 5 for video approval.
    
    Reference: SRS.md Section 3.6
    """
    APPROVE = "approve"
    REGENERATE = "regenerate"


class HITLVideoFeedback(BaseModel):
    """User feedback for video regeneration at HITL Gate 5.
    
    Reference: SRS.md Section 3.6, RABA_Architecture.md:989-1055
    """
    action: HITLVideoAction = Field(
        ...,
        description="User action: approve or regenerate"
    )
    feedback: Optional[str] = Field(
        default=None,
        description="General feedback for regeneration"
    )
    pacing_feedback: Optional[str] = Field(
        default=None,
        description="Feedback on video pacing"
    )
    transition_feedback: Optional[str] = Field(
        default=None,
        description="Feedback on scene transitions"
    )
    audio_feedback: Optional[str] = Field(
        default=None,
        description="Feedback on audio/dialogue"
    )
    visual_feedback: Optional[str] = Field(
        default=None,
        description="Feedback on visual style"
    )
    specific_timestamp: Optional[float] = Field(
        default=None,
        ge=0,
        description="Specific timestamp with issue (seconds)"
    )
    
    def get_combined_feedback(self) -> str:
        """Combine all feedback into a single string for regeneration."""
        parts = []
        if self.feedback:
            parts.append(f"General: {self.feedback}")
        if self.pacing_feedback:
            parts.append(f"Pacing: {self.pacing_feedback}")
        if self.transition_feedback:
            parts.append(f"Transitions: {self.transition_feedback}")
        if self.audio_feedback:
            parts.append(f"Audio: {self.audio_feedback}")
        if self.visual_feedback:
            parts.append(f"Visual: {self.visual_feedback}")
        if self.specific_timestamp is not None:
            parts.append(f"Issue at {self.specific_timestamp}s")
        return " | ".join(parts) if parts else ""
