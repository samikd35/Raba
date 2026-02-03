# Solution Critique Chat Functionality - Design Document

## 📚 Learnings from Market Research Analysis Chat

### Architecture Overview

The Market Research Analysis chat uses a **RAG (Retrieval-Augmented Generation)** architecture with these key components:

1. **Report Chunking Service** - Converts JSON reports into searchable text chunks
2. **Vector Storage** - Stores chunks with embeddings in Supabase `chunks` table  
3. **Chat Service** - Retrieves relevant chunks and generates responses
4. **Conversation Memory** - Client-side history management

---

## 🔍 Deep Dive: How Market Research Chat Works

### 1. Report Preparation & Chunking

**File**: `src/market_research/services/report_chunking_service.py`

#### Process Flow:
```
JSON Report (structured_report)
    ↓
Extract sections (executive summary, assumptions, research data)
    ↓
Convert each section to formatted text
    ↓
Split text into chunks (~1000 chars, 200 char overlap)
    ↓
Generate embeddings for each chunk (OpenAI embeddings)
    ↓
Store in Supabase `chunks` table with metadata
```

#### Key Implementation Details:

**Chunking Configuration**:
```python
self.chunk_size = 1000  # Characters per chunk
self.chunk_overlap = 200  # Overlap between chunks
```

**Chunk Creation**:
- Executive summary → Multiple chunks
- Each assumption analysis → Multiple chunks  
- Research data summary → Multiple chunks
- Chunks have metadata:
  - `source_type`: "analysis_report"
  - `section`: "executive_summary", "assumption_1", etc.
  - `persona_id`: For multi-persona support
  - `project_id`, `tenant_id`: For filtering

**Storage Strategy**:
```python
# CRITICAL: Only delete analysis_report chunks, preserve uploaded docs
report_chunk_ids = [
    chunk['id'] for chunk in existing_chunks 
    if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
    and chunk.get('metadata', {}).get('persona_id') == persona_id
]
# Delete old, insert new
```

**Automatic Triggering**:
```python
# In market_research_analysis_service.py - AFTER database save
await self.analysis_db_adapter.update_analysis_data(...)  # Save first

# Then chunk report (critical: must be after DB save)
if analysis_results.get("structured_report"):
    chunking_service = ReportChunkingService()
    await chunking_service.chunk_and_embed_report(
        project_id=project_id,
        tenant_id=tenant_id,
        persona_id=persona_id
    )
```

---

### 2. Chat Retrieval (RAG)

**File**: `src/market_research/services/chat_service.py`

#### Process Flow:
```
User Question
    ↓
Generate query embedding
    ↓
Vector similarity search in chunks table
    ↓
Filter by: source_type="analysis_report", persona_id (if multi-persona)
    ↓
Calculate cosine similarity scores
    ↓
Return top N chunks (sorted by relevance)
    ↓
Build context string from chunks
    ↓
Send to LLM with system prompt
    ↓
Return grounded response
```

#### Key Implementation Details:

**Context Retrieval**:
```python
async def _retrieve_context(self, project_id, tenant_id, query, persona_id):
    # 1. Get report chunks (analysis_report type)
    report_chunks = await self._retrieve_report_chunks(
        project_id, tenant_id, query, max_chunks=15, persona_id=persona_id
    )
    
    # 2. Get uploaded document chunks (csv/pdf type)
    research_chunks = await self._retrieve_research_chunks(
        project_id, tenant_id, query, max_chunks=20, persona_id=persona_id
    )
    
    return {
        "research_chunks": research_chunks,
        "report_chunks": report_chunks,
        "has_context": len(research_chunks) > 0 or len(report_chunks) > 0
    }
```

**Vector Search**:
```python
# Get all chunks for project
all_chunks = await chunk_service.get_chunks_by_report_id(project_id)

# Filter by source_type and persona_id
report_chunks = [
    chunk for chunk in all_chunks
    if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
    and chunk.get('metadata', {}).get('persona_id') == persona_id
]

# Generate query embedding
query_embedding = await embedding_service.generate_embeddings([query])

# Calculate cosine similarity
for chunk in report_chunks:
    similarity = np.dot(query_embedding, chunk_embedding) / (
        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
    )

# Sort by similarity, return top N
```

