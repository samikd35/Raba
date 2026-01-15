# RABA Phase 4.3 & 4.5 Implementation Plan

**Version**: 1.0  
**Created**: January 15, 2026  
**Based on**: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md), [Guides/RABA_Architecture.md](../Guides/RABA_Architecture.md), [Guides/SRS.md](../Guides/SRS.md), [Guides/rule.md](../Guides/rule.md)

---

## Overview

This document provides a **detailed step-by-step implementation plan** for:
- **Phase 4.3**: Caching Layer (Redis/Upstash integration)
- **Phase 4.5**: API Completion (full endpoint implementation with file upload, rate limiting, documentation)

```
IMPLEMENTATION DEPENDENCIES
═══════════════════════════

Phase 4.3 (Caching Layer)          Phase 4.5 (API Completion)
─────────────────────────          ─────────────────────────
├─ Redis Service Enhancement       ├─ Full Generate Endpoint
├─ Research Caching                │   └─ Depends on: 4.3 (cache lookup)
├─ Tool List Caching               ├─ Complete Workflows Endpoint
├─ Cache Key Helpers               ├─ Rate Limiting
└─ Cache Hit/Miss Testing          ├─ API Documentation
                                   └─ Integration Tests
```

---

## Phase 4.3: Caching Layer

> **Goal**: Implement multi-layer caching with Redis/Upstash for research results, tool registry, and workflow state.  
> **Duration**: ~3-4 hours  
> **Reference**: [RABA_Architecture.md - Section 9: Caching Strategy](../Guides/RABA_Architecture.md)

### Prerequisites

- Upstash Redis database created
- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` (or `redis_url`) in `.env`
- Existing `app/services/redis.py` (already implemented - needs enhancement)

---

### 4.3.1 Enhance Redis Service for Upstash

**File**: `app/services/redis.py`  
**Est. Time**: 45 minutes

#### Current State Analysis

The existing `redis.py` already has:
- Basic `CacheService` and `RedisService` classes
- JSON serialization support
- Prefix-based key management (`raba:`)

#### Required Enhancements

**Step 1**: Add Upstash REST client support (alternative to standard Redis for serverless)

```
Enhancement Plan:
1. Add upstash-redis package dependency
2. Create UpstashRedisService class for REST-based access
3. Add connection pooling configuration
4. Implement async methods properly (current implementation uses sync client)
```

**Reference**: [Upstash Redis Python Documentation](https://upstash.com/docs/redis/tutorials/python_fastapi_caching)

**Implementation Details**:

| Task | Description | Reference |
|------|-------------|-----------|
| **4.3.1.1** | Add `upstash-redis` to `requirements.txt` | [upstash-redis PyPI](https://pypi.org/project/upstash-redis/) |
| **4.3.1.2** | Create `UpstashRedisService` class with async support | Architecture Section 9.1 |
| **4.3.1.3** | Add connection health check method | NFR-301 (99.5% uptime) |
| **4.3.1.4** | Implement graceful fallback when Redis unavailable | Architecture 5.4 Error Handling |

**Configuration to Add** (from Architecture Section 7.1):

```python
# Expected in app/config.py
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    ttl_short: int = 3600      # 1 hour (tool list)
    ttl_medium: int = 86400    # 1 day
    ttl_long: int = 604800     # 7 days (research)
    cache_prefix: str = "raba:"
```

---

### 4.3.2 Implement Research Caching

**File**: `app/agents/deep_research.py` (enhancement)  
**New File**: `app/utils/cache.py`  
**Est. Time**: 30 minutes

**Reference**: 
- SRS FR-307: "System SHALL cache research results in Redis with configurable TTL (default: 7 days)"
- Architecture Section 2.4: Deep Research Agent caching flow

#### Cache Key Strategy (from Architecture Section 9.2)

```
Cache Key Format: raba:research:{topic_hash}:{depth}
Example: raba:research:a1b2c3d4e5f6g7h8:standard

