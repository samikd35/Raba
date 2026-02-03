"""
Mock services for testing.

This module provides mock implementations of services to use when
the actual services are not available or have dependency issues.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock

class MockEngagementService:
    """Mock implementation of the engagement service."""
    
    async def get_engagement_overview(self, start_date=None, end_date=None):
        """Return mock engagement overview data."""
        return MagicMock(
            dict=lambda: {
                'total_users': 150,
                'active_users': 85,
                'new_users': 12,
                'total_sessions': 320,
                'avg_session_duration': 15.5,
                'total_page_views': 1250,
                'avg_pages_per_session': 3.9,
                'total_clicks': 890,
                'total_reports_generated': 145,
                'total_links_clicked': 234,
                'avg_engagement_score': 76.8,
                'bounce_rate': 25.3
            }
        )
    
    async def get_engagement_trends(self, start_date=None, end_date=None, interval="1 day"):
        """Return mock engagement trends data."""
        trends = []
        current_date = start_date or (date.today() - timedelta(days=7))
        end = end_date or date.today()
        
        while current_date <= end:
            trends.append(MagicMock(
                dict=lambda: {
                    'time_bucket': current_date.isoformat(),
                    'active_users': 30 + (current_date.day % 10),
                    'total_sessions': 60 + (current_date.day % 15),
                    'avg_session_duration': 12.5 + (current_date.day % 5),
                    'total_page_views': 250 + (current_date.day * 10),
                    'total_clicks': 180 + (current_date.day * 5),
                    'total_reports': 25 + (current_date.day % 8),
                    'avg_engagement_score': 70.0 + (current_date.day % 10)
                }
            ))
            current_date += timedelta(days=1)
        
        return trends
    
    async def get_daily_metrics(self, start_date=None, end_date=None, limit=365):
        """Return mock daily metrics data."""
        metrics = []
        current_date = start_date or (date.today() - timedelta(days=7))
        end = end_date or date.today()
        
        while current_date <= end:
            metrics.append(MagicMock(
                dict=lambda: {
                    'date': current_date.isoformat(),
                    'total_users': 45 + (current_date.day % 10),
                    'active_users': 32 + (current_date.day % 8),
                    'new_users': 3 + (current_date.day % 3),
                    'returning_users': 29 + (current_date.day % 7),
                    'total_sessions': 78 + (current_date.day % 12),
                    'total_page_views': 312 + (current_date.day * 8),
                    'total_clicks': 189 + (current_date.day * 4),
                    'total_reports_generated': 34 + (current_date.day % 6),
                    'total_links_clicked': 56 + (current_date.day % 9),
                    'avg_session_duration': 14.2 + (current_date.day % 4),
                    'avg_pages_per_session': 4.0 + (current_date.day % 2),
                    'avg_clicks_per_session': 2.4 + (current_date.day % 1),
                    'bounce_rate': 25.0 - (current_date.day % 5),
                    'avg_engagement_score': 75.5 + (current_date.day % 8)
                }
            ))
            current_date += timedelta(days=1)
        
        return metrics
    
    async def get_user_session_analytics(self, start_date=None, end_date=None, limit=1000):
        """Return mock session analytics data."""
        sessions = []
        for i in range(10):  # Return 10 mock sessions
            sessions.append(MagicMock(
                dict=lambda: {
                    'session_id': f"session_{i}",
                    'user_id': f"user_{i % 5}",
                    'session_start': datetime.now().isoformat(),
                    'session_end': (datetime.now() + timedelta(minutes=15)).isoformat(),
                    'duration_minutes': 15,
                    'page_views': 8 + (i % 5),
                    'unique_pages': 4 + (i % 3),
                    'clicks_count': 12 + (i % 8),
                    'scrolls_count': 25 + (i % 10),
                    'reports_generated': 2 + (i % 2),
                    'links_clicked': 5 + (i % 3),
                    'downloads_count': 1 + (i % 2),
                    'bounce_rate': 20.0 - (i % 10),
                    'engagement_score': 75.0 + (i % 15),
                    'entry_page': '/dashboard',
                    'exit_page': '/reports',
                    'device_type': 'desktop',
                    'browser': 'Chrome',
                    'os': 'Windows'
                }
            ))
        
        return sessions

# Create mock service instances
mock_engagement_service = MockEngagementService()