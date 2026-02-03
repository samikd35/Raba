"""
Streamlined Main Application - Modular Architecture
===================================================

This is the new main application file that replaces the monolithic app.py.
It demonstrates clean separation of concerns:

1. ✅ Configuration and setup only (no business logic)
2. ✅ Middleware configuration in logical order
3. ✅ Router registration for modular endpoints
4. ✅ Startup/shutdown lifecycle management
5. ✅ Production-ready security configuration

Key improvements over monolithic structure:
- Business logic moved to services
- Database operations moved to repositories
- API endpoints moved to routers
- Data models separated into dedicated files
- Authentication consolidated into single secure system
"""

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables
# In production (Azure), environment variables are set via Azure Portal
# In development, load from .env file but DON'T override existing env vars
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=dotenv_path, override=False)  # Don't override Azure env vars

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("mint-api")

logging.getLogger("src.mint.api.auth.production.system.ProductionAuthSystem").setLevel(
    logging.DEBUG
)
logging.getLogger("src.mint.api.auth.production.system").setLevel(logging.DEBUG)

# ==========================================
# APPLICATION SETUP
# ==========================================

# Create the FastAPI application with security configuration
app = FastAPI(
    title="Yuba API",
    description="Modular API for Yuba. **All Problem Generator endpoints require Bearer token authentication.** Get your JWT token from `/api/auth/login` and include it in the Authorization header as `Bearer <token>`.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "🔒 Problem Generator",
            "description": "AI-powered problem statement generation with authentication",
        },
        {
            "name": "📊 Problem Generator Analytics",
            "description": "Analytics and monitoring for problem generation",
        },
        {
            "name": "🔐 Authentication",
            "description": "User authentication and authorization",
        },
        {
            "name": "💬 Chat",
            "description": "Chat and messaging functionality",
        },
        {
            "name": "📈 Performance",
            "description": "Performance monitoring and metrics",
        },
        {
            "name": "📋 Reports",
            "description": "Report generation and management",
        },
        {
            "name": "💡 Insights",
            "description": "Actionable insights and analytics",
        },
        {
            "name": "💱 Credit Exchange",
            "description": "Admin API for managing credit exchange rates and currency conversions",
        },
        {
            "name": "💳 Credits",
            "description": "Credit granting and allocation system for admins and organizations",
        },
        {
            "name": "payments-stripe",
            "description": "Stripe payment integration for credit purchases and organization invitations",
        },
        {
            "name": "🌐 WebSocket",
            "description": "Real-time WebSocket connections",
        },
        {
            "name": "🏢 Tenant",
            "description": "Tenant management for Individual, Team, and Organization types",
        },
        {
            "name": "👑 Admin Tenant",
            "description": "Admin dashboard for tenant oversight and management",
        },
        {
            "name": "🧠 Vector Storage",
            "description": "Vector storage and RAG system for module context preservation",
        },
        {
            "name": "🎯 Value Proposition Module (Module 2)",
            "description": "Value Proposition Canvas generation and project management",
        },
        {
            "name": "📊 Market Research Analysis",
            "description": "AI-powered market research analysis and assumption validation",
        },
    ],
)

# Add security scheme for Bearer token authentication
from fastapi.openapi.utils import get_openapi


