"""
Database Adapter for Pitch Deck Generator

Handles all database operations for:
- Pitch deck CRUD (stored in vmp_projects.pitch_deck_data)
- Project context loading
- Deck versioning
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.mint.api.system.core.supabase_client import get_service_role_client

logger = logging.getLogger(__name__)


class PitchDeckDatabaseAdapter:
    """
    Database adapter for Pitch Deck Generator operations.
    
    Uses service role client for backend operations (bypasses RLS).
    All operations include explicit tenant_id checks for security.
    
    Pitch deck data is stored in vmp_projects.pitch_deck_data JSONB column.
    """
    
    PROJECTS_TABLE = "vmp_projects"
    CHUNKS_TABLE = "chunks"
    
    def __init__(self, use_service_role: bool = True):
        """Initialize with service role client."""
        if use_service_role:
            self.supabase = get_service_role_client()
            self.client = self.supabase.client
        else:
            self.supabase = get_service_role_client()
            self.client = self.supabase.client
        logger.info("✅ PitchDeckDatabaseAdapter initialized")
    
    # =========================================================================
    # PROJECT VERIFICATION & CONTEXT
    # =========================================================================
    
    async def verify_project_access(
        self,
        project_id: str,
        tenant_id: str
    ) -> bool:
        """
        Verify that the project exists and belongs to the tenant.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID to verify ownership
            
        Returns:
            True if access is valid, False otherwise
        """
        try:
            result = self.client.table(self.PROJECTS_TABLE)\
                .select("id, tenant_id")\
                .eq("id", project_id)\
                .execute()
            
            if not result.data:
                logger.warning(f"Project {project_id} not found")
                return False
            
            project = result.data[0]
            
            if project["tenant_id"] != tenant_id:
                logger.warning(f"Tenant mismatch: project belongs to {project['tenant_id']}, not {tenant_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying project access: {e}")
            return False
    
    async def load_project_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load project context for deck generation.
        
        Returns project metadata and available artifacts summary.
        """
        try:
            result = self.client.table(self.PROJECTS_TABLE)\
                .select(
                    "id, tenant_id, user_id, name, description, "
                    "personas, vpc_data, vpc_v2_data, field_prep_data, "
                    "mvp_data, analysis_data, soln_critique_data, "
                    "refined_problem_statement, enhanced_context, "
                    "pitch_deck_data, pitch_deck_status"
                )\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if not result.data:
                logger.warning(f"Project {project_id} not found for tenant {tenant_id}")
                return None
            
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error loading project context: {e}")
            return None
    
    async def get_project_summary(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get a summary of the project for deck planning.
        
        Returns:
            Dict with project_name, description, and available_artifacts list
        """
        project = await self.load_project_context(project_id, tenant_id)
        if not project:
            return {
                "project_name": "Unknown",
                "project_description": "",
                "available_artifacts": [],
                "has_personas": False,
                "has_vpc_v2": False,
                "has_bmc": False,
                "has_vps": False,
                "has_market_research": False,
                "has_mvp_requirements": False,
            }
        
        # Determine available artifacts
        available_artifacts = []
        
        # Check personas
        personas = project.get("personas", [])
        if personas and len(personas) > 0:
            available_artifacts.append("vmp_persona")
        
        # Check VPC v1 data
        vpc_data = project.get("vpc_data", {})
        if vpc_data:
            if vpc_data.get("customer_profile"):
                available_artifacts.append("vmp_customer_profile")
            if vpc_data.get("value_map"):
                available_artifacts.append("vmp_value_map")
        
        # Check VPC v2 data
        vpc_v2_data = project.get("vpc_v2_data", {})
        if vpc_v2_data:
            for key, value in vpc_v2_data.items():
                if key.startswith("P") and isinstance(value, dict):
                    if value.get("customer_profile"):
                        if "vmp_customer_profile_v2" not in available_artifacts:
                            available_artifacts.append("vmp_customer_profile_v2")
                    if value.get("value_proposition"):
                        if "vmp_vps_v2" not in available_artifacts:
                            available_artifacts.append("vmp_vps_v2")
                    if value.get("bmc"):
                        if "vmp_bmc_v2" not in available_artifacts:
                            available_artifacts.append("vmp_bmc_v2")
        
        # Check field prep data
        field_prep = project.get("field_prep_data", {})
        if field_prep:
            if field_prep.get("hypotheses"):
                available_artifacts.append("vmp_hypothesis")
            if field_prep.get("assumptions"):
                available_artifacts.append("vmp_assumptions")
            if field_prep.get("questionnaires"):
                available_artifacts.append("vmp_questionnaire")
        
        # Check MVP data
        mvp_data = project.get("mvp_data", {})
        if mvp_data and (mvp_data.get("amrg") or mvp_data.get("mvp_requirements")):
            available_artifacts.append("vmp_mvp_requirements")
        
        # Check analysis data (market research)
        analysis_data = project.get("analysis_data", {})
        if analysis_data and analysis_data.get("stage") == "analysis_completed":
            available_artifacts.append("vmp_market_research")
        
        # Build summary text
        summary_parts = []
        if project.get("name"):
            summary_parts.append(f"Project: {project.get('name')}")
        if project.get("description"):
            summary_parts.append(f"Description: {project.get('description')}")
        if project.get("refined_problem_statement"):
            summary_parts.append(f"Problem: {project.get('refined_problem_statement')}")
        
        # Add enhanced context if available
        enhanced_context = project.get("enhanced_context", {})
        if enhanced_context:
            if enhanced_context.get("industry"):
                summary_parts.append(f"Industry: {enhanced_context.get('industry')}")
            if enhanced_context.get("target_market"):
                summary_parts.append(f"Target Market: {enhanced_context.get('target_market')}")
        
        # Auto-detect category from project data
        detected_category = self._detect_category(project, enhanced_context, vpc_v2_data, mvp_data)
        
        return {
            "project_name": project.get("name", "Unknown"),
            "project_description": project.get("description", ""),
            "refined_problem_statement": project.get("refined_problem_statement", ""),
            "available_artifacts": available_artifacts,
            "has_personas": "vmp_persona" in available_artifacts,
            "has_vpc_v2": "vmp_vps_v2" in available_artifacts or "vmp_customer_profile_v2" in available_artifacts,
            "has_bmc": "vmp_bmc_v2" in available_artifacts,
            "has_vps": "vmp_vps_v2" in available_artifacts,
            "has_market_research": "vmp_market_research" in available_artifacts,
            "has_mvp_requirements": "vmp_mvp_requirements" in available_artifacts,
            "summary_text": "\n".join(summary_parts),
            "enhanced_context": enhanced_context,
            "detected_category": detected_category,
        }
    
    def _detect_category(
        self,
        project: Dict[str, Any],
        enhanced_context: Dict[str, Any],
        vpc_v2_data: Dict[str, Any],
        mvp_data: Dict[str, Any]
    ) -> str:
        """
        Auto-detect business category from project data.
        
        Sources checked (in priority order):
        1. enhanced_context.business_type or category
        2. enhanced_context.industry keywords
        3. BMC revenue streams / channels
        4. MVP requirements product type
        5. Project description keywords
        
        Returns:
            Category string: PLATFORM_SAAS, CPG, INFRA_PROJECT, or OTHER
        """
        # Priority 1: Direct category in enhanced_context
        if enhanced_context:
            business_type = enhanced_context.get("business_type", "").upper()
            category = enhanced_context.get("category", "").upper()
            
            # Check direct mappings
            for val in [business_type, category]:
                if "SAAS" in val or "SOFTWARE" in val or "PLATFORM" in val:
                    return "PLATFORM_SAAS"
                if "CPG" in val or "CONSUMER" in val or "RETAIL" in val or "ECOMMERCE" in val:
                    return "CPG"
                if "INFRA" in val or "INFRASTRUCTURE" in val or "HARDWARE" in val:
                    return "INFRA_PROJECT"
            
            # Check industry keywords
            industry = enhanced_context.get("industry", "").lower()
            if any(kw in industry for kw in ["saas", "software", "tech", "platform", "digital", "app", "cloud"]):
                return "PLATFORM_SAAS"
            if any(kw in industry for kw in ["retail", "consumer", "cpg", "food", "beverage", "fashion"]):
                return "CPG"
            if any(kw in industry for kw in ["infrastructure", "hardware", "manufacturing", "construction"]):
                return "INFRA_PROJECT"
        
        # Priority 2: Check BMC data for revenue model hints
        if vpc_v2_data:
            for key, value in vpc_v2_data.items():
                if key.startswith("P") and isinstance(value, dict):
                    bmc = value.get("bmc", {})
                    if bmc:
                        # Check revenue streams
                        revenue_streams = str(bmc.get("revenue_streams", "")).lower()
                        channels = str(bmc.get("channels", "")).lower()
                        
                        if any(kw in revenue_streams for kw in ["subscription", "saas", "license", "recurring"]):
                            return "PLATFORM_SAAS"
                        if any(kw in revenue_streams for kw in ["retail", "e-commerce", "product sales"]):
                            return "CPG"
                        if any(kw in channels for kw in ["app", "web", "platform", "api"]):
                            return "PLATFORM_SAAS"
        
        # Priority 3: Check MVP data for product type hints
        if mvp_data:
            mvp_reqs = mvp_data.get("amrg") or mvp_data.get("mvp_requirements", {})
            if mvp_reqs:
                mvp_str = str(mvp_reqs).lower()
                if any(kw in mvp_str for kw in ["app", "platform", "software", "api", "dashboard", "saas"]):
                    return "PLATFORM_SAAS"
                if any(kw in mvp_str for kw in ["product", "packaging", "retail", "inventory"]):
                    return "CPG"
        
        # Priority 4: Check project description
        description = (project.get("description", "") + " " + project.get("refined_problem_statement", "")).lower()
        if any(kw in description for kw in ["app", "platform", "software", "saas", "digital", "automation"]):
            return "PLATFORM_SAAS"
        if any(kw in description for kw in ["product", "consumer", "retail", "goods", "packaging"]):
            return "CPG"
        if any(kw in description for kw in ["infrastructure", "hardware", "construction"]):
            return "INFRA_PROJECT"
        
        # Default
        return "OTHER"
    
    # =========================================================================
    # PITCH DECK CRUD
    # =========================================================================
    
    async def get_pitch_deck_data(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get the pitch_deck_data for a project.
        
        Returns:
            Dict with current_version and versions array
        """
        try:
            result = self.client.table(self.PROJECTS_TABLE)\
                .select("pitch_deck_data, pitch_deck_status")\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if not result.data:
                return {"current_version": 0, "versions": []}
            
            data = result.data[0].get("pitch_deck_data", {})
            if not data:
                return {"current_version": 0, "versions": []}
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting pitch deck data: {e}")
            return {"current_version": 0, "versions": []}
    
    async def get_next_version(
        self,
        project_id: str,
        tenant_id: str
    ) -> int:
        """Get the next version number for a new deck."""
        data = await self.get_pitch_deck_data(project_id, tenant_id)
        return data.get("current_version", 0) + 1
    
    async def update_pitch_deck_status(
        self,
        project_id: str,
        tenant_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the pitch_deck_status column.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            status: 'not_started', 'processing', 'completed', 'failed'
            error_message: Optional error message for failed status
        """
        try:
            update_data = {
                "pitch_deck_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.PROJECTS_TABLE)\
                .update(update_data)\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Updated pitch deck status to '{status}' for project {project_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating pitch deck status: {e}")
            return False
    
    async def save_deck_version(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        deck_version: Dict[str, Any]
    ) -> bool:
        """
        Save a new deck version to pitch_deck_data.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User who triggered generation
            deck_version: Complete deck version object
        """
        try:
            # Get current data
            current_data = await self.get_pitch_deck_data(project_id, tenant_id)
            
            # Add new version
            version_number = deck_version.get("version", current_data.get("current_version", 0) + 1)
            deck_version["version"] = version_number
            deck_version["created_at"] = datetime.utcnow().isoformat()
            deck_version["created_by"] = user_id
            
            versions = current_data.get("versions", [])
            versions.append(deck_version)
            
            # Update pitch_deck_data
            new_data = {
                "current_version": version_number,
                "versions": versions
            }
            
            update_result = self.client.table(self.PROJECTS_TABLE)\
                .update({
                    "pitch_deck_data": new_data,
                    "pitch_deck_status": deck_version.get("status", "completed"),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if update_result.data:
                logger.info(f"✅ Saved pitch deck version {version_number} for project {project_id}")
                return True
            
            logger.error(f"Failed to save pitch deck version - no data returned")
            return False
            
        except Exception as e:
            logger.error(f"Error saving deck version: {e}")
            return False
    
    async def get_deck_version(
        self,
        project_id: str,
        tenant_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific deck version or the latest.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            version: Specific version number, or None for latest
            
        Returns:
            Deck version dict or None
        """
        try:
            data = await self.get_pitch_deck_data(project_id, tenant_id)
            versions = data.get("versions", [])
            
            if not versions:
                return None
            
            if version is None:
                # Return latest
                return versions[-1]
            
            # Find specific version
            for v in versions:
                if v.get("version") == version:
                    return v
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting deck version: {e}")
            return None
    
    async def list_deck_versions(
        self,
        project_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all deck versions for a project.
        
        Returns:
            List of version summaries (version, purpose, stage, status, created_at)
        """
        try:
            data = await self.get_pitch_deck_data(project_id, tenant_id)
            versions = data.get("versions", [])
            
            summaries = []
            for v in versions:
                summaries.append({
                    "version": v.get("version"),
                    "deck_purpose": v.get("deck_purpose"),
                    "stage": v.get("stage"),
                    "category": v.get("category"),
                    "slide_count": len(v.get("slides", [])),
                    "status": v.get("status"),
                    "created_at": v.get("created_at"),
                    "created_by": v.get("created_by"),
                })
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error listing deck versions: {e}")
            return []
    
    # =========================================================================
    # ARTIFACT LOADING (for RAG context)
    # =========================================================================
    
    async def get_artifact_chunks(
        self,
        project_id: str,
        tenant_id: str,
        artifact_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chunks for specified artifact types.
        
        This is used for direct chunk loading when not using vector search.
        """
        try:
            query = self.client.table(self.CHUNKS_TABLE)\
                .select("*")\
                .eq("project_id", project_id)\
                .eq("tenant_id", tenant_id)
            
            if artifact_types:
                query = query.in_("source_type", artifact_types)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting artifact chunks: {e}")
            return []
