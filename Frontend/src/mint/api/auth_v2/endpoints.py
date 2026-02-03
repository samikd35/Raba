import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from google.auth.transport import requests
from google.oauth2 import id_token
from src.mint.utils.url_safe_serializer import serializer

from ..services.communication.email_service import email_service
from ..tenant.service import TenantService
from .models import (CompleteSignupRequest, CreateUserRequest,
                     DirectSignupRequest, GoogleSignInRequest, LoginRequest,
                     PasswordResetConfirmRequest, PasswordResetEmailRequest,
                     SignupEmailRequest, UpdatePasswordRequest,
                     UpdateProfileRequest, WaitlistJoinRequest,
                     WaitlistJoinResponse, WaitlistCheckResponse,
                     WaitlistStatsResponse, WaitlistBatchInviteRequest,
                     WaitlistBatchInviteResponse)
from .service import AuthService
from .waitlist_service import WaitlistService
from .utils import (check_self_or_admin, check_self_or_super_admin,
                    create_access_token, get_admin_user, get_current_user,
                    get_super_admin_user, verify_password)

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

auth_router = APIRouter()

oauth2_scheme = HTTPBearer()

auth_service = AuthService()
waitlist_service = WaitlistService()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
DUMMY_PASSWORD = os.getenv("DUMMY_PASSWORD")