**LLM Response Generation**:
```python
system_prompt = """You are a helpful AI assistant analyzing market research data.
ONLY use information from the provided context.
If answer not in context, say so.
Cite sources when possible."""

context_text = "\n\n=== ANALYSIS REPORT ===\n" + "\n\n".join([
    f"[Analysis Report Section]\n{chunk['content']}"
    for chunk in report_chunks
])

response = await ai_service.generate_analysis_response(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{context_text}\n\nQUESTION: {user_message}"}
    ],
    model="gpt-4o-mini",  # Cost-effective
    max_tokens=1000,
    temperature=0.3  # Low for factual responses
)
```

---

### 3. Conversation Memory

**Strategy**: Client-side history management

```python
# Client sends history with each request
conversation_history = [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"},
    {"role": "user", "content": "New question"}
]

# Server updates and returns
updated_history = conversation_history + [
    {"role": "user", "content": user_message},
    {"role": "assistant", "content": generated_response}
]

# Keep only last 10 messages (20 total with pairs)
if len(updated_history) > 20:
    updated_history = updated_history[-20:]
```

**Benefits**:
- No database storage needed
- Stateless server (scalable)
- User controls history (can clear anytime)

---

### 4. API Endpoints

**File**: `src/market_research/api/chat_endpoints.py`

#### 1. Prepare Report for Chat
```
POST /api/v1/market-research/analysis/chat/projects/{project_id}/prepare-report
```

**Purpose**: Chunk and embed the report AFTER analysis completes

**Flow**:
1. Validate analysis is complete
2. Load structured report from database
3. Create chunks with embeddings
4. Store in vector database

**When Called**: 
- Manually by user/frontend after analysis completes
- Automatically in service layer after DB save (recommended)

---

#### 2. Send Chat Message
```
POST /api/v1/market-research/analysis/chat/projects/{project_id}/message

Body:
{
  "message": "What are the key findings?",
  "persona_id": "persona-uuid",  // For multi-persona
  "conversation_history": [...]   // Previous messages
}
```

**Response**:
```json
{
  "success": true,
  "answer": "Based on the analysis report...",
  "sources": [
    {
      "type": "analysis_report",
      "section_count": 5,
      "chunk_count": 15
    }
  ],
  "context_used": {
    "research_chunks": 0,
    "report_chunks": 5
  },
  "conversation_history": [...],  // Updated history
  "timestamp": "2024-..."
}
```

---

#### 3. Clear Conversation
```
POST /api/v1/market-research/analysis/chat/projects/{project_id}/clear
```

**Purpose**: Reset conversation history (client-side)

---

#### 4. Chat Status
```
GET /api/v1/market-research/analysis/chat/projects/{project_id}/status
```

**Response**:
```json
{
  "chat_ready": true,
  "status": {
    "analysis_complete": true,
    "report_prepared": true
  },
  "available_sources": {
    "analysis_assumptions": 5,
    "report_chunks": 15
  }
}
```

---

## 🎯 Critical Lessons Learned

### ⚠️ CRITICAL FIX: Timing Issue

**Problem**: Original implementation tried to chunk report BEFORE saving to database

```python
# ❌ WRONG - In workflow _finalize_analysis():
async def _finalize_analysis(self, state):
    if state.get("structured_report"):
        # Tries to chunk here - report not in DB yet!
        await chunking_service.chunk_and_embed_report(...)  # FAILS
    return state
```

**Solution**: Chunk AFTER database save in service layer

```python
# ✅ CORRECT - In service execute_analysis():
# 1. Save to database first
await self.db_adapter.update_analysis_data(project_id, tenant_id, analysis_results)

# 2. THEN chunk report (now it's in the database)
if analysis_results.get("structured_report"):
    await chunking_service.chunk_and_embed_report(project_id, tenant_id)
```

**Lesson**: Always chunk/embed AFTER the source data is persisted in database.

---

### 🎭 Multi-Persona Support

**Challenge**: Projects can have multiple personas, each with their own analysis

**Solution**: Tag chunks with `persona_id` in metadata

```python
metadata = {
    "source_type": "analysis_report",
    "persona_id": persona_id,  # Critical for isolation
    "project_id": project_id,
    # ...
}

# Retrieval filters by persona_id
chunks = [
    chunk for chunk in all_chunks
    if chunk.get('metadata', {}).get('persona_id') == persona_id
]
```

