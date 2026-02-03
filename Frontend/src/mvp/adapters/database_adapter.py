"""
MVP Database Adapter

Dedicated database adapter for MVP module operations.
Provides clean separation from VPM module and better maintainability.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
import logging

from src.mint.api.system.core.supabase_client import get_supabase_client, get_service_role_client
from src.vpm.services.workflow_status_service import get_workflow_status_service, WorkflowStage

logger = logging.getLogger(__name__)


class MVPDatabaseAdapter:
    """
    Database adapter for MVP Development Suite.
    
    Handles all database operations for VPS, BMC, Critique, and Refinement features.
    """
    
    def __init__(self, use_service_role: bool = False):
        """
        Initialize MVP database adapter.
        
        Args:
            use_service_role: If True, use service role client with elevated permissions
        """
        self.supabase = get_service_role_client() if use_service_role else get_supabase_client()
        self.use_service_role = use_service_role
        logger.info(f"MVP Database Adapter initialized (service_role={use_service_role})")
    
    # ==================== PROJECT DATA RETRIEVAL ====================
    
    def get_project(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete project data including VPC, personas, and field prep.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            
        Returns:
            Project data dictionary or None if not found
        """
        try:
            response = self.supabase.client.table('vmp_projects').select(
                'id, tenant_id, user_id, name, description, pv_report_id, '
                'status, current_step, vpc_data, vpc_v2_data, field_prep_data, personas, '
                'research_documents_data, analysis_data, mvp_data, '
                'soln_critique_data, '  # ✅ Added solution critique data
                'context_mode, context_status, enhanced_context, '  # ✅ Added bootstrap context fields
                'created_at, updated_at'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                logger.warning(f"Project {project_id} not found for tenant {tenant_id}")
                return None
            
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error fetching project {project_id}: {e}")
            traceback.print_exc()
            return None
    
    def get_mvp_data(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get MVP data for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            
        Returns:
            MVP data dictionary or empty dict if not found
        """
        try:
            response = self.supabase.client.table('vmp_projects').select(
                'mvp_data'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                logger.warning(f"No MVP data found for project {project_id}")
                return {}
            
            mvp_data = response.data[0].get('mvp_data', {})
            if mvp_data:
                logger.info(f"Retrieved MVP data for project {project_id}: {list(mvp_data.keys())}")
            else:
                logger.info(f"Retrieved MVP data for project {project_id}: []")
            return mvp_data if mvp_data else {}
            
        except Exception as e:
            logger.error(f"Error fetching MVP data for {project_id}: {e}")
            traceback.print_exc()
            return {}
    
    # ==================== VPS OPERATIONS ====================
    
    def save_vps_v1(
        self, 
        project_id: str, 
        tenant_id: str, 
        vps_data,  # Can be List[Dict] or Dict (backwards compatible)
        user_id: str
    ) -> bool:
        """
        Save VPS v1 data to project.
        
        Supports multi-persona:
        - vps_data can be a list of VPS (multi-persona)
        - vps_data can be a single dict (backwards compatible)
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            vps_data: VPS data to save (List[Dict] or Dict)
            user_id: User ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing mvp_data
            current_mvp_data = self.get_mvp_data(project_id, tenant_id)
            
            # Normalize to list format (for consistency)
            if isinstance(vps_data, list):
                vps_list = vps_data
                logger.info(f"Saving {len(vps_list)} VPS (multi-persona)")
            else:
                vps_list = [vps_data]
                logger.info(f"Saving 1 VPS (single item, backwards compatible)")
            
            # Add user info to metadata for each VPS
            for vps in vps_list:
                if 'generation_metadata' in vps:
                    vps['generation_metadata']['generated_by'] = user_id
            
            # Update with new VPS v1 (always store as array)
            current_mvp_data['vps_v1'] = vps_list
            
            # Update version tracking
            if 'current_version' not in current_mvp_data or not isinstance(current_mvp_data.get('current_version'), dict):
                current_mvp_data['current_version'] = {}
            current_mvp_data['current_version']['vps'] = 'v1'
            current_mvp_data['current_version']['vps_updated_at'] = datetime.utcnow().isoformat()
            current_mvp_data['current_version']['vps_count'] = len(vps_list)
            
            # Save back to database
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': current_mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            response_data = getattr(response, "data", None)
            success = isinstance(response_data, list) and len(response_data) > 0
            if not success:
                try:
                    verify_mvp_data = self.get_mvp_data(project_id, tenant_id)
                    verified_vps = verify_mvp_data.get("vps_v1")
                    if verified_vps == vps_list:
                        success = True
                        logger.info(
                            f"✅ Successfully saved {len(vps_list)} VPS v1 for project {project_id} (verified by re-read)"
                        )
                    else:
                        logger.error(
                            f"❌ Failed to save VPS v1 for project {project_id} (service_role={self.use_service_role}). "
                            f"Update returned 0 rows; verification did not match."
                        )
                except Exception as verify_error:
                    logger.error(
                        f"❌ Failed to verify VPS v1 save for project {project_id} (service_role={self.use_service_role}): {verify_error}"
                    )
                    traceback.print_exc()
            
            if success:
                logger.info(f"✅ Successfully saved {len(vps_list)} VPS v1 for project {project_id}")
                
                # � WORKFLOW STATUS: Mark VPS v1 as completed
                try:
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.VPS_V1,
                        additional_metadata={"vps_count": len(vps_list)}
                    )
                except Exception as status_error:
                    logger.warning(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
                
                # �🔄 BACKGROUND CHUNKING: Chunk VPS v1 for "Chat with Project" feature
                try:
                    import asyncio
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    asyncio.create_task(
                        chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.VPS_V1,
                            feature_data={"vps": vps_list}
                        )
                    )
                    logger.info(f"🚀 Background chunking spawned for VPS v1")
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Background chunking failed (non-blocking): {chunk_error}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving VPS v1 for {project_id}: {e}")
            traceback.print_exc()
            return False
    
    def get_vps_v1(self, project_id: str, tenant_id: str):
        """
        Get VPS v1 data for a project.
        
        Returns array format for multi-persona support.
        Handles backwards compatibility (converts single dict to array).
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            
        Returns:
            List of VPS v1 data, or None if not found
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            vps_v1 = mvp_data.get('vps_v1')
            
            if vps_v1:
                # Ensure array format (backwards compatibility)
                if isinstance(vps_v1, list):
                    logger.info(f"Retrieved {len(vps_v1)} VPS v1 for project {project_id}")
                    return vps_v1
                else:
                    # Old format: single dict, convert to array
                    logger.info(f"Retrieved 1 VPS v1 (converted from legacy format) for project {project_id}")
                    return [vps_v1]
            else:
                logger.info(f"No VPS v1 found for project {project_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching VPS v1 for {project_id}: {e}")
            return None
    
    def update_vps_v1(
        self,
        project_id: str,
        tenant_id: str,
        updates: Dict[str, Any],
        user_id: str
    ) -> bool:
        """
        Update specific fields in VPS v1.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            updates: Dictionary of fields to update
            user_id: User ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            
            if 'vps_v1' not in mvp_data:
                logger.error(f"No VPS v1 found to update for project {project_id}")
                return False
            
            # Update specified fields
            for key, value in updates.items():
                mvp_data['vps_v1'][key] = value
            
            # Update metadata
            if 'generation_metadata' not in mvp_data['vps_v1']:
                mvp_data['vps_v1']['generation_metadata'] = {}
            
            mvp_data['vps_v1']['generation_metadata']['last_updated_at'] = datetime.utcnow().isoformat()
            mvp_data['vps_v1']['generation_metadata']['last_updated_by'] = user_id
            
            # Save back
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Successfully updated VPS v1 for project {project_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating VPS v1 for {project_id}: {e}")
            traceback.print_exc()
            return False
    
    # ==================== VPS V2 OPERATIONS ====================
    
    def save_vps_v2(
        self,
        project_id: str,
        tenant_id: str,
        vps_data,  # Can be List[Dict] or Dict (backwards compatible)
        user_id: str
    ) -> bool:
        """
        Save VPS v2 (refined) data to project.
        
        Supports multi-persona (same as v1).
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            vps_data: VPS v2 data to save (List[Dict] or Dict)
            user_id: User ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_mvp_data = self.get_mvp_data(project_id, tenant_id)
            
            # Normalize to list format
            if isinstance(vps_data, list):
                vps_list = vps_data
                logger.info(f"Saving {len(vps_list)} VPS v2 (multi-persona)")
            else:
                vps_list = [vps_data]
                logger.info(f"Saving 1 VPS v2 (single item)")
            
            # Add user info to each VPS
            for vps in vps_list:
                if 'generation_metadata' in vps:
                    vps['generation_metadata']['generated_by'] = user_id
            
            # Always store as array
            current_mvp_data['vps_v2'] = vps_list
            
            # Update version tracking
            if 'current_version' not in current_mvp_data or not isinstance(current_mvp_data.get('current_version'), dict):
                current_mvp_data['current_version'] = {}
            current_mvp_data['current_version']['vps'] = 'v2'
            current_mvp_data['current_version']['vps_updated_at'] = datetime.utcnow().isoformat()
            current_mvp_data['current_version']['vps_count'] = len(vps_list)
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': current_mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Successfully saved {len(vps_list)} VPS v2 for project {project_id}")
                
                # 📊 WORKFLOW STATUS: Mark VPS v2 as completed
                try:
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.VPS_V2,
                        additional_metadata={"vps_count": len(vps_list)}
                    )
                except Exception as status_error:
                    logger.warning(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk VPS v2 for "Chat with Project" feature
                try:
                    import asyncio
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    asyncio.create_task(
                        chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.VPS_V2,
                            feature_data={"vps": vps_list}
                        )
                    )
                    logger.info(f"🚀 Background chunking spawned for VPS v2")
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Background chunking failed (non-blocking): {chunk_error}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving VPS v2 for {project_id}: {e}")
            traceback.print_exc()
            return False
    
    def get_vps_v2(self, project_id: str, tenant_id: str):
        """
        Get VPS v2 data for a project.
        
        Returns array format for multi-persona support.
        
        Returns:
            List of VPS v2 data, or None if not found
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            vps_v2 = mvp_data.get('vps_v2')
            
            if vps_v2:
                # Ensure array format (backwards compatibility)
                if isinstance(vps_v2, list):
                    logger.info(f"Retrieved {len(vps_v2)} VPS v2 for project {project_id}")
                    return vps_v2
                else:
                    logger.info(f"Retrieved 1 VPS v2 (converted from legacy format)")
                    return [vps_v2]
            return None
        except Exception as e:
            logger.error(f"Error fetching VPS v2 for {project_id}: {e}")
            return None
    
    # ==================== GENERIC MVP COMPONENT OPERATIONS ====================
    
    def update_mvp_component(
        self,
        project_id: str,
        tenant_id: str,
        component_path: str,
        component_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update a specific component in MVP data.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            component_path: Path to component (e.g., 'vps_v1', 'bmc_v1', 'critique')
            component_data: Component data to save
            user_id: Optional user ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_mvp_data = self.get_mvp_data(project_id, tenant_id)
            current_mvp_data[component_path] = component_data
            
            # Update version tracking if applicable
            if component_path.startswith('vps_') or component_path.startswith('bmc_'):
                if 'current_version' not in current_mvp_data or not isinstance(current_mvp_data.get('current_version'), dict):
                    current_mvp_data['current_version'] = {}
                
                component_type = component_path.split('_')[0]  # 'vps' or 'bmc'
                version = component_path.split('_')[1] if '_' in component_path else 'v1'
                current_mvp_data['current_version'][component_type] = version
                current_mvp_data['current_version'][f'{component_type}_updated_at'] = datetime.utcnow().isoformat()
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': current_mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Successfully updated MVP component '{component_path}' for project {project_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating MVP component '{component_path}' for {project_id}: {e}")
            traceback.print_exc()
            return False
    
    def get_mvp_component(
        self,
        project_id: str,
        tenant_id: str,
        component_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific component from MVP data.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            component_path: Path to component (e.g., 'vps_v1', 'bmc_v1')
            
        Returns:
            Component data or None if not found
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            return mvp_data.get(component_path)
        except Exception as e:
            logger.error(f"Error fetching MVP component '{component_path}' for {project_id}: {e}")
            return None
    
    # ==================== VERSION TRACKING ====================
    
    def get_current_versions(self, project_id: str, tenant_id: str) -> Dict[str, str]:
        """
        Get current versions of all MVP components.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            
        Returns:
            Dictionary with current versions (e.g., {'vps': 'v1', 'bmc': 'v2'})
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            return mvp_data.get('current_version', {})
        except Exception as e:
            logger.error(f"Error fetching current versions for {project_id}: {e}")
            return {}
    
    # ==================== VALIDATION HELPERS ====================
    
    def validate_project_access(self, project_id: str, tenant_id: str, user_id: str) -> bool:
        """
        Validate that user has access to project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            project = self.get_project(project_id, tenant_id)
            if not project:
                return False
            
            # Project exists and tenant matches (tenant isolation ensures access)
            return True
            
        except Exception as e:
            logger.error(f"Error validating project access: {e}")
            return False
    
    # ==================== BMC OPERATIONS ====================
    
    def get_bmc(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get BMC for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            
        Returns:
            BMC data dictionary or None if not found
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            bmc = mvp_data.get('bmc')
            
            if bmc:
                logger.info(f"Retrieved BMC for project {project_id}")
            else:
                logger.info(f"No BMC found for project {project_id}")
            
            return bmc
            
        except Exception as e:
            logger.error(f"Error retrieving BMC for project {project_id}: {e}")
            traceback.print_exc()
            return None
    
    def save_bmc(
        self,
        project_id: str,
        tenant_id: str,
        bmc_data: Dict[str, Any],
        user_id: str
    ) -> bool:
        """
        Save complete BMC to database.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            bmc_data: Complete BMC data with all 9 blocks
            user_id: User ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Saving BMC for project {project_id}")
            
            # Get existing MVP data
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            
            # Update BMC
            mvp_data['bmc'] = bmc_data
            
            # Save to database
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if response.data:
                logger.info(f"✅ Successfully saved BMC for project {project_id}")
                
                # � WORKFLOW STATUS: Mark BMC v1 as completed
                try:
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.BMC_V1
                    )
                except Exception as status_error:
                    logger.warning(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
                
                # � BACKGROUND CHUNKING: Chunk BMC v1 for "Chat with Project" feature
                try:
                    import asyncio
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    asyncio.create_task(
                        chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.BMC_V1,
                            feature_data={"bmc": bmc_data}
                        )
                    )
                    logger.info(f"🚀 Background chunking spawned for BMC v1")
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Background chunking failed (non-blocking): {chunk_error}")
                
                return True
            else:
                logger.error(f"❌ Failed to save BMC for project {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving BMC for project {project_id}: {e}")
            traceback.print_exc()
            return False
    
    def update_bmc_block(
        self,
        project_id: str,
        tenant_id: str,
        block_name: str,
        block_data: Dict[str, Any],
        user_id: str
    ) -> bool:
        """
        Update a specific BMC block.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            block_name: Name of block to update
            block_data: Updated block data
            user_id: User ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Updating BMC block '{block_name}' for project {project_id}")
            
            # Get existing MVP data
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            
            if 'bmc' not in mvp_data:
                logger.error(f"No BMC found for project {project_id}")
                return False
            
            # Update specific block
            mvp_data['bmc'][block_name] = block_data
            
            # Save to database
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if response.data:
                logger.info(f"✅ Successfully updated BMC block '{block_name}' for project {project_id}")
                return True
            else:
                logger.error(f"❌ Failed to update BMC block '{block_name}' for project {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating BMC block '{block_name}' for project {project_id}: {e}")
            traceback.print_exc()
            return False
    
    def save_bmc_progress(
        self,
        project_id: str,
        tenant_id: str,
        partial_bmc: Dict[str, Any]
    ) -> bool:
        """Save partial BMC during generation."""
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            mvp_data['bmc'] = partial_bmc
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if response.data:
                logger.info(f"✅ Successfully saved BMC progress for project {project_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error saving BMC progress for project {project_id}: {e}")
            return False
    
    def get_bmc_v2(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get BMC v2 for a project."""
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            if mvp_data:
                return mvp_data.get('bmc_v2')
            return None
        except Exception as e:
            logger.error(f"Error retrieving BMC v2: {e}")
            return None
    
    def save_bmc_v2(
        self,
        project_id: str,
        tenant_id: str,
        bmc_data: Dict[str, Any],
        user_id: str
    ) -> bool:
        """Save BMC v2 for a project."""
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            if mvp_data is None:
                mvp_data = {}
            
            bmc_data['last_modified_at'] = datetime.utcnow().isoformat()
            bmc_data['last_modified_by'] = user_id
            
            mvp_data['bmc_v2'] = bmc_data
            
            # Update version tracking (as dict, not string)
            if 'current_version' not in mvp_data or not isinstance(mvp_data.get('current_version'), dict):
                mvp_data['current_version'] = {}
            mvp_data['current_version']['bmc'] = 'v2'
            mvp_data['current_version']['bmc_updated_at'] = datetime.utcnow().isoformat()
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if response.data:
                logger.info(f"✅ Successfully saved BMC v2 for project {project_id}")
                
                # 📊 WORKFLOW STATUS: Mark BMC v2 as completed
                try:
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.BMC_V2
                    )
                except Exception as status_error:
                    logger.warning(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk BMC v2 for "Chat with Project" feature
                try:
                    import asyncio
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    asyncio.create_task(
                        chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.BMC_V2,
                            feature_data={"bmc": bmc_data}
                        )
                    )
                    logger.info(f"🚀 Background chunking spawned for BMC v2")
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Background chunking failed (non-blocking): {chunk_error}")
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving BMC v2: {e}")
            return False


# Singleton instances
_mvp_database_adapter_instances: Dict[bool, MVPDatabaseAdapter] = {}


def get_mvp_database_adapter(use_service_role: bool = False) -> MVPDatabaseAdapter:
    """
    Get singleton instance of MVP database adapter.
    
    Args:
        use_service_role: If True, use service role client
        
    Returns:
        MVPDatabaseAdapter instance
    """
    global _mvp_database_adapter_instances
    if use_service_role not in _mvp_database_adapter_instances:
        _mvp_database_adapter_instances[use_service_role] = MVPDatabaseAdapter(use_service_role=use_service_role)
    return _mvp_database_adapter_instances[use_service_role]
