"""
Provider registry module for MINT.

This module defines abstract base classes and concrete implementations for
all pluggable external service providers (LLMs, search engines, vector stores).
"""

import abc
import os
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypeVar, Type, Generic, Union, cast

from pydantic import BaseModel, Field, ValidationError

# Constants for environment variable names
ENV_LLM_PROVIDER = "MINT_LLM_PROVIDER"
ENV_SEARCH_PROVIDER = "MINT_SEARCH_PROVIDER"
ENV_VECTOR_PROVIDER = "MINT_VECTOR_PROVIDER"

# Provider type definitions
ProviderType = Literal["llm", "search", "vector"]
T = TypeVar('T')  # Generic type for provider results


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    pass


class ProviderNotFoundError(ProviderError):
    """Exception raised when a requested provider is not available."""
    pass


class ProviderConfigError(ProviderError):
    """Exception raised when provider configuration is invalid."""
    pass


class ProviderConfig(BaseModel):
    """Base configuration model for providers."""
    provider_type: ProviderType
    provider_name: str
    api_key_env_var: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    
    class Config:
        extra = "forbid"


class Provider(Generic[T], abc.ABC):
    """Abstract base class for all providers."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self.api_key = self._get_api_key()
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable if specified."""
        if self.config.api_key_env_var:
            return os.environ.get(self.config.api_key_env_var)
        return None
    
    @abc.abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is operational."""
        pass
    
    @abc.abstractmethod
    def fallback_available(self) -> bool:
        """Check if fallback options are available."""
        pass
