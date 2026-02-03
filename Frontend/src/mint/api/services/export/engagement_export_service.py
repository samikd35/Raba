"""
Engagement Analytics Export Service

This service provides comprehensive export functionality for user engagement data,
including PDF reports with visualizations, CSV exports, and automated email delivery.
"""

import logging
import io
import csv
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta, date
from pathlib import Path
import base64

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not available - PDF export will be disabled")

# Chart generation imports
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib not available - chart generation will be disabled")

# Try to import engagement_service, but use mock if it fails
try:
    from ..user.engagement import engagement_service
except ImportError:
    print("Using mock engagement service for testing")
    from ...system.core.mock_services import mock_engagement_service
    engagement_service = mock_engagement_service
from ..communication.email_service import email_service
from ....schemas.schemas import (
    EngagementExportRequest,
    EngagementExportFormat,
    EngagementExportResult
)
# Type aliases for ReportLab components
from typing import Any
ReportLabTable = Any
ReportLabImage = Any

logger = logging.getLogger(__name__)


class EngagementExportService:
    """Service for exporting engagement analytics data in various formats."""
    
    def __init__(self):
        self.engagement_service = engagement_service
        self.email_service = email_service
        
    async def export_engagement_data(
        self,
        export_request: EngagementExportRequest
    ) -> EngagementExportResult:
        """
        Export engagement data in the specified format.
        
        Args:
            export_request: Export configuration and parameters
            
        Returns:
            Export result with file data or download URL
        """
        try:
            logger.info(f"Starting engagement data export: {export_request.format.value}")
            
            # Fetch the engagement data
            data = await self._fetch_engagement_data(export_request)
            
            # Generate export based on format
            if export_request.format == EngagementExportFormat.CSV:
                result = await self._export_csv(data, export_request)
            elif export_request.format == EngagementExportFormat.JSON:
                result = await self._export_json(data, export_request)
            elif export_request.format == EngagementExportFormat.PDF:
                result = await self._export_pdf(data, export_request)
            elif export_request.format == EngagementExportFormat.EXCEL:
                result = await self._export_excel(data, export_request)
            else:
                raise ValueError(f"Unsupported export format: {export_request.format}")
            
            # Send email if requested
            if export_request.email_delivery and export_request.email_recipients:
                await self._send_export_email(result, export_request)
            
            logger.info(f"Successfully exported engagement data: {export_request.format.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error exporting engagement data: {str(e)}")
            raise
    
    async def _fetch_engagement_data(
        self,
        export_request: EngagementExportRequest
    ) -> Dict[str, Any]:
        """Fetch all required engagement data for export."""
        try:
            data = {}
            
            # Get overview metrics
            overview = await self.engagement_service.get_engagement_overview(
                start_date=export_request.start_date,
                end_date=export_request.end_date
            )
            data['overview'] = overview.dict()
            
            # Get trends data
            trends = await self.engagement_service.get_engagement_trends(
                start_date=export_request.start_date,
                end_date=export_request.end_date,
                interval="1 day"
            )
            data['trends'] = [trend.dict() for trend in trends]
            
            # Get daily metrics
            daily_metrics = await self.engagement_service.get_daily_metrics(
                start_date=export_request.start_date,
                end_date=export_request.end_date,
                limit=365
            )
            data['daily_metrics'] = [metric.dict() for metric in daily_metrics]
            
            # Get session analytics if requested
            if export_request.include_sessions:
                sessions = await self.engagement_service.get_user_session_analytics(
                    start_date=datetime.combine(export_request.start_date, datetime.min.time()),
                    end_date=datetime.combine(export_request.end_date, datetime.max.time()),
                    limit=1000
                )
                data['sessions'] = [session.dict() for session in sessions]
            
            # Get event data if requested
            if export_request.include_events:
                # This would require a method to get all events in date range
                # For now, we'll include a summary
                data['events_summary'] = {
                    'note': 'Individual event data available on request',
                    'total_events': 'See daily metrics for aggregated counts'
                }
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching engagement data: {str(e)}")
            raise
    
    async def _export_csv(
        self,
        data: Dict[str, Any],
        export_request: EngagementExportRequest
    ) -> EngagementExportResult:
        """Export engagement data as CSV."""
        try:
            output = io.StringIO()
            
            # Create multiple CSV sections
            sections = []
            
            # Overview metrics
            if 'overview' in data:
                sections.append(self._create_overview_csv_section(data['overview']))
            
            # Daily metrics
            if 'daily_metrics' in data:
                sections.append(self._create_daily_metrics_csv_section(data['daily_metrics']))
            
            # Trends data
            if 'trends' in data:
                sections.append(self._create_trends_csv_section(data['trends']))
            
            # Session data
            if 'sessions' in data and export_request.include_sessions:
                sections.append(self._create_sessions_csv_section(data['sessions']))
            
            # Combine all sections
            csv_content = '\n\n'.join(sections)
            
            return EngagementExportResult(
                format=EngagementExportFormat.CSV,
                filename=f"engagement_export_{export_request.start_date}_{export_request.end_date}.csv",
                content=csv_content.encode('utf-8'),
                content_type='text/csv',
                size=len(csv_content.encode('utf-8')),
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating CSV export: {str(e)}")
            raise
    
    def _create_overview_csv_section(self, overview: Dict[str, Any]) -> str:
        """Create CSV section for overview metrics."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['ENGAGEMENT OVERVIEW METRICS'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Users', overview.get('total_users', 0)])
        writer.writerow(['Active Users', overview.get('active_users', 0)])
        writer.writerow(['New Users', overview.get('new_users', 0)])
        writer.writerow(['Total Sessions', overview.get('total_sessions', 0)])
        writer.writerow(['Avg Session Duration (minutes)', overview.get('avg_session_duration', 0)])
        writer.writerow(['Total Page Views', overview.get('total_page_views', 0)])
        writer.writerow(['Avg Pages Per Session', overview.get('avg_pages_per_session', 0)])
        writer.writerow(['Total Clicks', overview.get('total_clicks', 0)])
        writer.writerow(['Total Reports Generated', overview.get('total_reports_generated', 0)])
        writer.writerow(['Total Links Clicked', overview.get('total_links_clicked', 0)])
        writer.writerow(['Avg Engagement Score', overview.get('avg_engagement_score', 0)])
        writer.writerow(['Bounce Rate (%)', overview.get('bounce_rate', 0)])
        
        return output.getvalue()
    
    def _create_daily_metrics_csv_section(self, daily_metrics: List[Dict[str, Any]]) -> str:
        """Create CSV section for daily metrics."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['DAILY ENGAGEMENT METRICS'])
        writer.writerow([
            'Date', 'Total Users', 'Active Users', 'New Users', 'Returning Users',
            'Total Sessions', 'Total Page Views', 'Total Clicks', 'Reports Generated',
            'Links Clicked', 'Avg Session Duration', 'Avg Pages Per Session',
            'Avg Clicks Per Session', 'Bounce Rate', 'Avg Engagement Score'
        ])
        
        for metric in daily_metrics:
            writer.writerow([
                metric.get('date', ''),
                metric.get('total_users', 0),
                metric.get('active_users', 0),
                metric.get('new_users', 0),
                metric.get('returning_users', 0),
                metric.get('total_sessions', 0),
                metric.get('total_page_views', 0),
                metric.get('total_clicks', 0),
                metric.get('total_reports_generated', 0),
                metric.get('total_links_clicked', 0),
                metric.get('avg_session_duration', 0),
                metric.get('avg_pages_per_session', 0),
                metric.get('avg_clicks_per_session', 0),
                metric.get('bounce_rate', 0),
                metric.get('avg_engagement_score', 0)
            ])
        
        return output.getvalue()
    
    def _create_trends_csv_section(self, trends: List[Dict[str, Any]]) -> str:
        """Create CSV section for trends data."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['ENGAGEMENT TRENDS'])
        writer.writerow([
            'Time Bucket', 'Active Users', 'Total Sessions', 'Avg Session Duration',
            'Total Page Views', 'Total Clicks', 'Total Reports', 'Avg Engagement Score'
        ])
        
        for trend in trends:
            writer.writerow([
                trend.get('time_bucket', ''),
                trend.get('active_users', 0),
                trend.get('total_sessions', 0),
                trend.get('avg_session_duration', 0),
                trend.get('total_page_views', 0),
                trend.get('total_clicks', 0),
                trend.get('total_reports', 0),
                trend.get('avg_engagement_score', 0)
            ])
        
        return output.getvalue()
    
    def _create_sessions_csv_section(self, sessions: List[Dict[str, Any]]) -> str:
        """Create CSV section for session data."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['SESSION ANALYTICS'])
        writer.writerow([
            'Session ID', 'User ID', 'Session Start', 'Session End', 'Duration (minutes)',
            'Page Views', 'Unique Pages', 'Clicks', 'Scrolls', 'Reports Generated',
            'Links Clicked', 'Downloads', 'Bounce Rate', 'Engagement Score',
            'Entry Page', 'Exit Page', 'Device Type', 'Browser', 'OS'
        ])
        
        for session in sessions:
            writer.writerow([
                session.get('session_id', ''),
                session.get('user_id', ''),
                session.get('session_start', ''),
                session.get('session_end', ''),
                session.get('duration_minutes', 0),
                session.get('page_views', 0),
                session.get('unique_pages', 0),
                session.get('clicks_count', 0),
                session.get('scrolls_count', 0),
                session.get('reports_generated', 0),
                session.get('links_clicked', 0),
                session.get('downloads_count', 0),
                session.get('bounce_rate', 0),
                session.get('engagement_score', 0),
                session.get('entry_page', ''),
                session.get('exit_page', ''),
                session.get('device_type', ''),
                session.get('browser', ''),
                session.get('os', '')
            ])
        
        return output.getvalue()
    
    async def _export_json(
        self,
        data: Dict[str, Any],
        export_request: EngagementExportRequest
    ) -> EngagementExportResult:
        """Export engagement data as JSON."""
        try:
            # Add metadata to the export
            export_data = {
                'metadata': {
                    'export_date': datetime.utcnow().isoformat(),
                    'date_range': {
                        'start_date': export_request.start_date.isoformat(),
                        'end_date': export_request.end_date.isoformat()
                    },
                    'export_format': export_request.format.value,
                    'includes_sessions': export_request.include_sessions,
                    'includes_events': export_request.include_events
                },
                'data': data
            }
            
            json_content = json.dumps(export_data, indent=2, default=str)
            
            return EngagementExportResult(
                format=EngagementExportFormat.JSON,
                filename=f"engagement_export_{export_request.start_date}_{export_request.end_date}.json",
                content=json_content.encode('utf-8'),
                content_type='application/json',
                size=len(json_content.encode('utf-8')),
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating JSON export: {str(e)}")
            raise
    
    async def _export_pdf(
        self,
        data: Dict[str, Any],
        export_request: EngagementExportRequest
    ) -> EngagementExportResult:
        """Export engagement data as PDF with visualizations."""
        if not REPORTLAB_AVAILABLE:
            raise Exception("PDF export not available - ReportLab not installed")
        
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=HexColor('#2c3e50')
            )
            story.append(Paragraph("Engagement Analytics Report", title_style))
            story.append(Spacer(1, 20))
            
            # Report metadata
            metadata_style = styles['Normal']
            story.append(Paragraph(f"<b>Report Period:</b> {export_request.start_date} to {export_request.end_date}", metadata_style))
            story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", metadata_style))
            story.append(Spacer(1, 20))
            
            # Overview metrics table
            if 'overview' in data:
                story.append(Paragraph("Overview Metrics", styles['Heading2']))
                overview_table = self._create_overview_pdf_table(data['overview'])
                story.append(overview_table)
                story.append(Spacer(1, 20))
            
            # Charts (if matplotlib is available)
            if MATPLOTLIB_AVAILABLE and 'trends' in data:
                chart_images = await self._generate_charts(data)
                for chart_image in chart_images:
                    story.append(chart_image)
                    story.append(Spacer(1, 20))
            
            # Daily metrics summary
            if 'daily_metrics' in data and data['daily_metrics']:
                story.append(Paragraph("Daily Metrics Summary", styles['Heading2']))
                daily_table = self._create_daily_metrics_pdf_table(data['daily_metrics'][:10])  # Last 10 days
                story.append(daily_table)
                story.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return EngagementExportResult(
                format=EngagementExportFormat.PDF,
                filename=f"engagement_report_{export_request.start_date}_{export_request.end_date}.pdf",
                content=pdf_content,
                content_type='application/pdf',
                size=len(pdf_content),
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating PDF export: {str(e)}")
            raise
    
    def _create_overview_pdf_table(self, overview: Dict[str, Any]) -> ReportLabTable:
        """Create PDF table for overview metrics."""
        data = [
            ['Metric', 'Value'],
            ['Total Users', f"{overview.get('total_users', 0):,}"],
            ['Active Users', f"{overview.get('active_users', 0):,}"],
            ['New Users', f"{overview.get('new_users', 0):,}"],
            ['Total Sessions', f"{overview.get('total_sessions', 0):,}"],
            ['Avg Session Duration', f"{overview.get('avg_session_duration', 0):.1f} minutes"],
            ['Total Page Views', f"{overview.get('total_page_views', 0):,}"],
            ['Avg Pages Per Session', f"{overview.get('avg_pages_per_session', 0):.1f}"],
            ['Total Clicks', f"{overview.get('total_clicks', 0):,}"],
            ['Total Reports Generated', f"{overview.get('total_reports_generated', 0):,}"],
            ['Total Links Clicked', f"{overview.get('total_links_clicked', 0):,}"],
            ['Avg Engagement Score', f"{overview.get('avg_engagement_score', 0):.2f}"],
            ['Bounce Rate', f"{overview.get('bounce_rate', 0):.1f}%"]
        ]
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    def _create_daily_metrics_pdf_table(self, daily_metrics: List[Dict[str, Any]]) -> ReportLabTable:
        """Create PDF table for daily metrics."""
        data = [['Date', 'Active Users', 'Sessions', 'Page Views', 'Reports', 'Engagement Score']]
        
        for metric in daily_metrics:
            data.append([
                str(metric.get('date', '')),
                f"{metric.get('active_users', 0):,}",
                f"{metric.get('total_sessions', 0):,}",
                f"{metric.get('total_page_views', 0):,}",
                f"{metric.get('total_reports_generated', 0):,}",
                f"{metric.get('avg_engagement_score', 0):.2f}"
            ])
        
        table = Table(data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    async def _generate_charts(self, data: Dict[str, Any]) -> List[ReportLabImage]:
        """Generate chart images for PDF."""
        if not MATPLOTLIB_AVAILABLE:
            return []
        
        charts = []
        
        try:
            # Set style
            plt.style.use('seaborn-v0_8')
            
            # Trends chart
            if 'trends' in data and data['trends']:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                dates = [datetime.fromisoformat(str(trend['time_bucket'])) for trend in data['trends']]
                active_users = [trend['active_users'] for trend in data['trends']]
                sessions = [trend['total_sessions'] for trend in data['trends']]
                
                ax.plot(dates, active_users, label='Active Users', marker='o')
                ax.plot(dates, sessions, label='Total Sessions', marker='s')
                
                ax.set_title('Engagement Trends Over Time')
                ax.set_xlabel('Date')
                ax.set_ylabel('Count')
                ax.legend()
                ax.grid(True, alpha=0.3)
                
                # Format dates
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
                plt.xticks(rotation=45)
                
                plt.tight_layout()
                
                # Save to buffer
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                buffer.seek(0)
                
                # Create ReportLab Image
                chart_image = Image(buffer, width=6*inch, height=3.6*inch)
                charts.append(chart_image)
                
                plt.close()
            
        except Exception as e:
            logger.error(f"Error generating charts: {str(e)}")
        
        return charts
    
    async def _export_excel(
        self,
        data: Dict[str, Any],
        export_request: EngagementExportRequest
    ) -> EngagementExportResult:
        """Export engagement data as Excel file."""
        try:
            if not OPENPYXL_AVAILABLE:
                # Fallback to CSV format
                logger.warning("Excel export not available - falling back to CSV")
                csv_result = await self._export_csv(data, export_request)
                return EngagementExportResult(
                    format=EngagementExportFormat.EXCEL,
                    filename=f"engagement_export_{export_request.start_date}_{export_request.end_date}.xlsx",
                    content=csv_result.content,
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    size=csv_result.size,
                    generated_at=datetime.utcnow()
                )
            
            # Create workbook with multiple sheets
            wb = openpyxl.Workbook()
            
            # Overview sheet
            overview_sheet = wb.active
            overview_sheet.title = "Engagement Overview"
            self._create_overview_excel_sheet(overview_sheet, data)
            
            # Daily metrics sheet
            if 'daily_metrics' in data and data['daily_metrics']:
                daily_sheet = wb.create_sheet("Daily Metrics")
                self._create_daily_metrics_excel_sheet(daily_sheet, data)
            
            # Trends sheet
            if 'trends' in data and data['trends']:
                trends_sheet = wb.create_sheet("Engagement Trends")
                self._create_trends_excel_sheet(trends_sheet, data)
            
            # Sessions sheet (if requested)
            if 'sessions' in data and data['sessions'] and export_request.include_sessions:
                sessions_sheet = wb.create_sheet("Session Analytics")
                self._create_sessions_excel_sheet(sessions_sheet, data)
            
            # Save to buffer
            buffer = io.BytesIO()
            wb.save(buffer)
            excel_content = buffer.getvalue()
            buffer.close()
            
            return EngagementExportResult(
                format=EngagementExportFormat.EXCEL,
                filename=f"engagement_export_{export_request.start_date}_{export_request.end_date}.xlsx",
                content=excel_content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                size=len(excel_content),
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating Excel export: {str(e)}")
            raise
    
    def _create_overview_excel_sheet(self, sheet, data: Dict[str, Any]):
        """Create Excel sheet for engagement overview data."""
        # Title
        sheet.cell(row=1, column=1, value="ENGAGEMENT OVERVIEW METRICS").font = Font(bold=True, size=14)
        
        # Overview metrics
        overview = data.get('overview', {})
        if overview:
            sheet.cell(row=3, column=1, value="Metric").font = Font(bold=True)
            sheet.cell(row=3, column=2, value="Value").font = Font(bold=True)
            
            # Apply header styling
            for col in range(1, 3):
                cell = sheet.cell(row=3, column=col)
                cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
            
            # Add metrics
            metrics = [
                ('Total Users', overview.get('total_users', 0)),
                ('Active Users', overview.get('active_users', 0)),
                ('New Users', overview.get('new_users', 0)),
                ('Total Sessions', overview.get('total_sessions', 0)),
                ('Avg Session Duration (minutes)', overview.get('avg_session_duration', 0)),
                ('Total Page Views', overview.get('total_page_views', 0)),
                ('Avg Pages Per Session', overview.get('avg_pages_per_session', 0)),
                ('Total Clicks', overview.get('total_clicks', 0)),
                ('Total Reports Generated', overview.get('total_reports_generated', 0)),
                ('Total Links Clicked', overview.get('total_links_clicked', 0)),
                ('Avg Engagement Score', overview.get('avg_engagement_score', 0)),
                ('Bounce Rate (%)', overview.get('bounce_rate', 0))
            ]
            
            for i, (metric, value) in enumerate(metrics, 4):
                sheet.cell(row=i, column=1, value=metric)
                sheet.cell(row=i, column=2, value=value)
                
                # Apply alternating row colors
                if i % 2 == 0:
                    for col in range(1, 3):
                        sheet.cell(row=i, column=col).fill = PatternFill(
                            start_color="F5F5F5", end_color="F5F5F5", fill_type="solid"
                        )
    
    def _create_daily_metrics_excel_sheet(self, sheet, data: Dict[str, Any]):
        """Create Excel sheet for daily metrics data."""
        # Title
        sheet.cell(row=1, column=1, value="DAILY ENGAGEMENT METRICS").font = Font(bold=True, size=14)
        
        # Headers
        headers = [
            'Date', 'Total Users', 'Active Users', 'New Users', 'Returning Users',
            'Total Sessions', 'Total Page Views', 'Total Clicks', 'Reports Generated',
            'Links Clicked', 'Avg Session Duration', 'Avg Pages Per Session',
            'Avg Clicks Per Session', 'Bounce Rate', 'Avg Engagement Score'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data rows
        daily_metrics = data.get('daily_metrics', [])
        for i, metric in enumerate(daily_metrics, 4):
            sheet.cell(row=i, column=1, value=metric.get('date', ''))
            sheet.cell(row=i, column=2, value=metric.get('total_users', 0))
            sheet.cell(row=i, column=3, value=metric.get('active_users', 0))
            sheet.cell(row=i, column=4, value=metric.get('new_users', 0))
            sheet.cell(row=i, column=5, value=metric.get('returning_users', 0))
            sheet.cell(row=i, column=6, value=metric.get('total_sessions', 0))
            sheet.cell(row=i, column=7, value=metric.get('total_page_views', 0))
            sheet.cell(row=i, column=8, value=metric.get('total_clicks', 0))
            sheet.cell(row=i, column=9, value=metric.get('total_reports_generated', 0))
            sheet.cell(row=i, column=10, value=metric.get('total_links_clicked', 0))
            sheet.cell(row=i, column=11, value=metric.get('avg_session_duration', 0))
            sheet.cell(row=i, column=12, value=metric.get('avg_pages_per_session', 0))
            sheet.cell(row=i, column=13, value=metric.get('avg_clicks_per_session', 0))
            sheet.cell(row=i, column=14, value=metric.get('bounce_rate', 0))
            sheet.cell(row=i, column=15, value=metric.get('avg_engagement_score', 0))
            
            # Apply alternating row colors
            if i % 2 == 0:
                for col in range(1, 16):
                    sheet.cell(row=i, column=col).fill = PatternFill(
                        start_color="F5F5F5", end_color="F5F5F5", fill_type="solid"
                    )
    
    def _create_trends_excel_sheet(self, sheet, data: Dict[str, Any]):
        """Create Excel sheet for trends data."""
        # Title
        sheet.cell(row=1, column=1, value="ENGAGEMENT TRENDS").font = Font(bold=True, size=14)
        
        # Headers
        headers = [
            'Time Bucket', 'Active Users', 'Total Sessions', 'Avg Session Duration',
            'Total Page Views', 'Total Clicks', 'Total Reports', 'Avg Engagement Score'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data rows
        trends = data.get('trends', [])
        for i, trend in enumerate(trends, 4):
            sheet.cell(row=i, column=1, value=trend.get('time_bucket', ''))
            sheet.cell(row=i, column=2, value=trend.get('active_users', 0))
            sheet.cell(row=i, column=3, value=trend.get('total_sessions', 0))
            sheet.cell(row=i, column=4, value=trend.get('avg_session_duration', 0))
            sheet.cell(row=i, column=5, value=trend.get('total_page_views', 0))
            sheet.cell(row=i, column=6, value=trend.get('total_clicks', 0))
            sheet.cell(row=i, column=7, value=trend.get('total_reports', 0))
            sheet.cell(row=i, column=8, value=trend.get('avg_engagement_score', 0))
            
            # Apply alternating row colors
            if i % 2 == 0:
                for col in range(1, 9):
                    sheet.cell(row=i, column=col).fill = PatternFill(
                        start_color="F5F5F5", end_color="F5F5F5", fill_type="solid"
                    )
        
        # Add chart if data exists
        if trends and len(trends) > 1:
            chart_sheet = sheet.parent.create_sheet("Engagement Charts")
            self._create_engagement_charts(chart_sheet, data)
    
    def _create_sessions_excel_sheet(self, sheet, data: Dict[str, Any]):
        """Create Excel sheet for session data."""
        # Title
        sheet.cell(row=1, column=1, value="SESSION ANALYTICS").font = Font(bold=True, size=14)
        
        # Headers
        headers = [
            'Session ID', 'User ID', 'Session Start', 'Session End', 'Duration (min)',
            'Page Views', 'Unique Pages', 'Clicks', 'Scrolls', 'Reports Generated',
            'Links Clicked', 'Downloads', 'Bounce Rate', 'Engagement Score',
            'Entry Page', 'Exit Page', 'Device Type', 'Browser', 'OS'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Data rows
        sessions = data.get('sessions', [])
        for i, session in enumerate(sessions, 4):
            sheet.cell(row=i, column=1, value=session.get('session_id', ''))
            sheet.cell(row=i, column=2, value=session.get('user_id', ''))
            sheet.cell(row=i, column=3, value=session.get('session_start', ''))
            sheet.cell(row=i, column=4, value=session.get('session_end', ''))
            sheet.cell(row=i, column=5, value=session.get('duration_minutes', 0))
            sheet.cell(row=i, column=6, value=session.get('page_views', 0))
            sheet.cell(row=i, column=7, value=session.get('unique_pages', 0))
            sheet.cell(row=i, column=8, value=session.get('clicks_count', 0))
            sheet.cell(row=i, column=9, value=session.get('scrolls_count', 0))
            sheet.cell(row=i, column=10, value=session.get('reports_generated', 0))
            sheet.cell(row=i, column=11, value=session.get('links_clicked', 0))
            sheet.cell(row=i, column=12, value=session.get('downloads_count', 0))
            sheet.cell(row=i, column=13, value=session.get('bounce_rate', 0))
            sheet.cell(row=i, column=14, value=session.get('engagement_score', 0))
            sheet.cell(row=i, column=15, value=session.get('entry_page', ''))
            sheet.cell(row=i, column=16, value=session.get('exit_page', ''))
            sheet.cell(row=i, column=17, value=session.get('device_type', ''))
            sheet.cell(row=i, column=18, value=session.get('browser', ''))
            sheet.cell(row=i, column=19, value=session.get('os', ''))
            
            # Apply alternating row colors
            if i % 2 == 0:
                for col in range(1, 20):
                    sheet.cell(row=i, column=col).fill = PatternFill(
                        start_color="F5F5F5", end_color="F5F5F5", fill_type="solid"
                    )
    
    def _create_engagement_charts(self, sheet, data: Dict[str, Any]):
        """Create charts for engagement data in Excel."""
        if not OPENPYXL_AVAILABLE:
            return
        
        sheet.cell(row=1, column=1, value="ENGAGEMENT ANALYTICS CHARTS").font = Font(bold=True, size=16)
        
        # User activity chart
        daily_metrics = data.get('daily_metrics', [])
        if daily_metrics:
            sheet.cell(row=3, column=1, value="User Activity Over Time").font = Font(bold=True, size=14)
            
            # Add data for chart
            sheet.cell(row=5, column=1, value="Date")
            sheet.cell(row=5, column=2, value="Active Users")
            sheet.cell(row=5, column=3, value="Total Sessions")
            
            for i, metric in enumerate(daily_metrics, 6):
                sheet.cell(row=i, column=1, value=metric.get('date', ''))
                sheet.cell(row=i, column=2, value=metric.get('active_users', 0))
                sheet.cell(row=i, column=3, value=metric.get('total_sessions', 0))
            
            # Create chart
            chart = LineChart()
            chart.title = "User Activity Over Time"
            chart.style = 2
            chart.x_axis.title = "Date"
            chart.y_axis.title = "Count"
            
            # Add data to chart
            data_length = len(daily_metrics)
            cats = Reference(sheet, min_col=1, min_row=6, max_row=5+data_length)
            data = Reference(sheet, min_col=2, min_row=5, max_col=3, max_row=5+data_length)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            
            # Add chart to sheet
            sheet.add_chart(chart, "A20")
            
            # Engagement score chart
            sheet.cell(row=3, column=5, value="Engagement Metrics").font = Font(bold=True, size=14)
            
            # Add data for chart
            sheet.cell(row=5, column=5, value="Date")
            sheet.cell(row=5, column=6, value="Engagement Score")
            sheet.cell(row=5, column=7, value="Bounce Rate")
            
            for i, metric in enumerate(daily_metrics, 6):
                sheet.cell(row=i, column=5, value=metric.get('date', ''))
                sheet.cell(row=i, column=6, value=metric.get('avg_engagement_score', 0))
                sheet.cell(row=i, column=7, value=metric.get('bounce_rate', 0))
            
            # Create chart
            chart2 = LineChart()
            chart2.title = "Engagement Metrics Over Time"
            chart2.style = 2
            chart2.x_axis.title = "Date"
            chart2.y_axis.title = "Value"
            
            # Add data to chart
            cats = Reference(sheet, min_col=5, min_row=6, max_row=5+data_length)
            data = Reference(sheet, min_col=6, min_row=5, max_col=7, max_row=5+data_length)
            chart2.add_data(data, titles_from_data=True)
            chart2.set_categories(cats)
            
            # Add chart to sheet
            sheet.add_chart(chart2, "G20")
    
    async def _send_export_email(
        self,
        export_result: EngagementExportResult,
        export_request: EngagementExportRequest
    ) -> bool:
        """Send export file via email."""
        try:
            subject = f"Engagement Analytics Export - {export_request.start_date} to {export_request.end_date}"
            
            body = f"""
            Your engagement analytics export is ready.
            
            Report Details:
            - Period: {export_request.start_date} to {export_request.end_date}
            - Format: {export_request.format.value.upper()}
            - Generated: {export_result.generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
            - File Size: {export_result.size:,} bytes
            
            Please find the report attached to this email.
            
            Best regards,
            MINT Analytics Team
            """
            
            # Create attachment
            attachment = {
                'filename': export_result.filename,
                'content': base64.b64encode(export_result.content).decode('utf-8'),
                'content_type': export_result.content_type
            }
            
            # Send email to all recipients
            for recipient in export_request.email_recipients:
                await self.email_service.send_email(
                    to_email=recipient,
                    subject=subject,
                    body=body,
                    attachments=[attachment]
                )
            
            logger.info(f"Export email sent to {len(export_request.email_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending export email: {str(e)}")
            return False
    
    async def schedule_automated_report(
        self,
        export_request: EngagementExportRequest,
        schedule_config: Dict[str, Any]
    ) -> str:
        """
        Schedule automated engagement reports.
        
        Args:
            export_request: Export configuration
            schedule_config: Schedule configuration (frequency, time, etc.)
            
        Returns:
            Schedule ID for managing the scheduled report
        """
        try:
            # Create a unique schedule ID
            schedule_id = f"engagement_schedule_{uuid.uuid4()}"
            
            # Schedule configuration
            schedule = {
                'id': schedule_id,
                'export_request': export_request.dict(),
                'schedule': schedule_config,
                'created_at': datetime.utcnow().isoformat(),
                'last_run': None,
                'next_run': None,
                'run_count': 0,
                'status': 'active'
            }
            
            # Calculate next run time based on frequency
            frequency = schedule_config.get('frequency', 'daily')
            time_of_day = schedule_config.get('time_of_day', '00:00')
            day_of_week = schedule_config.get('day_of_week')
            day_of_month = schedule_config.get('day_of_month')
            
            now = datetime.utcnow()
            next_run = None
            
            if frequency == 'daily':
                hour, minute = map(int, time_of_day.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run = next_run + timedelta(days=1)
            
            elif frequency == 'weekly' and day_of_week:
                # Convert day name to number (0=Monday, 6=Sunday)
                day_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                          'friday': 4, 'saturday': 5, 'sunday': 6}
                target_day = day_map.get(day_of_week.lower(), 0)
                
                hour, minute = map(int, time_of_day.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                days_ahead = target_day - next_run.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                next_run = next_run + timedelta(days=days_ahead)
            
            elif frequency == 'monthly' and day_of_month:
                # Get target day of month (1-31)
                target_day = min(int(day_of_month), 28)  # Cap at 28 to handle February
                
                hour, minute = map(int, time_of_day.split(':'))
                next_run = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)  # Start at 1st of month
                
                if now.day < target_day:
                    # Target day is later this month
                    next_run = next_run.replace(day=target_day)
                else:
                    # Target day already happened this month, go to next month
                    if now.month == 12:
                        next_run = next_run.replace(year=now.year+1, month=1, day=target_day)
                    else:
                        next_run = next_run.replace(month=now.month+1, day=target_day)
            
            if next_run:
                schedule['next_run'] = next_run.isoformat()
            
            # In a real implementation, this would be stored in a database
            # For now, we'll just log it
            logger.info(f"Scheduled automated engagement report: {schedule_id}")
            logger.info(f"Next run scheduled for: {schedule['next_run']}")
            
            return schedule_id
            
        except Exception as e:
            logger.error(f"Error scheduling automated report: {str(e)}")
            raise


# Global export service instance
engagement_export_service = EngagementExportService()