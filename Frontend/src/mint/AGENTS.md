# Core Module Architecture

## Purpose
The `src/mint` module acts as the **application kernel**. It contains:
1.  **Main Application Entry:** `main_app.py` wires all routers, middleware, and exception handlers.
2.  **Authentication:**
    - **Infrastructure:** `api/auth` (Middleware, Production Auth System). [Details](api/auth/AGENTS.md)
    - **Endpoints:** `api/auth_v2` (Login, Signup, Profile). [Details](api/auth_v2/AGENTS.md)
3.  **Shared Services:** Global utilities like `supabase_client`, `email_service`, and `redis_client`.
4.  **Base Routers:** User, Tenant, and System endpoints.

## Directory Structure
- `api/`: Presentation layer (routers, middleware). [Details](api/AGENTS.md)
- `repositories/`: Data access layer for core entities.
- `services/`: Business logic for core features. [Details](services/AGENTS.md)

## Key Components
- **ProductionAuthSystem:** Single source of truth for auth. Handles JWT verification (HS256/RS256), rate limiting (Redis), and session management.
- **SupabaseClient:** Wrapper around the official Supabase Python client. Usage: `get_supabase_client(use_service_role=True)`.
- **Modular Routers:** All routers are defined in their respective sub-modules and imported into `main_app.py`.

## Developer Notes
- **Do not add business logic to `main_app.py`.**
- Use `request.state.auth_context` to access user info in endpoints.
- Always use `get_service_role_client()` for admin-level database operations.
