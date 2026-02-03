"""
Example implementation of role-based access control using the enhanced authentication middleware.

This module demonstrates how to set up and use role-based access control in a FastAPI application.
"""
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from src.mint.api.auth import (
    EnhancedAuthMiddleware,
    get_current_user_with_roles,
    requires_roles
)

# Create FastAPI application
app = FastAPI(title="MINT API with Role-Based Access Control")

# Add the enhanced authentication middleware
app.add_middleware(
    EnhancedAuthMiddleware,
    supabase_url=os.getenv("SUPABASE_URL", ""),
    api_key=os.getenv("SUPABASE_KEY", ""),
    exclude_paths=["/docs", "/openapi.json", "/health", "/public"],
    role_protected_paths={
        "/admin/": ["admin"],
        "/reports/": ["analyst", "admin"],
        "/settings/": ["admin"]
    }
)

# Define some models for our API
class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []


class Report(BaseModel):
    id: str
    title: str
    content: str
    created_by: str


# Public endpoint - no authentication required
@app.get("/public/health")
async def health_check():
    """Public health check endpoint that doesn't require authentication."""
    return {"status": "ok"}


# Protected endpoint - requires authentication but no specific role
@app.get("/profile", response_model=UserProfile)
async def get_profile(user_info: Dict = Depends(get_current_user_with_roles)):
    """Get the current user's profile. Requires authentication but no specific role."""
    return UserProfile(
        user_id=user_info["user_id"],
        display_name="Example User",
        email="user@example.com",
        roles=user_info["roles"]
    )


# Admin-only endpoint using the requires_roles dependency
@app.get("/admin/users")
async def list_users(user_info: Dict = Depends(requires_roles("admin"))):
    """List all users. Requires admin role."""
    # In a real application, this would fetch users from a database
    return {
        "message": f"Access granted to admin {user_info['user_id']}",
        "users": [
            {"id": "user1", "name": "User One"},
            {"id": "user2", "name": "User Two"}
        ]
    }


# Endpoint that accepts multiple roles
@app.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user_info: Dict = Depends(requires_roles(["analyst", "admin"]))
):
    """Get a specific report. Requires analyst or admin role."""
    # In a real application, this would fetch the report from a database
    return Report(
        id=report_id,
        title="Example Report",
        content="This is an example report content.",
        created_by="system"
    )


# Settings endpoint - protected by middleware path configuration
@app.put("/settings/system")
async def update_system_settings(
    settings: Dict,
    user_info: Dict = Depends(get_current_user_with_roles)
):
    """
    Update system settings.
    
    This endpoint is protected by the middleware's role_protected_paths configuration,
    which requires the admin role for all paths starting with /settings/.
    """
    return {
        "message": "Settings updated successfully",
        "updated_by": user_info["user_id"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)