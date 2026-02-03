"""
Database service for Problem Refiner feature.

This module provides database operations for problem refiner sessions, results,
and analytics using the Supabase client.
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from src.mint.api.system.core.supabase_client import get_supabase_client, get_service_role_client

logger = logging.getLogger(__name__)

# PERFORMANCE OPTIMIZATION: Columns needed for list view only
# Excludes large JSONB fields: problem_statements, problem_scores, interview_questions, validation_cues, refined_variants, parsed_context
HISTORY_LIST_COLUMNS = "id, tenant_id, user_id, session_title, original_idea, status, researched, research_notes, processing_time_seconds, metadata, created_at, updated_at, completed_at"


class ProblemRefinerDatabaseService:
    """Service for database operations related to problem refiner."""
    
    def __init__(self, use_service_role: bool = True):
        """
        Initialize the database service with Supabase client.
        
        Args:
            use_service_role: Whether to use service role client (bypasses RLS)
        """
        self.use_service_role = use_service_role
        self.client = get_service_role_client() if use_service_role else get_supabase_client(use_service_role=False)
    
    # =============================================
    # SESSION OPERATIONS
    # =============================================
    
    def create_refiner_session(
        self,
        user_id: uuid.UUID,
        session_title: str,
        original_idea: str,
        parsed_context: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new problem refiner session.
        
        Args:
            user_id: ID of the user
            session_title: Short summary of the original idea
            original_idea: The raw idea input by user
            parsed_context: Optional parsed context from the idea
            
        Returns:
            Created session data or None if failed
        """
        try:
            # OLD CODE - REMOVED - This was using wrong schema
            # This code block was using documented schema that doesn't match actual table
            
            # Generate a unique session_id as per schema
            import uuid
            session_uuid = str(uuid.uuid4())
            
            # Try to get user's actual tenant_id from tenant_memberships
            actual_tenant_id = None
            if tenant_id is not None:
                actual_tenant_id = str(tenant_id)
            else:
                # Try to get user's tenant from tenant_memberships
                try:
                    tenant_result = self.client.client.table("tenant_memberships") \
                        .select("tenant_id") \
                        .eq("user_id", str(user_id)) \
                        .eq("is_active", True) \
                        .execute()
                    
                    if tenant_result.data:
                        actual_tenant_id = tenant_result.data[0]["tenant_id"]
                        logger.info(f"Found user's tenant: {actual_tenant_id}")
                    else:
                        logger.warning(f"No active tenant found for user {user_id}")
                except Exception as tenant_error:
                    logger.error(f"Error getting user's tenant: {tenant_error}")
            
            # Prepare insert data matching the ACTUAL table schema from tables.sql
            # Real columns: id, tenant_id, user_id, session_title, original_idea, status, parsed_context, etc.
            insert_data = {
                "user_id": str(user_id),
                "session_title": session_title,  # Use session_title, not session_id
                "original_idea": original_idea,  # Use original_idea, not original_problem
                "status": "running",  # Default status per table schema
                "parsed_context": parsed_context or {}
            }
            
            # Only add tenant_id if we found a valid one
            if actual_tenant_id:
                insert_data["tenant_id"] = actual_tenant_id
            
            logger.info(f"Creating refiner session with EXACT schema data: {insert_data}")
            result = self.client.client.table("problem_refiner_sessions").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created refiner session {result.data[0]['id']} for user {user_id}")
                return result.data[0]
            else:
                logger.error("Failed to create refiner session: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating refiner session: {str(e)}")
            logger.error(f"Insert data was: {insert_data}")
            # Log the full exception details
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def update_refiner_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a problem refiner session.
        
        Args:
            session_id: Session ID to update
            user_id: ID of the user (for security)
            updates: Dictionary of fields to update
            
        Returns:
            Updated session data or None if failed
        """
        try:
            # Add completed timestamp if completing session
            if updates.get("status") == "completed" and "completed_at" not in updates:
                updates["completed_at"] = datetime.utcnow().isoformat()
            
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.client.table("problem_refiner_sessions").update(updates).eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Updated refiner session {session_id}")
                return result.data[0]
            else:
                logger.warning(f"No refiner session found to update: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating refiner session: {str(e)}")
            return None
    
    def get_user_refiner_history(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get user's refiner session history.
        
        PERFORMANCE OPTIMIZED:
        - Selective column fetching (excludes large JSONB fields)
        - Combined count with main query (single round-trip)
        - Debug queries gated behind environment variable
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results
            offset: Offset for pagination
            status_filter: Optional status filter ('completed', 'failed', etc.)
            
        Returns:
            Tuple of (sessions list, total count)
        """
        try:
            # DEBUG MODE: Only run expensive debug queries when explicitly enabled
            debug_mode = os.environ.get("REFINER_HISTORY_DEBUG", "false").lower() == "true"
            if debug_mode:
                logger.info(f"🔍 DEBUG MODE ENABLED - Running diagnostic queries")
                debug_query = self.client.client.table("problem_refiner_sessions") \
                    .select("id, user_id, session_title, status, created_at") \
                    .limit(10).execute()
                logger.info(f"DEBUG: Found {len(debug_query.data) if debug_query.data else 0} total sessions in table")
                if debug_query.data:
                    for session in debug_query.data[:3]:
                        logger.info(f"DEBUG: Session - user_id: {session.get('user_id')}, status: {session.get('status')}")
            
            # PERFORMANCE OPTIMIZATION: Build query with selective columns and count in same request
            # Excludes large JSONB fields: problem_statements, problem_scores, interview_questions, 
            # validation_cues, refined_variants, parsed_context
            query = self.client.client.table("problem_refiner_sessions") \
                .select(HISTORY_LIST_COLUMNS, count="exact") \
                .eq("user_id", str(user_id))
            
            # Apply status filter
            if status_filter:
                query = query.eq("status", status_filter)
                if debug_mode:
                    logger.info(f"DEBUG: Applied status filter: {status_filter}")
            
            # Apply sorting and pagination
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            # Execute single query with count (eliminates separate count query)
            result = query.execute()
            
            # Get count from the same response (no extra round-trip)
            total_count = result.count if result.count is not None else len(result.data) if result.data else 0
            sessions = result.data if result.data else []
            
            logger.info(f"Retrieved {len(sessions)} refiner sessions (total: {total_count}) for user {user_id}")
            
            # Debug logging only when enabled
            if debug_mode and sessions:
                logger.info(f"📤 FINAL RESULT for user {user_id}: Returning {len(sessions)} sessions")
            
            return sessions, total_count
            
        except Exception as e:
            logger.error(f"Error getting refiner history for user {user_id}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return [], 0
    
    def get_refiner_session_details(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific refiner session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for security)
            
        Returns:
            Complete session details including all results
        """
        try:
            # Get session info (single table contains everything)
            session_result = self.client.client.table("problem_refiner_sessions").select("*").eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if not session_result.data:
                logger.warning(f"Refiner session {session_id} not found for user {user_id}")
                return None
            
            session_data = session_result.data[0]
            logger.info(f"Retrieved refiner session details for {session_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting refiner session details {session_id}: {str(e)}")
            return None
    
    # =============================================
    # RESULTS OPERATIONS (Single Table)
    # =============================================
    
    def save_refiner_results(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        results_data: Dict[str, Any]
    ) -> bool:
        """
        Save problem refiner results to the session (single table).
        
        Args:
            session_id: Session ID
            user_id: User ID (for security)
            results_data: Dictionary containing problem_statements, scores, etc.
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create refined problem summary from problem statements
            problem_statements = results_data.get("problem_statements", [])
            refined_problem_summary = ""
            if problem_statements:
                # Create a summary of the refined problems
                refined_problem_summary = "; ".join([
                    f"{stmt.get('stakeholder', 'Unknown')}: {stmt.get('statement', '')}"
                    for stmt in problem_statements[:3]  # Take first 3 statements
                ])
            
            # Update the session with results using ACTUAL table schema from tables.sql
            # Real columns: problem_statements, problem_scores, interview_questions, validation_cues, etc.
            update_data = {
                "problem_statements": results_data.get("problem_statements"),  # ✅ Direct JSONB column
                "problem_scores": results_data.get("problem_scores"),          # ✅ Direct JSONB column
                "interview_questions": results_data.get("interview_questions"), # ✅ Direct JSONB column
                "validation_cues": results_data.get("validation_cues"),        # ✅ Direct JSONB column
                "refined_variants": results_data.get("refined_variants"),      # ✅ Direct JSONB column
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            result = self.client.client.table("problem_refiner_sessions").update(update_data).eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Saved refiner results for session {session_id}")
                return True
            else:
                logger.error("Failed to save refiner results: No data returned")
                return False
                
        except Exception as e:
            logger.error(f"Error saving refiner results for session {session_id}: {str(e)}")
            return False
    
    def update_research_status(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        researched: bool = True,
        research_notes: Optional[str] = None
    ) -> bool:
        """
        Update research status for a session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for security)
            researched: Whether the session has been researched
            research_notes: Optional research notes
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            update_data = {
                "researched": researched,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if research_notes is not None:
                update_data["research_notes"] = research_notes
            
            result = self.client.client.table("problem_refiner_sessions").update(update_data).eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if result.data:
                logger.info(f"Updated research status for session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for research status update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating research status: {str(e)}")
            return False
    
    # =============================================
    # ANALYTICS OPERATIONS
    # =============================================
    
    def create_refiner_analytics(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        analytics_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create analytics record for a refiner session.
        
        Args:
            user_id: ID of the user
            session_id: Session ID
            analytics_data: Analytics data (idea_length, generation_time_ms, etc.)
            
        Returns:
            Created analytics record or None if failed
        """
        try:
            insert_data = {
                "user_id": str(user_id),
                "session_id": str(session_id),
                **analytics_data
            }
            
            result = self.client.client.table("problem_refiner_analytics").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"Created refiner analytics for session {session_id}")
                return result.data[0]
            else:
                logger.error("Failed to create refiner analytics: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating refiner analytics: {str(e)}")
            return None
    
    def get_user_refiner_analytics_summary(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get analytics summary for a user's refiner usage.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Analytics summary dictionary
        """
        try:
            # Get session statistics
            sessions_result = self.client.client.table("problem_refiner_sessions").select("*").eq("user_id", str(user_id)).execute()
            
            if not sessions_result.data:
                return {
                    "total_sessions": 0,
                    "total_problems_generated": 0,
                    "success_rate": 0.0,
                    "average_generation_time_ms": 0.0
                }
            
            sessions = sessions_result.data
            total_sessions = len(sessions)
            
            # Calculate metrics from actual table data
            successful_sessions = sum(1 for s in sessions if s.get("status") == "completed")
            total_problems = sum(len(s.get("problem_statements", [])) if s.get("problem_statements") else 0 for s in sessions)
            
            # Convert processing_time_seconds to milliseconds
            generation_times = [s.get("processing_time_seconds", 0) * 1000 for s in sessions if s.get("processing_time_seconds")]
            avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0.0
            
            return {
                "total_sessions": total_sessions,
                "total_problems_generated": total_problems,
                "success_rate": successful_sessions / total_sessions if total_sessions > 0 else 0.0,
                "average_generation_time_ms": avg_generation_time
            }
            
        except Exception as e:
            logger.error(f"Error getting refiner analytics summary for user {user_id}: {str(e)}")
            return {}
    
    # =============================================
    # UTILITY FUNCTIONS
    # =============================================
    
    def generate_session_title(self, original_idea: str, max_length: int = 50) -> str:
        """
        Generate a short session title from the original idea.
        
        Args:
            original_idea: The original idea text
            max_length: Maximum length of the title
            
        Returns:
            Generated session title
        """
        # Clean and truncate the idea
        cleaned_idea = original_idea.strip()
        
        # Take first sentence or first max_length characters
        if '.' in cleaned_idea:
            first_sentence = cleaned_idea.split('.')[0]
            if len(first_sentence) <= max_length:
                return first_sentence
        
        # Truncate and add ellipsis if needed
        if len(cleaned_idea) <= max_length:
            return cleaned_idea
        else:
            return cleaned_idea[:max_length-3] + "..."
