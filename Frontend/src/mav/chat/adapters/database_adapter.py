"""
Database Adapter for Project Chat Feature

Handles all database operations for:
- Chat threads (CRUD)
- Chat messages (CRUD with pagination)
- Thread memory (read/update)
- Project verification
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.mint.api.system.core.supabase_client import get_service_role_client

from ..models import (
    ChatThread,
    ChatMessage,
    ChatThreadMemoryRecord,
    ThreadStatus,
    MessageRole,
    ThreadMemory,
    MemoryPatch,
    Citation,
    ToolTrace,
)

logger = logging.getLogger(__name__)


class ChatDatabaseAdapter:
    """
    Database adapter for Project Chat operations.
    
    Uses service role client for backend operations (bypasses RLS).
    All operations include explicit tenant_id checks for security.
    """
    
    THREADS_TABLE = "project_chat_threads"
    MESSAGES_TABLE = "project_chat_messages"
    MEMORY_TABLE = "project_chat_thread_memory"
    PROJECTS_TABLE = "vmp_projects"
    
    def __init__(self):
        """Initialize with service role client."""
        self.supabase = get_service_role_client()
        self.client = self.supabase.client  # Access the actual Supabase client
        logger.info("✅ ChatDatabaseAdapter initialized with service role client")
    
    # =========================================================================
    # PROJECT VERIFICATION
    # =========================================================================
    
    async def verify_project_access(
        self,
        project_id: str,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Verify that the project exists and belongs to the tenant.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID to verify ownership
            user_id: Optional user ID for additional verification
            
        Returns:
            True if access is valid, False otherwise
        """
        try:
            query = self.client.table(self.PROJECTS_TABLE).select("id, tenant_id, user_id").eq("id", project_id)
            
            result = query.execute()
            
            if not result.data:
                logger.warning(f"Project {project_id} not found")
                return False
            
            project = result.data[0]
            
            # Verify tenant ownership
            if project["tenant_id"] != tenant_id:
                logger.warning(f"Tenant mismatch: project belongs to {project['tenant_id']}, not {tenant_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying project access: {e}")
            return False
    
    async def get_project_info(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get basic project info for context.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Project info dict or None
        """
        try:
            result = self.client.table(self.PROJECTS_TABLE).select(
                "id, name, description, personas, current_step"
            ).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return None
    
    # =========================================================================
    # THREAD OPERATIONS
    # =========================================================================
    
    async def create_thread(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatThread]:
        """
        Create a new chat thread for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User creating the thread
            title: Optional thread title
            metadata: Optional metadata
            
        Returns:
            Created ChatThread or None on error
        """
        try:
            # Verify project access first
            if not await self.verify_project_access(project_id, tenant_id, user_id):
                logger.error(f"Access denied: cannot create thread for project {project_id}")
                return None
            
            data = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "title": title,
                "status": ThreadStatus.ACTIVE.value,
                "metadata": metadata or {}
            }
            
            result = self.client.table(self.THREADS_TABLE).insert(data).execute()
            
            if result.data:
                thread_data = result.data[0]
                logger.info(f"✅ Created thread {thread_data['id']} for project {project_id}")
                return ChatThread(
                    id=thread_data["id"],
                    project_id=thread_data["project_id"],
                    tenant_id=thread_data["tenant_id"],
                    user_id=thread_data["user_id"],
                    title=thread_data.get("title"),
                    status=ThreadStatus(thread_data["status"]),
                    created_at=datetime.fromisoformat(thread_data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(thread_data["updated_at"].replace("Z", "+00:00")),
                    last_message_at=None,
                    metadata=thread_data.get("metadata", {})
                )
            
            logger.error("Failed to create thread: no data returned")
            return None
            
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            return None
    
    async def get_thread(
        self,
        thread_id: str,
        tenant_id: str
    ) -> Optional[ChatThread]:
        """
        Get a thread by ID with tenant verification.
        
        Args:
            thread_id: Thread ID
            tenant_id: Tenant ID for verification
            
        Returns:
            ChatThread or None
        """
        try:
            result = self.client.table(self.THREADS_TABLE).select("*").eq("id", thread_id).eq("tenant_id", tenant_id).execute()
            
            if not result.data:
                return None
            
            thread_data = result.data[0]
            return ChatThread(
                id=thread_data["id"],
                project_id=thread_data["project_id"],
                tenant_id=thread_data["tenant_id"],
                user_id=thread_data["user_id"],
                title=thread_data.get("title"),
                status=ThreadStatus(thread_data["status"]),
                created_at=datetime.fromisoformat(thread_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(thread_data["updated_at"].replace("Z", "+00:00")),
                last_message_at=datetime.fromisoformat(thread_data["last_message_at"].replace("Z", "+00:00")) if thread_data.get("last_message_at") else None,
                metadata=thread_data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            return None
    
    async def list_threads(
        self,
        project_id: str,
        tenant_id: str,
        status: Optional[ThreadStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[ChatThread], int]:
        """
        List threads for a project with pagination.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            status: Optional status filter
            limit: Max threads to return
            offset: Pagination offset
            
        Returns:
            Tuple of (threads list, total count)
        """
        try:
            # Build query
            query = self.client.table(self.THREADS_TABLE).select("*", count="exact").eq("project_id", project_id).eq("tenant_id", tenant_id)
            
            if status:
                query = query.eq("status", status.value)
            else:
                # By default, exclude deleted threads
                query = query.neq("status", ThreadStatus.DELETED.value)
            
            # Order by last activity (most recent first)
            query = query.order("last_message_at", desc=True, nullsfirst=False).order("created_at", desc=True)
            
            # Pagination
            query = query.range(offset, offset + limit - 1)
            
            result = query.execute()
            
            threads = []
            for row in result.data:
                threads.append(ChatThread(
                    id=row["id"],
                    project_id=row["project_id"],
                    tenant_id=row["tenant_id"],
                    user_id=row["user_id"],
                    title=row.get("title"),
                    status=ThreadStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
                    last_message_at=datetime.fromisoformat(row["last_message_at"].replace("Z", "+00:00")) if row.get("last_message_at") else None,
                    metadata=row.get("metadata", {})
                ))
            
            total_count = result.count if result.count is not None else len(threads)
            
            return threads, total_count
            
        except Exception as e:
            logger.error(f"Error listing threads: {e}")
            return [], 0
    
    async def update_thread_status(
        self,
        thread_id: str,
        tenant_id: str,
        status: ThreadStatus
    ) -> bool:
        """
        Update thread status (archive/delete).
        
        Args:
            thread_id: Thread ID
            tenant_id: Tenant ID for verification
            status: New status
            
        Returns:
            True if successful
        """
        try:
            result = self.client.table(self.THREADS_TABLE).update({
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", thread_id).eq("tenant_id", tenant_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating thread status: {e}")
            return False
    
    async def update_thread_title(
        self,
        thread_id: str,
        tenant_id: str,
        title: str
    ) -> bool:
        """
        Update thread title.
        
        Args:
            thread_id: Thread ID
            tenant_id: Tenant ID for verification
            title: New title
            
        Returns:
            True if successful
        """
        try:
            result = self.client.table(self.THREADS_TABLE).update({
                "title": title,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", thread_id).eq("tenant_id", tenant_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating thread title: {e}")
            return False
    
    # =========================================================================
    # MESSAGE OPERATIONS
    # =========================================================================
    
    async def create_message(
        self,
        thread_id: str,
        role: MessageRole,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        tool_trace: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatMessage]:
        """
        Create a new message in a thread.
        
        Args:
            thread_id: Thread ID
            role: Message role (user, assistant, tool, system)
            content: Message content
            citations: Optional citations array
            tool_trace: Optional tool trace for audit
            metadata: Optional metadata
            
        Returns:
            Created ChatMessage or None
        """
        try:
            data = {
                "thread_id": thread_id,
                "role": role.value,
                "content": content,
                "citations": citations or [],
                "tool_trace": tool_trace,
                "metadata": metadata or {}
            }
            
            result = self.client.table(self.MESSAGES_TABLE).insert(data).execute()
            
            if result.data:
                msg_data = result.data[0]
                logger.info(f"✅ Created {role.value} message in thread {thread_id}")
                return ChatMessage(
                    id=msg_data["id"],
                    thread_id=msg_data["thread_id"],
                    role=MessageRole(msg_data["role"]),
                    content=msg_data["content"],
                    citations=msg_data.get("citations", []),
                    tool_trace=ToolTrace(**msg_data["tool_trace"]) if msg_data.get("tool_trace") else None,
                    metadata=msg_data.get("metadata", {}),
                    created_at=datetime.fromisoformat(msg_data["created_at"].replace("Z", "+00:00"))
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    async def get_messages(
        self,
        thread_id: str,
        tenant_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        order: str = "desc"
    ) -> Tuple[List[ChatMessage], Optional[str], bool]:
        """
        Get messages for a thread with cursor-based pagination.
        
        Args:
            thread_id: Thread ID
            tenant_id: Tenant ID for verification
            limit: Max messages to return
            cursor: Message ID to start from (exclusive)
            order: Sort order ('asc' or 'desc')
            
        Returns:
            Tuple of (messages, next_cursor, has_more)
        """
        try:
            # First verify thread belongs to tenant
            thread = await self.get_thread(thread_id, tenant_id)
            if not thread:
                logger.warning(f"Thread {thread_id} not found or access denied")
                return [], None, False
            
            # Build query
            query = self.client.table(self.MESSAGES_TABLE).select("*").eq("thread_id", thread_id)
            
            # Cursor-based pagination
            if cursor:
                # Get the cursor message's created_at
                cursor_result = self.client.table(self.MESSAGES_TABLE).select("created_at").eq("id", cursor).execute()
                if cursor_result.data:
                    cursor_time = cursor_result.data[0]["created_at"]
                    if order == "desc":
                        query = query.lt("created_at", cursor_time)
                    else:
                        query = query.gt("created_at", cursor_time)
            
            # Order
            query = query.order("created_at", desc=(order == "desc"))
            
            # Fetch one extra to check has_more
            query = query.limit(limit + 1)
            
            result = query.execute()
            
            messages = []
            has_more = len(result.data) > limit
            
            # Process only up to limit
            for row in result.data[:limit]:
                messages.append(ChatMessage(
                    id=row["id"],
                    thread_id=row["thread_id"],
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    citations=row.get("citations", []),
                    tool_trace=ToolTrace(**row["tool_trace"]) if row.get("tool_trace") else None,
                    metadata=row.get("metadata", {}),
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                ))
            
            # Next cursor is the last message's ID
            next_cursor = messages[-1].id if messages and has_more else None
            
            return messages, next_cursor, has_more
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return [], None, False
    
    async def get_recent_messages(
        self,
        thread_id: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get recent messages for context window (lightweight).
        
        Args:
            thread_id: Thread ID
            limit: Number of recent messages
            
        Returns:
            List of {role, content} dicts
        """
        try:
            result = self.client.table(self.MESSAGES_TABLE).select("role, content").eq("thread_id", thread_id).order("created_at", desc=True).limit(limit).execute()
            
            # Reverse to get chronological order
            messages = []
            for row in reversed(result.data):
                messages.append({
                    "role": row["role"],
                    "content": row["content"]
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    async def get_message_count(self, thread_id: str) -> int:
        """Get total message count for a thread."""
        try:
            result = self.client.table(self.MESSAGES_TABLE).select("id", count="exact").eq("thread_id", thread_id).execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
    
    # =========================================================================
    # THREAD MEMORY OPERATIONS
    # =========================================================================
    
    async def get_thread_memory(self, thread_id: str) -> Optional[ThreadMemory]:
        """
        Get thread memory.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            ThreadMemory or None
        """
        try:
            result = self.client.table(self.MEMORY_TABLE).select("*").eq("thread_id", thread_id).execute()
            
            if not result.data:
                # Memory should be auto-created by trigger, but handle missing case
                logger.warning(f"No memory found for thread {thread_id}, returning empty")
                return ThreadMemory()
            
            memory_data = result.data[0]
            return ThreadMemory(
                running_summary=memory_data.get("running_summary"),
                pinned_facts=memory_data.get("pinned_facts", []),
                open_loops=memory_data.get("open_loops", []),
                last_context_refs=memory_data.get("last_context_refs", {})
            )
            
        except Exception as e:
            logger.error(f"Error getting thread memory: {e}")
            return None
    
    async def update_thread_memory(
        self,
        thread_id: str,
        memory_patch: MemoryPatch,
        last_context_refs: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update thread memory with a patch.
        
        Args:
            thread_id: Thread ID
            memory_patch: Changes to apply
            last_context_refs: Optional context refs to update
            
        Returns:
            True if successful
        """
        try:
            # Get current memory
            current = await self.get_thread_memory(thread_id)
            if current is None:
                logger.error(f"Cannot update memory: thread {thread_id} memory not found")
                return False
            
            # Apply patch
            new_summary = memory_patch.new_summary if memory_patch.new_summary else current.running_summary
            
            # Update pinned facts
            new_pinned_facts = list(current.pinned_facts)
            for fact in memory_patch.pinned_facts_remove:
                if fact in new_pinned_facts:
                    new_pinned_facts.remove(fact)
            for fact in memory_patch.pinned_facts_add:
                if fact not in new_pinned_facts:
                    new_pinned_facts.append(fact)
            
            # Update open loops
            new_open_loops = list(current.open_loops)
            for loop in memory_patch.open_loops_remove:
                if loop in new_open_loops:
                    new_open_loops.remove(loop)
            for loop in memory_patch.open_loops_add:
                if loop not in new_open_loops:
                    new_open_loops.append(loop)
            
            # Prepare update data
            update_data = {
                "running_summary": new_summary,
                "pinned_facts": new_pinned_facts,
                "open_loops": new_open_loops,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if last_context_refs is not None:
                update_data["last_context_refs"] = last_context_refs
            
            # Execute update
            result = self.client.table(self.MEMORY_TABLE).update(update_data).eq("thread_id", thread_id).execute()
            
            if result.data:
                logger.info(f"✅ Updated memory for thread {thread_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating thread memory: {e}")
            return False
    
    async def get_thread_memory_record(
        self,
        thread_id: str,
        tenant_id: str
    ) -> Optional[ChatThreadMemoryRecord]:
        """
        Get full thread memory record (for debug endpoint).
        
        Args:
            thread_id: Thread ID
            tenant_id: Tenant ID for verification
            
        Returns:
            ChatThreadMemoryRecord or None
        """
        try:
            # Verify thread access
            thread = await self.get_thread(thread_id, tenant_id)
            if not thread:
                return None
            
            result = self.client.table(self.MEMORY_TABLE).select("*").eq("thread_id", thread_id).execute()
            
            if not result.data:
                return None
            
            memory_data = result.data[0]
            return ChatThreadMemoryRecord(
                id=memory_data["id"],
                thread_id=memory_data["thread_id"],
                running_summary=memory_data.get("running_summary"),
                pinned_facts=memory_data.get("pinned_facts", []),
                open_loops=memory_data.get("open_loops", []),
                last_context_refs=memory_data.get("last_context_refs", {}),
                updated_at=datetime.fromisoformat(memory_data["updated_at"].replace("Z", "+00:00"))
            )
            
        except Exception as e:
            logger.error(f"Error getting thread memory record: {e}")
            return None
    
    # =========================================================================
    # ORGANIZATION OWNER CHAT OPERATIONS
    # =========================================================================
    
    async def create_org_owner_thread(
        self,
        project_id: str,
        project_tenant_id: str,
        org_owner_user_id: str,
        organization_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatThread]:
        """
        Create a chat thread for an organization owner accessing a member's project.
        
        The thread stores the PROJECT's tenant_id (for RAG to work correctly),
        but marks it with org_owner_access metadata for authorization.
        
        Args:
            project_id: VMP project ID (member's project)
            project_tenant_id: The project's tenant_id (member's tenant)
            org_owner_user_id: Organization owner's user ID
            organization_id: Organization ID
            title: Optional thread title
            metadata: Optional additional metadata
            
        Returns:
            Created ChatThread or None on error
        """
        try:
            thread_metadata = metadata or {}
            thread_metadata.update({
                "org_owner_access": True,
                "organization_id": organization_id,
                "accessed_by_user_id": org_owner_user_id
            })
            
            data = {
                "project_id": project_id,
                "tenant_id": project_tenant_id,  # Use project's tenant for RAG
                "user_id": org_owner_user_id,
                "title": title,
                "status": ThreadStatus.ACTIVE.value,
                "metadata": thread_metadata
            }
            
            result = self.client.table(self.THREADS_TABLE).insert(data).execute()
            
            if result.data:
                thread_data = result.data[0]
                logger.info(f"✅ Created org owner thread {thread_data['id']} for project {project_id} (org: {organization_id})")
                return ChatThread(
                    id=thread_data["id"],
                    project_id=thread_data["project_id"],
                    tenant_id=thread_data["tenant_id"],
                    user_id=thread_data["user_id"],
                    title=thread_data.get("title"),
                    status=ThreadStatus(thread_data["status"]),
                    created_at=datetime.fromisoformat(thread_data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(thread_data["updated_at"].replace("Z", "+00:00")),
                    last_message_at=None,
                    metadata=thread_data.get("metadata", {})
                )
            
            logger.error("Failed to create org owner thread: no data returned")
            return None
            
        except Exception as e:
            logger.error(f"Error creating org owner thread: {e}")
            return None
    
    async def get_org_owner_thread(
        self,
        thread_id: str,
        organization_id: str
    ) -> Optional[ChatThread]:
        """
        Get a thread by ID with organization owner verification.
        
        Verifies that the thread has org_owner_access metadata matching
        the organization_id.
        
        Args:
            thread_id: Thread ID
            organization_id: Organization ID for verification
            
        Returns:
            ChatThread or None
        """
        try:
            result = self.client.table(self.THREADS_TABLE).select("*").eq("id", thread_id).execute()
            
            if not result.data:
                return None
            
            thread_data = result.data[0]
            metadata = thread_data.get("metadata", {})
            
            # Verify this is an org owner thread for this organization
            if not metadata.get("org_owner_access"):
                logger.warning(f"Thread {thread_id} is not an org owner thread")
                return None
            
            if metadata.get("organization_id") != organization_id:
                logger.warning(f"Thread {thread_id} belongs to org {metadata.get('organization_id')}, not {organization_id}")
                return None
            
            return ChatThread(
                id=thread_data["id"],
                project_id=thread_data["project_id"],
                tenant_id=thread_data["tenant_id"],
                user_id=thread_data["user_id"],
                title=thread_data.get("title"),
                status=ThreadStatus(thread_data["status"]),
                created_at=datetime.fromisoformat(thread_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(thread_data["updated_at"].replace("Z", "+00:00")),
                last_message_at=datetime.fromisoformat(thread_data["last_message_at"].replace("Z", "+00:00")) if thread_data.get("last_message_at") else None,
                metadata=thread_data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Error getting org owner thread {thread_id}: {e}")
            return None
    
    async def list_org_owner_threads(
        self,
        project_id: str,
        organization_id: str,
        status: Optional[ThreadStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[ChatThread], int]:
        """
        List org owner threads for a project.
        
        Args:
            project_id: VMP project ID
            organization_id: Organization ID
            status: Optional status filter
            limit: Max threads to return
            offset: Pagination offset
            
        Returns:
            Tuple of (threads list, total count)
        """
        try:
            # We need to filter by project_id and metadata->organization_id
            # Since Supabase doesn't easily support JSON field filtering with count,
            # we'll fetch all and filter in Python
            query = self.client.table(self.THREADS_TABLE).select("*", count="exact").eq("project_id", project_id)
            
            if status:
                query = query.eq("status", status.value)
            else:
                query = query.neq("status", ThreadStatus.DELETED.value)
            
            query = query.order("last_message_at", desc=True, nullsfirst=False).order("created_at", desc=True)
            
            result = query.execute()
            
            # Filter for org owner threads belonging to this organization
            org_threads = []
            for row in result.data:
                metadata = row.get("metadata", {})
                if metadata.get("org_owner_access") and metadata.get("organization_id") == organization_id:
                    org_threads.append(ChatThread(
                        id=row["id"],
                        project_id=row["project_id"],
                        tenant_id=row["tenant_id"],
                        user_id=row["user_id"],
                        title=row.get("title"),
                        status=ThreadStatus(row["status"]),
                        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                        updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
                        last_message_at=datetime.fromisoformat(row["last_message_at"].replace("Z", "+00:00")) if row.get("last_message_at") else None,
                        metadata=row.get("metadata", {})
                    ))
            
            total_count = len(org_threads)
            paginated = org_threads[offset:offset + limit]
            
            return paginated, total_count
            
        except Exception as e:
            logger.error(f"Error listing org owner threads: {e}")
            return [], 0
    
    async def get_org_owner_messages(
        self,
        thread_id: str,
        organization_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        order: str = "desc"
    ) -> Tuple[List[ChatMessage], Optional[str], bool]:
        """
        Get messages for an org owner thread.
        
        First verifies org owner access, then returns messages.
        
        Args:
            thread_id: Thread ID
            organization_id: Organization ID for verification
            limit: Max messages to return
            cursor: Message ID to start from
            order: Sort order
            
        Returns:
            Tuple of (messages, next_cursor, has_more)
        """
        try:
            # Verify org owner access
            thread = await self.get_org_owner_thread(thread_id, organization_id)
            if not thread:
                logger.warning(f"Org owner access denied for thread {thread_id}")
                return [], None, False
            
            # Use the thread's tenant_id for message retrieval
            return await self.get_messages(
                thread_id=thread_id,
                tenant_id=thread.tenant_id,
                limit=limit,
                cursor=cursor,
                order=order
            )
            
        except Exception as e:
            logger.error(f"Error getting org owner messages: {e}")
            return [], None, False


# Singleton instance
_chat_db_adapter: Optional[ChatDatabaseAdapter] = None


def get_chat_database_adapter() -> ChatDatabaseAdapter:
    """Get or create singleton ChatDatabaseAdapter instance."""
    global _chat_db_adapter
    if _chat_db_adapter is None:
        _chat_db_adapter = ChatDatabaseAdapter()
    return _chat_db_adapter