---

### 🗑️ Smart Deletion Strategy

**Challenge**: Don't delete uploaded document chunks when updating report chunks

**Solution**: Selective deletion by source_type

```python
# Only delete analysis_report chunks for this persona
report_chunk_ids = [
    chunk['id'] for chunk in existing_chunks 
    if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
    and chunk.get('metadata', {}).get('persona_id') == persona_id
]

# Delete only those, preserve csv/pdf chunks
for chunk_id in report_chunk_ids:
    supabase.client.table("chunks").delete().eq("id", chunk_id).execute()
```

---

## 📋 Solution Critique Chat Implementation Plan

### Phase 1: Report Chunking Service

**File**: `src/mvp/soln_critique/services/critique_report_chunking_service.py`

**Responsibilities**:
1. Convert critique JSON report to text chunks
2. Generate embeddings
3. Store in `chunks` table with `source_type="solution_critique"`

**Chunk Structure**:
```python
{
    "content": "Executive summary text...",
    "embedding": [0.123, 0.456, ...],
    "metadata": {
        "source_type": "solution_critique",
        "section": "executive_summary",
        "dimension": "market_viability",
        "project_id": "uuid",
        "tenant_id": "uuid",
        "critique_id": "market-001",
        "severity": "high",
        "created_at": "2024-..."
    }
}
```

---

### Phase 2: Chat Service

**File**: `src/mvp/soln_critique/services/critique_chat_service.py`

**Responsibilities**:
1. Retrieve relevant chunks using vector search
2. Build context from chunks
3. Generate grounded responses with LLM
4. Manage conversation history (client-side)

**RAG Flow**:
```
User Question
    ↓
Generate embedding
    ↓
Search chunks (source_type="solution_critique")
    ↓
Calculate similarity scores
    ↓
Get top 10-15 chunks
    ↓
Build context string (executive summary, relevant critiques, sources)
    ↓
LLM with system prompt ("Only use critique data...")
    ↓
Return answer with sources
```

---

### Phase 3: Automatic Report Preparation

**Location**: `src/mvp/soln_critique/services/critique_workflow.py`

**Modification to `_save_to_database_node`**:

```python
async def _save_to_database_node(self, state):
    # ... existing save logic ...
    
    # Save critique to database
    await self.db_adapter.update(...)
    
    # ✅ AUTOMATIC: Prepare report for chat (AFTER save)
    if state['status'] == 'completed' and state.get('final_report'):
        try:
            logger.info("💬 AUTO-PREPARE: Chunking critique report for chat...")
            
            from ..services.critique_report_chunking_service import CritiqueReportChunkingService
            chunking_service = CritiqueReportChunkingService()
            
            result = await chunking_service.chunk_and_embed_report(
                project_id=state['project_id'],
                tenant_id=state['tenant_id']
            )
            
            if result["success"]:
                logger.info(f"✅ AUTO-PREPARE: Chat ready with {result['chunk_count']} chunks")
            else:
                logger.warning(f"⚠️ AUTO-PREPARE: Failed - {result['message']}")
                
        except Exception as e:
            # Non-blocking - chat preparation failure doesn't fail workflow
            logger.error(f"❌ AUTO-PREPARE: Error preparing chat: {e}")
    
    return state
```

---

### Phase 4: API Endpoints

**File**: `src/mvp/soln_critique/api/chat_endpoints.py`

**Endpoints**:

1. **POST** `/api/v2/mvp/projects/{project_id}/solution-critique/chat/message`
   - Send message, get response
   - Include conversation_history in request
   
2. **POST** `/api/v2/mvp/projects/{project_id}/solution-critique/chat/clear`
   - Clear conversation history

3. **GET** `/api/v2/mvp/projects/{project_id}/solution-critique/chat/status`
   - Check if chat is ready

4. **POST** `/api/v2/mvp/projects/{project_id}/solution-critique/chat/prepare` (Optional)
   - Manually prepare report if auto-prepare fails

---

## 🎨 System Prompt Design

