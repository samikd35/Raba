# HITL (Human-in-the-Loop) API

Endpoints for manual approval gates and user feedback in video generation workflows.

**Tag:** `video-generation`

---

## Overview

When a workflow is created with `hitl_mode: "manual"`, it pauses at 5 gates for user review:

| Gate | Agent | What User Reviews |
|------|-------|-------------------|
| `tool_selection` | Intent/Tool Selector | Selected visual style tool |
| `research` | Deep Research | Gathered facts and sources |
| `script` | Script Writer | Generated script structure |
| `images` | Image Generator | Generated keyframe images |
| `video` | Video Producer | Final video output |

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflows/{workflow_id}/feedback` | Submit HITL feedback |
| `GET` | `/api/v1/workflows/{workflow_id}/gate` | Get current gate status |
| `GET` | `/api/v1/workflows/{workflow_id}/gate/{gate_name}/output` | Get gate output for review |

---

## POST /api/v1/workflows/{workflow_id}/feedback

Submit user feedback at the current HITL gate.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow identifier |

### Request

**Content-Type:** `application/json`

```json
{
  "action": "approve | edit | regenerate | add_image",
  "feedback": "string (optional, for regenerate)",
  "edited_content": { ... },
  "additional_images": ["url1", "url2"]
}
```

### Actions

| Action | Description | Valid Gates |
|--------|-------------|-------------|
| `approve` | Accept output, continue to next step | All |
| `edit` | Apply direct edits to content | tool_selection, research, script, images |
| `regenerate` | Re-run agent with feedback (max 3 attempts) | All |
| `add_image` | Add user reference images | images only |

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | enum | ✅ | Action to take |
| `feedback` | string | ❌ | Feedback text for regeneration |
| `edited_content` | object | ❌ | Direct edits to apply |
| `additional_images` | array | ❌ | Image URLs to add (images gate only) |

### Response

**Status:** `200 OK`

```json
{
  "workflow_id": "wf_abc123def456",
  "gate": "script",
  "action_taken": "regenerate",
  "next_step": null,
  "regeneration_count": 1,
  "max_regenerations": 3,
  "message": "Regenerating script with your feedback"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Workflow identifier |
| `gate` | enum | Gate that was processed |
| `action_taken` | enum | Action that was applied |
| `next_step` | string\|null | Next workflow node |
| `regeneration_count` | integer | Current regeneration count |
| `max_regenerations` | integer | Maximum allowed (always 3) |
| `message` | string | Status message |

### Examples

**Approve current output:**
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/wf_abc123/feedback" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

**Regenerate with feedback:**
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/wf_abc123/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "regenerate",
    "feedback": "Make the hook more dramatic and attention-grabbing"
  }'
```

**Edit script directly:**
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/wf_abc123/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "edit",
    "edited_content": {
      "hook": {
        "script": "You wont BELIEVE what happens next..."
      }
    }
  }'
```

**Add reference images:**
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/wf_abc123/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_image",
    "additional_images": [
      "https://example.com/reference1.png",
      "https://example.com/reference2.png"
    ]
  }'
