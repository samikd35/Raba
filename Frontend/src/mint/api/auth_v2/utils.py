import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.mint.api.system.core.supabase_client import get_service_role_client

# Load from env
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

oauth2_scheme = HTTPBearer()

logger = logging.getLogger(__name__)


# password
def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    Returns the hashed password as a UTF-8 string.
    """
    salt = bcrypt.gensalt()  # Automatically picks a good cost factor
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plaintext password matches the hashed password.
    Returns True if valid, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# token
def create_access_token(
    email: str,
    roles: list,
    user_id: str,
    tenant_id: str,
    tenant_type: str,
    can_skip_module: Optional[bool] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "roles": roles,
        "exp": expire,
        "type": "access",
        "uid": user_id,
        "tenant_id": tenant_id,
        "tenant_type": tenant_type,
        "can_skip_module": can_skip_module,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, email: str, roles: list) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "roles": roles,
        "uid": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Check revocation
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def refresh_access_token(refresh_token: str, user_id: str) -> str:
    """
    Validate refresh token (from DB + decode) and issue a new access token.
    """
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh" or payload.get("uid") != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token type"
        )

    # Issue new access token
    return create_access_token(
        email=payload["sub"], roles=payload["roles"], user_id=payload["uid"]
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
):
    """
    Get current authenticated user.

    This dependency validates the token directly with Supabase.
    """
    try:
        token = credentials.credentials
        logger.info("Validating token for user authentication")

        # Get Supabase client and validate token
        payload = decode_token(token)
        return {
            "email": payload.get("sub"),
            "roles": payload.get("roles"),
            "user_id": payload.get("uid"),
            "tenant_id": payload.get("tenant_id"),
            "tenant_type": payload.get("tenant_type"),
            "can_skip_module": payload.get("can_skip_module"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "authentication_failed",
                "message": "Invalid authentication token",
            },
        )


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that ensures the current user has role 'admin' or higher.
    """
    if current_user["roles"][0] not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def get_super_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that ensures the current user has role 'super_admin'.
    """
    if current_user["roles"][0] != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return current_user


def check_self_or_admin(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Ensure the user is either:
    - The same user (self), OR
    - An admin/super_admin.

    Args:
        current_user: dict from get_current_user()
        target_user_id: str ID of the user being accessed
        action: str description for error messages (e.g., 'edit profile')

    Raises:
        HTTPException if not allowed
    """
    if current_user["user_id"] != user_id and current_user["roles"][0] not in [
        "admin",
        "super_admin",
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed for this user",
        )
    return current_user


