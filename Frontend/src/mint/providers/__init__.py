"""
Provider registry package for MINT.

This package manages all pluggable external service providers.
"""

# Base classes from registry
from .registry import (
    Provider,
    ProviderConfig,
    ProviderError,
    ProviderNotFoundError,
    ProviderConfigError
)

# LLM provider classes are now in the AI module
# from .llm import (
#     LLMProvider,
#     LLMConfig,
#     OpenAIProvider,
#     GeminiProvider
# )

# Search provider classes
from .search import (
    SearchProvider,
    SearchConfig,
    SearchResult,
    BraveSearchProvider,
    TavilySearchProvider,
    SerperSearchProvider
)

# Vector store provider classes
from .vector import (
    VectorProvider,
    VectorConfig,
    VectorSearchResult,
    PgVectorProvider,
    QdrantVectorProvider
)

# Provider factory
from .factory import (
    get_provider,
    get_fallback_provider
)

__all__ = [
    # Base classes
    "Provider",
    "ProviderConfig",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderConfigError",
    
    # LLM providers are now in the AI module
    # "LLMProvider",
    # "LLMConfig",
    # "OpenAIProvider",
    # "GeminiProvider",
    
    # Search providers
    "SearchProvider",
    "SearchConfig",
    "SearchResult",
    "BraveSearchProvider",
    "TavilySearchProvider",
    "SerperSearchProvider",
    
    # Vector store providers
    "VectorProvider",
    "VectorConfig",
    "VectorSearchResult",
    "PgVectorProvider",
    "QdrantVectorProvider",
    
    # Factory functions
    "get_provider",
    "get_fallback_provider"
]
