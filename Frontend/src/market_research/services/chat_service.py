"""
Market Research Analysis Chat Service

Provides conversational interface for querying uploaded research documents
and generated analysis reports using RAG (Retrieval-Augmented Generation).

Features:
- Multi-source context retrieval (documents + report + project data)
- Conversation memory for follow-up questions
- Grounded responses using only available data
- Citation tracking for transparency
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ..adapters.vector_adapter import AnalysisAgentVectorAdapter
from ..utils.ai_service_wrapper import AIServiceWrapper

# AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class MarketResearchChatService:
    """
    Chat service for market research analysis with RAG and conversation memory.
    
    Retrieves context from:
    1. Uploaded research documents (PDFs/CSVs)
    2. Generated analysis report
    3. PV report chunks
    4. Actionable insights
    5. Personas, hypotheses, and assumptions
    """
    
    def __init__(self):
        """Initialize chat service with required adapters."""
        self.db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.vector_adapter = AnalysisAgentVectorAdapter()
        self.ai_service = AIServiceWrapper()
        
        # Chat configuration
        self.max_context_tokens = 4000  # Leave room for response
        self.max_history_messages = 10  # Last 10 messages
        self.similarity_threshold = 0.7
        
    async def chat(
        self,
        project_id: str,
        tenant_id: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        persona_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate a grounded response.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_message: User's question/message
            conversation_history: Previous conversation messages
            
        Returns:
            Response with answer, sources, and updated conversation
        """
        try:
            persona_tag = f" for persona '{persona_id}'" if persona_id else ""
            logger.info(f"💬 CHAT: Processing message for project {project_id}{persona_tag}")
            logger.info(f"💬 CHAT: User message: {user_message[:100]}...")
            
            # Initialize conversation history if not provided
            if conversation_history is None:
                conversation_history = []
            
            # Retrieve multi-source context using RAG with persona filtering
            context = await self._retrieve_context(
                project_id=project_id,
                tenant_id=tenant_id,
                query=user_message,
                conversation_history=conversation_history,
                persona_id=persona_id,
                user_id=user_id
            )
            
            if not context["has_context"]:
                return {
                    "success": False,
                    "error": "no_context",
                    "message": "No research data or analysis report found for this project. Please upload documents and run analysis first."
                }
            
            # Generate response using LLM with retrieved context
            response = await self._generate_response(
                user_message=user_message,
                context=context,
                conversation_history=conversation_history
            )
            
            # Update conversation history
            updated_history = self._update_conversation_history(
                conversation_history=conversation_history,
                user_message=user_message,
                assistant_response=response["answer"]
            )
            
            logger.info(f"✅ CHAT: Generated response with {len(response['sources'])} sources")
            
            return {
                "success": True,
                "answer": response["answer"],
                "sources": response["sources"],
                "context_used": {
                    "research_chunks": len(context.get("research_chunks", [])),
                    "report_chunks": len(context.get("report_chunks", []))
                },
                "conversation_history": updated_history,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ CHAT: Error processing message: {e}")
            return {
                "success": False,
                "error": "chat_error",
                "message": f"Failed to process chat message: {str(e)}"
            }
    
    async def _retrieve_context(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        conversation_history: List[Dict[str, str]],
        persona_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context from uploaded documents and analysis report ONLY.
        
        For multi-persona projects, filters by persona_id to ensure chat isolation.
        
        Returns context from:
        - Research documents (uploaded PDFs/CSVs) for the specified persona
        - Analysis report chunks (final generated report) for the specified persona
        """
        try:
            persona_tag = f" for persona '{persona_id}'" if persona_id else ""
            logger.info(f"🔍 CHAT CONTEXT: Starting retrieval from uploaded documents and analysis report{persona_tag}")
            
            # 1. Get research document chunks (uploaded CSV/PDF files) - PERSONA FILTERED
            logger.info(f"📄 CHAT CONTEXT: Retrieving from uploaded research documents{persona_tag}...")
            research_chunks = await self._retrieve_research_chunks(
                project_id, tenant_id, query, max_chunks=20, persona_id=persona_id, user_id=user_id
            )
            logger.info(f"✅ CHAT CONTEXT: Retrieved {len(research_chunks)} research document chunks{persona_tag}")
            
            # 2. Get analysis report chunks (final generated report) - PERSONA FILTERED
            logger.info(f"📊 CHAT CONTEXT: Retrieving from analysis report{persona_tag}...")
            report_chunks = await self._retrieve_report_chunks(
                project_id, tenant_id, query, max_chunks=15, persona_id=persona_id
            )
            logger.info(f"✅ CHAT CONTEXT: Retrieved {len(report_chunks)} analysis report chunks{persona_tag}")
            
            # Combine context - ONLY uploaded documents and analysis report
            # Include project context for monitoring
            context = {
                "research_chunks": research_chunks,
                "report_chunks": report_chunks,
                "has_context": len(research_chunks) > 0 or len(report_chunks) > 0,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "user_id": user_id
            }
            
            logger.info(f"✅ CHAT CONTEXT: Context retrieval complete. Total chunks: {len(research_chunks) + len(report_chunks)}")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ CHAT CONTEXT: Error retrieving context: {e}")
            return {
                "research_chunks": [],
                "report_chunks": [],
                "has_context": False
            }
    
    async def _retrieve_research_chunks(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        max_chunks: int = 10,
        persona_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks from uploaded research documents (CSV/PDF only) for the specified persona using direct database access."""
        try:
            # Load all chunks from chunks table
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            
            chunk_service = get_chunk_storage_service()
            all_stored_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            if not all_stored_chunks:
                logger.warning(f"No chunks found for project {project_id}")
                return []
            
            # CRITICAL FIX: Filter for ONLY uploaded document chunks (csv/pdf), exclude analysis_report
            # PERSONA FILTER: Only get chunks for the specified persona
            if persona_id:
                stored_chunks = [
                    chunk for chunk in all_stored_chunks
                    if chunk.get('metadata', {}).get('source_type') in ['csv', 'pdf']
                    and chunk.get('metadata', {}).get('persona_id') == persona_id
                ]
                logger.info(f"🎭 PERSONA FILTER: Filtered to persona '{persona_id}' - {len(stored_chunks)} chunks")
            else:
                stored_chunks = [
                    chunk for chunk in all_stored_chunks
                    if chunk.get('metadata', {}).get('source_type') in ['csv', 'pdf']
                ]
            
            # Debug: Show source type distribution
            source_types = {}
            for chunk in all_stored_chunks:
                st = chunk.get('metadata', {}).get('source_type', 'unknown')
                source_types[st] = source_types.get(st, 0) + 1
            
            logger.info(f"🔍 RESEARCH FILTER: Found {len(all_stored_chunks)} total chunks")
            logger.info(f"🔍 SOURCE TYPE DISTRIBUTION: {source_types}")
            logger.info(f"🔍 FILTERED RESULT: {len(stored_chunks)} csv/pdf chunks for research")
            
            if not stored_chunks:
                logger.warning(f"No CSV/PDF research chunks found for project {project_id}")
                return []
            
            # Generate embedding for the query with monitoring
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            
            started_at = datetime.utcnow()
            query_embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            # Record embedding usage (fire-and-forget)
            if user_id or tenant_id:
                try:
                    monitoring_context = AIUsageContext(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        project_id=project_id,
                        feature_id="market_research_chat",
                        workflow_name="chat_workflow",
                        step_name="query_embedding",
                        environment="prod"
                    )
                    finished_at = datetime.utcnow()
                    monitoring_service = get_monitoring_service()
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai",
                            model_name="text-embedding-3-small",
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="success" if query_embedding else "error",
                            embedding_tokens=len(query) // 4,
                            input_chars=len(query)
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record embedding monitoring: {monitor_error}")
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Calculate similarity scores and rank chunks
            import numpy as np
            scored_chunks = []
            
            for chunk_data in stored_chunks:
                # Get chunk embedding
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        import json
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                elif isinstance(raw_embedding, list):
                    chunk_embedding = raw_embedding
                else:
                    continue
                
                # Calculate cosine similarity
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        'content': chunk_data.get('content', ''),
                        'similarity': float(similarity),
                        'metadata': chunk_data.get('metadata', {})
                    })
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity: {e}")
                    continue
            
            # IMPROVED RETRIEVAL: Ensure diversity across source files and types
            # Group chunks by source file and type
            chunks_by_source = {}
            for chunk in scored_chunks:
                source_file = chunk['metadata'].get('source_filename', 'unknown')
                source_type = chunk['metadata'].get('source_type', 'unknown')
                key = f"{source_type}:{source_file}"
                
                if key not in chunks_by_source:
                    chunks_by_source[key] = []
                chunks_by_source[key].append(chunk)
            
            # Get diverse chunks: top chunk from each source, then fill remaining slots
            top_chunks = []
            
            # First pass: Get best chunk from each source
            for source_key, source_chunks in sorted(chunks_by_source.items()):
                if len(top_chunks) >= max_chunks:
                    break
                # Add best chunk from this source
                top_chunks.append(source_chunks[0])
            
            # Second pass: Fill remaining slots with next best chunks overall
            if len(top_chunks) < max_chunks:
                remaining_chunks = [
                    chunk for chunk in scored_chunks 
                    if chunk not in top_chunks
                ]
                remaining_chunks.sort(key=lambda x: x['similarity'], reverse=True)
                top_chunks.extend(remaining_chunks[:max_chunks - len(top_chunks)])
            
            # Sort final selection by similarity
            top_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            
            # DEBUG: Log what we're returning with diversity info
            source_distribution = {}
            for chunk in top_chunks:
                source_file = chunk['metadata'].get('source_filename', 'unknown')
                source_type = chunk['metadata'].get('source_type', 'unknown')
                key = f"{source_type}:{source_file}"
                source_distribution[key] = source_distribution.get(key, 0) + 1
            
            logger.info(f"🔍 RESEARCH CHUNKS DEBUG: Returning {len(top_chunks)} chunks from {len(source_distribution)} sources")
            logger.info(f"🔍 SOURCE DISTRIBUTION: {source_distribution}")
            if top_chunks:
                logger.info(f"🔍 FIRST CHUNK METADATA: {top_chunks[0].get('metadata', {})}")
                logger.info(f"🔍 FIRST CHUNK CONTENT PREVIEW: {top_chunks[0].get('content', '')[:200]}...")
            
            return top_chunks
            
        except Exception as e:
            logger.error(f"❌ CHAT: Error retrieving research chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _retrieve_report_chunks(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        max_chunks: int = 5,
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks from the generated analysis report for the specified persona using direct database access."""
        try:
            # Load all chunks from chunks table and filter for analysis_report
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            
            chunk_service = get_chunk_storage_service()
            all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            # Filter for analysis report chunks only
            # PERSONA FILTER: Only get report chunks for the specified persona
            if persona_id:
                report_chunks = [
                    chunk for chunk in all_chunks
                    if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
                    and chunk.get('metadata', {}).get('persona_id') == persona_id
                ]
                logger.info(f"🎭 PERSONA FILTER: Filtered report chunks to persona '{persona_id}' - {len(report_chunks)} chunks")
            else:
                report_chunks = [
                    chunk for chunk in all_chunks
                    if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
                ]
            
            if not report_chunks:
                logger.warning(f"No analysis report chunks found for project {project_id}")
                return []
            
            # Generate embedding for the query
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            query_embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Calculate similarity scores and rank chunks
            import numpy as np
            scored_chunks = []
            
            for chunk_data in report_chunks:
                # Get chunk embedding
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        import json
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                elif isinstance(raw_embedding, list):
                    chunk_embedding = raw_embedding
                else:
                    continue
                
                # Calculate cosine similarity
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        'content': chunk_data.get('content', ''),
                        'similarity': float(similarity),
                        'metadata': chunk_data.get('metadata', {})
                    })
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity: {e}")
                    continue
            
            # Sort by similarity and return top chunks
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = scored_chunks[:max_chunks]
            
            # DEBUG: Log what we're returning
            logger.info(f"🔍 REPORT CHUNKS DEBUG: Returning {len(top_chunks)} chunks")
            if top_chunks:
                logger.info(f"🔍 FIRST REPORT CHUNK KEYS: {list(top_chunks[0].keys())}")
                logger.info(f"🔍 FIRST REPORT CHUNK METADATA: {top_chunks[0].get('metadata', {})}")
                logger.info(f"🔍 FIRST REPORT CHUNK CONTENT PREVIEW: {top_chunks[0].get('content', '')[:200]}...")
            
            return top_chunks
            
        except Exception as e:
            logger.error(f"❌ CHAT: Error retrieving report chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _load_project_metadata(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Load project metadata including personas, hypotheses, and assumptions."""
        try:
            # Get project context from database
            project_context = await self.db_adapter.get_vmp_project_context(
                project_id=project_id,
                tenant_id=tenant_id
            )
            
            if not project_context:
                return {}
            
            metadata = {}
            
            # Extract personas
            personas = project_context.get("personas", [])
            if personas:
                metadata["personas"] = personas
            
            # Extract field prep data (hypotheses, assumptions)
            field_prep_data = project_context.get("field_prep_data", {})
            if field_prep_data:
                if "hypotheses" in field_prep_data:
                    metadata["hypotheses"] = field_prep_data["hypotheses"]
                if "assumptions" in field_prep_data:
                    metadata["assumptions"] = field_prep_data["assumptions"]
            
            # Extract VPC data (customer profile)
            vpc_data = project_context.get("vpc_data", {})
            if vpc_data and "customer_profile" in vpc_data:
                metadata["customer_profile"] = vpc_data["customer_profile"]
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ CHAT: Error loading project metadata: {e}")
            return {}
    
    async def _generate_response(
        self,
        user_message: str,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate a grounded response using LLM with retrieved context."""
        try:
            # Build context string from all sources
            context_parts = []
            sources = []
            
            # Add research document context
            if context["research_chunks"]:
                logger.info(f"🔍 CONTEXT BUILD: Building context from {len(context['research_chunks'])} research chunks")
                
                research_context = "\n\n".join([
                    f"[Research Document - {chunk.get('metadata', {}).get('source_filename', chunk.get('metadata', {}).get('filename', 'Unknown'))}]\n{chunk['content']}"
                    for chunk in context["research_chunks"][:20]  # Top 20
                ])
                context_parts.append(f"=== RESEARCH DOCUMENTS ===\n{research_context}")
                
                logger.info(f"🔍 CONTEXT BUILD: Research context length: {len(research_context)} characters")
                
                # Track sources
                for chunk in context["research_chunks"][:20]:
                    metadata = chunk.get("metadata", {})
                    sources.append({
                        "type": "research_document",
                        "filename": metadata.get("source_filename", metadata.get("filename", "Unknown")),
                        "source_type": metadata.get("source_type", "unknown")
                    })
            
            # Add analysis report context
            if context["report_chunks"]:
                logger.info(f"🔍 CONTEXT BUILD: Building context from {len(context['report_chunks'])} report chunks")
                
                report_context = "\n\n".join([
                    f"[Analysis Report Section]\n{chunk['content']}"
                    for chunk in context["report_chunks"][:15]  # Top 15
                ])
                context_parts.append(f"=== ANALYSIS REPORT ===\n{report_context}")
                
                logger.info(f"🔍 CONTEXT BUILD: Report context length: {len(report_context)} characters")
                
                sources.append({
                    "type": "analysis_report",
                    "section_count": len(context["report_chunks"][:15])
                })
            
            # REMOVED: PV report, actionable insights, and project metadata
            # Chat now uses ONLY uploaded documents and analysis report
            
            # Combine all context
            full_context = "\n\n" + "="*80 + "\n\n".join(context_parts)
            
            logger.info(f"🔍 CONTEXT BUILD: Total context parts: {len(context_parts)}")
            logger.info(f"🔍 CONTEXT BUILD: Full context length: {len(full_context)} characters")
            logger.info(f"🔍 CONTEXT BUILD: Context preview (first 500 chars): {full_context[:500]}...")
            
            # Build conversation history string
            history_text = ""
            if conversation_history:
                recent_history = conversation_history[-self.max_history_messages:]
                history_text = "\n\n=== CONVERSATION HISTORY ===\n" + "\n\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                    for msg in recent_history
                ])
            
            # Create system prompt
            system_prompt = """You are a helpful AI assistant analyzing market research data. Your role is to answer questions based STRICTLY on the provided context from:
- Uploaded research documents (PDFs and CSVs that were uploaded to the project)
- Generated analysis report (the final market research analysis report)

CRITICAL RULES:
1. ONLY use information from these TWO sources: uploaded documents and the analysis report
2. If the answer is not in the context, say "I don't have enough information in the available data to answer that question."
3. Cite your sources when possible (e.g., "According to the uploaded research documents..." or "The analysis report shows...")
4. Be conversational but accurate
5. If asked about specific statistics, use exact numbers from the context
6. Consider the conversation history for follow-up questions

DO NOT:
- Make up information not in the context
- Speculate or infer beyond what's stated
- Use external knowledge
- Provide generic advice not grounded in the uploaded documents or analysis report"""

            # Create user prompt
            user_prompt = f"""{history_text}

CONTEXT:
{full_context}

USER QUESTION:
{user_message}

Please provide a helpful, accurate answer based ONLY on the context provided above."""

            # Generate response using LLM with monitoring
            logger.info("🤖 CHAT: Generating LLM response...")
            
            # Create monitoring context from project context
            monitoring_context = AIUsageContext(
                user_id=context.get("user_id"),
                tenant_id=context.get("tenant_id"),
                project_id=context.get("project_id"),
                feature_id="market_research_chat",
                workflow_name="chat_workflow",
                step_name="generate_response",
                environment="prod"
            ) if context.get("project_id") else None
            
            response = await self.ai_service.generate_analysis_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-5-mini",  # Use gpt-5-mini for Azure OpenAI
                max_completion_tokens=16000,  # gpt-5-mini needs large token budget
                monitoring_context=monitoring_context
            )
            
            # Extract content from response dict
            response_text = response.get("content", "") if isinstance(response, dict) else str(response)
            
            logger.info(f"✅ CHAT: Generated response: {len(response_text)} characters")
            
            return {
                "answer": response_text,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"❌ CHAT: Error generating response: {e}")
            return {
                "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
                "sources": []
            }
    
    def _update_conversation_history(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str,
        assistant_response: str
    ) -> List[Dict[str, str]]:
        """Update conversation history with new messages."""
        # Add new messages
        updated_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ]
        
        # Keep only recent messages to manage context size
        if len(updated_history) > self.max_history_messages * 2:  # *2 for user+assistant pairs
            updated_history = updated_history[-(self.max_history_messages * 2):]
        
        return updated_history
    
    async def clear_conversation(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clear conversation history for a project and persona (if multi-persona)."""
        try:
            logger.info(f"🗑️ CHAT: Clearing conversation history for project {project_id}")
            
            # In a production system, you might want to store conversation history
            # in the database. For now, we just return success since history
            # is managed client-side
            
            return {
                "success": True,
                "message": "Conversation history cleared",
                "project_id": project_id
            }
            
        except Exception as e:
            logger.error(f"❌ CHAT: Error clearing conversation: {e}")
            return {
                "success": False,
                "error": "clear_error",
                "message": f"Failed to clear conversation: {str(e)}"
            }
