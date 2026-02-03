"""
Report trend detection service for identifying research patterns and suggesting related reports.

This service provides:
- Research pattern identification
- Recurring topic detection
- Related report suggestions
- JSON-compliant data processing
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import re
from difflib import SequenceMatcher

from ..system.core.supabase_client import get_supabase_client
from ...schemas.schemas import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class ResearchPattern(BaseModel):
    """Model for research pattern data."""
    pattern_id: str = Field(..., description="Unique identifier for the pattern")
    pattern_type: str = Field(..., description="Type of pattern (topic, industry, temporal)")
    pattern_name: str = Field(..., description="Human-readable name for the pattern")
    frequency: int = Field(..., description="Number of times this pattern appears")
    confidence: float = Field(..., description="Confidence score for the pattern (0.0-1.0)")
    first_occurrence: str = Field(..., description="Date of first occurrence")
    last_occurrence: str = Field(..., description="Date of last occurrence")
    related_reports: List[str] = Field(..., description="List of report IDs showing this pattern")


class RecurringTopic(BaseModel):
    """Model for recurring topic data."""
    topic: str = Field(..., description="Topic name")
    occurrences: int = Field(..., description="Number of occurrences")
    trend_direction: str = Field(..., description="Trend direction: increasing, decreasing, stable")
    trend_strength: float = Field(..., description="Strength of the trend (0.0-1.0)")
    time_periods: List[str] = Field(..., description="Time periods when topic appeared")
    related_keywords: List[str] = Field(..., description="Related keywords and phrases")


class RelatedReport(BaseModel):
    """Model for related report suggestion."""
    report_id: str = Field(..., description="ID of the related report")
    title: str = Field(..., description="Title of the related report")
    similarity_score: float = Field(..., description="Similarity score (0.0-1.0)")
    similarity_reasons: List[str] = Field(..., description="Reasons for similarity")
    created_at: str = Field(..., description="Creation date of the report")


class TrendInsights(BaseModel):
    """Model for comprehensive trend insights."""
    research_patterns: List[ResearchPattern] = Field(..., description="Identified research patterns")
    recurring_topics: List[RecurringTopic] = Field(..., description="Recurring topics analysis")
    trend_summary: Dict[str, Any] = Field(..., description="Summary of trends")
    recommendations: List[str] = Field(..., description="Trend-based recommendations")


class ReportTrendDetectionService:
    """Service for detecting trends and patterns in report history."""
    
    def __init__(self):
        self.supabase = None
    
    def _get_supabase(self):
        """Get supabase client, initializing if needed."""
        if self.supabase is None:
            self.supabase = get_supabase_client()
        return self.supabase
    
    async def identify_research_patterns(self, user_id: str, days: int = 90) -> List[ResearchPattern]:
        """
        Identify research patterns for a user.
        
        Args:
            user_id: User ID
            days: Number of days to analyze (default 90)
            
        Returns:
            List of identified research patterns
        """
        try:
            # Get user's reports from the specified period
            reports = await self._get_user_reports(user_id, days)
            
            if not reports:
                return []
            
            patterns = []
            
            # Identify topic patterns
            topic_patterns = self._identify_topic_patterns(reports)
            patterns.extend(topic_patterns)
            
            # Identify industry patterns
            industry_patterns = self._identify_industry_patterns(reports)
            patterns.extend(industry_patterns)
            
            # Identify temporal patterns
            temporal_patterns = self._identify_temporal_patterns(reports)
            patterns.extend(temporal_patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying research patterns: {str(e)}")
            raise
    
    async def detect_recurring_topics(self, user_id: str, days: int = 90) -> List[RecurringTopic]:
        """
        Detect recurring topics in user's research.
        
        Args:
            user_id: User ID
            days: Number of days to analyze (default 90)
            
        Returns:
            List of recurring topics with trend analysis
        """
        try:
            # Get user's reports from the specified period
            reports = await self._get_user_reports(user_id, days)
            
            if not reports:
                return []
            
            # Extract topics from all reports with timestamps
            topic_timeline = self._extract_topic_timeline(reports)
            
            # Analyze trends for each topic
            recurring_topics = []
            for topic, occurrences in topic_timeline.items():
                if len(occurrences) >= 2:  # Must appear at least twice to be recurring
                    trend_data = self._analyze_topic_trend(topic, occurrences)
                    recurring_topics.append(trend_data)
            
            # Sort by trend strength and frequency
            recurring_topics.sort(key=lambda x: (x.trend_strength, x.occurrences), reverse=True)
            
            return recurring_topics
            
        except Exception as e:
            logger.error(f"Error detecting recurring topics: {str(e)}")
            raise
    
    async def suggest_related_reports(self, user_id: str, current_report_id: str, limit: int = 5) -> List[RelatedReport]:
        """
        Suggest related reports based on content similarity.
        
        Args:
            user_id: User ID
            current_report_id: ID of the current report
            limit: Maximum number of suggestions
            
        Returns:
            List of related report suggestions
        """
        try:
            # Get the current report
            current_report = await self._get_report_by_id(current_report_id, user_id)
            if not current_report:
                return []
            
            # Get all other reports by the user
            all_reports = await self._get_user_reports(user_id, days=365)  # Look back 1 year
            other_reports = [r for r in all_reports if r['id'] != current_report_id]
            
            if not other_reports:
                return []
            
            # Calculate similarity scores
            similarities = []
            for report in other_reports:
                similarity_score, reasons = self._calculate_similarity(current_report, report)
                if similarity_score > 0.3:  # Minimum similarity threshold
                    similarities.append({
                        'report': report,
                        'score': similarity_score,
                        'reasons': reasons
                    })
            
            # Sort by similarity score and take top results
            similarities.sort(key=lambda x: x['score'], reverse=True)
            
            # Create related report objects
            related_reports = []
            for sim in similarities[:limit]:
                related_report = RelatedReport(
                    report_id=sim['report']['id'],
                    title=sim['report']['title'],
                    similarity_score=round(sim['score'], 3),
                    similarity_reasons=sim['reasons'],
                    created_at=sim['report']['created_at']
                )
                related_reports.append(related_report)
            
            return related_reports
            
        except Exception as e:
            logger.error(f"Error suggesting related reports: {str(e)}")
            raise
    
    async def generate_trend_insights(self, user_id: str) -> TrendInsights:
        """
        Generate comprehensive trend insights for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Comprehensive trend insights
        """
        try:
            # Get research patterns
            research_patterns = await self.identify_research_patterns(user_id)
            
            # Get recurring topics
            recurring_topics = await self.detect_recurring_topics(user_id)
            
            # Generate trend summary
            trend_summary = self._generate_trend_summary(research_patterns, recurring_topics)
            
            # Generate recommendations
            recommendations = self._generate_trend_recommendations(research_patterns, recurring_topics)
            
            return TrendInsights(
                research_patterns=research_patterns,
                recurring_topics=recurring_topics,
                trend_summary=trend_summary,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error generating trend insights: {str(e)}")
            raise
    
    async def _get_user_reports(self, user_id: str, days: int) -> List[Dict[str, Any]]:
        """Get user's reports from the specified time period."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            result = self._get_supabase().table('mint_reports').select(
                'id, title, content, category, created_at, updated_at'
            ).eq('user_id', user_id).gte(
                'created_at', start_date.isoformat()
            ).order('created_at', desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting user reports: {str(e)}")
            return []
    
    async def _get_report_by_id(self, report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific report by ID."""
        try:
            result = self._get_supabase().table('mint_reports').select(
                'id, title, content, category, created_at'
            ).eq('id', report_id).eq('user_id', user_id).single().execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting report by ID: {str(e)}")
            return None
    
    def _identify_topic_patterns(self, reports: List[Dict[str, Any]]) -> List[ResearchPattern]:
        """Identify topic-based patterns in reports."""
        patterns = []
        
        # Extract topics from all reports
        topic_occurrences = defaultdict(list)
        for report in reports:
            topics = self._extract_topics_from_report(report)
            for topic in topics:
                topic_occurrences[topic].append(report)
        
        # Identify patterns (topics appearing multiple times)
        for topic, report_list in topic_occurrences.items():
            if len(report_list) >= 2:  # Must appear at least twice
                pattern = ResearchPattern(
                    pattern_id=f"topic_{hash(topic)}",
                    pattern_type="topic",
                    pattern_name=f"Research focus on '{topic}'",
                    frequency=len(report_list),
                    confidence=min(len(report_list) / 10.0, 1.0),  # Max confidence at 10 occurrences
                    first_occurrence=min(r['created_at'] for r in report_list),
                    last_occurrence=max(r['created_at'] for r in report_list),
                    related_reports=[r['id'] for r in report_list]
                )
                patterns.append(pattern)
        
        return patterns
    
    def _identify_industry_patterns(self, reports: List[Dict[str, Any]]) -> List[ResearchPattern]:
        """Identify industry-based patterns in reports."""
        patterns = []
        
        # Extract industries from all reports
        industry_occurrences = defaultdict(list)
        for report in reports:
            industry = self._extract_industry_from_report(report)
            if industry:
                industry_occurrences[industry].append(report)
        
        # Identify patterns (industries appearing multiple times)
        for industry, report_list in industry_occurrences.items():
            if len(report_list) >= 2:  # Must appear at least twice
                pattern = ResearchPattern(
                    pattern_id=f"industry_{hash(industry)}",
                    pattern_type="industry",
                    pattern_name=f"Industry focus on '{industry}'",
                    frequency=len(report_list),
                    confidence=min(len(report_list) / 5.0, 1.0),  # Max confidence at 5 occurrences
                    first_occurrence=min(r['created_at'] for r in report_list),
                    last_occurrence=max(r['created_at'] for r in report_list),
                    related_reports=[r['id'] for r in report_list]
                )
                patterns.append(pattern)
        
        return patterns
    
    def _identify_temporal_patterns(self, reports: List[Dict[str, Any]]) -> List[ResearchPattern]:
        """Identify temporal patterns in research activity."""
        patterns = []
        
        if len(reports) < 3:
            return patterns
        
        # Group reports by week
        weekly_counts = defaultdict(int)
        for report in reports:
            created_date = datetime.fromisoformat(report['created_at'].replace('Z', '+00:00'))
            week_key = created_date.strftime('%Y-W%U')
            weekly_counts[week_key] += 1
        
        # Identify high-activity periods (weeks with 3+ reports)
        high_activity_weeks = {week: count for week, count in weekly_counts.items() if count >= 3}
        
        if high_activity_weeks:
            pattern = ResearchPattern(
                pattern_id="temporal_high_activity",
                pattern_type="temporal",
                pattern_name="High research activity periods",
                frequency=sum(high_activity_weeks.values()),
                confidence=0.8,
                first_occurrence=min(reports, key=lambda r: r['created_at'])['created_at'],
                last_occurrence=max(reports, key=lambda r: r['created_at'])['created_at'],
                related_reports=[r['id'] for r in reports]
            )
            patterns.append(pattern)
        
        return patterns
    
    def _extract_topic_timeline(self, reports: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract topics with their occurrence timeline."""
        topic_timeline = defaultdict(list)
        
        for report in reports:
            topics = self._extract_topics_from_report(report)
            created_date = datetime.fromisoformat(report['created_at'].replace('Z', '+00:00'))
            
            for topic in topics:
                topic_timeline[topic].append({
                    'date': created_date,
                    'report_id': report['id'],
                    'title': report['title']
                })
        
        return topic_timeline
    
    def _analyze_topic_trend(self, topic: str, occurrences: List[Dict[str, Any]]) -> RecurringTopic:
        """Analyze trend for a specific topic."""
        # Sort occurrences by date
        sorted_occurrences = sorted(occurrences, key=lambda x: x['date'])
        
        # Determine trend direction
        if len(sorted_occurrences) < 3:
            trend_direction = "stable"
            trend_strength = 0.5
        else:
            # Simple trend analysis based on time intervals
            intervals = []
            for i in range(1, len(sorted_occurrences)):
                interval = (sorted_occurrences[i]['date'] - sorted_occurrences[i-1]['date']).days
                intervals.append(interval)
            
            # If intervals are getting shorter, trend is increasing
            if len(intervals) >= 2:
                avg_early = sum(intervals[:len(intervals)//2]) / (len(intervals)//2)
                avg_late = sum(intervals[len(intervals)//2:]) / (len(intervals) - len(intervals)//2)
                
                if avg_late < avg_early * 0.8:
                    trend_direction = "increasing"
                    trend_strength = 0.8
                elif avg_late > avg_early * 1.2:
                    trend_direction = "decreasing"
                    trend_strength = 0.6
                else:
                    trend_direction = "stable"
                    trend_strength = 0.5
            else:
                trend_direction = "stable"
                trend_strength = 0.5
        
        # Extract time periods
        time_periods = [occ['date'].strftime('%Y-%m') for occ in sorted_occurrences]
        
        # Generate related keywords (simplified)
        related_keywords = [topic.lower(), f"{topic} analysis", f"{topic} trends"]
        
        return RecurringTopic(
            topic=topic,
            occurrences=len(occurrences),
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            time_periods=list(set(time_periods)),
            related_keywords=related_keywords
        )
    
    def _calculate_similarity(self, report1: Dict[str, Any], report2: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate similarity between two reports."""
        similarity_score = 0.0
        reasons = []
        
        # Title similarity
        title_sim = SequenceMatcher(None, report1['title'].lower(), report2['title'].lower()).ratio()
        if title_sim > 0.3:
            similarity_score += title_sim * 0.3
            reasons.append(f"Similar titles ({title_sim:.2f})")
        
        # Category similarity
        cat1 = report1.get('category', '').lower()
        cat2 = report2.get('category', '').lower()
        if cat1 and cat2 and cat1 == cat2:
            similarity_score += 0.4
            reasons.append(f"Same category: {cat1}")
        
        # Content similarity (simplified)
        topics1 = set(self._extract_topics_from_report(report1))
        topics2 = set(self._extract_topics_from_report(report2))
        
        if topics1 and topics2:
            topic_overlap = len(topics1.intersection(topics2)) / len(topics1.union(topics2))
            if topic_overlap > 0.2:
                similarity_score += topic_overlap * 0.3
                reasons.append(f"Common topics ({topic_overlap:.2f})")
        
        return min(similarity_score, 1.0), reasons
    
    def _extract_topics_from_report(self, report: Dict[str, Any]) -> List[str]:
        """Extract topics from a report."""
        topics = []
        
        # Extract from title
        title = report.get('title', '')
        if title:
            title_words = [word.strip().lower() for word in title.split() if len(word.strip()) > 3]
            topics.extend(title_words)
        
        # Extract from content
        content = report.get('content', {})
        if isinstance(content, dict):
            # Look for keywords
            for field in ['keywords', 'tags', 'topics']:
                if field in content and isinstance(content[field], list):
                    topics.extend([str(item).lower() for item in content[field]])
        
        # Remove duplicates and filter
        unique_topics = list(set(topics))
        stop_words = {'this', 'that', 'with', 'from', 'they', 'have', 'been', 
                     'will', 'their', 'said', 'each', 'which', 'more', 'than'}
        filtered_topics = [topic for topic in unique_topics 
                         if topic not in stop_words and len(topic) > 2]
        
        return filtered_topics[:10]
    
    def _extract_industry_from_report(self, report: Dict[str, Any]) -> Optional[str]:
        """Extract industry from a report."""
        # Check category field first
        if 'category' in report and report['category']:
            return str(report['category']).strip()
        
        # Check content for industry information
        content = report.get('content', {})
        if isinstance(content, dict):
            if 'industry' in content:
                industry = content['industry']
                if isinstance(industry, str):
                    return industry.strip()
                elif isinstance(industry, dict) and 'name' in industry:
                    return str(industry['name']).strip()
        
        return None
    
    def _generate_trend_summary(self, patterns: List[ResearchPattern], topics: List[RecurringTopic]) -> Dict[str, Any]:
        """Generate a summary of trends."""
        return {
            'total_patterns': len(patterns),
            'pattern_types': {
                'topic': len([p for p in patterns if p.pattern_type == 'topic']),
                'industry': len([p for p in patterns if p.pattern_type == 'industry']),
                'temporal': len([p for p in patterns if p.pattern_type == 'temporal'])
            },
            'recurring_topics_count': len(topics),
            'increasing_trends': len([t for t in topics if t.trend_direction == 'increasing']),
            'stable_trends': len([t for t in topics if t.trend_direction == 'stable']),
            'decreasing_trends': len([t for t in topics if t.trend_direction == 'decreasing']),
            'most_frequent_pattern': patterns[0].pattern_name if patterns else None,
            'strongest_trend': max(topics, key=lambda t: t.trend_strength).topic if topics else None
        }
    
    def _generate_trend_recommendations(self, patterns: List[ResearchPattern], topics: List[RecurringTopic]) -> List[str]:
        """Generate recommendations based on trends."""
        recommendations = []
        
        # Recommendations based on patterns
        if patterns:
            top_pattern = max(patterns, key=lambda p: p.frequency)
            recommendations.append(f"Continue exploring {top_pattern.pattern_name.lower()} - it's your most researched area")
        
        # Recommendations based on increasing trends
        increasing_topics = [t for t in topics if t.trend_direction == 'increasing']
        if increasing_topics:
            top_increasing = max(increasing_topics, key=lambda t: t.trend_strength)
            recommendations.append(f"Deep dive into '{top_increasing.topic}' - your interest is growing")
        
        # Recommendations based on stable topics
        stable_topics = [t for t in topics if t.trend_direction == 'stable' and t.occurrences >= 3]
        if stable_topics:
            recommendations.append("Consider exploring adjacent areas to your stable research topics")
        
        # General recommendations
        if len(patterns) > 3:
            recommendations.append("You have diverse research interests - consider synthesizing insights across areas")
        
        if not recommendations:
            recommendations.append("Continue building your research history to identify meaningful trends")
        
        return recommendations


# Global service instance
report_trend_detection_service = ReportTrendDetectionService()