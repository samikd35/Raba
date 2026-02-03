# Solution Critique - Implementation Checklist

Use this as your daily progress tracker during implementation.

---

## Pre-Implementation ☑️

- [ ] Read README.md
- [ ] Read IMPLEMENTATION_SUMMARY.md
- [ ] Skim SOLUTION_CRITIQUE_ARCHITECTURE.md (sections 1-3)
- [ ] Verify environment variables (Azure OpenAI, Brave Search)
- [ ] Execute database migration
- [ ] Create folder structure

---

## Phase 1: Foundation Setup ☑️
**Target: Day 1 Morning (2-3 hours)**

### Task 1.1: Folder Structure
- [ ] Create all folders (agents, services, models, prompts, api)
- [ ] Create all `__init__.py` files
- [ ] Verify structure matches documentation

### Task 1.2: Database Migration
- [ ] Execute ALTER TABLE to add soln_critique_data column
- [ ] Execute CREATE INDEX command
- [ ] Verify column exists in vmp_projects table

### Task 1.3: State Models
- [ ] Create `models/state_models.py`
- [ ] Define `SolutionCritiqueState` (TypedDict)
- [ ] Define `CritiqueResult` (TypedDict)
- [ ] Define `SearchQuery` (TypedDict)
- [ ] Test: Can import models

### Task 1.4: Response Models
- [ ] Create `models/response_models.py`
- [ ] Define `CritiqueGenerateRequest` (Pydantic)
- [ ] Define `CritiqueGenerateResponse` (Pydantic)
- [ ] Define `CritiqueStatusResponse` (Pydantic)
- [ ] Define `CritiqueResultsResponse` (Pydantic)
- [ ] Test: Can import and validate models

---

## Phase 2: Core Services ☑️
**Target: Day 1 Afternoon (3-4 hours)**

### Task 2.1: Context Loader
- [ ] Create `services/context_loader.py`
- [ ] Implement `ContextLoader` class
- [ ] Implement `load_project_context()` method
- [ ] Implement helper methods (_extract_geography, etc.)
- [ ] Test: Can load VPC/VPS/BMC data
- [ ] Test: Returns proper error messages

### Task 2.2: Query Planner
- [ ] Create `services/query_planner.py`
- [ ] Implement `QueryPlanner` class
- [ ] Implement `plan_research_queries()` method
- [ ] Build system and user prompts
- [ ] Implement fallback queries
- [ ] Test: Generates 15-20 queries
- [ ] Test: AI monitoring works
- [ ] Verify: JSON output only

### Task 2.3: Web Researcher
- [ ] Create `services/web_researcher.py`
- [ ] Implement `WebResearcher` class
- [ ] Implement `execute_research()` method
- [ ] Implement batch execution logic
- [ ] Implement retry logic
- [ ] Test: Can execute single query
- [ ] Test: Can execute batch queries
- [ ] Test: Handles rate limits

---

## Phase 3: Critique Agents ☑️
**Target: Day 2-3 (8-10 hours)**

### Task 3.1: Base Critique Agent
- [ ] Create `agents/base_critique_agent.py`
- [ ] Implement `BaseCritiqueAgent` abstract class
- [ ] Define abstract methods (get_dimension, get_system_prompt, etc.)
- [ ] Implement `generate_critique()` method
- [ ] Implement prompt building logic with citation requirements
- [ ] Implement validation logic
- [ ] **Implement citation validation** (regex check for [1], [2], etc.)
- [ ] **Implement source collection** (web + BMC + VPC + VPS)
- [ ] **Implement citation tracking** (citation_count, unique_sources_used)
- [ ] Test: Can instantiate concrete subclass
- [ ] Verify: AI monitoring integration
- [ ] **Verify: Citations present in output** ([1][2][3] format)
- [ ] **Verify: Sources list included** (numbered sources)
- [ ] **Verify: Minimum 5 citations per critique**

