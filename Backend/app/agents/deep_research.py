"""RABA Deep Research Agent.

Main agent orchestrating research workflow with content type routing.
Handles factual research (Deep Research Agent), creative ideation, and hybrid content.

Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md Step 5
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from app.config import get_settings
from app.graph.state import VideoGenerationState
from app.models.research import (
    CreativeIdeationOutput,
    HybridResearchOutput,
    ResearchOutput,
    ResearchResult,
    ResearchStrategy,
)
from app.services.creative_ideation import (
    CreativeIdeationService,
    get_creative_ideation_service,
)
from app.services.deep_research import (
    DeepResearchService,
    DeepResearchTimeoutError,
    get_deep_research_service,
)
from app.services.google_search import GoogleSearchService, get_google_search_service
from app.services.redis import get_redis_service
from app.services.supabase import get_supabase_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DeepResearchAgentError(Exception):
    """Base exception for Deep Research Agent errors."""
    pass


class DeepResearchAgent:
    """
    Main agent for research phase of video generation.
    
    Routes between:
    - FACTUAL: Deep Research Agent with Google Search grounding
    - CREATIVE: Creative ideation without fact-checking
    - HYBRID: Factual base + creative extension
    
    Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md
    """
    
    def __init__(self):
        self._deep_research = get_deep_research_service()
        self._creative_ideation = get_creative_ideation_service()
        self._google_search = get_google_search_service()
        self._redis = get_redis_service()
        self._supabase = get_supabase_service()
        self._settings = get_settings()
    
    def _get_intent_type(self, state: VideoGenerationState) -> str:
        """Extract intent_type from state."""
        intent_metadata = state.get("intent_metadata") or {}
        return intent_metadata.get("intent_type", "educational")
    
    def _get_tone(self, state: VideoGenerationState) -> str:
        """Extract tone from state."""
        intent_metadata = state.get("intent_metadata") or {}
        return intent_metadata.get("tone", "informative")
    
    def _get_tool_category(self, state: VideoGenerationState) -> str:
        """Extract tool category from state."""
        selected_tool = state.get("selected_tool") or {}
        return selected_tool.get("category", state.get("category", "surreal_realism"))
    
    async def _check_cache(
        self,
        topic: str,
        tool_category: str,
        strategy: ResearchStrategy,
    ) -> Optional[dict]:
        """Check Redis cache for existing research."""
        cache_key = DeepResearchService.generate_cache_key(
            topic=topic,
            tool_category=tool_category,
            strategy=strategy,
        )
        
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                logger.info(f"Cache HIT for research: {cache_key}")
                return cached
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
        
        return None
    
    async def _set_cache(
        self,
        topic: str,
        tool_category: str,
        strategy: ResearchStrategy,
        result: dict,
    ) -> None:
        """Store research result in Redis cache."""
        cache_key = DeepResearchService.generate_cache_key(
            topic=topic,
            tool_category=tool_category,
            strategy=strategy,
        )
        
        try:
            ttl = self._settings.cache_ttl_research
            await self._redis.set(cache_key, result, ttl=ttl)
            logger.info(f"Cached research result: {cache_key} (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    async def _execute_factual_research(
        self,
        state: VideoGenerationState,
    ) -> tuple[ResearchOutput, list[str]]:
        """
        Execute factual research with Deep Research Agent.
        
        Returns:
            Tuple of (ResearchOutput, list of image URLs)
        """
        topic = state.get("topic", "")
        tool_category = self._get_tool_category(state)
        duration = state.get("duration_seconds", 18)
        workflow_id = state.get("workflow_id", "unknown")
        
        logger.info(f"Executing FACTUAL research for: {topic[:50]}...")
        
        research_task = self._deep_research.research(
            topic=topic,
            tool_category=tool_category,
            duration_seconds=duration,
            timeout_seconds=300,
        )
        
        image_task = self._google_search.search_and_store_images(
            query=topic,
            workflow_id=workflow_id,
            num_images=3,
        )
        
        try:
            research_output, research_images = await asyncio.gather(
                research_task,
                image_task,
            )
        except DeepResearchTimeoutError:
            logger.warning("Deep research timed out, using fallback")
            research_output = ResearchOutput(
                executive_summary=f"Research on: {topic}",
                strategy_used=ResearchStrategy.FACTUAL,
                is_fictional=False,
            )
            research_images = await image_task
        
        image_urls = [img.storage_url for img in research_images]
        research_output.research_images = research_images
        
        return research_output, image_urls
    
    async def _execute_creative_research(
        self,
        state: VideoGenerationState,
    ) -> tuple[CreativeIdeationOutput, list[str]]:
        """
        Execute creative ideation (no fact-grounding).
        
        Returns:
            Tuple of (CreativeIdeationOutput, empty list - no image search)
        """
        topic = state.get("topic", "")
        tool_category = self._get_tool_category(state)
        duration = state.get("duration_seconds", 18)
        tone = self._get_tone(state)
        
        logger.info(f"Executing CREATIVE ideation for: {topic[:50]}...")
        
        creative_output = await self._creative_ideation.generate_creative_ideation(
            topic=topic,
            tool_category=tool_category,
            duration_seconds=duration,
            tone=tone,
        )
        
        return creative_output, []
    
    async def _execute_hybrid_research(
        self,
        state: VideoGenerationState,
    ) -> tuple[HybridResearchOutput, list[str]]:
        """
        Execute hybrid research (factual base + creative extension).
        
        Returns:
            Tuple of (HybridResearchOutput, list of image URLs)
        """
        topic = state.get("topic", "")
        tool_category = self._get_tool_category(state)
        duration = state.get("duration_seconds", 18)
        tone = self._get_tone(state)
        workflow_id = state.get("workflow_id", "unknown")
        
        logger.info(f"Executing HYBRID research for: {topic[:50]}...")
        
        factual_output, image_urls = await self._execute_factual_research(state)
        
        hybrid_output = await self._creative_ideation.generate_hybrid_content(
            topic=topic,
            factual_research=factual_output,
            tool_category=tool_category,
            duration_seconds=duration,
            tone=tone,
        )
        
        return hybrid_output, image_urls
    
    def _result_to_dict(self, result: ResearchResult) -> dict[str, Any]:
        """Convert research result to dictionary for state storage."""
        return result.model_dump(mode="json")
    
    async def _persist_to_supabase(
        self,
        workflow_id: str,
        research_data: dict,
        research_images: list[str],
        strategy: ResearchStrategy,
    ) -> None:
        """Persist research results to Supabase."""
        try:
            await self._supabase.update_workflow(
                workflow_id=workflow_id,
                updates={
                    "research_output": research_data,
                    "research_images": research_images,
                    "status": "research_complete",
                },
            )
            logger.info(f"Persisted research to Supabase: {workflow_id}")
        except Exception as e:
            logger.error(f"Failed to persist research: {e}")
    
    async def research(
        self,
        state: VideoGenerationState,
    ) -> VideoGenerationState:
        """
        Main entry point for research phase.
        
        Routes to appropriate strategy based on content type:
        - FACTUAL: Deep Research + image search
        - CREATIVE: Creative ideation (no grounding)
        - HYBRID: Factual base + creative extension
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with research_data populated
        """
        from app.utils.helpers import utc_now_iso
        
        topic = state.get("topic", "")
        workflow_id = state.get("workflow_id", "unknown")
        intent_type = self._get_intent_type(state)
        tone = self._get_tone(state)
        tool_category = self._get_tool_category(state)
        
        logger.info(f"Deep Research Agent starting for workflow: {workflow_id}")
        logger.info(f"  Topic: {topic[:50]}...")
        logger.info(f"  Intent: {intent_type}, Tone: {tone}")
        
        strategy = self._creative_ideation.determine_strategy(
            intent_type=intent_type,
            topic=topic,
            tone=tone,
        )
        logger.info(f"  Strategy: {strategy.value}")
        
        cached = await self._check_cache(topic, tool_category, strategy)
        if cached:
            state["research_data"] = cached
            state["research_images"] = cached.get("research_images", [])
            state["phase_timestamps"] = {
                **state.get("phase_timestamps", {}),
                "deep_research": utc_now_iso(),
            }
            logger.info("Returning cached research result")
            return state
        
        result: ResearchResult
        image_urls: list[str]
        
        if strategy == ResearchStrategy.FACTUAL:
            result, image_urls = await self._execute_factual_research(state)
        elif strategy == ResearchStrategy.CREATIVE:
            result, image_urls = await self._execute_creative_research(state)
        else:
            result, image_urls = await self._execute_hybrid_research(state)
        
        research_dict = self._result_to_dict(result)
        
        await self._set_cache(topic, tool_category, strategy, research_dict)
        
        await self._persist_to_supabase(
            workflow_id=workflow_id,
            research_data=research_dict,
            research_images=image_urls,
            strategy=strategy,
        )
        
        state["research_data"] = research_dict
        state["research_images"] = image_urls
        state["phase_timestamps"] = {
            **state.get("phase_timestamps", {}),
            "deep_research": utc_now_iso(),
        }
        
        logger.info(f"Deep Research Agent completed for workflow: {workflow_id}")
        logger.info(f"  Strategy used: {strategy.value}")
        logger.info(f"  Images found: {len(image_urls)}")
        
        return state


_deep_research_agent: Optional[DeepResearchAgent] = None


def get_deep_research_agent() -> DeepResearchAgent:
    """Get singleton Deep Research Agent instance."""
    global _deep_research_agent
    if _deep_research_agent is None:
        _deep_research_agent = DeepResearchAgent()
    return _deep_research_agent


async def run_deep_research(state: VideoGenerationState) -> VideoGenerationState:
    """
    Convenience function to run Deep Research Agent.
    
    This is the function that will be wired to the LangGraph node.
    """
    agent = get_deep_research_agent()
    return await agent.research(state)
