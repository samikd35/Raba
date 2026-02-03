"""
Ground Truth Context Builder (Tier 1) - Two-Tier RAG System

This module implements the first tier of the two-tier RAG architecture, ensuring that
every analysis prompt includes complete, accurate statistical context from the statistics
registry. This eliminates "chunk hallucination" by providing ground truth data directly.

Key Features:
- Always includes pre-computed statistics (~500 tokens)
- Filters statistics by analysis type and persona context
- Embeds citations for full traceability
- Ensures statistical accuracy regardless of retrieval results
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..models.analysis_models import StatisticsRegistryEntry
from ..services.statistics_registry_service import StatisticsRegistryService
from ..utils.error_handling import ErrorHandlingService

logger = logging.getLogger(__name__)


class GroundTruthContextBuilder:
    """
    Builds Tier 1 context with ground truth statistics for analysis prompts.
    
    This class ensures that every analysis includes accurate, pre-computed statistics
    as the foundation for quantitative claims, preventing chunk-based hallucination.
    """
    
    def __init__(
        self,
        statistics_registry: StatisticsRegistryService,
        error_handler: ErrorHandlingService
    ):
        self.registry = statistics_registry
        self.error_handler = error_handler
        self.max_tokens = 16_000  # gpt-5-mini needs large token budget
        
        # Analysis type to relevant statistic categories mapping
        self.analysis_type_filters = {
            'pain': ['problems', 'challenges', 'difficulties', 'frustrations', 'obstacles'],
            'size': ['frequency', 'percentage', 'statistics', 'demographics', 'distribution'],
            'solution': ['current_solutions', 'alternatives', 'workarounds', 'existing_tools'],
            'gains': ['benefits', 'advantages', 'value', 'outcomes', 'results'],
            'jtbd': ['tasks', 'jobs', 'goals', 'objectives', 'needs']
        }
    
    async def build_statistics_context(
        self,
        project_id: str,
        tenant_id: str,
        analysis_type: str,
        persona_id: Optional[str] = None
    ) -> str:
        """
        Build Tier 1 context with ground truth statistics.
        
        Args:
            project_id: Project identifier
            tenant_id: Tenant identifier
            analysis_type: Type of analysis (pain, size, solution, gains, jtbd)
            persona_id: Optional persona filter
            
        Returns:
            Formatted statistics context string (~500 tokens)
        """
        try:
            # Get relevant statistics from registry
            statistics = await self.registry.get_statistics_for_analysis(
                project_id=project_id,
                tenant_id=tenant_id,
                analysis_type=analysis_type,
                persona_id=persona_id
            )
            
            if not statistics:
                logger.warning(f"No statistics found for project {project_id}, analysis {analysis_type}")
                return self._build_empty_context()
            
            # Build formatted context
            context_parts = [
                "═══════════════════════════════════════════════════════════",
                "📊 GROUND TRUTH STATISTICS - SOURCE OF TRUTH FOR ALL PERCENTAGES",
                "═══════════════════════════════════════════════════════════",
                "CRITICAL: Use ONLY these pre-computed statistics for quantitative claims.",
                "DO NOT calculate percentages from evidence chunks below.",
                ""
            ]
            
            # Add CSV statistics
            csv_stats = statistics.get('csv_statistics', {})
            if csv_stats:
                context_parts.extend(self._format_csv_statistics(csv_stats, analysis_type))
            
            # Add PDF statistics
            pdf_stats = statistics.get('pdf_statistics', {})
            if pdf_stats:
                context_parts.extend(self._format_pdf_statistics(pdf_stats, analysis_type))
            
            # Add persona context if specified
            if persona_id:
                persona_context = self._format_persona_context(statistics, persona_id)
                if persona_context:
                    context_parts.extend(persona_context)
            
            # Add citation registry information
            citation_info = self._format_citation_info(statistics.get('citation_registry', {}))
            if citation_info:
                context_parts.extend(citation_info)
            
            context_parts.append("═══════════════════════════════════════════════════════════")
            
            full_context = "\n".join(context_parts)
            
            # Ensure token budget compliance
            return self._ensure_token_budget(full_context)
            
        except Exception as e:
            logger.error(f"Error building ground truth context: {e}")
            return await self.error_handler.handle_context_building_error(e, {
                'project_id': project_id,
                'analysis_type': analysis_type,
                'persona_id': persona_id
            })
    
    def _format_csv_statistics(self, csv_stats: Dict[str, Any], analysis_type: str) -> List[str]:
        """Format CSV statistics for context inclusion."""
        formatted = ["📈 SURVEY DATA STATISTICS:"]
        
        metadata = csv_stats.get('metadata', {})
        if metadata:
            formatted.append(f"Source: {metadata.get('filename', 'Unknown')}")
            formatted.append(f"Total Responses: {metadata.get('total_rows', 0)}")
            formatted.append("")
        
        # Filter and format categorical distributions
        distributions = csv_stats.get('categorical_distributions', {})
        relevant_fields = self._filter_relevant_fields(distributions, analysis_type)
        
        for field_name, field_data in relevant_fields.items():
            formatted.append(f"📊 {field_name.replace('_', ' ').title()}:")
            formatted.append(f"   Total Responses: {field_data.get('total_responses', 0)}")
            
            # Add top distributions
            distribution = field_data.get('distribution', [])[:5]  # Top 5 values
            for item in distribution:
                value = item.get('value', 'Unknown')
                count = item.get('count', 0)
                percentage = item.get('percentage', 0.0)
                citation_id = item.get('citation_id', '')
                formatted.append(f"   • {value}: {count} ({percentage:.1f}%) [Cite: {citation_id}]")
            
            formatted.append("")
        
        return formatted
    
    def _format_pdf_statistics(self, pdf_stats: Dict[str, Any], analysis_type: str) -> List[str]:
        """Format PDF statistics for context inclusion."""
        formatted = ["🎤 INTERVIEW DATA STATISTICS:"]
        
        metadata = pdf_stats.get('metadata', {})
        if metadata:
            formatted.append(f"Source: {metadata.get('filename', 'Unknown')}")
            formatted.append(f"Total Pages: {metadata.get('total_pages', 0)}")
            formatted.append(f"Total Segments: {metadata.get('total_segments', 0)}")
            formatted.append("")
        
        # Filter and format themes
        themes = pdf_stats.get('themes', {})
        relevant_themes = self._filter_relevant_themes(themes, analysis_type)
        
        if relevant_themes:
            formatted.append("🏷️ Key Themes:")
            for theme_name, theme_data in list(relevant_themes.items())[:8]:  # Top 8 themes
                frequency = theme_data.get('frequency', 0)
                percentage = theme_data.get('percentage', 0.0)
                citation_id = theme_data.get('citation_id', '')
                formatted.append(f"   • {theme_name}: {frequency} mentions ({percentage:.1f}%) [Cite: {citation_id}]")
            formatted.append("")
        
        # Add participant profile summary
        participant_profile = pdf_stats.get('participant_profile', {})
        if participant_profile:
            demographics = participant_profile.get('demographics', {})
            if demographics:
                formatted.append("👥 Participant Demographics:")
                for demo_key, demo_value in list(demographics.items())[:3]:  # Top 3 demographics
                    formatted.append(f"   • {demo_key}: {demo_value}")
                formatted.append("")
        
        return formatted
    
    def _format_persona_context(self, statistics: Dict[str, Any], persona_id: str) -> List[str]:
        """Format persona-specific context information."""
        persona_mappings = statistics.get('persona_mappings', {})
        persona_data = persona_mappings.get(persona_id, {})
        
        if not persona_data:
            return []
        
        formatted = [f"🎯 PERSONA-SPECIFIC DATA (ID: {persona_id}):"]
        
        associated_stats = persona_data.get('associated_statistics', [])
        if associated_stats:
            formatted.append(f"   Associated Statistics: {len(associated_stats)} entries")
        
        relevance_scores = persona_data.get('relevance_scores', {})
        if relevance_scores:
            high_relevance = {k: v for k, v in relevance_scores.items() if v > 0.7}
            if high_relevance:
                formatted.append("   High Relevance Areas:")
                for area, score in list(high_relevance.items())[:3]:
                    formatted.append(f"   • {area}: {score:.2f}")
        
        formatted.append("")
        return formatted
    
    def _format_citation_info(self, citation_registry: Dict[str, Any]) -> List[str]:
        """Format citation registry information."""
        if not citation_registry:
            return []
        
        formatted = ["📚 CITATION REGISTRY:"]
        formatted.append(f"   Total Citations Available: {len(citation_registry)}")
        formatted.append("   All statistics above include citation IDs for verification.")
        formatted.append("")
        
        return formatted
    
    def _filter_relevant_fields(self, distributions: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Filter categorical distributions based on analysis type."""
        if analysis_type not in self.analysis_type_filters:
            return distributions
        
        keywords = self.analysis_type_filters[analysis_type]
        relevant_fields = {}
        
        for field_name, field_data in distributions.items():
            field_lower = field_name.lower()
            
            # Check if field name contains relevant keywords
            if any(keyword in field_lower for keyword in keywords):
                relevant_fields[field_name] = field_data
                continue
            
            # For 'size' analysis, include all demographic fields
            if analysis_type == 'size':
                relevant_fields[field_name] = field_data
        
        # If no specific matches, include top fields by response count
        if not relevant_fields and distributions:
            sorted_fields = sorted(
                distributions.items(),
                key=lambda x: x[1].get('total_responses', 0),
                reverse=True
            )
            relevant_fields = dict(sorted_fields[:5])
        
        return relevant_fields
    
    def _filter_relevant_themes(self, themes: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Filter PDF themes based on analysis type."""
        if analysis_type not in self.analysis_type_filters:
            return themes
        
        keywords = self.analysis_type_filters[analysis_type]
        relevant_themes = {}
        
        for theme_name, theme_data in themes.items():
            theme_lower = theme_name.lower()
            
            # Check if theme name contains relevant keywords
            if any(keyword in theme_lower for keyword in keywords):
                relevant_themes[theme_name] = theme_data
        
        # If no specific matches, include top themes by frequency
        if not relevant_themes and themes:
            sorted_themes = sorted(
                themes.items(),
                key=lambda x: x[1].get('frequency', 0),
                reverse=True
            )
            relevant_themes = dict(sorted_themes[:8])
        
        return relevant_themes
    
    def _ensure_token_budget(self, context: str) -> str:
        """Ensure context stays within token budget (~500 tokens)."""
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = self.max_tokens * 4
        
        if len(context) <= max_chars:
            return context
        
        # Truncate while preserving structure
        lines = context.split('\n')
        truncated_lines = []
        current_length = 0
        
        # Always include header
        header_end = 6  # First 6 lines are header
        for i in range(min(header_end, len(lines))):
            truncated_lines.append(lines[i])
            current_length += len(lines[i]) + 1
        
        # Add content within budget
        for i in range(header_end, len(lines)):
            line_length = len(lines[i]) + 1
            if current_length + line_length > max_chars:
                truncated_lines.append("... [Content truncated to fit token budget] ...")
                break
            truncated_lines.append(lines[i])
            current_length += line_length
        
        return '\n'.join(truncated_lines)
    
    def _build_empty_context(self) -> str:
        """Build context when no statistics are available."""
        return """
═══════════════════════════════════════════════════════════
📊 GROUND TRUTH STATISTICS - SOURCE OF TRUTH FOR ALL PERCENTAGES
═══════════════════════════════════════════════════════════
CRITICAL: Use ONLY these pre-computed statistics for quantitative claims.
DO NOT calculate percentages from evidence chunks below.

⚠️  NO STATISTICS AVAILABLE
No pre-computed statistics found for this analysis.
Proceed with qualitative analysis only.
Avoid making specific percentage or frequency claims.

═══════════════════════════════════════════════════════════
"""
    
    async def get_statistics_summary(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of available statistics for validation purposes.
        
        Returns:
            Dictionary with statistics availability and metadata
        """
        try:
            statistics = await self.registry.get_statistics_for_analysis(
                project_id=project_id,
                tenant_id=tenant_id,
                analysis_type='comprehensive',  # Get all statistics
                persona_id=persona_id
            )
            
            if not statistics:
                return {'available': False, 'reason': 'No statistics found'}
            
            summary = {
                'available': True,
                'csv_statistics_count': len(statistics.get('csv_statistics', {}).get('categorical_distributions', {})),
                'pdf_themes_count': len(statistics.get('pdf_statistics', {}).get('themes', {})),
                'citation_count': len(statistics.get('citation_registry', {})),
                'persona_associations': len(statistics.get('persona_mappings', {})),
                'last_updated': statistics.get('metadata', {}).get('last_updated')
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting statistics summary: {e}")
            return {'available': False, 'reason': f'Error: {str(e)}'}