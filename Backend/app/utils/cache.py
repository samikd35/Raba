"""RABA Cache Utilities.

Provides standardized cache key generation and TTL management.
Reference: RABA_Architecture.md Section 9.2 - Cache Key Naming Convention
"""

import hashlib
from typing import Optional

from app.config import settings


class CacheKeys:
    """
    Standardized cache key naming.
    
    All keys use the format: raba:{category}:{identifier}
    Reference: Architecture Section 9.2
    """
    
    PREFIX = "raba:"
    
    # TTL values (seconds) - loaded from settings
    TTL_SHORT = 3600         # 1 hour (tools list, sessions)
    TTL_MEDIUM = 86400       # 1 day (scripts, image prompts)
    TTL_LONG = 604800        # 7 days (research)
    
    @classmethod
    def _hash(cls, value: str, length: int = 16) -> str:
        """Generate a truncated SHA256 hash of a string."""
        return hashlib.sha256(value.lower().strip().encode()).hexdigest()[:length]
    
    @classmethod
    def research(cls, topic: str, depth: str = "standard") -> str:
        """
        Generate cache key for research results.
        
        Args:
            topic: Research topic
            depth: Research depth ("quick", "standard", "deep")
            
        Returns:
            Cache key: raba:research:{topic_hash}:{depth}
        """
        topic_hash = cls._hash(topic)
        return f"{cls.PREFIX}research:{topic_hash}:{depth}"
    
    @classmethod
    def research_ttl(cls) -> int:
        """Get TTL for research cache (from settings or default 7 days)."""
        return getattr(settings, 'cache_ttl_research', cls.TTL_LONG)
    
    @classmethod
    def script(cls, research_hash: str, tool_id: str) -> str:
        """
        Generate cache key for generated scripts.
        
        Args:
            research_hash: Hash of the research data
            tool_id: Tool ID used for generation
            
        Returns:
            Cache key: raba:script:{research_hash}:{tool_id}
        """
        return f"{cls.PREFIX}script:{research_hash}:{tool_id}"
    
    @classmethod
    def script_ttl(cls) -> int:
        """Get TTL for script cache (1 day)."""
        return cls.TTL_MEDIUM
    
    @classmethod
    def image_prompt(cls, script_hash: str) -> str:
        """
        Generate cache key for image generation prompts.
        
        Args:
            script_hash: Hash of the script
            
        Returns:
            Cache key: raba:image_prompt:{script_hash}
        """
        return f"{cls.PREFIX}image_prompt:{script_hash}"
    
    @classmethod
    def image_prompt_ttl(cls) -> int:
        """Get TTL for image prompt cache (1 day)."""
        return cls.TTL_MEDIUM
    
    @classmethod
    def tools_list(cls) -> str:
        """
        Generate cache key for tools list.
        
        Returns:
            Cache key: raba:tools:list
        """
        return f"{cls.PREFIX}tools:list"
    
    @classmethod
    def tools_ttl(cls) -> int:
        """Get TTL for tools cache (from settings or default 1 hour)."""
        return getattr(settings, 'cache_ttl_tools', cls.TTL_SHORT)
    
    @classmethod
    def tools_by_category(cls, category: str) -> str:
        """
        Generate cache key for tools filtered by category.
        
        Args:
            category: Tool category
            
        Returns:
            Cache key: raba:tools:category:{category}
        """
        return f"{cls.PREFIX}tools:category:{category}"
    
    @classmethod
    def user_session(cls, user_id: str) -> str:
        """
        Generate cache key for user session data.
        
        Args:
            user_id: User UUID
            
        Returns:
            Cache key: raba:session:{user_id}
        """
        return f"{cls.PREFIX}session:{user_id}"
    
    @classmethod
    def session_ttl(cls) -> int:
        """Get TTL for session cache (1 hour)."""
        return cls.TTL_SHORT
    
    @classmethod
    def job_status(cls, job_id: str) -> str:
        """
        Generate cache key for workflow/job status.
        
        Args:
            job_id: Workflow UUID
            
        Returns:
            Cache key: raba:job:{job_id}
        """
        return f"{cls.PREFIX}job:{job_id}"
    
    @classmethod
    def job_status_ttl(cls) -> int:
        """Get TTL for job status cache (24 hours)."""
        return cls.TTL_MEDIUM
    
    @classmethod
    def rate_limit(cls, identifier: str, endpoint: str) -> str:
        """
        Generate cache key for rate limiting.
        
        Args:
            identifier: IP address or user ID
            endpoint: API endpoint path
            
        Returns:
            Cache key: raba:ratelimit:{identifier}:{endpoint_hash}
        """
        endpoint_hash = cls._hash(endpoint, 8)
        return f"{cls.PREFIX}ratelimit:{identifier}:{endpoint_hash}"
    
    @classmethod
    def rate_limit_ttl(cls) -> int:
        """Get TTL for rate limit windows (1 minute)."""
        return 60


def generate_topic_hash(topic: str) -> str:
    """
    Generate a hash for a topic string.
    
    Used for cache key generation and deduplication.
    
    Args:
        topic: Topic string to hash
        
    Returns:
        16-character hex hash
    """
    return CacheKeys._hash(topic, 16)


def generate_content_hash(content: str, length: int = 16) -> str:
    """
    Generate a hash for any content string.
    
    Args:
        content: Content to hash
        length: Length of resulting hash (default 16)
        
    Returns:
        Hex hash of specified length
    """
    return hashlib.sha256(content.encode()).hexdigest()[:length]
