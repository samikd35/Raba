"""
Enhanced Correlation Engine with Source Balancing - Two-Tier RAG System

Handles semantic similarity matching between assumptions and research data with
enhanced source balancing to prevent PDF invisibility and ensure proportional
representation from all data sources.

Key Enhancements:
- Enforces minimum PDF inclusion to prevent invisibility
- Implements persona-aware query generation
- Uses adaptive similarity thresholds
- Provides proportional token allocation between source types
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio

# Import existing embedding service
from src.mint.api.services.ai.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class CorrelationError(Exception):
    """Custom exception for correlation engine errors"""
    pass


DEFAULT_CONTEXT_TOKEN_BUDGET = 4_000  # Actual data budget after prompt structure


class CorrelationEngine:
    """
    Enhanced engine for finding semantic correlations with source balancing.
    
    Uses embeddings-based similarity search with enhanced source balancing to ensure
    proportional representation from CSV and PDF sources, preventing PDF invisibility
    and maintaining balanced analysis perspectives.
    
    Key Features:
    - Enforces minimum PDF inclusion (prevents PDF invisibility)
    - Implements persona-aware query generation
    - Uses adaptive similarity thresholds
    - Provides proportional token allocation between source types
    """
    
    # Analysis type specific keywords for enhanced correlation
    ANALYSIS_TYPE_KEYWORDS = {
        "pain": [
            "problem", "issue", "challenge", "difficulty", "frustration", "pain point",
            "struggle", "obstacle", "barrier", "complaint", "concern", "worry",
            "annoying", "irritating", "time-consuming", "expensive", "inefficient",
            "hard", "difficult", "complicated", "confusing", "stressful"
        ],
        "size": [
            "frequency", "often", "always", "never", "sometimes", "usually", "rarely",
            "daily", "weekly", "monthly", "yearly", "percentage", "percent", "%",
            "number", "count", "amount", "quantity", "volume", "scale", "size",
            "many", "few", "most", "all", "some", "majority", "minority",
            "statistics", "data", "survey", "study", "research", "findings"
        ],
        "solution": [
            "solution", "alternative", "current", "existing", "competitor", "competition",
            "tool", "software", "platform", "service", "product", "method", "approach",
            "way", "how", "process", "system", "technology", "vendor", "provider",
            "using", "use", "utilize", "implement", "adopt", "switch", "replace",
            "better", "worse", "comparison", "versus", "vs", "compared to"
        ],
        "gains": [
            "benefit", "advantage", "value", "gain", "improvement", "better", "faster",
            "cheaper", "easier", "more efficient", "save", "saving", "reduce", "increase",
            "enhance", "optimize", "streamline", "automate", "simplify", "accelerate",
            "ROI", "return on investment", "cost savings", "time savings", "productivity",
            "revenue", "profit", "growth", "success", "achievement", "outcome", "result"
        ],
        "jtbd": [
            "job", "task", "activity", "workflow", "process", "procedure", "step",
            "goal", "objective", "purpose", "need", "want", "desire", "requirement",
            "responsibility", "duty", "role", "function", "capability", "outcome",
            "accomplish", "achieve", "complete", "finish", "deliver", "perform",
            "when", "where", "why", "how", "what", "who", "context", "situation"
        ]
    }
    
    # Default similarity thresholds
    DEFAULT_SIMILARITY_THRESHOLD = 0.7
    MIN_SIMILARITY_THRESHOLD = 0.5
    MAX_SIMILARITY_THRESHOLD = 0.95
    
    def __init__(self):
        """Initialize the enhanced correlation engine with source balancing."""
        self.embedding_service = get_embedding_service()
        self._query_cache = {}  # Cache for generated queries
        self._embedding_cache = {}  # Cache for embeddings
        
        # Source balancing configuration
        self.min_pdf_chunks = 3  # Minimum PDF chunks to include
        self.min_csv_chunks = 2  # Minimum CSV chunks to include
        self.pdf_token_ratio = 0.6  # Prefer PDF content (60% of tokens)
        self.csv_token_ratio = 0.4  # CSV content gets 40% of tokens
        
        # Adaptive threshold configuration
        self.base_similarity_threshold = 0.7
        self.relaxed_similarity_threshold = 0.4
        self.high_quality_threshold = 0.85
    
    async def find_relevant_data(
        self,
        assumption: Dict[str, Any],
        research_chunks: List[Dict[str, Any]],
        analysis_type: str,
        top_k: int = 10,
        similarity_threshold: float = 0.5,
        use_llm_validation: bool = False,
        persona_context: Optional[Dict[str, Any]] = None,
        enforce_source_balancing: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find research data chunks relevant to a specific assumption with source balancing.
        
        Enhanced version that ensures balanced representation from CSV and PDF sources,
        preventing PDF invisibility and maintaining proportional token allocation.
        
        Args:
            assumption: Assumption dictionary with text and metadata
            research_chunks: List of research chunks with embeddings
            analysis_type: Type of analysis ('pain', 'size', 'solution', 'gains', 'jtbd')
            top_k: Maximum number of chunks to return
            similarity_threshold: Minimum similarity score for relevance
            use_llm_validation: Whether to use LLM for additional validation
            persona_context: Optional persona context for enhanced query generation
            enforce_source_balancing: Whether to enforce minimum source representation
            
        Returns:
            List of relevant research chunks with similarity scores and source balancing
            
        Raises:
            CorrelationError: If correlation fails
        """
        try:
            if not assumption or not research_chunks:
                return []
            
            valid_analysis_types = ["pain", "size", "solution", "gains", "jtbd", "general"]
            if analysis_type not in valid_analysis_types:
                raise CorrelationError(f"Invalid analysis type: {analysis_type}")
            
            # Validate similarity threshold
            similarity_threshold = max(
                self.MIN_SIMILARITY_THRESHOLD,
                min(similarity_threshold, self.MAX_SIMILARITY_THRESHOLD)
            )
            
            # Generate persona-aware correlation query
            query = self._create_persona_aware_correlation_query(
                assumption.get("text", ""),
                assumption.get("persona_name", ""),
                analysis_type,
                persona_context
            )
            
            logger.info(f"Finding relevant data for assumption '{assumption.get('id', 'unknown')}' "
                       f"with analysis type '{analysis_type}' using semantic similarity")
            
            # Perform source-balanced semantic similarity search
            if enforce_source_balancing:
                relevant_chunks = await self._source_balanced_similarity_search(
                    query, research_chunks, top_k, similarity_threshold, analysis_type
                )
            else:
                relevant_chunks = await self._semantic_similarity_search(
                    query, research_chunks, top_k * 2, similarity_threshold
                )
            
            # Apply enhanced filtering and ranking with source balancing
            filtered_chunks = await self._enhanced_filter_and_rank_chunks(
                relevant_chunks, analysis_type, assumption, persona_context
            )
            
            # Optional: Use LLM for additional validation of top candidates
            if use_llm_validation and len(filtered_chunks) > 0:
                filtered_chunks = await self._llm_validate_correlations(
                    filtered_chunks[:top_k * 2], assumption, analysis_type
                )
            
            # Return top-k results
            final_chunks = filtered_chunks[:top_k]
            
            logger.info(f"Found {len(final_chunks)} relevant chunks for assumption "
                       f"'{assumption.get('id', 'unknown')}' with analysis type '{analysis_type}'")
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error finding relevant data for assumption: {e}")
            raise CorrelationError(f"Failed to find relevant data: {str(e)}")
    
    async def _llm_validate_correlations(
        self,
        candidate_chunks: List[Dict[str, Any]],
        assumption: Dict[str, Any],
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to validate and re-rank correlation candidates.
        
        This provides an additional layer of intelligent validation beyond embeddings.
        
        Args:
            candidate_chunks: Chunks to validate
            assumption: Original assumption
            analysis_type: Type of analysis
            
        Returns:
            LLM-validated and re-ranked chunks
        """
        try:
            # This would integrate with the existing AI service
            # For now, return the chunks as-is (placeholder for future enhancement)
            logger.info(f"LLM validation requested for {len(candidate_chunks)} chunks "
                       f"(analysis_type: {analysis_type})")
            
            # TODO: Implement LLM-based validation using existing AI service
            # This could ask the LLM: "Is this research data relevant to validating 
            # the assumption about [assumption_text] specifically for [analysis_type]?"
            
            return candidate_chunks
            
        except Exception as e:
            logger.error(f"Error in LLM validation: {e}")
            return candidate_chunks  # Fallback to original ranking
    
    def _create_persona_aware_correlation_query(
        self,
        assumption_text: str,
        persona_name: str,
        analysis_type: str,
        persona_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a persona-aware correlation query that considers target persona context.
        
        Enhanced version that incorporates persona characteristics, demographics,
        and behavioral patterns into the search query for more targeted results.
        
        Args:
            assumption_text: The assumption text
            persona_name: Name of the persona
            analysis_type: Type of analysis
            persona_context: Optional persona context with demographics and characteristics
            
        Returns:
            Persona-aware correlation query string
        """
        # Create enhanced cache key
        persona_key = ""
        if persona_context:
            persona_key = f"|{persona_context.get('id', '')}"
        
        cache_key = f"{assumption_text}|{persona_name}|{analysis_type}{persona_key}"
        
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        # Build persona-aware query
        query_parts = []
        
        # Start with the core assumption
        if assumption_text:
            query_parts.append(assumption_text)
        
        # Add enhanced persona context
        if persona_context:
            # Add persona demographics
            demographics = persona_context.get('demographics', {})
            if demographics:
                demo_parts = []
                for key, value in demographics.items():
                    if value:
                        demo_parts.append(f"{key}: {value}")
                if demo_parts:
                    query_parts.append(f"Demographics: {', '.join(demo_parts)}")
            
            # Add persona characteristics
            characteristics = persona_context.get('characteristics', [])
            if characteristics:
                query_parts.append(f"User characteristics: {', '.join(characteristics)}")
            
            # Add persona goals and motivations
            goals = persona_context.get('goals', [])
            if goals:
                query_parts.append(f"Goals and motivations: {', '.join(goals)}")
        
        elif persona_name:
            query_parts.append(f"For {persona_name} users:")
        
        # Add analysis-type specific context with persona considerations
        persona_analysis_contexts = {
            "pain": [
                "What specific problems or frustrations does this persona experience?",
                "What challenges are unique to this user type?",
                "What pain points matter most to this demographic?",
                "What obstacles prevent this persona from achieving their goals?"
            ],
            "size": [
                "How frequently does this persona encounter this situation?",
                "What percentage of this user type experiences this?",
                "How common is this issue among similar users?",
                "What is the scale of this problem for this demographic?"
            ],
            "solution": [
                "What tools or methods does this persona currently use?",
                "What alternatives are popular with this user type?",
                "How does this demographic typically solve similar problems?",
                "What existing solutions appeal to this persona?"
            ],
            "gains": [
                "What benefits would matter most to this persona?",
                "What value does this user type prioritize?",
                "What improvements would this demographic appreciate?",
                "What outcomes align with this persona's goals?"
            ],
            "jtbd": [
                "What jobs is this persona trying to accomplish?",
                "What workflows are typical for this user type?",
                "What are this persona's primary objectives?",
                "In what context does this persona operate?"
            ]
        }
        
        # Add persona-specific analysis context
        if analysis_type in persona_analysis_contexts:
            context_questions = persona_analysis_contexts[analysis_type]
            query_parts.extend(context_questions)
        
        # Combine into persona-aware query
        query = " ".join(query_parts)
        
        # Cache the query
        self._query_cache[cache_key] = query
        
        return query
    
    async def _source_balanced_similarity_search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
        similarity_threshold: float,
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search with enforced source balancing.
        
        Ensures minimum representation from PDF sources to prevent invisibility
        and maintains proportional token allocation between source types.
        
        Args:
            query: Search query
            chunks: List of chunks with embeddings
            top_k: Maximum number of results
            similarity_threshold: Base similarity threshold
            analysis_type: Type of analysis for adaptive thresholding
            
        Returns:
            Source-balanced list of chunks with similarity scores
        """
        try:
            # Separate chunks by source type
            pdf_chunks = [c for c in chunks if c.get('source_type') == 'pdf']
            csv_chunks = [c for c in chunks if c.get('source_type') == 'csv']
            
            logger.info(f"Source balancing: {len(pdf_chunks)} PDF chunks, {len(csv_chunks)} CSV chunks available")
            
            # Perform similarity search on each source type separately
            pdf_results = await self._semantic_similarity_search(
                query, pdf_chunks, top_k, similarity_threshold
            )
            csv_results = await self._semantic_similarity_search(
                query, csv_chunks, top_k, similarity_threshold
            )
            
            # Apply adaptive thresholding if insufficient results
            if len(pdf_results) < self.min_pdf_chunks and pdf_chunks:
                logger.info(f"Insufficient PDF results ({len(pdf_results)}), applying adaptive threshold")
                relaxed_threshold = max(self.relaxed_similarity_threshold, similarity_threshold * 0.6)
                pdf_results = await self._semantic_similarity_search(
                    query, pdf_chunks, self.min_pdf_chunks * 2, relaxed_threshold
                )
            
            if len(csv_results) < self.min_csv_chunks and csv_chunks:
                logger.info(f"Insufficient CSV results ({len(csv_results)}), applying adaptive threshold")
                relaxed_threshold = max(self.relaxed_similarity_threshold, similarity_threshold * 0.6)
                csv_results = await self._semantic_similarity_search(
                    query, csv_chunks, self.min_csv_chunks * 2, relaxed_threshold
                )
            
            # Enforce minimum representation
            pdf_selected = pdf_results[:max(self.min_pdf_chunks, len(pdf_results))]
            csv_selected = csv_results[:max(self.min_csv_chunks, len(csv_results))]
            
            # Apply proportional token allocation
            balanced_results = self._apply_proportional_token_allocation(
                pdf_selected, csv_selected, top_k, analysis_type
            )
            
            logger.info(f"Source balanced results: {len([c for c in balanced_results if c.get('source_type') == 'pdf'])} PDF, "
                       f"{len([c for c in balanced_results if c.get('source_type') == 'csv'])} CSV chunks")
            
            return balanced_results
            
        except Exception as e:
            logger.error(f"Error in source-balanced similarity search: {e}")
            # Fallback to regular similarity search
            return await self._semantic_similarity_search(query, chunks, top_k, similarity_threshold)
    
    def _apply_proportional_token_allocation(
        self,
        pdf_chunks: List[Dict[str, Any]],
        csv_chunks: List[Dict[str, Any]],
        max_chunks: int,
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """
        Apply proportional token allocation between source types.
        
        Ensures consistent balancing across analyses while respecting
        the relative importance of different source types for different analyses.
        
        Args:
            pdf_chunks: PDF chunks to allocate
            csv_chunks: CSV chunks to allocate
            max_chunks: Maximum total chunks to return
            analysis_type: Type of analysis for allocation weighting
            
        Returns:
            Proportionally allocated chunks
        """
        try:
            # Adjust allocation ratios based on analysis type
            analysis_ratios = {
                'pain': {'pdf': 0.7, 'csv': 0.3},      # Pain analysis benefits from qualitative data
                'size': {'pdf': 0.4, 'csv': 0.6},      # Size analysis needs quantitative data
                'solution': {'pdf': 0.6, 'csv': 0.4},  # Solution analysis benefits from interviews
                'gains': {'pdf': 0.6, 'csv': 0.4},     # Gains analysis benefits from qualitative insights
                'jtbd': {'pdf': 0.8, 'csv': 0.2},      # JTBD analysis heavily relies on interviews
                'general': {'pdf': 0.6, 'csv': 0.4}    # Default balanced allocation
            }
            
            ratios = analysis_ratios.get(analysis_type, analysis_ratios['general'])
            
            # Calculate target allocation
            target_pdf_chunks = max(1, int(max_chunks * ratios['pdf']))
            target_csv_chunks = max(1, int(max_chunks * ratios['csv']))
            
            # Ensure we don't exceed available chunks
            actual_pdf_chunks = min(target_pdf_chunks, len(pdf_chunks))
            actual_csv_chunks = min(target_csv_chunks, len(csv_chunks))
            
            # Adjust if we have remaining capacity
            total_allocated = actual_pdf_chunks + actual_csv_chunks
            if total_allocated < max_chunks:
                remaining = max_chunks - total_allocated
                
                # Distribute remaining capacity proportionally
                if len(pdf_chunks) > actual_pdf_chunks:
                    additional_pdf = min(remaining, len(pdf_chunks) - actual_pdf_chunks)
                    actual_pdf_chunks += additional_pdf
                    remaining -= additional_pdf
                
                if remaining > 0 and len(csv_chunks) > actual_csv_chunks:
                    additional_csv = min(remaining, len(csv_chunks) - actual_csv_chunks)
                    actual_csv_chunks += additional_csv
            
            # Select final chunks
            selected_pdf = pdf_chunks[:actual_pdf_chunks]
            selected_csv = csv_chunks[:actual_csv_chunks]
            
            # Combine and sort by similarity score
            all_selected = selected_pdf + selected_csv
            all_selected.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            # Add allocation metadata
            for chunk in all_selected:
                chunk['source_balancing'] = {
                    'analysis_type': analysis_type,
                    'target_ratio': ratios[chunk.get('source_type', 'unknown')],
                    'enforced_minimum': True
                }
            
            logger.info(f"Proportional allocation for {analysis_type}: {actual_pdf_chunks} PDF, {actual_csv_chunks} CSV chunks")
            
            return all_selected[:max_chunks]
            
        except Exception as e:
            logger.error(f"Error in proportional token allocation: {e}")
            # Fallback to simple combination
            combined = (pdf_chunks + csv_chunks)[:max_chunks]
            combined.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            return combined
    
    async def _enhanced_filter_and_rank_chunks(
        self,
        chunks: List[Dict[str, Any]],
        analysis_type: str,
        assumption: Dict[str, Any],
        persona_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhanced filtering and ranking with persona awareness and source balancing.
        
        Incorporates persona relevance scoring and maintains source balance
        while applying semantic filtering.
        
        Args:
            chunks: List of chunks with similarity scores
            analysis_type: Type of analysis
            assumption: Original assumption for context
            persona_context: Optional persona context for relevance scoring
            
        Returns:
            Enhanced filtered and ranked chunks
        """
        try:
            if not chunks:
                return []
            
            # Apply enhanced relevance scoring
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                similarity_score = chunk.get("similarity_score", 0)
                
                # Calculate semantic relevance (existing logic)
                semantic_indicators = self._get_semantic_indicators(analysis_type)
                semantic_score = self._calculate_semantic_relevance(content, semantic_indicators)
                
                # Calculate persona relevance if context provided
                persona_score = 0.5  # Default neutral score
                if persona_context:
                    persona_score = self._calculate_persona_relevance(content, persona_context)
                
                # Calculate source type bonus (slight preference for balanced representation)
                source_bonus = self._calculate_source_balance_bonus(chunk, chunks)
                
                # Weighted combination of all scores
                combined_score = (
                    similarity_score * 0.7 +      # Primary: embedding similarity
                    semantic_score * 0.15 +       # Secondary: semantic indicators
                    persona_score * 0.1 +         # Tertiary: persona relevance
                    source_bonus * 0.05           # Quaternary: source balance
                )
                
                chunk["relevance_score"] = combined_score
                chunk["semantic_score"] = semantic_score
                chunk["persona_score"] = persona_score
                chunk["source_bonus"] = source_bonus
                chunk["analysis_type"] = analysis_type
                
                # Enhanced confidence scoring
                if similarity_score >= self.high_quality_threshold:
                    chunk["confidence"] = "high"
                elif similarity_score >= self.base_similarity_threshold:
                    chunk["confidence"] = "medium"
                else:
                    chunk["confidence"] = "low"
            
            # Re-sort by combined relevance score
            chunks.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            # Apply enhanced context window management
            filtered_chunks = self._enhanced_context_window_management(chunks, analysis_type)
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"Error in enhanced filtering and ranking: {e}")
            return chunks  # Return original chunks on error
    
    def _calculate_persona_relevance(self, content: str, persona_context: Dict[str, Any]) -> float:
        """
        Calculate how relevant content is to the target persona.
        
        Args:
            content: Chunk content to evaluate
            persona_context: Persona context with demographics and characteristics
            
        Returns:
            Persona relevance score (0-1)
        """
        try:
            relevance_signals = 0
            total_signals = 0
            
            # Check demographic alignment
            demographics = persona_context.get('demographics', {})
            for demo_key, demo_value in demographics.items():
                if demo_value and isinstance(demo_value, str):
                    total_signals += 1
                    if demo_value.lower() in content:
                        relevance_signals += 1
            
            # Check characteristic alignment
            characteristics = persona_context.get('characteristics', [])
            for characteristic in characteristics:
                if isinstance(characteristic, str):
                    total_signals += 1
                    if characteristic.lower() in content:
                        relevance_signals += 1
            
            # Check goal alignment
            goals = persona_context.get('goals', [])
            for goal in goals:
                if isinstance(goal, str):
                    total_signals += 1
                    # Use semantic matching for goals
                    if self._has_semantic_concept(content, goal.lower()):
                        relevance_signals += 1
            
            # Calculate relevance score
            if total_signals > 0:
                return relevance_signals / total_signals
            else:
                return 0.5  # Neutral score if no persona signals
                
        except Exception as e:
            logger.error(f"Error calculating persona relevance: {e}")
            return 0.5
    
    def _calculate_source_balance_bonus(self, chunk: Dict[str, Any], all_chunks: List[Dict[str, Any]]) -> float:
        """
        Calculate a small bonus for maintaining source balance.
        
        Args:
            chunk: Current chunk to evaluate
            all_chunks: All chunks in the current selection
            
        Returns:
            Source balance bonus (0-1)
        """
        try:
            chunk_source = chunk.get('source_type', 'unknown')
            
            # Count source distribution in current selection
            source_counts = {}
            for c in all_chunks:
                source = c.get('source_type', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            total_chunks = len(all_chunks)
            if total_chunks == 0:
                return 0.5
            
            # Calculate current source ratio
            current_ratio = source_counts.get(chunk_source, 0) / total_chunks
            
            # Ideal ratios (prefer slight PDF emphasis for qualitative insights)
            ideal_ratios = {'pdf': 0.6, 'csv': 0.4}
            ideal_ratio = ideal_ratios.get(chunk_source, 0.5)
            
            # Bonus for chunks that help achieve ideal balance
            if current_ratio < ideal_ratio:
                return 0.8  # Bonus for underrepresented source
            elif current_ratio > ideal_ratio * 1.5:
                return 0.2  # Penalty for overrepresented source
            else:
                return 0.5  # Neutral for balanced representation
                
        except Exception as e:
            logger.error(f"Error calculating source balance bonus: {e}")
            return 0.5
    
    def _enhanced_context_window_management(
        self,
        chunks: List[Dict[str, Any]],
        analysis_type: str,
        max_total_tokens: int = DEFAULT_CONTEXT_TOKEN_BUDGET
    ) -> List[Dict[str, Any]]:
        """
        Enhanced context window management with source balancing preservation.
        
        Ensures that source balancing is maintained even when truncating for token limits.
        
        Args:
            chunks: List of chunks to manage
            analysis_type: Type of analysis
            max_total_tokens: Maximum total tokens to include
            
        Returns:
            Filtered chunks within token limit with preserved source balance
        """
        try:
            if not chunks:
                return []
            
            # Separate by source type for balanced selection
            pdf_chunks = [c for c in chunks if c.get('source_type') == 'pdf']
            csv_chunks = [c for c in chunks if c.get('source_type') == 'csv']
            
            # Calculate proportional token allocation
            analysis_ratios = {
                'pain': {'pdf': 0.7, 'csv': 0.3},
                'size': {'pdf': 0.4, 'csv': 0.6},
                'solution': {'pdf': 0.6, 'csv': 0.4},
                'gains': {'pdf': 0.6, 'csv': 0.4},
                'jtbd': {'pdf': 0.8, 'csv': 0.2},
                'general': {'pdf': 0.6, 'csv': 0.4}
            }
            
            ratios = analysis_ratios.get(analysis_type, analysis_ratios['general'])
            
            pdf_token_budget = int(max_total_tokens * ratios['pdf'])
            csv_token_budget = int(max_total_tokens * ratios['csv'])
            
            # Select chunks within budget for each source type
            selected_pdf = self._select_chunks_within_token_budget(pdf_chunks, pdf_token_budget)
            selected_csv = self._select_chunks_within_token_budget(csv_chunks, csv_token_budget)
            
            # Combine and maintain order by relevance score
            all_selected = selected_pdf + selected_csv
            all_selected.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            # Calculate actual token usage
            total_tokens = sum(
                chunk.get("token_count", len(chunk.get("content", "").split()) * 1.3)
                for chunk in all_selected
            )
            
            logger.info(f"Enhanced context window: {len(all_selected)} chunks, {total_tokens} tokens "
                       f"({len(selected_pdf)} PDF + {len(selected_csv)} CSV) for {analysis_type}")
            
            return all_selected
            
        except Exception as e:
            logger.error(f"Error in enhanced context window management: {e}")
            return chunks[:10]  # Fallback
    
    def _select_chunks_within_token_budget(
        self,
        chunks: List[Dict[str, Any]],
        token_budget: int
    ) -> List[Dict[str, Any]]:
        """
        Select chunks that fit within the specified token budget.
        
        Args:
            chunks: Chunks to select from
            token_budget: Available token budget
            
        Returns:
            Selected chunks within budget
        """
        selected = []
        current_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = chunk.get("token_count", len(chunk.get("content", "").split()) * 1.3)
            
            if current_tokens + chunk_tokens <= token_budget:
                selected.append(chunk)
                current_tokens += chunk_tokens
            else:
                # Try to fit a truncated version if there's meaningful space left
                remaining_tokens = token_budget - current_tokens
                if remaining_tokens > 100:  # Minimum useful chunk size
                    truncated_chunk = self._truncate_chunk_to_budget(chunk, remaining_tokens)
                    if truncated_chunk:
                        selected.append(truncated_chunk)
                break
        
        return selected
    
    def _truncate_chunk_to_budget(self, chunk: Dict[str, Any], token_budget: int) -> Optional[Dict[str, Any]]:
        """
        Truncate a chunk to fit within the token budget.
        
        Args:
            chunk: Chunk to truncate
            token_budget: Available token budget
            
        Returns:
            Truncated chunk or None if not viable
        """
        try:
            content = chunk.get("content", "")
            words = content.split()
            max_words = int(token_budget / 1.3)  # Approximate word count
            
            if max_words > 20:  # Minimum meaningful content
                truncated_chunk = chunk.copy()
                truncated_chunk["content"] = " ".join(words[:max_words]) + "... [truncated for token budget]"
                truncated_chunk["token_count"] = token_budget
                truncated_chunk["truncated"] = True
                return truncated_chunk
            
            return None
            
        except Exception as e:
            logger.error(f"Error truncating chunk: {e}")
            return None
    
    def _create_correlation_query(
        self,
        assumption_text: str,
        persona_name: str,
        analysis_type: str
    ) -> str:
        """
        Create a semantically rich correlation query for embedding-based search.
        
        Uses LLM-style prompting to create queries that capture the intent
        of each analysis type without being constrained by predefined keywords.
        
        Args:
            assumption_text: The assumption text
            persona_name: Name of the persona
            analysis_type: Type of analysis
            
        Returns:
            Semantically rich correlation query string
        """
        # Create cache key
        cache_key = f"{assumption_text}|{persona_name}|{analysis_type}"
        
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        # Build semantically rich query based on analysis intent
        query_parts = []
        
        # Start with the core assumption
        if assumption_text:
            query_parts.append(assumption_text)
        
        # Add persona context for personalization
        if persona_name:
            query_parts.append(f"For {persona_name} users:")
        
        # Add analysis-type specific semantic context (LLM-style prompting)
        analysis_contexts = {
            "pain": [
                "What problems, challenges, or frustrations do users experience?",
                "What makes this difficult, annoying, or time-consuming?",
                "What complaints or negative feedback have users expressed?",
                "What obstacles prevent users from achieving their goals?"
            ],
            "size": [
                "How frequently does this occur? How many users are affected?",
                "What are the statistics, numbers, or quantitative data?",
                "How often do users encounter this situation?",
                "What is the scale, magnitude, or scope of this issue?"
            ],
            "solution": [
                "What current tools, methods, or approaches do users employ?",
                "What alternatives, competitors, or existing solutions are available?",
                "How do users currently solve this problem?",
                "What workarounds or substitutes do users rely on?"
            ],
            "gains": [
                "What benefits, value, or improvements would users gain?",
                "How would this make users' lives better, faster, or easier?",
                "What positive outcomes or advantages would result?",
                "What value proposition or return on investment is expected?"
            ],
            "jtbd": [
                "What job is the user trying to accomplish?",
                "What tasks, workflows, or processes are involved?",
                "What is the user's ultimate goal or desired outcome?",
                "In what context or situation does this job arise?"
            ],
            "general": [
                "What does the research data reveal about this assumption?",
                "What evidence supports or contradicts this claim?",
                "What patterns or insights emerge from the data?",
                "What do users say about this topic?"
            ]
        }
        
        # Add multiple semantic perspectives for richer matching
        if analysis_type in analysis_contexts:
            context_questions = analysis_contexts[analysis_type]
            # Use all context questions to create a rich semantic space
            query_parts.extend(context_questions)
        
        # Combine into a semantically rich query
        query = " ".join(query_parts)
        
        # Cache the query
        self._query_cache[cache_key] = query
        
        return query
    
    async def _semantic_similarity_search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search using embeddings.
        
        Args:
            query: Search query
            chunks: List of chunks with embeddings
            top_k: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of chunks with similarity scores
        """
        try:
            # Filter chunks that have embeddings - check both possible embedding fields
            chunks_with_embeddings = []
            for chunk in chunks:
                # Check multiple possible embedding field names
                embedding = (
                    chunk.get("embedding") or 
                    chunk.get("embeddings") or 
                    chunk.get("vector") or
                    chunk.get("embedding_vector")
                )
                
                # Check if embedding exists and is not empty
                if embedding:
                    if isinstance(embedding, str):
                        # String embedding - check if it's not empty and not just whitespace
                        if embedding.strip() and len(embedding.strip()) > 10:  # Reasonable minimum length
                            chunks_with_embeddings.append(chunk)
                    elif isinstance(embedding, (list, tuple)) and len(embedding) > 0:
                        # List/tuple embedding
                        chunks_with_embeddings.append(chunk)
                    elif hasattr(embedding, '__len__') and len(embedding) > 0:
                        # Array-like embedding
                        chunks_with_embeddings.append(chunk)
            
            # Analyze data source breakdown
            pdf_chunks = [c for c in chunks_with_embeddings if c.get('source_type') == 'pdf']
            csv_chunks = [c for c in chunks_with_embeddings if c.get('source_type') == 'csv']
            
            logger.info(f"🔍 CORRELATION: Found {len(chunks_with_embeddings)}/{len(chunks)} chunks with embeddings")
            logger.info(f"🔍 CORRELATION: Data source breakdown - PDF: {len(pdf_chunks)} chunks, CSV: {len(csv_chunks)} chunks")
            
            # Log specific files being used
            pdf_files = list(set([c.get('source_filename', 'unknown') for c in pdf_chunks]))
            csv_files = list(set([c.get('source_filename', 'unknown') for c in csv_chunks]))
            
            if pdf_files:
                logger.info(f"🔍 CORRELATION: PDF files in use: {', '.join(pdf_files)}")
            if csv_files:
                logger.info(f"🔍 CORRELATION: CSV files in use: {', '.join(csv_files)}")
            
            if not chunks_with_embeddings:
                logger.warning("No chunks with embeddings found")
                return []
            
            # Generate query embedding
            query_embeddings = await self.embedding_service.generate_embeddings([query])
            
            if not query_embeddings or not query_embeddings[0]:
                logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = np.array(query_embeddings[0])
            
            # Calculate similarities
            similarities = []
            for chunk in chunks_with_embeddings:
                try:
                    # Get embedding from any of the possible field names
                    embedding = (
                        chunk.get("embedding") or 
                        chunk.get("embeddings") or 
                        chunk.get("vector") or
                        chunk.get("embedding_vector")
                    )
                    
                    # Handle string representations of embeddings
                    if isinstance(embedding, str):
                        # Try to parse string representation back to array
                        try:
                            # Remove numpy string wrapper if present
                            if embedding.startswith("np.str_('") and embedding.endswith("')"):
                                embedding = embedding[9:-2]  # Remove np.str_(' and ')
                            elif embedding.startswith('[') and embedding.endswith(']'):
                                # Parse list string to actual list
                                embedding = eval(embedding)
                            else:
                                # Try to split comma-separated values
                                embedding = [float(x.strip()) for x in embedding.split(',')]
                        except Exception as e:
                            chunk_id = chunk.get('id', chunk.get('index', 'unknown'))
                            logger.warning(f"Failed to parse embedding string for chunk {chunk_id}: {str(e)[:100]}...")  # Limit error message
                            continue
                    
                    chunk_embedding = np.array(embedding, dtype=np.float32)
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                    
                    if similarity >= similarity_threshold:
                        chunk_with_score = chunk.copy()
                        chunk_with_score["similarity_score"] = float(similarity)
                        similarities.append(chunk_with_score)
                        
                except Exception as e:
                    chunk_id = chunk.get('index', chunk.get('id', 'unknown'))
                    error_msg = str(e)
                    # Prevent embedding data from being logged in error messages
                    if len(error_msg) > 200:
                        error_msg = error_msg[:200] + "... [truncated]"
                    logger.warning(f"Error calculating similarity for chunk {chunk_id}: {error_msg}")
                    continue
            
            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Return top-k results
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic similarity search: {e}")
            return []
    
    async def _filter_and_rank_chunks(
        self,
        chunks: List[Dict[str, Any]],
        analysis_type: str,
        assumption: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply semantic filtering and ranking with minimal keyword dependency.
        
        Primarily relies on embedding-based similarity with light semantic validation.
        
        Args:
            chunks: List of chunks with similarity scores
            analysis_type: Type of analysis
            assumption: Original assumption for context
            
        Returns:
            Filtered and re-ranked chunks
        """
        try:
            if not chunks:
                return []
            
            # Apply semantic relevance scoring (primarily embedding-based)
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                similarity_score = chunk.get("similarity_score", 0)
                
                # Light semantic validation using analysis type concepts
                # This is more flexible than rigid keyword matching
                semantic_indicators = self._get_semantic_indicators(analysis_type)
                semantic_score = self._calculate_semantic_relevance(content, semantic_indicators)
                
                # Weighted combination favoring embedding similarity (90%) over semantic indicators (10%)
                combined_score = (similarity_score * 0.9) + (semantic_score * 0.1)
                
                chunk["relevance_score"] = combined_score
                chunk["semantic_score"] = semantic_score
                chunk["analysis_type"] = analysis_type
                
                # Add confidence based on similarity threshold
                if similarity_score >= 0.8:
                    chunk["confidence"] = "high"
                elif similarity_score >= 0.6:
                    chunk["confidence"] = "medium"
                else:
                    chunk["confidence"] = "low"
            
            # Re-sort by combined relevance score
            chunks.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            # Apply context window management for large documents
            filtered_chunks = self._manage_context_window(chunks, analysis_type)
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"Error filtering and ranking chunks: {e}")
            return chunks  # Return original chunks on error
    
    def _get_semantic_indicators(self, analysis_type: str) -> List[str]:
        """
        Get flexible semantic indicators for analysis types.
        
        These are broader concepts rather than rigid keywords.
        """
        indicators = {
            "pain": ["negative", "difficult", "problem", "challenge", "frustration"],
            "size": ["quantitative", "frequency", "scale", "measurement", "data"],
            "solution": ["alternative", "current", "existing", "approach", "method"],
            "gains": ["positive", "benefit", "improvement", "value", "advantage"],
            "jtbd": ["goal", "task", "objective", "purpose", "workflow"],
            "general": ["relevant", "related", "pertinent", "applicable", "concerning"]
        }
        return indicators.get(analysis_type, [])
    
    def _calculate_semantic_relevance(self, content: str, indicators: List[str]) -> float:
        """
        Calculate semantic relevance using flexible concept matching.
        
        This is more nuanced than simple keyword counting.
        """
        if not indicators:
            return 0.5  # Neutral score if no indicators
        
        # Look for semantic concepts rather than exact matches
        relevance_signals = 0
        total_signals = len(indicators)
        
        for indicator in indicators:
            # Check for the concept and related terms
            if self._has_semantic_concept(content, indicator):
                relevance_signals += 1
        
        return relevance_signals / total_signals if total_signals > 0 else 0.5
    
    def _has_semantic_concept(self, content: str, concept: str) -> bool:
        """
        Check if content contains a semantic concept (more flexible than exact matching).
        """
        # This could be enhanced with more sophisticated NLP techniques
        # For now, using flexible pattern matching
        
        concept_patterns = {
            "negative": ["problem", "issue", "difficult", "hard", "bad", "poor", "fail", "error", "wrong"],
            "difficult": ["hard", "complex", "complicated", "challenging", "tough", "struggle"],
            "problem": ["issue", "challenge", "difficulty", "trouble", "concern", "obstacle"],
            "challenge": ["difficulty", "obstacle", "barrier", "hurdle", "problem", "issue"],
            "frustration": ["annoying", "irritating", "frustrating", "disappointing", "upset"],
            "quantitative": ["number", "count", "amount", "quantity", "percent", "statistics"],
            "frequency": ["often", "always", "sometimes", "rarely", "daily", "weekly", "monthly"],
            "scale": ["large", "small", "big", "huge", "massive", "scope", "size", "magnitude"],
            "measurement": ["metric", "measure", "data", "statistics", "numbers", "count"],
            "data": ["statistics", "numbers", "metrics", "measurements", "survey", "study"],
            "alternative": ["option", "choice", "different", "other", "instead", "substitute"],
            "current": ["existing", "present", "now", "currently", "today", "at present"],
            "existing": ["current", "present", "available", "in place", "established"],
            "approach": ["method", "way", "technique", "strategy", "process", "procedure"],
            "method": ["approach", "way", "technique", "process", "procedure", "system"],
            "positive": ["good", "great", "excellent", "better", "improved", "beneficial"],
            "benefit": ["advantage", "value", "gain", "improvement", "positive", "helpful"],
            "improvement": ["better", "enhanced", "upgraded", "optimized", "refined"],
            "value": ["benefit", "advantage", "worth", "useful", "valuable", "important"],
            "advantage": ["benefit", "value", "positive", "good", "helpful", "useful"],
            "goal": ["objective", "target", "aim", "purpose", "intention", "desired"],
            "task": ["job", "activity", "work", "assignment", "duty", "responsibility"],
            "objective": ["goal", "target", "aim", "purpose", "intention", "desired"],
            "purpose": ["goal", "objective", "reason", "intention", "aim", "point"],
            "workflow": ["process", "procedure", "steps", "sequence", "flow", "method"]
        }
        
        patterns = concept_patterns.get(concept, [concept])
        
        # Check if any pattern matches
        for pattern in patterns:
            if pattern in content:
                return True
        
        return False
    
    def _manage_context_window(
        self,
        chunks: List[Dict[str, Any]],
        analysis_type: str,
        max_total_tokens: int = DEFAULT_CONTEXT_TOKEN_BUDGET
    ) -> List[Dict[str, Any]]:
        """
        Manage context window size for large documents.
        
        Args:
            chunks: List of chunks to manage
            analysis_type: Type of analysis
            max_total_tokens: Maximum total tokens to include
            
        Returns:
            Filtered chunks within token limit
        """
        try:
            if not chunks:
                return []
            
            # Calculate total tokens
            total_tokens = 0
            filtered_chunks = []
            
            for chunk in chunks:
                chunk_tokens = chunk.get("token_count", len(chunk.get("content", "").split()) * 1.3)
                
                if total_tokens + chunk_tokens <= max_total_tokens:
                    filtered_chunks.append(chunk)
                    total_tokens += chunk_tokens
                else:
                    # Check if we can fit a smaller portion
                    remaining_tokens = max_total_tokens - total_tokens
                    if remaining_tokens > 100:  # Minimum viable chunk size
                        # Truncate chunk content to fit
                        content = chunk.get("content", "")
                        words = content.split()
                        max_words = int(remaining_tokens / 1.3)  # Approximate word count
                        
                        if max_words > 20:  # Minimum meaningful content
                            truncated_chunk = chunk.copy()
                            truncated_chunk["content"] = " ".join(words[:max_words]) + "..."
                            truncated_chunk["token_count"] = remaining_tokens
                            truncated_chunk["truncated"] = True
                            filtered_chunks.append(truncated_chunk)
                    
                    break
            
            # Analyze final selection data sources
            final_pdf_chunks = [c for c in filtered_chunks if c.get('source_type') == 'pdf']
            final_csv_chunks = [c for c in filtered_chunks if c.get('source_type') == 'csv']
            
            logger.info(f"Context window management: {len(filtered_chunks)}/{len(chunks)} chunks, "
                       f"{total_tokens} tokens for analysis type '{analysis_type}'")
            logger.info(f"Final selection breakdown: {len(final_pdf_chunks)} PDF chunks + {len(final_csv_chunks)} CSV chunks")
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"Error managing context window: {e}")
            return chunks[:10]  # Fallback to first 10 chunks
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Normalize vectors
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)
            
            # Calculate cosine similarity
            similarity = np.dot(vec1_norm, vec2_norm)
            
            # Ensure result is in [0, 1] range
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def batch_find_relevant_data(
        self,
        assumptions: List[Dict[str, Any]],
        research_chunks: List[Dict[str, Any]],
        analysis_types: List[str],
        top_k: int = 10
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Find relevant data for multiple assumptions and analysis types in batch.
        
        Args:
            assumptions: List of assumptions
            research_chunks: List of research chunks
            analysis_types: List of analysis types to process
            top_k: Maximum chunks per assumption-analysis combination
            
        Returns:
            Nested dictionary: {assumption_id: {analysis_type: [chunks]}}
        """
        try:
            results = {}
            
            # Process each assumption
            for assumption in assumptions:
                assumption_id = assumption.get("id", f"assumption_{len(results)}")
                results[assumption_id] = {}
                
                # Process each analysis type for this assumption
                for analysis_type in analysis_types:
                    try:
                        relevant_chunks = await self.find_relevant_data_for_assumption(
                            assumption, research_chunks, analysis_type, top_k
                        )
                        results[assumption_id][analysis_type] = relevant_chunks
                        
                    except Exception as e:
                        logger.error(f"Error processing assumption {assumption_id} "
                                   f"with analysis type {analysis_type}: {e}")
                        results[assumption_id][analysis_type] = []
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch correlation processing: {e}")
            raise CorrelationError(f"Batch processing failed: {str(e)}")
    
    def clear_cache(self):
        """Clear internal caches."""
        self._query_cache.clear()
        self._embedding_cache.clear()
        logger.info("Correlation engine caches cleared")


# Service instance getter following VMP patterns
_correlation_engine: Optional[CorrelationEngine] = None

def get_correlation_engine() -> CorrelationEngine:
    """Get correlation engine singleton."""
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = CorrelationEngine()
    return _correlation_engine