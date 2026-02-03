"""
VPS Service - Orchestration Layer

Handles business logic and orchestration for VPS generation.
Coordinates between context loading, AI generation, and database storage.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..adapters.database_adapter import get_mvp_database_adapter
from ..agents.vps_agent import VPSGenerationAgent
from ..agents.vps_v2_agent import VPSV2RefinementAgent
from ..utils.context_loader import MVPContextLoader
from src.vpm.adapters.database_adapter import get_yuba_database_adapter
from src.vpm.adapters.vector_adapter import get_yuba_vector_adapter

logger = logging.getLogger(__name__)


class VPSService:
    """Service for VPS generation orchestration."""
    
    def __init__(self):
        """Initialize VPS service with required adapters and agents."""
        self.mvp_adapter = get_mvp_database_adapter(use_service_role=True)
        self.vpm_adapter = get_yuba_database_adapter()
        self.vector_adapter = get_yuba_vector_adapter()
        self.vps_agent = VPSGenerationAgent()
        self.vps_v2_agent = VPSV2RefinementAgent()
        self.context_loader = MVPContextLoader(self.vpm_adapter, self.vector_adapter)
        
        logger.info("VPS Service initialized with v1 and v2 agents")
    
    async def generate_vps_v1(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate VPS v1 for a project.
        
        Supports multi-persona generation:
        - 1 persona: Generates 1 VPS
        - 2 personas: Generates 2 VPS in parallel (one per persona)
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            creativity_level: AI creativity level (0.0-1.0)
            
        Returns:
            Dictionary with VPS v1 data (array) and metadata
            
        Raises:
            ValueError: If validation fails or context insufficient
            Exception: If generation fails
        """
        try:
            logger.info(f"🚀 Starting VPS v1 generation for project {project_id}")
            
            # Step 1: Validate project access
            logger.info(f"Step 1: Validating project access...")
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"Project {project_id} not found or access denied")
            logger.info(f"✅ Step 1: Project access validated")
            
            # Step 2: Get project to check context mode
            logger.info(f"Step 2: Fetching project details...")
            project = self.mvp_adapter.get_project(project_id, tenant_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Check if this is a bootstrap project
            context_mode = project.get('context_mode', 'normal')
            
            if context_mode == 'bootstrap':
                # Bootstrap mode: Personas are synthesized from enhanced_context
                logger.info(f"🚀 Bootstrap mode detected - using bootstrap context flow")
                vps_list = await self._generate_bootstrap_vps(
                    project_id, tenant_id, user_id, project, creativity_level
                )
            else:
                # Normal mode: Personas must exist in project data
                personas = project.get('personas', [])
                if not personas:
                    raise ValueError("No personas found. Please identify personas first.")
                
                logger.info(f"✅ Found {len(personas)} persona(s): {[p.get('name', 'Unknown') for p in personas]}")
                
                # Step 3: Generate VPS for each persona (in parallel if multiple)
                if len(personas) == 1:
                    logger.info(f"📝 Single persona detected - generating 1 VPS")
                    vps_list = await self._generate_single_persona_vps(
                        project_id, tenant_id, user_id, personas[0], creativity_level
                    )
                else:
                    logger.info(f"🎭 Multiple personas detected - generating {len(personas)} VPS in parallel")
                    vps_list = await self._generate_multi_persona_vps_parallel(
                        project_id, tenant_id, user_id, personas, creativity_level
                    )
            
            # Step 4: Save to database (as array)
            logger.info(f"Saving {len(vps_list)} VPS to database")
            success = self.mvp_adapter.save_vps_v1(
                project_id=project_id,
                tenant_id=tenant_id,
                vps_data=vps_list,  # Now an array
                user_id=user_id
            )
            
            if not success:
                raise Exception("Failed to save VPS v1 to database")
            
            logger.info(f"✅ Successfully completed VPS v1 generation for project {project_id}")
            
            # Step 5: Return result
            # For bootstrap mode, persona_count comes from vps_list length
            persona_count = len(personas) if context_mode != 'bootstrap' else len(vps_list)
            
            return {
                "vps_v1": vps_list,  # Array of VPS (1 or 2)
                "project_id": project_id,
                "persona_count": persona_count,
                "vps_count": len(vps_list),
                "context_mode": context_mode,
                "already_existed": False,
                "message": f"Generated {len(vps_list)} VPS" + (f" for {persona_count} persona(s)" if context_mode != 'bootstrap' else " from bootstrap context")
            }
            
        except ValueError as e:
            logger.error(f"❌ Validation error in VPS generation: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error generating VPS v1 for project {project_id}: {e}")
            raise
    
    async def _generate_single_persona_vps(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona: Dict[str, Any],
        creativity_level: float
    ) -> List[Dict[str, Any]]:
        """Generate VPS for a single persona."""
        try:
            persona_id = persona.get('id') or persona.get('persona_id')
            persona_name = persona.get('name') or persona.get('persona_name', 'Unknown')
            
            logger.info(f"📝 Generating VPS for persona: {persona_name} (ID: {persona_id})")
            
            # Load persona-specific context
            context = await self.context_loader.load_vps_context_for_persona(
                project_id, tenant_id, persona
            )
            
            # Validate context completeness
            completeness = context.get('context_completeness', 0.0)
            if completeness < 0.5:
                raise ValueError(
                    f"Insufficient context for persona {persona_name} (completeness: {completeness:.2%})"
                )
            
            # Add user_id to context for monitoring
            context['user_id'] = user_id
            context['tenant_id'] = tenant_id
            
            # Generate VPS
            vps_data = await self.vps_agent.generate_vps(
                context=context,
                creativity_level=creativity_level
            )
            
            logger.info(f"✅ Generated VPS for {persona_name} with confidence: {vps_data['generation_metadata']['confidence_score']:.2f}")
            
            return [vps_data]  # Return as single-item array
            
        except Exception as e:
            logger.error(f"❌ Error generating VPS for persona {persona_name}: {e}")
            raise
    
    async def _generate_bootstrap_vps(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        project: Dict[str, Any],
        creativity_level: float
    ) -> List[Dict[str, Any]]:
        """
        Generate VPS for a bootstrap project using enhanced_context.
        
        Bootstrap projects don't have traditional personas - instead they have
        CustomerSegments in enhanced_context which are adapted into personas
        by the BootstrapContextAdapter.
        """
        try:
            logger.info(f"📝 Generating VPS for bootstrap project {project_id}")
            
            # Load context using the context loader (which handles bootstrap mode)
            context = await self.context_loader.load_vps_context(project_id, tenant_id)
            
            # Validate context completeness
            completeness = context.get('context_completeness', 0.0)
            if completeness < 0.3:  # Lower threshold for bootstrap projects
                raise ValueError(
                    f"Insufficient bootstrap context (completeness: {completeness:.2%}). "
                    "Please ensure enhanced_context has required fields."
                )
            
            # Get personas from adapted context (synthesized from CustomerSegments)
            personas = context.get('personas', [])
            logger.info(f"✅ Bootstrap context loaded with {len(personas)} synthesized persona(s)")
            
            # Add user_id to context for monitoring
            context['user_id'] = user_id
            context['tenant_id'] = tenant_id
            
            # Generate VPS using the adapted context
            vps_data = await self.vps_agent.generate_vps(
                context=context,
                creativity_level=creativity_level
            )
            
            # Add bootstrap metadata
            vps_data['generation_metadata']['context_mode'] = 'bootstrap'
            vps_data['generation_metadata']['context_source'] = 'enhanced_context'
            
            confidence = vps_data.get('generation_metadata', {}).get('confidence_score', 0)
            logger.info(f"✅ Generated bootstrap VPS with confidence: {confidence:.2f}")
            
            return [vps_data]  # Return as single-item array
            
        except Exception as e:
            logger.error(f"❌ Error generating bootstrap VPS for project {project_id}: {e}")
            raise
    
    async def _generate_multi_persona_vps_parallel(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        personas: List[Dict[str, Any]],
        creativity_level: float
    ) -> List[Dict[str, Any]]:
        """Generate VPS for multiple personas in parallel."""
        import asyncio
        
        try:
            logger.info(f"🚀 Starting parallel VPS generation for {len(personas)} personas")
            
            # Create tasks for each persona
            tasks = []
            for persona in personas:
                persona_id = persona.get('id') or persona.get('persona_id')
                persona_name = persona.get('name') or persona.get('persona_name', 'Unknown')
                logger.info(f"  - Queuing VPS generation for: {persona_name} (ID: {persona_id})")
                
                task = self._generate_vps_for_persona(
                    project_id, tenant_id, user_id, persona, creativity_level
                )
                tasks.append(task)
            
            # Run all generations in parallel
            logger.info(f"⚡ Executing {len(tasks)} parallel VPS generations...")
            vps_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for errors
            vps_list = []
            errors = []
            for idx, result in enumerate(vps_results):
                if isinstance(result, Exception):
                    persona_name = personas[idx].get('name', 'Unknown')
                    error_msg = f"Failed to generate VPS for {persona_name}: {str(result)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                else:
                    vps_list.append(result)
            
            if errors:
                raise Exception(f"Failed to generate VPS for some personas: {'; '.join(errors)}")
            
            logger.info(f"✅ Successfully generated {len(vps_list)} VPS in parallel")
            
            return vps_list
            
        except Exception as e:
            logger.error(f"❌ Error in parallel VPS generation: {e}")
            raise
    
    async def _generate_vps_for_persona(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona: Dict[str, Any],
        creativity_level: float
    ) -> Dict[str, Any]:
        """Generate VPS for a single persona (used in parallel execution)."""
        try:
            persona_id = persona.get('id') or persona.get('persona_id')
            persona_name = persona.get('name') or persona.get('persona_name', 'Unknown')
            
            logger.info(f"🔄 Generating VPS for persona: {persona_name}")
            
            # Load persona-specific context
            context = await self.context_loader.load_vps_context_for_persona(
                project_id, tenant_id, persona
            )
            
            # Validate context completeness
            completeness = context.get('context_completeness', 0.0)
            if completeness < 0.5:
                raise ValueError(
                    f"Insufficient context for persona {persona_name} (completeness: {completeness:.2%})"
                )
            
            # Add user_id to context for monitoring
            context['user_id'] = user_id
            context['tenant_id'] = tenant_id
            
            # Generate VPS
            vps_data = await self.vps_agent.generate_vps(
                context=context,
                creativity_level=creativity_level
            )
            
            logger.info(f"✅ VPS for {persona_name}: confidence {vps_data['generation_metadata']['confidence_score']:.2f}")
            
            return vps_data
            
        except Exception as e:
            logger.error(f"❌ Error generating VPS for persona {persona_name}: {e}")
            raise
    
    async def get_vps_v1(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get VPS v1 for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            
        Returns:
            VPS v1 data or None if not found
        """
        try:
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"Project {project_id} not found or access denied")
            
            vps_data = self.mvp_adapter.get_vps_v1(project_id, tenant_id)
            
            if vps_data:
                logger.info(f"Retrieved VPS v1 for project {project_id}")
            else:
                logger.info(f"No VPS v1 found for project {project_id}")
            
            return vps_data
            
        except Exception as e:
            logger.error(f"Error retrieving VPS v1 for project {project_id}: {e}")
            raise
    
    async def update_vps_v1(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update VPS v1 for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            updates: Dictionary of fields to update
            
        Returns:
            Updated VPS v1 data
            
        Raises:
            ValueError: If VPS v1 not found
        """
        try:
            logger.info(f"Updating VPS v1 for project {project_id}")
            
            # Validate access
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"Project {project_id} not found or access denied")
            
            # Check if VPS v1 exists
            existing_vps = self.mvp_adapter.get_vps_v1(project_id, tenant_id)
            if not existing_vps:
                raise ValueError(f"VPS v1 not found for project {project_id}. Generate it first.")
            
            # Update
            success = self.mvp_adapter.update_vps_v1(
                project_id=project_id,
                tenant_id=tenant_id,
                updates=updates,
                user_id=user_id
            )
            
            if not success:
                raise Exception("Failed to update VPS v1")
            
            # Get updated data
            updated_vps = self.mvp_adapter.get_vps_v1(project_id, tenant_id)
            
            logger.info(f"✅ Successfully updated VPS v1 for project {project_id}")
            
            return updated_vps
            
        except Exception as e:
            logger.error(f"Error updating VPS v1 for project {project_id}: {e}")
            raise
    
    async def generate_vps_v2(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        critique_feedback: Optional[Dict[str, Any]] = None,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate VPS v2 (refined version) based on solution critique feedback.
        
        Uses RAG to retrieve relevant critique insights and intelligently refine VPS v1.
        The agent decides what to update (whole, partial, or nothing) based on critique analysis.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            user_id: User ID for audit trail
            critique_feedback: DEPRECATED - now uses RAG for critique retrieval
            creativity_level: AI creativity level (0.0-1.0)
            
        Returns:
            Dictionary with VPS v2 data and refinement metadata
            
        Raises:
            ValueError: If VPS v1 not found or solution critique not available
        """
        try:
            logger.info(f"🚀 Starting VPS v2 refinement for project {project_id}")
            
            # Step 1: Validate project access
            logger.info("Step 1: Validating project access...")
            if not self.mvp_adapter.validate_project_access(project_id, tenant_id, user_id):
                raise ValueError(f"Project {project_id} not found or access denied")
            logger.info("✅ Step 1: Project access validated")
            
            # Step 2: Check if VPS v1 exists (required) - now returns array
            logger.info("Step 2: Loading VPS v1...")
            vps_v1_list = self.mvp_adapter.get_vps_v1(project_id, tenant_id)
            if not vps_v1_list or len(vps_v1_list) == 0:
                raise ValueError(
                    f"VPS v1 not found for project {project_id}. "
                    "Generate VPS v1 first before creating v2."
                )
            logger.info(f"✅ Step 2: Loaded {len(vps_v1_list)} VPS v1 (multi-persona)")
            
            # Step 3: Check if solution critique exists
            logger.info("Step 3: Checking for solution critique...")
            project_data = self.mvp_adapter.get_project(project_id, tenant_id)
            if not project_data:
                raise ValueError(f"Project {project_id} not found")
            
            critique_data = project_data.get('soln_critique_data')
            if not critique_data or critique_data.get('status') != 'completed':
                raise ValueError(
                    f"Solution critique not found or not completed for project {project_id}. "
                    "Generate solution critique first to enable VPS v2 refinement."
                )
            logger.info("✅ Step 3: Solution critique found and completed")
            
            # Step 4: Refine each VPS (in parallel if multiple)
            if len(vps_v1_list) == 1:
                logger.info("📝 Single VPS detected - refining 1 VPS v2")
                vps_v2_list = await self._refine_single_vps(
                    project_id, tenant_id, user_id, vps_v1_list[0], creativity_level
                )
            else:
                logger.info(f"🎭 Multiple VPS detected - refining {len(vps_v1_list)} VPS v2 in parallel")
                vps_v2_list = await self._refine_multi_vps_parallel(
                    project_id, tenant_id, user_id, vps_v1_list, creativity_level
                )
            
            # Step 5: Save to database (as array)
            logger.info(f"Step 5: Saving {len(vps_v2_list)} VPS v2 to database...")
            success = self.mvp_adapter.save_vps_v2(
                project_id=project_id,
                tenant_id=tenant_id,
                vps_data=vps_v2_list,  # Now an array
                user_id=user_id
            )
            
            if not success:
                raise Exception("Failed to save VPS v2 to database")
            logger.info("✅ Step 5: VPS v2 saved successfully")
            
            logger.info(f"✅ Successfully completed VPS v2 refinement for project {project_id}")
            
            return {
                "vps_v2": vps_v2_list,  # Array of refined VPS
                "project_id": project_id,
                "persona_count": len(vps_v1_list),
                "vps_count": len(vps_v2_list),
                "message": f"Refined {len(vps_v2_list)} VPS for {len(vps_v1_list)} persona(s)"
            }
            
        except ValueError as e:
            logger.error(f"❌ Validation error in VPS v2 refinement: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error generating VPS v2 for project {project_id}: {e}")
            raise
    
    async def _retrieve_critique_chunks_for_vps(
        self,
        project_id: str,
        tenant_id: str,
        vps_v1: Dict[str, Any]
    ) -> list:
        """
        Retrieve relevant critique chunks using RAG for VPS refinement.
        
        Uses the VPS v1 content to query critique chunks and retrieve
        the most relevant feedback for refinement.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            vps_v1: Current VPS v1 data
            
        Returns:
            List of relevant critique chunks
        """
        try:
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            import numpy as np
            
            chunk_service = get_chunk_storage_service()
            embedding_service = EmbeddingService()
            
            # Load all chunks for the project
            all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            if not all_chunks:
                logger.warning(f"No chunks found for project {project_id}")
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
            
            # Build query from VPS v1 components
            # Handle both structured (dict) and legacy (string) primary_statement formats
            primary_stmt = vps_v1.get('primary_statement', '')
            if isinstance(primary_stmt, dict):
                # Structured format - concatenate all components
                primary_text = " ".join([
                    primary_stmt.get('our', ''),
                    primary_stmt.get('help', ''),
                    primary_stmt.get('who_want_to', ''),
                    primary_stmt.get('by', ''),
                    primary_stmt.get('and', ''),
                    primary_stmt.get('unlike', '')
                ])
            else:
                # Legacy string format
                primary_text = primary_stmt
            
            query_parts = [
                "value proposition",
                primary_text,
                " ".join([diff.get('title', '') for diff in vps_v1.get('key_differentiators', [])])
            ]
            query = " ".join(query_parts)
            
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
            
            # Sort by similarity and get top chunks
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = scored_chunks[:15]  # Top 15 most relevant chunks
            
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
    
    async def _refine_single_vps(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        vps_v1: Dict[str, Any],
        creativity_level: float
    ) -> List[Dict[str, Any]]:
        """Refine a single VPS."""
        try:
            persona_id = vps_v1.get('persona_id')
            persona_name = vps_v1.get('persona_name', 'Unknown')
            
            logger.info(f"📝 Refining VPS for persona: {persona_name} (ID: {persona_id})")
            
            # Retrieve critique chunks
            critique_chunks = await self._retrieve_critique_chunks_for_vps(
                project_id=project_id,
                tenant_id=tenant_id,
                vps_v1=vps_v1
            )
            
            # Build context
            context = {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'user_id': user_id,
                'context_completeness': 1.0
            }
            
            # Refine VPS
            vps_v2_data = await self.vps_v2_agent.refine_vps(
                vps_v1=vps_v1,
                critique_chunks=critique_chunks,
                original_context=context,
                creativity_level=creativity_level
            )
            
            logger.info(f"✅ Refined VPS for {persona_name}: {vps_v2_data['refinement_metadata']['refinement_decision']}")
            
            return [vps_v2_data]
            
        except Exception as e:
            logger.error(f"❌ Error refining VPS for persona {persona_name}: {e}")
            raise
    
    async def _refine_multi_vps_parallel(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        vps_v1_list: List[Dict[str, Any]],
        creativity_level: float
    ) -> List[Dict[str, Any]]:
        """Refine multiple VPS in parallel."""
        import asyncio
        
        try:
            logger.info(f"🚀 Starting parallel VPS v2 refinement for {len(vps_v1_list)} personas")
            
            # Create tasks for each VPS
            tasks = []
            for vps_v1 in vps_v1_list:
                persona_name = vps_v1.get('persona_name', 'Unknown')
                persona_id = vps_v1.get('persona_id')
                logger.info(f"  - Queuing VPS v2 refinement for: {persona_name} (ID: {persona_id})")
                
                task = self._refine_vps_for_persona(
                    project_id, tenant_id, user_id, vps_v1, creativity_level
                )
                tasks.append(task)
            
            # Run all refinements in parallel
            logger.info(f"⚡ Executing {len(tasks)} parallel VPS v2 refinements...")
            vps_v2_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for errors
            vps_v2_list = []
            errors = []
            for idx, result in enumerate(vps_v2_results):
                if isinstance(result, Exception):
                    persona_name = vps_v1_list[idx].get('persona_name', 'Unknown')
                    error_msg = f"Failed to refine VPS for {persona_name}: {str(result)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                else:
                    vps_v2_list.append(result)
            
            if errors:
                raise Exception(f"Failed to refine VPS for some personas: {'; '.join(errors)}")
            
            logger.info(f"✅ Successfully refined {len(vps_v2_list)} VPS v2 in parallel")
            
            return vps_v2_list
            
        except Exception as e:
            logger.error(f"❌ Error in parallel VPS v2 refinement: {e}")
            raise
    
    async def _refine_vps_for_persona(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        vps_v1: Dict[str, Any],
        creativity_level: float
    ) -> Dict[str, Any]:
        """Refine VPS for a single persona (used in parallel execution)."""
        try:
            persona_name = vps_v1.get('persona_name', 'Unknown')
            
            logger.info(f"🔄 Refining VPS v2 for persona: {persona_name}")
            
            # Retrieve critique chunks
            critique_chunks = await self._retrieve_critique_chunks_for_vps(
                project_id=project_id,
                tenant_id=tenant_id,
                vps_v1=vps_v1
            )
            
            # Build context
            context = {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'user_id': user_id,
                'context_completeness': 1.0
            }
            
            # Refine VPS
            vps_v2_data = await self.vps_v2_agent.refine_vps(
                vps_v1=vps_v1,
                critique_chunks=critique_chunks,
                original_context=context,
                creativity_level=creativity_level
            )
            
            logger.info(f"✅ VPS v2 for {persona_name}: {vps_v2_data['refinement_metadata']['refinement_decision']}")
            
            return vps_v2_data
            
        except Exception as e:
            logger.error(f"❌ Error refining VPS v2 for persona {persona_name}: {e}")
            raise
    
    def get_current_version(self, project_id: str, tenant_id: str) -> str:
        """
        Get current VPS version for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
            
        Returns:
            Current version ('v1', 'v2', or 'none')
        """
        try:
            versions = self.mvp_adapter.get_current_versions(project_id, tenant_id)
            return versions.get('vps', 'none')
        except Exception as e:
            logger.error(f"Error getting current VPS version: {e}")
            return 'none'


# Singleton instance
_vps_service_instance = None


def get_vps_service() -> VPSService:
    """Get singleton instance of VPS service."""
    global _vps_service_instance
    if _vps_service_instance is None:
        _vps_service_instance = VPSService()
    return _vps_service_instance