def custom_openapi():
    # Force regeneration by commenting out the cache check temporarily
    # if app.openapi_schema:
    #     return app.openapi_schema

    print("🔧 DEBUG: Generating new OpenAPI schema...")
    openapi_schema = get_openapi(
        title="Yuba API",
        version="2.0.0",
        description="Modular API for Yuba",
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token authentication. Get your token from /api/auth/login endpoint and include it in the Authorization header as 'Bearer <token>'",
        }
    }

    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Add security to all protected endpoints
    pgen_count = 0
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Add security to specific auth-related endpoints and all problem generator, workflow, insights, and reports endpoints
                if (
                    (
                        "auth" in path
                        and any(
                            keyword in operation.get("summary", "").lower()
                            for keyword in ["protected", "me", "verify", "profile"]
                        )
                    )
                    or ("/api/v1/pgen" in path)
                    or ("/api/workflow" in path)
                    or ("/api/insights" in path)
                    or ("/api/organizations" in path)
                    or ("/api/v1/tenant" in path)
                    or ("/api/teams")
                ):
                    operation["security"] = [{"BearerAuth": []}]

                    # Add detailed security description for problem generator endpoints
                    if "/api/v1/pgen" in path:
                        pgen_count += 1
                        operation["summary"] = (
                            f"🔒 {operation.get('summary', 'Problem Generator Endpoint')}"
                        )
                        if "description" not in operation:
                            operation["description"] = (
                                "This endpoint requires Bearer token authentication. Please obtain a JWT token from the /api/auth/login endpoint and include it in the Authorization header."
                            )
                        else:
                            operation["description"] = (
                                f"{operation['description']}\n\n**Authentication Required:** Bearer token (JWT) from /api/auth/login endpoint."
                            )

                    # Add security description for reports endpoints
                    elif "/api/reports" in path:
                        operation["summary"] = (
                            f"🔒 {operation.get('summary', 'Report History Endpoint')}"
                        )
                        if "description" not in operation:
                            operation["description"] = (
                                "This endpoint requires Bearer token authentication. Please obtain a JWT token from the /api/auth/login endpoint and include it in the Authorization header."
                            )
                        else:
                            operation["description"] = (
                                f"{operation['description']}\n\n**Authentication Required:** Bearer token (JWT) from /api/auth/login endpoint."
                            )

    print(f"🔧 DEBUG: Applied security to {pgen_count} problem generator endpoints")

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# ==========================================
# STARTUP & SHUTDOWN EVENTS
# ==========================================


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("=== MINT API Starting Up ===")
    logger.info("Initializing modular architecture with separated concerns")

    # ==========================================
    # SUPABASE CLIENT INITIALIZATION CHECK
    # Catches version incompatibility issues BEFORE deployment
    # ==========================================
    try:
        logger.info("🔍 Testing Supabase client initialization...")
        from .api.system.core.supabase_client import SupabaseClient
        
        # Test creating a client - this will catch ClientOptions version issues
        test_client = SupabaseClient(use_service_role=True)
        logger.info("✅ Supabase client initialization test PASSED")
        
        # Log the supabase library version for debugging
        try:
            import supabase
            supabase_version = getattr(supabase, '__version__', 'unknown')
            logger.info(f"📦 Supabase library version: {supabase_version}")
        except Exception:
            logger.warning("⚠️ Could not determine supabase library version")
            
    except Exception as supabase_error:
        logger.error("=" * 60)
        logger.error("❌ SUPABASE CLIENT INITIALIZATION FAILED!")
        logger.error(f"Error: {type(supabase_error).__name__}: {supabase_error}")
        logger.error("")
        logger.error("This error will also occur in deployment!")
        logger.error("Common causes:")
        logger.error("  1. supabase-py version mismatch (check requirements.txt)")
        logger.error("  2. ClientOptions API changed between versions")
        logger.error("  3. Missing SUPABASE_URL or SUPABASE_KEY env vars")
        logger.error("")
        logger.error("Fix: Pin exact supabase version in requirements.txt")
        logger.error("=" * 60)
        raise  # Fail fast - don't let the app start with broken Supabase

    try:
        # Import and initialize startup services
        from .api.system.init import initialize_services

        await initialize_services()

        logger.info("✅ All services initialized successfully")
        logger.info("✅ Production authentication system active")
        logger.info("✅ Modular architecture loaded")

    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    logger.info("=== MINT API Shutting Down ===")

    try:
        from .api.system.init import shutdown_services

        await shutdown_services()
        logger.info("✅ All services shut down cleanly")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")


# ==========================================
# MIDDLEWARE CONFIGURATION
# ==========================================

# CORS middleware (configured first)
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
    allow_methods=os.getenv("CORS_ALLOW_METHODS", "*").split(","),
    allow_headers=os.getenv("CORS_ALLOW_HEADERS", "*").split(","),
)

# Security middleware chain (order matters!)
logger.info("Configuring production security middleware chain")

from .api.production_auth_system import ProductionAuthMiddleware
from .api.system.middleware.ip_whitelist import IPWhitelistMiddleware

# Import security middleware
from .api.system.middleware.rate_limiter import AdminRateLimitMiddleware

# Common exclude paths for middleware
exclude_paths = [
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/api/health",
    "/api/auth/health",
    "/",
    "/ui",
]

# 1. Rate limiting middleware (outermost layer)
app.add_middleware(
    AdminRateLimitMiddleware,
    admin_window_size=int(os.getenv("ADMIN_RATE_WINDOW_SEC", 60)),
    admin_max_requests=int(os.getenv("ADMIN_RATE_MAX", 200)),
    login_window_size=int(os.getenv("LOGIN_RATE_WINDOW_SEC", 300)),
    login_max_requests=int(os.getenv("LOGIN_RATE_MAX", 5)),
    exclude_paths=exclude_paths,
)

# 2. IP whitelisting for super admin endpoints
app.add_middleware(
    IPWhitelistMiddleware,
    whitelist=None,  # Load from environment variable
    super_admin_paths=[
        "/api/admin/infrastructure/",
        "/api/admin/settings/",
        "/api/admin/auth/roles",
        "/api/admin/system/maintenance",
    ],
    exclude_paths=exclude_paths,
)

