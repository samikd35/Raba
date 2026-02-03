# RABA Code Generation Rules

## Documentation & References
- Always follow patterns in `Backend/Documentations/` (nano_prompt_guide.md, veo_doc.md, gemini_doc.md, etc.)
- Reference and update `Backend/Documentations/API_Docs/` when making API changes
- Consult `Guides/RABA_Architecture.md` for system design patterns and update when there are changes to the architecture.

## Code Consistency
- Deeply understand existing implementation before changing anything
- Use centralized services: `WorkflowRepository`, `GeminiService`, `CacheService`, `VeoService`, `NanoBananaService`
- Match existing code style: async/await, error handling patterns, logging format
- Preserve LangGraph state structure and node contracts

## Implementation Guidelines
- Functions should do one thing well; prefer composition over large functions
- Use type hints; follow existing model structures in `Backend/app/models/`
- Handle errors consistently: custom exceptions, typed errors, clear messages
- Maintain HITL gate patterns and workflow state transitions

## Research & Learning
- Perform web search when unfamiliar with APIs, libraries, or patterns
- Verify against official documentation (Gemini API, LangGraph, FastAPI) before implementing
- Check for breaking changes or deprecations in dependencies

## Documentation Maintenance
- Update API docs when adding/modifying endpoints
- Keep architecture docs current with design changes
- Document new services, agents, or workflows inline and in docs

## Testing & Verification
- Ensure changes build cleanly and preserve existing functionality
- Consider edge cases and invalid inputs
- Verify state persistence in LangGraph workflows

## Tool Creation/Enhancer Maintenance (CRITICAL)
The tool creation and enhancement system (`Backend/app/services/tool_enhancer.py`) is the **source of truth** for prompt template generation.

**When making prompt template changes, update:**
1. `TOOL_ENHANCEMENT_SYSTEM_PROMPT` - Controls new tool creation
2. `TOOL_IMPROVEMENT_SYSTEM_PROMPT` - Controls tool improvement/bulk updates
3. `app/services/template_validation.py` - Template validation rules

**Template types stored in tools table:**
- `script_prompt_template` - Used by script_writer agent
- `image_prompt_template` - Used by image_generator agent
- `video_prompt_template` - Used by video_generator agent

**After template changes:** Run bulk-improve on existing tools to regenerate their templates.

## Database Schema Reference
- Reference `Backend/Documentations/tables.sql` for current database schema
- Update `tables.sql` when modifying table structures or constraints
- Sync schema changes with `Guides/RABA_Architecture.md` Section 8 (Database Schema)
- Key tables: `workflows`, `tools`, `media`, `config`

## Workflows & Commands
- Backend API workflow: create generation via `POST /api/v1/generate` or `/api/v1/generate/with-image`, then poll `GET /api/v1/workflows/{id}` (see `Backend/Documentations/API_Docs/`)
- HITL workflow: submit feedback with `POST /api/v1/workflows/{id}/feedback`, gate status via `GET /api/v1/workflows/{id}/gate`
- Monitoring workflow: usage summary via `GET /api/v1/monitoring/summary`, pricing via `GET /api/v1/monitoring/pricing`
- Run backend server: `uvicorn app.main:app --reload --port 8000` or `python -m app.main`
- Run backend tests: `pytest tests/ -v` (or specific tests via `python -m pytest tests/test_cache.py -v`)
- Format/lint backend: `black app/ tests/`, `isort app/ tests/`, `ruff check app/ tests/`
- Bulk tool template update script: `Backend/bulk_update_ingredients.sh`
- Frontend dev server: `npm run dev` (or `yarn dev`, `pnpm dev`, `bun dev`)
