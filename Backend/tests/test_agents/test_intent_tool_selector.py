"""Tests for Intent/Tool Selector Agent.

Tests intent extraction, parameter validation, tool scoring, and selection.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.intent_tool_selector import (
    DEFAULT_TOOLS,
    IntentToolSelectorAgent,
    IntentToolSelectorError,
)
from app.models.tool import (
    IntentExtractionResponse,
    IntentMetadata,
    IntentToolOutput,
    IntentType,
    TargetAudience,
    ToneType,
    ToolCapabilities,
    ToolMetadata,
    ToolRelevanceResponse,
    ToolScore,
    UserReferenceMode,
    ValidatedParams,
)
from app.models.workflow import (
    AspectRatioEnum,
    CategoryEnum,
    ResolutionEnum,
)


class TestParameterValidation:
    """Tests for parameter validation."""
    
    def test_valid_duration_range(self):
        """Test that valid duration passes through."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.duration_seconds == 18
    
    def test_duration_below_minimum_adjusted(self):
        """Test that duration below 8 is adjusted to 8."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=5,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.duration_seconds == 8
    
    def test_duration_above_maximum_adjusted(self):
        """Test that duration above 25 is adjusted to 25."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=30,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.duration_seconds == 25
    
    def test_valid_aspect_ratio_vertical(self):
        """Test vertical aspect ratio validation."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.aspect_ratio == AspectRatioEnum.VERTICAL
    
    def test_valid_aspect_ratio_horizontal(self):
        """Test horizontal aspect ratio validation."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="16:9",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.aspect_ratio == AspectRatioEnum.HORIZONTAL
    
    def test_invalid_aspect_ratio_defaults_to_vertical(self):
        """Test that invalid aspect ratio defaults to 9:16."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="4:3",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.aspect_ratio == AspectRatioEnum.VERTICAL
    
    def test_valid_resolution_1080p(self):
        """Test 1080p resolution validation."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.resolution == ResolutionEnum.FULL_HD
    
    def test_valid_resolution_720p(self):
        """Test 720p resolution validation."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="720p",
            user_has_reference_image=False,
        )
        assert params.resolution == ResolutionEnum.HD
    
    def test_invalid_resolution_defaults_to_1080p(self):
        """Test that invalid resolution defaults to 1080p."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="4K",
            user_has_reference_image=False,
        )
        assert params.resolution == ResolutionEnum.FULL_HD
    
    def test_user_reference_mode_with_reference(self):
        """Test reference mode when user has image."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=True,
        )
        assert params.user_reference_mode == UserReferenceMode.WITH_REFERENCE
    
    def test_user_reference_mode_no_reference(self):
        """Test reference mode when user has no image."""
        agent = IntentToolSelectorAgent()
        params = agent._validate_params(
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            user_has_reference_image=False,
        )
        assert params.user_reference_mode == UserReferenceMode.NO_REFERENCE


class TestFallbackIntent:
    """Tests for fallback intent classification."""
    
    def test_educational_intent_from_how_keyword(self):
        """Test educational intent detection from 'how' keyword."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("How do magnets work")
        assert intent.intent_type == IntentType.EDUCATIONAL
    
    def test_educational_intent_from_what_keyword(self):
        """Test educational intent detection from 'what' keyword."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("What is gravity")
        assert intent.intent_type == IntentType.EDUCATIONAL
    
    def test_entertainment_intent_from_funny_keyword(self):
        """Test entertainment intent detection from 'funny' keyword."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("Funny cat fails")
        assert intent.intent_type == IntentType.ENTERTAINMENT
    
    def test_inspirational_intent_from_story_keyword(self):
        """Test inspirational intent detection from 'story' keyword."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("The story of overcoming adversity")
        assert intent.intent_type == IntentType.INSPIRATIONAL
    
    def test_tech_audience_from_keywords(self):
        """Test tech audience detection."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("How AI programming works")
        assert intent.target_audience == TargetAudience.TECH
    
    def test_science_audience_from_keywords(self):
        """Test science audience detection."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("How biology and chemistry work")
        assert intent.target_audience == TargetAudience.SCIENCE
    
    def test_business_audience_from_keywords(self):
        """Test business audience detection."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("How to invest money wisely")
        assert intent.target_audience == TargetAudience.BUSINESS
    
    def test_general_audience_default(self):
        """Test general audience as default."""
        agent = IntentToolSelectorAgent()
        intent = agent._fallback_intent("Random topic about nothing specific")
        assert intent.target_audience == TargetAudience.GENERAL


