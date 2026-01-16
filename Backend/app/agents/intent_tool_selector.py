"""RABA Intent/Tool Selector Agent.

Extracts intent from user topic, validates parameters, and selects optimal tool.
This is the FIRST agent in the workflow - all other agents depend on its output.
"""

from typing import Optional

from app.config import get_settings
from app.models.tool import (
    IntentExtractionResponse,
    IntentMetadata,
    IntentToolOutput,
    IntentType,
    TargetAudience,
    ToneType,
    ToolCapabilities,
    ToolMetadata,
    ToolScore,
    UserReferenceMode,
    ValidatedParams,
)
from app.models.workflow import (
    AspectRatioEnum,
    CategoryEnum,
    ResolutionEnum,
    WorkflowInput,
)
from app.services.gemini import GeminiService, get_gemini_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IntentToolSelectorError(Exception):
    """Base exception for Intent/Tool Selector errors."""
    pass


class ToolNotFoundError(IntentToolSelectorError):
    """No suitable tool found."""
    pass


INTENT_EXTRACTION_SYSTEM_PROMPT = """<role>
You are an expert video content strategist specializing in YouTube Shorts.
Your task is to analyze topics and determine the optimal video generation approach.
You understand viral content, engagement patterns, and audience psychology.
</role>

<constraints>
1. Always infer intent from context - never ask for clarification
2. Be precise and direct in classification
3. Consider viral potential when determining tone
4. Extract 3-7 relevant keywords for tool matching
5. Assess topic complexity honestly (0=simple explainer, 1=deep technical)
</constraints>

<output_format>
Return a structured JSON response with:
- intent_type: educational | entertainment | inspirational | tutorial
- target_audience: general | tech | science | business
- tone: serious | humorous | dramatic | casual
- keywords: list of 3-7 key terms
- complexity_score: 0.0 to 1.0
- reasoning: brief explanation
</output_format>"""


INTENT_EXTRACTION_PROMPT_TEMPLATE = """<context>
Topic: {topic}
Duration: {duration_seconds} seconds
Category Preference: {category} (auto = AI decides best category)
</context>

<task>
Analyze this topic for YouTube Shorts video generation:

1. **Intent Type**: What is the primary purpose?
   - educational: Teaching facts, explaining concepts
   - entertainment: Fun, engaging, surprising content
   - inspirational: Motivating, emotional, aspirational
   - tutorial: Step-by-step how-to

2. **Target Audience**: Who would watch this?
   - general: Broad appeal, mainstream
   - tech: Technology enthusiasts
   - science: Science-curious viewers
   - business: Professionals, entrepreneurs

3. **Tone**: What tone maximizes viral potential for this topic?
   - serious: Authoritative, factual
   - humorous: Funny, witty, entertaining
   - dramatic: Intense, emotional, surprising
   - casual: Friendly, conversational

4. **Keywords**: Extract 3-7 key terms that define this topic

5. **Complexity**: Rate from 0.0 (simple) to 1.0 (complex)
</task>

<examples>
Topic: "How black holes actually work"
→ intent_type: educational, audience: science, tone: dramatic, complexity: 0.7

Topic: "Why cats always land on their feet"  
→ intent_type: entertainment, audience: general, tone: humorous, complexity: 0.3

Topic: "The forgotten scientist who changed everything"
→ intent_type: inspirational, audience: science, tone: dramatic, complexity: 0.5
</examples>

<final_instruction>
Think step-by-step about what would make "{topic}" most engaging for YouTube Shorts.
</final_instruction>"""


TOOL_RELEVANCE_SYSTEM_PROMPT = """You are a video production expert evaluating tool-topic fit.
Rate how well a video generation tool matches a given topic.
Consider visual style, capabilities, and audience expectations.
Return only a JSON with relevance_score (0.0-1.0) and brief reasoning."""


