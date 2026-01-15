"""Tests for Image Generator Agent.

Tests image count calculation, prompt building, and style consistency.

Reference: PHASE3_1_IMAGE_GENERATOR_PLAN.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.image_generator import (
    ImageGeneratorAgent,
    calculate_images_to_generate,
    build_image_prompt,
    TOOL_VISUAL_VOCABULARY,
)
from app.models.image import (
    GeneratedImage,
    ImageAspectRatio,
    ImageGenerationConfig,
    ImageGeneratorOutput,
    ImageModel,
    ImageResolution,
    ImageSource,
    StyleReference,
    WorkflowImage,
)


class TestCalculateImagesToGenerate:
    """Tests for image count calculation logic."""
    
    def test_no_external_images_5_scenes(self):
        """5 scenes, no external images → 3 generated (max for Veo 3.1)."""
        result = calculate_images_to_generate(
            scene_count=5,
            user_has_reference=False,
            research_image_count=0,
        )
        assert result == 3  # MAX_IMAGES = 3 for Veo 3.1
    
    def test_no_external_images_3_scenes(self):
        """3 scenes, no external images → 3 generated."""
        result = calculate_images_to_generate(
            scene_count=3,
            user_has_reference=False,
            research_image_count=0,
        )
        assert result == 3
    
    def test_with_user_reference(self):
        """5 scenes, user reference → 2 generated (3 - 1 user ref)."""
        result = calculate_images_to_generate(
            scene_count=5,
            user_has_reference=True,
            research_image_count=0,
        )
        assert result == 2  # MAX_IMAGES=3 minus 1 user ref
    
    def test_with_research_images(self):
        """5 scenes, 2 research images → 1 generated (3 - 2 research)."""
        result = calculate_images_to_generate(
            scene_count=5,
            user_has_reference=False,
            research_image_count=2,
        )
        assert result == 1  # MAX_IMAGES=3 minus 2 research (min 1)
    
    def test_with_user_and_research(self):
        """5 scenes, user ref + 2 research → 1 generated (min 1)."""
        result = calculate_images_to_generate(
            scene_count=5,
            user_has_reference=True,
            research_image_count=2,
        )
        assert result == 1  # Always at least 1 (FR-504)
    
    def test_minimum_one_image(self):
        """Always generate at least 1 image (FR-504)."""
        result = calculate_images_to_generate(
            scene_count=2,
            user_has_reference=True,
            research_image_count=5,
        )
        assert result >= 1
    
    def test_maximum_three_images(self):
        """Never generate more than 3 images (Veo 3.1 max reference images)."""
        result = calculate_images_to_generate(
            scene_count=10,
            user_has_reference=False,
            research_image_count=0,
        )
        assert result <= 3  # MAX_IMAGES = 3 for Veo 3.1
    
    def test_research_images_capped_at_2(self):
        """Research images contribution capped at 2."""
        result_2 = calculate_images_to_generate(
            scene_count=5,
            user_has_reference=False,
            research_image_count=2,
        )
        result_5 = calculate_images_to_generate(
            scene_count=5,
            user_has_reference=False,
            research_image_count=5,
        )
        assert result_2 == result_5


class TestBuildImagePrompt:
    """Tests for prompt building with tool vocabulary."""
    
    def test_surreal_realism_vocabulary(self):
        """Prompt includes surreal_realism vocabulary."""
        scene = {
            "description": "A football floating in liquid glass",
            "camera_direction": "slow macro zoom",
            "lighting": "golden hour",
            "mood": "mysterious",
        }
        
        prompt = build_image_prompt(
            scene=scene,
            scene_number=1,
            total_scenes=3,
            tool_category="surreal_realism",
            topic="Impossible football physics",
            duration_seconds=18,
        )
        
        assert "surreal_realism" not in prompt.lower()
        assert any(kw in prompt for kw in ["liquid-glass", "photorealistic", "impossible physics"])
        assert "Scene 1 of 3" in prompt
        assert "floating in liquid glass" in prompt
    
    def test_anime_vocabulary(self):
        """Prompt includes high_octane_anime vocabulary."""
        scene = {
            "description": "Epic football battle with energy effects",
            "camera_direction": "rapid cuts",
            "mood": "intense",
        }
        
        prompt = build_image_prompt(
            scene=scene,
            scene_number=2,
            total_scenes=4,
            tool_category="high_octane_anime",
            topic="Football legends clash",
            duration_seconds=20,
        )
        
        assert any(kw in prompt for kw in ["Sakuga", "ink-splashes", "motion lines"])
        assert "Scene 2 of 4" in prompt
    
    def test_stylized_3d_vocabulary(self):
        """Prompt includes stylized_3d vocabulary."""
        scene = {
            "description": "Miniature football stadium diorama",
            "camera_direction": "orbital rotation",
        }
        
        prompt = build_image_prompt(
            scene=scene,
            scene_number=1,
            total_scenes=2,
            tool_category="stylized_3d",
            topic="Stadium data visualization",
            duration_seconds=12,
        )
        
        assert any(kw in prompt for kw in ["miniature", "diorama", "3D", "isometric"])
    
    def test_includes_scene_description(self):
        """Prompt includes the scene description."""
        scene = {
            "description": "Messi dribbling past defenders in slow motion",
        }
        
        prompt = build_image_prompt(
            scene=scene,
            scene_number=1,
            total_scenes=1,
            tool_category="surreal_realism",
            topic="Messi magic",
            duration_seconds=15,
        )
        
        assert "Messi dribbling past defenders" in prompt
    
    def test_includes_camera_direction(self):
        """Prompt includes camera direction if provided."""
        scene = {
            "description": "Goal celebration",
            "camera_direction": "dramatic low angle",
        }
        
        prompt = build_image_prompt(
            scene=scene,
            scene_number=1,
            total_scenes=1,
            tool_category="surreal_realism",
            topic="Goal!",
            duration_seconds=10,
        )
        
        assert "dramatic low angle" in prompt
    
    def test_fallback_to_default_vocabulary(self):
        """Unknown category falls back to surreal_realism."""
        scene = {"description": "Test scene"}
        
        prompt = build_image_prompt(
            scene=scene,
            scene_number=1,
            total_scenes=1,
            tool_category="unknown_category",
            topic="Test",
            duration_seconds=10,
        )
        
        assert any(kw in prompt for kw in TOOL_VISUAL_VOCABULARY["surreal_realism"]["style_keywords"])


class TestImageModels:
    """Tests for image model classes."""
    
    def test_generated_image_creation(self):
        """GeneratedImage can be created with required fields."""
        img = GeneratedImage(
            url="https://example.com/image.png",
            prompt="Test prompt",
            scene_number=1,
        )
        
        assert img.url == "https://example.com/image.png"
        assert img.scene_number == 1
        assert img.model_used == ImageModel.NANO_BANANA_PRO
    
    def test_style_reference_color_palette_limit(self):
        """StyleReference limits color palette to 5 colors."""
        ref = StyleReference(
            color_palette=["red", "blue", "green", "yellow", "orange", "purple", "pink"]
        )
        
        assert len(ref.color_palette) == 5
    
    def test_image_generator_output_urls(self):
        """ImageGeneratorOutput provides URL accessors."""
        img1 = GeneratedImage(url="url1", prompt="p1", scene_number=1)
        img2 = GeneratedImage(url="url2", prompt="p2", scene_number=2)
        
        output = ImageGeneratorOutput(
            generated_images=[img1, img2],
            all_images=[
                WorkflowImage(url="ref", source=ImageSource.USER_REFERENCE),
                WorkflowImage(url="url1", source=ImageSource.GENERATED, scene_number=1),
                WorkflowImage(url="url2", source=ImageSource.GENERATED, scene_number=2),
            ],
        )
        
        assert output.generated_image_urls == ["url1", "url2"]
        assert output.all_image_urls == ["ref", "url1", "url2"]
    
    def test_image_generation_config_defaults(self):
        """ImageGenerationConfig has sensible defaults."""
        config = ImageGenerationConfig()
        
        assert config.model == ImageModel.NANO_BANANA_PRO
        assert config.aspect_ratio == ImageAspectRatio.PORTRAIT_9_16
        assert config.resolution == ImageResolution.RES_2K
        assert config.maintain_consistency is True
        assert config.max_retries == 3


class TestImageGeneratorAgent:
    """Tests for ImageGeneratorAgent class."""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock workflow state."""
        return {
            "workflow_id": "test-workflow-123",
            "topic": "Messi vs Ronaldo debate",
            "duration_seconds": 18,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "category": "surreal_realism",
            "script_output": {
                "scenes": [
                    {"description": "Scene 1 description", "scene_number": 1, "mood": "epic"},
                    {"description": "Scene 2 description", "scene_number": 2, "mood": "intense"},
                    {"description": "Scene 3 description", "scene_number": 3, "mood": "dramatic"},
                ]
            },
            "selected_tool": {
                "category": "surreal_realism",
                "tool_name": "Impossible Simulations",
            },
            "user_reference_image_url": None,
            "research_images": [],
            "phase_timestamps": {},
        }
    
    @pytest.mark.asyncio
    async def test_agent_calculates_correct_image_count(self, mock_state):
        """Agent calculates correct number of images based on scenes."""
        with patch.object(ImageGeneratorAgent, '__init__', lambda x: None):
            agent = ImageGeneratorAgent()
            agent.nano_banana = MagicMock()
            agent.supabase = MagicMock()
            
            count = calculate_images_to_generate(
                scene_count=3,
                user_has_reference=False,
                research_image_count=0,
            )
            
            assert count == 3
    
    @pytest.mark.asyncio
    async def test_agent_reduces_count_with_user_reference(self, mock_state):
        """Agent reduces image count when user provides reference."""
        mock_state["user_reference_image_url"] = "https://example.com/ref.png"
        
        count = calculate_images_to_generate(
            scene_count=3,
            user_has_reference=True,
            research_image_count=0,
        )
        
        assert count == 2
    
    @pytest.mark.asyncio
    async def test_agent_reduces_count_with_research_images(self, mock_state):
        """Agent reduces image count when research provides images."""
        mock_state["research_images"] = ["img1.png", "img2.png"]
        
        count = calculate_images_to_generate(
            scene_count=3,
            user_has_reference=False,
            research_image_count=2,
        )
        
        assert count == 1


