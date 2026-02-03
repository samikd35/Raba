"""
Cache Invalidation Service for Yuba Backend.

Provides centralized cache invalidation for write operations and workflow cascade invalidation.

This service implements:
- Write-through cache invalidation (Requirements 6.1-6.6)
- Workflow-aware cascade invalidation (Requirements 7.1-7.5)
- Pattern-based invalidation using Redis SCAN
- Background task execution for non-blocking invalidation

Key features:
- Table-to-cache mapping for automatic invalidation
- Workflow dependency map for cascade invalidation
- Always invalidates PROJECT_FULL and CHAT_CONTEXT on workflow step completion
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .redis_service import RedisCacheService


class WriteOperation(Enum):
    """Database write operation types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# Import EntityType from entity_cache_service
from .entity_cache_service import EntityType


# Workflow dependency map for cascade invalidation
# When a workflow step completes, all downstream dependencies should be invalidated
# Requirement 7.2: Maintains dependency map of workflow steps
WORKFLOW_DEPENDENCIES: Dict[EntityType, List[EntityType]] = {
    # Feature 1: PV Report -> affects Project and Chat Context
    EntityType.PV_REPORT: [
        EntityType.PROJECT,
        EntityType.PROJECT_FULL,
        EntityType.CHAT_CONTEXT,
    ],
    
    # Feature 3: Persona -> affects Customer Profile v1
    EntityType.PERSONA: [
        EntityType.PERSONAS_LIST,
        EntityType.CUSTOMER_PROFILE_V1,
        EntityType.CP_V1_JTBD,
        EntityType.CP_V1_PAINS,
        EntityType.CP_V1_GAINS,
    ],
    
    # Feature 4: Customer Profile v1 -> affects Value Map, VPS v1, CP v2
    EntityType.CUSTOMER_PROFILE_V1: [
        EntityType.VALUE_MAP,
        EntityType.VPS_V1,
        EntityType.CUSTOMER_PROFILE_V2,
    ],
    
    # Feature 5: Hypothesis -> affects Assumptions, Questionnaire
    EntityType.HYPOTHESIS: [
        EntityType.HYPOTHESES_LIST,
        EntityType.ASSUMPTIONS_LIST,
        EntityType.QUESTIONNAIRE,
    ],
    
    # Feature 6: Assumption -> affects Questionnaire, Market Research
    EntityType.ASSUMPTION: [
        EntityType.ASSUMPTIONS_LIST,
        EntityType.QUESTIONNAIRE,
        EntityType.MR_PROJECT,
    ],
    
    # Feature 8: Market Research Results -> affects CP v2
    EntityType.MR_RESULTS: [
        EntityType.CUSTOMER_PROFILE_V2,
        EntityType.CP_V2_JTBD,
        EntityType.CP_V2_PAINS,
        EntityType.CP_V2_GAINS,
    ],
    
    # Feature 9: Customer Profile v2 -> affects Value Map, VPS
    EntityType.CUSTOMER_PROFILE_V2: [
        EntityType.VALUE_MAP,
        EntityType.VPS_V1,
        EntityType.VPS_V2,
    ],
    
    # Feature 10: Value Map -> affects VPS, BMC
    EntityType.VALUE_MAP: [
        EntityType.VPS_V1,
        EntityType.VPS_V2,
        EntityType.BMC_V1,
        EntityType.BMC_V2,
    ],
    
    # Feature 11: VPS v1 -> affects BMC v1, VPS v2
    EntityType.VPS_V1: [
        EntityType.BMC_V1,
        EntityType.VPS_V2,
    ],
    
    # Feature 12: BMC v1 -> affects Solution Critique, BMC v2
    EntityType.BMC_V1: [
        EntityType.SOLUTION_CRITIQUE,
        EntityType.BMC_V2,
    ],
    
    # Feature 13: Solution Critique -> affects VPS v2, BMC v2
    EntityType.SOLUTION_CRITIQUE: [
        EntityType.VPS_V2,
        EntityType.BMC_V2,
    ],
    
    # Feature 14: VPS v2 -> affects Requirements, Pitch, GTM
    EntityType.VPS_V2: [
        EntityType.MVP_REQUIREMENTS,
        EntityType.PITCH_DECK,
        EntityType.GTM_STRATEGY,
    ],
    
    # Feature 15: BMC v2 -> affects Requirements, Pitch, GTM
    EntityType.BMC_V2: [
        EntityType.MVP_REQUIREMENTS,
        EntityType.PITCH_DECK,
        EntityType.GTM_STRATEGY,
    ],
    
    # Feature 16: MVP Requirements -> affects Chat Context, Pitch
    EntityType.MVP_REQUIREMENTS: [
        EntityType.CHAT_CONTEXT,
        EntityType.PITCH_DECK,
    ],
}