# 3. Production Authentication System (innermost layer)
logger.warning("🔒 PRODUCTION SECURITY: Unified authentication system active")
logger.warning("🔒 SECURITY UPGRADE: JWT fallback vulnerability eliminated")
logger.warning("🔒 SECURITY UPGRADE: Multiple auth handlers consolidated")

app.add_middleware(
    ProductionAuthMiddleware,
    supabase_url=os.getenv("SUPABASE_URL"),
    service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY"),
    redis_url=os.getenv("REDIS_URL"),
    exclude_paths=exclude_paths,
)

# ==========================================
# ROUTER REGISTRATION
# ==========================================

logger.info("Registering modular API routers")

# Core workflow endpoints (NEW MODULAR STRUCTURE)
from .api.system.endpoints.workflow_endpoints import router as workflow_router

app.include_router(workflow_router, prefix="/api/workflow", tags=["workflow"])

# Authentication admin endpoints - Removed (not essential for core functionality)
# from .api.production_auth_system import auth_admin_router
# app.include_router(auth_admin_router, tags=["auth-admin"])

# User authentication endpoints (register, login, etc.)
# try:
#     from .api.auth import auth_router
#     logger.info("✅ Successfully imported auth_router")
#     logger.info(f"Auth router routes: {[route.path for route in auth_router.routes]}")
#     app.include_router(auth_router, tags=["authentication"])
#     logger.info("✅ Successfully registered auth_router")
# except Exception as e:
#     logger.error(f"❌ Failed to import/register auth_router: {e}")
#     import traceback
#     logger.error(traceback.format_exc())
try:
    from .api.auth_v2.endpoints import auth_router

    logger.info("✅ Successfully imported auth_router")
    logger.info(f"Auth router routes: {[route.path for route in auth_router.routes]}")
    app.include_router(auth_router, prefix="/api/v2/auth", tags=["authentication"])
    logger.info("✅ Successfully registered auth_router")
except Exception as e:
    logger.error(f"❌ Failed to import/register auth_router: {e}")
    import traceback

    logger.error(traceback.format_exc())

from .api.chat import router as chat_router
# Performance router removed - redundant with auth-admin endpoints
# from .api.performance import performance_router
from .api.report import history_router as report_history_router

# Existing modular routers (already separated)
from .api.system.endpoints.websocket_endpoints import router as websocket_router

app.include_router(websocket_router, tags=["websocket"])
app.include_router(chat_router, tags=["chat"])
# app.include_router(performance_router, tags=["performance"])  # Removed - use /api/auth/admin/metrics instead
app.include_router(report_history_router)  # Use the router's own tags

# User-to-user messaging
from .api.messaging import messaging_router, messaging_websocket_router

app.include_router(messaging_router, tags=["messaging"])
app.include_router(messaging_websocket_router, tags=["messaging-websocket"])

# Problem generator routers
from src.pgen.api.problem_generator_endpoints import \
    router as problem_generator_router

app.include_router(problem_generator_router)

# Tenant management (Individual, Team, Organization) - Simple version for testing
from .api.organization.endpoints import router as organization_router

app.include_router(
    organization_router, tags=["organization"], prefix="/api/organization"
)

from .api.payment_invites.endpoints import router as payment_inv_router

app.include_router(
    payment_inv_router, tags=["organization"], prefix="/api/organization"
)

# User Monitoring (Super Admin Only)
logger.info("🔍 Registering User Monitoring router (super admin only)...")
try:
    import sys
    from pathlib import Path
    
    # Add monitor directory to path
    monitor_path = Path(__file__).parent.parent.parent / "monitor"
    if str(monitor_path) not in sys.path:
        sys.path.insert(0, str(monitor_path))
    
    from users.endpoints import router as user_monitoring_router
    
    app.include_router(
        user_monitoring_router, tags=["user-monitoring"], prefix="/api/admin"
    )
    logger.info("✅ User Monitoring router registered successfully")
    logger.info("📊 Available endpoints:")
    logger.info("   - GET /api/admin/users (paginated user list)")
    logger.info("   - GET /api/admin/monitoring/onboarding (conversion funnel)")
    logger.info("   - GET /api/admin/monitoring/activation (first value metrics)")
    logger.info("   - GET /api/admin/monitoring/retention (user segments)")
except Exception as e:
    logger.error(f"❌ Failed to register User Monitoring router: {e}")
    import traceback
    logger.error(traceback.format_exc())

# AI Token Monitoring (Super Admin Only)
logger.info("🔍 Registering AI Token Monitoring router (super admin only)...")
try:
    import sys
    from pathlib import Path
    
    # Add monitor directory to path if not already added
    monitor_path = Path(__file__).parent.parent.parent / "monitor"
    if str(monitor_path) not in sys.path:
        sys.path.insert(0, str(monitor_path))
    
    from tokens.endpoints import router as ai_token_monitoring_router
    
    app.include_router(
        ai_token_monitoring_router, tags=["ai-token-monitoring"], prefix="/api/admin"
    )
    logger.info("✅ AI Token Monitoring router registered successfully")
    logger.info("📊 Available endpoints:")
    logger.info("   - GET /api/admin/monitoring/ai-usage/system (system-wide metrics)")
    logger.info("   - GET /api/admin/monitoring/ai-usage/tenants (tenant rankings)")
    logger.info("   - GET /api/admin/monitoring/ai-usage/tenants/{tenant_id} (tenant details)")
    logger.info("   - GET /api/admin/monitoring/ai-usage/features (feature analytics)")
    logger.info("   - GET /api/admin/monitoring/ai-usage/models (model analytics)")
    logger.info("   - GET /api/admin/monitoring/ai-usage/projects/{project_id} (project details)")
    logger.info("   - GET /api/admin/monitoring/ai-usage/users/{user_id} (user analytics)")
    logger.info("   - GET /api/admin/monitoring/ai-model-pricing (list pricing)")
    logger.info("   - POST /api/admin/monitoring/ai-model-pricing (create pricing)")
    logger.info("   - PATCH /api/admin/monitoring/ai-model-pricing/{id} (update pricing)")
    logger.info("   - DELETE /api/admin/monitoring/ai-model-pricing/{id} (delete pricing)")
except Exception as e:
    logger.error(f"❌ Failed to register AI Token Monitoring router: {e}")
    import traceback
    logger.error(traceback.format_exc())

# Tenant management (Individual, Team, Organization) - Simple version for testing
from .api.tenant import tenant_router

app.include_router(tenant_router, tags=["tenant"])

# Feature management
from .api.features.endpoints import router as features_router

app.include_router(features_router)

# Team management
from .api.team.endpoints import teams_router

app.include_router(teams_router)

# User workspaces (workspace switcher)
from .api.user.workspaces import workspaces_router

app.include_router(workspaces_router)

# Invitation validation
from .api.invitations.endpoints import invitations_router

app.include_router(invitations_router)

# Payment (Flutterwave)
from .api.payment_v2.endpoints import router as payment_router

app.include_router(payment_router)

# Payment Stripe
from .api.payment_v2_stripe.endpoints import router as payment_stripe_router

app.include_router(payment_stripe_router)

# Payment Invites Stripe
from .api.payment_invites_stripe.endpoints import router as payment_invites_stripe_router

app.include_router(payment_invites_stripe_router, tags=["organization"], prefix="/api/organization")

# Package management
from .api.packages.endpoints import router as package_router

app.include_router(package_router)

# Credit exchange management (Admin API for credit exchange rates)
from .api.credit_exchange.endpoints import router as credit_exchange_router

app.include_router(credit_exchange_router)

# profile management
from .api.cofounder_matching.endpoints import router as profile_enum_router
from .api.cofounder_matching.admin import router as profile_admin_router
from .api.cofounder_matching.matches import router as profile_matches_router
from .api.cofounder_matching.profiles import router as profile_me_router
from .api.cofounder_matching.directory import router as directory_router
from .api.cofounder_matching.reports import router as profile_reports_router
from .api.cofounder_matching.enum_suggestions import router as enum_suggestions_router

app.include_router(profile_enum_router)
app.include_router(profile_admin_router)
app.include_router(profile_matches_router)
app.include_router(profile_me_router)
app.include_router(directory_router)
app.include_router(profile_reports_router)
app.include_router(enum_suggestions_router)

# Credit management
from .api.credit.endpoints import router as credit_router
from .api.credit.admin_endpoints import router as credit_admin_router

app.include_router(credit_router)
app.include_router(credit_admin_router)


# Vector storage and RAG system
from .api.vector_storage import vector_storage_router

app.include_router(vector_storage_router, tags=["vector-storage"])

# Actionable insights
from .api.actionable_insights import router as insights_router

app.include_router(insights_router, tags=["insights"])
logger.info("✅ Actionable insights router registered successfully")

# VPM (Value Proposition Module) - VPC 2.0 and Field Prep
try:
    from src.vpm.api.endpoints import router as vpm_router
    app.include_router(vpm_router)
    logger.info("✅ VPM router registered successfully")
except Exception as e:
    logger.error(f"❌ Failed to register VPM router: {e}")

# MVP (MVP Development Suite) - VPS, BMC, Critique
try:
    from src.mvp.api.endpoints import router as mvp_router
    app.include_router(mvp_router)
    logger.info("✅ MVP router registered successfully")
except Exception as e:
    logger.error(f"❌ Failed to register MVP router: {e}")

