"""
Integrated VPM Service

This service wraps the original VPM services and integrates them with Yuba's infrastructure
without modifying the original VPM code. It acts as a bridge layer.
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Ensure Yuba's environment variables are loaded for VPM services
yuba_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
yuba_env_path = os.path.abspath(yuba_env_path)
if os.path.exists(yuba_env_path):
    load_dotenv(yuba_env_path, override=False)
    print(f"🔧 Loaded Yuba environment for VPM services: {yuba_env_path}")

# Add VPM directory to Python path
vpm_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'VPM')
vpm_path = os.path.abspath(vpm_path)
if vpm_path not in sys.path:
    sys.path.insert(0, vpm_path)

# VPM path validation
print(f"🔍 VPM Path: {vpm_path}")
if not os.path.exists(vpm_path):
    print(f"❌ VPM Path does not exist: {vpm_path}")
else:
    print(f"✅ VPM Path exists with {len(os.listdir(vpm_path))} items")

# Import adapters
from ..adapters.auth_adapter import get_yuba_auth_adapter
from ..adapters.vector_adapter import get_yuba_vector_adapter
from ..adapters.database_adapter import get_yuba_database_adapter

# Import original VPM services (required for Pure Bridge Architecture)
try:
    # Test basic VPM module access first
    if not os.path.exists(vpm_path):
        raise ImportError(f"VPM directory not found at {vpm_path}")
    
    # Check for required subdirectories
    required_dirs = ['VMP', 'ValMap', 'core', 'Field_Prep']
    missing_dirs = [d for d in required_dirs if not os.path.exists(os.path.join(vpm_path, d))]
    if missing_dirs:
        raise ImportError(f"Missing VPM directories: {missing_dirs}")
    
    # Import original VPM services (Pure Bridge - no fallbacks)
    from core.session_manager import GraphState
    from VMP.services import VMPService
    from VMP.data_access import VMPDataAccess
    from VMP.vector_service import VMPVectorService
    from ValMap.services import VPCGeneratorService
    try:
        from core.session_manager import GraphState
        from VMP.services import VMPService
        from VMP.data_access import VMPDataAccess
        from VMP.vector_service import VMPVectorService
        from ValMap.services import VPCGeneratorService
        print("✅ Successfully loaded original VPM services")
    except ImportError as e:
        print(f"❌ VPM Import Error: {e}")
        print(f"❌ Pure Bridge Architecture requires original VPM services")
        print(f"❌ Path details:")
        print(f"   - VPM path: {vpm_path}")
        print(f"   - Path exists: {os.path.exists(vpm_path)}")
        if os.path.exists(vpm_path):
            print(f"   - VMP exists: {os.path.exists(os.path.join(vpm_path, 'VMP'))}")
            print(f"   - ValMap exists: {os.path.exists(os.path.join(vpm_path, 'ValMap'))}")
            print(f"   - core exists: {os.path.exists(os.path.join(vpm_path, 'core'))}")
        raise ImportError(f"❌ Original VPM services are required but not available: {e}")
    
except Exception as e:
    print(f"✅ Successfully imported VPM services")
except Exception as e:
    print(f"❌ ERROR: Failed to import VPM services: {e}")
    raise


# ==================== PROBLEM STATEMENT GENERATION PROMPTS ====================

PROBLEM_STATEMENT_SYSTEM_PROMPT = """
You are an expert at crafting clear, CONCISE problem statements in CAUSE-AND-EFFECT format.

MANDATORY FORMAT - Every statement MUST follow this pattern:
"[CAUSE/Root Problem] is [EFFECT VERB] [WHO/Stakeholder] from [BLOCKED OUTCOME]."

EFFECT VERBS to use: "preventing", "forcing", "causing", "blocking", "leaving"

EXAMPLES (follow these exactly):
✅ "The lack of affordable diapers with acceptable standards is preventing Kenyan urban parents from maintaining their babies' proper hygiene."
✅ "Ethiopian university graduates' inability to meet global standards is preventing them from competing in the international job market."
✅ "The ambulance's long response time more than triples the amount of preventable deaths in Lagos."
✅ "The absence of real-time weather data is preventing Kenyan smallholder farmers from optimizing their planting dates."

❌ WRONG (too long/verbose):
"Rainfed smallholder maize and bean farmers in western and central Kenya owning 0.5-2 hectares struggle to decide the optimal planting date because they lack timely, localized and interpretable information..." → TOO LONG

CRITICAL REQUIREMENTS:
1. MAXIMUM 180 CHARACTERS (not words!) - one concise sentence
2. MUST use cause-and-effect structure with effect verb
3. Must clearly show: CAUSE → EFFECT VERB → WHO → BLOCKED OUTCOME
4. Be specific about geography and stakeholder
5. NO verbose explanations - be punchy and direct
"""

PROBLEM_STATEMENT_USER_PROMPT = """
Transform the following research summary into a CONCISE cause-and-effect problem statement.

RESEARCH SUMMARY:
{executive_summary}

