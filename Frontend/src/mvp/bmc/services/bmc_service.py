"""
BMC Service

Orchestrates the sequential generation of all 9 Business Model Canvas blocks.
Handles context loading, agent coordination, error recovery, and progressive saving.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
import logging

from src.mvp.bmc.agents.bmc_agent import BMCGenerationAgent
from src.mvp.bmc.agents.bmc_v2_agent import BMCRefinementAgent
from src.mvp.bmc.utils.bmc_context_loader import BMCContextLoader
from src.mvp.adapters.database_adapter import get_mvp_database_adapter
from src.vpm.adapters.database_adapter import get_yuba_database_adapter
from src.vpm.adapters.vector_adapter import get_yuba_vector_adapter

logger = logging.getLogger(__name__)


class BMCService:
    """
    Service for Business Model Canvas generation orchestration.
    
    Coordinates sequential generation of all 9 BMC blocks with progressive saving.
    """
    
    def __init__(self):
        """Initialize BMC service with required adapters and agents."""
        self.mvp_adapter = get_mvp_database_adapter(use_service_role=True)
        self.vpm_adapter = get_yuba_database_adapter()
        self.vector_adapter = get_yuba_vector_adapter()
        self.bmc_agent = BMCGenerationAgent()
        self.bmc_v2_agent = BMCRefinementAgent()
        self.context_loader = BMCContextLoader(
            self.vpm_adapter,
            self.vector_adapter,
            self.mvp_adapter
        )
        
        logger.info("BMC Service initialized with v1 and v2 agents")
    
    async def generate_bmc(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate complete Business Model Canvas in single API request.
        
        All 9 blocks are generated sequentially in the background, with each block
        building upon previously generated blocks for consistency and cross-referencing.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            creativity_level: Temperature for AI generation (0.0-1.0)
            
        Returns:
            Complete BMC with all 9 blocks and generation metadata
            
        Raises:
            ValueError: If prerequisites not met or generation fails
        """
        total_start_time = time.time()
        logger.info(f"🚀 Starting BMC generation for project {project_id}")
        
        try:
            # Step 1: Validate project access
            logger.info("Step 1: Validating project access...")
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Step 2: Load context (validates VPS v1 exists)
            logger.info("Step 2: Loading context...")
            context = await self.context_loader.load_bmc_context(project_id, tenant_id)
            logger.info(f"✅ Context loaded with {context.get('context_completeness', 0):.2%} completeness")
            
            # Step 3: Initialize BMC data structure
            bmc_data = {}
            block_times = {}
            
            # Step 4: Generate Block 1 - Customer Segments
            logger.info("=" * 60)
            logger.info("Step 4: Generating Block 1 - Customer Segments")
            logger.info("=" * 60)
            block_start = time.time()
            customer_segments = await self.bmc_agent.generate_customer_segments(context)
            block_times['customer_segments'] = time.time() - block_start
            bmc_data['customer_segments'] = customer_segments
            
            # Save progress after Block 1
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 1 complete")
            
            # Step 5: Generate Block 2 - Value Propositions
            logger.info("=" * 60)
            logger.info("Step 5: Generating Block 2 - Value Propositions")
            logger.info("=" * 60)
            block_start = time.time()
            value_propositions = await self.bmc_agent.generate_value_propositions(
                context,
                customer_segments
            )
            block_times['value_propositions'] = time.time() - block_start
            bmc_data['value_propositions'] = value_propositions
            
            # Save progress after Block 2
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 2 complete")
            
            # Step 6: Generate Block 3 - Channels
            logger.info("=" * 60)
            logger.info("Step 6: Generating Block 3 - Channels")
            logger.info("=" * 60)
            block_start = time.time()
            channels = await self.bmc_agent.generate_channels(
                context,
                customer_segments,
                value_propositions
            )
            block_times['channels'] = time.time() - block_start
            bmc_data['channels'] = channels
            
            # Save progress after Block 3
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 3 complete")
            
            # Step 7: Generate Block 4 - Customer Relationships
            logger.info("=" * 60)
            logger.info("Step 7: Generating Block 4 - Customer Relationships")
            logger.info("=" * 60)
            block_start = time.time()
            previous_blocks = {
                'customer_segments': customer_segments,
                'value_propositions': value_propositions,
                'channels': channels
            }
            customer_relationships = await self.bmc_agent.generate_customer_relationships(
                context,
                previous_blocks
            )
            block_times['customer_relationships'] = time.time() - block_start
            bmc_data['customer_relationships'] = customer_relationships
            
            # Save progress after Block 4
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 4 complete")
            
            # Step 8: Generate Block 5 - Revenue Streams
            logger.info("=" * 60)
            logger.info("Step 8: Generating Block 5 - Revenue Streams")
            logger.info("=" * 60)
            block_start = time.time()
            previous_blocks['customer_relationships'] = customer_relationships
            revenue_streams = await self.bmc_agent.generate_revenue_streams(
                context,
                previous_blocks
            )
            block_times['revenue_streams'] = time.time() - block_start
            bmc_data['revenue_streams'] = revenue_streams
            
            # Save progress after Block 5
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 5 complete")
            
            # Step 9: Generate Block 6 - Key Resources
            logger.info("=" * 60)
            logger.info("Step 9: Generating Block 6 - Key Resources")
            logger.info("=" * 60)
            block_start = time.time()
            previous_blocks['revenue_streams'] = revenue_streams
            key_resources = await self.bmc_agent.generate_key_resources(
                context,
                previous_blocks
            )
            block_times['key_resources'] = time.time() - block_start
            bmc_data['key_resources'] = key_resources
            
            # Save progress after Block 6
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 6 complete")
            
            # Step 10: Generate Block 7 - Key Activities
            logger.info("=" * 60)
            logger.info("Step 10: Generating Block 7 - Key Activities")
            logger.info("=" * 60)
            block_start = time.time()
            previous_blocks['key_resources'] = key_resources
            key_activities = await self.bmc_agent.generate_key_activities(
                context,
                previous_blocks
            )
            block_times['key_activities'] = time.time() - block_start
            bmc_data['key_activities'] = key_activities
            
            # Save progress after Block 7
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 7 complete")
            
            # Step 11: Generate Block 8 - Key Partnerships
            logger.info("=" * 60)
            logger.info("Step 11: Generating Block 8 - Key Partnerships")
            logger.info("=" * 60)
            block_start = time.time()
            previous_blocks['key_activities'] = key_activities
            key_partnerships = await self.bmc_agent.generate_key_partnerships(
                context,
                previous_blocks
            )
            block_times['key_partnerships'] = time.time() - block_start
            bmc_data['key_partnerships'] = key_partnerships
            
            # Save progress after Block 8
            await self._save_progress(project_id, tenant_id, bmc_data, "Block 8 complete")
            
            # Step 12: Generate Block 9 - Cost Structure (Final Block)
            logger.info("=" * 60)
            logger.info("Step 12: Generating Block 9 - Cost Structure (FINAL)")
            logger.info("=" * 60)
            block_start = time.time()
            previous_blocks['key_partnerships'] = key_partnerships
            cost_structure = await self.bmc_agent.generate_cost_structure(
                context,
                previous_blocks
            )
            block_times['cost_structure'] = time.time() - block_start
            bmc_data['cost_structure'] = cost_structure
            
            # Step 13: Add overall generation metadata
            total_time = time.time() - total_start_time
            bmc_data['generation_metadata'] = {
                'generated_at': datetime.utcnow().isoformat(),
                'model_used': 'gpt-4',
                'total_generation_time': total_time,
                'context_completeness': context.get('context_completeness', 0.0),
                'version': 'v1',
                'block_generation_times': block_times,
                'blocks_generated': 9,
                'user_id': user_id
            }
            
            # Step 14: Final save with complete BMC
            logger.info("=" * 60)
            logger.info("Step 13: Saving complete BMC...")
            logger.info("=" * 60)
            success = self.mvp_adapter.save_bmc(project_id, tenant_id, bmc_data, user_id)
            
            if not success:
                raise ValueError("Failed to save complete BMC to database")
            
            # Step 15: Log success summary
            logger.info("=" * 60)
            logger.info("🎉 BMC GENERATION COMPLETE!")
            logger.info("=" * 60)
            logger.info(f"Project: {project_id}")
            logger.info(f"Total Time: {total_time:.2f}s")
            logger.info(f"Blocks Generated: 9/9")
            logger.info(f"Block Times:")
            for block_name, block_time in block_times.items():
                logger.info(f"  - {block_name}: {block_time:.2f}s")
            logger.info("=" * 60)
            
            return {
                "bmc": bmc_data,
                "project_id": project_id,
                "message": "BMC generated successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating BMC for project {project_id}: {e}")
            logger.exception(e)
            raise ValueError(f"BMC generation failed: {str(e)}")
    
    async def get_bmc(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing BMC for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for access validation
            
        Returns:
            BMC data if exists, None otherwise
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Get BMC
            bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            
            if bmc:
                logger.info(f"Retrieved BMC for project {project_id}")
                return {
                    "bmc": bmc,
                    "project_id": project_id
                }
            else:
                logger.info(f"No BMC found for project {project_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving BMC for project {project_id}: {e}")
            raise
    
    async def update_bmc_block(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        block_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a specific BMC block (manual user edits).
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of block to update
            block_data: Updated block data
            
        Returns:
            Updated BMC
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Validate block name
            valid_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            if block_name not in valid_blocks:
                raise ValueError(f"Invalid block name: {block_name}")
            
            # Update block
            success = self.mvp_adapter.update_bmc_block(
                project_id,
                tenant_id,
                block_name,
                block_data,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to update block {block_name}")
            
            # Get updated BMC
            bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            
            logger.info(f"Updated BMC block '{block_name}' for project {project_id}")
            
            return {
                "bmc": bmc,
                "project_id": project_id,
                "updated_block": block_name,
                "message": f"Block {block_name} updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating BMC block '{block_name}' for project {project_id}: {e}")
            raise
    
    async def update_bmc_v2_block(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        block_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a specific BMC v2 block (manual user edits).
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of block to update
            block_data: Updated block data
            
        Returns:
            Updated BMC v2
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Validate block name
            valid_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            if block_name not in valid_blocks:
                raise ValueError(f"Invalid block name: {block_name}")
            
            # Get existing BMC v2
            existing_bmc_v2 = self.mvp_adapter.get_bmc_v2(project_id, tenant_id)
            if not existing_bmc_v2:
                raise ValueError("No existing BMC v2 found. Generate BMC v2 first.")
            
            # Mark block as changed by user
            block_data['changed'] = True
            block_data['change_reason'] = f"User manual edit"
            block_data['edited_by'] = user_id
            block_data['edited_at'] = datetime.utcnow().isoformat()
            
            # Update the block in BMC v2
            existing_bmc_v2[block_name] = block_data
            
            # Save updated BMC v2
            success = self.mvp_adapter.save_bmc_v2(
                project_id,
                tenant_id,
                existing_bmc_v2,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to update BMC v2 block {block_name}")
            
            # Get updated BMC v2
            bmc_v2 = self.mvp_adapter.get_bmc_v2(project_id, tenant_id)
            
            logger.info(f"Updated BMC v2 block '{block_name}' for project {project_id}")
            
            return {
                "bmc": bmc_v2,
                "project_id": project_id,
                "updated_block": block_name,
                "message": f"BMC v2 block {block_name} updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating BMC v2 block '{block_name}' for project {project_id}: {e}")
            raise
    
    async def regenerate_bmc_block(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Regenerate a specific BMC block using AI.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of block to regenerate
            creativity_level: Temperature for AI generation
            
        Returns:
            Updated BMC with regenerated block
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Load context
            context = await self.context_loader.load_bmc_context(project_id, tenant_id)
            
            # Get existing BMC for previous blocks
            existing_bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            if not existing_bmc:
                raise ValueError("No existing BMC found. Generate complete BMC first.")
            
            # Regenerate specific block
            logger.info(f"Regenerating block '{block_name}' for project {project_id}")
            
            if block_name == 'customer_segments':
                new_block = await self.bmc_agent.generate_customer_segments(context)
            elif block_name == 'value_propositions':
                new_block = await self.bmc_agent.generate_value_propositions(
                    context,
                    existing_bmc['customer_segments']
                )
            elif block_name == 'channels':
                new_block = await self.bmc_agent.generate_channels(
                    context,
                    existing_bmc['customer_segments'],
                    existing_bmc['value_propositions']
                )
            elif block_name == 'customer_relationships':
                previous_blocks = {
                    'customer_segments': existing_bmc['customer_segments'],
                    'value_propositions': existing_bmc['value_propositions'],
                    'channels': existing_bmc['channels']
                }
                new_block = await self.bmc_agent.generate_customer_relationships(context, previous_blocks)
            elif block_name == 'revenue_streams':
                previous_blocks = {
                    'customer_segments': existing_bmc['customer_segments'],
                    'value_propositions': existing_bmc['value_propositions'],
                    'channels': existing_bmc['channels'],
                    'customer_relationships': existing_bmc['customer_relationships']
                }
                new_block = await self.bmc_agent.generate_revenue_streams(context, previous_blocks)
            elif block_name == 'key_resources':
                previous_blocks = {k: v for k, v in existing_bmc.items() if k != 'generation_metadata'}
                new_block = await self.bmc_agent.generate_key_resources(context, previous_blocks)
            elif block_name == 'key_activities':
                previous_blocks = {k: v for k, v in existing_bmc.items() if k != 'generation_metadata'}
                new_block = await self.bmc_agent.generate_key_activities(context, previous_blocks)
            elif block_name == 'key_partnerships':
                previous_blocks = {k: v for k, v in existing_bmc.items() if k != 'generation_metadata'}
                new_block = await self.bmc_agent.generate_key_partnerships(context, previous_blocks)
            elif block_name == 'cost_structure':
                previous_blocks = {k: v for k, v in existing_bmc.items() if k != 'generation_metadata'}
                new_block = await self.bmc_agent.generate_cost_structure(context, previous_blocks)
            else:
                raise ValueError(f"Invalid block name: {block_name}")
            
            # Update block
            success = self.mvp_adapter.update_bmc_block(
                project_id,
                tenant_id,
                block_name,
                new_block,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to save regenerated block {block_name}")
            
            # Get updated BMC
            bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            
            logger.info(f"Regenerated BMC block '{block_name}' for project {project_id}")
            
            return {
                "bmc": bmc,
                "project_id": project_id,
                "regenerated_block": block_name,
                "message": f"Block {block_name} regenerated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error regenerating BMC block '{block_name}' for project {project_id}: {e}")
            raise
    
    async def _save_progress(
        self,
        project_id: str,
        tenant_id: str,
        partial_bmc: Dict[str, Any],
        message: str
    ) -> None:
        """
        Save partial BMC during generation (for progress tracking and recovery).
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            partial_bmc: Partial BMC data
            message: Progress message
        """
        try:
            success = self.mvp_adapter.save_bmc_progress(project_id, tenant_id, partial_bmc)
            if success:
                logger.info(f"✅ Progress saved: {message}")
            else:
                logger.warning(f"⚠️ Failed to save progress: {message}")
        except Exception as e:
            logger.warning(f"⚠️ Error saving progress: {e}")
            # Don't raise - progress saving failures shouldn't stop generation
    
    async def generate_bmc_v2(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate BMC v2 (refined version) based on solution critique and VPS v2 alignment.
        
        Uses RAG to retrieve relevant critique insights and intelligently refine BMC v1.
        Ensures Value Propositions block aligns with refined VPS v2.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            creativity_level: AI creativity level (0.0-1.0)
            
        Returns:
            Dictionary with BMC v2 data and refinement metadata
            
        Raises:
            ValueError: If BMC v1, VPS v2, or Solution Critique not found
        """
        try:
            logger.info(f"🚀 Starting BMC v2 refinement for project {project_id}")
            
            # Step 1: Validate project access
            logger.info("Step 1: Validating project access...")
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"Project {project_id} not found or access denied")
            logger.info("✅ Step 1: Project access validated")
            
            # Step 2: Check if BMC v1 exists (required)
            logger.info("Step 2: Loading BMC v1...")
            bmc_v1 = self.mvp_adapter.get_bmc(project_id, tenant_id)
            if not bmc_v1:
                raise ValueError(
                    f"BMC v1 not found for project {project_id}. "
                    "Generate BMC v1 first before creating v2."
                )
            logger.info(f"✅ Step 2: BMC v1 loaded (9 blocks)")
            
            # Step 3: Check if VPS v2 exists (required for alignment)
            logger.info("Step 3: Loading VPS v2...")
            vps_v2_list = self.mvp_adapter.get_vps_v2(project_id, tenant_id)
            if not vps_v2_list:
                raise ValueError(
                    f"VPS v2 not found for project {project_id}. "
                    "Generate VPS v2 first before creating BMC v2."
                )
            # VPS v2 is returned as a list for multi-persona support - use first/primary
            vps_v2 = vps_v2_list[0] if isinstance(vps_v2_list, list) else vps_v2_list
            confidence = vps_v2.get('generation_metadata', {}).get('confidence_score', 'N/A') if isinstance(vps_v2, dict) else 'N/A'
            logger.info(f"✅ Step 3: VPS v2 loaded ({len(vps_v2_list) if isinstance(vps_v2_list, list) else 1} VPS, confidence: {confidence})")
            
            # Step 4: Check if solution critique exists
            logger.info("Step 4: Checking for solution critique...")
            project_data = self.mvp_adapter.get_project(project_id, tenant_id)
            if not project_data:
                raise ValueError(f"Project {project_id} not found")
            
            critique_data = project_data.get('soln_critique_data')
            if not critique_data or critique_data.get('status') != 'completed':
                raise ValueError(
                    f"Solution critique not found or not completed for project {project_id}. "
                    "Generate solution critique first to enable BMC v2 refinement."
                )
            logger.info("✅ Step 4: Solution critique found and completed")
            
            # Step 5: Use RAG to retrieve relevant critique chunks
            logger.info("Step 5: Retrieving relevant critique chunks using RAG...")
            critique_chunks = await self._retrieve_critique_chunks_for_bmc(
                project_id=project_id,
                tenant_id=tenant_id,
                bmc_v1=bmc_v1,
                vps_v2=vps_v2
            )
            
            if not critique_chunks:
                logger.warning("⚠️ No critique chunks retrieved. Proceeding with empty critique context.")
            else:
                logger.info(f"✅ Step 5: Retrieved {len(critique_chunks)} relevant critique chunks")
            
            # Step 6: Build minimal context (only project metadata)
            logger.info("Step 6: Building minimal context for BMC v2...")
            context = {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'user_id': user_id
            }
            logger.info("✅ Step 6: Minimal context built (no VPC/personas/research loading)")
            
            # Step 7: Refine BMC using BMC v2 agent with critique chunks and VPS v2
            logger.info("Step 7: Refining BMC with critique-driven analysis and VPS v2 alignment...")
            bmc_v2_data = await self.bmc_v2_agent.refine_bmc(
                bmc_v1=bmc_v1,
                vps_v2=vps_v2,
                critique_chunks=critique_chunks,
                context=context,
                creativity_level=creativity_level
            )
            logger.info(f"✅ Step 7: BMC v2 refined (decision: {bmc_v2_data['refinement_metadata']['refinement_decision']})")
            
            # Step 8: Save to database
            logger.info("Step 8: Saving BMC v2 to database...")
            success = self.mvp_adapter.save_bmc_v2(
                project_id=project_id,
                tenant_id=tenant_id,
                bmc_data=bmc_v2_data,
                user_id=user_id
            )
            
            if not success:
                raise Exception("Failed to save BMC v2 to database")
            logger.info("✅ Step 8: BMC v2 saved successfully")
            
            logger.info(f"✅ Successfully completed BMC v2 refinement for project {project_id}")
            logger.info(f"Blocks changed: {bmc_v2_data['refinement_metadata']['blocks_changed']}/9")
            logger.info(f"VPS v2 aligned: {bmc_v2_data['generation_metadata']['vps_v2_aligned']}")
            logger.info(f"Critique sources used: {len(bmc_v2_data['refinement_metadata']['critique_sources_used'])}")
            
            return {
                "bmc_v2": bmc_v2_data,
                "project_id": project_id,
                "message": f"BMC v2 refined successfully ({bmc_v2_data['refinement_metadata']['refinement_decision']})"
            }
            
        except ValueError as e:
            logger.error(f"❌ Validation error in BMC v2 refinement: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error generating BMC v2 for project {project_id}: {e}")
            raise
    
    async def _retrieve_critique_chunks_for_bmc(
        self,
        project_id: str,
        tenant_id: str,
        bmc_v1: Dict[str, Any],
        vps_v2: Dict[str, Any]
    ) -> list:
        """
        Retrieve relevant critique chunks using RAG for BMC refinement.
        
        Uses BMC v1 and VPS v2 content to query critique chunks and retrieve
        the most relevant feedback for refinement.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            bmc_v1: Current BMC v1 data
            vps_v2: Refined VPS v2 data
            
        Returns:
            List of relevant critique chunks
        """
        try:
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            from src.mint.api.system.core.supabase_client import get_service_role_client
            import numpy as np
            
            chunk_service = get_chunk_storage_service()
            embedding_service = EmbeddingService()
            
            # Load all chunks for the project
            all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            if not all_chunks:
                # Try with service role client directly (bypass RLS)
                logger.warning(f"No chunks found via chunk_service for project {project_id}, trying service role...")
                supabase = get_service_role_client()
                result = supabase.client.table("chunks") \
                    .select("id, chunk_index, content, embedding, metadata") \
                    .eq("doc_id", project_id) \
                    .order("chunk_index") \
                    .execute()
                all_chunks = result.data if result.data else []
                logger.info(f"Service role query found {len(all_chunks)} chunks")
                
                if not all_chunks:
                    # Also try querying by metadata.project_id as fallback
                    logger.warning(f"Still no chunks, checking metadata.project_id...")
                    result = supabase.client.table("chunks") \
                        .select("id, chunk_index, content, embedding, metadata") \
                        .execute()
                    # Filter by metadata project_id
                    all_chunks = [
                        c for c in (result.data or [])
                        if c.get('metadata', {}).get('project_id') == project_id
                    ]
                    logger.info(f"Metadata filter found {len(all_chunks)} chunks")
            
            if not all_chunks:
                logger.warning(f"No chunks found for project {project_id} after all attempts")
                return []
            
            # Filter for solution_critique chunks only
            critique_chunks = [
                chunk for chunk in all_chunks
                if chunk.get('metadata', {}).get('source_type') == 'solution_critique'
            ]
            
            logger.info(f"Found {len(all_chunks)} total chunks, {len(critique_chunks)} solution_critique chunks")
            
            if not critique_chunks:
                logger.warning(f"No solution_critique chunks found for project {project_id}")
                return []
            
            # Build query from BMC v1 blocks and VPS v2
            # Handle both structured (dict) and legacy (string) primary_statement formats
            primary_stmt = vps_v2.get('primary_statement', '')
            if isinstance(primary_stmt, dict):
                primary_text = " ".join([
                    primary_stmt.get('our', ''),
                    primary_stmt.get('help', ''),
                    primary_stmt.get('who_want_to', ''),
                    primary_stmt.get('by', ''),
                    primary_stmt.get('and', ''),
                    primary_stmt.get('unlike', '')
                ]).strip()
            else:
                primary_text = primary_stmt
            
            query_parts = [
                "business model canvas",
                primary_text,
                # Add sample from each BMC block
                str(bmc_v1.get('customer_segments', {}).get('items', [])[:2]),
                str(bmc_v1.get('value_propositions', {}).get('items', [])[:2]),
                str(bmc_v1.get('revenue_streams', {}).get('items', [])[:2])
            ]
            query = " ".join(query_parts)[:500]  # Limit query length
            
            logger.info(f"RAG query: {query[:200]}...")
            
            # Generate query embedding
            query_embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Calculate similarity scores
            scored_chunks = []
            for chunk_data in critique_chunks:
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        import json
                        chunk_embedding = json.loads(raw_embedding)
                        
                        # Cosine similarity
                        chunk_vec = np.array(chunk_embedding)
                        query_vec = np.array(query_embedding)
                        similarity = np.dot(chunk_vec, query_vec) / (
                            np.linalg.norm(chunk_vec) * np.linalg.norm(query_vec)
                        )
                        
                        scored_chunks.append({
                            "chunk": chunk_data,
                            "similarity": float(similarity)
                        })
                    except Exception as e:
                        logger.warning(f"Error calculating similarity for chunk: {e}")
                        continue
            
            # Sort by similarity and get top chunks (20 for BMC - more blocks to refine)
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = scored_chunks[:20]  # Top 20 for BMC (vs 15 for VPS)
            
            logger.info(f"✅ Retrieved {len(top_chunks)} relevant critique chunks")
            if top_chunks:
                logger.info(f"Top similarity score: {top_chunks[0]['similarity']:.3f}")
                logger.info(f"Lowest similarity score: {top_chunks[-1]['similarity']:.3f}")
            
            # Return chunk data with similarity scores
            return [
                {
                    "content": item["chunk"]["content"],
                    "metadata": item["chunk"].get("metadata", {}),
                    "similarity": item["similarity"]
                }
                for item in top_chunks
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving critique chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    # ==================== BMC ITEM ADDITION WITH AI ENHANCEMENT ====================
    
    async def add_bmc_item_with_enhancement(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        label: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Add a new item to a BMC block with AI-enhanced description.
        
        Similar to persona AI enrichment, this:
        1. Takes user's label and description
        2. Queries PV report and actionable insights for relevant context
        3. Uses AI to enhance the description with evidence from the data
        4. Adds the enriched item to the specified BMC block
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of BMC block to add item to
            label: User-provided label/name for the item
            description: User-provided description (will be AI-enhanced)
            
        Returns:
            Dict with added_item, ai_enhanced flag, and updated BMC
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Validate block name
            valid_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            if block_name not in valid_blocks:
                raise ValueError(f"Invalid block name: {block_name}. Valid blocks: {', '.join(valid_blocks)}")
            
            # Get existing BMC
            existing_bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            if not existing_bmc:
                raise ValueError("No existing BMC found. Generate BMC first before adding items.")
            
            logger.info(f"🔍 Adding AI-enhanced item to BMC block '{block_name}' for project {project_id}")
            
            # AI ENRICHMENT: Query PV report and actionable insights
            ai_enhanced = True
            enhanced_description = description
            evidence_source = "user_input"
            
            try:
                # Use dual context search to find relevant information
                context_query = f"{label} {description} {block_name.replace('_', ' ')} business model"
                
                logger.info(f"🔍 Context query: {context_query}")
                
                context = await self.vector_adapter.dual_context_search(
                    project_id=project_id,
                    query=context_query,
                    max_results_per_store=10
                )
                
                logger.info(f"🔍 Retrieved context - PV: {len(context.get('pv_report_context', []))} items, Insights: {len(context.get('actionable_insights_context', []))}")
                
                # Extract evidence from context
                evidence_items = []
                
                # Get evidence from PV report context
                for item in context.get('pv_report_context', [])[:2]:
                    raw_content = item.get('content', '')
                    cleaned_quote = self._clean_evidence_quote(raw_content, max_length=400)
                    if len(cleaned_quote) > 50:
                        evidence_items.append({
                            "source": "pv_report",
                            "quote": cleaned_quote,
                            "relevance_score": item.get('score', 0.8)
                        })
                
                # Get evidence from actionable insights
                for item in context.get('actionable_insights_context', [])[:1]:
                    raw_content = item.get('content', '')
                    cleaned_quote = self._clean_evidence_quote(raw_content, max_length=400)
                    if len(cleaned_quote) > 50:
                        evidence_items.append({
                            "source": "actionable_insights",
                            "quote": cleaned_quote,
                            "relevance_score": item.get('score', 0.8)
                        })
                
                logger.info(f"🔍 Extracted {len(evidence_items)} evidence items")
                
                if evidence_items:
                    # Use Azure OpenAI to enhance description (same provider as BMC generation)
                    from src.mint.api.ai.providers import OpenAIProvider
                    from src.mint.api.ai.models import LLMConfig
                    from src.mint.api.ai.config import get_client_config, ModelUseCase
                    
                    # Get Azure OpenAI config
                    provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
                    
                    # Build config - gpt-5-mini doesn't support temperature
                    is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
                    
                    config_kwargs = {
                        "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
                        "model_name": model_name,
                        "max_tokens": 16000,  # gpt-5-mini needs large token budget
                        "azure_endpoint": client_config.get("azure_endpoint"),
                        "api_version": client_config.get("api_version"),
                        "api_key": client_config.get("api_key")
                    }
                    
                    if not is_gpt5_model:
                        config_kwargs["temperature"] = 0.3  # Lower temperature for more consistent enhancement
                    
                    config = LLMConfig(**config_kwargs)
                    ai_provider = OpenAIProvider(config)
                    
                    logger.info(f"🔧 Using Azure OpenAI for BMC v1 enhancement: {provider_type}, model={model_name}")
                    
                    # Prepare context for AI
                    context_text = "\n\n".join([
                        f"Evidence {i+1} ({ev['source']}): {ev['quote']}"
                        for i, ev in enumerate(evidence_items)
                    ])
                    
                    # Block-specific enhancement guidance
                    block_guidance = self._get_block_enhancement_guidance(block_name)
                    
                    enhancement_prompt = f"""Based on the user's BMC item concept and evidence from the PV report and insights, enhance the description to be more specific and data-driven.

BMC Block: {block_name.replace('_', ' ').title()}
User's Item Label: {label}
User's Description: {description}

Evidence from PV Report and Insights:
{context_text}

{block_guidance}

Task:
1. Enhance the description to be more specific, actionable, and data-driven (keep it 50-400 characters)
2. Ground the enhanced content in the evidence provided
3. Maintain the user's original intent while adding specificity
4. Identify the most relevant evidence source for this item

Return ONLY a JSON object with this structure:
{{
  "enhanced_description": "Enhanced description here",
  "evidence_source": "The primary evidence source (e.g., 'pv_report', 'market_research', 'field_research', 'vpc_analysis')"
}}"""

                    messages = [
                        {"role": "system", "content": "You are an expert business model strategist. Enhance BMC item descriptions based on evidence from market research data. Return ONLY valid JSON."},
                        {"role": "user", "content": enhancement_prompt}
                    ]
                    
                    logger.info(f"🔍 Calling Azure OpenAI for BMC v1 enhancement")
                    
                    # Call Azure OpenAI with JSON response format
                    response = await ai_provider.generate_chat(
                        messages=messages,
                        response_format={"type": "json_object"}
                    )
                    
                    # Parse response
                    import json
                    if not response.content:
                        raise ValueError("AI returned empty content")
                    ai_response = json.loads(response.content)
                    
                    enhanced_description = ai_response.get('enhanced_description', description)
                    evidence_source = ai_response.get('evidence_source', 'pv_report')
                    
                    logger.info(f"✅ AI enhancement complete (Azure OpenAI)")
                    logger.info(f"🔍 Enhanced description: {enhanced_description[:100]}...")
                else:
                    logger.warning(f"⚠️ No evidence found, using original description")
                    ai_enhanced = False
                    
            except Exception as e:
                logger.warning(f"⚠️ AI enrichment failed: {str(e)}")
                ai_enhanced = False
                enhanced_description = description
                evidence_source = "user_input"
            
            # Create new item with proper structure based on block type
            new_item = self._create_bmc_item(
                block_name=block_name,
                label=label,
                enhanced_description=enhanced_description,
                evidence_source=evidence_source,
                existing_bmc=existing_bmc,
                user_id=user_id,
                ai_enhanced=ai_enhanced
            )
            
            # Add item to the block
            block_data = existing_bmc.get(block_name, {})
            items_key = self._get_block_items_key(block_name)
            
            if items_key not in block_data:
                block_data[items_key] = []
            
            block_data[items_key].append(new_item)
            
            # Update the block in BMC
            success = self.mvp_adapter.update_bmc_block(
                project_id,
                tenant_id,
                block_name,
                block_data,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to add item to block {block_name}")
            
            # Get updated BMC
            updated_bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            
            logger.info(f"✅ Added AI-enhanced item to BMC block '{block_name}' for project {project_id}")
            
            return {
                "added_item": new_item,
                "ai_enhanced": ai_enhanced,
                "block_name": block_name,
                "bmc": updated_bmc,
                "project_id": project_id,
                "message": f"Successfully added item '{label}' to {block_name.replace('_', ' ')}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding BMC item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _clean_evidence_quote(self, text: str, max_length: int = 400) -> str:
        """Clean and format evidence quotes by removing HTML tags and truncating properly."""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove chunk IDs and markers
        text = re.sub(r'chunk-\d+', '', text)
        text = re.sub(r'class="report-chunk"', '', text)
        
        # Remove markdown headers at the start
        text = re.sub(r'^#+\s+', '', text.strip())
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        # Truncate to max length
        if len(text) > max_length:
            truncated = text[:max_length]
            last_period = truncated.rfind('.')
            last_question = truncated.rfind('?')
            last_exclamation = truncated.rfind('!')
            
            last_sentence_end = max(last_period, last_question, last_exclamation)
            
            if last_sentence_end > max_length * 0.7:
                text = truncated[:last_sentence_end + 1]
            else:
                last_space = truncated.rfind(' ')
                if last_space > 0:
                    text = truncated[:last_space] + '...'
                else:
                    text = truncated + '...'
        
        return text.strip()
    
    def _get_block_enhancement_guidance(self, block_name: str) -> str:
        """Get block-specific guidance for AI enhancement."""
        guidance = {
            'customer_segments': "Focus on specific demographics, behaviors, needs, and market size data.",
            'value_propositions': "Emphasize unique benefits, pain relief, and gain creation with quantifiable impact.",
            'channels': "Include specific channel types, reach metrics, and customer touchpoints.",
            'customer_relationships': "Describe relationship type, engagement methods, and retention strategies.",
            'revenue_streams': "Include pricing models, revenue potential, and customer willingness to pay.",
            'key_resources': "Specify resource type (physical, intellectual, human, financial) and strategic importance.",
            'key_activities': "Focus on critical operations, processes, and their impact on value delivery.",
            'key_partnerships': "Describe partner type, strategic value, and mutual benefits.",
            'cost_structure': "Include cost type (fixed/variable), magnitude estimates, and optimization potential."
        }
        return f"Block-specific guidance: {guidance.get(block_name, 'Provide specific, actionable details.')}"
    
    def _get_block_items_key(self, block_name: str) -> str:
        """Get the key used for items array in each block."""
        items_keys = {
            'customer_segments': 'segments',
            'value_propositions': 'propositions',
            'channels': 'channels',
            'customer_relationships': 'relationships',
            'revenue_streams': 'revenue_streams',
            'key_resources': 'resources',
            'key_activities': 'activities',
            'key_partnerships': 'partnerships',
            'cost_structure': 'cost_categories'
        }
        return items_keys.get(block_name, 'items')
    
    def _create_bmc_item(
        self,
        block_name: str,
        label: str,
        enhanced_description: str,
        evidence_source: str,
        existing_bmc: Dict[str, Any],
        user_id: str,
        ai_enhanced: bool
    ) -> Dict[str, Any]:
        """Create a properly structured BMC item based on block type."""
        from datetime import datetime
        import re
        
        # Get existing items to determine next ID
        block_data = existing_bmc.get(block_name, {})
        
        # Try multiple keys to find existing items (BMC v1 uses specific keys, BMC v2 uses 'items')
        items_key = self._get_block_items_key(block_name)
        existing_items = block_data.get(items_key, [])
        
        # Also check 'items' key for BMC v2 structure
        if not existing_items and 'items' in block_data:
            existing_items = block_data.get('items', [])
        
        # Generate ID based on block prefix
        id_prefixes = {
            'customer_segments': 'seg',
            'value_propositions': 'vp',
            'channels': 'ch',
            'customer_relationships': 'rel',
            'revenue_streams': 'rev',
            'key_resources': 'res',
            'key_activities': 'act',
            'key_partnerships': 'part',
            'cost_structure': 'cost'
        }
        prefix = id_prefixes.get(block_name, 'item')
        
        # Find the highest existing ID number to ensure unique sequential ID
        max_id_num = 0
        for item in existing_items:
            item_id = item.get('id', '')
            # Extract number from ID like "ch-001", "seg-002", etc.
            match = re.search(r'-(\d+)$', item_id)
            if match:
                id_num = int(match.group(1))
                if id_num > max_id_num:
                    max_id_num = id_num
        
        new_id = f"{prefix}-{max_id_num + 1:03d}"
        logger.info(f"🔢 Generated new ID: {new_id} (found {len(existing_items)} existing items, max ID num: {max_id_num})")
        
        # Base item structure
        base_item = {
            "id": new_id,
            "name": label,
            "description": enhanced_description,
            "evidence_source": evidence_source,
            "created_by": "user",
            "user_id": user_id,
            "ai_enhanced": ai_enhanced,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add block-specific fields
        if block_name == 'customer_segments':
            base_item.update({
                "type": "user_defined",
                "characteristics": [],
                "needs": [],
                "size_estimate": "To be determined"
            })
        elif block_name == 'value_propositions':
            base_item.update({
                "target_segments": [],
                "pain_relievers": [],
                "gain_creators": []
            })
        elif block_name == 'channels':
            base_item.update({
                "type": "user_defined",
                "phase": "awareness",
                "segment_ids": []
            })
        elif block_name == 'customer_relationships':
            base_item.update({
                "type": "user_defined",
                "segment_ids": [],
                "purpose": "acquisition"
            })
        elif block_name == 'revenue_streams':
            base_item.update({
                "type": "user_defined",
                "pricing_strategy": "To be determined",
                "revenue_potential": "To be determined",
                "segment_ids": []
            })
        elif block_name == 'key_resources':
            base_item.update({
                "type": "user_defined",
                "criticality": "medium",
                "required_for": [],
                "acquisition_strategy": "To be determined"
            })
        elif block_name == 'key_activities':
            base_item.update({
                "type": "user_defined",
                "criticality": "medium",
                "required_for": [],
                "resources_needed": []
            })
        elif block_name == 'key_partnerships':
            base_item.update({
                "partner_type": "strategic_alliance",
                "partner_description": label,
                "motivation": "To be determined",
                "value_contribution": enhanced_description,
                "activities_supported": [],
                "resources_provided": []
            })
        elif block_name == 'cost_structure':
            base_item.update({
                "type": "user_defined",
                "related_resources": [],
                "related_activities": [],
                "related_partnerships": [],
                "cost_estimate": "To be determined",
                "optimization_potential": "To be determined"
            })
        
        return base_item
    
    async def add_bmc_v2_item_with_enhancement(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        label: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Add a new item to a BMC v2 block with AI-enhanced description.
        
        Same as add_bmc_item_with_enhancement but operates on BMC v2.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of BMC block to add item to
            label: User-provided label/name for the item
            description: User-provided description (will be AI-enhanced)
            
        Returns:
            Dict with added_item, ai_enhanced flag, and updated BMC v2
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Validate block name
            valid_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            if block_name not in valid_blocks:
                raise ValueError(f"Invalid block name: {block_name}. Valid blocks: {', '.join(valid_blocks)}")
            
            # Get existing BMC v2
            existing_bmc_v2 = self.mvp_adapter.get_bmc_v2(project_id, tenant_id)
            if not existing_bmc_v2:
                raise ValueError("No existing BMC v2 found. Generate BMC v2 first before adding items.")
            
            logger.info(f"🔍 Adding AI-enhanced item to BMC v2 block '{block_name}' for project {project_id}")
            
            # AI ENRICHMENT: Query PV report and actionable insights
            ai_enhanced = True
            enhanced_description = description
            evidence_source = "user_input"
            
            try:
                # Use dual context search to find relevant information
                context_query = f"{label} {description} {block_name.replace('_', ' ')} business model"
                
                logger.info(f"🔍 Context query: {context_query}")
                
                context = await self.vector_adapter.dual_context_search(
                    project_id=project_id,
                    query=context_query,
                    max_results_per_store=10
                )
                
                logger.info(f"🔍 Retrieved context - PV: {len(context.get('pv_report_context', []))} items, Insights: {len(context.get('actionable_insights_context', []))}")
                
                # Extract evidence from context
                evidence_items = []
                
                # Get evidence from PV report context
                for item in context.get('pv_report_context', [])[:2]:
                    raw_content = item.get('content', '')
                    cleaned_quote = self._clean_evidence_quote(raw_content, max_length=400)
                    if len(cleaned_quote) > 50:
                        evidence_items.append({
                            "source": "pv_report",
                            "quote": cleaned_quote,
                            "relevance_score": item.get('score', 0.8)
                        })
                
                # Get evidence from actionable insights
                for item in context.get('actionable_insights_context', [])[:1]:
                    raw_content = item.get('content', '')
                    cleaned_quote = self._clean_evidence_quote(raw_content, max_length=400)
                    if len(cleaned_quote) > 50:
                        evidence_items.append({
                            "source": "actionable_insights",
                            "quote": cleaned_quote,
                            "relevance_score": item.get('score', 0.8)
                        })
                
                logger.info(f"🔍 Extracted {len(evidence_items)} evidence items")
                
                if evidence_items:
                    # Use Azure OpenAI to enhance description (same provider as BMC generation)
                    from src.mint.api.ai.providers import OpenAIProvider
                    from src.mint.api.ai.models import LLMConfig
                    from src.mint.api.ai.config import get_client_config, ModelUseCase
                    
                    # Get Azure OpenAI config
                    provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
                    
                    # Build config - gpt-5-mini doesn't support temperature
                    is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
                    
                    config_kwargs = {
                        "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
                        "model_name": model_name,
                        "max_tokens": 16000,  # gpt-5-mini needs large token budget
                        "azure_endpoint": client_config.get("azure_endpoint"),
                        "api_version": client_config.get("api_version"),
                        "api_key": client_config.get("api_key")
                    }
                    
                    if not is_gpt5_model:
                        config_kwargs["temperature"] = 0.3  # Lower temperature for more consistent enhancement
                    
                    config = LLMConfig(**config_kwargs)
                    ai_provider = OpenAIProvider(config)
                    
                    logger.info(f"🔧 Using Azure OpenAI for BMC v2 enhancement: {provider_type}, model={model_name}")
                    
                    # Prepare context for AI
                    context_text = "\n\n".join([
                        f"Evidence {i+1} ({ev['source']}): {ev['quote']}"
                        for i, ev in enumerate(evidence_items)
                    ])
                    
                    # Block-specific enhancement guidance
                    block_guidance = self._get_block_enhancement_guidance(block_name)
                    
                    enhancement_prompt = f"""Based on the user's BMC item concept and evidence from the PV report and insights, enhance the description to be more specific and data-driven.

BMC Block: {block_name.replace('_', ' ').title()}
User's Item Label: {label}
User's Description: {description}

Evidence from PV Report and Insights:
{context_text}

{block_guidance}

Task:
1. Enhance the description to be more specific, actionable, and data-driven (keep it 50-400 characters)
2. Ground the enhanced content in the evidence provided
3. Maintain the user's original intent while adding specificity
4. Identify the most relevant evidence source for this item

Return ONLY a JSON object with this structure:
{{
  "enhanced_description": "Enhanced description here",
  "evidence_source": "The primary evidence source (e.g., 'pv_report', 'market_research', 'field_research', 'vpc_analysis')"
}}"""

                    messages = [
                        {"role": "system", "content": "You are an expert business model strategist. Enhance BMC item descriptions based on evidence from market research data. Return ONLY valid JSON."},
                        {"role": "user", "content": enhancement_prompt}
                    ]
                    
                    logger.info(f"🔍 Calling Azure OpenAI for BMC v2 enhancement")
                    
                    # Call Azure OpenAI with JSON response format
                    response = await ai_provider.generate_chat(
                        messages=messages,
                        response_format={"type": "json_object"}
                    )
                    
                    # Parse response
                    import json
                    if not response.content:
                        raise ValueError("AI returned empty content")
                    ai_response = json.loads(response.content)
                    
                    enhanced_description = ai_response.get('enhanced_description', description)
                    evidence_source = ai_response.get('evidence_source', 'pv_report')
                    
                    logger.info(f"✅ AI enhancement complete (Azure OpenAI)")
                    logger.info(f"🔍 Enhanced description: {enhanced_description[:100]}...")
                else:
                    logger.warning(f"⚠️ No evidence found, using original description")
                    ai_enhanced = False
                    
            except Exception as e:
                logger.warning(f"⚠️ AI enrichment failed: {str(e)}")
                ai_enhanced = False
                enhanced_description = description
                evidence_source = "user_input"
            
            # Create new item with proper structure based on block type
            new_item = self._create_bmc_item(
                block_name=block_name,
                label=label,
                enhanced_description=enhanced_description,
                evidence_source=evidence_source,
                existing_bmc=existing_bmc_v2,
                user_id=user_id,
                ai_enhanced=ai_enhanced
            )
            
            # Add item to the block - BMC v2 uses 'items' key for all blocks
            block_data = existing_bmc_v2.get(block_name, {})
            
            # BMC v2 structure uses 'items' key
            if 'items' not in block_data:
                block_data['items'] = []
            
            block_data['items'].append(new_item)
            block_data['changed'] = True
            block_data['change_reason'] = f"User added item: {label}"
            
            # Update the block in BMC v2
            existing_bmc_v2[block_name] = block_data
            
            # Save updated BMC v2
            success = self.mvp_adapter.save_bmc_v2(
                project_id,
                tenant_id,
                existing_bmc_v2,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to add item to BMC v2 block {block_name}")
            
            # Get updated BMC v2
            updated_bmc_v2 = self.mvp_adapter.get_bmc_v2(project_id, tenant_id)
            
            logger.info(f"✅ Added AI-enhanced item to BMC v2 block '{block_name}' for project {project_id}")
            
            return {
                "added_item": new_item,
                "ai_enhanced": ai_enhanced,
                "block_name": block_name,
                "bmc": updated_bmc_v2,
                "project_id": project_id,
                "message": f"Successfully added item '{label}' to BMC v2 {block_name.replace('_', ' ')}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding BMC v2 item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def delete_bmc_item(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        item_id: str
    ) -> Dict[str, Any]:
        """
        Delete an item from a BMC v1 block by its ID.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of BMC block to delete item from
            item_id: ID of the item to delete (e.g., 'ch-001', 'seg-002')
            
        Returns:
            Dict with deleted_item_id and updated BMC
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Validate block name
            valid_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            if block_name not in valid_blocks:
                raise ValueError(f"Invalid block name: {block_name}. Valid blocks: {', '.join(valid_blocks)}")
            
            # Get existing BMC
            existing_bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            if not existing_bmc:
                raise ValueError("No existing BMC found.")
            
            logger.info(f"🗑️ Deleting item '{item_id}' from BMC block '{block_name}' for project {project_id}")
            
            # Get the block data
            block_data = existing_bmc.get(block_name, {})
            
            # Find items - try specific key first, then 'items'
            items_key = self._get_block_items_key(block_name)
            existing_items = block_data.get(items_key, [])
            
            if not existing_items and 'items' in block_data:
                items_key = 'items'
                existing_items = block_data.get('items', [])
            
            # Find and remove the item
            item_found = False
            updated_items = []
            for item in existing_items:
                if item.get('id') == item_id:
                    item_found = True
                    logger.info(f"🗑️ Found item to delete: {item.get('name', item_id)}")
                else:
                    updated_items.append(item)
            
            if not item_found:
                raise ValueError(f"Item with ID '{item_id}' not found in block '{block_name}'")
            
            # Update the block with remaining items
            block_data[items_key] = updated_items
            existing_bmc[block_name] = block_data
            
            # Save updated BMC
            success = self.mvp_adapter.update_bmc_block(
                project_id,
                tenant_id,
                block_name,
                block_data,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to delete item from BMC block {block_name}")
            
            # Get updated BMC
            updated_bmc = self.mvp_adapter.get_bmc(project_id, tenant_id)
            
            logger.info(f"✅ Deleted item '{item_id}' from BMC block '{block_name}' for project {project_id}")
            
            return {
                "deleted_item_id": item_id,
                "block_name": block_name,
                "bmc": updated_bmc,
                "project_id": project_id,
                "message": f"Successfully deleted item '{item_id}' from {block_name.replace('_', ' ')}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting BMC item: {e}")
            raise
    
    def delete_bmc_v2_item(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        item_id: str
    ) -> Dict[str, Any]:
        """
        Delete an item from a BMC v2 block by its ID.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            block_name: Name of BMC block to delete item from
            item_id: ID of the item to delete (e.g., 'ch-001', 'seg-002')
            
        Returns:
            Dict with deleted_item_id and updated BMC v2
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"User {user_id} does not have access to project {project_id}")
            
            # Validate block name
            valid_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            if block_name not in valid_blocks:
                raise ValueError(f"Invalid block name: {block_name}. Valid blocks: {', '.join(valid_blocks)}")
            
            # Get existing BMC v2
            existing_bmc_v2 = self.mvp_adapter.get_bmc_v2(project_id, tenant_id)
            if not existing_bmc_v2:
                raise ValueError("No existing BMC v2 found.")
            
            logger.info(f"🗑️ Deleting item '{item_id}' from BMC v2 block '{block_name}' for project {project_id}")
            
            # Get the block data
            block_data = existing_bmc_v2.get(block_name, {})
            
            # BMC v2 uses 'items' key
            existing_items = block_data.get('items', [])
            
            # Find and remove the item
            item_found = False
            updated_items = []
            for item in existing_items:
                if item.get('id') == item_id:
                    item_found = True
                    logger.info(f"🗑️ Found item to delete: {item.get('name', item_id)}")
                else:
                    updated_items.append(item)
            
            if not item_found:
                raise ValueError(f"Item with ID '{item_id}' not found in BMC v2 block '{block_name}'")
            
            # Update the block with remaining items
            block_data['items'] = updated_items
            block_data['changed'] = True
            block_data['change_reason'] = f"User deleted item: {item_id}"
            existing_bmc_v2[block_name] = block_data
            
            # Save updated BMC v2
            success = self.mvp_adapter.save_bmc_v2(
                project_id,
                tenant_id,
                existing_bmc_v2,
                user_id
            )
            
            if not success:
                raise ValueError(f"Failed to delete item from BMC v2 block {block_name}")
            
            # Get updated BMC v2
            updated_bmc_v2 = self.mvp_adapter.get_bmc_v2(project_id, tenant_id)
            
            logger.info(f"✅ Deleted item '{item_id}' from BMC v2 block '{block_name}' for project {project_id}")
            
            return {
                "deleted_item_id": item_id,
                "block_name": block_name,
                "bmc": updated_bmc_v2,
                "project_id": project_id,
                "message": f"Successfully deleted item '{item_id}' from BMC v2 {block_name.replace('_', ' ')}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting BMC v2 item: {e}")
            raise