TOOL_RELEVANCE_PROMPT_TEMPLATE = """Rate the relevance of this video generation tool for the topic:

**Tool**: {tool_name}
**Description**: {tool_description}
**Visual Style**: {tool_capabilities}
**Best For**: {example_topics}

**Topic**: {topic}
**Intent**: {intent_type}
**Keywords**: {keywords}

Score 0.0-1.0:
- 1.0 = Perfect match (tool is ideal for this topic type)
- 0.7+ = Good match (tool can handle this well)
- 0.4-0.7 = Acceptable (usable but not optimal)
- <0.4 = Poor match (tool style doesn't fit)"""


DEFAULT_TOOLS: list[ToolMetadata] = [
    ToolMetadata(
        tool_id="surreal_impossible_sims",
        tool_name="Impossible Simulations",
        category=CategoryEnum.SURREAL_REALISM,
        description="Visualize invisible forces and impossible physical phenomena with photorealistic grounding. Perfect for science, physics, and 'what if' scenarios.",
        capabilities=ToolCapabilities(
            flow_visualization=True,
            invisible_forces=True,
            photorealistic_grounding=True,
            viral_signal="Information without Boredom",
        ),
        example_topics=[
            "How magnets work",
            "What happens inside a black hole",
            "Visualizing quantum mechanics",
            "The physics of sound waves",
        ],
        video_prompt_template="""Visualize the invisible forces in {topic} using flowing, liquid-glass aesthetics.
Show {element} as a tangible phenomenon with color gradients representing {attribute}.
Photorealistic grounding while depicting impossible physical phenomena.
Maintain scientific accuracy with visual wonder. Focus on {focus_area}.""",
        cost_per_request=0.5,
        estimated_quality=0.9,
    ),
    ToolMetadata(
        tool_id="anime_concept_combat",
        tool_name="Concept Combat",
        category=CategoryEnum.HIGH_OCTANE_ANIME,
        description="Transform abstract ideas into high-energy Sakuga-style battles. Ideal for philosophy, debates, historical conflicts, and conceptual showdowns.",
        capabilities=ToolCapabilities(
            philosophical_debates=True,
            sakuga_style=True,
            calligraphic_combat=True,
            viral_signal="Zen-Action",
        ),
        example_topics=[
            "Plato vs Aristotle",
            "Nature vs Nurture debate",
            "The battle between good and evil",
            "Science vs Religion",
        ],
        video_prompt_template="""Recreate {topic} as a high-energy Sakuga-style battle.
Personify {concept1} and {concept2} as opposing forces in philosophical duel.
Each strike represents a logical argument. Ink-splashes form key definitions.
Dynamic camera movements with elemental explosions. Scientific laws warp visually.""",
        cost_per_request=0.6,
        estimated_quality=0.85,
    ),
    ToolMetadata(
        tool_id="stylized_data_dioramas",
        tool_name="Data Dioramas",
        category=CategoryEnum.STYLIZED_3D,
        description="Transform statistics and data into miniature physical landscapes. Great for economic trends, demographics, and comparative analysis.",
        capabilities=ToolCapabilities(
            miniature_worlds=True,
            data_visualization=True,
            photorealistic_grounding=True,
            viral_signal="Tangible Information",
        ),
        example_topics=[
            "World population growth",
            "Stock market trends",
            "Climate change data",
            "Country GDP comparison",
        ],
        video_prompt_template="""Transform {topic} data into a miniature diorama landscape.
Statistics become physical terrain - {metric1} as mountains, {metric2} as valleys.
Tilt-shift photography aesthetic with warm lighting.
Camera slowly reveals the data story through landscape exploration.""",
        cost_per_request=0.55,
        estimated_quality=0.8,
    ),
]


