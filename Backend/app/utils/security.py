"""RABA Security Utilities.

Input sanitization and security helpers.

Reference: Phase 5.1.1 - Input Sanitization
"""

import html
import re
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)

DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # Script tags
    r"javascript:",                  # JavaScript protocol
    r"on\w+\s*=",                   # Event handlers
    r"data:\s*text/html",           # Data URLs with HTML
]

SQL_INJECTION_PATTERNS = [
    r";\s*DROP\s+",
    r";\s*DELETE\s+",
    r";\s*UPDATE\s+.*SET",
    r"'\s*OR\s+'1'\s*=\s*'1",
    r"--\s*$",
    r"/\*.*\*/",
]

MAX_TOPIC_LENGTH = 500
MAX_INPUT_LENGTH = 10000


def sanitize_text(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitize user text input.
    
    - Strips whitespace
    - Escapes HTML entities
    - Truncates to max length
    - Removes null bytes
    
    Args:
        text: Raw user input
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Strip whitespace
    text = text.strip()
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Input truncated to {max_length} chars")
    
    return text


def sanitize_topic(topic: str) -> str:
    """
    Sanitize video topic input.
    
    Args:
        topic: User-provided topic
        
    Returns:
        Sanitized topic
    """
    return sanitize_text(topic, max_length=MAX_TOPIC_LENGTH)


def check_dangerous_content(text: str) -> tuple[bool, Optional[str]]:
    """
    Check for potentially dangerous content patterns.
    
    Args:
        text: Text to check
        
    Returns:
        Tuple of (is_safe, reason if unsafe)
    """
    text_lower = text.lower()
    
    # Check for XSS patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
            logger.warning(f"Dangerous pattern detected: {pattern}")
            return False, "Content contains potentially dangerous patterns"
    
    # Check for SQL injection
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(f"SQL injection pattern detected: {pattern}")
            return False, "Content contains potentially dangerous patterns"
    
    return True, None


def mask_api_key(key: str, visible_chars: int = 4) -> str:
    """
    Mask an API key for safe logging.
    
    Args:
        key: API key to mask
        visible_chars: Number of chars to show at start and end
        
    Returns:
        Masked key like "AIza...Mwc"
    """
    if not key or len(key) <= visible_chars * 2:
        return "***"
    
    return f"{key[:visible_chars]}...{key[-visible_chars:]}"


def mask_sensitive_data(data: dict, sensitive_keys: Optional[list[str]] = None) -> dict:
    """
    Mask sensitive data in a dictionary for safe logging.
    
    Args:
        data: Dictionary containing potentially sensitive data
        sensitive_keys: Keys to mask (default: common sensitive keys)
        
    Returns:
        Dictionary with masked sensitive values
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "api_key", "apikey", "api-key",
            "token", "access_token", "refresh_token",
            "password", "secret", "credential",
            "authorization", "auth",
            "supabase_key", "redis_url",
            "google_api_key", "langchain_api_key",
        ]
    
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        if any(sk in key_lower for sk in sensitive_keys):
            if isinstance(value, str):
                masked[key] = mask_api_key(value)
            else:
                masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked[key] = value
    
    return masked


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid UUID format
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Remove path separators
    filename = re.sub(r'[/\\]', '', filename)
    
    # Remove special characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename
