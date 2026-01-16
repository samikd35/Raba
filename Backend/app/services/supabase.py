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

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List workflows with pagination and filtering.
        
        Args:
            limit: Max records to return
            offset: Records to skip
            status_filter: Optional status filter
            
        Returns:
            Dict with 'data' (list) and 'count' (int)
        """
        query = self.client.table(self.TABLE_NAME).select("*", count="exact")
        
        if status_filter and status_filter.lower() != "all":
            query = query.eq("status", status_filter)
            
        # Order by creation date descending
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        
        return {
            "data": response.data,
            "count": response.count
        }

    async def delete(self, workflow_id: str) -> bool:
        """
        Delete workflow by ID.
        
        Args:
            workflow_id: Workflow UUID
            
        Returns:
            True if deleted
        """
        self._logger.info(f"Deleting workflow: {workflow_id}")
        self.client.table(self.TABLE_NAME).delete().eq("id", workflow_id).execute()
        return True


def get_workflow_repository() -> WorkflowRepository:
    """Get WorkflowRepository instance."""
    return WorkflowRepository()


class SupabaseService:
    """
    Unified Supabase service for database and storage operations.
    
    Reference: PHASE2_3_DEEP_RESEARCH_PLAN.md
    """
    
    STORAGE_BUCKET = "media"  # Single bucket for all media files
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._workflow_repo: Optional[WorkflowRepository] = None
        self._logger = get_logger(f"{__name__}.SupabaseService")
        self._bucket_verified: set[str] = set()  # Track verified buckets
    
    @property
    def client(self) -> Client:
        """Get Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client
    
    @property
    def workflows(self) -> WorkflowRepository:
        """Get workflow repository."""
        if self._workflow_repo is None:
            self._workflow_repo = WorkflowRepository(self.client)
        return self._workflow_repo
    
    async def update_workflow(
        self,
        workflow_id: str,
        updates: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Update a workflow record."""
        return await self.workflows.update(workflow_id, updates)
    
    async def _ensure_bucket_exists(self, bucket: str) -> bool:
        """
        Ensure the storage bucket exists, create if it doesn't.
        
        Args:
            bucket: Bucket name to verify/create
            
        Returns:
            True if bucket exists or was created, False otherwise
        """
        if bucket in self._bucket_verified:
            return True
        
        try:
            # Use list_buckets to check if bucket exists
            buckets = self.client.storage.list_buckets()
            bucket_names = [b.name for b in buckets] if buckets else []
            
            if bucket in bucket_names:
                self._bucket_verified.add(bucket)
                self._logger.info(f"Storage bucket '{bucket}' verified")
                return True
            
            # Bucket doesn't exist, try to create it
            self._logger.info(f"Bucket '{bucket}' not found, creating...")
            self.client.storage.create_bucket(
                bucket,
                options={
                    "public": True,
                    "file_size_limit": 52428800,  # 50MB
                    "allowed_mime_types": [
                        "image/jpeg", "image/png", "image/webp", "image/gif",
                        "video/mp4", "video/webm", "audio/mpeg", "audio/wav"
                    ]
                }
            )
            self._bucket_verified.add(bucket)
            self._logger.info(f"Storage bucket '{bucket}' created successfully")
            return True
            
        except Exception as e:
            error_str = str(e)
            # Check if bucket already exists (race condition or API quirk)
            if "already exists" in error_str.lower() or "duplicate" in error_str.lower():
                self._bucket_verified.add(bucket)
                self._logger.info(f"Storage bucket '{bucket}' already exists")
                return True
            
            self._logger.error(f"Failed to ensure bucket '{bucket}' exists: {e}")
            return False
    
    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """
        Upload file to Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            file_data: File bytes
            content_type: MIME type
            
        Returns:
            Public URL if successful, None otherwise
        """
        # Ensure bucket exists before upload
        if not await self._ensure_bucket_exists(bucket):
            self._logger.warning(f"Bucket '{bucket}' not available, skipping upload")
            return None
        
        try:
            self._logger.info(f"Uploading to {bucket}/{path}")
            
            self.client.storage.from_(bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": content_type},
            )
            
            public_url = self.client.storage.from_(bucket).get_public_url(path)
            self._logger.info(f"Upload successful: {path}")
            return public_url
            
        except Exception as e:
            self._logger.error(f"Upload failed: {e}")
            return None


_supabase_service: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    """Get singleton SupabaseService instance."""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
