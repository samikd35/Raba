"""
Utility functions for the API
"""
import uuid
import os
from typing import Optional

def is_production_env() -> bool:
    """Check if we're running in production environment"""
    env = os.getenv('ENVIRONMENT', '').lower()
    return env == 'production'

def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID
    
    Args:
        value: String to check
        
    Returns:
        bool: True if the string is a valid UUID, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(value)
        return str(uuid_obj) == value
    except (ValueError, AttributeError, TypeError):
        return False

def get_deterministic_uuid_for_user(user_id: str) -> str:
    """
    Generate a deterministic UUID for a user ID string.
    This ensures the same user_id always maps to the same UUID.
    
    Args:
        user_id: User ID string
        
    Returns:
        str: UUID string
    """
    # Use a fixed namespace for deterministic generation
    namespace = uuid.UUID('00000000-0000-0000-0000-000000000000')
    return str(uuid.uuid5(namespace, user_id))