Where:
- topic_hash = SHA256(topic.lower())[:16]
- depth = "quick" | "standard" | "deep"
```

#### Implementation Steps

| Task | Description | File | Reference |
|------|-------------|------|-----------|
| **4.3.2.1** | Create `CacheKeys` utility class | `app/utils/cache.py` | Architecture 9.2 |
| **4.3.2.2** | Add `generate_topic_hash()` function | `app/utils/cache.py` | Architecture 9.2 |
| **4.3.2.3** | Implement research cache lookup in Deep Research agent | `app/agents/deep_research.py` | FR-307 |
| **4.3.2.4** | Implement research cache write after successful research | `app/agents/deep_research.py` | FR-307 |
| **4.3.2.5** | Add `cache_hit` field to `ResearchOutput` model | `app/models/research.py` | Architecture 2.4 |

#### Cache Flow (from Architecture Section 2.4)

```
Input: {topic, research_depth, user_context}
    ↓
Check Redis Cache (L1)
    ↓
If HIT: Return cached data (mark cache_hit=true)
    ↓
If MISS: Invoke Gemini 2.5 Pro with Google Search Grounding
    ↓
Cache Results in Redis
    - Key: raba:research:{topic_hash}:{depth}
    - TTL: 7 days (604800 seconds)
    - Value: {findings, sources, citations, research_images[], generated_at}
    ↓
Persist to Supabase (workflows.research_output)
    ↓
Output: {research_data, sources[], confidence_scores, research_images[], cache_hit}
```

---

### 4.3.3 Implement Tool List Caching

**File**: `app/tools/registry.py` (enhancement)  
**Est. Time**: 20 minutes

**Reference**: 
- Architecture Section 4.1: ToolRegistry with caching
- Implementation Plan Task 4.3.3: "Cache tool registry (1 hour TTL)"

#### Cache Key Strategy

```
Cache Key: raba:tools:list
TTL: 1 hour (3600 seconds)
Value: JSON array of all enabled tools
```

#### Implementation Steps

| Task | Description | File | Reference |
|------|-------------|------|-----------|
| **4.3.3.1** | Add cache lookup in `list_all_tools()` method | `app/tools/registry.py` | Architecture 4.1 |
| **4.3.3.2** | Add cache write after database fetch | `app/tools/registry.py` | Architecture 4.1 |
| **4.3.3.3** | Implement cache invalidation on tool registration | `app/tools/registry.py` | Architecture 9.3 |

#### Cache Invalidation (from Architecture Section 9.3)

```python
# When new tool is registered:
async def invalidate_on_new_tool(self, tool_id: str):
    """When new tool added, invalidate tools list cache."""
    await redis.delete(CacheKeys.tools_list())
