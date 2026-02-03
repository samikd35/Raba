"""
Persona-Aware Correlation Engine for Market Research Analysis

Intelligently associates research data with project personas and provides
persona-aware analysis routing with relevance scoring and confidence levels.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime
from collections import defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ..utils.error_handling import (
    DocumentProcessingError,
    handle_document_processing_errors, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity
)

logger = logging.getLogger(__name__)

# Ensure NLTK data is available
def _ensure_nltk_data():
    """Ensure required NLTK data is available."""
    required_packages = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/stopwords', 'stopwords')
    ]
    
    for data_path, package_name in required_packages:
        try:
            nltk.data.find(data_path)
        except LookupError:
            try:
                nltk.download(package_name, quiet=True)
            except Exception:
                pass

# Initialize NLTK data
_ensure_nltk_data()


class PersonaAwareCorrelationEngine:
    """
    Persona-aware correlation engine that intelligently associates research data
    with project personas and provides targeted analysis routing.
    
    Key Features:
    - Automatic persona inference based on content analysis
    - Persona relevance scoring and association confidence levels
    - Cross-persona accessibility with persona-specific highlighting
    - Intelligent content-persona matching using NLP techniques
    - Dynamic persona profile analysis and keyword extraction
    """
    
    # Configuration constants
    MIN_RELEVANCE_SCORE = 0.3  # Minimum score for persona association
    HIGH_CONFIDENCE_THRESHOLD = 0.7  # Threshold for high confidence associations
    MAX_PERSONA_KEYWORDS = 20  # Maximum keywords per persona profile
    
    # Common persona-related keywords
    PERSONA_INDICATORS = {
        'demographics': [
            'age', 'gender', 'location', 'education', 'income', 'occupation',
            'experience', 'years', 'background', 'role', 'position'
        ],
        'behavioral': [
            'behavior', 'habit', 'preference', 'tendency', 'pattern',
            'frequency', 'usage', 'adoption', 'engagement'
        ],
        'psychographic': [
            'motivation', 'goal', 'value', 'belief', 'attitude', 'lifestyle',
            'personality', 'interest', 'priority', 'concern'
        ],
        'contextual': [
            'situation', 'context', 'environment', 'scenario', 'use case',
            'workflow', 'process', 'task', 'job', 'responsibility'
        ]
    }
    
    def __init__(self, db_adapter: Optional[AnalysisAgentDatabaseAdapter] = None):
        """
        Initialize persona-aware correlation engine.
        
        Args:
            db_adapter: Database adapter instance (optional)
        """
        self.db_adapter = db_adapter or AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.logger = logger
        self.stop_words = set(stopwords.words('english'))
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    @handle_document_processing_errors
    @monitor_performance("persona_data_association")
    async def associate_data_with_personas(
        self,
        project_id: str,
        tenant_id: str,
        research_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Intelligently associate research data with project personas.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            research_data: Research data containing statistics and content
            
        Returns:
            Dictionary mapping persona IDs to associated statistic IDs
        """
        try:
            # Get project personas
            project_context = await self.db_adapter.get_vmp_project_context(project_id, tenant_id)
            if not project_context or not project_context.get('personas'):
                return {'general': self._extract_all_statistic_ids(research_data)}
            
            personas = project_context['personas']
            associations = defaultdict(list)
            
            # Process each persona
            for persona in personas:
                persona_id = persona.get('id', persona.get('name', 'unknown'))
                
                # Extract persona profile for matching
                persona_profile = self._extract_persona_profile(persona)
                
                # Associate CSV statistics
                csv_stats = research_data.get('csv_statistics', {})
                if csv_stats:
                    csv_associations = await self._associate_csv_statistics(
                        csv_stats, persona_profile, persona_id
                    )
                    associations[persona_id].extend(csv_associations)
                
                # Associate PDF content
                pdf_stats = research_data.get('pdf_statistics', {})
                if pdf_stats:
                    pdf_associations = await self._associate_pdf_content(
                        pdf_stats, persona_profile, persona_id
                    )
                    associations[persona_id].extend(pdf_associations)
            
            # Add general associations for data not strongly associated with any persona
            all_statistic_ids = self._extract_all_statistic_ids(research_data)
            associated_ids = set()
            for persona_ids in associations.values():
                associated_ids.update(persona_ids)
            
            general_ids = [sid for sid in all_statistic_ids if sid not in associated_ids]
            if general_ids:
                associations['general'] = general_ids
            
            # Convert defaultdict to regular dict
            final_associations = dict(associations)
            
            self.logger.info(
                f"Associated research data with {len(final_associations)} persona groups"
            )
            
            return final_associations
            
        except Exception as e:
            self.logger.error(f"Error associating data with personas: {e}")
            return {'general': self._extract_all_statistic_ids(research_data)}
    
    async def find_relevant_data(
        self,
        assumption: Dict[str, Any],
        research_chunks: List[Dict[str, Any]],
        analysis_type: str = "general",
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Compatibility method for standard correlation engine interface.
        
        Args:
            assumption: Assumption being analyzed
            research_chunks: Available research chunks
            analysis_type: Type of analysis being performed
            top_k: Maximum number of chunks to return
            
        Returns:
            List of relevant research chunks
        """
        try:
            # Extract persona information from assumption
            persona_id = assumption.get('persona_id') or assumption.get('id', 'unknown')
            
            # Use the research chunks directly instead of loading from database
            # This maintains compatibility with the existing workflow
            logger.info(f"🔍 PERSONA CORRELATION: Processing {len(research_chunks)} chunks for {analysis_type} analysis")
            
            # Simple relevance scoring based on content similarity
            # This is a simplified version that works with the provided chunks
            relevant_chunks = []
            assumption_text = assumption.get('text', '').lower()
            
            for chunk in research_chunks[:top_k]:  # Limit to top_k
                if chunk and isinstance(chunk, dict):
                    chunk_content = chunk.get('content', '').lower()
                    # Simple keyword matching for now
                    if any(word in chunk_content for word in assumption_text.split() if len(word) > 3):
                        relevant_chunks.append(chunk)
            
            logger.info(f"🔍 PERSONA CORRELATION: Found {len(relevant_chunks)} relevant chunks")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error in persona-aware correlation: {e}")
            # Fallback to returning first top_k chunks
            return research_chunks[:top_k] if research_chunks else []

    @handle_document_processing_errors
    @monitor_performance("persona_relevant_data_search")
    async def find_persona_relevant_data(
        self,
        project_id: str,
        tenant_id: str,
        assumption: Dict[str, Any],
        persona_id: str,
        analysis_type: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Find statistics and evidence relevant to specific persona and analysis.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            assumption: Assumption being analyzed
            persona_id: Target persona ID
            analysis_type: Type of analysis ('pain', 'size', 'solution', 'gains', 'jtbd')
            
        Returns:
            Tuple of (ground_truth_statistics, evidence_chunks)
        """
        try:
            # Get research data
            research_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if not research_data:
                return {}, []
            
            # Get persona profile
            project_context = await self.db_adapter.get_vmp_project_context(project_id, tenant_id)
            persona_profile = self._get_persona_profile(project_context, persona_id)
            
            # Get statistics registry
            statistics_registry = research_data.get('statistics_registry', {})
            
            # Filter statistics by persona relevance
            relevant_statistics = self._filter_statistics_by_persona_relevance(
                statistics_registry, persona_profile, analysis_type
            )
            
            # Get evidence chunks
            all_chunks = await self.db_adapter.get_research_chunks_for_analysis(project_id, tenant_id)
            relevant_chunks = self._filter_chunks_by_persona_relevance(
                all_chunks, persona_profile, assumption, analysis_type
            )
            
            self.logger.info(
                f"Found persona-relevant data: {len(relevant_statistics)} statistics, "
                f"{len(relevant_chunks)} chunks for persona {persona_id}"
            )
            
            return relevant_statistics, relevant_chunks
            
        except Exception as e:
            self.logger.error(f"Error finding persona-relevant data: {e}")
            return {}, []
    
    def calculate_persona_relevance(
        self,
        content: str,
        persona_profile: Dict[str, Any]
    ) -> float:
        """
        Calculate relevance score between content and persona profile.
        
        Args:
            content: Text content to analyze
            persona_profile: Persona profile dictionary
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            if not content or not persona_profile:
                return 0.0
            
            # Extract persona keywords
            persona_keywords = self._extract_persona_keywords(persona_profile)
            if not persona_keywords:
                return 0.5  # Neutral relevance if no keywords
            
            # Calculate keyword overlap
            content_lower = content.lower()
            content_words = set(word_tokenize(content_lower))
            content_words = {word for word in content_words if word not in self.stop_words}
            
            persona_words = set(persona_keywords)
            
            # Calculate Jaccard similarity
            intersection = len(content_words.intersection(persona_words))
            union = len(content_words.union(persona_words))
            
            if union == 0:
                return 0.0
            
            jaccard_score = intersection / union
            
            # Calculate TF-IDF similarity if we have enough content
            if len(content.split()) > 10:
                tfidf_score = self._calculate_tfidf_similarity(content, persona_profile)
                # Combine scores with weights
                relevance_score = 0.6 * jaccard_score + 0.4 * tfidf_score
            else:
                relevance_score = jaccard_score
            
            return min(1.0, relevance_score)
            
        except Exception as e:
            self.logger.warning(f"Error calculating persona relevance: {e}")
            return 0.5  # Default to neutral relevance
    
    async def infer_persona_from_content(
        self,
        content: str,
        available_personas: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], float]:
        """
        Infer the most relevant persona for given content.
        
        Args:
            content: Content to analyze
            available_personas: List of available persona profiles
            
        Returns:
            Tuple of (persona_id, confidence_score)
        """
        try:
            if not content or not available_personas:
                return None, 0.0
            
            best_persona = None
            best_score = 0.0
            
            for persona in available_personas:
                persona_id = persona.get('id', persona.get('name', 'unknown'))
                persona_profile = self._extract_persona_profile(persona)
                
                relevance_score = self.calculate_persona_relevance(content, persona_profile)
                
                if relevance_score > best_score:
                    best_score = relevance_score
                    best_persona = persona_id
            
            # Only return if confidence is above threshold
            if best_score >= self.MIN_RELEVANCE_SCORE:
                confidence_level = "high" if best_score >= self.HIGH_CONFIDENCE_THRESHOLD else "medium"
                return best_persona, best_score
            
            return None, best_score
            
        except Exception as e:
            self.logger.error(f"Error inferring persona from content: {e}")
            return None, 0.0
    
    # Private helper methods
    
    def _extract_persona_profile(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured profile from persona data."""
        profile = {
            'name': persona.get('name', ''),
            'description': persona.get('description', ''),
            'demographics': {},
            'behaviors': {},
            'goals': {},
            'pain_points': {},
            'keywords': []
        }
        
        # Extract from description
        description = persona.get('description', '')
        if description:
            profile['keywords'].extend(self._extract_keywords_from_text(description))
        
        # Extract from other fields
        for key, value in persona.items():
            if isinstance(value, str) and key not in ['id', 'name', 'description']:
                profile['keywords'].extend(self._extract_keywords_from_text(value))
        
        # Extract structured information if available
        if 'demographics' in persona:
            profile['demographics'] = persona['demographics']
        
        if 'behaviors' in persona:
            profile['behaviors'] = persona['behaviors']
        
        if 'goals' in persona:
            profile['goals'] = persona['goals']
        
        if 'pain_points' in persona:
            profile['pain_points'] = persona['pain_points']
        
        # Limit keywords
        profile['keywords'] = list(set(profile['keywords']))[:self.MAX_PERSONA_KEYWORDS]
        
        return profile
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        if not text:
            return []
        
        # Tokenize and filter
        words = word_tokenize(text.lower())
        keywords = []
        
        for word in words:
            if (len(word) > 2 and 
                word not in self.stop_words and 
                word.isalpha()):
                keywords.append(word)
        
        return keywords
    
    def _extract_persona_keywords(self, persona_profile: Dict[str, Any]) -> List[str]:
        """Extract all keywords from persona profile."""
        keywords = []
        
        # Add explicit keywords
        keywords.extend(persona_profile.get('keywords', []))
        
        # Extract from name and description
        name = persona_profile.get('name', '')
        description = persona_profile.get('description', '')
        
        keywords.extend(self._extract_keywords_from_text(name))
        keywords.extend(self._extract_keywords_from_text(description))
        
        # Extract from structured fields
        for field_name, field_data in persona_profile.items():
            if isinstance(field_data, dict):
                for key, value in field_data.items():
                    if isinstance(value, str):
                        keywords.extend(self._extract_keywords_from_text(value))
            elif isinstance(field_data, str) and field_name not in ['name', 'description']:
                keywords.extend(self._extract_keywords_from_text(field_data))
        
        return list(set(keywords))
    
    async def _associate_csv_statistics(
        self,
        csv_stats: Dict[str, Any],
        persona_profile: Dict[str, Any],
        persona_id: str
    ) -> List[str]:
        """Associate CSV statistics with persona."""
        associations = []
        
        categorical_dists = csv_stats.get('categorical_distributions', {})
        
        for field_name, field_data in categorical_dists.items():
            # Calculate relevance based on field name and values
            field_text = f"{field_name} " + " ".join([
                item['value'] for item in field_data.get('distribution', [])
            ])
            
            relevance_score = self.calculate_persona_relevance(field_text, persona_profile)
            
            if relevance_score >= self.MIN_RELEVANCE_SCORE:
                associations.append(f"csv_categorical_{field_name}")
        
        # Associate numerical summaries
        numerical_summaries = csv_stats.get('numerical_summaries', {})
        for field_name in numerical_summaries.keys():
            relevance_score = self.calculate_persona_relevance(field_name, persona_profile)
            
            if relevance_score >= self.MIN_RELEVANCE_SCORE:
                associations.append(f"csv_numerical_{field_name}")
        
        return associations
    
    async def _associate_pdf_content(
        self,
        pdf_stats: Dict[str, Any],
        persona_profile: Dict[str, Any],
        persona_id: str
    ) -> List[str]:
        """Associate PDF content with persona."""
        associations = []
        
        # Associate themes
        themes = pdf_stats.get('themes', {})
        for theme_name, theme_data in themes.items():
            # Get theme context
            theme_text = theme_name + " " + " ".join([
                example for example in theme_data.get('context_examples', [])
            ])
            
            relevance_score = self.calculate_persona_relevance(theme_text, persona_profile)
            
            if relevance_score >= self.MIN_RELEVANCE_SCORE:
                associations.append(f"pdf_theme_{theme_name}")
        
        # Associate quotes
        quotes = pdf_stats.get('key_quotes', [])
        for i, quote_data in enumerate(quotes):
            quote_text = quote_data.get('quote', '') + " " + quote_data.get('context', '')
            
            relevance_score = self.calculate_persona_relevance(quote_text, persona_profile)
            
            if relevance_score >= self.MIN_RELEVANCE_SCORE:
                associations.append(f"pdf_quote_{i}")
        
        return associations
    
    def _extract_all_statistic_ids(self, research_data: Dict[str, Any]) -> List[str]:
        """Extract all statistic IDs from research data."""
        statistic_ids = []
        
        # CSV statistics
        csv_stats = research_data.get('csv_statistics', {})
        for field_name in csv_stats.get('categorical_distributions', {}):
            statistic_ids.append(f"csv_categorical_{field_name}")
        
        for field_name in csv_stats.get('numerical_summaries', {}):
            statistic_ids.append(f"csv_numerical_{field_name}")
        
        # PDF statistics
        pdf_stats = research_data.get('pdf_statistics', {})
        for theme_name in pdf_stats.get('themes', {}):
            statistic_ids.append(f"pdf_theme_{theme_name}")
        
        quote_count = len(pdf_stats.get('key_quotes', []))
        for i in range(quote_count):
            statistic_ids.append(f"pdf_quote_{i}")
        
        return statistic_ids
    
    def _get_persona_profile(
        self,
        project_context: Optional[Dict[str, Any]],
        persona_id: str
    ) -> Dict[str, Any]:
        """Get persona profile from project context."""
        if not project_context or not project_context.get('personas'):
            return {}
        
        personas = project_context['personas']
        
        for persona in personas:
            if persona.get('id') == persona_id or persona.get('name') == persona_id:
                return self._extract_persona_profile(persona)
        
        return {}
    
    def _filter_statistics_by_persona_relevance(
        self,
        statistics_registry: Dict[str, Any],
        persona_profile: Dict[str, Any],
        analysis_type: str
    ) -> Dict[str, Any]:
        """Filter statistics by persona relevance and analysis type."""
        filtered_stats = {
            'csv_statistics': {},
            'pdf_statistics': {},
            'persona_relevance': {
                'persona_profile': persona_profile,
                'analysis_type': analysis_type,
                'filtered_at': datetime.utcnow().isoformat()
            }
        }
        
        # Filter CSV statistics
        csv_stats = statistics_registry.get('csv_statistics', {})
        if csv_stats:
            filtered_csv = self._filter_csv_by_relevance(csv_stats, persona_profile, analysis_type)
            filtered_stats['csv_statistics'] = filtered_csv
        
        # Filter PDF statistics
        pdf_stats = statistics_registry.get('pdf_statistics', {})
        if pdf_stats:
            filtered_pdf = self._filter_pdf_by_relevance(pdf_stats, persona_profile, analysis_type)
            filtered_stats['pdf_statistics'] = filtered_pdf
        
        return filtered_stats
    
    def _filter_csv_by_relevance(
        self,
        csv_stats: Dict[str, Any],
        persona_profile: Dict[str, Any],
        analysis_type: str
    ) -> Dict[str, Any]:
        """Filter CSV statistics by persona relevance."""
        filtered = dict(csv_stats)  # Start with all data
        
        # Add relevance scores to categorical distributions
        categorical_dists = filtered.get('categorical_distributions', {})
        for field_name, field_data in categorical_dists.items():
            field_text = f"{field_name} " + " ".join([
                item['value'] for item in field_data.get('distribution', [])
            ])
            relevance_score = self.calculate_persona_relevance(field_text, persona_profile)
            field_data['persona_relevance_score'] = relevance_score
        
        # Add relevance scores to numerical summaries
        numerical_summaries = filtered.get('numerical_summaries', {})
        for field_name, field_data in numerical_summaries.items():
            relevance_score = self.calculate_persona_relevance(field_name, persona_profile)
            field_data['persona_relevance_score'] = relevance_score
        
        return filtered
    
    def _filter_pdf_by_relevance(
        self,
        pdf_stats: Dict[str, Any],
        persona_profile: Dict[str, Any],
        analysis_type: str
    ) -> Dict[str, Any]:
        """Filter PDF statistics by persona relevance."""
        filtered = dict(pdf_stats)  # Start with all data
        
        # Add relevance scores to themes
        themes = filtered.get('themes', {})
        for theme_name, theme_data in themes.items():
            theme_text = theme_name + " " + " ".join([
                example for example in theme_data.get('context_examples', [])
            ])
            relevance_score = self.calculate_persona_relevance(theme_text, persona_profile)
            theme_data['persona_relevance_score'] = relevance_score
        
        # Add relevance scores to quotes
        quotes = filtered.get('key_quotes', [])
        for quote_data in quotes:
            quote_text = quote_data.get('quote', '') + " " + quote_data.get('context', '')
            relevance_score = self.calculate_persona_relevance(quote_text, persona_profile)
            quote_data['persona_relevance_score'] = relevance_score
        
        return filtered
    
    def _filter_chunks_by_persona_relevance(
        self,
        chunks: List[Dict[str, Any]],
        persona_profile: Dict[str, Any],
        assumption: Dict[str, Any],
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """Filter chunks by persona relevance."""
        filtered_chunks = []
        
        for chunk in chunks:
            content = chunk.get('content', '')
            
            # Calculate persona relevance
            persona_relevance = self.calculate_persona_relevance(content, persona_profile)
            
            # Calculate assumption relevance
            assumption_text = assumption.get('assumption_text', '')
            assumption_relevance = self._calculate_assumption_relevance(content, assumption_text)
            
            # Combine scores
            combined_score = 0.6 * persona_relevance + 0.4 * assumption_relevance
            
            if combined_score >= self.MIN_RELEVANCE_SCORE:
                chunk_copy = dict(chunk)
                chunk_copy['persona_relevance_score'] = persona_relevance
                chunk_copy['assumption_relevance_score'] = assumption_relevance
                chunk_copy['combined_relevance_score'] = combined_score
                filtered_chunks.append(chunk_copy)
        
        # Sort by combined relevance score
        filtered_chunks.sort(key=lambda x: x['combined_relevance_score'], reverse=True)
        
        return filtered_chunks
    
    def _calculate_tfidf_similarity(
        self,
        content: str,
        persona_profile: Dict[str, Any]
    ) -> float:
        """Calculate TF-IDF similarity between content and persona profile."""
        try:
            # Create persona text
            persona_text = " ".join([
                persona_profile.get('name', ''),
                persona_profile.get('description', ''),
                " ".join(persona_profile.get('keywords', []))
            ])
            
            if not persona_text.strip():
                return 0.0
            
            # Fit TF-IDF on both texts
            texts = [content, persona_text]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            self.logger.warning(f"Error calculating TF-IDF similarity: {e}")
            return 0.0
    
    def _calculate_assumption_relevance(self, content: str, assumption_text: str) -> float:
        """Calculate relevance between content and assumption."""
        if not content or not assumption_text:
            return 0.0
        
        # Simple keyword overlap approach
        content_words = set(word_tokenize(content.lower()))
        assumption_words = set(word_tokenize(assumption_text.lower()))
        
        # Remove stop words
        content_words = {word for word in content_words if word not in self.stop_words}
        assumption_words = {word for word in assumption_words if word not in self.stop_words}
        
        if not content_words or not assumption_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(content_words.intersection(assumption_words))
        union = len(content_words.union(assumption_words))
        
        return intersection / union if union > 0 else 0.0


# Service instance getter following VMP patterns
_persona_aware_correlation_engine: Optional[PersonaAwareCorrelationEngine] = None

def get_persona_aware_correlation_engine(
    db_adapter: Optional[AnalysisAgentDatabaseAdapter] = None
) -> PersonaAwareCorrelationEngine:
    """Get persona-aware correlation engine singleton."""
    global _persona_aware_correlation_engine
    if _persona_aware_correlation_engine is None:
        _persona_aware_correlation_engine = PersonaAwareCorrelationEngine(db_adapter)
    return _persona_aware_correlation_engine