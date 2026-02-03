"""
Database Adapter for GTM Strategy Generator

Handles all database operations for:
- GTM strategy CRUD (stored in vmp_projects.gtm_data)
- Project context loading
- GTM versioning
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.mint.api.system.core.supabase_client import get_service_role_client

logger = logging.getLogger(__name__)


class GTMDatabaseAdapter:
    """
    Database adapter for GTM Strategy Generator operations.
    
    Uses service role client for backend operations (bypasses RLS).
    All operations include explicit tenant_id checks for security.
    
    GTM data is stored in vmp_projects.gtm_data JSONB column.
    """
    
    PROJECTS_TABLE = "vmp_projects"
    CHUNKS_TABLE = "chunks"
    
    def __init__(self, use_service_role: bool = True):
        """Initialize with service role client."""
        self.supabase = get_service_role_client()
        self.client = self.supabase.client
        logger.info("✅ GTMDatabaseAdapter initialized")
    
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
        Load project context for GTM generation.
        
        Returns project metadata and available artifacts summary.
        """
        try:
            result = self.client.table(self.PROJECTS_TABLE)\
                .select(
                    "id, tenant_id, user_id, name, description, "
                    "personas, vpc_data, vpc_v2_data, field_prep_data, "
                    "mvp_data, analysis_data, soln_critique_data, "
                    "refined_problem_statement, enhanced_context, "
                    "gtm_data, gtm_status, pitch_deck_data"
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
        Get a summary of the project for GTM planning.
        
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
                "has_pitch_deck": False,
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
        
        # Check solution critique
        soln_critique = project.get("soln_critique_data")
        if soln_critique:
            available_artifacts.append("vmp_soln_critique")
        
        # Check pitch deck
        pitch_deck_data = project.get("pitch_deck_data", {})
        if pitch_deck_data and pitch_deck_data.get("versions"):
            available_artifacts.append("vmp_pitch_deck")
        
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
            "has_pitch_deck": "vmp_pitch_deck" in available_artifacts,
            "summary_text": "\n".join(summary_parts),
            "enhanced_context": enhanced_context,
        }
    
    # =========================================================================
    # GTM DATA CRUD
    # =========================================================================
    
    async def get_gtm_data(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get the gtm_data for a project.
        
        Returns:
            Dict with current_version and versions array
        """
        try:
            result = self.client.table(self.PROJECTS_TABLE)\
                .select("gtm_data, gtm_status")\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if not result.data:
                return {"current_version": 0, "versions": []}
            
            data = result.data[0].get("gtm_data", {})
            if not data:
                return {"current_version": 0, "versions": []}
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting GTM data: {e}")
            return {"current_version": 0, "versions": []}
    
    async def get_next_version(
        self,
        project_id: str,
        tenant_id: str
    ) -> int:
        """Get the next version number for a new GTM strategy."""
        data = await self.get_gtm_data(project_id, tenant_id)
        return data.get("current_version", 0) + 1
    
    async def update_gtm_status(
        self,
        project_id: str,
        tenant_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the gtm_status column.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            status: 'not_started', 'processing', 'completed', 'failed'
            error_message: Optional error message for failed status
        """
        try:
            update_data = {
                "gtm_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.PROJECTS_TABLE)\
                .update(update_data)\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Updated GTM status to '{status}' for project {project_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating GTM status: {e}")
            return False
    
    async def save_gtm_version(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        gtm_pack: Dict[str, Any]
    ) -> bool:
        """
        Save a new GTM version to gtm_data.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User who triggered generation
            gtm_pack: Complete GTM strategy pack
        """
        try:
            # Get current data
            current_data = await self.get_gtm_data(project_id, tenant_id)
            
            # Add new version
            version_number = gtm_pack.get("version", current_data.get("current_version", 0) + 1)
            gtm_pack["version"] = version_number
            gtm_pack["created_at"] = datetime.utcnow().isoformat()
            gtm_pack["created_by"] = user_id
            
            versions = current_data.get("versions", [])
            versions.append(gtm_pack)
            
            # Update gtm_data
            new_data = {
                "current_version": version_number,
                "versions": versions
            }
            
            update_result = self.client.table(self.PROJECTS_TABLE)\
                .update({
                    "gtm_data": new_data,
                    "gtm_status": gtm_pack.get("status", "completed"),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", project_id)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            if update_result.data:
                logger.info(f"✅ Saved GTM version {version_number} for project {project_id}")
                return True
            
            logger.error(f"Failed to save GTM version - no data returned")
            return False
            
        except Exception as e:
            logger.error(f"Error saving GTM version: {e}")
            return False
    
    async def get_gtm_version(
        self,
        project_id: str,
        tenant_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific GTM version or the latest.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            version: Specific version number, or None for latest
            
        Returns:
            GTM pack dict or None
        """
        try:
            data = await self.get_gtm_data(project_id, tenant_id)
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
            logger.error(f"Error getting GTM version: {e}")
            return None
    
    async def list_gtm_versions(
        self,
        project_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all GTM versions for a project.
        
        Returns:
            List of version summaries
        """
        try:
            data = await self.get_gtm_data(project_id, tenant_id)
            versions = data.get("versions", [])
            
            summaries = []
            for v in versions:
                summaries.append({
                    "version": v.get("version"),
                    "summary": v.get("summary", "")[:200],
                    "step_count": len(v.get("steps", [])),
                    "status": v.get("status"),
                    "created_at": v.get("created_at"),
                    "created_by": v.get("created_by"),
                })
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error listing GTM versions: {e}")
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


# Singleton instance
_gtm_db_adapter: Optional[GTMDatabaseAdapter] = None


def get_gtm_database_adapter() -> GTMDatabaseAdapter:
    """Get or create singleton GTMDatabaseAdapter instance."""
    global _gtm_db_adapter
    if _gtm_db_adapter is None:
        _gtm_db_adapter = GTMDatabaseAdapter()
    return _gtm_db_adapter
