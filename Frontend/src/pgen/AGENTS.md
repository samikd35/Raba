# Problem Generator (PGEN) Architecture

## Purpose
The `src/pgen` module is the **AI engine** for converting user observations into validated problem statements. It utilizes **LangGraph** to orchestrate a complex 12-node workflow.

## Directory Structure
- `agents/`: Contains the `ProblemGeneratorGraph` (workflow logic) and `graph_state.py`.
- `nodes/`: Individual LangGraph nodes (e.g., `query_expander_node`, `scraper_pool_node`).
- `services/`: `problem_database_service.py`, `job_status_service.py`.
- `models/`: Pydantic models for request/response bodies.
- `api/`: FastAPI routers exposing the generator.

## The Workflow (LangGraph)
The `ProblemGeneratorGraph` implements a "Cause → Effect + Context" methodology:
1.  **Search Fan-out:** Parallel DB & Web Search (Node 2).
2.  **Scraper Pool:** Asynchronous content fetching (Node 3).
3.  **Clustering & Synthesis:** Merges insights (Node 6) and generates micro-stories (Node 7).
4.  **Refinement:** Formalizes output into structured problem statements (Node 8).
5.  **Ranking:** Selects top 3-5 results based on relevance (Node 11).

## Key Patterns
- **Streaming:** The graph supports `astream()` for real-time frontend updates.
- **State Management:** `ProblemGraphState` (TypedDict) maintains the workflow context (queries, hits, clusters) across nodes.
- **Asynchronous Processing:** Heavy I/O (scraping, LLM calls) is fully async.
