#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Utility Functions.

This module provides utility functions for AI operations, including
configuration management, error handling, and provider selection.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .models import (
    ModelProvider, ModelUseCase, ModelType, ModelConfiguration,
    DEFAULT_PROVIDER, FALLBACK_PROVIDER, AZURE_DEPLOYMENTS, 
    OPENAI_MODELS, DEFAULT_MODELS, MODEL_DIMENSIONS
)

# Configure logging
logger = logging.getLogger(__name__)


def is_azure_configured() -> bool:
    """Check if Azure OpenAI is properly configured.
    
    Returns:
        bool: True if Azure OpenAI environment variables are set
    """
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY"
    ]
    return all(os.getenv(var) for var in required_vars)


def get_azure_config() -> Dict[str, str]:
    """Get Azure OpenAI configuration from environment variables.
    
    Returns:
        Dict[str, str]: Azure OpenAI configuration
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini")
    # Build Azure OpenAI base_url: endpoint + /openai/deployments/{deployment}/
    base_url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment_name}/" if endpoint else ""
    
    return {
        "endpoint": endpoint,
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        "deployment_name": deployment_name,
        "base_url": base_url,
    }


def get_api_key(provider: ModelProvider = DEFAULT_PROVIDER) -> str:
    """Get API key for the specified provider with Azure-first strategy.
    
    Args:
        provider: AI model provider
        
    Returns:
        str: API key for the provider
    """
    if provider == ModelProvider.AZURE_OPENAI:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            logger.warning("AZURE_OPENAI_API_KEY not found in environment variables")
            # Try fallback to OpenAI
            if is_azure_configured():
                logger.info("Azure endpoint configured but API key missing, trying OpenAI fallback")
            return get_api_key(FALLBACK_PROVIDER)
    elif provider == ModelProvider.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
    elif provider == ModelProvider.GEMINI:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found in environment variables")
    elif provider == ModelProvider.ANTHROPIC:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment variables")
    else:
        logger.error(f"Unknown provider: {provider}")
        api_key = ""
        
    return api_key or ""


def get_provider_with_fallback() -> ModelProvider:
    """Get the best available provider with fallback logic.
    
    Returns:
        ModelProvider: Azure OpenAI if configured, otherwise OpenAI
    """
    if is_azure_configured():
        logger.info("Using Azure OpenAI as primary provider")
        return ModelProvider.AZURE_OPENAI
    else:
        logger.info("Azure OpenAI not configured, falling back to OpenAI")
        return ModelProvider.OPENAI


def get_model_for_use_case(use_case: ModelUseCase, provider: Optional[ModelProvider] = None) -> str:
    """Get the appropriate model/deployment for a specific use case.
    
    Args:
        use_case: The specific use case for the model
        provider: Optional provider override
        
    Returns:
        str: Model name or deployment name
    """
    if provider is None:
        provider = get_provider_with_fallback()
    
    if provider == ModelProvider.AZURE_OPENAI:
        deployment = AZURE_DEPLOYMENTS.get(use_case)
        if deployment:
            logger.debug(f"Using Azure deployment '{deployment}' for use case '{use_case}'")
            return deployment
        else:
            logger.warning(f"No Azure deployment configured for use case '{use_case}', falling back to OpenAI")
            provider = FALLBACK_PROVIDER
    
    if provider == ModelProvider.OPENAI:
        model = OPENAI_MODELS.get(use_case)
        if model:
            logger.debug(f"Using OpenAI model '{model}' for use case '{use_case}'")
            return model
    
    # Final fallback
    logger.error(f"No model configured for use case '{use_case}' and provider '{provider}'")
    return "gpt-5-mini"  # Safe default


def get_client_config(use_case: ModelUseCase, provider: Optional[ModelProvider] = None) -> Tuple[ModelProvider, str, Dict[str, Any]]:
    """Get complete client configuration for a use case.
    
    Args:
        use_case: The specific use case for the model
        provider: Optional provider override
        
    Returns:
        Tuple[ModelProvider, str, Dict[str, Any]]: (provider, model/deployment, client_config)
    """
    if provider is None:
        provider = get_provider_with_fallback()
    
    model = get_model_for_use_case(use_case, provider)
    api_key = get_api_key(provider)
    
    if provider == ModelProvider.AZURE_OPENAI:
        azure_config = get_azure_config()
        # IMPORTANT: Base URL must point to the correct Azure deployment for this use case
        endpoint = azure_config["endpoint"].rstrip("/") if azure_config.get("endpoint") else ""
        # Allow per-use-case deployment overrides via environment variables
        import os
        if use_case == ModelUseCase.EMBEDDING:
            deployment_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", model)
        else:
            deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", model)
        base_url = f"{endpoint}/openai/deployments/{deployment_name}/" if endpoint and deployment_name else ""
        client_config = {
            "api_key": api_key,
            "azure_endpoint": azure_config["endpoint"],
            "api_version": azure_config["api_version"],
            "base_url": base_url,  # Use use-case specific deployment in path
        }
    else:
        client_config = {
            "api_key": api_key,
        }
    
    return provider, model, client_config


def get_model_name(model_type: ModelType, provider: ModelProvider = DEFAULT_PROVIDER) -> str:
    """Get model name for the specified type and provider (legacy function).
    
    Args:
        model_type: Type of model
        provider: AI model provider
        
    Returns:
        str: Model name
    """
    # Map legacy ModelType to new ModelUseCase
    if model_type == ModelType.EMBEDDING:
        return get_model_for_use_case(ModelUseCase.EMBEDDING, provider)
    elif model_type == ModelType.CHAT:
        return get_model_for_use_case(ModelUseCase.CHAT_COMPLETION, provider)
    else:
        return DEFAULT_MODELS.get(model_type, {}).get(provider, "")


def get_embedding_dimension(model_name: str) -> int:
    """Get embedding dimension for the specified model.
    
    Args:
        model_name: Name of the embedding model
        
    Returns:
        int: Embedding dimension
    """
    return MODEL_DIMENSIONS.get(model_name, 1536)  # Default to OpenAI's dimension


def validate_model_configuration(config: ModelConfiguration) -> bool:
    """Validate a model configuration.
    
    Args:
        config: Model configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    if not config.api_key:
        logger.error("API key is required")
        return False
    
    if config.provider == ModelProvider.AZURE_OPENAI and not config.azure_endpoint:
        logger.error("Azure endpoint is required for Azure OpenAI provider")
        return False
    
    if config.max_tokens is not None and config.max_tokens <= 0:
        logger.error("Max tokens must be positive")
        return False
    
    if not (0 <= config.temperature <= 2):
        logger.error("Temperature must be between 0 and 2")
        return False
    
    return True