### Task 3.2: Market Viability Agent
- [ ] Create `agents/market_viability_agent.py`
- [ ] Extend `BaseCritiqueAgent`
- [ ] Implement all abstract methods
- [ ] Define system prompt
- [ ] Test: Generates valid critique
- [ ] Verify: JSON output only
- [ ] Verify: Evidence citations present

### Task 3.3: Operational Feasibility Agent
- [ ] Create `agents/operational_feasibility_agent.py`
- [ ] Extend `BaseCritiqueAgent`
- [ ] Implement all abstract methods
- [ ] Define system prompt
- [ ] Test: Generates valid critique

### Task 3.4: Business Model Agent
- [ ] Create `agents/business_model_agent.py`
- [ ] Extend `BaseCritiqueAgent`
- [ ] Implement all abstract methods
- [ ] Define system prompt
- [ ] Test: Generates valid critique

### Task 3.5: Competitive Differentiation Agent
- [ ] Create `agents/competitive_differentiation_agent.py`
- [ ] Extend `BaseCritiqueAgent`
- [ ] Implement all abstract methods
- [ ] Define system prompt
- [ ] Test: Generates valid critique

### Task 3.6: Technical Scalability Agent
- [ ] Create `agents/technical_scalability_agent.py`
- [ ] Extend `BaseCritiqueAgent`
- [ ] Implement all abstract methods
- [ ] Define system prompt
- [ ] Test: Generates valid critique

### Task 3.7: Report Synthesizer Agent
- [ ] Create `agents/report_synthesizer_agent.py`
- [ ] Implement `CritiqueReportSynthesizerAgent` class
- [ ] Implement `synthesize_report()` method
- [ ] Implement severity calculation
- [ ] Implement grouping by dimension
- [ ] Test: Combines multiple critiques
- [ ] Test: Generates executive summary
- [ ] Verify: JSON output structure

---

## Phase 4: Workflow Orchestration ☑️
**Target: Day 3-4 (3-4 hours)**

### Task 4.1: LangGraph Workflow
- [ ] Create `services/critique_workflow.py`
- [ ] Implement `SolutionCritiqueWorkflow` class
- [ ] Initialize all agents
- [ ] Build LangGraph workflow graph
- [ ] Define all nodes (prepare, plan, research, 5 critiques, synthesize)
- [ ] Define workflow edges (sequential then parallel)
- [ ] Verify: Parallel execution configured correctly
- [ ] Implement all node functions
- [ ] Test: Workflow executes end-to-end
- [ ] Test: All 5 critiques run in parallel

### Task 4.2: Database Integration
- [ ] Add save method to workflow
- [ ] Implement load method for status checks
- [ ] Store complete critique data in soln_critique_data column
- [ ] Test: Can save to database
- [ ] Test: Can retrieve from database
- [ ] Verify: JSONB structure correct

---

## Phase 5: API Layer ☑️
**Target: Day 4 (2-3 hours)**

### Task 5.1: Generate Endpoint
- [ ] Create `api/endpoints.py`
- [ ] Implement POST /solution-critique/generate endpoint
- [ ] Add async/background processing (optional)
- [ ] Validate required data (VPC/VPS/BMC) exists
- [ ] Handle force_regenerate flag
- [ ] Return 202 Accepted response
- [ ] Test: Can trigger generation
- [ ] Test: Returns proper response

### Task 5.2: Status Endpoint
- [ ] Implement GET /solution-critique/status endpoint
- [ ] Load critique data from database
- [ ] Return status (processing/completed/failed)
- [ ] Include progress information
- [ ] Test: Returns correct status
- [ ] Test: Handles non-existent projects

### Task 5.3: Results Endpoint
- [ ] Implement GET /solution-critique/results endpoint
- [ ] Load complete critique data
- [ ] Return structured JSON report
- [ ] Handle error cases (not completed, not found)
- [ ] Test: Returns complete report
- [ ] Test: JSON structure valid
- [ ] Verify: All critiques present

### Task 5.4: API Integration
- [ ] Register router in main app
- [ ] Add to API documentation
- [ ] Test: All endpoints accessible
- [ ] Test: Authentication works
- [ ] Test: Authorization works

---

