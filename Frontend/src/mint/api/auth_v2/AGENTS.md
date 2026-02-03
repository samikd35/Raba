# Auth V2 Router Architecture

## Purpose
The `src/mint/api/auth_v2` module contains the **Active Public API Endpoints** for user authentication. While `src/mint/api/auth` handles the *verification infrastructure* (middleware), this module handles the *transactional endpoints* (login, signup, etc.).

## Directory Structure
- `endpoints.py`: The FastAPI router defining `/api/v2/auth/*` paths.
- `service.py`: Business logic for User CRUD, Password Hashing, and Supabase interaction.
- `waitlist_service.py`: Logic for managing the pre-launch waitlist.
- `models.py`: Pydantic schemas for requests (e.g., `LoginRequest`, `CreateUserRequest`).

## Key Flows
1.  **Signup:**
    - `POST /signup/send-link`: Sends magic link/verification email.
    - `POST /signup/verify`: Exchanges token for user creation.
    - `POST /signup/direct`: Direct creation (if enabled).
2.  **Login:**
    - `POST /login`: Validates credentials, returns JWT.
    - `POST /login/{tenant_id}`: Switches context to a specific organization.
    - `POST /google-signin`: Exchanges Google ID Token for session.
3.  **Profile:**
    - `GET /me`: Returns current user + active tenant info.
    - `PUT /users/{id}`: Profile updates.

## Integration
- **Dependency:** Uses `AuthService` to interact with the database.
- **Middleware:** Endpoints here are *protected* by the `ProductionAuthMiddleware` defined in `../auth/production/system.py`.
