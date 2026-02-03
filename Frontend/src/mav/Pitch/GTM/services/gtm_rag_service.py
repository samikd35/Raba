"""
GTM RAG Service

Handles vector similarity search over project chunks for GTM strategy generation.
Provides step-aware retrieval with artifact type filtering and version preference.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.mint.api.system.core.supabase_client import get_service_role_client
from src.mint.api.services.ai.embedding_service import EmbeddingService, get_embedding_service

from ..models import (
    ProjectEvidence,
    DEFAULT_GTM_CONFIG,
    GTM_STEP_ARTIFACT_HINTS,
    VERSION_PRIORITY_BOOST,
    SECTION_PENALTY,
)

logger = logging.getLogger(__name__)

# Retry configuration for embedding calls
MAX_EMBEDDING_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


class GTMRAGService:
    """
    Service for retrieving project evidence for GTM strategy steps.
    
    Uses the existing chunks table populated by VMPProjectChunkingService.
    Provides step-aware retrieval with artifact type filtering and re-ranking.
    Prioritizes v2 artifacts over v1 for most recent/authoritative content.
    """
    
    CHUNKS_TABLE = "chunks"
    
    def __init__(self):
        """Initialize RAG service with embedding service and DB client."""
        self.supabase = get_service_role_client()
        self.embedding_service: EmbeddingService = get_embedding_service()
        logger.info("✅ GTMRAGService initialized")
    
    async def retrieve_for_step(
        self,
        query: str,
        project_id: str,
        tenant_id: str,
        step_type: str,
        artifact_hints: Optional[List[str]] = None,
        top_k: int = None,
        similarity_threshold: float = 0.0
    ) -> List[ProjectEvidence]:
        """
        Retrieve relevant project evidence for a GTM step.
        
        Args:
            query: Search query (will be embedded)
            project_id: VMP project ID (strict filter)
            tenant_id: Tenant ID (strict filter)
            step_type: GTM step type (problem, audience_icp, etc.)
            artifact_hints: Optional override for artifact types to search
            top_k: Max chunks to return (default from config)
            similarity_threshold: Min relevance score (default 0.0)
            
        Returns:
            List of ProjectEvidence objects sorted by relevance (v2 preferred)
        """
        top_k = top_k or DEFAULT_GTM_CONFIG.rag_top_k
        
        # Get artifact hints for this step if not provided
        if artifact_hints is None:
            artifact_hints = GTM_STEP_ARTIFACT_HINTS.get(step_type, [])
        
        try:
            # Step 1: Generate query embedding with retry
            logger.info(f"🔍 GTM RAG: Generating embedding for step '{step_type}': {query[:50]}...")
            query_embedding = await self._generate_embedding_with_retry(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Step 2: Execute vector similarity search using RPC function
            logger.info(f"🔍 GTM RAG: Searching chunks for project {project_id}, step={step_type}")
            
            # Use the match_project_chunks function
            result = self.supabase.client.rpc(
                "match_project_chunks",
                {
                    "query_embedding": query_embedding,
                    "p_project_id": project_id,
                    "p_tenant_id": tenant_id,
                    "match_count": top_k * 3,  # Get more to filter and re-rank
                    "match_threshold": similarity_threshold
                }
            ).execute()
            
            logger.info(f"🔍 GTM RAG: RPC returned {len(result.data) if result.data else 0} chunks")
            
            if not result.data:
                logger.info("🔍 GTM RAG: No matching chunks found, trying fallback")
                return await self._fallback_retrieval(
                    query, project_id, tenant_id, top_k, artifact_hints
                )
            
            # Step 3: Filter by artifact hints if provided
            filtered_chunks = result.data
            if artifact_hints:
                filtered_chunks = []
                for chunk in result.data:
                    source_type = chunk.get("source_type") or chunk.get("metadata", {}).get("source_type", "unknown")
                    # Include if source_type matches any hint or is a close variant
                    if any(hint in source_type or source_type in hint for hint in artifact_hints):
                        filtered_chunks.append(chunk)
                
                # If filtering too aggressive, fall back to all results
                if len(filtered_chunks) < 3 and len(result.data) >= 3:
                    logger.info(f"🔍 GTM RAG: Artifact filter too strict ({len(filtered_chunks)} results), using all {len(result.data)}")
                    filtered_chunks = result.data
            
            # Step 4: Convert to ProjectEvidence with re-ranking (v2 preferred)
            evidence_list = []
            for chunk in filtered_chunks:
                source_type = chunk.get("source_type") or chunk.get("metadata", {}).get("source_type", "unknown")
                section_type = chunk.get("metadata", {}).get("section_type", "")
                
                # Calculate adjusted score with version priority
                base_score = float(chunk.get("similarity", 0.5))
                boost = VERSION_PRIORITY_BOOST.get(source_type, 0)
                penalty = SECTION_PENALTY.get(section_type, 0)
                adjusted_score = base_score + boost + penalty
                
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
            
            # Re-sort by adjusted score and take top_k
            evidence_list.sort(key=lambda x: x.score, reverse=True)
            evidence_list = evidence_list[:top_k]
            
            logger.info(f"✅ GTM RAG: Retrieved {len(evidence_list)} evidence chunks for step '{step_type}' (re-ranked with v2 priority)")
            
            # Log artifact type distribution
            artifact_counts = {}
            for e in evidence_list:
                artifact_counts[e.artifact_type] = artifact_counts.get(e.artifact_type, 0) + 1
            logger.info(f"🔍 GTM RAG: Artifact distribution: {artifact_counts}")
            
            return evidence_list
            
        except Exception as e:
            logger.error(f"❌ GTM RAG retrieval error: {e}")
            return await self._fallback_retrieval(
                query, project_id, tenant_id, top_k, artifact_hints
            )
    
    async def _generate_embedding_with_retry(self, text: str) -> Optional[List[float]]:
        """Generate embedding with exponential backoff retry."""
        for attempt in range(MAX_EMBEDDING_RETRIES):
            try:
                embedding = await self.embedding_service.generate_single_embedding(text)
                if embedding:
                    return embedding
            except Exception as e:
                logger.warning(f"⚠️ Embedding attempt {attempt + 1} failed: {e}")
                if attempt < MAX_EMBEDDING_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        logger.error("❌ All embedding attempts failed")
        return None
    
    async def _fallback_retrieval(
        self,
        query: str,
        project_id: str,
        tenant_id: str,
        top_k: int,
        artifact_hints: Optional[List[str]] = None
    ) -> List[ProjectEvidence]:
        """
        Fallback retrieval using direct query if RPC fails.
        
        Fetches chunks directly from the chunks table with project filter.
        """
        try:
            logger.info(f"🔍 GTM RAG: Using fallback direct query for project {project_id}")
            
            # Direct query to chunks table
            query_builder = self.supabase.client.table(self.CHUNKS_TABLE)\
                .select("id, content, metadata, chunk_index")\
                .eq("doc_id", project_id)\
                .limit(top_k * 2)
            
            result = query_builder.execute()
            
            if not result.data:
                logger.info("🔍 GTM RAG: Fallback also returned no results")
                return []
            
            # Convert to ProjectEvidence
            evidence_list = []
            for chunk in result.data:
                metadata = chunk.get("metadata", {})
                source_type = metadata.get("source_type", "unknown")
                
                # Apply artifact hint filtering
                if artifact_hints:
                    if not any(hint in source_type or source_type in hint for hint in artifact_hints):
                        continue
                
                # Calculate score (fallback has no similarity, use priority boost only)
                base_score = 0.5
                boost = VERSION_PRIORITY_BOOST.get(source_type, 0)
                adjusted_score = base_score + boost
                
                evidence = ProjectEvidence(
                    chunk_id=str(chunk["id"]),
                    content=chunk["content"],
                    artifact_type=source_type,
                    section=metadata.get("section"),
                    chunk_index=chunk.get("chunk_index", 0),
                    score=adjusted_score,
                    metadata=metadata
                )
                evidence_list.append(evidence)
            
            # Sort by score and limit
            evidence_list.sort(key=lambda x: x.score, reverse=True)
            evidence_list = evidence_list[:top_k]
            
            logger.info(f"✅ GTM RAG: Fallback retrieved {len(evidence_list)} chunks")
            return evidence_list
            
        except Exception as e:
            logger.error(f"❌ GTM RAG fallback error: {e}")
            return []
    
    def format_evidence_for_context(
        self,
        evidence_list: List[ProjectEvidence],
        max_chars: int = 6000
    ) -> str:
        """
        Format project evidence as text for LLM context.
        
        Args:
            evidence_list: List of ProjectEvidence
            max_chars: Maximum total characters
            
        Returns:
            Formatted text with evidence blocks and citation markers
        """
        if not evidence_list:
            return "No project evidence available."
        
        lines = []
        total_chars = 0
        
        for i, evidence in enumerate(evidence_list, 1):
            ref_id = f"P{i}"
            
            # Determine version indicator
            version_indicator = ""
            if "_v2" in evidence.artifact_type:
                version_indicator = " [v2 - LATEST]"
            elif "_v1" in evidence.artifact_type:
                version_indicator = " [v1]"
            
            header = f"[{ref_id}] ({evidence.artifact_type}{version_indicator}) Score: {evidence.score:.2f}"
            content = evidence.content[:800]  # Truncate long content
            
            block = f"{header}\n{content}\n"
            
            if total_chars + len(block) > max_chars:
                break
            
            lines.append(block)
            total_chars += len(block)
        
        return "\n".join(lines)
    
    def create_citations_from_evidence(
        self,
        evidence_list: List[ProjectEvidence],
        citations_used: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create citation objects from evidence that was actually used.
        
        Args:
            evidence_list: All retrieved evidence
            citations_used: List of citation IDs used (P1, P2, etc.)
            
        Returns:
            List of citation dicts for the used evidence
        """
        citations = []
        
        for i, evidence in enumerate(evidence_list, 1):
            ref_id = f"P{i}"
            if not citations_used or ref_id in citations_used:
                # Determine version from artifact type
                version = None
                if "_v2" in evidence.artifact_type:
                    version = 2
                elif "_v1" in evidence.artifact_type:
                    version = 1
                
                citations.append({
                    "id": ref_id,
                    "type": "project",
                    "artifact_ref": evidence.artifact_type,
                    "artifact_version": version,
                    "chunk_ref": evidence.chunk_id,
                    "snippet": evidence.content[:200] if evidence.content else ""
                })
        
        return citations


# Singleton instance
_gtm_rag_service: Optional[GTMRAGService] = None


def get_gtm_rag_service() -> GTMRAGService:
    """Get or create singleton GTMRAGService instance."""
    global _gtm_rag_service
    if _gtm_rag_service is None:
        _gtm_rag_service = GTMRAGService()
    return _gtm_rag_service
