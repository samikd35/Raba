"""RABA Script Writer Agent.

Generates viral-optimized scripts for YouTube Shorts (8-25 seconds).
Transforms research output into hooks, scenes, pattern interrupts, and CTAs.

Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md, RABA_Architecture.md Section 2.5
Prompting: Backend/Documentations/prompting_Docs.md
"""

import math
import time
from typing import Any, Optional

from app.graph.state import VideoGenerationState
from app.models.research import (
    CreativeIdeationOutput,
    HybridResearchOutput,
    ResearchOutput,
    ResearchStrategy,
)
from app.models.script import (
    CTASection,
    CTAType,
    HookArchetype,
    HookSection,
    PatternInterruptType,
    Scene,
    ScriptOutput,
    ViralMetrics,
)
from app.services.gemini import GEMINI_3_FLASH, get_gemini_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


TOOL_VISUAL_VOCABULARY = {
    "surreal_realism": {
        "style_keywords": [
            "flowing liquid-glass",
            "photorealistic grounding",
            "impossible physics",
            "tangible phenomenon",
            "color gradients",
            "scientific wonder",
        ],
        "camera_styles": [
            "slow macro zoom",
            "floating perspective",
            "seamless transition",
        ],
        "mood_keywords": [
            "awe-inspiring",
            "mysterious",
            "scientifically beautiful",
        ],
    },
    "high_octane_anime": {
        "style_keywords": [
            "Sakuga-style",
            "ink-splashes",
            "elemental explosions",
            "dynamic motion lines",
            "calligraphic combat",
            "philosophical duel",
        ],
        "camera_styles": [
            "rapid cuts",
            "dynamic tracking",
            "impact frames",
        ],
        "mood_keywords": [
            "intense",
            "epic",
            "philosophical",
        ],
    },
    "stylized_3d": {
        "style_keywords": [
            "miniature landscape",
            "data diorama",
            "clean 3D aesthetic",
            "isometric view",
            "stylized materials",
        ],
        "camera_styles": [
            "orbital rotation",
            "tilt-shift effect",
            "smooth dolly",
        ],
        "mood_keywords": [
            "clean",
            "informative",
            "visually organized",
        ],
    },
}

HOOK_ARCHETYPE_MAP = {
    "educational": [HookArchetype.TEACHER, HookArchetype.FORTUNETELLER],
    "entertainment": [HookArchetype.STORYTELLER, HookArchetype.DISRUPTOR],
    "inspirational": [HookArchetype.FORTUNETELLER, HookArchetype.STORYTELLER],
    "tutorial": [HookArchetype.TEACHER, HookArchetype.FORTUNETELLER],
}


def _build_system_instruction() -> str:
    """Build system instruction following prompting best practices.
    
    Reference: prompting_Docs.md - Use XML tags, be precise and direct.
    """
    return """<role>
You are Gemini 3, a specialized viral short-form video scriptwriter for YouTube Shorts.
You create scripts optimized for maximum viewer retention and engagement.
You are precise, creative, and understand viral content psychology.
</role>

<instructions>
1. **Analyze**: Understand the topic, research data, and target audience.
2. **Plan**: Structure the script with hook, scenes, pattern interrupts, and CTA.
3. **Execute**: Generate rich, sensory descriptions with precise timing.
4. **Optimize**: Ensure viral elements are present (curiosity gap, emotional beats).
</instructions>

<constraints>
- Verbosity: Medium (rich descriptions but concise dialogue)
- Tone: Match the requested tone from context
- Duration: MUST match the exact requested duration
- Pattern interrupts: Place every 3-5 seconds to maintain attention
- Dialogue: Short, punchy phrases suitable for short-form video
</constraints>

<output_format>
Return valid JSON matching the ScriptOutput schema exactly.
All timestamps must be precise and add up to the total duration.
</output_format>"""


