"""
User engagement service for admin dashboard.

This service provides comprehensive user engagement tracking and analytics
capabilities, including event tracking, session analytics, and engagement metrics.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from ..api.supabase_client import SupabaseClient
from ..schemas.schemas import (
    UserEngagementEvent,
    UserEngagementEventCreate,
    EngagementEventType,
    EngagementEventCategory,
    UserSessionAnalytics,
    UserSessionAnalyticsUpdate,
    EngagementMetricsDaily,
    EngagementOverview,
    EngagementTrend,
    EngagementQuery
)

logger = logging.getLogger(__name__)


class UserEngagementService:
    """Service for managing user engagement tracking and analytics."""
    
    def __init__(self):
        try:
            self.supabase = SupabaseClient(
                supabase_url=os.environ.get("SUPABASE_URL", ""),
                supabase_key=os.environ.get("SUPABASE_KEY", ""),
                use_service_role=True
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {e}")
            self.supabase = None
    
    async def record_engagement_event(self, event: UserEngagementEventCreate) -> str:
        """
        Record a user engagement event.
        
        Args:
            event: Engagement event data
            
        Returns:
            ID of the created event record
        """
        try:
            result = self.supabase.rpc(
                'record_engagement_event',
                {
                    'p_user_id': event.user_id,
                    'p_event_type': event.event_type.value,
                    'p_event_category': event.event_category.value,
                    'p_event_label': event.event_label,
                    'p_event_value': event.event_value,
                    'p_page_url': event.page_url,
                    'p_page_title': event.page_title,
                    'p_element_id': event.element_id,
                    'p_element_class': event.element_class,
                    'p_element_text': event.element_text,
                    'p_session_id': event.session_id,
                    'p_metadata': event.metadata
                }
            ).execute()
            
            if result.data:
                event_id = result.data
                logger.debug(f"Recorded engagement event: {event.event_type.value} for user {event.user_id}")
                return event_id
            else:
                logger.error("Failed to record engagement event - no data returned")
                raise Exception("Failed to record engagement event")
                
        except Exception as e:
            logger.error(f"Error recording engagement event: {str(e)}")
            raise
    
    async def update_session_analytics(self, update: UserSessionAnalyticsUpdate) -> bool:
        """
        Update user session analytics.
        
        Args:
            update: Session analytics update data
            
        Returns:
            True if update was successful
        """
        try:
            result = self.supabase.rpc(
                'update_session_analytics',
                {
                    'p_user_id': update.user_id,
                    'p_session_id': update.session_id,
                    'p_session_start': update.session_start.isoformat() if update.session_start else None,
                    'p_session_end': update.session_end.isoformat() if update.session_end else None,
                    'p_page_view': update.page_view,
                    'p_unique_page': update.unique_page,
                    'p_click': update.click,
                    'p_scroll': update.scroll,
                    'p_report_generated': update.report_generated,
                    'p_link_clicked': update.link_clicked,
                    'p_download': update.download,
                    'p_entry_page': update.entry_page,
                    'p_exit_page': update.exit_page,
                    'p_referrer': update.referrer,
                    'p_user_agent': update.user_agent,
                    'p_ip_address': update.ip_address,
                    'p_device_info': update.device_info
                }
            ).execute()
            
            if result.data:
                logger.debug(f"Updated session analytics for user: {update.user_id}, session: {update.session_id}")
                return True
            else:
                logger.error(f"Failed to update session analytics for user: {update.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating session analytics: {str(e)}")
            raise
    
    async def get_engagement_overview(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> EngagementOverview:
        """
        Get engagement overview metrics.
        
        Args:
            start_date: Start date for metrics (defaults to 30 days ago)
            end_date: End date for metrics (defaults to today)
            
        Returns:
            Engagement overview metrics
        """
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            result = self.supabase.rpc(
                'get_engagement_overview',
                {
                    'p_start_date': start_date.isoformat(),
                    'p_end_date': end_date.isoformat()
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return EngagementOverview(
                    total_users=row['total_users'],
                    active_users=row['active_users'],
                    new_users=row['new_users'],
                    total_sessions=row['total_sessions'],
                    avg_session_duration=float(row['avg_session_duration'] or 0),
                    total_page_views=row['total_page_views'],
                    avg_pages_per_session=float(row['avg_pages_per_session'] or 0),
                    total_clicks=row['total_clicks'],
                    total_reports_generated=row['total_reports_generated'],
                    total_links_clicked=row['total_links_clicked'],
                    avg_engagement_score=float(row['avg_engagement_score'] or 0),
                    bounce_rate=float(row['bounce_rate'] or 0)
                )
            else:
                return EngagementOverview(
                    total_users=0,
                    active_users=0,
                    new_users=0,
                    total_sessions=0,
                    avg_session_duration=0.0,
                    total_page_views=0,
                    avg_pages_per_session=0.0,
                    total_clicks=0,
                    total_reports_generated=0,
                    total_links_clicked=0,
                    avg_engagement_score=0.0,
                    bounce_rate=0.0
                )
                
        except Exception as e:
            logger.error(f"Error retrieving engagement overview: {str(e)}")
            raise
    
    async def get_engagement_trends(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        interval: str = "1 day"
    ) -> List[EngagementTrend]:
        """
        Get engagement trends over time.
        
        Args:
            start_date: Start date for trends (defaults to 30 days ago)
            end_date: End date for trends (defaults to today)
            interval: Time interval for aggregation
            
        Returns:
            List of engagement trend data points
        """
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            result = self.supabase.rpc(
                'get_engagement_trends',
                {
                    'p_start_date': start_date.isoformat(),
                    'p_end_date': end_date.isoformat(),
                    'p_interval': interval
                }
            ).execute()
            
            trends = []
            if result.data:
                for row in result.data:
                    trend = EngagementTrend(
                        time_bucket=datetime.fromisoformat(str(row['time_bucket'])),
                        active_users=row['active_users'],
                        total_sessions=row['total_sessions'],
                        avg_session_duration=float(row['avg_session_duration'] or 0),
                        total_page_views=row['total_page_views'],
                        total_clicks=row['total_clicks'],
                        total_reports=row['total_reports'],
                        avg_engagement_score=float(row['avg_engagement_score'] or 0)
                    )
                    trends.append(trend)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error retrieving engagement trends: {str(e)}")
            raise
    
    async def get_user_engagement_events(
        self,
        user_id: str,
        limit: int = 100,
        event_type: Optional[EngagementEventType] = None,
        event_category: Optional[EngagementEventCategory] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UserEngagementEvent]:
        """
        Get user engagement events with filtering.
        
        Args:
            user_id: User ID
            limit: Maximum number of events to return
            event_type: Filter by event type
            event_category: Filter by event category
            start_date: Filter events after this date
            end_date: Filter events before this date
            
        Returns:
            List of user engagement events
        """
        try:
            query = self.supabase.table('user_engagement_events').select('*').eq('user_id', user_id)
            
            if event_type:
                query = query.eq('event_type', event_type.value)
            if event_category:
                query = query.eq('event_category', event_category.value)
            if start_date:
                query = query.gte('timestamp', start_date.isoformat())
            if end_date:
                query = query.lte('timestamp', end_date.isoformat())
            
            result = query.order('timestamp', desc=True).limit(limit).execute()
            
            events = []
            if result.data:
                for row in result.data:
                    event = UserEngagementEvent(
                        id=row['id'],
                        user_id=row['user_id'],
                        event_type=EngagementEventType(row['event_type']),
                        event_category=EngagementEventCategory(row['event_category']),
                        event_label=row['event_label'],
                        event_value=float(row['event_value']) if row['event_value'] else None,
                        page_url=row['page_url'],
                        page_title=row['page_title'],
                        element_id=row['element_id'],
                        element_class=row['element_class'],
                        element_text=row['element_text'],
                        session_id=row['session_id'],
                        timestamp=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')),
                        metadata=row['metadata'] or {},
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
                    )
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error retrieving user engagement events: {str(e)}")
            raise
    
    async def get_user_session_analytics(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UserSessionAnalytics]:
        """
        Get user session analytics with filtering.
        
        Args:
            user_id: Filter by user ID
            session_id: Filter by session ID
            limit: Maximum number of sessions to return
            start_date: Filter sessions after this date
            end_date: Filter sessions before this date
            
        Returns:
            List of user session analytics
        """
        try:
            query = self.supabase.table('user_session_analytics').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
            if session_id:
                query = query.eq('session_id', session_id)
            if start_date:
                query = query.gte('session_start', start_date.isoformat())
            if end_date:
                query = query.lte('session_start', end_date.isoformat())
            
            result = query.order('session_start', desc=True).limit(limit).execute()
            
            sessions = []
            if result.data:
                for row in result.data:
                    session = UserSessionAnalytics(
                        id=row['id'],
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        session_start=datetime.fromisoformat(row['session_start'].replace('Z', '+00:00')),
                        session_end=datetime.fromisoformat(row['session_end'].replace('Z', '+00:00')) if row['session_end'] else None,
                        duration_minutes=float(row['duration_minutes'] or 0),
                        page_views=row['page_views'] or 0,
                        unique_pages=row['unique_pages'] or 0,
                        clicks_count=row['clicks_count'] or 0,
                        scrolls_count=row['scrolls_count'] or 0,
                        reports_generated=row['reports_generated'] or 0,
                        links_clicked=row['links_clicked'] or 0,
                        downloads_count=row['downloads_count'] or 0,
                        bounce_rate=float(row['bounce_rate'] or 0),
                        engagement_score=float(row['engagement_score'] or 0),
                        entry_page=row['entry_page'],
                        exit_page=row['exit_page'],
                        referrer=row['referrer'],
                        user_agent=row['user_agent'],
                        ip_address=row['ip_address'],
                        device_type=row['device_type'],
                        browser=row['browser'],
                        os=row['os'],
                        screen_resolution=row['screen_resolution'],
                        session_data=row['session_data'] or {},
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                    )
                    sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error retrieving user session analytics: {str(e)}")
            raise
    
    async def aggregate_daily_metrics(self, target_date: Optional[date] = None) -> bool:
        """
        Aggregate daily engagement metrics.
        
        Args:
            target_date: Date to aggregate (defaults to yesterday)
            
        Returns:
            True if aggregation was successful
        """
        try:
            if not target_date:
                target_date = date.today() - timedelta(days=1)
            
            result = self.supabase.rpc(
                'aggregate_daily_engagement_metrics',
                {'p_date': target_date.isoformat()}
            ).execute()
            
            if result.data:
                logger.info(f"Successfully aggregated daily engagement metrics for {target_date}")
                return True
            else:
                logger.error(f"Failed to aggregate daily engagement metrics for {target_date}")
                return False
                
        except Exception as e:
            logger.error(f"Error aggregating daily engagement metrics: {str(e)}")
            raise
    
    async def get_daily_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30
    ) -> List[EngagementMetricsDaily]:
        """
        Get daily engagement metrics.
        
        Args:
            start_date: Start date for metrics
            end_date: End date for metrics
            limit: Maximum number of days to return
            
        Returns:
            List of daily engagement metrics
        """
        try:
            query = self.supabase.table('engagement_metrics_daily').select('*')
            
            if start_date:
                query = query.gte('date', start_date.isoformat())
            if end_date:
                query = query.lte('date', end_date.isoformat())
            
            result = query.order('date', desc=True).limit(limit).execute()
            
            metrics = []
            if result.data:
                for row in result.data:
                    metric = EngagementMetricsDaily(
                        id=row['id'],
                        date=datetime.fromisoformat(str(row['date'])),
                        total_users=row['total_users'] or 0,
                        active_users=row['active_users'] or 0,
                        new_users=row['new_users'] or 0,
                        returning_users=row['returning_users'] or 0,
                        total_sessions=row['total_sessions'] or 0,
                        total_page_views=row['total_page_views'] or 0,
                        total_clicks=row['total_clicks'] or 0,
                        total_reports_generated=row['total_reports_generated'] or 0,
                        total_links_clicked=row['total_links_clicked'] or 0,
                        avg_session_duration=float(row['avg_session_duration'] or 0),
                        avg_pages_per_session=float(row['avg_pages_per_session'] or 0),
                        avg_clicks_per_session=float(row['avg_clicks_per_session'] or 0),
                        bounce_rate=float(row['bounce_rate'] or 0),
                        avg_engagement_score=float(row['avg_engagement_score'] or 0),
                        top_pages=row['top_pages'] or [],
                        top_events=row['top_events'] or [],
                        device_breakdown=row['device_breakdown'] or {},
                        browser_breakdown=row['browser_breakdown'] or {},
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                    )
                    metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving daily engagement metrics: {str(e)}")
            raise
    
    # Convenience methods for common tracking scenarios
    
    async def track_page_view(
        self,
        user_id: str,
        page_url: str,
        page_title: Optional[str] = None,
        session_id: Optional[str] = None,
        referrer: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Track a page view event."""
        try:
            # Record the engagement event
            await self.record_engagement_event(UserEngagementEventCreate(
                user_id=user_id,
                event_type=EngagementEventType.PAGE_VIEW,
                event_category=EngagementEventCategory.NAVIGATION,
                page_url=page_url,
                page_title=page_title,
                session_id=session_id
            ))
            
            # Update session analytics
            await self.update_session_analytics(UserSessionAnalyticsUpdate(
                user_id=user_id,
                session_id=session_id or f"session_{user_id}_{int(datetime.now().timestamp())}",
                page_view=True,
                unique_page=page_url,
                entry_page=page_url,
                referrer=referrer,
                user_agent=user_agent,
                ip_address=ip_address
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking page view: {str(e)}")
            return False
    
    async def track_click(
        self,
        user_id: str,
        element_id: Optional[str] = None,
        element_class: Optional[str] = None,
        element_text: Optional[str] = None,
        page_url: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Track a click event."""
        try:
            await self.record_engagement_event(UserEngagementEventCreate(
                user_id=user_id,
                event_type=EngagementEventType.CLICK,
                event_category=EngagementEventCategory.ACTION,
                element_id=element_id,
                element_class=element_class,
                element_text=element_text,
                page_url=page_url,
                session_id=session_id
            ))
            
            # Update session analytics
            if session_id:
                await self.update_session_analytics(UserSessionAnalyticsUpdate(
                    user_id=user_id,
                    session_id=session_id,
                    click=True
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking click: {str(e)}")
            return False
    
    async def track_report_generation(
        self,
        user_id: str,
        report_type: str,
        page_url: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Track a report generation event."""
        try:
            await self.record_engagement_event(UserEngagementEventCreate(
                user_id=user_id,
                event_type=EngagementEventType.PAGE_VIEW,  # Using page_view as base type
                event_category=EngagementEventCategory.REPORT,
                event_label=f"report_generated_{report_type}",
                page_url=page_url,
                session_id=session_id,
                metadata={"report_type": report_type}
            ))
            
            # Update session analytics
            if session_id:
                await self.update_session_analytics(UserSessionAnalyticsUpdate(
                    user_id=user_id,
                    session_id=session_id,
                    report_generated=True
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking report generation: {str(e)}")
            return False


# Global engagement service instance
engagement_service = UserEngagementService()