## Phase 6: Testing & Validation ☑️
**Target: Day 5 (4-6 hours)**

### Task 6.1: Unit Tests
- [ ] Test Context Loader
- [ ] Test Query Planner
- [ ] Test Web Researcher
- [ ] Test Base Critique Agent
- [ ] Test Each Critique Agent (5 tests)
- [ ] Test Report Synthesizer
- [ ] Run all unit tests
- [ ] Achieve >80% code coverage

### Task 6.2: Integration Tests
- [ ] Test workflow nodes
- [ ] Test parallel execution
- [ ] Test database operations
- [ ] Test API endpoints
- [ ] Run all integration tests

### Task 6.3: End-to-End Tests
- [ ] Test complete flow (context → report)
- [ ] Test with real project data
- [ ] Verify 45-60 second completion time
- [ ] Test error scenarios
- [ ] Test missing data scenarios
- [ ] Test API failures
- [ ] Test AI service failures

### Task 6.4: Performance Testing
- [ ] Measure context loading time
- [ ] Measure query planning time
- [ ] Measure web research time
- [ ] Measure parallel critique time
- [ ] Measure synthesis time
- [ ] Verify total time < 60 seconds

### Task 6.5: AI Monitoring Verification
- [ ] Verify all AI calls tracked
- [ ] Check token usage reports
- [ ] Verify provider information logged
- [ ] Check error tracking
- [ ] Validate monitoring context

### Task 6.6: Citation System Verification **NEW**
- [ ] **Verify all critiques have citations** ([1][2] format)
- [ ] **Verify sources section present** in all critiques
- [ ] **Verify citation_count field** present and accurate
- [ ] **Verify minimum citations met** (5-8 per critique)
- [ ] **Verify sources are numbered** sequentially (1, 2, 3...)
- [ ] **Verify citation validation** (no invalid [N] references)
- [ ] **Verify source types** (web, bmc, vpc, vps)
- [ ] **Verify global sources list** in final report
- [ ] **Verify executive summary citations**
- [ ] **Verify suggestion citations** (supporting_sources array)
- [ ] **Test citation extraction** (regex pattern works)
- [ ] **Test source de-duplication** in synthesis

---

## Documentation & Cleanup ☑️
**Target: Day 5 Afternoon**

- [ ] Add docstrings to all classes
- [ ] Add docstrings to all methods
- [ ] Add type hints throughout
- [ ] Update README if needed
- [ ] Add usage examples
- [ ] Document any known issues
- [ ] Create deployment notes
- [ ] Update API documentation

---

## Deployment Checklist ☑️

### Pre-Deployment
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Database migration executed

### Deployment
- [ ] Deploy to staging
- [ ] Test in staging environment
- [ ] Monitor AI usage
- [ ] Monitor performance
- [ ] Deploy to production
- [ ] Monitor production

### Post-Deployment
- [ ] Verify feature works end-to-end
- [ ] Check AI monitoring dashboard
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Gather user feedback

---

## Progress Tracking

### Day 1
- [x] Pre-implementation
- [ ] Phase 1: Foundation
- [ ] Phase 2: Core Services

### Day 2
- [ ] Phase 3: Base Agent + 2 Critique Agents

### Day 3
- [ ] Phase 3: Remaining 3 Agents + Synthesizer

### Day 4
- [ ] Phase 4: Workflow
- [ ] Phase 5: API Layer

### Day 5
- [ ] Phase 6: Testing
- [ ] Documentation & Cleanup

---

## Notes & Issues

### Blockers
- [ ] None currently

### Questions
- [ ] None currently

### Decisions Made
- [ ] Using GPT-4.1 via existing AIServiceWrapper
- [ ] Parallel critique execution via LangGraph
- [ ] JSON output only (no markdown)
- [ ] Storing in vmp_projects.soln_critique_data

---

## Final Sign-Off

- [ ] All features implemented
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Deployed to production
- [ ] Monitoring confirmed
- [ ] Feature accepted

**Completed by:** _________________
**Date:** _________________
**Notes:** _________________
