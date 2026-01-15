"""Tests for Video Generator Agent.

Tests segment planning, reference image selection, prompt building,
and video generation flow.

Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.video_generator import (
    VideoGeneratorAgent,
    calculate_segments_needed,
    plan_video_segments,
    select_reference_images,
    build_video_prompt,
    build_extension_prompt,
    TOOL_VIDEO_VOCABULARY,
    MAX_SEGMENT_DURATION,
    EXTENSION_DURATION,
    MAX_REFERENCE_IMAGES,
)
from app.models.video import (
    GeneratedVideo,
    HITLVideoAction,
    HITLVideoFeedback,
    ReferenceImageSelection,
    VideoAspectRatio,
    VideoGenerationConfig,
    VideoGeneratorOutput,
    VideoModel,
    VideoResolution,
    VideoSegment,
    VideoSegmentType,
)


class TestCalculateSegmentsNeeded:
    """Tests for segment count calculation logic."""
    
    def test_8s_duration_single_segment(self):
        """8s duration needs only 1 segment."""
        result = calculate_segments_needed(8)
        assert result == 1
    
    def test_12s_duration_two_segments(self):
        """12s duration needs 2 segments (8s + 4s extension)."""
        result = calculate_segments_needed(12)
        assert result == 2
    
    def test_18s_duration_three_segments(self):
        """18s duration needs 3 segments (8s + 7s + 3s)."""
        result = calculate_segments_needed(18)
        assert result == 3
    
    def test_25s_duration_four_segments(self):
        """25s duration needs 4 segments (8s + 7s + 7s + 3s)."""
        result = calculate_segments_needed(25)
        assert result == 4
    
    def test_less_than_8s_single_segment(self):
        """Duration less than 8s needs only 1 segment."""
        result = calculate_segments_needed(6)
        assert result == 1


class TestPlanVideoSegments:
    """Tests for video segment planning."""
    
    def test_8s_video_single_segment(self):
        """8s video has single initial segment."""
        segments = plan_video_segments(8)
        
        assert len(segments) == 1
        assert segments[0]["type"] == "initial"
        assert segments[0]["start_time"] == 0.0
        assert segments[0]["end_time"] == 8.0
        assert segments[0]["duration"] == 8.0
    
    def test_18s_video_three_segments(self):
        """18s video has 3 segments with correct timing."""
        segments = plan_video_segments(18)
        
        assert len(segments) == 3
        
        assert segments[0]["type"] == "initial"
        assert segments[0]["start_time"] == 0.0
        assert segments[0]["end_time"] == 8.0
        
        assert segments[1]["type"] == "extension"
        assert segments[1]["start_time"] == 8.0
        
        assert segments[2]["type"] == "extension"
    
    def test_segment_numbers_are_sequential(self):
        """Segment numbers are 0-indexed and sequential."""
        segments = plan_video_segments(25)
        
        for i, seg in enumerate(segments):
            assert seg["segment_number"] == i
    
    def test_first_segment_is_always_initial(self):
        """First segment is always 'initial' type."""
        for duration in [8, 12, 18, 25]:
            segments = plan_video_segments(duration)
            assert segments[0]["type"] == "initial"
    
    def test_remaining_segments_are_extensions(self):
        """All segments after first are 'extension' type."""
        segments = plan_video_segments(25)
        
        for seg in segments[1:]:
            assert seg["type"] == "extension"


class TestSelectReferenceImages:
    """Tests for reference image selection logic."""
    
    def test_max_three_images_selected(self):
        """Never select more than 3 images."""
        result = select_reference_images(
            user_reference_url="user.png",
            generated_images=["gen1.png", "gen2.png", "gen3.png"],
            research_images=["res1.png", "res2.png"],
        )
        
        assert len(result) <= MAX_REFERENCE_IMAGES
    
    def test_user_reference_has_highest_priority(self):
        """User reference is always first if provided."""
        result = select_reference_images(
            user_reference_url="user.png",
            generated_images=["gen1.png", "gen2.png"],
            research_images=["res1.png"],
        )
        
        assert result[0] == "user.png"
    
    def test_generated_images_have_second_priority(self):
        """Generated images come before research images."""
        result = select_reference_images(
            user_reference_url=None,
            generated_images=["gen1.png", "gen2.png"],
            research_images=["res1.png", "res2.png"],
        )
        
        assert "gen1.png" in result
        assert result.index("gen1.png") < result.index("res1.png") if "res1.png" in result else True
    
    def test_first_and_last_generated_images_selected(self):
        """For 3+ generated images, select first and last for coverage."""
        result = select_reference_images(
            user_reference_url=None,
            generated_images=["gen1.png", "gen2.png", "gen3.png"],
            research_images=[],
        )
        
        assert "gen1.png" in result
        assert "gen3.png" in result
    
    def test_research_images_fill_remaining_slots(self):
        """Research images fill remaining slots after user and generated."""
        result = select_reference_images(
            user_reference_url="user.png",
            generated_images=["gen1.png"],
            research_images=["res1.png", "res2.png"],
        )
        
        assert len(result) == 3
        assert "res1.png" in result
    
    def test_no_images_returns_empty(self):
        """No images available returns empty list."""
        result = select_reference_images(
            user_reference_url=None,
            generated_images=[],
            research_images=[],
        )
        
        assert result == []
    
    def test_only_user_reference(self):
        """Only user reference returns single-element list."""
        result = select_reference_images(
            user_reference_url="user.png",
            generated_images=[],
            research_images=[],
        )
        
        assert result == ["user.png"]


class TestBuildVideoPrompt:
    """Tests for Veo prompt building."""
    
    @pytest.fixture
    def sample_script_output(self):
        """Create sample script output for tests."""
        return {
            "hook": {
                "text": "You won't believe what happened!",
                "visual_direction": "Dramatic zoom on football",
            },
            "scenes": [
                {
                    "scene_number": 1,
                    "description": "Player dribbles past defenders",
                    "dialogue": "Watch this skill!",
                    "camera_direction": "tracking shot",
                    "mood": "intense",
                    "start_time": 2,
                    "end_time": 6,
                },
                {
                    "scene_number": 2,
                    "description": "Goal celebration",
                    "dialogue": "GOOOAL!",
                    "camera_direction": "wide shot",
                    "mood": "euphoric",
                    "start_time": 6,
                    "end_time": 12,
                },
            ],
            "call_to_action": {
                "text": "Like and subscribe!",
                "visual_direction": "End card animation",
            },
            "duration_seconds": 18,
        }
    
    def test_prompt_includes_style_keywords(self, sample_script_output):
        """Prompt includes tool-specific style keywords."""
        segment_info = {"start_time": 0, "end_time": 8}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="surreal_realism",
            topic="Football magic",
            segment_info=segment_info,
        )
        
        assert any(kw in prompt for kw in ["photorealistic", "cinematic", "dreamlike"])
    
    def test_prompt_includes_hook_for_initial_segment(self, sample_script_output):
        """Initial segment prompt includes hook content."""
        segment_info = {"start_time": 0, "end_time": 8}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="surreal_realism",
            topic="Football",
            segment_info=segment_info,
            is_extension=False,
        )
        
        assert "won't believe" in prompt
    
    def test_extension_prompt_includes_continuation(self, sample_script_output):
        """Extension prompt includes continuation context."""
        segment_info = {"start_time": 8, "end_time": 15}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="surreal_realism",
            topic="Football",
            segment_info=segment_info,
            is_extension=True,
            previous_segment_end="Player finished dribbling",
        )
        
        assert "CONTINUATION" in prompt
        assert "finished dribbling" in prompt
    
    def test_prompt_includes_audio_cues(self, sample_script_output):
        """Prompt includes audio generation cues."""
        segment_info = {"start_time": 0, "end_time": 8}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="surreal_realism",
            topic="Football",
            segment_info=segment_info,
        )
        
        assert "[AUDIO]" in prompt
    
    def test_prompt_includes_no_watermarks_requirement(self, sample_script_output):
        """Prompt specifies no watermarks requirement."""
        segment_info = {"start_time": 0, "end_time": 8}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="surreal_realism",
            topic="Football",
            segment_info=segment_info,
        )
        
        assert "watermark" in prompt.lower()
    
    def test_anime_vocabulary_in_prompt(self, sample_script_output):
        """Anime tool category uses anime vocabulary."""
        segment_info = {"start_time": 0, "end_time": 8}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="high_octane_anime",
            topic="Football",
            segment_info=segment_info,
        )
        
        assert any(kw in prompt for kw in ["Sakuga", "anime", "dynamic", "impact"])
    
    def test_3d_vocabulary_in_prompt(self, sample_script_output):
        """Stylized 3D tool category uses 3D vocabulary."""
        segment_info = {"start_time": 0, "end_time": 8}
        
        prompt = build_video_prompt(
            script_output=sample_script_output,
            tool_category="stylized_3d",
            topic="Football",
            segment_info=segment_info,
        )
        
        assert any(kw in prompt for kw in ["3D", "isometric", "diorama", "tilt-shift"])


class TestVideoModels:
    """Tests for video model classes."""
    
    def test_video_generation_config_defaults(self):
        """VideoGenerationConfig has sensible defaults."""
        config = VideoGenerationConfig()
        
        assert config.model == VideoModel.VEO_3_1
        assert config.aspect_ratio == VideoAspectRatio.PORTRAIT_9_16
        assert config.resolution == VideoResolution.RES_720P
        assert config.enable_audio is True
        assert config.max_retries == 3
    
    def test_video_generation_config_resolution_for_extension(self):
        """Config enforces 720p for videos needing extension."""
        config = VideoGenerationConfig(
            resolution=VideoResolution.RES_1080P,
            target_duration_seconds=18,
        )
        
        assert config.resolution == VideoResolution.RES_720P
    
    def test_video_segment_creation(self):
        """VideoSegment can be created with required fields."""
        segment = VideoSegment(
            segment_number=0,
            segment_type=VideoSegmentType.INITIAL,
            duration_seconds=8.0,
            start_time=0.0,
            end_time=8.0,
        )
        
        assert segment.segment_number == 0
        assert segment.segment_type == VideoSegmentType.INITIAL
        assert segment.duration_seconds == 8.0
    
    def test_generated_video_creation(self):
        """GeneratedVideo can be created with required fields."""
        video = GeneratedVideo(
            url="https://storage.example.com/video.mp4",
            duration_seconds=18.0,
        )
        
        assert video.url == "https://storage.example.com/video.mp4"
        assert video.duration_seconds == 18.0
        assert video.audio_included is True
        assert video.mime_type == "video/mp4"
    
    def test_reference_image_selection_max_3(self):
        """ReferenceImageSelection limits to 3 images."""
        selection = ReferenceImageSelection(
            selected_urls=["a", "b", "c", "d", "e"]
        )
        
        assert len(selection.selected_urls) == 3
    
    def test_reference_image_selection_method(self):
        """ReferenceImageSelection.select_images() works correctly."""
        selection = ReferenceImageSelection(
            user_reference_url="user.png",
            generated_image_urls=["gen1.png", "gen2.png"],
            research_image_urls=["res1.png"],
        )
        
        result = selection.select_images()
        
        assert len(result) == 3
        assert result[0] == "user.png"
    
    def test_hitl_video_feedback_combined(self):
        """HITLVideoFeedback combines all feedback fields."""
        feedback = HITLVideoFeedback(
            action=HITLVideoAction.REGENERATE,
            feedback="General issue",
            pacing_feedback="Too fast",
            audio_feedback="Dialogue unclear",
        )
        
        combined = feedback.get_combined_feedback()
        
        assert "General" in combined
        assert "Pacing" in combined
        assert "Audio" in combined


class TestVideoGeneratorAgent:
    """Tests for VideoGeneratorAgent class."""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock workflow state."""
        return {
            "workflow_id": "test-workflow-123",
            "topic": "Messi vs Ronaldo GOAT debate",
            "duration_seconds": 18,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "enable_audio": True,
            "script_output": {
                "hook": {
                    "text": "The GOAT debate ends HERE!",
                    "visual_direction": "Epic montage opening",
                },
                "scenes": [
                    {
                        "scene_number": 1,
                        "description": "Split screen of both legends",
                        "dialogue": "Two legends, one question",
                        "camera_direction": "parallel tracking",
                        "mood": "dramatic",
                        "start_time": 2,
                        "end_time": 8,
                    },
                    {
                        "scene_number": 2,
                        "description": "Statistics comparison",
                        "dialogue": "The numbers speak!",
                        "camera_direction": "zoom in",
                        "mood": "intense",
                        "start_time": 8,
                        "end_time": 14,
                    },
                ],
                "call_to_action": {
                    "text": "Who's YOUR GOAT?",
                    "visual_direction": "Comment prompt",
                },
                "duration_seconds": 18,
            },
            "selected_tool": {
                "category": "surreal_realism",
                "tool_name": "GOAT Debates",
            },
            "generated_images": [
                "https://storage.example.com/gen1.png",
                "https://storage.example.com/gen2.png",
                "https://storage.example.com/gen3.png",
            ],
            "user_reference_image_url": None,
            "research_images": [],
            "phase_timestamps": {},
        }
    
    def test_agent_uses_720p_for_extended_videos(self, mock_state):
        """Agent uses 720p for videos >8s (extension requirement)."""
        assert mock_state["duration_seconds"] > 8
        
        config = VideoGenerationConfig(
            target_duration_seconds=mock_state["duration_seconds"],
            resolution=VideoResolution.RES_1080P,
        )
        
        assert config.resolution == VideoResolution.RES_720P
    
    def test_agent_selects_max_3_reference_images(self, mock_state):
        """Agent selects at most 3 reference images for Veo."""
        selected = select_reference_images(
            user_reference_url=mock_state["user_reference_image_url"],
            generated_images=mock_state["generated_images"],
            research_images=mock_state["research_images"],
        )
        
        assert len(selected) <= 3
    
    def test_agent_plans_correct_segments_for_18s(self, mock_state):
        """Agent plans correct number of segments for 18s video."""
        segments = plan_video_segments(mock_state["duration_seconds"])
        
        assert len(segments) == 3
        assert segments[0]["type"] == "initial"
        assert segments[1]["type"] == "extension"
        assert segments[2]["type"] == "extension"


