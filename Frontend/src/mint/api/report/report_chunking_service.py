#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Chunking Service for MINT.

This module provides functionality to chunk reports and generate embeddings
for RAG-powered chat with reports.
"""

import json
import logging
import re
import uuid
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import httpx
import numpy as np
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..system.core.supabase_client import get_supabase_client
from ..services.ai.embedding_service import get_embedding_service
from .report_models import ReportChunk, ReportChunkWithEmbedding

# Import AI token monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext
from ..system.middleware.id_consistency_middleware import ensure_report_id_consistency, log_id_flow, IDConsistencyError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 1000  # Characters
DEFAULT_CHUNK_OVERLAP = 125  # Characters (12.5% of 1000)
# Use OpenAI embeddings for consistency with vector search
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small
MAX_BATCH_SIZE = 10  # Maximum number of chunks to embed in a single API call
MAX_RETRIES = 3  # Maximum number of retries for API calls





class ReportChunkingService:
    """Service for chunking reports and generating embeddings."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the report chunking service.
        
        Args:
            api_key: Optional API key for the embedding model
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.supabase = get_supabase_client()
        
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variables using AI configuration."""
        from src.mint.api.ai.config import get_api_key, get_provider_with_fallback
        # Use Azure OpenAI with fallback to OpenAI for embeddings
        provider = get_provider_with_fallback()
        api_key = get_api_key(provider)
        if not api_key:
            logger.warning(f"API key not found for provider {provider}")
        return api_key or ""
    
    def chunk_report(
        self, 
        report_content: str, 
        chunk_size: int = DEFAULT_CHUNK_SIZE, 
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[ReportChunk]:
        """Chunk a report into smaller pieces with overlap.
        
        Args:
            report_content: The report content to chunk
            chunk_size: The maximum size of each chunk in characters
            chunk_overlap: The overlap between chunks in characters
            
        Returns:
            List[ReportChunk]: List of report chunks
        """
        logger.info(f"Chunking report with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        # Validate overlap percentage (should be 10-15%)
        overlap_percentage = (chunk_overlap / chunk_size) * 100
        if not (10 <= overlap_percentage <= 15):
            logger.warning(
                f"Overlap percentage {overlap_percentage:.1f}% is outside recommended range (10-15%). "
                f"Adjusting overlap to maintain 12.5% overlap."
            )
            chunk_overlap = int(chunk_size * 0.125)  # Set to 12.5% overlap
        
        # Clean up the report content
        # Preserve paragraph breaks but remove excessive whitespace
        report_content = re.sub(r'[ \t]+', ' ', report_content)
        report_content = re.sub(r'\n{3,}', '\n\n', report_content)
        
        # Split the report into paragraphs while preserving headings
        paragraphs = []
        current_paragraph = ""
        
        for line in report_content.split('\n'):
            line = line.strip()
            # Check if line is a heading (starts with # or ##)
            if re.match(r'^#{1,6}\s+', line):
                # If we have accumulated text, add it as a paragraph
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = ""
                # Add heading as its own paragraph to ensure it stays with its content
                paragraphs.append(line)
            elif not line:  # Empty line indicates paragraph break
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = ""
            else:
                if current_paragraph:
                    current_paragraph += " " + line
                else:
                    current_paragraph = line
        
        # Add the last paragraph if it's not empty
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        chunk_start_char = 0
        total_chars = 0
        section_context = ""  # Track current section heading
        
        for paragraph in paragraphs:
            # Check if this is a heading
            is_heading = re.match(r'^#{1,6}\s+', paragraph)
            if is_heading:
                section_context = paragraph.strip()
            
            # If adding this paragraph would exceed the chunk size, create a new chunk
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                # Calculate character positions
                chunk_end_char = chunk_start_char + len(current_chunk)
                
                # Create chunk with metadata
                chunks.append(
                    ReportChunk(
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        metadata={
                            "start_char": chunk_start_char,
                            "end_char": chunk_end_char,
                            "section": section_context,
                            "position": chunk_index + 1,  # 1-based position for user-friendly display
                            "overlap_previous": chunk_index > 0,  # Whether this chunk overlaps with previous
                            "overlap_next": True,  # Will be updated for the last chunk
                        }
                    )
                )
                
                # Calculate the start position for the next chunk with overlap
                overlap_text = ""
                if len(current_chunk) > chunk_overlap:
                    # Find a good break point for overlap (prefer sentence boundaries)
                    overlap_text = current_chunk[-chunk_overlap:]
                    sentence_break = re.search(r'[.!?]\s+', overlap_text)
                    
                    if sentence_break:
                        # Start from the beginning of the last complete sentence in the overlap
                        break_pos = sentence_break.end()
                        overlap_text = overlap_text[break_pos:]
                    
                    # Start a new chunk with overlap from the previous chunk
                    current_chunk = overlap_text + " " + paragraph
                    chunk_start_char = chunk_end_char - len(overlap_text)
                else:
                    # If the previous chunk is smaller than the overlap, just use it all
                    current_chunk = current_chunk + " " + paragraph
                    # Don't update chunk_start_char as we're using the entire previous chunk
                
                chunk_index += 1
            else:
                # Add the paragraph to the current chunk
                if current_chunk:
                    current_chunk += " " + paragraph
                else:
                    current_chunk = paragraph
                    # Only update start position when starting a new chunk from scratch
                    if chunk_index == 0:
                        chunk_start_char = total_chars
            
            # Update total character count
            total_chars += len(paragraph) + 1  # +1 for the space or newline
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunk_end_char = chunk_start_char + len(current_chunk)
            chunks.append(
                ReportChunk(
                    chunk_index=chunk_index,
                    content=current_chunk.strip(),
                    metadata={
                        "start_char": chunk_start_char,
                        "end_char": chunk_end_char,
                        "section": section_context,
                        "position": chunk_index + 1,
                        "overlap_previous": chunk_index > 0,
                        "overlap_next": False,  # Last chunk doesn't overlap with next
                    }
                )
            )
        
        # Update the overlap_next flag for the second-to-last chunk
        if len(chunks) > 1:
            chunks[-2].metadata["overlap_next"] = True
        
        # Add HTML span wrappers for citation highlighting
        for chunk in chunks:
            chunk_id = f"chunk-{chunk.chunk_index}"
            chunk.content = f'<span id="{chunk_id}" class="report-chunk">{chunk.content}</span>'
            chunk.metadata["chunk_id"] = chunk_id
        
        logger.info(f"Created {len(chunks)} chunks from report")
        return chunks
    
    async def generate_embeddings(
        self, 
        chunks: List[ReportChunk],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> List[ReportChunkWithEmbedding]:
        """Generate embeddings for report chunks.
        
        Args:
            chunks: List of report chunks
            user_id: Optional user ID for monitoring
            tenant_id: Optional tenant ID for monitoring
            report_id: Optional report ID for monitoring
            
        Returns:
            List[ReportChunkWithEmbedding]: List of report chunks with embeddings
        """
        from src.mint.api.services.utilities.id_logging_service import log_chunking_operation
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        if not self.api_key:
            log_chunking_operation("EMBEDDING_FAILED_NO_API_KEY", "unknown")
            raise ValueError("API key is required for generating embeddings")
        
        log_chunking_operation("EMBEDDING_START", "unknown", chunk_count=len(chunks))
        
        # Get the embedding service
        embedding_service = get_embedding_service(self.api_key)
        
        # Extract plain text from HTML content
        texts = [self._extract_text_from_html(chunk.content) for chunk in chunks]
        
        # Create monitoring context for embedding generation
        monitoring_context = None
        if user_id or tenant_id or report_id:
            monitoring_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=report_id,
                feature_id="pv_report_embedding",
                workflow_name="pv_report_workflow",
                step_name="report_chunk_embedding",
                environment="prod"
            )
        
        # Generate embeddings using the embedding service
        embeddings = await embedding_service.generate_embeddings(texts, monitoring_context)
        
        # Combine chunks with their embeddings
        chunks_with_embeddings = []
        failed_embeddings = 0
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is not None:
                chunks_with_embeddings.append(
                    ReportChunkWithEmbedding(
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        metadata=chunk.metadata,
                        embedding=embedding
                    )
                )
            else:
                logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_index}")
                failed_embeddings += 1
        
        success_count = len(chunks_with_embeddings)
        logger.info(f"Successfully generated embeddings for {success_count}/{len(chunks)} chunks")
        
        log_chunking_operation("EMBEDDING_COMPLETE", "unknown", 
                             chunk_count=len(chunks),
                             embedding_count=success_count,
                             failed_count=failed_embeddings)
        
        return chunks_with_embeddings
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from HTML content.
        
        Args:
            html_content: HTML content
            
        Returns:
            str: Plain text
        """
        # Simple regex to remove HTML tags
        return re.sub(r'<[^>]+>', '', html_content)
    
    async def store_chunks(
        self, 
        report_id: str, 
        chunks_with_embeddings: List[ReportChunkWithEmbedding]
    ) -> bool:
        """Store report chunks with embeddings in the database.
        
        Args:
            report_id: ID of the report
            chunks_with_embeddings: List of report chunks with embeddings
            
        Returns:
            bool: True if successful, False otherwise
        """
        from src.mint.api.services.utilities.id_logging_service import log_chunking_operation, log_database_operation
        
        logger.info(f"Storing {len(chunks_with_embeddings)} chunks for report {report_id}")
        
        if not chunks_with_embeddings:
            logger.warning("No chunks to store")
            log_chunking_operation("STORAGE_FAILED_NO_CHUNKS", report_id)
            return False
        
        log_chunking_operation("STORAGE_START", report_id, chunk_count=len(chunks_with_embeddings))
        
        try:
            # Use lazy import to avoid circular dependency
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            chunk_storage_service = get_chunk_storage_service()
            
            # Log database operation attempt
            log_database_operation("INSERT", "report_chunks", 
                                 filters={"report_id": report_id},
                                 record_count=len(chunks_with_embeddings))
            
            success = await chunk_storage_service.store_chunks(report_id, chunks_with_embeddings)
            
            if success:
                log_chunking_operation("STORAGE_SUCCESS", report_id, chunk_count=len(chunks_with_embeddings))
                log_database_operation("INSERT_SUCCESS", "report_chunks", 
                                     filters={"report_id": report_id},
                                     result_count=len(chunks_with_embeddings))
            else:
                log_chunking_operation("STORAGE_FAILED", report_id, chunk_count=len(chunks_with_embeddings))
                log_database_operation("INSERT_FAILED", "report_chunks", 
                                     filters={"report_id": report_id})
            
            return success
        
        except Exception as e:
            logger.error(f"Error storing chunks: {e}")
            log_chunking_operation("STORAGE_FAILED_EXCEPTION", report_id, 
                                 chunk_count=len(chunks_with_embeddings),
                                 error=str(e))
            return False
    
    async def process_report(
        self, 
        report_id: str, 
        report_content: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> bool:
        """Process a report by chunking, generating embeddings, and storing.
        
        Args:
            report_id: ID of the report
            report_content: Content of the report
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Processing report {report_id}")
        
        try:
            # Step 1: Chunk the report
            chunks = self.chunk_report(report_content, chunk_size, chunk_overlap)
            
            # Step 2: Generate embeddings
            chunks_with_embeddings = await self.generate_embeddings(chunks)
            
            # Step 3: Store chunks with embeddings
            success = await self.store_chunks(report_id, chunks_with_embeddings)
            
            return success
        
        except Exception as e:
            logger.error(f"Error processing report: {e}")
            return False
    
    async def process_report_from_json(
        self, 
        report_id: str, 
        report_json: Dict[str, Any],
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        status_callback: Optional[callable] = None
    ) -> bool:
        """Process a report from JSON by extracting content, chunking, generating embeddings, and storing.
        
        Args:
            report_id: ID of the report (must be valid UUID from mint_reports.id)
            report_json: JSON content of the report
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            status_callback: Optional callback function to report processing status
            
        Returns:
            bool: True if successful, False otherwise
        """
        from src.mint.api.services.utilities.id_logging_service import log_chunking_operation, IDOperationTracker
        
        logger.info(f"Processing report {report_id} from JSON")
        
        # Helper function to update status
        def update_status(stage: str, message: str, progress: float = None):
            if status_callback:
                status_callback(report_id, stage, message, progress)
        
        # Start comprehensive ID tracking for chunking operation
        with IDOperationTracker("REPORT_CHUNKING", report_id=report_id) as tracker:
            
            update_status("validation", "Validating report...", 0.1)
            
            # CRITICAL: Validate report_id format and existence
            if not self._validate_report_id(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                tracker.log_error("INVALID_REPORT_ID", f"Invalid report_id format: {report_id}")
                log_chunking_operation("CHUNKING_FAILED_INVALID_ID", report_id)
                update_status("error", "Invalid report ID format", 0.0)
                return False
            
            tracker.update_ids("ID_VALIDATION_SUCCESS")
            
            # Verify report exists in database before processing
            if not await self._verify_report_exists(report_id):
                logger.error(f"Report {report_id} does not exist in mint_reports table")
                tracker.log_error("REPORT_NOT_FOUND", f"Report {report_id} does not exist in mint_reports table")
                log_chunking_operation("CHUNKING_FAILED_NOT_FOUND", report_id)
                update_status("error", "Report not found in database", 0.0)
                return False
            
            tracker.update_ids("REPORT_EXISTENCE_VERIFIED")
            log_chunking_operation("CHUNKING_START", report_id, 
                                 chunk_size=chunk_size, 
                                 chunk_overlap=chunk_overlap)
            
            try:
                # Extract text content from the report JSON
                update_status("extraction", "Extracting content from report...", 0.2)
                tracker.update_ids("CONTENT_EXTRACTION_START")
                report_content = self._extract_text_from_report_json(report_json)
                
                content_length = len(report_content)
                tracker.update_ids("CONTENT_EXTRACTION_SUCCESS", content_length=content_length)
                
                # Process the extracted content with validated report_id
                logger.info(f"ID CONSISTENCY: Using validated report_id {report_id} for chunking")
                tracker.update_ids("PROCESSING_START")
                
                update_status("chunking", "Breaking report into chunks...", 0.3)
                
                # Step 1: Chunk the report
                chunks = self.chunk_report(report_content, chunk_size, chunk_overlap)
                update_status("embedding", f"Generating embeddings for {len(chunks)} chunks...", 0.5)
                
                # Step 2: Generate embeddings (pass report_id for monitoring)
                chunks_with_embeddings = await self.generate_embeddings(chunks, report_id=report_id)
                update_status("storing", "Storing processed chunks...", 0.8)
                
                # Step 3: Store chunks with embeddings
                success = await self.store_chunks(report_id, chunks_with_embeddings)
                
                if success:
                    tracker.update_ids("PROCESSING_SUCCESS")
                    log_chunking_operation("CHUNKING_SUCCESS", report_id)
                    update_status("complete", "Report processing completed successfully!", 1.0)
                else:
                    tracker.log_error("PROCESSING_FAILED", "Report processing returned False")
                    log_chunking_operation("CHUNKING_FAILED", report_id)
                    update_status("error", "Failed to store processed chunks", 0.8)
                
                return success
            
            except Exception as e:
                logger.error(f"Error processing report from JSON: {e}")
                tracker.log_error("PROCESSING_EXCEPTION", str(e))
                log_chunking_operation("CHUNKING_FAILED_EXCEPTION", report_id, error=str(e))
                update_status("error", f"Processing failed: {str(e)}", 0.0)
                return False
    
    def _validate_report_id(self, report_id: str) -> bool:
        """Validate that report_id is a proper UUID format.
        
        Args:
            report_id: The report ID to validate
            
        Returns:
            bool: True if valid UUID format, False otherwise
        """
        try:
            import uuid
            uuid.UUID(report_id)
            return True
        except (ValueError, TypeError):
            return False
    
    async def _verify_report_exists(self, report_id: str) -> bool:
        """Verify that the report exists in the mint_reports table.
        
        Args:
            report_id: The report ID to verify
            
        Returns:
            bool: True if report exists, False otherwise
        """
        try:
            result = self.supabase.client.table("documents") \
                .select("id") \
                .eq("id", report_id) \
                .eq("source_type", "pv_report") \
                .limit(1) \
                .execute()
            
            exists = bool(result.data and len(result.data) > 0)
            if exists:
                logger.info(f"ID CONSISTENCY: Verified report {report_id} exists in documents table")
            else:
                logger.error(f"ID CONSISTENCY: Report {report_id} NOT found in documents table")
            
            return exists
            
        except Exception as e:
            logger.error(f"Error verifying report existence: {e}")
            return False
    
    def _extract_text_from_report_json(self, report_json: Dict[str, Any]) -> str:
        """Extract text content from a report JSON.
        
        Args:
            report_json: JSON content of the report
            
        Returns:
            str: Extracted text content
        """
        # Initialize an empty list to collect text parts
        text_parts = []
        
        # Handle the actual report structure used in the database
        # Reports are stored with structure: {"reports": {"final": {...}}, "metadata": {}, "conversation_history": [...]}
        report = None
        
        # First, try to find the final report in the nested structure
        if isinstance(report_json, dict):
            if "reports" in report_json and isinstance(report_json["reports"], dict):
                if "final" in report_json["reports"] and report_json["reports"]["final"]:
                    report = report_json["reports"]["final"]
                    logger.info("Found final report in nested structure")
            
            # Fallback: try direct report key
            if not report and "report" in report_json:
                report = report_json["report"]
                logger.info("Found report in direct structure")
            
            # Fallback: use the root if it has report-like fields
            if not report and any(key in report_json for key in ["title", "summary", "executive_summary", "industry_analysis"]):
                report = report_json
                logger.info("Using root as report structure")
        
        if not report:
            logger.warning("No report content found in JSON structure")
            return ""
        
        logger.info(f"Extracting text from report with keys: {list(report.keys()) if isinstance(report, dict) else 'not a dict'}")
        
        # Extract title
        if "title" in report:
            text_parts.append(f"# {report['title']}")
        
        # Extract summary/executive summary
        if "summary" in report:
            text_parts.append(f"## Executive Summary\n{report['summary']}")
        elif "executive_summary" in report:
            if isinstance(report["executive_summary"], dict) and "content" in report["executive_summary"]:
                text_parts.append(f"## Executive Summary\n{report['executive_summary']['content']}")
            else:
                text_parts.append(f"## Executive Summary\n{report['executive_summary']}")
        
        # Extract industry analysis
        if "industry_analysis" in report:
            if isinstance(report["industry_analysis"], dict) and "content" in report["industry_analysis"]:
                text_parts.append(f"## Industry Analysis\n{report['industry_analysis']['content']}")
            else:
                text_parts.append(f"## Industry Analysis\n{report['industry_analysis']}")
        
        # Extract challenges analysis
        if "challenges_analysis" in report:
            if isinstance(report["challenges_analysis"], dict) and "content" in report["challenges_analysis"]:
                text_parts.append(f"## Challenges Analysis\n{report['challenges_analysis']['content']}")
            else:
                text_parts.append(f"## Challenges Analysis\n{report['challenges_analysis']}")
        
        # Extract recommendations
        if "recommendations" in report:
            if isinstance(report["recommendations"], dict) and "content" in report["recommendations"]:
                text_parts.append(f"## Recommendations\n{report['recommendations']['content']}")
            else:
                text_parts.append(f"## Recommendations\n{report['recommendations']}")
        
        # Extract sections if they exist
        if "sections" in report and isinstance(report["sections"], dict):
            for section_title, section_content in report["sections"].items():
                if isinstance(section_content, dict) and "content" in section_content:
                    text_parts.append(f"## {section_title}\n{section_content['content']}")
                elif isinstance(section_content, str):
                    text_parts.append(f"## {section_title}\n{section_content}")
                elif isinstance(section_content, list):
                    # Handle list of section items
                    section_text = f"## {section_title}\n"
                    for item in section_content:
                        if isinstance(item, dict) and "content" in item:
                            section_text += f"{item['content']}\n\n"
                        elif isinstance(item, str):
                            section_text += f"{item}\n\n"
                    text_parts.append(section_text)
        
        # Join all parts with double newlines
        extracted_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(extracted_text)} characters of text from report")
        
        return extracted_text


# Singleton instance
_report_chunking_service = None


def get_report_chunking_service(api_key: Optional[str] = None) -> ReportChunkingService:
    """Get the singleton instance of the report chunking service.
    
    Args:
        api_key: Optional API key for the embedding model
        
    Returns:
        ReportChunkingService: The report chunking service
    """
    global _report_chunking_service
    if _report_chunking_service is None:
        _report_chunking_service = ReportChunkingService(api_key)
    return _report_chunking_service


async def process_report(report_id: str, report_content: Dict[str, Any]) -> bool:
    """Process a report by chunking, generating embeddings, and storing.
    
    Args:
        report_id: ID of the report
        report_content: Content of the report
        
    Returns:
        bool: True if successful, False otherwise
    """
    service = get_report_chunking_service()
    return await service.process_report_from_json(report_id, report_content)