"""
Conversation history management for MIntel.

This module handles storing and retrieving conversation history, including initial queries,
follow-up questions, and answers in Supabase.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .supabase_client import SupabaseClient, get_service_role_client, get_standard_client

# Configure logging
logger = logging.getLogger(__name__)

class ConversationHistoryManager:
    """Manager for conversation history operations."""
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """
        Initialize the conversation history manager.
        
        Args:
            supabase_client: Optional SupabaseClient instance. If None, a new one will be created.
        """
        self.supabase = supabase_client or get_standard_client()
        self.history_table = "mint_conversation_history"
        
    async def store_initial_query(self, session_id: str, query: str, user_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Store the initial query for a research session.
        
        Args:
            session_id: The session ID.
            query: The initial user query.
            user_id: The user ID from auth context.
            metadata: Optional metadata about the query.
            
        Returns:
            The ID of the stored history record, or None if storage failed.
        """
        try:
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": "initial_query",
                "content": query,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Build the query
            query = self.supabase.client.table(self.history_table).insert(data)
            
            # Execute the query
            response = query.execute()
            
            if not response.data or len(response.data) == 0:
                logger.error(f"Error storing initial query: {response.error}")
                return None
            
            record_id = response.data[0]["id"]
            logger.info(f"Stored initial query with ID: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error storing initial query: {str(e)}")
            return None
            
    async def store_follow_up_question(self, session_id: str, question: str, user_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Store a follow-up question in the conversation history.
        
        Args:
            session_id: The session ID.
            question: The follow-up question.
            user_id: The user ID from auth context.
            metadata: Optional metadata about the question.
            
        Returns:
            The ID of the stored history record, or None if storage failed.
        """
        try:
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": "follow_up_question",
                "content": question,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Build the query
            query = self.supabase.client.table(self.history_table).insert(data)
            
            # Execute the query
            response = query.execute()
            
            if not response.data or len(response.data) == 0:
                logger.error(f"Error storing follow-up question: {response.error}")
                return None
            
            record_id = response.data[0]["id"]
            logger.info(f"Stored follow-up question with ID: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error storing follow-up question: {str(e)}")
            return None
            
    async def store_answer(self, session_id: str, answer: str, user_id: str = None, related_to_question_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Store an answer in the conversation history.
        
        Args:
            session_id: The session ID.
            answer: The answer content.
            user_id: The user ID from auth context.
            related_to_question_id: Optional ID of the question this answer relates to.
            metadata: Optional metadata about the answer.
            
        Returns:
            The ID of the stored history record, or None if storage failed.
        """
        try:
            metadata = metadata or {}
            if related_to_question_id:
                metadata["related_to_question_id"] = related_to_question_id
                
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": "answer",
                "content": answer,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            # Build the query
            query = self.supabase.client.table(self.history_table).insert(data)
            
            # Execute the query
            response = query.execute()
            
            if not response.data or len(response.data) == 0:
                logger.error(f"Error storing answer: {response.error}")
                return None
            
            record_id = response.data[0]["id"]
            logger.info(f"Stored answer with ID: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error storing answer: {str(e)}")
            return None
    
    async def store_clarification(self, session_id: str, clarification: str, user_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Store a clarification request or response in the conversation history.
        
        Args:
            session_id: The session ID.
            clarification: The clarification content.
            user_id: The user ID from auth context.
            metadata: Optional metadata about the clarification.
            
        Returns:
            The ID of the stored history record, or None if storage failed.
        """
        try:
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": "clarification",
                "content": clarification,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Build the query
            query = self.supabase.client.table(self.history_table).insert(data)
            
            # Execute the query
            response = query.execute()
            
            if not response.data or len(response.data) == 0:
                logger.error(f"Error storing clarification: {response.error}")
                return None
            
            record_id = response.data[0]["id"]
            logger.info(f"Stored clarification with ID: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error storing clarification: {str(e)}")
            return None
    
    async def get_conversation_history(self, session_id: str, user_id: str = None) -> List[Dict[str, Any]]:
        """
        Get the full conversation history for a session.
        
        Args:
            session_id: The session ID.
            user_id: Optional user ID for additional filtering and security.
            
        Returns:
            A list of conversation history items, ordered by timestamp, or empty list if none found.
        """
        try:
            # Build the query
            query = self.supabase.client.table(self.history_table)\
                .select("*")\
                .eq("session_id", session_id)
            
            # Add user_id filter if provided for additional security
            if user_id:
                query = query.eq("user_id", user_id)
                
            query = query.order("timestamp", desc=False)  # Oldest first
                
            # Execute the query
            response = query.execute()
            
            if not response.data:
                logger.info(f"No conversation history found for session: {session_id}")
                return []
            
            return response.data
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
            
    async def get_conversation_thread(self, session_id: str, user_id: str = None, message_types: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get conversation history organized by message type.
        
        Args:
            session_id: The session ID.
            user_id: Optional user ID for additional filtering and security.
            message_types: Optional list of message types to filter by.
            
        Returns:
            Dictionary with message types as keys and lists of messages as values.
        """
        history = await self.get_conversation_history(session_id, user_id)
        
        if not history:
            return {}
            
        # Filter by message type if specified
        if message_types:
            history = [item for item in history if item.get("message_type") in message_types]
            
        # Organize by message type
        result = {}
        for item in history:
            msg_type = item.get("message_type")
            if msg_type not in result:
                result[msg_type] = []
            result[msg_type].append(item)
            
        return result
