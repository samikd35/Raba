"""Tests for Deep Research Agent.

Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md Step 10
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.research import (
    CreativeIdeationOutput,
    HybridResearchOutput,
    NarrativeArc,
    ResearchOutput,
    ResearchStrategy,
)
from app.services.creative_ideation import CreativeIdeationService


class TestResearchStrategyDetermination:
    """Tests for content type routing logic."""
    
    def test_strategy_factual_educational(self):
        """Educational intent should return FACTUAL strategy."""
        service = CreativeIdeationService()
        strategy = service.determine_strategy(
            intent_type="educational",
            topic="How black holes work",
            tone="informative",
        )
        assert strategy == ResearchStrategy.FACTUAL
    
    def test_strategy_factual_tutorial(self):
        """Tutorial intent should return FACTUAL strategy."""
        service = CreativeIdeationService()
        strategy = service.determine_strategy(
            intent_type="tutorial",
            topic="How to bake bread",
            tone="instructional",
        )
        assert strategy == ResearchStrategy.FACTUAL
    
    def test_strategy_creative_entertainment(self):
        """Entertainment intent should return CREATIVE strategy."""
        service = CreativeIdeationService()
        strategy = service.determine_strategy(
            intent_type="entertainment",
            topic="A robot's journey through space",
            tone="dramatic",
        )
        assert strategy == ResearchStrategy.CREATIVE
    
    def test_strategy_hybrid_inspirational(self):
        """Inspirational intent should return HYBRID strategy."""
        service = CreativeIdeationService()
        strategy = service.determine_strategy(
            intent_type="inspirational",
            topic="The power of perseverance",
            tone="motivational",
        )
        assert strategy == ResearchStrategy.HYBRID
    
    def test_strategy_creative_from_keywords(self):
        """Topic with strong creative indicators should be CREATIVE."""
        service = CreativeIdeationService()
        strategy = service.determine_strategy(
            intent_type="educational",
            topic="What if dragons existed in medieval times imagine the possibilities",
            tone="casual",
        )
        assert strategy == ResearchStrategy.HYBRID
    
    def test_strategy_factual_from_keywords(self):
        """Topic with factual indicators should be FACTUAL."""
        service = CreativeIdeationService()
        strategy = service.determine_strategy(
            intent_type="",
            topic="How does photosynthesis actually work? Explain the science",
            tone="",
        )
        assert strategy == ResearchStrategy.FACTUAL


class TestResearchModels:
    """Tests for research model structures."""
    
    def test_research_output_defaults(self):
        """ResearchOutput should have correct defaults."""
        output = ResearchOutput()
        assert output.strategy_used == ResearchStrategy.FACTUAL
        assert output.is_fictional is False
        assert output.research_findings == []
        assert output.research_images == []
        assert output.cache_hit is False
    
    def test_creative_ideation_output_defaults(self):
        """CreativeIdeationOutput should mark content as fictional."""
        output = CreativeIdeationOutput(
            story_concept="A robot learns to love",
            narrative_arc=NarrativeArc(
                hook="Meet ARIA-7",
                conflict="Can machines feel?",
                resolution="Love transcends code",
            ),
        )
        assert output.is_fictional is True
        assert output.strategy_used == ResearchStrategy.CREATIVE
        assert output.citations == []
    
    def test_hybrid_output_structure(self):
        """HybridResearchOutput should contain both factual and creative."""
        factual = ResearchOutput(
            executive_summary="Facts about Rome",
            strategy_used=ResearchStrategy.FACTUAL,
        )
        creative = CreativeIdeationOutput(
            story_concept="Romans with smartphones",
            narrative_arc=NarrativeArc(
                hook="Imagine",
                conflict="Technology clash",
                resolution="History changed",
            ),
        )
        hybrid = HybridResearchOutput(
            factual_base=factual,
            creative_extension=creative,
            blend_points=["Transition at historical accuracy"],
        )
        assert hybrid.strategy_used == ResearchStrategy.HYBRID
        assert hybrid.is_fictional is False
        assert hybrid.factual_base.executive_summary == "Facts about Rome"


class TestDeepResearchService:
    """Tests for Deep Research Service."""
    
    def test_cache_key_generation(self):
        """Cache key should be deterministic."""
        from app.services.deep_research import DeepResearchService
        
        key1 = DeepResearchService.generate_cache_key(
            topic="Black holes",
            tool_category="surreal_realism",
            strategy=ResearchStrategy.FACTUAL,
        )
        key2 = DeepResearchService.generate_cache_key(
            topic="Black holes",
            tool_category="surreal_realism",
            strategy=ResearchStrategy.FACTUAL,
        )
        assert key1 == key2
        assert key1.startswith("research:")
    
    def test_cache_key_varies_by_strategy(self):
        """Different strategies should have different cache keys."""
        from app.services.deep_research import DeepResearchService
        
        key_factual = DeepResearchService.generate_cache_key(
            topic="Test topic",
            tool_category="anime",
            strategy=ResearchStrategy.FACTUAL,
        )
        key_creative = DeepResearchService.generate_cache_key(
            topic="Test topic",
            tool_category="anime",
            strategy=ResearchStrategy.CREATIVE,
        )
        assert key_factual != key_creative
    
    def test_research_prompt_building(self):
        """Research prompt should include all context."""
        from app.services.deep_research import DeepResearchService
        
        service = DeepResearchService()
        prompt = service._build_research_prompt(
            topic="Quantum computing",
            tool_category="surreal_realism",
            duration_seconds=18,
            target_audience="tech",
        )
        
        assert "Quantum computing" in prompt
        assert "surreal_realism" in prompt
        assert "18 seconds" in prompt
        assert "tech" in prompt


class TestCreativeIdeationService:
    """Tests for Creative Ideation Service."""
    
    def test_creative_prompt_building(self):
        """Creative prompt should be structured correctly."""
        service = CreativeIdeationService()
        prompt = service._build_creative_prompt(
            topic="A wizard's apprentice",
            tool_category="high_octane_anime",
            duration_seconds=20,
            tone="dramatic",
        )
        
        assert "wizard's apprentice" in prompt
        assert "high_octane_anime" in prompt
        assert "20 seconds" in prompt
        assert "dramatic" in prompt
        assert "FICTION" in prompt


class TestDeepResearchAgent:
    """Tests for Deep Research Agent orchestration."""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock workflow state."""
        return {
            "workflow_id": "test-workflow-123",
            "topic": "How black holes work",
            "duration_seconds": 18,
            "category": "surreal_realism",
            "hitl_mode": "auto",
            "intent_metadata": {
                "intent_type": "educational",
                "tone": "informative",
            },
            "selected_tool": {
                "tool_id": "surreal_impossible_sims",
                "category": "surreal_realism",
            },
            "phase_timestamps": {},
        }
    
    @pytest.fixture
    def mock_creative_state(self):
        """Create a mock state for creative content."""
        return {
            "workflow_id": "test-workflow-456",
            "topic": "A lonely robot finding friendship in space",
            "duration_seconds": 18,
            "category": "high_octane_anime",
            "hitl_mode": "auto",
            "intent_metadata": {
                "intent_type": "entertainment",
                "tone": "dramatic",
            },
            "selected_tool": {
                "tool_id": "anime_concept_combat",
                "category": "high_octane_anime",
            },
            "phase_timestamps": {},
        }
    
    @pytest.mark.asyncio
    async def test_agent_determines_strategy(self, mock_state):
        """Agent should correctly determine research strategy."""
        from app.agents.deep_research import DeepResearchAgent
        
        agent = DeepResearchAgent()
        
        intent_type = agent._get_intent_type(mock_state)
        tone = agent._get_tone(mock_state)
        
        strategy = agent._creative_ideation.determine_strategy(
            intent_type=intent_type,
            topic=mock_state["topic"],
            tone=tone,
        )
        
        assert strategy == ResearchStrategy.FACTUAL
    
    @pytest.mark.asyncio
    async def test_agent_determines_creative_strategy(self, mock_creative_state):
        """Agent should detect creative content correctly."""
        from app.agents.deep_research import DeepResearchAgent
        
        agent = DeepResearchAgent()
        
        intent_type = agent._get_intent_type(mock_creative_state)
        tone = agent._get_tone(mock_creative_state)
        
        strategy = agent._creative_ideation.determine_strategy(
            intent_type=intent_type,
            topic=mock_creative_state["topic"],
            tone=tone,
        )
        
        assert strategy == ResearchStrategy.CREATIVE


class TestGoogleSearchService:
    """Tests for Google Custom Search Service."""
    
    def test_allowed_image_extensions(self):
        """Should recognize valid image extensions."""
        from app.services.google_search import ALLOWED_IMAGE_EXTENSIONS
        
        assert ".jpg" in ALLOWED_IMAGE_EXTENSIONS
        assert ".png" in ALLOWED_IMAGE_EXTENSIONS
        assert ".webp" in ALLOWED_IMAGE_EXTENSIONS
    
    def test_max_image_size(self):
        """Max image size should be 10MB."""
        from app.services.google_search import MAX_IMAGE_SIZE_BYTES
        
        assert MAX_IMAGE_SIZE_BYTES == 10 * 1024 * 1024


class TestRedisService:
    """Tests for Redis caching service."""
    
    def test_key_prefixing(self):
        """Keys should be prefixed with 'raba:'."""
        from app.services.redis import RedisService
        
        service = RedisService()
        key = service._make_key("test_key")
        
        assert key == "raba:test_key"
