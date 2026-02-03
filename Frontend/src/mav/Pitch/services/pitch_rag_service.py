"""
Pitch Deck RAG Service

Handles vector similarity search over project chunks for pitch deck generation.
Provides slide-aware retrieval with artifact type filtering.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.mint.api.system.core.supabase_client import get_service_role_client
from src.mint.api.services.ai.embedding_service import EmbeddingService, get_embedding_service

from ..models import ProjectEvidence, DEFAULT_PITCH_CONFIG, SLIDE_ARTIFACT_HINTS

logger = logging.getLogger(__name__)

# Retry configuration for embedding calls
MAX_EMBEDDING_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class PitchDeckRAGService:
    """
    Service for retrieving project evidence for pitch deck slides.
    
    Uses the existing chunks table populated by VMPProjectChunkingService.
    Provides slide-aware retrieval with artifact type filtering and re-ranking.
    """
    
    CHUNKS_TABLE = "chunks"
    
    # Priority boosts for different artifact types
    PRIORITY_BOOST = {
        "vmp_bmc_v2": 0.15,
        "vmp_vps_v2": 0.15,
        "vmp_mvp_requirements": 0.12,
        "vmp_market_research": 0.12,
        "vmp_customer_profile_v2": 0.10,
        "vmp_hypothesis": 0.08,
        "vmp_assumptions": 0.08,
        "vmp_bmc_v1": 0.05,
        "vmp_vps_v1": 0.05,
        "vmp_persona": 0.05,
    }
    
    # Penalize metadata-heavy sections
    SECTION_PENALTY = {
        "sources": -0.20,
        "references": -0.20,
        "metadata": -0.15,
    }
    
    def __init__(self):
        """Initialize RAG service with embedding service and DB client."""
        self.supabase = get_service_role_client()
        self.embedding_service: EmbeddingService = get_embedding_service()
        logger.info("✅ PitchDeckRAGService initialized")
    
    async def retrieve_for_slide(
        self,
        query: str,
        project_id: str,
        tenant_id: str,
        slide_type: Optional[str] = None,
        artifact_hints: Optional[List[str]] = None,
        top_k: int = None
    ) -> List[ProjectEvidence]:
        """
        Retrieve relevant project evidence for a specific slide.
        
        Args:
            query: Search query (will be embedded)
            project_id: VMP project ID (strict filter)
            tenant_id: Tenant ID (strict filter)
            slide_type: Type of slide (for default artifact hints)
            artifact_hints: Specific artifact types to prioritize
            top_k: Max chunks to return
            
        Returns:
            List of ProjectEvidence objects sorted by relevance
        """
        top_k = top_k or DEFAULT_PITCH_CONFIG.rag_top_k
        
        # Get artifact hints from slide type if not provided
        if not artifact_hints and slide_type:
            artifact_hints = SLIDE_ARTIFACT_HINTS.get(slide_type, [])
        
        try:
            # Step 1: Generate query embedding with retry logic
            logger.info(f"🔍 PITCH RAG: Generating embedding for: {query[:50]}...")
            query_embedding = None
            last_error = None
            
            for attempt in range(MAX_EMBEDDING_RETRIES):
                try:
                    query_embedding = await self.embedding_service.generate_single_embedding(query)
                    if query_embedding:
                        break
                except Exception as embed_error:
                    last_error = embed_error
                    if attempt < MAX_EMBEDDING_RETRIES - 1:
                        delay = RETRY_BASE_DELAY * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"🔄 PITCH RAG: Embedding attempt {attempt + 1} failed, retrying in {delay}s: {embed_error}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"🔍 PITCH RAG: All {MAX_EMBEDDING_RETRIES} embedding attempts failed: {embed_error}")
            
            if not query_embedding:
                logger.error(f"Failed to generate query embedding after {MAX_EMBEDDING_RETRIES} attempts")
                return []
            
            # Step 2: Execute vector similarity search
            logger.info(f"🔍 PITCH RAG: Searching chunks for project {project_id}, slide_type={slide_type}")
            
            result = self.supabase.client.rpc(
                "match_project_chunks",
                {
                    "query_embedding": query_embedding,
                    "p_project_id": project_id,
                    "p_tenant_id": tenant_id,
                    "match_count": top_k * 3,  # Get more for re-ranking
                    "match_threshold": 0.0
                }
            ).execute()
            
            logger.info(f"🔍 PITCH RAG: RPC returned {len(result.data) if result.data else 0} chunks")
            
            if not result.data:
                logger.info("🔍 PITCH RAG: No matching chunks found")
                return []
            
            # Step 3: Re-rank with artifact hints and priorities
            evidence_list = []
            for chunk in result.data:
                source_type = chunk.get("source_type") or chunk.get("metadata", {}).get("source_type", "unknown")
                section_type = chunk.get("metadata", {}).get("section_type", "")
                
                # Calculate adjusted score
                base_score = float(chunk.get("similarity", 0.5))
                
                # Apply priority boost
                boost = self.PRIORITY_BOOST.get(source_type, 0)
                
                # Apply section penalty
                penalty = self.SECTION_PENALTY.get(section_type, 0)
                
                # Apply artifact hint boost (if this artifact type is hinted)
                hint_boost = 0.10 if artifact_hints and source_type in artifact_hints else 0
                
                adjusted_score = base_score + boost + penalty + hint_boost
                
                evidence = ProjectEvidence(
                    chunk_id=str(chunk["id"]),
                    content=chunk["content"],
                    artifact_type=source_type,
                    section=chunk.get("section"),
                    chunk_index=chunk.get("chunk_index", 0),
                    score=adjusted_score,
                    metadata=chunk.get("metadata", {})
                )
                evidence_list.append(evidence)
            
            # Sort by adjusted score
            evidence_list.sort(key=lambda x: x.score, reverse=True)
            
            # Return top_k after re-ranking
            final_list = evidence_list[:top_k]
            
            logger.info(f"🔍 PITCH RAG: Returning {len(final_list)} evidence items after re-ranking")
            for i, ev in enumerate(final_list[:3]):
                logger.info(f"  {i+1}. {ev.artifact_type} (score={ev.score:.3f}): {ev.content[:60]}...")
            
            return final_list
            
        except Exception as e:
            logger.error(f"Error retrieving evidence: {e}")
            return []
    
    def format_evidence_for_prompt(
        self,
        evidence_list: List[ProjectEvidence],
        max_chars: int = 8000
    ) -> str:
        """
        Format evidence list as a text block for prompts.
        
        Args:
            evidence_list: List of ProjectEvidence objects
            max_chars: Maximum characters for the block
            
        Returns:
            Formatted text block with evidence
        """
        if not evidence_list:
            return "No project evidence available."
        
        lines = []
        total_chars = 0
        
        for i, ev in enumerate(evidence_list, 1):
            # Format: [P{i}] ({artifact_type}): {content}
            entry = f"[P{i}] ({ev.artifact_type}): {ev.content}"
            
            if total_chars + len(entry) > max_chars:
                lines.append(f"... ({len(evidence_list) - i + 1} more items truncated)")
                break
            
            lines.append(entry)
            total_chars += len(entry) + 1
        
        return "\n\n".join(lines)
    
    def create_citations_from_evidence(
        self,
        evidence_list: List[ProjectEvidence],
        citations_used: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create citation objects from evidence list.
        
        Args:
            evidence_list: Full list of evidence that was provided to the model
            citations_used: List of citation IDs used by the model (e.g., ["P1", "P3"])
            
        Returns:
            List of citation dicts for the used citations
        """
        citations = []
        
        for cite_id in citations_used:
            if not cite_id.startswith("P"):
                continue
            
            try:
                idx = int(cite_id[1:]) - 1  # P1 -> index 0
                if 0 <= idx < len(evidence_list):
                    ev = evidence_list[idx]
                    citations.append({
                        "id": cite_id,
                        "type": "project",
                        "artifact_ref": ev.artifact_type,
                        "artifact_version": ev.metadata.get("version"),
                        "chunk_ref": ev.chunk_id,
                        "snippet": ev.content[:200] + "..." if len(ev.content) > 200 else ev.content,
                    })
            except (ValueError, IndexError):
                logger.warning(f"Invalid citation ID: {cite_id}")
        
        return citations
