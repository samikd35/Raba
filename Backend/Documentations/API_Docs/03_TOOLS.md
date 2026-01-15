# Tools API

Full CRUD operations for video generation tools with AI-enhanced creation.

**Tag:** `tools`

---

## Overview

Tools define visual styles and prompt templates for video generation. Each tool contains:
- **Prompt templates** for script, image, and video generation
- **Capabilities** (e.g., flow visualization, anime style)
- **Parameters schema** for customization

Tools can be created from simple ideas - Gemini 2.5 Flash enhances them into full configurations.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/tools` | List all tools |
| `POST` | `/api/v1/tools` | Create new tool |
| `GET` | `/api/v1/tools/{tool_id}` | Get tool details |
| `PUT` | `/api/v1/tools/{tool_id}` | Update tool |
| `DELETE` | `/api/v1/tools/{tool_id}` | Delete tool (soft) |
| `POST` | `/api/v1/tools/preview` | Preview AI enhancement |
| `POST` | `/api/v1/tools/{tool_id}/improve` | Improve existing tool |
| `POST` | `/api/v1/tools/{tool_id}/execute` | Execute tool with topic |

---

## GET /api/v1/tools

List all tools with optional filters.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | - | Filter by category |
| `is_active` | boolean | `true` | Filter by active status |
| `limit` | integer | `50` | Page size (1-100) |
| `offset` | integer | `0` | Page offset |

### Category Values
- `surreal_realism`
- `high_octane_anime`
- `stylized_3d`

### Response

**Status:** `200 OK`

```json
{
  "tools": [
    {
      "id": "uuid-123",
      "tool_id": "cosmic_flow_visualizer",
      "tool_name": "Cosmic Flow Visualizer",
      "category": "surreal_realism",
      "description": "Visualizes cosmic phenomena with flowing particle effects...",
      "capabilities": {
        "flow_visualization": true,
        "invisible_forces": true,
        "photorealistic_grounding": true
      },
      "is_active": true,
      "priority": 100,
      "version": 2,
      "usage_count": 156,
      "success_rate": 0.94,
      "created_at": "2026-01-10T08:00:00Z",
      "updated_at": "2026-01-14T12:30:00Z"
    }
  ],
  "total": 12,
  "limit": 50,
  "offset": 0
}
```

### Example

```bash
# List all active tools in surreal_realism category
curl -X GET "http://localhost:8000/api/v1/tools?category=surreal_realism&is_active=true"
```

---

## POST /api/v1/tools

Create a new tool from a user idea. Gemini 2.5 Flash enhances the idea into a full tool configuration.

### Request

**Content-Type:** `application/json`

```json
{
  "tool_name": "Neon Cyberpunk Streets",
  "idea": "A tool for creating cyberpunk city scenes with neon lights, rain-slicked streets, holographic advertisements, and a noir atmosphere. Should work well for tech topics and futuristic concepts.",
  "category": "stylized_3d"
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | string | ✅ | Display name (3-100 chars) |
| `idea` | string | ✅ | Description of tool purpose (10-2000 chars) |
| `category` | enum | ❌ | Category hint (AI will classify if not provided) |

### Response

**Status:** `201 Created`

```json
{
  "id": "uuid-456",
  "tool_id": "neon_cyberpunk_streets",
  "tool_name": "Neon Cyberpunk Streets",
  "category": "stylized_3d",
  "description": "Creates immersive cyberpunk cityscapes with dramatic neon lighting, reflective wet surfaces, and holographic elements. Perfect for tech explainers, futuristic concepts, and noir-style narratives.",
  "capabilities": {
    "flow_visualization": false,
    "invisible_forces": false,
    "photorealistic_grounding": false,
    "miniature_worlds": false,
    "data_visualization": true,
    "viral_signal": "aesthetic_immersion"
  },
  "script_prompt_template": "Write a {duration}-second script about {topic} with a cyberpunk noir tone...",
  "image_prompt_template": "A cinematic cyberpunk street scene depicting {scene_description}...",
  "video_prompt_template": "Generate a {duration}-second video following this script: {script}...",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "neon_intensity": { "type": "number", "default": 0.8 },
      "rain_enabled": { "type": "boolean", "default": true }
    }
  },
  "original_idea": "A tool for creating cyberpunk city scenes...",
  "is_active": true,
  "priority": 0,
  "version": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "created_at": "2026-01-15T14:00:00Z",
  "updated_at": "2026-01-15T14:00:00Z"
}
```

### Example

```bash
curl -X POST "http://localhost:8000/api/v1/tools" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "Microscopic Universe",
    "idea": "Visualize microscopic worlds - cells, molecules, atoms - as if they were vast cosmic landscapes. Perfect for biology and chemistry topics."
  }'
```

---

## GET /api/v1/tools/{tool_id}

Get detailed information about a specific tool.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool_id` | string | Tool slug identifier (e.g., `cosmic_flow_visualizer`) |

### Response

**Status:** `200 OK`

Full `ToolResponse` object (see POST response above).

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/tools/cosmic_flow_visualizer"
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Tool not found |

---

## PUT /api/v1/tools/{tool_id}

Update an existing tool. All fields are optional.

> **Note:** If `idea` is changed, the tool will be re-enhanced by Gemini.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool_id` | string | Tool slug identifier |

### Request

**Content-Type:** `application/json`

```json
{
  "tool_name": "Updated Tool Name",
  "idea": "Updated idea (triggers re-enhancement)",
  "description": "Manual description override",
  "capabilities": { ... },
  "is_active": true,
  "script_prompt_template": "...",
  "image_prompt_template": "...",
  "video_prompt_template": "...",
  "priority": 50
}
```

### Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Updated display name |
| `idea` | string | Updated idea (triggers re-enhancement) |
| `description` | string | Manual description override |
| `capabilities` | object | Updated capability flags |
| `is_active` | boolean | Enable/disable tool |
| `script_prompt_template` | string | Updated script template |
| `image_prompt_template` | string | Updated image template |
| `video_prompt_template` | string | Updated video template |
| `priority` | integer | Selection priority (0-1000) |

### Response

**Status:** `200 OK`

Updated `ToolResponse` object.

### Example

```bash
# Update priority and description
curl -X PUT "http://localhost:8000/api/v1/tools/cosmic_flow_visualizer" \
  -H "Content-Type: application/json" \
  -d '{
    "priority": 150,
    "description": "Enhanced cosmic visualization with improved particle effects"
  }'
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Tool not found |

---

## DELETE /api/v1/tools/{tool_id}

Soft delete a tool (sets `is_active = false`).

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool_id` | string | Tool slug identifier |

### Response

**Status:** `200 OK`

```json
{
  "success": true,
  "tool_id": "cosmic_flow_visualizer"
}
```

### Example

```bash
curl -X DELETE "http://localhost:8000/api/v1/tools/cosmic_flow_visualizer"
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Tool not found |

---

## POST /api/v1/tools/preview

Preview AI enhancement without saving. See what Gemini will generate before committing.

### Request

Same as `POST /api/v1/tools`

```json
{
  "tool_name": "Quantum Realm Explorer",
  "idea": "Visualize quantum mechanics concepts - superposition, entanglement, wave functions - with abstract, flowing visuals."
}
```

### Response

**Status:** `200 OK`

```json
{
  "tool_id": "quantum_realm_explorer",
  "tool_name": "Quantum Realm Explorer",
  "category": "surreal_realism",
  "description": "Renders quantum mechanical concepts through abstract flowing visuals...",
  "capabilities": { ... },
  "script_prompt_template": "...",
  "image_prompt_template": "...",
  "video_prompt_template": "...",
  "parameters_schema": { ... },
  "reasoning": "This tool is classified as surreal_realism because quantum concepts benefit from..."
}
```

### Example

```bash
curl -X POST "http://localhost:8000/api/v1/tools/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "Abstract Data Flows",
    "idea": "Visualize data and algorithms as flowing rivers of light"
  }'
