# Solution Critique - Documentation & Implementation Guide

## 📚 Documentation Overview

This folder contains the complete specifications and implementation guide for the **Solution Critique** feature - an AI-powered reality-check system that analyzes proposed solutions using VPC v2, VPS, and BMC data combined with web research.

---

## 📄 Available Documents

### 1. **SOLUTION_CRITIQUE_ARCHITECTURE.md** ⭐ (Architecture Reference)
**Purpose:** Complete technical architecture and design specifications

**Contents:**
- System architecture & workflow
- LangGraph node structure
- All 5 critique agent specifications
- Database schema & storage
- AI service integration patterns
- API endpoint specifications
- JSON schema definitions
- Error handling strategies
- Performance characteristics

**Use this:** As your reference manual during implementation. Everything you need to know about how the system works.

**Size:** Comprehensive (50+ pages equivalent)

---

### 2. **SOLUTION_CRITIQUE_IMPLEMENTATION_PLAN.md** (Implementation Guide)
**Purpose:** Step-by-step implementation tasks with code examples

**Contents:**
- Phase-by-phase breakdown (6 phases)
- Task-by-task implementation steps
- Complete code examples for each component
- Testing strategies per phase
- Time estimates per task
- Prerequisites and setup

**Use this:** As your implementation checklist. Follow it sequentially to build the feature.

**Size:** Detailed (40+ pages equivalent)

**Status:** Partially complete (Phases 1-3 detailed, see summary for Phases 4-6)

---

### 3. **IMPLEMENTATION_SUMMARY.md** ⚡ (Quick Reference)
**Purpose:** Condensed implementation guide with key points

**Contents:**
- Quick task breakdown (20 tasks)
- Total time estimate (4-5 days)
- Key implementation points
- Critical success factors
- Testing strategy summary
- Day-by-day implementation order

**Use this:** As your quick reference and checklist. Start here if you want the TL;DR.

**Size:** Concise (5 pages)

---

### 4. **README.md** (This File)
**Purpose:** Navigation and overview

---

## 🚀 Quick Start Guide

### For Developers Starting Implementation:

#### Step 1: Understand the Feature (30 minutes)
1. Read `IMPLEMENTATION_SUMMARY.md` first (overview)
2. Skim `SOLUTION_CRITIQUE_ARCHITECTURE.md` sections 1-3 (high-level architecture)
3. Understand the workflow: Context → Queries → Research → 5 Parallel Critiques → Synthesis

#### Step 2: Setup Environment (30 minutes)
1. Verify environment variables:
   ```bash
   # Azure OpenAI
   echo $AZURE_OPENAI_ENDPOINT
   echo $AZURE_OPENAI_API_KEY
   
   # Brave Search
   echo $BRAVE_API_KEY
   ```

2. Execute database migration:
   ```sql
   ALTER TABLE vmp_projects 
   ADD COLUMN IF NOT EXISTS soln_critique_data JSONB DEFAULT NULL;
   
   CREATE INDEX IF NOT EXISTS idx_vmp_projects_soln_critique 
   ON vmp_projects USING gin (soln_critique_data);
   ```

3. Create folder structure:
   ```bash
   cd /Users/samikd/MyProjects/Yuba/Backend/src/mvp/soln_critique
   mkdir -p agents services models prompts api
   touch __init__.py agents/__init__.py services/__init__.py models/__init__.py prompts/__init__.py api/__init__.py
   ```

#### Step 3: Implement Phase by Phase (4-5 days)
Follow either:
- **Detailed:** `SOLUTION_CRITIQUE_IMPLEMENTATION_PLAN.md` (task-by-task with code)
- **Quick:** `IMPLEMENTATION_SUMMARY.md` (condensed checklist)

**Recommended approach:**
- Use SUMMARY for daily planning
- Use IMPLEMENTATION_PLAN for detailed code examples
- Use ARCHITECTURE for reference when stuck

#### Step 4: Test Continuously
- Test after each phase
- See testing strategy in IMPLEMENTATION_SUMMARY.md
- Reference test examples in IMPLEMENTATION_PLAN.md

---

## 🎯 Key Features

### What Makes This Feature Unique

1. **Parallel Critique Generation** ⚡
   - All 5 critique agents run simultaneously
   - LangGraph orchestrates parallel execution
   - Reduces total processing time by 5x

2. **Web Research Integration** 🌐
   - 15-20 targeted Brave Search queries
   - Evidence-based critiques (not just opinions)
   - Cites web sources with URLs

3. **JSON Output Only** 📊
   - Structured, parseable output
   - No markdown fallback
   - Ready for frontend consumption

4. **GPT-4.1 Powered** 🤖
   - Azure OpenAI GPT-4.1 via existing service
   - AI monitoring integrated
   - Token usage tracked