# Table to cache pattern mapping for query cache invalidation
# Requirement 6.3: Maintains mapping of database tables to cache key patterns
TABLE_TO_QUERY_CACHE_MAP: Dict[str, List[str]] = {
    # VMP Projects table
    "vmp_projects": [
        "query:vmp_projects_list:{tenant_id}:*",
        "query:vmp_completed_questionnaires:{tenant_id}:*",
        "query:vmp_completed_value_maps:{tenant_id}:*",
        "query:vmp_completed_vps_v2:{tenant_id}:*",
    ],
    
    # Documents table (PV Reports)
    "documents": [
        "query:report_history:{tenant_id}:*",
        "query:pv_reports:{tenant_id}:*",
        "query:document_list:{tenant_id}:*",
    ],
    
    # Tenants table
    "tenants": [
        "query:user_workspaces:{user_id}:*",
        "query:tenant_details:{tenant_id}:*",
    ],
    
    # Team members table
    "team_members": [
        "query:team_members:{tenant_id}:*",
        "query:team_list:{tenant_id}:*",
    ],
    
    # Market research sessions table
    "market_research_sessions": [
        "query:mr_sessions:{tenant_id}:*",
        "query:mr_results:{tenant_id}:*",
    ],
    
    # Personas table
    "personas": [
        "query:personas_list:{tenant_id}:*",
    ],
    
    # Customer profiles table
    "customer_profiles": [
        "query:customer_profiles:{tenant_id}:*",
    ],
    
    # Value maps table
    "value_maps": [
        "query:value_maps:{tenant_id}:*",
    ],
    
    # Hypotheses table
    "hypotheses": [
        "query:hypotheses_list:{tenant_id}:*",
    ],
    
    # Assumptions table
    "assumptions": [
        "query:assumptions_list:{tenant_id}:*",
    ],
    
    # Questionnaires table
    "questionnaires": [
        "query:questionnaires:{tenant_id}:*",
    ],
    
    # Chat sessions table
    "chat_sessions": [
        "query:chat_sessions:{tenant_id}:*",
        "query:chat_history:{tenant_id}:*",
    ],
    
    # Credit transactions table
    "credit_transactions": [
        "query:credit_balance:{tenant_id}:*",
        "query:credit_history:{tenant_id}:*",
    ],
    
    # Credit lots table (for grants and balance changes)
    "credit_lots": [
        "credits:{tenant_id}",
        "query:credit_balance:{tenant_id}:*",
    ],
    
    # Tenant credit consumptions table
    "tenant_credit_consumptions": [
        "credits:{tenant_id}",
        "query:credit_balance:{tenant_id}:*",
        "query:credit_history:{tenant_id}:*",
    ],
    
    # User profiles table
    "user_profiles": [
        "query:user_profile:{user_id}:*",
    ],
    
    # Organizations table
    "organizations": [
        "query:organization:{tenant_id}:*",
        "query:org_members:{tenant_id}:*",
    ],
}


