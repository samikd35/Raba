"""Tests for Script Writer Agent.

Tests script generation, structure validation, and viral metrics.
Reference: PHASE2_4_SCRIPT_GENERATOR_PLAN.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
from app.agents.script_writer import (
    ScriptWriterAgent,
    get_script_writer_agent,
    _extract_research_summary,
    _calculate_scene_count,
    _calculate_viral_metrics,
    HOOK_ARCHETYPE_MAP,
    TOOL_VISUAL_VOCABULARY,
)


class TestScriptModels:
    """Tests for script Pydantic models."""
    
    def test_hook_section_valid(self):
        """Test valid HookSection creation."""
        hook = HookSection(
            archetype=HookArchetype.TEACHER,
            script="You've been understanding this wrong.",
            visual_direction="Close-up zoom out reveal",
            duration_seconds=2.0,
            psychological_lever="curiosity_gap",
        )
        assert hook.archetype == HookArchetype.TEACHER
        assert hook.duration_seconds == 2.0
        assert "curiosity_gap" in hook.psychological_lever
    
    def test_hook_section_duration_bounds(self):
        """Test hook duration must be 1-3 seconds."""
        with pytest.raises(ValueError):
            HookSection(
                archetype=HookArchetype.TEACHER,
                script="Too long hook",
                visual_direction="Test",
                duration_seconds=5.0,  # Invalid: > 3.0
            )
    
    def test_scene_valid(self):
        """Test valid Scene creation."""
        scene = Scene(
            scene_number=1,
            timestamp_start=2.0,
            timestamp_end=6.0,
            description="Rich visual description",
            dialogue="Short dialogue here.",
            audio_cues=["ambient sound"],
            camera_direction="slow zoom",
            lighting="dramatic",
            mood="intense",
            pattern_interrupt_type=PatternInterruptType.NEW_FACT,
            visual_keywords=["keyword1", "keyword2"],
        )
        assert scene.scene_number == 1
        assert scene.duration_seconds == 4.0
        assert scene.pattern_interrupt_type == PatternInterruptType.NEW_FACT
    
    def test_scene_timestamp_validation(self):
        """Test timestamp_end must be after timestamp_start."""
        with pytest.raises(ValueError):
            Scene(
                scene_number=1,
                timestamp_start=6.0,
                timestamp_end=4.0,  # Invalid: before start
                description="Test",
            )
    
    def test_cta_section_valid(self):
        """Test valid CTASection creation."""
        cta = CTASection(
            type=CTAType.FOLLOW,
            placement_seconds=16.5,
            script="Follow for more.",
            visual_direction="Logo animation",
        )
        assert cta.type == CTAType.FOLLOW
        assert cta.placement_seconds == 16.5
    
    def test_viral_metrics_calculation(self):
        """Test viral score calculation with weights."""
        metrics = ViralMetrics(
            hook_strength=0.85,
            pattern_interrupt_density=0.80,
            emotional_arc=0.75,
            call_to_action_clarity=0.80,
            audience_fit=0.75,
            novelty_factor=0.70,
        )
        score = metrics.calculate_viral_score()
        
        # Expected: 0.85*0.25 + 0.80*0.20 + 0.75*0.20 + 0.80*0.15 + 0.75*0.10 + 0.70*0.10
        # = 0.2125 + 0.16 + 0.15 + 0.12 + 0.075 + 0.07 = 0.7875
        assert 0.78 <= score <= 0.80
        assert score <= 0.98  # Capped at 0.98
    
    def test_script_output_valid(self):
        """Test valid ScriptOutput creation."""
        hook = HookSection(
            archetype=HookArchetype.TEACHER,
            script="Test hook",
            visual_direction="Test visual",
            duration_seconds=2.0,
        )
        scenes = [
            Scene(
                scene_number=1,
                timestamp_start=2.0,
                timestamp_end=8.0,
                description="Scene 1",
            ),
            Scene(
                scene_number=2,
                timestamp_start=8.0,
                timestamp_end=16.5,
                description="Scene 2",
            ),
        ]
        cta = CTASection(
            type=CTAType.FOLLOW,
            placement_seconds=16.5,
        )
        
        script = ScriptOutput(
            hook=hook,
            scenes=scenes,
            call_to_action=cta,
            total_duration_seconds=18.0,
        )
        
        assert len(script.scenes) == 2
        assert script.total_duration_seconds == 18.0
    
    def test_script_output_duration_bounds(self):
        """Test script duration must be 8-25 seconds."""
        hook = HookSection(
            archetype=HookArchetype.TEACHER,
            script="Test",
            visual_direction="Test",
        )
        scenes = [Scene(
            scene_number=1,
            timestamp_start=2.0,
            timestamp_end=4.0,
            description="Test",
        )]
        cta = CTASection(type=CTAType.FOLLOW, placement_seconds=4.0)
        
        with pytest.raises(ValueError):
            ScriptOutput(
                hook=hook,
                scenes=scenes,
                call_to_action=cta,
                total_duration_seconds=5.0,  # Invalid: < 8.0
            )


class TestScriptWriterHelpers:
    """Tests for helper functions."""
    
    def test_scene_count_8s(self):
        """Test scene count for 8 second video."""
        count = _calculate_scene_count(8)
        assert 2 <= count <= 3
    
    def test_scene_count_18s(self):
        """Test scene count for 18 second video."""
        count = _calculate_scene_count(18)
        assert 4 <= count <= 5
    
    def test_scene_count_25s(self):
        """Test scene count for 25 second video."""
        count = _calculate_scene_count(25)
        assert 6 <= count <= 8
    
    def test_extract_research_summary_factual(self):
        """Test research summary extraction from factual data."""
        research_data = {
            "strategy_used": "factual",
            "is_fictional": False,
            "executive_summary": "Key insights about the topic.",
            "research_findings": [
                {"key_facts": ["Fact 1", "Fact 2", "Fact 3"]},
                {"key_facts": ["Fact 4"]},
            ],
            "interesting_angles": ["Angle 1", "Angle 2"],
        }
        
        summary, is_fictional = _extract_research_summary(research_data)
        
        assert not is_fictional
        assert "Key insights" in summary
        assert "Fact 1" in summary
    
    def test_extract_research_summary_creative(self):
        """Test research summary extraction from creative data."""
        research_data = {
            "strategy_used": "creative",
            "is_fictional": True,
            "story_concept": "A hero's journey through space.",
            "narrative_arc": {"hook": "The unexpected discovery"},
            "characters": [{"name": "Alex"}, {"name": "Nova"}],
            "tone": "epic",
            "visual_inspiration": ["sci-fi", "cosmic"],
        }
        
        summary, is_fictional = _extract_research_summary(research_data)
        
        assert is_fictional
        assert "hero's journey" in summary
        assert "Alex" in summary
    
    def test_extract_research_summary_hybrid(self):
        """Test research summary extraction from hybrid data."""
        research_data = {
            "strategy_used": "hybrid",
            "is_fictional": False,
            "factual_base": {
                "research_findings": [{"key_facts": ["Historical fact"]}],
            },
            "creative_extension": {
                "story_concept": "What if they had met?",
            },
            "blend_points": ["Transition at meeting"],
        }
        
        summary, is_fictional = _extract_research_summary(research_data)
        
        assert not is_fictional
        assert "Historical fact" in summary or "What if" in summary
    
    def test_hook_archetype_mapping(self):
        """Test hook archetype mapping for intent types."""
        assert HookArchetype.TEACHER in HOOK_ARCHETYPE_MAP["educational"]
        assert HookArchetype.STORYTELLER in HOOK_ARCHETYPE_MAP["entertainment"]
        assert HookArchetype.FORTUNETELLER in HOOK_ARCHETYPE_MAP["inspirational"]
    
    def test_tool_visual_vocabulary(self):
        """Test tool visual vocabulary exists for all categories."""
        assert "surreal_realism" in TOOL_VISUAL_VOCABULARY
        assert "high_octane_anime" in TOOL_VISUAL_VOCABULARY
        assert "stylized_3d" in TOOL_VISUAL_VOCABULARY
        
        for category, vocab in TOOL_VISUAL_VOCABULARY.items():
            assert "style_keywords" in vocab
            assert "camera_styles" in vocab
            assert "mood_keywords" in vocab


class TestViralMetricsCalculation:
    """Tests for viral metrics calculation."""
    
    def test_calculate_viral_metrics_good_hook(self):
        """Test metrics calculation with good hook."""
        hook = HookSection(
            archetype=HookArchetype.TEACHER,
            script="Did you know this?",  # Question format
            visual_direction="Test",
            duration_seconds=2.0,  # Good: <= 2.5s
        )
        scenes = [
            Scene(
                scene_number=1,
                timestamp_start=2.0,
                timestamp_end=10.0,
                description="Test",
                pattern_interrupt_type=PatternInterruptType.NEW_FACT,
                mood="setup",
            ),
            Scene(
                scene_number=2,
                timestamp_start=10.0,
                timestamp_end=16.5,
                description="Test",
                pattern_interrupt_type=PatternInterruptType.EMOTIONAL_PIVOT,
                mood="intense climax",
            ),
        ]
        cta = CTASection(
            type=CTAType.FOLLOW,
            placement_seconds=16.5,
            script="Follow for more!",
        )
        
        script = ScriptOutput(
            hook=hook,
            scenes=scenes,
            call_to_action=cta,
            total_duration_seconds=18.0,
        )
        
        metrics = _calculate_viral_metrics(script)
        
        # Good hook (short + question)
        assert metrics.hook_strength >= 0.85
        
        # All scenes have interrupts
        assert metrics.pattern_interrupt_density == 1.0
        
        # Has setup and climax
        assert metrics.emotional_arc >= 0.75
        
        # CTA has script
        assert metrics.call_to_action_clarity == 0.80
    
    def test_calculate_viral_metrics_poor_hook(self):
        """Test metrics calculation with poor hook."""
        hook = HookSection(
            archetype=HookArchetype.STORYTELLER,
            script="Let me tell you something",  # No question
            visual_direction="Test",
            duration_seconds=3.0,  # Poor: > 2.5s
        )
        scenes = [
            Scene(
                scene_number=1,
                timestamp_start=3.0,
                timestamp_end=16.5,
                description="Test",
                mood="neutral",  # No setup/climax keywords
            ),
        ]
        cta = CTASection(
            type=CTAType.FOLLOW,
            placement_seconds=16.5,
            script="",  # No CTA script
        )
        
        script = ScriptOutput(
            hook=hook,
            scenes=scenes,
            call_to_action=cta,
            total_duration_seconds=18.0,
        )
        
        metrics = _calculate_viral_metrics(script)
        
        # Poor hook (long, no question)
        assert metrics.hook_strength < 0.80
        
        # No interrupts
        assert metrics.pattern_interrupt_density == 0.0
        
        # No CTA script
        assert metrics.call_to_action_clarity == 0.60


class TestScriptWriterAgent:
    """Tests for ScriptWriterAgent."""
    
    def test_get_script_writer_agent_singleton(self):
        """Test singleton pattern for agent."""
        agent1 = get_script_writer_agent()
        agent2 = get_script_writer_agent()
        assert agent1 is agent2
    
    @pytest.mark.asyncio
    async def test_generate_script_mock(self):
        """Test script generation with mocked Gemini response."""
        mock_script = ScriptOutput(
            hook=HookSection(
                archetype=HookArchetype.TEACHER,
                script="Test hook",
                visual_direction="Test visual",
                duration_seconds=2.0,
            ),
            scenes=[
                Scene(
                    scene_number=1,
                    timestamp_start=2.0,
                    timestamp_end=16.5,
                    description="Test scene",
                    pattern_interrupt_type=PatternInterruptType.NEW_FACT,
                )
            ],
            call_to_action=CTASection(
                type=CTAType.FOLLOW,
                placement_seconds=16.5,
            ),
            total_duration_seconds=18.0,
        )
        
        with patch("app.agents.script_writer.get_gemini_service") as mock_gemini:
            mock_service = MagicMock()
            mock_service.generate_structured_output = AsyncMock(return_value=mock_script)
            mock_gemini.return_value = mock_service
            
            agent = ScriptWriterAgent()
            agent.gemini = mock_service
            
            result = await agent.generate_script(
                topic="How black holes work",
                duration_seconds=18,
                research_data={
                    "strategy_used": "factual",
                    "research_findings": [{"key_facts": ["Fact 1"]}],
                    "executive_summary": "About black holes",
                },
                intent_type="educational",
                tone="informative",
                target_audience="general",
                tool_category="surreal_realism",
            )
            
            assert result is not None
            assert result.hook.archetype == HookArchetype.TEACHER
            assert len(result.scenes) >= 1
            assert result.viral_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_run_from_state(self):
        """Test running agent from workflow state."""
        mock_script = ScriptOutput(
            hook=HookSection(
                archetype=HookArchetype.TEACHER,
                script="Test hook",
                visual_direction="Test visual",
                duration_seconds=2.0,
            ),
            scenes=[
                Scene(
                    scene_number=1,
                    timestamp_start=2.0,
                    timestamp_end=16.5,
                    description="Test scene",
                )
            ],
            call_to_action=CTASection(
                type=CTAType.FOLLOW,
                placement_seconds=16.5,
            ),
            total_duration_seconds=18.0,
        )
        
        state = {
            "workflow_id": "test-123",
            "topic": "Test topic",
            "duration_seconds": 18,
            "research_data": {
                "strategy_used": "factual",
                "research_findings": [],
                "executive_summary": "Test",
            },
            "intent_metadata": {
                "intent_type": "educational",
                "tone": "informative",
                "target_audience": "general",
            },
            "selected_tool": {
                "category": "surreal_realism",
            },
        }
        
        with patch("app.agents.script_writer.get_gemini_service") as mock_gemini:
            mock_service = MagicMock()
            mock_service.generate_structured_output = AsyncMock(return_value=mock_script)
            mock_gemini.return_value = mock_service
            
            agent = ScriptWriterAgent()
            agent.gemini = mock_service
            
            result = await agent.run(state)
            
            assert "script_output" in result
            assert "hook" in result
            assert "scenes" in result
            assert "call_to_action" in result
            assert "viral_score" in result


class TestPatternInterrupts:
    """Tests for pattern interrupt logic."""
    
    def test_pattern_interrupt_types_enum(self):
        """Test all pattern interrupt types exist."""
        types = [
            PatternInterruptType.SCENE_CHANGE,
            PatternInterruptType.VISUAL_EFFECT,
            PatternInterruptType.NEW_FACT,
            PatternInterruptType.PERSPECTIVE_SHIFT,
            PatternInterruptType.EMOTIONAL_PIVOT,
            PatternInterruptType.SENSORY_CUE,
        ]
        assert len(types) == 6
    
    def test_scene_with_interrupt(self):
        """Test scene with pattern interrupt assigned."""
        scene = Scene(
            scene_number=1,
            timestamp_start=2.0,
            timestamp_end=6.0,
            description="Test scene",
            pattern_interrupt_type=PatternInterruptType.NEW_FACT,
        )
        assert scene.pattern_interrupt_type == PatternInterruptType.NEW_FACT
    
    def test_scene_without_interrupt(self):
        """Test scene without pattern interrupt."""
        scene = Scene(
            scene_number=1,
            timestamp_start=2.0,
            timestamp_end=6.0,
            description="Test scene",
        )
        assert scene.pattern_interrupt_type is None


class TestToolIntegration:
    """Tests for tool specs integration."""
    
    def test_surreal_realism_vocabulary(self):
        """Test surreal realism tool vocabulary."""
        vocab = TOOL_VISUAL_VOCABULARY["surreal_realism"]
        assert "flowing liquid-glass" in vocab["style_keywords"]
        assert "photorealistic grounding" in vocab["style_keywords"]
    
    def test_high_octane_anime_vocabulary(self):
        """Test high octane anime tool vocabulary."""
        vocab = TOOL_VISUAL_VOCABULARY["high_octane_anime"]
        assert "Sakuga-style" in vocab["style_keywords"]
        assert "dynamic tracking" in vocab["camera_styles"]
    
    def test_stylized_3d_vocabulary(self):
        """Test stylized 3D tool vocabulary."""
        vocab = TOOL_VISUAL_VOCABULARY["stylized_3d"]
        assert "miniature landscape" in vocab["style_keywords"]
        assert "isometric view" in vocab["style_keywords"]