```

---

## POST /api/v1/tools/{tool_id}/improve

Improve an existing tool based on feedback. Gemini analyzes the current tool and suggestions to generate an improved version.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool_id` | string | Tool slug identifier |

### Request

**Content-Type:** `application/json`

```json
{
  "improvement_suggestion": "The particle effects are good but the color palette is too muted. Make it more vibrant with blues and purples. Also add more dramatic camera movements.",
  "preserve_templates": false
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `improvement_suggestion` | string | ✅ | - | What to improve (10-2000 chars) |
| `preserve_templates` | boolean | ❌ | `false` | Keep existing prompt templates |

### Response

**Status:** `200 OK`

Updated `ToolResponse` with incremented version and improvement history.

```json
{
  "id": "uuid-123",
  "tool_id": "cosmic_flow_visualizer",
  "tool_name": "Cosmic Flow Visualizer",
  "version": 3,
  "improvement_history": [
    {
      "timestamp": "2026-01-14T12:30:00Z",
      "previous_version": 1,
      "suggestion": "Add more vibrant colors",
      "changes_made": "Updated color palette..."
    },
    {
      "timestamp": "2026-01-15T14:30:00Z",
      "previous_version": 2,
      "suggestion": "The particle effects are good but...",
      "changes_made": "Enhanced color vibrancy with blues and purples..."
    }
  ],
  "last_improved_at": "2026-01-15T14:30:00Z"
}
```

### Example

```bash
curl -X POST "http://localhost:8000/api/v1/tools/cosmic_flow_visualizer/improve" \
  -H "Content-Type: application/json" \
  -d '{
    "improvement_suggestion": "Add support for slow-motion effects and improve the lighting model",
    "preserve_templates": true
  }'
