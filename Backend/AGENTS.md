# AGENTS.md - Backend (RABA)

**Purpose:** Backend-specific rules for AI agents.

**Read First:** Root `AGENTS.md` and `Documentations/API_Docs/`

---

## Tech Stack

Python 3.11+, FastAPI, Pydantic 2.5+, LangGraph, Supabase, Redis, Google Gemini 2.5, Veo 3.1, Nano Banana Pro, pytest

---

## Project Structure

```
Backend/
├── app/
│   ├── main.py          # FastAPI entry
│   ├── agents/          # Agent implementations
│   ├── api/routes/      # API route handlers
│   ├── graph/           # LangGraph workflow
│   ├── models/          # Pydantic models
│   ├── services/        # External service clients
│   └── utils/           # Utilities
```

---

## Code Style

**Naming:** Files snake_case, Classes PascalCase, functions snake_case, constants UPPER_SNAKE_CASE  
**Type Hints:** Required for all functions, use Pydantic models, `Optional[T]` for nullable  
**Pattern:** Async/await for I/O, repository pattern for DB, structured logging

```python
# ✅ Good: Typed, error handling, logging
async def create_workflow(
    input_data: WorkflowInput,
    user_id: Optional[str] = None
) -> WorkflowCreateResponse:
    logger.info(f"Creating workflow: {input_data.topic[:50]}")
    try:
        # Implementation
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")
```

---

## FastAPI Patterns

**Routes:** Proper response models, status codes, rate limiting, tags, error handling  
**Validation:** Pydantic models, field validation, custom validators  
**Error Handling:** Appropriate HTTP codes, user-friendly messages, structured logging, never expose internals

```python
@router.post("", response_model=WorkflowCreateResponse, status_code=201)
@limiter.limit("5/minute")
async def create_workflow(input_data: WorkflowInput) -> WorkflowCreateResponse:
    # Implementation with comprehensive error handling
```

---

## Agent Patterns

**Structure:** Follow existing patterns in `app/agents/`, async/await, structured outputs (Pydantic), error handling, caching  
**LangGraph Nodes:** Update state dict, handle errors gracefully, log operations, return updated state

```python
async def deep_research_node(state: VideoGenerationState) -> VideoGenerationState:
    try:
        result = await agent.research(state["topic"])
        state["research_data"] = result.dict()
        return state
    except Exception as e:
        state["error"] = str(e)
        return state
```

---

## Database & Caching

**Repository Pattern:** Async operations, proper error handling, transactions for multi-step  
**Caching:** Redis for expensive operations, appropriate TTLs (research=7d, tools=1h), invalidate on updates

---

## Testing

**Structure:** Unit tests for agents, integration tests for APIs, mock external calls, test error paths  
**Coverage:** >80% target, test edge cases, validation scenarios

```python
@pytest.mark.asyncio
async def test_research_success(mock_gemini, mock_cache):
    agent = DeepResearchAgent(mock_gemini, mock_cache)
    result = await agent.research("topic")
    assert isinstance(result, ResearchOutput)
```

---

## Security

✅ **ALWAYS:** Input validation/sanitization, env vars for secrets, rate limiting, content safety checks  
❌ **NEVER:** Log secrets, expose internal errors, skip validation, trust user input

**Commands:** `uvicorn app.main:app --reload`, `pytest tests/ -v`, `black app/`, `ruff check app/`  
**Checklist:** Types, error handling, logging, tests, caching, security, documentation updated
