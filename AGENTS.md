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