def _build_hook_prompt(
    topic: str,
    intent_type: str,
    tone: str,
    target_audience: str,
    research_summary: str,
    selected_archetype: HookArchetype,
    tool_category: str,
) -> str:
    """Build prompt for hook generation.
    
    Reference: prompting_Docs.md - Context first, then task at end.
    """
    tool_vocab = TOOL_VISUAL_VOCABULARY.get(tool_category, TOOL_VISUAL_VOCABULARY["surreal_realism"])
    
    return f"""<context>
Topic: {topic}
Intent Type: {intent_type}
Tone: {tone}
Target Audience: {target_audience}
Visual Style: {tool_category}

Research Summary:
{research_summary}

Tool Visual Keywords: {', '.join(tool_vocab['style_keywords'])}
</context>

<examples>
Example 1 (TEACHER archetype for educational):
{{
  "archetype": "teacher",
  "script": "You've been understanding gravity wrong. Here's the truth.",
  "visual_direction": "Close-up of floating water droplet, camera slowly pulls back to reveal astronaut in space station",
  "duration_seconds": 2.0,
  "psychological_lever": "curiosity_gap",
  "estimated_vvsa_impact": 0.85
}}

Example 2 (STORYTELLER archetype for entertainment):
{{
  "archetype": "storyteller",
  "script": "Nobody expected what happened next.",
  "visual_direction": "Dark silhouette against dramatic sunset, face slowly illuminated",
  "duration_seconds": 2.0,
  "psychological_lever": "curiosity_gap",
  "estimated_vvsa_impact": 0.82
}}

Example 3 (DISRUPTOR archetype for contrarian):
{{
  "archetype": "disruptor",
  "script": "Everything you know about sleep is wrong.",
  "visual_direction": "Person jolting awake, clock showing 3AM, eerie blue lighting",
  "duration_seconds": 1.5,
  "psychological_lever": "fomo",
  "estimated_vvsa_impact": 0.88
}}
</examples>

<task>
Generate a viral hook for this video using the {selected_archetype.value.upper()} archetype.

Requirements:
1. Script must be under 10 words, spoken confidently
2. Visual direction must immediately capture attention
3. Use {tool_category} visual style vocabulary
4. Duration should be 1.5-2.5 seconds
5. Choose appropriate psychological lever (curiosity_gap, fomo, relatability, dopamine)

Return ONLY valid JSON matching the HookSection schema.
</task>"""


def _build_scenes_prompt(
    topic: str,
    duration_seconds: int,
    hook_duration: float,
    research_summary: str,
    intent_type: str,
    tone: str,
    tool_category: str,
    scene_count: int,
    is_fictional: bool,
) -> str:
    """Build prompt for scene generation.
    
    Reference: prompting_Docs.md - Structured prompts with clear examples.
    """
    tool_vocab = TOOL_VISUAL_VOCABULARY.get(tool_category, TOOL_VISUAL_VOCABULARY["surreal_realism"])
    remaining_duration = duration_seconds - hook_duration - 1.5  # Reserve 1.5s for CTA
    avg_scene_duration = remaining_duration / scene_count
    
    content_type = "fictional/creative" if is_fictional else "factual/educational"
    
    return f"""<context>
Topic: {topic}
Content Type: {content_type}
Total Duration: {duration_seconds} seconds
Hook Duration: {hook_duration} seconds
CTA Duration: 1.5 seconds
Remaining for Scenes: {remaining_duration} seconds
Number of Scenes Needed: {scene_count}
Average Scene Duration: {avg_scene_duration:.1f} seconds

Intent Type: {intent_type}
Tone: {tone}
Visual Style: {tool_category}

Research/Story Summary:
{research_summary}

Style Keywords: {', '.join(tool_vocab['style_keywords'])}
Camera Styles: {', '.join(tool_vocab['camera_styles'])}
Mood Keywords: {', '.join(tool_vocab['mood_keywords'])}
</context>

<pattern_interrupt_rules>
- Place a pattern interrupt every 3-5 seconds
- Vary interrupt types to prevent habituation
- Types: scene_change, visual_effect, new_fact, perspective_shift, emotional_pivot, sensory_cue
- First scene after hook: usually visual_effect or new_fact
- Middle scenes: perspective_shift or emotional_pivot
- Pre-climax scene: sensory_cue or emotional_pivot
</pattern_interrupt_rules>

<scene_requirements>
1. **Specificity**: Use precise descriptions ("shuffling with hunched shoulders" not "walking sadly")
2. **Sensory Detail**: Include light, texture, atmosphere, sound
3. **Emotional Triggers**: Authenticity, relatability, aspirational elements
4. **Dialogue**: Short phrases, natural speech patterns, max 15 words per scene
5. **Visual Keywords**: Include 3-5 keywords for image/video generation
</scene_requirements>

<example_scene>
{{
  "scene_number": 1,
  "timestamp_start": 2.0,
  "timestamp_end": 5.5,
  "description": "Camera pushes through swirling cosmic dust, revealing a massive black hole. Light bends impossibly around its edge, creating rainbow halos.",
  "dialogue": "But here's what nobody tells you about black holes.",
  "audio_cues": ["deep rumbling bass", "ethereal synth pad"],
  "camera_direction": "slow push-in with gentle rotation",
  "lighting": "dramatic rim lighting with purple and orange gradients",
  "mood": "awe-inspiring, mysterious",
  "pattern_interrupt_type": "new_fact",
  "visual_keywords": ["black hole", "cosmic dust", "light bending", "rainbow halo", "space"]
}}
</example_scene>

<task>
Generate exactly {scene_count} scenes for this video.

Critical Requirements:
1. Scene 1 starts at timestamp {hook_duration} seconds
2. Last scene ends at timestamp {duration_seconds - 1.5} seconds (before CTA)
3. Timestamps must be continuous (no gaps)
4. Each scene should be roughly {avg_scene_duration:.1f} seconds
5. Include pattern interrupts every 3-5 seconds
6. Use {tool_category} visual vocabulary throughout
7. Match the {tone} tone consistently

Return ONLY a valid JSON array of Scene objects.
</task>"""


