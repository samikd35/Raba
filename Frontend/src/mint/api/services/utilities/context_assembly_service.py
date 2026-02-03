#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Context Assembly Service for MINT.

This module provides functionality to assemble retrieved chunks into LLM context
with proper formatting, ranking, and selection.
"""

import logging
import re
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .vector_search_service import ChunkSearchResult
from .cache_service import cached, invalidate_by_tag

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_CONTEXT_LENGTH = 8000  # Maximum context length in characters
DEFAULT_INCLUDE_METADATA = True  # Whether to include metadata in context
DEFAULT_FORMAT_TYPE = "markdown"  # Default format type (markdown or text)


class ContextAssemblyOptions(BaseModel):
    """Schema for context assembly options."""
    max_context_length: int = DEFAULT_MAX_CONTEXT_LENGTH
    include_metadata: bool = DEFAULT_INCLUDE_METADATA
    format_type: str = DEFAULT_FORMAT_TYPE  # 'markdown' or 'text'
    include_citations: bool = True
    deduplicate_content: bool = True
    prioritize_by_similarity: bool = True


class AssembledContext(BaseModel):
    """Schema for assembled context."""
    context: str
    chunks: List[ChunkSearchResult]
    total_chunks: int
    included_chunks: int
    context_length: int
    truncated: bool = False


class ContextAssemblyService:
    """Service for assembling retrieved chunks into LLM context."""

    @cached(ttl_seconds=300, key_prefix="context_assembly", tags=["context_assembly"])
    def assemble_context(
        self,
        chunks: List[ChunkSearchResult],
        options: Optional[ContextAssemblyOptions] = None
    ) -> AssembledContext:
        """Assemble retrieved chunks into LLM context with caching.
        
        Args:
            chunks: List of chunks to assemble
            options: Assembly options
            
        Returns:
            AssembledContext: Assembled context
        """
        logger.info(f"Assembling context from {len(chunks)} chunks")
        
        # Use default options if none provided
        if options is None:
            options = ContextAssemblyOptions()
        
        try:
            # Step 1: Rank and select chunks
            selected_chunks = self._rank_and_select_chunks(chunks, options)
            
            # Step 2: Format chunks into context
            context, truncated = self._format_chunks(selected_chunks, options)
            
            # Return the assembled context
            return AssembledContext(
                context=context,
                chunks=selected_chunks,
                total_chunks=len(chunks),
                included_chunks=len(selected_chunks),
                context_length=len(context),
                truncated=truncated
            )
        
        except Exception as e:
            logger.error(f"Error assembling context: {e}")
            # Return a minimal context with error information
            return AssembledContext(
                context=f"Error assembling context: {str(e)}",
                chunks=[],
                total_chunks=len(chunks),
                included_chunks=0,
                context_length=0,
                truncated=False
            )
    
    def _rank_and_select_chunks(
        self,
        chunks: List[ChunkSearchResult],
        options: ContextAssemblyOptions
    ) -> List[ChunkSearchResult]:
        """Rank and select chunks based on relevance and other criteria.
        
        Args:
            chunks: List of chunks to rank and select
            options: Assembly options
            
        Returns:
            List[ChunkSearchResult]: Selected chunks
        """
        # Start with all chunks
        selected_chunks = list(chunks)
        
        # Sort by similarity if enabled
        if options.prioritize_by_similarity:
            selected_chunks.sort(key=lambda x: x.similarity, reverse=True)
        
        # Deduplicate content if enabled
        if options.deduplicate_content:
            selected_chunks = self._deduplicate_chunks(selected_chunks)
        
        # Ensure we don't exceed the maximum context length
        selected_chunks = self._limit_context_length(selected_chunks, options.max_context_length)
        
        # Sort by chunk_index to maintain document order
        selected_chunks.sort(key=lambda x: x.chunk_index)
        
        return selected_chunks
    
    def _deduplicate_chunks(self, chunks: List[ChunkSearchResult]) -> List[ChunkSearchResult]:
        """Remove duplicate or highly similar chunks.
        
        Args:
            chunks: List of chunks to deduplicate
            
        Returns:
            List[ChunkSearchResult]: Deduplicated chunks
        """
        # Simple deduplication based on content similarity
        deduplicated = []
        content_hashes = set()
        
        for chunk in chunks:
            # Create a simplified representation of the content for comparison
            # This removes whitespace and converts to lowercase
            simplified_content = re.sub(r'\s+', '', chunk.content.lower())
            content_hash = hash(simplified_content)
            
            # Only add if we haven't seen this content before
            if content_hash not in content_hashes:
                content_hashes.add(content_hash)
                deduplicated.append(chunk)
        
        return deduplicated
    
    def _limit_context_length(
        self,
        chunks: List[ChunkSearchResult],
        max_length: int
    ) -> List[ChunkSearchResult]:
        """Limit the total context length by selecting chunks.
        
        Args:
            chunks: List of chunks to limit
            max_length: Maximum context length in characters
            
        Returns:
            List[ChunkSearchResult]: Limited chunks
        """
        limited_chunks = []
        current_length = 0
        
        for chunk in chunks:
            # Calculate the length this chunk would add
            # Include some overhead for formatting
            chunk_length = len(chunk.content) + 50
            
            # If adding this chunk would exceed the limit, stop
            if current_length + chunk_length > max_length:
                break
            
            limited_chunks.append(chunk)
            current_length += chunk_length
        
        return limited_chunks
    
    def _format_chunks(
        self,
        chunks: List[ChunkSearchResult],
        options: ContextAssemblyOptions
    ) -> Tuple[str, bool]:
        """Format chunks into context.
        
        Args:
            chunks: List of chunks to format
            options: Assembly options
            
        Returns:
            Tuple[str, bool]: Formatted context and whether it was truncated
        """
        if not chunks:
            return "", False
        
        # Start with a header
        context_parts = ["SOURCE CHUNKS:"]
        truncated = False
        
        # Format each chunk
        for i, chunk in enumerate(chunks):
            # Format the chunk content
            if options.format_type == "markdown":
                # Format as markdown with citation
                if options.include_citations:
                    chunk_text = f"[{i+1}] {chunk.content}"
                else:
                    chunk_text = chunk.content
                
                # Add metadata if enabled
                if options.include_metadata and chunk.metadata:
                    metadata_text = "\n".join([f"- {k}: {v}" for k, v in chunk.metadata.items()])
                    chunk_text += f"\n\n*Metadata:*\n{metadata_text}"
            else:
                # Format as plain text
                if options.include_citations:
                    chunk_text = f"[{i+1}] {chunk.content}"
                else:
                    chunk_text = chunk.content
                
                # Add metadata if enabled
                if options.include_metadata and chunk.metadata:
                    metadata_text = "\n".join([f"{k}: {v}" for k, v in chunk.metadata.items()])
                    chunk_text += f"\n\nMetadata:\n{metadata_text}"
            
            context_parts.append(chunk_text)
        
        # Join all parts with double newlines
        context = "\n\n".join(context_parts)
        
        # Check if we need to truncate
        if len(context) > options.max_context_length:
            context = context[:options.max_context_length]
            truncated = True
            # Add a note about truncation
            context += "\n\n[Context truncated due to length limits]"
        
        return context, truncated
    
    def assemble_context_with_system_prompt(
        self,
        chunks: List[ChunkSearchResult],
        system_prompt: str,
        query: str,
        options: Optional[ContextAssemblyOptions] = None
    ) -> str:
        """Assemble context with system prompt and query.
        
        Args:
            chunks: List of chunks to assemble
            system_prompt: System prompt for the LLM
            query: User query
            options: Assembly options
            
        Returns:
            str: Assembled context with system prompt and query
        """
        # Assemble the context from chunks
        assembled = self.assemble_context(chunks, options)
        
        # Combine system prompt, context, and query
        full_prompt = f"{system_prompt}\n\n"
        
        if assembled.context:
            full_prompt += f"{assembled.context}\n\n"
        
        full_prompt += f"Question: {query}"
        
        return full_prompt


# Singleton instance
_context_assembly_service = None


def get_context_assembly_service() -> ContextAssemblyService:
    """Get the singleton instance of the context assembly service.
    
    Returns:
        ContextAssemblyService: The context assembly service
    """
    global _context_assembly_service
    if _context_assembly_service is None:
        _context_assembly_service = ContextAssemblyService()
    return _context_assembly_service


def assemble_context(
    chunks: List[ChunkSearchResult],
    max_context_length: int = DEFAULT_MAX_CONTEXT_LENGTH,
    include_metadata: bool = DEFAULT_INCLUDE_METADATA,
    format_type: str = DEFAULT_FORMAT_TYPE
) -> AssembledContext:
    """Assemble retrieved chunks into LLM context.
    
    Args:
        chunks: List of chunks to assemble
        max_context_length: Maximum context length in characters
        include_metadata: Whether to include metadata in context
        format_type: Format type ('markdown' or 'text')
        
    Returns:
        AssembledContext: Assembled context
    """
    service = get_context_assembly_service()
    options = ContextAssemblyOptions(
        max_context_length=max_context_length,
        include_metadata=include_metadata,
        format_type=format_type
    )
    return service.assemble_context(chunks, options)


def assemble_context_with_system_prompt(
    chunks: List[ChunkSearchResult],
    system_prompt: str,
    query: str,
    max_context_length: int = DEFAULT_MAX_CONTEXT_LENGTH,
    include_metadata: bool = DEFAULT_INCLUDE_METADATA,
    format_type: str = DEFAULT_FORMAT_TYPE
) -> str:
    """Assemble context with system prompt and query.
    
    Args:
        chunks: List of chunks to assemble
        system_prompt: System prompt for the LLM
        query: User query
        max_context_length: Maximum context length in characters
        include_metadata: Whether to include metadata in context
        format_type: Format type ('markdown' or 'text')
        
    Returns:
        str: Assembled context with system prompt and query
    """
    service = get_context_assembly_service()
    options = ContextAssemblyOptions(
        max_context_length=max_context_length,
        include_metadata=include_metadata,
        format_type=format_type
    )
    return service.assemble_context_with_system_prompt(chunks, system_prompt, query, options)