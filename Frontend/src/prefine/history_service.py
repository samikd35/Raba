"""
History service for Problem Refiner feature.

This module provides high-level history operations for the problem refiner,
including session management and result retrieval.
"""

import uuid
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .database_service import ProblemRefinerDatabaseService

logger = logging.getLogger(__name__)


class ProblemRefinerHistoryService:
    """Service for managing problem refiner history operations."""
    
    def __init__(self):
        """Initialize the history service."""
        self.db_service = ProblemRefinerDatabaseService()
    
    def get_user_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get user's refiner session history.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results
            offset: Offset for pagination
            status_filter: Optional status filter
            
        Returns:
            Tuple of (sessions list, total count)
        """
        try:
            return self.db_service.get_user_refiner_history(
                user_id=uuid.UUID(user_id),
                limit=limit,
                offset=offset,
                status_filter=status_filter
            )
        except Exception as e:
            logger.error(f"Error getting user history: {str(e)}")
            return [], 0
    
    def get_session_details(
        self,
        session_id: str,
        user_id: str,
        include_results: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for security)
            include_results: Whether to include problem statements
            
        Returns:
            Session details with optional results
        """
        try:
            return self.db_service.get_refiner_session_details(
                session_id=uuid.UUID(session_id),
                user_id=uuid.UUID(user_id)
            )
        except Exception as e:
            logger.error(f"Error getting session details: {str(e)}")
            return None
    
    def mark_result_researched(
        self,
        result_id: str,
        user_id: str
    ) -> bool:
        """
        Mark a session as researched when user clicks to research.
        
        Args:
            result_id: Session ID (treating as session for problem refiner)
            user_id: User ID (for security)
            
        Returns:
            True if updated successfully
        """
        try:
            return self.db_service.update_research_status(
                session_id=uuid.UUID(result_id),
                user_id=uuid.UUID(user_id),
                researched=True
            )
        except Exception as e:
            logger.error(f"Error marking session as researched: {str(e)}")
            return False
    
    def get_analytics_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get analytics summary for a user's refiner usage.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Analytics summary dictionary
        """
        try:
            return self.db_service.get_user_refiner_analytics_summary(
                user_id=uuid.UUID(user_id)
            )
        except Exception as e:
            logger.error(f"Error getting analytics summary: {str(e)}")
            return {}
    
    def transform_session_for_frontend(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform session data for frontend consumption.
        
        Args:
            session_data: Raw session data from database
            
        Returns:
            Transformed session data
        """
        try:
            # Transform results if present
            results = session_data.get('results', [])
            transformed_results = []
            
            for result in results:
                transformed_result = {
                    'id': result.get('result_id'),
                    'stakeholder': result.get('stakeholder'),
                    'statement': result.get('statement'),
                    'assumptions': result.get('assumptions', []),
                    'overall_score': result.get('overall_score'),
                    'rank': result.get('rank'),
                    'selected': result.get('selected', False),
                    'researched': result.get('researched', False)
                }
                transformed_results.append(transformed_result)
            
            # Transform session data using ACTUAL table column names
            transformed_session = {
                'session_id': session_data.get('id'),  # Use 'id' as session_id
                'session_title': session_data.get('session_title'),
                'original_idea': session_data.get('original_idea'),
                'status': session_data.get('status'),
                'created_at': session_data.get('created_at'),
                'completed_at': session_data.get('completed_at'),
                'problems_generated': len(session_data.get('problem_statements', [])) if session_data.get('problem_statements') else 0,
                'generation_success': session_data.get('status') == 'completed',
                'generation_time_ms': session_data.get('processing_time_seconds', 0) * 1000 if session_data.get('processing_time_seconds') else None,
                'results': transformed_results
            }
            
            return transformed_session
            
        except Exception as e:
            logger.error(f"Error transforming session data: {str(e)}")
            return session_data
    
    def search_sessions_by_idea(
        self,
        user_id: str,
        search_query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user's sessions by original idea content.
        
        Args:
            user_id: ID of the user
            search_query: Search query to match against original ideas
            limit: Maximum number of results
            
        Returns:
            List of matching sessions
        """
        try:
            # Get all user sessions
            sessions, _ = self.db_service.get_user_refiner_history(
                user_id=uuid.UUID(user_id),
                limit=100,  # Get more for searching
                offset=0
            )
            
            # Simple text search in original ideas and session titles
            search_lower = search_query.lower()
            matching_sessions = []
            
            for session in sessions:
                original_idea = session.get('original_idea', '').lower()
                session_title = session.get('session_title', '').lower()
                
                if search_lower in original_idea or search_lower in session_title:
                    matching_sessions.append(session)
                    
                if len(matching_sessions) >= limit:
                    break
            
            return matching_sessions
            
        except Exception as e:
            logger.error(f"Error searching sessions: {str(e)}")
            return []
    
    # Additional methods needed by the router
    async def store_refinement_result(
        self,
        user_id: str,
        original_idea: str,
        refined_idea: str,
        refinement_type: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store refinement result in database.
        
        Args:
            user_id: User ID
            original_idea: Original idea text
            refined_idea: Refined idea text
            refinement_type: Type of refinement
            context: Context data
            metadata: Additional metadata
            
        Returns:
            True if stored successfully
        """
        try:
            # Create a session for this refinement
            session_title = self.db_service.generate_session_title(original_idea)
            session = self.db_service.create_refiner_session(
                user_id=uuid.UUID(user_id),
                session_title=session_title,
                original_idea=original_idea,
                parsed_context=context
            )
            
            if session:
                # Save the refined results
                results_data = {
                    "problem_statements": [{"statement": refined_idea}],
                    "metadata": metadata,
                    "refinement_type": refinement_type
                }
                
                return self.db_service.save_refiner_results(
                    session_id=uuid.UUID(session["id"]),
                    user_id=uuid.UUID(user_id),
                    results_data=results_data
                )
            return False
            
        except Exception as e:
            logger.error(f"Error storing refinement result: {str(e)}")
            return False
    
    async def update_researched_status(
        self,
        result_id: str,
        researched: bool,
        research_notes: str = None
    ) -> bool:
        """
        Update researched status for a session.
        
        Args:
            result_id: Session ID
            researched: Whether researched
            research_notes: Research notes
            
        Returns:
            True if updated successfully
        """
        try:
            # For problem refiner, we need user_id but don't have it here
            # This is a limitation of the current API design
            logger.warning("update_researched_status called without user_id - this may fail")
            return False
        except Exception as e:
            logger.error(f"Error updating researched status: {str(e)}")
            return False
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get user analytics (async wrapper for compatibility).
        
        Args:
            user_id: User ID
            
        Returns:
            Analytics data
        """
        return self.get_analytics_summary(user_id)
    
    async def search_refinements(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search refinements (async wrapper for compatibility).
        
        Args:
            user_id: User ID
            query: Search query
            limit: Result limit
            
        Returns:
            Search results
        """
        results = self.search_sessions_by_idea(user_id, query, limit)
        return {
            "results": results,
            "total_count": len(results),
            "search_time_ms": 0
        }