```

---

### 4.3.4 Create Cache Key Helpers

**New File**: `app/utils/cache.py`  
**Est. Time**: 20 minutes

**Reference**: Architecture Section 9.2 - Cache Key Naming Convention

#### Implementation

Create a `CacheKeys` class with standardized key generation methods:

| Method | Key Format | TTL | Purpose |
|--------|-----------|-----|---------|
| `research(topic, depth)` | `raba:research:{hash}:{depth}` | 7 days | Research results |
| `script(research_hash, tool_id)` | `raba:script:{hash}:{tool_id}` | 1 day | Generated scripts |
| `image_prompt(script_hash)` | `raba:image_prompt:{hash}` | 1 day | Image prompts |
| `tools_list()` | `raba:tools:list` | 1 hour | Tool registry |
| `user_session(user_id)` | `raba:session:{user_id}` | 1 hour | User sessions |
| `job_status(job_id)` | `raba:job:{job_id}` | 24 hours | Workflow status |

---

### 4.3.5 Test Cache Hit/Miss

**New File**: `tests/test_cache.py`  
**Est. Time**: 30 minutes

#### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| **TC-001** | `test_cache_set_get` | Basic set/get operations | Value retrieved matches value set |
| **TC-002** | `test_cache_ttl_expiry` | Verify TTL expiration | Value returns None after TTL |
| **TC-003** | `test_research_cache_hit` | Research with cached topic | Returns `cache_hit=True` |
| **TC-004** | `test_research_cache_miss` | Research with new topic | Returns `cache_hit=False` |
| **TC-005** | `test_tool_list_cache` | Tool list caching | Second call uses cache |
| **TC-006** | `test_cache_invalidation` | Tool registration invalidates cache | Cache cleared after registration |
| **TC-007** | `test_cache_key_generation` | Key format validation | Keys match expected format |
| **TC-008** | `test_redis_unavailable_fallback` | Graceful degradation | System works without cache |

---

## Phase 4.5: API Completion

> **Goal**: Complete all API endpoints with full functionality, file upload, rate limiting, and documentation.  
> **Duration**: ~4-5 hours  
> **Reference**: [SRS.md - Section 3: Functional Requirements](../Guides/SRS.md)

### Prerequisites

- Phase 4.3 completed (caching layer)
- All Phase 2-3 agents functional
- HITL system (Phase 4.1) working

---

### 4.5.1 Complete Generate Endpoint

**File**: `app/api/routes/generate.py`  
**Est. Time**: 45 minutes

**Reference**:
- SRS FR-101 to FR-110: User Input Requirements
- Architecture Section 3: Data Flow

#### Current State Analysis

The existing `generate.py` has basic workflow creation but lacks:
- File upload support for reference images
- Integration with LangGraph workflow execution
- Cache lookup before creating new workflow (for duplicate topics)

#### Required Enhancements

| Task | Description | Reference |
|------|-------------|-----------|
| **4.5.1.1** | Add `File` parameter for `reference_image` upload | FR-109: Optional reference image (max 10MB) |
| **4.5.1.2** | Implement file validation (size, type) | FR-109: jpg/png/webp, max 10MB |
| **4.5.1.3** | Upload reference image to Supabase Storage | FR-804: Upload media to Storage |
| **4.5.1.4** | Check cache for similar recent topics (optional optimization) | NFR-203: 80%+ cache hit rate |
| **4.5.1.5** | Trigger LangGraph workflow execution | Architecture 3: Data Flow |
| **4.5.1.6** | Return workflow ID for polling | FR-805: Return workflow ID |

#### File Upload Implementation

```
Request Format (multipart/form-data):
- topic: str (required)
- duration_seconds: int (8-25, default: 18)
- aspect_ratio: str ("9:16" | "16:9", default: "9:16")
- resolution: str ("720p" | "1080p", default: "1080p")
- category: str ("surreal_realism" | "high_octane_anime" | "stylized_3d" | "auto")
- hitl_mode: str ("auto" | "manual", default: "auto")
- enable_audio: bool (default: true)
- enable_subtitles: bool (default: false)
- reference_image: File (optional, max 10MB, jpg/png/webp)

