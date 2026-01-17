"""RABA Script Models.

Pydantic models for Script Generator Agent output, including:
- Hook section with viral archetypes
- Scenes with visual directions
- Pattern interrupts for engagement
- Call-to-action
- Viral metrics

Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md, RABA_Architecture.md Section 2.5
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class HookArchetype(str, Enum):
    """Hook archetypes for viral short-form content.
    
    Reference: RABA_Architecture.md:348-365
    """
    FORTUNETELLER = "fortuneteller"  # Promise future outcome (transformation hook)
    TEACHER = "teacher"              # Fast, actionable value (solution hook)
    DISRUPTOR = "disruptor"          # Challenge status quo (contrarian hook)
    STORYTELLER = "storyteller"      # Relatable narrative (emotional hook)


class PatternInterruptType(str, Enum):
    """Types of pattern interrupts to maintain viewer attention.
    
    Reference: RABA_Architecture.md:1302-1343
    """
    SCENE_CHANGE = "scene_change"          # New location/subject
    VISUAL_EFFECT = "visual_effect"        # Transition, animation shift
    NEW_FACT = "new_fact"                  # Information reveal
    PERSPECTIVE_SHIFT = "perspective_shift"  # Different angle/interpretation
    EMOTIONAL_PIVOT = "emotional_pivot"    # Mood change
    SENSORY_CUE = "sensory_cue"            # Sound/visual surprise


class CTAType(str, Enum):
    """Call-to-action types for video endings."""
    FOLLOW = "follow"
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    SUBSCRIBE = "subscribe"


class HookSection(BaseModel):
    """The viral hook for the first 1-2 seconds.
    
    Reference: RABA_Architecture.md:348-365
    """
    archetype: HookArchetype = Field(
        ...,
        description="Hook archetype type"
    )
    script: str = Field(
        ...,
        description="Verbal hook text (spoken, max ~10 words)",
        max_length=100
    )
    visual_direction: str = Field(
        ...,
        description="Visual direction for what viewer sees during hook"
    )
    duration_seconds: float = Field(
        default=2.0,
        ge=1.0,
        le=3.0,
        description="Duration of hook (1-3 seconds)"
    )
    psychological_lever: str = Field(
        default="curiosity_gap",
        description="Psychological lever: curiosity_gap, fomo, relatability, dopamine"
    )
    estimated_vvsa_impact: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Estimated Views vs Swiped Away impact score"
    )


class Scene(BaseModel):
    """A single scene with visual directions.
    
    Reference: RABA_Architecture.md:385-415
    """
    scene_number: int = Field(
        ...,
        ge=1,
        description="Scene order (1-indexed)"
    )
    timestamp_start: float = Field(
        ...,
        ge=0.0,
        description="Start time in seconds"
    )
    timestamp_end: float = Field(
        ...,
        ge=0.0,
        description="End time in seconds"
    )
    description: str = Field(
        ...,
        description="Rich sensory visual description"
    )
    dialogue: Optional[str] = Field(
        default=None,
        description="Optional spoken dialogue/narration"
    )
    audio_cues: list[str] = Field(
        default_factory=list,
        description="Sound design notes (ambient, SFX, music)"
    )
    camera_direction: str = Field(
        default="",
        description="Camera movement/angle (e.g., 'slow zoom in', 'pan left')"
    )
    lighting: str = Field(
        default="",
        description="Lighting description"
    )
    mood: str = Field(
        default="",
        description="Emotional tone/atmosphere"
    )
    pattern_interrupt_type: Optional[PatternInterruptType] = Field(
        default=None,
        description="Type of pattern interrupt at this scene (if applicable)"
    )
    visual_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords for image/video generation"
    )
    
    @property
    def duration_seconds(self) -> float:
        """Calculate scene duration."""
        return self.timestamp_end - self.timestamp_start
    
    @field_validator("timestamp_end")
    @classmethod
    def validate_timestamp_order(cls, v: float, info) -> float:
        """Ensure timestamp_end is after timestamp_start."""
        if "timestamp_start" in info.data and v <= info.data["timestamp_start"]:
            raise ValueError("timestamp_end must be greater than timestamp_start")
        return v


class CTASection(BaseModel):
    """Call-to-action section at the end of the video."""
    type: CTAType = Field(
        default=CTAType.FOLLOW,
        description="Type of call-to-action"
    )
    placement_seconds: float = Field(
        ...,
        description="When CTA appears (seconds from start)"
    )
    script: str = Field(
        default="",
        description="CTA spoken text (optional)"
    )
    visual_direction: str = Field(
        default="",
        description="Visual direction for CTA"
    )


class ViralMetrics(BaseModel):
    """Viral optimization metrics for the script.
    
    Reference: RABA_Architecture.md:1345-1383
    """
    hook_strength: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Hook effectiveness score (weight: 0.25)"
    )
    pattern_interrupt_density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Interrupt frequency score (weight: 0.20)"
    )
    emotional_arc: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Story structure score (weight: 0.20)"
    )
    call_to_action_clarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="CTA effectiveness score (weight: 0.15)"
    )
    audience_fit: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Target audience match score (weight: 0.10)"
    )
    novelty_factor: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Uniqueness of angle score (weight: 0.10)"
    )
    
    def calculate_viral_score(self) -> float:
        """Calculate weighted viral score."""
        weights = {
            "hook_strength": 0.25,
            "pattern_interrupt_density": 0.20,
            "emotional_arc": 0.20,
            "call_to_action_clarity": 0.15,
            "audience_fit": 0.10,
            "novelty_factor": 0.10,
        }
        score = (
            self.hook_strength * weights["hook_strength"] +
            self.pattern_interrupt_density * weights["pattern_interrupt_density"] +
            self.emotional_arc * weights["emotional_arc"] +
            self.call_to_action_clarity * weights["call_to_action_clarity"] +
            self.audience_fit * weights["audience_fit"] +
            self.novelty_factor * weights["novelty_factor"]
        )
        return min(0.98, score)


class ScriptOutput(BaseModel):
    """Complete script output from the Script Generator Agent.
    
    Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md, RABA_Architecture.md:385-415
    """
    hook: HookSection = Field(
        ...,
        description="Viral hook section (first 1-3 seconds)"
    )
    scenes: list[Scene] = Field(
        ...,
        min_length=1,
        description="List of scenes with visual directions"
    )
    call_to_action: CTASection = Field(
        ...,
        description="Call-to-action section"
    )
    lead_character: Optional[str] = Field(
        default=None,
        description="Optional lead character name for consistency"
    )
    lead_character_description: Optional[str] = Field(
        default=None,
        description="Optional description for the lead character"
    )
    
    viral_metrics: ViralMetrics = Field(
        default_factory=ViralMetrics,
        description="Breakdown of viral metrics"
    )
    estimated_completion_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Predicted viewer completion rate"
    )
    viral_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite viral score"
    )
    total_duration_seconds: float = Field(
        ...,
        ge=8.0,
        le=60.0,
        description="Total script duration (8-60 seconds)"
    )
    
    tool_category_applied: str = Field(
        default="",
        description="Tool category whose specs were applied"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )
    
    @field_validator("scenes")
    @classmethod
    def validate_scene_count(cls, v: list[Scene]) -> list[Scene]:
        """Ensure at least one scene exists."""
        if len(v) < 1:
            raise ValueError("At least one scene is required")
        return v


class ScriptRequest(BaseModel):
    """Request model for script generation."""
    topic: str = Field(..., description="Video topic")
    duration_seconds: int = Field(default=18, ge=8, le=60)
    intent_type: str = Field(default="educational")
    tone: str = Field(default="informative")
    target_audience: str = Field(default="general")
    tool_category: str = Field(default="surreal_realism")
    research_summary: str = Field(default="", description="Summary from research phase")
    is_fictional: bool = Field(default=False)


class ScriptResponse(BaseModel):
    """Response wrapper for script generation results."""
    success: bool = Field(default=True)
    script: Optional[ScriptOutput] = None
    processing_time_seconds: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
