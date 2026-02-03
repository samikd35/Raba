# Solution Critique - AI Models & Deep Dive

## 🤖 AI Models Used

### Primary Model: **GPT-4 (Azure OpenAI)**

**Configuration**:
```python
# From ai_service_wrapper.py
provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)

# Model call in base_critique_agent.py
response = await self.ai_service.generate_analysis_response(
    messages=messages,
    model="gpt-4",           # Maps to GPT-4.1 via Azure
    temperature=0.1,         # Low for factual analysis
    max_tokens=3000,         # Per critique
    json_mode=True,          # Force JSON output
    monitoring_context=monitoring_context
)
```

**Where Used**:

1. **Query Planning** (`services/query_planner.py`)
   - Generates 15-20 targeted search queries
   - Temperature: 0.3
   - Max tokens: 2000

2. **5 Critique Agents** (`agents/`)
   - Market Viability
   - Operational Feasibility
   - Business Model
   - Competitive Differentiation
   - Technical Scalability
   - Temperature: 0.1 (very factual)
   - Max tokens: 3000 each

3. **Report Synthesis** (`agents/report_synthesizer_agent.py`)
   - Combines all critiques into final report
   - Generates executive summary
   - Temperature: 0.2
   - Max tokens: 1500

**Total GPT-4 Calls per Critique**: 7 calls
- 1 for query planning
- 5 for parallel critiques (simultaneous)
- 1 for synthesis

---

### Secondary Model: **GPT-4o-mini**

**Configuration**:
```python
# From critique_chat_service.py
response = await self.ai_service.generate_analysis_response(
    messages=[...],
    model="gpt-4o-mini",     # Cost-effective for chat
    max_tokens=1000,
    temperature=0.3          # Low for grounded responses
)
```

**Where Used**:
- Chat endpoint: `/solution-critique/chat/message`
- Answers user questions about the critique report
- Uses RAG (Retrieval-Augmented Generation) with vector search

---

## 📊 AI Usage Summary

### Per Critique Generation

| Component | Model | Calls | Tokens (est.) | Purpose |
|-----------|-------|-------|---------------|---------|
| Query Planning | GPT-4 | 1 | ~2,000 | Generate search queries |
| Market Viability | GPT-4 | 1 | ~3,000 | Generate critiques |
| Operational Feasibility | GPT-4 | 1 | ~3,000 | Generate critiques |
| Business Model | GPT-4 | 1 | ~3,000 | Generate critiques |
| Competitive Differentiation | GPT-4 | 1 | ~3,000 | Generate critiques |
| Technical Scalability | GPT-4 | 1 | ~3,000 | Generate critiques |
| Report Synthesis | GPT-4 | 1 | ~1,500 | Generate summary |
| **Total** | **GPT-4** | **7** | **~18,500** | **Complete critique** |

### Per Chat Interaction

| Component | Model | Calls | Tokens (est.) | Purpose |
|-----------|-------|-------|---------------|---------|
| Chat Response | GPT-4o-mini | 1 | ~1,000 | Answer questions |

---

## 🏗️ System Architecture

### High-Level Flow

```
1. User Request (API)
   ↓
2. Context Loading (VPC v2 + VPS + BMC)
   ↓
3. Query Planning (GPT-4 generates 15-20 queries)
   ↓
4. Web Research (Brave Search - parallel batches)
   ↓
5. ┌─────────────────────────────────────────┐
   │  PARALLEL CRITIQUE GENERATION (GPT-4)   │
   ├─────────────────────────────────────────┤
   │  • Market Viability Agent               │
   │  • Operational Feasibility Agent        │
   │  • Business Model Agent                 │
   │  • Competitive Differentiation Agent    │
   │  • Technical Scalability Agent          │
   └─────────────────────────────────────────┘
   ↓ (All 5 complete simultaneously)
6. Report Synthesis (GPT-4 generates executive summary)
   ↓
7. Database Storage (vmp_projects.soln_critique_data)
   ↓
8. Auto-Chunk for Chat (Background)
   ↓
9. JSON Response to User
```

**Total Processing Time**: 45-60 seconds

---

## 🔄 Complete End-to-End Flow

### Step-by-Step Execution

**1. User Initiates Critique** (t=0s)
```
POST /api/v2/mvp/projects/{project_id}/solution-critique/generate
```

**2. API Validation** (t=0-1s)
- Check auth (auth_v2.utils)
- Validate project exists
- Check VPC, VPS, BMC present
- Check if critique already exists

**3. Background Task Starts** (t=1s)
- Generate session_id
- Return immediately to user
- Start `SolutionCritiqueWorkflow`

**4. Context Preparation** (t=1-5s)
- Load VPC v2 data
- Load VPS data
- Load BMC data
- Extract geography, industry, solution description

**5. Query Planning** (t=5-10s)
- **GPT-4 Call #1**
- Generate 15-20 search queries
- Categorize by dimension
- Add priority and rationale

