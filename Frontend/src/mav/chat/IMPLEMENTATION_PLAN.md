# Project Chat (Module 4) - Implementation Plan

## Overview

The Project Chat feature enables users to have ChatGPT-style conversations with their VMP projects. Users can ask questions and receive **grounded answers** using:

1. **Project RAG** - Retrieval over project's chunked/embedded artifacts
2. **Bounded Web Search** - Optional external research when internal data is insufficient

The system supports **threads**, **message history**, **thread memory** (continuity without replaying history), and **structured citations**.

---

## Architecture

### High-Level Flow

```
User Message → Load Context → Route Intent → Retrieve Evidence → Grade Sufficiency
     ↓                                              ↓
   [Web Search if needed] ←──────────────────── [Insufficient]
     ↓                                              ↓
Compose Answer ← ──────────────────────────── [Sufficient]
     ↓
Update Memory → Persist → Return Response
```

### LangGraph Workflow (10 Nodes)

```
┌─────────────────────────────────────────────────────────────────┐
│                         START                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. LoadThreadContext                                            │
│     Load: thread_summary, pinned_facts, open_loops,             │
│           messages_window (bounded N)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. IntentRouter                                                 │
│     Classify: PROJECT_ONLY | PROJECT_PLUS_WEB | WEB_ONLY | META │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        [PROJECT_*]      [WEB_ONLY]       [META]
              │               │               │
              ▼               │               ▼
┌────────────────────────┐   │     ┌────────────────────────┐
│  3. QueryRewrite       │   │     │  Handle Meta           │
│     Optimize for RAG   │   │     │  (summarize, etc.)     │
└────────────────────────┘   │     └────────────────────────┘
              │               │
              ▼               │
┌────────────────────────┐   │
│  4. ProjectRetrieve    │   │
│     Vector search      │   │
│     (top-K chunks)     │   │
└────────────────────────┘   │
              │               │
              ▼               │
┌────────────────────────┐   │
│  5. EvidenceGrade      │   │
│     SUFFICIENT |       │   │
│     PARTIAL |          │   │
│     INSUFFICIENT       │   │
└────────────────────────┘   │
              │               │
    ┌─────────┴─────────┐    │
    │                   │    │
    ▼                   ▼    ▼
[SUFFICIENT]    [NEEDS_WEB] [WEB_ONLY]
    │                   │    │
    │                   ▼    │
    │     ┌────────────────────────┐
    │     │  6. WebPlan            │
    │     │     Generate 3-6       │
    │     │     search queries     │
    │     └────────────────────────┘
    │                   │
    │                   ▼
    │     ┌────────────────────────┐
    │     │  7. WebSearch +        │
    │     │     ExtractEvidence    │
    │     └────────────────────────┘
    │                   │
    └─────────┬─────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. AnswerCompose                                                │
│     Generate response with inline citations [P1], [W1]          │
│     Return structured citations array                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. MemoryUpdate                                                 │
│     Update: running_summary, pinned_facts, open_loops           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  10. Persist                                                     │
│      Store: assistant message, citations, tool_trace            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                            END
```

---

## Folder Structure

```
/Backend/src/mav/
├── chat/
│   ├── __init__.py
│   ├── models.py                    # Pydantic models (state, citations, etc.)
│   ├── IMPLEMENTATION_PLAN.md       # This document
│   ├── req.md                       # Product requirements
│   ├── agent.md                     # Agent/prompt specifications
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── database_adapter.py      # Supabase CRUD operations
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── project_rag_service.py   # Vector retrieval for project chunks
│   │   └── web_search_service.py    # Bounded web search with evidence extraction
│   │
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── chat_workflow.py         # Main LangGraph orchestration
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── context_loader.py    # Node 1: LoadThreadContext
│   │   │   ├── intent_router.py     # Node 2: IntentRouter
│   │   │   ├── query_rewriter.py    # Node 3: QueryRewrite
│   │   │   ├── project_retriever.py # Node 4: ProjectRetrieve
│   │   │   ├── evidence_grader.py   # Node 5: EvidenceGrade
│   │   │   ├── web_planner.py       # Node 6: WebPlan
│   │   │   ├── web_searcher.py      # Node 7: WebSearch + ExtractEvidence
│   │   │   ├── answer_composer.py   # Node 8: AnswerCompose
│   │   │   ├── memory_updater.py    # Node 9: MemoryUpdate
│   │   │   └── persistor.py         # Node 10: Persist
│   │   └── prompts/
│   │       └── chat_prompts.py      # All prompt templates
│   │
│   └── api/
│       ├── __init__.py
│       └── endpoints.py             # FastAPI router
```

---

## Database Schema

### Tables