Reference: SRS Section 3.1 (FR-101 to FR-110)
```

#### Validation Rules (from SRS)

| Parameter | Validation | Error Message |
|-----------|------------|---------------|
| `topic` | Required, non-empty | "Topic is required" |
| `duration_seconds` | 8-25 | "Duration must be between 8 and 25 seconds" |
| `aspect_ratio` | "9:16" or "16:9" | "Invalid aspect ratio" |
| `resolution` | "720p" or "1080p" | "Invalid resolution" |
| `reference_image` | ≤10MB, jpg/png/webp | "Image must be ≤10MB and jpg/png/webp" |

---

### 4.5.2 Complete Workflows Endpoint

**File**: `app/api/routes/workflows.py`  
**Est. Time**: 30 minutes

**Reference**:
- Architecture Section 3: Data Flow - step 9
- SRS FR-805: Return final video URL

#### Current State Analysis

The existing `workflows.py` has:
- Basic `GET /workflows/{workflow_id}` returning workflow data
- Stub `GET /workflows` list endpoint

#### Required Enhancements

| Task | Description | Reference |
|------|-------------|-----------|
| **4.5.2.1** | Calculate `generation_time_seconds` from timestamps | NFR-101: Track completion time |
| **4.5.2.2** | Add `all_media` field to response | Architecture 3: Data Flow step 9 |
| **4.5.2.3** | Implement full list endpoint with filtering | Architecture 8.3: Indexes |
| **4.5.2.4** | Add status filtering (pending, completed, failed) | Architecture 8.2: Status enum |
| **4.5.2.5** | Implement pagination properly | API best practices |
| **4.5.2.6** | Add `DELETE /workflows/{id}` endpoint | Cleanup capability |

#### Response Schema Enhancement (from Architecture Section 3)

```json
{
  "workflow_id": "uuid",
  "status": "completed",
  "video_url": "string (Supabase Storage URL)",
  "video_duration": "float",
  "resolution": "string",
  "aspect_ratio": "string",
  "all_image_urls": ["string"],
  "generation_time_seconds": "float",
  "metadata": {
    "tool_used": "string",
    "category": "string",
    "segment_count": "integer"
  }
}
```

---

### 4.5.3 Add Rate Limiting

**File**: `app/main.py` (enhancement)  
**New File**: `app/api/middleware/rate_limiter.py`  
**Est. Time**: 30 minutes

**Reference**:
- NFR-405: "Rate limiting SHALL be implemented on API endpoints"
- Architecture Section 10.2.A: Rate Limiting implementation

#### Rate Limiting Strategy (from Architecture)

```python
# Using slowapi library
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Rate limits by endpoint
@app.post("/api/v1/generate")
@limiter.limit("5/minute")  # 5 requests per minute per IP
async def generate_video(request: GenerateRequest):
    pass
```

#### Implementation Steps

| Task | Description | Reference |
|------|-------------|-----------|
| **4.5.3.1** | Add `slowapi` to `requirements.txt` | [slowapi GitHub](https://github.com/laurentS/slowapi) |
| **4.5.3.2** | Create rate limiter middleware | Architecture 10.2.A |
| **4.5.3.3** | Configure rate limits per endpoint | See table below |
| **4.5.3.4** | Add rate limit exceeded handler | Return 429 with retry-after |
| **4.5.3.5** | Store rate limit state in Redis | Distributed rate limiting |

#### Rate Limit Configuration

| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| `POST /api/v1/generate` | 5/minute | Expensive operation (video generation) |
| `GET /api/v1/workflows/{id}` | 60/minute | Polling endpoint (allow frequent checks) |
| `GET /api/v1/workflows` | 30/minute | List endpoint |
| `POST /api/v1/workflows/{id}/feedback` | 10/minute | HITL feedback |
| `GET /api/v1/tools` | 60/minute | Cacheable, low cost |

---

### 4.5.4 API Documentation Enhancement

**File**: `app/main.py`  
**Est. Time**: 30 minutes

**Reference**:
- Implementation Plan Task 4.5.4: "OpenAPI schema improvements"
- NFR-503: "New tools/categories SHALL be addable without code changes"

#### OpenAPI Enhancements

| Task | Description |
|------|-------------|
| **4.5.4.1** | Add API title, description, version in FastAPI init |
| **4.5.4.2** | Add tags for endpoint grouping |
| **4.5.4.3** | Add response examples for all endpoints |
| **4.5.4.4** | Document error responses (400, 404, 429, 500, 503) |
| **4.5.4.5** | Add security scheme documentation (when auth added) |

#### FastAPI Metadata Configuration

```python
app = FastAPI(
    title="RABA API",
    description="AI-Powered YouTube Shorts Generator - Multi-Agent Pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "generate", "description": "Video generation endpoints"},
        {"name": "workflows", "description": "Workflow status and results"},
        {"name": "tools", "description": "Tool repository management"},
        {"name": "hitl", "description": "Human-in-the-Loop feedback"},
    ]
)
```

---

### 4.5.5 Integration Tests

**New File**: `tests/test_api/test_integration.py`  
**Est. Time**: 1 hour

**Reference**:
- SRS Section 8: Acceptance Criteria
- Implementation Plan: "Full API test suite"

#### Test Scenarios

| Test ID | Test Name | Description | Validates |
|---------|-----------|-------------|-----------|
| **IT-001** | `test_full_auto_workflow` | Complete auto mode generation | FR-701 |
| **IT-002** | `test_workflow_with_reference_image` | Upload image and generate | FR-109, FR-502 |
| **IT-003** | `test_workflow_status_polling` | Poll until completion | FR-805 |
| **IT-004** | `test_rate_limiting` | Verify 429 after limit | NFR-405 |
| **IT-005** | `test_invalid_input_validation` | Test all validation errors | FR-110 |
| **IT-006** | `test_workflow_not_found` | 404 for invalid workflow ID | Error handling |
| **IT-007** | `test_list_workflows_pagination` | Test pagination params | API completion |
| **IT-008** | `test_generate_with_all_params` | All optional params | FR-101-110 |

#### Test Fixtures Required

```python
# Fixtures to create in conftest.py
@pytest.fixture
def test_client():
    """FastAPI test client."""
    
