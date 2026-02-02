"""RABA Deep Research Service.

Wrapper for Gemini Deep Research Agent via the Interactions API.
Handles background execution, polling, and result parsing.
Includes Redis caching for research results (7-day TTL).

Reference: 
- Backend/Documentations/deep_research_Doc.md
- PHASE2_3_DEEP_RESEARCH_PLAN.md Step 2
- RABA_Architecture.md Section 9 - Caching Strategy
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Any, Optional

from google import genai
from pydantic import BaseModel

from app.config import get_settings
from app.models.research import (
    Citation,
    ResearchFinding,
    ResearchOutput,
    ResearchStrategy,
)
from app.services.gemini import GEMINI_3_PRO, GEMINI_2_5_FLASH, GeminiService, get_gemini_service
from app.services.redis import get_redis_service, RedisService
from app.utils.cache import CacheKeys
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"


class DeepResearchError(Exception):
    """Base exception for Deep Research errors."""
    pass


class DeepResearchTimeoutError(DeepResearchError):
    """Timeout waiting for research completion."""
    pass


class DeepResearchParseError(DeepResearchError):
    """Error parsing research output."""
    pass


class ParsedResearchReport(BaseModel):
    """Structured output from parsing raw research text."""
    executive_summary: str = ""
    findings: list[dict[str, Any]] = []
    visual_elements: list[str] = []
    interesting_angles: list[str] = []
    sources: list[dict[str, str]] = []


class DeepResearchService:
    """
    Service for conducting deep research using Gemini Deep Research Agent.
    
    Features:
    - Uses the Interactions API with background=True for long-running tasks
    - Redis caching with 7-day TTL for research results
    - Graceful fallback when cache unavailable
    
    Reference: 
    - deep_research_Doc.md
    - RABA_Architecture.md Section 9 - Caching Strategy
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or get_settings().google_api_key
        self._client: Optional[genai.Client] = None
        self._gemini_service = get_gemini_service()
        self._redis: Optional[RedisService] = None
    
    @property
    def redis(self) -> RedisService:
        """Get Redis service (lazy initialization)."""
        if self._redis is None:
            self._redis = get_redis_service()
        return self._redis
    
    def _get_client(self) -> genai.Client:
        """Get or create GenAI client."""
        if self._client is None:
            if not self._api_key:
                raise DeepResearchError("Google API key not configured")
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Created GenAI client for Deep Research")
        return self._client
    
    def _build_research_prompt(
        self,
        topic: str,
        tool_category: str,
        duration_seconds: int,
        target_audience: str = "general",
    ) -> str:
        """
        Build a structured research prompt for the Deep Research Agent.
        
        Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md - Prompt Template
        """
        return f"""Research the topic: "{topic}"

Context for video generation:
- Visual style: {tool_category}
- Duration: {duration_seconds} seconds (YouTube Shorts format)
- Target audience: {target_audience}

PROVIDE A COMPREHENSIVE RESEARCH REPORT with these REQUIRED sections:

## 1. EXECUTIVE SUMMARY (2-3 sentences)
Write a compelling 2-3 sentence summary that captures:
- The core concept explained simply
- Why this topic is visually interesting/viral-worthy
- The emotional hook or surprise factor

## 2. KEY FACTS (5-8 bullet points)
Provide 5-8 specific, fact-checked bullet points:
- Each fact must be visually demonstrable for video
- Include specific numbers, statistics, or measurements where possible
- Cite sources in [Source Name] format
- Focus on surprising or counterintuitive information

Example format:
• Black holes can be as small as an atom but contain the mass of a mountain [NASA]
• Time slows down by 50% at the event horizon compared to Earth [Einstein's Relativity]

## 3. VISUAL ELEMENTS (4-6 items)
Describe 4-6 specific visual scenes perfect for {tool_category} style video:
- Each should be a concrete, filmable moment
- Include colors, textures, movements, scale references
- Consider dramatic lighting and camera angles

Example format:
• A clock melting and stretching as it approaches the black hole's edge
• Light bending in rainbow spirals around the event horizon
• A astronaut's perspective looking into the infinite darkness

## 4. INTERESTING ANGLES (3-5 items)
Provide 3-5 unique perspectives for viral content:
- Counterintuitive facts that surprise viewers
- Relatable comparisons ("It's like...")
- Emotional hooks or mind-bending concepts
- "Did you know?" style hooks

Example format:
• If you fell into a black hole, you'd see the entire future of the universe flash before you
• A teaspoon of black hole material would weigh more than Mount Everest

## 5. SOURCES
List all sources with URLs for fact-checking.

IMPORTANT REQUIREMENTS:
- Be SPECIFIC and DETAILED - avoid vague statements
- Every section must have content (no empty sections)
- Focus on visual, demonstrable information
- Include surprising facts for viral potential
- All facts must be accurate and well-sourced"""
    
    async def start_research(
        self,
        topic: str,
        tool_category: str = "surreal_realism",
        duration_seconds: int = 18,
        target_audience: str = "general",
    ) -> str:
        """
        Start a deep research task in the background.
        
        Args:
            topic: The topic to research
            tool_category: Visual style category
            duration_seconds: Target video duration
            target_audience: Target audience type
            
        Returns:
            interaction_id: ID for polling the research status
        """
        client = self._get_client()
        prompt = self._build_research_prompt(
            topic=topic,
            tool_category=tool_category,
            duration_seconds=duration_seconds,
            target_audience=target_audience,
        )
        
        logger.info(f"Starting deep research for topic: {topic[:50]}...")
        
        try:
            # Try using the Deep Research agent via Interactions API
            if hasattr(client, 'interactions'):
                interaction = await asyncio.to_thread(
                    client.interactions.create,
                    input=prompt,
                    agent=DEEP_RESEARCH_AGENT,
                    background=True,
                )
                interaction_id = interaction.id
                logger.info(f"Deep research started: {interaction_id}")
                return interaction_id
            else:
                # Fallback: Use grounded generation directly
                logger.info("Interactions API not available, using grounded generation fallback")
                text, citations = await self._gemini_service.generate_with_grounding(
                    prompt=prompt,
                    model=GEMINI_3_PRO,
                )
                # Store result directly and return a synthetic ID
                synthetic_id = f"grounded_{hashlib.md5(topic.encode()).hexdigest()[:16]}"
                self._grounded_results = getattr(self, '_grounded_results', {})
                self._grounded_results[synthetic_id] = {
                    "text": text,
                    "citations": citations,
                    "status": "completed",
                }
                logger.info(f"Grounded research completed: {synthetic_id}")
                return synthetic_id
            
        except Exception as e:
            logger.error(f"Failed to start deep research: {e}")
            raise DeepResearchError(f"Failed to start research: {e}")
    
    async def poll_research(
        self,
        interaction_id: str,
    ) -> tuple[str, Optional[str]]:
        """
        Check the status of a research task.
        
        Args:
            interaction_id: The interaction ID from start_research
            
        Returns:
            Tuple of (status, result_text)
            - status: "in_progress", "completed", or "failed"
            - result_text: The research report if completed, None otherwise
        """
        client = self._get_client()
        
        # Check if this is a grounded fallback result
        grounded_results = getattr(self, '_grounded_results', {})
        if interaction_id in grounded_results:
            result = grounded_results[interaction_id]
            return result["status"], result["text"]
        
        try:
            if hasattr(client, 'interactions'):
                interaction = await asyncio.to_thread(
                    client.interactions.get,
                    interaction_id,
                )
                
                status = interaction.status
                result_text = None
                
                if status == "completed":
                    if interaction.outputs:
                        result_text = interaction.outputs[-1].text
                    logger.info(f"Research completed: {interaction_id}")
                elif status == "failed":
                    error_msg = getattr(interaction, 'error', 'Unknown error')
                    logger.error(f"Research failed: {error_msg}")
                    raise DeepResearchError(f"Research failed: {error_msg}")
                
                return status, result_text
            else:
                # No Interactions API, return error
                raise DeepResearchError("Interactions API not available")
            
        except DeepResearchError:
            raise
        except Exception as e:
            logger.error(f"Failed to poll research: {e}")
            raise DeepResearchError(f"Failed to poll research: {e}")
    
    async def wait_for_completion(
        self,
        interaction_id: str,
        timeout_seconds: int = 300,
        poll_interval: int = 10,
    ) -> str:
        """
        Poll until research completes or times out.
        
        Args:
            interaction_id: The interaction ID from start_research
            timeout_seconds: Maximum time to wait (default 5 minutes)
            poll_interval: Seconds between polls (default 10)
            
        Returns:
            The completed research report text
            
        Raises:
            DeepResearchTimeoutError: If timeout is reached
            DeepResearchError: If research fails
        """
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise DeepResearchTimeoutError(
                    f"Research timed out after {timeout_seconds}s"
                )
            
            status, result_text = await self.poll_research(interaction_id)
            
            if status == "completed" and result_text:
                return result_text
            
            logger.debug(
                f"Research in progress... ({elapsed:.0f}s / {timeout_seconds}s)"
            )
            await asyncio.sleep(poll_interval)

    async def quick_grounded_research(
        self,
        topic: str,
        tool_category: str = "surreal_realism",
        duration_seconds: int = 18,
        target_audience: str = "general",
    ) -> ResearchOutput:
        """Fast fallback: generate grounded research text and parse it.

        Uses Gemini grounded generation directly (no Interactions API) and
        then parses the result into structured ResearchOutput. Designed for
        timeout scenarios to avoid returning empty research.
        """
        prompt = self._build_research_prompt(
            topic=topic,
            tool_category=tool_category,
            duration_seconds=duration_seconds,
            target_audience=target_audience,
        )
        text, _citations = await self._gemini_service.generate_with_grounding(
            prompt=prompt, model=GEMINI_3_PRO
        )
        output = await self.parse_research_output(text)
        output.cache_hit = False
        output.strategy_used = ResearchStrategy.FACTUAL
        output.is_fictional = False
        return output
    
    async def parse_research_output(
        self,
        raw_text: str,
    ) -> ResearchOutput:
        """
        Parse raw research text into structured ResearchOutput.
        
        Uses Gemini 3 Pro to extract structured data from the report.
        
        Args:
            raw_text: The raw research report text
            
        Returns:
            Structured ResearchOutput
        """
        parse_prompt = f"""Parse the following research report into structured JSON format.

RESEARCH REPORT:
{raw_text}

EXTRACT and return JSON with ALL these fields populated:

{{
    "executive_summary": "A compelling 2-3 sentence summary of the topic",
    "findings": [
        {{
            "topic_segment": "Main Topic",
            "key_facts": [
                "Specific fact 1 with numbers/details",
                "Specific fact 2 with numbers/details",
                "Specific fact 3 with numbers/details"
            ],
            "citations": [{{"source": "Source Name", "url": "https://...", "quote": "relevant quote"}}],
            "confidence": 0.85
        }},
        {{
            "topic_segment": "Supporting Details",
            "key_facts": ["fact 4", "fact 5"],
            "citations": [],
            "confidence": 0.8
        }}
    ],
    "visual_elements": [
        "Detailed visual description 1 for video scene",
        "Detailed visual description 2 for video scene",
        "Detailed visual description 3 for video scene",
        "Detailed visual description 4 for video scene"
    ],
    "interesting_angles": [
        "Surprising/counterintuitive angle 1",
        "Viral hook angle 2",
        "Emotional/relatable angle 3"
    ],
    "sources": [{{"source": "Source Name", "url": "https://..."}}]
}}

CRITICAL REQUIREMENTS:
1. executive_summary: MUST be 2-3 complete sentences summarizing the topic
2. findings: MUST have at least 2 topic segments with 3+ key_facts each
3. visual_elements: MUST have at least 4 specific, filmable visual descriptions
4. interesting_angles: MUST have at least 3 unique perspectives/hooks
5. sources: Extract ALL mentioned sources with URLs if available

DO NOT leave any section empty. If information is not explicitly in the report, infer reasonable content based on the topic."""

        try:
            # Use Gemini 2.5 Flash for parsing - it doesn't require thinking mode
            # and is faster for structured output extraction
            logger.info(f"[PARSE] Starting parse of {len(raw_text)} chars research text")
            logger.info(f"[PARSE] Raw text preview: {raw_text[:300]}...")
            
            parsed = await self._gemini_service.generate_structured_output(
                prompt=parse_prompt,
                response_model=ParsedResearchReport,
                model=GEMINI_2_5_FLASH,
            )
            
            # Log what we got from parsing
            logger.info(f"[PARSE] Parsed executive_summary: {len(parsed.executive_summary)} chars")
            logger.info(f"[PARSE] Parsed findings: {len(parsed.findings)} items")
            logger.info(f"[PARSE] Parsed visual_elements: {len(parsed.visual_elements)} items")
            logger.info(f"[PARSE] Parsed interesting_angles: {len(parsed.interesting_angles)} items")
            logger.info(f"[PARSE] Parsed sources: {len(parsed.sources)} items")
            
            findings = []
            for f in parsed.findings:
                citations = []
                for c in f.get("citations", []):
                    # Handle None values robustly - url and source can be None from LLM
                    source = c.get("source") or ""
                    url = c.get("url") or ""
                    quote = c.get("quote")
                    # Only add citation if we have at least a source or url
                    if source or url:
                        citations.append(Citation(
                            source=source,
                            url=url,
                            quote=quote,
                        ))
                findings.append(
                    ResearchFinding(
                        topic_segment=f.get("topic_segment", ""),
                        key_facts=f.get("key_facts", []),
                        citations=citations,
                        confidence=f.get("confidence", 0.8),
                    )
                )
            
            return ResearchOutput(
                research_findings=findings,
                executive_summary=parsed.executive_summary,
                visual_elements=parsed.visual_elements,
                interesting_angles=parsed.interesting_angles,
                total_sources=len(parsed.sources),
                strategy_used=ResearchStrategy.FACTUAL,
                is_fictional=False,
            )
            
        except Exception as e:
            logger.error(f"[PARSE] Failed to parse research output: {e}")
            logger.error(f"[PARSE] Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"[PARSE] Traceback: {traceback.format_exc()}")
            
            # Fallback: Try to extract key info directly from raw text
            logger.info("[PARSE] Using fallback text extraction")
            return self._fallback_parse(raw_text)
    
    def _fallback_parse(self, raw_text: str) -> ResearchOutput:
        """
        Fallback parsing when structured output fails.
        Extracts key information directly from raw text using regex/heuristics.
        """
        import re
        
        def clean_markdown(text: str) -> str:
            """Remove markdown formatting from text."""
            # Remove bold/italic markers
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'__(.+?)__', r'\1', text)
            text = re.sub(r'_(.+?)_', r'\1', text)
            # Remove headers
            text = re.sub(r'^#+\s*', '', text)
            # Remove bullet points at start
            text = re.sub(r'^\s*[\u2022\-\*]\s*', '', text)
            # Remove leading/trailing whitespace and newlines
            text = text.strip()
            return text
        
        def is_section_header(text: str) -> bool:
            """Check if line is a section header to skip."""
            headers = ['VISUAL ELEMENTS', 'INTERESTING ANGLES', 'KEY FACTS', 'EXECUTIVE SUMMARY', 
                       'SOURCES', 'RESEARCH', 'FINDINGS', 'Style:', '**Style']
            text_lower = text.lower().strip()
            return any(h.lower() in text_lower for h in headers) and len(text) < 100
        
        lines = raw_text.split('\n')
        
        # Extract executive summary (first substantive paragraph)
        exec_summary = ""
        for line in lines:
            line = clean_markdown(line)
            if line and not line.startswith('#') and len(line) > 50 and not is_section_header(line):
                exec_summary = line
                break
        if not exec_summary:
            exec_summary = clean_markdown(raw_text[:1000]) if raw_text else "Research completed"
        
        # Extract bullet points as key facts
        key_facts = []
        bullet_patterns = [r'^\s*[\u2022\-\*]\s*(.+)', r'^\s*\d+\.\s*(.+)']
        for line in lines:
            for pattern in bullet_patterns:
                match = re.match(pattern, line)
                if match:
                    fact = clean_markdown(match.group(1))
                    # Skip section headers and style descriptions
                    if len(fact) > 20 and len(key_facts) < 8 and not is_section_header(fact):
                        key_facts.append(fact)
        
        # If no bullet points found, extract sentences with key indicators
        if len(key_facts) < 3:
            sentences = re.split(r'[.!?]+', raw_text)
            for sentence in sentences:
                sentence = clean_markdown(sentence)
                if len(sentence) > 30 and len(key_facts) < 8 and not is_section_header(sentence):
                    if any(word in sentence.lower() for word in ['is', 'are', 'can', 'has', 'have', 'was', 'were']):
                        key_facts.append(sentence)
        
        # Extract visual elements - look for descriptive visual content
        visual_elements = []
        visual_keywords = ['shot', 'camera', 'lighting', 'glow', 'swirl', 'warp', 'ring', 'disk', 'horizon', 'space']
        for sentence in re.split(r'[.!?]+', raw_text):
            sentence = clean_markdown(sentence)
            # Skip headers and short content
            if is_section_header(sentence) or len(sentence) < 30:
                continue
            if any(kw in sentence.lower() for kw in visual_keywords) and len(visual_elements) < 4:
                visual_elements.append(sentence)
        
        # If still not enough, generate topic-relevant visual descriptions
        if len(visual_elements) < 4:
            # Extract nouns/concepts from key facts to build visuals
            topic_concepts = []
            for fact in key_facts[:4]:
                words = fact.split()[:5]
                if words:
                    topic_concepts.append(' '.join(words))
            
            default_visuals = [
                "Dramatic wide shot revealing the cosmic phenomenon",
                "Close-up with swirling light and gravitational distortion",
                "Time-lapse visualization showing the extreme effects",
                "Cinematic pull-back revealing the scale and power"
            ]
            for i, visual in enumerate(default_visuals):
                if len(visual_elements) < 4:
                    visual_elements.append(visual)
        
        # Extract interesting angles (surprising facts, paradoxes)
        interesting_angles = []
        angle_keywords = ['paradox', 'surprising', 'amazing', 'actually', 'secret', 'survive', 'never', 'impossible']
        for sentence in re.split(r'[.!?]+', raw_text):
            sentence = clean_markdown(sentence)
            if is_section_header(sentence) or len(sentence) < 30:
                continue
            if any(kw in sentence.lower() for kw in angle_keywords) and len(interesting_angles) < 3:
                interesting_angles.append(sentence)
        
        # Fallback angles if not enough found
        if len(interesting_angles) < 3:
            default_angles = [
                "The mind-bending truth that defies common sense",
                "What happens when physics breaks down completely",
                "The terrifying beauty of nature's ultimate force"
            ]
            for angle in default_angles:
                if len(interesting_angles) < 3:
                    interesting_angles.append(angle)
        
        logger.info(f"[FALLBACK] Extracted: {len(key_facts)} facts, {len(visual_elements)} visuals, {len(interesting_angles)} angles")
        
        return ResearchOutput(
            executive_summary=exec_summary,
            research_findings=[
                ResearchFinding(
                    topic_segment="Key Information",
                    key_facts=key_facts[:4] if key_facts else ["Research data available"],
                    citations=[],
                    confidence=0.7,
                ),
                ResearchFinding(
                    topic_segment="Additional Details",
                    key_facts=key_facts[4:8] if len(key_facts) > 4 else ["See executive summary"],
                    citations=[],
                    confidence=0.6,
                ),
            ],
            visual_elements=visual_elements[:4] if visual_elements else [
                "Dramatic visualization of the core concept",
                "Close-up showing key details",
                "Wide shot establishing context",
                "Dynamic movement capturing the essence"
            ],
            interesting_angles=interesting_angles[:3],
            strategy_used=ResearchStrategy.FACTUAL,
            is_fictional=False,
            total_sources=0,
        )
    
    async def _get_cached_research(
        self,
        cache_key: str,
    ) -> Optional[ResearchOutput]:
        """
        Try to get research from cache.
        
        Args:
            cache_key: The cache key to look up
            
        Returns:
            ResearchOutput if found and valid, None otherwise
        """
        try:
            cached = await self.redis.get_with_metadata(cache_key)
            if cached and cached.get("data"):
                logger.info(f"Cache HIT for research: {cache_key}")
                data = cached["data"]
                
                findings = []
                for f in data.get("research_findings", []):
                    citations = [
                        Citation(**c) for c in f.get("citations", [])
                    ]
                    findings.append(ResearchFinding(
                        topic_segment=f.get("topic_segment", ""),
                        key_facts=f.get("key_facts", []),
                        citations=citations,
                        confidence=f.get("confidence", 0.8),
                    ))
                
                return ResearchOutput(
                    research_findings=findings,
                    executive_summary=data.get("executive_summary", ""),
                    visual_elements=data.get("visual_elements", []),
                    interesting_angles=data.get("interesting_angles", []),
                    total_sources=data.get("total_sources", 0),
                    strategy_used=ResearchStrategy(data.get("strategy_used", "factual")),
                    is_fictional=data.get("is_fictional", False),
                    cache_hit=True,
                    cached_at=data.get("cached_at"),
                )
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
        
        return None
    
    async def _cache_research(
        self,
        cache_key: str,
        output: ResearchOutput,
    ) -> bool:
        """
        Cache research output.
        
        Args:
            cache_key: The cache key
            output: ResearchOutput to cache
            
        Returns:
            True if cached successfully
        """
        try:
            cache_data = {
                "research_findings": [
                    {
                        "topic_segment": f.topic_segment,
                        "key_facts": f.key_facts,
                        "citations": [c.model_dump() for c in f.citations],
                        "confidence": f.confidence,
                    }
                    for f in output.research_findings
                ],
                "executive_summary": output.executive_summary,
                "visual_elements": output.visual_elements,
                "interesting_angles": output.interesting_angles,
                "total_sources": output.total_sources,
                "strategy_used": output.strategy_used.value,
                "is_fictional": output.is_fictional,
                "cached_at": datetime.utcnow().isoformat(),
            }
            
            ttl = CacheKeys.research_ttl()
            success = await self.redis.set(cache_key, cache_data, ttl=ttl)
            
            if success:
                logger.info(f"Cached research: {cache_key} (TTL: {ttl}s)")
            return success
            
        except Exception as e:
            logger.warning(f"Failed to cache research: {e}")
            return False
    
    async def research(
        self,
        topic: str,
        tool_category: str = "surreal_realism",
        duration_seconds: int = 18,
        target_audience: str = "general",
        timeout_seconds: int = 300,
        use_cache: bool = True,
    ) -> ResearchOutput:
        """
        Complete research workflow: check cache, start, wait, parse, cache.
        
        This is the main entry point for factual research.
        Includes Redis caching with 7-day TTL.
        
        Args:
            topic: Topic to research
            tool_category: Visual style category
            duration_seconds: Target video duration
            target_audience: Target audience
            timeout_seconds: Max time to wait
            use_cache: Whether to use caching (default True)
            
        Returns:
            Structured ResearchOutput (with cache_hit flag)
        """
        cache_key = CacheKeys.research(topic, "standard")
        
        if use_cache:
            cached_output = await self._get_cached_research(cache_key)
            if cached_output:
                return cached_output
            logger.info(f"Cache MISS for research: {cache_key}")
        
        interaction_id = await self.start_research(
            topic=topic,
            tool_category=tool_category,
            duration_seconds=duration_seconds,
            target_audience=target_audience,
        )
        
        raw_text = await self.wait_for_completion(
            interaction_id=interaction_id,
            timeout_seconds=timeout_seconds,
        )
        
        output = await self.parse_research_output(raw_text)
        output.interaction_id = interaction_id
        output.cache_hit = False
        
        if use_cache:
            await self._cache_research(cache_key, output)
        
        return output
    
    @staticmethod
    def generate_cache_key(
        topic: str,
        tool_category: str,
        strategy: ResearchStrategy,
    ) -> str:
        """
        Generate a cache key for research results.
        
        Key format: research:{hash(topic + tool_category + strategy)}
        """
        normalized = f"{topic.lower().strip()}:{tool_category}:{strategy.value}"
        hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"research:{hash_val}"


_deep_research_service: Optional[DeepResearchService] = None


def get_deep_research_service() -> DeepResearchService:
    """Get singleton Deep Research service instance."""
    global _deep_research_service
    if _deep_research_service is None:
        _deep_research_service = DeepResearchService()
    return _deep_research_service
