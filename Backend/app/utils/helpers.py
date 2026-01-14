"""RABA Helper Utilities."""

import uuid
from datetime import datetime, timezone


def generate_workflow_id() -> str:
    """Generate a unique workflow ID."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return utc_now().isoformat()