@pytest.fixture
def sample_reference_image():
    """Sample image file for upload tests."""
    
@pytest.fixture
def mock_redis():
    """Mock Redis for cache tests."""
```

---

## Implementation Checklist

### Phase 4.3: Caching Layer

- [ ] **4.3.1** Enhance Redis Service
  - [ ] 4.3.1.1 Add `upstash-redis` dependency
  - [ ] 4.3.1.2 Create `UpstashRedisService` class
  - [ ] 4.3.1.3 Add connection health check
  - [ ] 4.3.1.4 Implement graceful fallback

- [ ] **4.3.2** Research Caching
  - [ ] 4.3.2.1 Create `CacheKeys` utility class
  - [ ] 4.3.2.2 Add `generate_topic_hash()` function
  - [ ] 4.3.2.3 Implement cache lookup in Deep Research
  - [ ] 4.3.2.4 Implement cache write after research
  - [ ] 4.3.2.5 Add `cache_hit` to ResearchOutput model

- [ ] **4.3.3** Tool List Caching
  - [ ] 4.3.3.1 Add cache lookup in `list_all_tools()`
  - [ ] 4.3.3.2 Add cache write after DB fetch
  - [ ] 4.3.3.3 Implement cache invalidation on registration

- [ ] **4.3.4** Cache Key Helpers
  - [ ] Create `app/utils/cache.py` with `CacheKeys` class

- [ ] **4.3.5** Cache Tests
  - [ ] Create `tests/test_cache.py`
  - [ ] Implement all test cases (TC-001 to TC-008)

### Phase 4.5: API Completion

- [ ] **4.5.1** Complete Generate Endpoint
  - [ ] 4.5.1.1 Add File parameter for reference image
  - [ ] 4.5.1.2 Implement file validation
  - [ ] 4.5.1.3 Upload to Supabase Storage
  - [ ] 4.5.1.4 Cache lookup for similar topics
  - [ ] 4.5.1.5 Trigger LangGraph workflow
  - [ ] 4.5.1.6 Return workflow ID

- [ ] **4.5.2** Complete Workflows Endpoint
  - [ ] 4.5.2.1 Calculate generation time
  - [ ] 4.5.2.2 Add all_media field
  - [ ] 4.5.2.3 Implement full list endpoint
  - [ ] 4.5.2.4 Add status filtering
  - [ ] 4.5.2.5 Implement proper pagination
  - [ ] 4.5.2.6 Add DELETE endpoint

- [ ] **4.5.3** Rate Limiting
  - [ ] 4.5.3.1 Add `slowapi` dependency
  - [ ] 4.5.3.2 Create rate limiter middleware
  - [ ] 4.5.3.3 Configure per-endpoint limits
  - [ ] 4.5.3.4 Add 429 handler
  - [ ] 4.5.3.5 Redis-backed rate limiting

- [ ] **4.5.4** API Documentation
  - [ ] 4.5.4.1 Add API metadata
  - [ ] 4.5.4.2 Add endpoint tags
  - [ ] 4.5.4.3 Add response examples
  - [ ] 4.5.4.4 Document error responses
  - [ ] 4.5.4.5 Security scheme docs

- [ ] **4.5.5** Integration Tests
  - [ ] Create `tests/test_api/test_integration.py`
  - [ ] Implement all test scenarios (IT-001 to IT-008)

---

## Dependencies to Add

Add to `requirements.txt`:

```txt
# Caching (Phase 4.3)
upstash-redis>=1.0.0

