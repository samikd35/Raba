"""Tests for Output Processor.

Tests metadata calculation, workflow completion, and final output building.

Reference: PHASE3_3_OUTPUT_PROCESSOR_PLAN.md
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.output import (
    GenerationTiming,
    ImageOutputSummary,
    OutputURLs,
    VideoOutputSummary,
    WorkflowCompletionOutput,
    WorkflowErrorOutput,
    WorkflowMetadataSummary,
)
from app.models.workflow import WorkflowStatus
from app.utils.metadata import (
    calculate_phase_durations,
    calculate_total_generation_time,
    build_workflow_summary,
    consolidate_media_urls,
    extract_video_metadata,
    parse_iso_timestamp,
)


class TestParseIsoTimestamp:
    """Tests for ISO timestamp parsing."""
    
    def test_parse_valid_timestamp(self):
        """Parse valid ISO timestamp."""
        ts = "2026-01-15T06:30:00"
        result = parse_iso_timestamp(ts)
        
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_timestamp_with_z(self):
        """Parse timestamp with Z suffix."""
        ts = "2026-01-15T06:30:00Z"
        result = parse_iso_timestamp(ts)
        
        assert result is not None
        assert result.hour == 6
    
    def test_parse_invalid_timestamp(self):
        """Invalid timestamp returns None."""
        result = parse_iso_timestamp("not-a-timestamp")
        assert result is None
    
    def test_parse_empty_timestamp(self):
        """Empty timestamp returns None."""
        result = parse_iso_timestamp("")
        assert result is None


class TestCalculatePhaseDurations:
    """Tests for phase duration calculation."""
    
    def test_calculate_durations_from_completed_timestamps(self):
        """Calculate durations from completed timestamps."""
        base_time = datetime(2026, 1, 15, 6, 30, 0)
        
        timestamps = {
            "intent_tool_completed": (base_time + timedelta(seconds=2)).isoformat(),
            "deep_research_completed": (base_time + timedelta(seconds=17)).isoformat(),
            "script_writer_completed": (base_time + timedelta(seconds=25)).isoformat(),
            "image_generator_completed": (base_time + timedelta(seconds=70)).isoformat(),
            "video_generator_completed": (base_time + timedelta(seconds=250)).isoformat(),
        }
        
        durations = calculate_phase_durations(timestamps)
        
        assert "deep_research" in durations
        assert durations["deep_research"] == pytest.approx(15.0, abs=0.1)
        
        assert "script_writer" in durations
        assert durations["script_writer"] == pytest.approx(8.0, abs=0.1)
    
    def test_empty_timestamps(self):
        """Empty timestamps returns empty dict."""
        durations = calculate_phase_durations({})
        assert durations == {}


class TestCalculateTotalGenerationTime:
    """Tests for total generation time calculation."""
    
    def test_calculate_time_with_both_timestamps(self):
        """Calculate time from start to end."""
        start = "2026-01-15T06:30:00"
        end = "2026-01-15T06:34:12"
        
        total = calculate_total_generation_time(start, end)
        
        assert total == pytest.approx(252.0, abs=1.0)
    
    def test_calculate_time_without_end(self):
        """Calculate time from start to now."""
        start = datetime.utcnow().isoformat()
        
        total = calculate_total_generation_time(start)
        
        assert total >= 0
        assert total < 5
    
    def test_invalid_start_returns_zero(self):
        """Invalid start timestamp returns 0."""
        total = calculate_total_generation_time("invalid")
        assert total == 0.0


class TestBuildWorkflowSummary:
    """Tests for workflow summary building."""
    
    def test_build_summary_with_full_state(self):
        """Build summary from full state."""
        state = {
            "topic": "How black holes work",
            "selected_tool": {
                "tool_name": "Impossible Simulations",
                "tool_id": "surreal_impossible_sims",
                "category": "surreal_realism",
            },
            "script_output": {
                "viral_score": 0.85,
            },
            "video_metadata": {
                "segments": 3,
            },
            "hitl_mode": "auto",
            "enable_audio": True,
            "enable_subtitles": False,
        }
        
        summary = build_workflow_summary(state)
        
        assert summary["tool_used"] == "Impossible Simulations"
        assert summary["category"] == "surreal_realism"
        assert summary["viral_score"] == 0.85
        assert summary["segment_count"] == 3
    
    def test_build_summary_truncates_long_topic(self):
        """Long topic is truncated."""
        state = {
            "topic": "A" * 200,
            "selected_tool": {},
        }
        
        summary = build_workflow_summary(state)
        
        assert len(summary["topic"]) <= 103
        assert summary["topic"].endswith("...")
    
    def test_build_summary_with_minimal_state(self):
        """Build summary from minimal state."""
        state = {"topic": "Test"}
        
        summary = build_workflow_summary(state)
        
        assert summary["tool_used"] == "Unknown"
        assert summary["topic"] == "Test"


class TestConsolidateMediaUrls:
    """Tests for media URL consolidation."""
    
    def test_consolidate_all_sources(self):
        """Consolidate URLs from all sources."""
        state = {
            "final_video_url": "https://storage/video.mp4",
            "user_reference_image_url": "https://storage/user_ref.png",
            "research_images": ["https://storage/research1.png"],
            "generated_images": ["https://storage/gen1.png", "https://storage/gen2.png"],
        }
        
        media = consolidate_media_urls(state)
        
        assert media["video_url"] == "https://storage/video.mp4"
        assert len(media["all_image_urls"]) == 4
        assert media["user_reference_included"] is True
        assert media["generated_count"] == 2
        assert media["research_count"] == 1
    
    def test_consolidate_video_from_output(self):
        """Get video URL from video_output if final_video_url missing."""
        state = {
            "video_output": {
                "video": {
                    "url": "https://storage/video.mp4",
                }
            },
            "generated_images": [],
        }
        
        media = consolidate_media_urls(state)
        
        assert media["video_url"] == "https://storage/video.mp4"
    
    def test_consolidate_no_user_reference(self):
        """Consolidate without user reference."""
        state = {
            "final_video_url": "https://storage/video.mp4",
            "generated_images": ["https://storage/gen1.png"],
        }
        
        media = consolidate_media_urls(state)
        
        assert media["user_reference_included"] is False
        assert media["total_count"] == 1


class TestExtractVideoMetadata:
    """Tests for video metadata extraction."""
    
    def test_extract_from_video_output(self):
        """Extract metadata from video_output."""
        state = {
            "duration_seconds": 18,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "video_output": {
                "video": {
                    "duration_seconds": 18.5,
                    "total_segments": 3,
                    "file_size_bytes": 5000000,
                    "audio_included": True,
                }
            },
        }
        
        meta = extract_video_metadata(state)
        
        assert meta["duration_seconds"] == 18.5
        assert meta["segment_count"] == 3
        assert meta["file_size_bytes"] == 5000000
    
    def test_extract_fallback_to_state(self):
        """Fall back to state values if video_output missing."""
        state = {
            "duration_seconds": 18,
            "resolution": "1080p",
            "aspect_ratio": "16:9",
        }
        
        meta = extract_video_metadata(state)
        
        assert meta["duration_seconds"] == 18
        assert meta["resolution"] == "1080p"
        assert meta["aspect_ratio"] == "16:9"


class TestOutputModels:
    """Tests for output model classes."""
    
    def test_video_output_summary(self):
        """VideoOutputSummary creation."""
        summary = VideoOutputSummary(
            url="https://storage/video.mp4",
            duration_seconds=18.0,
            resolution="720p",
            aspect_ratio="9:16",
            segment_count=3,
        )
        
        assert summary.url == "https://storage/video.mp4"
        assert summary.duration_seconds == 18.0
        assert summary.segment_count == 3
    
    def test_image_output_summary(self):
        """ImageOutputSummary creation."""
        summary = ImageOutputSummary(
            generated_count=3,
            total_count=4,
            urls=["img1.png", "img2.png", "img3.png", "img4.png"],
        )
        
        assert summary.generated_count == 3
        assert len(summary.urls) == 4
    
    def test_generation_timing_formatted(self):
        """GenerationTiming provides formatted total."""
        timing = GenerationTiming(
            total_seconds=252.5,
            phase_breakdown={"video_generator": 180.0},
            started_at=datetime(2026, 1, 15, 6, 30, 0),
            completed_at=datetime(2026, 1, 15, 6, 34, 12),
        )
        
        assert timing.formatted_total == "4m 12s"
    
    def test_generation_timing_short_duration(self):
        """GenerationTiming formats short durations."""
        timing = GenerationTiming(
            total_seconds=45.0,
            phase_breakdown={},
            started_at=datetime(2026, 1, 15, 6, 30, 0),
            completed_at=datetime(2026, 1, 15, 6, 30, 45),
        )
        
        assert timing.formatted_total == "45s"
    
    def test_workflow_completion_output(self):
        """WorkflowCompletionOutput creation and API response."""
        video = VideoOutputSummary(
            url="https://storage/video.mp4",
            duration_seconds=18.0,
        )
        timing = GenerationTiming(
            total_seconds=252.0,
            phase_breakdown={},
            started_at=datetime(2026, 1, 15, 6, 30, 0),
            completed_at=datetime(2026, 1, 15, 6, 34, 12),
        )
        urls = OutputURLs(
            video_url="https://storage/video.mp4",
            all_image_urls=["img1.png"],
        )
        
        output = WorkflowCompletionOutput(
            workflow_id="test-123",
            status=WorkflowStatus.COMPLETED,
            video=video,
            timing=timing,
            urls=urls,
        )
        
        assert output.workflow_id == "test-123"
        assert output.video_url == "https://storage/video.mp4"
        assert output.generation_time_seconds == 252.0
        
        api_response = output.to_api_response()
        assert api_response["workflow_id"] == "test-123"
        assert api_response["status"] == "completed"
        assert api_response["video_url"] == "https://storage/video.mp4"
    
    def test_workflow_error_output(self):
        """WorkflowErrorOutput creation."""
        error_output = WorkflowErrorOutput(
            workflow_id="test-123",
            error="Video generation failed",
            error_details={"phase": "video_generator"},
        )
        
        assert error_output.status == WorkflowStatus.FAILED
        assert error_output.error == "Video generation failed"
        
        api_response = error_output.to_api_response()
        assert api_response["status"] == "failed"


class TestWorkflowService:
    """Tests for WorkflowService."""
    
    @pytest.fixture
    def mock_state(self):
        """Create mock workflow state."""
        return {
            "workflow_id": "test-workflow-123",
            "topic": "How black holes work",
            "duration_seconds": 18,
            "aspect_ratio": "9:16",
            "resolution": "720p",
            "hitl_mode": "auto",
            "enable_audio": True,
            "enable_subtitles": False,
            "started_at": "2026-01-15T06:30:00Z",
            "phase_timestamps": {
                "intent_tool_completed": "2026-01-15T06:30:02Z",
                "deep_research_completed": "2026-01-15T06:30:17Z",
                "script_writer_completed": "2026-01-15T06:30:25Z",
                "image_generator_completed": "2026-01-15T06:31:10Z",
                "video_generator_completed": "2026-01-15T06:34:10Z",
            },
            "final_video_url": "https://storage/video.mp4",
            "video_output": {
                "video": {
                    "url": "https://storage/video.mp4",
                    "duration_seconds": 18.0,
                    "total_segments": 3,
                    "audio_included": True,
                }
            },
            "generated_images": [
                "https://storage/gen1.png",
                "https://storage/gen2.png",
                "https://storage/gen3.png",
            ],
            "selected_tool": {
                "tool_name": "Impossible Simulations",
                "tool_id": "surreal_impossible_sims",
                "category": "surreal_realism",
            },
            "script_output": {
                "viral_score": 0.85,
            },
        }
    
    def test_validate_completion_ready_success(self, mock_state):
        """Validate ready state passes."""
        from app.services.workflow_service import WorkflowService
        
        with patch.object(WorkflowService, '__init__', lambda x: None):
            service = WorkflowService()
            service.supabase = MagicMock()
            
            is_valid, error_msg = service.validate_completion_ready(mock_state)
            
            assert is_valid is True
            assert error_msg == ""
    
    def test_validate_completion_ready_no_video(self, mock_state):
        """Validate fails without video URL."""
        from app.services.workflow_service import WorkflowService
        
        mock_state["final_video_url"] = ""
        mock_state["video_output"] = {}
        
        with patch.object(WorkflowService, '__init__', lambda x: None):
            service = WorkflowService()
            service.supabase = MagicMock()
            
            is_valid, error_msg = service.validate_completion_ready(mock_state)
            
            assert is_valid is False
            assert "No video URL" in error_msg
    
    def test_validate_completion_ready_with_error(self, mock_state):
        """Validate fails with error in state."""
        from app.services.workflow_service import WorkflowService
        
        mock_state["error"] = "Previous phase failed"
        
        with patch.object(WorkflowService, '__init__', lambda x: None):
            service = WorkflowService()
            service.supabase = MagicMock()
            
            is_valid, error_msg = service.validate_completion_ready(mock_state)
            
            assert is_valid is False
            assert "error" in error_msg.lower()
    
    def test_build_completion_output(self, mock_state):
        """Build completion output from state."""
        from app.services.workflow_service import WorkflowService
        
        with patch.object(WorkflowService, '__init__', lambda x: None):
            service = WorkflowService()
            service.supabase = MagicMock()
            
            output = service.build_completion_output(mock_state)
            
            assert output.workflow_id == "test-workflow-123"
            assert output.status == WorkflowStatus.COMPLETED
            assert output.video.url == "https://storage/video.mp4"
            assert output.images.generated_count == 3
            assert output.metadata.tool_used == "Impossible Simulations"
    
    def test_build_error_output(self, mock_state):
        """Build error output from state."""
        from app.services.workflow_service import WorkflowService
        
        mock_state["error"] = "Test error"
        mock_state["error_details"] = {"phase": "video_generator"}
        
        with patch.object(WorkflowService, '__init__', lambda x: None):
            service = WorkflowService()
            service.supabase = MagicMock()
            
            output = service.build_error_output(mock_state)
            
            assert output.status == WorkflowStatus.FAILED
            assert output.error == "Test error"
            assert output.partial_output is not None
            assert "script_output" in output.partial_output