def _build_full_script_prompt(
    topic: str,
    duration_seconds: int,
    research_summary: str,
    intent_type: str,
    tone: str,
    target_audience: str,
    tool_category: str,
    is_fictional: bool,
) -> str:
    """Build prompt for complete script generation in one call.
    
    Reference: prompting_Docs.md - Comprehensive prompt with all context.
    """
    tool_vocab = TOOL_VISUAL_VOCABULARY.get(tool_category, TOOL_VISUAL_VOCABULARY["surreal_realism"])
    
    archetypes = HOOK_ARCHETYPE_MAP.get(intent_type, [HookArchetype.TEACHER])
    recommended_archetype = archetypes[0].value
    
    scene_count = max(2, math.ceil(duration_seconds / 4))
    content_type = "fictional/creative" if is_fictional else "factual/educational"
    
    return f"""<context>
# Video Parameters
- Topic: {topic}
- Duration: {duration_seconds} seconds
- Content Type: {content_type}
- Intent: {intent_type}
- Tone: {tone}
- Target Audience: {target_audience}
- Visual Style: {tool_category}

# Research/Story Content
{research_summary}

# Tool Visual Vocabulary
Style Keywords: {', '.join(tool_vocab['style_keywords'])}
Camera Styles: {', '.join(tool_vocab['camera_styles'])}
Mood Keywords: {', '.join(tool_vocab['mood_keywords'])}
</context>

<viral_structure>
Timeline for {duration_seconds} second video:
- 0:00-0:02: HOOK (strongest opening, stop the scroll)
- 0:02-{duration_seconds-2}: SCENES with pattern interrupts every 3-5s
- {duration_seconds-2}:00-{duration_seconds}:00: CTA (satisfying conclusion + call-to-action)

Pattern Interrupt Types (vary these):
- scene_change: New location/subject
- visual_effect: Transition, animation shift  
- new_fact: Information reveal
- perspective_shift: Different angle/interpretation
- emotional_pivot: Mood change
- sensory_cue: Sound/visual surprise
</viral_structure>

<example_output>
{{
  "hook": {{
    "archetype": "teacher",
    "script": "You've been understanding this wrong.",
    "visual_direction": "Extreme close-up of eye, camera pulls back rapidly",
    "duration_seconds": 2.0,
    "psychological_lever": "curiosity_gap",
    "estimated_vvsa_impact": 0.85
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "timestamp_start": 2.0,
      "timestamp_end": 6.0,
      "description": "Rich visual description with sensory details...",
      "dialogue": "Short punchy dialogue here.",
      "audio_cues": ["ambient sound", "music cue"],
      "camera_direction": "camera movement description",
      "lighting": "lighting description",
      "mood": "emotional tone",
      "pattern_interrupt_type": "new_fact",
      "visual_keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ],
  "call_to_action": {{
    "type": "follow",
    "placement_seconds": {duration_seconds - 1.5},
    "script": "Follow for more.",
    "visual_direction": "Logo animation with subscribe button"
  }},
  "viral_metrics": {{
    "hook_strength": 0.85,
    "pattern_interrupt_density": 0.80,
    "emotional_arc": 0.75,
    "call_to_action_clarity": 0.80,
    "audience_fit": 0.75,
    "novelty_factor": 0.70
  }},
  "estimated_completion_rate": 0.72,
  "viral_score": 0.78,
  "total_duration_seconds": {duration_seconds},
  "tool_category_applied": "{tool_category}"
}}
</example_output>

<task>
Generate a complete viral script for this {duration_seconds}-second YouTube Short.

Requirements:
1. Hook: Use {recommended_archetype.upper()} archetype, 1.5-2.5 seconds
2. Scenes: Generate {scene_count} scenes with continuous timestamps
3. Pattern Interrupts: Place every 3-5 seconds, vary types
4. CTA: Natural call-to-action in final 1.5 seconds
5. Visual Style: Use {tool_category} vocabulary throughout
6. Dialogue: Short, punchy (max 15 words per scene)
7. Total Duration: Timestamps MUST add up to exactly {duration_seconds} seconds

Return ONLY valid JSON matching the ScriptOutput schema.
</task>

<final_instruction>
Before responding, verify:
1. Hook duration + all scene durations + CTA duration = {duration_seconds} seconds
2. All timestamps are continuous with no gaps
3. Pattern interrupts appear every 3-5 seconds
4. Visual descriptions use {tool_category} style vocabulary
</final_instruction>"""


