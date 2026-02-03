"""
User analytics service for admin dashboard.

This service provides comprehensive user analytics and tracking capabilities
for the admin dashboard, including user behavior analysis and engagement metrics.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..api.supabase_client import get_supabase_client
from ..schemas.schemas import (
    UserProfile,
    UserAnalyticsSummary,
    UserActivityLog,
    UserActivityType,
    UserAnalyticsQuery,
    UserAnalyticsResponse,
    UserActivityTimelineQuery,
    UserAnalyticsAggregated,
    UserAnalyticsAggregatedQuery,
    UserLoginAnalytics,
    UserRequestAnalytics,
    UserReportAnalytics,
    UserScreenTimeAnalytics
)

logger = logging.getLogger(__name__)


class UserAnalyticsService:
    """Service for managing user analytics and tracking."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def update_login_analytics(self, analytics: UserLoginAnalytics) -> bool:
        """
        Update user login analytics.
        
        Args:
            analytics: Login analytics data
            
        Returns:
            True if update was successful
        """
        try:
            result = self.supabase.rpc(
                'update_user_login_analytics',
                {
                    'p_user_id': analytics.user_id,
                    'p_ip_address': analytics.ip_address,
                    'p_user_agent': analytics.user_agent,
                    'p_session_id': analytics.session_id
                }
            ).execute()
            
            if result.data:
                logger.debug(f"Updated login analytics for user: {analytics.user_id}")
                return True
            else:
                logger.error(f"Failed to update login analytics for user: {analytics.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating login analytics: {str(e)}")
            raise
    
    async def update_request_analytics(self, analytics: UserRequestAnalytics) -> bool:
        """
        Update user request analytics.
        
        Args:
            analytics: Request analytics data
            
        Returns:
            True if update was successful
        """
        try:
            result = self.supabase.rpc(
                'update_user_request_analytics',
                {
                    'p_user_id': analytics.user_id,
                    'p_request_type': analytics.request_type,
                    'p_request_data': analytics.request_data,
                    'p_session_id': analytics.session_id
                }
            ).execute()
            
            if result.data:
                logger.debug(f"Updated request analytics for user: {analytics.user_id}")
                return True
            else:
                logger.error(f"Failed to update request analytics for user: {analytics.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating request analytics: {str(e)}")
            raise
    
    async def update_report_analytics(self, analytics: UserReportAnalytics) -> bool:
        """
        Update user report generation analytics.
        
        Args:
            analytics: Report analytics data
            
        Returns:
            True if update was successful
        """
        try:
            result = self.supabase.rpc(
                'update_user_report_analytics',
                {
                    'p_user_id': analytics.user_id,
                    'p_report_type': analytics.report_type,
                    'p_report_data': analytics.report_data,
                    'p_session_id': analytics.session_id
                }
            ).execute()
            
            if result.data:
                logger.debug(f"Updated report analytics for user: {analytics.user_id}")
                return True
            else:
                logger.error(f"Failed to update report analytics for user: {analytics.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating report analytics: {str(e)}")
            raise
    
    async def update_screen_time_analytics(self, analytics: UserScreenTimeAnalytics) -> bool:
        """
        Update user screen time analytics.
        
        Args:
            analytics: Screen time analytics data
            
        Returns:
            True if update was successful
        """
        try:
            result = self.supabase.rpc(
                'update_user_screen_time',
                {
                    'p_user_id': analytics.user_id,
                    'p_session_duration_minutes': analytics.session_duration_minutes,
                    'p_session_id': analytics.session_id
                }
            ).execute()
            
            if result.data:
                logger.debug(f"Updated screen time analytics for user: {analytics.user_id}")
                return True
            else:
                logger.error(f"Failed to update screen time analytics for user: {analytics.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating screen time analytics: {str(e)}")
            raise
    
    async def calculate_engagement_score(self, user_id: str) -> float:
        """
        Calculate and update engagement score for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Calculated engagement score
        """
        try:
            result = self.supabase.rpc(
                'calculate_engagement_score',
                {'p_user_id': user_id}
            ).execute()
            
            if result.data is not None:
                engagement_score = float(result.data)
                logger.debug(f"Calculated engagement score for user {user_id}: {engagement_score}")
                return engagement_score
            else:
                logger.error(f"Failed to calculate engagement score for user: {user_id}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating engagement score: {str(e)}")
            raise
    
    async def get_user_analytics_summary(self, query: UserAnalyticsQuery) -> UserAnalyticsResponse:
        """
        Get user analytics summary with filtering and pagination.
        
        Args:
            query: Query parameters
            
        Returns:
            Paginated user analytics data
        """
        try:
            result = self.supabase.rpc(
                'get_user_analytics_summary',
                {
                    'p_limit': query.limit,
                    'p_offset': query.offset,
                    'p_order_by': query.order_by,
                    'p_order_direction': query.order_direction
                }
            ).execute()
            
            users = []
            if result.data:
                for row in result.data:
                    user = UserAnalyticsSummary(
                        user_id=row['user_id'],
                        email=row['email'],
                        display_name=row['display_name'],
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                        last_login=datetime.fromisoformat(row['last_login'].replace('Z', '+00:00')) if row['last_login'] else None,
                        last_activity=datetime.fromisoformat(row['last_activity'].replace('Z', '+00:00')) if row['last_activity'] else None,
                        login_count=row['login_count'],
                        total_requests=row['total_requests'],
                        total_reports_generated=row['total_reports_generated'],
                        total_screen_time_minutes=row['total_screen_time_minutes'],
                        subscription_status=row['subscription_status'],
                        geographic_location=row['geographic_location'],
                        engagement_score=float(row['engagement_score']),
                        days_since_signup=row['days_since_signup'],
                        avg_requests_per_day=float(row['avg_requests_per_day']),
                        avg_reports_per_day=float(row['avg_reports_per_day'])
                    )
                    users.append(user)
            
            # Get total count for pagination
            count_result = self.supabase.table('user_profiles').select('*', count='exact').execute()
            total_count = count_result.count or 0
            
            has_more = (query.offset + len(users)) < total_count
            
            return UserAnalyticsResponse(
                users=users,
                total_count=total_count,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(f"Error retrieving user analytics summary: {str(e)}")
            raise
    
    async def get_user_activity_timeline(self, query: UserActivityTimelineQuery) -> List[UserActivityLog]:
        """
        Get user activity timeline.
        
        Args:
            query: Query parameters
            
        Returns:
            List of user activity log entries
        """
        try:
            activity_types = [t.value for t in query.activity_types] if query.activity_types else None
            
            result = self.supabase.rpc(
                'get_user_activity_timeline',
                {
                    'p_user_id': query.user_id,
                    'p_limit': query.limit,
                    'p_activity_types': activity_types
                }
            ).execute()
            
            activities = []
            if result.data:
                for row in result.data:
                    activity = UserActivityLog(
                        id=row['id'],
                        user_id=query.user_id,
                        activity_type=UserActivityType(row['activity_type']),
                        activity_data=row['activity_data'] or {},
                        session_id=row['session_id'],
                        timestamp=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')),
                        created_at=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                    )
                    activities.append(activity)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error retrieving user activity timeline: {str(e)}")
            raise
    
    async def get_user_analytics_aggregated(self, query: UserAnalyticsAggregatedQuery) -> List[UserAnalyticsAggregated]:
        """
        Get aggregated user analytics data.
        
        Args:
            query: Query parameters
            
        Returns:
            List of aggregated analytics data
        """
        try:
            result = self.supabase.rpc(
                'get_user_analytics_aggregated',
                {
                    'p_start_date': query.start_date.isoformat() if query.start_date else None,
                    'p_end_date': query.end_date.isoformat() if query.end_date else None,
                    'p_interval': query.interval
                }
            ).execute()
            
            analytics = []
            if result.data:
                for row in result.data:
                    analytic = UserAnalyticsAggregated(
                        time_bucket=datetime.fromisoformat(row['time_bucket'].replace('Z', '+00:00')),
                        new_users=row['new_users'],
                        active_users=row['active_users'],
                        total_logins=row['total_logins'],
                        total_requests=row['total_requests'],
                        total_reports=row['total_reports'],
                        avg_engagement_score=float(row['avg_engagement_score']) if row['avg_engagement_score'] else None
                    )
                    analytics.append(analytic)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error retrieving aggregated user analytics: {str(e)}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get detailed user profile with analytics.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile with analytics data
        """
        try:
            result = self.supabase.table('user_profiles').select(
                '*, auth.users!inner(email)'
            ).eq('id', user_id).single().execute()
            
            if result.data:
                row = result.data
                profile = UserProfile(
                    id=row['id'],
                    email=row['auth']['users']['email'] if row.get('auth') else None,
                    display_name=row['display_name'],
                    avatar_url=row['avatar_url'],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')),
                    last_login=datetime.fromisoformat(row['last_login'].replace('Z', '+00:00')) if row['last_login'] else None,
                    last_activity=datetime.fromisoformat(row['last_activity'].replace('Z', '+00:00')) if row['last_activity'] else None,
                    login_count=row['login_count'] or 0,
                    total_requests=row['total_requests'] or 0,
                    total_reports_generated=row['total_reports_generated'] or 0,
                    total_screen_time_minutes=row['total_screen_time_minutes'] or 0,
                    subscription_status=row['subscription_status'] or 'free',
                    subscription_start_date=datetime.fromisoformat(row['subscription_start_date'].replace('Z', '+00:00')) if row['subscription_start_date'] else None,
                    subscription_end_date=datetime.fromisoformat(row['subscription_end_date'].replace('Z', '+00:00')) if row['subscription_end_date'] else None,
                    geographic_location=row['geographic_location'],
                    timezone=row['timezone'],
                    usage_analytics=row['usage_analytics'] or {},
                    engagement_score=float(row['engagement_score'] or 0),
                    preferences=row['preferences'] or {}
                )
                return profile
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}")
            raise
    
    async def bulk_calculate_engagement_scores(self, limit: int = 100) -> int:
        """
        Calculate engagement scores for multiple users in bulk.
        
        Args:
            limit: Maximum number of users to process
            
        Returns:
            Number of users processed
        """
        try:
            # Get users who need engagement score updates
            result = self.supabase.table('user_profiles').select('id').limit(limit).execute()
            
            processed = 0
            if result.data:
                for row in result.data:
                    try:
                        await self.calculate_engagement_score(row['id'])
                        processed += 1
                    except Exception as e:
                        logger.error(f"Failed to calculate engagement score for user {row['id']}: {str(e)}")
                        continue
            
            logger.info(f"Bulk calculated engagement scores for {processed} users")
            return processed
            
        except Exception as e:
            logger.error(f"Error in bulk engagement score calculation: {str(e)}")
            raise


# Global user analytics service instance
user_analytics_service = UserAnalyticsService()