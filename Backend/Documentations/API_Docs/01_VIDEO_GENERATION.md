# Video Generation API

Endpoints for creating and managing video generation workflows.

**Tag:** `video-generation`

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/generate` | Create workflow (JSON) |
| `POST` | `/api/v1/generate/with-image` | Create workflow with image upload |
| `GET` | `/api/v1/workflows/{workflow_id}` | Get workflow status |
| `GET` | `/api/v1/workflows` | List all workflows |
| `DELETE` | `/api/v1/workflows/{workflow_id}` | Delete workflow |

---

## POST /api/v1/generate

Create a new video generation workflow using JSON body.

### Rate Limit
`5 requests/minute`

### Request

**Content-Type:** `application/json`

```json
{
  "topic": "string (required, 3-500 chars)",
  "duration_seconds": 18,
  "aspect_ratio": "9:16",
  "resolution": "1080p",
  "category": "auto",
  "hitl_mode": "auto",
  "enable_audio": true,
  "enable_subtitles": false
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `topic` | string | ✅ | - | Video topic/subject (3-500 characters) |
| `duration_seconds` | integer | ❌ | `18` | Video duration (8-25 seconds) |
| `aspect_ratio` | enum | ❌ | `"9:16"` | Video aspect ratio (`"9:16"`, `"16:9"`) |
| `resolution` | enum | ❌ | `"1080p"` | Video resolution (`"720p"`, `"1080p"`) |
| `category` | enum | ❌ | `"auto"` | Visual style category |
| `hitl_mode` | enum | ❌ | `"auto"` | Human-in-the-loop mode (`"auto"`, `"manual"`) |
| `enable_audio` | boolean | ❌ | `true` | Generate audio with video |
| `enable_subtitles` | boolean | ❌ | `false` | Generate subtitles |

### Category Options

| Value | Description |
|-------|-------------|
| `auto` | AI selects best category |
| `surreal_realism` | Photorealistic with surreal elements |
| `high_octane_anime` | High-energy anime style |
| `stylized_3d` | Stylized 3D renders |

### Response

**Status:** `201 Created`

```json
{
  "workflow_id": "wf_abc123def456",
  "status": "pending",
  "message": "Workflow created successfully. Video generation will start shortly."
}
```

### Example

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "How black holes bend light and time",
    "duration_seconds": 20,
    "category": "surreal_realism",
    "hitl_mode": "manual"
  }'
```

**Response:**
```json
{
  "workflow_id": "wf_7f3a9c2b1d4e",
  "status": "pending",
  "message": "Workflow created successfully. Video generation will start shortly."
}
```

---

## POST /api/v1/generate/with-image

Create a workflow with an optional reference image upload.

### Rate Limit
`5 requests/minute`

### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic` | string | ✅ | Video topic (3-500 chars) |
| `duration_seconds` | integer | ❌ | Duration 8-25s (default: 18) |
| `aspect_ratio` | enum | ❌ | Aspect ratio (default: `9:16`) |
| `resolution` | enum | ❌ | Resolution (default: `1080p`) |
| `category` | enum | ❌ | Category (default: `auto`) |
| `hitl_mode` | enum | ❌ | HITL mode (default: `auto`) |
| `enable_audio` | boolean | ❌ | Generate audio (default: `true`) |
| `enable_subtitles` | boolean | ❌ | Generate subtitles (default: `false`) |
| `reference_image` | file | ❌ | Reference image (max 10MB) |

### Supported Image Formats
- `image/jpeg`
- `image/png`
- `image/webp`

### Response

**Status:** `201 Created`

```json
{
  "workflow_id": "wf_abc123def456",
  "status": "pending",
  "message": "Workflow created successfully. Video generation will start shortly."
}
```

### Example

```bash
curl -X POST "http://localhost:8000/api/v1/generate/with-image" \
  -F "topic=Cyberpunk city at night" \
  -F "duration_seconds=15" \
  -F "category=stylized_3d" \
  -F "reference_image=@./my_reference.jpg"
```

### Errors

| Code | Condition |
|------|-----------|
| `400` | Invalid file type (not jpg/png/webp) |
| `400` | File too large (>10MB) |

---

## GET /api/v1/workflows/{workflow_id}

Get the current status and outputs of a workflow.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow UUID |

### Response

**Status:** `200 OK`