```

### Errors

| Code | Condition |
|------|-----------|
| `400` | Workflow not in manual mode |
| `400` | Invalid action for current gate |
| `400` | Max regenerations (3) exceeded |
| `409` | Workflow not at expected gate |
| `500` | Internal service error |

---

## GET /api/v1/workflows/{workflow_id}/gate

Get the current HITL gate status for a workflow.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow identifier |

### Response

**Status:** `200 OK`

```json
{
  "workflow_id": "wf_abc123def456",
  "current_gate": "script",
  "gate_info": {
    "gate": "script",
    "status": "awaiting",
    "current_output": {
      "hook": { "script": "...", "duration": 3 },
      "body": [{ "script": "...", "duration": 12 }],
      "cta": { "script": "...", "duration": 2 }
    },
    "regeneration_count": 0,
    "feedback_history": [],
    "awaiting_since": "2026-01-15T10:03:00Z"
  },
  "hitl_mode": "manual",
  "workflow_status": "awaiting_script_approval",
  "approved_gates": ["tool_selection", "research"]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Workflow identifier |
| `current_gate` | enum\|null | Currently active gate (null if not paused) |
| `gate_info` | object\|null | Detailed info about current gate |
| `hitl_mode` | string | HITL mode (`auto` or `manual`) |
| `workflow_status` | string | Current workflow status |
| `approved_gates` | array | List of already approved gates |

### Gate Info Object

| Field | Type | Description |
|-------|------|-------------|
| `gate` | enum | Gate identifier |
| `status` | enum | `pending`, `awaiting`, `approved`, `regenerating` |
| `current_output` | object | Output from agent being reviewed |
| `regeneration_count` | integer | Regeneration attempts used (0-3) |
| `feedback_history` | array | History of feedback for this gate |
| `awaiting_since` | datetime | When gate started awaiting |

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/workflows/wf_abc123/gate"
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Workflow not found |

---

## GET /api/v1/workflows/{workflow_id}/gate/{gate_name}/output

Get the agent output at a specific gate for detailed review.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow identifier |
| `gate_name` | enum | Gate name |

### Valid Gate Names
- `tool_selection`
- `research`
- `script`
- `images`
- `video`

### Response

**Status:** `200 OK`

```json
{
  "workflow_id": "wf_abc123def456",
  "gate": "script",
  "output": {
    "hook": {
      "script": "You won't believe what scientists just discovered...",
      "duration": 3,
      "visual_direction": "Dramatic zoom on cosmic imagery"
    },
    "body": [
      {
        "script": "Black holes don't just absorb light...",
        "duration": 6,
        "visual_direction": "Particle simulation of light bending"
      },
      {
        "script": "They literally bend time itself.",
        "duration": 6,
        "visual_direction": "Clock distortion effect near event horizon"
      }
    ],
    "cta": {
      "script": "Follow for more mind-blowing science!",
      "duration": 3,
      "visual_direction": "Subscribe button animation"
    },
    "total_duration": 18,
    "word_count": 52
  },
  "output_type": "script",
  "regeneration_count": 0,
  "can_regenerate": true,
  "valid_actions": ["approve", "edit", "regenerate"]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Workflow identifier |
| `gate` | enum | Gate identifier |
| `output` | object | Agent output to review (varies by gate) |
| `output_type` | string | Type: `tool_selection`, `research`, `script`, `images`, `video` |
| `regeneration_count` | integer | Regeneration attempts used |
| `can_regenerate` | boolean | Whether regeneration is still allowed |
| `valid_actions` | array | Actions valid for this gate |

### Output Structures by Gate

#### Tool Selection Output
```json
{
  "tool_id": "cosmic_flow_visualizer",
  "tool_name": "Cosmic Flow Visualizer",
  "category": "surreal_realism",
  "description": "Visualizes cosmic phenomena...",
  "confidence": 0.92,
  "reasoning": "Topic involves space visualization..."
}
```

#### Research Output
```json
{
  "facts": [
    "Black holes warp spacetime according to Einstein's theory",
    "Light cannot escape once past the event horizon",
    "Time dilation increases near the event horizon"
  ],
  "sources": ["NASA", "ESA", "Nature Journal"],
  "key_insights": "The dramatic visual potential lies in...",
  "viral_angle": "The mind-bending nature of time dilation..."
}
```

#### Script Output
```json
{
  "hook": { "script": "...", "duration": 3, "visual_direction": "..." },
  "body": [{ "script": "...", "duration": 6, "visual_direction": "..." }],
  "cta": { "script": "...", "duration": 2, "visual_direction": "..." },
  "total_duration": 18,
  "word_count": 52
}
```

#### Images Output
```json
{
  "image_urls": [
    "https://storage.example.com/keyframe_1.png",
    "https://storage.example.com/keyframe_2.png",
    "https://storage.example.com/keyframe_3.png"
  ],
  "prompts_used": [
    "A photorealistic black hole with accretion disk...",
    "Light bending around event horizon..."
  ]
}
```

#### Video Output
```json
{
  "video_url": "https://storage.example.com/final_video.mp4",
  "duration_seconds": 18,
  "resolution": "1080p",
  "thumbnail_url": "https://storage.example.com/thumbnail.jpg"
}
```

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/workflows/wf_abc123/gate/script/output"
```

### Errors

| Code | Condition |
|------|-----------|
| `400` | Invalid gate name |
| `404` | Workflow or gate output not found |

---

## Frontend Integration Guide

### HITL Workflow Handler

```javascript
class HITLWorkflowHandler {
  constructor(workflowId) {
    this.workflowId = workflowId;
    this.baseUrl = '/api/v1/workflows';
  }

  // Check current gate status
  async getGateStatus() {
    const res = await fetch(`${this.baseUrl}/${this.workflowId}/gate`);
    return res.json();
  }

  // Get output for review
  async getGateOutput(gateName) {
    const res = await fetch(
      `${this.baseUrl}/${this.workflowId}/gate/${gateName}/output`
    );
    return res.json();
  }

  // Submit feedback
  async submitFeedback(action, options = {}) {
    const res = await fetch(`${this.baseUrl}/${this.workflowId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...options })
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail);
    }
    
    return res.json();
  }

  // Convenience methods
  async approve() {
    return this.submitFeedback('approve');
  }

  async regenerate(feedback) {
    return this.submitFeedback('regenerate', { feedback });
  }

  async edit(editedContent) {
    return this.submitFeedback('edit', { edited_content: editedContent });
  }

  async addImages(imageUrls) {
    return this.submitFeedback('add_image', { additional_images: imageUrls });
  }
}