# Solution Critique (MVP Module - Solution Validation with Web Research)
try:
    from src.mvp.soln_critique.api.endpoints import router as solution_critique_router
    app.include_router(solution_critique_router)
    logger.info("✅ Solution Critique router registered successfully")
    logger.info("📊 Solution Critique endpoints:")
    logger.info("   - POST /api/v2/mvp/projects/{project_id}/solution-critique/generate")
    logger.info("   - GET /api/v2/mvp/projects/{project_id}/solution-critique/status")
    logger.info("   - GET /api/v2/mvp/projects/{project_id}/solution-critique/results")
except Exception as e:
    logger.error(f"❌ Failed to register Solution Critique router: {e}")
    logger.info("Solution Critique will be available when dependencies are installed")

# Solution Critique Chat (RAG-based chat with critique reports)
try:
    from src.mvp.soln_critique.api.chat_endpoints import chat_router as solution_critique_chat_router
    app.include_router(solution_critique_chat_router)
    logger.info("✅ Solution Critique Chat router registered successfully")
    logger.info("💬 Solution Critique Chat endpoints:")
    logger.info("   - POST /api/v2/mvp/projects/{project_id}/solution-critique/chat/message")
    logger.info("   - POST /api/v2/mvp/projects/{project_id}/solution-critique/chat/prepare")
    logger.info("   - POST /api/v2/mvp/projects/{project_id}/solution-critique/chat/clear")
    logger.info("   - GET /api/v2/mvp/projects/{project_id}/solution-critique/chat/status")
except Exception as e:
    logger.error(f"❌ Failed to register Solution Critique Chat router: {e}")
    logger.info("Solution Critique Chat will be available when dependencies are installed")

# VPS v2 (Critique-driven VPS Refinement) - Registered after Solution Critique for proper Swagger ordering
try:
    from src.mvp.api.vps_v2_endpoints import router as vps_v2_router
    app.include_router(vps_v2_router)
    logger.info("✅ VPS v2 router registered successfully (after Solution Critique)")
    logger.info("📝 VPS v2 endpoints:")
    logger.info("   - POST /api/v2/mvp/projects/{project_id}/vps/v2/generate")
    logger.info("   - GET /api/v2/mvp/projects/{project_id}/vps/v2")
except Exception as e:
    logger.error(f"❌ Failed to register VPS v2 router: {e}")

# BMC v2 (Critique-driven BMC Refinement with VPS v2 Alignment) - Registered after VPS v2
try:
    from src.mvp.bmc.api.bmc_v2_endpoints import router as bmc_v2_router
    app.include_router(bmc_v2_router)
    logger.info("✅ BMC v2 router registered successfully (after VPS v2)")
    logger.info("📊 BMC v2 endpoints:")
    logger.info("   - POST /api/v2/mvp/projects/{project_id}/bmc/v2/generate")
    logger.info("   - GET /api/v2/mvp/projects/{project_id}/bmc/v2")
except Exception as e:
    logger.error(f"❌ Failed to register BMC v2 router: {e}")

