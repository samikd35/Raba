"""RABA HITL API Routes.

API endpoints for Human-in-the-Loop feedback and gate management.

Endpoints:
- POST /workflows/{workflow_id}/feedback - Submit HITL feedback
- GET /workflows/{workflow_id}/gate - Get current gate status
- GET /workflows/{workflow_id}/gate/{gate_name}/output - Get gate output

Reference:
- Guides/SRS.md Section 3.7 (FR-7xx)
- Guides/RABA_Architecture.md Section 5.2
"""

from fastapi import APIRouter, HTTPException, Path, status

from app.models.hitl import (
    VALID_ACTIONS_PER_GATE,
    HITLFeedbackRequest,
    HITLFeedbackResponse,
    HITLGate,
    HITLGateOutputResponse,
    HITLGateStatusResponse,
    HITLModeNotManualError,
    InvalidHITLActionError,
    MaxRegenerationsExceededError,
    WorkflowNotAtGateError,
)
from app.services.hitl_service import HITLServiceError, get_hitl_service
from app.utils.logging import (
    get_logger,
    log_header,
    log_key_value,
    log_request_start,
    log_request_end,
    log_success,
    log_error_msg,
    log_warning_msg,
    log_hitl_event,
    log_operation,
)
import time

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["video-generation"])


@router.post(
    "/{workflow_id}/feedback",
    response_model=HITLFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit HITL feedback",
    description="Submit user feedback at an HITL gate (approve, edit, regenerate, add_image)",
)
async def submit_feedback(
    workflow_id: str = Path(..., description="Workflow identifier"),
    request: HITLFeedbackRequest = ...,
) -> HITLFeedbackResponse:
    """Submit HITL feedback at the current gate.
    
    Actions:
    - **approve**: Continue to next step
    - **edit**: Apply direct edits and continue
    - **regenerate**: Re-run agent with feedback (max 3 attempts)
    - **add_image**: Add user images (Gate 4 only)
    """
    start_time = time.time()
    log_header(logger, f"HITL FEEDBACK: {workflow_id}")
    log_request_start(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", {
        "action": request.action.value,
        "has_feedback": bool(request.feedback),
        "has_edits": bool(request.edited_content),
        "has_images": bool(request.additional_images),
    })
    
    try:
        with log_operation(logger, f"Process HITL action: {request.action.value}"):
            service = get_hitl_service()
            response = await service.process_feedback(workflow_id, request)
        
        log_hitl_event(logger, workflow_id, response.gate.value, request.action.value, {
            "regeneration_count": response.regeneration_count,
            "next_step": response.next_step or "awaiting",
        })
        log_success(logger, f"HITL feedback processed successfully")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", 200, duration_ms)
        return response
        
    except HITLModeNotManualError as e:
        log_warning_msg(logger, f"HITL action on auto workflow: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", 400, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except WorkflowNotAtGateError as e:
        log_warning_msg(logger, f"Workflow not at gate: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", 409, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    
    except InvalidHITLActionError as e:
        log_warning_msg(logger, f"Invalid action for gate: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", 400, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except MaxRegenerationsExceededError as e:
        log_warning_msg(logger, f"Max regenerations exceeded: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", 400, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except HITLServiceError as e:
        log_error_msg(logger, f"HITL service error: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "POST", f"/api/v1/workflows/{workflow_id}/feedback", 500, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{workflow_id}/gate",
    response_model=HITLGateStatusResponse,
    summary="Get current gate status",
    description="Get the current HITL gate status for a workflow",
)
async def get_gate_status(
    workflow_id: str = Path(..., description="Workflow identifier"),
) -> HITLGateStatusResponse:
    """Get current HITL gate status.
    
    Returns information about:
    - Current gate (if paused)
    - Gate output for review
    - Regeneration count
    - Approved gates
    """
    start_time = time.time()
    log_request_start(logger, "GET", f"/api/v1/workflows/{workflow_id}/gate")
    
    try:
        with log_operation(logger, "Fetch gate status"):
            service = get_hitl_service()
            result = await service.get_gate_status(workflow_id)
        
        log_hitl_event(logger, workflow_id, result.current_gate.value if result.current_gate else "none", "status_check", {
            "hitl_mode": result.hitl_mode,
            "workflow_status": result.workflow_status,
            "approved_gates": len(result.approved_gates),
        })
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}/gate", 200, duration_ms)
        return result
        
    except HITLServiceError as e:
        log_error_msg(logger, f"Failed to get gate status: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}/gate", 404, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{workflow_id}/gate/{gate_name}/output",
    response_model=HITLGateOutputResponse,
    summary="Get gate output for review",
    description="Get the agent output at a specific gate for user review",
)
async def get_gate_output(
    workflow_id: str = Path(..., description="Workflow identifier"),
    gate_name: str = Path(..., description="Gate name (tool_selection, research, script, images, video)"),
) -> HITLGateOutputResponse:
    """Get the output from an agent for review at a gate.
    
    Returns the agent's output along with valid actions for the gate.
    """
    start_time = time.time()
    log_request_start(logger, "GET", f"/api/v1/workflows/{workflow_id}/gate/{gate_name}/output")
    
    # Validate gate name
    try:
        gate = HITLGate(gate_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid gate name: {gate_name}. Valid: {[g.value for g in HITLGate]}",
        )
    
    try:
        service = get_hitl_service()
        workflow = await service.get_workflow(workflow_id)
        
        # Get output from stored gate outputs
        gate_outputs = workflow.get("hitl_gate_outputs") or {}
        output = gate_outputs.get(gate_name)
        
        if not output:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No output found for gate {gate_name}",
            )
        
        # Get regeneration info
        regen_counts = workflow.get("regeneration_counts") or {}
        regen_count = regen_counts.get(gate_name, 0)
        
        # Output type mapping
        output_types = {
            HITLGate.TOOL_SELECTION: "tool_selection",
            HITLGate.RESEARCH: "research",
            HITLGate.SCRIPT: "script",
            HITLGate.IMAGES: "images",
            HITLGate.VIDEO: "video",
        }
        
        log_hitl_event(logger, workflow_id, gate_name, "output_retrieved", {
            "regeneration_count": regen_count,
            "can_regenerate": regen_count < 3,
        })
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}/gate/{gate_name}/output", 200, duration_ms)
        
        return HITLGateOutputResponse(
            workflow_id=workflow_id,
            gate=gate,
            output=output,
            output_type=output_types[gate],
            regeneration_count=regen_count,
            can_regenerate=regen_count < 3,
            valid_actions=VALID_ACTIONS_PER_GATE[gate],
        )
        
    except HITLServiceError as e:
        log_error_msg(logger, f"Failed to get gate output: {e}")
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(logger, "GET", f"/api/v1/workflows/{workflow_id}/gate/{gate_name}/output", 404, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
