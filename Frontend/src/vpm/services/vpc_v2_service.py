"""
VPC v2 Service for VPM Integration

Generates Value Proposition Canvas v2 after market research analysis completion.
Includes updated customer profile and value map based on validated research.
Supports multi-persona projects with separate VPC v2 for each persona.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# Import Yuba adapters
from ..adapters.auth_adapter import YubaAuthAdapter
from ..adapters.database_adapter import YubaDatabaseAdapter
from ..adapters.vector_adapter import YubaVectorAdapter

# Import market research components for RAG
from ...market_research.adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ...market_research.utils.ai_service_wrapper import AIServiceWrapper
from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
from src.mint.api.services.ai.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Feature IDs for AI token monitoring
VPC_V2_CUSTOMER_PROFILE_FEATURE_ID = "vpc_v2_customer_profile_generation"
VPC_V2_VALUE_MAP_FEATURE_ID = "vpc_v2_value_map_generation"


class VPCv2Service:
    """
    Service for generating VPC v2 after market research analysis.
    
    Follows the same patterns as FieldPrepService and MarketResearchChatService.
    Supports multi-persona projects with separate VPC v2 for each persona.
    """
    
    def __init__(self, auth_adapter, db_adapter, vector_adapter):
        self.auth_adapter = auth_adapter
        self.db_adapter = db_adapter
        self.vector_adapter = vector_adapter
        
        # Reuse market research components
        self.analysis_db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.chunk_service = get_chunk_storage_service()
        self.embedding_service = EmbeddingService()
        self.ai_service = AIServiceWrapper()  # Use same AI service as market research
    
    async def generate_vpc_v2(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for VPC v2 generation.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            persona_id: Optional persona ID for multi-persona projects
        
        Returns:
            Dict with success status, vpc_v2 data, and messages
        """
        try:
            logger.info(f"🎯 VPC v2: Starting generation for project {project_id}, persona {persona_id}")
            
            # Store monitoring context for use in internal methods
            self._user_id = user_id
            self._tenant_id = tenant_id
            self._project_id = project_id
            
            # 1. Validate prerequisites
            validation = await self._validate_prerequisites(project_id, tenant_id)
            if not validation["ready"]:
                logger.error(f"❌ VPC v2: Prerequisites not met: {validation['error']}")
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_requirements": validation["missing"]
                }
            
            logger.info(f"✅ VPC v2: Prerequisites validated")
            
            # 2. Retrieve comprehensive context
            context = await self._retrieve_context_for_vpc_v2(
                project_id, tenant_id, persona_id
            )
            
            if not context["success"]:
                logger.error(f"❌ VPC v2: Failed to retrieve context: {context.get('error')}")
                return context
            
            logger.info(f"✅ VPC v2: Context retrieved successfully")
            
            # 3. Compare and update customer profile
            profile_update = await self._compare_and_update_customer_profile(
                vpc_v1_profile=context["vpc_v1_customer_profile"],
                analysis_results=context["analysis_report_chunks"],
                evidence_chunks=context["research_document_chunks"],
                persona_name=context.get("persona_name", "Target Persona")
            )
            
            if not profile_update["success"]:
                logger.error(f"❌ VPC v2: Customer profile update failed: {profile_update.get('error')}")
                return profile_update
            
            logger.info(f"✅ VPC v2: Customer profile updated (status: {profile_update['validation_status']})")
            
            # 4. Generate value map CANDIDATES (5 options per category, user will select 3)
            value_map_result = await self._generate_value_map(
                updated_customer_profile=profile_update["updated_profile"],
                analysis_results=context["analysis_report_chunks"],
                dual_context={
                    "pv_report": context["pv_report_context"],
                    "actionable_insights": context["actionable_insights_context"]
                },
                persona_name=context.get("persona_name", "Target Persona")
            )
            
            if not value_map_result["success"]:
                logger.error(f"❌ VPC v2: Value map candidates generation failed: {value_map_result.get('error')}")
                return value_map_result
            
            logger.info(f"✅ VPC v2: Value map candidates generated")
            
            # 5. Compose VPC v2 with CANDIDATES (not final selections yet)
            vpc_v2 = {
                "version": "v2",
                "persona_id": persona_id,
                "persona_name": context.get("persona_name", "Target Persona"),
                "customer_profile": profile_update["updated_profile"],
                "value_map_candidates": value_map_result["value_map_candidates"],
                "value_map_selections": None,  # Will be set after user selects 3 from each category
                "validation_metadata": {
                    "validation_status": profile_update["validation_status"],
                    "confidence": profile_update["confidence"],
                    "change_summary": profile_update["updated_profile"].get("change_log", {}),
                    "generated_at": datetime.utcnow().isoformat()
                },
                "status": "candidates_generated"  # Status: candidates_generated -> selections_made
            }
            
            # 6. Store in database
            storage_result = await self._store_vpc_v2(
                project_id=project_id,
                tenant_id=tenant_id,
                persona_id=persona_id,
                vpc_v2_data=vpc_v2
            )
            
            if not storage_result["success"]:
                logger.error(f"❌ VPC v2: Storage failed: {storage_result.get('error')}")
                return storage_result
            
            logger.info(f"✅ VPC v2: Successfully generated and stored")
            
            return {
                "success": True,
                "vpc_v2": vpc_v2,
                "message": "VPC v2 generated successfully with validated customer profile and value map"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"VPC v2 generation failed: {str(e)}"
            }
    
    async def generate_customer_profile_v2(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        PHASE 1: Generate VPC v2 customer profile only.
        
        This is the first step in VPC v2 workflow. It:
        1. Validates prerequisites
        2. Retrieves context
        3. Refines VPC v1 customer profile with research insights
        4. Stores refined customer profile
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            persona_id: Optional persona ID for multi-persona projects
        
        Returns:
            Dict with success status, customer_profile data, and messages
        """
        try:
            logger.info(f"🎯 VPC v2 (Phase 1): Starting customer profile generation for project {project_id}, persona {persona_id}")
            
            # 1. Validate prerequisites
            validation = await self._validate_prerequisites(project_id, tenant_id)
            if not validation["ready"]:
                logger.error(f"❌ VPC v2: Prerequisites not met: {validation['error']}")
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_requirements": validation["missing"]
                }
            
            logger.info(f"✅ VPC v2: Prerequisites validated")
            
            # 2. Retrieve comprehensive context
            context = await self._retrieve_context_for_vpc_v2(
                project_id, tenant_id, persona_id
            )
            
            if not context["success"]:
                logger.error(f"❌ VPC v2: Failed to retrieve context: {context.get('error')}")
                return context
            
            logger.info(f"✅ VPC v2: Context retrieved successfully")
            
            # 3. Compare and update customer profile
            profile_update = await self._compare_and_update_customer_profile(
                vpc_v1_profile=context["vpc_v1_customer_profile"],
                analysis_results=context["analysis_report_chunks"],
                evidence_chunks=context["research_document_chunks"],
                persona_name=context.get("persona_name", "Target Persona")
            )
            
            if not profile_update["success"]:
                logger.error(f"❌ VPC v2: Customer profile update failed: {profile_update.get('error')}")
                return profile_update
            
            logger.info(f"✅ VPC v2: Customer profile refined (status: {profile_update['validation_status']})")
            
            # 4. Compose VPC v2 customer profile data with NEW 3-COLUMN STRUCTURE
            # IMPORTANT: This will replace any existing customer profile (regeneration support)
            vpc_v2_customer_profile = {
                "version": "v2",
                "persona_id": persona_id,
                "persona_name": context.get("persona_name", "Target Persona"),
                # NEW 3-COLUMN STRUCTURE (for frontend display)
                "original_customer_profile": profile_update.get("original_customer_profile", {}),
                "changes": profile_update.get("changes", {}),
                "final_customer_profile": profile_update.get("final_customer_profile", {}),
                "summary": profile_update.get("summary", {}),
                # BACKWARD COMPATIBILITY: Keep customer_profile for existing code
                "customer_profile": profile_update["updated_profile"],
                "validation_metadata": {
                    "validation_status": profile_update["validation_status"],
                    "confidence": profile_update["confidence"],
                    "change_summary": profile_update["updated_profile"].get("change_log", {}),
                    "generated_at": datetime.utcnow().isoformat()
                },
                "status": "customer_profile_completed"
            }
            
            # 5. Store in database (replaces existing customer profile if regenerating)
            storage_result = await self._store_vpc_v2(
                project_id=project_id,
                tenant_id=tenant_id,
                persona_id=persona_id,
                vpc_v2_data=vpc_v2_customer_profile
            )
            
            if not storage_result["success"]:
                logger.error(f"❌ VPC v2: Storage failed: {storage_result.get('error')}")
                return storage_result
            
            logger.info(f"✅ VPC v2 (Phase 1): Customer profile generation completed successfully")
            
            # 📊 WORKFLOW STATUS: Mark Customer Profile v2 as completed
            try:
                from .workflow_status_service import get_workflow_status_service, WorkflowStage
                workflow_service = get_workflow_status_service()
                workflow_service.set_stage_completed(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    stage=WorkflowStage.CUSTOMER_PROFILE_V2
                )
            except Exception as status_error:
                logger.warning(f"⚠️ VPC v2: Workflow status update failed (non-blocking): {status_error}")
            
            return {
                "success": True,
                "customer_profile": vpc_v2_customer_profile,
                "message": "VPC v2 customer profile generated successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2 (Phase 1): Customer profile generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Customer profile generation failed: {str(e)}"
            }
    
    async def generate_value_map_v2(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        PHASE 2: Generate VPC v2 value map candidates.
        
        This is the second step in VPC v2 workflow (after customer profile). It:
        1. Validates that customer profile exists
        2. Retrieves context
        3. Generates 5 value map candidates per category
        4. Stores value map candidates
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            persona_id: Optional persona ID for multi-persona projects
        
        Returns:
            Dict with success status, value_map_candidates data, and messages
        """
        try:
            logger.info(f"🎯 VPC v2 (Phase 2): Starting value map generation for project {project_id}, persona {persona_id}")
            
            # 1. Check that customer profile exists
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            vpc_v2_data = project.get("vpc_v2_data", {})
            logger.info(f"🔍 VPC v2 (Phase 2): vpc_v2_data keys: {list(vpc_v2_data.keys()) if isinstance(vpc_v2_data, dict) else 'not a dict'}")
            logger.info(f"🔍 VPC v2 (Phase 2): persona_id provided: {persona_id}")
            
            # UNIFIED STRUCTURE: Always look for data under persona_id key
            # Structure: {P1: {customer_profile: {...}}, P2: {...}} for both single and multi-persona
            # LEGACY SUPPORT: Also handle flat structure {customer_profile: {...}, ...}
            customer_profile_exists = False
            actual_persona_id = persona_id
            is_legacy_flat = False
            
            if isinstance(vpc_v2_data, dict):
                # First check: Is this legacy flat structure? (customer_profile at root level)
                if vpc_v2_data.get("customer_profile") and not any(
                    k.startswith("P") and isinstance(vpc_v2_data.get(k), dict) 
                    for k in vpc_v2_data.keys()
                ):
                    # LEGACY flat structure detected
                    customer_profile_exists = True
                    is_legacy_flat = True
                    actual_persona_id = persona_id  # Keep the persona_id for storage later
                    logger.info(f"🔍 VPC v2 (Phase 2): Found LEGACY flat structure with customer_profile")
                # Second check: Unified structure with persona_id key
                elif persona_id and vpc_v2_data.get(persona_id):
                    customer_profile_exists = vpc_v2_data[persona_id].get("customer_profile") is not None
                    logger.info(f"🔍 VPC v2 (Phase 2): Found persona {persona_id}, has customer_profile: {customer_profile_exists}")
                # Third check: No persona_id provided, find first persona key
                elif not persona_id:
                    # Find persona keys (exclude metadata keys)
                    persona_keys = [k for k in vpc_v2_data.keys() if k.startswith("P") and isinstance(vpc_v2_data.get(k), dict)]
                    if persona_keys:
                        actual_persona_id = persona_keys[0]
                        customer_profile_exists = vpc_v2_data[actual_persona_id].get("customer_profile") is not None
                        logger.info(f"🔍 VPC v2 (Phase 2): No persona_id provided, using first persona: {actual_persona_id}, has customer_profile: {customer_profile_exists}")
            
            if not customer_profile_exists:
                logger.error(f"❌ VPC v2 (Phase 2): Customer profile not found. vpc_v2_data structure: {vpc_v2_data}")
                return {
                    "success": False,
                    "error": "VPC v2 customer profile must be generated first (Phase 1)"
                }
            
            logger.info(f"✅ VPC v2: Customer profile exists, proceeding with value map generation")
            
            # 2. Retrieve context (use actual_persona_id which might be auto-detected)
            context = await self._retrieve_context_for_vpc_v2(
                project_id, tenant_id, actual_persona_id
            )
            
            if not context["success"]:
                logger.error(f"❌ VPC v2: Failed to retrieve context: {context.get('error')}")
                return context
            
            # Get the refined customer profile from vpc_v2_data
            if is_legacy_flat:
                # LEGACY: Flat structure - customer_profile at root level
                refined_customer_profile = vpc_v2_data["customer_profile"]
                logger.info(f"🔍 VPC v2 (Phase 2): Using legacy flat customer profile")
            elif actual_persona_id and vpc_v2_data.get(actual_persona_id):
                # UNIFIED: Persona-keyed structure
                refined_customer_profile = vpc_v2_data[actual_persona_id]["customer_profile"]
                logger.info(f"🔍 VPC v2 (Phase 2): Using customer profile from persona {actual_persona_id}")
            else:
                # Fallback - shouldn't reach here but just in case
                refined_customer_profile = vpc_v2_data.get("customer_profile", {})
                logger.warning(f"⚠️ VPC v2 (Phase 2): Using fallback customer profile retrieval")
            
            # 3. Generate value map CANDIDATES (5 options per category)
            value_map_result = await self._generate_value_map(
                updated_customer_profile=refined_customer_profile,
                analysis_results=context["analysis_report_chunks"],
                dual_context={
                    "pv_report": context["pv_report_context"],
                    "actionable_insights": context["actionable_insights_context"]
                },
                persona_name=context.get("persona_name", "Target Persona")
            )
            
            if not value_map_result["success"]:
                logger.error(f"❌ VPC v2: Value map candidates generation failed: {value_map_result.get('error')}")
                return value_map_result
            
            logger.info(f"✅ VPC v2: Value map candidates generated")
            
            # 4. Update VPC v2 data with value map candidates
            # IMPORTANT: Always migrate to UNIFIED structure (persona-keyed)
            if is_legacy_flat:
                # MIGRATE: Convert legacy flat structure to unified persona-keyed structure
                logger.info(f"🔄 VPC v2 (Phase 2): Migrating legacy flat structure to unified format for {actual_persona_id}")
                
                # Create new unified structure with existing data under persona key
                new_vpc_v2_data = {
                    actual_persona_id: {
                        "customer_profile": vpc_v2_data.get("customer_profile"),
                        "value_map_candidates": value_map_result["value_map_candidates"],
                        "value_map_selections": None,  # Reset selections on regeneration
                        "status": "value_map_candidates_generated",
                        "persona_id": actual_persona_id,
                        "persona_name": vpc_v2_data.get("persona_name"),
                        "version": vpc_v2_data.get("version", "v2"),
                        "validation_metadata": vpc_v2_data.get("validation_metadata"),
                    }
                }
                vpc_v2_data = new_vpc_v2_data
                logger.info(f"✅ VPC v2 (Phase 2): Migrated to unified structure with key {actual_persona_id}")
            elif actual_persona_id and vpc_v2_data.get(actual_persona_id):
                # UNIFIED: Update specific persona's value map
                vpc_v2_data[actual_persona_id]["value_map_candidates"] = value_map_result["value_map_candidates"]
                vpc_v2_data[actual_persona_id]["value_map_selections"] = None  # Reset selections on regeneration
                vpc_v2_data[actual_persona_id]["status"] = "value_map_candidates_generated"
                logger.info(f"🔍 VPC v2 (Phase 2): Replaced value map for persona {actual_persona_id}")
            else:
                # Fallback: Create new persona entry
                vpc_v2_data[actual_persona_id] = {
                    "value_map_candidates": value_map_result["value_map_candidates"],
                    "value_map_selections": None,
                    "status": "value_map_candidates_generated",
                    "persona_id": actual_persona_id,
                }
                logger.info(f"🔍 VPC v2 (Phase 2): Created new persona entry for {actual_persona_id}")
            
            # 5. Store in database
            # Use PostgreSQL's jsonb_set for atomic updates to prevent race conditions
            from src.mint.api.system.core.supabase_client import get_service_role_client
            import json
            supabase = get_service_role_client()
            
            if actual_persona_id and vpc_v2_data.get(actual_persona_id):
                # Multi-persona: Use PostgreSQL jsonb_set for atomic update
                # This prevents race conditions when multiple personas are generated in parallel
                logger.info(f"🔍 VPC v2: Using atomic JSONB update for persona {actual_persona_id}")
                
                # Execute atomic JSONB updates using PostgreSQL's jsonb_set function
                # This updates only the specific persona's fields without reading first
                try:
                    # Use Supabase RPC to execute raw SQL with jsonb_set
                    # Pass dict directly - Supabase client will convert to JSONB
                    update_result = supabase.client.rpc('update_persona_value_map', {
                        'p_project_id': project_id,
                        'p_tenant_id': tenant_id,
                        'p_persona_id': actual_persona_id,
                        'p_value_map_candidates': value_map_result["value_map_candidates"]
                    }).execute()
                    
                    logger.info(f"✅ VPC v2: Atomic update result: {bool(update_result.data)}")
                    
                except Exception as e:
                    # Fallback: If RPC doesn't exist, use sequential approach with retry logic
                    logger.warning(f"⚠️ VPC v2: RPC not available ({e}), using fallback with retry")
                    
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            # Read latest data
                            current_project = supabase.client.table('vmp_projects').select('vpc_v2_data').eq('id', project_id).eq('tenant_id', tenant_id).single().execute()
                            
                            if current_project.data:
                                current_vpc_v2 = current_project.data.get('vpc_v2_data', {})
                                
                                # Check if current data is legacy flat structure
                                is_current_legacy = current_vpc_v2.get("customer_profile") and not any(
                                    k.startswith("P") and isinstance(current_vpc_v2.get(k), dict) 
                                    for k in current_vpc_v2.keys()
                                )
                                
                                if is_current_legacy:
                                    # MIGRATE: Convert legacy to unified structure
                                    logger.info(f"🔄 VPC v2 Fallback: Migrating legacy structure to unified format")
                                    current_vpc_v2 = {
                                        actual_persona_id: {
                                            "customer_profile": current_vpc_v2.get("customer_profile"),
                                            "value_map_candidates": value_map_result["value_map_candidates"],
                                            "value_map_selections": None,
                                            "status": "value_map_candidates_generated",
                                            "persona_id": actual_persona_id,
                                            "persona_name": current_vpc_v2.get("persona_name"),
                                            "version": current_vpc_v2.get("version", "v2"),
                                            "validation_metadata": current_vpc_v2.get("validation_metadata"),
                                        }
                                    }
                                else:
                                    # Ensure persona exists
                                    if actual_persona_id not in current_vpc_v2:
                                        current_vpc_v2[actual_persona_id] = {}
                                    
                                    # Update fields
                                    current_vpc_v2[actual_persona_id]['value_map_candidates'] = value_map_result["value_map_candidates"]
                                    current_vpc_v2[actual_persona_id]['value_map_selections'] = None
                                    current_vpc_v2[actual_persona_id]['status'] = 'value_map_candidates_generated'
                                
                                # Write back
                                update_result = supabase.client.table('vmp_projects').update({
                                    'vpc_v2_data': current_vpc_v2,
                                    'updated_at': datetime.utcnow().isoformat()
                                }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
                                
                                if update_result.data:
                                    logger.info(f"✅ VPC v2: Fallback update succeeded on attempt {attempt + 1}")
                                    break
                            else:
                                logger.error(f"❌ VPC v2: Could not read project data on attempt {attempt + 1}")
                        except Exception as retry_error:
                            logger.warning(f"⚠️ VPC v2: Retry attempt {attempt + 1} failed: {retry_error}")
                            if attempt == max_retries - 1:
                                raise
                            import asyncio
                            await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            
            # If we migrated from legacy, also do a full update to ensure migration is persisted
            if is_legacy_flat:
                logger.info(f"🔍 VPC v2: Persisting legacy migration with full update")
                update_result = supabase.client.table('vmp_projects').update({
                    'vpc_v2_data': vpc_v2_data,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                logger.error(f"❌ VPC v2: Failed to update project in database")
                storage_result = {
                    "success": False,
                    "error": "Failed to store VPC v2 in database"
                }
            else:
                logger.info(f"✅ VPC v2: Successfully stored VPC v2 in database")
                storage_result = {
                    "success": True,
                    "message": "VPC v2 stored successfully"
                }
            
            if not storage_result["success"]:
                logger.error(f"❌ VPC v2: Storage failed: {storage_result.get('error')}")
                return storage_result
            
            logger.info(f"✅ VPC v2 (Phase 2): Value map generation completed successfully")
            
            return {
                "success": True,
                "value_map_candidates": value_map_result["value_map_candidates"],
                "message": "VPC v2 value map candidates generated successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2 (Phase 2): Value map generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Value map generation failed: {str(e)}"
            }
    
    async def _validate_prerequisites(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Validate that all prerequisites for VPC v2 generation are met.
        
        Requirements:
        1. Market research analysis must be completed
        2. Analysis report must be embedded
        3. VPC v1 customer profile must exist
        """
        try:
            missing = []
            
            # Get project data
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "ready": False,
                    "error": "Project not found",
                    "missing": ["project"]
                }
            
            # Check 1: Analysis completed
            analysis_data = project.get("analysis_data", {})
            analysis_status = analysis_data.get("stage", "not_started")
            
            if analysis_status != "analysis_completed":
                missing.append("completed_analysis")
                logger.warning(f"⚠️ VPC v2: Analysis not completed (status: {analysis_status})")
            
            # Check 2: Analysis report embedded
            all_chunks = await self.chunk_service.get_chunks_by_report_id(project_id)
            report_chunks = [
                chunk for chunk in all_chunks
                if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
            ]
            
            if not report_chunks:
                missing.append("embedded_analysis_report")
                logger.warning(f"⚠️ VPC v2: Analysis report not embedded")
            
            # Check 3: VPC v1 customer profile exists
            vpc_data = project.get("vpc_data", {})
            
            # Check for single persona structure
            has_single_profile = vpc_data.get("customer_profile") is not None
            
            # Check for multi-persona structure
            has_multi_profile = False
            if vpc_data.get("vpcs"):
                for persona_vpc in vpc_data["vpcs"].values():
                    if persona_vpc.get("customer_profile"):
                        has_multi_profile = True
                        break
            
            if not has_single_profile and not has_multi_profile:
                missing.append("vpc_v1_customer_profile")
                logger.warning(f"⚠️ VPC v2: VPC v1 customer profile not found")
            
            if missing:
                return {
                    "ready": False,
                    "error": f"Missing prerequisites: {', '.join(missing)}",
                    "missing": missing
                }
            
            return {
                "ready": True,
                "message": "All prerequisites met"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Prerequisite validation failed: {e}")
            return {
                "ready": False,
                "error": f"Validation failed: {str(e)}",
                "missing": ["validation_error"]
            }
    
    async def _retrieve_context_for_vpc_v2(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive context for VPC v2 generation.
        Uses the SAME pattern as market research chat service.
        
        Returns:
        - VPC v1 customer profile
        - Analysis report chunks (embedded)
        - Research document chunks (uploaded PDFs/CSVs)
        - Dual vector store context (PV report + Actionable Insights)
        - Persona information
        """
        try:
            logger.info(f"🔍 VPC v2: Retrieving context for project {project_id}, persona {persona_id}")
            
            # 1. Get VPC v1 Customer Profile
            vpc_v1_data = await self._get_vpc_v1_customer_profile(
                project_id, tenant_id, persona_id
            )
            
            if not vpc_v1_data["success"]:
                return vpc_v1_data
            
            logger.info(f"✅ VPC v2: Retrieved VPC v1 customer profile")
            
            # 2. Get Market Research Analysis Report chunks (embedded) - REDUCED for token optimization
            analysis_report_chunks = await self._retrieve_analysis_report_chunks(
                project_id, tenant_id,
                query="customer profile validation pain gains jobs-to-be-done value proposition",
                max_chunks=5  # Reduced from 20 to 5
            )
            
            logger.info(f"✅ VPC v2: Retrieved {len(analysis_report_chunks)} analysis report chunks")
            
            # 3. Get Uploaded Research Documents chunks (for evidence) - REDUCED for token optimization
            research_document_chunks = await self._retrieve_research_document_chunks(
                project_id, tenant_id,
                query="customer needs problems solutions benefits",
                max_chunks=5  # Reduced from 15 to 5
            )
            
            logger.info(f"✅ VPC v2: Retrieved {len(research_document_chunks)} research document chunks")
            
            # 4. Get Dual Vector Store Context (PV Report + Actionable Insights) - REDUCED for token optimization
            dual_context = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query="value proposition solution design customer needs",
                max_results_per_store=3  # Reduced from 10 to 3
            )
            
            logger.info(f"✅ VPC v2: Retrieved dual vector store context")
            
            # 5. Get persona information
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            personas = project.get("personas", [])
            
            persona_name = "Target Persona"
            if persona_id and personas:
                for persona in personas:
                    if persona.get("id") == persona_id:
                        persona_name = persona.get("name", "Target Persona")
                        break
            
            return {
                "success": True,
                "vpc_v1_customer_profile": vpc_v1_data["customer_profile"],
                "analysis_report_chunks": analysis_report_chunks,
                "research_document_chunks": research_document_chunks,
                "pv_report_context": dual_context.get("pv_report_context", []),
                "actionable_insights_context": dual_context.get("actionable_insights_context", []),
                "persona_name": persona_name,
                "personas": personas
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Context retrieval failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Context retrieval failed: {str(e)}"
            }
    
    async def _get_vpc_v1_customer_profile(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get VPC v1 customer profile from vpc_data.
        Handles both single persona and multi-persona structures.
        """
        try:
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            vpc_data = project.get("vpc_data", {})
            logger.info(f"🔍 VPC v2: vpc_data keys: {list(vpc_data.keys()) if isinstance(vpc_data, dict) else 'not a dict'}")
            
            # Check if multi-persona project (has 'vpcs' key)
            if vpc_data.get("vpcs"):
                vpcs = vpc_data["vpcs"]
                logger.info(f"🔍 VPC v2: Multi-persona project detected, vpcs keys: {list(vpcs.keys())}")
                
                # If persona_id provided, get that specific persona
                if persona_id:
                    logger.info(f"🔍 VPC v2: Looking for persona_id '{persona_id}' (type: {type(persona_id)})")
                    logger.info(f"🔍 VPC v2: Available persona keys: {list(vpcs.keys())} (types: {[type(k) for k in vpcs.keys()]})")
                    
                    persona_vpc = vpcs.get(persona_id)
                    if persona_vpc:
                        logger.info(f"🔍 VPC v2: Found persona_vpc for {persona_id}, keys: {list(persona_vpc.keys())}")
                        if persona_vpc.get("customer_profile"):
                            logger.info(f"✅ VPC v2: Found multi-persona customer profile for {persona_id}")
                            return {
                                "success": True,
                                "customer_profile": persona_vpc["customer_profile"]
                            }
                        else:
                            logger.warning(f"⚠️ VPC v2: Persona {persona_id} found but has no customer_profile")
                    else:
                        logger.warning(f"⚠️ VPC v2: Persona {persona_id} not found in vpcs")
                else:
                    # No persona_id provided, try to get first persona
                    logger.info(f"🔍 VPC v2: No persona_id provided, using first persona")
                    first_persona_id = list(vpcs.keys())[0] if vpcs else None
                    if first_persona_id:
                        persona_vpc = vpcs[first_persona_id]
                        if persona_vpc.get("customer_profile"):
                            logger.info(f"✅ VPC v2: Using first persona {first_persona_id} customer profile")
                            return {
                                "success": True,
                                "customer_profile": persona_vpc["customer_profile"]
                            }
                        else:
                            logger.warning(f"⚠️ VPC v2: First persona {first_persona_id} has no customer_profile")
            
            # Single persona structure: vpc_data.customer_profile
            if vpc_data.get("customer_profile"):
                logger.info(f"✅ VPC v2: Found single persona customer profile")
                return {
                    "success": True,
                    "customer_profile": vpc_data["customer_profile"]
                }
            
            logger.error(f"❌ VPC v2: No customer profile found. vpc_data structure: {vpc_data}")
            return {
                "success": False,
                "error": "VPC v1 customer profile not found. Please complete VPC v1 first."
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Failed to get VPC v1 customer profile: {e}")
            return {
                "success": False,
                "error": f"Failed to get customer profile: {str(e)}"
            }
    
    async def _retrieve_analysis_report_chunks(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        max_chunks: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from analysis report using RAG.
        SAME pattern as MarketResearchChatService._retrieve_report_chunks()
        """
        try:
            # Load all chunks and filter for analysis_report
            all_chunks = await self.chunk_service.get_chunks_by_report_id(project_id)
            
            report_chunks = [
                chunk for chunk in all_chunks
                if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
            ]
            
            if not report_chunks:
                logger.warning(f"⚠️ VPC v2: No analysis report chunks found")
                return []
            
            # Generate embedding for query
            query_embeddings = await self.embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                logger.error("❌ VPC v2: Failed to generate query embedding")
                return []
            
            # Calculate similarity scores
            import numpy as np
            scored_chunks = []
            
            for chunk_data in report_chunks:
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                elif isinstance(raw_embedding, list):
                    chunk_embedding = raw_embedding
                else:
                    continue
                
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        'content': chunk_data.get('content', ''),
                        'similarity': float(similarity),
                        'metadata': chunk_data.get('metadata', {})
                    })
                except Exception as e:
                    logger.warning(f"⚠️ VPC v2: Failed to calculate similarity: {e}")
                    continue
            
            # Sort by similarity and return top chunks
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            return scored_chunks[:max_chunks]
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Error retrieving analysis report chunks: {e}")
            return []
    
    async def _retrieve_research_document_chunks(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        max_chunks: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from uploaded research documents.
        SAME pattern as MarketResearchChatService._retrieve_research_chunks()
        """
        try:
            # Load all chunks and filter for research documents (csv/pdf)
            all_chunks = await self.chunk_service.get_chunks_by_report_id(project_id)
            
            research_chunks = [
                chunk for chunk in all_chunks
                if chunk.get('metadata', {}).get('source_type') in ['csv', 'pdf']
            ]
            
            if not research_chunks:
                logger.warning(f"⚠️ VPC v2: No research document chunks found")
                return []
            
            # Generate embedding for query
            query_embeddings = await self.embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                logger.error("❌ VPC v2: Failed to generate query embedding")
                return []
            
            # Calculate similarity scores
            import numpy as np
            scored_chunks = []
            
            for chunk_data in research_chunks:
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                elif isinstance(raw_embedding, list):
                    chunk_embedding = raw_embedding
                else:
                    continue
                
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        'content': chunk_data.get('content', ''),
                        'similarity': float(similarity),
                        'metadata': chunk_data.get('metadata', {})
                    })
                except Exception as e:
                    logger.warning(f"⚠️ VPC v2: Failed to calculate similarity: {e}")
                    continue
            
            # Sort by similarity and return top chunks
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            return scored_chunks[:max_chunks]
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Error retrieving research document chunks: {e}")
            return []
    
    async def _compare_and_update_customer_profile(
        self,
        vpc_v1_profile: Dict[str, Any],
        analysis_results: List[Dict[str, Any]],
        evidence_chunks: List[Dict[str, Any]],
        persona_name: str
    ) -> Dict[str, Any]:
        """
        Refine VPC v1 customer profile with market research insights.
        
        NEW DATA STRUCTURE (3-Column Layout for Frontend):
        - original_customer_profile: Complete VPC v1 data (left column)
        - changes: Only what changed with explanations (middle column)
        - final_customer_profile: Merged result with status flags (right column)
        
        Returns:
        - success: bool
        - original_customer_profile: Preserved VPC v1 data
        - changes: Structured change tracking with explanations
        - final_customer_profile: Merged profile with status flags
        - summary: Statistics and validation summary
        - validation_status: Always "REFINED"
        - confidence: LLM confidence score
        """
        try:
            logger.info(f"🔍 VPC v2: Refining customer profile for {persona_name} with research insights")
            
            # STEP 1: Preserve original customer profile (deep copy)
            import copy
            original_customer_profile = {
                "jobs_to_be_done": copy.deepcopy(vpc_v1_profile.get('jobs_to_be_done', [])),
                "pains": copy.deepcopy(vpc_v1_profile.get('pains', [])),
                "gains": copy.deepcopy(vpc_v1_profile.get('gains', []))
            }
            
            # Format context for LLM
            analysis_context = self._format_analysis_results(analysis_results)
            evidence_context = self._format_evidence_chunks(evidence_chunks)
            
            # Build refinement prompt (NO validation/invalidation - user has already decided to proceed)
            prompt = f"""You are refining a Value Proposition Canvas customer profile for {persona_name} based on MARKET RESEARCH ANALYSIS data.

IMPORTANT CONTEXT: The user has already reviewed the market research analysis and decided to proceed with VPC v2. Your job is to REFINE the customer profile with research insights, NOT to validate or invalidate the idea.

ORIGINAL CUSTOMER PROFILE (VPC v1):

Jobs-to-be-Done:
{json.dumps(vpc_v1_profile.get('jobs_to_be_done', []), indent=2)}

Pains:
{json.dumps(vpc_v1_profile.get('pains', []), indent=2)}

Gains:
{json.dumps(vpc_v1_profile.get('gains', []), indent=2)}

MARKET RESEARCH ANALYSIS DATA (PRIMARY EVIDENCE SOURCE):
{analysis_context}

FIELD RESEARCH DATA (SUPPORTING EVIDENCE):
{evidence_context}

TASK:
1. Review the original customer profile items EXACTLY as written
2. ONLY modify items if there is CONCRETE EVIDENCE from the market research analysis data above
3. If NO evidence exists for an item, transfer it EXACTLY as-is to the final output (mark as "validated")
4. For any modifications, you MUST provide:
   - The EXACT original text (copy word-for-word)
   - The enhanced text with research-backed details
   - A clear explanation citing SPECIFIC data/quotes from the research
   - A direct evidence citation from the market research analysis

=== STRICT RULES (MUST FOLLOW) ===

1. **NO PARAPHRASING**: Do NOT rephrase, shorten, or reword original text unless you have CONCRETE EVIDENCE to add.
   - WRONG: Changing "Farmers need access to fresh produce" to "Farmers require fresh produce access" (just rewording)
   - RIGHT: Keep original text exactly OR add evidence like "Farmers need access to fresh produce (78% of respondents cited this as critical)"

2. **EVIDENCE-ONLY CHANGES**: Every change MUST cite specific market research data:
   - WRONG: "Enhanced for clarity" or "Improved wording"
   - RIGHT: "Added quantitative data: Survey shows 65% of users prioritize X" or "Research interview #3 states: 'direct quote'"

3. **PRESERVE WORD COUNT**: Do NOT reduce the length of original text. Only ADD information.
   - If original is 20 words, enhanced version should be 20+ words (with evidence added)

4. **EXACT TRANSFER FOR NO-EVIDENCE ITEMS**: If market research does NOT provide new insights for an item:
   - Mark it as "validated" 
   - Copy the EXACT original text (word-for-word, character-for-character)
   - Copy the EXACT original label (word-for-word, do NOT shorten or modify)
   - Do NOT make ANY modifications to text OR label

5. **EVIDENCE SOURCE**: All citations MUST come from the MARKET RESEARCH ANALYSIS DATA provided above.
   - Do NOT cite PV reports or hypothetical data
   - Do NOT make up statistics or quotes
   - If you cannot find evidence in the provided data, keep the item as-is

6. **LIMIT: EXACTLY 3 items per section** (jobs_to_be_done, pains, gains)
   - If original has more than 3, select the 3 most research-supported ones
   - If original has fewer than 3, ADD NEW items ONLY if research data supports them
   - validated + updated + new = EXACTLY 3 per section

OUTPUT FORMAT (JSON):
{{
    "overall_confidence": 0.85,
    "jobs_to_be_done": {{
        "validated": [
            {{
                "id": "jtbd-1",
                "text": "EXACT COPY of original text - word for word, no modifications",
                "label": "EXACT COPY of original label - DO NOT shorten or modify (e.g., if original is 'Dual-documentation and workflow resistance', keep it exactly, NOT 'Dual documentation')"
            }}
        ],
        "updated": [
            {{
                "id": "jtbd-2",
                "original_text": "EXACT COPY of original text - word for word",
                "updated_text": "Original text PLUS research evidence appended (e.g., 'Original text here, supported by 78% of survey respondents who stated...')",
                "label": "Short 3-5 word label for the updated text",
                "explanation": "MUST cite specific data: 'Added survey finding: 78% of respondents in Question 5 prioritized cost' or 'Added interview quote from Participant 3'",
                "evidence_citation": "DIRECT quote or specific data point from the MARKET RESEARCH ANALYSIS DATA section above"
            }}
        ],
        "removed": [
            {{
                "id": "jtbd-3",
                "original_text": "EXACT COPY of the removed item's original text",
                "explanation": "MUST cite contradicting evidence: 'Research data shows only 3% expressed this need (Question 7 results)'"
            }}
        ],
        "new": [
            {{
                "id": "new-jtbd-1",
                "text": "New insight discovered from research with evidence",
                "label": "Short 3-5 word label",
                "explanation": "MUST explain research source: 'Discovered from interview analysis - 5 of 8 participants mentioned this'",
                "evidence_citation": "DIRECT quote or specific data point from research"
            }}
        ]
    }},
    "pains": {{
        "validated": [...],
        "updated": [...],
        "removed": [...],
        "new": [...]
    }},
    "gains": {{
        "validated": [...],
        "updated": [...],
        "removed": [...],
        "new": [...]
    }},
    "validation_summary": "Overall assessment citing key research findings that informed the refinements"
}}

REMINDER: 
- "validated" items = EXACT original text (no changes whatsoever)
- "updated" items = Original text + NEW research evidence ADDED (never shortened or paraphrased)
- "removed" items = MUST have research evidence contradicting it
- "new" items = MUST have research evidence supporting it
- If you cannot cite specific evidence from the MARKET RESEARCH ANALYSIS DATA above, mark the item as "validated" and keep it EXACTLY as-is."""

            # Create monitoring context for AI usage tracking
            from monitor.tokens.models import AIUsageContext
            monitoring_context = AIUsageContext(
                user_id=self._user_id if hasattr(self, '_user_id') else None,
                tenant_id=self._tenant_id if hasattr(self, '_tenant_id') else None,
                project_id=self._project_id if hasattr(self, '_project_id') else None,
                feature_id=VPC_V2_CUSTOMER_PROFILE_FEATURE_ID,
                workflow_name="vpc_v2_workflow",
                step_name="customer_profile_refinement",
                environment="prod"
            )
            
            # Generate structured output using AI service (uses gpt-5-mini)
            system_message = """You are an expert market research analyst specializing in evidence-based customer profile refinement.

CRITICAL INSTRUCTIONS:
1. You ONLY make changes that are backed by SPECIFIC evidence from the provided market research data.
2. If there is no evidence to support a change, you MUST keep the original text EXACTLY as-is (mark as "validated").
3. NEVER paraphrase, shorten, or reword text without adding new research evidence.
4. All evidence citations MUST come from the MARKET RESEARCH ANALYSIS DATA - never from PV reports or hypothetical data.
5. When you update text, you APPEND research evidence to the original text - you do NOT replace or shorten it.

Your goal is ENHANCEMENT with evidence, not editing for style or brevity."""

            response = await self.ai_service.generate_analysis_response(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=16000,  # gpt-5-mini needs large token budget
                monitoring_context=monitoring_context
            )
            
            # Extract content from response
            response_content = response.get("content", response) if isinstance(response, dict) else response
            
            # Parse JSON response
            try:
                comparison_result = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_content, re.DOTALL)
                if json_match:
                    comparison_result = json.loads(json_match.group(1))
                else:
                    logger.error(f"❌ VPC v2: Failed to parse LLM response as JSON")
                    return {
                        "success": False,
                        "error": "Failed to parse comparison results"
                    }
            
            # STEP 2: POST-PROCESS LLM RESULT - Validate and enforce data structure consistency
            # This ensures all changes have proper evidence and structure
            def validate_and_fix_llm_result(llm_result: Dict[str, Any], original_profile: Dict[str, Any]) -> Dict[str, Any]:
                """
                Validate LLM output and enforce strict rules:
                1. Updated items MUST have evidence_citation - if missing, move to validated
                2. All items must have consistent data structure
                3. Detect paraphrasing without evidence and revert to original
                """
                fixed_result = {}
                
                for category in ["jobs_to_be_done", "pains", "gains"]:
                    category_data = llm_result.get(category, {})
                    original_items = original_profile.get(category, [])
                    
                    # Build lookup for original items by ID
                    original_lookup = {item.get("id"): item for item in original_items}
                    
                    validated = list(category_data.get("validated", []))
                    updated = []
                    removed = list(category_data.get("removed", []))
                    new = list(category_data.get("new", []))
                    
                    # ENFORCE: For all validated items, use EXACT original text and label from V1
                    enforced_validated = []
                    for item in validated:
                        item_id = item.get("id")
                        original_item = original_lookup.get(item_id)
                        if original_item:
                            # Use EXACT original text and label - ignore what LLM returned
                            enforced_validated.append({
                                "id": item_id,
                                "text": original_item.get("text", original_item.get("description", "")),
                                "label": original_item.get("label", f"{category} item")  # EXACT original label
                            })
                            logger.info(f"✅ VPC v2: Preserved exact original text and label for validated item {item_id}")
                        else:
                            # Fallback if original not found
                            enforced_validated.append(item)
                    validated = enforced_validated
                    
                    # Validate each "updated" item - must have evidence_citation
                    for item in category_data.get("updated", []):
                        item_id = item.get("id")
                        evidence = item.get("evidence_citation", item.get("evidence", ""))
                        original_text = item.get("original_text", item.get("original", ""))
                        updated_text = item.get("updated_text", item.get("updated", ""))
                        
                        # Check if evidence is missing or generic
                        has_valid_evidence = bool(evidence and len(evidence.strip()) > 10 and 
                                                   evidence.lower() not in ["none", "n/a", "no evidence", "enhanced for clarity"])
                        
                        # Check if this is just paraphrasing (updated text is similar length or shorter)
                        is_paraphrasing = len(updated_text) <= len(original_text) * 1.1 if original_text and updated_text else False
                        
                        if has_valid_evidence and not is_paraphrasing:
                            # Valid update with evidence - keep it
                            updated.append(item)
                            logger.info(f"✅ VPC v2: Valid update for {item_id} - has evidence and adds content")
                        else:
                            # Invalid update - revert to validated with EXACT original text AND label
                            original_item = original_lookup.get(item_id)
                            if original_item:
                                validated.append({
                                    "id": item_id,
                                    "text": original_item.get("text", original_item.get("description", "")),
                                    "label": original_item.get("label", f"{category} item")  # EXACT original label
                                })
                                if not has_valid_evidence:
                                    logger.warning(f"⚠️ VPC v2: Reverted {item_id} to validated - missing valid evidence citation")
                                if is_paraphrasing:
                                    logger.warning(f"⚠️ VPC v2: Reverted {item_id} to validated - detected paraphrasing without content addition")
                    
                    # Validate "removed" items - must have evidence for removal
                    valid_removed = []
                    for item in removed:
                        evidence = item.get("explanation", "")
                        has_valid_evidence = bool(evidence and len(evidence.strip()) > 20 and 
                                                   any(word in evidence.lower() for word in ["research", "survey", "interview", "data", "%", "respondent"]))
                        if has_valid_evidence:
                            valid_removed.append(item)
                        else:
                            # Can't remove without evidence - add back to validated
                            item_id = item.get("id")
                            original_item = original_lookup.get(item_id)
                            if original_item:
                                validated.append({
                                    "id": item_id,
                                    "text": original_item.get("text", original_item.get("description", "")),
                                    "label": original_item.get("label", f"{category} item")
                                })
                                logger.warning(f"⚠️ VPC v2: Reverted removal of {item_id} - no valid evidence for removal")
                    
                    # Validate "new" items - must have evidence
                    valid_new = []
                    for item in new:
                        evidence = item.get("evidence_citation", item.get("evidence", ""))
                        has_valid_evidence = bool(evidence and len(evidence.strip()) > 10)
                        if has_valid_evidence:
                            valid_new.append(item)
                        else:
                            logger.warning(f"⚠️ VPC v2: Discarded new item {item.get('id')} - no valid evidence")
                    
                    # CRITICAL: Ensure ALL original items are accounted for
                    # If an item is not in validated, updated, or removed, add it to validated
                    validated_ids = {item.get("id") for item in validated}
                    updated_ids = {item.get("id") for item in updated}
                    removed_ids = {item.get("id") for item in valid_removed}
                    accounted_ids = validated_ids | updated_ids | removed_ids
                    
                    for original_item in original_items:
                        item_id = original_item.get("id")
                        if item_id and item_id not in accounted_ids:
                            # Missing item - add to validated with EXACT original content
                            validated.append({
                                "id": item_id,
                                "text": original_item.get("text", original_item.get("description", "")),
                                "label": original_item.get("label", f"{category} item")
                            })
                            logger.warning(f"⚠️ VPC v2: Item {item_id} was missing from LLM output - auto-added to validated with original content")
                    
                    fixed_result[category] = {
                        "validated": validated,
                        "updated": updated,
                        "removed": valid_removed,
                        "new": valid_new
                    }
                
                # Preserve other fields from LLM result
                fixed_result["overall_confidence"] = llm_result.get("overall_confidence", 0.85)
                fixed_result["validation_summary"] = llm_result.get("validation_summary", "")
                
                return fixed_result
            
            # Apply validation and fix any issues
            comparison_result = validate_and_fix_llm_result(comparison_result, original_customer_profile)
            logger.info(f"✅ VPC v2: Post-processing complete - validated LLM output for data structure consistency")
            
            # STEP 3: Build changes structure (middle column - only what changed)
            changes = {
                "jobs_to_be_done": {
                    "validated_ids": [item.get("id") for item in comparison_result["jobs_to_be_done"].get("validated", [])],
                    "updated": [
                        {
                            "id": item.get("id"),
                            "original_text": item.get("original_text", item.get("original", "")),
                            "updated_text": item.get("updated_text", item.get("updated", "")),
                            "explanation": item.get("explanation", item.get("reason", "Enhanced with research insights")),
                            "evidence_citation": item.get("evidence_citation", item.get("evidence", ""))
                        }
                        for item in comparison_result["jobs_to_be_done"].get("updated", [])
                    ],
                    "removed": [
                        {
                            "id": item.get("id"),
                            "original_text": item.get("original_text", item.get("text", "")),
                            "explanation": item.get("explanation", item.get("reason", "Removed based on research"))
                        }
                        for item in comparison_result["jobs_to_be_done"].get("removed", [])
                    ]
                },
                "pains": {
                    "validated_ids": [item.get("id") for item in comparison_result["pains"].get("validated", [])],
                    "updated": [
                        {
                            "id": item.get("id"),
                            "original_text": item.get("original_text", item.get("original", "")),
                            "updated_text": item.get("updated_text", item.get("updated", "")),
                            "explanation": item.get("explanation", item.get("reason", "Enhanced with research insights")),
                            "evidence_citation": item.get("evidence_citation", item.get("evidence", ""))
                        }
                        for item in comparison_result["pains"].get("updated", [])
                    ],
                    "removed": [
                        {
                            "id": item.get("id"),
                            "original_text": item.get("original_text", item.get("text", "")),
                            "explanation": item.get("explanation", item.get("reason", "Removed based on research"))
                        }
                        for item in comparison_result["pains"].get("removed", [])
                    ]
                },
                "gains": {
                    "validated_ids": [item.get("id") for item in comparison_result["gains"].get("validated", [])],
                    "updated": [
                        {
                            "id": item.get("id"),
                            "original_text": item.get("original_text", item.get("original", "")),
                            "updated_text": item.get("updated_text", item.get("updated", "")),
                            "explanation": item.get("explanation", item.get("reason", "Enhanced with research insights")),
                            "evidence_citation": item.get("evidence_citation", item.get("evidence", ""))
                        }
                        for item in comparison_result["gains"].get("updated", [])
                    ],
                    "removed": [
                        {
                            "id": item.get("id"),
                            "original_text": item.get("original_text", item.get("text", "")),
                            "explanation": item.get("explanation", item.get("reason", "Removed based on research"))
                        }
                        for item in comparison_result["gains"].get("removed", [])
                    ]
                }
            }
            
            # STEP 3: Build final customer profile with status flags (right column)
            def build_final_profile_items(validated_items, updated_items, removed_items, new_items, original_items, item_type):
                """Build final profile items with status flags for each item"""
                result = []
                
                # Get IDs of updated and removed items
                updated_ids = {item.get("id") for item in updated_items}
                removed_ids = {item.get("id") for item in removed_items}
                
                # Add validated items (status = "validated")
                for item in validated_items:
                    item_id = item.get("id")
                    if item_id not in updated_ids and item_id not in removed_ids:
                        # Find original item to preserve full structure
                        original_item = next(
                            (o for o in original_items if o.get("id") == item_id), 
                            None
                        )
                        result.append({
                            "id": item_id,
                            "type": item_type,
                            "status": "validated",
                            "label": item.get("label") or (original_item.get("label") if original_item else None) or f"{item_type.upper()} Item",
                            "text": item.get("text") or (original_item.get("text") if original_item else ""),
                            "description": item.get("text") or (original_item.get("description") if original_item else ""),
                            "evidence": original_item.get("evidence", []) if original_item else [],
                            "confidence": original_item.get("confidence", 0.85) if original_item else 0.85,
                            "persona_id": original_item.get("persona_id") if original_item else None
                        })
                
                # Add updated items (status = "updated")
                for item in updated_items:
                    item_id = item.get("id")
                    # Find original item to preserve metadata
                    original_item = next(
                        (o for o in original_items if o.get("id") == item_id), 
                        None
                    )
                    updated_text = item.get("updated_text", item.get("updated", ""))
                    result.append({
                        "id": item_id,
                        "type": item_type,
                        "status": "updated",
                        "label": item.get("label") or (original_item.get("label") if original_item else None) or f"Updated {item_type.upper()}",
                        "text": updated_text,
                        "description": updated_text,
                        "original_text": item.get("original_text", item.get("original", "")),
                        "change_explanation": item.get("explanation", item.get("reason", "Enhanced with research insights")),
                        "evidence_citation": item.get("evidence_citation", item.get("evidence", "")),
                        "evidence": original_item.get("evidence", []) if original_item else [],
                        "confidence": 0.90,  # Higher confidence for updated items
                        "persona_id": original_item.get("persona_id") if original_item else None
                    })
                
                # Add new items (status = "new") - items discovered from research
                for item in new_items:
                    item_id = item.get("id")
                    item_text = item.get("text", "")
                    result.append({
                        "id": item_id,
                        "type": item_type,
                        "status": "new",
                        "label": item.get("label") or f"New {item_type.upper()}",
                        "text": item_text,
                        "description": item_text,
                        "change_explanation": item.get("explanation", "Discovered from market research"),
                        "evidence_citation": item.get("evidence_citation", item.get("evidence", "")),
                        "evidence": [],
                        "confidence": 0.85,
                        "persona_id": None
                    })
                
                return result
            
            # ENFORCE EXACTLY 3 ITEMS PER SECTION
            ITEMS_PER_SECTION = 3
            
            final_customer_profile = {
                "jobs_to_be_done": build_final_profile_items(
                    comparison_result["jobs_to_be_done"].get("validated", []),
                    comparison_result["jobs_to_be_done"].get("updated", []),
                    comparison_result["jobs_to_be_done"].get("removed", []),
                    comparison_result["jobs_to_be_done"].get("new", []),
                    original_customer_profile["jobs_to_be_done"],
                    "jtbd"
                )[:ITEMS_PER_SECTION],  # Enforce exactly 3 items
                "pains": build_final_profile_items(
                    comparison_result["pains"].get("validated", []),
                    comparison_result["pains"].get("updated", []),
                    comparison_result["pains"].get("removed", []),
                    comparison_result["pains"].get("new", []),
                    original_customer_profile["pains"],
                    "pain"
                )[:ITEMS_PER_SECTION],  # Enforce exactly 3 items
                "gains": build_final_profile_items(
                    comparison_result["gains"].get("validated", []),
                    comparison_result["gains"].get("updated", []),
                    comparison_result["gains"].get("removed", []),
                    comparison_result["gains"].get("new", []),
                    original_customer_profile["gains"],
                    "gain"
                )[:ITEMS_PER_SECTION]  # Enforce exactly 3 items
            }
            
            logger.info(f"📊 VPC v2: Final profile items - JTBD: {len(final_customer_profile['jobs_to_be_done'])}, Pains: {len(final_customer_profile['pains'])}, Gains: {len(final_customer_profile['gains'])} (required: {ITEMS_PER_SECTION} per section)")
            
            # STEP 4: Calculate summary statistics
            total_original_items = (
                len(original_customer_profile.get('jobs_to_be_done', [])) +
                len(original_customer_profile.get('pains', [])) +
                len(original_customer_profile.get('gains', []))
            )
            
            items_validated = (
                len(changes["jobs_to_be_done"]["validated_ids"]) +
                len(changes["pains"]["validated_ids"]) +
                len(changes["gains"]["validated_ids"])
            )
            
            items_updated = (
                len(changes["jobs_to_be_done"]["updated"]) +
                len(changes["pains"]["updated"]) +
                len(changes["gains"]["updated"])
            )
            
            items_removed = (
                len(changes["jobs_to_be_done"]["removed"]) +
                len(changes["pains"]["removed"]) +
                len(changes["gains"]["removed"])
            )
            
            change_percentage = ((items_updated + items_removed) / total_original_items * 100) if total_original_items > 0 else 0
            
            summary = {
                "total_original_items": total_original_items,
                "items_validated": items_validated,
                "items_updated": items_updated,
                "items_removed": items_removed,
                "items_in_final": items_validated + items_updated,
                "change_percentage": round(change_percentage, 1),
                "overall_confidence": comparison_result.get("overall_confidence", 0.85),
                "validation_summary": comparison_result.get("validation_summary", comparison_result.get("summary", "Customer profile refined with market research insights"))
            }
            
            logger.info(f"📊 VPC v2: Summary - Validated: {items_validated}, Updated: {items_updated}, Removed: {items_removed} (Change: {change_percentage:.1f}%)")
            
            # STEP 5: Build complete output structure (3-column layout)
            complete_profile = {
                "original_customer_profile": original_customer_profile,
                "changes": changes,
                "final_customer_profile": final_customer_profile,
                "summary": summary,
                # BACKWARD COMPATIBILITY: Keep the old structure for existing code
                "jobs_to_be_done": final_customer_profile["jobs_to_be_done"],
                "pains": final_customer_profile["pains"],
                "gains": final_customer_profile["gains"],
                "change_log": {
                    "jtbd_changes": changes["jobs_to_be_done"]["updated"],
                    "pain_changes": changes["pains"]["updated"],
                    "gain_changes": changes["gains"]["updated"],
                    "removed_items": {
                        "jtbd": changes["jobs_to_be_done"]["removed"],
                        "pains": changes["pains"]["removed"],
                        "gains": changes["gains"]["removed"]
                    },
                    "change_percentage": change_percentage
                },
                "validation_summary": summary["validation_summary"]
            }
            
            logger.info(f"✅ VPC v2: Customer profile refined successfully with new 3-column structure")
            
            return {
                "success": True,
                "updated_profile": complete_profile,
                "original_customer_profile": original_customer_profile,
                "changes": changes,
                "final_customer_profile": final_customer_profile,
                "summary": summary,
                "validation_status": "REFINED",  # Always REFINED, never INVALIDATED
                "confidence": comparison_result.get("overall_confidence", 0.8)
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Customer profile comparison failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Customer profile comparison failed: {str(e)}"
            }
    
    def _format_analysis_results(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Format analysis report chunks for LLM context (optimized for token usage)."""
        if not analysis_results:
            return "No analysis results available."
        
        formatted = []
        for i, chunk in enumerate(analysis_results[:5], 1):  # Limit to top 5 most relevant
            content = chunk.get('content', '')
            # Truncate long content to first 500 chars
            truncated_content = content[:500] + "..." if len(content) > 500 else content
            similarity = chunk.get('similarity', 0)
            formatted.append(f"[{i}] ({similarity:.2f}): {truncated_content}")
        
        return "\n".join(formatted)
    
    def _format_evidence_chunks(self, evidence_chunks: List[Dict[str, Any]]) -> str:
        """Format research document chunks for LLM context (optimized for token usage)."""
        if not evidence_chunks:
            return "No research evidence available."
        
        formatted = []
        for i, chunk in enumerate(evidence_chunks[:5], 1):  # Limit to top 5 most relevant
            content = chunk.get('content', '')
            # Truncate long content to first 400 chars
            truncated_content = content[:400] + "..." if len(content) > 400 else content
            similarity = chunk.get('similarity', 0)
            metadata = chunk.get('metadata', {})
            source = metadata.get('source_file', 'Unknown')[:30]  # Truncate source name
            formatted.append(f"[{i}] {source} ({similarity:.2f}): {truncated_content}")
        
        return "\n".join(formatted)
    
    async def _generate_value_map(
        self,
        updated_customer_profile: Dict[str, Any],
        analysis_results: List[Dict[str, Any]],
        dual_context: Dict[str, Any],
        persona_name: str
    ) -> Dict[str, Any]:
        """
        Generate Value Map based on validated customer profile.
        This is the FIRST TIME value map is created (not in VPC v1).
        """
        try:
            logger.info(f"🔍 VPC v2: Generating value map for {persona_name}")
            
            # Format contexts
            analysis_context = self._format_analysis_results(analysis_results)
            pv_context = self._format_dual_context_chunks(dual_context.get("pv_report", []))
            insights_context = self._format_dual_context_chunks(dual_context.get("actionable_insights", []))
            
            # Build value map CANDIDATES generation prompt (5 options per category)
            prompt = f"""You are designing Value Map candidates for {persona_name} based on validated market research.

VALIDATED CUSTOMER PROFILE:

Jobs-to-be-Done:
{json.dumps(updated_customer_profile.get('jobs_to_be_done', []), indent=2)}

Pains:
{json.dumps(updated_customer_profile.get('pains', []), indent=2)}

Gains:
{json.dumps(updated_customer_profile.get('gains', []), indent=2)}

MARKET RESEARCH INSIGHTS:
{analysis_context}

PROBLEM VALIDATION CONTEXT:
{pv_context}

ACTIONABLE INSIGHTS:
{insights_context}

TASK:
Generate Value Map CANDIDATES with THREE components. For each component, provide EXACTLY 5 OPTIONS (user will select 3).

1. PRODUCTS & SERVICES CANDIDATES (EXACTLY 5 options)
   - Solutions that address the validated Jobs-to-be-Done
   - Must be feasible, specific, and actionable
   - Grounded in research evidence
   - Each should map to specific JTBD items
   - Provide diverse options for user to choose from
   - Include a short, memorable label (3-5 words)

2. PAIN RELIEVERS CANDIDATES (EXACTLY 5 options)
   - Features/approaches that address the validated Pains
   - Prioritize by pain severity (from research)
   - Include evidence citations
   - Each should map to specific Pain items
   - Provide diverse options for user to choose from
   - Include a short, memorable label (3-5 words)

3. GAIN CREATORS CANDIDATES (EXACTLY 5 options)
   - Features/benefits that deliver the validated Gains
   - Prioritize by gain importance (from research)
   - Include evidence citations
   - Each should map to specific Gain items
   - Provide diverse options for user to choose from
   - Include a short, memorable label (3-5 words)

CRITICAL RULES:
- Generate EXACTLY 5 candidates for each category (not more, not less)
- All candidates must be grounded in research evidence
- Use specific, actionable language (not generic statements)
- Include evidence citations for credibility
- Map each candidate to specific customer profile elements
- Provide diverse options so user has meaningful choices
- Each candidate MUST have a short, memorable label (3-5 words) extracted from the text

OUTPUT FORMAT (JSON):
{{
    "products_services_candidates": [
        {{
            "id": "product-1",
            "label": "Short 3-5 word label",
            "text": "Specific product/service description",
            "addresses_jtbd": ["jtbd-1", "jtbd-3"],
            "evidence": "Quote or reference from research",
            "priority": "high" | "medium" | "low"
        }},
        // ... EXACTLY 5 candidates total
    ],
    "pain_relievers_candidates": [
        {{
            "id": "reliever-1",
            "label": "Short 3-5 word label",
            "text": "Specific pain relief feature/approach",
            "addresses_pain": ["pain-1"],
            "impact": "Description of how it relieves the pain",
            "evidence": "Quote or reference from research",
            "priority": "critical" | "high" | "medium"
        }},
        // ... EXACTLY 5 candidates total
    ],
    "gain_creators_candidates": [
        {{
            "id": "creator-1",
            "label": "Short 3-5 word label",
            "text": "Specific gain creation feature/benefit",
            "creates_gain": ["gain-1"],
            "value": "Description of value delivered",
            "evidence": "Quote or reference from research",
            "priority": "high" | "medium" | "low"
        }},
        // ... EXACTLY 5 candidates total
    ]
}}"""

            # Create monitoring context for AI usage tracking
            from monitor.tokens.models import AIUsageContext
            monitoring_context = AIUsageContext(
                user_id=self._user_id if hasattr(self, '_user_id') else None,
                tenant_id=self._tenant_id if hasattr(self, '_tenant_id') else None,
                project_id=self._project_id if hasattr(self, '_project_id') else None,
                feature_id=VPC_V2_VALUE_MAP_FEATURE_ID,
                workflow_name="vpc_v2_workflow",
                step_name="value_map_generation",
                environment="prod"
            )
            
            # Generate structured output using AI service (uses gpt-5-mini)
            response = await self.ai_service.generate_analysis_response(
                messages=[
                    {"role": "system", "content": "You are an expert value proposition designer specializing in creating evidence-based value maps."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=16000,  # gpt-5-mini needs large token budget
                monitoring_context=monitoring_context
            )
            
            # Extract content from response
            response_content = response.get("content", response) if isinstance(response, dict) else response
            
            # Parse JSON response
            try:
                value_map = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_content, re.DOTALL)
                if json_match:
                    value_map = json.loads(json_match.group(1))
                else:
                    logger.error(f"❌ VPC v2: Failed to parse value map response as JSON")
                    return {
                        "success": False,
                        "error": "Failed to parse value map results"
                    }
            
            # Validate value map candidates structure
            required_keys = ["products_services_candidates", "pain_relievers_candidates", "gain_creators_candidates"]
            if not all(key in value_map for key in required_keys):
                logger.error(f"❌ VPC v2: Value map candidates missing required keys")
                return {
                    "success": False,
                    "error": "Value map candidates structure incomplete"
                }
            
            # Validate we have exactly 5 candidates per category
            for key in required_keys:
                if len(value_map[key]) != 5:
                    logger.warning(f"⚠️ VPC v2: {key} has {len(value_map[key])} candidates (expected 5)")
            
            logger.info(f"✅ VPC v2: Value map candidates generated - Products: {len(value_map['products_services_candidates'])}, Pain Relievers: {len(value_map['pain_relievers_candidates'])}, Gain Creators: {len(value_map['gain_creators_candidates'])}")
            
            return {
                "success": True,
                "value_map_candidates": value_map
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Value map generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Value map generation failed: {str(e)}"
            }
    
    def _format_dual_context_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Format dual vector store chunks for LLM context (optimized for token usage)."""
        if not chunks:
            return "No context available."
        
        formatted = []
        for i, chunk in enumerate(chunks[:3], 1):  # Limit to top 3 most relevant
            content = chunk.get('content', chunk.get('text', ''))
            # Truncate long content to first 300 chars
            truncated_content = content[:300] + "..." if len(content) > 300 else content
            formatted.append(f"[{i}]: {truncated_content}")
        
        return "\n".join(formatted)
    
    async def _store_vpc_v2(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str],
        vpc_v2_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store VPC v2 in database.
        
        UNIFIED STORAGE STRUCTURE (same for single and multi-persona):
        vpc_v2_data = {persona_id: {customer_profile: {...}, value_map_candidates: {...}}, ...}
        
        This ensures consistent structure for frontend consumption.
        """
        try:
            logger.info(f"💾 VPC v2: Storing VPC v2 for project {project_id}, persona {persona_id}")
            
            # Get current project data
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Get current vpc_v2_data (if exists)
            current_vpc_v2 = project.get("vpc_v2_data", {})
            
            # Determine storage structure based on personas
            personas = project.get("personas", [])
            
            # UNIFIED APPROACH: Always store under persona_id key for consistent structure
            # This ensures frontend receives same format for 1 or N personas
            logger.info(f"💾 VPC v2: Project has {len(personas)} persona(s) - using unified persona-keyed structure")
            
            if not isinstance(current_vpc_v2, dict):
                current_vpc_v2 = {}
            
            # MIGRATION: If old flat structure exists (single persona), migrate it
            if current_vpc_v2.get("customer_profile") and not any(k.startswith("P") for k in current_vpc_v2.keys()):
                old_persona_id = personas[0].get("id", "P1") if personas else "P1"
                logger.info(f"🔄 VPC v2: Migrating old flat structure to persona-keyed structure under {old_persona_id}")
                migrated_data = {
                    "customer_profile": current_vpc_v2.get("customer_profile"),
                    "value_map_candidates": current_vpc_v2.get("value_map_candidates"),
                    "value_map_selections": current_vpc_v2.get("value_map_selections"),
                    "status": current_vpc_v2.get("status"),
                    "persona_id": old_persona_id,
                    "persona_name": current_vpc_v2.get("persona_name"),
                    "version": current_vpc_v2.get("version"),
                    "validation_metadata": current_vpc_v2.get("validation_metadata"),
                }
                current_vpc_v2 = {old_persona_id: {k: v for k, v in migrated_data.items() if v is not None}}
            
            # Store VPC v2 for this persona (replaces if exists)
            if persona_id:
                is_regeneration = persona_id in current_vpc_v2
                current_vpc_v2[persona_id] = vpc_v2_data
                if is_regeneration:
                    logger.info(f"🔄 VPC v2: Replacing existing data for persona {persona_id}")
                else:
                    logger.info(f"✨ VPC v2: Creating new data for persona {persona_id}")
            else:
                # If no persona_id provided, use first persona
                persona_id = personas[0].get("id", "P1") if personas else "P1"
                is_regeneration = persona_id in current_vpc_v2
                current_vpc_v2[persona_id] = vpc_v2_data
                if is_regeneration:
                    logger.info(f"🔄 VPC v2: Replacing existing data for persona {persona_id} (auto-detected)")
                else:
                    logger.info(f"✨ VPC v2: Creating new data for persona {persona_id} (auto-detected)")
            
            updated_vpc_v2 = current_vpc_v2
            
            # Update project in database (DO NOT change current_step - it has constraints)
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            update_result = supabase.client.table('vmp_projects').update({
                'vpc_v2_data': updated_vpc_v2,
                'updated_at': datetime.utcnow().isoformat()
                # NOTE: Not updating current_step - VPC v2 is supplementary data, doesn't change workflow step
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                logger.error(f"❌ VPC v2: Failed to update project in database")
                return {
                    "success": False,
                    "error": "Failed to store VPC v2 in database"
                }
            
            logger.info(f"✅ VPC v2: Successfully stored VPC v2 in database")
            
            return {
                "success": True,
                "message": "VPC v2 stored successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Storage failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Storage failed: {str(e)}"
            }
    
    async def save_value_map_selections(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str],
        selected_product_ids: List[str],
        selected_pain_reliever_ids: List[str],
        selected_gain_creator_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Save user's value map selections (3 from each category of 5 candidates).
        Similar to customer profile selection in VPC v1.
        """
        try:
            logger.info(f"💾 VPC v2: Saving value map selections for project {project_id}, persona {persona_id}")
            
            # Validate selection counts
            if len(selected_product_ids) != 3:
                return {
                    "success": False,
                    "error": f"Must select exactly 3 products/services (got {len(selected_product_ids)})"
                }
            if len(selected_pain_reliever_ids) != 3:
                return {
                    "success": False,
                    "error": f"Must select exactly 3 pain relievers (got {len(selected_pain_reliever_ids)})"
                }
            if len(selected_gain_creator_ids) != 3:
                return {
                    "success": False,
                    "error": f"Must select exactly 3 gain creators (got {len(selected_gain_creator_ids)})"
                }
            
            # Get current project data
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Get VPC v2 data
            vpc_v2_data = project.get("vpc_v2_data", {})
            personas = project.get("personas", [])
            
            # Get the specific VPC v2 to update
            logger.info(f"🔍 VPC v2 Selections: vpc_v2_data keys: {list(vpc_v2_data.keys()) if isinstance(vpc_v2_data, dict) else 'not a dict'}")
            logger.info(f"🔍 VPC v2 Selections: Number of personas: {len(personas)}")
            logger.info(f"🔍 VPC v2 Selections: persona_id provided: {persona_id}")
            
            if len(personas) > 1:
                if not persona_id:
                    return {
                        "success": False,
                        "error": "persona_id required for multi-persona projects"
                    }
                vpc_v2 = vpc_v2_data.get(persona_id, {})
                logger.info(f"🔍 VPC v2 Selections: Multi-persona - got vpc_v2 for {persona_id}, keys: {list(vpc_v2.keys()) if isinstance(vpc_v2, dict) else 'not a dict'}")
                
                # FIX: Handle corrupted double-nested structure from old bug
                # If vpc_v2 has persona_id as key (double nesting), unwrap it
                if persona_id in vpc_v2 and isinstance(vpc_v2.get(persona_id), dict):
                    logger.warning(f"⚠️ VPC v2 Selections: Detected double-nested structure, unwrapping...")
                    vpc_v2 = vpc_v2[persona_id]
                    logger.info(f"🔍 VPC v2 Selections: After unwrapping, keys: {list(vpc_v2.keys()) if isinstance(vpc_v2, dict) else 'not a dict'}")
            else:
                vpc_v2 = vpc_v2_data
                logger.info(f"🔍 VPC v2 Selections: Single persona - vpc_v2 keys: {list(vpc_v2.keys()) if isinstance(vpc_v2, dict) else 'not a dict'}")
            
            if not vpc_v2:
                return {
                    "success": False,
                    "error": "VPC v2 not found. Generate VPC v2 first."
                }
            
            # Get candidates
            candidates = vpc_v2.get("value_map_candidates", {})
            logger.info(f"🔍 VPC v2 Selections: candidates keys: {list(candidates.keys()) if isinstance(candidates, dict) else 'not a dict or empty'}")
            
            if not candidates:
                logger.error(f"❌ VPC v2 Selections: Value map candidates not found. vpc_v2 structure: {list(vpc_v2.keys())}")
                return {
                    "success": False,
                    "error": "Value map candidates not found"
                }
            
            # Extract selected items from candidates
            products_candidates = candidates.get("products_services_candidates", [])
            relievers_candidates = candidates.get("pain_relievers_candidates", [])
            creators_candidates = candidates.get("gain_creators_candidates", [])
            
            selected_products = [p for p in products_candidates if p["id"] in selected_product_ids]
            selected_relievers = [r for r in relievers_candidates if r["id"] in selected_pain_reliever_ids]
            selected_creators = [c for c in creators_candidates if c["id"] in selected_gain_creator_ids]
            
            # Validate all selections found
            if len(selected_products) != 3:
                return {
                    "success": False,
                    "error": f"Invalid product IDs: {selected_product_ids}"
                }
            if len(selected_relievers) != 3:
                return {
                    "success": False,
                    "error": f"Invalid pain reliever IDs: {selected_pain_reliever_ids}"
                }
            if len(selected_creators) != 3:
                return {
                    "success": False,
                    "error": f"Invalid gain creator IDs: {selected_gain_creator_ids}"
                }
            
            # Get persona name
            if len(personas) > 1:
                persona_name = next((p.get("name") for p in personas if p.get("id") == persona_id), None)
            else:
                persona_name = personas[0].get("name") if personas else None
            
            # Update VPC v2 with selections including persona_name
            vpc_v2["value_map_selections"] = {
                "persona_name": persona_name,  # Store persona_name in selections
                "products_services": selected_products,
                "pain_relievers": selected_relievers,
                "gain_creators": selected_creators
            }
            vpc_v2["status"] = "selections_made"
            vpc_v2["selections_made_at"] = datetime.utcnow().isoformat()
            
            # Update in database
            if len(personas) > 1:
                vpc_v2_data[persona_id] = vpc_v2
                updated_vpc_v2 = vpc_v2_data
            else:
                updated_vpc_v2 = vpc_v2
            
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            update_result = supabase.client.table('vmp_projects').update({
                'vpc_v2_data': updated_vpc_v2,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                return {
                    "success": False,
                    "error": "Failed to save value map selections"
                }
            
            logger.info(f"✅ VPC v2: Value map selections saved successfully")
            
            # 📊 WORKFLOW STATUS: Mark Value Map as completed
            try:
                from .workflow_status_service import get_workflow_status_service, WorkflowStage
                workflow_service = get_workflow_status_service()
                workflow_service.set_stage_completed(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    stage=WorkflowStage.VALUE_MAP
                )
            except Exception as status_error:
                logger.warning(f"⚠️ VPC v2: Workflow status update failed (non-blocking): {status_error}")
            
            # 🔄 BACKGROUND CHUNKING: Chunk Customer Profile v2 for "Chat with Project" feature
            try:
                from .project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                
                # Prepare complete customer profile v2 data for chunking
                customer_profile_v2_data = {
                    persona_id or "single": {
                        "customer_profile": vpc_v2.get("customer_profile", {}),
                        "value_map_selections": vpc_v2.get("value_map_selections", {}),
                        "persona_name": persona_name or "Single Persona"
                    }
                }
                
                await chunk_vmp_feature_background(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.CUSTOMER_PROFILE_V2,
                    feature_data={"customer_profiles_v2": customer_profile_v2_data}
                )
                logger.info(f"🚀 VPC v2: Background chunking spawned for customer profile v2")
            except Exception as chunk_error:
                logger.warning(f"⚠️ VPC v2: Background chunking failed (non-blocking): {chunk_error}")
            
            return {
                "success": True,
                "message": "Value map selections saved successfully",
                "selections": vpc_v2["value_map_selections"]
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Failed to save value map selections: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to save selections: {str(e)}"
            }
    
    async def update_customer_profile(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str],
        updated_profile: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update VPC v2 customer profile.
        Allows editing of the validated customer profile.
        
        Supports:
        1. Single-persona update: Provide persona_id and single persona's profile
        2. Batch update: Omit persona_id and provide multi-persona structure (P1, P2, etc.)
        3. Single-persona project update: Omit persona_id for single persona projects
        """
        try:
            logger.info(f"✏️ VPC v2: Updating customer profile for project {project_id}, persona {persona_id}")
            
            # Get current project data
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Get VPC v2 data
            vpc_v2_data = project.get("vpc_v2_data", {})
            personas = project.get("personas", [])
            is_multi_persona = len(personas) > 1
            
            # DETECT BATCH UPDATE: If no persona_id but updated_profile has P1, P2 keys
            is_batch_update = (
                not persona_id and 
                is_multi_persona and 
                isinstance(updated_profile, dict) and
                any(key.startswith('P') and key[1:].isdigit() for key in updated_profile.keys())
            )
            
            if is_batch_update:
                # BATCH UPDATE: Update all personas at once
                logger.info(f"🔄 VPC v2: Detected batch update for {len(updated_profile)} personas")
                
                for pid, profile_data in updated_profile.items():
                    if pid in vpc_v2_data:
                        vpc_v2_data[pid]["customer_profile"] = profile_data
                        vpc_v2_data[pid]["updated_at"] = datetime.utcnow().isoformat()
                        logger.info(f"   ✅ Updated persona {pid}")
                
                updated_vpc_v2 = vpc_v2_data
                
            else:
                # SINGLE-PERSONA UPDATE: Original logic
                if is_multi_persona:
                    if not persona_id:
                        return {
                            "success": False,
                            "error": "persona_id required for single-persona update in multi-persona projects"
                        }
                    vpc_v2 = vpc_v2_data.get(persona_id, {})
                else:
                    vpc_v2 = vpc_v2_data
                
                if not vpc_v2:
                    return {
                        "success": False,
                        "error": "VPC v2 not found"
                    }
                
                # Update customer profile
                vpc_v2["customer_profile"] = updated_profile
                vpc_v2["updated_at"] = datetime.utcnow().isoformat()
                
                # Update in database
                if is_multi_persona:
                    vpc_v2_data[persona_id] = vpc_v2
                    updated_vpc_v2 = vpc_v2_data
                else:
                    updated_vpc_v2 = vpc_v2
            
            # Save to database
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            update_result = supabase.client.table('vmp_projects').update({
                'vpc_v2_data': updated_vpc_v2,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                return {
                    "success": False,
                    "error": "Failed to update customer profile"
                }
            
            logger.info(f"✅ VPC v2: Customer profile updated successfully")
            
            return {
                "success": True,
                "message": f"Customer profile updated successfully ({len(updated_profile)} persona(s))" if is_batch_update else "Customer profile updated successfully",
                "customer_profile": updated_profile
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Failed to update customer profile: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to update customer profile: {str(e)}"
            }
    
    async def update_value_map_selections(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str],
        updated_selections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update VPC v2 value map selections.
        Allows editing of the selected value map items.
        
        Supports three modes:
        1. Batch update (multi-persona): Send selections with P1, P2 keys, omit persona_id
        2. Single-persona update (in multi-persona project): Send single persona data + persona_id
        3. Single-persona project update: Send selections, omit persona_id
        """
        try:
            logger.info(f"✏️ VPC v2: Updating value map selections for project {project_id}, persona {persona_id}")
            
            # Get current project data
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Get VPC v2 data
            vpc_v2_data = project.get("vpc_v2_data", {})
            personas = project.get("personas", [])
            is_multi_persona = len(personas) > 1
            
            # Detect batch update: multi-persona project with P1, P2, etc. keys in updated_selections
            is_batch_update = (
                not persona_id and 
                is_multi_persona and 
                isinstance(updated_selections, dict) and
                any(key.startswith('P') and key[1:].isdigit() for key in updated_selections.keys())
            )
            
            if is_batch_update:
                # Batch update mode: updated_selections contains {P1: {...}, P2: {...}}
                logger.info(f"🔄 VPC v2: Batch update mode - updating {len(updated_selections)} persona(s)")
                
                for pid, selections_data in updated_selections.items():
                    if pid in vpc_v2_data:
                        vpc_v2_data[pid]["value_map_selections"] = selections_data
                        vpc_v2_data[pid]["updated_at"] = datetime.utcnow().isoformat()
                    else:
                        logger.warning(f"⚠️ Persona {pid} not found in VPC v2 data, skipping")
                
                updated_vpc_v2 = vpc_v2_data
                message = f"Value map selections updated successfully ({len(updated_selections)} persona(s))"
                
            else:
                # Single-persona update mode
                if is_multi_persona:
                    # Multi-persona project: persona_id is required
                    if not persona_id:
                        return {
                            "success": False,
                            "error": "persona_id required for single-persona update in multi-persona projects"
                        }
                    vpc_v2 = vpc_v2_data.get(persona_id, {})
                    if not vpc_v2:
                        return {
                            "success": False,
                            "error": f"VPC v2 not found for persona {persona_id}"
                        }
                    
                    # Update single persona
                    vpc_v2["value_map_selections"] = updated_selections
                    vpc_v2["updated_at"] = datetime.utcnow().isoformat()
                    vpc_v2_data[persona_id] = vpc_v2
                    updated_vpc_v2 = vpc_v2_data
                    
                else:
                    # Single-persona project: update directly
                    vpc_v2 = vpc_v2_data
                    if not vpc_v2:
                        return {
                            "success": False,
                            "error": "VPC v2 not found"
                        }
                    
                    vpc_v2["value_map_selections"] = updated_selections
                    vpc_v2["updated_at"] = datetime.utcnow().isoformat()
                    updated_vpc_v2 = vpc_v2
                
                message = "Value map selections updated successfully"
            
            # Update in database
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            update_result = supabase.client.table('vmp_projects').update({
                'vpc_v2_data': updated_vpc_v2,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                return {
                    "success": False,
                    "error": "Failed to update value map selections"
                }
            
            logger.info(f"✅ VPC v2: {message}")
            
            return {
                "success": True,
                "message": message,
                "value_map_selections": updated_selections
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Failed to update value map selections: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to update value map selections: {str(e)}"
            }
    
    async def update_vpc_v2(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str],
        updated_vpc_v2: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update full VPC v2 data (customer profile + value map + any other fields).
        Allows comprehensive editing of the entire VPC v2 structure.
        
        Supports three modes:
        1. Batch update (multi-persona): Send vpc_v2 with P1, P2 keys, omit persona_id
        2. Single-persona update (in multi-persona project): Send single persona data + persona_id
        3. Single-persona project update: Send vpc_v2 data, omit persona_id
        """
        try:
            logger.info(f"✏️ VPC v2: Updating full VPC v2 for project {project_id}, persona {persona_id}")
            
            # Get current project data
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Get VPC v2 data
            vpc_v2_data = project.get("vpc_v2_data", {})
            personas = project.get("personas", [])
            is_multi_persona = len(personas) > 1
            
            # Detect batch update: multi-persona project with P1, P2, etc. keys in updated_vpc_v2
            is_batch_update = (
                not persona_id and 
                is_multi_persona and 
                isinstance(updated_vpc_v2, dict) and
                any(key.startswith('P') and key[1:].isdigit() for key in updated_vpc_v2.keys())
            )
            
            if is_batch_update:
                # Batch update mode: updated_vpc_v2 contains {P1: {...}, P2: {...}}
                logger.info(f"🔄 VPC v2: Batch update mode - updating {len(updated_vpc_v2)} persona(s)")
                
                for pid, vpc_data in updated_vpc_v2.items():
                    if pid in vpc_v2_data:
                        # Update the entire persona's VPC v2 data
                        vpc_v2_data[pid].update(vpc_data)
                        vpc_v2_data[pid]["updated_at"] = datetime.utcnow().isoformat()
                    else:
                        logger.warning(f"⚠️ Persona {pid} not found in VPC v2 data, skipping")
                
                updated_vpc_v2_final = vpc_v2_data
                message = f"VPC v2 updated successfully ({len(updated_vpc_v2)} persona(s))"
                
            else:
                # Single-persona update mode
                if is_multi_persona:
                    # Multi-persona project: persona_id is required
                    if not persona_id:
                        return {
                            "success": False,
                            "error": "persona_id required for single-persona update in multi-persona projects"
                        }
                    vpc_v2 = vpc_v2_data.get(persona_id, {})
                    if not vpc_v2:
                        return {
                            "success": False,
                            "error": f"VPC v2 not found for persona {persona_id}"
                        }
                    
                    # Update single persona's VPC v2 data
                    vpc_v2.update(updated_vpc_v2)
                    vpc_v2["updated_at"] = datetime.utcnow().isoformat()
                    vpc_v2_data[persona_id] = vpc_v2
                    updated_vpc_v2_final = vpc_v2_data
                    
                else:
                    # Single-persona project: update directly
                    vpc_v2 = vpc_v2_data
                    if not vpc_v2:
                        return {
                            "success": False,
                            "error": "VPC v2 not found"
                        }
                    
                    vpc_v2.update(updated_vpc_v2)
                    vpc_v2["updated_at"] = datetime.utcnow().isoformat()
                    updated_vpc_v2_final = vpc_v2
                
                message = "VPC v2 updated successfully"
            
            # Update in database
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            update_result = supabase.client.table('vmp_projects').update({
                'vpc_v2_data': updated_vpc_v2_final,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                return {
                    "success": False,
                    "error": "Failed to update VPC v2"
                }
            
            logger.info(f"✅ VPC v2: {message}")
            
            return {
                "success": True,
                "message": message,
                "vpc_v2": updated_vpc_v2_final
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2: Failed to update VPC v2: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to update VPC v2: {str(e)}"
            }
    
    # ============================================================================
    # BATCH PROCESSING METHODS (Multi-Persona Parallel Generation)
    # ============================================================================
    
    async def generate_customer_profile_v2_batch(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate VPC v2 customer profiles for ALL personas in parallel.
        
        This matches the VPC V1 pattern where a single API call generates
        customer profiles for all personas simultaneously.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
        
        Returns:
            Dict with success status and customer profiles for all personas
        """
        try:
            logger.info(f"🎯 VPC v2 Batch: Starting customer profile generation for project {project_id}")
            
            # 1. Get project and personas
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {"success": False, "error": "Project not found"}
            
            personas = project.get("personas", [])
            if not personas:
                return {"success": False, "error": "No personas found. Please identify personas first."}
            
            logger.info(f"✅ VPC v2 Batch: Found {len(personas)} personas")
            
            # 2. Validate prerequisites
            validation = await self._validate_prerequisites(project_id, tenant_id)
            if not validation["ready"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_requirements": validation["missing"]
                }
            
            logger.info(f"✅ VPC v2 Batch: Prerequisites validated")
            
            # 3. Generate customer profiles in PARALLEL
            import asyncio
            tasks = []
            for persona in personas:
                persona_id = persona.get("id")
                persona_name = persona.get("name", "Target Persona")
                
                task = self.generate_customer_profile_v2(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    persona_id=persona_id
                )
                tasks.append((persona_id, persona_name, task))
            
            logger.info(f"🚀 VPC v2 Batch: Launching {len(tasks)} parallel customer profile generations")
            
            # Execute in parallel
            results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
            
            # 4. Process results
            customer_profiles = {}
            errors = []
            
            for i, result in enumerate(results):
                persona_id, persona_name, _ = tasks[i]
                
                if isinstance(result, Exception):
                    logger.error(f"❌ VPC v2 Batch: Failed for {persona_name} ({persona_id}): {result}")
                    errors.append(f"{persona_name}: {str(result)}")
                elif result.get("success"):
                    customer_profiles[persona_id] = result["customer_profile"]
                    logger.info(f"✅ VPC v2 Batch: Success for {persona_name} ({persona_id})")
                else:
                    logger.error(f"❌ VPC v2 Batch: Failed for {persona_name} ({persona_id}): {result.get('error')}")
                    errors.append(f"{persona_name}: {result.get('error')}")
            
            if errors:
                return {
                    "success": False,
                    "error": f"Failed for some personas: {'; '.join(errors)}",
                    "partial_results": customer_profiles
                }
            
            logger.info(f"✅ VPC v2 Batch: Successfully generated customer profiles for {len(customer_profiles)} personas")
            
            return {
                "success": True,
                "customer_profiles": customer_profiles,
                "personas_processed": list(customer_profiles.keys()),
                "message": f"Customer profiles generated successfully for {len(customer_profiles)} personas"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2 Batch: Customer profile generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Batch customer profile generation failed: {str(e)}"
            }
    
    async def generate_value_map_v2_batch(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate VPC v2 value map candidates for ALL personas in parallel.
        
        This matches the VPC V1 pattern where a single API call generates
        value maps for all personas simultaneously.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
        
        Returns:
            Dict with success status and value map candidates for all personas
        """
        try:
            logger.info(f"🎯 VPC v2 Batch: Starting value map generation for project {project_id}")
            
            # 1. Get project and personas
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {"success": False, "error": "Project not found"}
            
            personas = project.get("personas", [])
            if not personas:
                return {"success": False, "error": "No personas found. Please identify personas first."}
            
            logger.info(f"✅ VPC v2 Batch: Found {len(personas)} personas")
            
            # 2. Validate that customer profiles exist for all personas
            vpc_v2_data = project.get("vpc_v2_data", {})
            missing_profiles = []
            
            # UNIFIED STRUCTURE: Always look under persona_id key
            # Structure: {P1: {customer_profile: {...}}, P2: {...}} for both single and multi-persona
            # LEGACY: Also check for old flat structure and handle gracefully
            
            for persona in personas:
                persona_id = persona.get("id")
                
                # Try unified structure first (persona-keyed)
                persona_vpc_v2 = vpc_v2_data.get(persona_id, {})
                
                # LEGACY FALLBACK: If no persona key found, check for flat structure
                if not persona_vpc_v2 and vpc_v2_data.get("customer_profile"):
                    persona_vpc_v2 = vpc_v2_data
                    logger.info(f"🔍 VPC v2 Batch: Using legacy flat structure for {persona_id}")
                else:
                    logger.info(f"🔍 VPC v2 Batch: Using unified structure vpc_v2_data[{persona_id}]")
                
                logger.info(f"🔍 VPC v2 Batch: persona_vpc_v2 keys: {list(persona_vpc_v2.keys()) if isinstance(persona_vpc_v2, dict) else 'not a dict'}")
                
                if not persona_vpc_v2.get("customer_profile"):
                    missing_profiles.append(persona.get("name", persona_id))
            
            if missing_profiles:
                return {
                    "success": False,
                    "error": f"Customer profiles not found for: {', '.join(missing_profiles)}. Generate customer profiles first."
                }
            
            logger.info(f"✅ VPC v2 Batch: All personas have customer profiles")
            
            # 3. Generate value maps in PARALLEL
            import asyncio
            tasks = []
            for persona in personas:
                persona_id = persona.get("id")
                persona_name = persona.get("name", "Target Persona")
                
                task = self.generate_value_map_v2(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    persona_id=persona_id
                )
                tasks.append((persona_id, persona_name, task))
            
            logger.info(f"🚀 VPC v2 Batch: Launching {len(tasks)} parallel value map generations")
            
            # Execute in parallel
            results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
            
            # 4. Process results
            value_map_candidates = {}
            errors = []
            
            for i, result in enumerate(results):
                persona_id, persona_name, _ = tasks[i]
                
                if isinstance(result, Exception):
                    logger.error(f"❌ VPC v2 Batch: Failed for {persona_name} ({persona_id}): {result}")
                    errors.append(f"{persona_name}: {str(result)}")
                elif result.get("success"):
                    value_map_candidates[persona_id] = result["value_map_candidates"]
                    logger.info(f"✅ VPC v2 Batch: Success for {persona_name} ({persona_id})")
                else:
                    logger.error(f"❌ VPC v2 Batch: Failed for {persona_name} ({persona_id}): {result.get('error')}")
                    errors.append(f"{persona_name}: {result.get('error')}")
            
            if errors:
                return {
                    "success": False,
                    "error": f"Failed for some personas: {'; '.join(errors)}",
                    "partial_results": value_map_candidates
                }
            
            logger.info(f"✅ VPC v2 Batch: Successfully generated value maps for {len(value_map_candidates)} personas")
            
            return {
                "success": True,
                "value_map_candidates": value_map_candidates,
                "personas_processed": list(value_map_candidates.keys()),
                "message": f"Value map candidates generated successfully for {len(value_map_candidates)} personas"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2 Batch: Value map generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Batch value map generation failed: {str(e)}"
            }
    
    async def save_value_map_selections_batch(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona_selections: Dict[str, Dict[str, List[str]]]
    ) -> Dict[str, Any]:
        """
        Save value map selections for multiple personas in a single operation.
        
        This matches the VPC V1 pattern where all persona selections are saved together.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            persona_selections: Dict mapping persona_id to their selections
                {
                    "P1": {
                        "selected_product_ids": [...],
                        "selected_pain_reliever_ids": [...],
                        "selected_gain_creator_ids": [...]
                    },
                    "P2": {...}
                }
        
        Returns:
            Dict with success status and saved selections
        """
        try:
            logger.info(f"🎯 VPC v2 Batch: Saving value map selections for project {project_id}")
            logger.info(f"🎯 VPC v2 Batch: Personas: {list(persona_selections.keys())}")
            
            # 1. Get project
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project:
                return {"success": False, "error": "Project not found"}
            
            vpc_v2_data = project.get("vpc_v2_data", {})
            personas = project.get("personas", [])
            
            # DEBUG: Show vpc_v2_data structure
            logger.info(f"🔍 VPC v2 Batch: vpc_v2_data keys: {list(vpc_v2_data.keys())}")
            for pid in vpc_v2_data.keys():
                logger.info(f"🔍 VPC v2 Batch: vpc_v2_data[{pid}] keys: {list(vpc_v2_data[pid].keys()) if isinstance(vpc_v2_data[pid], dict) else 'NOT A DICT'}")
            
            # CRITICAL FIX: Map persona names to IDs if frontend sends names instead of IDs
            # Build mapping: name -> id and id -> id
            persona_mapping = {}
            for p in personas:
                persona_id = p.get("id")
                persona_name = p.get("name")
                if persona_id:
                    persona_mapping[persona_id] = persona_id  # ID -> ID
                    if persona_name:
                        persona_mapping[persona_name] = persona_id  # Name -> ID
            
            logger.info(f"🔍 VPC v2 Batch: Persona mapping: {persona_mapping}")
            logger.info(f"🔍 VPC v2 Batch: Incoming persona_selections keys: {list(persona_selections.keys())}")
            
            # Normalize persona_selections to use IDs
            normalized_selections = {}
            for key, selections in persona_selections.items():
                mapped_id = persona_mapping.get(key)
                if mapped_id:
                    normalized_selections[mapped_id] = selections
                    logger.info(f"🔍 VPC v2 Batch: Mapped '{key}' -> '{mapped_id}'")
                else:
                    logger.warning(f"⚠️ VPC v2 Batch: Could not map persona key '{key}'")
                    normalized_selections[key] = selections  # Keep original if no mapping
            
            # 2. Process selections for each persona (like VPC V1 - just map IDs to objects)
            updated_vpc_v2_data = vpc_v2_data.copy()
            saved_selections = {}
            
            # UNIFIED STRUCTURE: Always use persona-keyed structure
            # Structure: {P1: {value_map_candidates: {...}}, P2: {...}} for both single and multi-persona
            logger.info(f"🔍 VPC v2 Batch: Processing {len(personas)} persona(s) with unified structure")
            
            for persona_id, selections in normalized_selections.items():
                logger.info(f"🔍 VPC v2 Batch: Processing selections for {persona_id}")
                logger.info(f"🔍 VPC v2 Batch: Selection keys: {list(selections.keys())}")
                logger.info(f"🔍 VPC v2 Batch: selected_product_ids: {selections.get('selected_product_ids', [])}")
                logger.info(f"🔍 VPC v2 Batch: selected_pain_reliever_ids: {selections.get('selected_pain_reliever_ids', [])}")
                logger.info(f"🔍 VPC v2 Batch: selected_gain_creator_ids: {selections.get('selected_gain_creator_ids', [])}")
                
                # CRITICAL FIX: Get persona_name for THIS persona at the start of each iteration
                # Previously, persona_name was only set in error blocks, causing all personas to get the same name
                persona_name = next((p.get("name") for p in personas if p.get("id") == persona_id), persona_id)
                logger.info(f"🔍 VPC v2 Batch: Resolved persona_name for {persona_id}: {persona_name}")
                
                # Validate selection counts
                if len(selections.get("selected_product_ids", [])) != 3:
                    return {"success": False, "error": f"Exactly 3 products must be selected for {persona_name} ({persona_id})"}
                if len(selections.get("selected_pain_reliever_ids", [])) != 3:
                    return {"success": False, "error": f"Exactly 3 pain relievers must be selected for {persona_name} ({persona_id})"}
                if len(selections.get("selected_gain_creator_ids", [])) != 3:
                    return {"success": False, "error": f"Exactly 3 gain creators must be selected for {persona_name} ({persona_id})"}
                
                # UNIFIED STRUCTURE: Always look under persona_id key
                persona_vpc_v2 = updated_vpc_v2_data.get(persona_id, {})
                
                # LEGACY FALLBACK: If no persona key found, check for flat structure
                if not persona_vpc_v2 and updated_vpc_v2_data.get("value_map_candidates"):
                    persona_vpc_v2 = updated_vpc_v2_data
                    logger.info(f"🔍 VPC v2 Batch: Using legacy flat structure for {persona_id}")
                else:
                    logger.info(f"🔍 VPC v2 Batch: Using unified structure vpc_v2_data[{persona_id}]")
                
                # DEBUG: Show what's in the database for this persona
                logger.info(f"🔍 VPC v2 Batch: persona_vpc_v2 for {persona_id} exists: {bool(persona_vpc_v2)}")
                if persona_vpc_v2:
                    logger.info(f"🔍 VPC v2 Batch: persona_vpc_v2[{persona_id}] keys: {list(persona_vpc_v2.keys())}")
                    logger.info(f"🔍 VPC v2 Batch: persona_vpc_v2[{persona_id}] type: {type(persona_vpc_v2)}")
                
                if not persona_vpc_v2:
                    return {
                        "success": False,
                        "error": f"No VPC v2 data found for {persona_name} ({persona_id}). Generate customer profile first."
                    }
                
                candidates = persona_vpc_v2.get("value_map_candidates", {})
                logger.info(f"🔍 VPC v2 Batch: candidates for {persona_id} exists: {bool(candidates)}")
                logger.info(f"🔍 VPC v2 Batch: candidates type: {type(candidates)}")
                
                # FIX: If candidates is a string (from old RPC bug), parse it
                if isinstance(candidates, str):
                    logger.warning(f"⚠️ VPC v2 Batch: candidates is a string, parsing JSON for {persona_id}")
                    try:
                        candidates = json.loads(candidates)
                        logger.info(f"✅ VPC v2 Batch: Successfully parsed candidates from JSON string")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ VPC v2 Batch: Failed to parse candidates JSON: {e}")
                        return {
                            "success": False,
                            "error": f"Invalid value map candidates format for {persona_id}. Please regenerate value maps."
                        }
                
                if candidates:
                    logger.info(f"🔍 VPC v2 Batch: candidates keys: {list(candidates.keys()) if isinstance(candidates, dict) else 'NOT A DICT'}")
                
                if not candidates:
                    return {
                        "success": False,
                        "error": f"No value map candidates found for {persona_name} ({persona_id}). Generate value maps first."
                    }
                
                logger.info(f"🔍 VPC v2 Batch: Found {len(candidates.get('products_services_candidates', []))} product candidates for {persona_id}")
                
                # Map selected IDs to full objects
                selected_products = [
                    item for item in candidates.get("products_services_candidates", [])
                    if item.get("id") in selections["selected_product_ids"]
                ]
                selected_pain_relievers = [
                    item for item in candidates.get("pain_relievers_candidates", [])
                    if item.get("id") in selections["selected_pain_reliever_ids"]
                ]
                selected_gain_creators = [
                    item for item in candidates.get("gain_creators_candidates", [])
                    if item.get("id") in selections["selected_gain_creator_ids"]
                ]
                
                # Store selections with persona_name
                value_map_selections = {
                    "persona_name": persona_name,  # Store persona_name in selections
                    "products_services": selected_products,
                    "pain_relievers": selected_pain_relievers,
                    "gain_creators": selected_gain_creators
                }
                
                persona_vpc_v2["value_map_selections"] = value_map_selections
                persona_vpc_v2["status"] = "selections_made"
                persona_vpc_v2["updated_at"] = datetime.utcnow().isoformat()
                
                # UNIFIED STRUCTURE: Always store under persona_id key
                updated_vpc_v2_data[persona_id] = persona_vpc_v2
                
                saved_selections[persona_id] = value_map_selections
                
                logger.info(f"✅ VPC v2 Batch: Saved selections for {persona_id}")
            
            # 4. Update database in single operation
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            update_result = supabase.client.table('vmp_projects').update({
                'vpc_v2_data': updated_vpc_v2_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not update_result.data:
                return {
                    "success": False,
                    "error": "Failed to save value map selections"
                }
            
            logger.info(f"✅ VPC v2 Batch: Successfully saved selections for {len(saved_selections)} personas")
            
            # 🔄 BACKGROUND CHUNKING: Chunk Customer Profile v2 for "Chat with Project" feature
            try:
                from .project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                
                # Prepare complete customer profile v2 data for chunking
                customer_profile_v2_data = {}
                for persona_id in saved_selections.keys():
                    persona_vpc_v2 = updated_vpc_v2_data.get(persona_id, {})
                    if persona_vpc_v2:
                        customer_profile_v2_data[persona_id] = {
                            "customer_profile": persona_vpc_v2.get("customer_profile", {}),
                            "value_map_selections": persona_vpc_v2.get("value_map_selections", {}),
                            "persona_name": persona_vpc_v2.get("persona_name", persona_id)
                        }
                
                await chunk_vmp_feature_background(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.CUSTOMER_PROFILE_V2,
                    feature_data={"customer_profiles_v2": customer_profile_v2_data}
                )
                logger.info(f"🚀 VPC v2 Batch: Background chunking spawned for customer profile v2")
            except Exception as chunk_error:
                logger.warning(f"⚠️ VPC v2 Batch: Background chunking failed (non-blocking): {chunk_error}")
            
            return {
                "success": True,
                "value_map_selections": saved_selections,
                "personas_processed": list(saved_selections.keys()),
                "message": f"Value map selections saved successfully for {len(saved_selections)} personas"
            }
            
        except Exception as e:
            logger.error(f"❌ VPC v2 Batch: Failed to save selections: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to save value map selections: {str(e)}"
            }
