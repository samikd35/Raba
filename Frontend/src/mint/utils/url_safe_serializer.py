import os

from dotenv import load_dotenv
from fastapi import HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeSerializer

load_dotenv()

SECRET_KEY = os.getenv("INVITE_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("INVITE_SECRET_KEY environment variable is required but not set")

serializer = URLSafeSerializer(SECRET_KEY, salt="tenant-invite")


# Create invite token
def create_invite_token(tenant_id: str, is_admin: bool, credit: int = None, is_team_leader: bool = False) -> str:
    return serializer.dumps(
        {"tenant_id": tenant_id, "is_admin": is_admin, "credits": credit, "is_team_leader": is_team_leader}
    )


# Verify invite token (with 48h expiration)
def verify_invite_token(token: str, tenant_id: str) -> dict:
    try:
        data = serializer.loads(token, max_age=48 * 3600)  # 48 hours in seconds
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Invite link expired")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid invite token")

    if data.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=400, detail="Organization mismatch in invite token"
        )

    return data
