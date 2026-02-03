"""
Database service for Problem Generator feature.

This module provides database operations for problem statements, analytics,
bookmarks, and likes using the Supabase client.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from src.mint.api.system.core.supabase_client import get_supabase_client, get_service_role_client
from ..models.problem_models import (
    ProblemStatementCreate,
    ProblemStatementUpdate,
    ProblemStatementResponse,
    ProblemStatementSummary,
    ProblemSearchRequest,
    SimilarProblemResponse,
    GenerationAnalyticsCreate,
    GenerationAnalyticsResponse,
    BookmarkCreate,
    BookmarkResponse,
    LikeCreate,
    LikeResponse,
    ProblemCategory,
    SeverityLevel,
    ProblemType,
    TimeHorizon,
    ComplexityLevel
)
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Container for search filters."""
    category: Optional[ProblemCategory] = None
    severity_level: Optional[SeverityLevel] = None
    problem_type: Optional[ProblemType] = None
    time_horizon: Optional[TimeHorizon] = None
    complexity_level: Optional[ComplexityLevel] = None
    target_geography: Optional[List[str]] = None
    min_quality_score: Optional[float] = None


class ProblemDatabaseService:
    """Service for database operations related to problem statements."""
    
    def __init__(self, use_service_role: bool = False):
        """
        Initialize the database service.
        
        Args:
            use_service_role: Whether to use service role client (bypasses RLS)
        """
        self.use_service_role = use_service_role
        self.client = get_service_role_client() if use_service_role else get_supabase_client(use_service_role=False)
    
    # =============================================
    # PROBLEM STATEMENT OPERATIONS
    # =============================================
    
    def create_problem_statement(
        self, 
        user_id: uuid.UUID, 
        problem_data: ProblemStatementCreate,
        embedding: Optional[List[float]] = None
    ) -> Optional[ProblemStatementResponse]:
        """
        Create a new problem statement.
        
        Args:
            user_id: ID of the user creating the problem
            problem_data: Problem statement data
            embedding: Optional vector embedding for similarity search
            
        Returns:
            Created problem statement or None if failed
        """
        try:
            # Prepare data for insertion
            insert_data = {
                "user_id": str(user_id),
                "title": problem_data.title,
                "description": problem_data.description,
                "category": problem_data.category.value,
                "severity_level": problem_data.severity_level.value,
                "target_demographics": problem_data.impact_focus,
                "impact_focus": problem_data.impact_focus,
                "affected_population_size": problem_data.affected_population_size.value if problem_data.affected_population_size else None,
                "problem_type": problem_data.problem_type.value,
                "time_horizon": problem_data.time_horizon.value,
                "complexity_level": problem_data.complexity_level.value,
                "root_causes": problem_data.root_causes,
                "potential_effects": problem_data.potential_effects,
                "stakeholders": problem_data.stakeholders,
                "success_metrics": problem_data.success_metrics,
                "supporting_sources": problem_data.supporting_sources,
                "generation_parameters": problem_data.generation_parameters,
                "generation_model": problem_data.generation_model,
                "embedding": embedding
            }
            
            # Add session_id if provided
            if hasattr(problem_data, 'session_id') and problem_data.session_id:
                insert_data["session_id"] = str(problem_data.session_id)
                logger.info(f"Adding session_id to problem statement: {problem_data.session_id}")
            
            # Add quality_score if provided
            if hasattr(problem_data, 'quality_score') and problem_data.quality_score is not None:
                insert_data["quality_score"] = problem_data.quality_score
            
            # Note: session_rank column doesn't exist in database schema, using created_at for ordering
            
            # Insert into database
            result = self.client.client.table("problem_statements").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created problem statement {result.data[0]['id']} for user {user_id}")
                
                # Prepare response data with required fields
                response_data = result.data[0].copy()
                
                # Add missing required fields with defaults
                response_data.setdefault('validation_feedback', None)
                response_data.setdefault('bookmark_count', 0)
                response_data.setdefault('view_count', 0)
                response_data.setdefault('like_count', 0)
                response_data.setdefault('quality_score', None)
                response_data.setdefault('validation_status', 'pending')
                response_data.setdefault('generation_parameters', {})
                response_data.setdefault('generation_model', 'gpt-4')
                response_data.setdefault('supporting_sources', [])
                
                # Ensure datetime fields are properly formatted
                if 'created_at' in response_data:
                    response_data['generation_timestamp'] = response_data['created_at']
                if 'updated_at' not in response_data:
                    response_data['updated_at'] = response_data.get('created_at')
                
                return ProblemStatementResponse(**response_data)
            else:
                logger.error("Failed to create problem statement: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating problem statement: {str(e)}")
            return None
    
    def get_problem_statement(
        self, 
        problem_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[ProblemStatementResponse]:
        """
        Get a specific problem statement by ID.
        
        Args:
            problem_id: ID of the problem statement
            user_id: ID of the requesting user
            
        Returns:
            Problem statement or None if not found
        """
        try:
            result = self.client.client.table("problem_statements").select("*").eq("id", str(problem_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                # Increment view count
                self._increment_view_count(problem_id)
                return ProblemStatementResponse(**result.data[0])
            else:
                logger.warning(f"Problem statement {problem_id} not found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting problem statement {problem_id}: {str(e)}")
            return None
    
    def update_problem_statement(
        self, 
        problem_id: uuid.UUID, 
        user_id: uuid.UUID, 
        update_data: ProblemStatementUpdate
    ) -> Optional[ProblemStatementResponse]:
        """
        Update an existing problem statement.
        
        Args:
            problem_id: ID of the problem statement
            user_id: ID of the user updating the problem
            update_data: Updated problem statement data
            
        Returns:
            Updated problem statement or None if failed
        """
        try:
            # Prepare update data (only include non-None fields)
            update_dict = {}
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    if hasattr(value, 'value'):  # Handle enum values
                        update_dict[field] = value.value
                    else:
                        update_dict[field] = value
            
            if not update_dict:
                logger.warning("No fields to update")
                return None
            
            # Add updated_at timestamp
            update_dict["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.client.table("problem_statements").update(update_dict).eq("id", str(problem_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Updated problem statement {problem_id} for user {user_id}")
                return ProblemStatementResponse(**result.data[0])
            else:
                logger.error("Failed to update problem statement: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error updating problem statement {problem_id}: {str(e)}")
            return None
    
    def delete_problem_statement(
        self, 
        problem_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> bool:
        """
        Delete a problem statement.
        
        Args:
            problem_id: ID of the problem statement
            user_id: ID of the user deleting the problem
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = self.client.client.table("problem_statements").delete().eq("id", str(problem_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Deleted problem statement {problem_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Problem statement {problem_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting problem statement {problem_id}: {str(e)}")
            return False
    
    def list_user_problems(
        self, 
        user_id: uuid.UUID, 
        limit: int = 20, 
        offset: int = 0,
        filters: Optional[SearchFilters] = None
    ) -> Tuple[List[ProblemStatementSummary], int]:
        """
        List problem statements for a user with optional filtering.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results
            offset: Offset for pagination
            filters: Optional search filters
            
        Returns:
            Tuple of (problem statements, total count)
        """
        try:
            # Build query
            query = self.client.client.table("problem_statements").select(
                "id, title, description, category, severity_level, problem_type, quality_score, like_count, bookmark_count, created_at"
            ).eq("user_id", str(user_id))
            
            # Apply filters
            if filters:
                if filters.category:
                    query = query.eq("category", filters.category.value)
                if filters.severity_level:
                    query = query.eq("severity_level", filters.severity_level.value)
                if filters.problem_type:
                    query = query.eq("problem_type", filters.problem_type.value)
                if filters.time_horizon:
                    query = query.eq("time_horizon", filters.time_horizon.value)
                if filters.complexity_level:
                    query = query.eq("complexity_level", filters.complexity_level.value)
                if filters.min_quality_score:
                    query = query.gte("quality_score", filters.min_quality_score)
                if filters.target_geography:
                    query = query.overlaps("target_geography", filters.target_geography)
            
            # Get total count
            count_result = query.execute()
            total_count = len(count_result.data) if count_result.data else 0
            
            # Get paginated results
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            problems = [ProblemStatementSummary(**item) for item in result.data] if result.data else []
            
            logger.info(f"Retrieved {len(problems)} problems for user {user_id}")
            return problems, total_count
            
        except Exception as e:
            logger.error(f"Error listing problems for user {user_id}: {str(e)}")
            return [], 0
    
    def search_similar_problems(
        self, 
        embedding: List[float], 
        user_id: Optional[uuid.UUID] = None,
        threshold: float = 0.7, 
        limit: int = 10
    ) -> List[SimilarProblemResponse]:
        """
        Search for similar problem statements using vector similarity.
        
        Args:
            embedding: Query embedding vector
            user_id: Optional user ID to filter results
            threshold: Similarity threshold (0-1)
            limit: Maximum number of results
            
        Returns:
            List of similar problem statements
        """
        try:
            # Use the match_problem_statements function
            params = {
                "query_embedding": embedding,
                "user_id_param": str(user_id) if user_id else None,
                "match_threshold": threshold,
                "match_count": limit
            }
            
            result = self.client.client.rpc("match_problem_statements", params).execute()
            
            if result.data:
                similar_problems = [SimilarProblemResponse(**item) for item in result.data]
                logger.info(f"Found {len(similar_problems)} similar problems")
                return similar_problems
            else:
                logger.info("No similar problems found")
                return []
                
        except Exception as e:
            logger.error(f"Error searching similar problems: {str(e)}")
            return []
    
    def _increment_view_count(self, problem_id: uuid.UUID) -> None:
        """
        Increment the view count for a problem statement.
        
        Args:
            problem_id: ID of the problem statement
        """
        try:
            self.client.client.rpc("increment_view_count", {"problem_id": str(problem_id)}).execute()
        except Exception as e:
            logger.debug(f"Failed to increment view count for {problem_id}: {str(e)}")
    
    # =============================================
    # ANALYTICS OPERATIONS
    # =============================================
    
    def create_generation_analytics(
        self, 
        user_id: uuid.UUID, 
        analytics_data: GenerationAnalyticsCreate
    ) -> Optional[GenerationAnalyticsResponse]:
        """
        Create a generation analytics record.
        
        Args:
            user_id: ID of the user
            analytics_data: Analytics data
            
        Returns:
            Created analytics record or None if failed
        """
        try:
            # Convert analytics data to dict and handle UUID serialization
            analytics_dict = analytics_data.model_dump() if hasattr(analytics_data, 'model_dump') else analytics_data.dict()
            
            # Convert UUID objects to strings for JSON serialization
            for key, value in analytics_dict.items():
                if isinstance(value, uuid.UUID):
                    analytics_dict[key] = str(value)
            
            insert_data = {
                "user_id": str(user_id),
                **analytics_dict
            }
            
            result = self.client.client.table("problem_generation_analytics").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created analytics record {result.data[0]['id']} for user {user_id}")
                return GenerationAnalyticsResponse(**result.data[0])
            else:
                logger.error("Failed to create analytics record: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating analytics record: {str(e)}")
            return None
    
    def get_user_analytics_summary(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get analytics summary for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Analytics summary dictionary
        """
        try:
            result = self.client.client.table("problem_generation_analytics").select("*").eq("user_id", str(user_id)).execute()
            
            if not result.data:
                return {
                    "total_sessions": 0,
                    "total_problems_generated": 0,
                    "success_rate": 0.0,
                    "average_generation_time_ms": 0.0,
                    "average_satisfaction_rating": 0.0
                }
            
            analytics = result.data
            total_sessions = len(analytics)
            successful_sessions = sum(1 for a in analytics if a.get("generation_success"))
            total_problems = sum(a.get("problems_generated", 0) for a in analytics)
            
            generation_times = [a.get("generation_time_ms") for a in analytics if a.get("generation_time_ms")]
            avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0.0
            
            satisfaction_ratings = [a.get("user_satisfaction_rating") for a in analytics if a.get("user_satisfaction_rating")]
            avg_satisfaction = sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0.0
            
            return {
                "total_sessions": total_sessions,
                "total_problems_generated": total_problems,
                "success_rate": successful_sessions / total_sessions if total_sessions > 0 else 0.0,
                "average_generation_time_ms": avg_generation_time,
                "average_satisfaction_rating": avg_satisfaction
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics summary for user {user_id}: {str(e)}")
            return {}
    
    # =============================================
    # BOOKMARK OPERATIONS
    # =============================================
    
    def create_bookmark(
        self, 
        user_id: uuid.UUID, 
        problem_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Create a bookmark for a problem statement.
        
        Args:
            user_id: ID of the user
            problem_id: ID of the problem statement
            
        Returns:
            Created bookmark data or None if failed
        """
        try:
            insert_data = {
                "user_id": str(user_id),
                "problem_id": str(problem_id)
            }
            
            result = self.client.client.table("problem_bookmarks").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created bookmark {result.data[0]['id']} for user {user_id}, problem {problem_id}")
                return result.data[0]
            else:
                logger.error("Failed to create bookmark: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating bookmark: {str(e)}")
            return None
    
    def get_bookmark(
        self,
        user_id: uuid.UUID,
        problem_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a bookmark for a specific user and problem.
        
        Args:
            user_id: ID of the user
            problem_id: ID of the problem statement
            
        Returns:
            Bookmark data or None if not found
        """
        try:
            result = self.client.client.table("problem_bookmarks")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .eq("problem_id", str(problem_id))\
                .execute()
            
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting bookmark for user {user_id}, problem {problem_id}: {str(e)}")
            return None
    
    def delete_bookmark(
        self, 
        user_id: uuid.UUID, 
        problem_statement_id: uuid.UUID
    ) -> bool:
        """
        Delete a bookmark.
        
        Args:
            user_id: ID of the user
            problem_statement_id: ID of the problem statement
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = self.client.client.table("problem_bookmarks").delete().eq("user_id", str(user_id)).eq("problem_statement_id", str(problem_statement_id)).execute()
            
            if result.data:
                logger.info(f"Deleted bookmark for problem {problem_statement_id} by user {user_id}")
                return True
            else:
                logger.warning(f"Bookmark not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting bookmark: {str(e)}")
            return False
    
    def get_user_bookmarks(
        self, 
        user_id: uuid.UUID, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[BookmarkResponse]:
        """
        Get bookmarks for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of bookmarks
        """
        try:
            result = self.client.client.table("problem_bookmarks").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            bookmarks = [BookmarkResponse(**item) for item in result.data] if result.data else []
            logger.info(f"Retrieved {len(bookmarks)} bookmarks for user {user_id}")
            return bookmarks
            
        except Exception as e:
            logger.error(f"Error getting bookmarks for user {user_id}: {str(e)}")
            return []
    
    # =============================================
    # LIKE OPERATIONS
    # =============================================
    
    def create_like(
        self, 
        user_id: uuid.UUID, 
        problem_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Create a like for a problem statement.
        
        Args:
            user_id: ID of the user
            problem_id: ID of the problem statement
            
        Returns:
            Created like data or None if failed
        """
        try:
            insert_data = {
                "user_id": str(user_id),
                "problem_id": str(problem_id)
            }
            
            result = self.client.client.table("problem_likes").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created like {result.data[0]['id']} for user {user_id}, problem {problem_id}")
                return result.data[0]
            else:
                logger.error("Failed to create like: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating like: {str(e)}")
            return None
    
    def get_like(
        self,
        user_id: uuid.UUID,
        problem_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a like for a specific user and problem.
        
        Args:
            user_id: ID of the user
            problem_id: ID of the problem statement
            
        Returns:
            Like data or None if not found
        """
        try:
            result = self.client.client.table("problem_likes")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .eq("problem_id", str(problem_id))\
                .execute()
            
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting like for user {user_id}, problem {problem_id}: {str(e)}")
            return None
    
    def delete_like(
        self, 
        user_id: uuid.UUID, 
        problem_statement_id: uuid.UUID
    ) -> bool:
        """
        Delete a like.
        
        Args:
            user_id: ID of the user
            problem_statement_id: ID of the problem statement
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = self.client.client.table("problem_likes").delete().eq("user_id", str(user_id)).eq("problem_statement_id", str(problem_statement_id)).execute()
            
            if result.data:
                logger.info(f"Deleted like for problem {problem_statement_id} by user {user_id}")
                return True
            else:
                logger.warning(f"Like not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting like: {str(e)}")
            return False
    
    def check_user_like(
        self, 
        user_id: uuid.UUID, 
        problem_statement_id: uuid.UUID
    ) -> bool:
        """
        Check if a user has liked a problem statement.
        
        Args:
            user_id: ID of the user
            problem_statement_id: ID of the problem statement
            
        Returns:
            True if user has liked the problem, False otherwise
        """
        try:
            result = self.client.client.table("problem_likes").select("id").eq("user_id", str(user_id)).eq("problem_statement_id", str(problem_statement_id)).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error checking user like: {str(e)}")
            return False

    # =============================================
    # GENERATION HISTORY OPERATIONS
    # =============================================
    
    def create_generation_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        parameters: Dict[str, Any],
        session_name: Optional[str] = None,
        session_description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new generation session.
        
        Args:
            user_id: ID of the user
            session_id: Unique session identifier
            parameters: Generation parameters used
            session_name: Optional session name
            session_description: Optional session description
            
        Returns:
            Created session data or None if failed
        """
        try:
            insert_data = {
                "session_id": str(session_id),
                "user_id": str(user_id),
                "session_name": session_name,
                "session_description": session_description,
                "parameters": parameters,
                "status": "running"
            }
            
            result = self.client.client.table("problem_generation_sessions").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created generation session {session_id} for user {user_id}")
                return result.data[0]
            else:
                logger.error("Failed to create generation session: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating generation session: {str(e)}")
            return None
    
    def update_generation_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a generation session.
        
        Args:
            session_id: Session ID to update
            user_id: ID of the user (for security)
            updates: Dictionary of fields to update
            
        Returns:
            Updated session data or None if failed
        """
        try:
            # Add updated timestamp if completing session
            if updates.get("status") == "completed" and "completed_at" not in updates:
                updates["completed_at"] = datetime.utcnow().isoformat()
            
            result = self.client.client.table("problem_generation_sessions").update(updates).eq("session_id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Updated generation session {session_id}")
                return result.data[0]
            else:
                logger.warning(f"Generation session {session_id} not found for update")
                return None
                
        except Exception as e:
            logger.error(f"Error updating generation session {session_id}: {str(e)}")
            return None
    
    def get_user_generation_history(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get user's generation history.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results
            offset: Offset for pagination
            status_filter: Optional status filter ('completed', 'failed', etc.)
            
        Returns:
            Tuple of (sessions list, total count)
        """
        try:
            # Build query
            query = self.client.client.table("problem_generation_sessions").select("*").eq("user_id", str(user_id))
            
            # Apply status filter
            if status_filter:
                query = query.eq("status", status_filter)
            
            # Get total count
            count_result = query.execute()
            total_count = len(count_result.data) if count_result.data else 0
            
            # Get paginated results
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            sessions = result.data if result.data else []
            
            logger.info(f"Retrieved {len(sessions)} generation sessions for user {user_id}")
            return sessions, total_count
            
        except Exception as e:
            logger.error(f"Error getting generation history for user {user_id}: {str(e)}")
            return [], 0
    
    def get_session_details(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        include_results: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for security)
            include_results: Whether to include generated problems
            
        Returns:
            Session details with optional results
        """
        try:
            # Get session info
            session_result = self.client.client.table("problem_generation_sessions").select("*").eq("session_id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if not session_result.data:
                logger.warning(f"Session {session_id} not found for user {user_id}")
                return None
            
            session_data = session_result.data[0]
            
            if include_results:
                # First check if results are stored in the generation_results JSONB field
                if session_data.get("generation_results") and len(session_data["generation_results"]) > 0:
                    session_data["results"] = session_data["generation_results"]
                    logger.info(f"Found {len(session_data['results'])} results in generation_results JSONB field for session {session_id}")
                else:
                    # Fallback: Get problems directly from problem_statements table
                    logger.info(f"No generation_results found for session {session_id}, falling back to direct problem lookup")
                    
                    problems_result = self.client.client.table("problem_statements")\
                        .select("*")\
                        .eq("session_id", str(session_id))\
                        .order("created_at")\
                        .execute()
                    
                    if problems_result.data:
                        # Transform direct problem data to match expected format
                        session_data["results"] = []
                        for idx, problem in enumerate(problems_result.data):
                            result_item = {
                                "result_id": None,  # No result_id since no generation_results record
                                "rank": idx + 1,  # Use index + 1 as rank since session_rank column doesn't exist
                                "selected": False,
                                "quality_score": problem.get("quality_score"),
                                "viewed": False,
                                "bookmarked": False,
                                "liked": False,
                                "problem_statements": problem
                            }
                            session_data["results"].append(result_item)
                        
                        logger.info(f"Found {len(session_data['results'])} problems directly for session {session_id}")
                    else:
                        session_data["results"] = []
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting session details for {session_id}: {str(e)}")
            return None
    
    def search_sessions_by_parameters(
        self,
        user_id: uuid.UUID,
        search_parameters: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user's sessions by parameter similarity.
        
        Args:
            user_id: User ID
            search_parameters: Parameters to search for
            limit: Maximum number of results
            
        Returns:
            List of similar sessions
        """
        try:
            # Use the database function for parameter-based search
            params = {
                "user_id_param": str(user_id),
                "search_parameters": search_parameters,
                "limit_param": limit
            }
            
            result = self.client.client.rpc("search_sessions_by_parameters", params).execute()
            
            sessions = result.data if result.data else []
            logger.info(f"Found {len(sessions)} similar sessions for user {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Error searching sessions by parameters: {str(e)}")
            return []
    
    def create_generation_result(
        self,
        session_id: uuid.UUID,
        problem_statement_id: uuid.UUID,
        rank: int,
        quality_score: Optional[float] = None,
        selected: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Create a generation result linking a problem to a session.
        
        Args:
            session_id: Session ID
            problem_statement_id: Problem statement ID
            rank: Ranking position in session
            quality_score: Optional quality score
            selected: Whether this result was selected by user
            
        Returns:
            Created result data or None if failed
        """
        try:
            insert_data = {
                "session_id": str(session_id),
                "problem_statement_id": str(problem_statement_id),
                "rank": rank,
                "quality_score": quality_score,
                "selected": selected
            }
            
            logger.info(f"Attempting to insert generation result with data: {insert_data}")
            logger.info(f"Using service role client: {self.client.use_service_role}")
            
            result = self.client.client.table("generation_results").insert(insert_data).execute()
            
            logger.info(f"Insert result: data={bool(result.data)}, count={result.count if hasattr(result, 'count') else 'N/A'}")
            
            if result.data:
                logger.info(f"Created generation result for session {session_id}, problem {problem_statement_id}")
                return result.data[0]
            else:
                logger.error(f"Failed to create generation result: No data returned. Result: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating generation result: {str(e)}")
            logger.error(f"Insert data was: {insert_data}")
            return None
    
    def create_user_favorite(
        self,
        user_id: uuid.UUID,
        favorite_type: str,
        target_id: uuid.UUID,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a user favorite.
        
        Args:
            user_id: User ID
            favorite_type: Type of favorite ('session', 'problem', 'result')
            target_id: ID of the target being favorited
            notes: Optional notes
            tags: Optional tags
            
        Returns:
            Created favorite data or None if failed
        """
        try:
            insert_data = {
                "user_id": str(user_id),
                "favorite_type": favorite_type,
                "notes": notes,
                "tags": tags or []
            }
            
            # Set the appropriate target field based on type
            if favorite_type == "session":
                insert_data["session_id"] = str(target_id)
            elif favorite_type == "problem":
                insert_data["problem_statement_id"] = str(target_id)
            elif favorite_type == "result":
                insert_data["result_id"] = str(target_id)
            else:
                raise ValueError(f"Invalid favorite_type: {favorite_type}")
            
            result = self.client.client.table("user_favorites").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created {favorite_type} favorite for user {user_id}")
                return result.data[0]
            else:
                logger.error("Failed to create user favorite: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user favorite: {str(e)}")
            return None
    
    def get_user_favorites(
        self,
        user_id: uuid.UUID,
        favorite_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's favorites.
        
        Args:
            user_id: User ID
            favorite_type: Optional type filter
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of user favorites
        """
        try:
            query = self.client.client.table("user_favorites").select("*").eq("user_id", str(user_id))
            
            if favorite_type:
                query = query.eq("favorite_type", favorite_type)
            
            result = query.order("saved_at", desc=True).range(offset, offset + limit - 1).execute()
            
            favorites = result.data if result.data else []
            logger.info(f"Retrieved {len(favorites)} favorites for user {user_id}")
            return favorites
            
        except Exception as e:
            logger.error(f"Error getting user favorites: {str(e)}")
            return []
    
    def delete_user_favorite(
        self,
        user_id: uuid.UUID,
        favorite_id: uuid.UUID
    ) -> bool:
        """
        Delete a user favorite.
        
        Args:
            user_id: User ID
            favorite_id: Favorite ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = self.client.client.table("user_favorites").delete().eq("id", str(favorite_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Deleted favorite {favorite_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Favorite {favorite_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user favorite: {str(e)}")
            return False
    
    def delete_problems_by_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> int:
        """
        Delete all problem statements associated with a generation session.
        
        Args:
            user_id: User ID (for security verification)
            session_id: Session ID to delete problems for
            
        Returns:
            Number of problems deleted
        """
        try:
            # First get count of problems to be deleted
            count_result = self.client.client.table("problem_statements")\
                .select("id", count="exact")\
                .eq("user_id", str(user_id))\
                .eq("session_id", str(session_id))\
                .execute()
            
            problems_count = len(count_result.data) if count_result.data else 0
            
            if problems_count == 0:
                logger.info(f"No problems found for session {session_id}")
                return 0
            
            # Delete all problem statements for this session
            result = self.client.client.table("problem_statements")\
                .delete()\
                .eq("user_id", str(user_id))\
                .eq("session_id", str(session_id))\
                .execute()
            
            logger.info(f"Deleted {problems_count} problem statements for session {session_id}")
            return problems_count
            
        except Exception as e:
            logger.error(f"Error deleting problems for session {session_id}: {str(e)}")
            return 0
    
    def delete_generation_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> bool:
        """
        Delete a generation session record.
        
        Args:
            user_id: User ID (for security verification)
            session_id: Session ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Delete the session record
            result = self.client.client.table("problem_generation_sessions")\
                .delete()\
                .eq("session_id", str(session_id))\
                .eq("user_id", str(user_id))\
                .execute()
            
            if result.data:
                logger.info(f"Deleted generation session {session_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting generation session {session_id}: {str(e)}")
            return False
    
    def search_problems_by_description(
        self,
        user_id: uuid.UUID,
        search_query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user's problem statements by description content.
        
        Args:
            user_id: User ID
            search_query: Query to search for in descriptions
            limit: Maximum number of results
            
        Returns:
            List of matching problem statements
        """
        try:
            # Use ilike for case-insensitive search with wildcards
            search_pattern = f"%{search_query}%"
            
            result = self.client.client.table("problem_statements")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .ilike("description", search_pattern)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            problems = result.data if result.data else []
            logger.info(f"Found {len(problems)} problems matching '{search_query}' for user {user_id}")
            return problems
            
        except Exception as e:
            logger.error(f"Error searching problems by description for user {user_id}: {str(e)}")
            return []