"""
Report analytics data visualization service for formatting data for charts and visualizations.

This service provides:
- Data formatting for various chart types
- Support for different time ranges
- Chart data generation for frontend consumption
- JSON-compliant data structures
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

from .report_usage_analytics_service import report_usage_analytics_service
from .report_trend_detection_service import report_trend_detection_service
from ..services.utilities.fallback_service import fallback_service
from ...utils.circuit_breaker import circuit_breaker, CircuitBreakerError
from ...schemas.schemas import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class ChartDataPoint(BaseModel):
    """Model for a single chart data point."""
    x: Union[str, int, float] = Field(..., description="X-axis value")
    y: Union[int, float] = Field(..., description="Y-axis value")
    label: Optional[str] = Field(None, description="Optional label for the data point")
    color: Optional[str] = Field(None, description="Optional color for the data point")


class ChartSeries(BaseModel):
    """Model for a chart data series."""
    name: str = Field(..., description="Series name")
    data: List[ChartDataPoint] = Field(..., description="Data points in the series")
    type: str = Field(..., description="Chart type: line, bar, pie, area")
    color: Optional[str] = Field(None, description="Series color")


class ChartConfig(BaseModel):
    """Model for chart configuration."""
    title: str = Field(..., description="Chart title")
    subtitle: Optional[str] = Field(None, description="Chart subtitle")
    x_axis_label: str = Field(..., description="X-axis label")
    y_axis_label: str = Field(..., description="Y-axis label")
    chart_type: str = Field(..., description="Chart type: line, bar, pie, area, scatter")
    time_range: str = Field(..., description="Time range: week, month, quarter, year")


class VisualizationData(BaseModel):
    """Model for complete visualization data."""
    config: ChartConfig = Field(..., description="Chart configuration")
    series: List[ChartSeries] = Field(..., description="Chart data series")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Generation timestamp")


class DashboardData(BaseModel):
    """Model for dashboard visualization data."""
    creation_frequency_chart: VisualizationData = Field(..., description="Report creation frequency chart")
    topic_distribution_chart: VisualizationData = Field(..., description="Topic distribution chart")
    industry_distribution_chart: VisualizationData = Field(..., description="Industry distribution chart")
    trend_analysis_chart: VisualizationData = Field(..., description="Trend analysis chart")
    summary_metrics: Dict[str, Any] = Field(..., description="Summary metrics for display")


class ReportAnalyticsVisualizationService:
    """Service for generating visualization data for report analytics."""
    
    def __init__(self):
        self.usage_service = report_usage_analytics_service
        self.trend_service = report_trend_detection_service
    
    @circuit_breaker(
        name="analytics_creation_frequency",
        failure_threshold=2,
        recovery_timeout=60,
        timeout=30
    )
    async def generate_creation_frequency_chart(
        self, 
        user_id: str, 
        time_range: str = "month"
    ) -> VisualizationData:
        """
        Generate chart data for report creation frequency.
        Enhanced with fallback mechanisms.
        
        Args:
            user_id: User ID
            time_range: Time range (week, month, quarter, year)
            
        Returns:
            Visualization data for creation frequency chart
        """
        cache_key = f"analytics_frequency_{user_id}_{time_range}"
        
        try:
            # Determine days based on time range
            days_map = {"week": 7, "month": 30, "quarter": 90, "year": 365}
            days = days_map.get(time_range, 30)
            
            # Get creation frequency data
            frequency_data = await self.usage_service.get_creation_frequency(user_id, days)
            
            # Convert to chart data points
            data_points = []
            for freq in frequency_data:
                data_points.append(ChartDataPoint(
                    x=freq.date,
                    y=freq.count,
                    label=f"{freq.count} reports"
                ))
            
            # Create chart series
            series = [ChartSeries(
                name="Reports Created",
                data=data_points,
                type="line",
                color="#3B82F6"
            )]
            
            # Create chart configuration
            config = ChartConfig(
                title="Report Creation Frequency",
                subtitle=f"Reports created over the last {time_range}",
                x_axis_label="Date",
                y_axis_label="Number of Reports",
                chart_type="line",
                time_range=time_range
            )
            
            result = VisualizationData(
                config=config,
                series=series,
                metadata={
                    "total_reports": sum(point.y for point in data_points),
                    "avg_per_day": sum(point.y for point in data_points) / len(data_points) if data_points else 0,
                    "peak_day": max(data_points, key=lambda p: p.y).x if data_points else None
                }
            )
            
            # Cache successful response
            fallback_service.cache_response(cache_key, result.model_dump())
            
            return result
            
        except CircuitBreakerError:
            # Try cached response
            logger.warning(f"Circuit breaker open for analytics, trying cache")
            cached_response = await fallback_service.cached_response_fallback(cache_key)
            if cached_response:
                return VisualizationData(**cached_response)
            
            # Return minimal fallback data
            return self._create_fallback_frequency_chart(time_range)
            
        except Exception as e:
            logger.error(f"Error generating creation frequency chart: {str(e)}")
            
            # Try cached response first
            cached_response = await fallback_service.cached_response_fallback(cache_key)
            if cached_response:
                return VisualizationData(**cached_response)
                
            # Return minimal fallback data
            return self._create_fallback_frequency_chart(time_range)
    
    async def generate_topic_distribution_chart(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> VisualizationData:
        """
        Generate chart data for topic distribution.
        
        Args:
            user_id: User ID
            limit: Maximum number of topics to show
            
        Returns:
            Visualization data for topic distribution chart
        """
        try:
            # Get topic analysis data
            topics = await self.usage_service.analyze_topics(user_id, limit)
            
            # Convert to chart data points
            data_points = []
            colors = self._generate_colors(len(topics))
            
            for i, topic in enumerate(topics):
                data_points.append(ChartDataPoint(
                    x=topic.topic,
                    y=topic.count,
                    label=f"{topic.topic}: {topic.count} ({topic.percentage}%)",
                    color=colors[i]
                ))
            
            # Create chart series
            series = [ChartSeries(
                name="Topic Distribution",
                data=data_points,
                type="pie",
                color=None  # Individual colors set on data points
            )]
            
            # Create chart configuration
            config = ChartConfig(
                title="Topic Distribution",
                subtitle="Most researched topics in your reports",
                x_axis_label="Topics",
                y_axis_label="Number of Reports",
                chart_type="pie",
                time_range="all"
            )
            
            return VisualizationData(
                config=config,
                series=series,
                metadata={
                    "total_topics": len(topics),
                    "top_topic": topics[0].topic if topics else None,
                    "topic_diversity": len(topics) / max(sum(t.count for t in topics), 1) if topics else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating topic distribution chart: {str(e)}")
            raise
    
    async def generate_industry_distribution_chart(
        self, 
        user_id: str, 
        limit: int = 8
    ) -> VisualizationData:
        """
        Generate chart data for industry distribution.
        
        Args:
            user_id: User ID
            limit: Maximum number of industries to show
            
        Returns:
            Visualization data for industry distribution chart
        """
        try:
            # Get industry analysis data
            industries = await self.usage_service.analyze_industries(user_id, limit)
            
            # Convert to chart data points
            data_points = []
            colors = self._generate_colors(len(industries))
            
            for i, industry in enumerate(industries):
                data_points.append(ChartDataPoint(
                    x=industry.industry,
                    y=industry.count,
                    label=f"{industry.industry}: {industry.count} reports ({industry.percentage}%)",
                    color=colors[i]
                ))
            
            # Create chart series
            series = [ChartSeries(
                name="Industry Distribution",
                data=data_points,
                type="bar",
                color="#10B981"
            )]
            
            # Create chart configuration
            config = ChartConfig(
                title="Industry Distribution",
                subtitle="Industries you've researched most",
                x_axis_label="Industries",
                y_axis_label="Number of Reports",
                chart_type="bar",
                time_range="all"
            )
            
            return VisualizationData(
                config=config,
                series=series,
                metadata={
                    "total_industries": len(industries),
                    "top_industry": industries[0].industry if industries else None,
                    "industry_focus": industries[0].percentage if industries else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating industry distribution chart: {str(e)}")
            raise
    
    async def generate_trend_analysis_chart(
        self, 
        user_id: str, 
        time_range: str = "quarter"
    ) -> VisualizationData:
        """
        Generate chart data for trend analysis.
        
        Args:
            user_id: User ID
            time_range: Time range for trend analysis
            
        Returns:
            Visualization data for trend analysis chart
        """
        try:
            # Get recurring topics with trend data
            days_map = {"week": 7, "month": 30, "quarter": 90, "year": 365}
            days = days_map.get(time_range, 90)
            
            recurring_topics = await self.trend_service.detect_recurring_topics(user_id, days)
            
            # Filter for topics with clear trends
            trending_topics = [t for t in recurring_topics if t.trend_strength > 0.6]
            
            # Create data points for each trending topic
            series_list = []
            colors = self._generate_colors(len(trending_topics))
            
            for i, topic in enumerate(trending_topics[:5]):  # Limit to top 5 for readability
                # Create trend line data (simplified)
                data_points = []
                for j, period in enumerate(topic.time_periods):
                    # Simulate trend data based on trend direction
                    base_value = topic.occurrences / len(topic.time_periods)
                    if topic.trend_direction == "increasing":
                        value = base_value * (1 + j * 0.2)
                    elif topic.trend_direction == "decreasing":
                        value = base_value * (1 - j * 0.1)
                    else:
                        value = base_value
                    
                    data_points.append(ChartDataPoint(
                        x=period,
                        y=round(value, 1),
                        label=f"{topic.topic}: {value:.1f}"
                    ))
                
                series_list.append(ChartSeries(
                    name=topic.topic.title(),
                    data=data_points,
                    type="line",
                    color=colors[i]
                ))
            
            # Create chart configuration
            config = ChartConfig(
                title="Topic Trends",
                subtitle=f"Trending topics over the last {time_range}",
                x_axis_label="Time Period",
                y_axis_label="Topic Frequency",
                chart_type="line",
                time_range=time_range
            )
            
            return VisualizationData(
                config=config,
                series=series_list,
                metadata={
                    "trending_topics_count": len(trending_topics),
                    "strongest_trend": max(trending_topics, key=lambda t: t.trend_strength).topic if trending_topics else None,
                    "trend_directions": {
                        "increasing": len([t for t in trending_topics if t.trend_direction == "increasing"]),
                        "decreasing": len([t for t in trending_topics if t.trend_direction == "decreasing"]),
                        "stable": len([t for t in trending_topics if t.trend_direction == "stable"])
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating trend analysis chart: {str(e)}")
            raise
    
    async def generate_dashboard_data(
        self, 
        user_id: str, 
        time_range: str = "month"
    ) -> DashboardData:
        """
        Generate complete dashboard visualization data.
        
        Args:
            user_id: User ID
            time_range: Time range for time-based charts
            
        Returns:
            Complete dashboard data
        """
        try:
            # Generate all chart data
            creation_chart = await self.generate_creation_frequency_chart(user_id, time_range)
            topic_chart = await self.generate_topic_distribution_chart(user_id)
            industry_chart = await self.generate_industry_distribution_chart(user_id)
            trend_chart = await self.generate_trend_analysis_chart(user_id, time_range)
            
            # Generate summary metrics
            usage_insights = await self.usage_service.generate_usage_insights(user_id)
            
            summary_metrics = {
                "total_reports": usage_insights.total_reports,
                "reports_this_period": getattr(usage_insights, f"reports_this_{time_range.replace('quarter', 'month')}", usage_insights.reports_this_month),
                "avg_reports_per_day": usage_insights.avg_reports_per_day,
                "most_active_day": usage_insights.most_active_day,
                "top_topic": usage_insights.top_topics[0].topic if usage_insights.top_topics else "No data",
                "top_industry": usage_insights.top_industries[0].industry if usage_insights.top_industries else "No data",
                "research_diversity": len(usage_insights.top_topics),
                "time_range": time_range
            }
            
            return DashboardData(
                creation_frequency_chart=creation_chart,
                topic_distribution_chart=topic_chart,
                industry_distribution_chart=industry_chart,
                trend_analysis_chart=trend_chart,
                summary_metrics=summary_metrics
            )
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {str(e)}")
            raise
    
    def format_chart_data_for_frontend(
        self, 
        visualization_data: VisualizationData, 
        chart_library: str = "chartjs"
    ) -> Dict[str, Any]:
        """
        Format chart data for specific frontend chart libraries.
        
        Args:
            visualization_data: Visualization data to format
            chart_library: Target chart library (chartjs, recharts, d3)
            
        Returns:
            Formatted chart data for the specified library
        """
        try:
            if chart_library == "chartjs":
                return self._format_for_chartjs(visualization_data)
            elif chart_library == "recharts":
                return self._format_for_recharts(visualization_data)
            elif chart_library == "d3":
                return self._format_for_d3(visualization_data)
            else:
                # Return generic format
                return visualization_data.model_dump()
                
        except Exception as e:
            logger.error(f"Error formatting chart data: {str(e)}")
            raise
    
    def _format_for_chartjs(self, viz_data: VisualizationData) -> Dict[str, Any]:
        """Format data for Chart.js library."""
        config = viz_data.config
        
        if config.chart_type == "pie":
            # Pie chart format
            series = viz_data.series[0]
            return {
                "type": "pie",
                "data": {
                    "labels": [point.x for point in series.data],
                    "datasets": [{
                        "data": [point.y for point in series.data],
                        "backgroundColor": [point.color for point in series.data],
                        "label": series.name
                    }]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": config.title
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            }
        else:
            # Line/Bar chart format
            datasets = []
            for series in viz_data.series:
                datasets.append({
                    "label": series.name,
                    "data": [point.y for point in series.data],
                    "backgroundColor": series.color,
                    "borderColor": series.color,
                    "type": series.type
                })
            
            return {
                "type": config.chart_type,
                "data": {
                    "labels": [point.x for point in viz_data.series[0].data],
                    "datasets": datasets
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": config.title
                        }
                    },
                    "scales": {
                        "x": {
                            "title": {
                                "display": True,
                                "text": config.x_axis_label
                            }
                        },
                        "y": {
                            "title": {
                                "display": True,
                                "text": config.y_axis_label
                            }
                        }
                    }
                }
            }
    
    def _format_for_recharts(self, viz_data: VisualizationData) -> Dict[str, Any]:
        """Format data for Recharts library."""
        config = viz_data.config
        
        # Convert data to Recharts format
        data = []
        if config.chart_type == "pie":
            series = viz_data.series[0]
            for point in series.data:
                data.append({
                    "name": point.x,
                    "value": point.y,
                    "fill": point.color
                })
        else:
            # Combine all series data
            combined_data = defaultdict(dict)
            for series in viz_data.series:
                for point in series.data:
                    combined_data[point.x][series.name] = point.y
            
            data = [{"name": k, **v} for k, v in combined_data.items()]
        
        return {
            "type": config.chart_type,
            "data": data,
            "config": {
                "title": config.title,
                "xAxisLabel": config.x_axis_label,
                "yAxisLabel": config.y_axis_label
            }
        }
    
    def _format_for_d3(self, viz_data: VisualizationData) -> Dict[str, Any]:
        """Format data for D3.js library."""
        return {
            "type": viz_data.config.chart_type,
            "title": viz_data.config.title,
            "data": [
                {
                    "series": series.name,
                    "values": [{"x": p.x, "y": p.y, "label": p.label, "color": p.color} for p in series.data]
                }
                for series in viz_data.series
            ],
            "axes": {
                "x": viz_data.config.x_axis_label,
                "y": viz_data.config.y_axis_label
            }
        }
    
    def _generate_colors(self, count: int) -> List[str]:
        """Generate a list of colors for chart data."""
        base_colors = [
            "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
            "#06B6D4", "#84CC16", "#F97316", "#EC4899", "#6366F1"
        ]
        
        # Repeat colors if we need more than the base set
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        
        return colors
    
    def _create_fallback_frequency_chart(self, time_range: str) -> VisualizationData:
        """Create fallback frequency chart with minimal data."""
        config = ChartConfig(
            title="Report Creation Frequency",
            subtitle=f"Data temporarily unavailable",
            x_axis_label="Date",
            y_axis_label="Number of Reports",
            chart_type="line",
            time_range=time_range
        )
        
        # Create minimal data point
        data_points = [ChartDataPoint(
            x=datetime.now().strftime("%Y-%m-%d"),
            y=0,
            label="No data available"
        )]
        
        series = [ChartSeries(
            name="Reports Created",
            data=data_points,
            type="line",
            color="#3B82F6"
        )]
        
        return VisualizationData(
            config=config,
            series=series,
            metadata={
                "total_reports": 0,
                "avg_per_day": 0,
                "peak_day": None,
                "fallback_mode": True
            }
        )
    
    def _create_fallback_topic_chart(self) -> VisualizationData:
        """Create fallback topic distribution chart."""
        config = ChartConfig(
            title="Topic Distribution",
            subtitle="Data temporarily unavailable",
            x_axis_label="Topics",
            y_axis_label="Number of Reports",
            chart_type="pie",
            time_range="all"
        )
        
        data_points = [ChartDataPoint(
            x="No Data",
            y=1,
            label="Data unavailable",
            color="#E5E7EB"
        )]
        
        series = [ChartSeries(
            name="Topic Distribution",
            data=data_points,
            type="pie"
        )]
        
        return VisualizationData(
            config=config,
            series=series,
            metadata={
                "total_topics": 0,
                "top_topic": None,
                "topic_diversity": 0,
                "fallback_mode": True
            }
        )


# Global service instance
report_analytics_visualization_service = ReportAnalyticsVisualizationService()