# Table to entity type mapping for entity cache invalidation
TABLE_TO_ENTITY_TYPE_MAP: Dict[str, List[EntityType]] = {
    "vmp_projects": [EntityType.PROJECT, EntityType.PROJECT_FULL, EntityType.USER_PROJECTS, EntityType.TENANT_PROJECTS],
    "documents": [EntityType.PV_REPORT, EntityType.PV_REPORT_CHUNKS],
    "tenants": [EntityType.TENANT, EntityType.WORKSPACE],
    "team_members": [EntityType.TEAM_MEMBERS, EntityType.TEAM],
    "market_research_sessions": [EntityType.MR_SESSION, EntityType.MR_PROJECT, EntityType.MR_RESULTS],
    "personas": [EntityType.PERSONA, EntityType.PERSONAS_LIST],
    "customer_profiles": [EntityType.CUSTOMER_PROFILE_V1, EntityType.CUSTOMER_PROFILE_V2],
    "value_maps": [EntityType.VALUE_MAP, EntityType.VALUE_MAP_PRODUCTS, EntityType.VALUE_MAP_PAIN_RELIEVERS, EntityType.VALUE_MAP_GAIN_CREATORS],
    "hypotheses": [EntityType.HYPOTHESIS, EntityType.HYPOTHESES_LIST],
    "assumptions": [EntityType.ASSUMPTION, EntityType.ASSUMPTIONS_LIST],
    "questionnaires": [EntityType.QUESTIONNAIRE, EntityType.QUESTIONNAIRE_RESPONSES],
    "chat_sessions": [EntityType.CHAT_SESSION, EntityType.CHAT_HISTORY, EntityType.CHAT_CONTEXT],
    "user_profiles": [EntityType.USER_PROFILE, EntityType.USER_WORKSPACES],
    "organizations": [EntityType.ORGANIZATION],
}


