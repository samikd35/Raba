"""RABA HITL Service.

Service for managing Human-in-the-Loop gates, feedback processing,
and regeneration logic.

Reference:
- Guides/SRS.md Section 3.7 (FR-7xx)
- Guides/RABA_Architecture.md Section 5.2
"""

from datetime import datetime
from typing import Any, Optional

from app.models.hitl import (
    GATE_AGENT_MAP,
    GATE_STATUS_MAP,
    MAX_REGENERATION_ATTEMPTS,
    VALID_ACTIONS_PER_GATE,
    HITLAction,
    HITLFeedback,
    HITLFeedbackRequest,
    HITLFeedbackResponse,
    HITLGate,
    HITLGateInfo,
    HITLGateStatus,
    HITLGateStatusResponse,
    HITLModeNotManualError,
    InvalidHITLActionError,
    MaxRegenerationsExceededError,
    WorkflowNotAtGateError,
)
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class HITLServiceError(Exception):
    """Base exception for HITL service errors."""
    pass


class HITLService:
    """Service for HITL gate management and feedback processing.
    
    Handles:
    - Pausing workflow at gates (FR-702)
    - Processing user actions: APPROVE, EDIT, REGENERATE, ADD_IMAGE (FR-703)
    - Enforcing regeneration limits (FR-704)
    - Persisting feedback to database (FR-705)
    - Updating workflow status (FR-706, FR-707)
    """
    
    def __init__(self):
        """Initialize the HITL service."""
        self.supabase = get_supabase_client()
        logger.info("HITLService initialized")
    
    async def pause_at_gate(
        self,
        workflow_id: str,
        gate: HITLGate,
        current_output: dict[str, Any],
    ) -> None:
        """Pause workflow at an HITL gate for user review.
        
        Updates workflow status to awaiting_<gate>_approval (FR-707).
        Stores current output for user review.
        
        Args:
            workflow_id: Workflow identifier
            gate: Gate to pause at
            current_output: Agent output for user to review
        """
        logger.info(f"Pausing workflow {workflow_id} at gate: {gate.value}")
        
        status = GATE_STATUS_MAP[gate]
        
        # Update workflow in database
        update_data = {
            "status": status,
            "current_hitl_gate": gate.value,
            "hitl_gate_outputs": {gate.value: current_output},
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        self.supabase.table("workflows").update(update_data).eq(
            "id", workflow_id
        ).execute()
        
        logger.info(f"Workflow {workflow_id} paused at {gate.value}, status: {status}")
    
    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Get workflow data from database."""
        result = self.supabase.table("workflows").select("*").eq(
            "id", workflow_id
        ).single().execute()
        
        if not result.data:
            raise HITLServiceError(f"Workflow not found: {workflow_id}")
        
        return result.data
    
    async def get_gate_status(self, workflow_id: str) -> HITLGateStatusResponse:
        """Get current HITL gate status for a workflow."""
        workflow = await self.get_workflow(workflow_id)
        
        current_gate_str = workflow.get("current_hitl_gate")
        current_gate = HITLGate(current_gate_str) if current_gate_str else None
        
        gate_info = None
        if current_gate:
            gate_outputs = workflow.get("hitl_gate_outputs") or {}
            feedback_history = workflow.get("hitl_feedback") or []
            regen_counts = workflow.get("regeneration_counts") or {}
            
            gate_feedback = [
                HITLFeedback(**f) for f in feedback_history 
                if f.get("gate") == current_gate.value
            ]
            
            gate_info = HITLGateInfo(
                gate=current_gate,
                status=HITLGateStatus.AWAITING,
                current_output=gate_outputs.get(current_gate.value),
                regeneration_count=regen_counts.get(current_gate.value, 0),
                feedback_history=gate_feedback,
                awaiting_since=datetime.fromisoformat(workflow.get("updated_at"))
                if workflow.get("updated_at") else None,
            )
        
        approved = workflow.get("hitl_approved") or {}
        approved_gates = [HITLGate(g) for g, v in approved.items() if v]
        
        return HITLGateStatusResponse(
            workflow_id=workflow_id,
            current_gate=current_gate,
            gate_info=gate_info,
            hitl_mode=workflow.get("hitl_mode", "auto"),
            workflow_status=workflow.get("status", "unknown"),
            approved_gates=approved_gates,
        )
    
    async def process_feedback(
        self,
        workflow_id: str,
        request: HITLFeedbackRequest,
    ) -> HITLFeedbackResponse:
        """Process user feedback at an HITL gate.
        
        Args:
            workflow_id: Workflow identifier
            request: User's feedback request
            
        Returns:
            Response with action result
            
        Raises:
            HITLModeNotManualError: If workflow is in auto mode
            WorkflowNotAtGateError: If workflow not at any gate
            InvalidHITLActionError: If action invalid for gate
            MaxRegenerationsExceededError: If 3 attempts exceeded
        """
        workflow = await self.get_workflow(workflow_id)
        
        # Validate manual mode
        if workflow.get("hitl_mode") != "manual":
            raise HITLModeNotManualError(workflow_id)
        
        # Get current gate
        current_gate_str = workflow.get("current_hitl_gate")
        if not current_gate_str:
            raise WorkflowNotAtGateError(workflow_id, None, None)
        
        gate = HITLGate(current_gate_str)
        
        # Validate action for gate
        valid_actions = VALID_ACTIONS_PER_GATE.get(gate, [])
        if request.action not in valid_actions:
            raise InvalidHITLActionError(gate, request.action)
        
        # Get regeneration count
        regen_counts = workflow.get("regeneration_counts") or {}
        current_regen = regen_counts.get(gate.value, 0)
        
        # Process based on action
        if request.action == HITLAction.APPROVE:
            return await self._handle_approve(workflow_id, gate, workflow)
        
        elif request.action == HITLAction.EDIT:
            return await self._handle_edit(
                workflow_id, gate, workflow, request.edited_content
            )
        
        elif request.action == HITLAction.REGENERATE:
            if current_regen >= MAX_REGENERATION_ATTEMPTS:
                raise MaxRegenerationsExceededError(gate)
            return await self._handle_regenerate(
                workflow_id, gate, workflow, request.feedback, current_regen
            )
        
        elif request.action == HITLAction.ADD_IMAGE:
            return await self._handle_add_image(
                workflow_id, gate, workflow, request.additional_images
            )
        
        raise HITLServiceError(f"Unknown action: {request.action}")
    
    async def _handle_approve(
        self,
        workflow_id: str,
        gate: HITLGate,
        workflow: dict,
    ) -> HITLFeedbackResponse:
        """Handle APPROVE action - continue to next step."""
        logger.info(f"Processing APPROVE for {workflow_id} at {gate.value}")
        
        # Mark gate as approved
        approved = workflow.get("hitl_approved") or {}
        approved[gate.value] = True
        
        # Store feedback
        feedback = HITLFeedback(gate=gate, action=HITLAction.APPROVE)
        feedback_history = workflow.get("hitl_feedback") or []
        feedback_history.append(feedback.model_dump(mode="json"))
        
        # Clear current gate
        self.supabase.table("workflows").update({
            "hitl_approved": approved,
            "hitl_feedback": feedback_history,
            "current_hitl_gate": None,
            "status": "processing",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", workflow_id).execute()
        
        # Determine next step
        next_steps = {
            HITLGate.TOOL_SELECTION: "deep_research",
            HITLGate.RESEARCH: "script_writer",
            HITLGate.SCRIPT: "image_generator",
            HITLGate.IMAGES: "video_generator",
            HITLGate.VIDEO: "output_processor",
        }
        
        return HITLFeedbackResponse(
            workflow_id=workflow_id,
            gate=gate,
            action_taken=HITLAction.APPROVE,
            next_step=next_steps.get(gate),
            message="Approved. Continuing to next step.",
        )
    
    async def _handle_edit(
        self,
        workflow_id: str,
        gate: HITLGate,
        workflow: dict,
        edited_content: Optional[dict],
    ) -> HITLFeedbackResponse:
        """Handle EDIT action - apply user edits and continue."""
        logger.info(f"Processing EDIT for {workflow_id} at {gate.value}")
        
        if not edited_content:
            raise HITLServiceError("edited_content required for EDIT action")
        
        # Apply edits based on gate
        await self._apply_edits(workflow_id, gate, edited_content)
        
        # Mark as approved and store feedback
        approved = workflow.get("hitl_approved") or {}
        approved[gate.value] = True
        
        feedback = HITLFeedback(
            gate=gate, 
            action=HITLAction.EDIT,
            edited_content=edited_content,
        )
        feedback_history = workflow.get("hitl_feedback") or []
        feedback_history.append(feedback.model_dump(mode="json"))
        
        self.supabase.table("workflows").update({
            "hitl_approved": approved,
            "hitl_feedback": feedback_history,
            "current_hitl_gate": None,
            "status": "processing",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", workflow_id).execute()
        
        return HITLFeedbackResponse(
            workflow_id=workflow_id,
            gate=gate,
            action_taken=HITLAction.EDIT,
            message="Edits applied. Continuing to next step.",
        )
    
    async def _handle_regenerate(
        self,
        workflow_id: str,
        gate: HITLGate,
        workflow: dict,
        feedback_text: Optional[str],
        current_regen: int,
    ) -> HITLFeedbackResponse:
        """Handle REGENERATE action - re-run agent with feedback."""
        logger.info(f"Processing REGENERATE for {workflow_id} at {gate.value}")
        
        new_regen = current_regen + 1
        
        # Update regeneration count
        regen_counts = workflow.get("regeneration_counts") or {}
        regen_counts[gate.value] = new_regen
        
        # Store feedback
        feedback = HITLFeedback(
            gate=gate,
            action=HITLAction.REGENERATE,
            feedback=feedback_text,
            regeneration_attempt=new_regen,
        )
        feedback_history = workflow.get("hitl_feedback") or []
        feedback_history.append(feedback.model_dump(mode="json"))
        
        # Set status for regeneration (agent will pick up feedback)
        self.supabase.table("workflows").update({
            "regeneration_counts": regen_counts,
            "hitl_feedback": feedback_history,
            "current_hitl_gate": None,
            "pending_regeneration": gate.value,
            "regeneration_feedback": feedback_text,
            "status": "regenerating",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", workflow_id).execute()
        
        return HITLFeedbackResponse(
            workflow_id=workflow_id,
            gate=gate,
            action_taken=HITLAction.REGENERATE,
            regeneration_count=new_regen,
            message=f"Regenerating (attempt {new_regen}/{MAX_REGENERATION_ATTEMPTS})",
        )
    
    async def _handle_add_image(
        self,
        workflow_id: str,
        gate: HITLGate,
        workflow: dict,
        additional_images: Optional[list[str]],
    ) -> HITLFeedbackResponse:
        """Handle ADD_IMAGE action - add user images and continue."""
        logger.info(f"Processing ADD_IMAGE for {workflow_id} at {gate.value}")
        
        if gate != HITLGate.IMAGES:
            raise InvalidHITLActionError(gate, HITLAction.ADD_IMAGE)
        
        if not additional_images:
            raise HITLServiceError("additional_images required for ADD_IMAGE action")
        
        # Add images to workflow
        existing_images = workflow.get("generated_images") or []
        all_images = existing_images + additional_images
        
        # Mark approved and store feedback
        approved = workflow.get("hitl_approved") or {}
        approved[gate.value] = True
        
        feedback = HITLFeedback(
            gate=gate,
            action=HITLAction.ADD_IMAGE,
            additional_images=additional_images,
        )
        feedback_history = workflow.get("hitl_feedback") or []
        feedback_history.append(feedback.model_dump(mode="json"))
        
        self.supabase.table("workflows").update({
            "generated_images": all_images,
            "hitl_approved": approved,
            "hitl_feedback": feedback_history,
            "current_hitl_gate": None,
            "status": "processing",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", workflow_id).execute()
        
        return HITLFeedbackResponse(
            workflow_id=workflow_id,
            gate=gate,
            action_taken=HITLAction.ADD_IMAGE,
            message=f"Added {len(additional_images)} image(s). Continuing.",
        )
    
    async def _apply_edits(
        self,
        workflow_id: str,
        gate: HITLGate,
        edited_content: dict,
    ) -> None:
        """Apply user edits to the appropriate workflow field."""
        field_map = {
            HITLGate.TOOL_SELECTION: "tool_selection",
            HITLGate.RESEARCH: "research_output",
            HITLGate.SCRIPT: "script_output",
            HITLGate.IMAGES: "generated_images",
        }
        
        field = field_map.get(gate)
        if not field:
            raise HITLServiceError(f"Edit not supported for gate: {gate.value}")
        
        self.supabase.table("workflows").update({
            field: edited_content,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", workflow_id).execute()
        
        logger.info(f"Applied edits to {field} for workflow {workflow_id}")


# Singleton instance
_hitl_service: Optional[HITLService] = None


def get_hitl_service() -> HITLService:
    """Get or create HITLService singleton."""
    global _hitl_service
    if _hitl_service is None:
        _hitl_service = HITLService()
    return _hitl_service
