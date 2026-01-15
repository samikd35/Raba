# Phase 4.1 & 4.2 Implementation Plan
## HITL (Human-in-the-Loop) System & Multi-Segment Video Generation

**Version**: 1.0  
**Created**: January 15, 2026  
**Status**: Planning  
**References**:
- [Guides/SRS.md](../Guides/SRS.md) - Functional Requirements FR-7xx
- [Guides/RABA_Architecture.md](../Guides/RABA_Architecture.md) - Section 5.2 HITL System
- [Guides/rule.md](../Guides/rule.md) - HITL Gates overview
- [Backend/Documentations/veo_doc.md](./Documentations/veo_doc.md) - Video extension feature

---

## Executive Summary

This plan covers two interconnected advanced features:

| Phase | Feature | Purpose |
|-------|---------|---------|
| **4.1** | HITL System | Enable manual mode with 5 approval gates, feedback processing, and regeneration |
| **4.2** | Multi-Segment Video | Complete video extension implementation for 8-25s seamless videos |

---

## Phase 4.1: HITL (Human-in-the-Loop) System

### 4.1.1 Objectives

Enable the `manual` HITL mode where users can:
1. **Pause** workflow at 5 defined gates
2. **Review** agent outputs before proceeding
3. **APPROVE** to continue to next step
4. **EDIT** content directly (scripts, images)
5. **REGENERATE** with feedback (max 3 attempts per gate)

### 4.1.2 Functional Requirements (from SRS.md)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-701** | In auto mode, system SHALL run end-to-end without human intervention | Must |
| **FR-702** | In manual mode, system SHALL pause at 5 defined gates for user action | Must |
| **FR-703** | At each gate, user SHALL be able to APPROVE, EDIT, or REGENERATE | Must |
| **FR-704** | System SHALL limit regeneration attempts to 3 per gate | Must |
| **FR-705** | System SHALL persist all HITL feedback to `workflows.hitl_feedback` | Must |
| **FR-706** | System SHALL update `workflows.current_hitl_gate` when paused | Must |
| **FR-707** | System SHALL update `workflows.status` to `awaiting_<gate>_approval` | Must |

### 4.1.3 The 5 HITL Gates

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HITL GATES OVERVIEW                          │
├─────────┬─────────────────────┬─────────────────────────────────────┤
│  Gate   │ After Agent         │ User Can                            │
├─────────┼─────────────────────┼─────────────────────────────────────┤
│  1      │ Tool Selection      │ Change category, approve tool       │
│  2      │ Deep Research       │ Edit facts, view sources, regenerate│
│  3      │ Script Generator    │ Edit text directly, regenerate      │
│  4      │ Image Generator     │ Add/remove images, regenerate       │
│  5      │ Video Generator     │ Approve or regenerate final video   │
└─────────┴─────────────────────┴─────────────────────────────────────┘
```

**Reference**: SRS.md Section 9.1, RABA_Architecture.md Section 5.2

### 4.1.4 Architecture Design

#### 4.1.4.1 Models to Create

**File**: `app/models/hitl.py`

```
HITLAction (Enum)
├── APPROVE = "approve"         # Continue to next step
├── EDIT = "edit"              # User directly edited content
├── REGENERATE = "regenerate"   # Re-run agent with feedback
└── ADD_IMAGE = "add_image"     # User adds reference image (Gate 4 only)

HITLGate (Enum)
├── TOOL_SELECTION = "tool_selection"
├── RESEARCH = "research"
├── SCRIPT = "script"
├── IMAGES = "images"
└── VIDEO = "video"

HITLFeedback (BaseModel)
├── gate: HITLGate
├── action: HITLAction
├── feedback: Optional[str]            # User's feedback for regeneration
├── edited_content: Optional[dict]     # User's direct edits
├── additional_images: Optional[list]  # User-added images (Gate 4)
├── created_at: datetime
└── regeneration_attempt: int          # 1, 2, or 3