class CacheInvalidationService:
    """
    Centralized cache invalidation for write operations.
    
    Implements:
    - Write-through invalidation on database writes (Requirements 6.1, 6.2)
    - Pattern-based invalidation using Redis SCAN (Requirement 6.4)
    - Workflow cascade invalidation (Requirements 7.1-7.5)
    - Background task execution for non-blocking invalidation (Requirement 6.6)
    
    Usage:
        invalidation_service = CacheInvalidationService(cache_service)
        
        # After database write
        await invalidation_service.on_write(
            table_name="vmp_projects",
            operation=WriteOperation.UPDATE,
            record_id="project-123",
            tenant_id="tenant-456"
        )
        
        # After workflow step completion
        await invalidation_service.on_feature_completed(
            feature_entity=EntityType.CUSTOMER_PROFILE_V1,
            project_id="project-123",
            tenant_id="tenant-456"
        )
    """
    
    def __init__(self, cache_service: "RedisCacheService"):
        """
        Initialize CacheInvalidationService with a RedisCacheService instance.
        
        Args:
            cache_service: The underlying Redis cache service
        """
        self.cache = cache_service
    
    async def on_write(
        self,
        table_name: str,
        operation: WriteOperation,
        record_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        background: bool = False
    ) -> None:
        """
        Invalidate caches after database write.
        
        Call this after any CREATE/UPDATE/DELETE operation to ensure
        cache consistency.
        
        Args:
            table_name: Name of the database table that was modified
            operation: Type of write operation (CREATE/UPDATE/DELETE)
            record_id: ID of the record that was modified
            tenant_id: Tenant ID for isolation
            user_id: User ID (optional, for user-specific caches)
            old_data: Previous data before update (optional, for smart invalidation)
            new_data: New data after update (optional, for smart invalidation)
            background: If True, run invalidation in background task
            
        Requirements:
            6.1: Invalidates related entity caches after database write
            6.2: Invalidates related query caches using pattern matching
            6.6: Supports background task execution for non-blocking invalidation
        """
        if background:
            # Run invalidation in background task
            asyncio.create_task(
                self._do_invalidation(
                    table_name, operation, record_id, tenant_id, user_id, old_data, new_data
                )
            )
        else:
            await self._do_invalidation(
                table_name, operation, record_id, tenant_id, user_id, old_data, new_data
            )
    
    async def _do_invalidation(
        self,
        table_name: str,
        operation: WriteOperation,
        record_id: str,
        tenant_id: str,
        user_id: Optional[str],
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]]
    ) -> None:
        """
        Perform the actual cache invalidation.
        
        This method is separated to support both sync and background execution.
        """
        logger.info(
            f"Cache invalidation: {operation.value} on {table_name}:{record_id} "
            f"for tenant {tenant_id}"
        )
        
        try:
            # Invalidate entity caches
            await self._invalidate_entity_caches(table_name, record_id, tenant_id)
            
            # Invalidate query caches
            await self._invalidate_query_caches(table_name, tenant_id, user_id)
            
            logger.debug(f"Cache invalidation completed for {table_name}:{record_id}")
            
        except Exception as e:
            # Requirement 6.5: Log error and rely on TTL expiry as fallback
            logger.error(
                f"Cache invalidation failed for {table_name}:{record_id}: {e}. "
                "Relying on TTL expiry as fallback."
            )
    
    async def _invalidate_entity_caches(
        self,
        table_name: str,
        record_id: str,
        tenant_id: str
    ) -> None:
        """
        Invalidate specific entity caches based on table name.
        
        Args:
            table_name: Name of the database table
            record_id: ID of the record
            tenant_id: Tenant ID
        """
        entity_types = TABLE_TO_ENTITY_TYPE_MAP.get(table_name, [])
        
        for entity_type in entity_types:
            cache_key = f"{entity_type.value}:{tenant_id}:{record_id}"
            try:
                deleted = await self.cache.delete(cache_key)
                if deleted:
                    logger.debug(f"Invalidated entity cache: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to invalidate entity cache {cache_key}: {e}")
        
        # Also invalidate any variants using pattern matching
        for entity_type in entity_types:
            pattern = f"{entity_type.value}:{tenant_id}:{record_id}:*"
            try:
                deleted_count = await self.cache.delete_pattern(pattern)
                if deleted_count > 0:
                    logger.debug(f"Invalidated {deleted_count} variant caches for pattern: {pattern}")
            except Exception as e:
                logger.warning(f"Failed to invalidate variant caches for pattern {pattern}: {e}")
    
    async def _invalidate_query_caches(
        self,
        table_name: str,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Invalidate related query caches using patterns.
        
        Uses Redis SCAN to find and delete matching keys.
        
        Args:
            table_name: Name of the database table
            tenant_id: Tenant ID
            user_id: User ID (optional)
            
        Requirement 6.4: Uses Redis SCAN to find and delete matching keys
        """
        patterns = TABLE_TO_QUERY_CACHE_MAP.get(table_name, [])
        
        for pattern in patterns:
            # Resolve placeholders in pattern
            resolved_pattern = pattern.format(
                tenant_id=tenant_id,
                user_id=user_id or "*"
            )
            
            try:
                deleted_count = await self.cache.delete_pattern(resolved_pattern)
                if deleted_count > 0:
                    logger.debug(
                        f"Invalidated {deleted_count} query caches for pattern: {resolved_pattern}"
                    )
            except Exception as e:
                logger.warning(f"Failed to invalidate query caches for pattern {resolved_pattern}: {e}")
    
    async def on_feature_completed(
        self,
        feature_entity: EntityType,
        project_id: str,
        tenant_id: str,
        background: bool = False
    ) -> None:
        """
        Cascade invalidation when workflow step completes.
        
        This method invalidates all downstream dependent caches when a
        workflow step completes, ensuring data consistency across the
        19-step VPM workflow.
        
        Args:
            feature_entity: The entity type of the completed feature
            project_id: ID of the project
            tenant_id: Tenant ID
            background: If True, run invalidation in background task
            
        Requirements:
            7.1: Invalidates downstream dependent caches when workflow step completes
            7.3: Always invalidates PROJECT_FULL and CHAT_CONTEXT on any step completion
            7.4: Provides on_feature_completed method for cascade invalidation
        """
        if background:
            asyncio.create_task(
                self._do_cascade_invalidation(feature_entity, project_id, tenant_id)
            )
        else:
            await self._do_cascade_invalidation(feature_entity, project_id, tenant_id)
    
    async def _do_cascade_invalidation(
        self,
        feature_entity: EntityType,
        project_id: str,
        tenant_id: str
    ) -> None:
        """
        Perform the actual cascade invalidation.
        """
        logger.info(
            f"Workflow cascade invalidation: {feature_entity.value} completed "
            f"for project {project_id} in tenant {tenant_id}"
        )
        
        try:
            # Requirement 7.3: Always invalidate PROJECT_FULL and CHAT_CONTEXT
            await self._invalidate_always_required(project_id, tenant_id)
            
            # Invalidate the completed feature itself
            await self._invalidate_entity(feature_entity, project_id, tenant_id)
            
            # Requirement 7.1: Invalidate downstream dependencies
            downstream = WORKFLOW_DEPENDENCIES.get(feature_entity, [])
            for entity_type in downstream:
                await self._invalidate_entity(entity_type, project_id, tenant_id)
                logger.debug(f"Invalidated downstream {entity_type.value} for project {project_id}")
            
            logger.info(
                f"Cascade invalidation completed: invalidated {len(downstream) + 3} cache entries "
                f"for {feature_entity.value}"
            )
            
        except Exception as e:
            logger.error(
                f"Cascade invalidation failed for {feature_entity.value} "
                f"on project {project_id}: {e}. Relying on TTL expiry as fallback."
            )
    
    async def _invalidate_always_required(
        self,
        project_id: str,
        tenant_id: str
    ) -> None:
        """
        Invalidate caches that should always be invalidated on any workflow step.
        
        Requirement 7.3: Always invalidates PROJECT_FULL and CHAT_CONTEXT
        """
        always_invalidate = [
            EntityType.PROJECT_FULL,
            EntityType.CHAT_CONTEXT,
        ]
        
        for entity_type in always_invalidate:
            await self._invalidate_entity(entity_type, project_id, tenant_id)
    
    async def _invalidate_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        tenant_id: str
    ) -> None:
        """
        Invalidate a single entity cache entry.
        
        Args:
            entity_type: Type of entity to invalidate
            entity_id: ID of the entity
            tenant_id: Tenant ID
        """
        cache_key = f"{entity_type.value}:{tenant_id}:{entity_id}"
        try:
            await self.cache.delete(cache_key)
            logger.debug(f"Invalidated entity cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to invalidate entity cache {cache_key}: {e}")
    
    async def invalidate_project_caches(
        self,
        project_id: str,
        tenant_id: str
    ) -> int:
        """
        Invalidate all caches related to a project.
        
        This is useful when a project is deleted or when a major
        change affects all project data.
        
        Args:
            project_id: ID of the project
            tenant_id: Tenant ID
            
        Returns:
            Number of cache entries invalidated
        """
        invalidated_count = 0
        
        # Invalidate all project-related entity types
        project_entity_types = [
            EntityType.PROJECT,
            EntityType.PROJECT_FULL,
            EntityType.PERSONA,
            EntityType.PERSONAS_LIST,
            EntityType.CUSTOMER_PROFILE_V1,
            EntityType.CP_V1_JTBD,
            EntityType.CP_V1_PAINS,
            EntityType.CP_V1_GAINS,
            EntityType.HYPOTHESIS,
            EntityType.HYPOTHESES_LIST,
            EntityType.ASSUMPTION,
            EntityType.ASSUMPTIONS_LIST,
            EntityType.QUESTIONNAIRE,
            EntityType.QUESTIONNAIRE_RESPONSES,
            EntityType.MR_SESSION,
            EntityType.MR_PROJECT,
            EntityType.MR_RESULTS,
            EntityType.CUSTOMER_PROFILE_V2,
            EntityType.CP_V2_JTBD,
            EntityType.CP_V2_PAINS,
            EntityType.CP_V2_GAINS,
            EntityType.VALUE_MAP,
            EntityType.VALUE_MAP_PRODUCTS,
            EntityType.VALUE_MAP_PAIN_RELIEVERS,
            EntityType.VALUE_MAP_GAIN_CREATORS,
            EntityType.VPS_V1,
            EntityType.BMC_V1,
            EntityType.BMC_V1_SECTIONS,
            EntityType.SOLUTION_CRITIQUE,
            EntityType.CRITIQUE_SESSION,
            EntityType.VPS_V2,
            EntityType.BMC_V2,
            EntityType.BMC_V2_SECTIONS,
            EntityType.MVP_REQUIREMENTS,
            EntityType.AMRG_SESSION,
            EntityType.REQUIREMENT_SPECS,
            EntityType.CHAT_SESSION,
            EntityType.CHAT_HISTORY,
            EntityType.CHAT_CONTEXT,
            EntityType.PITCH_DECK,
            EntityType.PITCH_SESSION,
            EntityType.PITCH_SLIDES,
            EntityType.GTM_STRATEGY,
            EntityType.GTM_SESSION,
            EntityType.GTM_CHANNELS,
        ]
        
        for entity_type in project_entity_types:
            cache_key = f"{entity_type.value}:{tenant_id}:{project_id}"
            try:
                if await self.cache.delete(cache_key):
                    invalidated_count += 1
            except Exception as e:
                logger.warning(f"Failed to invalidate {cache_key}: {e}")
        
        logger.info(f"Invalidated {invalidated_count} project caches for project {project_id}")
        return invalidated_count
    
    async def invalidate_tenant_caches(
        self,
        tenant_id: str
    ) -> int:
        """
        Invalidate all caches for a tenant.
        
        This is useful when a tenant is deleted or when tenant-wide
        changes occur.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Number of cache entries invalidated
        """
        # Use pattern matching to delete all tenant caches
        pattern = f"*:{tenant_id}:*"
        
        try:
            deleted_count = await self.cache.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} caches for tenant {tenant_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to invalidate tenant caches for {tenant_id}: {e}")
            return 0
    
    def get_downstream_dependencies(
        self,
        feature_entity: EntityType
    ) -> List[EntityType]:
        """
        Get the list of downstream dependencies for a feature entity.
        
        This is useful for understanding what will be invalidated when
        a workflow step completes.
        
        Args:
            feature_entity: The entity type to get dependencies for
            
        Returns:
            List of downstream entity types
            
        Requirement 7.2: Maintains dependency map of workflow steps
        """
        return WORKFLOW_DEPENDENCIES.get(feature_entity, [])
    
    def get_query_cache_patterns(
        self,
        table_name: str
    ) -> List[str]:
        """
        Get the list of query cache patterns for a table.
        
        This is useful for understanding what query caches will be
        invalidated when a table is modified.
        
        Args:
            table_name: Name of the database table
            
        Returns:
            List of cache key patterns
            
        Requirement 6.3: Maintains mapping of database tables to cache key patterns
        """
        return TABLE_TO_QUERY_CACHE_MAP.get(table_name, [])


# Global singleton instance
_invalidation_service: Optional[CacheInvalidationService] = None


def get_invalidation_service() -> Optional[CacheInvalidationService]:
    """
    Get global cache invalidation service instance.
    
    Returns:
        CacheInvalidationService singleton instance or None if not initialized
    """
    return _invalidation_service


def init_invalidation_service(cache_service: "RedisCacheService") -> CacheInvalidationService:
    """
    Initialize cache invalidation service with a RedisCacheService.
    
    Args:
        cache_service: The underlying Redis cache service
        
    Returns:
        Initialized CacheInvalidationService instance
    """
    global _invalidation_service
    _invalidation_service = CacheInvalidationService(cache_service)
    logger.info("CacheInvalidationService initialized")
    return _invalidation_service


def shutdown_invalidation_service() -> None:
    """Shutdown cache invalidation service."""
    global _invalidation_service
    _invalidation_service = None
    logger.info("CacheInvalidationService shutdown")