# Rate Limiting (Phase 4.5)
slowapi>=0.1.9

# File Upload (Phase 4.5)
python-multipart>=0.0.6
```

---

## Files to Create/Modify

### New Files

| File | Phase | Purpose |
|------|-------|---------|
| `app/utils/cache.py` | 4.3.4 | Cache key helpers |
| `app/api/middleware/rate_limiter.py` | 4.5.3 | Rate limiting middleware |
| `tests/test_cache.py` | 4.3.5 | Cache unit tests |
| `tests/test_api/test_integration.py` | 4.5.5 | API integration tests |

### Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `app/services/redis.py` | 4.3.1 | Add Upstash support, async methods |
| `app/agents/deep_research.py` | 4.3.2 | Add cache lookup/write |
| `app/tools/registry.py` | 4.3.3 | Add tool list caching |
| `app/models/research.py` | 4.3.2 | Add `cache_hit` field |
| `app/api/routes/generate.py` | 4.5.1 | File upload, workflow trigger |
| `app/api/routes/workflows.py` | 4.5.2 | Complete all endpoints |
| `app/main.py` | 4.5.3-4 | Rate limiting, API docs |
| `requirements.txt` | Both | New dependencies |

---

## Estimated Timeline

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| **4.3.1** | Redis Service Enhancement | 45 min |
| **4.3.2** | Research Caching | 30 min |
| **4.3.3** | Tool List Caching | 20 min |
| **4.3.4** | Cache Key Helpers | 20 min |
| **4.3.5** | Cache Tests | 30 min |
| **4.5.1** | Generate Endpoint | 45 min |
| **4.5.2** | Workflows Endpoint | 30 min |
| **4.5.3** | Rate Limiting | 30 min |
| **4.5.4** | API Documentation | 30 min |
| **4.5.5** | Integration Tests | 1 hr |
| **Total** | | **~6-7 hours** |

---

## References

### Documentation
- [Guides/RABA_Architecture.md](../Guides/RABA_Architecture.md) - Sections 9 (Caching), 10 (Rate Limiting)
- [Guides/SRS.md](../Guides/SRS.md) - FR-101-110, FR-307, NFR-405
- [Guides/rule.md](../Guides/rule.md) - Design principles

### API Documentation
- [Backend/Documentations/gemini_doc.md](./Documentations/gemini_doc.md) - Gemini 3 API
- [Backend/Documentations/veo_doc.md](./Documentations/veo_doc.md) - Veo 3.1 API
- [Backend/Documentations/nanao_banana_doc.md](./Documentations/nanao_banana_doc.md) - Image generation

### External References
- [Upstash Redis Python Documentation](https://upstash.com/docs/redis/tutorials/python_fastapi_caching)
- [slowapi GitHub](https://github.com/laurentS/slowapi) - Rate limiting library
- [FastAPI File Uploads](https://fastapi.tiangolo.com/tutorial/request-files/)

---

## Success Criteria

### Phase 4.3 Complete When:
- [ ] Research results cached with 7-day TTL
- [ ] Tool list cached with 1-hour TTL
- [ ] Cache hit rate measurable via logging
- [ ] Graceful fallback when Redis unavailable
- [ ] All cache tests passing

### Phase 4.5 Complete When:
- [ ] Reference image upload working (max 10MB)
- [ ] All input validations returning proper errors
- [ ] Rate limiting active on all endpoints
- [ ] Workflow list endpoint with pagination/filtering
- [ ] OpenAPI docs complete with examples
- [ ] All integration tests passing
