"""
Engagement Monitoring Service for MINT.

This service provides functionality for monitoring user engagement metrics,
tracking user interactions, and analyzing engagement patterns.
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

from ...system.core.supabase_client import get_supabase_client
from ...cache import cached

logger = logging.getLogger(__name__)


@dataclass
class EngagementMetric:
    """Data class for engagement metrics."""
    user_id: str
    session_id: str
    action_type: str
    timestamp: datetime
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EngagementSummary:
    """Data class for engagement summary."""
    total_sessions: int
    active_users: int
    avg_session_duration: float
    total_actions: int
    top_actions: List[Tuple[str, int]]
    engagement_score: float


class EngagementMonitoringService:
    """Service for monitoring user engagement and interactions."""
    
    def __init__(self):
        """Initialize the engagement monitoring service."""
        self.supabase = get_supabase_client()
        self._monitoring_active = False
        self._session_tracker = {}  # Track active sessions
        self._action_counts = {}    # Track action frequencies
    
    async def record_engagement(
        self,
        user_id: str,
        session_id: str,
        action_type: str,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an engagement event.
        
        Args:
            user_id: ID of the user
            session_id: ID of the session
            action_type: Type of action performed
            duration: Duration of the action in seconds
            metadata: Additional metadata about the action
            
        Returns:
            ID of the recorded engagement event
        """
        try:
            engagement_data = {
                'user_id': user_id,
                'session_id': session_id,
                'action_type': action_type,
                'timestamp': datetime.utcnow().isoformat(),
                'duration': duration,
                'metadata': metadata or {}
            }
            
            result = self.supabase.table('engagement_events').insert(engagement_data).execute()
            
            if result.data:
                engagement_id = result.data[0]['id']
                
                # Update local tracking
                self._update_local_tracking(user_id, session_id, action_type, duration)
                
                logger.debug(f"Recorded engagement: {user_id} - {action_type}")
                return engagement_id
            else:
                logger.error("Failed to record engagement - no data returned")
                raise Exception("Failed to record engagement")
                
        except Exception as e:
            logger.error(f"Error recording engagement: {str(e)}")
            raise
    
    def _update_local_tracking(
        self,
        user_id: str,
        session_id: str,
        action_type: str,
        duration: Optional[float]
    ):
        """Update local tracking for real-time metrics."""
        # Track session activity
        if session_id not in self._session_tracker:
            self._session_tracker[session_id] = {
                'user_id': user_id,
                'start_time': time.time(),
                'actions': [],
                'total_duration': 0
            }
        
        self._session_tracker[session_id]['actions'].append({
            'action_type': action_type,
            'timestamp': time.time(),
            'duration': duration or 0
        })
        
        if duration:
            self._session_tracker[session_id]['total_duration'] += duration
        
        # Track action frequencies
        if action_type not in self._action_counts:
            self._action_counts[action_type] = 0
        self._action_counts[action_type] += 1
    
    async def get_engagement_summary(
        self,
        user_id: Optional[str] = None,
        hours_back: int = 24
    ) -> EngagementSummary:
        """
        Get engagement summary for a user or all users.
        
        Args:
            user_id: Specific user ID (None for all users)
            hours_back: Number of hours to look back
            
        Returns:
            Engagement summary data
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Build query
            query = self.supabase.table('engagement_events').select('*')
            query = query.gte('timestamp', start_time.isoformat())
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.execute()
            
            if not result.data:
                return EngagementSummary(
                    total_sessions=0,
                    active_users=0,
                    avg_session_duration=0.0,
                    total_actions=0,
                    top_actions=[],
                    engagement_score=0.0
                )
            
            # Process data
            sessions = {}
            action_counts = {}
            total_duration = 0
            users = set()
            
            for event in result.data:
                session_id = event['session_id']
                user_id_event = event['user_id']
                action_type = event['action_type']
                duration = event.get('duration', 0) or 0
                
                users.add(user_id_event)
                
                # Track sessions
                if session_id not in sessions:
                    sessions[session_id] = {
                        'user_id': user_id_event,
                        'actions': 0,
                        'duration': 0
                    }
                
                sessions[session_id]['actions'] += 1
                sessions[session_id]['duration'] += duration
                total_duration += duration
                
                # Track action counts
                if action_type not in action_counts:
                    action_counts[action_type] = 0
                action_counts[action_type] += 1
            
            # Calculate metrics
            total_sessions = len(sessions)
            active_users = len(users)
            avg_session_duration = total_duration / total_sessions if total_sessions > 0 else 0
            total_actions = sum(action_counts.values())
            
            # Get top actions
            top_actions = sorted(
                action_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Calculate engagement score (0-100)
            engagement_score = self._calculate_engagement_score(
                total_sessions, active_users, avg_session_duration, total_actions
            )
            
            return EngagementSummary(
                total_sessions=total_sessions,
                active_users=active_users,
                avg_session_duration=avg_session_duration,
                total_actions=total_actions,
                top_actions=top_actions,
                engagement_score=engagement_score
            )
            
        except Exception as e:
            logger.error(f"Error getting engagement summary: {str(e)}")
            raise
    
    def _calculate_engagement_score(
        self,
        total_sessions: int,
        active_users: int,
        avg_session_duration: float,
        total_actions: int
    ) -> float:
        """Calculate engagement score based on various metrics."""
        # Normalize metrics (these thresholds can be adjusted based on your data)
        session_score = min(total_sessions / 10, 1.0) * 25  # Max 25 points
        user_score = min(active_users / 5, 1.0) * 25        # Max 25 points
        duration_score = min(avg_session_duration / 300, 1.0) * 25  # Max 25 points (5 min = 100%)
        action_score = min(total_actions / 50, 1.0) * 25    # Max 25 points
        
        return session_score + user_score + duration_score + action_score
    
    @cached(ttl_seconds=300, key_prefix="engagement", tags=["engagement", "monitoring"])
    async def get_user_engagement_trends(
        self,
        user_id: str,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get engagement trends for a specific user.
        
        Args:
            user_id: ID of the user
            days_back: Number of days to look back
            
        Returns:
            List of daily engagement data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            result = self.supabase.rpc(
                'get_user_engagement_trends',
                {
                    'p_user_id': user_id,
                    'p_start_date': start_date.isoformat()
                }
            ).execute()
            
            trends = []
            if result.data:
                for row in result.data:
                    trends.append({
                        'date': row['date'],
                        'sessions': row['sessions'],
                        'actions': row['actions'],
                        'duration': row['duration'],
                        'engagement_score': row['engagement_score']
                    })
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting user engagement trends: {str(e)}")
            raise
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get currently active sessions.
        
        Returns:
            List of active session data
        """
        try:
            # Get sessions that have been active in the last 30 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=30)
            
            result = self.supabase.rpc(
                'get_active_sessions',
                {'p_cutoff_time': cutoff_time.isoformat()}
            ).execute()
            
            active_sessions = []
            if result.data:
                for row in result.data:
                    active_sessions.append({
                        'session_id': row['session_id'],
                        'user_id': row['user_id'],
                        'last_activity': row['last_activity'],
                        'action_count': row['action_count'],
                        'total_duration': row['total_duration']
                    })
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {str(e)}")
            raise
    
    async def cleanup_old_engagement_data(self, days_to_keep: int = 90):
        """
        Clean up old engagement data to maintain performance.
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = self.supabase.table('engagement_events').delete().lt(
                'timestamp', cutoff_date.isoformat()
            ).execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {deleted_count} old engagement records")
            
        except Exception as e:
            logger.error(f"Error cleaning up engagement data: {str(e)}")
            raise
    
    async def start_monitoring(self, interval_seconds: int = 300):
        """
        Start continuous engagement monitoring.
        
        Args:
            interval_seconds: Interval between monitoring cycles
        """
        self._monitoring_active = True
        logger.info("Starting engagement monitoring")
        
        while self._monitoring_active:
            try:
                # Clean up old sessions (inactive for more than 1 hour)
                current_time = time.time()
                inactive_sessions = []
                
                for session_id, session_data in self._session_tracker.items():
                    last_action_time = max(
                        [action['timestamp'] for action in session_data['actions']],
                        default=session_data['start_time']
                    )
                    
                    if current_time - last_action_time > 3600:  # 1 hour
                        inactive_sessions.append(session_id)
                
                # Remove inactive sessions
                for session_id in inactive_sessions:
                    del self._session_tracker[session_id]
                
                # Log monitoring stats
                logger.debug(f"Active sessions: {len(self._session_tracker)}")
                logger.debug(f"Action counts: {dict(list(self._action_counts.items())[:5])}")
                
                # Wait for next cycle
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in engagement monitoring cycle: {str(e)}")
                await asyncio.sleep(interval_seconds)
    
    def stop_monitoring(self):
        """Stop continuous engagement monitoring."""
        self._monitoring_active = False
        logger.info("Stopping engagement monitoring")


# Global engagement monitoring service instance
engagement_monitoring_service = EngagementMonitoringService()