class TestToolVideoVocabulary:
    """Tests for tool-specific video vocabulary."""
    
    def test_surreal_realism_has_required_keys(self):
        """Surreal realism vocabulary has all required keys."""
        vocab = TOOL_VIDEO_VOCABULARY["surreal_realism"]
        
        assert "style_keywords" in vocab
        assert "camera_movements" in vocab
        assert "audio_cues" in vocab
        assert "lighting" in vocab
    
    def test_anime_has_required_keys(self):
        """High octane anime vocabulary has all required keys."""
        vocab = TOOL_VIDEO_VOCABULARY["high_octane_anime"]
        
        assert "style_keywords" in vocab
        assert "camera_movements" in vocab
        assert "audio_cues" in vocab
        assert "lighting" in vocab
    
    def test_3d_has_required_keys(self):
        """Stylized 3D vocabulary has all required keys."""
        vocab = TOOL_VIDEO_VOCABULARY["stylized_3d"]
        
        assert "style_keywords" in vocab
        assert "camera_movements" in vocab
        assert "audio_cues" in vocab
        assert "lighting" in vocab
    
    def test_all_vocabularies_have_multiple_items(self):
        """All vocabularies have multiple items in each category."""
        for category, vocab in TOOL_VIDEO_VOCABULARY.items():
            assert len(vocab["style_keywords"]) >= 3, f"{category} missing style keywords"
            assert len(vocab["camera_movements"]) >= 3, f"{category} missing camera movements"
            assert len(vocab["audio_cues"]) >= 3, f"{category} missing audio cues"


