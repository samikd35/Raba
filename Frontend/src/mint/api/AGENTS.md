# API Layer Architecture

## Purpose
The `src/mint/api` directory contains the **Presentation Layer** of the application. It maps HTTP requests to business logic.
It uses **FastAPI Routers** to organize endpoints by domain (e.g., Auth, Billing, Chat).

## Sub-Module Map
| Directory | Description | Documentation |
|-----------|-------------|---------------|
| `auth/` | **Authentication System**. Handles Login, Signup, JWTs, and Sessions. | [Auth AGENTS.md](auth/AGENTS.md) |
| `organization/` | **Tenant Management**. Handling Orgs, Teams, and Members. | [Org AGENTS.md](organization/AGENTS.md) |
| `payment_v2/` | **Payments**. Flutterwave & Credits. | [Payment AGENTS.md](payment_v2/AGENTS.md) |
| `messaging/` | **Chat**. WebSocket & REST messaging. | [Messaging AGENTS.md](messaging/AGENTS.md) |
| `venture_builder/` | **Expert Platform**. Coaching & Booking. | [VB AGENTS.md](venture_builder/AGENTS.md) |
| `system/` | **Core System**. Health checks, Middleware, Global dependencies. | [System AGENTS.md](system/AGENTS.md) |

## Standard Patterns
1.  **Thin Routes:** Endpoints should primarily validate input (`Pydantic Models`) and call a **Service**.
    - *Bad:* Writing SQL/Supabase calls directly in the route function.
    - *Good:* `await UserService.get_profile(user_id)`
2.  **Dependency Injection:** Use `Depends()` for:
    - `AuthContext`: Getting the current user.
    - `Services`: Getting instances of business logic classes.
3.  **Response Models:** Always specify `response_model` in the decorator for auto-documentation.

## Key Files
- `middleware_config.py`: Central place for configuring CORS, Rate Limiting, and Auth middleware.
- `models.py`: Shared Pydantic models used across multiple API domains.
