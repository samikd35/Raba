#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Model Configuration for MINT.

This module provides centralized configuration for AI models used in the application.
Supports Azure OpenAI as primary provider with OpenAI as fallback.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple

from .models import (
    ModelProvider, ModelUseCase, ModelType, DEFAULT_PROVIDER, FALLBACK_PROVIDER,
    AZURE_DEPLOYMENTS, OPENAI_MODELS, DEFAULT_MODELS, MODEL_DIMENSIONS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Re-export functions from utils for backward compatibility
from .utils import (
    is_azure_configured,
    get_azure_config,
    get_api_key,
    get_provider_with_fallback,
    get_model_for_use_case,
    get_client_config,
    get_model_name,
    get_embedding_dimension
)