// Usage
const handler = new HITLWorkflowHandler('wf_abc123');

// Check if waiting for approval
const status = await handler.getGateStatus();
if (status.current_gate) {
  console.log(`Waiting at: ${status.current_gate}`);
  
  // Get output to display to user
  const output = await handler.getGateOutput(status.current_gate);
  displayForReview(output);
}

// After user reviews, submit feedback
await handler.approve();
// or
await handler.regenerate('Make it more dramatic');
```

### Polling for HITL Gates

```javascript
async function pollForHITLGate(workflowId, onGateReached) {
  const handler = new HITLWorkflowHandler(workflowId);
  
  const poll = async () => {
    const status = await handler.getGateStatus();
    
    if (status.current_gate) {
      const output = await handler.getGateOutput(status.current_gate);
      await onGateReached(status.current_gate, output);
    } else if (status.workflow_status === 'completed') {
      return { completed: true };
    } else if (status.workflow_status === 'failed') {
      return { failed: true };
    } else {
      // Still processing, poll again
      await new Promise(r => setTimeout(r, 3000));
      return poll();
    }
  };
  
  return poll();
}

// Usage
await pollForHITLGate('wf_abc123', async (gate, output) => {
  console.log(`Review needed at ${gate}`);
  
  // Show UI for review
  const userAction = await showReviewModal(gate, output);
  
  const handler = new HITLWorkflowHandler('wf_abc123');
  await handler.submitFeedback(userAction.action, userAction.options);
});
```

### Script Editor Component Example

```javascript
// React component for editing script at HITL gate
function ScriptEditor({ workflowId, scriptOutput, onComplete }) {
  const [script, setScript] = useState(scriptOutput);
  const [loading, setLoading] = useState(false);
  
  const handleApprove = async () => {
    setLoading(true);
    await fetch(`/api/v1/workflows/${workflowId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'approve' })
    });
    onComplete();
  };
  
  const handleEdit = async () => {
    setLoading(true);
    await fetch(`/api/v1/workflows/${workflowId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'edit',
        edited_content: script
      })
    });
    onComplete();
  };
  
  const handleRegenerate = async (feedback) => {
    setLoading(true);
    await fetch(`/api/v1/workflows/${workflowId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'regenerate',
        feedback
      })
    });
    onComplete();
  };
  
  // Render editor UI...
}
```
