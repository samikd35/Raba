#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Module for MINT.

This module provides a complete solution for AI functionality in the MINT system,
including model configuration, provider management, and client services.

Module Structure:
- models: Pydantic models and data structures
- config: AI configuration and settings
- providers: LLM provider implementations
- client: AI client services
- utils: Utility functions and helpers
"""

from .models import (
    # Enums
    ModelProvider, ModelType, ModelUseCase,
    
    # Core Models
    LLMConfig, LLMResponse, EmbeddingResponse, ModelConfiguration,
    ProviderConfig, AzureOpenAIConfig, OpenAIConfig, GeminiConfig, AnthropicConfig,
    ModelDeployment, ModelDimensions, AIError, CircuitBreakerState,
    RetryConfig, FallbackConfig,
    
    # Constants
    AZURE_DEPLOYMENTS, OPENAI_MODELS, DEFAULT_MODELS, MODEL_DIMENSIONS,
    DEFAULT_PROVIDER, FALLBACK_PROVIDER
)
from .config import (
    # Configuration functions
    is_azure_configured, get_azure_config, get_api_key,
    get_provider_with_fallback, get_model_for_use_case, get_client_config,
    get_model_name, get_embedding_dimension
)
from .providers import (
    # Provider classes
    LLMProvider, OpenAIProvider, GeminiProvider
)
from .client import LLMClientService
from .utils import (
    # Utility functions
    validate_model_configuration, get_available_providers,
    format_error_message, calculate_response_time, sanitize_model_input,
    get_model_info
)

__all__ = [
    # Enums
    "ModelProvider",
    "ModelType", 
    "ModelUseCase",
    
    # Core Models
    "LLMConfig",
    "LLMResponse",
    "EmbeddingResponse",
    "ModelConfiguration",
    "ProviderConfig",
    "AzureOpenAIConfig",
    "OpenAIConfig",
    "GeminiConfig",
    "AnthropicConfig",
    "ModelDeployment",
    "ModelDimensions",
    "AIError",
    "CircuitBreakerState",
    "RetryConfig",
    "FallbackConfig",
    
    # Constants
    "AZURE_DEPLOYMENTS",
    "OPENAI_MODELS",
    "DEFAULT_MODELS",
    "MODEL_DIMENSIONS",
    "DEFAULT_PROVIDER",
    "FALLBACK_PROVIDER",
    
    # Configuration Functions
    "is_azure_configured",
    "get_azure_config",
    "get_api_key",
    "get_provider_with_fallback",
    "get_model_for_use_case",
    "get_client_config",
    "get_model_name",
    "get_embedding_dimension",
    
    # Provider Classes
    "LLMProvider",
    "OpenAIProvider",
    "AzureOpenAIProvider",
    "GeminiProvider",
    "AnthropicProvider",
    "LLMProviderRegistry",
    
    # Client Services
    "LLMClientService",
    
    # Utility Functions
    "validate_model_configuration",
    "get_available_providers",
    "format_error_message",
    "calculate_response_time",
    "sanitize_model_input",
    "get_model_info"
]
