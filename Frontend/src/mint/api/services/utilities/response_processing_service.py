"""
Response Processing Service for Report Chat Feature

This module provides functionality for processing LLM responses,
extracting and validating citations, and formatting responses for frontend display.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

class ResponseProcessingService:
    """Service for processing LLM responses."""
    
    def __init__(self):
        """Initialize the response processing service."""
        # Regular expression for finding citations in the format [1], [2,3], etc.
        self.citation_pattern = r'\[(\d+(?:,\s*\d+)*)\]'
    
    def process_response(self, 
                        llm_response: str, 
                        available_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process the LLM response to extract and validate citations.
        
        Args:
            llm_response: The raw response from the LLM
            available_chunks: List of chunks that were provided as context
            
        Returns:
            Dict containing the processed response with validated citations
        """
        # Extract citations from the response
        citations, processed_text = self._extract_citations(llm_response)
        
        # Validate citations against available chunks
        validated_citations = self._validate_citations(citations, available_chunks)
        
        # Format the response for frontend display
        formatted_response = self._format_for_frontend(processed_text, validated_citations)
        
        return {
            "processed_text": processed_text,
            "citations": validated_citations,
            "formatted_response": formatted_response
        }
    
    def _extract_citations(self, text: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extract citations from the text and replace them with HTML-friendly markers.
        
        Args:
            text: The text to extract citations from
            
        Returns:
            Tuple containing:
                - List of extracted citations with their positions
                - Text with citations replaced by HTML-friendly markers
        """
        citations = []
        positions = []
        
        # Find all citation matches
        for match in re.finditer(self.citation_pattern, text):
            citation_text = match.group(0)  # The full citation text, e.g., [1,2,3]
            citation_indices = match.group(1)  # Just the indices, e.g., 1,2,3
            
            # Parse the indices
            try:
                indices = [int(idx.strip()) for idx in citation_indices.split(',')]
                
                # Store the citation information
                citations.append({
                    "original_text": citation_text,
                    "indices": indices,
                    "start": match.start(),
                    "end": match.end()
                })
                
                # Store the position for later replacement
                positions.append((match.start(), match.end(), len(citations) - 1))
            except ValueError:
                logger.warning(f"Failed to parse citation indices: {citation_indices}")
        
        # Replace citations with HTML-friendly markers, starting from the end to preserve positions
        processed_text = text
        for start, end, citation_idx in sorted(positions, reverse=True):
            marker = f'<citation id="citation-{citation_idx+1}">[{citation_idx+1}]</citation>'
            processed_text = processed_text[:start] + marker + processed_text[end:]
        
        return citations, processed_text
    
    def _validate_citations(self, 
                          citations: List[Dict[str, Any]], 
                          available_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate citations against available chunks.
        
        Args:
            citations: List of extracted citations
            available_chunks: List of chunks that were provided as context
            
        Returns:
            List of validated citations with chunk information
        """
        # Get the set of valid chunk indices
        valid_indices = {chunk.get("chunk_index") for chunk in available_chunks}
        
        validated_citations = []
        for i, citation in enumerate(citations):
            valid_chunk_indices = []
            invalid_chunk_indices = []
            
            for idx in citation["indices"]:
                if idx in valid_indices:
                    valid_chunk_indices.append(idx)
                else:
                    invalid_chunk_indices.append(idx)
            
            # Create the validated citation
            validated_citation = {
                "id": i + 1,  # 1-based ID for frontend display
                "original_text": citation["original_text"],
                "valid_indices": valid_chunk_indices,
                "invalid_indices": invalid_chunk_indices,
                "is_valid": len(valid_chunk_indices) > 0
            }
            
            # Add chunk content for valid indices
            if validated_citation["is_valid"]:
                validated_citation["chunks"] = [
                    next((chunk for chunk in available_chunks if chunk.get("chunk_index") == idx), None)
                    for idx in valid_chunk_indices
                ]
                validated_citation["chunks"] = [chunk for chunk in validated_citation["chunks"] if chunk is not None]
            
            validated_citations.append(validated_citation)
        
        return validated_citations
    
    def _format_for_frontend(self, 
                           text: str, 
                           citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format the processed response for frontend display.
        
        Args:
            text: The processed text with HTML-friendly citation markers
            citations: List of validated citations
            
        Returns:
            Dict containing the formatted response for frontend display
        """
        # Create a mapping of citation IDs to their information
        citation_map = {citation["id"]: citation for citation in citations}
        
        # Count valid and invalid citations
        valid_citations = sum(1 for c in citations if c["is_valid"])
        invalid_citations = sum(1 for c in citations if not c["is_valid"])
        
        return {
            "html": text,
            "citation_map": citation_map,
            "stats": {
                "total_citations": len(citations),
                "valid_citations": valid_citations,
                "invalid_citations": invalid_citations
            }
        }
    
    def extract_citation_references(self, text: str) -> Set[int]:
        """
        Extract all citation references from a text.
        
        Args:
            text: The text to extract citation references from
            
        Returns:
            Set of unique citation indices referenced in the text
        """
        references = set()
        
        for match in re.finditer(self.citation_pattern, text):
            citation_indices = match.group(1)  # Just the indices, e.g., 1,2,3
            
            try:
                indices = [int(idx.strip()) for idx in citation_indices.split(',')]
                references.update(indices)
            except ValueError:
                logger.warning(f"Failed to parse citation indices: {citation_indices}")
        
        return references
    
    def format_citations_markdown(self, 
                                text: str, 
                                chunk_map: Dict[int, Dict[str, Any]]) -> str:
        """
        Format citations in markdown format for display.
        
        Args:
            text: The text with citations
            chunk_map: Mapping of chunk indices to chunk information
            
        Returns:
            Text with formatted markdown citations
        """
        def replace_citation(match):
            citation_indices = match.group(1)
            indices = [int(idx.strip()) for idx in citation_indices.split(',')]
            
            # Create a footnote-style citation
            footnotes = []
            for idx in indices:
                if idx in chunk_map:
                    chunk = chunk_map[idx]
                    # Create a short excerpt from the chunk
                    excerpt = chunk.get("content", "")[:50] + "..." if len(chunk.get("content", "")) > 50 else chunk.get("content", "")
                    footnotes.append(f"Chunk {idx}: {excerpt}")
                else:
                    footnotes.append(f"Chunk {idx}: Not found")
            
            # Join the footnotes with line breaks
            footnote_text = "<br>".join(footnotes)
            
            # Return the formatted citation
            return f'[{citation_indices}](# "{footnote_text}")'
        
        # Replace citations with markdown footnotes
        return re.sub(self.citation_pattern, replace_citation, text)