class TestToolScoring:
    """Tests for tool scoring functionality."""
    
    def test_tool_score_calculation(self):
        """Test weighted score calculation."""
        total = ToolScore.calculate_total(
            relevance=0.8,
            capability=1.0,
            cost=0.6,
            recency=0.5,
        )
        expected = (0.8 * 0.4) + (1.0 * 0.3) + (0.6 * 0.2) + (0.5 * 0.1)
        assert abs(total - expected) < 0.001
    
    def test_tool_score_model(self):
        """Test ToolScore model creation."""
        score = ToolScore(
            tool_id="test_tool",
            relevance_score=0.8,
            capability_score=1.0,
            cost_score=0.6,
            recency_score=0.5,
            total_score=0.74,
        )
        assert score.tool_id == "test_tool"
        assert score.total_score == 0.74
    
    def test_keyword_relevance_scoring(self):
        """Test fallback keyword-based relevance scoring."""
        agent = IntentToolSelectorAgent()
        tool = DEFAULT_TOOLS[0]
        intent = IntentMetadata(
            topic="How magnets and physics work",
            intent_type=IntentType.EDUCATIONAL,
            target_audience=TargetAudience.SCIENCE,
            tone=ToneType.SERIOUS,
            keywords=["magnets", "physics", "force"],
            complexity_score=0.5,
        )
        
        score = agent._keyword_relevance_score(tool, intent)
        assert 0.0 <= score <= 1.0


class TestCapabilityMatching:
    """Tests for capability matching."""
    
    def test_capability_match_passes_for_valid_params(self):
        """Test capability matching with valid parameters."""
        agent = IntentToolSelectorAgent()
        tool = DEFAULT_TOOLS[0]
        params = ValidatedParams(
            duration_seconds=18,
            aspect_ratio=AspectRatioEnum.VERTICAL,
            resolution=ResolutionEnum.FULL_HD,
            user_reference_mode=UserReferenceMode.NO_REFERENCE,
        )
        
        assert agent._check_capability_match(tool, params) is True
    
    def test_capability_match_fails_for_unsupported_duration(self):
        """Test capability matching fails for unsupported duration."""
        agent = IntentToolSelectorAgent()
        
        tool = ToolMetadata(
            tool_id="limited_tool",
            tool_name="Limited Tool",
            category=CategoryEnum.SURREAL_REALISM,
            description="A tool with limited duration",
            max_duration_seconds=10,
        )
        
        params = ValidatedParams(
            duration_seconds=20,
            aspect_ratio=AspectRatioEnum.VERTICAL,
            resolution=ResolutionEnum.FULL_HD,
            user_reference_mode=UserReferenceMode.NO_REFERENCE,
        )
        
        assert agent._check_capability_match(tool, params) is False


class TestToolSelection:
    """Tests for tool selection logic."""
    
    def test_default_tools_loaded(self):
        """Test that default tools are loaded."""
        agent = IntentToolSelectorAgent()
        assert len(agent.tools) >= 3
    
    def test_fallback_tool_returns_surreal_realism(self):
        """Test fallback tool is Surreal Realism."""
        agent = IntentToolSelectorAgent()
        fallback = agent._get_fallback_tool()
        assert fallback.tool_id == "surreal_impossible_sims"
    
    def test_fallback_tool_with_empty_tools_returns_default(self):
        """Test fallback with empty tools list still returns default."""
        agent = IntentToolSelectorAgent(tools=[])
        fallback = agent._get_fallback_tool()
        assert fallback.tool_id == "surreal_impossible_sims"
    
    def test_execution_params_built_correctly(self):
        """Test execution parameters are built correctly."""
        agent = IntentToolSelectorAgent()
        tool = DEFAULT_TOOLS[0]
        intent = IntentMetadata(
            topic="Test topic",
            intent_type=IntentType.EDUCATIONAL,
            target_audience=TargetAudience.SCIENCE,
            tone=ToneType.DRAMATIC,
            keywords=["test", "keyword"],
            complexity_score=0.5,
        )
        params = ValidatedParams(
            duration_seconds=18,
            aspect_ratio=AspectRatioEnum.VERTICAL,
            resolution=ResolutionEnum.FULL_HD,
            user_reference_mode=UserReferenceMode.NO_REFERENCE,
        )
        
        exec_params = agent._build_execution_params(tool, intent, params)
        
        assert exec_params["tool_id"] == tool.tool_id
        assert exec_params["duration"] == 18
        assert exec_params["tone"] == "dramatic"
        assert exec_params["aspect_ratio"] == "9:16"


