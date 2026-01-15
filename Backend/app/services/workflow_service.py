"""RABA Workflow Service.

Service for workflow completion, status management, and final output building.

Reference: PHASE3_3_OUTPUT_PROCESSOR_PLAN.md Section 4 (Step 2)
"""

from datetime import datetime
from typing import Any, Optional

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
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger
from app.utils.metadata import (
    build_workflow_summary,
    calculate_phase_durations,
    calculate_total_generation_time,
    consolidate_media_urls,
    extract_video_metadata,
    generate_shareable_link,
    parse_iso_timestamp,
)

logger = get_logger(__name__)


class WorkflowServiceError(Exception):
    """Base exception for workflow service errors."""
    pass


class WorkflowNotFoundError(WorkflowServiceError):
    """Raised when workflow is not found."""
    pass


class WorkflowCompletionError(WorkflowServiceError):
    """Raised when workflow completion fails."""
    pass


class WorkflowService:
    """Service for workflow completion and status management.
    
    Handles:
    - Building final workflow output
    - Calculating generation timing
    - Updating workflow status in database
    - Consolidating media references
    
    Reference: PHASE3_3_OUTPUT_PROCESSOR_PLAN.md
    """
    
    def __init__(self):
        """Initialize the workflow service."""
        self.supabase = get_supabase_client()
        logger.info("WorkflowService initialized")
    
    def build_completion_output(
        self,
        state: dict[str, Any],
    ) -> WorkflowCompletionOutput:
        """Build complete workflow output from state.
        
        Args:
            state: Final workflow state
            
        Returns:
            WorkflowCompletionOutput with all data
            
        Reference: SRS.md Section 7.2 - Output Data Schema
        """
        workflow_id = state.get("workflow_id", "unknown")
        logger.info(f"Building completion output for workflow: {workflow_id}")
        
        timing = self._build_timing(state)
        
        media = consolidate_media_urls(state)
        video_meta = extract_video_metadata(state)
        summary = build_workflow_summary(state)
        
        video_summary = VideoOutputSummary(
            url=media["video_url"],
            duration_seconds=video_meta["duration_seconds"],
            resolution=video_meta["resolution"],
            aspect_ratio=video_meta["aspect_ratio"],
            segment_count=video_meta["segment_count"],
            file_size_bytes=video_meta["file_size_bytes"],
            audio_included=video_meta["audio_included"],
        )
        
        image_summary = ImageOutputSummary(
            generated_count=media["generated_count"],
            total_count=media["total_count"],
            urls=media["all_image_urls"],
            user_reference_included=media["user_reference_included"],
            research_images_count=media["research_count"],
        )
        
        metadata_summary = WorkflowMetadataSummary(
            tool_used=summary["tool_used"],
            tool_id=summary["tool_id"],
            category=summary["category"],
            topic=summary["topic"],
            hitl_mode=summary["hitl_mode"],
            audio_enabled=summary["audio_enabled"],
            subtitles_enabled=summary["subtitles_enabled"],
            viral_score=summary["viral_score"],
        )
        
        shareable_link = generate_shareable_link(workflow_id, media["video_url"])
        
        urls = OutputURLs(
            video_url=media["video_url"],
            all_image_urls=media["all_image_urls"],
            shareable_link=shareable_link,
        )
        
        output = WorkflowCompletionOutput(
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            video=video_summary,
            images=image_summary,
            metadata=metadata_summary,
            timing=timing,
            urls=urls,
        )
        
        logger.info(f"Completion output built: {timing.total_seconds:.1f}s total")
        return output
    
    def build_error_output(
        self,
        state: dict[str, Any],
    ) -> WorkflowErrorOutput:
        """Build error output for failed workflow.
        
        Args:
            state: Workflow state with error
            
        Returns:
            WorkflowErrorOutput with error details
        """
        workflow_id = state.get("workflow_id", "unknown")
        error = state.get("error", "Unknown error")
        error_details = state.get("error_details", {})
        
        partial_output = {}
        if state.get("script_output"):
            partial_output["script_output"] = state.get("script_output")
        if state.get("generated_images"):
            partial_output["generated_images"] = state.get("generated_images")
        if state.get("research_data"):
            partial_output["research_summary"] = {
                "has_research": True,
                "is_fictional": state.get("research_data", {}).get("is_fictional", False),
            }
        
        return WorkflowErrorOutput(
            workflow_id=workflow_id,
            status=WorkflowStatus.FAILED,
            error=error,
            error_details=error_details,
            partial_output=partial_output if partial_output else None,
        )
    
    def _build_timing(self, state: dict[str, Any]) -> GenerationTiming:
        """Build timing breakdown from state.
        
        Args:
            state: Workflow state
            
        Returns:
            GenerationTiming with breakdown
        """
        started_at_str = state.get("started_at", "")
        phase_timestamps = state.get("phase_timestamps", {})
        
        started_at = parse_iso_timestamp(started_at_str)
        if not started_at:
            started_at = datetime.utcnow()
        
        completed_at = datetime.utcnow()
        
        total_seconds = calculate_total_generation_time(
            started_at_str,
            completed_at.isoformat(),
        )
        
        phase_breakdown = calculate_phase_durations(phase_timestamps)
        
        return GenerationTiming(
            total_seconds=total_seconds,
            phase_breakdown=phase_breakdown,
            started_at=started_at,
            completed_at=completed_at,
        )
    
    async def update_workflow_completed(
        self,
        workflow_id: str,
        output: WorkflowCompletionOutput,
    ) -> None:
        """Update workflow status to completed in database.
        
        Args:
            workflow_id: Workflow identifier
            output: Completion output to store
            
        Reference: SRS.md FR-802 - Persist all agent outputs
        """
        try:
            from app.utils.helpers import utc_now_iso
            
            update_data = {
                "status": WorkflowStatus.COMPLETED.value,
                "completed_at": utc_now_iso(),
                "current_hitl_gate": None,
                "updated_at": utc_now_iso(),
            }
            
            self.supabase.table("workflows").update(update_data).eq(
                "id", workflow_id
            ).execute()
            
            logger.info(f"Workflow {workflow_id} marked as completed in database")
            
        except Exception as e:
            logger.error(f"Failed to update workflow status: {e}")
    
    async def update_workflow_failed(
        self,
        workflow_id: str,
        error: str,
        error_details: Optional[dict] = None,
    ) -> None:
        """Update workflow status to failed in database.
        
        Args:
            workflow_id: Workflow identifier
            error: Error message
            error_details: Optional detailed error info
        """
        try:
            from app.utils.helpers import utc_now_iso
            
            update_data = {
                "status": WorkflowStatus.FAILED.value,
                "error": error,
                "error_details": error_details or {},
                "completed_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            }
            
            self.supabase.table("workflows").update(update_data).eq(
                "id", workflow_id
            ).execute()
            
            logger.info(f"Workflow {workflow_id} marked as failed in database")
            
        except Exception as e:
            logger.error(f"Failed to update workflow failed status: {e}")
    
    def validate_completion_ready(self, state: dict[str, Any]) -> tuple[bool, str]:
        """Validate that workflow is ready for completion.
        
        Args:
            state: Workflow state
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if state.get("error"):
            return False, f"Workflow has error: {state.get('error')}"
        
        video_url = state.get("final_video_url", "")
        if not video_url:
            video_output = state.get("video_output", {})
            if video_output:
                video_url = video_output.get("video", {}).get("url", "")
        
        if not video_url:
            return False, "No video URL in workflow state"
        
        return True, ""


_workflow_service: Optional[WorkflowService] = None


def get_workflow_service() -> WorkflowService:
    """Get or create the WorkflowService singleton.
    
    Returns:
        WorkflowService instance
    """
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service