@auth_router.post("/signup/send-link")
async def send_signup_link(request: SignupEmailRequest):
    """
    Start sign-up by sending a verification link to the email.
    """
    try:
        # Check if user already exists
        existing_user = auth_service.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email is already registered")

        token = serializer.dumps({"email": request.email})

        frontend_url = os.getenv("FRONTEND_URL", "")
        signup_link = f"{frontend_url}/signup-verify?token={token}"
        # signup_link = f"http://localhost:8000/signup/verify?token={token}"

        subject = "Complete your sign-up"
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a90e2; color: white; padding: 10px 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ display: inline-block; background-color: #4a90e2; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome!</h1>
                </div>
                <div class="content">
                    <p>Click the link below to complete your registration:</p>
                    <p>You have <strong>1 hour</strong> to finish your registration.</p>
                    <p style="text-align: center;">
                        <a href="{signup_link}" class="button">Complete Sign-up</a>
                    </p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """

        email_sent = email_service.send_email(
            to_email=request.email, subject=subject, html_content=html_content
        )
        if not email_sent:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong trying to send the email",
            )

        return {"message": "Sign-up link sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error sending sign-up email: {str(e)}"
        )


@auth_router.post("/signup/verify")
async def complete_signup(data: CompleteSignupRequest):
    try:
        # Decode token and extract email
        payload = serializer.loads(data.token, max_age=3600)
        email = payload["email"]

        # Use service to create user
        user = await auth_service.create_user_profile(
            email=email,
            password=data.password,
            full_name=data.full_name,
            avatar_url=data.avatar_url,
            timezone=data.timezone,
            preferences=data.preferences,
            bio=data.bio,
            website=data.website,
            location=data.location,
        )

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Error verifying email or creating user",
            )

        return {"message": "User created successfully", "user": user}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error verifying email or creating user: {str(e)}",
        )


@auth_router.post("/signup/direct")
async def direct_signup(data: DirectSignupRequest):
    try:
        existing_user = auth_service.get_user_by_email(data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email is already registered")

        user = await auth_service.create_user_profile(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            avatar_url=data.avatar_url,
            timezone=data.timezone,
            preferences=data.preferences,
            bio=data.bio,
            website=data.website,
            location=data.location,
        )

        if not user:
            raise HTTPException(status_code=400, detail="Error creating user")

        # Get or create individual tenant for the user
        tenant_id = await auth_service.get_individual_tenant_for_user(
            user["id"], user["full_name"], user["email"]
        )

        # Generate access token (can_skip_module is None for new signup)
        access_token = create_access_token(
            email=user["email"],
            roles=[user.get("role", "user"), "owner"],
            user_id=user["id"],
            tenant_id=tenant_id,
            tenant_type="individual",
            can_skip_module=None,
        )

        return {
            "message": "User created successfully",
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "tenant_id": tenant_id,
                "tenant_type": "individual",
                "full_name": user.get("full_name"),
                "roles": [user.get("role", "user"), "owner"],
                "can_skip_module": None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating user: {str(e)}",
        )


@auth_router.post("/login")
async def login(data: LoginRequest):
    """
    Authenticate user and return access & refresh tokens.
    """
    try:
        # Fetch user by email
        user = auth_service.get_user_by_email(data.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Verify password
        if not verify_password(data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        tenant_id = await auth_service.get_individual_tenant_for_user(
            user["id"], user["full_name"], user["email"]
        )

        # Generate tokens (can_skip_module is None for individual tenant login)
        access_token = create_access_token(
            email=user["email"],
            roles=[user.get("role", "user"), "owner"],
            user_id=user["id"],
            tenant_id=tenant_id,
            tenant_type="individual",
            can_skip_module=None,
        )

        return {
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "tenant_id": tenant_id,
                "tenant_type": "individual",
                "full_name": user.get("full_name"),
                "roles": [user.get("role"), "owner"],
                "can_skip_module": None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@auth_router.post("/login/{tenant_id}")
async def tenant_login(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """
    Tenant-specific login:
    - Requires global login first (valid token).
    - Accepts tenant_id.
    - Checks tenant_memberships table for user membership.
    - Issues a new access token with [global_role, tenant_role].
    """
    try:
        membership = auth_service.get_tenant_membership(
            tenant_id=tenant_id, user_id=current_user["user_id"]
        )
        tenant = auth_service.get_tenant_details(tenant_id)

        if not membership:
            raise HTTPException(
                status_code=403, detail="User is not a member of this tenant"
            )

        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid tenant id")

        # Get can_skip_module from org_teams or org_individuals if in an organization
        can_skip_module = auth_service.get_can_skip_module(
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            tenant_type=tenant["tenant_type"],
        )

        # Issue new token with both roles
        access_token = create_access_token(
            email=current_user["email"],
            roles=[current_user["roles"][0], membership["role"]],
            user_id=current_user["user_id"],
            tenant_id=tenant_id,
            tenant_type=tenant["tenant_type"],
            can_skip_module=can_skip_module,
        )

        return {
            "access_token": access_token,
            "tenant_id": tenant_id,
            "tenant_type": tenant["tenant_type"],
            "user_id": current_user["user_id"],
            "email": current_user["email"],
            "roles": [current_user["roles"][0], membership["role"]],
            "can_skip_module": can_skip_module,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant login failed: {str(e)}")


@auth_router.post("/google-signin")
async def google_signin(data: GoogleSignInRequest):
    """
    Sign in with Google using ID token.
    - Verifies the token with Google
    - If user doesn't exist, creates them
    - Returns access token
    """
    try:
        # Verify Google token
        id_info = id_token.verify_oauth2_token(
            data.id_token, requests.Request(), GOOGLE_CLIENT_ID
        )

        email = id_info["email"]
        first_name = id_info.get("given_name", "")
        last_name = id_info.get("family_name", "")
        avatar_url = id_info.get("picture")

        # Get or create user
        user, tenant_id, tenant_type = await auth_service.get_or_create_google_user(
            email,
            password=DUMMY_PASSWORD,
            full_name=f"{first_name} {last_name}",
            avatar_url=avatar_url,
        )

        if not user:
            raise HTTPException(
                status_code=500, detail="Failed to create or fetch user"
            )

        # Create token (can_skip_module is None for individual tenant login)
        tenant_type = tenant_type or "individual"
        access_token = create_access_token(
            email=user["email"],
            roles=[user.get("role", "user"), "owner"],
            user_id=user["id"],
            tenant_id=tenant_id,
            tenant_type=tenant_type,
            can_skip_module=None,
        )

        return {
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user.get("full_name"),
                "avatar_url": user.get("avatar_url"),
                "roles": [user.get("role", "user"), "owner"],
                "tenant_id": tenant_id,
                "tenant_type": tenant_type,
                "can_skip_module": None,
            },
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google ID token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google sign-in failed: {str(e)}")


@auth_router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get the current authenticated user (from access token).
    """
    try:
        user = auth_service.get_user_by_email(current_user["email"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        tenant_id = current_user.get("tenant_id")
        service = TenantService()

        try:
            tenant = await service.get_tenant(tenant_id)
        except Exception:
            tenant = None

        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "avatar_url": user.get("avatar_url"),
            "timezone": user.get("timezone"),
            "preferences": user.get("preferences", {}),
            "bio": user.get("bio"),
            "website": user.get("website"),
            "location": user.get("location"),
            "roles": current_user["roles"],
            "tenant_id": current_user["tenant_id"],
            "tenant_type": current_user["tenant_type"],
            "tenant": tenant.data if tenant and tenant.data else None,
            "can_skip_module": current_user.get("can_skip_module"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")


@auth_router.post("/create-user")
async def create_user(
    data: CreateUserRequest, current_user: dict = Depends(get_super_admin_user)
):
    """
    Super Admin can create a new user with any role (user, admin, super_admin).
    """
    try:
        user = await auth_service.create_user_with_role(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            avatar_url=data.avatar_url,
            timezone=data.timezone,
            preferences=data.preferences,
            bio=data.bio,
            website=data.website,
            location=data.location,
            role=data.role,
        )

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Error creating user",
            )

        return {"message": "User created successfully", "user": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.put("/users/{user_id}")
async def edit_profile(
    user_id: str,
    data: UpdateProfileRequest,
    current_user: dict = Depends(check_self_or_admin),
):
    """
    Update a user profile.
    - Users can update their own profile.
    - Admins & Super Admins can update any profile.
    - None values are ignored (do not overwrite).
    """
    try:
        # Only include provided fields and skip None
        updates = {k: v for k, v in data.dict().items() if v is not None}

        if not updates:
            raise HTTPException(
                status_code=400, detail="No valid fields provided for update"
            )

        user = auth_service.update_user_profile(user_id, updates)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "Profile updated successfully", "user": user}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update profile: {str(e)}"
        )


@auth_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(check_self_or_super_admin),
):
    """
    Delete a user profile.
    - Only Super Admins can delete accounts.
    """
    try:
        success = auth_service.delete_user_profile(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@auth_router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(check_self_or_admin)):
    """
    Get a user by ID.
    - The user themselves can access their profile.
    - Admins & Super Admins can access any profile.
    """
    try:
        user = auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")