5. **5 Critique Dimensions** 🔍
   - Market Viability
   - Operational Feasibility
   - Business Model
   - Competitive Differentiation
   - Technical Scalability

6. **Strict Citation System** 📚 (Following PV Report Standards)
   - Numbered citations [1], [2], [3] embedded in all text
   - Sources section with complete references
   - Every factual claim must be cited
   - Minimum 5-8 citations per critique
   - Citation tracking and validation

---

## 📊 System Architecture at a Glance

```
User Request
    ↓
Context Preparation (VPC v2 + VPS + BMC)
    ↓
Query Planning (GPT-4.1 generates 15-20 queries)
    ↓
Web Research (Brave Search parallel batches)
    ↓
┌─────────────────────────────────────────┐
│  PARALLEL CRITIQUE GENERATION           │
├─────────────────────────────────────────┤
│ • Market Viability Agent                │
│ • Operational Feasibility Agent         │
│ • Business Model Agent                  │
│ • Competitive Differentiation Agent     │
│ • Technical Scalability Agent           │
└─────────────────────────────────────────┘
    ↓ (All complete)
Report Synthesis (GPT-4.1 generates executive summary)
    ↓
Store to Database (vmp_projects.soln_critique_data)
    ↓
JSON Response to User
```

**Total Time:** 45-60 seconds

---

## 📁 Folder Structure

```
/Backend/src/mvp/soln_critique/
├── README.md                                    # This file
├── SOLUTION_CRITIQUE_ARCHITECTURE.md            # Architecture reference
├── SOLUTION_CRITIQUE_IMPLEMENTATION_PLAN.md     # Implementation guide
├── IMPLEMENTATION_SUMMARY.md                    # Quick reference
│
├── agents/                                      # All critique agents
│   ├── __init__.py
│   ├── base_critique_agent.py                   # Abstract base
│   ├── market_viability_agent.py
│   ├── operational_feasibility_agent.py
│   ├── business_model_agent.py
│   ├── competitive_differentiation_agent.py
│   ├── technical_scalability_agent.py
│   └── report_synthesizer_agent.py
│
├── services/                                    # Core services
│   ├── __init__.py
│   ├── critique_workflow.py                     # LangGraph orchestration
│   ├── context_loader.py                        # Load VPC/VPS/BMC
│   ├── query_planner.py                         # Generate search queries
│   └── web_researcher.py                        # Execute Brave Search
│
├── models/                                      # Data models
│   ├── __init__.py
│   ├── state_models.py                          # LangGraph state
│   └── response_models.py                       # API responses
│
├── prompts/                                     # AI prompts
│   ├── __init__.py
│   ├── query_planning_prompt.py
│   ├── market_viability_prompt.py
│   ├── operational_feasibility_prompt.py
│   ├── business_model_prompt.py
│   ├── competitive_differentiation_prompt.py
│   ├── technical_scalability_prompt.py
│   └── synthesizer_prompt.py
│
└── api/                                         # API endpoints
    ├── __init__.py
    └── endpoints.py                             # FastAPI routes
```

---

## 🔑 Key Implementation Points

### ✅ Must Follow

1. **Reuse Existing Services**
   - AI Service: `/src/market_research/utils/ai_service_wrapper.py`
   - Brave Search: `/src/mint/providers/search.py`
   - Database Adapter: `/src/mvp/adapters/database_adapter.py`
   - AI Monitoring: `monitor.tokens.service`

2. **Parallel Critique Execution**
   ```python
   # All 5 agents run simultaneously
   workflow.add_edge("execute_research", "market_critique")
   workflow.add_edge("execute_research", "operational_critique")
   workflow.add_edge("execute_research", "business_model_critique")
   workflow.add_edge("execute_research", "competitive_critique")
   workflow.add_edge("execute_research", "technical_critique")
   ```

3. **JSON Output Only**
   ```python
   # Force JSON mode
   response = await ai_service.generate_analysis_response(
       messages=messages,
       json_mode=True,  # CRITICAL
       monitoring_context=monitoring_context
   )
   ```

4. **AI Monitoring Integration**
   ```python
   from monitor.tokens.models import AIUsageContext
   
   monitoring_context = AIUsageContext(
       tenant_id=tenant_id,
       user_id=user_id,
       feature_name="solution_critique",
       operation_name="market_viability_critique",
       project_id=project_id
   )
   ```

5. **Database Storage**
   ```python
   # Store in vmp_projects.soln_critique_data (JSONB column)
   critique_data = {
       'session_id': session_id,
       'status': 'completed',
       'critique_report': final_report  # JSON structure with citations
   }
   ```