```python
system_prompt = """You are a startup advisor helping analyze a solution critique report.

Your role is to answer questions based STRICTLY on the solution critique data provided in the context.

CONTEXT SOURCES:
- Solution critique report with 5 dimensions:
  1. Market Viability
  2. Operational Feasibility
  3. Business Model
  4. Competitive Differentiation
  5. Technical Scalability
- Executive summary with overall assessment
- Prioritized actions and recommendations
- Source citations from web research, BMC, VPC, VPS

CRITICAL RULES:
1. ONLY use information from the solution critique report
2. If answer not in the report, say "I don't have that information in the critique."
3. Cite critique dimensions when relevant (e.g., "According to the market viability critique...")
4. Reference severity levels (high/medium/low) and specific issues
5. Consider conversation history for follow-up questions
6. Be honest about limitations and missing data

DO NOT:
- Make up critiques or issues not in the report
- Speculate beyond what's stated
- Use external knowledge
- Provide generic advice not grounded in the critique

When asked about:
- **Risks**: Cite high-severity critiques with evidence
- **Recommendations**: Use the prioritized actions from the report
- **Sources**: Reference the web research and project data cited
- **Viability**: Use the executive summary overall assessment
"""
```

---

## 📊 Database Schema

**Table**: `chunks` (existing, shared with market research)

**Solution Critique Chunks**:
```sql
{
    "doc_id": "project_uuid",  -- project_id
    "chunk_index": 2050,       -- Unique index after other chunks
    "content": "Market viability critique shows...",
    "embedding": [0.123, ...], -- 1536-dim vector
    "metadata": {
        "source_type": "solution_critique",
        "section": "market_viability",
        "project_id": "project_uuid",
        "tenant_id": "tenant_uuid",
        "critique_id": "market-001",
        "severity": "high",
        "dimension": "market_viability",
        "citation_count": 8,
        "created_at": "2024-11-20T10:30:00Z"
    }
}
```

---

## ✅ Implementation Checklist

### Phase 1: Report Chunking Service
- [ ] Create `CritiqueReportChunkingService`
- [ ] Implement `chunk_and_embed_report()`
- [ ] Format executive summary to text
- [ ] Format each dimension critique to text
- [ ] Format prioritized actions to text
- [ ] Format sources section to text
- [ ] Split text into chunks (1000 chars, 200 overlap)
- [ ] Generate embeddings
- [ ] Store with source_type="solution_critique"
- [ ] Test chunking with sample report

### Phase 2: Chat Service
- [ ] Create `SolutionCritiqueChatService`
- [ ] Implement `chat()` method
- [ ] Implement `_retrieve_context()` with vector search
- [ ] Implement `_generate_response()` with LLM
- [ ] Implement conversation history management
- [ ] Test RAG retrieval accuracy
- [ ] Test response quality

### Phase 3: Automatic Preparation
- [ ] Modify `_save_to_database_node` in workflow
- [ ] Add auto-chunking after DB save
- [ ] Make it non-blocking (errors don't fail workflow)
- [ ] Add comprehensive logging
- [ ] Test auto-prepare triggers correctly

### Phase 4: API Endpoints
- [ ] Create `chat_endpoints.py`
- [ ] Implement message endpoint
- [ ] Implement clear endpoint
- [ ] Implement status endpoint
- [ ] Implement manual prepare endpoint (optional)
- [ ] Add request/response models
- [ ] Register router in main_app.py
- [ ] Test all endpoints

### Phase 5: Testing & Validation
- [ ] Test end-to-end flow
- [ ] Test chat with various questions
- [ ] Test conversation history
- [ ] Test source citations
- [ ] Test error handling
- [ ] Performance testing (response time)
- [ ] Test with multiple projects

---

## 🚀 Next Steps

**Ready to implement?** Let me know and I'll:

1. ✅ Create the chunking service
2. ✅ Create the chat service
3. ✅ Modify the workflow for auto-preparation
4. ✅ Create API endpoints
5. ✅ Register routes
6. ✅ Test everything

**Estimated Time**: 3-4 hours for complete implementation

**Key Success Metrics**:
- Chat responds within 2-3 seconds
- Responses are grounded in critique data (no hallucinations)
- Conversation history works for follow-up questions
- Auto-preparation works after critique generation
- Multiple users can chat simultaneously

---

Let me know when you're ready to proceed! 🎉
