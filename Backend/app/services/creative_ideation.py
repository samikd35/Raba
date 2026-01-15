"""RABA Creative Ideation Service.

Generates story elements, characters, and scenes for fictional/entertainment content.
Does NOT use fact-grounding - pure creative generation.

Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md Step 3
"""

import re
from typing import Optional

from pydantic import BaseModel

from app.config import get_settings
from app.models.research import (
    CharacterDescription,
    CreativeIdeationOutput,
    HybridResearchOutput,
    NarrativeArc,
    ResearchOutput,
    ResearchStrategy,
    SceneIdea,
)
from app.services.gemini import GEMINI_3_PRO, GeminiService, get_gemini_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

CREATIVE_INDICATORS = [
    "what if",
    "imagine",
    "story",
    "fictional",
    "fantasy",
    "dragon",
    "wizard",
    "superhero",
    "magic",
    "alien",
    "robot",
    "future",
    "alternate",
    "parallel universe",
    "time travel",
    "mythical",
    "legend",
    "fairy tale",
    "sci-fi",
    "adventure",
]

FACTUAL_INDICATORS = [
    "how does",
    "how do",
    "what is",
    "history of",
    "science of",
    "explain",
    "why does",
    "facts about",
    "truth about",
    "real",
    "actually",
    "research",
    "study",
    "statistics",
    "data",
    "evidence",
]


class CreativeIdeationError(Exception):
    """Base exception for Creative Ideation errors."""
    pass


class ParsedCreativeOutput(BaseModel):
    """Structured output from creative generation parsing."""
    story_concept: str = ""
    characters: list[dict] = []
    scenes: list[dict] = []
    narrative_arc: dict = {}
    visual_inspiration: list[str] = []
    tone: str = ""
    color_palette: list[str] = []


