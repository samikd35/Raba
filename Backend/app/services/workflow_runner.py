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


def _normalize_image_list(val: Any) -> list[str]:
    """Normalize research_images or generated_images from DB to list of URL strings."""
    if not val:
        return []
    if isinstance(val, list):
        out = []
        for i in val:
            if isinstance(i, str):
                out.append(i)
            elif isinstance(i, dict):
                u = i.get("url") or i.get("image_url") or i.get("storage_url")
                if u:
                    out.append(u)
        return out
    if isinstance(val, dict):
        arr = val.get("image_urls") or val.get("all_image_urls") or val.get("images") or []
        return _normalize_image_list(arr) if isinstance(arr, list) else []
    return []


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
    
    async def run_workflow(self, workflow_id: str, input_overrides: Optional[dict[str, Any]] = None) -> dict[str, Any]:
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
        if input_overrides:
            # Merge any user-provided overrides (e.g., selected video model)
            initial_state.update(input_overrides)
        
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
            # Set recursion_limit to handle longer workflows (default is 25)
            config = {"recursion_limit": 100}
            final_state = await graph.ainvoke(initial_state, config=config)
            
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
            "enable_audio": workflow.get("enable_audio", False),
            "enable_subtitles": workflow.get("enable_subtitles", False),
            "user_reference_image_url": workflow.get("user_reference_image_url"),
            "user_selected_tool_id": workflow.get("user_selected_tool_id"),
            "started_at": utc_now_iso(),
            "phase_timestamps": {},
            "hitl_approved": {},
        }

    def _build_continue_state(self, workflow: dict[str, Any]) -> VideoGenerationState:
        """Build LangGraph state from a failed workflow's persisted outputs.
        
        Hydrates state with all completed step outputs so the graph can skip
        those nodes and continue from the first step that did not complete.
        
        CRITICAL: Extracts nested fields (scenes, hook, call_to_action) from script_output
        and top-level fields (visual_validation, global_style_anchor) so downstream nodes
        are properly grounded on the persisted outputs.
        
        Args:
            workflow: Workflow record from database (must be failed)
            
        Returns:
            State dict with persisted outputs for continue run
        """
        ts = workflow.get("tool_selection") or {}
        base = self._build_initial_state(workflow)
        # Map DB fields to state keys used by nodes
        base["selected_tool"] = ts.get("selected_tool") or ts
        base["intent_metadata"] = ts.get("intent_metadata")
        base["tool_execution_params"] = ts.get("tool_execution_params")
        base["research_data"] = workflow.get("research_output")
        base["research_images"] = _normalize_image_list(workflow.get("research_images"))
        
        # CRITICAL: Extract script_output and nested fields that nodes expect separately
        script_output = workflow.get("script_output") or {}
        base["script_output"] = script_output
        # Extract scenes, hook, and call_to_action from script_output for downstream nodes
        # Image Generator and Video Generator read these as top-level state fields
        if script_output:
            base["scenes"] = script_output.get("scenes", [])
            base["hook"] = script_output.get("hook", {})
            base["call_to_action"] = script_output.get("call_to_action", {})
            # Also preserve viral_score if present
            if "viral_score" in script_output:
                base["viral_score"] = script_output.get("viral_score")
        
        # CRITICAL: Restore validation and anchor outputs for downstream grounding
        base["visual_validation"] = workflow.get("visual_validation")
        base["global_style_anchor"] = workflow.get("global_style_anchor")
        
        base["character_reference_sheet"] = workflow.get("character_reference_sheet")
        base["generated_images"] = _normalize_image_list(workflow.get("generated_images"))
        # video_output.video_url -> final_video_url for downstream
        vo = workflow.get("video_output") or {}
        if isinstance(vo, dict) and vo.get("video_url"):
            base["final_video_url"] = vo["video_url"]
        # Avoid HITL gates on already-completed steps when continuing
        base["hitl_approved"] = {
            "tool_selection": True,
            "research": True,
            "script": True,
            "images": True,
            "video": True,
        }
        base["regeneration_counts"] = workflow.get("regeneration_counts") or {}
        return base

    async def run_workflow_continue(self, workflow_id: str, input_overrides: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Resume a failed workflow from the last persisted step.
        
        Loads persisted outputs (tool_selection, research_output, script_output,
        character_reference_sheet, generated_images, video_output) into state.
        Nodes skip work when their output already exists, so execution continues
        from the first step that did not complete.
        
        Call only for workflows with status 'failed'.
        
        Args:
            workflow_id: Workflow UUID
            input_overrides: Optional overrides (e.g. video_model)
            
        Returns:
            Final workflow state dict
        """
        log_header(logger, f"WORKFLOW CONTINUE: {workflow_id}")
        
        repo = get_workflow_repository()
        workflow = await repo.get_by_id(workflow_id)
        
        if not workflow:
            log_error_msg(logger, f"Workflow not found: {workflow_id}")
            return {"error": f"Workflow not found: {workflow_id}"}
        
        if workflow.get("status") != "failed":
            log_error_msg(logger, f"Cannot continue workflow {workflow_id}: status={workflow.get('status')}")
            return {"error": f"Only failed workflows can be continued. Current status: {workflow.get('status')}"}
        
        log_workflow_event(logger, workflow_id, "Continue from failed", {
            "topic": workflow.get("topic", "")[:60],
            "has_script": bool(workflow.get("script_output")),
            "has_images": bool(workflow.get("generated_images")),
        })
        
        # Set status to running and clear previous error
        await repo.update(workflow_id, {
            "status": WorkflowStatus.RUNNING.value,
            "updated_at": utc_now_iso(),
            "error": None,
        })
        
        initial_state = self._build_continue_state(workflow)
        if input_overrides:
            initial_state.update(input_overrides)
        
        log_subheader(logger, "Continue State (hydrated from DB)")
        log_key_value(logger, "workflow_id", workflow_id)
        log_key_value(logger, "has research_data", bool(initial_state.get("research_data")))
        log_key_value(logger, "has script_output", bool(initial_state.get("script_output")))
        log_key_value(logger, "has generated_images", bool(initial_state.get("generated_images")))
        
        try:
            graph = self._get_compiled_graph()
            log_subheader(logger, "Executing LangGraph Pipeline (continue)")
            logger.info(f"{Colors.BRIGHT_CYAN}▶ Pipeline continue started{Colors.RESET}")
            
            # Set recursion_limit to handle longer workflows (default is 25)
            config = {"recursion_limit": 100}
            final_state = await graph.ainvoke(initial_state, config=config)
            
            if final_state.get("current_hitl_gate"):
                log_workflow_event(logger, workflow_id, f"Paused at HITL gate: {final_state.get('current_hitl_gate')}")
                return final_state
            
            if final_state.get("error"):
                log_error_msg(logger, f"Workflow continue failed: {final_state.get('error')}")
                await self._update_status(workflow_id, WorkflowStatus.FAILED, error=final_state.get("error"))
                return final_state
            
            log_success(logger, f"Workflow {workflow_id} continued and completed successfully!")
            log_workflow_event(logger, workflow_id, "Continue execution completed", {
                "has_video": bool(final_state.get("final_video_url")),
            })
            return final_state
            
        except Exception as e:
            log_error_msg(logger, f"Workflow continue failed: {e}")
            await self._update_status(workflow_id, WorkflowStatus.FAILED, error=str(e))
            return {"workflow_id": workflow_id, "error": str(e), "status": "failed"}
    
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


async def run_workflow_background(workflow_id: str, video_model: Optional[str] = None) -> None:
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
        overrides = {"video_model": video_model} if video_model else None
        await runner.run_workflow(workflow_id, input_overrides=overrides)
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


async def run_workflow_continue_background(workflow_id: str) -> None:
    """Run a continue-from-failed workflow as a background task.
    
    Args:
        workflow_id: The workflow ID to continue
    """
    logger.info(f"{Colors.BRIGHT_MAGENTA}[BACKGROUND]{Colors.RESET} Continue workflow: {workflow_id}")
    
    try:
        runner = get_workflow_runner()
        await runner.run_workflow_continue(workflow_id)
    except Exception as e:
        log_error_msg(logger, f"Background workflow continue failed: {e}")
        try:
            repo = get_workflow_repository()
            await repo.update(workflow_id, {
                "status": WorkflowStatus.FAILED.value,
                "error": f"Continue failed: {str(e)}",
                "completed_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            })
        except Exception as update_err:
            log_error_msg(logger, f"Failed to update failed status: {update_err}")
