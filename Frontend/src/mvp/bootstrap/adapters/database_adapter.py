"""
Bootstrap Database Adapter

Handles all database operations for the bootstrap workflow including
project creation, status updates, and enhanced context storage.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid
import json
import time

from src.mint.api.system.core.supabase_client import get_service_role_client

logger = logging.getLogger(__name__)


class BootstrapDatabaseAdapter:
    """
    Database adapter for Module 3 Bootstrap operations.
    
    Follows patterns from src/mvp/adapters/database_adapter.py
    """
    
    def __init__(self, use_service_role: bool = True):
        """Initialize with Supabase client."""
        self.supabase = get_service_role_client()
        logger.info("Bootstrap Database Adapter initialized")
    
    async def create_bootstrap_project(
        self,
        tenant_id: str,
        user_id: str,
        project_name: str,
        idea_text: Optional[str] = None,
        file_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new bootstrap project with context_mode='bootstrap'.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            project_name: Name for the project
            idea_text: Optional initial idea text
            file_keys: Optional list of uploaded file storage keys
            
        Returns:
            Created project data
            
        Raises:
            Exception: If project creation fails
        """
        try:
            project_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Initial enhanced_context structure
            initial_context = {
                "version": 1,
                "draft": None,
                "confirmed": None,
                "metadata": {
                    "context_mode": "bootstrap",
                    "created_at": now,
                    "intake": {
                        "idea_text": idea_text,
                        "file_keys": file_keys or []
                    }
                }
            }
            
            project_data = {
                "id": project_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "name": project_name,
                "context_mode": "bootstrap",
                "context_status": "embedding",
                "context_version": 1,
                "enhanced_context": initial_context,
                "pv_report_id": None,  # Bootstrap projects don't require PV report
                "created_at": now,
                "updated_at": now
            }
            
            logger.info(f"🔍 Inserting bootstrap project: {project_id}")
            logger.info(f"   - tenant_id: {tenant_id}")
            logger.info(f"   - user_id: {user_id}")
            logger.info(f"   - project_name: {project_name}")
            
            response = self.supabase.client.table("vmp_projects").insert(
                project_data
            ).execute()
            
            logger.info(f"🔍 Insert response: {response}")
            
            if not response.data:
                raise Exception("Failed to create bootstrap project")
            
            logger.info(f"✅ Created bootstrap project {project_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"❌ Error creating bootstrap project: {e}")
            raise
    
    def get_bootstrap_project(
        self,
        project_id: str,
        tenant_id: str,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Get a bootstrap project by ID with retry logic for transient errors.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            max_retries: Max retry attempts for transient connection errors
            
        Returns:
            Project data or None if not found
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.supabase.client.table("vmp_projects").select(
                    "*"
                ).eq("id", project_id).eq("tenant_id", tenant_id).execute()
                
                if response.data:
                    return response.data[0]
                return None
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if this is a transient connection error worth retrying
                is_transient = any(err in error_str for err in [
                    "connection reset",
                    "connection refused",
                    "broken pipe",
                    "timeout",
                    "temporary failure",
                    "errno 54",
                    "errno 104"
                ])
                
                if is_transient and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.5  # 0.5s, 1s, 1.5s
                    logger.warning(f"⚠️ Transient error getting project {project_id}, retry {attempt + 1}/{max_retries} in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Error getting bootstrap project {project_id}: {e}")
                    return None
        
        logger.error(f"❌ Failed to get bootstrap project {project_id} after {max_retries} retries: {last_error}")
        return None
    
    def update_context_status(
        self,
        project_id: str,
        tenant_id: str,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """
        Update the context_status of a bootstrap project.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            status: New context_status value
            error: Optional error message if status is 'failed'
            
        Returns:
            True if successful
        """
        try:
            update_data = {
                "context_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # If failed, store error in enhanced_context.metadata
            if status == "failed" and error:
                project = self.get_bootstrap_project(project_id, tenant_id)
                if project:
                    enhanced_context = project.get("enhanced_context", {})
                    if not enhanced_context:
                        enhanced_context = {}
                    if "metadata" not in enhanced_context:
                        enhanced_context["metadata"] = {}
                    enhanced_context["metadata"]["error"] = error
                    enhanced_context["metadata"]["failed_at"] = datetime.utcnow().isoformat()
                    update_data["enhanced_context"] = enhanced_context
            
            response = self.supabase.client.table("vmp_projects").update(
                update_data
            ).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Updated context_status to '{status}' for project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating context_status for {project_id}: {e}")
            return False
    
    def save_clarifying_questions(
        self,
        project_id: str,
        tenant_id: str,
        questions: List[Dict[str, Any]],
        max_retries: int = 3
    ) -> bool:
        """
        Save generated clarifying questions to enhanced_context.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            questions: List of question objects
            max_retries: Max retry attempts for the update operation
            
        Returns:
            True if successful
        """
        try:
            project = self.get_bootstrap_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            enhanced_context = project.get("enhanced_context", {})
            if not enhanced_context:
                enhanced_context = {"version": 1, "metadata": {}}
            
            if "metadata" not in enhanced_context:
                enhanced_context["metadata"] = {}
            
            enhanced_context["metadata"]["clarifying_questions"] = questions
            enhanced_context["metadata"]["questions_generated_at"] = datetime.utcnow().isoformat()
            
            # Retry logic for the update operation
            last_error = None
            for attempt in range(max_retries):
                try:
                    response = self.supabase.client.table("vmp_projects").update({
                        "enhanced_context": enhanced_context,
                        "context_status": "questions_pending",
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", project_id).eq("tenant_id", tenant_id).execute()
                    
                    success = len(response.data) > 0
                    if success:
                        logger.info(f"✅ Saved {len(questions)} clarifying questions for project {project_id}")
                    return success
                    
                except Exception as update_error:
                    last_error = update_error
                    error_str = str(update_error).lower()
                    
                    is_transient = any(err in error_str for err in [
                        "connection reset", "connection refused", "broken pipe",
                        "timeout", "temporary failure", "errno 54", "errno 104"
                    ])
                    
                    if is_transient and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 0.5
                        logger.warning(f"⚠️ Transient error saving questions, retry {attempt + 1}/{max_retries} in {wait_time}s: {update_error}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise update_error
            
            raise Exception(f"Failed to save questions after {max_retries} retries: {last_error}")
            
        except Exception as e:
            logger.error(f"❌ Error saving clarifying questions for {project_id}: {e}")
            return False
    
    def save_clarifying_answers(
        self,
        project_id: str,
        tenant_id: str,
        answers: List[Dict[str, Any]]
    ) -> bool:
        """
        Save user's answers to clarifying questions.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            answers: List of answer objects
            
        Returns:
            True if successful
        """
        try:
            project = self.get_bootstrap_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            enhanced_context = project.get("enhanced_context", {})
            if "metadata" not in enhanced_context:
                enhanced_context["metadata"] = {}
            
            enhanced_context["metadata"]["clarifying_answers"] = answers
            enhanced_context["metadata"]["answers_received_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.client.table("vmp_projects").update({
                "enhanced_context": enhanced_context,
                "context_status": "answers_received",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Saved {len(answers)} clarifying answers for project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving clarifying answers for {project_id}: {e}")
            return False
    
    def save_research_results(
        self,
        project_id: str,
        tenant_id: str,
        research_results: Dict[str, Any]
    ) -> bool:
        """
        Save web research results to enhanced_context.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            research_results: Research results with sources
            
        Returns:
            True if successful
        """
        try:
            project = self.get_bootstrap_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            enhanced_context = project.get("enhanced_context", {})
            if "metadata" not in enhanced_context:
                enhanced_context["metadata"] = {}
            
            enhanced_context["metadata"]["research_results"] = research_results
            enhanced_context["metadata"]["research_completed_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.client.table("vmp_projects").update({
                "enhanced_context": enhanced_context,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Saved research results for project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving research results for {project_id}: {e}")
            return False
    
    def save_enhanced_context(
        self,
        project_id: str,
        tenant_id: str,
        enhanced_context: Dict[str, Any],
        version: int = 1
    ) -> bool:
        """
        Save the complete enhanced context draft.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            enhanced_context: Complete enhanced context object
            version: Context version number
            
        Returns:
            True if successful
        """
        try:
            enhanced_context["version"] = version
            enhanced_context["metadata"]["updated_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.client.table("vmp_projects").update({
                "enhanced_context": enhanced_context,
                "context_version": version,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Saved enhanced context v{version} for project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving enhanced context for {project_id}: {e}")
            return False
    
    def confirm_enhanced_context(
        self,
        project_id: str,
        tenant_id: str,
        confirmed_context: Dict[str, Any]
    ) -> bool:
        """
        Save user-confirmed (possibly edited) enhanced context.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID for security
            confirmed_context: User-confirmed context data
            
        Returns:
            True if successful
        """
        try:
            project = self.get_bootstrap_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            enhanced_context = project.get("enhanced_context", {})
            current_version = project.get("context_version", 1)
            new_version = current_version + 1
            
            # Set confirmed, keep draft for reference
            enhanced_context["confirmed"] = confirmed_context
            enhanced_context["version"] = new_version
            enhanced_context["metadata"]["confirmed_at"] = datetime.utcnow().isoformat()
            enhanced_context["metadata"]["updated_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.client.table("vmp_projects").update({
                "enhanced_context": enhanced_context,
                "context_status": "context_confirmed",
                "context_version": new_version,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Confirmed enhanced context v{new_version} for project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error confirming enhanced context for {project_id}: {e}")
            return False
    
    def validate_project_access(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> bool:
        """
        Validate that a user has access to a project.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            True if user has access
        """
        try:
            response = self.supabase.client.table("vmp_projects").select(
                "id"
            ).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"❌ Error validating project access for {project_id}: {e}")
            return False
    
    def list_bootstrap_projects(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List bootstrap projects with pagination and optional search.
        
        Args:
            tenant_id: Tenant ID for filtering
            user_id: Optional user ID to filter by owner
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search query for project name
            
        Returns:
            Dict with projects list, total_count, and pagination info
        """
        try:
            # Build base query - filter by context_mode='bootstrap' and context_status='context_ready'
            # Only "ready" projects are considered complete bootstrap projects
            query = self.supabase.client.table("vmp_projects").select(
                "id, name, context_status, context_mode, created_at, updated_at, user_id, enhanced_context",
                count="exact"
            ).eq("tenant_id", tenant_id).eq("context_mode", "bootstrap").eq("context_status", "context_ready")
            
            # Filter by user if provided
            if user_id:
                query = query.eq("user_id", user_id)
            
            # Apply search filter
            if search:
                query = query.ilike("name", f"%{search}%")
            
            # Order by created_at descending (newest first)
            query = query.order("created_at", desc=True)
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)
            
            response = query.execute()
            
            total_count = response.count if response.count is not None else len(response.data)
            has_next = (page * page_size) < total_count
            
            # Transform projects for response
            projects = []
            for project in response.data:
                enhanced_context = project.get("enhanced_context", {}) or {}
                metadata = enhanced_context.get("metadata", {}) or {}
                
                projects.append({
                    "id": project["id"],
                    "name": project["name"],
                    "context_status": project["context_status"],
                    "created_at": project["created_at"],
                    "updated_at": project["updated_at"],
                    "idea_text": metadata.get("intake", {}).get("idea_text"),
                    "has_files": len(metadata.get("intake", {}).get("file_keys", [])) > 0,
                    "questions_count": len(metadata.get("clarifying_questions", [])),
                    "has_draft": enhanced_context.get("draft") is not None,
                    "has_confirmed": enhanced_context.get("confirmed") is not None
                })
            
            logger.info(f"✅ Listed {len(projects)} bootstrap projects for tenant {tenant_id}")
            
            return {
                "success": True,
                "projects": projects,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": has_next
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing bootstrap projects: {e}")
            return {
                "success": False,
                "error": str(e),
                "projects": [],
                "total_count": 0
            }
    
    def delete_bootstrap_project(
        self,
        project_id: str,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a bootstrap project.
        
        Args:
            project_id: Project ID to delete
            tenant_id: Tenant ID for security
            user_id: Optional user ID for ownership check
            
        Returns:
            Dict with success status and message
        """
        try:
            # First verify the project exists and belongs to tenant
            project = self.get_bootstrap_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Verify it's a bootstrap project
            if project.get("context_mode") != "bootstrap":
                return {
                    "success": False,
                    "error": "Not a bootstrap project"
                }
            
            # Optional ownership check
            if user_id and project.get("user_id") != user_id:
                return {
                    "success": False,
                    "error": "You don't have permission to delete this project"
                }
            
            # Delete associated chunks first
            try:
                self.supabase.client.table("chunks").delete().eq(
                    "project_id", project_id
                ).execute()
                logger.info(f"🗑️ Deleted chunks for project {project_id}")
            except Exception as chunk_error:
                logger.warning(f"Error deleting chunks: {chunk_error}")
            
            # Delete associated documents
            try:
                self.supabase.client.table("documents").delete().eq(
                    "project_id", project_id
                ).execute()
                logger.info(f"🗑️ Deleted documents for project {project_id}")
            except Exception as doc_error:
                logger.warning(f"Error deleting documents: {doc_error}")
            
            # Delete the project
            response = self.supabase.client.table("vmp_projects").delete().eq(
                "id", project_id
            ).eq("tenant_id", tenant_id).execute()
            
            if response.data:
                logger.info(f"✅ Deleted bootstrap project {project_id}")
                return {
                    "success": True,
                    "message": f"Project '{project.get('name', project_id)}' deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete project"
                }
            
        except Exception as e:
            logger.error(f"❌ Error deleting bootstrap project {project_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_bootstrap_database_adapter(use_service_role: bool = True) -> BootstrapDatabaseAdapter:
    """Factory function for BootstrapDatabaseAdapter."""
    return BootstrapDatabaseAdapter(use_service_role=use_service_role)
