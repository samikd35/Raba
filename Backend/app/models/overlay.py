"""Overlay and Validation Models.

Models to support Phase 3 features:
- Subtitles/overlay items
- Character reference sheet
- Visual logic validation output
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OverlayAlignment(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class OverlayItem(BaseModel):
    """Metadata for a subtitle/text overlay element."""
    text: str = Field(..., description="Overlay text (subtitle line)")
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    position: OverlayAlignment = Field(default=OverlayAlignment.BOTTOM, description="Vertical alignment")
    image_url: Optional[str] = Field(default=None, description="URL of rendered text image (optional)")


class CharacterReferenceImage(BaseModel):
    """Single view in a character reference sheet."""
    view: str = Field(..., description="View label (front/side/back/face)")
    url: str = Field(..., description="Image URL for this view")


class CharacterReferenceSheet(BaseModel):
    """Character reference sheet to maintain consistency."""
    character_name: str = Field(..., description="Lead character name")
    character_description: str = Field(default="", description="Text description")
    reference_images: list[CharacterReferenceImage] = Field(default_factory=list)
    character_metadata: dict = Field(default_factory=dict)


class VisualRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VisualValidationOutput(BaseModel):
    """Output from visual logic validation agent."""
    validation_passed: bool = Field(default=True)
    flagged_issues: list[str] = Field(default_factory=list)
    suggested_alternatives: list[str] = Field(default_factory=list)
    risk_level: VisualRiskLevel = Field(default=VisualRiskLevel.LOW)
    requires_revision: bool = Field(default=False)

