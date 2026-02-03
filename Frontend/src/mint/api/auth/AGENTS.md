# Auth Module Architecture

## Purpose
The `src/mint/api/auth` directory houses the **Core Authentication Infrastructure** (middleware, logic, dependencies) used throughout the entire application.

**Important:** This directory does *not* contain the login/signup API endpoints. Those are located in `src/mint/api/auth_v2`.

## Directory Structure
- `production/`: Contains the `ProductionAuthSystem` (single source of truth for auth logic).
- `dependencies.py`: FastAPI dependency functions (`get_current_user`, `get_auth_context`).
- `utils.py`: Helper functions for token manipulation.

## Core Components
1.  **ProductionAuthSystem:**
    - Handles JWT verification (HS256/RS256).
    - Manages session caching (Redis).
    - Enforces rate limits.
    - Located in `production/system.py`.

2.  **ProductionAuthMiddleware:**
    - Intercepts every HTTP request.
    - Verifies the `Authorization: Bearer <token>` header.
    - Injects the user context into `request.state.auth_context`.

## Where are the Endpoints?
- **Login / Signup:** Go to `src/mint/api/auth_v2/AGENTS.md`.
- **Profile Management:** Go to `src/mint/api/auth_v2/AGENTS.md`.

## Developer Notes
- **Do not modify** the middleware logic unless you are updating the core security protocols.
- **Do not add new endpoints** to this folder. Add them to `auth_v2`.