def get_available_providers() -> List[ModelProvider]:
    """Get list of available providers based on environment configuration.
    
    Returns:
        List[ModelProvider]: List of available providers
    """
    available = []
    
    if is_azure_configured():
        available.append(ModelProvider.AZURE_OPENAI)
    
    if os.getenv("OPENAI_API_KEY"):
        available.append(ModelProvider.OPENAI)
    
    if os.getenv("GOOGLE_API_KEY"):
        available.append(ModelProvider.GEMINI)
    
    if os.getenv("ANTHROPIC_API_KEY"):
        available.append(ModelProvider.ANTHROPIC)
    
    return available


def format_error_message(error: Exception, provider: str, model: str) -> str:
    """Format error message for AI operations.
    
    Args:
        error: The exception that occurred
        provider: The provider that failed
        model: The model that failed
        
    Returns:
        str: Formatted error message
    """
    timestamp = datetime.now().isoformat()
    return f"AI Error [{timestamp}] - Provider: {provider}, Model: {model}, Error: {str(error)}"


def calculate_response_time(start_time: float, end_time: float) -> float:
    """Calculate response time in seconds.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        float: Response time in seconds
    """
    return end_time - start_time


def sanitize_model_input(text: str, max_length: int = 100000) -> str:
    """Sanitize input text for AI models.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Input text truncated to {max_length} characters")
    
    # Remove null bytes and control characters
    text = text.replace('\x00', '')
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')
    
    return text.strip()


def get_model_info(provider: ModelProvider, model_name: str) -> Dict[str, Any]:
    """Get information about a specific model.
    
    Args:
        provider: The model provider
        model_name: The model name
        
    Returns:
        Dict[str, Any]: Model information
    """
    info = {
        "provider": provider.value,
        "model_name": model_name,
        "dimension": get_embedding_dimension(model_name) if "embedding" in model_name.lower() else None,
        "supports_streaming": True,
        "max_tokens": 4096,  # Default, should be overridden per model
    }
    
    # Add provider-specific information
    if provider == ModelProvider.AZURE_OPENAI:
        info["deployment_type"] = "Azure OpenAI"
        info["supports_functions"] = True
    elif provider == ModelProvider.OPENAI:
        info["deployment_type"] = "OpenAI"
        info["supports_functions"] = True
    elif provider == ModelProvider.GEMINI:
        info["deployment_type"] = "Google Gemini"
        info["supports_functions"] = False
    elif provider == ModelProvider.ANTHROPIC:
        info["deployment_type"] = "Anthropic"
        info["supports_functions"] = False
    
    return info