```

### Errors

| Code | Condition |
|------|-----------|
| `404` | Tool not found |

---

## POST /api/v1/tools/{tool_id}/execute

Execute a tool with a topic to generate ready-to-use prompts.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool_id` | string | Tool slug identifier |

### Request

**Content-Type:** `application/json`

```json
{
  "topic": "How black holes warp spacetime",
  "parameters": {
    "neon_intensity": 0.9,
    "rain_enabled": true
  }
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic` | string | ✅ | Topic to generate prompts for (3-500 chars) |
| `parameters` | object | ❌ | Tool-specific parameters |

### Response

**Status:** `200 OK`

```json
{
  "tool_id": "cosmic_flow_visualizer",
  "topic": "How black holes warp spacetime",
  "generated_prompts": {
    "script_prompt": "Write an 18-second script about how black holes warp spacetime with a dramatic, awe-inspiring tone. Structure: 3s hook capturing attention, 12s body explaining the concept with visual descriptions, 3s CTA. Use simple language for general audience.",
    "image_prompt": "A photorealistic visualization of a massive black hole warping the fabric of spacetime around it. Visible accretion disk with bright orange and yellow plasma. Stars in the background appear distorted and stretched due to gravitational lensing. Deep space backdrop with subtle nebula colors. Cinematic lighting, 8K quality.",
    "video_prompt": "Generate an 18-second cinematic video depicting the concept of black holes warping spacetime. Start with a dramatic zoom from deep space toward a supermassive black hole. Show the accretion disk rotating with visible plasma flows. Demonstrate gravitational lensing effect on background stars. Smooth camera movements with orchestral background music building tension."
  },
  "estimated_generation_time": 180.5
}
```

### Example

```bash
curl -X POST "http://localhost:8000/api/v1/tools/cosmic_flow_visualizer/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "The mysterious dark matter that holds galaxies together"
  }'
```

### Errors

| Code | Condition |
|------|-----------|
| `400` | Tool is not active |
| `404` | Tool not found |
| `422` | Parameter validation failed |

