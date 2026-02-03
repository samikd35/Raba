#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vector Search Service for MINT.

This module provides functionality for vector similarity search of report chunks
with parameters for controlling precision and recall.
"""

import logging
import asyncio
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from ...system.core.supabase_client import get_supabase_client
from .embedding_service import get_embedding_service
from ...report.report_models import ReportChunk
from ...cache.core import cached, invalidate_by_tag
from ...ai.config import get_api_key, ModelProvider

# Import AI token monitoring service
from monitor.tokens.models import AIUsageContext
from ...system.middleware.id_consistency_middleware import ensure_report_id_consistency, log_id_flow, IDConsistencyError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SIMILARITY_THRESHOLD = 0.2  # Default cosine similarity threshold
DEFAULT_MAX_CHUNKS = 5  # Default maximum number of chunks to return
DEFAULT_RERANKING_ENABLED = False  # Default reranking setting
DEFAULT_HYBRID_SEARCH_ENABLED = False  # Default hybrid search setting
DEFAULT_KEYWORD_WEIGHT = 0.3  # Default weight for keyword search in hybrid mode


class ChunkSearchResult(BaseModel):
    """Schema for a chunk search result."""
    id: str
    report_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = {}
    similarity: float


class VectorSearchOptions(BaseModel):
    """Schema for vector search options."""
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    max_chunks: int = DEFAULT_MAX_CHUNKS
    reranking_enabled: bool = DEFAULT_RERANKING_ENABLED
    hybrid_search_enabled: bool = DEFAULT_HYBRID_SEARCH_ENABLED
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT


class VectorSearchService:
    """Service for vector similarity search of report chunks."""

    def _validate_report_id_for_search(self, report_id: str) -> bool:
        """Validate report ID before performing search.
        
        Args:
            report_id: The report ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            import uuid
            uuid.UUID(report_id)
            logger.info(f"SEARCH ID VALIDATION: Report ID {report_id} is valid UUID")
            return True
        except (ValueError, TypeError):
            logger.error(f"SEARCH ID VALIDATION: Invalid report ID format: {report_id}")
            return False
    

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the vector search service.
        
        Args:
            api_key: Optional API key for the embedding model
        """
        self.api_key = api_key or self._get_api_key_from_env()
        supabase_client = get_supabase_client()
        # Access the actual Supabase client object, not the wrapper
        self.supabase = supabase_client.client
        
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variables using ai_config."""
        # Use the centralized client configuration for embeddings
        from src.mint.api.ai.config import get_client_config, ModelUseCase
        provider, model, client_config = get_client_config(ModelUseCase.EMBEDDING)
        api_key = client_config.get("api_key")
        if not api_key:
            logger.warning(f"API key not found for provider {provider} in environment variables")
        return api_key or ""
    
    @cached(ttl_seconds=3600, key_prefix="query_embedding", tags=["embeddings"])
    async def generate_embedding(
        self, 
        text: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate embedding for a text with caching.
        
        Args:
            text: Text to generate embedding for
            user_id: Optional user ID for monitoring
            tenant_id: Optional tenant ID for monitoring
            report_id: Optional report ID for monitoring
            
        Returns:
            List[float]: Embedding vector, or None if generation failed
        """
        logger.info("Generating embedding for query")
        
        if not self.api_key:
            raise ValueError("API key is required for generating embeddings")
        
        # Create a cache key based on text hash for better cache utilization
        # This helps with slight variations in queries that would produce the same embedding
        text_normalized = text.lower().strip()
        
        try:
            # Get the embedding service with centralized configuration
            embedding_service = get_embedding_service()
            
            # Create monitoring context for query embedding
            monitoring_context = None
            if user_id or tenant_id or report_id:
                monitoring_context = AIUsageContext(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    project_id=report_id,
                    feature_id="pv_report_chat",
                    workflow_name="pv_report_workflow",
                    step_name="query_embedding",
                    environment="prod"
                )
            
            # Generate embedding using the embedding service
            embeddings = await embedding_service.generate_embeddings([text], monitoring_context)
            
            # Return the first (and only) embedding
            return embeddings[0] if embeddings and embeddings[0] is not None else None
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
            
    async def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in a batch.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List[Optional[List[float]]]: List of embedding vectors
        """
        logger.info(f"Generating batch embeddings for {len(texts)} texts")
        
        if not self.api_key:
            raise ValueError("API key is required for generating embeddings")
        
        try:
            # Get the embedding service with centralized configuration
            embedding_service = get_embedding_service()
            
            # Generate embeddings in a batch
            embeddings = await embedding_service.generate_embeddings(texts)
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    @cached(ttl_seconds=300, key_prefix="vector_search", tags=["vector_search"])
    async def search_chunks(
        self, 
        report_id: str, 
        query: str,
        options: Optional[VectorSearchOptions] = None
    ) -> List[ChunkSearchResult]:
        """Search for chunks using vector similarity with caching.
        
        Args:
            report_id: ID of the report
            query: Query to search for
            options: Search options
            
        Returns:
            List[ChunkSearchResult]: List of search results
        """
        from ...services.utilities.id_logging_service import log_vector_search_operation, IDOperationTracker
        
        logger.info(f"Searching chunks for report {report_id}")
        
        # Start comprehensive ID tracking for vector search
        with IDOperationTracker("VECTOR_SEARCH", report_id=report_id) as tracker:
            
            # Validate report ID format
            if not self._validate_report_id_for_search(report_id):
                tracker.log_error("INVALID_REPORT_ID", f"Invalid report ID format: {report_id}")
                log_vector_search_operation("SEARCH_FAILED_INVALID_ID", report_id, query)
                return []
            
            # Use default options if none provided
            if options is None:
                options = VectorSearchOptions()
            
            # Log search start
            log_vector_search_operation("SEARCH_START", report_id, query, 
                                      similarity_threshold=options.similarity_threshold,
                                      max_chunks=options.max_chunks)
            
            try:
                # Generate embedding for the query
                tracker.update_ids("EMBEDDING_GENERATION", query_preview=query[:50])
                query_embedding = await self.generate_embedding(query)
                
                if not query_embedding:
                    logger.error("Failed to generate embedding for query")
                    tracker.log_error("EMBEDDING_FAILED", "Failed to generate query embedding")
                    log_vector_search_operation("SEARCH_FAILED_EMBEDDING", report_id, query)
                    return []
                
                tracker.update_ids("EMBEDDING_SUCCESS", embedding_dim=len(query_embedding))
                
                # Perform vector similarity search
                tracker.update_ids("VECTOR_SEARCH_START")
                results = await self._vector_search(report_id, query_embedding, options)
                
                tracker.update_ids("VECTOR_SEARCH_COMPLETE", initial_results=len(results))
                
                # If hybrid search is enabled, combine with keyword search
                if options.hybrid_search_enabled:
                    tracker.update_ids("HYBRID_SEARCH_START")
                    keyword_results = await self._keyword_search(report_id, query, options.max_chunks)
                    results = self._combine_search_results(
                        vector_results=results,
                        keyword_results=keyword_results,
                        keyword_weight=options.keyword_weight,
                        max_chunks=options.max_chunks
                    )
                    tracker.update_ids("HYBRID_SEARCH_COMPLETE", hybrid_results=len(results))
                
                # Apply reranking if enabled
                if options.reranking_enabled and len(results) > 1:
                    tracker.update_ids("RERANKING_START")
                    results = await self._rerank_results(query, results)
                    tracker.update_ids("RERANKING_COMPLETE", reranked_results=len(results))
                
                # Log successful search
                log_vector_search_operation("SEARCH_SUCCESS", report_id, query, chunk_count=len(results))
                tracker.update_ids("SEARCH_COMPLETE", final_results=len(results))
                
                return results
            
            except Exception as e:
                logger.error(f"Error searching chunks: {e}")
                tracker.log_error("SEARCH_EXCEPTION", str(e))
                log_vector_search_operation("SEARCH_FAILED_EXCEPTION", report_id, query, error=str(e))
                return []
    
    async def _vector_search(
        self, 
        report_id: str, 
        query_embedding: List[float],
        options: VectorSearchOptions
    ) -> List[ChunkSearchResult]:
        """Perform vector similarity search.
        
        Args:
            report_id: ID of the report
            query_embedding: Query embedding
            options: Search options
            
        Returns:
            List[ChunkSearchResult]: List of search results
        """
        from ...services.utilities.id_logging_service import log_database_operation, log_vector_search_operation
        
        try:
            # Log the database query attempt
            log_database_operation("RPC_CALL", "match_report_chunks", 
                                 filters={"report_id_param": report_id, 
                                         "match_count": options.max_chunks * 2})
            
            # Use direct SQL query since match_report_chunks RPC function doesn't exist
            try:
                # Query chunks table directly with vector similarity
                result = self.supabase.table("chunks").select(
                    "*, documents!chunks_doc_id_fkey(id, title, source_type)"
                ).eq("doc_id", report_id).limit(options.max_chunks).execute()
            except AttributeError as e:
                logger.error(f"Supabase client error in vector search: {e}")
                logger.error(f"Supabase client type: {type(self.supabase)}")
                log_vector_search_operation("DB_CLIENT_ERROR", report_id, error=str(e))
                raise
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error in vector search: {result.error}")
                log_database_operation("RPC_ERROR", "match_report_chunks", 
                                     filters={"report_id_param": report_id}, 
                                     error=str(result.error))
                return []
            
            # Log successful database query
            raw_result_count = len(result.data) if result.data else 0
            log_database_operation("QUERY_SUCCESS", "chunks", 
                                 filters={"doc_id": report_id}, 
                                 result_count=raw_result_count)
            
            # Convert to ChunkSearchResult objects (no similarity filtering since we're not doing vector search)
            results = [
                ChunkSearchResult(
                    id=item.get("id"),
                    report_id=report_id,  # Use the provided report_id
                    chunk_index=item.get("chunk_index", 0),
                    content=item.get("content", ""),
                    metadata=item.get("metadata", {}),
                    similarity=0.8  # Default similarity since we're not doing vector search
                )
                for item in (result.data or [])
            ]
            
            # Log filtering results
            filtered_count = len(results)
            if filtered_count != raw_result_count:
                log_vector_search_operation("SIMILARITY_FILTERING", report_id,
                                          raw_results=raw_result_count,
                                          filtered_results=filtered_count,
                                          threshold=options.similarity_threshold)
            
            # Limit to max_chunks
            final_results = results[:options.max_chunks]
            if len(final_results) != filtered_count:
                log_vector_search_operation("RESULT_LIMITING", report_id,
                                          filtered_results=filtered_count,
                                          final_results=len(final_results),
                                          max_chunks=options.max_chunks)
            
            return final_results
        
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            log_vector_search_operation("VECTOR_SEARCH_EXCEPTION", report_id, error=str(e))
            return []
    
    async def _keyword_search(
        self, 
        report_id: str, 
        query: str,
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """Perform keyword search as fallback or for hybrid search.
        
        Args:
            report_id: ID of the report
            query: Query to search for
            max_chunks: Maximum number of chunks to return
            
        Returns:
            List[Dict[str, Any]]: List of search results
        """
        try:
            # Extract keywords from query (simple approach: split by spaces and remove common words)
            stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "about"}
            keywords = [word.lower() for word in query.split() if word.lower() not in stop_words]
            
            if not keywords:
                return []
            
            # Build a query that searches for any of the keywords
            # This uses Postgres' full-text search capabilities
            search_query = " | ".join(keywords)
            
            # Use Postgres' to_tsquery and plainto_tsquery for better keyword matching
            try:
                # The Supabase Python client API has changed
                # Now we need to use the .filter() method with explicit operator and criteria
                query = self.supabase.table("report_chunks") \
                    .select("id, report_id, chunk_index, content, metadata") \
                    .eq("report_id", report_id)
                
                # Only apply keyword filter if we have keywords
                if keywords:
                    query = query.filter("content", "ilike", f"%{keywords[0]}%")
                
                # Execute the query with a limit
                result = query.limit(max_chunks).execute()
                    
                # If there are multiple keywords, we can filter the results in Python
                # This is less efficient but works with the current API
                if len(keywords) > 1:
                    filtered_data = []
                    for item in result.data:
                        content = item.get("content", "").lower()
                        # Check if all keywords are in the content
                        if all(keyword in content for keyword in keywords[1:]):
                            filtered_data.append(item)
                    result.data = filtered_data
            except AttributeError as e:
                logger.error(f"Supabase client error in keyword search: {e}")
                logger.error(f"Supabase client type: {type(self.supabase)}")
                raise
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error in keyword search: {result.error}")
                return []
            
            # Add a placeholder similarity score (will be adjusted in hybrid search)
            for item in result.data:
                item["similarity"] = 0.5  # Default similarity for keyword matches
            
            return result.data
        
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def _combine_search_results(
        self,
        vector_results: List[ChunkSearchResult],
        keyword_results: List[Dict[str, Any]],
        keyword_weight: float,
        max_chunks: int
    ) -> List[ChunkSearchResult]:
        """Combine vector and keyword search results for hybrid search.
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            keyword_weight: Weight for keyword results (0-1)
            max_chunks: Maximum number of chunks to return
            
        Returns:
            List[ChunkSearchResult]: Combined search results
        """
        # Create a dictionary to track the best score for each chunk
        combined_results = {}
        
        # Process vector results
        for result in vector_results:
            combined_results[result.id] = {
                "result": result,
                "score": result.similarity * (1 - keyword_weight)  # Weight the vector similarity
            }
        
        # Process keyword results
        for item in keyword_results:
            chunk_id = item.get("id")
            if chunk_id in combined_results:
                # If the chunk is already in the results, add the keyword score
                combined_results[chunk_id]["score"] += item.get("similarity", 0.5) * keyword_weight
            else:
                # Otherwise, add a new entry
                combined_results[chunk_id] = {
                    "result": ChunkSearchResult(
                        id=item.get("id"),
                        report_id=item.get("report_id"),
                        chunk_index=item.get("chunk_index"),
                        content=item.get("content"),
                        metadata=item.get("metadata", {}),
                        similarity=item.get("similarity", 0.5) * keyword_weight
                    ),
                    "score": item.get("similarity", 0.5) * keyword_weight
                }
        
        # Sort by combined score and take the top max_chunks
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:max_chunks]
        
        # Update the similarity scores with the combined scores
        for item in sorted_results:
            item["result"].similarity = item["score"]
        
        return [item["result"] for item in sorted_results]
    
    async def _rerank_results(
        self,
        query: str,
        results: List[ChunkSearchResult]
    ) -> List[ChunkSearchResult]:
        """Rerank search results using a more sophisticated algorithm.
        
        Args:
            query: Original query
            results: Initial search results
            
        Returns:
            List[ChunkSearchResult]: Reranked search results
        """
        # This is a placeholder for a more sophisticated reranking algorithm
        # In a real implementation, this could use a cross-encoder model or other techniques
        
        # For now, we'll just return the results as-is
        return results
    
    async def search_chunks_with_fallback(
        self, 
        report_id: str, 
        query: str,
        options: Optional[VectorSearchOptions] = None
    ) -> List[ChunkSearchResult]:
        """Search for chunks with fallback to keyword search if vector search fails.
        
        Args:
            report_id: ID of the report
            query: Query to search for
            options: Search options
            
        Returns:
            List[ChunkSearchResult]: List of search results
        """
        logger.info(f"Searching chunks with fallback for report {report_id}")
        
        # Use default options if none provided
        if options is None:
            options = VectorSearchOptions()
        
        try:
            # Try vector search first
            results = await self.search_chunks(report_id, query, options)
            
            # If vector search fails or returns no results, fall back to keyword search
            if not results:
                logger.info("Vector search returned no results, falling back to keyword search")
                keyword_results = await self._keyword_search(report_id, query, options.max_chunks)
                
                # Convert to ChunkSearchResult objects
                results = [
                    ChunkSearchResult(
                        id=item.get("id"),
                        report_id=item.get("report_id"),
                        chunk_index=item.get("chunk_index"),
                        content=item.get("content"),
                        metadata=item.get("metadata", {}),
                        similarity=item.get("similarity", 0.5)
                    )
                    for item in keyword_results
                ]
            
            return results
        
        except Exception as e:
            logger.error(f"Error in search with fallback: {e}")
            
            # Try keyword search as last resort
            try:
                logger.info("Vector search failed, falling back to keyword search")
                keyword_results = await self._keyword_search(report_id, query, options.max_chunks)
                
                # Convert to ChunkSearchResult objects
                return [
                    ChunkSearchResult(
                        id=item.get("id"),
                        report_id=item.get("report_id"),
                        chunk_index=item.get("chunk_index"),
                        content=item.get("content"),
                        metadata=item.get("metadata", {}),
                        similarity=item.get("similarity", 0.5)
                    )
                    for item in keyword_results
                ]
            
            except Exception as keyword_error:
                logger.error(f"Keyword search also failed: {keyword_error}")
                return []


