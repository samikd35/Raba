# Solution Critique - Quick Implementation Summary

## Documents Created

1. **SOLUTION_CRITIQUE_ARCHITECTURE.md** - Complete architecture reference
2. **SOLUTION_CRITIQUE_IMPLEMENTATION_PLAN.md** - Detailed step-by-step guide (partial)

## Implementation Task Breakdown

### Phase 1: Foundation (Day 1)
**Time: 3-4 hours**

1. ✅ Create folder structure (10 min)
2. ✅ Create state models (30 min)
3. ✅ Create response models (20 min)
4. ✅ Add database column (5 min)

### Phase 2: Core Services (Day 1-2)
**Time: 3-4 hours**

5. Context Loader (45 min) - Load VPC/VPS/BMC from database
6. Query Planner (1 hour) - Generate search queries with GPT-4.1
7. Web Researcher (45 min) - Execute Brave Search in parallel batches

### Phase 3: Critique Agents (Day 2-3)
**Time: 8-10 hours**

8. Base Critique Agent (1 hour) - Abstract base class
9. Market Viability Agent (1 hour)
10. Operational Feasibility Agent (1.5 hours)
11. Business Model Agent (1.5 hours)
12. Competitive Differentiation Agent (1.5 hours)
13. Technical Scalability Agent (1.5 hours)
14. Report Synthesizer Agent (1.5 hours)

### Phase 4: Workflow (Day 3-4)
**Time: 3-4 hours**

15. LangGraph Workflow (2 hours) - Orchestrate all agents (PARALLEL critique generation)
16. Database Integration (1 hour) - Save/load critique data from vmp_projects.soln_critique_data

### Phase 5: API Layer (Day 4)
**Time: 2-3 hours**

17. Generate Endpoint (1 hour) - POST /api/v2/vmp/projects/{id}/solution-critique/generate
18. Status Endpoint (30 min) - GET /api/v2/vmp/projects/{id}/solution-critique/status
19. Results Endpoint (30 min) - GET /api/v2/vmp/projects/{id}/solution-critique/results

### Phase 6: Testing (Day 5)
**Time: 4-6 hours**

20. Unit tests for services (2 hours)
21. Integration tests for workflow (2 hours)
22. End-to-end API tests (2 hours)

---

## Total Estimated Time: 4-5 Days

---

## Citation System Requirements

### Strict Citation Standards (Following PV Report)

**CRITICAL:** Every critique must follow PV report citation standards:

1. **Numbered Citations**: Use [1], [2], [3] format in all text
2. **Sources Section**: Maintain numbered list of all sources
3. **Every Claim Cited**: No unsupported statements allowed
4. **Citation Tracking**: Track citation_count and unique_sources_used

### Citation Implementation Pattern

```python
# Step 1: Build sources list
sources = []
for web_result in web_results:
    sources.append({
        "id": len(sources) + 1,
        "type": "web",
        "title": web_result['title'],
        "url": web_result['url'],
        "snippet": web_result['snippet'][:200]
    })

# Step 2: Generate critique with citations
prompt = f"""
Generate critique with citations [1], [2], [3].

SOURCES:
{format_sources_for_prompt(sources)}

Requirements:
- Every claim must have [N] citation
- Minimum 5-8 citations per critique
- Use [1][2] for multiple sources
"""

# Step 3: Validate citations
import re
citations = re.findall(r'\[(\d+)\]', critique_text)
citation_count = len(set(citations))

# Step 4: Return with metadata
return {
    "problem": critique_text,  # With [1][2] citations
    "sources": sources,  # Numbered list
    "citation_count": citation_count,
    "unique_sources_used": len(set(citations))
}
```

---

## Key Implementation Points

### 1. Reuse Existing Services ✅
- **AI Service**: `/src/market_research/utils/ai_service_wrapper.py`
- **Brave Search**: `/src/mint/providers/search.py`
- **Database Adapter**: `/src/mvp/adapters/database_adapter.py`
- **AI Monitoring**: `monitor.tokens.service`

### 2. Parallel Critique Generation ✅
```python
# All 5 critique agents run SIMULTANEOUSLY after research
workflow.add_edge("execute_research", "market_critique")
workflow.add_edge("execute_research", "operational_critique")
workflow.add_edge("execute_research", "business_model_critique")
workflow.add_edge("execute_research", "competitive_critique")
workflow.add_edge("execute_research", "technical_critique")

# All converge to synthesis
workflow.add_edge("market_critique", "synthesize_report")
workflow.add_edge("operational_critique", "synthesize_report")
# ... etc
```

### 3. JSON Output Only ✅
```python
# Force JSON mode in all AI calls
response = await ai_service.generate_analysis_response(
    messages=messages,
    json_mode=True,  # CRITICAL
    monitoring_context=monitoring_context
)

# Parse JSON response
critique_data = json.loads(response['content'])
```

