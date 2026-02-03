"""
Report formatting utilities for market research analysis.

Provides advanced formatting capabilities for markdown reports, including
PV comparison formatting, statistical data presentation, and output generation.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportFormatter:
    """Advanced report formatting utilities for market research analysis."""
    
    def __init__(self):
        """Initialize the report formatter."""
        self.formatting_config = {
            "max_evidence_length": 200,
            "max_quote_length": 150,
            "decimal_places": 2,
            "date_format": "%Y-%m-%d %H:%M:%S",
            "section_separator": "---"
        }
    
    def format_markdown_report(
        self,
        report_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Apply advanced markdown formatting to report content.
        
        Args:
            report_content: Raw markdown report content
            metadata: Optional metadata for formatting
            
        Returns:
            Formatted markdown report
        """
        try:
            # Clean up whitespace and line breaks
            formatted_content = self._clean_whitespace(report_content)
            
            # Apply consistent section formatting
            formatted_content = self._format_sections(formatted_content)
            
            # Format tables and statistical data
            formatted_content = self._format_tables(formatted_content)
            
            # Apply consistent bullet point formatting
            formatted_content = self._format_bullet_points(formatted_content)
            
            # Add table of contents if requested
            if metadata and metadata.get("include_toc", False):
                formatted_content = self._add_table_of_contents(formatted_content)
            
            return formatted_content
            
        except Exception as e:
            logger.error(f"Error formatting markdown report: {str(e)}")
            return report_content  # Return original content on error
    
    def format_pv_comparison_section(
        self,
        pv_comparisons: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]]
    ) -> str:
        """
        Create detailed PV comparison section with advanced formatting.
        
        Args:
            pv_comparisons: List of PV comparison results
            analysis_results: List of analysis results for context
            
        Returns:
            Formatted PV comparison section
        """
        if not pv_comparisons:
            return "No PV report data available for comparison."
        
        section_lines = [
            "# Problem Validation Report Comparison",
            "",
            "This section provides a detailed comparison between the market research analysis findings and existing Problem Validation (PV) report data.",
            ""
        ]
        
        # Create summary table
        summary_table = self._create_pv_summary_table(pv_comparisons)
        section_lines.extend([
            "## Consistency Summary",
            "",
            summary_table,
            ""
        ])
        
        # Add detailed comparisons
        section_lines.extend([
            "## Detailed Comparison Results",
            ""
        ])
        
        for i, comparison in enumerate(pv_comparisons, 1):
            detailed_comparison = self._format_detailed_pv_comparison(comparison, i)
            section_lines.append(detailed_comparison)
        
        # Add insights and recommendations
        insights = self._generate_pv_insights(pv_comparisons, analysis_results)
        section_lines.extend([
            "## Key Insights from PV Comparison",
            "",
            insights
        ])
        
        return "\n".join(section_lines)
    
    def format_statistical_data(
        self,
        statistical_data: Dict[str, Any],
        title: str = "Statistical Analysis"
    ) -> str:
        """
        Format statistical data into readable markdown tables and charts.
        
        Args:
            statistical_data: Dictionary containing statistical information
            title: Title for the statistical section
            
        Returns:
            Formatted statistical data section
        """
        if not statistical_data:
            return f"## {title}\n\nNo statistical data available."
        
        section_lines = [
            f"## {title}",
            ""
        ]
        
        # Format numerical statistics
        if "metrics" in statistical_data:
            metrics_table = self._create_metrics_table(statistical_data["metrics"])
            section_lines.extend([
                "### Key Metrics",
                "",
                metrics_table,
                ""
            ])
        
        # Format distributions
        if "distributions" in statistical_data:
            distributions = self._format_distributions(statistical_data["distributions"])
            section_lines.extend([
                "### Data Distributions",
                "",
                distributions,
                ""
            ])
        
        # Format correlations
        if "correlations" in statistical_data:
            correlations = self._format_correlations(statistical_data["correlations"])
            section_lines.extend([
                "### Correlations",
                "",
                correlations,
                ""
            ])
        
        return "\n".join(section_lines)
    
    def generate_executive_summary_with_charts(
        self,
        analysis_results: List[Dict[str, Any]],
        include_charts: bool = True
    ) -> str:
        """
        Generate enhanced executive summary with visual elements.
        
        Args:
            analysis_results: List of analysis results
            include_charts: Whether to include ASCII charts
            
        Returns:
            Enhanced executive summary
        """
        if not analysis_results:
            return "No analysis results available for executive summary."
        
        # Calculate summary statistics
        stats = self._calculate_summary_statistics(analysis_results)
        
        summary_lines = [
            "# Executive Summary",
            "",
            f"**Analysis Date:** {datetime.now().strftime(self.formatting_config['date_format'])}",
            f"**Total Assumptions Analyzed:** {stats['total_assumptions']}",
            f"**Overall Validation Rate:** {stats['validation_rate']:.1%}",
            ""
        ]
        
        # Add validation breakdown
        validation_breakdown = self._create_validation_breakdown_table(stats)
        summary_lines.extend([
            "## Validation Results Overview",
            "",
            validation_breakdown,
            ""
        ])
        
        # Add confidence distribution if charts are enabled
        if include_charts and stats['confidence_scores']:
            confidence_chart = self._create_confidence_distribution_chart(stats['confidence_scores'])
            summary_lines.extend([
                "## Confidence Score Distribution",
                "",
                confidence_chart,
                ""
            ])
        
        # Add key insights
        key_insights = self._extract_executive_insights(analysis_results, stats)
        summary_lines.extend([
            "## Key Insights",
            "",
            key_insights,
            ""
        ])
        
        return "\n".join(summary_lines)
    
    def export_report_formats(
        self,
        report_content: str,
        output_dir: str,
        filename_base: str,
        formats: List[str] = ["markdown", "json"]
    ) -> Dict[str, str]:
        """
        Export report in multiple formats.
        
        Args:
            report_content: The report content to export
            output_dir: Directory to save files
            filename_base: Base filename without extension
            formats: List of formats to export ("markdown", "json", "html")
            
        Returns:
            Dictionary mapping format to file path
        """
        output_paths = {}
        
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for format_type in formats:
                if format_type == "markdown":
                    file_path = output_path / f"{filename_base}.md"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    output_paths["markdown"] = str(file_path)
                
                elif format_type == "json":
                    # Convert markdown to structured JSON
                    json_data = self._markdown_to_json(report_content)
                    file_path = output_path / f"{filename_base}.json"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    output_paths["json"] = str(file_path)
                
                elif format_type == "html":
                    # Convert markdown to HTML (basic conversion)
                    html_content = self._markdown_to_html(report_content)
                    file_path = output_path / f"{filename_base}.html"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    output_paths["html"] = str(file_path)
            
            logger.info(f"Report exported in {len(output_paths)} formats to {output_dir}")
            return output_paths
            
        except Exception as e:
            logger.error(f"Error exporting report formats: {str(e)}")
            return {}
    
    def _clean_whitespace(self, content: str) -> str:
        """Clean up whitespace and line breaks in content."""
        # Remove excessive blank lines
        lines = content.split('\n')
        cleaned_lines = []
        blank_count = 0
        
        for line in lines:
            if line.strip() == '':
                blank_count += 1
                if blank_count <= 2:  # Allow max 2 consecutive blank lines
                    cleaned_lines.append(line)
            else:
                blank_count = 0
                cleaned_lines.append(line.rstrip())  # Remove trailing whitespace
        
        return '\n'.join(cleaned_lines)
    
    def _format_sections(self, content: str) -> str:
        """Apply consistent section formatting."""
        # Ensure proper spacing around section separators
        content = content.replace('\n---\n', f'\n\n{self.formatting_config["section_separator"]}\n\n')
        
        # Ensure proper spacing around headers
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                # Add blank line before header if not already present
                if i > 0 and lines[i-1].strip() != '' and not lines[i-1].startswith('#'):
                    formatted_lines.append('')
                formatted_lines.append(line)
                # Add blank line after header if not already present
                if i < len(lines) - 1 and lines[i+1].strip() != '':
                    formatted_lines.append('')
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _format_tables(self, content: str) -> str:
        """Format tables for better readability."""
        # This is a placeholder for table formatting logic
        # In a full implementation, you would parse and reformat markdown tables
        return content
    
    def _format_bullet_points(self, content: str) -> str:
        """Apply consistent bullet point formatting."""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip().startswith('- '):
                # Ensure consistent spacing
                formatted_line = '- ' + line.strip()[2:].strip()
                formatted_lines.append(formatted_line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _add_table_of_contents(self, content: str) -> str:
        """Add table of contents to the report."""
        lines = content.split('\n')
        toc_lines = ['# Table of Contents', '']
        content_lines = []
        
        in_research_data_section = False
        in_assumptions_section = False
        assumption_counter = 0
        
        for line in lines:
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('# ').strip()
                
                # Track which section we're in
                if level == 1 and 'Research Data Summary' in title:
                    in_research_data_section = True
                    in_assumptions_section = False
                elif level == 1 and 'Assumptions Analysis' in title:
                    in_research_data_section = False
                    in_assumptions_section = True
                    assumption_counter = 0
                elif level == 1:
                    in_research_data_section = False
                    in_assumptions_section = False
                
                # Skip level 2 headers under Research Data Summary (individual files)
                if in_research_data_section and level == 2:
                    content_lines.append(line)
                    continue
                
                # Replace assumption validation status with numbered format
                if in_assumptions_section and level == 2:
                    assumption_counter += 1
                    # Replace status emoji with "Assumption N"
                    title = f"Assumption {assumption_counter}"
                
                indent = '  ' * (level - 1)
                anchor = title.lower().replace(' ', '-').replace('&', '').replace(',', '').replace('✅', '').replace('⚠️', '').replace('❌', '').strip()
                toc_lines.append(f'{indent}- [{title}](#{anchor})')
            content_lines.append(line)
        
        toc_lines.extend(['', '---', ''])
        return '\n'.join(toc_lines + content_lines)
    
    def _create_pv_summary_table(self, pv_comparisons: List[Dict[str, Any]]) -> str:
        """Create summary table for PV comparisons."""
        consistent_count = len([c for c in pv_comparisons if c.get("consistency_status") == "consistent"])
        inconsistent_count = len([c for c in pv_comparisons if c.get("consistency_status") == "inconsistent"])
        partial_count = len([c for c in pv_comparisons if c.get("consistency_status") == "partial"])
        no_data_count = len([c for c in pv_comparisons if c.get("consistency_status") == "no_data"])
        unknown_count = len([c for c in pv_comparisons if c.get("consistency_status") == "unknown"])
        total_count = len(pv_comparisons)

        def _percent(count: int) -> float:
            return (count / total_count * 100) if total_count else 0.0

        table_lines = [
            "| Status | Count | Percentage |",
            "|--------|-------|------------|",
            f"| ✅ Consistent | {consistent_count} | {_percent(consistent_count):.1f}% |",
            f"| ⚠️ Inconsistent | {inconsistent_count} | {_percent(inconsistent_count):.1f}% |",
            f"| 🔄 Partial | {partial_count} | {_percent(partial_count):.1f}% |",
        ]

        if no_data_count:
            table_lines.append(f"| ℹ️ No PV Data | {no_data_count} | {_percent(no_data_count):.1f}% |")
        if unknown_count:
            table_lines.append(f"| ❓ Pending Analysis | {unknown_count} | {_percent(unknown_count):.1f}% |")

        table_lines.append(
            f"| **Total** | **{total_count}** | **100.0%** |"
        )

        return '\n'.join(table_lines)
    
    def _format_detailed_pv_comparison(self, comparison: Dict[str, Any], index: int) -> str:
        """Format detailed PV comparison for single assumption."""
        assumption_id = comparison.get("assumption_id", f"assumption-{index}")
        consistency_status = comparison.get("consistency_status", "unknown")
        status_label = comparison.get("status_label", consistency_status.replace("_", " ").title())
        details = comparison.get("comparison_details", "No details available")
        pv_finding = comparison.get("pv_finding", "No PV finding available")
        analysis_finding = comparison.get("analysis_finding", "No analysis finding available")
        score = comparison.get("overall_consistency_score")

        status_icons = {
            "consistent": "✅",
            "inconsistent": "⚠️",
            "partial": "🔄",
            "unknown": "❓",
            "no_data": "ℹ️"
        }

        status_icon = comparison.get("status_icon") or status_icons.get(consistency_status, "❓")

        comparison_lines = [
            f"### {status_icon} {assumption_id}",
            "",
            f"**Consistency Status:** {status_label}",
        ]

        if isinstance(score, (int, float)):
            comparison_lines.append(f"**Consistency Score:** {score:.2f}")
            comparison_lines.append("")
        else:
            comparison_lines.append("")

        comparison_lines.extend([
            "**PV Report Finding:**",
            f"> {pv_finding}",
            "",
            "**Market Research Analysis Finding:**",
            f"> {analysis_finding}",
            "",
            "**Comparison Details:**",
            details,
            ""
        ])

        return '\n'.join(comparison_lines)

    def _generate_pv_insights(
        self,
        pv_comparisons: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]]
    ) -> str:
        """Generate insights from PV comparison results."""
        consistent_count = len([c for c in pv_comparisons if c.get("consistency_status") == "consistent"])
        total_count = len(pv_comparisons)
        consistency_rate = consistent_count / total_count if total_count > 0 else 0
        
        insights_lines = []
        
        if consistency_rate >= 0.8:
            insights_lines.append("- **High Consistency:** Your market research analysis strongly aligns with previous PV findings, indicating robust validation methodology.")
        elif consistency_rate >= 0.6:
            insights_lines.append("- **Moderate Consistency:** Most findings align with PV data, with some areas requiring further investigation.")
        else:
            insights_lines.append("- **Low Consistency:** Significant discrepancies exist between PV and market research findings, suggesting need for methodology review.")
        
        # Add specific insights based on patterns
        inconsistent_assumptions = [c for c in pv_comparisons if c.get("consistency_status") == "inconsistent"]
        if inconsistent_assumptions:
            insights_lines.append(f"- **{len(inconsistent_assumptions)} assumptions** show inconsistencies that may indicate market evolution or methodology differences.")
        
        return '\n'.join(insights_lines)
    
    def _create_metrics_table(self, metrics: Dict[str, Union[int, float]]) -> str:
        """Create formatted table for metrics."""
        table_lines = [
            "| Metric | Value |",
            "|--------|-------|"
        ]
        
        for metric_name, value in metrics.items():
            formatted_name = metric_name.replace('_', ' ').title()
            if isinstance(value, float):
                formatted_value = f"{value:.{self.formatting_config['decimal_places']}f}"
            else:
                formatted_value = str(value)
            table_lines.append(f"| {formatted_name} | {formatted_value} |")
        
        return '\n'.join(table_lines)
    
    def _format_distributions(self, distributions: Dict[str, Any]) -> str:
        """Format distribution data."""
        dist_lines = []
        
        for dist_name, dist_data in distributions.items():
            dist_lines.append(f"**{dist_name.replace('_', ' ').title()}:**")
            if isinstance(dist_data, dict):
                for key, value in dist_data.items():
                    dist_lines.append(f"- {key}: {value}")
            else:
                dist_lines.append(f"- {dist_data}")
            dist_lines.append("")
        
        return '\n'.join(dist_lines)
    
    def _format_correlations(self, correlations: Dict[str, float]) -> str:
        """Format correlation data."""
        corr_lines = []
        
        for corr_name, corr_value in correlations.items():
            strength = "Strong" if abs(corr_value) > 0.7 else "Moderate" if abs(corr_value) > 0.4 else "Weak"
            direction = "Positive" if corr_value > 0 else "Negative"
            corr_lines.append(f"- **{corr_name}:** {corr_value:.3f} ({strength} {direction} correlation)")
        
        return '\n'.join(corr_lines)
    
    def _calculate_summary_statistics(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from analysis results."""
        total_assumptions = len(analysis_results)
        validated_count = len([a for a in analysis_results if a.get("validation_status") == "validated"])
        partially_validated_count = len([a for a in analysis_results if a.get("validation_status") == "partially_validated"])
        invalidated_count = len([a for a in analysis_results if a.get("validation_status") == "invalidated"])
        
        confidence_scores = [a.get("overall_confidence", 0.0) for a in analysis_results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        validation_rate = (validated_count + partially_validated_count) / total_assumptions if total_assumptions > 0 else 0
        
        return {
            "total_assumptions": total_assumptions,
            "validated_count": validated_count,
            "partially_validated_count": partially_validated_count,
            "invalidated_count": invalidated_count,
            "validation_rate": validation_rate,
            "average_confidence": avg_confidence,
            "confidence_scores": confidence_scores
        }
    
    def _create_validation_breakdown_table(self, stats: Dict[str, Any]) -> str:
        """Create validation breakdown table."""
        total = stats["total_assumptions"]
        
        table_lines = [
            "| Validation Status | Count | Percentage |",
            "|------------------|-------|------------|",
            f"| ✅ Validated | {stats['validated_count']} | {stats['validated_count']/total*100:.1f}% |",
            f"| ⚠️ Partially Validated | {stats['partially_validated_count']} | {stats['partially_validated_count']/total*100:.1f}% |",
            f"| ❌ Invalidated | {stats['invalidated_count']} | {stats['invalidated_count']/total*100:.1f}% |",
            f"| **Total** | **{total}** | **100.0%** |"
        ]
        
        return '\n'.join(table_lines)
    
    def _create_confidence_distribution_chart(self, confidence_scores: List[float]) -> str:
        """Create ASCII chart for confidence distribution."""
        if not confidence_scores:
            return "No confidence data available."
        
        # Create bins
        bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        bin_counts = [0] * (len(bins) - 1)
        
        for score in confidence_scores:
            for i in range(len(bins) - 1):
                if bins[i] <= score < bins[i + 1] or (i == len(bins) - 2 and score == 1.0):
                    bin_counts[i] += 1
                    break
        
        # Create ASCII chart
        max_count = max(bin_counts) if bin_counts else 1
        chart_lines = ["```"]
        
        for i, count in enumerate(bin_counts):
            bar_length = int((count / max_count) * 20) if max_count > 0 else 0
            bar = "█" * bar_length
            label = f"{bins[i]:.1f}-{bins[i+1]:.1f}"
            chart_lines.append(f"{label:>8} | {bar} ({count})")
        
        chart_lines.append("```")
        return '\n'.join(chart_lines)
    
    def _extract_executive_insights(
        self,
        analysis_results: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> str:
        """Extract key insights for executive summary."""
        insights = []
        
        # Validation rate insight
        validation_rate = stats["validation_rate"]
        if validation_rate >= 0.8:
            insights.append("- **Strong market validation** with most assumptions supported by research data")
        elif validation_rate >= 0.6:
            insights.append("- **Moderate market validation** with majority of assumptions having evidence support")
        else:
            insights.append("- **Limited market validation** indicating need for assumption refinement")
        
        # Confidence insight
        avg_confidence = stats["average_confidence"]
        if avg_confidence >= 0.7:
            insights.append("- **High confidence** in analysis results based on strong evidence")
        elif avg_confidence >= 0.5:
            insights.append("- **Moderate confidence** in analysis results with room for additional validation")
        else:
            insights.append("- **Low confidence** in results suggesting need for more comprehensive research")
        
        # Top validated assumptions
        validated_assumptions = [a for a in analysis_results if a.get("validation_status") == "validated"]
        if validated_assumptions:
            top_validated = sorted(validated_assumptions, key=lambda x: x.get("overall_confidence", 0), reverse=True)[:2]
            insights.append(f"- **{len(validated_assumptions)} validated assumptions** provide strong foundation for market entry")
        
        return '\n'.join(insights)
    
    def _markdown_to_json(self, markdown_content: str) -> Dict[str, Any]:
        """Convert markdown report to structured JSON."""
        # This is a simplified conversion - in practice you'd use a proper markdown parser
        return {
            "content": markdown_content,
            "format": "markdown",
            "generated_at": datetime.now().isoformat(),
            "sections": self._extract_sections_from_markdown(markdown_content)
        }
    
    def _extract_sections_from_markdown(self, content: str) -> List[Dict[str, str]]:
        """Extract sections from markdown content."""
        sections = []
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('#'):
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": '\n'.join(current_content).strip()
                    })
                current_section = line.lstrip('# ').strip()
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip()
            })
        
        return sections
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to basic HTML."""
        # This is a very basic conversion - in practice you'd use a proper markdown to HTML converter
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Market Research Analysis Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            "h1, h2, h3 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            "</style>",
            "</head>",
            "<body>"
        ]
        
        # Basic markdown to HTML conversion
        for line in markdown_content.split('\n'):
            if line.startswith('# '):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith('## '):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith('### '):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith('- '):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.strip() == '':
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p>{line}</p>")
        
        html_lines.extend(["</body>", "</html>"])
        return '\n'.join(html_lines)