@auth_router.get("/users")
async def get_users(current_user: dict = Depends(get_admin_user)):
    """
    Get all users.
    - Admins & Super Admins can access.
    """
    try:
        users = auth_service.get_all_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@auth_router.put("/users/{user_id}/password")
async def update_password(
    user_id: str,
    data: UpdatePasswordRequest,
    current_user: dict = Depends(check_self_or_admin),
):
    """
    Update a user's password.
    - Users can update their own password.
    - Admins & Super Admins can update any user's password.
    """
    try:
        user = auth_service.update_user_password(user_id, data.new_password)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "Password updated successfully", "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update password: {str(e)}"
        )


""" @auth_router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user),
):
    try:
        token = credentials.credentials
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

        auth_service.supabase.table("revoked_tokens").insert(
            {
                "token": token,
                "user_id": current_user["user_id"],
                "expires_at": expires_at,
            }
        ).execute()

        return {"message": "Logout successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}") """


@auth_router.post("/reset-password/send-link")
async def send_reset_password_link(
    request: PasswordResetEmailRequest
):
    """
    Send a password reset email with a secure token link.
    """
    try:
        user = auth_service.get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        token = serializer.dumps({"email": request.email})
        frontend_url = os.getenv("FRONTEND_URL", "")
        reset_link = f"{frontend_url}/reset-password?token={token}"

        subject = "Password Reset Request"
        html_content = f"""
        <html>
        <body>
            <h3>Password Reset</h3>
            <p>Click the link below to reset your password. This link expires in 1 hour.</p>
            <a href="{reset_link}" style="background:#4a90e2;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Reset Password</a>
            <p>If you didn’t request this, you can ignore this email.</p>
        </body>
        </html>
        """

        email_sent = email_service.send_email(
            to_email=request.email, subject=subject, html_content=html_content
        )

        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send reset email")

        return {"message": "Password reset link sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@auth_router.post("/reset-password/confirm")
async def reset_password_confirm(
    data: PasswordResetConfirmRequest,
):
    """
    Accept a valid token and reset the user's password.
    """
    try:
        payload = serializer.loads(data.token, max_age=3600)
        email = payload.get("email")

        user = auth_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        updated_user = auth_service.update_user_password(user["id"], data.new_password)

        if not updated_user:
            raise HTTPException(status_code=400, detail="Failed to update password")

        return {"message": "Password reset successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Password reset failed: {str(e)}")


# ============================================================
# WAITLIST ENDPOINTS
# ============================================================


@auth_router.post("/waitlist/join", response_model=WaitlistJoinResponse)
async def join_waitlist(data: WaitlistJoinRequest):
    """
    Join the waitlist. Public endpoint - no auth required.

    When user later signs up with this email, they receive:
    - Normal trial credits (35 credits)
    - BONUS waitlist credits (100 credits) with source="waitlist_bonus"
    """
    try:
        result = waitlist_service.add_to_waitlist(
            email=data.email,
            source=data.source,
            referral_code=data.referral_code,
            metadata=data.metadata,
        )

        return WaitlistJoinResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to join waitlist: {str(e)}")


@auth_router.get("/waitlist/check/{email}", response_model=WaitlistCheckResponse)
async def check_waitlist_status(email: str):
    """
    Check if email is on waitlist (public, for UX purposes).
    """
    try:
        result = waitlist_service.check_waitlist_status(email)
        return WaitlistCheckResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check waitlist status: {str(e)}"
        )


