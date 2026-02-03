"""
Report usage analytics service for tracking and analyzing report creation patterns.

This service provides comprehensive analytics on report usage including:
- Report creation frequency tracking
- Topic and industry analysis
- Usage insights generation
- JSON-compliant data processing
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

from ..system.core.supabase_client import get_supabase_client
from ...schemas.schemas import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class ReportCreationFrequency(BaseModel):
    """Model for report creation frequency data."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    count: int = Field(..., description="Number of reports created on this date")


class TopicAnalysis(BaseModel):
    """Model for topic analysis data."""
    topic: str = Field(..., description="Topic or keyword")
    count: int = Field(..., description="Number of reports containing this topic")
    percentage: float = Field(..., description="Percentage of total reports")


class IndustryAnalysis(BaseModel):
    """Model for industry analysis data."""
    industry: str = Field(..., description="Industry name")
    count: int = Field(..., description="Number of reports for this industry")
    percentage: float = Field(..., description="Percentage of total reports")


class UsageInsights(BaseModel):
    """Model for usage insights data."""
    total_reports: int = Field(..., description="Total number of reports")
    reports_this_week: int = Field(..., description="Reports created this week")
    reports_this_month: int = Field(..., description="Reports created this month")
    avg_reports_per_day: float = Field(..., description="Average reports per day")
    most_active_day: str = Field(..., description="Day with most report creation")
    top_topics: List[TopicAnalysis] = Field(..., description="Top topics analyzed")
    top_industries: List[IndustryAnalysis] = Field(..., description="Top industries analyzed")
    creation_frequency: List[ReportCreationFrequency] = Field(..., description="Daily creation frequency")


