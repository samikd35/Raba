#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Models and Data Structures.

This module contains Pydantic models and data structures for AI functionality,
including model configurations, responses, and provider definitions.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Literal, Union
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """Enum for AI model providers."""
    AZURE_OPENAI = "azure_openai"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class ModelType(str, Enum):
    """Enum for AI model types."""
    EMBEDDING = "embedding"
    CHAT = "chat"
    COMPLETION = "completion"


class ModelUseCase(str, Enum):
    """Enum for specific AI model use cases for fine-grained control."""
    REPORT_GENERATION = "report_generation"  # Industry/PESTEL agents - use gpt-4.1
    CHAT_COMPLETION = "chat_completion"      # General chat/completion - use gpt-4.1-mini
    QUERY_GENERATION = "query_generation"    # Query/clarification - use gpt-4.1-mini
    EMBEDDING = "embedding"                  # Text embeddings - use text-embedding-3-small


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""
    provider_type: Literal["llm"] = "llm"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    # Provider configuration
    provider_name: Optional[str] = None
    api_key_env_var: Optional[str] = None
    # Azure OpenAI specific fields
    azure_endpoint: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow extra fields for Azure OpenAI


class LLMResponse(BaseModel):
    """Standardized response from LLM providers."""
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    provider: Optional[str] = None
    response_time: Optional[float] = None
    error: Optional[str] = None


class EmbeddingResponse(BaseModel):
    """Standardized response for embedding operations."""
    embeddings: List[List[float]]
    model: str
    usage: Optional[Dict[str, int]] = None
    provider: Optional[str] = None
    response_time: Optional[float] = None
    error: Optional[str] = None


class ModelConfiguration(BaseModel):
    """Complete model configuration for a specific use case."""
    provider: ModelProvider
    model_name: str
    use_case: ModelUseCase
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    api_key: str
    azure_endpoint: Optional[str] = None
    api_version: Optional[str] = None
    dimension: Optional[int] = None


class ProviderConfig(BaseModel):
    """Base configuration for AI providers."""
    provider_type: str
    api_key: str
    model_name: str
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    
    class Config:
        extra = "allow"


class AzureOpenAIConfig(ProviderConfig):
    """Configuration for Azure OpenAI provider."""
    provider_type: Literal["azure_openai"] = "azure_openai"
    azure_endpoint: str
    api_version: str = "2025-11-18"
    deployment_name: str
    base_url: Optional[str] = None  # For gpt-5-mini pattern


class OpenAIConfig(ProviderConfig):
    """Configuration for OpenAI provider."""
    provider_type: Literal["openai"] = "openai"


class GeminiConfig(ProviderConfig):
    """Configuration for Google Gemini provider."""
    provider_type: Literal["gemini"] = "gemini"


class AnthropicConfig(ProviderConfig):
    """Configuration for Anthropic provider."""
    provider_type: Literal["anthropic"] = "anthropic"


class ModelDeployment(BaseModel):
    """Model deployment configuration."""
    use_case: ModelUseCase
    azure_deployment: str
    openai_model: str
    gemini_model: Optional[str] = None
    anthropic_model: Optional[str] = None


class ModelDimensions(BaseModel):
    """Model dimension specifications."""
    model_name: str
    dimension: int
    provider: ModelProvider


class AIError(BaseModel):
    """AI service error information."""
    error_type: str
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None
    timestamp: Optional[str] = None
    retry_after: Optional[int] = None


class CircuitBreakerState(BaseModel):
    """Circuit breaker state information."""
    is_open: bool
    failure_count: int
    last_failure_time: Optional[float] = None
    next_attempt_time: Optional[float] = None


class RetryConfig(BaseModel):
    """Retry configuration for AI operations."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class FallbackConfig(BaseModel):
    """Fallback configuration for AI operations."""
    enabled: bool = True
    fallback_provider: Optional[ModelProvider] = None
    fallback_model: Optional[str] = None
    custom_fallback: Optional[str] = None


# Model deployment mappings
AZURE_DEPLOYMENTS = {
    ModelUseCase.REPORT_GENERATION: "gpt-5-mini",    # Model router for all LLM tasks
    ModelUseCase.CHAT_COMPLETION: "gpt-5-mini",      # Model router for chat/completion
    ModelUseCase.QUERY_GENERATION: "gpt-5-mini",     # Model router for query generation
    ModelUseCase.EMBEDDING: "text-embedding-3-small",  # text-embedding-3-small
}

OPENAI_MODELS = {
    ModelUseCase.REPORT_GENERATION: "gpt-4.1-2025-04-14",  # GPT-4.1 for report generation
    ModelUseCase.CHAT_COMPLETION: "gpt-4.1-mini",          # GPT-4.1-mini for chat
    ModelUseCase.QUERY_GENERATION: "gpt-4.1-mini",         # GPT-4.1-mini for queries
    ModelUseCase.EMBEDDING: "text-embedding-3-small",      # OpenAI embedding model
}

# Legacy model configurations (for backward compatibility)
DEFAULT_MODELS = {
    ModelType.EMBEDDING: {
        ModelProvider.AZURE_OPENAI: "text-embedding-3-small",
        ModelProvider.OPENAI: "text-embedding-3-small",
        ModelProvider.GEMINI: "gemini-embedding-001"
    },
    ModelType.CHAT: {
        ModelProvider.AZURE_OPENAI: "gpt-5-mini",
        ModelProvider.OPENAI: "gpt-4.1-mini",
        ModelProvider.GEMINI: "gemini-1.5-flash"
    }
}

# Model dimensions
MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "gemini-embedding-001": 768
}

# Default provider priority
DEFAULT_PROVIDER = ModelProvider.AZURE_OPENAI
FALLBACK_PROVIDER = ModelProvider.OPENAI
