"""
Evidence Retrieval Engine (Tier 2) - Two-Tier RAG System

This module implements the second tier of the two-tier RAG architecture, providing
balanced qualitative evidence to support statistical claims. It ensures representation
from all source types and manages token budgets for optimal information density.

Key Features:
- Retrieves balanced qualitative evidence (~2,500 tokens)
- Ensures minimum representation from CSV and PDF sources
- Implements semantic similarity search with persona-aware filtering
- Manages token budgets with intelligent content selection
"""

import logging
from copy import deepcopy
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime

from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ..adapters.vector_adapter import AnalysisAgentVectorAdapter
from ..services.statistics_registry_service import StatisticsRegistryService
from ..utils.error_handling import ErrorHandlingService
from .caching_optimization_system import get_token_optimizer, get_resource_manager
from ..utils.ai_service_wrapper import get_ai_service_wrapper

logger = logging.getLogger(__name__)


class EvidenceRetrievalEngine:
    """
    Retrieves balanced qualitative evidence for Tier 2 of the two-tier RAG system.
    
    This engine ensures that analysis agents receive representative examples from all
    uploaded sources, preventing PDF invisibility and maintaining balanced perspectives.
    """
    
    def __init__(
        self,
        db_adapter: AnalysisAgentDatabaseAdapter,
        vector_adapter: AnalysisAgentVectorAdapter,
        statistics_registry: StatisticsRegistryService,
        error_handler: ErrorHandlingService
    ):
        self.db_adapter = db_adapter
        self.vector_adapter = vector_adapter
        self.registry = statistics_registry
        self.error_handler = error_handler

        # ENTERPRISE CONFIGURATION - Aggressive optimization for comprehensive analysis
        self.max_tokens = 16_000  # gpt-5-mini needs large token budget
        self.min_pdf_chunks = 3  # Ensure PDF representation
        self.min_csv_chunks = 5  # Ensure CSV representation
        self.similarity_threshold = 0.6  # Lowered base threshold for enterprise recall
        self.adaptive_threshold_min = 0.25  # Aggressive minimum for comprehensive coverage

        # Token estimation (rough approximation)
        self.chars_per_token = 4
        self.avg_chunk_tokens = 150  # Average tokens per chunk
        self._ai_wrapper = None
        self._retrieval_cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self._query_expansion_cache: Dict[Tuple[str, str, str], List[str]] = {}
        
        # ENTERPRISE AI EXPANSION CONFIGURATION - Aggressive semantic diversity
        self.ai_expansion_enabled = True  # Enable/disable AI expansion
        self.ai_expansion_count = 12  # Generate 12 diverse queries for enterprise coverage
        self.ai_expansion_max_tokens = 16000  # gpt-5-mini needs large token budget for reasoning
        self.use_semantic_diversity = True  # Generate diverse query types
        self.use_multi_layer_expansion = True  # Multi-layered query expansion
        self.use_contextual_synonyms = True  # Context-aware synonym generation
    
    async def retrieve_balanced_evidence(
        self,
        query: str,
        project_id: str,
        tenant_id: str,
        analysis_type: str,
        persona_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        *,
        assumption_id: Optional[str] = None,
        assumption: Optional[Dict[str, Any]] = None,
        persona: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve balanced evidence ensuring representation from all sources.
        
        Args:
            query: Search query for evidence retrieval
            project_id: Project identifier
            tenant_id: Tenant identifier
            analysis_type: Type of analysis (pain, size, solution, gains, jtbd)
            persona_id: Optional persona filter
            max_tokens: Optional token budget override
            
        Returns:
            List of evidence chunks with metadata and citations
        """
        try:
            token_budget = max_tokens or self.max_tokens

            cache_key = (project_id, assumption_id or query, analysis_type)
            if cache_key in self._retrieval_cache:
                cached = self._retrieval_cache[cache_key]
                logger.info(
                    "♻️ RAG: Returning cached evidence packet for assumption %s",
                    assumption_id or "unknown",
                )
                return deepcopy(cached.get("chunks", []))

            # Get all available chunks
            all_chunks = await self._get_research_chunks(project_id, tenant_id)

            if not all_chunks:
                logger.warning(f"No research chunks found for project {project_id}")
                return []

            # Filter by persona if specified
            if persona_id:
                all_chunks = await self._filter_by_persona(all_chunks, persona_id, project_id)

            # Separate by source type
            csv_chunks, pdf_chunks = self._separate_by_source_type(all_chunks)

            logger.info(f"🔍 AVAILABLE CHUNKS: {len(csv_chunks)} CSV, {len(pdf_chunks)} PDF (from {len(all_chunks)} total)")
            
            # Debug source type distribution in all_chunks
            source_types = {}
            for chunk in all_chunks:
                source_type = chunk.get('source_type', 'unknown')
                source_types[source_type] = source_types.get(source_type, 0) + 1
            logger.info(f"🔍 SOURCE TYPE BREAKDOWN: {source_types}")
            
            expanded_queries = await self._expand_query_terms(
                query=query,
                analysis_type=analysis_type,
                assumption=assumption,
                persona=persona,
                cache_key=cache_key,
            )

            # Perform semantic similarity search across expanded queries
            csv_relevant = await self._semantic_search(
                expanded_queries, csv_chunks, analysis_type, top_k=20
            )
            pdf_relevant = await self._semantic_search(
                expanded_queries, pdf_chunks, analysis_type, top_k=15
            )
            
            # Use all relevant chunks that passed semantic filtering
            csv_selected = csv_relevant  # Use all CSV chunks that passed threshold
            pdf_selected = pdf_relevant  # Use all PDF chunks that passed threshold
            
            logger.info(f"🔍 SELECTED CHUNKS: {len(csv_selected)} CSV, {len(pdf_selected)} PDF (no minimum requirements)")
            
            # Combine and balance within token budget using optimization
            balanced_chunks = await self._optimize_content_selection(
                csv_selected, pdf_selected, token_budget, analysis_type, persona_id
            )
            
            # Add retrieval metadata
            for chunk in balanced_chunks:
                chunk.setdefault("summary", self._summarize_chunk(chunk))
                chunk.setdefault("verbatim", chunk.get("content", ""))
                chunk['retrieval_metadata'] = {
                    'retrieved_at': datetime.utcnow().isoformat(),
                    'query': query,
                    'expanded_queries': expanded_queries,
                    'analysis_type': analysis_type,
                    'persona_id': persona_id,
                    'similarity_score': chunk.get('similarity_score', 0.0),
                    'source_balance_enforced': True
                }

            logger.info(f"Retrieved {len(balanced_chunks)} balanced evidence chunks")
            self._retrieval_cache[cache_key] = {"chunks": deepcopy(balanced_chunks)}
            return balanced_chunks

        except Exception as e:
            logger.error(f"Error retrieving balanced evidence: {e}")
            return await self.error_handler.handle_evidence_retrieval_error(e, {
                'project_id': project_id,
                'query': query,
                'analysis_type': analysis_type
            })

    async def _expand_query_terms(
        self,
        *,
        query: str,
        analysis_type: str,
        assumption: Optional[Dict[str, Any]],
        persona: Optional[Dict[str, Any]],
        cache_key: Tuple[str, str, str],
    ) -> List[str]:
        """Generate enriched query terms for sparse datasets."""

        if cache_key in self._query_expansion_cache:
            return self._query_expansion_cache[cache_key]

        base_terms = [query]
        heuristic_terms = await self._build_heuristic_terms(analysis_type, assumption, persona)
        base_terms.extend(heuristic_terms)

        try:
            if not self.ai_expansion_enabled:
                logger.info("⚙️ AI expansion disabled, using heuristics only")
            else:
                wrapper = self._ensure_ai_wrapper()
                persona_label = persona.get("name") if isinstance(persona, dict) else "general"
                assumption_text = assumption.get("text") if isinstance(assumption, dict) else ""
                
                # Enhanced prompt with semantic diversity instructions
                if self.use_semantic_diversity:
                    prompt = self._build_semantic_diversity_prompt(
                        assumption_text, persona_label, analysis_type, heuristic_terms
                    )
                else:
                    prompt = self._build_basic_expansion_prompt(
                        assumption_text, persona_label, analysis_type, heuristic_terms
                    )

                response = await wrapper.generate_analysis_response(
                    messages=[
                        {"role": "system", "content": "You are an expert at query expansion for semantic search systems."},
                        {"role": "user", "content": prompt},
                    ],
                    model="gpt-5-mini",
                    max_completion_tokens=self.ai_expansion_max_tokens,
                    json_mode=False,
                )

                if isinstance(response, dict):
                    content = response.get("content", "")
                else:
                    content = str(response)

                ai_terms = [line.strip() for line in content.splitlines() if line.strip()]
                base_terms.extend(ai_terms[:self.ai_expansion_count])
                
                logger.info(f"🤖 AI EXPANSION: Generated {len(ai_terms[:self.ai_expansion_count])} diverse query terms")
        except Exception as exc:
            logger.warning("⚠️ QUERY EXPANSION: Falling back to heuristics (%s)", exc)

        # Deduplicate while preserving order
        seen = set()
        expanded = []
        for term in base_terms:
            normalised = term.lower()
            if normalised in seen or not term.strip():
                continue
            seen.add(normalised)
            expanded.append(term.strip())

        self._query_expansion_cache[cache_key] = expanded
        return expanded

    async def _build_heuristic_terms(
        self,
        analysis_type: str,
        assumption: Optional[Dict[str, Any]],
        persona: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Construct lightweight heuristic expansions using assumption metadata."""

        assumption_text = (assumption or {}).get("text", "")
        persona_name = (persona or {}).get("name", "")
        keywords = [analysis_type]

        if persona_name:
            keywords.append(persona_name)

        if assumption_text:
            keywords.append(assumption_text)
            keywords.extend(assumption_text.split())

        # ENTERPRISE-GRADE INTELLIGENT SEMANTIC EXPANSION
        if self.use_contextual_synonyms:
            smart_synonyms = await self._generate_contextual_synonyms(
                analysis_type, assumption_text, persona_name
            )
            keywords.extend(smart_synonyms)
        else:
            # Fallback to basic expansion if AI is unavailable
            basic_synonyms = self._get_basic_analysis_synonyms(analysis_type)
            keywords.extend(basic_synonyms)

        cleaned = []
        seen = set()
        for keyword in keywords:
            term = keyword.strip()
            if not term:
                continue
            if term.lower() in seen:
                continue
            seen.add(term.lower())
            cleaned.append(term)

        return cleaned[:12]
    
    async def _generate_contextual_synonyms(
        self,
        analysis_type: str,
        assumption_text: str,
        persona_name: str
    ) -> List[str]:
        """Generate intelligent, contextually relevant synonyms using AI."""
        try:
            wrapper = self._ensure_ai_wrapper()
            
            prompt = f"""You are an expert semantic analyst for market research. Generate contextually relevant synonyms and related terms.

**CONTEXT:**
- Analysis Type: {analysis_type}
- Assumption: {assumption_text[:200] if assumption_text else 'Not provided'}
- Persona: {persona_name or 'General'}

**TASK:**
Generate 15 contextually intelligent synonyms, related terms, and semantic variations for "{analysis_type}" analysis in this specific context.

**REQUIREMENTS:**
1. **Context-Aware**: Terms must be relevant to the specific assumption and persona
2. **Semantic Diversity**: Cover different aspects and angles
3. **Market Research Focus**: Terms that would appear in surveys, interviews, research data
4. **Practical Relevance**: Terms that real people would use when discussing this topic
5. **Varied Specificity**: Mix of broad and specific terms

**OUTPUT FORMAT:**
Return ONLY the terms, one per line, no formatting or explanation.

**EXAMPLE OUTPUT:**
challenges
difficulties
pain points
obstacles
..."""

            response = await wrapper.generate_analysis_response(
                messages=[
                    {"role": "system", "content": "You are an expert semantic analyst specializing in contextual term generation."},
                    {"role": "user", "content": prompt},
                ],
                model="gpt-5-mini",
                max_completion_tokens=16000,  # gpt-5-mini needs large token budget
                json_mode=False,
            )

            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)

            # Parse the response into individual terms
            terms = []
            for line in content.strip().split('\n'):
                term = line.strip()
                if term and not term.startswith('#') and len(term) > 2:
                    terms.append(term)
            
            logger.info(f"🤖 SMART SYNONYMS: Generated {len(terms)} contextual terms for {analysis_type}")
            return terms[:15]  # Limit to 15 terms
            
        except Exception as e:
            logger.warning(f"⚠️ Smart synonym generation failed: {e}, falling back to basic synonyms")
            return self._get_basic_analysis_synonyms(analysis_type)
    
    def _get_basic_analysis_synonyms(self, analysis_type: str) -> List[str]:
        """Fallback basic synonyms when AI expansion fails."""
        # UPDATED: Removed size_frequency and current_solutions (solution)
        basic_synonyms = {
            "pain_points": ["challenges", "frustrations", "problems", "difficulties", "issues"],
            # REMOVED: "size_frequency": ["frequency", "prevalence", "scale", "occurrence", "numbers"],
            # REMOVED: "solution": ["alternatives", "options", "approaches", "methods", "tools"],
            "gains": ["benefits", "value", "advantages", "improvements", "outcomes"],
            "jtbd": ["tasks", "goals", "objectives", "jobs", "functions"],
            "general": ["needs", "requirements", "experiences", "behaviors", "patterns"]
        }
        return basic_synonyms.get(analysis_type, ["needs", "requirements", "patterns"])
    
    def _build_semantic_diversity_prompt(
        self,
        assumption_text: str,
        persona_label: str,
        analysis_type: str,
        heuristic_terms: List[str]
    ) -> str:
        """Build an advanced prompt for semantically diverse query expansion."""
        
        analysis_context = {
            "pain": "customer problems, challenges, frustrations, and pain points",
            "size": "problem frequency, market size, prevalence, and quantitative indicators",
            "solution": "current alternatives, workarounds, existing tools, and competitive solutions",
            "gains": "desired benefits, outcomes, value propositions, and aspirations",
            "jtbd": "functional jobs, tasks to accomplish, goals, and objectives"
        }
        
        context_description = analysis_context.get(analysis_type, "relevant information")
        
        return f"""You are an ENTERPRISE-GRADE query expansion specialist for comprehensive market research analysis.

**ENTERPRISE CONTEXT:**
- Core Assumption: {assumption_text or 'Not provided'}
- Target Persona: {persona_label or 'General audience'}
- Analysis Domain: {analysis_type} ({context_description})
- Seed Keywords: {', '.join(heuristic_terms[:8]) if heuristic_terms else 'None'}

**MISSION:**
Generate {self.ai_expansion_count} HIGHLY DIVERSE, ENTERPRISE-QUALITY search queries to achieve MAXIMUM RECALL from research datasets (CSV surveys, PDF interviews, market studies).

**ENTERPRISE REQUIREMENTS:**
1. **MAXIMUM SEMANTIC COVERAGE**: Each query MUST explore a completely different semantic space
2. **MULTI-DIMENSIONAL QUERY TYPES**:
   - **Behavioral**: Actions, behaviors, usage patterns
   - **Emotional**: Feelings, frustrations, satisfaction levels
   - **Contextual**: Situations, environments, circumstances
   - **Quantitative**: Numbers, frequencies, measurements
   - **Qualitative**: Descriptions, narratives, experiences
   - **Comparative**: Alternatives, preferences, trade-offs
   - **Temporal**: Time-based patterns, changes, trends
   - **Causal**: Reasons, drivers, motivations
3. **ENTERPRISE PRECISION**: Balance broad recall with targeted relevance
4. **PERSONA INTELLIGENCE**: Incorporate persona-specific language and perspectives
5. **DOMAIN EXPERTISE**: Leverage deep understanding of {analysis_type} analysis patterns

**CRITICAL SUCCESS FACTORS:**
- NO semantic overlap between queries
- MAXIMUM diversity in search angles
- ENTERPRISE-GRADE comprehensiveness
- OPTIMAL similarity score potential (target 0.5+ scores)

**OUTPUT FORMAT:**
Return EXACTLY {self.ai_expansion_count} queries, one per line, no formatting or explanation.

**ENTERPRISE QUALITY EXAMPLES:**
behavioral usage patterns and decision making
emotional frustrations and satisfaction drivers
contextual situations requiring solutions
quantitative frequency and prevalence data
..."""
    
    def _build_basic_expansion_prompt(
        self,
        assumption_text: str,
        persona_label: str,
        analysis_type: str,
        heuristic_terms: List[str]
    ) -> str:
        """Build a basic prompt for query expansion (fallback)."""
        
        return f"""Expand this search query for a retrieval system.

Assumption: {assumption_text or query}
Persona: {persona_label or 'General'}
Analysis Focus: {analysis_type}
Existing Terms: {', '.join(heuristic_terms[:8]) or 'None'}

Generate {self.ai_expansion_count} diverse search queries (one per line) that will help find relevant evidence.
Focus on semantic variations, related concepts, and different phrasings.
"""

    def _summarize_chunk(self, chunk: Dict[str, Any]) -> str:
        """Create a lightweight summary snippet for a chunk."""

        content = chunk.get("content", "").strip()
        if not content:
            return ""

        sentences = [part.strip() for part in content.split(".") if part.strip()]
        if not sentences:
            return content[:200]

        summary = " ".join(sentences[:2])
        return summary[:320]

    def _ensure_ai_wrapper(self):
        if self._ai_wrapper is None:
            self._ai_wrapper = get_ai_service_wrapper()
        return self._ai_wrapper
    
    async def _get_research_chunks(self, project_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all research chunks for the project from the chunks table (production-grade)."""
        try:
            # PRODUCTION FIX: Load chunks from the proper chunks table with embeddings
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            
            chunk_service = get_chunk_storage_service()
            stored_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            if not stored_chunks:
                logger.warning(f"No chunks found in chunks table for project {project_id}")
                return []
            
            # Convert to the format expected by evidence retrieval
            formatted_chunks = []
            for chunk_data in stored_chunks:
                # Extract metadata to determine source type and file
                metadata = chunk_data.get('metadata', {})
                source_type = metadata.get('source_type', 'unknown')
                source_file = metadata.get('filename', metadata.get('source_file', 'unknown'))
                
                # CRITICAL FIX: Deserialize embedding from string to numeric array
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        import json
                        embedding = json.loads(raw_embedding)
                        logger.debug(f"🔧 EMBEDDING FIX: Deserialized embedding from string to array (length: {len(embedding)})")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ EMBEDDING ERROR: Failed to deserialize embedding: {e}")
                        embedding = None
                elif raw_embedding and isinstance(raw_embedding, list):
                    embedding = raw_embedding  # Already in correct format
                else:
                    embedding = None
                
                formatted_chunk = {
                    'id': chunk_data.get('id'),
                    'chunk_index': chunk_data.get('chunk_index', 0),
                    'content': chunk_data.get('content', ''),
                    'embedding': embedding,  # ✅ Properly deserialized embeddings!
                    'source_type': source_type,
                    'source_file': source_file,
                    'metadata': metadata
                }
                formatted_chunks.append(formatted_chunk)
            
            # Separate by source type for logging
            csv_chunks = [c for c in formatted_chunks if c['source_type'] == 'csv']
            pdf_chunks = [c for c in formatted_chunks if c['source_type'] == 'pdf']
            
            logger.info(f"✅ PRODUCTION: Retrieved {len(formatted_chunks)} chunks from chunks table ({len(csv_chunks)} CSV, {len(pdf_chunks)} PDF)")
            
            # Debug PDF chunk distribution by source file
            if pdf_chunks:
                pdf_by_file = {}
                for chunk in pdf_chunks:
                    source_file = chunk.get('source_file', 'unknown')
                    pdf_by_file[source_file] = pdf_by_file.get(source_file, 0) + 1
                logger.info(f"🔍 PDF DISTRIBUTION: {pdf_by_file}")
            else:
                logger.warning("⚠️ NO PDF CHUNKS: No PDF chunks found in retrieved data")
            
            # Verify embeddings are present and properly formatted
            chunks_with_embeddings = sum(1 for c in formatted_chunks if c.get('embedding'))
            logger.info(f"✅ PRODUCTION: {chunks_with_embeddings}/{len(formatted_chunks)} chunks have embeddings")
            
            # Debug embedding format for first chunk
            if formatted_chunks and formatted_chunks[0].get('embedding'):
                first_embedding = formatted_chunks[0]['embedding']
                logger.info(f"🔍 EMBEDDING FORMAT: Type={type(first_embedding)}, Length={len(first_embedding) if first_embedding else 0}")
                if isinstance(first_embedding, list) and len(first_embedding) > 0:
                    logger.info(f"🔍 EMBEDDING SAMPLE: First 3 values={first_embedding[:3]}")
                else:
                    logger.warning(f"⚠️ EMBEDDING ISSUE: First embedding is not a proper numeric array")
            
            return formatted_chunks
            
        except Exception as e:
            logger.error(f"❌ PRODUCTION: Error loading chunks from chunks table: {e}")
            logger.error(f"❌ PRODUCTION: No fallback available - chunks table is the single source of truth")
            raise Exception(f"Failed to load chunks from production chunks table: {e}")
    
    
    async def _filter_by_persona(
        self, 
        chunks: List[Dict[str, Any]], 
        persona_id: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Filter chunks by persona relevance."""
        try:
            # Debug input to persona filtering
            input_csv = [c for c in chunks if c.get('source_type') == 'csv']
            input_pdf = [c for c in chunks if c.get('source_type') == 'pdf']
            logger.info(f"🔍 PERSONA FILTER INPUT: {len(input_csv)} CSV, {len(input_pdf)} PDF chunks")
            # Get persona associations from statistics registry
            statistics = await self.registry.get_statistics_for_analysis(
                project_id=project_id,
                tenant_id='',  # Will be handled by registry
                analysis_type='comprehensive',
                persona_id=persona_id
            )
            
            persona_mappings = statistics.get('persona_mappings', {}) if statistics else {}
            persona_data = persona_mappings.get(persona_id, {})
            
            if not persona_data:
                # If no specific persona associations, return all chunks
                logger.info(f"No persona associations found for {persona_id}, returning all chunks")
                return chunks
            
            # Filter chunks based on persona associations
            associated_stats = persona_data.get('associated_statistics', [])
            relevance_scores = persona_data.get('relevance_scores', {})
            
            filtered_chunks = []
            for chunk in chunks:
                # Check if chunk is associated with persona-relevant statistics
                chunk_relevance = self._calculate_chunk_persona_relevance(
                    chunk, associated_stats, relevance_scores
                )
                
                if chunk_relevance > 0.3:  # Threshold for persona relevance
                    chunk['persona_relevance_score'] = chunk_relevance
                    filtered_chunks.append(chunk)
            
            # If too few persona-specific chunks, include general chunks
            if len(filtered_chunks) < 10:
                general_chunks = [c for c in chunks if c not in filtered_chunks]
                for chunk in general_chunks[:10]:
                    chunk['persona_relevance_score'] = 0.2  # Low but included
                    filtered_chunks.append(chunk)
            
            # Debug output from persona filtering
            output_csv = [c for c in filtered_chunks if c.get('source_type') == 'csv']
            output_pdf = [c for c in filtered_chunks if c.get('source_type') == 'pdf']
            logger.info(f"🔍 PERSONA FILTER OUTPUT: {len(output_csv)} CSV, {len(output_pdf)} PDF chunks (from {len(filtered_chunks)} total)")
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"Error filtering by persona: {e}")
            return chunks  # Return all chunks on error
    
    def _calculate_chunk_persona_relevance(
        self,
        chunk: Dict[str, Any],
        associated_stats: List[str],
        relevance_scores: Dict[str, float]
    ) -> float:
        """Calculate how relevant a chunk is to the target persona."""
        chunk_text = chunk.get('content', '').lower()
        
        # Check for direct statistical associations
        stat_relevance = 0.0
        for stat_id in associated_stats:
            if stat_id in chunk.get('citation_ids', []):
                stat_relevance = 1.0
                break
        
        # Check for keyword relevance
        keyword_relevance = 0.0
        for keyword, score in relevance_scores.items():
            if keyword.lower() in chunk_text:
                keyword_relevance = max(keyword_relevance, score)
        
        # Combine relevance scores
        return max(stat_relevance, keyword_relevance * 0.8)
    
    def _separate_by_source_type(self, chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Separate chunks by source type (CSV vs PDF)."""
        csv_chunks = [c for c in chunks if c.get('source_type') == 'csv']
        pdf_chunks = [c for c in chunks if c.get('source_type') == 'pdf']
        
        return csv_chunks, pdf_chunks
    
    async def _semantic_search(
        self,
        query: Any,
        chunks: List[Dict[str, Any]],
        analysis_type: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search on chunks."""
        if not chunks:
            return []

        # Debug input chunks by source type
        csv_input = [c for c in chunks if c.get('source_type') == 'csv']
        pdf_input = [c for c in chunks if c.get('source_type') == 'pdf']
        logger.info(f"🔍 SEMANTIC INPUT: {len(csv_input)} CSV, {len(pdf_input)} PDF chunks for {analysis_type}")
        
        try:
            # Enhance query with analysis type keywords
            query_text = " ".join(query) if isinstance(query, list) else str(query)
            enhanced_query = self._enhance_query_for_analysis_type(query_text, analysis_type)
            logger.info(f"🔍 QUERY EXPANSION DEBUG: Original query='{query_text[:100]}...'")
            logger.info(f"🔍 QUERY EXPANSION DEBUG: Enhanced query='{enhanced_query[:200]}...'")
            logger.info(f"🔍 QUERY EXPANSION DEBUG: Expansion added {len(enhanced_query) - len(query)} characters")
            
            # Get embeddings for query
            query_embedding = await self.vector_adapter.get_embedding(enhanced_query)
            logger.info(f"🔍 QUERY DEBUG: Enhanced query length={len(enhanced_query)}, embedding_length={len(query_embedding) if query_embedding else 0}")
            
            if not query_embedding:
                logger.error("❌ QUERY EMBEDDING FAILED: No embedding generated for query")
                return []
            
            # Calculate similarities
            scored_chunks = []
            chunks_with_embeddings = 0
            chunks_without_embeddings = 0
            
            for i, chunk in enumerate(chunks[:3]):  # Debug first 3 chunks
                logger.info(f"🔍 CHUNK DEBUG {i}: keys={list(chunk.keys()) if isinstance(chunk, dict) else 'Not a dict'}")
                if isinstance(chunk, dict) and 'content' in chunk:
                    content_preview = chunk['content'][:100] + "..." if len(chunk['content']) > 100 else chunk['content']
                    logger.info(f"🔍 CHUNK DEBUG {i}: content_preview='{content_preview}'")
            
            for chunk in chunks:
                chunk_embedding = chunk.get('embedding')
                
                if chunk_embedding:
                    chunks_with_embeddings += 1
                    similarity = await self.vector_adapter.calculate_similarity(
                        query_embedding, chunk_embedding
                    )
                    chunk['similarity_score'] = similarity
                    scored_chunks.append(chunk)
                else:
                    chunks_without_embeddings += 1
                    logger.error(f"❌ PRODUCTION: Chunk missing embedding - this should not happen with proper chunks table storage")
                    logger.error(f"❌ PRODUCTION: Chunk keys: {list(chunk.keys()) if isinstance(chunk, dict) else 'Not a dict'}")
            
            logger.info(f"🔍 EMBEDDING DEBUG: {chunks_with_embeddings} chunks with embeddings, {chunks_without_embeddings} without embeddings")
            if chunks_without_embeddings > 0:
                logger.warning(f"⚠️ EMBEDDING ISSUE: {chunks_without_embeddings} chunks are missing embeddings - they will be skipped from semantic search")
            
            # Sort by similarity and apply threshold
            scored_chunks.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Apply adaptive threshold
            threshold = self._get_adaptive_threshold(scored_chunks, analysis_type)
            
            # Debug similarity scores
            if scored_chunks:
                scores = [c['similarity_score'] for c in scored_chunks]
                max_score = max(scores)
                min_score = min(scores)
                avg_score = sum(scores) / len(scores)
                logger.info(f"🔍 SIMILARITY DEBUG: Max={max_score:.3f}, Min={min_score:.3f}, Avg={avg_score:.3f}, Threshold={threshold:.3f}")
                
                # Show top 3 scores for debugging
                top_3_scores = sorted(scores, reverse=True)[:3]
                logger.info(f"🔍 TOP 3 SCORES: {[f'{s:.3f}' for s in top_3_scores]}")
            else:
                logger.warning("⚠️ NO SCORED CHUNKS: No chunks had embeddings to calculate similarity")
            
            relevant_chunks = [
                c for c in scored_chunks 
                if c['similarity_score'] >= threshold
            ][:top_k]
            
            # Debug filtering results by source type
            csv_relevant = [c for c in relevant_chunks if c.get('source_type') == 'csv']
            pdf_relevant = [c for c in relevant_chunks if c.get('source_type') == 'pdf']
            
            logger.info(f"🔍 SEMANTIC OUTPUT: {len(relevant_chunks)} total relevant chunks (threshold: {threshold:.2f})")
            logger.info(f"🔍 SEMANTIC BREAKDOWN: {len(csv_relevant)} CSV, {len(pdf_relevant)} PDF chunks passed threshold")
            
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            # Fallback to keyword matching
            return self._fallback_keyword_search(query, chunks, top_k)
    
    def _enhance_query_for_analysis_type(self, query: str, analysis_type: str) -> str:
        """Enhance query with intelligent semantic expansion for better evidence retrieval."""
        # Extract key concepts from the assumption query
        expanded_queries = [query]
        
        # Add semantic variations and related concepts
        expanded_queries.extend(self._generate_semantic_variations(query, analysis_type))
        
        # Combine into enriched query
        return " ".join(expanded_queries)
    
    def _generate_semantic_variations(self, query: str, analysis_type: str) -> List[str]:
        """Generate semantic variations of the query to capture indirect evidence."""
        import re
        
        variations = []
        query_lower = query.lower()
        
        # Analysis-type specific semantic expansions
        type_expansions = {
            'pain_points': {
                'keywords': ['problems', 'challenges', 'difficulties', 'frustrations', 'obstacles', 'issues', 'struggles', 'barriers'],
                'patterns': [
                    (r'time-consuming', ['takes too long', 'slow', 'inefficient', 'tedious', 'lengthy process']),
                    (r'confusing', ['unclear', 'complicated', 'difficult to understand', 'hard to figure out', 'overwhelming']),
                    (r'expensive', ['costly', 'high price', 'unaffordable', 'too much money', 'budget constraints']),
                    (r'difficult', ['hard', 'challenging', 'struggle with', 'trouble with', 'cannot easily']),
                    (r'lack of', ['missing', 'no access to', 'unavailable', 'cannot find', 'need more'])
                ]
            },
            'gains_benefits': {
                'keywords': ['benefits', 'advantages', 'value', 'outcomes', 'results', 'improvements', 'success', 'desire', 'want', 'prefer'],
                'patterns': [
                    (r'easier', ['simpler', 'more convenient', 'less effort', 'straightforward', 'user-friendly']),
                    (r'faster', ['quicker', 'saves time', 'more efficient', 'rapid', 'speed up']),
                    (r'better', ['improved', 'enhanced', 'superior', 'higher quality', 'more effective']),
                    (r'affordable', ['cheap', 'low cost', 'budget-friendly', 'economical', 'good value']),
                    (r'practical', ['useful', 'actionable', 'applicable', 'hands-on', 'real-world'])
                ]
            },
            'jobs_to_be_done': {
                'keywords': ['tasks', 'jobs', 'goals', 'objectives', 'trying to', 'need to', 'want to', 'accomplish', 'achieve', 'purpose'],
                'patterns': [
                    (r'meal planning', ['plan meals', 'decide what to eat', 'organize food', 'prepare menus', 'food preparation']),
                    (r'nutrition', ['healthy eating', 'nutritious food', 'balanced diet', 'food quality', 'vitamins']),
                    (r'shopping', ['buying food', 'grocery', 'purchasing', 'getting food', 'market visits']),
                    (r'cooking', ['preparing food', 'making meals', 'food preparation', 'kitchen work', 'recipes'])
                ]
            },
            # REMOVED: size_frequency analysis type
            # 'size_frequency': {
            #     'keywords': ['frequency', 'how often', 'how many', 'percentage', 'number of', 'count', 'statistics', 'data', 'regularly', 'sometimes', 'rarely'],
            #     'patterns': [
            #         (r'often', ['frequently', 'regularly', 'commonly', 'usually', 'typically']),
            #         (r'rarely', ['seldom', 'infrequently', 'not often', 'occasionally', 'sometimes'])
            #     ]
            # },
            # REMOVED: current_solutions analysis type
            # 'current_solutions': {
            #     'keywords': ['current', 'existing', 'currently use', 'now using', 'alternatives', 'workarounds', 'tools', 'methods', 'approaches'],
            #     'patterns': [
            #         (r'current solutions', ['what they use now', 'existing tools', 'current methods', 'how they currently', 'present approach'])
            #     ]
            # }
        }
        
        expansion_config = type_expansions.get(analysis_type, {'keywords': [], 'patterns': []})
        
        # Add general keywords for this analysis type
        if expansion_config['keywords']:
            variations.append(' '.join(expansion_config['keywords'][:5]))  # Top 5 keywords
        
        # Add pattern-based semantic variations
        for pattern, synonyms in expansion_config.get('patterns', []):
            if re.search(pattern, query_lower):
                variations.extend(synonyms[:3])  # Top 3 synonyms per pattern
        
        # Add contextual inference keywords based on common research data patterns
        contextual_keywords = self._infer_contextual_keywords(query_lower, analysis_type)
        if contextual_keywords:
            variations.append(contextual_keywords)
        
        return variations
    
    def _infer_contextual_keywords(self, query: str, analysis_type: str) -> str:
        """Infer contextual keywords that might appear in research data related to the query."""
        # Map assumption concepts to likely research data patterns
        contextual_mappings = {
            'meal planning': 'food preparation cooking grocery shopping family meals',
            'nutrition': 'healthy diet vitamins balanced meals food quality',
            'time-consuming': 'busy schedule limited time work family responsibilities',
            'confusing': 'information overload unclear instructions complicated',
            'low-income': 'budget cost money financial affordable cheap',
            'caregivers': 'family children parents household dependents',
            'education': 'learning knowledge information training guidance',
            'access': 'availability resources services programs support'
        }
        
        # Find matching concepts in query
        for concept, keywords in contextual_mappings.items():
            if concept in query:
                return keywords
        
        return ''
    
    def _get_adaptive_threshold(self, scored_chunks: List[Dict[str, Any]], analysis_type: str) -> float:
        """Get adaptive similarity threshold based on available data quality and analysis type."""
        if not scored_chunks:
            return self.adaptive_threshold_min
        
        # Calculate enhanced score distribution
        scores = [c['similarity_score'] for c in scored_chunks]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        std_dev = (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5
        
        # Analysis-specific base thresholds - LOWERED for better recall with semantic expansion
        # The intelligent query expansion compensates for lower thresholds
        # UPDATED: Removed size_frequency and current_solutions
        analysis_thresholds = {
            'pain_points': 0.55,      # Lower threshold, rely on semantic expansion
            # REMOVED: 'size_frequency': 0.50,   # Market size can use broader evidence  
            # REMOVED: 'current_solutions': 0.50, # Solutions benefit from related concepts
            'gains_benefits': 0.55,   # Benefits use semantic variations
            'jobs_to_be_done': 0.55   # JTBD uses contextual keywords
        }
        
        base_threshold = analysis_thresholds.get(analysis_type, 0.55)
        
        # Enhanced adaptive logic - ensure we always get some results
        if max_score > 0.85 and std_dev > 0.1:
            # Excellent matches with good distribution
            return min(base_threshold + 0.05, max_score - 0.08)
        elif max_score > 0.75:
            # Good quality matches - use base threshold
            return min(base_threshold, max_score - 0.1)
        elif max_score > 0.5:
            # Medium quality - enterprise-grade threshold adjustment
            return max(0.30, min(base_threshold - 0.15, max_score - 0.03))
        else:
            # Lower quality - enterprise requires comprehensive coverage
            return max(self.adaptive_threshold_min, min(0.30, max_score - 0.02))
    
    def _fallback_keyword_search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based search when semantic search fails."""
        query_words = set(query.lower().split())
        
        scored_chunks = []
        for chunk in chunks:
            content = chunk.get('content', '').lower()
            content_words = set(content.split())
            
            # Calculate keyword overlap
            overlap = len(query_words.intersection(content_words))
            score = overlap / len(query_words) if query_words else 0
            
            chunk['similarity_score'] = score
            scored_chunks.append(chunk)
        
        scored_chunks.sort(key=lambda x: x['similarity_score'], reverse=True)
        return scored_chunks[:top_k]
    
    async def _ensure_minimum_representation(
        self,
        chunks: List[Dict[str, Any]],
        min_count: int,
        source_type: str
    ) -> List[Dict[str, Any]]:
        """Ensure minimum representation from a source type."""
        if len(chunks) >= min_count:
            return chunks[:min_count * 2]  # Allow some extra for balancing
        
        # If insufficient relevant chunks, include all available with adaptive minimum
        if len(chunks) > 0:
            # Be more flexible - if we have any chunks, use them
            logger.info(f"🔧 ADAPTIVE MINIMUM: Using {len(chunks)} {source_type} chunks (below target of {min_count})")
            return chunks
        else:
            logger.warning(f"⚠️ NO {source_type.upper()} CHUNKS: No {source_type} chunks available")
            return []
    
    async def _optimize_content_selection(
        self,
        csv_chunks: List[Dict[str, Any]],
        pdf_chunks: List[Dict[str, Any]],
        token_budget: int,
        analysis_type: str,
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Use token budget optimizer for intelligent content selection.
        
        Args:
            csv_chunks: Available CSV chunks
            pdf_chunks: Available PDF chunks
            token_budget: Maximum tokens available
            analysis_type: Type of analysis for relevance scoring
            persona_id: Optional persona context
            
        Returns:
            Optimized list of selected chunks
        """
        try:
            # Get token optimizer
            optimizer = get_token_optimizer()
            
            # Combine all available content
            all_content = []
            
            # Add CSV chunks with metadata
            for chunk in csv_chunks:
                all_content.append({
                    **chunk,
                    'source_type': 'csv',
                    'estimated_tokens': len(chunk.get('content', '')) // self.chars_per_token
                })
            
            # Add PDF chunks with metadata
            for chunk in pdf_chunks:
                all_content.append({
                    **chunk,
                    'source_type': 'pdf',
                    'estimated_tokens': len(chunk.get('content', '')) // self.chars_per_token
                })
            
            # Get persona context if available
            persona_context = None
            if persona_id:
                persona_context = await self._get_persona_context(persona_id)
            
            # Define source balance requirements
            source_balance_requirements = {
                'csv': 0.3,  # Minimum 30% CSV content
                'pdf': 0.4   # Minimum 40% PDF content
            }
            
            # Optimize content selection
            optimization_result = await optimizer.optimize_content_selection(
                available_content=all_content,
                token_budget=token_budget,
                analysis_type=analysis_type,
                persona_context=persona_context,
                source_balance_requirements=source_balance_requirements
            )
            
            selected_content = optimization_result['selected_content']
            
            # Add optimization metadata to chunks
            for chunk in selected_content:
                chunk['optimization_metadata'] = {
                    'information_density': optimization_result['information_density'],
                    'token_utilization': optimization_result['optimization_metrics']['token_utilization'],
                    'relevance_score': chunk.get('relevance_score', 0.0),
                    'optimized_selection': True
                }
            
            logger.info(
                f"Optimized selection: {len(selected_content)} chunks, "
                f"density: {optimization_result['information_density']:.3f}, "
                f"utilization: {optimization_result['optimization_metrics']['token_utilization']:.3f}"
            )
            
            return selected_content
            
        except Exception as e:
            logger.warning(f"Token optimization failed, falling back to basic balancing: {e}")
            # Fallback to basic balancing
            return await self._balance_within_token_budget(csv_chunks, pdf_chunks, token_budget)
    
    async def _get_persona_context(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get persona context for optimization."""
        try:
            # This would typically fetch from the personas data
            # For now, return a basic structure
            return {
                'id': persona_id,
                'description': f"Persona {persona_id}",
                'role': 'user',
                'goals': [],
                'challenges': []
            }
        except Exception as e:
            logger.warning(f"Could not get persona context for {persona_id}: {e}")
            return None
    
    async def _balance_within_token_budget(
        self,
        csv_chunks: List[Dict[str, Any]],
        pdf_chunks: List[Dict[str, Any]],
        token_budget: int
    ) -> List[Dict[str, Any]]:
        """Balance chunks within token budget with proportional allocation."""
        total_chunks = len(csv_chunks) + len(pdf_chunks)
        if total_chunks == 0:
            return []
        
        # Calculate proportional allocation
        csv_ratio = len(csv_chunks) / total_chunks
        pdf_ratio = len(pdf_chunks) / total_chunks
        
        # Allocate tokens proportionally but ensure minimums
        csv_tokens = max(int(token_budget * csv_ratio), 500)  # Minimum 500 tokens for CSV
        pdf_tokens = max(int(token_budget * pdf_ratio), 800)  # Minimum 800 tokens for PDF
        
        # Adjust if over budget
        total_allocated = csv_tokens + pdf_tokens
        if total_allocated > token_budget:
            scale_factor = token_budget / total_allocated
            csv_tokens = int(csv_tokens * scale_factor)
            pdf_tokens = int(pdf_tokens * scale_factor)
        
        # Select chunks within token budgets
        selected_csv = self._select_chunks_within_budget(csv_chunks, csv_tokens)
        selected_pdf = self._select_chunks_within_budget(pdf_chunks, pdf_tokens)
        
        # Combine and add selection metadata
        balanced_chunks = selected_csv + selected_pdf
        
        for chunk in balanced_chunks:
            chunk['selection_metadata'] = {
                'token_budget_used': True,
                'source_balancing_applied': True,
                'selection_priority': chunk.get('similarity_score', 0.0)
            }
        
        logger.info(f"Balanced selection: {len(selected_csv)} CSV, {len(selected_pdf)} PDF chunks")
        return balanced_chunks
    
    def _select_chunks_within_budget(
        self,
        chunks: List[Dict[str, Any]],
        token_budget: int
    ) -> List[Dict[str, Any]]:
        """Select chunks that fit within the specified token budget."""
        selected = []
        current_tokens = 0
        
        # Sort by similarity score (highest first)
        sorted_chunks = sorted(chunks, key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        for chunk in sorted_chunks:
            # Estimate chunk tokens
            content = chunk.get('content', '')
            chunk_tokens = len(content) // self.chars_per_token
            
            if current_tokens + chunk_tokens <= token_budget:
                selected.append(chunk)
                current_tokens += chunk_tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = token_budget - current_tokens
                if remaining_tokens > 50:  # Minimum useful chunk size
                    truncated_content = content[:remaining_tokens * self.chars_per_token]
                    truncated_chunk = chunk.copy()
                    truncated_chunk['content'] = truncated_content + "... [truncated]"
                    truncated_chunk['truncated'] = True
                    selected.append(truncated_chunk)
                break
        
        return selected
    
    async def get_evidence_summary(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of available evidence for validation purposes.
        
        Returns:
            Dictionary with evidence availability and distribution
        """
        try:
            all_chunks = await self._get_research_chunks(project_id, tenant_id)
            
            if not all_chunks:
                return {'available': False, 'reason': 'No evidence chunks found'}
            
            csv_chunks, pdf_chunks = self._separate_by_source_type(all_chunks)
            
            summary = {
                'available': True,
                'total_chunks': len(all_chunks),
                'csv_chunks': len(csv_chunks),
                'pdf_chunks': len(pdf_chunks),
                'source_balance': {
                    'csv_ratio': len(csv_chunks) / len(all_chunks) if all_chunks else 0,
                    'pdf_ratio': len(pdf_chunks) / len(all_chunks) if all_chunks else 0
                },
                'persona_filtered': persona_id is not None,
                'estimated_total_tokens': len(all_chunks) * self.avg_chunk_tokens
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting evidence summary: {e}")
            return {'available': False, 'reason': f'Error: {str(e)}'}