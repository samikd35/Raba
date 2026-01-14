"""RABA Supabase Service.

Provides async Supabase client wrapper for database and storage operations.
"""

from typing import Any, Optional

from supabase import Client, create_client

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance.
    
    Returns:
        Supabase client
        
    Raises:
        ValueError: If Supabase URL or key not configured
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    if not settings.supabase_url or not settings.supabase_key:
        logger.error("Supabase URL or key not configured")
        raise ValueError("Supabase URL and key must be configured")
    
    logger.info("Initializing Supabase client...")
    _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    logger.info("Supabase client initialized successfully")
    
    return _supabase_client


class WorkflowRepository:
    """Repository for workflow database operations."""
    
    TABLE_NAME = "workflows"
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize repository with Supabase client."""
        self._client = client
        self._logger = get_logger(f"{__name__}.WorkflowRepository")
    
    @property
    def client(self) -> Client:
        """Get Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client
    
    async def create(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new workflow record.
        
        Args:
            workflow_data: Workflow data to insert
            
        Returns:
            Created workflow record
        """
        self._logger.info(f"Creating workflow with topic: {workflow_data.get('topic', 'N/A')[:50]}...")
        
        response = self.client.table(self.TABLE_NAME).insert(workflow_data).execute()
        
        if response.data:
            self._logger.info(f"Workflow created with ID: {response.data[0].get('id')}")
            return response.data[0]
        
        self._logger.error("Failed to create workflow - no data returned")
        raise ValueError("Failed to create workflow")
    
    async def get_by_id(self, workflow_id: str) -> Optional[dict[str, Any]]:
        """
        Get workflow by ID.
        
        Args:
            workflow_id: Workflow UUID
            
        Returns:
            Workflow record or None
        """
        self._logger.info(f"Fetching workflow: {workflow_id}")
        
        response = self.client.table(self.TABLE_NAME).select("*").eq("id", workflow_id).execute()
        
        if response.data:
            self._logger.info(f"Workflow found: {workflow_id}")
            return response.data[0]
        
        self._logger.warning(f"Workflow not found: {workflow_id}")
        return None
    
    async def update(self, workflow_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Update workflow by ID.
        
        Args:
            workflow_id: Workflow UUID
            updates: Fields to update
            
        Returns:
            Updated workflow record or None
        """
        self._logger.info(f"Updating workflow: {workflow_id}")
        
        response = (
            self.client.table(self.TABLE_NAME)
            .update(updates)
            .eq("id", workflow_id)
            .execute()
        )
        
        if response.data:
            self._logger.info(f"Workflow updated: {workflow_id}")
            return response.data[0]
        
        self._logger.warning(f"Failed to update workflow: {workflow_id}")
        return None
    
    async def update_status(self, workflow_id: str, status: str) -> Optional[dict[str, Any]]:
        """
        Update workflow status.
        
        Args:
            workflow_id: Workflow UUID
            status: New status
            
        Returns:
            Updated workflow record
        """
        self._logger.info(f"Updating workflow {workflow_id} status to: {status}")
        return await self.update(workflow_id, {"status": status})


def get_workflow_repository() -> WorkflowRepository:
    """Get WorkflowRepository instance."""
    return WorkflowRepository()
