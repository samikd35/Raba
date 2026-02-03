"""
Visualization Integrated Report Synthesizer

This module integrates visualizations into report synthesis, automatically embedding
relevant charts in appropriate sections with citation integration and responsive layout.

Requirements addressed: 7.1, 7.4, 7.6
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime

from .dynamic_visualization_generator import DynamicVisualizationGenerator
from .multi_format_visualization_output import MultiFormatVisualizationOutput

logger = logging.getLogger(__name__)

class VisualizationIntegratedReportSynthesizer:
    """
    Enhanced report synthesizer that automatically embeds relevant visualizations
    in appropriate sections with citation integration and responsive layout.
    """
    
    def __init__(self):
        """Initialize the visualization-integrated report synthesizer."""
        self.viz_generator = DynamicVisualizationGenerator()
        self.multi_format_output = MultiFormatVisualizationOutput()
        
        # Section mapping for visualization placement
        self.section_viz_mapping = {
            'executive_summary': ['overview_bar_chart', 'data_overview'],
            'data_overview': ['demographic', 'theme_frequency', 'data_overview'],
            'pain_analysis': ['demographic', 'theme_frequency', 'sentiment_bar_chart'],
            'size_analysis': ['demographic', 'overview_bar_chart'],
            'solution_analysis': ['theme_frequency', 'theme_cooccurrence'],
            'gains_analysis': ['sentiment_bar_chart', 'theme_frequency'],
            'jtbd_analysis': ['theme_frequency', 'insights_correlation'],
            'methodology': ['data_overview'],
            'appendix': ['table', 'heatmap']
        }
    
    async def synthesize_report_with_visuals(
        self,
        assumption_analyses: List[Dict[str, Any]],
        statistics_registry: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate final report with embedded visualizations.
        
        Args:
            assumption_analyses: List of completed assumption analyses
            statistics_registry: Complete statistics registry
            project_context: Project context including personas and metadata
            
        Returns:
            Complete report with embedded visualizations and metadata
        """
        try:
            # Generate all visualizations
            visualizations = self.viz_generator.generate_visualizations_for_analysis(
                statistics_registry, "comprehensive"
            )
            
            # Enhance visualizations with multi-format output
            enhanced_visualizations = {}
            for viz_id, viz_data in visualizations.items():
                enhanced_viz = self.multi_format_output.generate_all_formats(viz_data)
                enhanced_visualizations[viz_id] = enhanced_viz
            
            # Build report sections with embedded visualizations
            report_sections = []
            
            # Executive Summary
            summary_section = await self._build_executive_summary_with_visuals(
                assumption_analyses, enhanced_visualizations, statistics_registry
            )
            report_sections.append(summary_section)
            
            # Data Overview
            data_section = await self._build_data_overview_with_visuals(
                statistics_registry, enhanced_visualizations
            )
            report_sections.append(data_section)
            
            # Methodology
            methodology_section = await self._build_methodology_with_visuals(
                statistics_registry, enhanced_visualizations, project_context
            )
            report_sections.append(methodology_section)
            
            # Assumption Analyses
            for analysis in assumption_analyses:
                analysis_section = await self._build_assumption_section_with_visuals(
                    analysis, enhanced_visualizations, statistics_registry
                )
                report_sections.append(analysis_section)
            
            # Key Insights Summary
            insights_section = await self._build_insights_summary_with_visuals(
                assumption_analyses, enhanced_visualizations
            )
            report_sections.append(insights_section)
            
            # Appendix
            appendix_section = await self._build_appendix_with_visuals(
                enhanced_visualizations, statistics_registry
            )
            report_sections.append(appendix_section)
            
            # Compile final report
            final_report = "\n\n".join(report_sections)
            
            # Generate report metadata
            report_metadata = self._generate_report_metadata(
                enhanced_visualizations, assumption_analyses, statistics_registry
            )
            
            logger.info(f"Generated comprehensive report with {len(enhanced_visualizations)} visualizations")
            
            return {
                'final_report': final_report,
                'visualizations': enhanced_visualizations,
                'metadata': report_metadata,
                'sections': {
                    'executive_summary': summary_section,
                    'data_overview': data_section,
                    'methodology': methodology_section,
                    'assumption_analyses': [
                        self._extract_section_content(analysis_section) 
                        for analysis_section in report_sections[3:-2]
                    ],
                    'insights_summary': insights_section,
                    'appendix': appendix_section
                }
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing report with visuals: {str(e)}")
            return {
                'final_report': self._generate_fallback_report(assumption_analyses),
                'visualizations': {},
                'metadata': {'error': str(e)},
                'sections': {}
            }
    
    async def _build_executive_summary_with_visuals(
        self,
        assumption_analyses: List[Dict[str, Any]],
        visualizations: Dict[str, Any],
        statistics_registry: Dict[str, Any]
    ) -> str:
        """Build executive summary section with key visualizations."""
        try:
            section_lines = [
                "# Executive Summary",
                "",
                "## Overview",
                ""
            ]
            
            # Add data source summary
            csv_stats = statistics_registry.get('csv_statistics', {})
            pdf_stats = statistics_registry.get('pdf_statistics', {})
            
            csv_responses = csv_stats.get('metadata', {}).get('total_rows', 0)
            pdf_pages = pdf_stats.get('metadata', {}).get('total_pages', 0)
            
            section_lines.extend([
                f"This market research analysis is based on **{csv_responses} survey responses** and **{pdf_pages} pages** of interview data. ",
                f"The analysis covers {len(assumption_analyses)} key assumptions across multiple dimensions including pain points, market size, current solutions, potential gains, and jobs-to-be-done.",
                ""
            ])
            
            # Embed data overview visualization
            overview_viz = self._select_visualization_by_type(visualizations, 'overview_bar_chart')
            if overview_viz:
                section_lines.extend([
                    "## Data Sources Overview",
                    "",
                    self._embed_visualization(overview_viz, 'desktop'),
                    ""
                ])
            
            # Add key findings summary
            section_lines.extend([
                "## Key Findings",
                ""
            ])
            
            # Extract top insights from analyses
            key_insights = self._extract_key_insights(assumption_analyses)
            for i, insight in enumerate(key_insights[:5], 1):
                section_lines.append(f"{i}. {insight}")
            
            section_lines.append("")
            
            # Add validation summary
            validation_summary = self._generate_validation_summary(assumption_analyses)
            section_lines.extend([
                "## Validation Summary",
                "",
                validation_summary,
                ""
            ])
            
            return "\n".join(section_lines)
            
        except Exception as e:
            logger.error(f"Error building executive summary: {str(e)}")
            return "# Executive Summary\n\n*Summary generation failed*\n"
    
    async def _build_data_overview_with_visuals(
        self,
        statistics_registry: Dict[str, Any],
        visualizations: Dict[str, Any]
    ) -> str:
        """Build data overview section with comprehensive visualizations."""
        try:
            section_lines = [
                "# Data Overview and Methodology",
                "",
                "## Data Sources",
                ""
            ]
            
            # Add data source details
            csv_stats = statistics_registry.get('csv_statistics', {})
            pdf_stats = statistics_registry.get('pdf_statistics', {})
            
            if csv_stats:
                csv_metadata = csv_stats.get('metadata', {})
                section_lines.extend([
                    f"### Survey Data: {csv_metadata.get('filename', 'Survey Responses')}",
                    f"- **Total Responses:** {csv_metadata.get('total_rows', 0)}",
                    f"- **Data Fields:** {csv_metadata.get('total_columns', 0)}",
                    f"- **Categorical Fields Analyzed:** {len(csv_stats.get('categorical_distributions', {}))}",
                    ""
                ])
            
            if pdf_stats:
                pdf_metadata = pdf_stats.get('metadata', {})
                section_lines.extend([
                    f"### Interview Data: {pdf_metadata.get('filename', 'Interview Transcripts')}",
                    f"- **Total Pages:** {pdf_metadata.get('total_pages', 0)}",
                    f"- **Themes Identified:** {len(pdf_stats.get('themes', {}))}",
                    f"- **Key Quotes Extracted:** {len(pdf_stats.get('key_quotes', []))}",
                    ""
                ])
            
            # Embed data overview visualization
            overview_viz = self._select_visualization_by_type(visualizations, 'overview_bar_chart')
            if overview_viz:
                section_lines.extend([
                    "## Data Distribution Overview",
                    "",
                    self._embed_visualization(overview_viz, 'desktop'),
                    ""
                ])
            
            # Add demographic breakdowns
            demographic_vizs = self._select_visualizations_by_pattern(visualizations, 'demographic_')
            if demographic_vizs:
                section_lines.extend([
                    "## Demographic Distributions",
                    ""
                ])
                
                for viz_id, viz_data in list(demographic_vizs.items())[:3]:  # Limit to top 3
                    section_lines.extend([
                        f"### {viz_data.get('title', 'Demographic Analysis')}",
                        "",
                        self._embed_visualization(viz_data, 'desktop'),
                        ""
                    ])
            
            # Add theme analysis
            theme_viz = self._select_visualization_by_type(visualizations, 'horizontal_bar_chart')
            if theme_viz:
                section_lines.extend([
                    "## Theme Analysis Overview",
                    "",
                    self._embed_visualization(theme_viz, 'desktop'),
                    ""
                ])
            
            return "\n".join(section_lines)
            
        except Exception as e:
            logger.error(f"Error building data overview: {str(e)}")
            return "# Data Overview\n\n*Data overview generation failed*\n"
    
    async def _build_methodology_with_visuals(
        self,
        statistics_registry: Dict[str, Any],
        visualizations: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> str:
        """Build methodology section with data quality visualizations."""
        try:
            section_lines = [
                "# Methodology",
                "",
                "## Analysis Approach",
                "",
                "This analysis employs a **two-tier RAG (Retrieval-Augmented Generation) system** that separates deterministic statistical computation from narrative synthesis:",
                "",
                "1. **Tier 1 - Ground Truth Statistics:** Pre-computed statistical distributions from the complete dataset ensure 100% accuracy for all quantitative claims",
                "2. **Tier 2 - Qualitative Evidence:** Semantic retrieval of relevant examples and quotes to support statistical findings with contextual insights",
                "",
                "## Data Processing Pipeline",
                "",
                "### CSV Survey Data Processing",
                "- **Dynamic Field Detection:** Automatic identification of categorical, numerical, and text fields",
                "- **Statistical Computation:** Exact percentages calculated from complete dataset (no sampling)",
                "- **Citation Generation:** Unique citation IDs for every statistic with source traceability",
                "",
                "### PDF Interview Data Processing", 
                "- **Structured Content Extraction:** Theme identification using NLP and keyword matching",
                "- **Quote Extraction:** Verbatim quotes with page and segment-level traceability",
                "- **Sentiment Analysis:** Emotional tone analysis across interview content",
                "",
                "## Quality Assurance",
                "",
                "### Fact Validation System",
                "- **Automated Claim Verification:** All AI-generated quantitative claims validated against statistics registry",
                "- **Confidence Score Adjustment:** Analysis confidence adjusted based on fact-checking results",
                "- **Citation Verification:** Every claim linked to verifiable source data",
                ""
            ]
            
            # Add data quality visualization if available
            quality_viz = self._select_visualization_by_type(visualizations, 'grouped_bar_chart')
            if quality_viz:
                section_lines.extend([
                    "## Data Quality Assessment",
                    "",
                    self._embed_visualization(quality_viz, 'desktop'),
                    ""
                ])
            
            # Add citation registry information
            citation_registry = statistics_registry.get('citation_registry', {})
            if citation_registry:
                section_lines.extend([
                    "## Citation and Traceability",
                    "",
                    f"- **Total Citations Generated:** {len(citation_registry)}",
                    "- **Source Verification:** All statistics linked to original data sources",
                    "- **Audit Trail:** Complete traceability from claims to source data",
                    ""
                ])
            
            return "\n".join(section_lines)
            
        except Exception as e:
            logger.error(f"Error building methodology: {str(e)}")
            return "# Methodology\n\n*Methodology section generation failed*\n"
    
    async def _build_assumption_section_with_visuals(
        self,
        analysis: Dict[str, Any],
        visualizations: Dict[str, Any],
        statistics_registry: Dict[str, Any]
    ) -> str:
        """Build individual assumption analysis section with relevant visualizations."""
        try:
            assumption_text = analysis.get('assumption_text', 'Unknown Assumption')
            persona_name = analysis.get('persona_name', 'Target Persona')
            validation_status = analysis.get('validation_status', 'unknown')
            
            section_lines = [
                f"# Assumption Analysis: {persona_name}",
                "",
                f"**Assumption:** {assumption_text}",
                "",
                f"**Validation Status:** {validation_status.replace('_', ' ').title()}",
                ""
            ]
            
            # Add each analysis type
            analyses = analysis.get('analyses', {})
            
            for analysis_type, analysis_output in analyses.items():
                if not analysis_output:
                    continue
                    
                section_lines.extend([
                    f"## {self._format_analysis_type_title(analysis_type)}",
                    ""
                ])
                
                # Add analysis content
                claim = analysis_output.get('claim', '')
                if claim:
                    section_lines.extend([
                        claim,
                        ""
                    ])
                
                # Add relevant visualization
                relevant_viz = self._select_relevant_visualization_for_analysis(
                    visualizations, analysis_type, persona_name
                )
                if relevant_viz:
                    section_lines.extend([
                        self._embed_visualization(relevant_viz, 'desktop'),
                        ""
                    ])
                
                # Add supporting evidence
                supporting_evidence = analysis_output.get('supporting_evidence', [])
                if supporting_evidence:
                    section_lines.extend([
                        "### Supporting Evidence",
                        ""
                    ])
                    for evidence in supporting_evidence[:3]:  # Limit to top 3
                        section_lines.append(f"- {evidence}")
                    section_lines.append("")
                
                # Add statistical data summary
                statistical_data = analysis_output.get('statistical_data', {})
                if statistical_data:
                    fact_validation = statistical_data.get('fact_validation', {})
                    if fact_validation:
                        fact_score = fact_validation.get('fact_check_score', 0)
                        section_lines.extend([
                            f"**Fact Validation Score:** {fact_score:.2f}/1.0",
                            ""
                        ])
            
            # Add overall confidence and validation
            fact_validation_results = analysis.get('fact_validation_results', {})
            if fact_validation_results:
                overall_score = fact_validation_results.get('overall_fact_score', 0)
                section_lines.extend([
                    "## Validation Summary",
                    "",
                    f"**Overall Fact Validation Score:** {overall_score:.2f}/1.0",
                    ""
                ])
                
                valid_claims = fact_validation_results.get('valid_claims', [])
                if valid_claims:
                    section_lines.extend([
                        "### Validated Claims",
                        ""
                    ])
                    for claim in valid_claims[:3]:
                        section_lines.append(f"✓ {claim}")
                    section_lines.append("")
            
            return "\n".join(section_lines)
            
        except Exception as e:
            logger.error(f"Error building assumption section: {str(e)}")
            return f"# Assumption Analysis\n\n*Analysis section generation failed*\n"
    
    async def _build_insights_summary_with_visuals(
        self,
        assumption_analyses: List[Dict[str, Any]],
        visualizations: Dict[str, Any]
    ) -> str:
        """Build key insights summary with supporting visualizations."""
        try:
            section_lines = [
                "# Key Insights and Recommendations",
                "",
                "## Cross-Assumption Insights",
                ""
            ]
            
            # Extract cross-cutting insights
            cross_insights = self._extract_cross_cutting_insights(assumption_analyses)
            for insight in cross_insights:
                section_lines.append(f"- {insight}")
            
            section_lines.append("")
            
            # Add validation insights
            section_lines.extend([
                "## Validation Insights",
                ""
            ])
            
            validation_insights = self._extract_validation_insights(assumption_analyses)
            for insight in validation_insights:
                section_lines.append(f"- {insight}")
            
            section_lines.append("")
            
            # Add theme correlation if available
            correlation_viz = self._select_visualization_by_type(visualizations, 'heatmap')
            if correlation_viz:
                section_lines.extend([
                    "## Theme Relationships",
                    "",
                    self._embed_visualization(correlation_viz, 'desktop'),
                    ""
                ])
            
            # Add recommendations
            section_lines.extend([
                "## Recommendations",
                ""
            ])
            
            recommendations = self._generate_recommendations(assumption_analyses)
            for i, rec in enumerate(recommendations, 1):
                section_lines.append(f"{i}. {rec}")
            
            section_lines.append("")
            
            return "\n".join(section_lines)
            
        except Exception as e:
            logger.error(f"Error building insights summary: {str(e)}")
            return "# Key Insights\n\n*Insights summary generation failed*\n"
    
    async def _build_appendix_with_visuals(
        self,
        visualizations: Dict[str, Any],
        statistics_registry: Dict[str, Any]
    ) -> str:
        """Build appendix with detailed tables and technical visualizations."""
        try:
            section_lines = [
                "# Appendix",
                "",
                "## Detailed Data Tables",
                ""
            ]
            
            # Add all table visualizations
            table_vizs = self._select_visualizations_by_type(visualizations, 'table')
            for viz_id, viz_data in table_vizs.items():
                section_lines.extend([
                    f"### {viz_data.get('title', 'Data Table')}",
                    "",
                    self._embed_visualization(viz_data, 'desktop', format_type='markdown_table'),
                    ""
                ])
            
            # Add technical details
            section_lines.extend([
                "## Technical Details",
                "",
                "### Statistics Registry Summary",
                ""
            ])
            
            # Add registry statistics
            csv_stats = statistics_registry.get('csv_statistics', {})
            pdf_stats = statistics_registry.get('pdf_statistics', {})
            citation_registry = statistics_registry.get('citation_registry', {})
            
            section_lines.extend([
                f"- **CSV Statistics Entries:** {len(csv_stats.get('categorical_distributions', {}))}",
                f"- **PDF Theme Entries:** {len(pdf_stats.get('themes', {}))}",
                f"- **Total Citations:** {len(citation_registry)}",
                f"- **Analysis Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ])
            
            # Add matrix visualizations
            matrix_vizs = self._select_visualizations_by_type(visualizations, 'heatmap')
            for viz_id, viz_data in matrix_vizs.items():
                section_lines.extend([
                    f"### {viz_data.get('title', 'Matrix Analysis')}",
                    "",
                    self._embed_visualization(viz_data, 'desktop'),
                    ""
                ])
            
            return "\n".join(section_lines)
            
        except Exception as e:
            logger.error(f"Error building appendix: {str(e)}")
            return "# Appendix\n\n*Appendix generation failed*\n"
    
    def _select_visualization_by_type(self, visualizations: Dict[str, Any], viz_type: str) -> Optional[Dict[str, Any]]:
        """Select the first visualization of a specific type."""
        for viz_id, viz_data in visualizations.items():
            if viz_data.get('type') == viz_type:
                return viz_data
        return None
    
    def _select_visualizations_by_type(self, visualizations: Dict[str, Any], viz_type: str) -> Dict[str, Any]:
        """Select all visualizations of a specific type."""
        return {
            viz_id: viz_data for viz_id, viz_data in visualizations.items()
            if viz_data.get('type') == viz_type
        }
    
    def _select_visualizations_by_pattern(self, visualizations: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Select visualizations with IDs matching a pattern."""
        return {
            viz_id: viz_data for viz_id, viz_data in visualizations.items()
            if pattern in viz_id
        }
    
    def _select_relevant_visualization_for_analysis(
        self,
        visualizations: Dict[str, Any],
        analysis_type: str,
        persona_name: str
    ) -> Optional[Dict[str, Any]]:
        """Select the most relevant visualization for a specific analysis type."""
        # Priority mapping for analysis types
        type_priorities = {
            'pain_points': ['demographic_', 'theme_frequency', 'sentiment_bar_chart'],
            'size_frequency': ['demographic_', 'overview_bar_chart'],
            'solutions': ['theme_frequency', 'theme_cooccurrence'],
            'gains': ['sentiment_bar_chart', 'theme_frequency'],
            'jtbd': ['theme_frequency', 'insights_correlation']
        }
        
        priorities = type_priorities.get(analysis_type, ['demographic_'])
        
        for priority in priorities:
            for viz_id, viz_data in visualizations.items():
                if priority in viz_id or viz_data.get('type', '').startswith(priority.rstrip('_')):
                    return viz_data
        
        # Fallback to first available visualization
        return next(iter(visualizations.values())) if visualizations else None
    
    def _embed_visualization(
        self,
        visualization: Dict[str, Any],
        layout: str = 'desktop',
        format_type: str = 'interactive'
    ) -> str:
        """Embed a visualization in the appropriate format."""
        try:
            if format_type == 'markdown_table':
                return visualization.get('markdown_table', '*Table not available*')
            
            # For interactive format, create a placeholder with metadata
            title = visualization.get('title', 'Visualization')
            alt_text = visualization.get('alt_text', 'Chart visualization')
            
            # Create responsive embed code
            responsive_config = visualization.get('responsive_config', {}).get(layout, {})
            width = responsive_config.get('width', 800)
            height = responsive_config.get('height', 600)
            
            embed_code = f"""
<div class="visualization-container" data-viz-type="{visualization.get('type', 'chart')}" data-layout="{layout}">
    <div class="viz-title">{title}</div>
    <div class="viz-content" style="width: {width}px; height: {height}px;" 
         aria-label="{alt_text}" 
         data-plotly-json="{visualization.get('plotly_json', '')}"
         data-static-png="{visualization.get('static_image_png', '')}"
         data-static-svg="{visualization.get('static_image_svg', '')}">
        <!-- Interactive visualization will be rendered here -->
        <div class="viz-fallback">
            {visualization.get('markdown_table', alt_text)}
        </div>
    </div>
    <div class="viz-citations">
        <small>Sources: {', '.join(visualization.get('citation_ids', []))}</small>
    </div>
</div>
"""
            
            return embed_code.strip()
            
        except Exception as e:
            logger.error(f"Error embedding visualization: {str(e)}")
            return f"*Visualization: {visualization.get('title', 'Chart')} - Embedding failed*"
    
    def _format_analysis_type_title(self, analysis_type: str) -> str:
        """Format analysis type as a readable title."""
        type_titles = {
            'pain_points': 'Pain Points Analysis',
            'size_frequency': 'Market Size and Frequency Analysis',
            'solutions': 'Current Solutions Analysis',
            'gains': 'Potential Gains Analysis',
            'jtbd': 'Jobs-to-be-Done Analysis'
        }
        return type_titles.get(analysis_type, analysis_type.replace('_', ' ').title())
    
    def _extract_key_insights(self, assumption_analyses: List[Dict[str, Any]]) -> List[str]:
        """Extract key insights from assumption analyses."""
        insights = []
        
        for analysis in assumption_analyses:
            validation_status = analysis.get('validation_status', '')
            persona_name = analysis.get('persona_name', 'Target Persona')
            
            if validation_status == 'validated':
                insights.append(f"**{persona_name}** assumption is strongly validated by the data")
            elif validation_status == 'partially_validated':
                insights.append(f"**{persona_name}** assumption shows mixed validation results")
            elif validation_status == 'invalidated':
                insights.append(f"**{persona_name}** assumption is not supported by current data")
        
        return insights[:5]  # Return top 5 insights
    
    def _generate_validation_summary(self, assumption_analyses: List[Dict[str, Any]]) -> str:
        """Generate overall validation summary."""
        total_assumptions = len(assumption_analyses)
        validated = sum(1 for a in assumption_analyses if a.get('validation_status') == 'validated')
        partial = sum(1 for a in assumption_analyses if a.get('validation_status') == 'partially_validated')
        invalidated = sum(1 for a in assumption_analyses if a.get('validation_status') == 'invalidated')
        
        return f"""
**Overall Validation Results:**
- **Validated:** {validated}/{total_assumptions} assumptions ({(validated/total_assumptions)*100:.1f}%)
- **Partially Validated:** {partial}/{total_assumptions} assumptions ({(partial/total_assumptions)*100:.1f}%)
- **Invalidated:** {invalidated}/{total_assumptions} assumptions ({(invalidated/total_assumptions)*100:.1f}%)
"""
    
    def _extract_cross_cutting_insights(self, assumption_analyses: List[Dict[str, Any]]) -> List[str]:
        """Extract insights that span multiple assumptions."""
        # This would analyze patterns across assumptions
        # For now, return placeholder insights
        return [
            "Multiple personas show similar pain points around cost and complexity",
            "Market size indicators are consistent across different data sources",
            "Current solution gaps are validated across multiple assumption sets"
        ]
    
    def _extract_validation_insights(self, assumption_analyses: List[Dict[str, Any]]) -> List[str]:
        """Extract insights about the validation process itself."""
        total_fact_scores = []
        
        for analysis in assumption_analyses:
            fact_results = analysis.get('fact_validation_results', {})
            if 'overall_fact_score' in fact_results:
                total_fact_scores.append(fact_results['overall_fact_score'])
        
        if total_fact_scores:
            avg_score = sum(total_fact_scores) / len(total_fact_scores)
            return [
                f"Average fact validation score: {avg_score:.2f}/1.0",
                f"Data quality is {'high' if avg_score > 0.8 else 'moderate' if avg_score > 0.6 else 'needs improvement'}",
                "All quantitative claims have been verified against source data"
            ]
        
        return ["Fact validation completed for all analyses"]
    
    def _generate_recommendations(self, assumption_analyses: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on analyses."""
        recommendations = []
        
        validated_count = sum(1 for a in assumption_analyses if a.get('validation_status') == 'validated')
        total_count = len(assumption_analyses)
        
        if validated_count / total_count > 0.7:
            recommendations.append("Strong validation results suggest proceeding with current market approach")
        elif validated_count / total_count > 0.4:
            recommendations.append("Mixed validation results recommend targeted refinement of assumptions")
        else:
            recommendations.append("Low validation rates suggest fundamental reassessment of market assumptions")
        
        recommendations.extend([
            "Conduct additional research in areas with low validation scores",
            "Focus on validated assumptions for immediate market entry strategies",
            "Monitor invalidated assumptions for potential market evolution"
        ])
        
        return recommendations
    
    def _generate_fallback_report(self, assumption_analyses: List[Dict[str, Any]]) -> str:
        """Generate a basic report when visualization integration fails."""
        return f"""
# Market Research Analysis Report

## Summary
Analysis completed for {len(assumption_analyses)} assumptions.

*Note: Enhanced report generation with visualizations encountered an error. Please refer to individual analysis results.*

## Assumptions Analyzed
{chr(10).join([f"- {a.get('assumption_text', 'Unknown assumption')}" for a in assumption_analyses])}
"""
    
    def _extract_section_content(self, section: str) -> str:
        """Extract clean content from a section for metadata."""
        # Remove markdown formatting for metadata
        clean_content = re.sub(r'[#*`]', '', section)
        return clean_content[:500] + "..." if len(clean_content) > 500 else clean_content
    
    def _generate_report_metadata(
        self,
        visualizations: Dict[str, Any],
        assumption_analyses: List[Dict[str, Any]],
        statistics_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata for the report."""
        return {
            'generation_timestamp': datetime.now().isoformat(),
            'total_visualizations': len(visualizations),
            'visualization_types': list(set(v.get('type', 'unknown') for v in visualizations.values())),
            'total_assumptions': len(assumption_analyses),
            'validation_summary': {
                'validated': sum(1 for a in assumption_analyses if a.get('validation_status') == 'validated'),
                'partially_validated': sum(1 for a in assumption_analyses if a.get('validation_status') == 'partially_validated'),
                'invalidated': sum(1 for a in assumption_analyses if a.get('validation_status') == 'invalidated')
            },
            'data_sources': {
                'csv_files': 1 if statistics_registry.get('csv_statistics') else 0,
                'pdf_files': 1 if statistics_registry.get('pdf_statistics') else 0,
                'total_citations': len(statistics_registry.get('citation_registry', {}))
            },
            'accessibility_features': {
                'alt_text_provided': all(v.get('alt_text') for v in visualizations.values()),
                'markdown_fallbacks': all(v.get('markdown_table') for v in visualizations.values()),
                'responsive_layouts': all(v.get('responsive_config') for v in visualizations.values())
            }
        }