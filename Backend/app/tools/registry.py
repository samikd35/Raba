"""RABA Tool Registry Service.

Centralized registry for managing video generation tools.
Handles CRUD operations with Supabase and Redis caching.
"""

import json
from datetime import datetime
from typing import Any, Optional

from app.models.tool import (
    ImprovementRecord,
    ToolEnhancementResponse,
    ToolListResponse,
    ToolResponse,
    ToolUpdate,
)
from app.services.redis import CacheService, get_cache_service
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour


class ToolNotFoundError(Exception):
    """Raised when a tool is not found."""
    pass


class ToolRegistryError(Exception):
    """Base exception for registry errors."""
    pass


class ToolRegistry:
    """
    Centralized tool registry with caching.
    
    Manages all CRUD operations for video generation tools,
    with Redis caching for performance.
    """
    
    TABLE_NAME = "tools"
    
    def __init__(
        self,
        supabase_client=None,
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize tool registry.
        
        Args:
            supabase_client: Optional Supabase client
            cache_service: Optional cache service
        """
        self._supabase = supabase_client
        self._cache = cache_service
        self._logger = get_logger(f"{__name__}.ToolRegistry")
    
    @property
    def supabase(self):
        """Get Supabase client (lazy initialization)."""
        if self._supabase is None:
            self._supabase = get_supabase_client()
        return self._supabase
    
    @property
    def cache(self) -> Optional[CacheService]:
        """Get cache service (lazy initialization). Returns None if Redis unavailable."""
        if self._cache is None:
            try:
                self._cache = get_cache_service()
                # Test connection
                self._cache.client.ping()
            except Exception as e:
                self._logger.warning(f"Redis unavailable, caching disabled: {e}")
                self._cache = None
        return self._cache
    
    def _cache_key(self, key_type: str, identifier: str = "") -> str:
        """Generate cache key."""
        if identifier:
            return f"tools:{key_type}:{identifier}"
        return f"tools:{key_type}"
    
    async def _cache_get(self, key: str) -> Optional[str]:
        """Get from cache, returns None if cache unavailable."""
        if self.cache is None:
            return None
        try:
            return await self.cache.get(key)
        except Exception as e:
            self._logger.warning(f"Cache get failed: {e}")
            return None
    
    async def _cache_set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> None:
        """Set in cache, silently fails if cache unavailable."""
        if self.cache is None:
            return
        try:
            await self.cache.set(key, value, ttl)
        except Exception as e:
            self._logger.warning(f"Cache set failed: {e}")
    
    async def _cache_delete(self, key: str) -> None:
        """Delete from cache, silently fails if cache unavailable."""
        if self.cache is None:
            return
        try:
            await self.cache.delete(key)
        except Exception as e:
            self._logger.warning(f"Cache delete failed: {e}")
    
    async def _invalidate_cache(self) -> None:
        """Invalidate all tool caches."""
        if self.cache is None:
            return
        self._logger.info("Invalidating tool caches")
        await self._cache_delete(self._cache_key("list"))
        for category in ["surreal_realism", "high_octane_anime", "stylized_3d"]:
            await self._cache_delete(self._cache_key("category", category))
    
    def _record_to_response(self, record: dict[str, Any]) -> ToolResponse:
        """Convert database record to ToolResponse."""
        return ToolResponse(
            id=str(record["id"]),
            tool_id=record["tool_id"],
            tool_name=record["tool_name"],
            category=record["category"],
            description=record.get("description"),
            capabilities=record.get("capabilities"),
            script_prompt_template=record.get("script_prompt_template"),
            image_prompt_template=record.get("image_prompt_template"),
            video_prompt_template=record.get("video_prompt_template"),
            parameters_schema=record.get("parameters_schema"),
            original_idea=record.get("original_idea"),
            is_active=record.get("is_active", True),
            priority=record.get("priority", 0),
            version=record.get("version", 1),
            usage_count=record.get("usage_count", 0),
            success_rate=record.get("success_rate", 0.0),
            improvement_history=record.get("improvement_history"),
            created_by=str(record["created_by"]) if record.get("created_by") else None,
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            last_improved_at=record.get("last_improved_at"),
        )
    
    async def create(
        self,
        enhanced_tool: ToolEnhancementResponse,
        original_idea: str,
        created_by: Optional[str] = None,
    ) -> ToolResponse:
        """
        Create a new tool from enhanced data.
        
        Args:
            enhanced_tool: Tool data from Gemini enhancement
            original_idea: User's original idea
            created_by: Optional creator UUID
            
        Returns:
            Created tool response
        """
        self._logger.info(f"Creating tool: {enhanced_tool.tool_id}")
        
        # Check if tool_id already exists
        existing = await self.get_by_tool_id(enhanced_tool.tool_id)
        if existing:
            # Append suffix to make unique
            base_id = enhanced_tool.tool_id
            counter = 1
            while existing:
                enhanced_tool.tool_id = f"{base_id}_{counter}"
                existing = await self.get_by_tool_id(enhanced_tool.tool_id)
                counter += 1
            self._logger.info(f"Tool ID adjusted to: {enhanced_tool.tool_id}")
        
        # Prepare insert data
        insert_data = {
            "tool_id": enhanced_tool.tool_id,
            "tool_name": enhanced_tool.tool_name,
            "category": enhanced_tool.category.value,
            "description": enhanced_tool.description,
            "capabilities": enhanced_tool.capabilities.model_dump(),
            "script_prompt_template": enhanced_tool.script_prompt_template,
            "image_prompt_template": enhanced_tool.image_prompt_template,
            "video_prompt_template": enhanced_tool.video_prompt_template,
            "parameters_schema": enhanced_tool.parameters_schema,
            "original_idea": original_idea,
            "is_active": True,
            "priority": 50,  # Default priority
            "version": 1,
            "usage_count": 0,
            "success_rate": 0.0,
            "improvement_history": [],
        }
        
        if created_by:
            insert_data["created_by"] = created_by
        
        # Insert into database
        response = self.supabase.table(self.TABLE_NAME).insert(insert_data).execute()
        
        if not response.data:
            raise ToolRegistryError("Failed to create tool - no data returned")
        
        # Invalidate cache
        await self._invalidate_cache()
        
        self._logger.info(f"Tool created: {enhanced_tool.tool_id}")
        return self._record_to_response(response.data[0])
    
    async def get_by_tool_id(self, tool_id: str) -> Optional[ToolResponse]:
        """
        Get tool by tool_id.
        
        Args:
            tool_id: Unique tool slug identifier
            
        Returns:
            Tool response or None
        """
        # Check cache first
        cache_key = self._cache_key("id", tool_id)
        cached = await self._cache_get(cache_key)
        if cached:
            self._logger.debug(f"Cache hit for tool: {tool_id}")
            return ToolResponse.model_validate_json(cached)
        
        # Query database
        response = (
            self.supabase.table(self.TABLE_NAME)
            .select("*")
            .eq("tool_id", tool_id)
            .execute()
        )
        
        if not response.data:
            return None
        
        tool = self._record_to_response(response.data[0])
        
        # Cache result
        await self._cache_set(cache_key, tool.model_dump_json())
        
        return tool
    
    async def get_by_id(self, id: str) -> Optional[ToolResponse]:
        """
        Get tool by database UUID.
        
        Args:
            id: Database UUID
            
        Returns:
            Tool response or None
        """
        response = (
            self.supabase.table(self.TABLE_NAME)
            .select("*")
            .eq("id", id)
            .execute()
        )
        
        if not response.data:
            return None
        
        return self._record_to_response(response.data[0])
    
    async def list_tools(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> ToolListResponse:
        """
        List tools with optional filters.
        
        Args:
            category: Optional category filter
            is_active: Filter by active status
            limit: Page size
            offset: Page offset
            
        Returns:
            Paginated tool list
        """
        # Build cache key
        cache_key = self._cache_key("list") if not category else self._cache_key("category", category)
        
        # Check cache (only for default queries)
        if offset == 0 and limit == 50:
            cached = await self._cache_get(cache_key)
            if cached:
                self._logger.debug(f"Cache hit for tool list")
                data = json.loads(cached)
                return ToolListResponse(**data)
        
        # Build query
        query = self.supabase.table(self.TABLE_NAME).select("*", count="exact")
        
        if category:
            query = query.eq("category", category)
        
        if is_active is not None:
            query = query.eq("is_active", is_active)
        
        # Add pagination and ordering
        query = query.order("priority", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        
        tools = [self._record_to_response(record) for record in response.data]
        total = response.count or len(tools)
        
        result = ToolListResponse(
            tools=tools,
            total=total,
            limit=limit,
            offset=offset,
        )
        
        # Cache result (only for default queries)
        if offset == 0 and limit == 50:
            await self._cache_set(cache_key, result.model_dump_json())
        
        return result
    
    async def update(
        self,
        tool_id: str,
        updates: ToolUpdate,
    ) -> ToolResponse:
        """
        Update a tool.
        
        Args:
            tool_id: Tool slug identifier
            updates: Fields to update
            
        Returns:
            Updated tool response
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        self._logger.info(f"Updating tool: {tool_id}")
        
        # Verify tool exists
        existing = await self.get_by_tool_id(tool_id)
        if not existing:
            raise ToolNotFoundError(f"Tool not found: {tool_id}")
        
        # Build update data (only non-None fields)
        update_data: dict[str, Any] = {}
        
        if updates.tool_name is not None:
            update_data["tool_name"] = updates.tool_name
        if updates.description is not None:
            update_data["description"] = updates.description
        if updates.capabilities is not None:
            update_data["capabilities"] = updates.capabilities.model_dump()
        if updates.is_active is not None:
            update_data["is_active"] = updates.is_active
        if updates.script_prompt_template is not None:
            update_data["script_prompt_template"] = updates.script_prompt_template
        if updates.image_prompt_template is not None:
            update_data["image_prompt_template"] = updates.image_prompt_template
        if updates.video_prompt_template is not None:
            update_data["video_prompt_template"] = updates.video_prompt_template
        if updates.priority is not None:
            update_data["priority"] = updates.priority
        if updates.idea is not None:
            update_data["original_idea"] = updates.idea
        
        if not update_data:
            return existing
        
        # Increment version
        update_data["version"] = existing.version + 1
        
        # Execute update
        response = (
            self.supabase.table(self.TABLE_NAME)
            .update(update_data)
            .eq("tool_id", tool_id)
            .execute()
        )
        
        if not response.data:
            raise ToolRegistryError(f"Failed to update tool: {tool_id}")
        
        # Invalidate cache
        await self._invalidate_cache()
        await self._cache_delete(self._cache_key("id", tool_id))
        
        self._logger.info(f"Tool updated: {tool_id}")
        return self._record_to_response(response.data[0])
    
    async def apply_improvement(
        self,
        tool_id: str,
        enhanced_tool: ToolEnhancementResponse,
        improvement_suggestion: str,
    ) -> ToolResponse:
        """
        Apply an improvement to a tool.
        
        Records the improvement in history and updates the tool.
        
        Args:
            tool_id: Tool to improve
            enhanced_tool: Improved tool data from Gemini
            improvement_suggestion: Original user suggestion
            
        Returns:
            Updated tool response
        """
        self._logger.info(f"Applying improvement to tool: {tool_id}")
        
        # Get existing tool
        existing = await self.get_by_tool_id(tool_id)
        if not existing:
            raise ToolNotFoundError(f"Tool not found: {tool_id}")
        
        # Create improvement record
        improvement = ImprovementRecord(
            timestamp=datetime.utcnow().isoformat(),
            previous_version=existing.version,
            suggestion=improvement_suggestion,
            changes_made=enhanced_tool.reasoning,
        )
        
        # Get existing history or create new
        history = existing.improvement_history or []
        history.append(improvement.model_dump())
        
        # Build update data
        update_data = {
            "tool_name": enhanced_tool.tool_name,
            "description": enhanced_tool.description,
            "capabilities": enhanced_tool.capabilities.model_dump(),
            "script_prompt_template": enhanced_tool.script_prompt_template,
            "image_prompt_template": enhanced_tool.image_prompt_template,
            "video_prompt_template": enhanced_tool.video_prompt_template,
            "parameters_schema": enhanced_tool.parameters_schema,
            "improvement_history": history,
            "last_improved_at": datetime.utcnow().isoformat(),
            "version": existing.version + 1,
        }
        
        # Execute update
        response = (
            self.supabase.table(self.TABLE_NAME)
            .update(update_data)
            .eq("tool_id", tool_id)
            .execute()
        )
        
        if not response.data:
            raise ToolRegistryError(f"Failed to apply improvement: {tool_id}")
        
        # Invalidate cache
        await self._invalidate_cache()
        await self._cache_delete(self._cache_key("id", tool_id))
        
        self._logger.info(f"Improvement applied to tool: {tool_id}")
        return self._record_to_response(response.data[0])
    
    async def delete(self, tool_id: str) -> bool:
        """
        Soft delete a tool (set is_active = false).
        
        Args:
            tool_id: Tool to delete
            
        Returns:
            True if deleted
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        self._logger.info(f"Deleting tool: {tool_id}")
        
        # Verify tool exists
        existing = await self.get_by_tool_id(tool_id)
        if not existing:
            raise ToolNotFoundError(f"Tool not found: {tool_id}")
        
        # Soft delete
        response = (
            self.supabase.table(self.TABLE_NAME)
            .update({"is_active": False})
            .eq("tool_id", tool_id)
            .execute()
        )
        
        if not response.data:
            raise ToolRegistryError(f"Failed to delete tool: {tool_id}")
        
        # Invalidate cache
        await self._invalidate_cache()
        await self._cache_delete(self._cache_key("id", tool_id))
        
        self._logger.info(f"Tool deleted: {tool_id}")
        return True
    
    async def increment_usage(self, tool_id: str) -> None:
        """
        Increment tool usage count.
        
        Args:
            tool_id: Tool that was used
        """
        # Use database function for atomic increment
        self.supabase.rpc("increment_tool_usage", {"p_tool_id": tool_id}).execute()
        
        # Invalidate specific tool cache
        await self._cache_delete(self._cache_key("id", tool_id))
    
    async def update_success_rate(self, tool_id: str, success: bool) -> None:
        """
        Update tool success rate after a generation.
        
        Args:
            tool_id: Tool that was used
            success: Whether generation succeeded
        """
        self.supabase.rpc(
            "update_tool_success_rate",
            {"p_tool_id": tool_id, "p_success": success}
        ).execute()
        
        # Invalidate specific tool cache
        await self._cache_delete(self._cache_key("id", tool_id))


# Singleton instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get singleton tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