```json
{
  "workflow_id": "wf_abc123def456",
  "status": "completed",
  "topic": "How black holes bend light and time",
  "duration_seconds": 20,
  "aspect_ratio": "9:16",
  "resolution": "1080p",
  "category": "surreal_realism",
  "hitl_mode": "auto",
  "current_hitl_gate": null,
  "tool_selection": {
    "tool_id": "cosmic_flow_visualizer",
    "tool_name": "Cosmic Flow Visualizer",
    "confidence": 0.92
  },
  "research_output": {
    "facts": ["Black holes warp spacetime...", "..."],
    "sources": ["NASA", "ESA"]
  },
  "script_output": {
    "hook": { "script": "You won't believe...", "duration": 3 },
    "body": [{ "script": "...", "duration": 12 }],
    "cta": { "script": "Follow for more!", "duration": 2 }
  },
  "generated_images": [
    "https://storage.example.com/images/img1.png",
    "https://storage.example.com/images/img2.png"
  ],
  "video_url": "https://storage.example.com/videos/final.mp4",
  "error": null,
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:05:30Z",
  "completed_at": "2026-01-15T10:05:30Z",
  "generation_time_seconds": 330.5
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Unique identifier |
| `status` | enum | Current workflow status |
| `topic` | string | Original topic |
| `duration_seconds` | integer | Requested duration |
| `aspect_ratio` | string | Video aspect ratio |
| `resolution` | string | Video resolution |
| `category` | string | Selected category |
| `hitl_mode` | string | HITL mode |
| `current_hitl_gate` | string\|null | Current HITL gate if paused |
| `tool_selection` | object\|null | Tool selection output |
| `research_output` | object\|null | Research agent output |
| `script_output` | object\|null | Script generation output |
| `generated_images` | array\|null | Generated image URLs |
| `video_url` | string\|null | Final video URL |
| `error` | string\|null | Error message if failed |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `completed_at` | datetime\|null | Completion timestamp |
| `generation_time_seconds` | float\|null | Total generation time |

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/workflows/wf_abc123def456"
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Workflow not found |
| `503` | Database unavailable |

---

## GET /api/v1/workflows

List all workflows with pagination and filtering.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `20` | Max results (1-100) |
| `offset` | integer | `0` | Number to skip |
| `status` | string | - | Filter by status |

### Response

**Status:** `200 OK`

```json
{
  "workflows": [
    {
      "workflow_id": "wf_abc123def456",
      "status": "completed",
      "topic": "How black holes bend light...",
      "category": "surreal_realism",
      "created_at": "2026-01-15T10:00:00Z",
      "completed_at": "2026-01-15T10:05:30Z",
      "generation_time_seconds": 330.5,
      "has_video": true
    },
    {
      "workflow_id": "wf_xyz789ghi012",
      "status": "running",
      "topic": "Ancient Roman engineering...",
      "category": "stylized_3d",
      "created_at": "2026-01-15T11:00:00Z",
      "completed_at": null,
      "generation_time_seconds": null,
      "has_video": false
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

### Example

```bash
# Get first 10 completed workflows
curl -X GET "http://localhost:8000/api/v1/workflows?limit=10&status=completed"

# Get page 2 of results
curl -X GET "http://localhost:8000/api/v1/workflows?limit=20&offset=20"
```

---

## DELETE /api/v1/workflows/{workflow_id}

Delete a workflow and its associated media.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workflow_id` | string | Workflow UUID to delete |

### Response

**Status:** `204 No Content`

No response body.

### Example

```bash
curl -X DELETE "http://localhost:8000/api/v1/workflows/wf_abc123def456"
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Workflow not found |
| `503` | Database unavailable |

---

## Frontend Integration Guide

### Creating a Video

```javascript
// 1. Create workflow
const response = await fetch('/api/v1/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: 'How photosynthesis works',
    duration_seconds: 18,
    hitl_mode: 'auto'
  })
});

const { workflow_id } = await response.json();

// 2. Poll for status
const pollStatus = async () => {
  const res = await fetch(`/api/v1/workflows/${workflow_id}`);
  const workflow = await res.json();
  
  if (workflow.status === 'completed') {
    return workflow.video_url;
  } else if (workflow.status === 'failed') {
    throw new Error(workflow.error);
  } else {
    // Poll again in 5 seconds
    await new Promise(r => setTimeout(r, 5000));
    return pollStatus();
  }
};

const videoUrl = await pollStatus();
```

### Creating with Image Upload

```javascript
const formData = new FormData();
formData.append('topic', 'Cyberpunk cityscape');
formData.append('duration_seconds', '15');
formData.append('reference_image', fileInput.files[0]);

const response = await fetch('/api/v1/generate/with-image', {
  method: 'POST',
  body: formData
});
```

### Pagination Helper

```javascript
async function* fetchAllWorkflows(status = null) {
  let offset = 0;
  const limit = 20;
  
  while (true) {
    const url = new URL('/api/v1/workflows', baseUrl);
    url.searchParams.set('limit', limit);
    url.searchParams.set('offset', offset);
    if (status) url.searchParams.set('status', status);
    
    const res = await fetch(url);
    const data = await res.json();
    
    for (const workflow of data.workflows) {
      yield workflow;
    }
    
    if (!data.has_more) break;
    offset += limit;
  }
}

// Usage
for await (const workflow of fetchAllWorkflows('completed')) {
  console.log(workflow.workflow_id);
}
```
