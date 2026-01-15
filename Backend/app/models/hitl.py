"""RABA HITL (Human-in-the-Loop) Models.

Defines Pydantic models and enums for the HITL system that enables
manual approval mode with 5 gates for user review and feedback.

Reference:
- Guides/SRS.md Section 3.7 (FR-7xx)
- Guides/RABA_Architecture.md Section 5.2
- Guides/rule.md HITL Gates section
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HITLAction(str, Enum):
    """Actions a user can take at an HITL gate.
    
    Reference: RABA_Architecture.md Section 5.2
    """
    APPROVE = "approve"         # Continue to next step
    EDIT = "edit"               # User directly edited the content
    REGENERATE = "regenerate"   # Re-run agent with feedback
    ADD_IMAGE = "add_image"     # User adds reference image (Gate 4 only)


class HITLGate(str, Enum):
    """The 5 HITL gates in the workflow.
    
    Reference: SRS.md Section 9.1, rule.md HITL Gates
    """
    TOOL_SELECTION = "tool_selection"  # Gate 1: After Intent/Tool Selector
    RESEARCH = "research"              # Gate 2: After Deep Research
    SCRIPT = "script"                  # Gate 3: After Script Generator
    IMAGES = "images"                  # Gate 4: After Image Generator
    VIDEO = "video"                    # Gate 5: After Video Generator


class HITLGateStatus(str, Enum):
    """Status of an HITL gate."""
    PENDING = "pending"           # Not yet reached
    AWAITING = "awaiting"         # Paused, waiting for user action
    APPROVED = "approved"         # User approved, continuing
    REGENERATING = "regenerating" # User requested regeneration


# Mapping of gates to workflow status strings (FR-707)
GATE_STATUS_MAP = {
    HITLGate.TOOL_SELECTION: "awaiting_tool_selection_approval",
    HITLGate.RESEARCH: "awaiting_research_approval",
    HITLGate.SCRIPT: "awaiting_script_approval",
    HITLGate.IMAGES: "awaiting_images_approval",
    HITLGate.VIDEO: "awaiting_video_approval",
}

# Mapping of gates to the agent that runs before them
GATE_AGENT_MAP = {
    HITLGate.TOOL_SELECTION: "intent_tool_selector",
    HITLGate.RESEARCH: "deep_research",
    HITLGate.SCRIPT: "script_writer",
    HITLGate.IMAGES: "image_generator",
    HITLGate.VIDEO: "video_generator",
}

# Valid actions per gate (ADD_IMAGE only valid at images gate)
VALID_ACTIONS_PER_GATE = {
    HITLGate.TOOL_SELECTION: [HITLAction.APPROVE, HITLAction.EDIT, HITLAction.REGENERATE],
    HITLGate.RESEARCH: [HITLAction.APPROVE, HITLAction.EDIT, HITLAction.REGENERATE],
    HITLGate.SCRIPT: [HITLAction.APPROVE, HITLAction.EDIT, HITLAction.REGENERATE],
    HITLGate.IMAGES: [HITLAction.APPROVE, HITLAction.EDIT, HITLAction.REGENERATE, HITLAction.ADD_IMAGE],
    HITLGate.VIDEO: [HITLAction.APPROVE, HITLAction.REGENERATE],  # No edit for video
}

# Maximum regeneration attempts per gate (FR-704)
MAX_REGENERATION_ATTEMPTS = 3


class HITLFeedback(BaseModel):
    """User feedback at an HITL gate.
    
    Stored in workflows.hitl_feedback (FR-705).
    
    Reference: RABA_Architecture.md Section 5.2
    """
    gate: HITLGate = Field(..., description="The gate this feedback is for")
    action: HITLAction = Field(..., description="Action taken by user")
    feedback: Optional[str] = Field(
        default=None, 
        description="User's feedback text for regeneration"
    )
    edited_content: Optional[dict[str, Any]] = Field(
        default=None, 
        description="User's direct edits to content"
    )
    additional_images: Optional[list[str]] = Field(
        default=None, 
        description="User-added image URLs (Gate 4 only)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When feedback was submitted"
    )
    regeneration_attempt: int = Field(
        default=0, 
        ge=0, 
        le=MAX_REGENERATION_ATTEMPTS,
        description="Which regeneration attempt this is (0 if not regeneration)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "gate": "script",
                "action": "regenerate",
                "feedback": "Make the hook more dramatic",
                "created_at": "2026-01-15T10:30:00Z",
                "regeneration_attempt": 1
            }
        }


class HITLGateInfo(BaseModel):
    """Information about a specific HITL gate's current state."""
    gate: HITLGate = Field(..., description="Gate identifier")
    status: HITLGateStatus = Field(
        default=HITLGateStatus.PENDING,
        description="Current status of this gate"
    )
    current_output: Optional[dict[str, Any]] = Field(
        default=None, 
        description="Output from agent being reviewed"
    )
    regeneration_count: int = Field(
        default=0, 
        ge=0, 
        le=MAX_REGENERATION_ATTEMPTS,
        description="Number of regeneration attempts used"
    )
    feedback_history: list[HITLFeedback] = Field(
        default_factory=list,
        description="History of feedback for this gate"
    )
    awaiting_since: Optional[datetime] = Field(
        default=None, 
        description="When gate started awaiting approval"
    )
    
    @property
    def can_regenerate(self) -> bool:
        """Check if regeneration is still allowed."""
        return self.regeneration_count < MAX_REGENERATION_ATTEMPTS


