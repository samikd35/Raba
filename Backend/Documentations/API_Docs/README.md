# RABA API Documentation

## Overview

RABA (AI-Powered Multi-Agent YouTube Shorts Generator) provides a comprehensive REST API for generating viral YouTube Shorts (8-25 seconds) using a multi-agent pipeline.

**Base URL:** `http://localhost:8000`  
**API Version:** `v1`  
**API Prefix:** `/api/v1`

---

## Documentation Files

| File | Description |
|------|-------------|
| [Video Generation](./01_VIDEO_GENERATION.md) | Workflow creation, status, and management |
| [HITL (Human-in-the-Loop)](./02_HITL.md) | Manual approval gates and feedback submission |
| [Tools](./03_TOOLS.md) | Tool repository CRUD and execution |
| [Monitoring](./04_MONITORING.md) | Usage metrics and cost tracking |
| [Health & System](./05_HEALTH.md) | Health checks and system info |

---

## Quick Reference

### Authentication
Currently, no authentication is required (development mode). Production will use API keys.

### Rate Limits
| Endpoint | Limit |
|----------|-------|
| `/api/v1/generate` | 5 requests/minute |
| `/api/v1/workflows` | 60 requests/minute |
| `/api/v1/tools` | 60 requests/minute |

### Common Response Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (successful deletion) |
| `400` | Bad Request - Invalid input |
| `404` | Not Found |
| `409` | Conflict - Resource state conflict |
| `422` | Validation Error |
| `429` | Too Many Requests - Rate limited |
| `500` | Internal Server Error |
| `503` | Service Unavailable |

---

## Workflow States

```
pending → running → [HITL gates if manual] → completed
                                           → failed
```

### Status Values
| Status | Description |
|--------|-------------|
| `pending` | Workflow created, not yet started |
| `running` | Workflow in progress |
| `awaiting_tool_approval` | HITL: Waiting for tool selection approval |
| `awaiting_research_approval` | HITL: Waiting for research approval |
| `awaiting_script_approval` | HITL: Waiting for script approval |
| `awaiting_image_approval` | HITL: Waiting for image approval |
| `awaiting_video_approval` | HITL: Waiting for video approval |
| `completed` | Successfully completed |
| `failed` | Failed with error |

---

## Common Enums

### Category (Visual Style)
```json
["auto", "surreal_realism", "high_octane_anime", "stylized_3d"]
```

### HITL Mode
```json
["auto", "manual"]
```

### Aspect Ratio
```json
["9:16", "16:9"]
```

### Resolution
```json
["720p", "1080p"]
```

---

## Error Response Format

All errors follow this structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Error message",
      "type": "error_type"
    }
  ]
}
```

---

## Interactive Documentation

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`