**6. Web Research** (t=10-25s)
- Execute Brave Search queries in batches
- 5 queries per batch
- 1 second delay between batches
- Collect ~85 web sources

**7. Parallel Critique Generation** (t=25-50s)
- **GPT-4 Calls #2-6** (simultaneous)
- All 5 agents run in parallel
- Each generates 2-4 critiques
- Each with 5-8 citations
- Total: ~15 critiques

**8. Report Synthesis** (t=50-55s)
- **GPT-4 Call #7**
- Aggregate all critiques
- Deduplicate sources
- Renumber citations
- Generate executive summary
- Prioritize actions

**9. Database Save** (t=55-56s)
- Store in `vmp_projects.soln_critique_data`
- Status: "completed"

**10. Auto-Chunk for Chat** (t=56-60s)
- Convert report to text chunks
- Generate embeddings
- Store in vector database
- ~25-30 chunks created

**11. Complete** (t=60s)
- User can fetch results
- User can start chatting

---

## 🎯 Key Components

### 1. Workflow Orchestration (LangGraph)

**File**: `services/critique_workflow.py`

**11 Nodes**:
1. prepare_context
2. plan_queries (GPT-4)
3. execute_research
4-8. 5 parallel critique agents (GPT-4)
9. synthesize_report (GPT-4)
10. save_to_database
11. END

**Parallel Execution**:
```python
# All 5 agents start simultaneously after research
workflow.add_edge("execute_research", "market_critique")
workflow.add_edge("execute_research", "operational_critique")
workflow.add_edge("execute_research", "business_model_critique")
workflow.add_edge("execute_research", "competitive_critique")
workflow.add_edge("execute_research", "technical_critique")
```

---

### 2. Citation System (PV Report Standards)

**Every critique must have**:
- Numbered citations: [1], [2], [3]
- Minimum 5-8 citations
- Sources section with all references
- Citation validation

**Example**:
```json
{
  "problem": "Market demand is unvalidated [1]. Only 15% adoption [2]...",
  "sources": [
    {"id": 1, "type": "bmc", "field": "customer_segments"},
    {"id": 2, "type": "web", "title": "Market Report", "url": "..."}
  ],
  "citation_count": 8
}
```

---

### 3. Chat with RAG

**Process**:
1. Convert report to text chunks (1000 chars)
2. Generate embeddings (OpenAI)
3. Store in vector database
4. User asks question
5. Vector search finds top 15 chunks
6. GPT-4o-mini generates grounded response

**Automatic**: Happens after critique completes

---

## 📁 File Structure

```
/soln_critique/
├── agents/                  # 7 agents
│   ├── base_critique_agent.py
│   ├── market_viability_agent.py
│   ├── operational_feasibility_agent.py
│   ├── business_model_agent.py
│   ├── competitive_differentiation_agent.py
│   ├── technical_scalability_agent.py
│   └── report_synthesizer_agent.py
├── services/                # Core services
│   ├── critique_workflow.py
│   ├── context_loader.py
│   ├── query_planner.py
│   ├── web_researcher.py
│   ├── critique_report_chunking_service.py
│   └── critique_chat_service.py
├── api/                     # API endpoints
│   ├── endpoints.py         # 3 critique endpoints
│   └── chat_endpoints.py    # 4 chat endpoints
└── models/                  # Data models
    ├── state_models.py
    └── response_models.py
```

---

## 🎯 Key Design Decisions

### 1. Parallel Execution
**Why**: Reduce time from ~5 min to ~1 min
**How**: LangGraph parallel edges
**Result**: 5x faster

### 2. JSON-Only Output
**Why**: Structured, parseable, frontend-ready
**How**: `json_mode=True` in all AI calls
**Result**: Consistent format

### 3. Citation System
**Why**: Credibility and transparency
**How**: Numbered citations in all text
**Result**: Evidence-based critiques

### 4. Auto-Chat Preparation
**Why**: Immediate chat availability
**How**: Chunk after DB save
**Result**: No manual prep needed

---

## 📊 Database Schema

**Table**: `vmp_projects`
**Column**: `soln_critique_data` (JSONB)

**Structure**:
```json
{
  "session_id": "uuid",
  "status": "completed",
  "generated_at": "2024-11-20T10:55:00Z",
  "critique_report": {
    "executive_summary": {...},
    "critiques_by_dimension": {...},
    "all_critiques": [...],
    "sources": [...],
    "metadata": {
      "ai_model": "gpt-4.1",
      "total_critiques": 15,
      "total_citations": 127
    }
  }
}
```

---

## ✅ Summary

**Models**:
- GPT-4 (Azure): 7 calls per critique
- GPT-4o-mini: 1 call per chat message

**Processing Time**: 45-60 seconds

**Output**: Structured JSON with citations

**Chat**: RAG-based with vector search

**Storage**: JSONB in vmp_projects table