class TestIntentToolOutput:
    """Tests for IntentToolOutput model."""
    
    def test_intent_tool_output_creation(self):
        """Test creating IntentToolOutput."""
        output = IntentToolOutput(
            topic="Test topic",
            intent_metadata=IntentMetadata(
                topic="Test topic",
                intent_type=IntentType.EDUCATIONAL,
                target_audience=TargetAudience.GENERAL,
                tone=ToneType.CASUAL,
                keywords=["test"],
                complexity_score=0.5,
            ),
            validated_params=ValidatedParams(
                duration_seconds=18,
                aspect_ratio=AspectRatioEnum.VERTICAL,
                resolution=ResolutionEnum.FULL_HD,
                user_reference_mode=UserReferenceMode.NO_REFERENCE,
            ),
            selected_tool=DEFAULT_TOOLS[0],
            tool_execution_params={},
            confidence=0.85,
            fallback_used=False,
        )
        
        assert output.topic == "Test topic"
        assert output.confidence == 0.85
        assert output.fallback_used is False
    
    def test_confidence_rejects_out_of_range(self):
        """Test confidence rejects values outside 0-1 range."""
        import pydantic
        
        with pytest.raises(pydantic.ValidationError):
            IntentToolOutput(
                topic="Test",
                intent_metadata=IntentMetadata(
                    topic="Test",
                    intent_type=IntentType.EDUCATIONAL,
                    target_audience=TargetAudience.GENERAL,
                    tone=ToneType.CASUAL,
                    keywords=["test"],
                    complexity_score=0.5,
                ),
                validated_params=ValidatedParams(
                    duration_seconds=18,
                    aspect_ratio=AspectRatioEnum.VERTICAL,
                    resolution=ResolutionEnum.FULL_HD,
                    user_reference_mode=UserReferenceMode.NO_REFERENCE,
                ),
                selected_tool=DEFAULT_TOOLS[0],
                tool_execution_params={},
                confidence=1.5,
                fallback_used=False,
            )


class TestAgentIntegration:
    """Integration tests for the full agent flow."""
    
    @pytest.mark.asyncio
    async def test_run_with_mocked_gemini(self):
        """Test full agent run with mocked Gemini service."""
        mock_gemini = MagicMock()
        
        mock_gemini.generate_structured_output = AsyncMock(
            side_effect=[
                IntentExtractionResponse(
                    intent_type=IntentType.EDUCATIONAL,
                    target_audience=TargetAudience.SCIENCE,
                    tone=ToneType.DRAMATIC,
                    keywords=["black", "holes", "physics", "space"],
                    complexity_score=0.7,
                    reasoning="Science education topic about cosmology",
                ),
                ToolRelevanceResponse(
                    relevance_score=0.9,
                    reasoning="Perfect match for physics visualization",
                ),
                ToolRelevanceResponse(
                    relevance_score=0.4,
                    reasoning="Less suited for science topics",
                ),
                ToolRelevanceResponse(
                    relevance_score=0.6,
                    reasoning="Could work for data aspects",
                ),
            ]
        )
        
        agent = IntentToolSelectorAgent(gemini_service=mock_gemini)
        
        result = await agent.run(
            topic="How black holes work",
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            category="auto",
            user_has_reference_image=False,
        )
        
        assert isinstance(result, IntentToolOutput)
        assert result.topic == "How black holes work"
        assert result.intent_metadata.intent_type == IntentType.EDUCATIONAL
        assert result.validated_params.duration_seconds == 18
        assert result.selected_tool is not None
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_run_with_category_filter(self):
        """Test agent run with specific category filter."""
        mock_gemini = MagicMock()
        
        mock_gemini.generate_structured_output = AsyncMock(
            side_effect=[
                IntentExtractionResponse(
                    intent_type=IntentType.ENTERTAINMENT,
                    target_audience=TargetAudience.GENERAL,
                    tone=ToneType.HUMOROUS,
                    keywords=["philosophy", "debate"],
                    complexity_score=0.5,
                    reasoning="Philosophical entertainment",
                ),
                ToolRelevanceResponse(
                    relevance_score=0.85,
                    reasoning="Great for philosophical debates",
                ),
            ]
        )
        
        agent = IntentToolSelectorAgent(gemini_service=mock_gemini)
        
        result = await agent.run(
            topic="Plato vs Aristotle",
            duration_seconds=20,
            aspect_ratio="9:16",
            resolution="1080p",
            category="high_octane_anime",
            user_has_reference_image=False,
        )
        
        assert result.selected_tool.category == CategoryEnum.HIGH_OCTANE_ANIME
    
    @pytest.mark.asyncio
    async def test_run_uses_fallback_on_llm_failure(self):
        """Test agent uses fallback when LLM fails."""
        mock_gemini = MagicMock()
        mock_gemini.generate_structured_output = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        agent = IntentToolSelectorAgent(gemini_service=mock_gemini)
        
        result = await agent.run(
            topic="How magnets work",
            duration_seconds=18,
            aspect_ratio="9:16",
            resolution="1080p",
            category="auto",
            user_has_reference_image=False,
        )
        
        assert result.intent_metadata.reasoning == "Fallback classification based on keyword matching"
        assert result.selected_tool is not None