### 4. GPT-4.1 Model ✅
```python
# AIServiceWrapper automatically uses GPT-4.1 from Azure OpenAI
# Already configured in existing system
ai_service = get_ai_service_wrapper()
```

### 5. AI Monitoring ✅
```python
from monitor.tokens.models import AIUsageContext

monitoring_context = AIUsageContext(
    tenant_id=tenant_id,
    user_id=user_id,
    feature_name="solution_critique",
    operation_name="market_viability_critique",
    project_id=project_id
)

# Pass to AI service
await ai_service.generate_analysis_response(
    messages=messages,
    monitoring_context=monitoring_context  # CRITICAL
)
```

### 6. Database Storage ✅
```python
# Store in vmp_projects.soln_critique_data
critique_data = {
    'session_id': session_id,
    'status': 'completed',
    'generated_at': datetime.utcnow().isoformat(),
    'critique_report': final_report  # JSON structure
}

# Use existing database adapter
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter
db_adapter = MVPDatabaseAdapter(use_service_role=True)

# Update project
response = db_adapter.supabase.client.table('vmp_projects').update({
    'soln_critique_data': critique_data,
    'updated_at': datetime.utcnow().isoformat()
}).eq('id', project_id).eq('tenant_id', tenant_id).execute()
```

---

## Implementation Order

### Day 1: Foundation + Core Services
1. Create folder structure
2. Create models (state + response)
3. Execute database migration
4. Implement Context Loader
5. Implement Query Planner
6. Implement Web Researcher
7. **Test:** Can load context, generate queries, execute searches

### Day 2: Base Agent + 2 Critique Agents
1. Implement Base Critique Agent
2. Implement Market Viability Agent
3. Implement Operational Feasibility Agent
4. **Test:** Can generate 2 critique dimensions

### Day 3: Remaining Agents + Synthesizer
1. Implement Business Model Agent
2. Implement Competitive Differentiation Agent
3. Implement Technical Scalability Agent
4. Implement Report Synthesizer Agent
5. **Test:** Can generate all 5 critiques + synthesis

### Day 4: Workflow + API
1. Implement LangGraph Workflow (parallel execution)
2. Implement Generate Endpoint (async/background)
3. Implement Status Endpoint
4. Implement Results Endpoint
5. **Test:** End-to-end flow works

### Day 5: Testing + Polish
1. Write unit tests
2. Write integration tests
3. Test error handling
4. Test parallel execution
5. Test AI monitoring
6. Performance testing

---

## Critical Success Factors

### ✅ Must Have
1. **Parallel critique execution** - All 5 agents run simultaneously
2. **JSON output only** - No markdown fallback
3. **GPT-4.1 model** - Use Azure OpenAI via existing service
4. **AI monitoring** - Track all AI calls via monitor.tokens.service
5. **Database column** - Store in vmp_projects.soln_critique_data
6. **Reuse services** - Don't reinvent AI service, search provider, database adapter

### ⚠️ Watch Out For
1. **Memory management** - Parallel execution requires careful state handling
2. **Rate limiting** - Brave Search API has limits
3. **AI token limits** - Monitor GPT-4 token usage per critique
4. **Error handling** - Handle agent failures gracefully
5. **State synchronization** - LangGraph manages this, but be aware

---

## Testing Strategy

### Unit Tests
- Context Loader: Can load VPC/VPS/BMC
- Query Planner: Generates 15-20 queries
- Web Researcher: Executes searches with retry
- Each Agent: Generates valid JSON critique
- Synthesizer: Combines critiques into report

### Integration Tests
- Workflow: All nodes execute in correct order
- Parallel Execution: 5 agents run simultaneously
- Database: Can save/load critique data
- API: Generate/status/results endpoints work

### End-to-End Tests
- Complete flow: Context → Queries → Research → Critique → Report
- Error scenarios: Missing data, API failures
- Performance: Completes in 45-60 seconds

---

## Next Steps

1. **Read both documentation files fully**
2. **Execute database migration**
3. **Follow implementation plan phase by phase**
4. **Test after each phase**
5. **Refer to architecture doc for detailed specifications**

---

## Key Files to Reference

### Existing Implementations to Study
- `/src/market_research/services/analysis_workflow.py` - LangGraph parallel processing
- `/src/market_research/utils/ai_service_wrapper.py` - AI service with monitoring
- `/src/mint/providers/search.py` - Brave Search provider
- `/src/mvp/adapters/database_adapter.py` - Database operations

### Similar Patterns
- Market Research: Parallel agent execution, streaming results
- BMC Generation: Context loading, sequential generation
- VPM: Database storage patterns, JSONB operations

---

**Ready to implement! Start with Phase 1.**