class TestAspectRatioAndResolutionMapping:
    """Tests for aspect ratio and resolution handling."""
    
    def test_portrait_9_16_mapping(self):
        """9:16 video maps correctly."""
        from app.agents.video_generator import ASPECT_RATIO_MAP
        
        assert ASPECT_RATIO_MAP["9:16"] == VideoAspectRatio.PORTRAIT_9_16
    
    def test_landscape_16_9_mapping(self):
        """16:9 video maps correctly."""
        from app.agents.video_generator import ASPECT_RATIO_MAP
        
        assert ASPECT_RATIO_MAP["16:9"] == VideoAspectRatio.LANDSCAPE_16_9
    
    def test_720p_resolution_mapping(self):
        """720p resolution maps correctly."""
        from app.agents.video_generator import RESOLUTION_MAP
        
        assert RESOLUTION_MAP["720p"] == VideoResolution.RES_720P
    
    def test_1080p_resolution_mapping(self):
        """1080p resolution maps correctly."""
        from app.agents.video_generator import RESOLUTION_MAP
        
        assert RESOLUTION_MAP["1080p"] == VideoResolution.RES_1080P


class TestSeamlessExtension:
    """Tests for seamless video extension logic."""
    
    def test_extension_prompts_reference_previous_end(self):
        """Extension prompts reference how previous segment ended."""
        script_output = {
            "scenes": [
                {"description": "Scene 1", "scene_number": 1},
                {"description": "Scene 2", "scene_number": 2},
            ]
        }
        segment_info = {"start_time": 8, "end_time": 15}
        
        prompt = build_extension_prompt(
            script_output=script_output,
            tool_category="surreal_realism",
            segment_info=segment_info,
            previous_end_description="Player celebrated goal",
        )
        
        assert "celebrated goal" in prompt
        assert "CONTINUATION" in prompt
    
    def test_extension_prompt_maintains_style_consistency(self):
        """Extension prompts include style consistency requirements."""
        script_output = {"scenes": []}
        segment_info = {"start_time": 8, "end_time": 15}
        
        prompt = build_extension_prompt(
            script_output=script_output,
            tool_category="surreal_realism",
            segment_info=segment_info,
            previous_end_description="Previous action",
        )
        
        assert "seamless" in prompt.lower() or "consistency" in prompt.lower()
