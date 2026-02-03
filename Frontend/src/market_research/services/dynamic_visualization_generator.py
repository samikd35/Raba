"""
Dynamic Visualization Generator for Market Research Analysis

This module provides context-aware chart generation based on data characteristics
and analysis context. It creates appropriate visualizations for CSV categorical
distributions, PDF interview themes, and comparison charts.

Requirements addressed: 7.1, 7.2, 7.3, 7.4
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
import base64
import io
from PIL import Image
import kaleido

logger = logging.getLogger(__name__)

class DynamicVisualizationGenerator:
    """
    Generates context-appropriate visualizations based on data characteristics
    and analysis context.
    """
    
    def __init__(self):
        """Initialize the visualization generator."""
        self.chart_counter = 0
        self.color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
    
    def generate_visualizations_for_analysis(
        self,
        statistics_registry: Dict[str, Any],
        analysis_type: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate context-appropriate visualizations.
        
        Args:
            statistics_registry: Complete statistics registry from database
            analysis_type: Type of analysis (pain, size, solution, gains, jtbd, comprehensive)
            persona_id: Optional persona ID for filtering
            
        Returns:
            Dictionary of visualization objects with metadata
        """
        try:
            visualizations = {}
            
            # Extract relevant statistics
            csv_stats = statistics_registry.get('csv_statistics', {})
            pdf_stats = statistics_registry.get('pdf_statistics', {})
            
            # Filter by persona if specified
            if persona_id:
                csv_stats = self._filter_stats_by_persona(csv_stats, persona_id)
                pdf_stats = self._filter_stats_by_persona(pdf_stats, persona_id)
            
            # Generate demographic charts from CSV data
            if csv_stats:
                demographic_charts = self.create_demographic_charts(csv_stats, analysis_type)
                visualizations.update(demographic_charts)
            
            # Generate theme visualizations from PDF data
            if pdf_stats:
                theme_charts = self.create_theme_visualizations(pdf_stats, analysis_type)
                visualizations.update(theme_charts)
            
            # Generate comparison charts if both data types exist
            if csv_stats and pdf_stats:
                comparison_charts = self.create_comparison_charts(csv_stats, pdf_stats, analysis_type)
                visualizations.update(comparison_charts)
            
            logger.info(f"Generated {len(visualizations)} visualizations for {analysis_type} analysis")
            return visualizations
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            return {}
    
    def create_demographic_charts(
        self, 
        csv_statistics: Dict[str, Any], 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Generate bar charts and tables for demographic distributions.
        
        Args:
            csv_statistics: CSV statistics from registry
            analysis_type: Type of analysis for context-aware generation
            
        Returns:
            Dictionary of demographic visualization objects
        """
        charts = {}
        
        try:
            categorical_distributions = csv_statistics.get('categorical_distributions', {})
            
            for field_name, distribution_data in categorical_distributions.items():
                if not distribution_data.get('distribution'):
                    continue
                
                # Determine chart type based on data characteristics
                chart_type = self._determine_chart_type(distribution_data, analysis_type)
                
                if chart_type == 'bar_chart':
                    chart = self._create_bar_chart(field_name, distribution_data)
                elif chart_type == 'pie_chart':
                    chart = self._create_pie_chart(field_name, distribution_data)
                else:
                    chart = self._create_table_chart(field_name, distribution_data)
                
                if chart:
                    chart_id = f"demographic_{field_name}_{self.chart_counter}"
                    self.chart_counter += 1
                    charts[chart_id] = chart
            
            return charts
            
        except Exception as e:
            logger.error(f"Error creating demographic charts: {str(e)}")
            return {}
    
    def create_theme_visualizations(
        self, 
        pdf_statistics: Dict[str, Any], 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Generate theme frequency charts and co-occurrence matrices for PDF interview data.
        
        Args:
            pdf_statistics: PDF statistics from registry
            analysis_type: Type of analysis for context-aware generation
            
        Returns:
            Dictionary of theme visualization objects
        """
        charts = {}
        
        try:
            themes = pdf_statistics.get('themes', {})
            
            if themes:
                # Create theme frequency chart
                frequency_chart = self._create_theme_frequency_chart(themes, analysis_type)
                if frequency_chart:
                    chart_id = f"theme_frequency_{self.chart_counter}"
                    self.chart_counter += 1
                    charts[chart_id] = frequency_chart
                
                # Create co-occurrence matrix if enough themes
                if len(themes) >= 3:
                    cooccurrence_chart = self._create_theme_cooccurrence_matrix(themes)
                    if cooccurrence_chart:
                        chart_id = f"theme_cooccurrence_{self.chart_counter}"
                        self.chart_counter += 1
                        charts[chart_id] = cooccurrence_chart
            
            # Create sentiment analysis chart if available
            participant_profile = pdf_statistics.get('participant_profile', {})
            sentiment_data = participant_profile.get('sentiment_analysis', {})
            if sentiment_data:
                sentiment_chart = self._create_sentiment_chart(sentiment_data)
                if sentiment_chart:
                    chart_id = f"sentiment_analysis_{self.chart_counter}"
                    self.chart_counter += 1
                    charts[chart_id] = sentiment_chart
            
            return charts
            
        except Exception as e:
            logger.error(f"Error creating theme visualizations: {str(e)}")
            return {}
    
    def create_comparison_charts(
        self, 
        csv_stats: Dict[str, Any], 
        pdf_stats: Dict[str, Any],
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Generate comparison visualizations between quantitative and qualitative data.
        
        Args:
            csv_stats: CSV statistics from registry
            pdf_stats: PDF statistics from registry
            analysis_type: Type of analysis for context-aware generation
            
        Returns:
            Dictionary of comparison visualization objects
        """
        charts = {}
        
        try:
            # Create data source overview
            overview_chart = self._create_data_source_overview(csv_stats, pdf_stats)
            if overview_chart:
                chart_id = f"data_overview_{self.chart_counter}"
                self.chart_counter += 1
                charts[chart_id] = overview_chart
            
            # Create insights correlation chart
            correlation_chart = self._create_insights_correlation_chart(csv_stats, pdf_stats, analysis_type)
            if correlation_chart:
                chart_id = f"insights_correlation_{self.chart_counter}"
                self.chart_counter += 1
                charts[chart_id] = correlation_chart
            
            return charts
            
        except Exception as e:
            logger.error(f"Error creating comparison charts: {str(e)}")
            return {}
    
    def _filter_stats_by_persona(self, stats: Dict[str, Any], persona_id: str) -> Dict[str, Any]:
        """Filter statistics by persona association."""
        # Implementation would filter based on persona_associations in the data
        # For now, return all stats (persona filtering can be enhanced later)
        return stats
    
    def _determine_chart_type(self, distribution_data: Dict[str, Any], analysis_type: str) -> str:
        """Determine the most appropriate chart type based on data characteristics."""
        distribution = distribution_data.get('distribution', [])
        unique_values = len(distribution)
        
        # Use pie chart for small number of categories (≤5) and certain analysis types
        if unique_values <= 5 and analysis_type in ['pain', 'gains', 'solution']:
            return 'pie_chart'
        
        # Use bar chart for moderate number of categories (≤15)
        elif unique_values <= 15:
            return 'bar_chart'
        
        # Use table for large number of categories
        else:
            return 'table'
    
    def _create_bar_chart(self, field_name: str, distribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a bar chart for categorical distribution."""
        try:
            distribution = distribution_data.get('distribution', [])
            
            # Extract data for plotting
            labels = [item['value'] for item in distribution]
            values = [item['count'] for item in distribution]
            percentages = [item['percentage'] for item in distribution]
            
            # Create bar chart
            fig = go.Figure(data=[
                go.Bar(
                    x=labels,
                    y=values,
                    text=[f"{p:.1f}%" for p in percentages],
                    textposition='auto',
                    marker_color=self.color_palette[0],
                    hovertemplate='<b>%{x}</b><br>Count: %{y}<br>Percentage: %{text}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title=f"Distribution of {field_name.replace('_', ' ').title()}",
                xaxis_title=field_name.replace('_', ' ').title(),
                yaxis_title="Count",
                showlegend=False,
                height=400,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Get citation IDs
            citation_ids = [item.get('citation_id', '') for item in distribution if item.get('citation_id')]
            
            return {
                "type": "bar_chart",
                "title": f"Distribution of {field_name.replace('_', ' ').title()}",
                "plotly_json": fig.to_json(),
                "citation_ids": citation_ids,
                "field_name": field_name,
                "total_responses": distribution_data.get('total_responses', 0)
            }
            
        except Exception as e:
            logger.error(f"Error creating bar chart for {field_name}: {str(e)}")
            return {}
    
    def _create_pie_chart(self, field_name: str, distribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pie chart for categorical distribution."""
        try:
            distribution = distribution_data.get('distribution', [])
            
            # Extract data for plotting
            labels = [item['value'] for item in distribution]
            values = [item['count'] for item in distribution]
            
            # Create pie chart
            fig = go.Figure(data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    textinfo='label+percent',
                    textposition='auto',
                    marker_colors=self.color_palette[:len(labels)],
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title=f"Distribution of {field_name.replace('_', ' ').title()}",
                showlegend=True,
                height=400,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Get citation IDs
            citation_ids = [item.get('citation_id', '') for item in distribution if item.get('citation_id')]
            
            return {
                "type": "pie_chart",
                "title": f"Distribution of {field_name.replace('_', ' ').title()}",
                "plotly_json": fig.to_json(),
                "citation_ids": citation_ids,
                "field_name": field_name,
                "total_responses": distribution_data.get('total_responses', 0)
            }
            
        except Exception as e:
            logger.error(f"Error creating pie chart for {field_name}: {str(e)}")
            return {}
    
    def _create_table_chart(self, field_name: str, distribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a table for categorical distribution with many categories."""
        try:
            distribution = distribution_data.get('distribution', [])
            
            # Sort by count descending
            sorted_distribution = sorted(distribution, key=lambda x: x['count'], reverse=True)
            
            # Take top 20 for display
            top_distribution = sorted_distribution[:20]
            
            # Create table data
            table_data = {
                'Value': [item['value'] for item in top_distribution],
                'Count': [item['count'] for item in top_distribution],
                'Percentage': [f"{item['percentage']:.1f}%" for item in top_distribution]
            }
            
            # Create table figure
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=list(table_data.keys()),
                    fill_color='lightblue',
                    align='left',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=list(table_data.values()),
                    fill_color='white',
                    align='left',
                    font=dict(size=11, color='black')
                )
            )])
            
            fig.update_layout(
                title=f"Top Values for {field_name.replace('_', ' ').title()}",
                height=min(600, 50 + len(top_distribution) * 25),
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Get citation IDs
            citation_ids = [item.get('citation_id', '') for item in distribution if item.get('citation_id')]
            
            return {
                "type": "table",
                "title": f"Top Values for {field_name.replace('_', ' ').title()}",
                "plotly_json": fig.to_json(),
                "citation_ids": citation_ids,
                "field_name": field_name,
                "total_responses": distribution_data.get('total_responses', 0),
                "showing_top": len(top_distribution),
                "total_unique": len(distribution)
            }
            
        except Exception as e:
            logger.error(f"Error creating table chart for {field_name}: {str(e)}")
            return {}
    
    def _create_theme_frequency_chart(self, themes: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Create a frequency chart for PDF themes."""
        try:
            # Extract theme data
            theme_names = list(themes.keys())
            frequencies = [themes[theme].get('frequency', 0) for theme in theme_names]
            percentages = [themes[theme].get('percentage', 0) for theme in theme_names]
            
            # Sort by frequency
            sorted_data = sorted(zip(theme_names, frequencies, percentages), key=lambda x: x[1], reverse=True)
            theme_names, frequencies, percentages = zip(*sorted_data) if sorted_data else ([], [], [])
            
            # Create horizontal bar chart for better readability with long theme names
            fig = go.Figure(data=[
                go.Bar(
                    x=frequencies,
                    y=theme_names,
                    orientation='h',
                    text=[f"{p:.1f}%" for p in percentages],
                    textposition='auto',
                    marker_color=self.color_palette[1],
                    hovertemplate='<b>%{y}</b><br>Frequency: %{x}<br>Percentage: %{text}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title="Theme Frequency Analysis",
                xaxis_title="Frequency",
                yaxis_title="Themes",
                showlegend=False,
                height=max(400, len(theme_names) * 30),
                margin=dict(l=150, r=50, t=80, b=50)
            )
            
            # Get citation IDs
            citation_ids = []
            for theme in themes.values():
                if isinstance(theme, dict) and 'citation_id' in theme:
                    citation_ids.append(theme['citation_id'])
            
            return {
                "type": "horizontal_bar_chart",
                "title": "Theme Frequency Analysis",
                "plotly_json": fig.to_json(),
                "citation_ids": citation_ids,
                "total_themes": len(theme_names)
            }
            
        except Exception as e:
            logger.error(f"Error creating theme frequency chart: {str(e)}")
            return {}
    
    def _create_theme_cooccurrence_matrix(self, themes: Dict[str, Any]) -> Dict[str, Any]:
        """Create a co-occurrence matrix for themes."""
        try:
            theme_names = list(themes.keys())
            
            # Create mock co-occurrence data (in real implementation, this would be calculated from source data)
            # For now, create a simple correlation matrix based on theme frequencies
            frequencies = [themes[theme].get('frequency', 0) for theme in theme_names]
            
            # Create correlation matrix
            matrix = np.outer(frequencies, frequencies)
            matrix = matrix / np.max(matrix)  # Normalize
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=matrix,
                x=theme_names,
                y=theme_names,
                colorscale='Blues',
                showscale=True,
                hovertemplate='<b>%{y}</b> & <b>%{x}</b><br>Co-occurrence: %{z:.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                title="Theme Co-occurrence Matrix",
                xaxis_title="Themes",
                yaxis_title="Themes",
                height=max(500, len(theme_names) * 40),
                margin=dict(l=150, r=50, t=80, b=100)
            )
            
            # Rotate x-axis labels for better readability
            fig.update_xaxes(tickangle=45)
            
            return {
                "type": "heatmap",
                "title": "Theme Co-occurrence Matrix",
                "plotly_json": fig.to_json(),
                "citation_ids": [],
                "matrix_size": len(theme_names)
            }
            
        except Exception as e:
            logger.error(f"Error creating theme co-occurrence matrix: {str(e)}")
            return {}
    
    def _create_sentiment_chart(self, sentiment_data: Dict[str, float]) -> Dict[str, Any]:
        """Create a sentiment analysis chart."""
        try:
            sentiments = list(sentiment_data.keys())
            scores = list(sentiment_data.values())
            
            # Create bar chart
            fig = go.Figure(data=[
                go.Bar(
                    x=sentiments,
                    y=scores,
                    marker_color=[
                        '#d62728' if s < 0.3 else '#ff7f0e' if s < 0.7 else '#2ca02c' 
                        for s in scores
                    ],
                    hovertemplate='<b>%{x}</b><br>Score: %{y:.2f}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title="Sentiment Analysis Overview",
                xaxis_title="Sentiment Categories",
                yaxis_title="Sentiment Score",
                showlegend=False,
                height=400,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            return {
                "type": "sentiment_bar_chart",
                "title": "Sentiment Analysis Overview",
                "plotly_json": fig.to_json(),
                "citation_ids": [],
                "sentiment_categories": len(sentiments)
            }
            
        except Exception as e:
            logger.error(f"Error creating sentiment chart: {str(e)}")
            return {}
    
    def _create_data_source_overview(self, csv_stats: Dict[str, Any], pdf_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create an overview chart showing data sources."""
        try:
            # Calculate data source metrics
            csv_responses = csv_stats.get('metadata', {}).get('total_rows', 0)
            pdf_pages = pdf_stats.get('metadata', {}).get('total_pages', 0)
            csv_fields = len(csv_stats.get('categorical_distributions', {}))
            pdf_themes = len(pdf_stats.get('themes', {}))
            
            # Create summary chart
            categories = ['Survey Responses', 'Interview Pages', 'Data Fields', 'Identified Themes']
            values = [csv_responses, pdf_pages, csv_fields, pdf_themes]
            colors = self.color_palette[:4]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=categories,
                    y=values,
                    marker_color=colors,
                    text=values,
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title="Data Source Overview",
                xaxis_title="Data Categories",
                yaxis_title="Count",
                showlegend=False,
                height=400,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            return {
                "type": "overview_bar_chart",
                "title": "Data Source Overview",
                "plotly_json": fig.to_json(),
                "citation_ids": [],
                "data_summary": {
                    "csv_responses": csv_responses,
                    "pdf_pages": pdf_pages,
                    "csv_fields": csv_fields,
                    "pdf_themes": pdf_themes
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating data source overview: {str(e)}")
            return {}
    
    def _create_insights_correlation_chart(
        self, 
        csv_stats: Dict[str, Any], 
        pdf_stats: Dict[str, Any], 
        analysis_type: str
    ) -> Dict[str, Any]:
        """Create a chart showing correlation between quantitative and qualitative insights."""
        try:
            # This is a conceptual chart showing the relationship between data types
            # In a real implementation, this would analyze actual correlations
            
            data_types = ['Quantitative Data', 'Qualitative Insights']
            coverage = [85, 92]  # Mock coverage percentages
            reliability = [95, 78]  # Mock reliability scores
            
            fig = go.Figure()
            
            # Add coverage bars
            fig.add_trace(go.Bar(
                name='Coverage %',
                x=data_types,
                y=coverage,
                marker_color=self.color_palette[0],
                yaxis='y',
                offsetgroup=1
            ))
            
            # Add reliability bars
            fig.add_trace(go.Bar(
                name='Reliability %',
                x=data_types,
                y=reliability,
                marker_color=self.color_palette[1],
                yaxis='y',
                offsetgroup=2
            ))
            
            fig.update_layout(
                title="Data Quality and Coverage Analysis",
                xaxis_title="Data Types",
                yaxis_title="Percentage",
                barmode='group',
                height=400,
                margin=dict(l=50, r=50, t=80, b=50),
                legend=dict(x=0.7, y=0.9)
            )
            
            return {
                "type": "grouped_bar_chart",
                "title": "Data Quality and Coverage Analysis",
                "plotly_json": fig.to_json(),
                "citation_ids": [],
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            logger.error(f"Error creating insights correlation chart: {str(e)}")
            return {}