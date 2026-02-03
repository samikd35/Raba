"""
Provider factory module for MINT.

This module implements the get_provider factory function that allows one-line swapping
between different provider implementations based on environment variables or config.
"""

import os
import importlib
import logging
from typing import Dict, Literal, Optional, Type, Any, Union, cast

from .registry import (
    Provider, 
    ProviderConfig, 
    ProviderError,
    ProviderNotFoundError, 
    ENV_LLM_PROVIDER, 
    ENV_SEARCH_PROVIDER, 
    ENV_VECTOR_PROVIDER
)

# Import from modules
# LLM providers are now in the AI module
# from .llm import LLMProvider, OpenAIProvider, GeminiProvider
from .search import SearchProvider, BraveSearchProvider, TavilySearchProvider, SerperSearchProvider
from .vector import VectorProvider, PgVectorProvider, QdrantVectorProvider

# Configure logging
logger = logging.getLogger(__name__)

# Default provider names per type
DEFAULT_PROVIDERS = {
    "llm": "openai",      # Default LLM provider
    "search": "tavily",   # Default search provider
    "vector": "pgvector"  # Default vector store provider
}

# Provider registry
PROVIDER_REGISTRY = {
    # LLM providers are now in the AI module
    # "llm": {
    #     "openai": OpenAIProvider,
    #     "gemini": GeminiProvider,
    # },
    "search": {
        "brave": BraveSearchProvider,
        "tavily": TavilySearchProvider,
        "serper": SerperSearchProvider,
    },
    "vector": {
        "pgvector": PgVectorProvider,
        "qdrant": QdrantVectorProvider,
    }
}


def get_provider_env_var(provider_type: Literal["llm", "search", "vector"]) -> str:
    """Get the environment variable name for the specified provider type."""
    if provider_type == "llm":
        return ENV_LLM_PROVIDER
    elif provider_type == "search":
        return ENV_SEARCH_PROVIDER
    elif provider_type == "vector":
        return ENV_VECTOR_PROVIDER
    else:
        raise ValueError(f"Invalid provider type: {provider_type}")


def get_provider(
    provider_type: Literal["llm", "search", "vector"],
    provider_name: Optional[str] = None,
    config: Optional[ProviderConfig] = None
) -> Provider:
    """
    Factory function to get the appropriate provider based on type and name.
    
    Args:
        provider_type: Type of provider ("llm", "search", or "vector")
        provider_name: Name of the specific provider implementation
                      If not provided, checks environment variable or uses default
        config: Optional configuration for the provider
                If not provided, default config will be used
    
    Returns:
        Provider implementation instance
    
    Raises:
        ProviderNotFoundError: If the specified provider is not found
        ProviderError: If there's an error initializing the provider
    """
    # If provider_name is not specified, check environment variable
    if not provider_name:
        env_var = get_provider_env_var(provider_type)
        provider_name = os.environ.get(env_var)
        
        # If not set in environment, use default
        if not provider_name:
            provider_name = DEFAULT_PROVIDERS.get(provider_type)
            logger.info(
                f"No {provider_type} provider specified. Using default: {provider_name}"
            )
    
    # Get provider class from registry
    if provider_type not in PROVIDER_REGISTRY:
        raise ProviderNotFoundError(f"Provider type not supported: {provider_type}")
    
    provider_classes = PROVIDER_REGISTRY[provider_type]
    if provider_name not in provider_classes:
        raise ProviderNotFoundError(
            f"Provider '{provider_name}' not found for type '{provider_type}'. "
            f"Available options: {', '.join(provider_classes.keys())}"
        )
    
    provider_class = provider_classes[provider_name]
    
    try:
        # Initialize provider with config or default config
        provider = provider_class(config)
        
        # Check if provider is operational
        if not provider.health_check():
            logger.warning(
                f"{provider_name} provider not operational. Check API keys and connectivity."
            )
        
        return provider
    except Exception as e:
        raise ProviderError(f"Failed to initialize {provider_name} provider: {str(e)}")


def get_fallback_provider(
    provider_type: Literal["llm", "search", "vector"],
    primary_provider_name: str
) -> Optional[Provider]:
    """
    Get a fallback provider different from the primary provider.
    
    Args:
        provider_type: Type of provider
        primary_provider_name: Name of the primary provider to avoid
    
    Returns:
        Fallback provider or None if no viable fallback is available
    """
    if provider_type not in PROVIDER_REGISTRY:
        return None
    
    provider_classes = PROVIDER_REGISTRY[provider_type]
    
    # Try each provider that's not the primary one
    for name, provider_class in provider_classes.items():
        if name != primary_provider_name:
            try:
                provider = provider_class()
                if provider.health_check():
                    logger.info(f"Using {name} as fallback for {primary_provider_name}")
                    return provider
            except Exception:
                continue
    
    return None