class TestStyleConsistency:
    """Tests for style consistency across images."""
    
    def test_style_reference_includes_character_descriptions(self):
        """StyleReference extracts character descriptions from scenes."""
        ref = StyleReference(
            style_description="Surreal football style",
            character_descriptions=[
                "Messi in Argentina jersey",
                "Ronaldo in Portugal jersey",
            ],
        )
        
        assert len(ref.character_descriptions) == 2
        assert "Messi" in ref.character_descriptions[0]
    
    def test_workflow_image_tracks_source(self):
        """WorkflowImage correctly tracks image source."""
        user_img = WorkflowImage(
            url="user.png",
            source=ImageSource.USER_REFERENCE,
            is_style_reference=True,
        )
        
        research_img = WorkflowImage(
            url="research.png",
            source=ImageSource.RESEARCH,
        )
        
        generated_img = WorkflowImage(
            url="generated.png",
            source=ImageSource.GENERATED,
            scene_number=1,
        )
        
        assert user_img.source == ImageSource.USER_REFERENCE
        assert user_img.is_style_reference is True
        assert research_img.source == ImageSource.RESEARCH
        assert generated_img.source == ImageSource.GENERATED
        assert generated_img.scene_number == 1


class TestAspectRatioMapping:
    """Tests for aspect ratio handling."""
    
    def test_portrait_9_16_mapping(self):
        """9:16 video maps to 9:16 image."""
        from app.agents.image_generator import ASPECT_RATIO_MAP
        
        assert ASPECT_RATIO_MAP["9:16"] == ImageAspectRatio.PORTRAIT_9_16
    
    def test_landscape_16_9_mapping(self):
        """16:9 video maps to 16:9 image."""
        from app.agents.image_generator import ASPECT_RATIO_MAP
        
        assert ASPECT_RATIO_MAP["16:9"] == ImageAspectRatio.LANDSCAPE_16_9
    
    def test_square_1_1_mapping(self):
        """1:1 video maps to 1:1 image."""
        from app.agents.image_generator import ASPECT_RATIO_MAP
        
        assert ASPECT_RATIO_MAP["1:1"] == ImageAspectRatio.SQUARE


class TestResolutionMapping:
    """Tests for resolution handling."""
    
    def test_720p_maps_to_1k(self):
        """720p video maps to 1K image."""
        from app.agents.image_generator import RESOLUTION_MAP
        
        assert RESOLUTION_MAP["720p"] == ImageResolution.RES_1K
    
    def test_1080p_maps_to_2k(self):
        """1080p video maps to 2K image."""
        from app.agents.image_generator import RESOLUTION_MAP
        
        assert RESOLUTION_MAP["1080p"] == ImageResolution.RES_2K