HITLGateStatus (BaseModel)
├── gate: HITLGate
├── status: Literal["pending", "approved", "editing", "regenerating"]
├── current_output: dict               # Output being reviewed
├── regeneration_count: int            # 0-3
├── feedback_history: list[HITLFeedback]
└── awaiting_since: Optional[datetime]
```

#### 4.1.4.2 Service to Create

**File**: `app/services/hitl_service.py`

```
HITLService
├── pause_at_gate(workflow_id, gate, current_output)
│   └── Updates workflow status to awaiting_<gate>_approval
├── process_feedback(workflow_id, feedback: HITLFeedback)
│   ├── APPROVE → clear gate, mark approved, continue
│   ├── EDIT → apply edits, clear gate, continue
│   ├── REGENERATE → validate attempts, store feedback, trigger re-run
│   └── ADD_IMAGE → add to workflow images, clear gate, continue
├── get_gate_status(workflow_id, gate) → HITLGateStatus
├── validate_regeneration_limit(workflow_id, gate) → bool
│   └── Returns False if 3 attempts reached
├── apply_user_edits(workflow_id, gate, edited_content)
│   └── Updates the appropriate workflow field
└── trigger_regeneration(workflow_id, gate, feedback)
    └── Resumes workflow at the agent before the gate
```

#### 4.1.4.3 API Endpoints to Create

**File**: `app/api/routes/hitl.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/workflows/{id}/feedback` | Submit HITL feedback |
| `GET` | `/api/v1/workflows/{id}/gate` | Get current gate status |
| `GET` | `/api/v1/workflows/{id}/gate/{gate_name}/output` | Get gate output for review |

**Request Schema** (POST /feedback):
```json
{
  "action": "approve|edit|regenerate|add_image",
  "feedback": "Optional feedback text",
  "edited_content": { "optional": "edits" },
  "additional_images": ["optional_image_urls"]
}
```

**Response Schema**:
```json
{
  "workflow_id": "uuid",
  "gate": "script",
  "action_taken": "approve",
  "next_step": "image_generator",
  "regeneration_count": 0
}
```

#### 4.1.4.4 Graph Updates

**File**: `app/graph/nodes.py` - Update HITL gate nodes

Current placeholders need to be expanded to:
1. Call `HITLService.pause_at_gate()` to update workflow status
2. Store the current output for user review
3. Use LangGraph's `interrupt_before` or checkpointing mechanism to truly pause

**File**: `app/graph/workflow.py` - Add regeneration routing

Need to add conditional edges that route back to agents when regeneration is requested:
- `hitl_tool_gate` → `intent_tool_selector` (on regenerate)
- `hitl_research_gate` → `deep_research` (on regenerate)
- `hitl_script_gate` → `script_writer` (on regenerate)
- `hitl_image_gate` → `image_generator` (on regenerate)
- `hitl_video_gate` → `video_generator` (on regenerate)

#### 4.1.4.5 State Updates

**File**: `app/graph/state.py`

Add/update fields:
```python
hitl_approved: dict[str, bool]          # {"tool_selection": True, ...}
hitl_feedback: list[dict]               # History of all feedback
current_hitl_gate: Optional[str]        # Current gate awaiting approval
regeneration_counts: dict[str, int]     # {"script": 2, ...}
hitl_gate_outputs: dict[str, dict]      # Cached outputs for review
```

### 4.1.5 Implementation Steps

#### Step 1: Create HITL Models (30 min)

**File**: `app/models/hitl.py`

- Create `HITLAction` enum with APPROVE, EDIT, REGENERATE, ADD_IMAGE
- Create `HITLGate` enum with all 5 gates
- Create `HITLFeedback` Pydantic model
- Create `HITLGateStatus` Pydantic model
- Create `HITLFeedbackRequest` for API input validation
- Create `HITLFeedbackResponse` for API response

#### Step 2: Create HITL Service (1 hour)

**File**: `app/services/hitl_service.py`

- Implement `HITLService` class with Supabase dependency
- Implement `pause_at_gate()` - updates workflow status in DB
- Implement `process_feedback()` - handles all 4 action types
- Implement `validate_regeneration_limit()` - enforces max 3 attempts
- Implement `apply_user_edits()` - applies edits based on gate type
- Implement `trigger_regeneration()` - sets up state for re-run
- Implement `get_gate_status()` - retrieves current gate info

#### Step 3: Create HITL API Endpoints (45 min)

**File**: `app/api/routes/hitl.py`

- Create router with `/workflows/{workflow_id}/feedback` POST endpoint
- Create `/workflows/{workflow_id}/gate` GET endpoint
- Add input validation with HITLFeedbackRequest
- Integrate with HITLService
- Add proper error handling for:
  - Workflow not found
  - Not at expected gate
  - Max regenerations exceeded
  - Invalid action for gate

#### Step 4: Update HITL Gate Nodes (45 min)

**File**: `app/graph/nodes.py`

Update each HITL gate node to:
1. Call `HITLService.pause_at_gate()`
2. Store current output in `hitl_gate_outputs`
3. Update `current_hitl_gate` in state
4. Return state that triggers workflow pause

Each gate node pattern:
```
async def hitl_<gate>_gate_node(state):
    # Get current output to present to user
    # Update workflow status to awaiting_<gate>_approval
    # Store output for review
    # Return state update with current_hitl_gate set