#### 1. `project_chat_threads`
Stores chat threads linked to VMP projects.

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid (PK) | Thread identifier |
| `project_id` | uuid (FK) | References `vmp_projects.id` |
| `tenant_id` | uuid (FK) | References `tenants.id` |
| `user_id` | uuid (FK) | References `user_profiles.id` |
| `title` | text | Optional thread title |
| `status` | text | 'active', 'archived', 'deleted' |
| `created_at` | timestamptz | Creation timestamp |
| `updated_at` | timestamptz | Last update timestamp |
| `last_message_at` | timestamptz | Timestamp of last message |

#### 2. `project_chat_messages`
Stores all messages in threads (user, assistant, tool).

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid (PK) | Message identifier |
| `thread_id` | uuid (FK) | References `project_chat_threads.id` |
| `role` | text | 'user', 'assistant', 'tool', 'system' |
| `content` | text | Message content |
| `citations` | jsonb | Structured citations array |
| `tool_trace` | jsonb | Retrieval IDs, web queries, timings |
| `metadata` | jsonb | Token usage, latency, feedback |
| `created_at` | timestamptz | Creation timestamp |

#### 3. `project_chat_thread_memory`
Stores thread memory for continuity without replaying full history.

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid (PK) | Memory record identifier |
| `thread_id` | uuid (FK, UNIQUE) | References `project_chat_threads.id` |
| `running_summary` | text | Compact summary of thread so far |
| `pinned_facts` | jsonb | User-validated stable facts/preferences |
| `open_loops` | jsonb | Unanswered questions, pending decisions |
| `last_context_refs` | jsonb | Last used chunks and web sources |
| `updated_at` | timestamptz | Last update timestamp |

### Indexes

```sql
CREATE INDEX idx_chat_threads_project ON project_chat_threads(project_id, tenant_id);
CREATE INDEX idx_chat_threads_user ON project_chat_threads(user_id);
CREATE INDEX idx_chat_messages_thread ON project_chat_messages(thread_id, created_at DESC);
CREATE INDEX idx_chat_memory_thread ON project_chat_thread_memory(thread_id);
```

---

## API Endpoints

### Thread Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/mav/projects/{project_id}/threads` | Create a new thread |
| `GET` | `/api/v1/mav/projects/{project_id}/threads` | List threads for a project |
| `GET` | `/api/v1/mav/threads/{thread_id}` | Get thread details |
| `DELETE` | `/api/v1/mav/threads/{thread_id}` | Archive/delete a thread |

### Messaging

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/mav/threads/{thread_id}/messages` | Post user message (triggers workflow) |
| `GET` | `/api/v1/mav/threads/{thread_id}/messages` | Get paginated message history |

### Debug/Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/mav/threads/{thread_id}/memory` | Get thread memory state |
| `GET` | `/api/v1/mav/threads/{thread_id}/export` | Export thread transcript |

---

## Data Models

### LangGraph State Schema

```python
class ChatState(TypedDict):
    # Identifiers
    project_id: str
    thread_id: str
    user_id: str
    tenant_id: str
    
    # Input
    user_message: str
    
    # Thread Context
    messages_window: List[Dict[str, str]]  # Last N messages
    thread_summary: str
    pinned_facts: List[str]
    open_loops: List[str]
    
    # Routing
    intent: str  # PROJECT_ONLY, PROJECT_PLUS_WEB, WEB_ONLY, META
    needs_clarification: bool
    clarifying_questions: List[str]
    
    # Retrieval
    rewritten_query: str
    query_filters: Dict[str, Any]
    project_evidence: List[ProjectEvidence]
    evidence_grade: str  # SUFFICIENT, PARTIAL, INSUFFICIENT
    missing_info: List[str]
    
    # Web Research
    web_queries: List[str]
    web_evidence: List[WebEvidence]
    
    # Response
    answer_text: str
    citations: List[Citation]
    follow_ups: List[str]
    
    # Memory Update
    memory_patch: MemoryPatch
    
    # Audit
    tool_trace: ToolTrace
```

### Citation Structure

```python
class InternalCitation(BaseModel):
    """Citation for project artifact evidence."""
    type: Literal["internal"] = "internal"
    ref_id: str                    # e.g., "P1", "P2"
    artifact_type: str             # e.g., "vmp_hypothesis", "vmp_assumptions"
    chunk_id: str                  # Database chunk ID
    version: Optional[int] = None  # Artifact version for auditability
    snippet: Optional[str] = None  # Evidence snippet
    score: float                   # Relevance score

class ExternalCitation(BaseModel):
    """Citation for web evidence."""
    type: Literal["external"] = "external"
    ref_id: str              # e.g., "W1", "W2"
    url: str
    title: str
    domain: str
    snippet: Optional[str] = None
    fetched_at: str          # ISO timestamp
    published_at: Optional[str] = None

Citation = Union[InternalCitation, ExternalCitation]
```

