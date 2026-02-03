"""
Report Chunking Service

Chunks and embeds the generated analysis report for chat functionality.
Stores report chunks in the vector database for RAG retrieval.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..adapters.vector_adapter import AnalysisAgentVectorAdapter
from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from src.mint.api.services.ai.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class ReportChunkingService:
    """
    Service for chunking and embedding analysis reports.
    
    Processes the final JSON report and creates searchable chunks
    that can be retrieved during chat interactions.
    """
    
    def __init__(self):
        """Initialize report chunking service."""
        self.vector_adapter = AnalysisAgentVectorAdapter()
        self.db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.embedding_service = get_embedding_service()
        
        # Chunking configuration
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        
    async def chunk_and_embed_report(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chunk and embed the analysis report for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            persona_id: Optional persona ID for multi-persona projects
            
        Returns:
            Result with chunk count and storage status
        """
        try:
            persona_tag = f" for persona '{persona_id}'" if persona_id else ""
            logger.info(f"📊 REPORT CHUNKING: Starting for project {project_id}{persona_tag}")
            
            # Load the analysis report from database
            analysis_data = await self.db_adapter.get_analysis_data(project_id, tenant_id)
            
            if not analysis_data:
                return {
                    "success": False,
                    "error": "no_report",
                    "message": "No analysis report found for this project"
                }
            
            # 🎭 MULTI-PERSONA: Get the structured report for this persona
            if persona_id and "personas" in analysis_data:
                # Multi-persona format
                persona_data = analysis_data.get("personas", {}).get(persona_id)
                if not persona_data:
                    return {
                        "success": False,
                        "error": "no_persona_report",
                        "message": f"No analysis report found for persona '{persona_id}'"
                    }
                structured_report = persona_data.get("structured_report")
                logger.info(f"🎭 REPORT CHUNKING: Loading report for persona '{persona_id}'")
            else:
                # Legacy single-persona format
                structured_report = analysis_data.get("structured_report")
                logger.info(f"📊 REPORT CHUNKING: Loading report (single-persona mode)")
            
            if not structured_report:
                return {
                    "success": False,
                    "error": "no_structured_report",
                    "message": "No structured report found in analysis data"
                }
            
            logger.info(f"✅ REPORT CHUNKING: Loaded structured report")
            logger.info(f"🔍 REPORT CHUNKING: Report type: {type(structured_report)}")
            
            # Debug: Print the actual structure
            if isinstance(structured_report, dict):
                logger.info(f"🔍 REPORT CHUNKING: Dict keys: {list(structured_report.keys())}")
                for key, value in structured_report.items():
                    logger.info(f"🔍 REPORT CHUNKING: Key '{key}' -> type: {type(value)}")
                    if isinstance(value, list) and len(value) > 0:
                        logger.info(f"🔍 REPORT CHUNKING: First item in '{key}': {type(value[0])}")
            elif isinstance(structured_report, list):
                logger.info(f"🔍 REPORT CHUNKING: List with {len(structured_report)} items")
                if len(structured_report) > 0:
                    logger.info(f"🔍 REPORT CHUNKING: First item type: {type(structured_report[0])}")
            
            # Handle both dict and list formats
            if isinstance(structured_report, list):
                # If it's a list, wrap it in a dict structure
                structured_report = {"assumptions": structured_report}
                logger.info(f"🔄 REPORT CHUNKING: Converted list to dict format")
            
            # Convert structured report to text chunks
            chunks = await self._create_report_chunks(structured_report)
            
            logger.info(f"✅ REPORT CHUNKING: Created {len(chunks)} chunks")
            
            # Generate embeddings for chunks
            chunks_with_embeddings = await self._generate_embeddings(chunks)
            
            logger.info(f"✅ REPORT CHUNKING: Generated embeddings for {len(chunks_with_embeddings)} chunks")
            
            # Store chunks in vector database with persona_id
            success = await self._store_report_chunks(
                project_id=project_id,
                tenant_id=tenant_id,
                chunks=chunks_with_embeddings,
                persona_id=persona_id
            )
            
            if success:
                persona_tag = f" for persona '{persona_id}'" if persona_id else ""
                logger.info(f"✅ REPORT CHUNKING: Successfully stored {len(chunks_with_embeddings)} chunks{persona_tag}")
                return {
                    "success": True,
                    "message": f"Successfully chunked and embedded report with {len(chunks_with_embeddings)} chunks{persona_tag}",
                    "chunk_count": len(chunks_with_embeddings),
                    "project_id": project_id,
                    "persona_id": persona_id
                }
            else:
                return {
                    "success": False,
                    "error": "storage_error",
                    "message": "Failed to store report chunks in vector database"
                }
            
        except Exception as e:
            logger.error(f"❌ REPORT CHUNKING: Error: {e}")
            return {
                "success": False,
                "error": "chunking_error",
                "message": f"Failed to chunk and embed report: {str(e)}"
            }
    
    async def _create_report_chunks(
        self,
        structured_report: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create text chunks from structured report.
        
        Chunks are created from:
        - Executive summary
        - Each assumption analysis
        - Key findings
        - Recommendations
        """
        chunks = []
        chunk_index = 0
        
        try:
            # 1. Chunk executive summary
            metadata = structured_report.get("metadata", {})
            executive_summary = structured_report.get("executive_summary", {})
            
            if executive_summary:
                summary_text = self._format_executive_summary(executive_summary, metadata)
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
            
            # 2. Chunk each assumption analysis
            assumptions = structured_report.get("assumptions", [])
            
            for assumption_idx, assumption in enumerate(assumptions):
                assumption_text = self._format_assumption_analysis(assumption, assumption_idx + 1)
                assumption_chunks = self._split_text_into_chunks(assumption_text)
                
                for i, chunk_text in enumerate(assumption_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": f"assumption_{assumption_idx + 1}",
                        "metadata": {
                            "section_type": "assumption_analysis",
                            "assumption_id": assumption.get("assumption_id"),
                            "assumption_index": assumption_idx + 1,
                            "validation_status": assumption.get("validation_status"),
                            "chunk_position": i,
                            "total_chunks_in_section": len(assumption_chunks)
                        }
                    })
                    chunk_index += 1
            
            # 3. Chunk research data summary if available
            research_summary = structured_report.get("research_data_summary", {})
            if research_summary:
                summary_text = self._format_research_summary(research_summary)
                summary_chunks = self._split_text_into_chunks(summary_text)
                
                for i, chunk_text in enumerate(summary_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "section": "research_data_summary",
                        "metadata": {
                            "section_type": "research_data_summary",
                            "chunk_position": i,
                            "total_chunks_in_section": len(summary_chunks)
                        }
                    })
                    chunk_index += 1
            
            logger.info(f"✅ REPORT CHUNKING: Created {len(chunks)} chunks from report")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ REPORT CHUNKING: Error creating chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"🔍 DEBUG: structured_report keys: {list(structured_report.keys()) if isinstance(structured_report, dict) else 'Not a dict'}")
            logger.error(f"🔍 DEBUG: assumptions type: {type(structured_report.get('assumptions', None))}")
            return []
    
    def _format_executive_summary(
        self,
        executive_summary: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """Format executive summary as text."""
        lines = [
            "=== EXECUTIVE SUMMARY ===",
            "",
            f"Project: {metadata.get('project_id', 'Unknown')}",
            f"Generated: {metadata.get('generated_at', 'Unknown')}",
            f"Total Assumptions: {metadata.get('total_assumptions', 0)}",
            f"Validated: {metadata.get('validated', 0)}",
            f"Partially Validated: {metadata.get('partially_validated', 0)}",
            f"Invalidated: {metadata.get('invalidated', 0)}",
            ""
        ]
        
        # Add key findings
        key_findings = executive_summary.get("key_findings", [])
        if key_findings:
            lines.append("KEY FINDINGS:")
            for finding in key_findings:
                lines.append(f"- {finding}")
            lines.append("")
        
        # Add validation overview
        validation_overview = executive_summary.get("validation_overview", {})
        if validation_overview:
            lines.append("VALIDATION OVERVIEW:")
            # Handle both dict and list formats
            if isinstance(validation_overview, dict):
                for key, value in validation_overview.items():
                    lines.append(f"- {key}: {value}")
            elif isinstance(validation_overview, list):
                for item in validation_overview:
                    lines.append(f"- {item}")
            lines.append("")
        
        # Add recommendations
        recommendations = executive_summary.get("recommendations", [])
        if recommendations:
            lines.append("RECOMMENDATIONS:")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_assumption_analysis(
        self,
        assumption: Dict[str, Any],
        index: int
    ) -> str:
        """Format assumption analysis as text."""
        lines = [
            f"=== ASSUMPTION {index}: {assumption.get('validation_status', 'UNKNOWN').upper()} ===",
            "",
            f"Assumption: {assumption.get('assumption_text', 'Unknown')}",
            f"Persona: {assumption.get('persona_name', 'Unknown')}",
            f"Confidence: {assumption.get('confidence', 0):.2f}",
            ""
        ]
        
        # Add analyses
        analyses = assumption.get("analyses", {})
        if analyses:
            lines.append("ANALYSIS DIMENSIONS:")
            lines.append("")
            
            # Map analysis types to readable names
            analysis_names = {
                "pain_points": "Pain Points Analysis",
                "size_frequency": "Problem Size & Frequency Analysis",
                "current_solutions": "Current Solutions Analysis",
                "gains_benefits": "Gains & Benefits Analysis",
                "jobs_to_be_done": "Jobs-to-be-Done Analysis"
            }
            
            # Handle both dict and list formats for analyses
            if isinstance(analyses, dict):
                analyses_items = analyses.items()
            elif isinstance(analyses, list):
                # Convert list to dict format
                analyses_items = [(f"analysis_{i}", item) for i, item in enumerate(analyses)]
            else:
                logger.warning(f"⚠️ REPORT CHUNKING: Unexpected analyses type: {type(analyses)}")
                analyses_items = []
            
            for analysis_type, analysis_data in analyses_items:
                if isinstance(analysis_data, dict):
                    analysis_name = analysis_names.get(analysis_type, analysis_type.replace("_", " ").title())
                    lines.append(f"--- {analysis_name} ---")
                    
                    # Add claim
                    claim = analysis_data.get("claim", "")
                    if claim:
                        lines.append(f"Claim: {claim}")
                    
                    # Add accuracy level
                    accuracy = analysis_data.get("accuracy_level", "")
                    if accuracy:
                        lines.append(f"Accuracy: {accuracy}")
                    
                    # Add key findings
                    key_findings = analysis_data.get("key_findings", [])
                    if key_findings:
                        lines.append("Key Findings:")
                        for finding in key_findings:
                            lines.append(f"  - {finding}")
                    
                    # Add statistical data if available
                    statistical_data = analysis_data.get("statistical_data", {})
                    if statistical_data:
                        lines.append("Statistical Data:")
                        for key, value in statistical_data.items():
                            lines.append(f"  - {key}: {value}")
                    
                    lines.append("")
        
        return "\n".join(lines)
    
    def _format_research_summary(
        self,
        research_summary: Dict[str, Any]
    ) -> str:
        """Format research data summary as text."""
        lines = [
            "=== RESEARCH DATA SUMMARY ===",
            ""
        ]
        
        # CSV data sources
        csv_sources = research_summary.get("csv_data_sources", [])
        if csv_sources:
            lines.append("CSV DATA SOURCES:")
            for source in csv_sources:
                lines.append(f"- {source.get('filename', 'Unknown')}: {source.get('total_responses', 0)} responses")
            lines.append("")
        
        # PDF data sources
        pdf_sources = research_summary.get("pdf_data_sources", [])
        if pdf_sources:
            lines.append("PDF DATA SOURCES:")
            for source in pdf_sources:
                lines.append(f"- {source.get('filename', 'Unknown')}: {source.get('total_pages', 0)} pages")
            lines.append("")
        
        return "\n".join(lines)
    
    def _split_text_into_chunks(
        self,
        text: str
    ) -> List[str]:
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
        try:
            # Extract text content from chunks
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings using embedding service
            embeddings = await self.embedding_service.generate_embeddings(texts)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                if i < len(embeddings):
                    chunk["embedding"] = embeddings[i]
                else:
                    logger.warning(f"⚠️ REPORT CHUNKING: Missing embedding for chunk {i}")
                    chunk["embedding"] = []
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ REPORT CHUNKING: Error generating embeddings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _store_report_chunks(
        self,
        project_id: str,
        tenant_id: str,
        chunks: List[Dict[str, Any]],
        persona_id: Optional[str] = None
    ) -> bool:
        """Store report chunks in vector database with persona_id tagging."""
        try:
            # 🎭 MULTI-PERSONA: Delete ONLY this persona's analysis_report chunks
            # This preserves uploaded document chunks (csv/pdf) and other personas' report chunks
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            
            chunk_service = get_chunk_storage_service()
            
            # Get all existing chunks for this project
            existing_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            # Log existing chunk distribution BEFORE deletion
            if existing_chunks:
                before_distribution = {}
                for chunk in existing_chunks:
                    st = chunk.get('metadata', {}).get('source_type', 'unknown')
                    pid = chunk.get('metadata', {}).get('persona_id', 'none')
                    key = f"{st}:{pid}"
                    before_distribution[key] = before_distribution.get(key, 0) + 1
                logger.info(f"📊 BEFORE DELETION: {before_distribution}")
            
            # 🎭 Delete analysis_report chunks (handle migration from old format)
            if existing_chunks:
                if persona_id:
                    # Multi-persona: delete this persona's chunks AND old untagged chunks (migration)
                    report_chunk_ids = [
                        chunk['id'] for chunk in existing_chunks 
                        if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
                        and (
                            chunk.get('metadata', {}).get('persona_id') == persona_id  # This persona's chunks
                            or not chunk.get('metadata', {}).get('persona_id')  # Old untagged chunks (migration)
                        )
                    ]
                    logger.info(f"🎭 REPORT STORAGE: Deleting {len(report_chunk_ids)} analysis_report chunks (persona '{persona_id}' + old untagged)")
                else:
                    # Single-persona: delete all analysis_report chunks
                    report_chunk_ids = [
                        chunk['id'] for chunk in existing_chunks 
                        if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
                    ]
                    logger.info(f"🗑️ REPORT STORAGE: Deleting {len(report_chunk_ids)} old analysis_report chunks (single-persona)")
                
                if report_chunk_ids:
                    # Delete old report chunks by ID
                    from src.mint.api.system.core.supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    logger.info(f"🗑️ DELETING: Removing {len(report_chunk_ids)} chunks...")
                    for chunk_id in report_chunk_ids:
                        supabase.client.table("chunks").delete().eq("id", chunk_id).execute()
                    logger.info(f"✅ DELETED: Successfully removed {len(report_chunk_ids)} old chunks")
            
            persona_tag = f" for persona '{persona_id}'" if persona_id else ""
            logger.info(f"🔍 REPORT STORAGE: Storing new analysis_report chunks{persona_tag} (preserving csv/pdf chunks and other personas)")
            
            # Prepare chunks for storage
            chunks_to_store = []
            
            for chunk in chunks:
                if not chunk.get("embedding"):
                    logger.warning(f"⚠️ REPORT CHUNKING: Skipping chunk {chunk.get('chunk_index')} - no embedding")
                    continue
                    
                # 🎭 MULTI-PERSONA: Add persona_id to metadata
                metadata = {
                    "source_type": "analysis_report",
                    "section": chunk["section"],
                    "project_id": project_id,
                    "tenant_id": tenant_id,
                    "created_at": datetime.utcnow().isoformat(),
                    **chunk.get("metadata", {})
                }
                
                # Add persona_id if provided
                if persona_id:
                    metadata["persona_id"] = persona_id
                
                chunks_to_store.append({
                    "content": chunk["content"],
                    "embedding": chunk["embedding"],
                    "index": chunk["chunk_index"],
                    "metadata": metadata
                })
            
            if not chunks_to_store:
                logger.error(f"❌ REPORT CHUNKING: No valid chunks to store")
                return False
            
            # CRITICAL: Insert chunks directly WITHOUT calling store_chunks (which deletes all chunks)
            # We manually deleted only analysis_report chunks above, now just insert new ones
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            from src.mint.api.report.report_models import ReportChunkWithEmbedding
            
            chunk_service = get_chunk_storage_service()
            
            # Format chunks for direct insertion
            formatted_chunks = []
            for chunk in chunks_to_store:
                try:
                    chunk_obj = ReportChunkWithEmbedding(
                        chunk_index=chunk.get('index', 0),
                        content=chunk['content'],
                        embedding=chunk['embedding'],
                        metadata=chunk.get('metadata', {})
                    )
                    formatted_chunks.append(chunk_obj)
                except Exception as e:
                    logger.warning(f"Failed to format chunk {chunk.get('index', 0)}: {e}")
                    continue
            
            # 🎭 CRITICAL: Find max chunk_index from ALL existing chunks (CSV/PDF + other personas)
            max_index = -1
            if existing_chunks:
                # Consider ALL chunks to avoid conflicts with other personas
                max_index = max(c.get('chunk_index', -1) for c in existing_chunks)
            
            logger.info(f"📊 MAX CHUNK INDEX (all sources): {max_index}, starting new chunks at {max_index + 1}")
            
            # Insert chunks directly to database WITHOUT deletion
            from src.mint.api.system.core.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            batch_size = 50
            success_count = 0
            
            for i in range(0, len(formatted_chunks), batch_size):
                batch = formatted_chunks[i:i+batch_size]
                batch_data = []
                
                for idx, chunk in enumerate(batch):
                    if chunk.embedding is None:
                        continue
                    
                    # Use chunk_index AFTER all CSV/PDF chunks to avoid conflicts
                    new_chunk_index = max_index + 1 + (i + idx)
                    
                    batch_data.append({
                        'doc_id': project_id,
                        'chunk_index': new_chunk_index,  # Non-conflicting index
                        'content': chunk.content,
                        'embedding': chunk.embedding,
                        'metadata': chunk.metadata
                    })
                
                if batch_data:
                    try:
                        result = supabase.client.table('chunks').insert(batch_data).execute()
                        success_count += len(batch_data)
                        logger.info(f"✅ Inserted batch {i//batch_size + 1}: {len(batch_data)} chunks")
                    except Exception as e:
                        logger.error(f"❌ Failed to insert batch: {e}")
                        return False
            
            logger.info(f"✅ REPORT STORAGE: Successfully inserted {success_count} analysis_report chunks")
            
            # Verify CSV/PDF chunks are still there
            final_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            after_distribution = {}
            for chunk in final_chunks:
                st = chunk.get('metadata', {}).get('source_type', 'unknown')
                after_distribution[st] = after_distribution.get(st, 0) + 1
            logger.info(f"📊 AFTER INSERTION: {after_distribution}")
            
            csv_pdf_count = after_distribution.get('csv', 0) + after_distribution.get('pdf', 0)
            if csv_pdf_count > 0:
                logger.info(f"✅ SUCCESS: CSV/PDF chunks preserved! ({csv_pdf_count} chunks)")
            else:
                logger.error(f"❌ CRITICAL: CSV/PDF chunks were deleted!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ REPORT CHUNKING: Error storing chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
