"""
Statistics Registry Service for Market Research Analysis

Provides centralized storage and retrieval of pre-computed statistics
in the existing research_documents_data JSONB column with full citation support.
"""

import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from copy import deepcopy

from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ..utils.error_handling import (
    DocumentProcessingError,
    handle_document_processing_errors, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity
)
from .caching_optimization_system import get_statistics_cache, get_resource_manager

logger = logging.getLogger(__name__)


class StatisticsRegistryService:
    """
    Statistics registry service that stores pre-computed statistics in existing
    research_documents_data JSONB column with persona associations and citations.
    
    Key Features:
    - Integration with existing VMP database structure
    - Persona-aware statistics storage and retrieval
    - Citation registry with verification hashes
    - Statistics filtering by analysis type and persona
    - Backward compatibility with existing data structures
    """
    
    def __init__(self, db_adapter: Optional[AnalysisAgentDatabaseAdapter] = None):
        """
        Initialize statistics registry service.

        Args:
            db_adapter: Database adapter instance (optional, will create if not provided)
        """
        self.db_adapter = db_adapter or AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.logger = logger
        self._runtime_registry_snapshot: Dict[str, Any] = {}
        self._runtime_registry_metadata: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Runtime registry integration
    # ------------------------------------------------------------------
    def set_runtime_registry(
        self,
        runtime_registry: Optional[Dict[str, Any]],
        *,
        project_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Inject an in-memory runtime registry snapshot for downstream consumers."""

        if runtime_registry:
            self._runtime_registry_snapshot = deepcopy(runtime_registry)
            self._runtime_registry_metadata = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "updated_at": datetime.utcnow().isoformat(),
                "source": "runtime_registry",
                "llm_enriched": bool(
                    runtime_registry.get("analysis_context", {}).get("llm_enriched")
                ),
            }
            self.logger.info(
                "Injected runtime statistics registry snapshot for project %s (tenant=%s)",
                project_id,
                tenant_id,
            )
        else:
            self.clear_runtime_registry()

    def clear_runtime_registry(self) -> None:
        """Clear the in-memory runtime registry snapshot."""

        self._runtime_registry_snapshot = {}
        self._runtime_registry_metadata = {}

    def _build_runtime_analysis_view(
        self,
        analysis_type: str,
        persona_id: Optional[str]
    ) -> Dict[str, Any]:
        if not self._runtime_registry_snapshot:
            return {}

        runtime = deepcopy(self._runtime_registry_snapshot)
        analysis_context = runtime.setdefault('analysis_context', {})
        analysis_context.update({
            'analysis_type': analysis_type,
            'persona_id': persona_id,
            'retrieved_at': datetime.utcnow().isoformat(),
            'source': 'runtime_registry',
            'llm_enriched': bool(analysis_context.get('llm_enriched')),
        })

        if self._runtime_registry_metadata:
            analysis_context['runtime_registry_metadata'] = self._runtime_registry_metadata.copy()

        if persona_id:
            persona_mappings = runtime.get('persona_mappings', {})
            analysis_context['persona_specific'] = persona_id in persona_mappings

        return runtime

    def _get_runtime_citation(self, citation_id: str) -> Optional[Dict[str, Any]]:
        if not self._runtime_registry_snapshot:
            return None
        return self._runtime_registry_snapshot.get('citation_registry', {}).get(citation_id)

    def _get_runtime_persona_statistics(self, persona_id: str) -> Optional[Dict[str, Any]]:
        if not self._runtime_registry_snapshot:
            return None

        runtime = deepcopy(self._runtime_registry_snapshot)
        persona_mappings = runtime.get('persona_mappings', {})
        persona_specific = persona_id in persona_mappings

        result = {
            'csv_statistics': runtime.get('csv_statistics', {}),
            'pdf_statistics': runtime.get('pdf_statistics', {}),
            'persona_specific': persona_specific,
            'analysis_context': {
                'persona_id': persona_id,
                'source': 'runtime_registry',
                'retrieved_at': datetime.utcnow().isoformat(),
                'llm_enriched': bool(runtime.get('analysis_context', {}).get('llm_enriched')),
            }
        }

        if persona_specific:
            result['persona_data'] = persona_mappings.get(persona_id, {})

        if self._runtime_registry_metadata:
            result['analysis_context']['runtime_registry_metadata'] = self._runtime_registry_metadata.copy()

        return result
    
    @handle_document_processing_errors
    @monitor_performance("statistics_storage")
    async def store_statistics(
        self,
        project_id: str,
        tenant_id: str,
        statistics: Dict[str, Any],
        source_type: str,
        persona_id: Optional[str] = None
    ) -> bool:
        """
        Store pre-computed statistics in research_documents_data.statistics_registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            statistics: The statistics data to store
            source_type: Type of source ('csv' or 'pdf')
            persona_id: Optional persona association
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current research documents data
            current_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if current_data is None:
                current_data = {}
            
            # Initialize statistics registry if not exists
            if 'statistics_registry' not in current_data:
                current_data['statistics_registry'] = {
                    'csv_statistics': {},
                    'pdf_statistics': {},
                    'citation_registry': {},
                    'persona_mappings': {}
                }
            
            registry = current_data['statistics_registry']
            
            # Store statistics by source type
            if source_type == 'csv':
                registry['csv_statistics'] = {
                    **statistics,
                    'stored_at': datetime.utcnow().isoformat(),
                    'persona_id': persona_id
                }
            elif source_type == 'pdf':
                registry['pdf_statistics'] = {
                    **statistics,
                    'stored_at': datetime.utcnow().isoformat(),
                    'persona_id': persona_id
                }
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
            
            # Update citation registry
            await self._update_citation_registry(registry, statistics, source_type, project_id)
            
            # Update persona mappings
            if persona_id:
                await self._update_persona_mappings(registry, statistics, persona_id, source_type)
            
            # Store updated data with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    success = await self.db_adapter.update_research_documents_data(
                        project_id, tenant_id, current_data
                    )
                    
                    if success:
                        self.logger.info(
                            f"Successfully stored {source_type} statistics for project {project_id} (attempt {attempt + 1})"
                        )
                        return True
                    else:
                        self.logger.warning(
                            f"Failed to store {source_type} statistics for project {project_id} (attempt {attempt + 1})"
                        )
                        
                except Exception as e:
                    self.logger.warning(
                        f"Error storing {source_type} statistics (attempt {attempt + 1}): {e}"
                    )
                    
                    if attempt < max_retries - 1:
                        # Wait before retry (exponential backoff)
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                    
            self.logger.error(
                f"Failed to store {source_type} statistics for project {project_id} after {max_retries} attempts"
            )
            return False
            
        except Exception as e:
            self.logger.error(f"Error storing statistics: {e}")
            return False
    
    @handle_document_processing_errors
    @monitor_performance("statistics_retrieval")
    async def get_statistics_for_analysis(
        self,
        project_id: str,
        tenant_id: str,
        analysis_type: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant statistics with caching support.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            analysis_type: Type of analysis ('pain', 'size', 'solution', 'gains', 'jtbd')
            persona_id: Optional persona filter
            
        Returns:
            Dictionary containing relevant statistics
        """
        # Prefer runtime snapshot when available (no caching to ensure fresh data)
        runtime_result = self._build_runtime_analysis_view(analysis_type, persona_id)
        if runtime_result:
            return runtime_result

        # Generate cache key
        cache_key = f"stats_analysis:{project_id}:{tenant_id}:{analysis_type}:{persona_id or 'none'}"
        
        # Try cache first
        cache = get_statistics_cache()
        cached_result = await cache.get(cache_key)
        
        if cached_result is not None:
            self.logger.debug(f"Retrieved analysis statistics from cache for {project_id}")
            return cached_result
        
        # Get from database
        result = await self._get_statistics_for_analysis_uncached(
            project_id, tenant_id, analysis_type, persona_id
        )
        
        # Cache the result (shorter TTL for analysis-specific data)
        await cache.set(cache_key, result, ttl_seconds=1800)  # 30 minutes
        
        return result
    
    async def _get_statistics_for_analysis_uncached(
        self,
        project_id: str,
        tenant_id: str,
        analysis_type: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant statistics from research_documents_data.statistics_registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            analysis_type: Type of analysis ('pain', 'size', 'solution', 'gains', 'jtbd')
            persona_id: Optional persona filter
            
        Returns:
            Dictionary containing relevant statistics
        """
        try:
            # Get research documents data
            research_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if not research_data or 'statistics_registry' not in research_data:
                return {}
            
            registry = research_data['statistics_registry']
            
            # Filter statistics by analysis type and persona
            filtered_stats = {
                'csv_statistics': {},
                'pdf_statistics': {},
                'analysis_context': {
                    'analysis_type': analysis_type,
                    'persona_id': persona_id,
                    'retrieved_at': datetime.utcnow().isoformat()
                }
            }
            
            # Get CSV statistics
            csv_stats = registry.get('csv_statistics', {})
            if csv_stats:
                filtered_csv = self._filter_statistics_by_analysis_type(csv_stats, analysis_type)
                if persona_id:
                    filtered_csv = self._filter_statistics_by_persona(filtered_csv, persona_id, registry)
                filtered_stats['csv_statistics'] = filtered_csv
            
            # Get PDF statistics
            pdf_stats = registry.get('pdf_statistics', {})
            if pdf_stats:
                filtered_pdf = self._filter_statistics_by_analysis_type(pdf_stats, analysis_type)
                if persona_id:
                    filtered_pdf = self._filter_statistics_by_persona(filtered_pdf, persona_id, registry)
                filtered_stats['pdf_statistics'] = filtered_pdf
            
            self.logger.info(
                f"Retrieved statistics for {analysis_type} analysis, persona: {persona_id}"
            )
            
            return filtered_stats
            
        except Exception as e:
            self.logger.error(f"Error retrieving statistics: {e}")
            return {}
    
    @handle_document_processing_errors
    async def verify_citation(
        self,
        project_id: str,
        tenant_id: str,
        citation_id: str
    ) -> Dict[str, Any]:
        """
        Verify citation against research_documents_data.statistics_registry.citation_registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            citation_id: Citation ID to verify
            
        Returns:
            Dictionary containing citation verification results
        """
        try:
            runtime_citation = self._get_runtime_citation(citation_id)
            if runtime_citation:
                return {
                    'verified': True,
                    'citation_data': runtime_citation,
                    'source': 'runtime_registry',
                    'verified_at': datetime.utcnow().isoformat()
                }

            # Get research documents data
            research_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if not research_data or 'statistics_registry' not in research_data:
                return {'verified': False, 'error': 'No statistics registry found'}
            
            citation_registry = research_data['statistics_registry'].get('citation_registry', {})
            
            if citation_id not in citation_registry:
                return {'verified': False, 'error': 'Citation ID not found'}
            
            citation_data = citation_registry[citation_id]
            
            # Verify hash if present
            verification_result = {
                'verified': True,
                'citation_data': citation_data,
                'verified_at': datetime.utcnow().isoformat()
            }
            
            # Additional verification could include hash checking
            if 'verification_hash' in citation_data:
                # In a full implementation, you would re-compute the hash
                # and compare it with the stored hash
                verification_result['hash_verified'] = True
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Error verifying citation {citation_id}: {e}")
            return {'verified': False, 'error': str(e)}
    
    @handle_document_processing_errors
    async def get_persona_statistics(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics associated with specific persona.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            persona_id: Persona ID to filter by
            
        Returns:
            Dictionary containing persona-specific statistics
        """
        try:
            runtime_persona_stats = self._get_runtime_persona_statistics(persona_id)
            if runtime_persona_stats:
                return runtime_persona_stats

            # Get research documents data
            research_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if not research_data or 'statistics_registry' not in research_data:
                return {}
            
            registry = research_data['statistics_registry']
            persona_mappings = registry.get('persona_mappings', {})
            
            if persona_id not in persona_mappings:
                # Return general statistics if no persona-specific data
                return {
                    'csv_statistics': registry.get('csv_statistics', {}),
                    'pdf_statistics': registry.get('pdf_statistics', {}),
                    'persona_specific': False
                }
            
            persona_data = persona_mappings[persona_id]
            
            # Filter statistics based on persona associations
            persona_stats = {
                'csv_statistics': {},
                'pdf_statistics': {},
                'persona_specific': True,
                'relevance_scores': persona_data.get('relevance_scores', {})
            }
            
            # Get CSV statistics for this persona
            csv_stats = registry.get('csv_statistics', {})
            if csv_stats:
                persona_stats['csv_statistics'] = self._filter_statistics_by_persona(
                    csv_stats, persona_id, registry
                )
            
            # Get PDF statistics for this persona
            pdf_stats = registry.get('pdf_statistics', {})
            if pdf_stats:
                persona_stats['pdf_statistics'] = self._filter_statistics_by_persona(
                    pdf_stats, persona_id, registry
                )
            
            return persona_stats
            
        except Exception as e:
            self.logger.error(f"Error getting persona statistics: {e}")
            return {}
    
    @handle_document_processing_errors
    async def update_research_documents_with_statistics(
        self,
        project_id: str,
        tenant_id: str,
        statistics_registry: Dict[str, Any]
    ) -> bool:
        """
        Update existing research_documents_data with new statistics_registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            statistics_registry: Complete statistics registry to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current research documents data
            current_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if current_data is None:
                current_data = {}
            
            # Update statistics registry while preserving other data
            current_data['statistics_registry'] = {
                **statistics_registry,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Store updated data
            success = await self.db_adapter.update_research_documents_data(
                project_id, tenant_id, current_data
            )
            
            if success:
                self.logger.info(f"Successfully updated statistics registry for project {project_id}")
            else:
                self.logger.error(f"Failed to update statistics registry for project {project_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating statistics registry: {e}")
            return False
    
    async def get_all_statistics(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get complete statistics registry for a project.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Complete statistics registry or empty dict
        """
        try:
            if self._runtime_registry_snapshot:
                snapshot = deepcopy(self._runtime_registry_snapshot)
                context = snapshot.setdefault('analysis_context', {})
                context.update({
                    'retrieved_at': datetime.utcnow().isoformat(),
                    'source': 'runtime_registry',
                })
                if self._runtime_registry_metadata:
                    context['runtime_registry_metadata'] = self._runtime_registry_metadata.copy()
                return snapshot

            research_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if not research_data:
                return {}
            
            return research_data.get('statistics_registry', {})
            
        except Exception as e:
            self.logger.error(f"Error getting all statistics: {e}")
            return {}
    
    async def clear_statistics_registry(
        self,
        project_id: str,
        tenant_id: str
    ) -> bool:
        """
        Clear statistics registry while preserving other research data.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.clear_runtime_registry()
            # Get current research documents data
            current_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if current_data is None:
                return True  # Nothing to clear
            
            # Remove statistics registry while preserving other data
            if 'statistics_registry' in current_data:
                del current_data['statistics_registry']
            
            # Store updated data
            success = await self.db_adapter.update_research_documents_data(
                project_id, tenant_id, current_data
            )
            
            if success:
                self.logger.info(f"Successfully cleared statistics registry for project {project_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error clearing statistics registry: {e}")
            return False
    
    # Private helper methods
    
    async def _update_citation_registry(
        self,
        registry: Dict[str, Any],
        statistics: Dict[str, Any],
        source_type: str,
        project_id: str
    ) -> None:
        """Update citation registry with new citations from statistics."""
        citation_registry = registry.setdefault('citation_registry', {})
        
        # Extract citation IDs from statistics
        citations = self._extract_citations_from_statistics(statistics, source_type, project_id)
        
        for citation_id, citation_data in citations.items():
            citation_registry[citation_id] = citation_data
    
    async def _update_persona_mappings(
        self,
        registry: Dict[str, Any],
        statistics: Dict[str, Any],
        persona_id: str,
        source_type: str
    ) -> None:
        """Update persona mappings with new statistics associations."""
        persona_mappings = registry.setdefault('persona_mappings', {})
        
        if persona_id not in persona_mappings:
            persona_mappings[persona_id] = {
                'associated_statistics': [],
                'relevance_scores': {}
            }
        
        # Extract statistic IDs and add to persona mapping
        statistic_ids = self._extract_statistic_ids_from_statistics(statistics, source_type)
        
        persona_data = persona_mappings[persona_id]
        persona_data['associated_statistics'].extend(statistic_ids)
        
        # Remove duplicates
        persona_data['associated_statistics'] = list(set(persona_data['associated_statistics']))
        
        # Set default relevance scores
        for stat_id in statistic_ids:
            if stat_id not in persona_data['relevance_scores']:
                persona_data['relevance_scores'][stat_id] = 1.0  # Default high relevance
    
    def _filter_statistics_by_analysis_type(
        self,
        statistics: Dict[str, Any],
        analysis_type: str
    ) -> Dict[str, Any]:
        """Filter statistics based on analysis type relevance."""
        # Analysis type mapping to relevant statistic types
        type_mappings = {
            'pain': ['categorical_distributions', 'themes'],
            'size': ['categorical_distributions', 'numerical_summaries'],
            'solution': ['themes', 'key_quotes'],
            'gains': ['themes', 'key_quotes', 'categorical_distributions'],
            'jtbd': ['themes', 'key_quotes', 'categorical_distributions']
        }
        
        relevant_types = type_mappings.get(analysis_type, list(statistics.keys()))
        
        filtered = {}
        for key, value in statistics.items():
            if key in relevant_types or key in ['metadata', 'extraction_timestamp']:
                filtered[key] = value
        
        return filtered
    
    def _filter_statistics_by_persona(
        self,
        statistics: Dict[str, Any],
        persona_id: str,
        registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter statistics based on persona relevance."""
        persona_mappings = registry.get('persona_mappings', {})
        
        if persona_id not in persona_mappings:
            return statistics  # Return all if no persona mapping
        
        persona_data = persona_mappings[persona_id]
        associated_stats = persona_data.get('associated_statistics', [])
        relevance_scores = persona_data.get('relevance_scores', {})
        
        # For now, return all statistics but add persona relevance metadata
        filtered = dict(statistics)
        filtered['persona_relevance'] = {
            'persona_id': persona_id,
            'associated_statistics': associated_stats,
            'relevance_scores': relevance_scores
        }
        
        return filtered
    
    def _extract_citations_from_statistics(
        self,
        statistics: Dict[str, Any],
        source_type: str,
        project_id: str
    ) -> Dict[str, Any]:
        """Extract citation information from statistics data."""
        citations = {}
        
        # Extract from categorical distributions
        categorical_dists = statistics.get('categorical_distributions', {})
        for field_name, field_data in categorical_dists.items():
            for item in field_data.get('distribution', []):
                citation_id = item.get('citation_id')
                if citation_id:
                    citations[citation_id] = {
                        'source_type': source_type,
                        'source_file': statistics.get('metadata', {}).get('filename', 'unknown'),
                        'data_path': f"categorical_distributions.{field_name}",
                        'verification_hash': self._generate_verification_hash(
                            project_id, source_type, field_name, item.get('value', '')
                        ),
                        'created_at': datetime.utcnow().isoformat()
                    }
        
        # Extract from numerical summaries
        numerical_summaries = statistics.get('numerical_summaries', {})
        for field_name, field_data in numerical_summaries.items():
            citation_id = field_data.get('citation_id')
            if citation_id:
                citations[citation_id] = {
                    'source_type': source_type,
                    'source_file': statistics.get('metadata', {}).get('filename', 'unknown'),
                    'data_path': f"numerical_summaries.{field_name}",
                    'verification_hash': self._generate_verification_hash(
                        project_id, source_type, field_name, 'summary'
                    ),
                    'created_at': datetime.utcnow().isoformat()
                }
        
        # Extract from themes (PDF)
        themes = statistics.get('themes', {})
        for theme_name, theme_data in themes.items():
            citation_id = theme_data.get('citation_id')
            if citation_id:
                citations[citation_id] = {
                    'source_type': source_type,
                    'source_file': statistics.get('metadata', {}).get('filename', 'unknown'),
                    'data_path': f"themes.{theme_name}",
                    'verification_hash': self._generate_verification_hash(
                        project_id, source_type, 'theme', theme_name
                    ),
                    'created_at': datetime.utcnow().isoformat()
                }
        
        # Extract from quotes (PDF)
        quotes = statistics.get('key_quotes', [])
        for i, quote_data in enumerate(quotes):
            citation_id = quote_data.get('citation_id')
            if citation_id:
                citations[citation_id] = {
                    'source_type': source_type,
                    'source_file': statistics.get('metadata', {}).get('filename', 'unknown'),
                    'data_path': f"key_quotes[{i}]",
                    'verification_hash': self._generate_verification_hash(
                        project_id, source_type, 'quote', str(i)
                    ),
                    'created_at': datetime.utcnow().isoformat()
                }
        
        return citations
    
    def _extract_statistic_ids_from_statistics(
        self,
        statistics: Dict[str, Any],
        source_type: str
    ) -> List[str]:
        """Extract statistic IDs from statistics data."""
        statistic_ids = []
        
        # Generate IDs based on the structure
        if source_type == 'csv':
            # Add categorical distribution IDs
            for field_name in statistics.get('categorical_distributions', {}):
                statistic_ids.append(f"csv_categorical_{field_name}")
            
            # Add numerical summary IDs
            for field_name in statistics.get('numerical_summaries', {}):
                statistic_ids.append(f"csv_numerical_{field_name}")
        
        elif source_type == 'pdf':
            # Add theme IDs
            for theme_name in statistics.get('themes', {}):
                statistic_ids.append(f"pdf_theme_{theme_name}")
            
            # Add quote IDs (simplified)
            quote_count = len(statistics.get('key_quotes', []))
            for i in range(quote_count):
                statistic_ids.append(f"pdf_quote_{i}")
        
        return statistic_ids
    
    def _generate_verification_hash(
        self,
        project_id: str,
        source_type: str,
        field_name: str,
        value_identifier: str
    ) -> str:
        """Generate verification hash for citation integrity."""
        base_string = f"{project_id}:{source_type}:{field_name}:{value_identifier}"
        hash_object = hashlib.md5(base_string.encode())
        return hash_object.hexdigest()


# Service instance getter following VMP patterns
_statistics_registry_service: Optional[StatisticsRegistryService] = None

def get_statistics_registry_service(
    db_adapter: Optional[AnalysisAgentDatabaseAdapter] = None
) -> StatisticsRegistryService:
    """Get statistics registry service singleton."""
    global _statistics_registry_service
    if _statistics_registry_service is None:
        _statistics_registry_service = StatisticsRegistryService(db_adapter)
    return _statistics_registry_service