```

#### Step 5: Add Regeneration Routing (45 min)

**File**: `app/graph/workflow.py`

- Modify conditional edges to support regeneration
- Add routing functions that check if regeneration was requested
- Each gate can route back to its predecessor agent
- Handle feedback passing to agents for regeneration context

#### Step 6: Update Agents for Feedback Context (1 hour)

**Files**: `app/agents/*.py`

Update agents to:
- Check for HITL feedback in state
- Use feedback to modify prompts/behavior on regeneration
- Clear feedback after processing
- Log regeneration attempts

For example, Script Writer should:
- Check `state.hitl_feedback` for script-related feedback
- Incorporate feedback into prompt: "Previous attempt feedback: {feedback}"
- Generate new script accordingly

#### Step 7: Update Exports (15 min)

**Files**: 
- `app/models/__init__.py` - Add HITL model exports
- `app/services/__init__.py` - Add HITLService exports
- `app/api/routes/__init__.py` - Add HITL router

#### Step 8: Create Unit Tests (45 min)

**File**: `tests/test_services/test_hitl_service.py`

Test cases:
- `test_pause_at_gate_updates_status`
- `test_process_approve_clears_gate`
- `test_process_edit_applies_changes`
- `test_process_regenerate_increments_count`
- `test_regeneration_limit_enforced`
- `test_add_image_at_gate_4`
- `test_invalid_action_for_gate`

**File**: `tests/test_api/test_hitl_endpoints.py`

Test cases:
- `test_submit_feedback_approve`
- `test_submit_feedback_regenerate`
- `test_get_gate_status`
- `test_max_regenerations_error`

---

## Phase 4.2: Multi-Segment Video Generation

### 4.2.1 Objectives

Complete the video extension implementation to generate seamless videos longer than 8 seconds using Veo 3.1's video extension feature.

### 4.2.2 Current State Analysis

**Already Implemented** (in Phase 3.2):
- `VeoService` with `generate_video()` and `extend_video()` methods
- `VideoGeneratorAgent` with segment planning logic
- Basic multi-segment video generation flow

**Needs Enhancement**:
- Frame extraction from previous segment
- Seamless audio continuity
- Segment stitching/verification
- Error handling for extension failures

### 4.2.3 Veo 3.1 Extension Constraints

**From veo_doc.md**:

| Constraint | Value |
|------------|-------|
| Extension resolution | 720p only (even if initial is 1080p) |
| Extension duration | 4, 6, or 8 seconds per extension |
| Audio continuity | Voice must be in last 1 second to extend effectively |
| Max chain length | ~148 seconds (18+ extensions) |

### 4.2.4 Architecture Design

#### 4.2.4.1 Extension Strategy

```
VIDEO EXTENSION FLOW (for 18s video)
════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│ SEGMENT 1 (Initial Generation)                                      │
│ ├── Resolution: 720p (or 1080p, will downgrade on extension)       │
│ ├── Duration: 8s                                                    │
│ ├── Reference Images: 3 max                                         │
│ ├── Prompt: Full scene description with audio cues                  │
│ └── Output: video_1.mp4 (with audio)                                │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SEGMENT 2 (Video Extension)                                         │
│ ├── Input: video_1.mp4 (as base video)                              │
│ ├── Resolution: 720p (extension constraint)                         │
│ ├── Duration: 8s                                                    │
│ ├── Prompt: Continuation prompt for next scene                      │
│ └── Output: video_1_extended.mp4 (16s total, seamless)              │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SEGMENT 3 (Video Extension)                                         │
│ ├── Input: video_1_extended.mp4 (as base video)                     │
│ ├── Resolution: 720p                                                │
│ ├── Duration: 2s (remaining: 18 - 16 = 2, rounds to 4s min)         │
│ ├── Prompt: Final segment with CTA                                  │
│ └── Output: final_video.mp4 (18-20s total, seamless)                │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Veo 3.1 extension automatically creates seamless video - no manual stitching needed!

#### 4.2.4.2 Updates to VeoService

**File**: `app/services/veo.py`

Enhance `extend_video()` method:
- Accept video bytes or video object from previous generation
- Build continuation prompt from script segment
- Handle audio continuity by ensuring dialogue in last second
- Return the extended video (which is seamless)

Add `generate_multi_segment_video()` method:
- Orchestrate full multi-segment generation
- Handle errors gracefully (retry individual segments)
- Track segment metadata for debugging

#### 4.2.4.3 Updates to VideoGeneratorAgent

**File**: `app/agents/video_generator.py`

Enhance the agent to:
1. Generate initial segment at requested resolution
2. For extensions, download previous video result
3. Pass video to `extend_video()` with continuation prompt
4. Continue until requested duration reached
5. Return final extended video URL

#### 4.2.4.4 Continuation Prompt Strategy

For seamless extensions, continuation prompts should:
- Reference the action from previous segment's end
- Describe the next scene naturally
- Include audio cues for dialogue continuation
- NOT repeat style/character descriptions (already in video)

Example continuation prompt:
```
Continue the scene. The character finishes their thought and 
transitions to explaining the second concept. Camera slowly 
zooms out to reveal more context. Dialogue: "[next script lines]"
```

**Reference**: veo_doc.md "Prompting for extension"

### 4.2.5 Implementation Steps

#### Step 1: Enhance VeoService extend_video (45 min)

**File**: `app/services/veo.py`

- Update `extend_video()` to accept video bytes
- Add proper video download if needed
- Ensure extension uses 720p (constraint)
- Add logging for extension debugging
- Handle extension-specific errors

#### Step 2: Implement Continuation Prompt Builder (30 min)

**File**: `app/agents/video_generator.py`

Create `build_continuation_prompt()` function:
- Takes segment index and script
- References previous action
- Includes next dialogue lines
- Optimized for seamless transition

#### Step 3: Update Video Generation Flow (1 hour)

**File**: `app/agents/video_generator.py`

Update `VideoGeneratorAgent.run()` to:
1. Check if duration > 8s → multi-segment mode
2. Generate initial segment with full prompt + reference images
3. For each extension:
   - Download previous video result
   - Build continuation prompt
   - Call `extend_video()`
   - Track cumulative duration
4. Return final extended video

#### Step 4: Add Audio Continuity Handling (30 min)

**File**: `app/agents/video_generator.py`

- Ensure script segments have dialogue ending that continues
- Add audio cue hints in prompts
- Handle cases where audio doesn't extend well (retry logic)

#### Step 5: Error Handling for Extensions (30 min)

**File**: `app/services/veo.py`

Add robust error handling:
- Extension timeout → retry with shorter duration
- Extension failure → try regenerating previous segment
- Audio sync issues → flag for manual review
- Track which segments succeeded for partial recovery

#### Step 6: Test Multi-Segment Generation (45 min)

**File**: `tests/test_agents/test_video_generator.py`

Add test cases:
- `test_generate_18s_video_3_segments`
- `test_generate_25s_video_4_segments`
- `test_continuation_prompt_building`
- `test_extension_resolution_constraint`
- `test_extension_failure_handling`

---

## Combined Data Flow

```
HITL + MULTI-SEGMENT COMBINED FLOW
═══════════════════════════════════

User Input (manual mode, 18s video)
         │
         ▼
┌────────────────────┐
│ Intent/Tool Select │
└─────────┬──────────┘
          │
          ▼
    [HITL GATE 1] ◄── User: APPROVE / EDIT / REGENERATE (max 3)
          │
          ▼
┌────────────────────┐
│   Deep Research    │
└─────────┬──────────┘
          │
          ▼
    [HITL GATE 2] ◄── User: APPROVE / EDIT / REGENERATE
          │
          ▼
┌────────────────────┐
│  Script Generator  │
└─────────┬──────────┘
          │
          ▼
    [HITL GATE 3] ◄── User: APPROVE / EDIT script / REGENERATE
          │
          ▼
┌────────────────────┐
│  Image Generator   │
│  (1-3 images for   │
│   Veo reference)   │
└─────────┬──────────┘
          │
          ▼
    [HITL GATE 4] ◄── User: APPROVE / ADD_IMAGE / REGENERATE
          │
          ▼
┌────────────────────────────────────────────────┐
│              Video Generator                    │
│  ┌─────────────────────────────────────────┐   │
│  │ Segment 1: 8s initial (with ref images) │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                           │
│  ┌─────────────────▼───────────────────────┐   │
│  │ Segment 2: 8s extension (seamless)      │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                           │
│  ┌─────────────────▼───────────────────────┐   │
│  │ Segment 3: 2-4s extension (final)       │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────┬──────────────────────────┘
                      │
                      ▼
    [HITL GATE 5] ◄── User: APPROVE / REGENERATE final video
                      │
                      ▼
            ┌─────────────────┐
            │ Output Processor│
            └─────────────────┘
```

---

## Error Handling Strategy

### HITL Errors

| Error | Handling |
|-------|----------|
| Max regenerations exceeded | Return 400 with message, suggest manual edit |
| Workflow not at expected gate | Return 409 Conflict |
| Invalid action for gate | Return 400 with allowed actions |
| Feedback processing failure | Log error, maintain gate status |

### Multi-Segment Errors

| Error | Handling |
|-------|----------|
| Extension timeout | Retry with 4s duration instead of 8s |
| Extension failed | Regenerate previous segment, retry extension |
| Audio discontinuity | Flag in metadata, continue (not blocking) |
| Video download failed | Retry download, use cached if available |

---

## Testing Strategy

### Phase 4.1 Tests

| Test Type | Scope |
|-----------|-------|
| Unit | HITLService methods, feedback processing |
| Integration | API endpoints with mock service |
| E2E | Full manual mode workflow with HITL pauses |

### Phase 4.2 Tests

| Test Type | Scope |
|-----------|-------|
| Unit | Continuation prompt building, segment planning |
| Integration | VeoService multi-segment generation |
| E2E | Generate 18s and 25s videos end-to-end |

---

## Implementation Order

| Step | Phase | Task | Est. Time |
|------|-------|------|-----------|
| 1 | 4.1 | Create HITL models | 30 min |
| 2 | 4.1 | Create HITLService | 1 hour |
| 3 | 4.1 | Create HITL API endpoints | 45 min |
| 4 | 4.1 | Update HITL gate nodes | 45 min |
| 5 | 4.1 | Add regeneration routing | 45 min |
| 6 | 4.1 | Update agents for feedback | 1 hour |
| 7 | 4.1 | Update exports | 15 min |
| 8 | 4.1 | HITL unit tests | 45 min |
| 9 | 4.2 | Enhance VeoService extend_video | 45 min |
| 10 | 4.2 | Implement continuation prompts | 30 min |
| 11 | 4.2 | Update video generation flow | 1 hour |
| 12 | 4.2 | Audio continuity handling | 30 min |
| 13 | 4.2 | Extension error handling | 30 min |
| 14 | 4.2 | Multi-segment tests | 45 min |

**Total Estimated Time**: ~9 hours

---

## Success Criteria

### Phase 4.1 (HITL)

- [ ] Manual mode pauses at all 5 gates
- [ ] APPROVE action continues workflow
- [ ] EDIT action applies changes correctly
- [ ] REGENERATE calls agent with feedback context
- [ ] Max 3 regenerations enforced per gate
- [ ] All feedback persisted to database
- [ ] API endpoints return correct status codes

### Phase 4.2 (Multi-Segment)

- [ ] 18s video generates as 3 seamless segments
- [ ] 25s video generates as 4 seamless segments
- [ ] No visible cuts between segments
- [ ] Audio continues across segments
- [ ] Extension failures handled gracefully
- [ ] Resolution constraint (720p) enforced for extensions

---

## Files Summary

### New Files

| File | Purpose |
|------|---------|
| `app/models/hitl.py` | HITL models and enums |
| `app/services/hitl_service.py` | HITL business logic |
| `app/api/routes/hitl.py` | HITL API endpoints |
| `tests/test_services/test_hitl_service.py` | HITL service tests |
| `tests/test_api/test_hitl_endpoints.py` | HITL API tests |

### Modified Files

| File | Changes |
|------|---------|
| `app/graph/nodes.py` | Expand HITL gate node implementations |
| `app/graph/workflow.py` | Add regeneration routing edges |
| `app/graph/state.py` | Add HITL-related state fields |
| `app/services/veo.py` | Enhance extend_video, add multi-segment |
| `app/agents/video_generator.py` | Multi-segment orchestration, continuation prompts |
| `app/models/__init__.py` | Export HITL models |
| `app/services/__init__.py` | Export HITLService |
| `app/api/routes/__init__.py` | Include HITL router |
| `tests/test_agents/test_video_generator.py` | Multi-segment tests |

---

## Open Questions

1. **Webhook Notifications**: Should we add webhook support to notify users when a gate is reached? (Not in initial scope but could be added)

2. **Gate Timeout**: Should gates auto-expire after a period? (e.g., 24 hours with no action)

3. **Partial Regeneration**: At Gate 4 (images), should users be able to regenerate just one image?

---

## Dependencies

- Phase 3.2 (Video Generator) must be complete ✅
- Phase 3.3 (Output Processing) must be complete ✅
- Existing HITL gate placeholders in workflow.py ✅
- VeoService with extend_video capability ✅

---

## Appendix A: HITL Feedback Request/Response Examples

### Approve Tool Selection (Gate 1)
```json
// POST /api/v1/workflows/{id}/feedback
{
  "action": "approve"
}

// Response
{
  "workflow_id": "abc-123",
  "gate": "tool_selection",
  "action_taken": "approve",
  "next_step": "deep_research"
}
```

### Regenerate Script with Feedback (Gate 3)
```json
// POST /api/v1/workflows/{id}/feedback
{
  "action": "regenerate",
  "feedback": "Make the hook more dramatic and add a surprising twist at the end"
}

// Response
{
  "workflow_id": "abc-123",
  "gate": "script",
  "action_taken": "regenerate",
  "regeneration_count": 1,
  "max_regenerations": 3
}
```

### Edit Script Directly (Gate 3)
```json
// POST /api/v1/workflows/{id}/feedback
{
  "action": "edit",
  "edited_content": {
    "hook": {
      "script": "You've been lied to about black holes your entire life...",
      "duration_seconds": 2.0
    }
  }
}

// Response
{
  "workflow_id": "abc-123",
  "gate": "script",
  "action_taken": "edit",
  "next_step": "image_generator"
}
```

### Add Image at Gate 4
```json
// POST /api/v1/workflows/{id}/feedback
{
  "action": "add_image",
  "additional_images": ["https://user-uploaded.com/my-image.png"]
}

// Response
{
  "workflow_id": "abc-123",
  "gate": "images",
  "action_taken": "add_image",
  "total_images": 4,
  "next_step": "video_generator"
}
```
