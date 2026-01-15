# Monitoring API

Endpoints for viewing token usage, cost metrics, and pricing information.

**Tag:** `monitoring`

---

## Overview

The monitoring API provides insights into:
- **Token usage** across all LLM calls
- **Cost breakdown** by generation type and model
- **Per-video metrics** for detailed analysis
- **Current pricing** information

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/monitoring/summary` | Get usage summary |
| `GET` | `/api/v1/monitoring/video/{video_id}` | Get video-specific usage |
| `GET` | `/api/v1/monitoring/pricing` | Get current pricing |

---

## GET /api/v1/monitoring/summary

Get aggregated token usage and cost summary for a time period.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | `7` | Number of days to include (1-90) |

### Response

**Status:** `200 OK`

```json
{
  "period": {
    "start": "2026-01-08T00:00:00Z",
    "end": "2026-01-15T14:30:00Z",
    "days": 7
  },
  "totals": {
    "total_tokens": 2450000,
    "total_cost_usd": 45.67,
    "total_videos": 23,
    "completed_videos": 20,
    "failed_videos": 3
  },
  "by_generation_type": {
    "text": {
      "tokens": 850000,
      "cost_usd": 8.50,
      "count": 46
    },
    "image": {
      "tokens": 120000,
      "cost_usd": 12.40,
      "count": 92
    },
    "video": {
      "tokens": 0,
      "cost_usd": 18.50,
      "count": 20
    },
    "research": {
      "tokens": 480000,
      "cost_usd": 6.27,
      "count": 23
    }
  },
  "by_model": {
    "gemini-2.5-flash": {
      "tokens": 650000,
      "cost_usd": 4.55,
      "calls": 89
    },
    "gemini-2.5-pro": {
      "tokens": 200000,
      "cost_usd": 4.00,
      "calls": 23
    },
    "gemini-3-flash-preview": {
      "tokens": 480000,
      "cost_usd": 7.20,
      "calls": 46
    },
    "nano-banana-pro": {
      "tokens": 120000,
      "cost_usd": 12.40,
      "calls": 92
    },
    "veo-3.1": {
      "tokens": 0,
      "cost_usd": 18.50,
      "calls": 20
    }
  },
  "metrics": {
    "success_rate": 0.87,
    "cache_hit_rate": 0.34,
    "avg_generation_time_seconds": 285.5,
    "avg_cost_per_video_usd": 1.98
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `period` | object | Time period covered |
| `totals` | object | Aggregate totals |
| `by_generation_type` | object | Breakdown by type (text/image/video/research) |
| `by_model` | object | Breakdown by LLM model |
| `metrics` | object | Performance metrics |

### Totals Object

| Field | Type | Description |
|-------|------|-------------|
| `total_tokens` | integer | Total tokens consumed |
| `total_cost_usd` | float | Total cost in USD |
| `total_videos` | integer | Total workflows created |
| `completed_videos` | integer | Successfully completed |
| `failed_videos` | integer | Failed workflows |

### Metrics Object

| Field | Type | Description |
|-------|------|-------------|
| `success_rate` | float | Completion rate (0-1) |
| `cache_hit_rate` | float | Cache hit ratio (0-1) |
| `avg_generation_time_seconds` | float | Average generation time |
| `avg_cost_per_video_usd` | float | Average cost per video |

### Example

```bash
# Get last 30 days summary
curl -X GET "http://localhost:8000/api/v1/monitoring/summary?days=30"

# Get last 7 days (default)
curl -X GET "http://localhost:8000/api/v1/monitoring/summary"
```

---

## GET /api/v1/monitoring/video/{video_id}

Get detailed usage metrics for a specific video/workflow.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `video_id` | string | Workflow/video ID |

### Response

**Status:** `200 OK`

```json
{
  "video_id": "wf_abc123def456",
  "status": "completed",
  "created_at": "2026-01-15T10:00:00Z",
  "completed_at": "2026-01-15T10:05:30Z",
  "total_cost_usd": 2.34,
  "total_tokens": 125000,
  "generation_time_seconds": 330.5,
  "steps": [
    {
      "step": "intent_tool_selection",
      "model": "gemini-2.5-flash",
      "tokens_in": 1200,
      "tokens_out": 450,
      "cost_usd": 0.012,
      "duration_seconds": 2.3,
      "cached": false
    },
    {
      "step": "deep_research",
      "model": "gemini-2.5-pro",
      "tokens_in": 8500,
      "tokens_out": 3200,
      "cost_usd": 0.234,
      "duration_seconds": 15.7,
      "cached": false
    },
    {
      "step": "script_generation",
      "model": "gemini-3-flash-preview",
      "tokens_in": 4200,
      "tokens_out": 1800,
      "cost_usd": 0.090,
      "duration_seconds": 8.2,
      "cached": false
    },
    {
      "step": "image_generation",
      "model": "nano-banana-pro",
      "tokens_in": 2400,
      "tokens_out": 0,
      "cost_usd": 0.52,
      "duration_seconds": 45.0,
      "cached": false,
      "images_generated": 4
    },
    {
      "step": "video_generation",
      "model": "veo-3.1",
      "tokens_in": 0,
      "tokens_out": 0,
      "cost_usd": 1.48,
      "duration_seconds": 259.3,
      "cached": false,
      "video_duration_seconds": 18
    }
  ],
  "breakdown": {
    "text_cost_usd": 0.336,
    "image_cost_usd": 0.52,
    "video_cost_usd": 1.48,
    "research_cost_usd": 0.234
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | string | Workflow identifier |
| `status` | string | Workflow status |
| `created_at` | datetime | Creation time |
| `completed_at` | datetime | Completion time |
| `total_cost_usd` | float | Total cost |
| `total_tokens` | integer | Total tokens used |
| `generation_time_seconds` | float | Total generation time |
| `steps` | array | Per-step breakdown |
| `breakdown` | object | Cost by category |

### Step Object

| Field | Type | Description |
|-------|------|-------------|
| `step` | string | Step name |
| `model` | string | Model used |
| `tokens_in` | integer | Input tokens |
| `tokens_out` | integer | Output tokens |
| `cost_usd` | float | Step cost |
| `duration_seconds` | float | Step duration |
| `cached` | boolean | Whether result was cached |
| `images_generated` | integer | Images generated (image step only) |
| `video_duration_seconds` | integer | Video duration (video step only) |

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/video/wf_abc123def456"
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Video/workflow not found |

---

## GET /api/v1/monitoring/pricing

Get current pricing information for all models.

### Response

**Status:** `200 OK`

```json
{
  "pricing": {
    "gemini-2.5-flash": {
      "input_per_million": 0.075,
      "output_per_million": 0.30
    },
    "gemini-2.5-pro": {
      "input_per_million": 1.25,
      "output_per_million": 5.00
    },
    "gemini-3-flash-preview": {
      "input_per_million": 0.15,
      "output_per_million": 0.60
    },
    "nano-banana-pro": {
      "input_per_million": 0.10,
      "per_image": 0.10
    },
    "veo-3.1": {
      "per_second": 0.08
    },
    "research": {
      "per_query": 0.05
    }
  },
  "notes": {
    "text_models": "Prices are per million tokens",
    "image_models": "Includes per-image charge plus token cost",
    "video_models": "Price is per second of generated video",
    "research": "Flat rate per research query"
  },
  "currency": "USD",
  "last_updated": "2026-01-15"
}
```

### Pricing Structure

#### Text Models (per million tokens)

| Model | Input | Output |
|-------|-------|--------|
| gemini-2.5-flash | $0.075 | $0.30 |
| gemini-2.5-pro | $1.25 | $5.00 |
| gemini-3-flash-preview | $0.15 | $0.60 |

#### Image Models

| Model | Per Million Tokens | Per Image |
|-------|-------------------|-----------|
| nano-banana-pro | $0.10 | $0.10 |

#### Video Models

| Model | Per Second |
|-------|------------|
| veo-3.1 | $0.08 |

#### Other

| Service | Rate |
|---------|------|
| Research query | $0.05 per query |

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/pricing"
```

---

## Frontend Integration Guide

### Monitoring Dashboard Service

```javascript
class MonitoringService {
  constructor(baseUrl = '/api/v1/monitoring') {
    this.baseUrl = baseUrl;
  }

  // Get usage summary
  async getSummary(days = 7) {
    const res = await fetch(`${this.baseUrl}/summary?days=${days}`);
    return res.json();
  }

  // Get video usage
  async getVideoUsage(videoId) {
    const res = await fetch(`${this.baseUrl}/video/${videoId}`);
    return res.json();
  }

  // Get pricing
  async getPricing() {
    const res = await fetch(`${this.baseUrl}/pricing`);
    return res.json();
  }

  // Calculate estimated cost for a video
  calculateEstimatedCost(durationSeconds, pricing) {
    // Rough estimates based on typical usage
    const textCost = 0.05;  // ~50k tokens for text generation
    const imageCost = 0.40; // ~4 images
    const videoCost = durationSeconds * pricing.pricing['veo-3.1'].per_second;
    const researchCost = pricing.pricing.research.per_query;
    
    return {
      text: textCost,
      image: imageCost,
      video: videoCost,
      research: researchCost,
      total: textCost + imageCost + videoCost + researchCost
    };
  }
}

// Usage
const monitoring = new MonitoringService();

// Get 30-day summary
const summary = await monitoring.getSummary(30);
console.log(`Total cost: $${summary.totals.total_cost_usd}`);
console.log(`Success rate: ${(summary.metrics.success_rate * 100).toFixed(1)}%`);

// Get specific video usage
const videoUsage = await monitoring.getVideoUsage('wf_abc123');
console.log(`Video cost: $${videoUsage.total_cost_usd}`);
```

### Cost Dashboard Component

```javascript
// React component for displaying usage metrics
function CostDashboard() {
  const [summary, setSummary] = useState(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSummary() {
      setLoading(true);
      const monitoring = new MonitoringService();
      const data = await monitoring.getSummary(days);
      setSummary(data);
      setLoading(false);
    }
    loadSummary();
  }, [days]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="dashboard">
      <div className="period-selector">
        <select value={days} onChange={e => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="totals">
        <div className="metric">
          <span className="label">Total Cost</span>
          <span className="value">${summary.totals.total_cost_usd.toFixed(2)}</span>
        </div>
        <div className="metric">
          <span className="label">Videos Generated</span>
          <span className="value">{summary.totals.completed_videos}</span>
        </div>
        <div className="metric">
          <span className="label">Success Rate</span>
          <span className="value">{(summary.metrics.success_rate * 100).toFixed(1)}%</span>
        </div>
        <div className="metric">
          <span className="label">Avg Cost/Video</span>
          <span className="value">${summary.metrics.avg_cost_per_video_usd.toFixed(2)}</span>
        </div>
      </div>

      <div className="breakdown">
        <h3>Cost by Type</h3>
        <div className="chart">
          {Object.entries(summary.by_generation_type).map(([type, data]) => (
            <div key={type} className="bar">
              <span className="type">{type}</span>
              <div 
                className="fill"
                style={{ 
                  width: `${(data.cost_usd / summary.totals.total_cost_usd) * 100}%` 
                }}
              />
              <span className="cost">${data.cost_usd.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### Video Cost Breakdown Component

```javascript
function VideoCostBreakdown({ videoId }) {
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    async function loadUsage() {
      const monitoring = new MonitoringService();
      const data = await monitoring.getVideoUsage(videoId);
      setUsage(data);
    }
    loadUsage();
  }, [videoId]);

  if (!usage) return <div>Loading...</div>;

  return (
    <div className="video-cost-breakdown">
      <h3>Cost Breakdown for {videoId}</h3>
      
      <div className="summary">
        <p>Total Cost: <strong>${usage.total_cost_usd.toFixed(2)}</strong></p>
        <p>Generation Time: <strong>{usage.generation_time_seconds.toFixed(1)}s</strong></p>
      </div>

      <table className="steps-table">
        <thead>
          <tr>
            <th>Step</th>
            <th>Model</th>
            <th>Tokens</th>
            <th>Duration</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {usage.steps.map((step, i) => (
            <tr key={i}>
              <td>{step.step}</td>
              <td>{step.model}</td>
              <td>{step.tokens_in + step.tokens_out}</td>
              <td>{step.duration_seconds.toFixed(1)}s</td>
              <td>${step.cost_usd.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```