def check_self_or_super_admin(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Ensure the user is either:
    - The same user (self), OR
    - An admin/super_admin.

    Args:
        current_user: dict from get_current_user()
        target_user_id: str ID of the user being accessed
        action: str description for error messages (e.g., 'edit profile')

    Raises:
        HTTPException if not allowed
    """
    if current_user["user_id"] != user_id and current_user["roles"][0] != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed for this user",
        )
    return current_user


def _check_tenant(current_user: dict, tenant_id: str):
    if current_user.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch",
        )


def get_tenant_id(request: Request) -> str:
    """
    Resolve tenant_id strictly from PATH params:
    - /orgs/{organization_id}/...  -> organization_id
    - /teams/{team_id}/...         -> team_id
    - /tenants/{tenant_id}/...     -> tenant_id

    No query parameters are created/exposed.
    """
    p = request.path_params
    tenant_id = p.get("tenant_id") or p.get("organization_id") or p.get("team_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A tenant identifier is required in the path.",
        )
    return tenant_id


def get_organization_id(request: Request) -> str:
    """
    Resolve organization_id strictly from PATH params.
    Used for organization admin endpoints where organization_id should be
    used for tenant verification (not tenant_id which may refer to a member).
    """
    p = request.path_params
    organization_id = p.get("organization_id")
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An organization_id is required in the path.",
        )
    return organization_id


def get_tenant_member(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _check_tenant(current_user, tenant_id)
    if len(current_user["roles"]) < 2 or current_user["roles"][1] not in [
        "member",
        "admin",
        "owner",
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant member privileges required",
        )
    return current_user


def get_tenant_admin_only(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _check_tenant(current_user, tenant_id)
    if len(current_user["roles"]) < 2 or current_user["roles"][1] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin only privileges required",
        )
    return current_user


def get_tenant_admin(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _check_tenant(current_user, tenant_id)
    if len(current_user["roles"]) < 2 or current_user["roles"][1] not in [
        "admin",
        "owner",
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin privileges required",
        )
    return current_user


def get_tenant_owner(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _check_tenant(current_user, tenant_id)
    if len(current_user["roles"]) < 2 or current_user["roles"][1] != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant owner privileges required",
        )
    return current_user


def get_global_admin_or_tenant_member(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    roles = current_user.get("roles", [])
    if not (
        roles[0] in ["admin", "super_admin"]
        or (len(roles) > 1 and roles[1] in ["admin", "owner", "member"])
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires global admin/super_admin OR tenant member",
        )
    if roles[0] not in ["admin", "super_admin"]:
        _check_tenant(current_user, tenant_id)
    return current_user


def get_global_admin_or_tenant_admin(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    roles = current_user.get("roles", [])
    if not (
        roles[0] in ["admin", "super_admin"]
        or (len(roles) > 1 and roles[1] in ["admin", "owner"])
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires global admin/super_admin OR tenant admin",
        )
    if roles[0] not in ["admin", "super_admin"]:
        _check_tenant(current_user, tenant_id)
    return current_user


def get_global_admin_or_tenant_owner(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    roles = current_user.get("roles", [])
    if not (
        roles[0] in ["admin", "super_admin"] or (len(roles) > 1 and roles[1] == "owner")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires global admin/super_admin OR tenant owner",
        )
    if roles[0] not in ["admin", "super_admin"]:
        _check_tenant(current_user, tenant_id)
    return current_user


def get_global_admin_or_org_owner(
    organization_id: str = Depends(get_organization_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Authorization dependency for organization admin endpoints.
    Uses organization_id (not tenant_id) for tenant verification.
    This is needed for endpoints like /{organization_id}/tenants/{tenant_id}/projects
    where tenant_id refers to a member, not the organization.
    """
    roles = current_user.get("roles", [])
    if not (
        roles[0] in ["admin", "super_admin"] or (len(roles) > 1 and roles[1] == "owner")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires global admin/super_admin OR organization owner",
        )
    if roles[0] not in ["admin", "super_admin"]:
        _check_tenant(current_user, organization_id)
    return current_user


def get_super_admin_or_tenant_admin(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    roles = current_user.get("roles", [])
    if not (
        roles[0] == "super_admin" or (len(roles) > 1 and roles[1] in ["admin", "owner"])
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires global super_admin OR tenant admin",
        )
    if roles[0] != "super_admin":
        _check_tenant(current_user, tenant_id)
    return current_user


def get_super_admin_or_tenant_owner(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    roles = current_user.get("roles", [])
    if not (roles[0] == "super_admin" or (len(roles) > 1 and roles[1] == "owner")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires global super_admin OR tenant owner",
        )
    if roles[0] != "super_admin":
        _check_tenant(current_user, tenant_id)
    return current_user


# =====================================================
# VENTURE BUILDER ROLE CHECKS
# =====================================================

def get_vb_or_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that ensures the current user is either:
    - A venture_builder, OR
    - An admin, OR
    - A super_admin

    Args:
        current_user: User dict from get_current_user

    Returns:
        current_user dict if authorized

    Raises:
        HTTPException 403 if user doesn't have required role
    """
    user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None

    if user_role not in ["venture_builder", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Venture Builder or Admin privileges required",
        )

    return current_user


def get_venture_builder_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that ensures the current user has 'venture_builder' role.

    Args:
        current_user: User dict from get_current_user

    Returns:
        current_user dict if authorized

    Raises:
        HTTPException 403 if user is not a venture builder
    """
    user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None

    if user_role != "venture_builder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Venture Builder privileges required",
        )

    return current_user


def get_vb_or_super_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that ensures the current user is either:
    - A venture_builder, OR
    - A super_admin

    Args:
        current_user: User dict from get_current_user

    Returns:
        current_user dict if authorized

    Raises:
        HTTPException 403 if user doesn't have required role
    """
    user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None

    if user_role not in ["venture_builder", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Venture Builder or Super Admin privileges required",
        )

    return current_user