6. **Citation System** (Following PV Report Standards)
   ```python
   # Every critique must include:
   {
     "problem": "Market demand is unvalidated [1]. Only 15% adoption [2]...",
     "sources": [
       {"id": 1, "type": "bmc", "field": "customer_segments", ...},
       {"id": 2, "type": "web", "title": "Market Report", "url": "...", ...}
     ],
     "citation_count": 8,
     "unique_sources_used": 6
   }
   
   # Citation requirements:
   - Numbered format: [1], [2], [3]
   - Every claim cited
   - Minimum 5-8 citations per critique
   - Source types: web, bmc, vpc, vps
   ```

---

## 🧪 Testing Strategy

### Unit Tests
- Context Loader
- Query Planner
- Web Researcher
- Each Critique Agent
- Report Synthesizer

### Integration Tests
- LangGraph workflow
- Parallel execution
- Database operations
- API endpoints

### End-to-End Tests
- Complete flow
- Error scenarios
- Performance benchmarks

---

## 📝 API Endpoints

### 1. Generate Critique
```
POST /api/v2/vmp/projects/{project_id}/solution-critique/generate
```

### 2. Check Status
```
GET /api/v2/vmp/projects/{project_id}/solution-critique/status
```

### 3. Get Results
```
GET /api/v2/vmp/projects/{project_id}/solution-critique/results
```

---

## 🔍 Reference Materials

### Existing Implementations to Study
1. **Market Research Analysis** (`/src/market_research/`)
   - LangGraph parallel processing
   - AI service wrapper usage
   - AI monitoring integration

2. **BMC Generation** (`/src/mvp/bmc/`)
   - Context loading patterns
   - Database storage
   - Sequential AI generation

3. **VPM Module** (`/src/vpm/`)
   - Database adapter patterns
   - JSONB operations
   - API endpoint structures

---

## ⏱️ Time Estimates

- **Day 1:** Foundation + Core Services (6-8 hours)
- **Day 2:** Base Agent + 2 Critique Agents (8 hours)
- **Day 3:** Remaining Agents + Synthesizer (8 hours)
- **Day 4:** Workflow + API (6 hours)
- **Day 5:** Testing + Polish (6-8 hours)

**Total:** 4-5 days (32-40 hours)

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Loads VPC v2, VPS, and BMC from project
- ✅ Generates 15-20 targeted search queries
- ✅ Executes web research with Brave Search
- ✅ Generates 5 critique dimensions in parallel
- ✅ Produces structured JSON report
- ✅ **All critiques have numbered citations [1][2][3]**
- ✅ **Every critique has sources section**
- ✅ **Minimum 5-8 citations per critique**
- ✅ **Citation validation passes**
- ✅ Stores results in database
- ✅ Provides status and results via API

### Non-Functional Requirements
- ✅ Completes in 45-60 seconds
- ✅ Uses GPT-4.1 via Azure OpenAI
- ✅ Tracks AI usage with monitoring
- ✅ Handles errors gracefully
- ✅ Supports parallel execution
- ✅ Provides evidence citations

---

## 🆘 Getting Help

### Stuck on Implementation?
1. Check **ARCHITECTURE.md** for detailed specifications
2. Review **IMPLEMENTATION_PLAN.md** for code examples
3. Study similar implementations (Market Research, BMC)
4. Check existing services for patterns

### Common Issues
1. **Missing data error** → Ensure VPC/VPS/BMC are generated first
2. **Parallel execution not working** → Check LangGraph edge definitions
3. **JSON parsing error** → Verify json_mode=True in AI service calls
4. **Monitoring not tracking** → Ensure monitoring_context is passed

---

## 📖 Reading Order Recommendations

### For Quick Start (1 hour)
1. This README (10 min)
2. IMPLEMENTATION_SUMMARY.md (20 min)
3. ARCHITECTURE.md sections 1-3 (30 min)

### For Deep Understanding (3 hours)
1. This README (10 min)
2. IMPLEMENTATION_SUMMARY.md (30 min)
3. ARCHITECTURE.md (complete) (90 min)
4. IMPLEMENTATION_PLAN.md sections 1-3 (50 min)

### For Implementation (Ongoing)
- Day-by-day: Follow IMPLEMENTATION_SUMMARY.md
- Per-task: Refer to IMPLEMENTATION_PLAN.md for code
- When stuck: Check ARCHITECTURE.md for specs

---

## 🚦 Status

- ✅ Architecture designed
- ✅ Documentation complete
- ⏳ Implementation pending
- ⏳ Testing pending

---

**Ready to build! Start with IMPLEMENTATION_SUMMARY.md and follow the phases.**

**Questions? Check ARCHITECTURE.md for detailed answers.**