@auth_router.get("/waitlist/stats", response_model=WaitlistStatsResponse)
async def get_waitlist_stats(current_user: dict = Depends(get_admin_user)):
    """
    Get waitlist statistics (admin only).
    """
    try:
        stats = waitlist_service.get_stats()
        return WaitlistStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get waitlist stats: {str(e)}"
        )


@auth_router.get("/waitlist/entries")
async def list_waitlist_entries(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_admin_user),
):
    """
    List waitlist entries (admin only).
    """
    try:
        entries = waitlist_service.list_entries(
            status=status, limit=limit, offset=offset
        )
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list waitlist entries: {str(e)}"
        )


@auth_router.post("/waitlist/send-invitations", response_model=WaitlistBatchInviteResponse)
async def send_waitlist_invitations(
    data: WaitlistBatchInviteRequest = None,
    current_user: dict = Depends(get_admin_user),
):
    """
    Send signup invitation emails to pending waitlist users (admin only).
    
    This endpoint sends emails to all users with status='pending' in the waitlist.
    After sending, their status is updated to 'invited'.
    
    - **batch_size**: Optional. Number of emails to send. If not provided, sends to all pending users.
    
    When users click the signup link and complete registration, they will receive:
    - Normal trial credits (35 credits)
    - BONUS waitlist credits (100 credits)
    """
    try:
        batch_size = data.batch_size if data else None
        result = waitlist_service.send_batch_signup_invitations(batch_size=batch_size)
        return WaitlistBatchInviteResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send waitlist invitations: {str(e)}"
        )
