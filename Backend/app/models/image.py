"""RABA Image Models.

Pydantic models for Image Generator Agent output, including:
- Image generation configuration
- Generated image metadata
- Style consistency tracking

Reference: PHASE3_1_IMAGE_GENERATOR_PLAN.md, RABA_Architecture.md Section 2.6
Prompting: Backend/Documentations/nano_prompt_guide.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ImageModel(str, Enum):
    """Available image generation models.
    
    Reference: nano_prompt_guide.md:4584-4591
    """
    NANO_BANANA_PRO = "gemini-3-pro-image-preview"  # Complex scenes, up to 4K
    NANO_BANANA = "gemini-2.5-flash-image"  # Simple scenes, 1024px max


class ImageResolution(str, Enum):
    """Supported image resolutions.
    
    Reference: nano_prompt_guide.md:4569-4582
    """
    RES_1K = "1K"  # 1024px
    RES_2K = "2K"  # 2048px
    RES_4K = "4K"  # 4096px (Nano Banana Pro only)


class ImageAspectRatio(str, Enum):
    """Supported image aspect ratios.
    
    Reference: nano_prompt_guide.md:4552-4582
    """
    SQUARE = "1:1"
    PORTRAIT_2_3 = "2:3"
    LANDSCAPE_3_2 = "3:2"
    PORTRAIT_3_4 = "3:4"
    LANDSCAPE_4_3 = "4:3"
    PORTRAIT_4_5 = "4:5"
    LANDSCAPE_5_4 = "5:4"
    PORTRAIT_9_16 = "9:16"  # YouTube Shorts vertical
    LANDSCAPE_16_9 = "16:9"  # YouTube Shorts horizontal
    ULTRAWIDE_21_9 = "21:9"


class ImageGenerationConfig(BaseModel):
    """Configuration for image generation.
    
    Reference: RABA_Architecture.md:1408-1419
    """
    model: ImageModel = Field(
        default=ImageModel.NANO_BANANA_PRO,
        description="Image generation model to use"
    )
    aspect_ratio: ImageAspectRatio = Field(
        default=ImageAspectRatio.PORTRAIT_9_16,
        description="Output image aspect ratio"
    )
    resolution: ImageResolution = Field(
        default=ImageResolution.RES_2K,
        description="Output image resolution"
    )
    style_keywords: list[str] = Field(
        default_factory=list,
        description="Style keywords from tool category"
    )
    maintain_consistency: bool = Field(
        default=True,
        description="Use previous images as style reference"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Max retry attempts on failure"
    )
    timeout_seconds: int = Field(
        default=120,
        ge=30,
        le=300,
        description="Timeout for image generation"
    )


class StyleReference(BaseModel):
    """Style reference for maintaining consistency across images.
    
    All images in a workflow should share consistent visual style.
    This model tracks reference images used for style consistency.
    """
    reference_image_url: Optional[str] = Field(
        default=None,
        description="URL of the primary style reference image"
    )
    reference_image_base64: Optional[str] = Field(
        default=None,
        description="Base64 encoded reference image for API calls"
    )
    style_description: str = Field(
        default="",
        description="Text description of the visual style to maintain"
    )
    color_palette: list[str] = Field(
        default_factory=list,
        description="Dominant colors to maintain across images"
    )
    character_descriptions: list[str] = Field(
        default_factory=list,
        description="Character descriptions for consistency"
    )
    
    @field_validator("color_palette")
    @classmethod
    def validate_color_palette(cls, v: list[str]) -> list[str]:
        """Limit color palette to 5 colors."""
        return v[:5] if len(v) > 5 else v


class GeneratedImage(BaseModel):
    """Metadata for a single generated image.
    
    Reference: RABA_Architecture.md:463-468
    """
    url: str = Field(
        ...,
        description="Public URL of the generated image"
    )
    storage_path: str = Field(
        default="",
        description="Path in Supabase Storage bucket"
    )
    prompt: str = Field(
        ...,
        description="Prompt used to generate the image"
    )
    scene_number: int = Field(
        ...,
        ge=1,
        description="Scene number this image represents"
    )
    model_used: ImageModel = Field(
        default=ImageModel.NANO_BANANA_PRO,
        description="Model used for generation"
    )
    aspect_ratio: ImageAspectRatio = Field(
        default=ImageAspectRatio.PORTRAIT_9_16,
        description="Aspect ratio of generated image"
    )
    resolution: ImageResolution = Field(
        default=ImageResolution.RES_2K,
        description="Resolution of generated image"
    )
    generation_time_ms: int = Field(
        default=0,
        ge=0,
        description="Time taken to generate in milliseconds"
    )
    used_style_reference: bool = Field(
        default=False,
        description="Whether a style reference was used"
    )
    style_reference_url: Optional[str] = Field(
        default=None,
        description="URL of style reference used (if any)"
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries before success"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )


class ImageSource(str, Enum):
    """Source type for images in the workflow."""
    USER_REFERENCE = "user_reference"
    RESEARCH = "research"
    GENERATED = "generated"


class WorkflowImage(BaseModel):
    """An image in the workflow with its source type.
    
    Used to track all images (user, research, generated) in a unified way.
    """
    url: str = Field(
        ...,
        description="Public URL of the image"
    )
    source: ImageSource = Field(
        ...,
        description="Source of the image"
    )
    scene_number: Optional[int] = Field(
        default=None,
        description="Scene number (for generated images)"
    )
    description: str = Field(
        default="",
        description="Description of the image content"
    )
    is_style_reference: bool = Field(
        default=False,
        description="Whether this image is used as style reference"
    )


class ImageGeneratorOutput(BaseModel):
    """Complete output from the Image Generator Agent.
    
    Reference: RABA_Architecture.md:463-468
    """
    generated_images: list[GeneratedImage] = Field(
        default_factory=list,
        description="List of generated images with metadata"
    )
    all_images: list[WorkflowImage] = Field(
        default_factory=list,
        description="All images: user_ref + research + generated"
    )
    style_reference: Optional[StyleReference] = Field(
        default=None,
        description="Style reference used for consistency"
    )
    total_images_generated: int = Field(
        default=0,
        ge=0,
        description="Total number of images generated"
    )
    total_generation_time_ms: int = Field(
        default=0,
        ge=0,
        description="Total time for all image generations"
    )
    model_used: ImageModel = Field(
        default=ImageModel.NANO_BANANA_PRO,
        description="Primary model used for generation"
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback model was used"
    )
    
    @property
    def all_image_urls(self) -> list[str]:
        """Get all image URLs in order."""
        return [img.url for img in self.all_images]
    
    @property
    def generated_image_urls(self) -> list[str]:
        """Get only generated image URLs."""
        return [img.url for img in self.generated_images]


class ImageGenerationRequest(BaseModel):
    """Request to generate images for a workflow.
    
    Used as input to the Image Generator Agent.
    """
    workflow_id: str = Field(
        ...,
        description="Workflow ID for storage path"
    )
    scenes: list[dict] = Field(
        ...,
        min_length=1,
        description="Scene descriptions from script output"
    )
    tool_category: str = Field(
        default="surreal_realism",
        description="Tool category for visual style"
    )
    tool_visual_vocabulary: dict = Field(
        default_factory=dict,
        description="Tool-specific visual vocabulary"
    )
    user_reference_image_url: Optional[str] = Field(
        default=None,
        description="User-provided reference image URL"
    )
    research_images: list[str] = Field(
        default_factory=list,
        description="Research image URLs"
    )
    aspect_ratio: str = Field(
        default="9:16",
        description="Video aspect ratio"
    )
    resolution: str = Field(
        default="1080p",
        description="Video resolution"
    )
    topic: str = Field(
        default="",
        description="Video topic for context"
    )
    duration_seconds: int = Field(
        default=18,
        ge=8,
        le=25,
        description="Video duration"
    )


class HITLImageFeedback(BaseModel):
    """User feedback for image regeneration at HITL Gate 4.
    
    Reference: SRS.md:126-127
    """
    action: str = Field(
        ...,
        description="User action: approve, add_image, remove_image, regenerate"
    )
    feedback: Optional[str] = Field(
        default=None,
        description="User feedback for regeneration"
    )
    images_to_remove: list[str] = Field(
        default_factory=list,
        description="URLs of images to remove"
    )
    images_to_add: list[str] = Field(
        default_factory=list,
        description="URLs of images to add"
    )
    style_feedback: Optional[str] = Field(
        default=None,
        description="Feedback on visual style"
    )
    regenerate_scene_numbers: list[int] = Field(
        default_factory=list,
        description="Specific scenes to regenerate"
    )
