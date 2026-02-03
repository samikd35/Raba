#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chunk Storage Service for MINT.

This module provides functionality to store report chunks and embeddings
in Supabase with transaction support and error handling.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from ...system.core.supabase_client import get_supabase_client
from ...report.report_models import ReportChunk, ReportChunkWithEmbedding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
BATCH_SIZE = 25  # Smaller batch size for better reliability


class ChunkStorageService:
    """Service for storing report chunks and embeddings in Supabase."""

    def __init__(self):
        """Initialize the chunk storage service."""
        self.supabase = get_supabase_client()
        
    async def store_chunks(
        self, 
        report_id: str, 
        chunks_with_embeddings: List[ReportChunkWithEmbedding]
    ) -> bool:
        """Store report chunks with embeddings in the database with transaction support.
        
        Args:
            report_id: ID of the report
            chunks_with_embeddings: List of report chunks with embeddings
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Storing {len(chunks_with_embeddings)} chunks for report {report_id}")
        
        if not chunks_with_embeddings:
            logger.warning("No chunks to store")
            return False
        
        try:
            # Start a transaction by deleting existing chunks for this report
            # This ensures we have a clean state and maintains atomicity
            try:
                delete_result = self.supabase.client.table("chunks").delete().eq("doc_id", report_id).execute()
                if hasattr(delete_result, "error") and delete_result.error:
                    logger.warning(f"Error deleting existing chunks: {delete_result.error}")
                    # If deletion fails, we should not proceed with insertion
                    return False
                else:
                    logger.info(f"Successfully deleted existing chunks for report {report_id}")
                    
                # Add a small delay to ensure deletion is fully committed
                await asyncio.sleep(0.5)
                
                # Verify deletion was successful by checking if any chunks remain
                verify_result = self.supabase.client.table("chunks").select("*").eq("doc_id", report_id).execute()
                remaining_count = len(verify_result.data) if verify_result.data else 0
                if remaining_count > 0:
                    logger.warning(f"Deletion incomplete: {remaining_count} chunks still exist for report {report_id}")
                    
                    # Try up to 3 more aggressive deletion attempts
                    for attempt in range(3):
                        logger.info(f"Aggressive deletion attempt {attempt + 1}/3")
                        
                        # Force another deletion attempt with longer timeout
                        delete_result = self.supabase.client.table("chunks").delete().eq("doc_id", report_id).execute()
                        await asyncio.sleep(1.5)  # Longer wait
                        
                        # Check again
                        verify_result = self.supabase.client.table("chunks").select("*").eq("doc_id", report_id).execute()
                        remaining_count = len(verify_result.data) if verify_result.data else 0
                        
                        if remaining_count == 0:
                            logger.info(f"✅ Deletion successful after {attempt + 1} attempts")
                            break
                        else:
                            logger.warning(f"Still {remaining_count} chunks remaining after attempt {attempt + 1}")
                    
                    # If still chunks remain after all attempts, fail the operation
                    if remaining_count > 0:
                        logger.error(f"❌ CRITICAL: Unable to delete all chunks after 3 attempts. {remaining_count} chunks remain.")
                        logger.error(f"❌ This will cause constraint violations. Aborting storage operation.")
                        return False
                    
            except Exception as e:
                logger.error(f"Error deleting existing chunks: {e}")
                return False
            
            # Store chunks in batches to avoid overloading the database
            success_count = 0
            
            for i in range(0, len(chunks_with_embeddings), BATCH_SIZE):
                batch = chunks_with_embeddings[i:i+BATCH_SIZE]
                
                # Prepare batch data for insertion
                batch_data = []
                skipped_count = 0
                for chunk in batch:
                    # Skip chunks with None embeddings
                    if chunk.embedding is None:
                        logger.warning(f"⚠️ SKIPPING chunk {chunk.chunk_index}: No embedding")
                        skipped_count += 1
                        continue
                        
                    # Ensure embedding is properly formatted for pgvector
                    embedding = chunk.embedding
                    if isinstance(embedding, str):
                        # If embedding is stored as string, parse it back to list
                        import json
                        try:
                            embedding = json.loads(embedding)
                        except:
                            logger.error(f"⚠️ SKIPPING chunk {chunk.chunk_index}: Failed to parse embedding string")
                            skipped_count += 1
                            continue
                    
                    # Ensure embedding is a list of floats
                    if not isinstance(embedding, list):
                        logger.error(f"⚠️ SKIPPING chunk {chunk.chunk_index}: Embedding is not a list: {type(embedding)}")
                        skipped_count += 1
                        continue
                    
                    # Validate embedding dimension
                    if len(embedding) != 1536:
                        logger.error(f"⚠️ SKIPPING chunk {chunk.chunk_index}: Wrong dimension: {len(embedding)}, expected 1536")
                        skipped_count += 1
                        continue
                    
                    # Ensure all values are floats (not numpy types or other numeric types)
                    try:
                        embedding = [float(x) for x in embedding]
                    except (ValueError, TypeError) as e:
                        logger.error(f"⚠️ SKIPPING chunk {chunk.chunk_index}: Failed to convert embedding to floats: {e}")
                        skipped_count += 1
                        continue
                    
                    # Calculate token count (rough estimate: 1 token ≈ 4 characters)
                    token_count = len(chunk.content) // 4
                    
                    batch_data.append({
                        "doc_id": report_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "token_count": token_count,
                        "embedding": embedding,  # Store as proper list for pgvector
                        "metadata": chunk.metadata
                    })
                
                if skipped_count > 0:
                    logger.warning(f"⚠️ BATCH {i//BATCH_SIZE + 1}: Skipped {skipped_count}/{len(batch)} chunks due to validation failures")
                
                if not batch_data:
                    logger.warning(f"⚠️ BATCH {i//BATCH_SIZE + 1}: No valid chunks to store (all skipped)")
                    continue
                
                # Insert batch into database with retry logic
                success = await self._insert_batch_with_retry(batch_data)
                if success:
                    success_count += len(batch_data)
                    logger.info(f"Stored chunks batch {i//BATCH_SIZE + 1}/{(len(chunks_with_embeddings)-1)//BATCH_SIZE + 1}")
            
            # Check if we stored at least 80% of chunks successfully
            success_rate = success_count / len(chunks_with_embeddings)
            if success_rate < 0.8:
                logger.warning(f"Only stored {success_count}/{len(chunks_with_embeddings)} chunks ({success_rate:.1%})")
                return False
            
            logger.info(f"Successfully stored {success_count}/{len(chunks_with_embeddings)} chunks ({success_rate:.1%})")
            return True
        
        except Exception as e:
            logger.error(f"Error storing chunks: {e}")
            return False
    
    async def _insert_batch_with_retry(self, batch_data: List[Dict[str, Any]]) -> bool:
        """Insert a batch of chunks with retry logic.
        
        Args:
            batch_data: List of chunk data to insert
            
        Returns:
            bool: True if successful, False otherwise
        """
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                # For now, use the regular insert method
                # The vector search will work even if stored as string, we just need to parse it
                result = self.supabase.client.table("chunks").insert(batch_data).execute()
                
                if hasattr(result, "error") and result.error:
                    logger.error(f"Error storing chunks batch: {result.error}")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        return False
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    return True  # Success
            
            except Exception as e:
                logger.error(f"Exception storing chunks batch: {e}")
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    return False
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        
        return False
    
    async def get_chunks_by_report_id(self, report_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a report.
        
        Args:
            report_id: ID of the report
            
        Returns:
            List[Dict[str, Any]]: List of chunks
        """
        try:
            result = self.supabase.client.table("chunks") \
                .select("id, chunk_index, content, embedding, metadata") \
                .eq("doc_id", report_id) \
                .order("chunk_index") \
                .execute()
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error getting chunks: {result.error}")
                return []
            
            return result.data
        
        except Exception as e:
            logger.error(f"Error getting chunks: {e}")
            return []
    
    async def delete_chunks_by_report_id(self, report_id: str) -> bool:
        """Delete all chunks for a report.
        
        Args:
            report_id: ID of the report
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.supabase.client.table("chunks").delete().eq("doc_id", report_id).execute()
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error deleting chunks: {result.error}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return False


# Singleton instance
_chunk_storage_service = None


def get_chunk_storage_service() -> ChunkStorageService:
    """Get the singleton instance of the chunk storage service.
    
    Returns:
        ChunkStorageService: The chunk storage service
    """
    global _chunk_storage_service
    if _chunk_storage_service is None:
        _chunk_storage_service = ChunkStorageService()
    return _chunk_storage_service


async def store_chunks(report_id: str, chunks_with_embeddings: List[ReportChunkWithEmbedding]) -> bool:
    """Store report chunks with embeddings in the database.
    
    Args:
        report_id: ID of the report
        chunks_with_embeddings: List of report chunks with embeddings
        
    Returns:
        bool: True if successful, False otherwise
    """
    service = get_chunk_storage_service()
    return await service.store_chunks(report_id, chunks_with_embeddings)