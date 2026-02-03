# Service Layer Architecture

## Purpose
The `src/mint/services` directory contains the **Business Logic Layer**. This is where the core application rules reside, independent of the HTTP interface (API) or the specific database implementation (Repositories).

## Pattern: Fat Service, Thin Controller
- **Controllers/Routers** should only handle HTTP concerns (parsing, validation, status codes).
- **Services** should handle logic, calculations, orchestration, and data transactions.

## Standard Structure
A typical service class (`UserService`) follows this pattern:
1.  **Initialization:** Accepts dependencies (e.g., `SupabaseClient`) via constructor.
2.  **Methods:** Async methods for specific business actions (`create_user`, `upgrade_plan`).
3.  **Return Values:** Returns Pydantic models or clean dictionaries, not raw database cursors.

## Integration
- **Calling Repositories:** Services often delegate raw data access to `src/mint/repositories`.
- **Calling External APIs:** Services wrap calls to Stripe, SendGrid, etc.
- **Error Handling:** Services should raise domain-specific exceptions (e.g., `UserNotFoundError`) which the API layer catches and converts to 404s.

## Key Services
- `workflow_service.py`: Orchestrates complex multi-step user flows.
- `sharing_service.py`: Manages permissions for shared resources (projects, docs).