---

## Frontend Integration Guide

### Tool Management Service

```javascript
class ToolService {
  constructor(baseUrl = '/api/v1/tools') {
    this.baseUrl = baseUrl;
  }

  // List tools with filters
  async listTools({ category, isActive = true, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({
      is_active: isActive,
      limit,
      offset
    });
    if (category) params.set('category', category);
    
    const res = await fetch(`${this.baseUrl}?${params}`);
    return res.json();
  }

  // Get single tool
  async getTool(toolId) {
    const res = await fetch(`${this.baseUrl}/${toolId}`);
    if (!res.ok) throw new Error('Tool not found');
    return res.json();
  }

  // Create new tool
  async createTool(name, idea, category = null) {
    const res = await fetch(this.baseUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_name: name,
        idea,
        category
      })
    });
    return res.json();
  }

  // Preview enhancement before creating
  async previewTool(name, idea, category = null) {
    const res = await fetch(`${this.baseUrl}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_name: name,
        idea,
        category
      })
    });
    return res.json();
  }

  // Update tool
  async updateTool(toolId, updates) {
    const res = await fetch(`${this.baseUrl}/${toolId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    return res.json();
  }

  // Improve tool
  async improveTool(toolId, suggestion, preserveTemplates = false) {
    const res = await fetch(`${this.baseUrl}/${toolId}/improve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        improvement_suggestion: suggestion,
        preserve_templates: preserveTemplates
      })
    });
    return res.json();
  }

  // Delete tool
  async deleteTool(toolId) {
    const res = await fetch(`${this.baseUrl}/${toolId}`, {
      method: 'DELETE'
    });
    return res.json();
  }

  // Execute tool
  async executeTool(toolId, topic, parameters = null) {
    const res = await fetch(`${this.baseUrl}/${toolId}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, parameters })
    });
    return res.json();
  }
}

// Usage
const toolService = new ToolService();

// List all surreal realism tools
const tools = await toolService.listTools({ category: 'surreal_realism' });

// Create a new tool
const newTool = await toolService.createTool(
  'Ocean Depths Explorer',
  'Visualize deep ocean scenes with bioluminescent creatures and underwater currents'
);

// Execute tool to get prompts
const prompts = await toolService.executeTool(
  'ocean_depths_explorer',
  'The mysterious creatures of the deep ocean'
);
```

### Tool Creator Component

```javascript
// React component for creating tools with preview
function ToolCreator({ onToolCreated }) {
  const [name, setName] = useState('');
  const [idea, setIdea] = useState('');
  const [category, setCategory] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);

  const handlePreview = async () => {
    setLoading(true);
    try {
      const result = await toolService.previewTool(name, idea, category);
      setPreview(result);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setLoading(true);
    try {
      const tool = await toolService.createTool(name, idea, category);
      onToolCreated(tool);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input 
        value={name} 
        onChange={e => setName(e.target.value)}
        placeholder="Tool Name"
      />
      <textarea
        value={idea}
        onChange={e => setIdea(e.target.value)}
        placeholder="Describe what this tool should do..."
      />
      <select value={category} onChange={e => setCategory(e.target.value)}>
        <option value="">Auto-detect category</option>
        <option value="surreal_realism">Surreal Realism</option>
        <option value="high_octane_anime">High Octane Anime</option>
        <option value="stylized_3d">Stylized 3D</option>
      </select>
      
      <button onClick={handlePreview} disabled={loading}>
        Preview Enhancement
      </button>
      
      {preview && (
        <div className="preview">
          <h4>AI Enhancement Preview</h4>
          <p><strong>Category:</strong> {preview.category}</p>
          <p><strong>Description:</strong> {preview.description}</p>
          <p><strong>Reasoning:</strong> {preview.reasoning}</p>
          
          <button onClick={handleCreate}>
            Create Tool
          </button>
        </div>
      )}
    </div>
  );
}
```