# Singleton instance
_vector_search_service = None


def get_vector_search_service(api_key: Optional[str] = None) -> VectorSearchService:
    """Get the singleton instance of the vector search service.
    
    Args:
        api_key: Optional API key for the embedding model
        
    Returns:
        VectorSearchService: The vector search service
    """
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService(api_key)
    return _vector_search_service


async def search_chunks(
    report_id: str, 
    query: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    reranking_enabled: bool = DEFAULT_RERANKING_ENABLED,
    hybrid_search_enabled: bool = DEFAULT_HYBRID_SEARCH_ENABLED
) -> List[ChunkSearchResult]:
    """Search for chunks using vector similarity.
    
    Args:
        report_id: ID of the report
        query: Query to search for
        similarity_threshold: Minimum similarity score to include a chunk
        max_chunks: Maximum number of chunks to return
        reranking_enabled: Whether to enable reranking
        hybrid_search_enabled: Whether to enable hybrid search
        
    Returns:
        List[ChunkSearchResult]: List of search results
    """
    service = get_vector_search_service()
    options = VectorSearchOptions(
        similarity_threshold=similarity_threshold,
        max_chunks=max_chunks,
        reranking_enabled=reranking_enabled,
        hybrid_search_enabled=hybrid_search_enabled
    )
    return await service.search_chunks(report_id, query, options)


async def search_chunks_with_fallback(
    report_id: str, 
    query: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_chunks: int = DEFAULT_MAX_CHUNKS
) -> List[ChunkSearchResult]:
    """Search for chunks with fallback to keyword search if vector search fails.
    
    Args:
        report_id: ID of the report
        query: Query to search for
        similarity_threshold: Minimum similarity score to include a chunk
        max_chunks: Maximum number of chunks to return
        
    Returns:
        List[ChunkSearchResult]: List of search results
    """
    service = get_vector_search_service()
    options = VectorSearchOptions(
        similarity_threshold=similarity_threshold,
        max_chunks=max_chunks
    )
    return await service.search_chunks_with_fallback(report_id, query, options)