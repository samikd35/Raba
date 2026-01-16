"""RABA Workflow Runner Service.

Compiles and executes the LangGraph video generation workflow.
Runs as a background task after workflow creation.
"""

import asyncio
from typing import Any, Optional

from app.graph.state import VideoGenerationState
from app.graph.workflow import create_workflow_graph
from app.models.workflow import WorkflowStatus
from app.services.supabase import get_workflow_repository
from app.utils.helpers import utc_now_iso
from app.utils.logging import (
    get_logger,
    log_header,
    log_subheader,
    log_key_value,
    log_success,
    log_error_msg,
    log_warning_msg,
    log_workflow_event,
    log_operation,
    Colors,
)

logger = get_logger(__name__)


class WorkflowRunner:
    """Runs video generation workflows using LangGraph.
    
    Compiles the workflow graph and executes it with proper state management,
    checkpointing, and status updates.
    """
    
    def __init__(self):
        """Initialize the workflow runner."""
        self._compiled_graph = None
        logger.info("WorkflowRunner initialized")
    
    def _get_compiled_graph(self):
        """Get or create the compiled workflow graph."""
        if self._compiled_graph is None:
            with log_operation(logger, "Compile LangGraph workflow"):
                graph = create_workflow_graph()
                self._compiled_graph = graph.compile()
                logger.info("Workflow graph compiled successfully")
        return self._compiled_graph
    
    async def run_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Execute a workflow by ID.
        
        Fetches workflow data, builds initial state, and runs the LangGraph.
        Updates workflow status throughout execution.
        
        Args:
            workflow_id: The workflow UUID to execute
            
        Returns:
            Final workflow state dict
        """
        log_header(logger, f"WORKFLOW EXECUTION: {workflow_id}")
        
        repo = get_workflow_repository()
        workflow = await repo.get_by_id(workflow_id)
        
        if not workflow:
            log_error_msg(logger, f"Workflow not found: {workflow_id}")
            return {"error": f"Workflow not found: {workflow_id}"}
        
        log_workflow_event(logger, workflow_id, "Starting execution", {
            "topic": workflow.get("topic", "")[:60],
            "hitl_mode": workflow.get("hitl_mode", "auto"),
            "category": workflow.get("category", "auto"),
        })
        
        # Update status to running
        await self._update_status(workflow_id, WorkflowStatus.RUNNING)
        
        # Build initial state from workflow data
        initial_state = self._build_initial_state(workflow)
        
        log_subheader(logger, "Initial State")
        log_key_value(logger, "workflow_id", workflow_id)
        log_key_value(logger, "topic", initial_state["topic"][:80])
        log_key_value(logger, "duration", f"{initial_state['duration_seconds']}s")
        log_key_value(logger, "hitl_mode", initial_state["hitl_mode"])
        
        try:
            # Get compiled graph
            graph = self._get_compiled_graph()
            
            # Execute the graph
            log_subheader(logger, "Executing LangGraph Pipeline")
            logger.info(f"{Colors.BRIGHT_CYAN}▶ Pipeline started{Colors.RESET}")
            
            # Run the graph - this will execute all nodes in sequence
            final_state = await graph.ainvoke(initial_state)
            
            # Check if workflow paused at HITL gate (manual mode)
            if final_state.get("current_hitl_gate"):
                gate = final_state.get("current_hitl_gate")
                log_workflow_event(logger, workflow_id, f"Paused at HITL gate: {gate}")
                logger.info(f"{Colors.BG_YELLOW}{Colors.BLACK} HITL {Colors.RESET} Awaiting user approval at gate: {gate}")
                return final_state
            
            # Check for errors
            if final_state.get("error"):
                log_error_msg(logger, f"Workflow failed: {final_state.get('error')}")
                await self._update_status(workflow_id, WorkflowStatus.FAILED)
                return final_state
            
            # Success!
            log_success(logger, f"Workflow {workflow_id} completed successfully!")
            log_workflow_event(logger, workflow_id, "Execution completed", {
                "status": final_state.get("status", "completed"),
                "has_video": bool(final_state.get("final_video_url")),
                "generation_time": f"{final_state.get('generation_time_seconds', 0):.1f}s",
            })
            
            return final_state
            
        except Exception as e:
            log_error_msg(logger, f"Workflow execution failed: {e}")
            
            await self._update_status(
                workflow_id, 
                WorkflowStatus.FAILED,
                error=str(e),
            )
            
            return {
                "workflow_id": workflow_id,
                "error": f"Execution failed: {str(e)}",
                "status": "failed",
            }
    
    def _build_initial_state(self, workflow: dict[str, Any]) -> VideoGenerationState:
        """Build initial LangGraph state from workflow data.
        
        Args:
            workflow: Workflow record from database
            
        Returns:
            Initial state dict for LangGraph
        """
        return {
            "workflow_id": workflow["id"],
            "topic": workflow["topic"],
            "duration_seconds": workflow.get("duration_seconds", 18),
            "aspect_ratio": workflow.get("aspect_ratio", "9:16"),
            "resolution": workflow.get("resolution", "1080p"),
            "category": workflow.get("category", "auto"),
            "hitl_mode": workflow.get("hitl_mode", "auto"),
            "enable_audio": workflow.get("enable_audio", True),
            "enable_subtitles": workflow.get("enable_subtitles", False),
            "user_reference_image_url": workflow.get("user_reference_image_url"),
            "started_at": utc_now_iso(),
            "phase_timestamps": {},
            "hitl_approved": {},
        }
    
    async def _update_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update workflow status in database.
        
        Args:
            workflow_id: Workflow ID
            status: New status
            error: Optional error message
        """
        try:
            repo = get_workflow_repository()
            
            update_data = {
                "status": status.value,
                "updated_at": utc_now_iso(),
            }
            
            if error:
                update_data["error"] = error
                update_data["completed_at"] = utc_now_iso()
            
            await repo.update(workflow_id, update_data)
            
            log_workflow_event(logger, workflow_id, f"Status updated: {status.value}")
            
        except Exception as e:
            log_error_msg(logger, f"Failed to update status: {e}")


# Singleton instance
_workflow_runner: Optional[WorkflowRunner] = None


def get_workflow_runner() -> WorkflowRunner:
    """Get or create the WorkflowRunner singleton."""
    global _workflow_runner
    if _workflow_runner is None:
        _workflow_runner = WorkflowRunner()
    return _workflow_runner


async def run_workflow_background(workflow_id: str) -> None:
    """Run a workflow as a background task.
    
    This is the entry point for triggering workflow execution
    after creation. It runs in the background without blocking
    the API response.
    
    Args:
        workflow_id: The workflow ID to execute
    """
    logger.info(f"{Colors.BRIGHT_MAGENTA}[BACKGROUND]{Colors.RESET} Starting workflow: {workflow_id}")
    
    try:
        runner = get_workflow_runner()
        await runner.run_workflow(workflow_id)
    except Exception as e:
        log_error_msg(logger, f"Background workflow failed: {e}")
        
        # Ensure status is updated even if runner fails
        try:
            repo = get_workflow_repository()
            await repo.update(workflow_id, {
                "status": WorkflowStatus.FAILED.value,
                "error": f"Background execution failed: {str(e)}",
                "completed_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            })
        except Exception as update_err:
            log_error_msg(logger, f"Failed to update failed status: {update_err}")
