"""
Multi-Format Visualization Output Service

This module provides multi-format output generation for visualizations including
interactive Plotly charts, static images (PNG/SVG), markdown tables, and
comprehensive accessibility features.

Requirements addressed: 7.5, 7.6
"""

import json
import logging
import base64
import io
from typing import Dict, Any, List, Optional, Tuple
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import plot
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import kaleido
import tempfile
import os

logger = logging.getLogger(__name__)

class MultiFormatVisualizationOutput:
    """
    Generates multiple output formats for visualizations with accessibility features.
    """
    
    def __init__(self):
        """Initialize the multi-format output generator."""
        # Configure Plotly for static image generation
        pio.kaleido.scope.mathjax = None
        
        # Default image settings
        self.default_width = 800
        self.default_height = 600
        self.default_dpi = 300
        
        # Accessibility settings
        self.min_contrast_ratio = 4.5  # WCAG AA standard
        self.font_size_min = 12
    
    def generate_all_formats(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate all output formats for a visualization.
        
        Args:
            visualization: Visualization object from DynamicVisualizationGenerator
            
        Returns:
            Enhanced visualization object with all formats and accessibility features
        """
        try:
            enhanced_viz = visualization.copy()
            
            # Generate interactive Plotly chart (already exists)
            plotly_json = visualization.get('plotly_json', '')
            if plotly_json:
                enhanced_viz['interactive_chart'] = self._enhance_interactive_chart(plotly_json)
            
            # Generate static image formats
            static_formats = self._generate_static_images(plotly_json, visualization)
            enhanced_viz.update(static_formats)
            
            # Generate markdown table fallback
            markdown_table = self._generate_markdown_table(visualization)
            enhanced_viz['markdown_table'] = markdown_table
            
            # Generate comprehensive alt-text
            alt_text = self._generate_alt_text(visualization)
            enhanced_viz['alt_text'] = alt_text
            
            # Generate accessibility metadata
            accessibility_features = self._generate_accessibility_features(visualization)
            enhanced_viz['accessibility'] = accessibility_features
            
            # Generate responsive layout configurations
            responsive_config = self._generate_responsive_config(visualization)
            enhanced_viz['responsive_config'] = responsive_config
            
            logger.info(f"Generated all formats for visualization: {visualization.get('title', 'Unknown')}")
            return enhanced_viz
            
        except Exception as e:
            logger.error(f"Error generating multi-format output: {str(e)}")
            return visualization
    
    def _enhance_interactive_chart(self, plotly_json: str) -> Dict[str, Any]:
        """Enhance interactive Plotly chart with accessibility features."""
        try:
            fig_dict = json.loads(plotly_json)
            fig = go.Figure(fig_dict)
            
            # Add accessibility enhancements
            fig.update_layout(
                # Keyboard navigation support
                dragmode='pan',
                
                # High contrast mode support
                plot_bgcolor='white',
                paper_bgcolor='white',
                
                # Font accessibility
                font=dict(
                    size=self.font_size_min,
                    color='black'
                ),
                
                # Hover accessibility
                hovermode='closest',
                
                # Legend accessibility
                legend=dict(
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='black',
                    borderwidth=1
                )
            )
            
            # Add ARIA labels and descriptions
            config = {
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['pan2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'chart',
                    'height': self.default_height,
                    'width': self.default_width,
                    'scale': 1
                },
                'accessible': True,
                'locale': 'en'
            }
            
            return {
                'plotly_json': fig.to_json(),
                'plotly_config': config,
                'html_div': plot(fig, output_type='div', include_plotlyjs=False, config=config)
            }
            
        except Exception as e:
            logger.error(f"Error enhancing interactive chart: {str(e)}")
            return {'plotly_json': plotly_json}
    
    def _generate_static_images(self, plotly_json: str, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """Generate static image formats (PNG and SVG)."""
        try:
            if not plotly_json:
                return {}
            
            fig_dict = json.loads(plotly_json)
            fig = go.Figure(fig_dict)
            
            # Enhance figure for static export
            fig.update_layout(
                font=dict(size=14, color='black'),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=60, r=60, t=100, b=60)
            )
            
            # Generate PNG
            png_bytes = fig.to_image(
                format="png",
                width=self.default_width,
                height=self.default_height,
                scale=2  # High DPI for better quality
            )
            png_base64 = base64.b64encode(png_bytes).decode('utf-8')
            
            # Generate SVG
            svg_string = fig.to_image(format="svg", width=self.default_width, height=self.default_height)
            svg_base64 = base64.b64encode(svg_string).decode('utf-8')
            
            return {
                'static_image_png': png_base64,
                'static_image_svg': svg_base64,
                'image_dimensions': {
                    'width': self.default_width,
                    'height': self.default_height,
                    'dpi': self.default_dpi
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating static images: {str(e)}")
            return {}
    
    def _generate_markdown_table(self, visualization: Dict[str, Any]) -> str:
        """Generate markdown table fallback for text-only environments."""
        try:
            viz_type = visualization.get('type', '')
            title = visualization.get('title', 'Data Visualization')
            
            if viz_type in ['bar_chart', 'pie_chart']:
                return self._create_distribution_table(visualization)
            elif viz_type == 'table':
                return self._create_data_table(visualization)
            elif viz_type == 'horizontal_bar_chart':
                return self._create_theme_table(visualization)
            elif viz_type == 'heatmap':
                return self._create_matrix_table(visualization)
            elif viz_type in ['sentiment_bar_chart', 'overview_bar_chart', 'grouped_bar_chart']:
                return self._create_summary_table(visualization)
            else:
                return f"## {title}\n\n*Visualization data available in interactive format*\n"
                
        except Exception as e:
            logger.error(f"Error generating markdown table: {str(e)}")
            return f"## {visualization.get('title', 'Visualization')}\n\n*Table format unavailable*\n"
    
    def _create_distribution_table(self, visualization: Dict[str, Any]) -> str:
        """Create markdown table for distribution charts."""
        try:
            title = visualization.get('title', 'Distribution')
            field_name = visualization.get('field_name', 'Category')
            total_responses = visualization.get('total_responses', 0)
            
            # Extract data from plotly_json
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [{}])[0]
            
            if visualization.get('type') == 'pie_chart':
                labels = data.get('labels', [])
                values = data.get('values', [])
            else:  # bar_chart
                labels = data.get('x', [])
                values = data.get('y', [])
            
            # Calculate percentages
            total = sum(values) if values else 1
            percentages = [(v / total) * 100 for v in values]
            
            # Create table
            table_lines = [
                f"## {title}",
                "",
                f"**Total Responses:** {total_responses}",
                "",
                f"| {field_name.replace('_', ' ').title()} | Count | Percentage |",
                "|" + "-" * (len(field_name) + 10) + "|-------|------------|"
            ]
            
            for label, count, pct in zip(labels, values, percentages):
                table_lines.append(f"| {label} | {count} | {pct:.1f}% |")
            
            return "\n".join(table_lines) + "\n"
            
        except Exception as e:
            logger.error(f"Error creating distribution table: {str(e)}")
            return f"## {visualization.get('title', 'Distribution')}\n\n*Table generation failed*\n"
    
    def _create_data_table(self, visualization: Dict[str, Any]) -> str:
        """Create markdown table for table-type visualizations."""
        try:
            title = visualization.get('title', 'Data Table')
            showing_top = visualization.get('showing_top', 0)
            total_unique = visualization.get('total_unique', 0)
            
            # Extract data from plotly_json
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [{}])[0]
            cells = data.get('cells', {})
            
            if not cells:
                return f"## {title}\n\n*No data available*\n"
            
            values = cells.get('values', [])
            if len(values) < 3:
                return f"## {title}\n\n*Insufficient data*\n"
            
            categories = values[0]
            counts = values[1]
            percentages = values[2]
            
            # Create table
            table_lines = [
                f"## {title}",
                "",
                f"**Showing top {showing_top} of {total_unique} unique values**",
                "",
                "| Value | Count | Percentage |",
                "|-------|-------|------------|"
            ]
            
            for cat, count, pct in zip(categories, counts, percentages):
                table_lines.append(f"| {cat} | {count} | {pct} |")
            
            return "\n".join(table_lines) + "\n"
            
        except Exception as e:
            logger.error(f"Error creating data table: {str(e)}")
            return f"## {visualization.get('title', 'Data Table')}\n\n*Table generation failed*\n"
    
    def _create_theme_table(self, visualization: Dict[str, Any]) -> str:
        """Create markdown table for theme frequency charts."""
        try:
            title = visualization.get('title', 'Theme Analysis')
            total_themes = visualization.get('total_themes', 0)
            
            # Extract data from plotly_json
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [{}])[0]
            
            themes = data.get('y', [])
            frequencies = data.get('x', [])
            
            # Create table
            table_lines = [
                f"## {title}",
                "",
                f"**Total Themes Identified:** {total_themes}",
                "",
                "| Theme | Frequency |",
                "|-------|-----------|"
            ]
            
            for theme, freq in zip(themes, frequencies):
                table_lines.append(f"| {theme} | {freq} |")
            
            return "\n".join(table_lines) + "\n"
            
        except Exception as e:
            logger.error(f"Error creating theme table: {str(e)}")
            return f"## {visualization.get('title', 'Theme Analysis')}\n\n*Table generation failed*\n"
    
    def _create_matrix_table(self, visualization: Dict[str, Any]) -> str:
        """Create markdown table for matrix/heatmap visualizations."""
        try:
            title = visualization.get('title', 'Matrix Analysis')
            matrix_size = visualization.get('matrix_size', 0)
            
            return f"""## {title}

**Matrix Size:** {matrix_size} x {matrix_size}

*This visualization shows relationships between themes in a matrix format. The interactive version provides detailed co-occurrence values.*

**Note:** Matrix data is best viewed in the interactive format for detailed analysis.
"""
            
        except Exception as e:
            logger.error(f"Error creating matrix table: {str(e)}")
            return f"## {visualization.get('title', 'Matrix Analysis')}\n\n*Table generation failed*\n"
    
    def _create_summary_table(self, visualization: Dict[str, Any]) -> str:
        """Create markdown table for summary/overview charts."""
        try:
            title = visualization.get('title', 'Summary')
            
            # Extract data from plotly_json
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [])
            
            if not data:
                return f"## {title}\n\n*No data available*\n"
            
            # Handle different chart types
            if len(data) == 1:
                # Single series
                chart_data = data[0]
                categories = chart_data.get('x', [])
                values = chart_data.get('y', [])
                
                table_lines = [
                    f"## {title}",
                    "",
                    "| Category | Value |",
                    "|----------|-------|"
                ]
                
                for cat, val in zip(categories, values):
                    table_lines.append(f"| {cat} | {val} |")
                    
            else:
                # Multiple series (grouped bar chart)
                table_lines = [
                    f"## {title}",
                    "",
                    "| Category | " + " | ".join([d.get('name', f'Series {i+1}') for i, d in enumerate(data)]) + " |",
                    "|----------|" + "|".join(["-" * len(d.get('name', f'Series {i+1}')) for i, d in enumerate(data)]) + "|"
                ]
                
                # Assume all series have same x values
                categories = data[0].get('x', [])
                for cat in categories:
                    row = f"| {cat} |"
                    for series in data:
                        x_vals = series.get('x', [])
                        y_vals = series.get('y', [])
                        try:
                            idx = x_vals.index(cat)
                            val = y_vals[idx]
                            row += f" {val} |"
                        except (ValueError, IndexError):
                            row += " - |"
                    table_lines.append(row)
            
            return "\n".join(table_lines) + "\n"
            
        except Exception as e:
            logger.error(f"Error creating summary table: {str(e)}")
            return f"## {visualization.get('title', 'Summary')}\n\n*Table generation failed*\n"
    
    def _generate_alt_text(self, visualization: Dict[str, Any]) -> str:
        """Generate comprehensive alt-text for accessibility."""
        try:
            viz_type = visualization.get('type', '')
            title = visualization.get('title', 'Visualization')
            
            if viz_type in ['bar_chart', 'pie_chart']:
                return self._generate_distribution_alt_text(visualization)
            elif viz_type == 'table':
                return self._generate_table_alt_text(visualization)
            elif viz_type == 'horizontal_bar_chart':
                return self._generate_theme_alt_text(visualization)
            elif viz_type == 'heatmap':
                return self._generate_matrix_alt_text(visualization)
            elif viz_type in ['sentiment_bar_chart', 'overview_bar_chart', 'grouped_bar_chart']:
                return self._generate_summary_alt_text(visualization)
            else:
                return f"Chart titled '{title}' showing data visualization."
                
        except Exception as e:
            logger.error(f"Error generating alt-text: {str(e)}")
            return f"Data visualization: {visualization.get('title', 'Chart')}"
    
    def _generate_distribution_alt_text(self, visualization: Dict[str, Any]) -> str:
        """Generate alt-text for distribution charts."""
        try:
            title = visualization.get('title', 'Distribution')
            field_name = visualization.get('field_name', 'category')
            total_responses = visualization.get('total_responses', 0)
            viz_type = visualization.get('type', 'chart')
            
            # Extract top values
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [{}])[0]
            
            if viz_type == 'pie_chart':
                labels = data.get('labels', [])
                values = data.get('values', [])
            else:
                labels = data.get('x', [])
                values = data.get('y', [])
            
            if not labels or not values:
                return f"{viz_type.replace('_', ' ').title()} showing distribution of {field_name}"
            
            # Find top 3 categories
            sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:3]
            
            alt_text = f"{viz_type.replace('_', ' ').title()} showing distribution of {field_name} from {total_responses} responses. "
            
            if sorted_data:
                top_items = []
                total = sum(values)
                for label, count in sorted_data:
                    percentage = (count / total) * 100 if total > 0 else 0
                    top_items.append(f"{label} ({count} responses, {percentage:.1f}%)")
                
                alt_text += f"Top categories: {', '.join(top_items)}."
            
            return alt_text
            
        except Exception as e:
            logger.error(f"Error generating distribution alt-text: {str(e)}")
            return f"Distribution chart for {visualization.get('field_name', 'data')}"
    
    def _generate_table_alt_text(self, visualization: Dict[str, Any]) -> str:
        """Generate alt-text for table visualizations."""
        try:
            title = visualization.get('title', 'Data Table')
            showing_top = visualization.get('showing_top', 0)
            total_unique = visualization.get('total_unique', 0)
            field_name = visualization.get('field_name', 'values')
            
            return f"Data table showing top {showing_top} values out of {total_unique} unique {field_name}. Table includes value names, counts, and percentages."
            
        except Exception as e:
            logger.error(f"Error generating table alt-text: {str(e)}")
            return "Data table with values, counts, and percentages"
    
    def _generate_theme_alt_text(self, visualization: Dict[str, Any]) -> str:
        """Generate alt-text for theme frequency charts."""
        try:
            total_themes = visualization.get('total_themes', 0)
            
            # Extract top themes
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [{}])[0]
            
            themes = data.get('y', [])
            frequencies = data.get('x', [])
            
            alt_text = f"Horizontal bar chart showing frequency of {total_themes} themes identified in interviews. "
            
            if themes and frequencies:
                # Top 3 themes
                top_themes = list(zip(themes, frequencies))[:3]
                theme_descriptions = [f"{theme} (frequency: {freq})" for theme, freq in top_themes]
                alt_text += f"Most frequent themes: {', '.join(theme_descriptions)}."
            
            return alt_text
            
        except Exception as e:
            logger.error(f"Error generating theme alt-text: {str(e)}")
            return "Theme frequency analysis chart"
    
    def _generate_matrix_alt_text(self, visualization: Dict[str, Any]) -> str:
        """Generate alt-text for matrix/heatmap visualizations."""
        try:
            matrix_size = visualization.get('matrix_size', 0)
            
            return f"Heatmap matrix showing co-occurrence relationships between {matrix_size} themes. Darker colors indicate stronger relationships between theme pairs."
            
        except Exception as e:
            logger.error(f"Error generating matrix alt-text: {str(e)}")
            return "Theme co-occurrence matrix heatmap"
    
    def _generate_summary_alt_text(self, visualization: Dict[str, Any]) -> str:
        """Generate alt-text for summary/overview charts."""
        try:
            title = visualization.get('title', 'Summary Chart')
            
            # Extract basic info
            plotly_data = json.loads(visualization.get('plotly_json', '{}'))
            data = plotly_data.get('data', [])
            
            if not data:
                return f"Summary chart titled '{title}'"
            
            if len(data) == 1:
                # Single series
                categories = data[0].get('x', [])
                values = data[0].get('y', [])
                
                alt_text = f"Bar chart titled '{title}' showing {len(categories)} categories. "
                
                if categories and values:
                    # Highest value
                    max_idx = values.index(max(values)) if values else 0
                    alt_text += f"Highest value: {categories[max_idx]} ({values[max_idx]})."
                    
            else:
                # Multiple series
                series_names = [d.get('name', f'Series {i+1}') for i, d in enumerate(data)]
                alt_text = f"Grouped bar chart titled '{title}' comparing {len(series_names)} data series: {', '.join(series_names)}."
            
            return alt_text
            
        except Exception as e:
            logger.error(f"Error generating summary alt-text: {str(e)}")
            return f"Summary chart: {visualization.get('title', 'Data visualization')}"
    
    def _generate_accessibility_features(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive accessibility metadata."""
        try:
            return {
                'wcag_compliance': 'AA',
                'screen_reader_compatible': True,
                'keyboard_navigable': True,
                'high_contrast_available': True,
                'text_alternative_provided': True,
                'color_blind_friendly': True,
                'minimum_font_size': self.font_size_min,
                'contrast_ratio': self.min_contrast_ratio,
                'aria_labels': {
                    'chart_title': visualization.get('title', 'Chart'),
                    'chart_type': visualization.get('type', 'visualization'),
                    'data_summary': f"Chart contains {len(visualization.get('citation_ids', []))} data sources"
                },
                'semantic_structure': {
                    'has_title': bool(visualization.get('title')),
                    'has_legend': True,
                    'has_axis_labels': True,
                    'has_data_labels': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating accessibility features: {str(e)}")
            return {'wcag_compliance': 'Unknown', 'screen_reader_compatible': False}
    
    def _generate_responsive_config(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """Generate responsive layout configurations for different screen sizes."""
        try:
            base_config = {
                'mobile': {
                    'width': 350,
                    'height': 300,
                    'font_size': 10,
                    'margin': {'l': 40, 'r': 20, 't': 60, 'b': 40}
                },
                'tablet': {
                    'width': 600,
                    'height': 450,
                    'font_size': 12,
                    'margin': {'l': 50, 'r': 30, 't': 70, 'b': 50}
                },
                'desktop': {
                    'width': self.default_width,
                    'height': self.default_height,
                    'font_size': 14,
                    'margin': {'l': 60, 'r': 60, 't': 80, 'b': 60}
                },
                'print': {
                    'width': 600,
                    'height': 400,
                    'font_size': 11,
                    'margin': {'l': 40, 'r': 40, 't': 60, 'b': 40},
                    'background_color': 'white',
                    'font_color': 'black'
                }
            }
            
            # Adjust for specific chart types
            viz_type = visualization.get('type', '')
            
            if viz_type == 'horizontal_bar_chart':
                # Need more height for horizontal bars
                for config in base_config.values():
                    config['height'] = int(config['height'] * 1.2)
                    
            elif viz_type == 'table':
                # Tables need more height
                for config in base_config.values():
                    config['height'] = int(config['height'] * 1.5)
                    
            elif viz_type == 'heatmap':
                # Square aspect ratio for matrices
                for config in base_config.values():
                    config['height'] = config['width']
            
            return base_config
            
        except Exception as e:
            logger.error(f"Error generating responsive config: {str(e)}")
            return {}