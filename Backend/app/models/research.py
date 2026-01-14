"""RABA Research Models.

Pydantic models for Deep Research Agent output, including:
- Factual research with citations (ResearchOutput)
- Creative/fictional content (CreativeIdeationOutput)
- Hybrid content (HybridResearchOutput)

Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ResearchStrategy(str, Enum):
    """Research strategy based on content type."""
    FACTUAL = "factual"      # Deep Research with Google Search grounding
    CREATIVE = "creative"    # Gemini Pro without grounding (fictional)
    HYBRID = "hybrid"        # Factual base + creative extension


class Citation(BaseModel):
    """A citation from research sources."""
    source: str = Field(..., description="Source name or publication")
    url: str = Field(..., description="URL to the source")
    quote: Optional[str] = Field(default=None, description="Relevant quote from source")


class ResearchFinding(BaseModel):
    """A single research finding with supporting facts."""
    topic_segment: str = Field(..., description="The sub-topic this finding covers")
    key_facts: list[str] = Field(default_factory=list, description="Key facts discovered")
    citations: list[Citation] = Field(default_factory=list, description="Supporting citations")
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.7-1.0 for grounded research)"
    )


class ResearchImage(BaseModel):
    """A reference image found during research."""
    url: str = Field(..., description="Original image URL")
    storage_path: str = Field(..., description="Path in Supabase Storage")
    storage_url: str = Field(..., description="Public URL from Supabase Storage")
    title: str = Field(default="", description="Image title or description")
    source_url: str = Field(default="", description="Source page URL")


class ResearchOutput(BaseModel):
    """Output from factual research using Gemini Deep Research Agent.
    
    Reference: RABA_Architecture.md Section 2.4
    """
    research_findings: list[ResearchFinding] = Field(
        default_factory=list,
        description="List of research findings with citations"
    )
    research_images: list[ResearchImage] = Field(
        default_factory=list,
        description="Reference images found during research"
    )
    research_depth_used: str = Field(
        default="standard",
        description="Research depth: quick, standard, or deep"
    )
    total_sources: int = Field(default=0, description="Total number of sources cited")
    cache_hit: bool = Field(default=False, description="Whether result came from cache")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )
    interaction_id: Optional[str] = Field(
        default=None,
        description="Gemini Interactions API ID for follow-up queries"
    )
    strategy_used: ResearchStrategy = Field(
        default=ResearchStrategy.FACTUAL,
        description="Research strategy that was used"
    )
    is_fictional: bool = Field(
        default=False,
        description="Whether content is fictional (always False for ResearchOutput)"
    )
    
    executive_summary: str = Field(
        default="",
        description="2-3 sentence summary of key insights"
    )
    visual_elements: list[str] = Field(
        default_factory=list,
        description="Visual elements suitable for video"
    )
    interesting_angles: list[str] = Field(
        default_factory=list,
        description="Unique perspectives for viral content"
    )


class CharacterDescription(BaseModel):
    """A character description for creative/fictional content."""
    name: str = Field(..., description="Character name")
    appearance: str = Field(..., description="Physical appearance description")
    personality: str = Field(default="", description="Personality traits")
    role: str = Field(default="", description="Role in the story (protagonist, etc.)")
    visual_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords for image generation"
    )


class SceneIdea(BaseModel):
    """A scene idea for creative content."""
    scene_number: int = Field(..., description="Scene order (1-indexed)")
    timestamp_start: float = Field(default=0.0, description="Start time in seconds")
    timestamp_end: float = Field(default=0.0, description="End time in seconds")
    description: str = Field(..., description="Visual description of the scene")
    mood: str = Field(default="", description="Emotional mood/atmosphere")
    visual_style: str = Field(default="", description="Visual style guidance")
    key_elements: list[str] = Field(
        default_factory=list,
        description="Key visual elements in the scene"
    )
    suggested_camera: str = Field(
        default="",
        description="Camera movement/angle suggestion"
    )
    dialogue: Optional[str] = Field(
        default=None,
        description="Optional dialogue for this scene"
    )


class NarrativeArc(BaseModel):
    """Narrative arc structure for storytelling."""
    hook: str = Field(..., description="Opening hook (first 1-2 seconds)")
    setup: str = Field(default="", description="Situation establishment")
    conflict: str = Field(default="", description="Central tension or question")
    climax: str = Field(default="", description="Peak moment")
    resolution: str = Field(default="", description="Satisfying ending")
    emotional_beats: list[str] = Field(
        default_factory=list,
        description="Key emotional moments throughout"
    )


class CreativeIdeationOutput(BaseModel):
    """Output from creative ideation for fictional/entertainment content.
    
    Used when intent_type is 'entertainment' or topic is clearly fictional.
    NO fact-checking or citations - pure creative generation.
    """
    story_concept: str = Field(..., description="Core story premise (1-2 sentences)")
    characters: list[CharacterDescription] = Field(
        default_factory=list,
        description="Characters in the story"
    )
    scenes: list[SceneIdea] = Field(
        default_factory=list,
        description="Scene breakdown for video"
    )
    narrative_arc: NarrativeArc = Field(
        ...,
        description="Story structure"
    )
    visual_inspiration: list[str] = Field(
        default_factory=list,
        description="Art style references and mood keywords"
    )
    tone: str = Field(default="", description="Overall tone (dramatic, humorous, etc.)")
    color_palette: list[str] = Field(
        default_factory=list,
        description="Suggested color palette"
    )
    
    is_fictional: bool = Field(
        default=True,
        description="Always True for creative content"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Always empty for creative content"
    )
    strategy_used: ResearchStrategy = Field(
        default=ResearchStrategy.CREATIVE,
        description="Always CREATIVE for this output type"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )
    cache_hit: bool = Field(default=False, description="Whether result came from cache")


class HybridResearchOutput(BaseModel):
    """Output combining factual research with creative extension.
    
    Used for topics like "What if Einstein met Tesla?" where we need:
    - Factual base (who they were, what they did)
    - Creative extension (imagined interaction)
    """
    factual_base: ResearchOutput = Field(
        ...,
        description="Grounded factual research"
    )
    creative_extension: CreativeIdeationOutput = Field(
        ...,
        description="Creative speculation built on facts"
    )
    blend_points: list[str] = Field(
        default_factory=list,
        description="Where facts transition to fiction"
    )
    
    strategy_used: ResearchStrategy = Field(
        default=ResearchStrategy.HYBRID,
        description="Always HYBRID for this output type"
    )
    is_fictional: bool = Field(
        default=False,
        description="False because it contains factual base"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )
    cache_hit: bool = Field(default=False, description="Whether result came from cache")


# Type alias for any research output type
ResearchResult = ResearchOutput | CreativeIdeationOutput | HybridResearchOutput


class ResearchRequest(BaseModel):
    """Request model for research operations."""
    topic: str = Field(..., description="Topic to research")
    intent_type: str = Field(
        default="educational",
        description="Intent type from Phase 2.1"
    )
    tone: str = Field(default="informative", description="Desired tone")
    tool_category: str = Field(
        default="surreal_realism",
        description="Visual style category"
    )
    duration_seconds: int = Field(default=18, ge=8, le=25)
    research_depth: str = Field(
        default="standard",
        description="Research depth: quick, standard, deep"
    )
    force_strategy: Optional[ResearchStrategy] = Field(
        default=None,
        description="Force a specific strategy (overrides auto-detection)"
    )


class ResearchResponse(BaseModel):
    """Response wrapper for research results."""
    success: bool = Field(default=True)
    strategy_used: ResearchStrategy
    result: ResearchResult
    processing_time_seconds: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
