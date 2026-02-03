"""
Test Suite for Dynamic Visualization Generation

This module tests chart generation with various data types and analysis contexts,
validates multi-format output generation and accessibility features, tests
visualization integration and citation linking in report synthesis.

Requirements addressed: All visualization requirements (7.1-7.6)
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from ..services.dynamic_visualization_generator import DynamicVisualizationGenerator
from ..services.multi_format_visualization_output import MultiFormatVisualizationOutput
from ..services.visualization_integrated_report_synthesizer import VisualizationIntegratedReportSynthesizer

class TestDynamicVisualizationGenerator:
    """Test suite for DynamicVisualizationGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a DynamicVisualizationGenerator instance."""
        return DynamicVisualizationGenerator()
    
    @pytest.fixture
    def sample_csv_statistics(self):
        """Sample CSV statistics for testing."""
        return {
            'metadata': {
                'filename': 'survey_responses.csv',
                'total_rows': 150,
                'total_columns': 8,
                'detected_types': {'age_group': 'categorical', 'satisfaction': 'categorical'}
            },
            'categorical_distributions': {
                'age_group': {
                    'total_responses': 150,
                    'unique_values': 4,
                    'distribution': [
                        {'value': '25-34', 'count': 60, 'percentage': 40.0, 'citation_id': 'csv_age_1'},
                        {'value': '35-44', 'count': 45, 'percentage': 30.0, 'citation_id': 'csv_age_2'},
                        {'value': '18-24', 'count': 30, 'percentage': 20.0, 'citation_id': 'csv_age_3'},
                        {'value': '45+', 'count': 15, 'percentage': 10.0, 'citation_id': 'csv_age_4'}
                    ]
                },
                'satisfaction': {
                    'total_responses': 150,
                    'unique_values': 3,
                    'distribution': [
                        {'value': 'Satisfied', 'count': 90, 'percentage': 60.0, 'citation_id': 'csv_sat_1'},
                        {'value': 'Neutral', 'count': 45, 'percentage': 30.0, 'citation_id': 'csv_sat_2'},
                        {'value': 'Dissatisfied', 'count': 15, 'percentage': 10.0, 'citation_id': 'csv_sat_3'}
                    ]
                }
            }
        }
    
    @pytest.fixture
    def sample_pdf_statistics(self):
        """Sample PDF statistics for testing."""
        return {
            'metadata': {
                'filename': 'interviews.pdf',
                'total_pages': 25,
                'total_segments': 120
            },
            'themes': {
                'cost_concerns': {
                    'frequency': 18,
                    'percentage': 72.0,
                    'citation_id': 'pdf_theme_1'
                },
                'ease_of_use': {
                    'frequency': 15,
                    'percentage': 60.0,
                    'citation_id': 'pdf_theme_2'
                },
                'feature_requests': {
                    'frequency': 12,
                    'percentage': 48.0,
                    'citation_id': 'pdf_theme_3'
                }
            },
            'participant_profile': {
                'sentiment_analysis': {
                    'positive': 0.65,
                    'neutral': 0.25,
                    'negative': 0.10
                }
            }
        }
    
    @pytest.fixture
    def sample_statistics_registry(self, sample_csv_statistics, sample_pdf_statistics):
        """Complete statistics registry for testing."""
        return {
            'csv_statistics': sample_csv_statistics,
            'pdf_statistics': sample_pdf_statistics,
            'citation_registry': {
                'csv_age_1': {'source_type': 'csv', 'source_file': 'survey_responses.csv'},
                'pdf_theme_1': {'source_type': 'pdf', 'source_file': 'interviews.pdf'}
            }
        }
    
    def test_generate_visualizations_for_analysis_comprehensive(self, generator, sample_statistics_registry):
        """Test comprehensive visualization generation."""
        visualizations = generator.generate_visualizations_for_analysis(
            sample_statistics_registry, "comprehensive"
        )
        
        assert isinstance(visualizations, dict)
        assert len(visualizations) > 0
        
        # Should have demographic charts
        demographic_charts = [v for k, v in visualizations.items() if 'demographic' in k]
        assert len(demographic_charts) > 0
        
        # Should have theme charts
        theme_charts = [v for k, v in visualizations.items() if 'theme' in k]
        assert len(theme_charts) > 0
        
        # Should have comparison charts
        comparison_charts = [v for k, v in visualizations.items() if any(x in k for x in ['overview', 'correlation'])]
        assert len(comparison_charts) > 0
    
    def test_create_demographic_charts_bar_chart(self, generator, sample_csv_statistics):
        """Test demographic bar chart generation."""
        charts = generator.create_demographic_charts(sample_csv_statistics, "size")
        
        assert isinstance(charts, dict)
        assert len(charts) > 0
        
        # Check first chart
        chart = next(iter(charts.values()))
        assert chart['type'] == 'bar_chart'
        assert 'title' in chart
        assert 'plotly_json' in chart
        assert 'citation_ids' in chart
        assert chart['total_responses'] == 150
        
        # Validate plotly JSON structure
        plotly_data = json.loads(chart['plotly_json'])
        assert 'data' in plotly_data
        assert 'layout' in plotly_data
    
    def test_create_demographic_charts_pie_chart(self, generator, sample_csv_statistics):
        """Test demographic pie chart generation for small categories."""
        charts = generator.create_demographic_charts(sample_csv_statistics, "pain")
        
        # Should create pie chart for satisfaction (3 categories) in pain analysis
        satisfaction_chart = None
        for chart in charts.values():
            if 'satisfaction' in chart.get('field_name', ''):
                satisfaction_chart = chart
                break
        
        if satisfaction_chart:
            assert satisfaction_chart['type'] == 'pie_chart'
            plotly_data = json.loads(satisfaction_chart['plotly_json'])
            pie_data = plotly_data['data'][0]
            assert 'labels' in pie_data
            assert 'values' in pie_data
    
    def test_create_theme_visualizations(self, generator, sample_pdf_statistics):
        """Test theme visualization generation."""
        charts = generator.create_theme_visualizations(sample_pdf_statistics, "comprehensive")
        
        assert isinstance(charts, dict)
        assert len(charts) > 0
        
        # Should have theme frequency chart
        frequency_chart = None
        for chart in charts.values():
            if chart.get('type') == 'horizontal_bar_chart':
                frequency_chart = chart
                break
        
        assert frequency_chart is not None
        assert 'Theme Frequency' in frequency_chart['title']
        assert frequency_chart['total_themes'] == 3
        
        # Should have sentiment chart
        sentiment_chart = None
        for chart in charts.values():
            if chart.get('type') == 'sentiment_bar_chart':
                sentiment_chart = chart
                break
        
        assert sentiment_chart is not None
        assert 'Sentiment Analysis' in sentiment_chart['title']
    
    def test_create_comparison_charts(self, generator, sample_csv_statistics, sample_pdf_statistics):
        """Test comparison chart generation."""
        charts = generator.create_comparison_charts(
            sample_csv_statistics, sample_pdf_statistics, "comprehensive"
        )
        
        assert isinstance(charts, dict)
        assert len(charts) > 0
        
        # Should have data overview chart
        overview_chart = None
        for chart in charts.values():
            if chart.get('type') == 'overview_bar_chart':
                overview_chart = chart
                break
        
        assert overview_chart is not None
        assert 'Data Source Overview' in overview_chart['title']
        
        # Validate data summary
        data_summary = overview_chart.get('data_summary', {})
        assert data_summary['csv_responses'] == 150
        assert data_summary['pdf_pages'] == 25
    
    def test_chart_type_determination(self, generator):
        """Test chart type determination logic."""
        # Small categories should use pie chart for certain analysis types
        small_distribution = {'distribution': [{'value': 'A', 'count': 10}, {'value': 'B', 'count': 5}]}
        chart_type = generator._determine_chart_type(small_distribution, 'pain')
        assert chart_type == 'pie_chart'
        
        # Medium categories should use bar chart
        medium_distribution = {'distribution': [{'value': f'Cat{i}', 'count': 10} for i in range(8)]}
        chart_type = generator._determine_chart_type(medium_distribution, 'size')
        assert chart_type == 'bar_chart'
        
        # Large categories should use table
        large_distribution = {'distribution': [{'value': f'Cat{i}', 'count': 10} for i in range(20)]}
        chart_type = generator._determine_chart_type(large_distribution, 'comprehensive')
        assert chart_type == 'table'
    
    def test_persona_filtering(self, generator, sample_statistics_registry):
        """Test persona-based filtering of statistics."""
        # Test with persona ID
        visualizations = generator.generate_visualizations_for_analysis(
            sample_statistics_registry, "comprehensive", persona_id="persona_1"
        )
        
        # Should still generate visualizations (filtering logic can be enhanced)
        assert isinstance(visualizations, dict)
    
    def test_error_handling_empty_data(self, generator):
        """Test error handling with empty data."""
        empty_registry = {'csv_statistics': {}, 'pdf_statistics': {}}
        
        visualizations = generator.generate_visualizations_for_analysis(
            empty_registry, "comprehensive"
        )
        
        assert isinstance(visualizations, dict)
        # Should handle empty data gracefully
    
    def test_citation_ids_preservation(self, generator, sample_csv_statistics):
        """Test that citation IDs are preserved in visualizations."""
        charts = generator.create_demographic_charts(sample_csv_statistics)
        
        for chart in charts.values():
            citation_ids = chart.get('citation_ids', [])
            assert isinstance(citation_ids, list)
            # Should have citation IDs from the source data
            if citation_ids:
                assert all(isinstance(cid, str) for cid in citation_ids)


class TestMultiFormatVisualizationOutput:
    """Test suite for MultiFormatVisualizationOutput."""
    
    @pytest.fixture
    def output_generator(self):
        """Create a MultiFormatVisualizationOutput instance."""
        return MultiFormatVisualizationOutput()
    
    @pytest.fixture
    def sample_visualization(self):
        """Sample visualization for testing."""
        return {
            'type': 'bar_chart',
            'title': 'Age Group Distribution',
            'plotly_json': json.dumps({
                'data': [{
                    'x': ['25-34', '35-44', '18-24', '45+'],
                    'y': [60, 45, 30, 15],
                    'type': 'bar'
                }],
                'layout': {'title': 'Age Group Distribution'}
            }),
            'citation_ids': ['csv_age_1', 'csv_age_2'],
            'field_name': 'age_group',
            'total_responses': 150
        }
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_generate_all_formats(self, mock_to_image, output_generator, sample_visualization):
        """Test generation of all output formats."""
        # Mock image generation
        mock_to_image.return_value = b'fake_image_data'
        
        enhanced_viz = output_generator.generate_all_formats(sample_visualization)
        
        assert isinstance(enhanced_viz, dict)
        
        # Should have interactive chart enhancements
        assert 'interactive_chart' in enhanced_viz
        
        # Should have static images
        assert 'static_image_png' in enhanced_viz
        assert 'static_image_svg' in enhanced_viz
        
        # Should have markdown table
        assert 'markdown_table' in enhanced_viz
        
        # Should have alt text
        assert 'alt_text' in enhanced_viz
        
        # Should have accessibility features
        assert 'accessibility' in enhanced_viz
        
        # Should have responsive config
        assert 'responsive_config' in enhanced_viz
    
    def test_enhance_interactive_chart(self, output_generator, sample_visualization):
        """Test interactive chart enhancement."""
        plotly_json = sample_visualization['plotly_json']
        
        enhanced = output_generator._enhance_interactive_chart(plotly_json)
        
        assert isinstance(enhanced, dict)
        assert 'plotly_json' in enhanced
        assert 'plotly_config' in enhanced
        assert 'html_div' in enhanced
        
        # Validate config
        config = enhanced['plotly_config']
        assert config['accessible'] is True
        assert config['displaylogo'] is False
    
    @patch('plotly.graph_objects.Figure.to_image')
    def test_generate_static_images(self, mock_to_image, output_generator, sample_visualization):
        """Test static image generation."""
        mock_to_image.return_value = b'fake_image_data'
        
        plotly_json = sample_visualization['plotly_json']
        static_formats = output_generator._generate_static_images(plotly_json, sample_visualization)
        
        assert isinstance(static_formats, dict)
        assert 'static_image_png' in static_formats
        assert 'static_image_svg' in static_formats
        assert 'image_dimensions' in static_formats
        
        # Validate base64 encoding
        png_data = static_formats['static_image_png']
        assert isinstance(png_data, str)
        
        # Validate dimensions
        dimensions = static_formats['image_dimensions']
        assert dimensions['width'] == 800
        assert dimensions['height'] == 600
    
    def test_generate_markdown_table_bar_chart(self, output_generator, sample_visualization):
        """Test markdown table generation for bar charts."""
        markdown_table = output_generator._generate_markdown_table(sample_visualization)
        
        assert isinstance(markdown_table, str)
        assert '## Age Group Distribution' in markdown_table
        assert '| Age Group | Count | Percentage |' in markdown_table
        assert '25-34' in markdown_table
        assert '40.0%' in markdown_table
    
    def test_generate_markdown_table_pie_chart(self, output_generator):
        """Test markdown table generation for pie charts."""
        pie_viz = {
            'type': 'pie_chart',
            'title': 'Satisfaction Distribution',
            'plotly_json': json.dumps({
                'data': [{
                    'labels': ['Satisfied', 'Neutral', 'Dissatisfied'],
                    'values': [90, 45, 15],
                    'type': 'pie'
                }]
            }),
            'field_name': 'satisfaction',
            'total_responses': 150
        }
        
        markdown_table = output_generator._generate_markdown_table(pie_viz)
        
        assert isinstance(markdown_table, str)
        assert '## Satisfaction Distribution' in markdown_table
        assert 'Satisfied' in markdown_table
        assert '60.0%' in markdown_table
    
    def test_generate_alt_text_distribution(self, output_generator, sample_visualization):
        """Test alt-text generation for distribution charts."""
        alt_text = output_generator._generate_alt_text(sample_visualization)
        
        assert isinstance(alt_text, str)
        assert 'bar chart' in alt_text.lower()
        assert 'age_group' in alt_text
        assert '150 responses' in alt_text
        assert '25-34' in alt_text  # Top category
    
    def test_generate_accessibility_features(self, output_generator, sample_visualization):
        """Test accessibility features generation."""
        accessibility = output_generator._generate_accessibility_features(sample_visualization)
        
        assert isinstance(accessibility, dict)
        assert accessibility['wcag_compliance'] == 'AA'
        assert accessibility['screen_reader_compatible'] is True
        assert accessibility['keyboard_navigable'] is True
        assert accessibility['high_contrast_available'] is True
        
        # Check ARIA labels
        aria_labels = accessibility['aria_labels']
        assert aria_labels['chart_title'] == 'Age Group Distribution'
        assert aria_labels['chart_type'] == 'bar_chart'
    
    def test_generate_responsive_config(self, output_generator, sample_visualization):
        """Test responsive configuration generation."""
        responsive_config = output_generator._generate_responsive_config(sample_visualization)
        
        assert isinstance(responsive_config, dict)
        assert 'mobile' in responsive_config
        assert 'tablet' in responsive_config
        assert 'desktop' in responsive_config
        assert 'print' in responsive_config
        
        # Validate mobile config
        mobile_config = responsive_config['mobile']
        assert mobile_config['width'] == 350
        assert mobile_config['height'] == 300
        assert mobile_config['font_size'] == 10
        
        # Validate desktop config
        desktop_config = responsive_config['desktop']
        assert desktop_config['width'] == 800
        assert desktop_config['height'] == 600
    
    def test_responsive_config_chart_type_adjustments(self, output_generator):
        """Test responsive config adjustments for different chart types."""
        # Test horizontal bar chart (needs more height)
        horizontal_viz = {'type': 'horizontal_bar_chart', 'title': 'Theme Frequency'}
        config = output_generator._generate_responsive_config(horizontal_viz)
        
        # Should have increased height
        assert config['desktop']['height'] > 600
        
        # Test table (needs more height)
        table_viz = {'type': 'table', 'title': 'Data Table'}
        config = output_generator._generate_responsive_config(table_viz)
        
        # Should have increased height
        assert config['desktop']['height'] > 600
        
        # Test heatmap (square aspect ratio)
        heatmap_viz = {'type': 'heatmap', 'title': 'Co-occurrence Matrix'}
        config = output_generator._generate_responsive_config(heatmap_viz)
        
        # Should have equal width and height
        assert config['desktop']['height'] == config['desktop']['width']
    
    def test_error_handling_invalid_plotly_json(self, output_generator):
        """Test error handling with invalid plotly JSON."""
        invalid_viz = {
            'type': 'bar_chart',
            'title': 'Invalid Chart',
            'plotly_json': 'invalid_json',
            'citation_ids': []
        }
        
        enhanced_viz = output_generator.generate_all_formats(invalid_viz)
        
        # Should handle errors gracefully and return original visualization
        assert enhanced_viz['title'] == 'Invalid Chart'


class TestVisualizationIntegratedReportSynthesizer:
    """Test suite for VisualizationIntegratedReportSynthesizer."""
    
    @pytest.fixture
    def synthesizer(self):
        """Create a VisualizationIntegratedReportSynthesizer instance."""
        return VisualizationIntegratedReportSynthesizer()
    
    @pytest.fixture
    def sample_assumption_analyses(self):
        """Sample assumption analyses for testing."""
        return [
            {
                'assumption_id': 'assumption_1',
                'assumption_text': 'Users struggle with high costs',
                'persona_name': 'Budget-Conscious User',
                'validation_status': 'validated',
                'analyses': {
                    'pain_points': {
                        'claim': 'Cost is the primary concern for 72% of users',
                        'supporting_evidence': ['High pricing mentioned in 18/25 interviews'],
                        'statistical_data': {'fact_validation': {'fact_check_score': 0.95}}
                    },
                    'size_frequency': {
                        'claim': 'Cost concerns affect 108 out of 150 survey respondents',
                        'supporting_evidence': ['Survey data shows consistent cost sensitivity'],
                        'statistical_data': {'fact_validation': {'fact_check_score': 0.98}}
                    }
                },
                'fact_validation_results': {'overall_fact_score': 0.96}
            },
            {
                'assumption_id': 'assumption_2',
                'assumption_text': 'Users need better ease of use',
                'persona_name': 'Tech-Savvy User',
                'validation_status': 'partially_validated',
                'analyses': {
                    'pain_points': {
                        'claim': 'Usability issues mentioned by 60% of tech users',
                        'supporting_evidence': ['Interface complexity noted in interviews'],
                        'statistical_data': {'fact_validation': {'fact_check_score': 0.78}}
                    }
                },
                'fact_validation_results': {'overall_fact_score': 0.78}
            }
        ]
    
    @pytest.fixture
    def sample_enhanced_visualizations(self):
        """Sample enhanced visualizations for testing."""
        return {
            'demographic_age_group_0': {
                'type': 'bar_chart',
                'title': 'Age Group Distribution',
                'plotly_json': '{"data": [], "layout": {}}',
                'citation_ids': ['csv_age_1'],
                'markdown_table': '## Age Group Distribution\n| Category | Count |\n|----------|-------|\n| 25-34 | 60 |',
                'alt_text': 'Bar chart showing age group distribution',
                'accessibility': {'wcag_compliance': 'AA'},
                'responsive_config': {'desktop': {'width': 800, 'height': 600}}
            },
            'theme_frequency_1': {
                'type': 'horizontal_bar_chart',
                'title': 'Theme Frequency Analysis',
                'plotly_json': '{"data": [], "layout": {}}',
                'citation_ids': ['pdf_theme_1'],
                'markdown_table': '## Theme Frequency\n| Theme | Frequency |\n|-------|----------|\n| Cost | 18 |',
                'alt_text': 'Horizontal bar chart showing theme frequencies',
                'total_themes': 3
            },
            'data_overview_2': {
                'type': 'overview_bar_chart',
                'title': 'Data Source Overview',
                'plotly_json': '{"data": [], "layout": {}}',
                'citation_ids': [],
                'data_summary': {'csv_responses': 150, 'pdf_pages': 25}
            }
        }
    
    @pytest.fixture
    def sample_statistics_registry(self):
        """Sample statistics registry for testing."""
        return {
            'csv_statistics': {
                'metadata': {'filename': 'survey.csv', 'total_rows': 150, 'total_columns': 8},
                'categorical_distributions': {'age_group': {}, 'satisfaction': {}}
            },
            'pdf_statistics': {
                'metadata': {'filename': 'interviews.pdf', 'total_pages': 25},
                'themes': {'cost_concerns': {}, 'ease_of_use': {}}
            },
            'citation_registry': {'csv_age_1': {}, 'pdf_theme_1': {}}
        }
    
    @pytest.fixture
    def sample_project_context(self):
        """Sample project context for testing."""
        return {
            'project_id': 'test_project',
            'personas': [
                {'id': 'persona_1', 'name': 'Budget-Conscious User'},
                {'id': 'persona_2', 'name': 'Tech-Savvy User'}
            ]
        }
    
    @patch.object(DynamicVisualizationGenerator, 'generate_visualizations_for_analysis')
    @patch.object(MultiFormatVisualizationOutput, 'generate_all_formats')
    @pytest.mark.asyncio
    async def test_synthesize_report_with_visuals(
        self, 
        mock_generate_formats, 
        mock_generate_viz,
        synthesizer, 
        sample_assumption_analyses,
        sample_enhanced_visualizations,
        sample_statistics_registry,
        sample_project_context
    ):
        """Test complete report synthesis with visualizations."""
        # Mock visualization generation
        mock_generate_viz.return_value = {
            'viz_1': {'type': 'bar_chart', 'title': 'Test Chart'}
        }
        mock_generate_formats.return_value = sample_enhanced_visualizations['demographic_age_group_0']
        
        result = await synthesizer.synthesize_report_with_visuals(
            sample_assumption_analyses,
            sample_statistics_registry,
            sample_project_context
        )
        
        assert isinstance(result, dict)
        assert 'final_report' in result
        assert 'visualizations' in result
        assert 'metadata' in result
        assert 'sections' in result
        
        # Validate report structure
        final_report = result['final_report']
        assert '# Executive Summary' in final_report
        assert '# Data Overview and Methodology' in final_report
        assert '# Methodology' in final_report
        assert '# Key Insights and Recommendations' in final_report
        
        # Validate metadata
        metadata = result['metadata']
        assert 'generation_timestamp' in metadata
        assert 'total_assumptions' in metadata
        assert metadata['total_assumptions'] == 2
    
    @pytest.mark.asyncio
    async def test_build_executive_summary_with_visuals(
        self, 
        synthesizer,
        sample_assumption_analyses,
        sample_enhanced_visualizations,
        sample_statistics_registry
    ):
        """Test executive summary section building."""
        section = await synthesizer._build_executive_summary_with_visuals(
            sample_assumption_analyses,
            sample_enhanced_visualizations,
            sample_statistics_registry
        )
        
        assert isinstance(section, str)
        assert '# Executive Summary' in section
        assert '## Overview' in section
        assert '150 survey responses' in section
        assert '25 pages' in section
        assert '## Key Findings' in section
        assert '## Validation Summary' in section
    
    @pytest.mark.asyncio
    async def test_build_data_overview_with_visuals(
        self,
        synthesizer,
        sample_statistics_registry,
        sample_enhanced_visualizations
    ):
        """Test data overview section building."""
        section = await synthesizer._build_data_overview_with_visuals(
            sample_statistics_registry,
            sample_enhanced_visualizations
        )
        
        assert isinstance(section, str)
        assert '# Data Overview and Methodology' in section
        assert '## Data Sources' in section
        assert 'Survey Data:' in section
        assert 'Interview Data:' in section
        assert 'Total Responses:** 150' in section
        assert 'Total Pages:** 25' in section
    
    @pytest.mark.asyncio
    async def test_build_assumption_section_with_visuals(
        self,
        synthesizer,
        sample_enhanced_visualizations,
        sample_statistics_registry
    ):
        """Test assumption analysis section building."""
        analysis = {
            'assumption_text': 'Users struggle with high costs',
            'persona_name': 'Budget-Conscious User',
            'validation_status': 'validated',
            'analyses': {
                'pain_points': {
                    'claim': 'Cost is the primary concern for 72% of users',
                    'supporting_evidence': ['High pricing mentioned in interviews'],
                    'statistical_data': {'fact_validation': {'fact_check_score': 0.95}}
                }
            },
            'fact_validation_results': {'overall_fact_score': 0.96}
        }
        
        section = await synthesizer._build_assumption_section_with_visuals(
            analysis,
            sample_enhanced_visualizations,
            sample_statistics_registry
        )
        
        assert isinstance(section, str)
        assert '# Assumption Analysis: Budget-Conscious User' in section
        assert 'Users struggle with high costs' in section
        assert 'Validation Status:** Validated' in section
        assert '## Pain Points Analysis' in section
        assert 'Cost is the primary concern for 72% of users' in section
        assert '## Validation Summary' in section
        assert 'Overall Fact Validation Score:** 0.96' in section
    
    def test_select_visualization_by_type(self, synthesizer, sample_enhanced_visualizations):
        """Test visualization selection by type."""
        viz = synthesizer._select_visualization_by_type(
            sample_enhanced_visualizations, 'bar_chart'
        )
        
        assert viz is not None
        assert viz['type'] == 'bar_chart'
        assert viz['title'] == 'Age Group Distribution'
    
    def test_select_visualizations_by_pattern(self, synthesizer, sample_enhanced_visualizations):
        """Test visualization selection by pattern."""
        vizs = synthesizer._select_visualizations_by_pattern(
            sample_enhanced_visualizations, 'demographic_'
        )
        
        assert isinstance(vizs, dict)
        assert len(vizs) == 1
        assert 'demographic_age_group_0' in vizs
    
    def test_select_relevant_visualization_for_analysis(self, synthesizer, sample_enhanced_visualizations):
        """Test relevant visualization selection for analysis types."""
        # Test pain analysis - should prefer demographic or theme charts
        viz = synthesizer._select_relevant_visualization_for_analysis(
            sample_enhanced_visualizations, 'pain_points', 'Budget-Conscious User'
        )
        
        assert viz is not None
        assert viz['type'] in ['bar_chart', 'horizontal_bar_chart']
        
        # Test size analysis - should prefer demographic or overview charts
        viz = synthesizer._select_relevant_visualization_for_analysis(
            sample_enhanced_visualizations, 'size_frequency', 'Budget-Conscious User'
        )
        
        assert viz is not None
    
    def test_embed_visualization_interactive(self, synthesizer, sample_enhanced_visualizations):
        """Test interactive visualization embedding."""
        viz = sample_enhanced_visualizations['demographic_age_group_0']
        
        embed_code = synthesizer._embed_visualization(viz, 'desktop', 'interactive')
        
        assert isinstance(embed_code, str)
        assert 'visualization-container' in embed_code
        assert 'Age Group Distribution' in embed_code
        assert 'data-plotly-json' in embed_code
        assert 'width: 800px' in embed_code
        assert 'height: 600px' in embed_code
    
    def test_embed_visualization_markdown_table(self, synthesizer, sample_enhanced_visualizations):
        """Test markdown table visualization embedding."""
        viz = sample_enhanced_visualizations['demographic_age_group_0']
        
        embed_code = synthesizer._embed_visualization(viz, 'desktop', 'markdown_table')
        
        assert isinstance(embed_code, str)
        assert '## Age Group Distribution' in embed_code
        assert '| Category | Count |' in embed_code
    
    def test_format_analysis_type_title(self, synthesizer):
        """Test analysis type title formatting."""
        assert synthesizer._format_analysis_type_title('pain_points') == 'Pain Points Analysis'
        assert synthesizer._format_analysis_type_title('size_frequency') == 'Market Size and Frequency Analysis'
        assert synthesizer._format_analysis_type_title('solutions') == 'Current Solutions Analysis'
        assert synthesizer._format_analysis_type_title('gains') == 'Potential Gains Analysis'
        assert synthesizer._format_analysis_type_title('jtbd') == 'Jobs-to-be-Done Analysis'
    
    def test_extract_key_insights(self, synthesizer, sample_assumption_analyses):
        """Test key insights extraction."""
        insights = synthesizer._extract_key_insights(sample_assumption_analyses)
        
        assert isinstance(insights, list)
        assert len(insights) == 2
        assert 'Budget-Conscious User** assumption is strongly validated' in insights[0]
        assert 'Tech-Savvy User** assumption shows mixed validation' in insights[1]
    
    def test_generate_validation_summary(self, synthesizer, sample_assumption_analyses):
        """Test validation summary generation."""
        summary = synthesizer._generate_validation_summary(sample_assumption_analyses)
        
        assert isinstance(summary, str)
        assert 'Overall Validation Results:' in summary
        assert 'Validated:** 1/2' in summary
        assert 'Partially Validated:** 1/2' in summary
        assert '50.0%' in summary
    
    def test_generate_report_metadata(
        self, 
        synthesizer,
        sample_enhanced_visualizations,
        sample_assumption_analyses,
        sample_statistics_registry
    ):
        """Test report metadata generation."""
        metadata = synthesizer._generate_report_metadata(
            sample_enhanced_visualizations,
            sample_assumption_analyses,
            sample_statistics_registry
        )
        
        assert isinstance(metadata, dict)
        assert 'generation_timestamp' in metadata
        assert metadata['total_visualizations'] == 3
        assert metadata['total_assumptions'] == 2
        
        # Validate validation summary
        validation_summary = metadata['validation_summary']
        assert validation_summary['validated'] == 1
        assert validation_summary['partially_validated'] == 1
        assert validation_summary['invalidated'] == 0
        
        # Validate data sources
        data_sources = metadata['data_sources']
        assert data_sources['csv_files'] == 1
        assert data_sources['pdf_files'] == 1
        assert data_sources['total_citations'] == 2
        
        # Validate accessibility features
        accessibility = metadata['accessibility_features']
        assert accessibility['alt_text_provided'] is True
        assert accessibility['markdown_fallbacks'] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_visualization_generation_failure(
        self,
        synthesizer,
        sample_assumption_analyses,
        sample_statistics_registry,
        sample_project_context
    ):
        """Test error handling when visualization generation fails."""
        # Mock visualization generator to raise exception
        with patch.object(synthesizer.viz_generator, 'generate_visualizations_for_analysis', 
                         side_effect=Exception("Visualization generation failed")):
            
            result = await synthesizer.synthesize_report_with_visuals(
                sample_assumption_analyses,
                sample_statistics_registry,
                sample_project_context
            )
            
            # Should return fallback report
            assert isinstance(result, dict)
            assert 'final_report' in result
            assert 'Market Research Analysis Report' in result['final_report']
            assert 'error' in result['metadata']
    
    def test_generate_fallback_report(self, synthesizer, sample_assumption_analyses):
        """Test fallback report generation."""
        fallback_report = synthesizer._generate_fallback_report(sample_assumption_analyses)
        
        assert isinstance(fallback_report, str)
        assert '# Market Research Analysis Report' in fallback_report
        assert 'Analysis completed for 2 assumptions' in fallback_report
        assert 'Users struggle with high costs' in fallback_report
        assert 'Users need better ease of use' in fallback_report


# Integration tests
class TestVisualizationIntegration:
    """Integration tests for the complete visualization system."""
    
    @pytest.fixture
    def complete_system(self):
        """Set up complete visualization system."""
        return {
            'generator': DynamicVisualizationGenerator(),
            'output': MultiFormatVisualizationOutput(),
            'synthesizer': VisualizationIntegratedReportSynthesizer()
        }
    
    @pytest.fixture
    def complete_test_data(self):
        """Complete test data for integration testing."""
        return {
            'statistics_registry': {
                'csv_statistics': {
                    'metadata': {'filename': 'test.csv', 'total_rows': 100, 'total_columns': 5},
                    'categorical_distributions': {
                        'category': {
                            'total_responses': 100,
                            'distribution': [
                                {'value': 'A', 'count': 50, 'percentage': 50.0, 'citation_id': 'csv_1'},
                                {'value': 'B', 'count': 30, 'percentage': 30.0, 'citation_id': 'csv_2'},
                                {'value': 'C', 'count': 20, 'percentage': 20.0, 'citation_id': 'csv_3'}
                            ]
                        }
                    }
                },
                'pdf_statistics': {
                    'metadata': {'filename': 'test.pdf', 'total_pages': 10},
                    'themes': {
                        'theme1': {'frequency': 8, 'percentage': 80.0, 'citation_id': 'pdf_1'},
                        'theme2': {'frequency': 6, 'percentage': 60.0, 'citation_id': 'pdf_2'}
                    }
                },
                'citation_registry': {
                    'csv_1': {'source_type': 'csv', 'source_file': 'test.csv'},
                    'pdf_1': {'source_type': 'pdf', 'source_file': 'test.pdf'}
                }
            },
            'assumption_analyses': [
                {
                    'assumption_text': 'Test assumption',
                    'persona_name': 'Test Persona',
                    'validation_status': 'validated',
                    'analyses': {
                        'pain_points': {
                            'claim': 'Test claim with 50% statistic',
                            'supporting_evidence': ['Test evidence'],
                            'statistical_data': {'fact_validation': {'fact_check_score': 0.9}}
                        }
                    },
                    'fact_validation_results': {'overall_fact_score': 0.9}
                }
            ],
            'project_context': {'project_id': 'test', 'personas': []}
        }
    
    @patch('plotly.graph_objects.Figure.to_image')
    @pytest.mark.asyncio
    async def test_end_to_end_visualization_pipeline(
        self, 
        mock_to_image,
        complete_system, 
        complete_test_data
    ):
        """Test complete end-to-end visualization pipeline."""
        mock_to_image.return_value = b'fake_image_data'
        
        # Generate visualizations
        visualizations = complete_system['generator'].generate_visualizations_for_analysis(
            complete_test_data['statistics_registry'], 'comprehensive'
        )
        
        assert len(visualizations) > 0
        
        # Enhance with multi-format output
        enhanced_visualizations = {}
        for viz_id, viz_data in visualizations.items():
            enhanced_viz = complete_system['output'].generate_all_formats(viz_data)
            enhanced_visualizations[viz_id] = enhanced_viz
        
        # Verify enhancements
        for viz in enhanced_visualizations.values():
            assert 'markdown_table' in viz
            assert 'alt_text' in viz
            assert 'accessibility' in viz
        
        # Synthesize report
        report_result = await complete_system['synthesizer'].synthesize_report_with_visuals(
            complete_test_data['assumption_analyses'],
            complete_test_data['statistics_registry'],
            complete_test_data['project_context']
        )
        
        # Verify complete report
        assert 'final_report' in report_result
        assert 'visualizations' in report_result
        assert 'metadata' in report_result
        
        final_report = report_result['final_report']
        assert '# Executive Summary' in final_report
        assert 'visualization-container' in final_report
    
    def test_citation_linking_throughout_pipeline(self, complete_system, complete_test_data):
        """Test that citation IDs are preserved throughout the pipeline."""
        # Generate visualizations
        visualizations = complete_system['generator'].generate_visualizations_for_analysis(
            complete_test_data['statistics_registry'], 'comprehensive'
        )
        
        # Verify citation IDs are preserved
        for viz in visualizations.values():
            citation_ids = viz.get('citation_ids', [])
            if citation_ids:
                # Should contain valid citation IDs from registry
                registry_citations = complete_test_data['statistics_registry']['citation_registry'].keys()
                assert any(cid in registry_citations for cid in citation_ids)
    
    def test_responsive_layout_consistency(self, complete_system, complete_test_data):
        """Test responsive layout consistency across formats."""
        # Generate and enhance visualizations
        visualizations = complete_system['generator'].generate_visualizations_for_analysis(
            complete_test_data['statistics_registry'], 'comprehensive'
        )
        
        enhanced_viz = complete_system['output'].generate_all_formats(
            next(iter(visualizations.values()))
        )
        
        # Verify responsive configurations
        responsive_config = enhanced_viz.get('responsive_config', {})
        
        assert 'mobile' in responsive_config
        assert 'tablet' in responsive_config
        assert 'desktop' in responsive_config
        assert 'print' in responsive_config
        
        # Verify layout consistency
        for layout_name, layout_config in responsive_config.items():
            assert 'width' in layout_config
            assert 'height' in layout_config
            assert 'font_size' in layout_config
            assert 'margin' in layout_config
    
    def test_accessibility_compliance_throughout_pipeline(self, complete_system, complete_test_data):
        """Test accessibility compliance throughout the visualization pipeline."""
        # Generate visualizations
        visualizations = complete_system['generator'].generate_visualizations_for_analysis(
            complete_test_data['statistics_registry'], 'comprehensive'
        )
        
        # Enhance with accessibility features
        for viz_id, viz_data in visualizations.items():
            enhanced_viz = complete_system['output'].generate_all_formats(viz_data)
            
            # Verify accessibility features
            accessibility = enhanced_viz.get('accessibility', {})
            assert accessibility.get('wcag_compliance') == 'AA'
            assert accessibility.get('screen_reader_compatible') is True
            assert accessibility.get('keyboard_navigable') is True
            
            # Verify alt-text exists and is meaningful
            alt_text = enhanced_viz.get('alt_text', '')
            assert len(alt_text) > 10  # Should be descriptive
            assert viz_data.get('title', '').lower() in alt_text.lower()
            
            # Verify markdown fallback exists
            markdown_table = enhanced_viz.get('markdown_table', '')
            assert len(markdown_table) > 0
            assert '##' in markdown_table  # Should have proper markdown structure