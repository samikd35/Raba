#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Embedding Service for MINT.

This module provides functions for generating embeddings for text.
"""

import os
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ...ai.config import (
    ModelProvider, 
    ModelType, 
    ModelUseCase,
    get_api_key, 
    get_model_name,
    get_embedding_dimension,
    get_client_config,
    get_provider_with_fallback
)

# Import AI token monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

# Import embedding cache service
from ...cache.embedding_cache_service import get_embedding_cache_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import shared Azure OpenAI semaphore
from ...system.core.azure_semaphore import azure_openai_semaphore

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
MAX_TEXT_LENGTH = 8192  # characters
MAX_BATCH_SIZE = 10  # texts per batch


class EmbeddingService:
    """Service for generating embeddings with Azure OpenAI support."""
    
    def __init__(self, api_key: Optional[str] = None, provider: Optional[ModelProvider] = None):
        """Initialize the embedding service with Azure OpenAI support.
        
        Args:
            api_key: Optional API key override
            provider: Optional provider override (defaults to Azure OpenAI with OpenAI fallback)
        """
        # Use centralized configuration to get the best provider and model
        self.provider, self.model, self.client_config = get_client_config(
            ModelUseCase.EMBEDDING, 
            provider
        )
        
        # Override API key if provided
        if api_key:
            self.client_config["api_key"] = api_key
        
        # Store API key as attribute for compatibility
        self.api_key = self.client_config["api_key"]
        
        # Initialize the appropriate client
        # For Azure, use deployment-based base_url (per-use-case)
        # Add timeout to prevent indefinite hangs
        if self.provider == ModelProvider.AZURE_OPENAI:
            logger.info(f"Initializing Azure OpenAI embedding service: deployment/model={self.model}")
            import os
            api_version = self.client_config.get("api_version") or os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
            self.client = AsyncOpenAI(
                api_key=self.client_config["api_key"],
                base_url=self.client_config["base_url"],
                timeout=120.0,  # 120 second timeout for all requests
                default_query={"api-version": api_version}
            )
            logger.info(f"Azure embeddings base_url: {self.client_config['base_url']}")
        elif self.provider == ModelProvider.OPENAI:
            logger.info(f"Initializing OpenAI embedding service with model: {self.model}")
            self.client = AsyncOpenAI(
                api_key=self.client_config["api_key"],
                timeout=120.0  # 120 second timeout for all requests
            )
        else:
            raise ValueError(f"Provider {self.provider} not supported for embeddings")
        
        logger.info(f"EmbeddingService initialized with provider: {self.provider}, model/deployment: {self.model}")
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError))
    )
    async def generate_single_embedding(
        self, 
        text: str,
        monitoring_context: Optional[AIUsageContext] = None,
        skip_cache: bool = False
    ) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            monitoring_context: Optional context for AI usage monitoring
            skip_cache: If True, bypass cache and always call API
            
        Returns:
            List[float]: Embedding vector
        """
        if not self.api_key:
            raise ValueError("API key is required for generating embeddings")
        
        # Truncate text if it's too long
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(f"Truncating text of length {len(text)} to {MAX_TEXT_LENGTH} characters")
            text = text[:MAX_TEXT_LENGTH]
        
        # Check cache first (unless skip_cache is True)
        if not skip_cache:
            try:
                embedding_cache = get_embedding_cache_service()
                cached_embedding = await embedding_cache.get_embedding(text, self.model)
                if cached_embedding is not None:
                    logger.debug(f"Embedding cache hit for model {self.model}")
                    return cached_embedding
            except Exception as cache_error:
                logger.warning(f"Error checking embedding cache: {cache_error}")
        
        # Record start time for monitoring
        started_at = datetime.utcnow()
        
        try:
            # Use semaphore to limit concurrent Azure OpenAI requests
            async with azure_openai_semaphore:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    encoding_format="float"
                )
            
            # Record end time for monitoring
            finished_at = datetime.utcnow()
            
            # Extract the embedding vector
            embedding = response.data[0].embedding
            
            # Cache the embedding for future use
            if not skip_cache:
                try:
                    embedding_cache = get_embedding_cache_service()
                    await embedding_cache.set_embedding(text, embedding, self.model)
                    logger.debug(f"Cached embedding for model {self.model}")
                except Exception as cache_error:
                    logger.warning(f"Error caching embedding: {cache_error}")
            
            # Record AI usage in monitoring system (fire-and-forget)
            if monitoring_context:
                try:
                    monitoring_service = get_monitoring_service()
                    
                    # Get token usage from response
                    usage = getattr(response, 'usage', None)
                    embedding_tokens = usage.total_tokens if usage else None
                    
                    # Determine provider name
                    provider_name = "azure_openai" if self.provider == ModelProvider.AZURE_OPENAI else "openai"
                    
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider=provider_name,
                            model_name=self.model,
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="success",
                            embedding_tokens=embedding_tokens,
                            input_chars=len(text)
                        )
                    )
                except Exception as monitor_error:
                    # Never let monitoring errors affect the main operation
                    logger.warning(f"Failed to record AI usage monitoring: {monitor_error}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            
            # Record error in monitoring system (fire-and-forget)
            finished_at = datetime.utcnow()
            if monitoring_context:
                try:
                    monitoring_service = get_monitoring_service()
                    
                    # Classify error type
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "too many requests" in error_msg:
                        error_type = "rate_limit"
                    elif "timeout" in error_msg:
                        error_type = "timeout"
                    else:
                        error_type = "provider_error"
                    
                    provider_name = "azure_openai" if self.provider == ModelProvider.AZURE_OPENAI else "openai"
                    
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider=provider_name,
                            model_name=self.model,
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="error",
                            error_type=error_type,
                            input_chars=len(text)
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record AI usage monitoring error: {monitor_error}")
            
            raise
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str],
        monitoring_context: Optional[AIUsageContext] = None
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to generate embeddings for
            monitoring_context: Optional context for AI usage monitoring
            
        Returns:
            List[Optional[List[float]]]: List of embeddings (None for failed embeddings)
        """
        if not self.api_key:
            raise ValueError("API key is required for generating embeddings")
        
        # Truncate texts if they're too long
        truncated_texts = []
        for text in texts:
            if len(text) > MAX_TEXT_LENGTH:
                logger.warning(f"Truncating text of length {len(text)} to {MAX_TEXT_LENGTH} characters")
                truncated_texts.append(text[:MAX_TEXT_LENGTH])
            else:
                truncated_texts.append(text)
        
        # Record start time for monitoring
        started_at = datetime.utcnow()
        
        try:
            # OpenAI supports batch embedding in a single API call
            # Use semaphore to limit concurrent Azure OpenAI requests
            async with azure_openai_semaphore:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=truncated_texts,
                    encoding_format="float"
                )
            
            # Record end time for monitoring
            finished_at = datetime.utcnow()
            
            # Extract embeddings in the same order as input texts
            embeddings = [data.embedding for data in response.data]
            
            # Record AI usage in monitoring system (fire-and-forget)
            if monitoring_context:
                try:
                    monitoring_service = get_monitoring_service()
                    
                    # Get token usage from response
                    usage = getattr(response, 'usage', None)
                    embedding_tokens = usage.total_tokens if usage else None
                    
                    # Determine provider name
                    provider_name = "azure_openai" if self.provider == ModelProvider.AZURE_OPENAI else "openai"
                    
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider=provider_name,
                            model_name=self.model,
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="success",
                            embedding_tokens=embedding_tokens,
                            input_chars=sum(len(text) for text in truncated_texts)
                        )
                    )
                except Exception as monitor_error:
                    # Never let monitoring errors affect the main operation
                    logger.warning(f"Failed to record AI usage monitoring: {monitor_error}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            
            # Record error in monitoring system (fire-and-forget)
            finished_at = datetime.utcnow()
            if monitoring_context:
                try:
                    monitoring_service = get_monitoring_service()
                    
                    # Classify error type
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "too many requests" in error_msg:
                        error_type = "rate_limit"
                    elif "timeout" in error_msg:
                        error_type = "timeout"
                    else:
                        error_type = "provider_error"
                    
                    provider_name = "azure_openai" if self.provider == ModelProvider.AZURE_OPENAI else "openai"
                    
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider=provider_name,
                            model_name=self.model,
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="error",
                            error_type=error_type,
                            input_chars=sum(len(text) for text in truncated_texts)
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record AI usage monitoring error: {monitor_error}")
            
            # If batch fails, fall back to individual processing
            return await self._fallback_individual_embeddings(truncated_texts, monitoring_context)
    
    async def _fallback_individual_embeddings(
        self, 
        texts: List[str],
        monitoring_context: Optional[AIUsageContext] = None
    ) -> List[Optional[List[float]]]:
        """Fallback method to generate embeddings one by one if batch fails.
        
        Args:
            texts: List of texts to generate embeddings for
            monitoring_context: Optional context for AI usage monitoring
            
        Returns:
            List[Optional[List[float]]]: List of embeddings (None for failed embeddings)
        """
        embeddings = []
        
        for text in texts:
            try:
                embedding = await self.generate_single_embedding(text, monitoring_context)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error generating individual embedding: {e}")
                embeddings.append(None)  # Add None for failed embedding
        
        return embeddings
    
    async def generate_embeddings(
        self, 
        texts: List[str],
        monitoring_context: Optional[AIUsageContext] = None
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for a list of texts with batch processing.
        
        Args:
            texts: List of texts to generate embeddings for
            monitoring_context: Optional context for AI usage monitoring
            
        Returns:
            List[Optional[List[float]]]: List of embeddings (None for failed embeddings)
        """
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        if not self.api_key:
            raise ValueError("API key is required for generating embeddings")
        
        if not texts:
            return []
            
        all_embeddings = [None] * len(texts)  # Pre-allocate with None values
        
        # Process texts in batches to optimize API calls
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i:i+MAX_BATCH_SIZE]
            batch_size = len(batch)
            
            try:
                # Generate embeddings for the batch
                batch_embeddings = await self.generate_embeddings_batch(batch, monitoring_context)
                
                # Add batch results to the full results list
                for j, embedding in enumerate(batch_embeddings):
                    all_embeddings[i+j] = embedding
                
                logger.info(f"Generated embeddings for batch {i//MAX_BATCH_SIZE + 1}/{(len(texts)-1)//MAX_BATCH_SIZE + 1}")
                
            except Exception as e:
                logger.error(f"Error generating embeddings for batch: {e}")
                # Individual embeddings will remain None in all_embeddings
        
        # Log success rate
        success_count = sum(1 for e in all_embeddings if e is not None)
        success_rate = success_count / len(texts) if texts else 0
        logger.info(f"Successfully generated {success_count}/{len(texts)} embeddings ({success_rate:.1%})")
        
        return all_embeddings


# Singleton instance
_embedding_service = None


def get_embedding_service(api_key: Optional[str] = None) -> EmbeddingService:
    """Get the singleton instance of the embedding service with Azure OpenAI support.
    
    Args:
        api_key: Optional API key override
        
    Returns:
        EmbeddingService: The embedding service
    """
    global _embedding_service
    
    # Always create a new service instance to ensure we get the latest configuration
    # This allows for dynamic switching between Azure and OpenAI based on environment
    if _embedding_service is None:
        logger.info("Initializing embedding service with Azure OpenAI support")
        _embedding_service = EmbeddingService(api_key=api_key)
        
    return _embedding_service


async def generate_embeddings(
    texts: List[str], 
    api_key: Optional[str] = None,
    monitoring_context: Optional[AIUsageContext] = None
) -> List[Optional[List[float]]]:
    """Generate embeddings for a list of texts.
    
    Args:
        texts: List of texts to generate embeddings for
        api_key: Optional API key for the embedding model
        monitoring_context: Optional context for AI usage monitoring
        
    Returns:
        List[Optional[List[float]]]: List of embeddings (None for failed embeddings)
    """
    service = get_embedding_service(api_key)
    return await service.generate_embeddings(texts, monitoring_context)
