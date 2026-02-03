"""
Entity Cache Service for Yuba Backend.

Provides tenant-isolated caching for all 19 workflow feature entity types.
Implements cache key format: {entity_type}:{tenant_id}:{entity_id}

This service implements:
- Tenant isolation in cache keys (Requirements 2.1, 2.2)
- Support for all 19 workflow feature entity types (Requirement 2.3)
- Configurable TTL per entity type (Requirement 2.5)
- Immediate invalidation on entity updates (Requirement 2.4)
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """
    All cacheable entity types in the system.
    
    Covers all 19 workflow features plus core entities.
    Each entity type has a short string value for compact cache keys.
    """
    
    # Core entities
    TENANT = "tenant"
    WORKSPACE = "workspace"
    USER_PROFILE = "user_profile"
    USER_WORKSPACES = "user_workspaces"
    ORGANIZATION = "org"
    TEAM = "team"
    TEAM_MEMBERS = "team_members"
    
    # Feature 1: Problem Validation Report
    PV_REPORT = "pv_report"
    PV_REPORT_CHUNKS = "pv_report_chunks"
    PV_SESSION = "pv_session"
    
    # Feature 2: Project
    PROJECT = "project"
    PROJECT_FULL = "project_full"
    USER_PROJECTS = "user_projects"
    TENANT_PROJECTS = "tenant_projects"
    
    # Feature 3: Persona
    PERSONA = "persona"
    PERSONAS_LIST = "personas_list"
    
    # Feature 4: Customer Profile v1
    CUSTOMER_PROFILE_V1 = "cp_v1"
    CP_V1_JTBD = "cp_v1_jtbd"
    CP_V1_PAINS = "cp_v1_pains"
    CP_V1_GAINS = "cp_v1_gains"
    
    # Feature 5: Hypothesis
    HYPOTHESIS = "hypothesis"
    HYPOTHESES_LIST = "hypotheses_list"
    
    # Feature 6: Assumption
    ASSUMPTION = "assumption"
    ASSUMPTIONS_LIST = "assumptions_list"
    
    # Feature 7: Questionnaire
    QUESTIONNAIRE = "questionnaire"
    QUESTIONNAIRE_RESPONSES = "questionnaire_resp"
    
    # Feature 8: Market Research
    MR_SESSION = "mr_session"
    MR_PROJECT = "mr_project"
    MR_RESULTS = "mr_results"
    MR_STATISTICS = "mr_statistics"
    
    # Feature 9: Customer Profile v2
    CUSTOMER_PROFILE_V2 = "cp_v2"
    CP_V2_JTBD = "cp_v2_jtbd"
    CP_V2_PAINS = "cp_v2_pains"
    CP_V2_GAINS = "cp_v2_gains"
    
    # Feature 10: Value Map
    VALUE_MAP = "value_map"
    VALUE_MAP_PRODUCTS = "vm_products"
    VALUE_MAP_PAIN_RELIEVERS = "vm_pain_rel"
    VALUE_MAP_GAIN_CREATORS = "vm_gain_cre"
    
    # Feature 11: VPS v1
    VPS_V1 = "vps_v1"
    
    # Feature 12: BMC v1
    BMC_V1 = "bmc_v1"
    BMC_V1_SECTIONS = "bmc_v1_sections"
    
    # Feature 13: Solution Critique
    SOLUTION_CRITIQUE = "soln_critique"
    CRITIQUE_SESSION = "critique_session"
    
    # Feature 14: VPS v2
    VPS_V2 = "vps_v2"
    
    # Feature 15: BMC v2
    BMC_V2 = "bmc_v2"
    BMC_V2_SECTIONS = "bmc_v2_sections"
    
    # Feature 16: Requirement Generator
    MVP_REQUIREMENTS = "mvp_req"
    AMRG_SESSION = "amrg_session"
    REQUIREMENT_SPECS = "req_specs"
    
    # Feature 17: Chat with Project
    CHAT_SESSION = "chat_session"
    CHAT_HISTORY = "chat_history"
    CHAT_CONTEXT = "chat_context"
    
    # Feature 18: Pitch Deck
    PITCH_DECK = "pitch_deck"
    PITCH_SESSION = "pitch_session"
    PITCH_SLIDES = "pitch_slides"
    
    # Feature 19: GTM
    GTM_STRATEGY = "gtm_strategy"
    GTM_SESSION = "gtm_session"
    GTM_CHANNELS = "gtm_channels"


# TTL Configuration per entity type (in seconds)
# Requirement 2.5: Configurable TTLs ranging from 1 minute to 30 minutes
ENTITY_TTL_CONFIG: Dict[EntityType, int] = {
    # Core entities
    EntityType.TENANT: 600,              # 10 min - rarely changes
    EntityType.WORKSPACE: 600,           # 10 min - rarely changes
    EntityType.USER_PROFILE: 300,        # 5 min - moderate changes
    EntityType.USER_WORKSPACES: 300,     # 5 min - moderate changes
    EntityType.ORGANIZATION: 1800,       # 30 min - very stable
    EntityType.TEAM: 600,                # 10 min - rarely changes
    EntityType.TEAM_MEMBERS: 600,        # 10 min - rarely changes
    
    # Feature 1: PV Report
    EntityType.PV_REPORT: 600,           # 10 min - stable after generation
    EntityType.PV_REPORT_CHUNKS: 1800,   # 30 min - very stable
    EntityType.PV_SESSION: 60,           # 1 min - active during generation
    
    # Feature 2: Project
    EntityType.PROJECT: 300,             # 5 min - moderate changes
    EntityType.PROJECT_FULL: 120,        # 2 min - aggregated data
    EntityType.USER_PROJECTS: 180,       # 3 min - list changes
    EntityType.TENANT_PROJECTS: 180,     # 3 min - list changes
    
    # Feature 3-6: Persona, CP v1, Hypothesis, Assumption
    EntityType.PERSONA: 300,             # 5 min
    EntityType.PERSONAS_LIST: 300,       # 5 min
    EntityType.CUSTOMER_PROFILE_V1: 300, # 5 min
    EntityType.CP_V1_JTBD: 300,          # 5 min
    EntityType.CP_V1_PAINS: 300,         # 5 min
    EntityType.CP_V1_GAINS: 300,         # 5 min
    EntityType.HYPOTHESIS: 300,          # 5 min
    EntityType.HYPOTHESES_LIST: 300,     # 5 min
    EntityType.ASSUMPTION: 300,          # 5 min
    EntityType.ASSUMPTIONS_LIST: 300,    # 5 min
    
    # Feature 7: Questionnaire
    EntityType.QUESTIONNAIRE: 600,       # 10 min - stable after creation
    EntityType.QUESTIONNAIRE_RESPONSES: 120,  # 2 min - responses come in
    
    # Feature 8: Market Research
    EntityType.MR_SESSION: 60,           # 1 min - active during research
    EntityType.MR_PROJECT: 300,          # 5 min
    EntityType.MR_RESULTS: 600,          # 10 min - stable after completion
    EntityType.MR_STATISTICS: 1800,      # 30 min - aggregated stats
    
    # Feature 9: CP v2
    EntityType.CUSTOMER_PROFILE_V2: 300, # 5 min
    EntityType.CP_V2_JTBD: 300,          # 5 min
    EntityType.CP_V2_PAINS: 300,         # 5 min
    EntityType.CP_V2_GAINS: 300,         # 5 min
    
    # Feature 10: Value Map
    EntityType.VALUE_MAP: 180,           # 3 min - edited during VPC
    EntityType.VALUE_MAP_PRODUCTS: 180,  # 3 min
    EntityType.VALUE_MAP_PAIN_RELIEVERS: 180,  # 3 min
    EntityType.VALUE_MAP_GAIN_CREATORS: 180,   # 3 min
    
    # Feature 11-15: VPS, BMC, Critique
    EntityType.VPS_V1: 600,              # 10 min - stable after generation
    EntityType.BMC_V1: 600,              # 10 min
    EntityType.BMC_V1_SECTIONS: 300,     # 5 min
    EntityType.SOLUTION_CRITIQUE: 600,   # 10 min
    EntityType.CRITIQUE_SESSION: 60,     # 1 min - active
    EntityType.VPS_V2: 600,              # 10 min
    EntityType.BMC_V2: 600,              # 10 min
    EntityType.BMC_V2_SECTIONS: 300,     # 5 min
    
    # Feature 16: Requirements
    EntityType.MVP_REQUIREMENTS: 600,    # 10 min
    EntityType.AMRG_SESSION: 60,         # 1 min - active
    EntityType.REQUIREMENT_SPECS: 600,   # 10 min
    
    # Feature 17: Chat
    EntityType.CHAT_SESSION: 300,        # 5 min
    EntityType.CHAT_HISTORY: 300,        # 5 min
    EntityType.CHAT_CONTEXT: 120,        # 2 min - context changes
    
    # Feature 18-19: Pitch, GTM
    EntityType.PITCH_DECK: 600,          # 10 min
    EntityType.PITCH_SESSION: 60,        # 1 min - active
    EntityType.PITCH_SLIDES: 300,        # 5 min
    EntityType.GTM_STRATEGY: 600,        # 10 min
    EntityType.GTM_SESSION: 60,          # 1 min - active
    EntityType.GTM_CHANNELS: 600,        # 10 min
}


def get_entity_ttl(entity_type: EntityType) -> int:
    """
    Get the configured TTL for an entity type.
    
    Args:
        entity_type: The entity type to get TTL for
        
    Returns:
        TTL in seconds, defaults to 300 (5 min) if not configured
    """
    return ENTITY_TTL_CONFIG.get(entity_type, 300)



class EntityCacheService:
    """
    Centralized entity caching with tenant isolation.
    
    Implements:
    - Tenant-isolated cache keys: {entity_type}:{tenant_id}:{entity_id}
    - Tenant validation on retrieval (cross-tenant access prevention)
    - Configurable TTL per entity type
    - Immediate invalidation on entity updates
    
    Requirements: 2.1, 2.2, 2.4
    """
    
    def __init__(self, cache_service: "RedisCacheService"):
        """
        Initialize EntityCacheService with a RedisCacheService instance.
        
        Args:
            cache_service: The underlying Redis cache service
        """
        self.cache = cache_service
    
    def _build_key(
        self,
        entity_type: EntityType,
        entity_id: str,
        tenant_id: str,
        variant: Optional[str] = None
    ) -> str:
        """
        Build tenant-isolated cache key.
        
        Key format: {entity_type}:{tenant_id}:{entity_id}[:variant]
        
        This format ensures:
        - Entity type isolation (different types don't collide)
        - Tenant isolation (different tenants don't share data)
        - Entity identification (unique per entity)
        - Optional variant for sub-resources
        
        Args:
            entity_type: The type of entity being cached
            entity_id: The unique identifier of the entity
            tenant_id: The tenant ID for isolation
            variant: Optional variant for sub-resources (e.g., "jtbd", "pains")
            
        Returns:
            Formatted cache key string
            
        Requirement 2.1: Cache key includes tenant_id for isolation
        """
        key_parts = [entity_type.value, tenant_id, entity_id]
        if variant:
            key_parts.append(variant)
        return ":".join(key_parts)
    
    async def get_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        tenant_id: str,
        variant: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached entity with tenant validation.
        
        This method retrieves a cached entity and validates that the
        requesting tenant matches the cached entity's tenant. If there's
        a mismatch, it returns None (cache miss) to prevent cross-tenant
        data access.
        
        Args:
            entity_type: The type of entity to retrieve
            entity_id: The unique identifier of the entity
            tenant_id: The requesting tenant's ID
            variant: Optional variant for sub-resources
            
        Returns:
            Cached entity data or None if not found/tenant mismatch
            
        Requirement 2.2: Validates requesting tenant matches cached tenant_id
        """
        cache_key = self._build_key(entity_type, entity_id, tenant_id, variant)
        
        try:
            cached_data = await self.cache.get(cache_key)
            
            if cached_data is None:
                logger.debug(f"Cache miss for {cache_key}")
                return None
            
            # Validate tenant isolation
            # The cached data should contain _tenant_id metadata
            if isinstance(cached_data, dict):
                cached_tenant = cached_data.get("_tenant_id")
                if cached_tenant and cached_tenant != tenant_id:
                    # Cross-tenant access attempt - treat as cache miss
                    logger.warning(
                        f"Cross-tenant cache access attempt: "
                        f"requested tenant {tenant_id}, cached tenant {cached_tenant}"
                    )
                    return None
                
                # Return the data without the internal metadata
                result = {k: v for k, v in cached_data.items() if not k.startswith("_")}
                logger.debug(f"Cache hit for {cache_key}")
                return result
            
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data
            
        except Exception as e:
            logger.error(f"Error retrieving entity from cache: {e}")
            return None
    
    async def set_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        tenant_id: str,
        data: Dict[str, Any],
        variant: Optional[str] = None,
        ttl_override: Optional[int] = None
    ) -> bool:
        """
        Cache entity with appropriate TTL and tenant metadata.
        
        Stores the entity data with tenant metadata for validation
        on retrieval. Uses the configured TTL for the entity type
        unless overridden.
        
        Args:
            entity_type: The type of entity to cache
            entity_id: The unique identifier of the entity
            tenant_id: The tenant ID for isolation
            data: The entity data to cache
            variant: Optional variant for sub-resources
            ttl_override: Optional TTL override in seconds
            
        Returns:
            True if cached successfully, False otherwise
            
        Requirement 2.5: Uses configurable TTL per entity type
        """
        cache_key = self._build_key(entity_type, entity_id, tenant_id, variant)
        
        # Determine TTL
        ttl = ttl_override if ttl_override is not None else get_entity_ttl(entity_type)
        
        # Add tenant metadata for validation on retrieval
        cache_data = {
            **data,
            "_tenant_id": tenant_id,
            "_entity_type": entity_type.value,
        }
        
        try:
            result = await self.cache.set(cache_key, cache_data, ttl=ttl)
            if result:
                logger.debug(f"Cached entity {cache_key} with TTL {ttl}s")
            return result
        except Exception as e:
            logger.error(f"Error caching entity: {e}")
            return False
    
    async def invalidate_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        tenant_id: str,
        variant: Optional[str] = None
    ) -> bool:
        """
        Invalidate cached entity immediately.
        
        Removes the entity from cache to ensure subsequent reads
        fetch fresh data from the database.
        
        Args:
            entity_type: The type of entity to invalidate
            entity_id: The unique identifier of the entity
            tenant_id: The tenant ID
            variant: Optional variant for sub-resources
            
        Returns:
            True if invalidated successfully, False otherwise
            
        Requirement 2.4: Invalidates cached entity immediately on update
        """
        cache_key = self._build_key(entity_type, entity_id, tenant_id, variant)
        
        try:
            result = await self.cache.delete(cache_key)
            logger.debug(f"Invalidated entity cache: {cache_key}")
            return result
        except Exception as e:
            logger.error(f"Error invalidating entity cache: {e}")
            return False
    
    async def invalidate_entity_all_variants(
        self,
        entity_type: EntityType,
        entity_id: str,
        tenant_id: str
    ) -> int:
        """
        Invalidate all variants of a cached entity.
        
        Uses pattern matching to delete all cache entries for an entity
        regardless of variant.
        
        Args:
            entity_type: The type of entity to invalidate
            entity_id: The unique identifier of the entity
            tenant_id: The tenant ID
            
        Returns:
            Number of cache entries invalidated
        """
        pattern = f"{entity_type.value}:{tenant_id}:{entity_id}:*"
        
        try:
            # Delete the base key
            base_key = self._build_key(entity_type, entity_id, tenant_id)
            await self.cache.delete(base_key)
            
            # Delete all variants
            deleted = await self.cache.delete_pattern(pattern)
            logger.debug(f"Invalidated {deleted + 1} cache entries for {entity_type.value}:{entity_id}")
            return deleted + 1
        except Exception as e:
            logger.error(f"Error invalidating entity variants: {e}")
            return 0
    
    # Convenience methods for common entities
    
    async def get_project(
        self,
        project_id: str,
        tenant_id: str,
        full: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get cached project data."""
        entity_type = EntityType.PROJECT_FULL if full else EntityType.PROJECT
        return await self.get_entity(entity_type, project_id, tenant_id)
    
    async def set_project(
        self,
        project_id: str,
        tenant_id: str,
        data: Dict[str, Any],
        full: bool = False
    ) -> bool:
        """Cache project data."""
        entity_type = EntityType.PROJECT_FULL if full else EntityType.PROJECT
        return await self.set_entity(entity_type, project_id, tenant_id, data)
    
    async def invalidate_project(
        self,
        project_id: str,
        tenant_id: str
    ) -> bool:
        """Invalidate all project-related caches."""
        # Invalidate both PROJECT and PROJECT_FULL
        await self.invalidate_entity(EntityType.PROJECT, project_id, tenant_id)
        await self.invalidate_entity(EntityType.PROJECT_FULL, project_id, tenant_id)
        return True
    
    async def get_user_profile(
        self,
        user_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached user profile."""
        return await self.get_entity(EntityType.USER_PROFILE, user_id, tenant_id)
    
    async def set_user_profile(
        self,
        user_id: str,
        tenant_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Cache user profile."""
        return await self.set_entity(EntityType.USER_PROFILE, user_id, tenant_id, data)
    
    async def invalidate_user_profile(
        self,
        user_id: str,
        tenant_id: str
    ) -> bool:
        """Invalidate user profile cache."""
        return await self.invalidate_entity(EntityType.USER_PROFILE, user_id, tenant_id)


# Type hint import for RedisCacheService (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .redis_service import RedisCacheService


# Global singleton instance
_entity_cache_service: Optional[EntityCacheService] = None


def get_entity_cache_service() -> Optional[EntityCacheService]:
    """
    Get global entity cache service instance.
    
    Returns:
        EntityCacheService singleton instance or None if not initialized
    """
    return _entity_cache_service


def init_entity_cache_service(cache_service: "RedisCacheService") -> EntityCacheService:
    """
    Initialize entity cache service with a RedisCacheService.
    
    Args:
        cache_service: The underlying Redis cache service
        
    Returns:
        Initialized EntityCacheService instance
    """
    global _entity_cache_service
    _entity_cache_service = EntityCacheService(cache_service)
    logger.info("EntityCacheService initialized")
    return _entity_cache_service


def shutdown_entity_cache_service() -> None:
    """Shutdown entity cache service."""
    global _entity_cache_service
    _entity_cache_service = None
    logger.info("EntityCacheService shutdown")