CONSTRUCTION STEPS:
1. Extract the ROOT CAUSE (what's broken/missing/inadequate)
2. Identify WHO is affected (specific group + geography)
3. Choose an EFFECT VERB (preventing, forcing, causing, etc.)
4. Identify the BLOCKED OUTCOME (what they cannot achieve)
5. Construct: "[CAUSE] is [EFFECT VERB] [WHO] from [OUTCOME]"

VALIDATION:
☐ Is it under 150 CHARACTERS? (REQUIRED)
☐ Does it use an effect verb (preventing, forcing, causing)? (REQUIRED)
☐ Does it follow cause-and-effect structure? (REQUIRED)

Return your response as JSON with this exact structure:
{{
  "problem_statement": "Your CONCISE cause-and-effect statement (max 150 chars)",
  "target_audience": "Who faces the problem",
  "core_problem": "What the problem/gap is",
  "impact": "What they're prevented from achieving",
  "confidence": 0.0-1.0
}}
"""


class IntegratedVPMService:
    """
    VPM Service integrated with Yuba infrastructure.
    
    This service acts as a bridge between VPM's original functionality
    and Yuba's existing systems (auth, credits, database, vector storage).
    
    The original VPM code remains completely unchanged.
    """
    
    def __init__(self):
        """Initialize with both Yuba adapters and original VPM services"""
        # Yuba integration adapters
        self.auth_adapter = get_yuba_auth_adapter()
        self.db_adapter = get_yuba_database_adapter()
        self.vector_adapter = get_yuba_vector_adapter()
        
        # Original VPM services (Pure Bridge - lazy initialization)
        self.GraphState = GraphState
        
        # Initialize as None - will be created when first needed
        self._original_vmp_service = None
        self._original_data_access = None
        self._original_vector_service = None
        self._vpc_generator = None
        
        print("✅ VPM services ready for lazy initialization")
        
        # Credit adapter for billing integration
        self.credit_adapter = self.auth_adapter  # Assuming auth_adapter has credit methods
    
    @property
    def original_vmp_service(self):
        """Lazy initialization of original VMP service"""
        if self._original_vmp_service is None:
            try:
                self._original_vmp_service = VMPService()
                print("✅ Original VMP service initialized")
            except Exception as e:
                raise Exception(f"❌ Failed to initialize VMP service: {e}")
        return self._original_vmp_service
    
    @property
    def original_data_access(self):
        """Lazy initialization of original data access"""
        if self._original_data_access is None:
            try:
                self._original_data_access = VMPDataAccess()
                print("✅ Original data access initialized")
            except Exception as e:
                raise Exception(f"❌ Failed to initialize data access: {e}")
        return self._original_data_access
    
    @property
    def original_vector_service(self):
        """Lazy initialization of original vector service"""
        if self._original_vector_service is None:
            try:
                self._original_vector_service = VMPVectorService()
                print("✅ Original vector service initialized")
            except Exception as e:
                raise Exception(f"❌ Failed to initialize vector service: {e}")
        return self._original_vector_service
    
    @property
    def vpc_generator(self):
        """Lazy initialization of VPC generator"""
        if self._vpc_generator is None:
            try:
                self._vpc_generator = VPCGeneratorService()
                print("✅ VPC generator initialized")
            except Exception as e:
                raise Exception(f"❌ Failed to initialize VPC generator: {e}")
        return self._vpc_generator
    
    async def browse_pv_reports(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35, 
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Browse available PV reports for VPM project creation.
        
        This method uses Yuba's existing vector storage to find PV reports
        while providing the interface VPM expects.
        """
        try:
            # Validate access using Yuba's auth system
            await self.auth_adapter.validate_tenant_access(user_id, tenant_id)
            
            # Get reports using Yuba's database adapter
            reports, total_count = await self.db_adapter.get_pv_reports(
                tenant_id=tenant_id,
                page=page,
                page_size=page_size,
                search_query=search
            )
            
            has_next = (page * page_size) < total_count
            
            return {
                'success': True,
                'reports': reports,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': has_next
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'reports': [],
                'total_count': 0
            }
    
    async def get_report_detail(self, report_id: str, tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific PV report."""
        try:
            # Validate access using Yuba's auth system
            await self.auth_adapter.validate_tenant_access(user_id, tenant_id)
            
            # Get report details using Yuba's database adapter
            report = await self.db_adapter.get_report_detail(report_id, tenant_id)
            
            if report:
                return {
                    'success': True,
                    'report': report
                }
            else:
                return {
                    'success': False,
                    'error': 'Report not found or access denied'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_project_detail(self, project_id: str, tenant_id: str, user_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific VMP project."""
        try:
            # Get project details using Yuba's database adapter
            project = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            
            if project:
                return {
                    'success': True,
                    'project': project
                }
            else:
                return {
                    'success': False,
                    'error': 'Project not found or access denied'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_dual_vector_context(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get dual vector store context for VPC generation."""
        try:
            # Get context using Yuba's vector adapter
            context = await self.vector_adapter.get_project_context(project_id, tenant_id)
            
            if context:
                return {
                    'success': True,
                    'context': context
                }
            else:
                return {
                    'success': False,
                    'error': 'No context found for project'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_vmp_project(
        self, 
        project_data: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create VPM project with Yuba integration.
        
        This is the key transition point from Module 1 (PVM) to Module 2 (VPM).
        It implements the dual vector store linking described in VPM documentation.
        """
        try:
            # Check credits using Yuba's credit system
            has_credits = await self.auth_adapter.check_feature_credits(
                user_id, 'project_creation'
            )
            
            if not has_credits:
                return {
                    'success': False,
                    'error': 'Insufficient credits for project creation',
                    'project': None
                }
            
            # Always fetch executive summary as description (no user input for description)
            print(f"🔍 DEBUG: Fetching executive summary from PV report to use as project description")
            executive_summary = await self.db_adapter.get_pv_report_executive_summary(
                project_data['pv_report_id'], 
                project_data['tenant_id']
            )
            if executive_summary:
                project_data['description'] = executive_summary
                print(f"✅ DEBUG: Set description from executive summary: {len(executive_summary)} chars")
                
                # NEW: Generate properly formatted problem statement using LLM
                refined_problem_statement = self._generate_formatted_problem_statement(executive_summary)
                project_data['refined_problem_statement'] = refined_problem_statement
                print(f"✅ DEBUG: Generated refined problem statement: {refined_problem_statement[:100]}...")
            else:
                # Fallback description if no executive summary found
                project_data['description'] = f"Value proposition development project based on Problem Validation report"
                print(f"⚠️ DEBUG: Using fallback description - no executive summary found")
            
            # First, create or link to parent project in main projects table
            parent_project_id = await self._ensure_parent_project(project_data, user_id)
            
            # Prepare project data for VMP-specific table with parent link
            project_data.update({
                'user_id': user_id,  # Add user_id to satisfy not-null constraint
                'parent_project_id': parent_project_id,  # Link to main projects table
                'status': 'active',
                'current_step': 'project_setup',
                'vpc_data': {},
                'field_prep_data': {},
                'settings': {}
            })
            
            # Create project using Yuba's database adapter
            print(f"🔍 DEBUG: About to create project with data: {project_data}")
            project = await self.db_adapter.create_vmp_project(project_data)
            print(f"🔍 DEBUG: Project creation returned: {project}")
            
            # Link contexts using dual vector store strategy
            print(f"🔍 DEBUG: About to link project contexts for project ID: {project['id']}")
            await self._link_project_contexts(
                project['id'], 
                project_data['pv_report_id']
            )
            print(f"🔍 DEBUG: Project contexts linked successfully")
            
            # Deduct credits using Yuba's credit system
            await self.auth_adapter.deduct_credits(
                user_id, 'project_creation', 5
            )
            
            # 📊 WORKFLOW STATUS: Mark Project as created
            try:
                from .workflow_status_service import get_workflow_status_service, WorkflowStage
                workflow_service = get_workflow_status_service()
                workflow_service.set_stage_completed(
                    project_id=project['id'],
                    tenant_id=project_data['tenant_id'],
                    stage=WorkflowStage.PROJECT_CREATED
                )
            except Exception as status_error:
                print(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
            
            return {
                'success': True,
                'project': project,
                'message': 'VPM project created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'project': None
            }
    
    async def get_user_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user's VPM projects.
        
        Uses Yuba's database system while providing VPM expected interface.
        """
        try:
            # Get projects using Yuba's database adapter
            projects, total_count = await self.db_adapter.get_vmp_projects(
                tenant_id=tenant_id,
                user_id=user_id,
                page=page,
                page_size=page_size,
                status_filter=status_filter,
                search_query=search
            )
            
            has_next = (page * page_size) < total_count
            
            return {
                'success': True,
                'projects': projects,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': has_next
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'projects': [],
                'total_count': 0
            }
    
    async def get_questionnaire_completed_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        search: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Get VPM projects that have completed questionnaire generation.
        
        Filters projects where:
        - field_prep_data.stage = 'questionnaires_completed'
        - field_prep_data.questionnaires array exists and is not empty
        - current_step = 'completed'
        
        Args:
            tenant_id: Tenant ID for filtering
            user_id: User ID (for audit, not filtering due to team collaboration)
            page: Page number for pagination
            page_size: Number of items per page
            search: Optional search query for project names
            include_metadata: Whether to include questionnaire metadata
            
        Returns:
            Dict with success status, projects list, and metadata
        """
        try:
            # Get questionnaire-completed projects using database adapter
            projects, total_count = await self.db_adapter.get_questionnaire_completed_projects(
                tenant_id=tenant_id,
                user_id=user_id,
                page=page,
                page_size=page_size,
                search_query=search,
                include_metadata=include_metadata
            )
            
            has_next = (page * page_size) < total_count
            
            return {
                'success': True,
                'projects': projects,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': has_next
            }
            
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch questionnaire-completed projects: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'projects': [],
                'total_count': 0
            }
    
    async def get_value_map_completed_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        search: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Get VPM projects that have completed Value Map selections (Module 2 final step).
        
        These projects are READY FOR MODULE 3 (VPS v1 generation).
        
        Filters projects where:
        - All personas have value_map_selections
        - Each value_map has 3+ items in products_services, pain_relievers, gain_creators
        
        Args:
            tenant_id: Tenant ID for filtering
            user_id: User ID (for audit, not filtering due to team collaboration)
            page: Page number for pagination
            page_size: Number of items per page
            search: Optional search query for project names
            include_metadata: Whether to include persona metadata
            
        Returns:
            Dict with success status, projects list, and metadata
        """
        try:
            # Get value-map-completed projects using database adapter
            projects, total_count = await self.db_adapter.get_value_map_completed_projects(
                tenant_id=tenant_id,
                user_id=user_id,
                page=page,
                page_size=page_size,
                search_query=search,
                include_metadata=include_metadata
            )
            
            has_next = (page * page_size) < total_count
            
            return {
                'success': True,
                'projects': projects,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': has_next
            }
            
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch value-map-completed projects: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'projects': [],
                'total_count': 0
            }
    
    async def get_vps_v2_completed_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        search: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Get VPM projects that have completed VPS v2 generation (Module 3 refinement).
        
        These projects are READY FOR AMRG (MVP Requirements Generator).
        
        Filters projects where:
        - mvp_data.vps_v2 exists and is not empty
        - mvp_data.current_version.vps = 'v2'
        
        Args:
            tenant_id: Tenant ID for filtering
            user_id: User ID (for audit, not filtering due to team collaboration)
            page: Page number for pagination
            page_size: Number of items per page
            search: Optional search query for project names
            include_metadata: Whether to include VPS v2 metadata
            
        Returns:
            Dict with success status, projects list, and metadata
        """
        try:
            # Get VPS v2 completed projects using database adapter
            projects, total_count = await self.db_adapter.get_vps_v2_completed_projects(
                tenant_id=tenant_id,
                user_id=user_id,
                page=page,
                page_size=page_size,
                search_query=search,
                include_metadata=include_metadata
            )
            
            has_next = (page * page_size) < total_count
            
            return {
                'success': True,
                'projects': projects,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': has_next
            }
            
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch VPS v2 completed projects: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'projects': [],
                'total_count': 0
            }
    
    async def get_latest_projects(
        self, 
        tenant_id: str, 
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get the latest VMP projects ordered by updated_at (most recent first).
        
        OPTIMIZED for fast fetching - designed for dashboard/quick access.
        
        Args:
            tenant_id: Tenant ID for filtering
            limit: Maximum number of projects to return (default 5)
            
        Returns:
            Dict with success status and projects list
        """
        try:
            projects = await self.db_adapter.get_latest_projects(
                tenant_id=tenant_id,
                limit=limit
            )
            
            return {
                'success': True,
                'projects': projects,
                'count': len(projects)
            }
            
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch latest projects: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'projects': [],
                'count': 0
            }
    
    async def identify_personas(
        self, 
        project_id: str, 
        tenant_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Identify personas from PV report and actionable insights using RAG.
        
        This is the new step that comes before customer profile generation.
        """
        try:
            # Check credits for persona identification
            has_credits = await self.auth_adapter.check_feature_credits(
                user_id, 'persona_identification'
            )
            
            if not has_credits:
                return {
                    'success': False,
                    'error': 'Insufficient credits for persona identification'
                }
            
            # Use the same dual context search as customer profile generation
            print(f"🔍 DEBUG: [IDENTIFY_PERSONAS] Getting dual context for persona identification")
            context = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query="customer persona stakeholder user problem pain point target market segment",
                max_results_per_store=15  # Same as customer profile generation
            )
            
            print(f"🔍 DEBUG: [IDENTIFY_PERSONAS] Context keys: {list(context.keys()) if context else 'None'}")
            print(f"🔍 DEBUG: [IDENTIFY_PERSONAS] PV context items: {len(context.get('pv_report_context', []))}")
            print(f"🔍 DEBUG: [IDENTIFY_PERSONAS] Insights context items: {len(context.get('actionable_insights_context', []))}")
            
            # Transform context to format expected by VMP service
            transformed_context = self._transform_context_for_vmp(context, {})
            
            # Import and use the original VMP persona service with our context
            from VMP.persona_service import get_persona_identification_service
            
            persona_service = get_persona_identification_service()
            
            # Call the proper persona identification method that returns structured response
            # We need to temporarily override the service's context retrieval to use our context
            original_retrieve_method = persona_service._retrieve_persona_content
            
            async def mock_retrieve_content(contexts):
                return (
                    transformed_context.get('pv_report', {}).get('content', ''),
                    transformed_context.get('actionable_insights', {}).get('content', '')
                )
            
            # Temporarily replace the method
            persona_service._retrieve_persona_content = mock_retrieve_content
            
            try:
                # Call the full identify_personas method which returns proper structure
                result = await persona_service.identify_personas(project_id, tenant_id)
            finally:
                # Restore original method
                persona_service._retrieve_persona_content = original_retrieve_method
            
            # Convert personas to dict format
            personas_data = [persona.dict() for persona in result.personas]
            
            # Save personas to database
            print(f"🔍 DEBUG: [IDENTIFY_PERSONAS] About to save {len(personas_data)} personas to database")
            save_success = await self.db_adapter.save_project_personas(project_id, personas_data)
            
            if save_success:
                print(f"✅ DEBUG: [IDENTIFY_PERSONAS] Successfully saved personas to database")
                
                # 📊 WORKFLOW STATUS: Mark Persona as created
                try:
                    from .workflow_status_service import get_workflow_status_service, WorkflowStage
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.PERSONA_CREATED,
                        additional_metadata={"personas_count": len(personas_data)}
                    )
                except Exception as status_error:
                    print(f"⚠️ DEBUG: [IDENTIFY_PERSONAS] Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk personas for "Chat with Project" feature
                try:
                    from .project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    await chunk_vmp_feature_background(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        feature_type=VMPFeatureType.PERSONA,
                        feature_data={"personas": personas_data}
                    )
                    print(f"🚀 DEBUG: [IDENTIFY_PERSONAS] Background chunking spawned for personas")
                except Exception as chunk_error:
                    print(f"⚠️ DEBUG: [IDENTIFY_PERSONAS] Background chunking failed (non-blocking): {chunk_error}")
            else:
                print(f"❌ DEBUG: [IDENTIFY_PERSONAS] Failed to save personas to database")
            
            # Deduct credits
            await self.auth_adapter.deduct_credits(
                user_id, 'persona_identification', 10
            )
            
            return {
                'success': True,
                'personas': personas_data,
                'total_personas': result.total_personas,
                'analysis_summary': result.analysis_summary,
                'requires_multiple_vpcs': result.requires_multiple_vpcs,
                'personas_saved': save_success
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_project_personas(
        self, 
        project_id: str, 
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get previously identified personas for a project."""
        try:
            print(f"🔍 DEBUG: [GET_PERSONAS] Retrieving personas for project {project_id}")
            
            # Get personas from the new personas column
            personas = await self.db_adapter.get_project_personas(project_id)
            
            if not personas:
                print(f"🔍 DEBUG: [GET_PERSONAS] No personas found for project {project_id}")
                return {
                    'success': False,
                    'error': 'Personas not yet identified for this project'
                }
            
            print(f"✅ DEBUG: [GET_PERSONAS] Found {len(personas)} personas for project {project_id}")
            
            return {
                'success': True,
                'data': {
                    'project_id': project_id,
                    'personas': personas,
                    'total_personas': len(personas),
                    'requires_multiple_vpcs': len(personas) > 1
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_executive_summary(
        self, 
        project_id: str, 
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get the executive summary for a project."""
        try:
            # Get project data
            project_data = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            
            if not project_data:
                return {
                    'success': False,
                    'error': 'Project not found'
                }
            
            # Get executive summary from vpc_data
            executive_summary = project_data.get('vpc_data', {}).get('executive_summary', '')
            
            # If no executive summary stored, try to fetch from PV report
            if not executive_summary:
                from VMP.persona_service import get_persona_identification_service
                persona_service = get_persona_identification_service()
                pv_report_id = project_data.get('pv_report_id')
                if pv_report_id:
                    executive_summary = await persona_service._retrieve_executive_summary(pv_report_id)
            
            return {
                'success': True,
                'executive_summary': executive_summary,
                'has_summary': bool(executive_summary)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_vpc_with_dual_context(
        self, 
        project_id: str, 
        generation_request: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate VPC using dual vector store context.
        
        This implements the sophisticated context strategy described in VPM docs:
        - Uses both PV report data and actionable insights
        - Provides rich context for AI generation
        - Maintains traceability to source data
        """
        try:
            # Check credits for VPC generation
            has_credits = await self.auth_adapter.check_feature_credits(
                user_id, 'vpc_generation'
            )
            
            if not has_credits:
                return {
                    'success': False,
                    'error': 'Insufficient credits for VPC generation',
                    'vpc_data': None
                }
            
            # Determine generation type and create appropriate context query
            generation_type = generation_request.get("generation_type", "customer_profile")
            
            if generation_type == "customer_profile":
                context_query = "customer problems pain points jobs to be done gains needs frustrations desires Ethiopian shoes footwear local manufacturing"
            elif generation_type == "value_map":
                context_query = "products services solutions pain relievers gain creators value proposition Ethiopian shoes manufacturing"
            else:
                context_query = generation_request.get('query', generation_request.get('prompt', 'customer problems value proposition solutions Ethiopian shoes'))
            
            print(f"🔍 DEBUG: Using context query for {generation_type}: '{context_query}'")
            
            # Get dual context as described in VPM documentation with semantic search
            # Increase context window for better VPC generation
            context = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query=context_query,
                max_results_per_store=20  # Increased from 5 to 10 for richer context
            )
            
            # Use original VPM service (pure bridge)
            vpc_result = await self._call_original_vpc_generation(
                context=context,
                generation_request=generation_request,
                project_id=project_id,
                user_id=user_id
            )
            
            # Deduct credits using Yuba's credit system
            await self.auth_adapter.deduct_credits(
                user_id, 'vpc_generation', 15
            )
            
            # Save the generated candidates to artifacts table for later selection
            print(f"🔍 DEBUG: About to save VPC artifacts for {generation_type}")
            artifact_saved = await self._save_vpc_artifacts(project_id, generation_type, vpc_result, user_id)
            print(f"🔍 DEBUG: Artifact save result: {artifact_saved}")
            
            return {
                'success': True,
                'vpc_data': vpc_result,
                'context_summary': context['context_summary'],
                'message': 'VPC generated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'vpc_data': None
            }
    
    async def _link_project_contexts(self, project_id: str, pv_report_id: str) -> bool:
        """
        Link project to both PV report and actionable insights contexts.
        
        This implements the dual vector store integration described in VPM docs.
        """
        try:
            return await self.db_adapter.link_project_contexts(project_id, pv_report_id)
        except Exception as e:
            print(f"Error linking project contexts: {e}")
            return False
    
    async def _call_original_vpc_generation(
        self, 
        context: Dict[str, Any], 
        generation_request: Dict[str, Any],
        project_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Call original VPM service for VPC generation.
        
        Pure bridge to original VPM service - no fallbacks.
        """
        try:
            # Create GraphState object that the original VPM service expects
            state = self.GraphState()
            
            # Populate state with context from dual vector store
            state["pv_report_context"] = context.get("pv_report_context", {})
            state["actionable_insights_context"] = context.get("actionable_insights_context", {})
            state["combined_context"] = context.get("combined_context", [])
            
            # Add generation parameters
            state["generation_type"] = generation_request.get("generation_type", "full_vpc")
            state["creativity_level"] = generation_request.get("creativity_level", 0.7)
            state["query"] = generation_request.get("query", "")
            
            # Get project data to extract PV report ID and customer profile selections
            db_adapter = get_yuba_database_adapter()
            # Get user_id from the generation request or extract from context
            user_id_for_query = generation_request.get("user_id") or user_id
            project_data = await db_adapter.get_project_with_selections(project_id, user_id_for_query)
            
            if project_data:
                print(f"🔍 DEBUG: Project data keys: {list(project_data.keys())}")
                print(f"🔍 DEBUG: Project data sample: {dict(list(project_data.items())[:3])}")
                
                # Add report_id that original VPM service expects
                report_id = project_data.get("pv_report_id")
                parent_project_id = project_data.get("parent_project_id")
                
                if report_id:
                    state["report_id"] = report_id
                    print(f"🔍 DEBUG: Set report_id in state: {report_id}")
                    
                    # ROOT CAUSE FIX: Update the PV report to include the parent_project_id
                    # This is the definitive solution to fix the data integrity issue
                    if parent_project_id:
                        print(f"🔍 DEBUG: Fixing PV report and actionable insights project_id linkage...")
                        await self._fix_pv_report_project_id(report_id, parent_project_id)
                        await self._fix_actionable_insights_project_id(report_id, parent_project_id)
                else:
                    print(f"🔍 DEBUG: No pv_report_id found. Checking all possible report ID fields...")
                    for key in project_data.keys():
                        if 'report' in key.lower() or 'id' in key.lower():
                            print(f"🔍 DEBUG: Found potential report field: {key} = {project_data[key]}")
                
                # Add customer profile selections for value map generation
                vpc_data = project_data.get("vpc_data", {})
                customer_profile = vpc_data.get("customer_profile", {})
                if customer_profile:
                    # Format customer profile selections for original VPM service
                    # VPM service expects: {"jtbd": [...], "pain": [...], "gain": [...]}
                    selections = {
                        "jtbd": customer_profile.get("jobs_to_be_done", []),
                        "pain": customer_profile.get("pains", []),
                        "gain": customer_profile.get("gains", [])
                    }
                    
                    # CRITICAL: VPM service expects "selections" key with this exact format
                    state["selections"] = selections  # This is what VPM service looks for!
                    state["customer_profile_selections"] = selections  # Backup for compatibility
                    state["customer_profile"] = customer_profile  # Original format
                    
                    print(f"🔍 DEBUG: Added customer profile selections for VPM service:")
                    print(f"🔍 DEBUG: - JTBD: {len(selections.get('jtbd', []))} items")
                    print(f"🔍 DEBUG: - Pains: {len(selections.get('pain', []))} items") 
                    print(f"🔍 DEBUG: - Gains: {len(selections.get('gain', []))} items")
                    print(f"🔍 DEBUG: Selections key set for VPM service: 'selections'")
            else:
                print(f"🔍 DEBUG: No project_data found for project_id: {project_id}")
            
            # Use the VPC Generator Service for actual VPC generation
            vpc_generator = self.vpc_generator
            generation_type = generation_request.get("generation_type", "full_vpc")
            
            # DEBUG: Print detailed context information
            print(f"🔍 DEBUG: Context being passed to VPC generation:")
            print(f"🔍 DEBUG: - PV Report Context items: {len(context.get('pv_report_context', []))}")
            print(f"🔍 DEBUG: - Actionable Insights items: {len(context.get('actionable_insights_context', []))}")
            print(f"🔍 DEBUG: - Combined Context items: {len(context.get('combined_context', []))}")
            
            # Print first few context items to see actual content
            for i, item in enumerate(context.get('combined_context', [])[:3]):
                print(f"🔍 DEBUG: Context item {i+1}: {item.get('content', '')[:200]}...")
            
            if generation_type == "customer_profile":
                # Use the dedicated customer profile generation method with persona support
                print(f"🔍 DEBUG: Calling dedicated customer profile generation method")
                customer_profile_result = await self.generate_customer_profile_with_dual_context(
                    project_id=project_id,
                    context=context,
                    generation_request=generation_request,
                    user_id=user_id
                )
                
                # Convert the result to the expected format
                result_state = {
                    'customer_profile': customer_profile_result['customer_profile'],
                    'generation_metadata': customer_profile_result['generation_metadata']
                }
                print(f"🔍 DEBUG: Customer profile generation completed")
            elif generation_type == "value_map":
                # Transform context and generate VALUE MAP (Products/Services, Pain Relievers, Gain Creators)
                # NOT Customer Profile (JTBD, Pains, Gains) - that's already done in Step 1
                transformed_context = self._transform_context_for_vmp(context, project_data)
                print(f"🔍 DEBUG: Transformed context keys: {list(transformed_context.keys())}")
                print(f"🔍 DEBUG: Report ID in state: {state.get('report_id', 'NOT SET')}")
                
                # ROBUST SOLUTION: Provide rich context directly to bypass project_id dependency
                # Add the transformed context directly to state so VPM service can use it
                state["pv_report_content"] = transformed_context.get("pv_report", "")
                state["actionable_insights_content"] = transformed_context.get("actionable_insights", "")
                state["context_provided"] = True  # Flag to indicate we're providing context directly
                
                # CRITICAL: Set the generation type to VALUE MAP, not customer profile
                state["generation_type"] = "value_map"  # Ensure VMP service generates VALUE MAP items
                state["target_generation"] = "value_proposition"  # Target the value proposition side
                
                print(f"🔍 DEBUG: Added direct context - PV Report: {len(state['pv_report_content'])} chars, Insights: {len(state['actionable_insights_content'])} chars")
                print(f"🔍 DEBUG: Generation target: VALUE MAP (Products/Services, Pain Relievers, Gain Creators)")
                
                # Generate VALUE MAP using the correct method - this should generate solutions, not repeat customer profile
                print(f"🔍 DEBUG: About to call generate_value_map_concurrent for VALUE MAP generation")
                vpc_generator.generate_value_map_concurrent(state)
                print(f"🔍 DEBUG: Called generate_value_map_concurrent, state keys: {list(state.keys())}")
                result_state = state
            else:
                # Generate full VPC (both customer profile and value map)
                transformed_context = self._transform_context_for_vmp(context, project_data)
                vpc_generator.generate_customer_profile_with_context(state, transformed_context)
                vpc_generator.generate_value_map_concurrent(state)
                # Compose the final VPC
                vpc_data = vpc_generator.compose_vpc(state, f"session_{project_id}")
                return vpc_data
            
            # Extract VPC data from result state
            print(f"🔍 DEBUG: Result state keys: {list(result_state.keys())}")
            print(f"🔍 DEBUG: Generation type: {generation_type}")
            
            # DETAILED DEBUGGING: Check what's actually in the result_state
            if "vm_candidates" in result_state:
                vm_candidates = result_state["vm_candidates"]
                print(f"🔍 DEBUG: vm_candidates found with keys: {list(vm_candidates.keys())}")
                for key, items in vm_candidates.items():
                    print(f"🔍 DEBUG: vm_candidates[{key}]: {len(items)} items")
                    if items:
                        print(f"🔍 DEBUG: First item in {key}: {items[0].get('label', 'No label')}")
            else:
                print(f"🔍 DEBUG: No vm_candidates in result_state")
                
            # Check for any other candidate keys
            for key in result_state.keys():
                if 'candidate' in key.lower():
                    print(f"🔍 DEBUG: Found candidate key: {key} = {type(result_state[key])}")
            
            if "vpc_data" in result_state and result_state["vpc_data"]:
                print(f"🔍 DEBUG: Found vpc_data in result_state")
                return result_state["vpc_data"]
            elif "customer_profile" in result_state or "value_map" in result_state:
                print(f"🔍 DEBUG: Found customer_profile or value_map in result_state")
                # Construct VPC data from individual components
                return {
                    'customer_profile': result_state.get("customer_profile", {}),
                    'value_map': result_state.get("value_map", {}),
                    'generation_metadata': {
                        'model_used': 'original_vmp',
                        'context_items_used': len(context.get('combined_context', [])),
                        'generation_time': datetime.utcnow().isoformat(),
                        'generation_type': generation_type
                    }
                }
            elif "error" in result_state:
                print(f"🔍 DEBUG: Found error in result_state: {result_state['error']}")
                raise Exception(f"VPM service error: {result_state['error']}")
            # Check for vm_candidates key (where value map data is stored)
            elif "vm_candidates" in result_state and result_state["vm_candidates"]:
                print(f"🔍 DEBUG: Found vm_candidates data: {list(result_state['vm_candidates'].keys())}")
                candidates_data = result_state["vm_candidates"]
                
                if generation_type == "value_map":
                    # Handle VALUE MAP candidates (Products/Services, Pain Relievers, Gain Creators)
                    value_map = {
                        'products_services': candidates_data.get('product_service', []),  # Note: singular form
                        'pain_relievers': candidates_data.get('pain_reliever', []),      # Note: singular form  
                        'gain_creators': candidates_data.get('gain_creator', [])         # Note: singular form
                    }
                    
                    print(f"🔍 DEBUG: Value Map extracted - Products: {len(value_map['products_services'])}, Pain Relievers: {len(value_map['pain_relievers'])}, Gain Creators: {len(value_map['gain_creators'])}")
                    
                    return {
                        'value_map': value_map,
                        'generation_metadata': {
                            'model_used': 'original_vmp',
                            'context_items_used': len(context.get('combined_context', [])),
                            'generation_time': datetime.utcnow().isoformat(),
                            'generation_type': generation_type,
                            'total_candidates': sum(len(value_map.get(k, [])) for k in ['products_services', 'pain_relievers', 'gain_creators'])
                        }
                    }
            # Check for candidates key (where original VMP stores generated data)
            elif "candidates" in result_state and result_state["candidates"]:
                print(f"🔍 DEBUG: Found candidates data: {list(result_state['candidates'].keys())}")
                candidates_data = result_state["candidates"]
                
                # DEBUG: Check what's actually in candidates_data
                print(f"🔍 DEBUG: candidates_data type: {type(candidates_data)}")
                print(f"🔍 DEBUG: candidates_data keys: {list(candidates_data.keys()) if isinstance(candidates_data, dict) else 'Not a dict'}")
                if isinstance(candidates_data, dict):
                    for key, value in candidates_data.items():
                        print(f"🔍 DEBUG: candidates_data['{key}'] = {type(value)} with {len(value) if isinstance(value, (list, dict)) else 'unknown'} items")
                        if isinstance(value, list) and value:
                            print(f"🔍 DEBUG: First item in {key}: {value[0] if value else 'empty'}")
                
                if generation_type == "customer_profile":
                    # Try different possible key names that VMP might use
                    possible_keys = {
                        'jobs_to_be_done': ['jtbd', 'jobs_to_be_done', 'job', 'jobs'],
                        'pains': ['pain', 'pains'],
                        'gains': ['gain', 'gains']
                    }
                    
                    customer_profile = {'jobs_to_be_done': [], 'pains': [], 'gains': []}
                    
                    for profile_key, possible_candidate_keys in possible_keys.items():
                        found = False
                        for candidate_key in possible_candidate_keys:
                            if candidate_key in candidates_data and candidates_data[candidate_key]:
                                customer_profile[profile_key] = candidates_data[candidate_key]
                                print(f"✅ DEBUG: Found {profile_key} data under key '{candidate_key}': {len(customer_profile[profile_key])} items")
                                found = True
                                break
                        
                        if not found:
                            print(f"🚨 DEBUG: No data found for {profile_key} in any of these keys: {possible_candidate_keys}")
                    
                    # DEBUG: Check what we extracted
                    print(f"🔍 DEBUG: Extracted customer_profile:")
                    print(f"  - jobs_to_be_done: {len(customer_profile['jobs_to_be_done'])} items")
                    print(f"  - pains: {len(customer_profile['pains'])} items") 
                    print(f"  - gains: {len(customer_profile['gains'])} items")
                    
                    return {
                        'customer_profile': customer_profile,
                        'generation_metadata': {
                            'model_used': 'original_vmp',
                            'context_items_used': len(context.get('combined_context', [])),
                            'generation_time': datetime.utcnow().isoformat(),
                            'generation_type': generation_type,
                            'total_candidates': sum(len(candidates_data.get(k, [])) for k in ['jtbd', 'pain', 'gain'])
                        }
                    }
                elif generation_type == "value_map":
                    # Handle value map candidates
                    value_map = {
                        'products_services': candidates_data.get('products_services', []),
                        'pain_relievers': candidates_data.get('pain_relievers', []),
                        'gain_creators': candidates_data.get('gain_creators', [])
                    }
                    
                    return {
                        'value_map': value_map,
                        'generation_metadata': {
                            'model_used': 'original_vmp',
                            'context_items_used': len(context.get('combined_context', [])),
                            'generation_time': datetime.utcnow().isoformat(),
                            'generation_type': generation_type,
                            'total_candidates': sum(len(candidates_data.get(k, [])) for k in ['products_services', 'pain_relievers', 'gain_creators'])
                        }
                    }
            else:
                print(f"🔍 DEBUG: No expected keys found in result_state")
                print(f"🔍 DEBUG: Available keys: {list(result_state.keys())}")
                raise Exception(f"VPM service did not generate VPC data. Available keys: {list(result_state.keys())}")
                
        except Exception as e:
            raise Exception(f"Failed to call original VPM service: {str(e)}")

    def _transform_context_for_vmp(self, context: Dict[str, Any], project_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transform Yuba's context format to the format expected by original VMP service.
        
        Yuba format: {'pv_report_context': [chunks], 'actionable_insights_context': [chunks]}
        VMP format: {'pv_report': {'content': 'combined_text'}, 'actionable_insights': {'content': 'combined_text'}}
        """
        try:
            # Combine PV report chunks into single content string
            pv_chunks = context.get('pv_report_context', [])
            pv_content = '\n\n'.join([
                chunk.get('content', '') for chunk in pv_chunks if chunk.get('content')
            ])
            
            # Combine actionable insights chunks into single content string
            insights_chunks = context.get('actionable_insights_context', [])
            insights_content = '\n\n'.join([
                chunk.get('content', '') for chunk in insights_chunks if chunk.get('content')
            ])
            
            # Transform to VMP expected format
            transformed = {
                'pv_report': {
                    'content': pv_content,
                    'metadata': {
                        'chunk_count': len(pv_chunks),
                        'source': 'yuba_integration'
                    }
                },
                'actionable_insights': {
                    'content': insights_content,
                    'metadata': {
                        'chunk_count': len(insights_chunks),
                        'source': 'yuba_integration'
                    }
                }
            }
            
            # Add project data if available (for persona context)
            if project_data:
                transformed['project_data'] = project_data
            
            print(f"🔍 DEBUG: Transformed context - PV content length: {len(pv_content)}")
            print(f"🔍 DEBUG: Transformed context - Insights content length: {len(insights_content)}")
            if pv_content:
                print(f"🔍 DEBUG: PV content preview: {pv_content[:300]}...")
            
            return transformed
            
        except Exception as e:
            print(f"❌ Error transforming context: {e}")
            return {
                'pv_report': {'content': ''},
                'actionable_insights': {'content': ''}
            }

    async def _ensure_parent_project(self, project_data: Dict[str, Any], user_id: str) -> str:
        """
        Ensure parent project exists in main projects table for journey tracking.
        
        This creates the parent project that tracks the user's entrepreneurial journey
        while the VMP project handles VPM-specific data.
        """
        try:
            # Import here to avoid circular imports
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            print(f"🔍 DEBUG: Checking for existing parent project...")
            print(f"🔍 DEBUG: tenant_id={project_data['tenant_id']}, user_id={user_id}, pv_report_id={project_data['pv_report_id']}")
            
            # Check if parent project already exists for this PV report
            supabase = get_service_role_client()
            
            existing_result = supabase.client.table('projects').select('id').eq(
                'tenant_id', project_data['tenant_id']
            ).eq('user_id', user_id).eq(
                'pv_report_id', project_data['pv_report_id']
            ).eq('current_module', 'value_proposition').execute()
            
            print(f"🔍 DEBUG: Existing parent query result: {existing_result.data}")
            
            if existing_result.data:
                # Parent project already exists
                parent_id = existing_result.data[0]['id']
                print(f"🔗 DEBUG: Using existing parent project: {parent_id}")
                return parent_id
            
            # Create new parent project in main projects table
            print(f"🆕 DEBUG: Creating new parent project...")
            parent_data = {
                'tenant_id': project_data['tenant_id'],
                'user_id': user_id,
                'name': project_data['name'],
                'description': project_data['description'],
                'current_module': 'value_proposition',
                'problem_statement': f"Value proposition development for {project_data['name']}",
                'pv_report_id': project_data['pv_report_id'],
                'status': 'active',
                'settings': {
                    'vmp_enabled': True,
                    'module_transition': 'problem_validation_to_value_proposition',
                    'journey_stage': 'value_proposition_development'
                }
            }
            
            print(f"🔍 DEBUG: Parent project data: {parent_data}")
            parent_result = supabase.client.table('projects').insert(parent_data).execute()
            print(f"🔍 DEBUG: Parent creation result: {parent_result}")
            
            if parent_result.data:
                parent_id = parent_result.data[0]['id']
                print(f"✅ DEBUG: Created parent project: {parent_id}")
                return parent_id
            else:
                print(f"❌ DEBUG: Parent creation failed - no data returned")
                print(f"❌ DEBUG: Full result: {parent_result}")
                raise Exception("Failed to create parent project - no data returned")
                
        except Exception as e:
            print(f"❌ Error ensuring parent project: {e}")
            print(f"❌ Exception type: {type(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            # Re-raise the original exception to prevent VMP creation with invalid parent
            raise Exception(f"Failed to ensure parent project: {e}")

    async def save_customer_profile_selections(
        self,
        project_id: str,
        selections: Dict[str, List[str]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Save customer profile selections (Step 1 completion).
        
        This stores the user's selected JTBD, Pains, and Gains for use in Value Map generation.
        """
        try:
            # First, get the generated candidates to map IDs to full objects
            db_adapter = get_yuba_database_adapter()
            
            # Get the last generated candidates from vpc_artifacts
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            artifacts_result = supabase.client.table('vmp_vpc_artifacts').select('*').eq(
                'project_id', project_id
            ).eq('artifact_type', 'customer_profile').order('created_at', desc=True).limit(1).execute()
            
            print(f"🔍 DEBUG: Artifacts query result: {len(artifacts_result.data) if artifacts_result.data else 0} items found")
            if artifacts_result.data:
                print(f"🔍 DEBUG: First artifact keys: {list(artifacts_result.data[0].keys())}")
                print(f"🔍 DEBUG: Artifact content type: {type(artifacts_result.data[0].get('content'))}")
            
            if not artifacts_result.data:
                return {
                    'success': False,
                    'error': 'No customer profile candidates found. Please generate candidates first.'
                }
            
            # Extract candidates from the artifact
            candidates_data = artifacts_result.data[0]['content']
            all_candidates = candidates_data.get('customer_profile_candidates', {}).get('customer_profile', {})
            
            # Map selected IDs to full objects
            selected_candidates = {
                'jtbd': [],
                'pain': [],
                'gain': []
            }
            
            # Helper function to normalize IDs for matching (same as value map)
            def normalize_id(id_value):
                """Normalize ID by removing prefixes and converting to string"""
                if isinstance(id_value, str):
                    # Remove common prefixes like 'jtbd-', 'pain-', 'gain-'
                    for prefix in ['jtbd-', 'pain-', 'gain-', 'job-']:
                        if id_value.startswith(prefix):
                            return id_value[len(prefix):]
                    return id_value
                return str(id_value)
            
            def ids_match(id1, id2):
                """Check if two IDs match after normalization"""
                return normalize_id(id1) == normalize_id(id2)
            
            # Map JTBD selections
            jtbd_candidates = all_candidates.get('jobs_to_be_done', [])
            print(f"🔍 DEBUG: Looking for JTBD IDs: {selections.get('jtbd', [])}")
            print(f"🔍 DEBUG: Available JTBD IDs: {[c.get('id') for c in jtbd_candidates]}")
            
            for jtbd_id in selections.get('jtbd', []):
                found = False
                for candidate in jtbd_candidates:
                    if ids_match(candidate.get('id'), jtbd_id):
                        selected_candidates['jtbd'].append(candidate)
                        found = True
                        print(f"✅ DEBUG: Found JTBD match: {jtbd_id} -> {candidate.get('id')}")
                        break
                if not found:
                    print(f"🚨 DEBUG: Could not find JTBD ID: {jtbd_id}")
            
            # Map Pain selections
            pain_candidates = all_candidates.get('pains', [])
            print(f"🔍 DEBUG: Looking for Pain IDs: {selections.get('pain', [])}")
            print(f"🔍 DEBUG: Available Pain IDs: {[c.get('id') for c in pain_candidates]}")
            
            for pain_id in selections.get('pain', []):
                found = False
                for candidate in pain_candidates:
                    if ids_match(candidate.get('id'), pain_id):
                        selected_candidates['pain'].append(candidate)
                        found = True
                        print(f"✅ DEBUG: Found Pain match: {pain_id} -> {candidate.get('id')}")
                        break
                if not found:
                    print(f"🚨 DEBUG: Could not find Pain ID: {pain_id}")
            
            # Map Gain selections
            gain_candidates = all_candidates.get('gains', [])
            print(f"🔍 DEBUG: Looking for Gain IDs: {selections.get('gain', [])}")
            print(f"🔍 DEBUG: Available Gain IDs: {[c.get('id') for c in gain_candidates]}")
            
            for gain_id in selections.get('gain', []):
                found = False
                for candidate in gain_candidates:
                    if ids_match(candidate.get('id'), gain_id):
                        selected_candidates['gain'].append(candidate)
                        found = True
                        print(f"✅ DEBUG: Found Gain match: {gain_id} -> {candidate.get('id')}")
                        break
                if not found:
                    print(f"🚨 DEBUG: Could not find Gain ID: {gain_id}")
            
            print(f"🔍 DEBUG: Mapped selections - JTBD: {len(selected_candidates['jtbd'])}, Pains: {len(selected_candidates['pain'])}, Gains: {len(selected_candidates['gain'])}")
            
            # Save the full objects to vpc_data
            success = await db_adapter.save_customer_profile_selections(
                project_id=project_id,
                selected_candidates=selected_candidates,
                user_id=user_id
            )
            
            if success:
                # 📊 WORKFLOW STATUS: Mark Customer Profile v1 as completed
                try:
                    from .workflow_status_service import get_workflow_status_service, WorkflowStage
                    # Get tenant_id from project
                    project_data = await self.db_adapter.get_project(project_id)
                    if project_data:
                        tenant_id = project_data.get('tenant_id')
                        if tenant_id:
                            workflow_service = get_workflow_status_service()
                            workflow_service.set_stage_completed(
                                project_id=project_id,
                                tenant_id=tenant_id,
                                stage=WorkflowStage.CUSTOMER_PROFILE_V1
                            )
                except Exception as status_error:
                    print(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
                
                return {
                    'success': True,
                    'message': 'Customer profile selections saved successfully',
                    'selected_candidates': selected_candidates
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save selections to database'
                }
                
        except Exception as e:
            print(f"Error in save_customer_profile_selections: {e}")
            return {'success': False, 'error': str(e)}

    async def generate_customer_profile_with_dual_context(
        self,
        project_id: str,
        context: Dict[str, Any],
        generation_request: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        STEP 1: Generate Customer Profile (JTBD, Pains, Gains) using dual context.
        Clean, focused method for customer profile generation only.
        """
        try:
            print(f"🔍 DEBUG: [STEP 1] Starting Customer Profile Generation")
            
            # Get project data for persona context (using same pattern as other methods)
            db_adapter = get_yuba_database_adapter()
            user_id_for_query = generation_request.get("user_id") or user_id
            print(f"🔍 DEBUG: [PERSONA_CONTEXT] Getting project data for project_id={project_id}, user_id={user_id_for_query}")
            project_data = await db_adapter.get_project_with_selections(project_id, user_id_for_query)
            
            # Get personas from the new personas column instead of vpc_data
            personas = await self.db_adapter.get_project_personas(project_id)
            
            if personas:
                print(f"🔍 DEBUG: [PERSONA_CONTEXT] Found {len(personas)} personas from database")
                for i, persona in enumerate(personas):
                    print(f"🔍 DEBUG: [PERSONA_CONTEXT] Persona {i+1}: {persona.get('name')} (ID: {persona.get('id')})")
            else:
                print(f"🔍 DEBUG: [PERSONA_CONTEXT] No personas found in database for project {project_id}")
                
            if not project_data:
                print(f"🔍 DEBUG: [PERSONA_CONTEXT] No project data found for project_id={project_id}, user_id={user_id_for_query}")
            
            # Initialize state for customer profile generation
            state = {}
            state["pv_report_context"] = context.get("pv_report_context", [])
            state["actionable_insights_context"] = context.get("actionable_insights_context", [])
            state["combined_context"] = context.get("combined_context", [])
            state["creativity_level"] = generation_request.get("creativity_level", 0.7)
            state["query"] = generation_request.get("query", "")
            
            # Transform context to format expected by original VMP service
            transformed_context = self._transform_context_for_vmp(context, project_data)
            print(f"🔍 DEBUG: [STEP 1] Generating Customer Profile with {len(context.get('combined_context', []))} context items")
            
            # Add persona context to the state for VMP service
            if personas:
                personas_context = f"""
IDENTIFIED PERSONAS:
The following personas have been identified as the key stakeholders who face this problem:

"""
                for i, persona in enumerate(personas, 1):
                    persona_id = persona.get('id', f'P{i}')
                    personas_context += f"""
{i}. {persona.get('name', 'Unknown Persona')} (ID: {persona_id})
   Description: {persona.get('description', 'No description available')}
   Problem Relationship: {persona.get('problem_relationship', 'No relationship defined')}
"""
                
                personas_context += f"""
CRITICAL REQUIREMENTS FOR PERSONA-SPECIFIC GENERATION:
1. Generate exactly 5 items per category (JTBD, Pains, Gains) - NOT 10!
2. MUST include the persona_id field in each item (use the exact IDs shown above: {', '.join([p.get('id', f'P{i+1}') for i, p in enumerate(personas)])})
3. For {len(personas)} personas, distribute items evenly: {5//len(personas)} items per persona minimum
4. Ensure items reflect the unique perspective and needs of each persona
5. Make the DESCRIPTION persona-specific, but keep LABELS clean without persona names
6. NEVER include persona names in the label - use persona_id field instead

EXAMPLE FORMAT:
{{
  "id": "jtbd-1",
  "type": "jtbd", 
  "label": "Access Fresh Produce Efficiently",
  "description": "Local footwear manufacturers need to manage their supply chain...",
  "persona_id": "{personas[0].get('id', 'P1')}",
  "evidence": [...],
  "confidence": 0.9
}}
"""
                
                # Add personas context to the transformed context
                transformed_context['personas_context'] = personas_context
                # CRITICAL: Also pass structured personas list to avoid fragile regex parsing
                transformed_context['personas_list'] = personas
                print(f"🔍 DEBUG: [STEP 1] Added persona context for {len(personas)} personas")
                print(f"🔍 DEBUG: [STEP 1] Personas context preview: {personas_context[:200]}...")
            
            # Generate customer profile using context data
            vpc_generator = self.vpc_generator
            vpc_generator.generate_customer_profile_with_context(state, transformed_context)
            
            # Extract customer profile candidates
            candidates_data = state.get("candidates", {})
            
            # DEBUG: Check what's actually in candidates_data from VMP service
            print(f"🔍 DEBUG: [STEP 1] candidates_data type: {type(candidates_data)}")
            print(f"🔍 DEBUG: [STEP 1] candidates_data keys: {list(candidates_data.keys()) if isinstance(candidates_data, dict) else 'Not a dict'}")
            if isinstance(candidates_data, dict):
                for key, value in candidates_data.items():
                    print(f"🔍 DEBUG: [STEP 1] candidates_data['{key}'] = {type(value)} with {len(value) if isinstance(value, (list, dict)) else 'unknown'} items")
                    if isinstance(value, list) and value:
                        print(f"🔍 DEBUG: [STEP 1] First item in {key}: {value[0] if value else 'empty'}")
            
            # Try different possible key names that VMP might use
            possible_keys = {
                'jobs_to_be_done': ['jtbd', 'jobs_to_be_done', 'job', 'jobs'],
                'pains': ['pain', 'pains'],
                'gains': ['gain', 'gains']
            }
            
            customer_profile = {'jobs_to_be_done': [], 'pains': [], 'gains': []}
            
            for profile_key, possible_candidate_keys in possible_keys.items():
                found = False
                for candidate_key in possible_candidate_keys:
                    if candidate_key in candidates_data and candidates_data[candidate_key]:
                        customer_profile[profile_key] = candidates_data[candidate_key]
                        print(f"✅ [STEP 1] Found {profile_key} data under key '{candidate_key}': {len(customer_profile[profile_key])} items")
                        found = True
                        break
                
                if not found:
                    print(f"🚨 [STEP 1] No data found for {profile_key} in any of these keys: {possible_candidate_keys}")
            
            print(f"✅ [STEP 1] Customer Profile Generated - JTBD: {len(customer_profile['jobs_to_be_done'])}, Pains: {len(customer_profile['pains'])}, Gains: {len(customer_profile['gains'])}")
            
            # Add persona information to response (using same data structure as above)
            personas_info = []
            if project_data:
                # Use personas from database for response metadata
                if personas:
                    personas_info = [
                        {
                            'id': persona.get('id', f'P{i+1}'),
                            'name': persona.get('name', 'Unknown Persona'),
                            'description': persona.get('description', ''),
                            'problem_relationship': persona.get('problem_relationship', '')
                        }
                        for i, persona in enumerate(personas)
                    ]
            
            return {
                'customer_profile': customer_profile,
                'generation_metadata': {
                    'model_used': 'original_vmp',
                    'context_items_used': len(context.get('combined_context', [])),
                    'generation_time': datetime.utcnow().isoformat(),
                    'generation_type': 'customer_profile',
                    'total_candidates': sum(len(candidates_data.get(k, [])) for k in ['jtbd', 'pain', 'gain']),
                    'personas': personas_info,
                    'multi_persona': len(personas_info) > 1,
                    'persona_driven_generation': len(personas_info) > 0
                }
            }
                
        except Exception as e:
            raise Exception(f"Failed to generate customer profile: {str(e)}")

    async def save_multi_persona_customer_profile_selections(
        self,
        project_id: str,
        persona_selections: Dict[str, Dict[str, List[str]]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Save customer profile selections for multi-persona projects.
        
        Args:
            project_id: VMP project ID
            persona_selections: {'P1': {'jtbd': [...], 'pain': [...], 'gain': [...]}, 'P2': {...}}
            user_id: User ID for security
        """
        try:
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Starting multi-persona selection save")
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Personas: {list(persona_selections.keys())}")
            
            # Get the latest customer profile artifacts to map IDs to full objects
            artifacts_result = await self.db_adapter.get_latest_vpc_artifacts(project_id, 'customer_profile')
            if not artifacts_result:
                return {'success': False, 'error': 'No customer profile artifacts found'}
            
            # Extract candidates from artifacts
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Raw artifacts_result keys: {list(artifacts_result.keys()) if artifacts_result else 'None'}")
            
            # The actual data is in the 'content' field, not 'artifact'
            artifacts_content = artifacts_result.get('content', {})
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] artifacts_content type: {type(artifacts_content)}")
            
            # If content is a string (JSON), parse it
            if isinstance(artifacts_content, str):
                import json
                try:
                    artifacts_content = json.loads(artifacts_content)
                    print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Parsed JSON content keys: {list(artifacts_content.keys()) if isinstance(artifacts_content, dict) else 'Not a dict'}")
                except json.JSONDecodeError as e:
                    print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Failed to parse JSON content: {e}")
                    artifacts_content = {}
            
            # Try to find the customer profile data - it's nested under customer_profile_candidates
            customer_profile_candidates = artifacts_content.get('customer_profile_candidates', {})
            customer_profile_data = customer_profile_candidates.get('customer_profile', {})
            
            if not customer_profile_data:
                # Fallback: try direct access
                customer_profile_data = artifacts_content.get('customer_profile', {})
                if not customer_profile_data:
                    # Last resort: try artifacts_content directly
                    customer_profile_data = artifacts_content
            
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] customer_profile_data keys: {list(customer_profile_data.keys()) if isinstance(customer_profile_data, dict) else 'Not a dict'}")
            
            all_candidates = {
                'jtbd': customer_profile_data.get('jobs_to_be_done', []),
                'pain': customer_profile_data.get('pains', []),
                'gain': customer_profile_data.get('gains', [])
            }
            
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Found {sum(len(v) for v in all_candidates.values())} total candidates")
            
            # Debug: Show available IDs
            for category, items in all_candidates.items():
                if items:
                    ids = [item.get('id', 'NO_ID') for item in items[:3]]  # Show first 3 IDs
                    print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Available {category} IDs (first 3): {ids}")
                else:
                    print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] No {category} items found")
            
            # Map selected IDs to full objects for each persona
            persona_selected_objects = {}
            for persona_id, selections in persona_selections.items():
                persona_selected_objects[persona_id] = {'jtbd': [], 'pain': [], 'gain': []}
                
                for category, selected_ids in selections.items():
                    candidates_list = all_candidates.get(category, [])
                    
                    for selected_id in selected_ids:
                        # Find the full object by ID
                        found_item = None
                        for candidate in candidates_list:
                            if candidate.get('id') == selected_id:
                                found_item = candidate
                                break
                        
                        if found_item:
                            persona_selected_objects[persona_id][category].append(found_item)
                            print(f"✅ DEBUG: [SAVE_MULTI_PERSONA] Mapped {selected_id} to {persona_id}.{category}")
                        else:
                            print(f"⚠️ DEBUG: [SAVE_MULTI_PERSONA] Could not find {selected_id} in {category} candidates")
            
            # Save using the existing database adapter with persona-aware logic
            # Convert to format expected by save_customer_profile_selections
            combined_selections = {'jtbd': [], 'pain': [], 'gain': []}
            for persona_id, persona_objects in persona_selected_objects.items():
                for category, items in persona_objects.items():
                    combined_selections[category].extend(items)
            
            print(f"🔍 DEBUG: [SAVE_MULTI_PERSONA] Combined selections: JTBD={len(combined_selections['jtbd'])}, Pain={len(combined_selections['pain'])}, Gain={len(combined_selections['gain'])}")
            
            # Save to database (the database adapter will handle multi-persona grouping)
            success = await self.db_adapter.save_customer_profile_selections(
                project_id=project_id,
                selected_candidates=combined_selections,
                user_id=user_id
            )
            
            if success:
                return {
                    'success': True,
                    'data': {
                        'project_id': project_id,
                        'personas_updated': list(persona_selections.keys()),
                        'total_selections': sum(len(v) for persona in persona_selections.values() for v in persona.values())
                    }
                }
            else:
                return {'success': False, 'error': 'Failed to save selections to database'}
                
        except Exception as e:
            print(f"Error in save_multi_persona_customer_profile_selections: {e}")
            return {'success': False, 'error': str(e)}

    async def generate_value_map_with_dual_context(
        self,
        project_id: str,
        context: Dict[str, Any],
        generation_request: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        STEP 2: Generate Value Map (Products/Services, Pain Relievers, Gain Creators) using dual context.
        Clean, focused method for value map generation only.
        """
        try:
            print(f"🔍 DEBUG: [STEP 2] Starting Value Map Generation")
            
            # Initialize state for value map generation
            state = {}
            state["pv_report_context"] = context.get("pv_report_context", [])
            state["actionable_insights_context"] = context.get("actionable_insights_context", [])
            state["combined_context"] = context.get("combined_context", [])
            state["creativity_level"] = generation_request.get("creativity_level", 0.7)
            state["query"] = generation_request.get("query", "")
            
            # Get project data to extract PV report ID and customer profile selections
            db_adapter = get_yuba_database_adapter()
            user_id_for_query = generation_request.get("user_id") or user_id
            project_data = await db_adapter.get_project_with_selections(project_id, user_id_for_query)
            
            if project_data:
                # Add report_id for VPM service
                report_id = project_data.get("pv_report_id")
                parent_project_id = project_data.get("parent_project_id")
                
                if report_id:
                    state["report_id"] = report_id
                    print(f"🔍 DEBUG: [STEP 2] Set report_id: {report_id}")
                    
                    # Fix data integrity issues
                    if parent_project_id:
                        await self._fix_pv_report_project_id(report_id, parent_project_id)
                        await self._fix_actionable_insights_project_id(report_id, parent_project_id)
                
                # CRITICAL: Add customer profile selections for value map generation
                vpc_data = project_data.get("vpc_data", {})
                customer_profile = vpc_data.get("customer_profile", {})
                if customer_profile:
                    # Format selections for VPM service (EXACTLY what it expects)
                    selections = {
                        "jtbd": customer_profile.get("jobs_to_be_done", []),
                        "pain": customer_profile.get("pains", []),
                        "gain": customer_profile.get("gains", [])
                    }
                    
                    state["selections"] = selections  # VPM service expects this key
                    print(f"🔍 DEBUG: [STEP 2] Customer profile selections loaded:")
                    print(f"🔍 DEBUG: [STEP 2] - JTBD: {len(selections['jtbd'])} items")
                    print(f"🔍 DEBUG: [STEP 2] - Pains: {len(selections['pain'])} items")
                    print(f"🔍 DEBUG: [STEP 2] - Gains: {len(selections['gain'])} items")
                else:
                    print(f"⚠️ [STEP 2] No customer profile selections found - value map generation may fail")
            
            # Transform context for VMP service
            transformed_context = self._transform_context_for_vmp(context, project_data)
            
            # Add context directly to state for robust generation
            state["pv_report_content"] = transformed_context.get("pv_report", "")
            state["actionable_insights_content"] = transformed_context.get("actionable_insights", "")
            state["context_provided"] = True
            
            print(f"🔍 DEBUG: [STEP 2] Context: PV Report ({len(state['pv_report_content'])} chars), Insights ({len(state['actionable_insights_content'])} chars)")
            
            # Generate VALUE MAP using original VPM service
            vpc_generator = self.vpc_generator
            print(f"🔍 DEBUG: [STEP 2] Calling generate_value_map_concurrent...")
            vpc_generator.generate_value_map_concurrent(state)
            
            # Extract value map candidates
            vm_candidates = state.get("vm_candidates", {})
            
            print(f"🔍 DEBUG: [STEP 2] FULL STATE KEYS: {list(state.keys())}")
            print(f"🔍 DEBUG: [STEP 2] vm_candidates keys: {list(vm_candidates.keys())}")
            
            # Check if we have any candidates at all
            if not vm_candidates:
                print(f"🚨 DEBUG: [STEP 2] vm_candidates is EMPTY! Checking for other candidate keys...")
                for key in state.keys():
                    if 'candidate' in key.lower():
                        print(f"🔍 DEBUG: [STEP 2] Found alternative candidate key: {key} = {type(state[key])}")
                        if isinstance(state[key], dict):
                            print(f"🔍 DEBUG: [STEP 2] {key} contents: {list(state[key].keys())}")
            
            for key, items in vm_candidates.items():
                print(f"🔍 DEBUG: [STEP 2] {key}: {len(items)} items")
                if items and len(items) > 0:
                    print(f"🔍 DEBUG: [STEP 2] First {key} item: {items[0].get('label', 'No label')}")
                    print(f"🔍 DEBUG: [STEP 2] First {key} item type: {items[0].get('type', 'No type')}")
            
            value_map = {
                'products_services': vm_candidates.get('product_service', []),
                'pain_relievers': vm_candidates.get('pain_reliever', []),
                'gain_creators': vm_candidates.get('gain_creator', [])
            }
            
            # CRITICAL DEBUG: Check if we're getting customer profile data instead
            if not any(value_map.values()) and state.get("candidates"):
                print(f"🚨 DEBUG: [STEP 2] No vm_candidates but found 'candidates' - VPM service returned wrong data type!")
                print(f"🔍 DEBUG: [STEP 2] candidates keys: {list(state['candidates'].keys())}")
                print(f"🚨 DEBUG: [STEP 2] This means VPM service generated customer profile instead of value map!")
            
            print(f"✅ [STEP 2] Value Map Generated - Products: {len(value_map['products_services'])}, Pain Relievers: {len(value_map['pain_relievers'])}, Gain Creators: {len(value_map['gain_creators'])}")
            
            # CRITICAL: Return the value map data directly, not wrapped in another structure
            return {
                'value_map': value_map,
                'generation_metadata': {
                    'model_used': 'original_vmp',
                    'context_items_used': len(context.get('combined_context', [])),
                    'generation_time': datetime.utcnow().isoformat(),
                    'generation_type': 'value_map',
                    'total_candidates': sum(len(value_map.get(k, [])) for k in ['products_services', 'pain_relievers', 'gain_creators'])
                }
            }
                
        except Exception as e:
            raise Exception(f"Failed to generate value map: {str(e)}")

    async def _fix_pv_report_project_id(self, report_id: str, parent_project_id: str) -> bool:
        """
        ROOT CAUSE FIX: Update the PV report to include the parent_project_id.
        This fixes the data integrity issue that prevents value map generation.
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            # Update the PV report document to include the project_id
            result = supabase.client.table('documents').update({
                'project_id': parent_project_id
            }).eq('id', report_id).eq('source_type', 'pv_report').execute()
            
            if result.data:
                print(f"✅ FIXED: Updated PV report {report_id} with project_id {parent_project_id}")
                return True
            else:
                print(f"❌ FAILED: Could not update PV report {report_id}")
                return False
                
        except Exception as e:
            print(f"Error fixing PV report project_id: {e}")
            return False

    async def _fix_actionable_insights_project_id(self, report_id: str, parent_project_id: str) -> bool:
        """
        Fix actionable insights project_id linkage.
        Updates actionable insights that are linked to the PV report to use the correct project_id.
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            # Update actionable insights documents that are linked to this PV report
            result = supabase.client.table('documents').update({
                'project_id': parent_project_id
            }).eq('source_document_id', report_id).eq('source_type', 'actionable_insights').execute()
            
            if result.data:
                print(f"✅ FIXED: Updated {len(result.data)} actionable insights with project_id {parent_project_id}")
                return True
            else:
                print(f"⚠️  No actionable insights found linked to report {report_id}")
                return True  # Not an error, just no linked insights
                
        except Exception as e:
            print(f"Error fixing actionable insights project_id: {e}")
            return False

    async def _save_vpc_artifacts(
        self,
        project_id: str,
        generation_type: str,
        vpc_result: Dict[str, Any],
        user_id: str
    ) -> bool:
        """
        Save VPC generation artifacts to the database for later selection.
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            # Determine artifact type and data structure
            if generation_type == "customer_profile":
                artifact_type = "customer_profile"
                artifact_data = {
                    "customer_profile_candidates": vpc_result
                }
            elif generation_type == "value_map":
                artifact_type = "value_map"
                artifact_data = {
                    "value_map_candidates": vpc_result
                }
            else:
                artifact_type = "vpc_canvas"
                artifact_data = vpc_result
            
            # Save to vmp_vpc_artifacts table
            result = supabase.client.table('vmp_vpc_artifacts').insert({
                'project_id': project_id,
                'artifact_type': artifact_type,
                'title': f"{generation_type.replace('_', ' ').title()} Candidates",
                'content': artifact_data,
                'created_by': user_id,
                'version': 1,
                'metadata': {
                    'generation_type': generation_type,
                    'created_at': datetime.utcnow().isoformat()
                }
            }).execute()
            
            print(f"🔍 DEBUG: Saved {artifact_type} artifacts for project {project_id}")
            return bool(result.data)
            
        except Exception as e:
            print(f"Error saving VPC artifacts: {e}")
            return False

    async def save_value_map_selections(
        self,
        project_id: str,
        selections: Dict[str, List[str]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Save value map selections (Step 2 completion).
        
        This stores the user's selected Products/Services, Pain Relievers, and Gain Creators
        and merges them with existing customer profile selections in vpc_data.
        """
        try:
            # First, get the generated value map candidates to map IDs to full objects
            db_adapter = get_yuba_database_adapter()
            
            # Get the last generated value map candidates from vpc_artifacts
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            artifacts_result = supabase.client.table('vmp_vpc_artifacts').select('*').eq(
                'project_id', project_id
            ).eq('artifact_type', 'value_map').order('created_at', desc=True).limit(1).execute()
            
            if not artifacts_result.data:
                return {
                    'success': False,
                    'error': 'No value map candidates found. Please generate value map first.'
                }
            
            # Extract candidates from the artifact
            candidates_data = artifacts_result.data[0]['content']
            print(f"🔍 DEBUG: Candidates data keys: {list(candidates_data.keys())}")
            print(f"🔍 DEBUG: Raw candidates_data: {candidates_data}")
            
            value_map_candidates = candidates_data.get('value_map_candidates', {})
            print(f"🔍 DEBUG: value_map_candidates type: {type(value_map_candidates)}")
            print(f"🔍 DEBUG: value_map_candidates keys: {list(value_map_candidates.keys()) if isinstance(value_map_candidates, dict) else 'Not a dict'}")
            
            all_candidates = value_map_candidates.get('value_map', {}) if isinstance(value_map_candidates, dict) else {}
            print(f"🔍 DEBUG: All candidates keys: {list(all_candidates.keys())}")
            print(f"🔍 DEBUG: Products services count: {len(all_candidates.get('products_services', []))}")
            print(f"🔍 DEBUG: Pain relievers count: {len(all_candidates.get('pain_relievers', []))}")
            print(f"🔍 DEBUG: Gain creators count: {len(all_candidates.get('gain_creators', []))}")
            
            # Map selected IDs to full objects
            selected_candidates = {
                'product_service': [],
                'pain_reliever': [],
                'gain_creator': []
            }
            
            # Helper function to normalize IDs for matching
            def normalize_id(id_value):
                """Normalize ID by removing prefixes and converting to string"""
                if isinstance(id_value, str):
                    # Remove common prefixes like 'product-', 'pain-', 'gain-'
                    for prefix in ['product-', 'pain-', 'gain-']:
                        if id_value.startswith(prefix):
                            return id_value[len(prefix):]
                    return id_value
                return str(id_value)
            
            def ids_match(id1, id2):
                """Check if two IDs match after normalization"""
                return normalize_id(id1) == normalize_id(id2)
            
            # Map Products/Services selections
            print(f"🔍 DEBUG: Looking for product service IDs: {selections.get('selected_product_service_ids', [])}")
            products_services = all_candidates.get('products_services', [])
            print(f"🔍 DEBUG: Available product service IDs: {[c.get('id') for c in products_services]}")
            
            for selected_id in selections.get('selected_product_service_ids', []):
                found = False
                for candidate in products_services:
                    if ids_match(candidate.get('id'), selected_id):
                        selected_candidates['product_service'].append(candidate)
                        found = True
                        print(f"✅ DEBUG: Found product service match: {selected_id} -> {candidate.get('id')}")
                        break
                if not found:
                    print(f"🚨 DEBUG: Could not find product service ID: {selected_id}")
            
            # Map Pain Relievers selections
            for selected_id in selections.get('selected_pain_reliever_ids', []):
                found = False
                for candidate in all_candidates.get('pain_relievers', []):
                    if ids_match(candidate.get('id'), selected_id):
                        selected_candidates['pain_reliever'].append(candidate)
                        found = True
                        print(f"✅ DEBUG: Found pain reliever match: {selected_id} -> {candidate.get('id')}")
                        break
                if not found:
                    print(f"🚨 DEBUG: Could not find pain reliever ID: {selected_id}")
            
            # Map Gain Creators selections
            for selected_id in selections.get('selected_gain_creator_ids', []):
                found = False
                for candidate in all_candidates.get('gain_creators', []):
                    if ids_match(candidate.get('id'), selected_id):
                        selected_candidates['gain_creator'].append(candidate)
                        found = True
                        print(f"✅ DEBUG: Found gain creator match: {selected_id} -> {candidate.get('id')}")
                        break
                if not found:
                    print(f"🚨 DEBUG: Could not find gain creator ID: {selected_id}")
            
            print(f"🔍 DEBUG: Mapped value map selections - Products: {len(selected_candidates['product_service'])}, Pain Relievers: {len(selected_candidates['pain_reliever'])}, Gain Creators: {len(selected_candidates['gain_creator'])}")
            
            # Save value map selections (this will merge with existing customer profile in vpc_data)
            success = await db_adapter.save_value_map_selections(
                project_id=project_id,
                selected_candidates=selected_candidates,
                user_id=user_id
            )
            
            if success:
                return {
                    'success': True,
                    'data': {
                        'project_id': project_id,
                        'step_completed': 2,
                        'selections_saved': {
                            'product_service_count': len(selected_candidates['product_service']),
                            'pain_reliever_count': len(selected_candidates['pain_reliever']),
                            'gain_creator_count': len(selected_candidates['gain_creator'])
                        }
                    },
                    'message': 'Value map selections saved successfully. VPC is now complete.',
                    'next_step': f'/api/v2/vmp/projects/{project_id}/vpc/step3/compose-final-vpc'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save selections to database'
                }
                
        except Exception as e:
            print(f"Error in save_value_map_selections: {e}")
            return {'success': False, 'error': str(e)}

    async def compose_final_vpc(
        self,
        project_id: str,
        composition_options: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        STEP 3: Compose final VPC from vpc_data column.
        
        Retrieves the complete Value Proposition Canvas from the vpc_data column
        which contains both customer profile and value map selections.
        """
        try:
            print(f"🔍 DEBUG: [STEP 3] Composing final VPC for project {project_id}")
            
            # Get complete project data including vpc_data
            db_adapter = get_yuba_database_adapter()
            project_data = await db_adapter.get_project_with_selections(project_id, user_id)
            
            if not project_data:
                return {
                    'success': False,
                    'error': 'Project not found'
                }
            
            # Get the complete VPC data from the vpc_data column
            vpc_data = project_data.get('vpc_data', {})
            print(f"🔍 DEBUG: [STEP 3] Raw project_data keys: {list(project_data.keys())}")
            print(f"🔍 DEBUG: [STEP 3] vpc_data type: {type(vpc_data)}")
            print(f"🔍 DEBUG: [STEP 3] vpc_data content: {vpc_data}")
            
            if vpc_data:
                print(f"🔍 DEBUG: [STEP 3] VPC data keys: {list(vpc_data.keys())}")
            else:
                print(f"🔍 DEBUG: [STEP 3] vpc_data is empty or None")
            
            if not vpc_data:
                return {
                    'success': False,
                    'error': 'No VPC data found. Please complete Steps 1 and 2 first.'
                }
            
            # Validate that both customer profile and value map exist
            customer_profile = vpc_data.get('customer_profile', {})
            value_map = vpc_data.get('value_map', {})
            
            print(f"🔍 DEBUG: [STEP 3] Customer profile keys: {list(customer_profile.keys())}")
            print(f"🔍 DEBUG: [STEP 3] Value map keys: {list(value_map.keys())}")
            
            # Check if customer profile has the required sections
            has_customer_profile = (
                customer_profile.get('jobs_to_be_done') or 
                customer_profile.get('pains') or 
                customer_profile.get('gains')
            )
            
            # Check if value map has the required sections  
            has_value_map = (
                value_map.get('products_services') or
                value_map.get('pain_relievers') or
                value_map.get('gain_creators')
            )
            
            # Debug value map contents
            print(f"🔍 DEBUG: [STEP 3] Products/Services count: {len(value_map.get('products_services', []))}")
            print(f"🔍 DEBUG: [STEP 3] Pain Relievers count: {len(value_map.get('pain_relievers', []))}")
            print(f"🔍 DEBUG: [STEP 3] Gain Creators count: {len(value_map.get('gain_creators', []))}")
            
            print(f"🔍 DEBUG: [STEP 3] Has customer profile: {bool(has_customer_profile)}")
            print(f"🔍 DEBUG: [STEP 3] Has value map: {bool(has_value_map)}")
            
            if not has_customer_profile:
                return {
                    'success': False,
                    'error': 'Customer profile selections missing. Please complete Step 1.'
                }
                
            if not has_value_map:
                return {
                    'success': False,
                    'error': 'Value map selections missing. Please complete Step 2. No products/services, pain relievers, or gain creators found.'
                }
            
            # Create the final VPC structure
            final_vpc = {
                'customer_profile': customer_profile,
                'value_map': value_map,
                'project_metadata': {
                    'project_id': project_id,
                    'project_name': project_data.get('name', 'Untitled Project'),
                    'project_description': project_data.get('description', ''),
                    'pv_report_id': project_data.get('pv_report_id'),
                    'created_at': project_data.get('created_at'),
                    'updated_at': project_data.get('updated_at')
                },
                'composition_metadata': {
                    'composed_at': datetime.utcnow().isoformat(),
                    'composition_options': composition_options,
                    'step_completed': 3,
                    'workflow_status': 'completed'
                }
            }
            
            # Count selections for summary
            customer_profile_count = (
                len(customer_profile.get('jobs_to_be_done', [])) +
                len(customer_profile.get('pains', [])) +
                len(customer_profile.get('gains', []))
            )
            
            value_map_count = (
                len(value_map.get('products_services', [])) +
                len(value_map.get('pain_relievers', [])) +
                len(value_map.get('gain_creators', []))
            )
            
            print(f"✅ [STEP 3] Final VPC composed - Customer Profile: {customer_profile_count} items, Value Map: {value_map_count} items")
            
            return {
                'success': True,
                'message': f'Final VPC composed successfully with {customer_profile_count + value_map_count} total selections',
                'vpc_data': final_vpc,
                'summary': {
                    'customer_profile_items': customer_profile_count,
                    'value_map_items': value_map_count,
                    'total_selections': customer_profile_count + value_map_count,
                    'workflow_completed': True
                }
            }
            
        except Exception as e:
            print(f"Error composing final VPC: {e}")
            return {'success': False, 'error': str(e)}

    async def get_vpc_workflow_status(
        self,
        project_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get the current status of the VPC workflow.
        
        Returns which step the user is on and what has been completed.
        """
        try:
            db_adapter = get_yuba_database_adapter()
            project_data = await db_adapter.get_project_with_selections(project_id, user_id)
            
            if not project_data:
                return {
                    'success': False,
                    'error': 'Project not found'
                }
            
            # Determine current step based on completed selections
            customer_profile_complete = bool(project_data.get('customer_profile_selections'))
            value_map_complete = bool(project_data.get('value_map_selections'))
            final_vpc_complete = bool(project_data.get('final_vpc'))
            
            if final_vpc_complete:
                current_step = "completed"
                next_action = None
            elif value_map_complete:
                current_step = 3
                next_action = "compose_final_vpc"
            elif customer_profile_complete:
                current_step = 2
                next_action = "generate_value_map"
            else:
                current_step = 1
                next_action = "generate_customer_profile"
            
            status = {
                'current_step': current_step,
                'next_action': next_action,
                'step_completion': {
                    'customer_profile': customer_profile_complete,
                    'value_map': value_map_complete,
                    'final_vpc': final_vpc_complete
                },
                'project_id': project_id
            }
            
            return {
                'success': True,
                'status': status
            }
            
        except Exception as e:
            print(f"Error getting VPC workflow status: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_formatted_problem_statement(self, executive_summary: str) -> str:
        """
        Generate properly formatted problem statement using LLM.
        Uses Approach 1: LLM Transformation with structured output.
        
        Args:
            executive_summary: Full executive summary text from PV report
            
        Returns:
            Properly formatted problem statement following required formats
        """
        if not executive_summary or not executive_summary.strip():
            return "Problem statement not available"
        
        try:
            print(f"🤖 DEBUG: Starting LLM problem statement generation...")
            
            # Import AI service (VPM's AI service)
            from VPM.core.ai_service import AIService
            
            ai_service = AIService()
            print(f"✅ DEBUG: AIService initialized")
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": PROBLEM_STATEMENT_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": PROBLEM_STATEMENT_USER_PROMPT.format(
                        executive_summary=executive_summary[:2000]  # Limit to first 2000 chars
                    )
                }
            ]
            print(f"✅ DEBUG: Messages prepared, calling LLM...")
            
            # Define JSON schema for structured output
            schema = {
                "type": "object",
                "properties": {
                    "problem_statement": {
                        "type": "string",
                        "description": "The formatted problem statement"
                    },
                    "format_used": {
                        "type": "string",
                        "description": "Which format was used (1, 2, 3, or 4)"
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "Who faces the problem"
                    },
                    "core_problem": {
                        "type": "string",
                        "description": "What the problem/gap is"
                    },
                    "impact": {
                        "type": "string",
                        "description": "What they're prevented from achieving"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0.0-1.0"
                    }
                },
                "required": ["problem_statement", "format_used"]
            }
            
            # Create monitoring context for AI usage tracking
            monitoring_context = None
            try:
                from monitor.tokens.models import AIUsageContext
                monitoring_context = AIUsageContext(
                    user_id=None,
                    tenant_id=None,
                    project_id=None,  # Not available in this context
                    feature_id="vpm_problem_statement_generation",
                    workflow_name="vpm_project_creation",
                    step_name="format_problem_statement",
                    environment="prod"
                )
            except ImportError:
                pass
            
            # Generate using AI (synchronous call) with monitoring
            print(f"🤖 Generating formatted problem statement using LLM...")
            result = ai_service.chat_json(messages, schema, monitoring_context=monitoring_context)
            
            problem_statement = result.get('problem_statement', '').strip()
            format_used = result.get('format_used', 'unknown')
            confidence = result.get('confidence', 0.0)
            
            print(f"✅ Generated problem statement (Format {format_used}, Confidence: {confidence:.2f})")
            print(f"   Statement: {problem_statement[:100]}...")
            
            # Validate output
            if not problem_statement or len(problem_statement) < 20:
                raise ValueError("Generated statement too short")
            
            # Ensure reasonable length (max 500 chars)
            if len(problem_statement) > 500:
                problem_statement = problem_statement[:497] + "..."
            
            return problem_statement
            
        except Exception as e:
            print(f"❌ ERROR: LLM problem statement generation failed: {e}")
            print(f"❌ ERROR type: {type(e).__name__}")
            import traceback
            print(f"❌ ERROR traceback: {traceback.format_exc()}")
            
            # Re-raise the exception to see the actual error
            raise
    
    def _extract_problem_statement_from_summary_fallback(self, executive_summary: str) -> str:
        """
        Fallback method: Extract first 1-2 sentences as problem statement.
        Used when LLM generation fails.
        
        Args:
            executive_summary: Full executive summary text
            
        Returns:
            Extracted problem statement (first 1-2 sentences)
        """
        if not executive_summary or not executive_summary.strip():
            return "Problem statement not available"
        
        # Clean the text
        text = executive_summary.strip()
        
        # Split into sentences (handle multiple sentence endings)
        import re
        sentences = re.split(r'\.(?:\s+(?=[A-Z])|$)', text)
        
        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return text[:200] + "..." if len(text) > 200 else text
        
        # Take first 1-2 sentences
        if len(sentences) == 1:
            problem_statement = sentences[0]
            if not problem_statement.endswith('.'):
                problem_statement += '.'
        else:
            problem_statement = f"{sentences[0]}. {sentences[1]}."
        
        # Ensure reasonable length (max 500 chars)
        if len(problem_statement) > 500:
            problem_statement = problem_statement[:497] + "..."
        
        return problem_statement


# Singleton instance
_integrated_vmp_service_instance = None

def get_integrated_vmp_service() -> IntegratedVPMService:
    """Get singleton instance of integrated VPM service"""
    global _integrated_vmp_service_instance
    if _integrated_vmp_service_instance is None:
        _integrated_vmp_service_instance = IntegratedVPMService()
    return _integrated_vmp_service_instance
