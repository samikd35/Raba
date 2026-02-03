"""
Pydantic models for Feature Video Seen tracking.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MarkFeatureVideoSeenRequest(BaseModel):
    """Request body for marking a feature video as seen."""
    
    feature_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Feature identifier, e.g., 'problem-explorer', 'vpc-canvas'",
        examples=["problem-explorer", "customer-profile", "hypothesis"]
    )
    source: Optional[Literal["autoplay", "icon_click"]] = Field(
        default=None,
        description="How the video was triggered"
    )


class MarkFeatureVideoSeenResponse(BaseModel):
    """Response for marking a feature video as seen."""
    
    ok: bool = True
    feature_id: str
    created: bool = Field(
        description="True if this was the first time seeing the video"
    )


class SeenFeatureVideosResponse(BaseModel):
    """Response containing all seen feature video IDs for a user."""
    
    seen: List[str] = Field(
        default_factory=list,
        description="List of feature IDs the user has seen"
    )


class FeatureVideoSeenRecord(BaseModel):
    """Full record from the database (for internal use)."""
    
    id: UUID
    user_id: UUID
    feature_id: str
    first_seen_at: datetime
    source: Optional[str] = None