def _extract_research_summary(research_data: dict[str, Any]) -> tuple[str, bool]:
    """Extract summary from research data (factual, creative, or hybrid)."""
    strategy = research_data.get("strategy_used", "factual")
    is_fictional = research_data.get("is_fictional", False)
    
    if strategy == "creative" or strategy == ResearchStrategy.CREATIVE.value:
        story_concept = research_data.get("story_concept", "")
        narrative = research_data.get("narrative_arc", {})
        hook = narrative.get("hook", "") if isinstance(narrative, dict) else ""
        characters = research_data.get("characters", [])
        char_names = [c.get("name", "") for c in characters[:3]] if characters else []
        
        summary = f"""Story Concept: {story_concept}
Opening Hook: {hook}
Characters: {', '.join(char_names) if char_names else 'Various'}
Tone: {research_data.get('tone', 'dramatic')}
Visual Style: {', '.join(research_data.get('visual_inspiration', [])[:3])}"""
        return summary, True
        
    elif strategy == "hybrid" or strategy == ResearchStrategy.HYBRID.value:
        factual = research_data.get("factual_base", {})
        creative = research_data.get("creative_extension", {})
        
        findings = factual.get("research_findings", [])
        facts = []
        for f in findings[:3]:
            if isinstance(f, dict):
                facts.extend(f.get("key_facts", [])[:2])
        
        story = creative.get("story_concept", "")
        
        summary = f"""Factual Base:
{chr(10).join(['- ' + fact for fact in facts[:5]])}

Creative Extension: {story}
Blend Points: {', '.join(research_data.get('blend_points', [])[:3])}"""
        return summary, False
        
    else:
        findings = research_data.get("research_findings", [])
        facts = []
        for f in findings:
            if isinstance(f, dict):
                facts.extend(f.get("key_facts", [])[:3])
        
        exec_summary = research_data.get("executive_summary", "")
        angles = research_data.get("interesting_angles", [])
        
        summary = f"""Executive Summary: {exec_summary}

Key Facts:
{chr(10).join(['- ' + fact for fact in facts[:6]])}

Interesting Angles: {', '.join(angles[:3]) if angles else 'Standard approach'}"""
        return summary, False


def _calculate_scene_count(duration_seconds: int) -> int:
    """Calculate optimal number of scenes based on duration."""
    return max(2, min(8, math.ceil(duration_seconds / 4)))


def _calculate_viral_metrics(script: ScriptOutput) -> ViralMetrics:
    """Calculate viral metrics for the generated script."""
    metrics = ViralMetrics()
    
    hook_duration = script.hook.duration_seconds
    if hook_duration <= 2.5:
        metrics.hook_strength = 0.85
    elif hook_duration <= 3.0:
        metrics.hook_strength = 0.75
    else:
        metrics.hook_strength = 0.60
    
    if "?" in script.hook.script:
        metrics.hook_strength = min(1.0, metrics.hook_strength + 0.05)
    
    interrupt_count = sum(1 for s in script.scenes if s.pattern_interrupt_type)
    expected_interrupts = len(script.scenes)
    metrics.pattern_interrupt_density = min(1.0, interrupt_count / max(1, expected_interrupts))
    
    if len(script.scenes) >= 2:
        has_setup = any("setup" in s.mood.lower() or s.scene_number == 1 for s in script.scenes)
        has_climax = any("climax" in s.mood.lower() or "intense" in s.mood.lower() for s in script.scenes)
        metrics.emotional_arc = 0.5 + (0.25 if has_setup else 0) + (0.25 if has_climax else 0)
    else:
        metrics.emotional_arc = 0.5
    
    if script.call_to_action.script:
        metrics.call_to_action_clarity = 0.80
    else:
        metrics.call_to_action_clarity = 0.60
    
    metrics.audience_fit = 0.75
    metrics.novelty_factor = 0.70
    
    return metrics