class CreativeIdeationService:
    """
    Service for generating creative/fictional content.
    
    Used when intent_type is 'entertainment' or topic is clearly fictional.
    NO fact-checking or citations - pure creative generation.
    """
    
    def __init__(self):
        self._gemini_service = get_gemini_service()
    
    def determine_strategy(
        self,
        intent_type: str,
        topic: str,
        tone: str = "",
    ) -> ResearchStrategy:
        """
        Determine the appropriate research strategy based on content type.
        
        Args:
            intent_type: Intent type from Phase 2.1 (educational, entertainment, etc.)
            topic: The topic/prompt from user
            tone: The desired tone
            
        Returns:
            ResearchStrategy enum value
        """
        topic_lower = topic.lower()
        
        if intent_type == "entertainment":
            return ResearchStrategy.CREATIVE
        
        if intent_type in ("educational", "tutorial"):
            creative_score = sum(
                1 for indicator in CREATIVE_INDICATORS
                if indicator in topic_lower
            )
            if creative_score >= 2:
                return ResearchStrategy.HYBRID
            return ResearchStrategy.FACTUAL
        
        if intent_type == "inspirational":
            return ResearchStrategy.HYBRID
        
        creative_score = sum(
            1 for indicator in CREATIVE_INDICATORS
            if indicator in topic_lower
        )
        factual_score = sum(
            1 for indicator in FACTUAL_INDICATORS
            if indicator in topic_lower
        )
        
        if creative_score > factual_score + 1:
            return ResearchStrategy.CREATIVE
        elif factual_score > creative_score:
            return ResearchStrategy.FACTUAL
        else:
            return ResearchStrategy.HYBRID
    
    def _build_creative_prompt(
        self,
        topic: str,
        tool_category: str,
        duration_seconds: int,
        tone: str,
    ) -> str:
        """Build the creative ideation prompt."""
        return f"""You are a master storyteller creating a short video narrative.

Topic: "{topic}"
Visual Style: {tool_category}
Duration: {duration_seconds} seconds
Tone: {tone or "engaging and dynamic"}

Create a compelling short-form video story. Return a JSON response with:

{{
    "story_concept": "Core story premise in 1-2 sentences that hooks viewers instantly",
    "characters": [
        {{
            "name": "Character name",
            "appearance": "Detailed physical appearance",
            "personality": "Key personality traits",
            "role": "protagonist/antagonist/supporting",
            "visual_keywords": ["keyword1", "keyword2"]
        }}
    ],
    "scenes": [
        {{
            "scene_number": 1,
            "timestamp_start": 0.0,
            "timestamp_end": 3.0,
            "description": "What we SEE in this scene - rich visual detail",
            "mood": "Emotional mood/atmosphere",
            "visual_style": "Visual style guidance",
            "key_elements": ["element1", "element2"],
            "suggested_camera": "Camera movement/angle",
            "dialogue": "Optional dialogue if any"
        }}
    ],
    "narrative_arc": {{
        "hook": "Opening hook for first 1-2 seconds",
        "setup": "Situation establishment",
        "conflict": "Central tension or question",
        "climax": "Peak moment",
        "resolution": "Satisfying ending",
        "emotional_beats": ["beat1", "beat2"]
    }},
    "visual_inspiration": ["Art style reference 1", "Mood keyword 2"],
    "tone": "Overall tone description",
    "color_palette": ["color1", "color2", "color3"]
}}

Scene breakdown for {duration_seconds}s video:
- Scene 1 (0-3s): Hook/Opening - grab attention immediately
- Scene 2 (3-8s): Setup/Context - establish the situation
- Scene 3 (8-15s): Development/Conflict - build tension
- Scene 4 (15-{duration_seconds}s): Climax/Resolution - satisfying payoff

Remember: This is FICTION. Be creative, imaginative, and visually stunning.
Do NOT include real-world citations - embrace pure creativity.
Focus on visual storytelling suitable for {tool_category} style."""
    
    async def generate_creative_ideation(
        self,
        topic: str,
        tool_category: str = "surreal_realism",
        duration_seconds: int = 18,
        tone: str = "",
    ) -> CreativeIdeationOutput:
        """
        Generate creative story elements for fictional content.
        
        Args:
            topic: The creative topic/prompt
            tool_category: Visual style category
            duration_seconds: Target video duration
            tone: Desired tone
            
        Returns:
            CreativeIdeationOutput with story, characters, scenes
        """
        prompt = self._build_creative_prompt(
            topic=topic,
            tool_category=tool_category,
            duration_seconds=duration_seconds,
            tone=tone,
        )
        
        logger.info(f"Generating creative ideation for: {topic[:50]}...")
        
        try:
            parsed = await self._gemini_service.generate_structured_output(
                prompt=prompt,
                response_model=ParsedCreativeOutput,
                model=GEMINI_3_PRO,
            )
            
            characters = [
                CharacterDescription(
                    name=c.get("name", "Character"),
                    appearance=c.get("appearance", ""),
                    personality=c.get("personality", ""),
                    role=c.get("role", ""),
                    visual_keywords=c.get("visual_keywords", []),
                )
                for c in parsed.characters
            ]
            
            scenes = [
                SceneIdea(
                    scene_number=s.get("scene_number", i + 1),
                    timestamp_start=s.get("timestamp_start", 0.0),
                    timestamp_end=s.get("timestamp_end", 0.0),
                    description=s.get("description", ""),
                    mood=s.get("mood", ""),
                    visual_style=s.get("visual_style", ""),
                    key_elements=s.get("key_elements", []),
                    suggested_camera=s.get("suggested_camera", ""),
                    dialogue=s.get("dialogue"),
                )
                for i, s in enumerate(parsed.scenes)
            ]
            
            arc_data = parsed.narrative_arc or {}
            narrative_arc = NarrativeArc(
                hook=arc_data.get("hook", ""),
                setup=arc_data.get("setup", ""),
                conflict=arc_data.get("conflict", ""),
                climax=arc_data.get("climax", ""),
                resolution=arc_data.get("resolution", ""),
                emotional_beats=arc_data.get("emotional_beats", []),
            )
            
            return CreativeIdeationOutput(
                story_concept=parsed.story_concept,
                characters=characters,
                scenes=scenes,
                narrative_arc=narrative_arc,
                visual_inspiration=parsed.visual_inspiration,
                tone=parsed.tone or tone,
                color_palette=parsed.color_palette,
                is_fictional=True,
                citations=[],
                strategy_used=ResearchStrategy.CREATIVE,
            )
            
        except Exception as e:
            logger.error(f"Creative ideation failed: {e}")
            return CreativeIdeationOutput(
                story_concept=f"A creative story about: {topic}",
                characters=[],
                scenes=[
                    SceneIdea(
                        scene_number=1,
                        description=f"Visual interpretation of {topic}",
                        mood="engaging",
                        visual_style=tool_category,
                        key_elements=[topic],
                    )
                ],
                narrative_arc=NarrativeArc(
                    hook=f"Discover {topic}",
                    conflict="The journey unfolds",
                    resolution="A satisfying conclusion",
                ),
                visual_inspiration=[tool_category],
                tone=tone or "engaging",
                is_fictional=True,
                strategy_used=ResearchStrategy.CREATIVE,
            )
    
    async def generate_hybrid_content(
        self,
        topic: str,
        factual_research: ResearchOutput,
        tool_category: str = "surreal_realism",
        duration_seconds: int = 18,
        tone: str = "",
    ) -> HybridResearchOutput:
        """
        Generate hybrid content combining factual research with creative extension.
        
        Args:
            topic: The topic
            factual_research: Pre-existing factual research
            tool_category: Visual style
            duration_seconds: Video duration
            tone: Desired tone
            
        Returns:
            HybridResearchOutput combining facts and fiction
        """
        facts_summary = factual_research.executive_summary
        if factual_research.research_findings:
            key_facts = []
            for finding in factual_research.research_findings[:3]:
                key_facts.extend(finding.key_facts[:2])
            facts_summary += "\nKey facts: " + "; ".join(key_facts[:5])
        
        creative_prompt = f"""Based on these real facts about "{topic}":

{facts_summary}

Now imagine a creative, fictional scenario that builds on these facts.
Create an engaging story that:
1. Uses the real facts as a foundation
2. Extends into imaginative "what if" territory
3. Creates compelling characters and scenes
4. Maintains visual appeal for {tool_category} style

Generate the creative extension as if the facts enable a fictional journey."""
        
        logger.info(f"Generating hybrid content for: {topic[:50]}...")
        
        creative_extension = await self.generate_creative_ideation(
            topic=creative_prompt,
            tool_category=tool_category,
            duration_seconds=duration_seconds,
            tone=tone,
        )
        
        blend_points = [
            f"Factual base: {factual_research.executive_summary[:100]}...",
            f"Creative extension begins with: {creative_extension.story_concept[:100]}...",
        ]
        
        return HybridResearchOutput(
            factual_base=factual_research,
            creative_extension=creative_extension,
            blend_points=blend_points,
            strategy_used=ResearchStrategy.HYBRID,
            is_fictional=False,
        )


_creative_ideation_service: Optional[CreativeIdeationService] = None


def get_creative_ideation_service() -> CreativeIdeationService:
    """Get singleton Creative Ideation service instance."""
    global _creative_ideation_service
    if _creative_ideation_service is None:
        _creative_ideation_service = CreativeIdeationService()
    return _creative_ideation_service