---

## Dependencies on Existing System

| Component | Location | Usage |
|-----------|----------|-------|
| `EmbeddingService` | `src/mint/api/services/ai/embedding_service.py` | Generate query embeddings |
| `BraveSearchProvider` | `src/mint/providers/search.py` | Web search with retry logic |
| `get_client_config` | `src/mint/api/ai/config.py` | Get Azure OpenAI config |
| `get_service_role_client` | `src/mint/api/system/core/supabase_client.py` | Database access |
| `report_chunks` table | Existing | Project artifact chunks |
| `vmp_projects` table | Existing | Project metadata |
| `VMPProjectChunkingService` | `src/vpm/services/project_chunking_service.py` | Reference for chunk structure |

---

## Security Requirements

### Multi-Tenant Isolation
- All database queries **MUST** filter by `tenant_id`
- Project access **MUST** verify user belongs to tenant
- RLS policies should be enabled on new tables

### Data Safety
- Retrieved project text and web content treated as **UNTRUSTED DATA**
- Explicit fences in prompts: `UNTRUSTED_PROJECT_EVIDENCE:` and `UNTRUSTED_WEB_PAGES:`
- No write-actions to project artifacts in v1

### Tool Gating
- Web search only when routed as necessary
- Bounded queries (3-6 max per search)
- Minimal web content storage (snippets only)

---

## Implementation Phases

### Phase 1: Database Schema
- [ ] Create migration SQL for new tables
- [ ] Add to `tables.sql` documentation
- [ ] Create RLS policies

### Phase 2: Data Models
- [ ] Create `models.py` with all Pydantic models
- [ ] Define `ChatState` TypedDict for LangGraph

### Phase 3: Database Adapter
- [ ] Implement thread CRUD operations
- [ ] Implement message CRUD with pagination
- [ ] Implement thread memory operations

### Phase 4: Project RAG Service
- [ ] Create vector similarity search function
- [ ] Implement retrieval with tenant/project filtering
- [ ] Return structured `ProjectEvidence` objects

### Phase 5: Web Search Service
- [ ] Integrate `BraveSearchProvider`
- [ ] Implement evidence extraction with LLM
- [ ] Return structured `WebEvidence` objects

### Phase 6: LangGraph Workflow
- [ ] Implement all 10 nodes
- [ ] Create prompt templates
- [ ] Wire up conditional routing

### Phase 7: FastAPI Endpoints
- [ ] Create router with all endpoints
- [ ] Add authentication dependencies
- [ ] Add credit consumption

### Phase 8: Integration & Testing
- [ ] Wire to main app router
- [ ] Test multi-tenant isolation
- [ ] Test RAG accuracy
- [ ] Test web fallback

---

## Configuration

### Default Settings

```python
CHAT_CONFIG = {
    "messages_window_size": 5,           # Recent messages to include
    "max_project_chunks": 10,            # Top-K chunks to retrieve
    "similarity_threshold": 0.5,         # Minimum relevance score
    "max_web_queries": 6,                # Bounded web searches
    "max_web_results_per_query": 5,      # Results per search
    "memory_update_frequency": 1,        # Update after every N turns
    "max_summary_length": 500,           # Characters for running summary
    "max_pinned_facts": 10,              # Maximum pinned facts
    "max_open_loops": 5,                 # Maximum open loops to track
}
```

---

## Prompt Templates Reference

All prompts are defined in `workflow/prompts/chat_prompts.py` and follow these patterns:

1. **System Prompt**: Sets authority rules, grounding rules, output rules
2. **Intent Router**: Classifies into PROJECT_ONLY, PROJECT_PLUS_WEB, WEB_ONLY, META
3. **Query Rewrite**: Optimizes user question for RAG retrieval
4. **Evidence Grade**: Determines if project evidence is sufficient
5. **Web Plan**: Generates bounded search queries
6. **Web Extract**: Extracts evidence from fetched pages
7. **Answer Compose**: Generates response with citations
8. **Memory Update**: Updates thread summary, facts, loops

See `agent.md` for full prompt templates.

---

## Success Criteria

1. ✅ Users can create/list threads and post messages
2. ✅ Thread history persists with pagination
3. ✅ Thread memory improves continuity across long threads
4. ✅ Answers include structured citations (project + web)
5. ✅ Web search triggers only when internal evidence insufficient
6. ✅ No cross-project or cross-tenant leakage
7. ✅ Tool traces persist for audit/debug