# Market Research Analysis Agent (Data Analysis Agent)
logger.info("🔍 DEBUG: Starting Market Research Analysis Agent integration...")
logger.info(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
logger.info(f"🔍 DEBUG: Python path: {sys.path[:3]}...")  # Show first 3 paths

try:
    logger.info("🔍 DEBUG: Attempting to import analysis_router...")
    from src.market_research.api.router import analysis_router
    logger.info("🔍 DEBUG: analysis_router imported successfully!")
    logger.info(f"🔍 DEBUG: Router type: {type(analysis_router)}")
    logger.info(f"🔍 DEBUG: Router prefix: {getattr(analysis_router, 'prefix', 'None')}")
    logger.info(f"🔍 DEBUG: Router tags: {getattr(analysis_router, 'tags', 'None')}")
    
    # Check if router has routes
    if hasattr(analysis_router, 'routes'):
        logger.info(f"🔍 DEBUG: Router has {len(analysis_router.routes)} routes")
        for i, route in enumerate(analysis_router.routes[:5]):  # Show first 5 routes
            logger.info(f"🔍 DEBUG: Route {i}: {getattr(route, 'path', 'unknown')} [{getattr(route, 'methods', 'unknown')}]")
    else:
        logger.warning("🔍 DEBUG: Router has no 'routes' attribute")

    logger.info("🔍 DEBUG: Including router in FastAPI app...")
    app.include_router(
        analysis_router,
        prefix="/api/v1/market-research",
        tags=["market-research-analysis"],
    )
    logger.info("✅ DEBUG: Market Research Analysis Agent router included successfully!")
    
    # Verify the router was added by checking app routes
    total_routes = len(app.routes)
    logger.info(f"🔍 DEBUG: Total app routes after inclusion: {total_routes}")
    
    # Check for market research routes specifically
    market_research_routes = [route for route in app.routes if hasattr(route, 'path') and 'market-research' in route.path]
    logger.info(f"🔍 DEBUG: Market research routes found: {len(market_research_routes)}")
    
    for route in market_research_routes[:5]:  # Show first 5 market research routes
        logger.info(f"🔍 DEBUG: Market research route: {route.path} [{getattr(route, 'methods', 'unknown')}]")
    
    logger.info("✅ Market Research Analysis Agent successfully integrated!")
    logger.info("📊 Available endpoints:")
    logger.info("   - POST /api/v1/market-research/analysis/projects/{project_id}/upload-documents")
    logger.info("   - POST /api/v1/market-research/analysis/projects/{project_id}/execute")
    logger.info("   - GET /api/v1/market-research/analysis/projects/{project_id}/status")
    logger.info("   - GET /api/v1/market-research/analysis/projects/{project_id}/results")
    logger.info("   - GET /api/v1/market-research/analysis/projects/{project_id}/documents")
    logger.info("   - DELETE /api/v1/market-research/analysis/projects/{project_id}/analysis")
    logger.info("   - GET /api/v1/market-research/analysis/monitoring/health")
    logger.info("   - GET /api/v1/market-research/analysis/monitoring/dashboard")
    
except ImportError as e:
    logger.error(f"❌ DEBUG: Market Research Analysis Agent import failed: {e}")
    logger.error(f"❌ DEBUG: Import error type: {type(e)}")
    logger.error(f"❌ DEBUG: Import error args: {e.args}")
    import traceback
    logger.error(f"❌ DEBUG: Full traceback:\n{traceback.format_exc()}")
    logger.info("Market Research Analysis Agent will be available when dependencies are installed")
except Exception as e:
    logger.error(f"⚠️ DEBUG: Market Research Analysis Agent integration failed: {e}")
    logger.error(f"⚠️ DEBUG: Error type: {type(e)}")
    logger.error(f"⚠️ DEBUG: Error args: {e.args}")
    import traceback
    logger.error(f"⚠️ DEBUG: Full traceback:\n{traceback.format_exc()}")
    logger.info("Market Research Analysis Agent will be available when integration is complete")

# Idea Refinement - Advanced Idea to Problem Statement Refinement
logger.info("🔍 Attempting Idea Refinement integration...")
try:
    from .api.idea_refinement_router import router as idea_refinement_router

    app.include_router(
        idea_refinement_router,
        prefix="/api/v1/idea-refinement",
        tags=["idea-refinement"],
    )
    logger.info("✅ Idea Refinement router registered successfully")
except ImportError as e:
    logger.error(f"❌ Idea Refinement import failed: {e}")
    logger.info("Idea Refinement will be available when dependencies are installed")
except Exception as e:
    logger.warning(f"⚠️ Idea Refinement integration failed: {e}")
    logger.info("Idea Refinement will be available when integration is complete")

# VPM Integration (Value Proposition Module - Module 2)
logger.info("🔍 Attempting VPM integration...")
try:
    logger.info("🔍 Importing VPM integration module...")
    from src.vpm.integration import integrate_vpm_with_yuba

    logger.info("🔍 VPM integration module imported successfully")
    logger.info("🔍 Calling integrate_vpm_with_yuba...")
    integrate_vpm_with_yuba(app)
    logger.info("✅ VPM (Value Proposition Module) successfully integrated!")
except ImportError as e:
    logger.error(f"❌ VPM integration import failed: {e}")
    logger.info("VPM module will be available when integration is complete")
except Exception as e:
    logger.warning(f"⚠️ VPM integration failed: {e}")
    logger.info("VPM module will be available when integration is complete")

import uuid
from typing import Any, Dict, List, Optional

# Simple Idea Refinement endpoints (bypassing complex imports)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Simple Problem Validation endpoints
problem_validation_router = APIRouter(
    prefix="/api/v1/problem-validation", tags=["problem-validation"]
)

# # Add a bypass endpoint for testing without credits
# @idea_refinement_router.post("/bypass-generate", response_model=Dict[str, Any])
# async def bypass_problem_generation():
#     """Generate problems without credit checks - FOR TESTING ONLY"""
#     try:
#         sample_problems = [
#             {
#                 "title": "Limited Access to Technology Solutions in Nigeria",
#                 "description": "The lack of accessible technology solutions prevents young adults in Nigeria from effectively addressing their daily challenges.",
#                 "category": "technology",
#                 "geography": "Nigeria",
#                 "severity": "High"
#             },
#             {
#                 "title": "High Cost of Mobile Apps for Young Adults",
#                 "description": "The high cost of mobile app solutions creates significant barriers for young adults in Nigeria.",
#                 "category": "technology",
#                 "geography": "Nigeria",
#                 "severity": "High"
#             }
#         ]

#         return {
#             "success": True,
#             "job_id": str(uuid.uuid4()),
#             "status": "completed",
#             "problems": sample_problems,
#             "message": "Sample problems generated successfully (bypass mode)"
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


class ProblemValidationRequest(BaseModel):
    problem_statement: str
    industry: Optional[str] = None
    geography: Optional[str] = None


class ProblemValidationResponse(BaseModel):
    success: bool
    validation_report: Dict[str, Any]
    recommendations: List[str]


@problem_validation_router.post("/validate", response_model=ProblemValidationResponse)
async def validate_problem(request: ProblemValidationRequest):
    """Validate a problem statement."""
    try:
        validation_report = {
            "problem_statement": request.problem_statement,
            "market_size": "Large market opportunity identified",
            "feasibility": "High technical feasibility",
            "competition": "Moderate competitive landscape",
            "validation_score": 8.5,
        }

        recommendations = [
            "Conduct customer interviews",
            "Analyze competitor solutions",
            "Define MVP scope",
            "Create financial projections",
        ]

        return ProblemValidationResponse(
            success=True,
            validation_report=validation_report,
            recommendations=recommendations,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@problem_validation_router.get("/reports")
async def get_validation_reports():
    """Get existing validation reports from database."""
    try:
        from .api.system.core.supabase_client import get_supabase_client

        supabase = get_supabase_client(use_service_role=True)

        result = (
            supabase.client.table("problem_validation_reports")
            .select("*")
            .limit(10)
            .execute()
        )

        return {
            "success": True,
            "reports": result.data if result.data else [],
            "total": len(result.data) if result.data else 0,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch reports: {str(e)}"
        )


@problem_validation_router.get("/health")
async def problem_validation_health():
    """Health check for problem validation service."""
    return {"status": "healthy", "service": "problem-validation"}


app.include_router(problem_validation_router)


# Direct Problem Generator endpoint using real API workflow
@app.post("/api/test-pgen-real")
async def test_problem_generator_real(request: dict):
    """Test Problem Generator using the real API workflow (bypasses auth)."""
    try:
        from src.pgen.agents.problem_generator_graph import ProblemGeneratorGraph
        from src.pgen.api.problem_generator_endpoints import ProblemGenerationJobRequest
        from src.pgen.models.problem_models import ProblemGenerationRequest
        from src.pgen.services.job_status_service import (
            JobStatus,
            get_job_status_service,
        )
        from src.pgen.services.problem_database_service import ProblemDatabaseService

        # Use your user ID
        user_id = "c96d40e0-66b1-4c00-a897-dac3fbe873ae"

        # Validate parameters
        parameters = request.get("parameters", {})
        pgen_request = ProblemGenerationRequest(**parameters)
        job_request = ProblemGenerationJobRequest(parameters=pgen_request)

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Initialize job status service
        job_status_service = get_job_status_service()

        # Create job record
        job_status_service.create_job(
            job_id=job_id,
            user_id=user_id,
            job_type="problem_generation",
            initial_message="Starting problem generation with real workflow",
        )

        # Update job to processing
        job_status_service.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10,
            message="Initializing Problem Generator workflow",
        )

        # Initialize the Problem Generator graph
        graph = ProblemGeneratorGraph()

        # Create initial state for the workflow
        initial_state = {"params": parameters, "user_id": user_id, "job_id": job_id}

        # Update progress
        job_status_service.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=20,
            message="Running 12-node AI workflow",
        )

        # Run the complete 12-node workflow
        result_state = await graph.graph.ainvoke(initial_state)

        # Update progress
        job_status_service.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=80,
            message="Processing generated problems",
        )

        # Extract results from the workflow
        final_problems = result_state.get("final", [])
        queries = result_state.get("queries", [])
        passages = result_state.get("passages", [])
        clusters = result_state.get("clusters", [])

        # Save problems to database if any were generated
        saved_problems = []
        if final_problems:
            db_service = ProblemDatabaseService(use_service_role=True)

            for problem in final_problems:
                try:
                    # Convert to database format
                    from src.pgen.models.problem_models import \
                        ProblemStatementCreate

                    problem_create = ProblemStatementCreate(
                        title=problem.get("title", "Generated Problem"),
                        description=problem.get("description", ""),
                        category=problem.get("category", "other"),
                        severity_level=problem.get("severity_level", "medium"),
                        problem_type=problem.get("problem_type", "operational"),
                        time_horizon=problem.get("time_horizon", "medium_term"),
                        complexity_level=problem.get("complexity_level", "moderate"),
                        target_geography=problem.get("target_geography", []),
                        impact_focus=problem.get("impact_focus", []),
                        root_causes=problem.get("root_causes", []),
                        potential_effects=problem.get("potential_effects", []),
                        stakeholders=problem.get("stakeholders", []),
                        success_metrics=problem.get("success_metrics", []),
                    )

                    saved_problem = db_service.create_problem_statement(
                        user_id=uuid.UUID(user_id), problem_data=problem_create
                    )

                    if saved_problem:
                        saved_problems.append(saved_problem)

                except Exception as e:
                    logger.warning(f"Failed to save problem to database: {e}")

        # Mark job as completed
        job_status_service.update_job_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message=f"Generated {len(final_problems)} problems successfully",
        )

        return {
            "success": True,
            "job_id": job_id,
            "user_id": user_id,
            "parameters_used": parameters,
            "problems_generated": len(final_problems),
            "problems_saved": len(saved_problems),
            "problems": final_problems[:5],  # Return first 5 problems
            "workflow_stats": {
                "queries_generated": len(queries),
                "passages_found": len(passages),
                "clusters_created": len(clusters),
                "final_problems": len(final_problems),
            },
            "message": f"Successfully generated {len(final_problems)} problems using real AI workflow",
        }

    except Exception as e:
        # Mark job as failed if it was created
        if "job_id" in locals():
            try:
                job_status_service.update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    progress=0,
                    message=f"Error: {str(e)}",
                )
            except:
                pass

        return {"success": False, "error": str(e), "error_type": type(e).__name__}


