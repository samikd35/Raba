"""
Workflow Status Service

Centralized service for managing project workflow status tracking.
Used by sidebar to determine which features are unlocked.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStage(str, Enum):
    """Workflow stages in order of progression."""
    # Early stages (before questionnaires)
    PROJECT_CREATED = "project_created"
    PERSONA_CREATED = "persona_created"
    CUSTOMER_PROFILE_V1 = "customer_profile_v1_completed"  # VPC v1 customer profile
    HYPOTHESIS = "hypothesis_completed"
    ASSUMPTIONS = "assumptions_completed"
    QUESTIONNAIRES = "questionnaires_completed"
    
    # Market research and VPC v2
    MARKET_RESEARCH = "market_research_completed"
    CUSTOMER_PROFILE_V2 = "customer_profile_v2_completed"
    VALUE_MAP = "value_map_completed"
    
    # MVP Development (Module 3)
    VPS_V1 = "vps_v1_completed"
    BMC_V1 = "bmc_v1_completed"
    SOLUTION_CRITIQUE = "solution_critique_completed"
    VPS_V2 = "vps_v2_completed"
    BMC_V2 = "bmc_v2_completed"
    MVP_REQUIREMENTS = "mvp_requirements_completed"


# Stage level mapping for sidebar unlock logic
# Lower numbers = earlier stages
STAGE_LEVELS = {
    # Early stages
    WorkflowStage.PROJECT_CREATED: 1,
    WorkflowStage.PERSONA_CREATED: 2,
    WorkflowStage.CUSTOMER_PROFILE_V1: 3,
    WorkflowStage.HYPOTHESIS: 4,
    WorkflowStage.ASSUMPTIONS: 5,
    WorkflowStage.QUESTIONNAIRES: 6,
    
    # Market research and VPC v2
    WorkflowStage.MARKET_RESEARCH: 7,
    WorkflowStage.CUSTOMER_PROFILE_V2: 8,
    WorkflowStage.VALUE_MAP: 9,
    
    # MVP Development
    WorkflowStage.VPS_V1: 10,
    WorkflowStage.BMC_V1: 11,
    WorkflowStage.SOLUTION_CRITIQUE: 12,
    WorkflowStage.VPS_V2: 13,
    WorkflowStage.BMC_V2: 14,
    WorkflowStage.MVP_REQUIREMENTS: 15,
}


class WorkflowStatusService:
    """
    Service for managing workflow status in vmp_projects.workflow_status column.
    
    This provides a unified way to:
    - Set completion flags for each workflow stage
    - Query which stages are completed
    - Calculate max_completed_level for sidebar unlock
    """
    
    def __init__(self):
        """Initialize workflow status service."""
        from src.mint.api.system.core.supabase_client import get_service_role_client
        self.supabase = get_service_role_client()
        logger.info("WorkflowStatusService initialized")
    
    def set_stage_completed(
        self,
        project_id: str,
        tenant_id: str,
        stage: WorkflowStage,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Mark a workflow stage as completed.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            stage: The workflow stage that was completed
            additional_metadata: Optional extra data to store
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"📊 Setting workflow status: {stage.value} for project {project_id}")
            
            # Get current workflow_status
            response = self.supabase.client.table('vmp_projects').select(
                'workflow_status'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                logger.warning(f"Project {project_id} not found")
                return False
            
            current_status = response.data[0].get('workflow_status') or {}
            
            # Build update
            now = datetime.utcnow().isoformat()
            stage_key = stage.value
            timestamp_key = f"{stage_key}_at"
            
            current_status[stage_key] = True
            current_status[timestamp_key] = now
            current_status['last_updated'] = now
            
            # Add additional metadata if provided
            if additional_metadata:
                metadata_key = f"{stage_key}_metadata"
                current_status[metadata_key] = additional_metadata
            
            # Recalculate max_completed_level
            current_status['max_completed_level'] = self._calculate_max_level(current_status)
            
            # Save to database
            update_response = self.supabase.client.table('vmp_projects').update({
                'workflow_status': current_status,
                'updated_at': now
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(update_response.data) > 0
            if success:
                logger.info(f"✅ Workflow status updated: {stage.value} = True, level = {current_status['max_completed_level']}")
                
                # 🔄 CACHE INVALIDATION: Invalidate sidebar status cache for this tenant
                try:
                    from src.mint.api.cache.invalidation_service import get_invalidation_service, WriteOperation
                    invalidation_service = get_invalidation_service()
                    invalidation_service.invalidate_on_write(
                        operation=WriteOperation.UPDATE,
                        table_name="vmp_projects",
                        tenant_id=tenant_id,
                        cache_prefixes=["vmp_sidebar_status"]
                    )
                    logger.info(f"🔄 Sidebar status cache invalidated for tenant {tenant_id}")
                except Exception as cache_error:
                    logger.warning(f"⚠️ Cache invalidation failed (non-blocking): {cache_error}")
            else:
                logger.error(f"❌ Failed to update workflow status for project {project_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error setting workflow status: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_workflow_status(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current workflow status for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Workflow status dict or None
        """
        try:
            response = self.supabase.client.table('vmp_projects').select(
                'workflow_status'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if response.data:
                return response.data[0].get('workflow_status') or {}
            return None
            
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            return None
    
    def get_sidebar_unlock_status(
        self,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated sidebar unlock status for a user's projects.
        
        Returns unlock flags based on the user's MAXIMUM progress across all projects.
        If ANY project has completed a stage, that sidebar item is unlocked.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            Dict with unlock flags for each sidebar item
        """
        try:
            logger.info(f"📊 Getting sidebar unlock status for tenant {tenant_id}")
            
            # Query to get project data - include fallback fields for when workflow_status column doesn't exist
            # This makes the service work even before migration is run
            response = self.supabase.client.table('vmp_projects').select(
                'id, personas, vpc_data, field_prep_data, analysis_data, vpc_v2_data, mvp_data, soln_critique_data, workflow_status'
            ).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                logger.info("No projects found, returning default unlock status")
                return self._get_default_unlock_status()
            
            # Aggregate: if ANY project has a stage completed, unlock it
            unlock_status = {
                'has_projects': True,
                # Early stages
                'project_created': True,  # If has projects, this is true
                'persona_created': False,
                'customer_profile_v1_completed': False,
                'hypothesis_completed': False,
                'assumptions_completed': False,
                'questionnaires_completed': False,
                # Market research and VPC v2
                'market_research_completed': False,
                'customer_profile_v2_completed': False,
                'value_map_completed': False,
                # MVP Development
                'vps_v1_completed': False,
                'bmc_v1_completed': False,
                'solution_critique_completed': False,
                'vps_v2_completed': False,
                'bmc_v2_completed': False,
                'mvp_requirements_completed': False,
                'max_level': 1,  # Level 1 = has projects
            }
            
            for project in response.data:
                # Try workflow_status column first (if migration has been run)
                status = project.get('workflow_status') or {}
                
                if status:
                    # Use workflow_status column
                    for stage in WorkflowStage:
                        if status.get(stage.value) == True:
                            unlock_status[stage.value] = True
                    
                    project_level = status.get('max_completed_level', 0)
                    if isinstance(project_level, int) and project_level > unlock_status['max_level']:
                        unlock_status['max_level'] = project_level
                else:
                    # FALLBACK: Infer status from existing data (before migration)
                    self._infer_status_from_data(project, unlock_status)
            
            logger.info(f"✅ Sidebar unlock status: max_level={unlock_status['max_level']}")
            
            return unlock_status
            
        except Exception as e:
            logger.error(f"❌ Error getting sidebar unlock status: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_unlock_status()
    
    def _infer_status_from_data(self, project: Dict[str, Any], unlock_status: Dict[str, Any]) -> None:
        """
        Infer workflow status from existing project data (fallback when workflow_status column doesn't exist).
        Updates unlock_status in place.
        """
        # Persona
        personas = project.get('personas') or []
        if personas and len(personas) > 0:
            unlock_status['persona_created'] = True
        
        # Customer Profile v1 (VPC v1)
        vpc_data = project.get('vpc_data') or {}
        if vpc_data and (vpc_data.get('customer_profile') or vpc_data.get('jobs_to_be_done')):
            unlock_status['customer_profile_v1_completed'] = True
        
        # Field prep stages
        field_prep = project.get('field_prep_data') or {}
        if field_prep.get('hypotheses'):
            unlock_status['hypothesis_completed'] = True
        if field_prep.get('assumptions'):
            unlock_status['assumptions_completed'] = True
        if field_prep.get('stage') == 'questionnaires_completed':
            unlock_status['questionnaires_completed'] = True
        
        # Market Research
        analysis = project.get('analysis_data') or {}
        if analysis.get('stage') == 'analysis_completed':
            unlock_status['market_research_completed'] = True
        
        # VPC v2
        vpc_v2 = project.get('vpc_v2_data') or {}
        if vpc_v2 and isinstance(vpc_v2, dict):
            has_customer_profile = any(
                isinstance(v, dict) and v.get('customer_profile')
                for v in vpc_v2.values() if isinstance(v, dict)
            )
            if has_customer_profile:
                unlock_status['customer_profile_v2_completed'] = True
            
            has_value_map = any(
                isinstance(v, dict) and v.get('value_map_selections')
                for v in vpc_v2.values() if isinstance(v, dict)
            )
            if has_value_map:
                unlock_status['value_map_completed'] = True
        
        # MVP stages
        mvp = project.get('mvp_data') or {}
        if mvp.get('vps_v1'):
            unlock_status['vps_v1_completed'] = True
        if mvp.get('bmc') and mvp.get('bmc') != {}:
            unlock_status['bmc_v1_completed'] = True
        if mvp.get('vps_v2'):
            unlock_status['vps_v2_completed'] = True
        if mvp.get('bmc_v2') and mvp.get('bmc_v2') != {}:
            unlock_status['bmc_v2_completed'] = True
        
        # Solution Critique
        critique = project.get('soln_critique_data') or {}
        if critique.get('status') == 'completed':
            unlock_status['solution_critique_completed'] = True
        
        # MVP Requirements
        amrg = mvp.get('amrg', {})
        if amrg.get('runs'):
            runs = amrg.get('runs', {})
            has_completed = any(
                r.get('status') == 'completed' 
                for r in runs.values() if isinstance(r, dict)
            )
            if has_completed:
                unlock_status['mvp_requirements_completed'] = True
        
        # Update max_level based on inferred status
        unlock_status['max_level'] = max(unlock_status['max_level'], self._calculate_max_level(unlock_status))
    
    def _calculate_max_level(self, status: Dict[str, Any]) -> int:
        """Calculate the maximum completed level from status flags."""
        max_level = 0
        
        for stage, level in STAGE_LEVELS.items():
            if status.get(stage.value) == True:
                max_level = max(max_level, level)
        
        return max_level
    
    def _get_default_unlock_status(self) -> Dict[str, Any]:
        """Return default unlock status (all locked)."""
        return {
            'has_projects': False,
            # Early stages
            'project_created': False,
            'persona_created': False,
            'customer_profile_v1_completed': False,
            'hypothesis_completed': False,
            'assumptions_completed': False,
            'questionnaires_completed': False,
            # Market research and VPC v2
            'market_research_completed': False,
            'customer_profile_v2_completed': False,
            'value_map_completed': False,
            # MVP Development
            'vps_v1_completed': False,
            'bmc_v1_completed': False,
            'solution_critique_completed': False,
            'vps_v2_completed': False,
            'bmc_v2_completed': False,
            'mvp_requirements_completed': False,
            'max_level': 0,
        }
    
    def sync_workflow_status_from_data(
        self,
        project_id: str,
        tenant_id: str
    ) -> bool:
        """
        Sync workflow_status by inspecting actual project data.
        
        Useful for:
        - Retroactive updates
        - Fixing inconsistencies
        - Migration from old data
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"🔄 Syncing workflow status for project {project_id}")
            
            # Get full project data
            response = self.supabase.client.table('vmp_projects').select(
                'id, personas, vpc_data, field_prep_data, analysis_data, vpc_v2_data, mvp_data, soln_critique_data, workflow_status, created_at'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                logger.warning(f"Project {project_id} not found")
                return False
            
            project = response.data[0]
            current_status = project.get('workflow_status') or {}
            now = datetime.utcnow().isoformat()
            
            # Check each stage
            personas = project.get('personas') or []
            vpc_data = project.get('vpc_data') or {}
            field_prep = project.get('field_prep_data') or {}
            analysis = project.get('analysis_data') or {}
            vpc_v2 = project.get('vpc_v2_data') or {}
            mvp = project.get('mvp_data') or {}
            critique = project.get('soln_critique_data') or {}
            
            # === EARLY STAGES ===
            
            # 1. Project Created (always true if project exists)
            current_status['project_created'] = True
            current_status['project_created_at'] = project.get('created_at') or now
            
            # 2. Persona Created (check if personas array has items)
            if personas and len(personas) > 0:
                current_status['persona_created'] = True
                current_status['persona_created_at'] = now
            
            # 3. Customer Profile v1 (VPC v1 - check vpc_data has customer profile)
            if vpc_data and (vpc_data.get('customer_profile') or vpc_data.get('jobs_to_be_done')):
                current_status['customer_profile_v1_completed'] = True
                current_status['customer_profile_v1_completed_at'] = now
            
            # 4. Hypothesis (check field_prep_data.stage or hypotheses array)
            if field_prep.get('hypotheses') or field_prep.get('stage') in ['hypothesis_completed', 'assumptions_completed', 'questionnaires_completed']:
                current_status['hypothesis_completed'] = True
                current_status['hypothesis_completed_at'] = field_prep.get('hypotheses_generated_at') or now
            
            # 5. Assumptions (check field_prep_data.stage or assumptions array)
            if field_prep.get('assumptions') or field_prep.get('stage') in ['assumptions_completed', 'questionnaires_completed']:
                current_status['assumptions_completed'] = True
                current_status['assumptions_completed_at'] = field_prep.get('assumptions_generated_at') or now
            
            # 6. Questionnaires
            if field_prep.get('stage') == 'questionnaires_completed':
                current_status['questionnaires_completed'] = True
                current_status['questionnaires_completed_at'] = field_prep.get('questionnaires_generated_at') or now
            
            # 2. Market Research
            if analysis.get('stage') == 'analysis_completed':
                current_status['market_research_completed'] = True
                current_status['market_research_completed_at'] = analysis.get('completed_at') or now
            
            # 3. Customer Profile v2 (check if any persona has customer_profile)
            if vpc_v2 and isinstance(vpc_v2, dict):
                has_customer_profile = any(
                    isinstance(v, dict) and v.get('customer_profile')
                    for v in vpc_v2.values()
                )
                if has_customer_profile:
                    current_status['customer_profile_v2_completed'] = True
                    current_status['customer_profile_v2_completed_at'] = now
            
            # 4. Value Map (check if any persona has value_map_selections)
            if vpc_v2 and isinstance(vpc_v2, dict):
                has_value_map = any(
                    isinstance(v, dict) and v.get('value_map_selections')
                    for v in vpc_v2.values()
                )
                if has_value_map:
                    current_status['value_map_completed'] = True
                    current_status['value_map_completed_at'] = now
            
            # 5. VPS v1
            if mvp.get('vps_v1'):
                current_status['vps_v1_completed'] = True
                current_status['vps_v1_completed_at'] = mvp.get('current_version', {}).get('vps_updated_at') or now
            
            # 6. BMC v1
            if mvp.get('bmc') and mvp.get('bmc') != {}:
                current_status['bmc_v1_completed'] = True
                current_status['bmc_v1_completed_at'] = mvp.get('current_version', {}).get('bmc_updated_at') or now
            
            # 7. Solution Critique
            if critique.get('status') == 'completed':
                current_status['solution_critique_completed'] = True
                current_status['solution_critique_completed_at'] = critique.get('completed_at') or now
            
            # 8. VPS v2
            if mvp.get('vps_v2'):
                current_status['vps_v2_completed'] = True
                current_status['vps_v2_completed_at'] = mvp.get('current_version', {}).get('vps_updated_at') or now
            
            # 9. BMC v2
            if mvp.get('bmc_v2') and mvp.get('bmc_v2') != {}:
                current_status['bmc_v2_completed'] = True
                current_status['bmc_v2_completed_at'] = mvp.get('current_version', {}).get('bmc_updated_at') or now
            
            # 10. MVP Requirements
            amrg = mvp.get('amrg', {})
            runs = amrg.get('runs', {})
            if any(r.get('status') == 'completed' for r in runs.values() if isinstance(r, dict)):
                current_status['mvp_requirements_completed'] = True
                current_status['mvp_requirements_completed_at'] = now
            
            # Calculate max level
            current_status['max_completed_level'] = self._calculate_max_level(current_status)
            current_status['last_updated'] = now
            
            # Save
            update_response = self.supabase.client.table('vmp_projects').update({
                'workflow_status': current_status
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(update_response.data) > 0
            if success:
                logger.info(f"✅ Synced workflow status: level={current_status['max_completed_level']}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error syncing workflow status: {e}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance
_workflow_status_service: Optional[WorkflowStatusService] = None


def get_workflow_status_service() -> WorkflowStatusService:
    """Get singleton instance of WorkflowStatusService."""
    global _workflow_status_service
    if _workflow_status_service is None:
        _workflow_status_service = WorkflowStatusService()
    return _workflow_status_service
