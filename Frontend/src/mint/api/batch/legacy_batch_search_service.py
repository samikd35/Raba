#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Search Service for MINT.

This module provides functionality for batch processing of vector searches
to improve performance when multiple queries need to be processed.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .vector_search_service import ChunkSearchResult, VectorSearchOptions, get_vector_search_service
from .cache_service import cached, invalidate_by_tag

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchSearchRequest(BaseModel):
    """Schema for a batch search request."""
    report_id: str
    queries: List[str]
    options: Optional[VectorSearchOptions] = None


class BatchSearchResult(BaseModel):
    """Schema for a batch search result."""
    query_index: int
    query: str
    chunks: List[ChunkSearchResult]


class BatchSearchService:
    """Service for batch processing of vector searches."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the batch search service.
        
        Args:
            api_key: Optional API key for the embedding model
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.vector_search_service = get_vector_search_service(api_key)
        
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
        logger.info(f"Performing batch search for {len(queries)} queries on report {report_id}")
        
        # Set default options if none provided
        if options is None:
            from .vector_search_service import VectorSearchOptions
            options = VectorSearchOptions()
        
        # Optimize batch size based on number of queries
        # For very large batches, split into smaller chunks to avoid timeouts
        MAX_BATCH_SIZE = 20
        if len(queries) > MAX_BATCH_SIZE:
            logger.info(f"Large batch of {len(queries)} queries detected, splitting into smaller batches")
            
            # Split into smaller batches
            all_results = []
            for i in range(0, len(queries), MAX_BATCH_SIZE):
                batch_queries = queries[i:i+MAX_BATCH_SIZE]
                batch_results = await self.batch_search(report_id, batch_queries, options)
                
                # Adjust query indices to match original indices
                for result in batch_results:
                    result.query_index += i
                
                all_results.extend(batch_results)
            
            return all_results
        
        try:
            # Generate embeddings for all queries in a batch
            query_embeddings = await self.vector_search_service.generate_batch_embeddings(queries)
            
            # Check if any embeddings failed
            if not all(query_embeddings):
                logger.error("Some query embeddings failed to generate")
                # Fall back to individual searches for queries with successful embeddings
                results = []
                
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
                return results
            
            # Use the batch_match_report_chunks function if available
            try:
                from .supabase_client import get_supabase_client
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
                # Use a dictionary to group results by query_index for faster processing
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
                    
                    results.append(BatchSearchResult(
                        query_index=i,
                        query=query,
                        chunks=chunks
                    ))
                
                return results
                
            except Exception as e:
                logger.error(f"Error using batch search function: {e}")
                logger.info("Falling back to individual searches")
                
                # Fall back to individual searches with parallel processing
                tasks = []
                
                # Create tasks for all searches using embeddings we already generated
                for i, (query, embedding) in enumerate(zip(queries, query_embeddings)):
                    task = asyncio.create_task(self._search_with_embedding(i, query, report_id, embedding, options))
                    tasks.append(task)
                
                # Wait for all tasks to complete
                completed_results = await asyncio.gather(*tasks)
                
                # Sort results by query index
                results = sorted(completed_results, key=lambda x: x.query_index)
                
                return results
        
        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            # Return empty results
            return [
                BatchSearchResult(
                    query_index=i,
                    query=query,
                    chunks=[]
                )
                for i, query in enumerate(queries)
            ]
    
    async def _search_with_embedding(
        self,
        index: int,
        query: str,
        report_id: str,
        embedding: List[float],
        options: Optional[VectorSearchOptions]
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
            return BatchSearchResult(
                query_index=index,
                query=query,
                chunks=chunks
            )
        except Exception as e:
            logger.error(f"Error in search with embedding: {e}")
            return BatchSearchResult(
                query_index=index,
                query=query,
                chunks=[]
            )
    
    async def _search_with_index(
        self,
        index: int,
        query: str,
        report_id: str,
        options: Optional[VectorSearchOptions]
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
        chunks = await self.vector_search_service.search_chunks(report_id, query, options)
        return BatchSearchResult(
            query_index=index,
            query=query,
            chunks=chunks
        )


# Singleton instance
_batch_search_service = None


def get_batch_search_service(api_key: Optional[str] = None) -> BatchSearchService:
    """Get the singleton instance of the batch search service.
    
    Args:
        api_key: Optional API key for the embedding model
        
    Returns:
        BatchSearchService: The batch search service
    """
    global _batch_search_service
    if _batch_search_service is None:
        _batch_search_service = BatchSearchService(api_key)
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