# RABA Software Requirements Specification (SRS)

**Document Version**: 1.0  
**Last Updated**: January 14, 2026  
**Project**: RABA - AI-Powered YouTube Shorts Generator

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document describes the functional and non-functional requirements for the RABA system - a multi-agent AI pipeline for automated generation of viral YouTube Shorts (8-25 seconds).

### 1.2 Scope

RABA automates the end-to-end process of creating short-form video content:
- User provides a topic and parameters
- System researches facts and finds reference images
- System generates a viral-optimized script
- System generates reference images
- System produces the final video with audio

### 1.3 Definitions & Acronyms

| Term | Definition |
|------|------------|
| **HITL** | Human-in-the-Loop - manual approval mode |
| **LLM** | Large Language Model |
| **Nano Banana Pro** | Gemini 2.5 Pro Image generation API |
| **Veo 3.1** | Google's video generation API |
| **Workflow** | A single video generation job from input to output |
| **Gate** | HITL checkpoint where user can approve/edit/regenerate |
| **Segment** | A single 8s video clip (videos >8s require multiple segments) |

### 1.4 References

- [RABA_Architecture.md](./RABA_Architecture.md) - Technical architecture document
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Veo 3.1 Video API](https://ai.google.dev/gemini-api/docs/video)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

## 2. System Overview

RABA is a **multi-agent pipeline** orchestrated by LangGraph that transforms a user's topic into a complete YouTube Short video. The system uses Google's Gemini family of models for LLM, image, and video generation.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   User      │───▶│   Intent/   │───▶│    Deep     │───▶│   Script    │───▶│   Image     │───▶│   Video     │
│   Input     │    │   Tool      │    │  Research   │    │  Generator  │    │  Generator  │    │  Generator  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                         │                  │                  │                  │                  │
                    [HITL Gate 1]     [HITL Gate 2]     [HITL Gate 3]     [HITL Gate 4]     [HITL Gate 5]
```

---

## 3. Functional Requirements

### 3.1 User Input (FR-1xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-101** | System SHALL accept a `topic` parameter (required, string) describing the video subject | Must |
| **FR-102** | System SHALL accept a `duration_seconds` parameter (8-25, default: 18) | Must |
| **FR-103** | System SHALL accept an `aspect_ratio` parameter ("9:16" or "16:9", default: "9:16") | Must |
| **FR-104** | System SHALL accept a `resolution` parameter ("720p" or "1080p", default: "1080p") | Must |
| **FR-105** | System SHALL accept a `category` parameter ("surreal_realism", "high_octane_anime", "stylized_3d", or "auto", default: "auto") | Must |
| **FR-106** | System SHALL accept a `hitl_mode` parameter ("auto" or "manual", default: "auto") | Must |
| **FR-107** | System SHALL accept an `enable_audio` parameter (boolean, default: true) | Must |
| **FR-108** | System SHALL accept an `enable_subtitles` parameter (boolean, default: false) | Should |
| **FR-109** | System SHALL accept an optional `reference_image` file upload (max 10MB, jpg/png/webp) | Should |
| **FR-110** | System SHALL validate all input parameters and return clear error messages for invalid inputs | Must |

### 3.2 Intent & Tool Selection (FR-2xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-201** | System SHALL analyze the topic using Gemini 2.5 Flash to determine intent type (educational, entertainment, inspirational, tutorial) | Must |
| **FR-202** | System SHALL select an appropriate tool/style based on the category parameter or auto-detect if "auto" | Must |
| **FR-203** | System SHALL support at least 3 category types: surreal_realism, high_octane_anime, stylized_3d | Must |
| **FR-204** | System SHALL persist tool selection results to `workflows.tool_selection` in Supabase | Must |
| **FR-205** | In manual HITL mode, system SHALL pause at Gate 1 for user approval of tool selection | Must |
| **FR-206** | At Gate 1, user SHALL be able to change the selected category | Should |

### 3.3 Deep Research (FR-3xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-301** | System SHALL use Gemini 2.5 Pro with Google Search grounding to research the topic | Must |
| **FR-302** | System SHALL gather factual data with source citations | Must |
| **FR-303** | System SHALL search for relevant reference images using Google Custom Search API | Must |
| **FR-304** | System SHALL download and store research images in Supabase Storage | Must |
| **FR-305** | System SHALL persist research output to `workflows.research_output` | Must |
| **FR-306** | System SHALL persist research image URLs to `workflows.research_images` | Must |
| **FR-307** | System SHALL cache research results in Redis with configurable TTL (default: 7 days) | Should |
| **FR-308** | In manual HITL mode, system SHALL pause at Gate 2 for user review of research | Must |
| **FR-309** | At Gate 2, user SHALL be able to edit facts or provide feedback for regeneration | Should |

### 3.4 Script Generation (FR-4xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-401** | System SHALL generate a video script using Gemini 2.5 Pro | Must |
| **FR-402** | Script SHALL include: hook (first 1-2s), scenes with dialogue/narration, visual directions, punchline | Must |
| **FR-403** | Script SHALL be optimized for viral engagement (pattern interrupts every 3-5s) | Should |
| **FR-404** | System SHALL persist script output to `workflows.script_output` | Must |
| **FR-405** | In manual HITL mode, system SHALL pause at Gate 3 for user review of script | Must |
| **FR-406** | At Gate 3, user SHALL be able to edit script text directly | Must |
| **FR-407** | At Gate 3, user SHALL be able to provide feedback for script regeneration | Should |

### 3.5 Image Generation (FR-5xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-501** | System SHALL generate 1-5 reference images using Nano Banana Pro (Gemini 2.5 Pro Image) | Must |
| **FR-502** | System SHALL reduce generated image count if user provided a reference image | Must |
| **FR-503** | System SHALL reduce generated image count if research found relevant images | Must |
| **FR-504** | System SHALL always generate at least 1 image | Must |
| **FR-505** | System SHALL never generate more than 5 images | Must |
| **FR-506** | System SHALL upload generated images to Supabase Storage | Must |
| **FR-507** | System SHALL persist image metadata to `workflows.generated_images` | Must |
| **FR-508** | In manual HITL mode, system SHALL pause at Gate 4 for user review of images | Must |
| **FR-509** | At Gate 4, user SHALL be able to add additional reference images | Should |
| **FR-510** | At Gate 4, user SHALL be able to provide feedback for image regeneration | Should |

### 3.6 Video Generation (FR-6xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-601** | System SHALL generate video using Veo 3.1 API | Must |
| **FR-602** | System SHALL use all available reference images (user + research + generated) | Must |
| **FR-603** | For videos >8 seconds, system SHALL generate multiple segments with max 8s each | Must |
| **FR-604** | System SHALL maintain visual continuity between segments using last-frame-to-first-frame technique | Must |
| **FR-605** | System SHALL generate native audio if `enable_audio` is true | Must |
| **FR-606** | System SHALL generate subtitles if `enable_subtitles` is true | Should |
| **FR-607** | System SHALL support both 9:16 (vertical) and 16:9 (horizontal) aspect ratios | Must |
| **FR-608** | System SHALL support 720p and 1080p resolutions | Must |
| **FR-609** | System SHALL persist video output to `workflows.video_output` | Must |
| **FR-610** | System SHALL upload final video to Supabase Storage | Must |
| **FR-611** | In manual HITL mode, system SHALL pause at Gate 5 for user approval of final video | Must |
| **FR-612** | At Gate 5, user SHALL be able to regenerate video with feedback | Should |

### 3.7 HITL (Human-in-the-Loop) (FR-7xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-701** | In auto mode, system SHALL run end-to-end without human intervention | Must |
| **FR-702** | In manual mode, system SHALL pause at 5 defined gates for user action | Must |
| **FR-703** | At each gate, user SHALL be able to APPROVE (continue), EDIT (modify), or REGENERATE (with feedback) | Must |
| **FR-704** | System SHALL limit regeneration attempts to 3 per gate | Must |
| **FR-705** | System SHALL persist all HITL feedback to `workflows.hitl_feedback` | Must |
| **FR-706** | System SHALL update `workflows.current_hitl_gate` when paused at a gate | Must |
| **FR-707** | System SHALL update `workflows.status` to `awaiting_<gate>_approval` when paused | Must |

### 3.8 Persistence & Storage (FR-8xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-801** | System SHALL create a workflow record in Supabase at job start | Must |
| **FR-802** | System SHALL persist all agent outputs to the workflows table | Must |
| **FR-803** | System SHALL upload all media (images, videos) to Supabase Storage | Must |
| **FR-804** | System SHALL track all media in the `media` table with workflow reference | Must |
| **FR-805** | System SHALL return final video URL upon workflow completion | Must |

### 3.9 Observability (FR-9xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-901** | System SHALL trace all workflow steps using LangSmith | Must |
| **FR-902** | System SHALL log input/output for each agent node | Should |
| **FR-903** | System SHALL track generation time per step | Should |

---

## 4. Non-Functional Requirements

### 4.1 Performance (NFR-1xx)

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-101** | Total workflow completion time (auto mode) | < 5 minutes |
| **NFR-102** | Intent/Tool Selection latency | < 3 seconds |
| **NFR-103** | Deep Research latency | < 30 seconds |
| **NFR-104** | Script Generation latency | < 15 seconds |
| **NFR-105** | Image Generation latency (per image) | < 20 seconds |
| **NFR-106** | Video Generation latency (per 8s segment) | < 60 seconds |
| **NFR-107** | API response time (non-generation endpoints) | < 500ms |

### 4.2 Scalability (NFR-2xx)

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-201** | Concurrent workflows supported | ≥ 10 |
| **NFR-202** | Tool repository size | ≥ 100 tools |
| **NFR-203** | Redis cache hit rate for repeated topics | ≥ 80% |

### 4.3 Reliability (NFR-3xx)

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-301** | System uptime | ≥ 99.5% |
| **NFR-302** | Workflow success rate | ≥ 95% |
| **NFR-303** | Data persistence guarantee | 100% (no data loss) |
| **NFR-304** | Error recovery - resume from last checkpoint | Supported |

### 4.4 Security (NFR-4xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **NFR-401** | All API endpoints SHALL use HTTPS | Must |
| **NFR-402** | API keys SHALL NOT be exposed in logs or responses | Must |
| **NFR-403** | User inputs SHALL be sanitized before use in prompts | Must |
| **NFR-404** | Row-Level Security (RLS) SHALL be enabled on Supabase tables | Must |
| **NFR-405** | Rate limiting SHALL be implemented on API endpoints | Should |
| **NFR-406** | Content safety filters SHALL block harmful content | Must |

### 4.5 Maintainability (NFR-5xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **NFR-501** | All configuration SHALL be centralized (not hardcoded) | Must |
| **NFR-502** | LLM models SHALL be swappable via configuration | Must |
| **NFR-503** | New tools/categories SHALL be addable without code changes | Should |
| **NFR-504** | System SHALL use environment variables for secrets | Must |

---

## 5. User Stories

### US-1: Basic Video Generation (Auto Mode)
**As a** content creator  
**I want to** provide a topic and get a complete video  
**So that** I can quickly produce YouTube Shorts without manual intervention

**Acceptance Criteria:**
- Given topic "How black holes work" and default parameters
- When I submit the request
- Then I receive a 1080p, 9:16, 18-second video with audio within 5 minutes

### US-2: Manual Review Mode
**As a** quality-focused creator  
**I want to** review and edit each step of video generation  
**So that** I can ensure the output meets my standards

**Acceptance Criteria:**
- Given hitl_mode="manual"
- When the system completes each step
- Then I can view the output, edit it, or request regeneration
- And I can provide specific feedback for regeneration

### US-3: Custom Reference Image
**As a** brand-conscious creator  
**I want to** upload my own reference image  
**So that** the generated video matches my visual style

**Acceptance Criteria:**
- Given I upload a reference image
- When the video is generated
- Then the visual style matches my reference image
- And fewer AI images are generated (to avoid redundancy)

### US-4: Long-Form Video (>8s)
**As a** creator  
**I want to** generate videos up to 25 seconds  
**So that** I can create more detailed content

**Acceptance Criteria:**
- Given duration_seconds=25
- When the video is generated
- Then the video is seamless (no visible cuts between segments)
- And character/style consistency is maintained throughout

### US-5: Category Selection
**As a** creator  
**I want to** choose a specific visual category  
**So that** my video has a consistent aesthetic

**Acceptance Criteria:**
- Given category="high_octane_anime"
- When the video is generated
- Then the visual style matches anime aesthetics
- And the tool selection respects my category choice

---

## 6. System Constraints

### 6.1 Technical Constraints

| Constraint | Description |
|------------|-------------|
| **TC-1** | Veo 3.1 maximum segment duration is 8 seconds |
| **TC-2** | Veo 3.1 supports max 3 reference images per generation |
| **TC-3** | Gemini API has rate limits and quotas |
| **TC-4** | Video resolutions limited to 720p and 1080p (no 4K) |
| **TC-5** | Reference image upload limited to 10MB |

### 6.2 Business Constraints

| Constraint | Description |
|------------|-------------|
| **BC-1** | Content must comply with YouTube community guidelines |
| **BC-2** | No celebrity likenesses or copyrighted material |
| **BC-3** | Content safety filters cannot be disabled |

### 6.3 Dependencies

| Dependency | Description |
|------------|-------------|
| **DEP-1** | Google Gemini API (LLM, Image, Video) |
| **DEP-2** | Google Custom Search API (image search) |
| **DEP-3** | Supabase (database + storage) |
| **DEP-4** | Redis/Upstash (caching) |
| **DEP-5** | LangSmith (tracing) |

---

## 7. Data Requirements

### 7.1 Input Data Schema

```json
{
  "topic": "string (required)",
  "duration_seconds": "integer 8-25 (default: 18)",
  "aspect_ratio": "enum ['9:16', '16:9'] (default: '9:16')",
  "resolution": "enum ['720p', '1080p'] (default: '1080p')",
  "category": "enum ['surreal_realism', 'high_octane_anime', 'stylized_3d', 'auto'] (default: 'auto')",
  "hitl_mode": "enum ['auto', 'manual'] (default: 'auto')",
  "enable_audio": "boolean (default: true)",
  "enable_subtitles": "boolean (default: false)",
  "reference_image": "file (optional, max 10MB)"
}
```

### 7.2 Output Data Schema

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

## 8. Acceptance Criteria Summary

| Feature | Acceptance Criteria |
|---------|---------------------|
| **Video Generation** | Video plays without errors, matches requested duration/resolution |
| **HITL Gates** | All 5 gates pause correctly in manual mode |
| **Multi-Segment** | Videos >8s are seamless with no visible cuts |
| **Image Search** | At least 1 relevant image found for most topics |
| **Persistence** | All outputs recoverable from database after completion |
| **Tracing** | All steps visible in LangSmith dashboard |

---

## 9. Appendix

### 9.1 HITL Gate Summary

| Gate # | Name | User Actions | Regenerate With |
|--------|------|--------------|-----------------|
| 1 | Tool Selection | Change category, approve | Category preference |
| 2 | Deep Research | Edit facts, view sources | Research angle feedback |
| 3 | Script | Edit text, change hook | Tone/content feedback |
| 4 | Image | Add/remove images | Style/composition feedback |
| 5 | Video | Approve/reject | Pacing/transition feedback |

### 9.2 Environment Variables Required

```bash
# Gemini API
GOOGLE_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Redis
UPSTASH_REDIS_URL=

# Google Custom Search (for image search)
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=

# LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=Raba
```

### 9.3 Related Documents

- **Architecture**: [RABA_Architecture.md](./RABA_Architecture.md) - Technical implementation details
- **API Reference**: (To be created) - API endpoint documentation
- **User Guide**: (To be created) - End-user documentation