class HITLFeedbackRequest(BaseModel):
    """API request model for submitting HITL feedback.
    
    POST /api/v1/workflows/{workflow_id}/feedback
    """
    action: HITLAction = Field(..., description="Action to take")
    feedback: Optional[str] = Field(
        default=None, 
        description="Feedback text for regeneration"
    )
    edited_content: Optional[dict[str, Any]] = Field(
        default=None, 
        description="Direct edits to apply"
    )
    additional_images: Optional[list[str]] = Field(
        default=None,
        description="Additional image URLs to add (Gate 4 only)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Approve",
                    "value": {"action": "approve"}
                },
                {
                    "summary": "Regenerate with feedback",
                    "value": {
                        "action": "regenerate",
                        "feedback": "Make it more dramatic"
                    }
                },
                {
                    "summary": "Edit script",
                    "value": {
                        "action": "edit",
                        "edited_content": {
                            "hook": {"script": "You won't believe this..."}
                        }
                    }
                },
                {
                    "summary": "Add image",
                    "value": {
                        "action": "add_image",
                        "additional_images": ["https://example.com/image.png"]
                    }
                }
            ]
        }


class HITLFeedbackResponse(BaseModel):
    """API response model after processing HITL feedback."""
    workflow_id: str = Field(..., description="Workflow identifier")
    gate: HITLGate = Field(..., description="Gate that was processed")
    action_taken: HITLAction = Field(..., description="Action that was applied")
    next_step: Optional[str] = Field(
        default=None, 
        description="Next node in workflow (if continuing)"
    )
    regeneration_count: int = Field(
        default=0, 
        description="Current regeneration count for this gate"
    )
    max_regenerations: int = Field(
        default=MAX_REGENERATION_ATTEMPTS,
        description="Maximum allowed regenerations"
    )
    message: Optional[str] = Field(
        default=None,
        description="Additional message about the action"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "abc-123-def",
                "gate": "script",
                "action_taken": "regenerate",
                "regeneration_count": 1,
                "max_regenerations": 3,
                "message": "Regenerating script with your feedback"
            }
        }


class HITLGateStatusResponse(BaseModel):
    """API response model for gate status query."""
    workflow_id: str = Field(..., description="Workflow identifier")
    current_gate: Optional[HITLGate] = Field(
        default=None, 
        description="Currently active gate (None if not paused)"
    )
    gate_info: Optional[HITLGateInfo] = Field(
        default=None, 
        description="Detailed info about current gate"
    )
    hitl_mode: str = Field(
        default="auto", 
        description="HITL mode (auto or manual)"
    )
    workflow_status: str = Field(..., description="Current workflow status")
    approved_gates: list[HITLGate] = Field(
        default_factory=list,
        description="List of gates already approved"
    )


class HITLGateOutputResponse(BaseModel):
    """API response for retrieving gate output for review."""
    workflow_id: str = Field(..., description="Workflow identifier")
    gate: HITLGate = Field(..., description="Gate identifier")
    output: dict[str, Any] = Field(..., description="Agent output to review")
    output_type: str = Field(..., description="Type of output (e.g., 'script', 'images')")
    regeneration_count: int = Field(default=0, description="Regeneration attempts used")
    can_regenerate: bool = Field(default=True, description="Whether regeneration is allowed")
    valid_actions: list[HITLAction] = Field(
        default_factory=list,
        description="Actions valid for this gate"
    )


# Error classes for HITL operations
class HITLError(Exception):
    """Base exception for HITL errors."""
    pass


class MaxRegenerationsExceededError(HITLError):
    """Raised when max regeneration attempts (3) have been reached."""
    def __init__(self, gate: HITLGate):
        self.gate = gate
        super().__init__(
            f"Maximum regeneration attempts ({MAX_REGENERATION_ATTEMPTS}) "
            f"exceeded for gate: {gate.value}"
        )


class InvalidHITLActionError(HITLError):
    """Raised when an invalid action is attempted for a gate."""
    def __init__(self, gate: HITLGate, action: HITLAction):
        self.gate = gate
        self.action = action
        valid = VALID_ACTIONS_PER_GATE.get(gate, [])
        super().__init__(
            f"Action '{action.value}' is not valid for gate '{gate.value}'. "
            f"Valid actions: {[a.value for a in valid]}"
        )


class WorkflowNotAtGateError(HITLError):
    """Raised when workflow is not at the expected gate."""
    def __init__(self, workflow_id: str, expected_gate: Optional[HITLGate], actual_gate: Optional[str]):
        self.workflow_id = workflow_id
        self.expected_gate = expected_gate
        self.actual_gate = actual_gate
        super().__init__(
            f"Workflow {workflow_id} is not at expected gate. "
            f"Expected: {expected_gate.value if expected_gate else 'any'}, "
            f"Actual: {actual_gate or 'not at any gate'}"
        )


class HITLModeNotManualError(HITLError):
    """Raised when HITL action attempted on auto-mode workflow."""
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        super().__init__(
            f"Workflow {workflow_id} is in auto mode. "
            "HITL actions only available in manual mode."
        )
