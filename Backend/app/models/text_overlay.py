"""Text Overlay Models.

Structured models for text overlays to add during post-processing.
These are separate from simple subtitle overlay items and include
styling and animation hints for FFmpeg-based compositing.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, Field


class TextOverlay(BaseModel):
    """Structured text overlay specification."""

    text: str = Field(..., description="Overlay text content")
    start_time: float = Field(..., ge=0.0, description="Start time in seconds")
    end_time: float = Field(..., ge=0.0, description="End time in seconds")
    position: Tuple[int, int] = Field(
        default=(40, 40), description="Top-left x,y position in pixels"
    )
    font_size: int = Field(default=48, ge=8, le=256, description="Font size (px)")
    font_color: str = Field(default="white", description="Font color")
    background_color: Optional[str] = Field(
        default="black@0.5", description="Optional background color with alpha"
    )
    fontfile: Optional[str] = Field(
        default=None, description="Optional absolute path to TTF/OTF font file"
    )
    animation: Optional[str] = Field(
        default=None, description="Optional animation hint (fade_in, slide_up, etc.)"
    )

