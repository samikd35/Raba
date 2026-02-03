#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Search Operations.

This module provides batch search functionality for vector searches,
including batch processing of multiple queries for improved performance.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from ..vector_search_service import ChunkSearchResult, VectorSearchOptions, get_vector_search_service
from ..cache_service import cached, invalidate_by_tag
from ..supabase_client import get_supabase_client
from .models import (
    BatchSearchRequest, BatchSearchResult, BatchSearchConfig,
    BatchSearchStatistics, BatchSearchError, BATCH_SEARCH_ERROR_CODES
)

# Configure logging
logger = logging.getLogger(__name__)


class BatchSearchService:
    """Service for batch processing of vector searches."""

    def __init__(self, api_key: Optional[str] = None, config: Optional[BatchSearchConfig] = None):
        """Initialize the batch search service.
        
        Args:
            api_key: Optional API key for the embedding model
            config: Batch search configuration
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.config = config or BatchSearchConfig()
        self.vector_search_service = get_vector_search_service(api_key)
        self.stats = BatchSearchStatistics()
        
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variables."""
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found in environment variables")
        return api_key or ""
    
    @cached(ttl_seconds=300, key_prefix="batch_search", tags=["vector_search", "batch"])
    async def batch_search(
        self,
        report_id: str,
        queries: List[str],
        options: Optional[VectorSearchOptions] = None
    ) -> List[BatchSearchResult]:
        """Perform batch search for multiple queries.
        
        Args:
            report_id: ID of the report
            queries: List of queries to search for
            options: Search options
            
        Returns:
            List[BatchSearchResult]: List of search results for each query
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Performing batch search for {len(queries)} queries on report {report_id}")
        
        # Update statistics
        self.stats.total_searches += 1
        self.stats.total_queries += len(queries)
        
        # Set default options if none provided
        if options is None:
            options = VectorSearchOptions()
        
        # Validate input
        if len(queries) > self.config.max_queries:
            error_msg = f"Query limit exceeded: {len(queries)} > {self.config.max_queries}"
            logger.error(error_msg)
            return self._create_error_results(queries, BATCH_SEARCH_ERROR_CODES["QUERY_LIMIT_EXCEEDED"])
        
        # Optimize batch size based on number of queries
        if len(queries) > self.config.max_batch_size:
            logger.info(f"Large batch of {len(queries)} queries detected, splitting into smaller batches")
            return await self._process_large_batch(report_id, queries, options)
        
        try:
            # Generate embeddings for all queries in a batch
            query_embeddings = await self.vector_search_service.generate_batch_embeddings(queries)
            
            # Check if any embeddings failed
            if not all(query_embeddings):
                logger.error("Some query embeddings failed to generate")
                return await self._fallback_to_individual_searches(report_id, queries, query_embeddings, options)
            
            # Use the batch_match_report_chunks function if available
            try:
                return await self._perform_batch_vector_search(report_id, queries, query_embeddings, options)
                
            except Exception as e:
                logger.error(f"Error using batch search function: {e}")
                logger.info("Falling back to individual searches")
                return await self._fallback_to_individual_searches(report_id, queries, query_embeddings, options)
        
        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            self.stats.failed_searches += 1
            return self._create_error_results(queries, str(e))
        finally:
            # Update execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.stats.avg_execution_time = (
                (self.stats.avg_execution_time * (self.stats.total_searches - 1) + execution_time) / 
                self.stats.total_searches
            )
    
    async def _process_large_batch(
        self,
        report_id: str,
        queries: List[str],
        options: VectorSearchOptions
    ) -> List[BatchSearchResult]:
        """Process a large batch by splitting it into smaller batches.
        
        Args:
            report_id: ID of the report
            queries: List of queries to search for
            options: Search options
            
        Returns:
            List[BatchSearchResult]: Combined results from all batches
        """
        all_results = []
        
        for i in range(0, len(queries), self.config.max_batch_size):
            batch_queries = queries[i:i+self.config.max_batch_size]
            batch_results = await self.batch_search(report_id, batch_queries, options)
            
            # Adjust query indices to match original indices
            for result in batch_results:
                result.query_index += i
            
            all_results.extend(batch_results)
        
        return all_results
    
    async def _perform_batch_vector_search(
        self,
        report_id: str,
        queries: List[str],
        query_embeddings: List[List[float]],
        options: VectorSearchOptions
    ) -> List[BatchSearchResult]:
        """Perform batch vector search using Supabase RPC.
        
        Args:
            report_id: ID of the report
            queries: List of queries
            query_embeddings: Pre-generated embeddings
            options: Search options
            
        Returns:
            List[BatchSearchResult]: Search results
        """
        supabase = get_supabase_client()
        
        # Call the batch search function with optimized parameters
        result = supabase.rpc(
            "batch_match_report_chunks",
            {
                "query_embeddings": query_embeddings,
                "report_id_param": report_id,
                "match_count": options.max_chunks * 2  # Request more results to allow for filtering
            }
        ).execute()
        
        if hasattr(result, "error") and result.error:
            logger.error(f"Error in batch vector search: {result.error}")
            raise Exception(f"Batch search error: {result.error}")
        
        # Process the results with optimized data structure
        batch_results = {}
        
        # Pre-allocate dictionaries for each query index
        for i in range(len(queries)):
            batch_results[i] = []
        
        # Process all results in a single pass
        for item in result.data:
            query_index = item.get("query_index")
            
            # Skip results with similarity below threshold
            if item.get("similarity", 0.0) < options.similarity_threshold:
                continue
            
            # Create a ChunkSearchResult
            chunk_result = ChunkSearchResult(
                id=item.get("id"),
                report_id=item.get("report_id"),
                chunk_index=item.get("chunk_index"),
                content=item.get("content"),
                metadata=item.get("metadata", {}),
                similarity=item.get("similarity", 0.0)
            )
            
            batch_results[query_index].append(chunk_result)
        
        # Create BatchSearchResult objects and limit to max_chunks
        results = []
        for i, query in enumerate(queries):
            chunks = batch_results.get(i, [])
            # Sort by similarity and limit to max_chunks
            chunks.sort(key=lambda x: x.similarity, reverse=True)
            chunks = chunks[:options.max_chunks]
            
            # Convert ChunkSearchResult to dict for serialization
            chunks_dict = [
                {
                    "id": chunk.id,
                    "report_id": chunk.report_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "similarity": chunk.similarity
                }
                for chunk in chunks
            ]
            
            results.append(BatchSearchResult(
                query_index=i,
                query=query,
                chunks=chunks_dict,
                success=True
            ))
        
        self.stats.successful_searches += 1
        return results
    
    async def _fallback_to_individual_searches(
        self,
        report_id: str,
        queries: List[str],
        query_embeddings: List[Optional[List[float]]],
        options: VectorSearchOptions
    ) -> List[BatchSearchResult]:
        """Fall back to individual searches when batch search fails.
        
        Args:
            report_id: ID of the report
            queries: List of queries
            query_embeddings: Pre-generated embeddings (may contain None values)
            options: Search options
            
        Returns:
            List[BatchSearchResult]: Search results
        """
        # Use asyncio.gather for parallel processing
        tasks = []
        for i, (query, embedding) in enumerate(zip(queries, query_embeddings)):
            if embedding:
                task = asyncio.create_task(self._search_with_embedding(i, query, report_id, embedding, options))
            else:
                task = asyncio.create_task(self._search_with_index(i, query, report_id, options))
            tasks.append(task)
        
        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks)
        
        # Sort results by query index
        results = sorted(completed_results, key=lambda x: x.query_index)
        
        # Update statistics
        successful_count = sum(1 for r in results if r.success)
        if successful_count == len(results):
            self.stats.successful_searches += 1
        else:
            self.stats.failed_searches += 1
        
        return results
    
    async def _search_with_embedding(
        self,
        index: int,
        query: str,
        report_id: str,
        embedding: List[float],
        options: VectorSearchOptions
    ) -> BatchSearchResult:
        """Perform search for a single query with pre-generated embedding.
        
        Args:
            index: Index of the query
            query: Query to search for
            report_id: ID of the report
            embedding: Pre-generated embedding
            options: Search options
            
        Returns:
            BatchSearchResult: Search result with query index
        """
        try:
            # Use the vector search service's internal method directly with the embedding
            chunks = await self.vector_search_service._vector_search(report_id, embedding, options)
            
            # Convert ChunkSearchResult to dict for serialization
            chunks_dict = [
                {
                    "id": chunk.id,
                    "report_id": chunk.report_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "similarity": chunk.similarity
                }
                for chunk in chunks
            ]
            
            return BatchSearchResult(
                query_index=index,
                query=query,
                chunks=chunks_dict,
                success=True
            )
        except Exception as e:
            logger.error(f"Error in search with embedding: {e}")
            return BatchSearchResult(
                query_index=index,
                query=query,
                chunks=[],
                success=False,
                error=str(e)
            )
    
    async def _search_with_index(
        self,
        index: int,
        query: str,
        report_id: str,
        options: VectorSearchOptions
    ) -> BatchSearchResult:
        """Perform search for a single query with index.
        
        Args:
            index: Index of the query
            query: Query to search for
            report_id: ID of the report
            options: Search options
            
        Returns:
            BatchSearchResult: Search result with query index
        """
        try:
            chunks = await self.vector_search_service.search_chunks(report_id, query, options)
            
            # Convert ChunkSearchResult to dict for serialization
            chunks_dict = [
                {
                    "id": chunk.id,
                    "report_id": chunk.report_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "similarity": chunk.similarity
                }
                for chunk in chunks
            ]
            
            return BatchSearchResult(
                query_index=index,
                query=query,
                chunks=chunks_dict,
                success=True
            )
        except Exception as e:
            logger.error(f"Error in search with index: {e}")
            return BatchSearchResult(
                query_index=index,
                query=query,
                chunks=[],
                success=False,
                error=str(e)
            )
    
    def _create_error_results(self, queries: List[str], error_message: str) -> List[BatchSearchResult]:
        """Create error results for all queries.
        
        Args:
            queries: List of queries
            error_message: Error message
            
        Returns:
            List[BatchSearchResult]: Error results
        """
        return [
            BatchSearchResult(
                query_index=i,
                query=query,
                chunks=[],
                success=False,
                error=error_message
            )
            for i, query in enumerate(queries)
        ]
    
    def get_statistics(self) -> BatchSearchStatistics:
        """Get batch search statistics.
        
        Returns:
            BatchSearchStatistics: Current statistics
        """
        # Update averages
        if self.stats.total_searches > 0:
            self.stats.avg_queries_per_search = self.stats.total_queries / self.stats.total_searches
        
        self.stats.last_updated = datetime.now(timezone.utc)
        return self.stats
    
    def reset_statistics(self) -> None:
        """Reset batch search statistics."""
        self.stats = BatchSearchStatistics()
        logger.info("Batch search statistics reset")


# Singleton instance
_batch_search_service = None


def get_batch_search_service(api_key: Optional[str] = None, config: Optional[BatchSearchConfig] = None) -> BatchSearchService:
    """Get the singleton instance of the batch search service.
    
    Args:
        api_key: Optional API key for the embedding model
        config: Optional batch search configuration
        
    Returns:
        BatchSearchService: The batch search service
    """
    global _batch_search_service
    if _batch_search_service is None:
        _batch_search_service = BatchSearchService(api_key, config)
    return _batch_search_service


async def batch_search(
    report_id: str,
    queries: List[str],
    options: Optional[VectorSearchOptions] = None
) -> List[BatchSearchResult]:
    """Perform batch search for multiple queries.
    
    Args:
        report_id: ID of the report
        queries: List of queries to search for
        options: Search options
        
    Returns:
        List[BatchSearchResult]: List of search results for each query
    """
    service = get_batch_search_service()
    return await service.batch_search(report_id, queries, options)


