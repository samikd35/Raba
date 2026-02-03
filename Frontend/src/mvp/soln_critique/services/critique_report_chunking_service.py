"""
Solution Critique Report Chunking Service

Chunks and embeds the generated critique report for chat functionality.
Stores critique chunks in the vector database for RAG retrieval.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.mint.api.services.ai.embedding_service import get_embedding_service
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter

logger = logging.getLogger(__name__)


class CritiqueReportChunkingService:
    """
    Service for chunking and embedding solution critique reports.
    
    Processes the final JSON critique report and creates searchable chunks
    that can be retrieved during chat interactions.
    """
    
    def __init__(self):
        """Initialize critique report chunking service."""
        self.db_adapter = MVPDatabaseAdapter(use_service_role=True)
        self.embedding_service = get_embedding_service()
        
        # Chunking configuration
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
    
    async def chunk_and_embed_report(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Chunk and embed the solution critique report for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Result with chunk count and storage status
        """
        try:
            logger.info(f"📊 CRITIQUE CHUNKING: Starting for project {project_id}")
            
            # Load the critique report from database
            project_data = self.db_adapter.get_project(project_id, tenant_id)
            
            if not project_data:
                return {
                    "success": False,
                    "error": "no_project",
                    "message": "Project not found"
                }
            
            critique_data = project_data.get('soln_critique_data')
            
            if not critique_data:
                return {
                    "success": False,
                    "error": "no_critique",
                    "message": "No solution critique found for this project"
                }
            
            # Check if critique is completed
            if critique_data.get('status') != 'completed':
                return {
                    "success": False,
                    "error": "critique_not_complete",
                    "message": f"Critique status is '{critique_data.get('status')}', not completed"
                }
            
            critique_report = critique_data.get('critique_report')
            
            if not critique_report:
                return {
                    "success": False,
                    "error": "no_report",
                    "message": "No critique report found in critique data"
                }
            
            logger.info(f"✅ CRITIQUE CHUNKING: Loaded critique report")
            
            # Convert critique report to text chunks
            chunks = await self._create_report_chunks(critique_report)
            
            logger.info(f"✅ CRITIQUE CHUNKING: Created {len(chunks)} chunks")
            
            # Generate embeddings for chunks
            chunks_with_embeddings = await self._generate_embeddings(chunks)
            
            logger.info(f"✅ CRITIQUE CHUNKING: Generated embeddings for {len(chunks_with_embeddings)} chunks")
            
            # Store chunks in vector database
            success = await self._store_critique_chunks(
                project_id=project_id,
                tenant_id=tenant_id,
                chunks=chunks_with_embeddings
            )
            
            if success:
                logger.info(f"✅ CRITIQUE CHUNKING: Successfully stored {len(chunks_with_embeddings)} chunks")
                return {
                    "success": True,
                    "message": f"Successfully chunked and embedded critique report with {len(chunks_with_embeddings)} chunks",
                    "chunk_count": len(chunks_with_embeddings),
                    "project_id": project_id
                }
            else:
                return {
                    "success": False,
                    "error": "storage_error",
                    "message": "Failed to store critique chunks in vector database"
                }
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHUNKING: Error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": "chunking_error",
                "message": f"Failed to chunk and embed critique report: {str(e)}"
            }
    
    async def _create_report_chunks(
        self,
        critique_report: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create text chunks from critique report.
        
        Chunks are created from:
        - Executive summary
        - Each dimension critique (5 dimensions)
        - Prioritized actions
        - Sources section
        """
        chunks = []
        chunk_index = 0
        
        try:
            # 1. Chunk executive summary
            executive_summary = critique_report.get("executive_summary", {})
            
            if executive_summary:
                summary_text = self._format_executive_summary(executive_summary)
                summary_chunks = self._split_text_into_chunks(summary_text)
                
                for i, chunk_text in enumerate(summary_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": "executive_summary",
                        "metadata": {
                            "section_type": "executive_summary",
                            "chunk_position": i,
                            "total_chunks_in_section": len(summary_chunks)
                        }
                    })
                    chunk_index += 1
            
            # 2. Chunk each dimension critique
            critiques_by_dimension = critique_report.get("critiques_by_dimension", {})
            
            for dimension, dimension_data in critiques_by_dimension.items():
                dimension_text = self._format_dimension_critiques(dimension, dimension_data)
                dimension_chunks = self._split_text_into_chunks(dimension_text)
                
                for i, chunk_text in enumerate(dimension_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": f"dimension_{dimension}",
                        "metadata": {
                            "section_type": "dimension_critique",
                            "dimension": dimension,
                            "dimension_severity": dimension_data.get("dimension_severity", "low"),
                            "chunk_position": i,
                            "total_chunks_in_section": len(dimension_chunks)
                        }
                    })
                    chunk_index += 1
            
            # 3. Chunk all critiques section (detailed)
            all_critiques = critique_report.get("all_critiques", [])
            
            for critique_idx, critique in enumerate(all_critiques):
                critique_text = self._format_single_critique(critique, critique_idx + 1)
                critique_chunks = self._split_text_into_chunks(critique_text)
                
                for i, chunk_text in enumerate(critique_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": f"critique_{critique_idx + 1}",
                        "metadata": {
                            "section_type": "individual_critique",
                            "critique_id": critique.get("critique_id"),
                            "dimension": critique.get("dimension"),
                            "severity": critique.get("severity", "medium"),
                            "chunk_position": i,
                            "total_chunks_in_section": len(critique_chunks)
                        }
                    })
                    chunk_index += 1
            
            # 4. Chunk prioritized actions
            prioritized_actions = critique_report.get("prioritized_actions", {})
            
            if prioritized_actions:
                actions_text = self._format_prioritized_actions(prioritized_actions)
                actions_chunks = self._split_text_into_chunks(actions_text)
                
                for i, chunk_text in enumerate(actions_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": "prioritized_actions",
                        "metadata": {
                            "section_type": "prioritized_actions",
                            "chunk_position": i,
                            "total_chunks_in_section": len(actions_chunks)
                        }
                    })
                    chunk_index += 1
            
            # 5. Chunk sources section
            sources = critique_report.get("sources", [])
            
            if sources:
                sources_text = self._format_sources(sources)
                sources_chunks = self._split_text_into_chunks(sources_text)
                
                for i, chunk_text in enumerate(sources_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": "sources",
                        "metadata": {
                            "section_type": "sources",
                            "chunk_position": i,
                            "total_chunks_in_section": len(sources_chunks)
                        }
                    })
                    chunk_index += 1
            
            logger.info(f"✅ CRITIQUE CHUNKING: Created {len(chunks)} chunks from report")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHUNKING: Error creating chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _format_executive_summary(self, executive_summary: Dict[str, Any]) -> str:
        """Format executive summary as text."""
        lines = [
            "=== SOLUTION CRITIQUE - EXECUTIVE SUMMARY ===",
            "",
            f"Overall Viability: {executive_summary.get('overall_viability', 'Unknown').upper()}",
            f"Overall Confidence: {executive_summary.get('overall_confidence', 0):.2f}",
            f"Total Critiques: {executive_summary.get('total_critiques', 0)}",
            ""
        ]
        
        # Add top 3 risks
        top_risks = executive_summary.get("top_3_risks", [])
        if top_risks:
            lines.append("TOP 3 RISKS:")
            for risk in top_risks:
                lines.append(f"- {risk}")
            lines.append("")
        
        # Add recommendation
        recommendation = executive_summary.get("recommendation", "")
        if recommendation:
            lines.append("OVERALL RECOMMENDATION:")
            lines.append(recommendation)
            lines.append("")
        
        # Add key insights
        key_insights = executive_summary.get("key_insights", [])
        if key_insights:
            lines.append("KEY INSIGHTS:")
            for insight in key_insights:
                lines.append(f"- {insight}")
            lines.append("")
        
        # Add severity distribution
        severity_dist = executive_summary.get("severity_distribution", {})
        if severity_dist:
            lines.append("SEVERITY DISTRIBUTION:")
            lines.append(f"- High: {severity_dist.get('high', 0)}")
            lines.append(f"- Medium: {severity_dist.get('medium', 0)}")
            lines.append(f"- Low: {severity_dist.get('low', 0)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_dimension_critiques(self, dimension: str, dimension_data: Dict[str, Any]) -> str:
        """Format dimension critiques as text."""
        lines = [
            f"=== {dimension.replace('_', ' ').upper()} CRITIQUES ===",
            "",
            f"Dimension Severity: {dimension_data.get('dimension_severity', 'Unknown').upper()}",
            f"Summary: {dimension_data.get('summary', 'No summary available')}",
            f"Total Citations: {dimension_data.get('citation_count', 0)}",
            ""
        ]
        
        # Add each critique in this dimension
        critiques = dimension_data.get("critiques", [])
        for critique in critiques:
            lines.append(f"--- CRITIQUE: {critique.get('title', 'Untitled')} ---")
            lines.append(f"Severity: {critique.get('severity', 'unknown').upper()}")
            lines.append(f"Confidence: {critique.get('confidence', 0):.2f}")
            lines.append("")
            lines.append("Problem:")
            lines.append(critique.get('problem', 'No problem description'))
            lines.append("")
            lines.append("Impact:")
            lines.append(critique.get('impact', 'No impact description'))
            lines.append("")
            
            # Add suggestions
            suggestions = critique.get('suggestions', [])
            if suggestions:
                lines.append("Suggestions:")
                for sug in suggestions:
                    lines.append(f"  [{sug.get('priority', 'unknown')}] {sug.get('action', 'No action')}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_single_critique(self, critique: Dict[str, Any], index: int) -> str:
        """Format individual critique as text."""
        lines = [
            f"=== CRITIQUE #{index}: {critique.get('title', 'Untitled')} ===",
            "",
            f"ID: {critique.get('critique_id', 'Unknown')}",
            f"Dimension: {critique.get('dimension', 'Unknown').replace('_', ' ').title()}",
            f"Severity: {critique.get('severity', 'unknown').upper()}",
            f"Confidence: {critique.get('confidence', 0):.2f}",
            f"Citations: {critique.get('citation_count', 0)}",
            ""
        ]
        
        # Problem description
        lines.append("PROBLEM:")
        lines.append(critique.get('problem', 'No problem description'))
        lines.append("")
        
        # Impact
        lines.append("IMPACT:")
        lines.append(critique.get('impact', 'No impact description'))
        lines.append("")
        
        # Suggestions
        suggestions = critique.get('suggestions', [])
        if suggestions:
            lines.append("SUGGESTED ACTIONS:")
            for sug in suggestions:
                lines.append(f"  Type: {sug.get('type', 'unknown')}")
                lines.append(f"  Priority: {sug.get('priority', 'unknown')}")
                lines.append(f"  Action: {sug.get('action', 'No action')}")
                lines.append(f"  Rationale: {sug.get('rationale', 'No rationale')}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_prioritized_actions(self, prioritized_actions: Dict[str, List]) -> str:
        """Format prioritized actions as text."""
        lines = [
            "=== PRIORITIZED ACTIONS ===",
            ""
        ]
        
        # Immediate actions
        immediate = prioritized_actions.get("immediate", [])
        if immediate:
            lines.append("IMMEDIATE PRIORITY (Must Address Now):")
            for action in immediate:
                lines.append(f"- {action.get('action', 'No action')}")
                lines.append(f"  Impact: {action.get('impact', 'unknown')}, Effort: {action.get('effort', 'unknown')}")
            lines.append("")
        
        # Short-term actions
        short_term = prioritized_actions.get("short_term", [])
        if short_term:
            lines.append("SHORT-TERM PRIORITY (Address Soon):")
            for action in short_term:
                lines.append(f"- {action.get('action', 'No action')}")
                lines.append(f"  Impact: {action.get('impact', 'unknown')}, Effort: {action.get('effort', 'unknown')}")
            lines.append("")
        
        # Long-term actions
        long_term = prioritized_actions.get("long_term", [])
        if long_term:
            lines.append("LONG-TERM PRIORITY (Future Consideration):")
            for action in long_term:
                lines.append(f"- {action.get('action', 'No action')}")
                lines.append(f"  Impact: {action.get('impact', 'unknown')}, Effort: {action.get('effort', 'unknown')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Format sources as text."""
        lines = [
            "=== RESEARCH SOURCES ===",
            "",
            f"Total Sources: {len(sources)}",
            ""
        ]
        
        # Group sources by type
        web_sources = [s for s in sources if s.get('type') == 'web']
        bmc_sources = [s for s in sources if s.get('type') == 'bmc']
        vpc_sources = [s for s in sources if s.get('type') == 'vpc']
        vps_sources = [s for s in sources if s.get('type') == 'vps']
        
        if web_sources:
            lines.append(f"WEB RESEARCH ({len(web_sources)} sources):")
            for source in web_sources[:10]:  # Limit to first 10
                lines.append(f"[{source.get('id')}] {source.get('title', 'Untitled')}")
                lines.append(f"    URL: {source.get('url', 'No URL')}")
            lines.append("")
        
        if bmc_sources:
            lines.append(f"BUSINESS MODEL CANVAS ({len(bmc_sources)} sources):")
            for source in bmc_sources:
                lines.append(f"[{source.get('id')}] {source.get('title', source.get('field', 'Unknown field'))}")
                if source.get('url'):
                    lines.append(f"    URL: {source.get('url')}")
            lines.append("")
        
        if vpc_sources:
            lines.append(f"VALUE PROPOSITION CANVAS ({len(vpc_sources)} sources):")
            for source in vpc_sources:
                lines.append(f"[{source.get('id')}] {source.get('title', source.get('field', 'Unknown field'))}")
                if source.get('url'):
                    lines.append(f"    URL: {source.get('url')}")
            lines.append("")
        
        if vps_sources:
            lines.append(f"VALUE PROPOSITION STATEMENT ({len(vps_sources)} sources):")
            for source in vps_sources:
                lines.append(f"[{source.get('id')}] {source.get('title', source.get('field', 'Unknown field'))}")
                if source.get('url'):
                    lines.append(f"    URL: {source.get('url')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If not the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings in the overlap region
                search_start = max(start, end - self.chunk_overlap)
                sentence_end = text.rfind(". ", search_start, end)
                
                if sentence_end != -1 and sentence_end > start:
                    end = sentence_end + 1  # Include the period
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
    
    async def _generate_embeddings(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for chunks."""
        import asyncio
        
        try:
            logger.info(f"🔄 CRITIQUE CHUNKING: Starting embedding generation for {len(chunks)} chunks...")
            
            # Extract text content from chunks
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings using embedding service with timeout
            try:
                embeddings = await asyncio.wait_for(
                    self.embedding_service.generate_embeddings(texts),
                    timeout=120.0  # 2 minute timeout for 60 chunks
                )
                logger.info(f"✅ CRITIQUE CHUNKING: Embedding API returned {len(embeddings) if embeddings else 0} embeddings")
            except asyncio.TimeoutError:
                logger.error(f"❌ CRITIQUE CHUNKING: Embedding generation timed out after 120 seconds")
                return []
            
            if not embeddings:
                logger.error(f"❌ CRITIQUE CHUNKING: Embedding service returned empty result")
                return []
            
            # Add embeddings to chunks
            valid_count = 0
            for i, chunk in enumerate(chunks):
                if i < len(embeddings) and embeddings[i] is not None:
                    chunk["embedding"] = embeddings[i]
                    valid_count += 1
                else:
                    logger.warning(f"⚠️ CRITIQUE CHUNKING: Missing/null embedding for chunk {i}")
                    chunk["embedding"] = []
            
            logger.info(f"✅ CRITIQUE CHUNKING: {valid_count}/{len(chunks)} chunks have valid embeddings")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHUNKING: Error generating embeddings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _store_critique_chunks(
        self,
        project_id: str,
        tenant_id: str,
        chunks: List[Dict[str, Any]]
    ) -> bool:
        """Store critique chunks in vector database."""
        try:
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            from src.mint.api.system.core.supabase_client import get_service_role_client
            from src.mint.api.report.report_models import ReportChunkWithEmbedding
            
            chunk_service = get_chunk_storage_service()
            supabase = get_service_role_client()  # Use service role for document creation
            
            # Ensure document entry exists (required for foreign key constraint)
            await self._ensure_document_exists(project_id, tenant_id, supabase)
            
            # Get all existing chunks for this project
            existing_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            # Delete ONLY solution_critique chunks (preserve other types)
            if existing_chunks:
                critique_chunk_ids = [
                    chunk['id'] for chunk in existing_chunks 
                    if chunk.get('metadata', {}).get('source_type') == 'solution_critique'
                ]
                
                if critique_chunk_ids:
                    logger.info(f"🗑️ CRITIQUE STORAGE: Deleting {len(critique_chunk_ids)} old solution_critique chunks")
                    for chunk_id in critique_chunk_ids:
                        supabase.client.table("chunks").delete().eq("id", chunk_id).execute()
                    logger.info(f"✅ DELETED: Removed {len(critique_chunk_ids)} old chunks")
            
            # Check how many chunks have valid embeddings
            chunks_with_embeddings = [c for c in chunks if c.get("embedding")]
            logger.info(f"💾 CRITIQUE STORAGE: {len(chunks_with_embeddings)}/{len(chunks)} chunks have embeddings")
            
            if not chunks_with_embeddings:
                logger.error(f"❌ CRITIQUE STORAGE: No chunks have valid embeddings, cannot store")
                return False
            
            logger.info(f"💾 CRITIQUE STORAGE: Storing {len(chunks_with_embeddings)} solution_critique chunks")
            
            # Find max chunk_index from ALL existing chunks
            max_index = -1
            if existing_chunks:
                max_index = max(c.get('chunk_index', -1) for c in existing_chunks)
            
            logger.info(f"📊 MAX CHUNK INDEX (all sources): {max_index}, starting new chunks at {max_index + 1}")
            
            # Prepare chunks for storage
            batch_size = 50
            success_count = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_data = []
                
                for idx, chunk in enumerate(batch):
                    if not chunk.get("embedding"):
                        continue
                    
                    # Use chunk_index AFTER all existing chunks
                    new_chunk_index = max_index + 1 + (i + idx)
                    
                    # Prepare metadata
                    metadata = {
                        "source_type": "solution_critique",
                        "section": chunk["section"],
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "created_at": datetime.utcnow().isoformat(),
                        **chunk.get("metadata", {})
                    }
                    
                    batch_data.append({
                        'doc_id': project_id,
                        'chunk_index': new_chunk_index,
                        'content': chunk["content"],
                        'embedding': chunk["embedding"],
                        'metadata': metadata
                    })
                
                if batch_data:
                    try:
                        result = supabase.client.table('chunks').insert(batch_data).execute()
                        success_count += len(batch_data)
                        logger.info(f"✅ Inserted batch {i//batch_size + 1}: {len(batch_data)} chunks")
                    except Exception as e:
                        logger.error(f"❌ Failed to insert batch: {e}")
                        return False
            
            logger.info(f"✅ CRITIQUE STORAGE: Successfully inserted {success_count} solution_critique chunks")
            
            # Verify storage
            final_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            after_distribution = {}
            for chunk in final_chunks:
                st = chunk.get('metadata', {}).get('source_type', 'unknown')
                after_distribution[st] = after_distribution.get(st, 0) + 1
            logger.info(f"📊 AFTER INSERTION: {after_distribution}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHUNKING: Error storing chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _ensure_document_exists(
        self,
        project_id: str,
        tenant_id: str,
        supabase
    ) -> None:
        """
        Ensure a document entry exists for the project.
        
        The chunks table has a foreign key constraint (doc_id -> documents.id).
        For bootstrap projects or projects without prior document entries,
        we need to create a document entry before storing chunks.
        """
        try:
            # Check if document already exists
            result = supabase.client.table("documents") \
                .select("id") \
                .eq("id", project_id) \
                .execute()
            
            if result.data:
                logger.info(f"✅ CRITIQUE STORAGE: Document entry exists for project {project_id}")
                return
            
            # Get project info for document creation
            project_data = self.db_adapter.get_project(project_id, tenant_id)
            project_name = project_data.get('name', 'Solution Critique') if project_data else 'Solution Critique'
            user_id = project_data.get('user_id') if project_data else None
            
            # Create document entry with project_id as the document id
            logger.info(f"📄 CRITIQUE STORAGE: Creating document entry for project {project_id}")
            
            # Note: documents.project_id has FK to 'projects' table, not 'vmp_projects'
            # Set project_id to NULL but store vmp_project_id in metadata
            doc_data = {
                "id": project_id,  # Use project_id as document id for chunks FK
                "tenant_id": tenant_id,
                "project_id": None,  # Cannot reference vmp_projects from documents.project_id FK
                "source_type": "solution_critique",
                "title": f"Solution Critique - {project_name}",
                "created_by": user_id,
                "metadata": {
                    "vmp_project_id": project_id,  # Store actual VMP project reference here
                    "created_for": "critique_chunks",
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            insert_result = supabase.client.table("documents").insert(doc_data).execute()
            
            if insert_result.data:
                logger.info(f"✅ CRITIQUE STORAGE: Created document entry for project {project_id}")
            else:
                logger.warning(f"⚠️ CRITIQUE STORAGE: Document insert returned no data")
                
        except Exception as e:
            # If document creation fails (e.g., already exists due to race condition), log but continue
            error_str = str(e)
            if "duplicate key" in error_str.lower() or "23505" in error_str:
                logger.info(f"✅ CRITIQUE STORAGE: Document already exists (concurrent creation)")
            else:
                logger.error(f"❌ CRITIQUE STORAGE: Error creating document: {e}")
                raise
