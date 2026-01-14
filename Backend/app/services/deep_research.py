"""RABA Deep Research Service.

Wrapper for Gemini Deep Research Agent via the Interactions API.
Handles background execution, polling, and result parsing.

Reference: 
- Backend/Documentations/deep_research_Doc.md
- PHASE2_3_DEEP_RESEARCH_PLAN.md Step 2
"""

import asyncio
import hashlib
import time
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
from app.services.gemini import GEMINI_3_PRO, GeminiService, get_gemini_service
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
    
    Uses the Interactions API with background=True for long-running tasks.
    Reference: deep_research_Doc.md
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or get_settings().google_api_key
        self._client: Optional[genai.Client] = None
        self._gemini_service = get_gemini_service()
    
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
- Duration: {duration_seconds} seconds
- Target audience: {target_audience}

Format the output as a structured report with:

1. EXECUTIVE SUMMARY
   - 2-3 key insights about the topic
   - What makes this topic interesting/viral-worthy

2. KEY FACTS
   - Bullet points of important facts
   - Each fact should be visually demonstrable
   - Include source citations in [brackets]

3. VISUAL ELEMENTS
   - Describe scenes/imagery that would work well for video
   - Focus on visually striking or surprising moments
   - Consider the {tool_category} visual style

4. INTERESTING ANGLES
   - Unique perspectives for viral content
   - Surprising or counterintuitive facts
   - Emotional hooks or relatable moments

5. SOURCES
   - List all sources with URLs

Requirements:
- All facts must have source citations
- Focus on visually demonstrable information
- Include surprising or counterintuitive facts (viral potential)
- If specific data is unavailable, explicitly state this
- Keep content appropriate for YouTube Shorts format"""
    
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
            interaction = await asyncio.to_thread(
                client.interactions.create,
                input=prompt,
                agent=DEEP_RESEARCH_AGENT,
                background=True,
            )
            
            interaction_id = interaction.id
            logger.info(f"Deep research started: {interaction_id}")
            return interaction_id
            
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
        
        try:
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

Extract and return JSON with these fields:
{{
    "executive_summary": "2-3 sentence summary",
    "findings": [
        {{
            "topic_segment": "sub-topic name",
            "key_facts": ["fact 1", "fact 2"],
            "citations": [{{"source": "name", "url": "url", "quote": "optional quote"}}],
            "confidence": 0.85
        }}
    ],
    "visual_elements": ["visual element 1", "visual element 2"],
    "interesting_angles": ["angle 1", "angle 2"],
    "sources": [{{"source": "name", "url": "url"}}]
}}

Important:
- Extract ALL cited sources with their URLs
- Group related facts into topic segments
- Include confidence scores based on source quality
- Keep visual elements focused on video-friendly descriptions"""

        try:
            parsed = await self._gemini_service.generate_structured_output(
                prompt=parse_prompt,
                response_model=ParsedResearchReport,
                model=GEMINI_3_PRO,
                thinking_level="low",
            )
            
            findings = []
            for f in parsed.findings:
                citations = [
                    Citation(
                        source=c.get("source", ""),
                        url=c.get("url", ""),
                        quote=c.get("quote"),
                    )
                    for c in f.get("citations", [])
                ]
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
            logger.error(f"Failed to parse research output: {e}")
            return ResearchOutput(
                executive_summary=raw_text[:500] if raw_text else "",
                research_findings=[
                    ResearchFinding(
                        topic_segment="Raw Research",
                        key_facts=[raw_text[:1000] if raw_text else "No content"],
                        citations=[],
                        confidence=0.5,
                    )
                ],
                strategy_used=ResearchStrategy.FACTUAL,
                is_fictional=False,
            )
    
    async def research(
        self,
        topic: str,
        tool_category: str = "surreal_realism",
        duration_seconds: int = 18,
        target_audience: str = "general",
        timeout_seconds: int = 300,
    ) -> ResearchOutput:
        """
        Complete research workflow: start, wait, parse.
        
        This is the main entry point for factual research.
        
        Args:
            topic: Topic to research
            tool_category: Visual style category
            duration_seconds: Target video duration
            target_audience: Target audience
            timeout_seconds: Max time to wait
            
        Returns:
            Structured ResearchOutput
        """
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