class ReportUsageAnalyticsService:
    """Service for tracking and analyzing report usage patterns."""
    
    def __init__(self):
        self.supabase = None
    
    def _get_supabase(self):
        """Get supabase client, initializing if needed."""
        if self.supabase is None:
            self.supabase = get_supabase_client()
        return self.supabase
    
    async def track_report_creation(self, user_id: str, report_id: str, report_data: Dict[str, Any]) -> bool:
        """
        Track a new report creation for analytics.
        
        Args:
            user_id: ID of the user who created the report
            report_id: ID of the created report
            report_data: Report content and metadata
            
        Returns:
            True if tracking was successful
        """
        try:
            # Extract topic and industry information from report data
            topics = self._extract_topics(report_data)
            industry = self._extract_industry(report_data)
            
            # Update report analytics table
            await self._update_report_analytics(user_id, topics, industry)
            
            logger.debug(f"Tracked report creation for user {user_id}, report {report_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking report creation: {str(e)}")
            return False
    
    async def get_creation_frequency(self, user_id: str, days: int = 30) -> List[ReportCreationFrequency]:
        """
        Get report creation frequency for a user over specified days.
        
        Args:
            user_id: User ID
            days: Number of days to analyze (default 30)
            
        Returns:
            List of daily creation frequency data
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Query reports created in the date range
            result = self._get_supabase().table('mint_reports').select(
                'created_at'
            ).eq('user_id', user_id).gte(
                'created_at', start_date.isoformat()
            ).lte(
                'created_at', end_date.isoformat()
            ).execute()
            
            # Count reports by date
            date_counts = defaultdict(int)
            if result.data:
                for report in result.data:
                    created_date = datetime.fromisoformat(
                        report['created_at'].replace('Z', '+00:00')
                    ).date().isoformat()
                    date_counts[created_date] += 1
            
            # Fill in missing dates with zero counts
            frequency_data = []
            current_date = start_date.date()
            while current_date <= end_date.date():
                date_str = current_date.isoformat()
                frequency_data.append(ReportCreationFrequency(
                    date=date_str,
                    count=date_counts.get(date_str, 0)
                ))
                current_date += timedelta(days=1)
            
            return frequency_data
            
        except Exception as e:
            logger.error(f"Error getting creation frequency: {str(e)}")
            raise
    
    async def analyze_topics(self, user_id: str, limit: int = 10) -> List[TopicAnalysis]:
        """
        Analyze topics from user's reports.
        
        Args:
            user_id: User ID
            limit: Maximum number of topics to return
            
        Returns:
            List of topic analysis data
        """
        try:
            # Get all reports for the user
            result = self._get_supabase().table('mint_reports').select(
                'content, title'
            ).eq('user_id', user_id).execute()
            
            if not result.data:
                return []
            
            # Extract and count topics
            all_topics = []
            for report in result.data:
                topics = self._extract_topics(report)
                all_topics.extend(topics)
            
            # Count topic occurrences
            topic_counts = Counter(all_topics)
            total_reports = len(result.data)
            
            # Create topic analysis data
            topic_analysis = []
            for topic, count in topic_counts.most_common(limit):
                percentage = (count / total_reports) * 100
                topic_analysis.append(TopicAnalysis(
                    topic=topic,
                    count=count,
                    percentage=round(percentage, 2)
                ))
            
            return topic_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing topics: {str(e)}")
            raise
    
    async def analyze_industries(self, user_id: str, limit: int = 10) -> List[IndustryAnalysis]:
        """
        Analyze industries from user's reports.
        
        Args:
            user_id: User ID
            limit: Maximum number of industries to return
            
        Returns:
            List of industry analysis data
        """
        try:
            # Get all reports for the user
            result = self._get_supabase().table('mint_reports').select(
                'content, category'
            ).eq('user_id', user_id).execute()
            
            if not result.data:
                return []
            
            # Extract and count industries
            industries = []
            for report in result.data:
                industry = self._extract_industry(report)
                if industry:
                    industries.append(industry)
            
            # Count industry occurrences
            industry_counts = Counter(industries)
            total_reports = len([r for r in result.data if self._extract_industry(r)])
            
            if total_reports == 0:
                return []
            
            # Create industry analysis data
            industry_analysis = []
            for industry, count in industry_counts.most_common(limit):
                percentage = (count / total_reports) * 100
                industry_analysis.append(IndustryAnalysis(
                    industry=industry,
                    count=count,
                    percentage=round(percentage, 2)
                ))
            
            return industry_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing industries: {str(e)}")
            raise
    
    async def generate_usage_insights(self, user_id: str) -> UsageInsights:
        """
        Generate comprehensive usage insights for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Usage insights data
        """
        try:
            # Get basic report counts
            total_reports = await self._get_total_reports(user_id)
            reports_this_week = await self._get_reports_in_period(user_id, 7)
            reports_this_month = await self._get_reports_in_period(user_id, 30)
            
            # Calculate average reports per day (based on last 30 days)
            avg_reports_per_day = reports_this_month / 30.0
            
            # Get most active day
            most_active_day = await self._get_most_active_day(user_id)
            
            # Get creation frequency for last 30 days
            creation_frequency = await self.get_creation_frequency(user_id, 30)
            
            # Get top topics and industries
            top_topics = await self.analyze_topics(user_id, 5)
            top_industries = await self.analyze_industries(user_id, 5)
            
            return UsageInsights(
                total_reports=total_reports,
                reports_this_week=reports_this_week,
                reports_this_month=reports_this_month,
                avg_reports_per_day=round(avg_reports_per_day, 2),
                most_active_day=most_active_day,
                top_topics=top_topics,
                top_industries=top_industries,
                creation_frequency=creation_frequency
            )
            
        except Exception as e:
            logger.error(f"Error generating usage insights: {str(e)}")
            raise
    
    def _extract_topics(self, report_data: Dict[str, Any]) -> List[str]:
        """
        Extract topics from report data.
        
        Args:
            report_data: Report content and metadata
            
        Returns:
            List of extracted topics
        """
        topics = []
        
        try:
            # Extract from title
            title = report_data.get('title', '')
            if title:
                # Simple keyword extraction from title
                title_words = [word.strip().lower() for word in title.split() 
                              if len(word.strip()) > 3]
                topics.extend(title_words)
            
            # Extract from content if it's JSON
            content = report_data.get('content', {})
            if isinstance(content, dict):
                # Look for keywords in various fields
                for field in ['keywords', 'tags', 'topics']:
                    if field in content and isinstance(content[field], list):
                        topics.extend([str(item).lower() for item in content[field]])
                
                # Extract from summary or description
                for field in ['summary', 'description', 'executive_summary']:
                    if field in content and isinstance(content[field], str):
                        # Simple keyword extraction
                        words = [word.strip().lower() for word in content[field].split() 
                                if len(word.strip()) > 4]
                        topics.extend(words[:5])  # Limit to first 5 words
            
            # Remove duplicates and filter
            unique_topics = list(set(topics))
            # Filter out common words
            stop_words = {'this', 'that', 'with', 'from', 'they', 'have', 'been', 
                         'will', 'their', 'said', 'each', 'which', 'more', 'than'}
            filtered_topics = [topic for topic in unique_topics 
                             if topic not in stop_words and len(topic) > 2]
            
            return filtered_topics[:10]  # Limit to top 10 topics
            
        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}")
            return []
    
    def _extract_industry(self, report_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract industry from report data.
        
        Args:
            report_data: Report content and metadata
            
        Returns:
            Extracted industry or None
        """
        try:
            # Check category field first
            if 'category' in report_data and report_data['category']:
                return str(report_data['category']).strip()
            
            # Check content for industry information
            content = report_data.get('content', {})
            if isinstance(content, dict):
                # Look for industry field
                if 'industry' in content:
                    industry = content['industry']
                    if isinstance(industry, str):
                        return industry.strip()
                    elif isinstance(industry, dict) and 'name' in industry:
                        return str(industry['name']).strip()
                
                # Look for sector field
                if 'sector' in content:
                    return str(content['sector']).strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting industry: {str(e)}")
            return None
    
    async def _update_report_analytics(self, user_id: str, topics: List[str], industry: Optional[str]) -> None:
        """
        Update the report analytics table with new report data.
        
        Args:
            user_id: User ID
            topics: List of topics from the report
            industry: Industry from the report
        """
        try:
            # This will be handled by the database trigger
            # The trigger automatically updates report_analytics when a new report is created
            logger.debug(f"Report analytics will be updated by database trigger for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating report analytics: {str(e)}")
            raise
    
    async def _get_total_reports(self, user_id: str) -> int:
        """Get total number of reports for a user."""
        try:
            result = self._get_supabase().table('mint_reports').select(
                '*', count='exact'
            ).eq('user_id', user_id).execute()
            
            return result.count or 0
            
        except Exception as e:
            logger.error(f"Error getting total reports: {str(e)}")
            return 0
    
    async def _get_reports_in_period(self, user_id: str, days: int) -> int:
        """Get number of reports created in the last N days."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            result = self._get_supabase().table('mint_reports').select(
                '*', count='exact'
            ).eq('user_id', user_id).gte(
                'created_at', start_date.isoformat()
            ).execute()
            
            return result.count or 0
            
        except Exception as e:
            logger.error(f"Error getting reports in period: {str(e)}")
            return 0
    
    async def _get_most_active_day(self, user_id: str) -> str:
        """Get the day of week with most report creation activity."""
        try:
            # Get reports from last 90 days
            start_date = datetime.now() - timedelta(days=90)
            
            result = self._get_supabase().table('mint_reports').select(
                'created_at'
            ).eq('user_id', user_id).gte(
                'created_at', start_date.isoformat()
            ).execute()
            
            if not result.data:
                return "No data"
            
            # Count by day of week
            day_counts = defaultdict(int)
            for report in result.data:
                created_date = datetime.fromisoformat(
                    report['created_at'].replace('Z', '+00:00')
                )
                day_name = created_date.strftime('%A')
                day_counts[day_name] += 1
            
            if not day_counts:
                return "No data"
            
            # Find most active day
            most_active = max(day_counts.items(), key=lambda x: x[1])
            return most_active[0]
            
        except Exception as e:
            logger.error(f"Error getting most active day: {str(e)}")
            return "Unknown"


# Global service instance
report_usage_analytics_service = ReportUsageAnalyticsService()