class IntentToolSelectorAgent:
    """
    Agent that extracts intent and selects optimal video generation tool.
    
    Responsibilities:
    1. Extract intent from user topic via LLM
    2. Validate and normalize parameters
    3. Score and select best tool for the topic
    4. Handle fallbacks gracefully
    """
    
    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        tools: Optional[list[ToolMetadata]] = None,
    ):
        """
        Initialize agent.
        
        Args:
            gemini_service: Gemini service instance (uses singleton if None)
            tools: Available tools (uses defaults if None)
        """
        self.gemini = gemini_service or get_gemini_service()
        self.tools = tools or DEFAULT_TOOLS
        self.settings = get_settings()
        
        logger.info(f"IntentToolSelectorAgent initialized with {len(self.tools)} tools")
    
    async def run(
        self,
        topic: str,
        duration_seconds: int = 18,
        aspect_ratio: str = "9:16",
        resolution: str = "1080p",
        category: str = "auto",
        user_has_reference_image: bool = False,
    ) -> IntentToolOutput:
        """
        Run the Intent/Tool Selection pipeline.
        
        Args:
            topic: User's video topic
            duration_seconds: Requested duration (8-25)
            aspect_ratio: Video aspect ratio
            resolution: Video resolution
            category: Category preference ("auto" or specific)
            user_has_reference_image: Whether user provided a reference image
            
        Returns:
            IntentToolOutput with all selection data
        """
        logger.info(f"Running Intent/Tool Selection for topic: {topic[:50]}...")
        
        validated_params = self._validate_params(
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            user_has_reference_image=user_has_reference_image,
        )
        logger.info(f"Validated params: {validated_params.model_dump()}")
        
        intent_metadata = await self._extract_intent(
            topic=topic,
            duration_seconds=validated_params.duration_seconds,
            category=category,
        )
        logger.info(f"Extracted intent: {intent_metadata.intent_type.value}, tone: {intent_metadata.tone.value}")
        
        selected_tool, confidence, fallback_used = await self._select_tool(
            intent=intent_metadata,
            params=validated_params,
            category_preference=category,
        )
        logger.info(f"Selected tool: {selected_tool.tool_name} (confidence: {confidence:.2f})")
        
        tool_execution_params = self._build_execution_params(
            tool=selected_tool,
            intent=intent_metadata,
            params=validated_params,
        )
        
        output = IntentToolOutput(
            topic=topic,
            intent_metadata=intent_metadata,
            validated_params=validated_params,
            selected_tool=selected_tool,
            tool_execution_params=tool_execution_params,
            confidence=confidence,
            fallback_used=fallback_used,
            selection_reasoning=f"Selected {selected_tool.tool_name} for {intent_metadata.intent_type.value} content about '{topic[:30]}...'",
        )
        
        logger.info(f"Intent/Tool Selection complete. Tool: {selected_tool.tool_id}")
        return output
    
    def _validate_params(
        self,
        duration_seconds: int,
        aspect_ratio: str,
        resolution: str,
        user_has_reference_image: bool,
    ) -> ValidatedParams:
        """Validate and normalize generation parameters."""
        validated_duration = max(8, min(25, duration_seconds))
        if validated_duration != duration_seconds:
            logger.warning(f"Duration adjusted from {duration_seconds} to {validated_duration}")
        
        try:
            validated_aspect = AspectRatioEnum(aspect_ratio)
        except ValueError:
            logger.warning(f"Invalid aspect ratio '{aspect_ratio}', defaulting to 9:16")
            validated_aspect = AspectRatioEnum.VERTICAL
        
        try:
            validated_resolution = ResolutionEnum(resolution)
        except ValueError:
            logger.warning(f"Invalid resolution '{resolution}', defaulting to 1080p")
            validated_resolution = ResolutionEnum.FULL_HD
        
        reference_mode = (
            UserReferenceMode.WITH_REFERENCE 
            if user_has_reference_image 
            else UserReferenceMode.NO_REFERENCE
        )
        
        return ValidatedParams(
            duration_seconds=validated_duration,
            aspect_ratio=validated_aspect,
            resolution=validated_resolution,
            user_reference_mode=reference_mode,
        )
    
    async def _extract_intent(
        self,
        topic: str,
        duration_seconds: int,
        category: str,
    ) -> IntentMetadata:
        """Extract intent from topic using LLM."""
        prompt = INTENT_EXTRACTION_PROMPT_TEMPLATE.format(
            topic=topic,
            duration_seconds=duration_seconds,
            category=category,
        )
        
        try:
            response = await self.gemini.generate_structured_output(
                prompt=prompt,
                response_model=IntentExtractionResponse,
                system_instruction=INTENT_EXTRACTION_SYSTEM_PROMPT,
            )
            
            return IntentMetadata(
                topic=topic,
                intent_type=response.intent_type,
                target_audience=response.target_audience,
                tone=response.tone,
                keywords=response.keywords,
                complexity_score=response.complexity_score,
                reasoning=response.reasoning,
            )
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            logger.warning("Using fallback intent classification")
            return self._fallback_intent(topic)
    
    def _fallback_intent(self, topic: str) -> IntentMetadata:
        """Provide fallback intent when LLM fails."""
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ["how", "what", "why", "explain"]):
            intent_type = IntentType.EDUCATIONAL
        elif any(word in topic_lower for word in ["funny", "weird", "strange", "crazy"]):
            intent_type = IntentType.ENTERTAINMENT
        elif any(word in topic_lower for word in ["story", "journey", "overcome", "achieve"]):
            intent_type = IntentType.INSPIRATIONAL
        else:
            intent_type = IntentType.EDUCATIONAL
        
        if any(word in topic_lower for word in ["code", "programming", "software", "ai", "tech"]):
            audience = TargetAudience.TECH
        elif any(word in topic_lower for word in ["physics", "biology", "chemistry", "space"]):
            audience = TargetAudience.SCIENCE
        elif any(word in topic_lower for word in ["business", "money", "invest", "market"]):
            audience = TargetAudience.BUSINESS
        else:
            audience = TargetAudience.GENERAL
        
        return IntentMetadata(
            topic=topic,
            intent_type=intent_type,
            target_audience=audience,
            tone=ToneType.DRAMATIC,
            keywords=topic.split()[:5],
            complexity_score=0.5,
            reasoning="Fallback classification based on keyword matching",
        )
    
    async def _select_tool(
        self,
        intent: IntentMetadata,
        params: ValidatedParams,
        category_preference: str,
    ) -> tuple[ToolMetadata, float, bool]:
        """
        Select the best tool for the given intent.
        
        Returns:
            Tuple of (selected_tool, confidence_score, fallback_used)
        """
        available_tools = self.tools
        if category_preference != "auto":
            try:
                category = CategoryEnum(category_preference)
                filtered = [t for t in self.tools if t.category == category]
                if filtered:
                    available_tools = filtered
                    logger.info(f"Filtered to {len(filtered)} tools in category: {category.value}")
            except ValueError:
                logger.warning(f"Invalid category '{category_preference}', using all tools")
        
        available_tools = [
            t for t in available_tools
            if self._check_capability_match(t, params)
        ]
        
        if not available_tools:
            logger.warning("No tools match capability requirements, using fallback")
            return self._get_fallback_tool(), 0.5, True
        
        scores = await self._score_tools(available_tools, intent, params)
        
        scores.sort(key=lambda s: s.total_score, reverse=True)
        best_score = scores[0]
        
        selected_tool = next(
            t for t in available_tools if t.tool_id == best_score.tool_id
        )
        
        return selected_tool, best_score.total_score, False
    
    def _check_capability_match(
        self,
        tool: ToolMetadata,
        params: ValidatedParams,
    ) -> bool:
        """Check if tool supports the requested parameters."""
        if params.duration_seconds > tool.max_duration_seconds:
            return False
        
        if params.aspect_ratio.value not in tool.supported_aspect_ratios:
            return False
        
        if params.resolution.value not in tool.supported_resolutions:
            return False
        
        return True
    
    async def _score_tools(
        self,
        tools: list[ToolMetadata],
        intent: IntentMetadata,
        params: ValidatedParams,
    ) -> list[ToolScore]:
        """Score all tools for the given intent."""
        scores = []
        
        for tool in tools:
            relevance = await self._calculate_relevance_score(tool, intent)
            
            capability = 1.0
            
            max_cost = max(t.cost_per_request for t in tools) or 1.0
            cost = 1.0 - (tool.cost_per_request / max_cost) if max_cost > 0 else 0.5
            
            recency = 0.5
            
            total = ToolScore.calculate_total(relevance, capability, cost, recency)
            
            scores.append(ToolScore(
                tool_id=tool.tool_id,
                relevance_score=relevance,
                capability_score=capability,
                cost_score=cost,
                recency_score=recency,
                total_score=total,
            ))
            
            logger.debug(f"Tool {tool.tool_id}: relevance={relevance:.2f}, total={total:.2f}")
        
        return scores
    
    async def _calculate_relevance_score(
        self,
        tool: ToolMetadata,
        intent: IntentMetadata,
    ) -> float:
        """Calculate semantic relevance score using LLM."""
        try:
            from app.models.tool import ToolRelevanceResponse
            
            capabilities_str = ", ".join([
                k for k, v in tool.capabilities.model_dump().items() 
                if v is True
            ])
            
            prompt = TOOL_RELEVANCE_PROMPT_TEMPLATE.format(
                tool_name=tool.tool_name,
                tool_description=tool.description,
                tool_capabilities=capabilities_str or "general purpose",
                example_topics=", ".join(tool.example_topics[:3]) if tool.example_topics else "various",
                topic=intent.topic,
                intent_type=intent.intent_type.value,
                keywords=", ".join(intent.keywords),
            )
            
            response = await self.gemini.generate_structured_output(
                prompt=prompt,
                response_model=ToolRelevanceResponse,
                system_instruction=TOOL_RELEVANCE_SYSTEM_PROMPT,
            )
            
            return response.relevance_score
            
        except Exception as e:
            logger.warning(f"LLM relevance scoring failed: {e}, using keyword matching")
            return self._keyword_relevance_score(tool, intent)
    
    def _keyword_relevance_score(
        self,
        tool: ToolMetadata,
        intent: IntentMetadata,
    ) -> float:
        """Fallback keyword-based relevance scoring."""
        topic_lower = intent.topic.lower()
        keywords_lower = [k.lower() for k in intent.keywords]
        
        tool_text = f"{tool.description} {' '.join(tool.example_topics)}".lower()
        
        matches = sum(1 for kw in keywords_lower if kw in tool_text)
        keyword_score = min(1.0, matches / max(len(keywords_lower), 1))
        
        topic_matches = sum(1 for word in topic_lower.split() if word in tool_text)
        topic_score = min(1.0, topic_matches / 5)
        
        return (keyword_score * 0.6) + (topic_score * 0.4)
    
    def _get_fallback_tool(self) -> ToolMetadata:
        """Get the default fallback tool (Surreal Realism)."""
        fallback = next(
            (t for t in self.tools if t.tool_id == "surreal_impossible_sims"),
            None
        )
        
        if fallback:
            return fallback
        
        if self.tools:
            return self.tools[0]
        
        return DEFAULT_TOOLS[0]
    
    def _build_execution_params(
        self,
        tool: ToolMetadata,
        intent: IntentMetadata,
        params: ValidatedParams,
    ) -> dict:
        """Build tool-specific execution parameters."""
        return {
            "tool_id": tool.tool_id,
            "video_prompt_template": tool.video_prompt_template,
            "image_prompt_template": tool.image_prompt_template,
            "style_keywords": [
                tool.capabilities.viral_signal,
                tool.category.value,
            ],
            "intent_keywords": intent.keywords,
            "complexity": intent.complexity_score,
            "tone": intent.tone.value,
            "duration": params.duration_seconds,
            "aspect_ratio": params.aspect_ratio.value,
            "resolution": params.resolution.value,
        }
    
    @classmethod
    def from_workflow_input(
        cls,
        workflow_input: WorkflowInput,
        gemini_service: Optional[GeminiService] = None,
    ) -> "IntentToolSelectorAgent":
        """Create agent from WorkflowInput."""
        return cls(gemini_service=gemini_service)
    
    async def run_from_workflow_input(
        self,
        workflow_input: WorkflowInput,
        user_has_reference_image: bool = False,
    ) -> IntentToolOutput:
        """Run agent from WorkflowInput model."""
        return await self.run(
            topic=workflow_input.topic,
            duration_seconds=workflow_input.duration_seconds,
            aspect_ratio=workflow_input.aspect_ratio.value,
            resolution=workflow_input.resolution.value,
            category=workflow_input.category.value,
            user_has_reference_image=user_has_reference_image,
        )