class ScriptWriterAgent:
    """
    Script Writer Agent for generating viral YouTube Shorts scripts.
    
    Transforms research output into structured scripts with:
    - Viral hooks (first 1-2 seconds)
    - Scenes with visual directions
    - Pattern interrupts (every 3-5 seconds)
    - Call-to-action
    
    Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md
    """
    
    def __init__(self):
        """Initialize Script Writer Agent."""
        self.gemini = get_gemini_service()
        logger.info("ScriptWriterAgent initialized")
    
    async def generate_script(
        self,
        topic: str,
        duration_seconds: int,
        research_data: dict[str, Any],
        intent_type: str = "educational",
        tone: str = "informative",
        target_audience: str = "general",
        tool_category: str = "surreal_realism",
    ) -> ScriptOutput:
        """
        Generate a complete viral script.
        
        Args:
            topic: Video topic
            duration_seconds: Target duration (8-25)
            research_data: Output from Deep Research agent
            intent_type: Content intent type
            tone: Desired tone
            target_audience: Target audience
            tool_category: Visual style category
            
        Returns:
            Complete ScriptOutput
        """
        logger.info(f"Generating script for: {topic[:50]}...")
        logger.info(f"Duration: {duration_seconds}s, Tool: {tool_category}")
        
        start_time = time.time()
        
        research_summary, is_fictional = _extract_research_summary(research_data)
        
        prompt = _build_full_script_prompt(
            topic=topic,
            duration_seconds=duration_seconds,
            research_summary=research_summary,
            intent_type=intent_type,
            tone=tone,
            target_audience=target_audience,
            tool_category=tool_category,
            is_fictional=is_fictional,
        )
        
        system_instruction = _build_system_instruction()
        
        try:
            script = await self.gemini.generate_structured_output(
                prompt=prompt,
                response_model=ScriptOutput,
                model=GEMINI_3_FLASH,
                system_instruction=system_instruction,
                temperature=1.0,
            )
            
            script.viral_metrics = _calculate_viral_metrics(script)
            script.viral_score = script.viral_metrics.calculate_viral_score()
            script.estimated_completion_rate = min(0.98, 0.4 + script.viral_score * 0.5)
            script.tool_category_applied = tool_category
            
            elapsed = time.time() - start_time
            logger.info(f"Script generated in {elapsed:.2f}s")
            logger.info(f"Viral score: {script.viral_score:.2f}")
            logger.info(f"Scenes: {len(script.scenes)}")
            
            return script
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            raise
    
    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        """
        Run script generation from workflow state.
        
        Args:
            state: Current workflow state
            
        Returns:
            State update dict with script output
        """
        topic = state.get("topic", "")
        duration_seconds = state.get("duration_seconds", 18)
        research_data = state.get("research_data", {})
        intent_metadata = state.get("intent_metadata", {})
        selected_tool = state.get("selected_tool", {})
        
        intent_type = intent_metadata.get("intent_type", "educational")
        if hasattr(intent_type, "value"):
            intent_type = intent_type.value
            
        tone = intent_metadata.get("tone", "informative")
        if hasattr(tone, "value"):
            tone = tone.value
            
        target_audience = intent_metadata.get("target_audience", "general")
        if hasattr(target_audience, "value"):
            target_audience = target_audience.value
        
        tool_category = selected_tool.get("category", "surreal_realism")
        if hasattr(tool_category, "value"):
            tool_category = tool_category.value
        
        script = await self.generate_script(
            topic=topic,
            duration_seconds=duration_seconds,
            research_data=research_data,
            intent_type=intent_type,
            tone=tone,
            target_audience=target_audience,
            tool_category=tool_category,
        )
        
        return {
            "script_output": script.model_dump(),
            "hook": script.hook.model_dump(),
            "scenes": [s.model_dump() for s in script.scenes],
            "call_to_action": script.call_to_action.model_dump(),
            "viral_score": script.viral_score,
        }


_script_writer_agent: Optional[ScriptWriterAgent] = None


def get_script_writer_agent() -> ScriptWriterAgent:
    """Get singleton Script Writer Agent instance."""
    global _script_writer_agent
    if _script_writer_agent is None:
        _script_writer_agent = ScriptWriterAgent()
    return _script_writer_agent