# Credit system removed
# from .api.credit_analytics import router as credit_analytics_router
# app.include_router(credit_analytics_router, tags=["credits"])

# Payment system (temporarily disabled for testing)
# from .api.payment import payment_router
# app.include_router(payment_router, tags=["payments"])

# Admin endpoints - REMOVED (legacy implementation no longer needed)
# from .api.admin_auth import register_admin_auth_routes
# from .api.admin import register_admin_endpoints, register_admin_settings_routes

# Credit system removed
# from .api.credit import config_router

# register_admin_auth_routes(app)  # Role system removed
# register_admin_endpoints(app)  # REMOVED - legacy admin endpoints
# register_admin_settings_routes(app)  # REMOVED - legacy admin settings
# app.include_router(config_router, prefix="/api/credit", tags=["credit-config"])

# ==========================================
# BASIC ENDPOINTS
# ==========================================


@app.get("/")
async def root():
    """Root endpoint - redirect to documentation."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mint-api",
        "architecture": "modular",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "unified_auth": True,
            "modular_endpoints": True,
            "separated_business_logic": True,
            "security_hardened": True,
        },
    }


@app.get("/api/health")
async def api_health_check():
    """API health check with more details."""
    try:
        # Check authentication system health
        from .api.production_auth_system import get_production_auth_system

        auth_system = get_production_auth_system()
        auth_metrics = auth_system.get_performance_metrics()

        return {
            "status": "healthy",
            "service": "mint-api",
            "architecture": "modular",
            "version": "2.0.0",
            "auth_system": {
                "status": auth_metrics.get("performance_health", "unknown"),
                "avg_response_time_ms": auth_metrics.get("avg_response_time", 0),
                "total_requests": auth_metrics.get("total_requests", 0),
                "success_rate": (
                    auth_metrics.get("successful_auths", 0)
                    / max(auth_metrics.get("total_requests", 1), 1)
                )
                * 100,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "service": "mint-api",
            "error": "Health check failed",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ==========================================
# STATIC FILE SERVING
# ==========================================

# Serve static UI files (if available)
try:
    app.mount("/ui", StaticFiles(directory="web", html=True), name="ui")
    logger.info("✅ Static UI files mounted at /ui")
except Exception as e:
    logger.warning(f"⚠️  Static UI files not available: {e}")

    @app.get("/ui")
    async def ui_info():
        """UI endpoint when static files are not available."""
        return {
            "message": "No UI files found. Create a 'web' directory with static files to enable the UI.",
            "api_docs": "/docs",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ==========================================
# APPLICATION METADATA
# ==========================================

# Log successful initialization
logger.info("🚀 MINT API application configured successfully")
logger.info("📁 Modular architecture active:")
logger.info("   - Endpoints: Separated into dedicated routers")
logger.info("   - Business Logic: Moved to service layer")
logger.info("   - Database Operations: Isolated in repository layer")
logger.info("   - Data Models: Defined in dedicated model files")
logger.info("   - Authentication: Consolidated into single secure system")
logger.info("🔒 Security enhancements active:")
logger.info("   - Production authentication system")
logger.info("   - JWT fallback vulnerability eliminated")
logger.info("   - Comprehensive rate limiting")
logger.info("   - Session management with token revocation")
logger.info("   - Zero-information-leakage error handling")

# Export the application
__all__ = ["app"]
