"""
Field Prep Service for VPM Integration

Handles the Field Research Preparation workflow that follows VPC generation.
Integrates with Yuba's existing systems while leveraging the original VPM Field Prep logic.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import sys
import os

# Add VPM directory to Python path
vpm_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'VPM')
vpm_path = os.path.abspath(vpm_path)
if vpm_path not in sys.path:
    sys.path.insert(0, vpm_path)

# Import Yuba adapters
from ..adapters.auth_adapter import YubaAuthAdapter
from ..adapters.database_adapter import YubaDatabaseAdapter
from ..adapters.vector_adapter import YubaVectorAdapter

# Import Field Prep models
from ..models.field_prep import (
    HYPOTHESIS_SCHEMA, ASSUMPTION_SCHEMA, STAKEHOLDER_ASSIGNMENT_SCHEMA, 
    StakeholderType, FieldPrepStage
)

# Import original VPM Field Prep service (required)
try:
    from Field_Prep.services import FieldPrepService
    from core.session_manager import GraphState
    print("✅ Successfully loaded original Field Prep service")
except ImportError as e:
    raise ImportError(f"❌ Original Field Prep service is required but not available: {e}")
except Exception as e:
    raise Exception(f"❌ Failed to initialize Field Prep service: {e}")


class YubaFieldPrepService:
    """
    Field Prep service integrated with Yuba systems.
    
    This service bridges the original VPM Field Prep functionality with Yuba's
    authentication, credit system, and database infrastructure.
    """
    
    def __init__(self, auth_adapter, db_adapter, vector_adapter, credit_adapter=None):
        self.auth_adapter = auth_adapter
        self.db_adapter = db_adapter
        self.vector_adapter = vector_adapter
        # credit_adapter is optional and not used anymore
        
        # Initialize original Field Prep service
        self.original_field_prep = FieldPrepService()
        self.GraphState = GraphState
    
    async def generate_hypothesis(
        self, 
        project_id: str, 
        user_id: str, 
        creativity_level: float = 0.7,
        tenant_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate market hypothesis based on PERSONAS and CUSTOMER PROFILE only.
        
        NEW WORKFLOW: Uses Personas + Customer Profile + PV Report + Actionable Insights as context.
        NO VALUE MAP OR VPC REQUIRED - hypothesis generation happens after customer profile selection.
        """
        try:
            # Get tenant_id if not provided
            if not tenant_id:
                # Try to get tenant_id from user
                from ..api.endpoints import get_user_tenant_id
                tenant_id = await get_user_tenant_id(user_id)
                if not tenant_id:
                    return {
                        'success': False,
                        'error': 'Could not determine user tenant'
                    }
            
            # Get project context (Personas + Customer Profile + dual vector store)
            print(f"🔍 DEBUG: [NEW WORKFLOW] Getting project context for project_id: {project_id}")
            project_context = await self._get_project_context_personas_only(project_id, tenant_id)
            if not project_context['success']:
                print(f"❌ DEBUG: Failed to get project context: {project_context.get('error')}")
                return project_context
            
            print(f"✅ DEBUG: Project context retrieved successfully")
            print(f"🔍 DEBUG: Project context keys: {list(project_context['data'].keys())}")
            
            # Check if personas are identified and customer profile is selected
            personas_data = project_context['data'].get('personas')
            customer_profile = project_context['data'].get('customer_profile')
            
            if not personas_data:
                print(f"❌ DEBUG: No personas found in project context")
                return {
                    'success': False,
                    'error': "Personas must be identified before generating hypothesis"
                }
            
            if not customer_profile:
                print(f"❌ DEBUG: No customer profile found in project context")
                return {
                    'success': False,
                    'error': "Customer profile must be selected before generating hypothesis"
                }
            
            print(f"✅ DEBUG: Found {len(personas_data)} personas and customer profile data")
            print(f"🔍 DEBUG: Personas: {[p.get('name', 'Unnamed') for p in personas_data]}")
            
            # Generate one hypothesis per persona
            hypotheses = []
            for i, persona in enumerate(personas_data):
                print(f"🔍 DEBUG: Generating hypothesis for persona {i+1}: {persona.get('name', 'Unnamed')}")
                
                hypothesis = await self._generate_single_hypothesis_for_persona(
                    project_id=project_id,
                    persona=persona,
                    customer_profile=customer_profile,
                    context=project_context['data'],
                    creativity_level=creativity_level,
                    hypothesis_number=i+1  # Pass sequential number
                )
                
                if hypothesis:
                    hypotheses.append(hypothesis)
                    print(f"✅ DEBUG: Generated hypothesis for persona {persona.get('name', 'Unnamed')}")
                else:
                    print(f"❌ DEBUG: Failed to generate hypothesis for persona {persona.get('name', 'Unnamed')}")
            
            if not hypotheses:
                return {
                    'success': False,
                    'error': "Failed to generate any hypotheses for the identified personas"
                }
            
            # Store hypotheses in project
            print(f"🔍 DEBUG: [SAVE_HYPOTHESES] Attempting to save {len(hypotheses)} hypotheses to project {project_id}")
            save_result = await self._save_hypotheses_to_project(project_id, hypotheses, user_id)
            if save_result:
                print(f"✅ DEBUG: [SAVE_HYPOTHESES] Successfully saved {len(hypotheses)} hypotheses to database")
            else:
                print(f"❌ DEBUG: [SAVE_HYPOTHESES] Failed to save hypotheses to project, but continuing...")
            
            return {
                'success': True,
                'hypotheses': hypotheses,
                'total_hypotheses': len(hypotheses),
                'personas_count': len(personas_data),
                'message': f"Generated {len(hypotheses)} hypothesis(es) for {len(personas_data)} persona(s)"
            }
            
        except Exception as e:
            print(f"❌ ERROR: Hypothesis generation failed: {str(e)}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Failed to generate hypothesis: {str(e)}"
            }
    
    async def _get_project_context_personas_only(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Get project context with personas and customer profile only (no VPC required).
        """
        try:
            # Get project data from database
            project_data = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project_data:
                return {
                    'success': False,
                    'error': "Project not found"
                }
            
            # Extract personas using the same method as integrated VMP service
            personas = await self.db_adapter.get_project_personas(project_id)
            print(f"🔍 DEBUG: [FIELD_PREP] Retrieved {len(personas)} personas for project {project_id}")
            if personas:
                print(f"🔍 DEBUG: [FIELD_PREP] Persona names: {[p.get('name', 'Unnamed') for p in personas]}")
            
            # Extract customer profile from vpc_data (supports multiple formats)
            vpc_data = project_data.get('vpc_data', {})
            print(f"🔍 DEBUG: [FIELD_PREP] VPC data keys: {list(vpc_data.keys())}")
            
            # Initialize combined customer profile
            combined_customer_profile = {
                'jtbd': [],
                'pains': [],
                'gains': []
            }
            
            # FORMAT 1: New nested structure - vpc_data.vpcs.P1.customer_profile
            vpcs = vpc_data.get('vpcs', {})
            print(f"🔍 DEBUG: [FIELD_PREP] VPCs available: {list(vpcs.keys())}")
            
            for persona_id, vpc_info in vpcs.items():
                persona_customer_profile = vpc_info.get('customer_profile', {})
                if persona_customer_profile:
                    print(f"🔍 DEBUG: [FIELD_PREP] Found customer profile for {persona_id}")
                    combined_customer_profile['jtbd'].extend(persona_customer_profile.get('jobs_to_be_done', []))
                    combined_customer_profile['pains'].extend(persona_customer_profile.get('pains', []))
                    combined_customer_profile['gains'].extend(persona_customer_profile.get('gains', []))
            
            # FORMAT 2: Legacy/direct format - vpc_data.customer_profile (fallback)
            if not combined_customer_profile['jtbd'] and not combined_customer_profile['pains'] and not combined_customer_profile['gains']:
                direct_customer_profile = vpc_data.get('customer_profile', {})
                if direct_customer_profile:
                    print(f"🔍 DEBUG: [FIELD_PREP] Using direct customer_profile from vpc_data")
                    # Handle both 'jobs_to_be_done' and 'jtbd' keys
                    combined_customer_profile['jtbd'].extend(direct_customer_profile.get('jobs_to_be_done', []))
                    combined_customer_profile['jtbd'].extend(direct_customer_profile.get('jtbd', []))
                    combined_customer_profile['pains'].extend(direct_customer_profile.get('pains', []))
                    combined_customer_profile['gains'].extend(direct_customer_profile.get('gains', []))
            
            # FORMAT 3: vpc_v2_data fallback
            if not combined_customer_profile['jtbd'] and not combined_customer_profile['pains'] and not combined_customer_profile['gains']:
                vpc_v2_data = project_data.get('vpc_v2_data', {})
                if vpc_v2_data:
                    print(f"🔍 DEBUG: [FIELD_PREP] Checking vpc_v2_data for customer profile")
                    v2_customer_profile = vpc_v2_data.get('customer_profile', {})
                    if v2_customer_profile:
                        print(f"🔍 DEBUG: [FIELD_PREP] Found customer profile in vpc_v2_data")
                        combined_customer_profile['jtbd'].extend(v2_customer_profile.get('jobs_to_be_done', []))
                        combined_customer_profile['jtbd'].extend(v2_customer_profile.get('jtbd', []))
                        combined_customer_profile['pains'].extend(v2_customer_profile.get('pains', []))
                        combined_customer_profile['gains'].extend(v2_customer_profile.get('gains', []))
            
            print(f"🔍 DEBUG: [FIELD_PREP] Combined customer profile: {len(combined_customer_profile['jtbd'])} JTBD, {len(combined_customer_profile['pains'])} pains, {len(combined_customer_profile['gains'])} gains")
            
            customer_profile = combined_customer_profile
            
            # Get dual vector store context
            context_data = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query="market hypothesis customer validation personas",
                max_results_per_store=5
            )
            
            return {
                'success': True,
                'data': {
                    'project_id': project_id,
                    'personas': personas,
                    'customer_profile': customer_profile,
                    'pv_report_context': context_data.get('pv_report_context', []),
                    'actionable_insights_context': context_data.get('actionable_insights_context', []),
                    'project_data': project_data
                }
            }
            
        except Exception as e:
            print(f"❌ ERROR: Failed to get project context: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to get project context: {str(e)}"
            }
    
    async def _generate_single_hypothesis_for_persona(
        self,
        project_id: str,
        persona: Dict[str, Any],
        customer_profile: Dict[str, Any],
        context: Dict[str, Any],
        creativity_level: float,
        hypothesis_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single hypothesis for a specific persona using customer profile + context.
        """
        try:
            # Prepare persona-specific context (rich context from persona data)
            persona_name = persona.get('name', 'Unnamed Persona')
            persona_description = persona.get('description', '')
            persona_problem_relationship = persona.get('problem_relationship', '')
            persona_evidence = persona.get('evidence', [])
            is_primary_payer = persona.get('is_primary_payer', True)
            
            # Extract evidence quotes for additional context
            evidence_quotes = []
            if isinstance(persona_evidence, list):
                for evidence in persona_evidence:
                    if isinstance(evidence, dict) and evidence.get('quote'):
                        evidence_quotes.append(f"- {evidence['quote']} (from {evidence.get('source', 'unknown')})")
            
            print(f"🔍 DEBUG: [PERSONA_CONTEXT] Using persona: {persona_name}")
            print(f"🔍 DEBUG: [PERSONA_CONTEXT] Description: {persona_description[:100]}...")
            print(f"🔍 DEBUG: [PERSONA_CONTEXT] Evidence quotes: {len(evidence_quotes)}")
            
            # Prepare customer profile context
            jtbd_items = customer_profile.get('jtbd', [])
            pain_items = customer_profile.get('pains', [])
            gain_items = customer_profile.get('gains', [])
            
            # Prepare vector context
            pv_context = context.get('pv_report_context', [])
            insights_context = context.get('actionable_insights_context', [])
            
            # Combine context into text format
            pv_text = '\n'.join([chunk.get('content', '') for chunk in pv_context if isinstance(chunk, dict)])
            insights_text = '\n'.join([chunk.get('content', '') for chunk in insights_context if isinstance(chunk, dict)])
            
            # Build persona-specific prompt with GPT-5.1-mini XML structure
            messages = [
                {
                    "role": "system",
                    "content": (
                        "<role>\n"
                        "You are a research expert crafting structured, testable hypotheses for problem validation.\n"
                        "</role>\n\n"
                        
                        "<definition>\n"
                        "A research hypothesis is a structured assumption that connects:\n"
                        "1. TARGET MARKET - Who are the users experiencing this?\n"
                        "2. THE PROBLEM - What specific challenges are they facing?\n"
                        "3. POTENTIAL ACTION - What solution/action might they adopt?\n"
                        "4. VALUE PROPOSITION - What benefit/value do they get from it?\n"
                        "</definition>\n\n"
                        
                        "<task>\n"
                        "Craft ONE structured research hypothesis following the EXACT framework format.\n"
                        "</task>\n\n"
                        
                        "<hypothesis_framework>\n"
                        "REQUIRED FORMAT (follow this EXACTLY):\n"
                        "\"We believe that [TARGET MARKET] is experiencing [THE PROBLEM], thus [MIGHT DO THIS ACTION/USE THIS SOLUTION], for [VALUE PROPOSITION/WHAT'S IN IT FOR THEM]\"\n"
                        "</hypothesis_framework>\n\n"
                        
                        "<hypothesis_examples>\n"
                        "GOOD EXAMPLES:\n"
                        "1. \"We believe that Professionals in Kigali are experiencing skills gaps and time constraints as far as preparing their meals go, thus might embrace an online food court and delivery platform, for conveniently selecting and ordering food of their choice and having it delivered to their doors\"\n"
                        "\n"
                        "2. \"We believe that South African Private Car Owners are experiencing heightened safety concerns, convenience challenges, and skills gaps while trying to service their cars, thus might adopt an on-demand mobile car servicing solution, for conveniently booking home-based car servicing appointments and tracking status at any time\"\n"
                        "\n"
                        "BAD EXAMPLES:\n"
                        "- \"Farmers struggle with crop losses\" (Missing the 4-part structure)\n"
                        "- \"Users need better tools\" (Too vague, no structure)\n"
                        "- Any hypothesis not following the 'We believe that... is experiencing... thus... for...' format\n"
                        "</hypothesis_examples>\n\n"
                        
                        "<critical_rules>\n"
                        "- MUST follow the exact 4-part framework structure\n"
                        "- KEEP IT CONCISE - total hypothesis should be 40-60 words maximum\n"
                        "- TARGET MARKET: Simple name only (3-5 words). ALWAYS use PLURAL form (e.g., 'Managers' not 'Manager', 'Owners' not 'Owner'). NO parenthetical explanations, NO job descriptions\n"
                        "  GOOD: 'Professionals in Kigali', 'South African Private Car Owners'\n"
                        "  BAD: 'Hospital HIS/IT Managers (hospital-level HIS focal persons responsible for...)'\n"
                        "- PROBLEM: ONE main challenge in plain language (10-15 words). NO technical jargon, NO listing multiple items\n"
                        "  GOOD: 'skills gaps and time constraints as far as preparing their meals go'\n"
                        "  BAD: 'dual-documentation, legal/compliance risk during migration, and workforce/ICT capacity shortages'\n"
                        "- ACTION: Simple solution description (8-12 words). NO implementation details, NO technical specs\n"
                        "  GOOD: 'might embrace an online food court and delivery platform'\n"
                        "  BAD: 'might adopt a bundled hybrid digitization service combining OCR + human abstraction, lightweight FHIR-based connectors'\n"
                        "- VALUE: ONE clear benefit (10-15 words). State the outcome, NOT technical capabilities\n"
                        "  GOOD: 'conveniently selecting and ordering food of their choice and having it delivered'\n"
                        "  BAD: 'faster record retrieval, standards-based interoperability of legacy data, and reduced disruption'\n"
                        "- NO specific pricing, NO business model details, NO conversion rates\n"
                        "- Use everyday language that anyone can understand\n"
                        "</critical_rules>\n\n"
                        
                        "<output_rules>\n"
                        "Return ONLY valid JSON matching the schema.\n"
                        "</output_rules>\n\n"
                        
                        "<json_schema>\n"
                        "{\n"
                        "  \"id\": \"string\",\n"
                        "  \"text\": \"string (the complete hypothesis in framework format)\",\n"
                        "  \"target_market\": \"string (the specific target users)\",\n"
                        "  \"problem\": \"string (the challenges they face)\",\n"
                        "  \"action\": \"string (what solution/action they might adopt)\",\n"
                        "  \"value_proposition\": \"string (the benefit they receive)\",\n"
                        "  \"evidence\": [\"string\"],\n"
                        "  \"persona_id\": \"string\"\n"
                        "}\n"
                        "</json_schema>"
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
<persona_profile>
Name: {persona_name}
Description: {persona_description}
Problem Relationship: {persona_problem_relationship}
Primary Payer: {is_primary_payer}
</persona_profile>

<persona_evidence>
{chr(10).join(evidence_quotes) if evidence_quotes else 'No specific evidence quotes available'}
</persona_evidence>

<customer_profile>
Jobs to be Done: {[item.get('label', '') for item in jtbd_items]}
Pains: {[item.get('label', '') for item in pain_items]}
Gains: {[item.get('label', '') for item in gain_items]}
</customer_profile>

<research_evidence_report>
{pv_text[:1500]}
</research_evidence_report>

<research_evidence_insights>
{insights_text[:1500]}
</research_evidence_insights>

<instructions>
Generate ONE structured research hypothesis for {persona_name} that follows the EXACT framework:

"We believe that [TARGET MARKET] is experiencing [THE PROBLEM], thus [MIGHT DO THIS ACTION/USE THIS SOLUTION], for [VALUE PROPOSITION]"

Use the context provided to:
1. TARGET MARKET: Use the persona name and key characteristics
2. PROBLEM: Synthesize the main pains and challenges from customer profile
3. ACTION: Propose a plausible solution/action they might adopt based on insights
4. VALUE: State the clear benefit/value they would receive (from gains)
</instructions>

<validation_checklist>
☐ Does it start with "We believe that..."?
☐ Is the TOTAL hypothesis 40-60 words maximum?
☐ Is TARGET MARKET just a simple name (3-5 words, NO parentheses)?
☐ Is PROBLEM one main challenge in plain language (NO technical jargon)?
☐ Is ACTION a simple solution (NO implementation details)?
☐ Is VALUE one clear benefit (NOT a list of capabilities)?
☐ Would a non-technical person understand every word?
</validation_checklist>

Return ONLY valid JSON with all required fields including the structured components.
""",
                },
            ]
            
            # Use original VPM AI service for consistency
            from core.ai_service import AIService
            ai_service = AIService()
            
            # Create monitoring context for AI usage tracking
            monitoring_context = None
            try:
                from monitor.tokens.models import AIUsageContext
                monitoring_context = AIUsageContext(
                    user_id=None,  # Not available in this context
                    tenant_id=None,  # Will be set by caller if available
                    project_id=project_id,
                    feature_id="vpm_hypothesis_generation",
                    workflow_name="field_prep_workflow",
                    step_name="generate_hypothesis",
                    environment="prod"
                )
            except ImportError:
                pass
            
            # Call AI service with monitoring
            response_data = ai_service.chat_json(messages, {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string", "description": "Complete hypothesis in framework format"},
                    "target_market": {"type": "string", "description": "The specific target users"},
                    "problem": {"type": "string", "description": "The challenges they face"},
                    "action": {"type": "string", "description": "What solution/action they might adopt"},
                    "value_proposition": {"type": "string", "description": "The benefit they receive"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "persona_id": {"type": "string"}
                },
                "required": ["id", "text", "target_market", "problem", "action", "value_proposition", "evidence", "persona_id"]
            }, monitoring_context=monitoring_context)
            
            # Generate sequential hypothesis ID and add persona mapping
            sequential_hypothesis_id = f"hypothesis-{hypothesis_number:03d}"  # e.g., hypothesis-001, hypothesis-002
            
            response_data['id'] = sequential_hypothesis_id  # Override AI-generated ID with sequential one
            response_data['persona_id'] = persona.get('id', f"persona_{persona_name.lower().replace(' ', '_')}")
            response_data['persona_name'] = persona_name
            response_data['generated_at'] = datetime.utcnow().isoformat()
            
            print(f"✅ DEBUG: Generated hypothesis for {persona_name} with ID {sequential_hypothesis_id}: {response_data.get('text', '')[:100]}...")
            
            return response_data
            
        except Exception as e:
            print(f"❌ ERROR: Failed to generate hypothesis for persona {persona.get('name', 'Unknown')}: {str(e)}")
            return None
    
    async def _save_hypotheses_to_project(self, project_id: str, hypotheses: List[Dict[str, Any]], user_id: str) -> bool:
        """
        Save generated hypotheses to the project's field_prep_data.
        """
        try:
            # Get current project data using service role client
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            project_result = supabase.client.table('vmp_projects').select('*').eq('id', project_id).single().execute()
            if not project_result.data:
                return False
            
            project_data = project_result.data
            
            # Update field_prep_data with hypotheses
            field_prep_data = project_data.get('field_prep_data', {})
            field_prep_data['hypotheses'] = hypotheses
            field_prep_data['hypotheses_generated_at'] = datetime.utcnow().isoformat()
            field_prep_data['stage'] = 'hypothesis_completed'
            
            print(f"🔍 DEBUG: [SAVE_HYPOTHESES] Updating field_prep_data with {len(hypotheses)} hypotheses")
            print(f"🔍 DEBUG: [SAVE_HYPOTHESES] Hypotheses data: {[(h.get('id', 'No ID'), h.get('persona_name', 'Unknown')) for h in hypotheses]}")
            
            # Save back to database (supabase already initialized above)
            result = supabase.client.table('vmp_projects').update({
                'field_prep_data': field_prep_data,
                'current_step': 'field_prep_assumptions',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            print(f"🔍 DEBUG: [SAVE_HYPOTHESES] Database update result: {bool(result.data)}")
            if result.data:
                print(f"✅ DEBUG: [SAVE_HYPOTHESES] Updated project {project_id} with field_prep_data")
                
                # 📊 WORKFLOW STATUS: Mark hypothesis as completed
                try:
                    from .workflow_status_service import get_workflow_status_service, WorkflowStage
                    tenant_id = project_data.get('tenant_id')
                    if tenant_id:
                        workflow_service = get_workflow_status_service()
                        workflow_service.set_stage_completed(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            stage=WorkflowStage.HYPOTHESIS,
                            additional_metadata={"hypotheses_count": len(hypotheses)}
                        )
                except Exception as status_error:
                    print(f"⚠️ DEBUG: [SAVE_HYPOTHESES] Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk hypotheses for "Chat with Project" feature
                try:
                    from .project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    # Get tenant_id from project data
                    tenant_id = project_data.get('tenant_id')
                    if tenant_id:
                        await chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.HYPOTHESIS,
                            feature_data={"hypotheses": hypotheses}
                        )
                        print(f"🚀 DEBUG: [SAVE_HYPOTHESES] Background chunking spawned for hypotheses")
                except Exception as chunk_error:
                    print(f"⚠️ DEBUG: [SAVE_HYPOTHESES] Background chunking failed (non-blocking): {chunk_error}")
            else:
                print(f"❌ DEBUG: [SAVE_HYPOTHESES] No data returned from database update")
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ ERROR: Failed to save hypotheses: {str(e)}")
            return False
        
    async def generate_assumptions(
        self, 
        project_id: str, 
        user_id: str,
        max_assumptions: int = 3,
        tenant_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate EXACTLY 2 assumptions per hypothesis based on personas.
        
        NEW WORKFLOW: Each hypothesis (per persona) gets EXACTLY 2 testable assumptions.
        STRICT REQUIREMENT: Always generates 2 assumptions per hypothesis (no more, no less).
        """
        try:
            # Get tenant_id if not provided
            if not tenant_id:
                # Try to get tenant_id from user
                from ..api.endpoints import get_user_tenant_id
                tenant_id = await get_user_tenant_id(user_id)
                if not tenant_id:
                    return {
                        'success': False,
                        'error': 'Could not determine user tenant'
                    }
            
            print(f"🔍 DEBUG: [NEW WORKFLOW] Starting assumptions generation for project: {project_id}")
            
            # Get project context with personas and hypotheses
            project_context = await self._get_project_context_personas_only(project_id, tenant_id)
            if not project_context['success']:
                print(f"❌ DEBUG: Failed to get project context: {project_context.get('error')}")
                return project_context
            
            print(f"✅ DEBUG: Project context retrieved successfully")
            
            # Get generated hypotheses from field_prep_data
            project_data = project_context['data']['project_data']
            field_prep_data = project_data.get('field_prep_data', {})
            hypotheses = field_prep_data.get('hypotheses', [])
            
            if not hypotheses:
                print(f"❌ DEBUG: No hypotheses found in field_prep_data")
                return {
                    'success': False,
                    'error': "Hypotheses must be generated before creating assumptions"
                }
            
            print(f"✅ DEBUG: Found {len(hypotheses)} hypotheses")
            
            # Generate 2-3 assumptions per hypothesis
            all_assumptions = []
            # MULTI-PERSONA FIX: Each persona/hypothesis gets its own assumption numbering starting from 001
            for i, hypothesis in enumerate(hypotheses):
                print(f"🔍 DEBUG: Generating assumptions for hypothesis {i+1}: {hypothesis.get('persona_name', 'Unknown')}")
                
                # Each hypothesis starts from assumption 001 (persona-specific numbering)
                hypothesis_assumptions = await self._generate_assumptions_for_hypothesis(
                    project_id=project_id,
                    hypothesis=hypothesis,
                    context=project_context['data'],
                    max_assumptions=max_assumptions,
                    start_assumption_number=1  # Always start from 1 for each persona/hypothesis
                )
                
                if hypothesis_assumptions:
                    all_assumptions.extend(hypothesis_assumptions)
                    print(f"✅ DEBUG: Generated {len(hypothesis_assumptions)} assumptions for {hypothesis.get('persona_name', 'Unknown')} (IDs: {[a['id'] for a in hypothesis_assumptions]})")
                else:
                    print(f"❌ DEBUG: Failed to generate assumptions for {hypothesis.get('persona_name', 'Unknown')}")
            
            if not all_assumptions:
                return {
                    'success': False,
                    'error': "Failed to generate any assumptions for the hypotheses"
                }
            
            # Save assumptions to project
            print(f"🔍 DEBUG: [SAVE_ASSUMPTIONS] Attempting to save {len(all_assumptions)} assumptions to project {project_id}")
            save_result = await self._save_assumptions_to_project(project_id, all_assumptions, user_id)
            if save_result:
                print(f"✅ DEBUG: [SAVE_ASSUMPTIONS] Successfully saved {len(all_assumptions)} assumptions to database")
            else:
                print(f"❌ DEBUG: [SAVE_ASSUMPTIONS] Failed to save assumptions to project, but continuing...")
            
            return {
                'success': True,
                'assumptions': all_assumptions,
                'total_assumptions': len(all_assumptions),
                'hypotheses_count': len(hypotheses),
                'hypotheses_reference': hypotheses,  # Include the source hypotheses for reference
                'message': f"Generated {len(all_assumptions)} assumption(s) for {len(hypotheses)} hypothesis(es)"
            }
            
        except Exception as e:
            print(f"❌ ERROR: Assumptions generation failed: {str(e)}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Failed to generate assumptions: {str(e)}"
            }
    
    def _validate_assumption_quality(self, assumption_text: str) -> Dict[str, Any]:
        """
        Validate that an assumption follows current-state guidelines.
        Returns validation result with warnings if assumption is problematic.
        """
        warnings = []
        is_valid = True
        
        # Check for intervention outcome patterns
        intervention_patterns = [
            r'\d+%\s+increase',
            r'\d+%\s+improvement',
            r'\d+%\s+reduction',
            r'after\s+receiving',
            r'after\s+using',
            r'will\s+report',
            r'will\s+experience'
        ]
        
        import re
        for pattern in intervention_patterns:
            if re.search(pattern, assumption_text, re.IGNORECASE):
                warnings.append(f"⚠️ Contains intervention outcome pattern: '{pattern}'")
                is_valid = False
        
        # NOTE: "would" and "will" are EXPECTED in assumption format per user requirements:
        # - "thus would adopt an alternative solution"
        # - "will readily adopt a service"
        # Only flag "going to" as overly speculative
        if re.search(r'going\s+to\s+', assumption_text, re.IGNORECASE):
            warnings.append(f"⚠️ Contains speculative pattern: 'going to'")
            is_valid = False
        
        # Check for specific metrics without context
        if re.search(r'\d+%', assumption_text) and not re.search(r'currently|existing|present', assumption_text, re.IGNORECASE):
            warnings.append("⚠️ Contains specific percentage without current-state context")
            is_valid = False
        
        # Check for pricing assumptions
        if re.search(r'pay|price|cost|\$\d+', assumption_text, re.IGNORECASE):
            warnings.append("⚠️ Contains pricing/payment assumption")
            is_valid = False
        
        # Positive indicators (current state language)
        current_state_patterns = [
            r'currently',
            r'existing',
            r'present',
            r'right now',
            r'at this time',
            r'today'
        ]
        
        has_current_state_language = any(
            re.search(pattern, assumption_text, re.IGNORECASE) 
            for pattern in current_state_patterns
        )
        
        if not has_current_state_language and is_valid:
            warnings.append("ℹ️ Suggestion: Add current-state language (currently, existing, present)")
        
        return {
            'is_valid': is_valid,
            'warnings': warnings,
            'has_current_state_language': has_current_state_language
        }
    
    async def _generate_assumptions_for_hypothesis(
        self,
        project_id: str,
        hypothesis: Dict[str, Any],
        context: Dict[str, Any],
        max_assumptions: int = 3,
        start_assumption_number: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate EXACTLY 3 testable assumptions for a specific hypothesis.
        Each assumption maps to a customer profile component: JTBD, Pain, Gain.
        
        STRICT REQUIREMENT: Always generates exactly 3 assumptions per hypothesis.
        """
        try:
            # STRICT: Generate EXACTLY 3 assumptions per hypothesis (1 for JTBD, 1 for Pain, 1 for Gain)
            min_assumptions = 3
            max_assumptions = 3  # Fixed at 3
            target_assumptions = 3  # Always 3 assumptions
            
            hypothesis_text = hypothesis.get('text', '')
            hypothesis_evidence = hypothesis.get('evidence', [])
            persona_name = hypothesis.get('persona_name', 'Unknown Persona')
            
            # Get the full persona data for rich context
            personas = context.get('personas', [])
            persona_data = None
            for p in personas:
                if p.get('name') == persona_name or p.get('id') == hypothesis.get('persona_id'):
                    persona_data = p
                    break
            
            # Extract rich persona context if available
            persona_description = persona_data.get('description', '') if persona_data else ''
            persona_problem_relationship = persona_data.get('problem_relationship', '') if persona_data else ''
            persona_evidence_quotes = []
            if persona_data and persona_data.get('evidence'):
                for evidence in persona_data.get('evidence', []):
                    if isinstance(evidence, dict) and evidence.get('quote'):
                        persona_evidence_quotes.append(f"- {evidence['quote']}")
            
            print(f"🔍 DEBUG: [ASSUMPTIONS] Using persona context for {persona_name}: {bool(persona_data)}")
            print(f"🔍 DEBUG: [ASSUMPTIONS] Persona evidence quotes: {len(persona_evidence_quotes)}")
            
            # Get context data
            pv_context = context.get('pv_report_context', [])
            insights_context = context.get('actionable_insights_context', [])
            customer_profile = context.get('customer_profile', {})
            
            # Combine context into text format
            pv_text = '\n'.join([chunk.get('content', '') for chunk in pv_context if isinstance(chunk, dict)])
            insights_text = '\n'.join([chunk.get('content', '') for chunk in insights_context if isinstance(chunk, dict)])
            
            # Build assumptions generation prompt with GPT-5.1-mini XML structure
            messages = [
                {
                    "role": "system",
                    "content": (
                        "<role>\n"
                        "You are a research expert generating testable assumptions for customer validation.\n"
                        "</role>\n\n"
                        
                        "<task>\n"
                        "Generate EXACTLY 3 testable assumptions for the given hypothesis. Each assumption maps to a customer profile component.\n"
                        "</task>\n\n"
                        
                        "<assumption_framework>\n"
                        "ASSUMPTION #1 (Jobs-to-be-Done):\n"
                        "Validation Objective: Confirm that the customer Jobs to Be Done are real and significant\n"
                        "Format: '[Target customers] are trying to [job they're hiring a product/service for], as opposed to [alternative], and thus would [adopt/buy/use] [solution type]'\n"
                        "EXAMPLES:\n"
                        "  - 'The user isn't just buying a laptop; they're hiring it to complete their work tasks untethered, thus would buy a laptop with longer battery life'\n"
                        "  - 'Movie enthusiasts are trying to have an entertaining night in, as opposed to going out to the movies, and thus would adopt an online movie streaming service'\n\n"
                        
                        "ASSUMPTION #2 (Pain):\n"
                        "Validation Objective: Confirm the pain points and alternative solutions customers are trying out to relieve the pain\n"
                        "Format: '[Target customers] are [frustrated/burdened] by [specific pain], so [action/alternative they would take]'\n"
                        "EXAMPLES:\n"
                        "  - 'Our customers are frustrated with the high cost of their current project management software, so a cheaper price point will convince them to switch'\n"
                        "  - 'Kenyans are heavily burdened by the cost, time, and risk associated with carrying cash while receiving and sending money, and thus would adopt an alternative solution that removes/minimizes the burden'\n\n"
                        
                        "ASSUMPTION #3 (Gain):\n"
                        "Validation Objective: Confirm that the customer gains are desirable and valuable\n"
                        "Format: '[Target customers] would appreciate/value [specific gains/benefits], unlike [current alternatives], and will readily adopt [solution type]'\n"
                        "EXAMPLES:\n"
                        "  - 'Kenyans would appreciate a cheaper, faster, and safer alternative to sending and receiving money, unlike the post office, bus companies, or traveling with cash'\n"
                        "  - 'Kigali professionals value time and effort savings highly and will readily adopt a service that offers fast, reliable delivery of meals and essentials directly to their location'\n"
                        "</assumption_framework>\n\n"
                        
                        "<critical_rules>\n"
                        "- Generate EXACTLY 3 assumptions in order: JTBD, Pain, Gain\n"
                        "- Each assumption must be testable through customer interviews\n"
                        "- ALWAYS use PLURAL form for target market (e.g., 'Professionals' not 'Professional')\n"
                        "- Focus on CURRENT STATE and existing behaviors\n"
                        "- Keep assumptions concise (1-2 sentences max)\n"
                        "- Include 2-3 evidence items per assumption from customer profile and research\n"
                        "</critical_rules>\n\n"
                        
                        "<output_rules>\n"
                        "Return ONLY valid JSON matching the schema.\n"
                        "</output_rules>\n\n"
                        
                        "<json_schema>\n"
                        "{\"assumptions\": [{\"id\": \"string\", \"text\": \"string\", \"component_type\": \"jtbd|pain|gain\", \"evidence\": [\"string\"], \"hypothesis_id\": \"string\", \"persona_name\": \"string\"}]}\n"
                        "</json_schema>"
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
<hypothesis_to_test>
{hypothesis_text}
</hypothesis_to_test>

<persona_profile>
Name: {persona_name}
Description: {persona_description}
Problem Relationship: {persona_problem_relationship}
</persona_profile>

<persona_evidence>
{chr(10).join(persona_evidence_quotes) if persona_evidence_quotes else 'No specific persona evidence available'}
</persona_evidence>

<hypothesis_evidence>
{hypothesis_evidence}
</hypothesis_evidence>

<customer_profile>
Jobs to be Done: {[item.get('label', '') for item in customer_profile.get('jtbd', [])]}
Pains: {[item.get('label', '') for item in customer_profile.get('pains', [])]}
Gains: {[item.get('label', '') for item in customer_profile.get('gains', [])]}
</customer_profile>

<research_evidence_report>
{pv_text[:1200]}
</research_evidence_report>

<research_evidence_insights>
{insights_text[:1200]}
</research_evidence_insights>

<instructions>
Generate EXACTLY 3 assumptions following this structure:

ASSUMPTION #1 (JTBD - component_type: "jtbd"):
Objective: Confirm that the customer Jobs to Be Done are real and significant
Format: "[Target customers] are trying to [job], as opposed to [alternative], and thus would [adopt solution]"
- Focus on what job the customer is "hiring" the product/service to do
- Contrast with alternatives they might use instead
- Evidence should cite: Customer profile JTBD items, hypothesis evidence

ASSUMPTION #2 (Pain - component_type: "pain"):
Objective: Confirm the pain points and alternative solutions customers are trying out to relieve the pain
Format: "[Target customers] are [frustrated/burdened] by [specific pain], so [action they would take]"
- State the specific pain (cost, time, risk, inconvenience)
- Mention what alternative solutions they might try
- Evidence should cite: Customer profile Pains, research insights

ASSUMPTION #3 (Gain - component_type: "gain"):
Objective: Confirm that the customer gains are desirable and valuable
Format: "[Target customers] would appreciate/value [specific gains], unlike [current alternatives], and will readily adopt [solution]"
- State the desired benefits (cost saving, time saving, convenience, safety)
- Contrast with inferior current alternatives
- Evidence should cite: Customer profile Gains, research recommendations
</instructions>

<validation_checklist>
☐ Exactly 3 assumptions generated (JTBD, Pain, Gain in order)?
☐ Each assumption references customer profile items in evidence?
☐ Assumptions are testable through customer interviews?
☐ Focus on CURRENT STATE, not future predictions?
</validation_checklist>

Return ONLY valid JSON.
""",
                },
            ]
            
            # Use original VPM AI service for consistency
            from core.ai_service import AIService
            ai_service = AIService()
            
            # Create monitoring context for AI usage tracking
            monitoring_context = None
            try:
                from monitor.tokens.models import AIUsageContext
                monitoring_context = AIUsageContext(
                    user_id=None,
                    tenant_id=None,
                    project_id=project_id,
                    feature_id="vpm_assumptions_generation",
                    workflow_name="field_prep_workflow",
                    step_name="generate_assumptions",
                    environment="prod"
                )
            except ImportError:
                pass
            
            # Call AI service with monitoring
            response_data = ai_service.chat_json(messages, {
                "type": "object",
                "properties": {
                    "assumptions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "component_type": {"type": "string", "enum": ["jtbd", "pain", "gain"]},
                                "evidence": {"type": "array", "items": {"type": "string"}},
                                "hypothesis_id": {"type": "string"},
                                "persona_name": {"type": "string"}
                            },
                            "required": ["id", "text", "component_type", "evidence", "hypothesis_id", "persona_name"]
                        },
                        f"minItems": min_assumptions,
                        f"maxItems": max_assumptions
                    }
                },
                "required": ["assumptions"]
            }, monitoring_context=monitoring_context)
            
            assumptions = response_data.get('assumptions', [])
            
            # STRICT VALIDATION: Ensure exactly 3 assumptions were generated (1 JTBD, 1 Pain, 1 Gain)
            if len(assumptions) != 3:
                print(f"⚠️ WARNING: AI generated {len(assumptions)} assumptions instead of 3. Adjusting...")
                if len(assumptions) < 3:
                    print(f"❌ ERROR: Only {len(assumptions)} assumption(s) generated. Cannot proceed.")
                    return []
                elif len(assumptions) > 3:
                    print(f"⚠️ WARNING: Truncating to first 3 assumptions")
                    assumptions = assumptions[:3]
            
            # COMPONENT TYPE VALIDATION: Ensure we have one assumption for each component type
            component_types = [assumption.get('component_type') for assumption in assumptions]
            required_types = {'jtbd', 'pain', 'gain'}
            found_types = set(component_types)
            
            if found_types != required_types:
                missing_types = required_types - found_types
                extra_types = found_types - required_types
                print(f"⚠️ WARNING: Component type validation failed!")
                print(f"  - Required: {required_types}")
                print(f"  - Found: {found_types}")
                if missing_types:
                    print(f"  - Missing: {missing_types}")
                if extra_types:
                    print(f"  - Extra: {extra_types}")
            else:
                print(f"✅ SUCCESS: All component types present: {found_types}")
            
            # Add metadata and sequential IDs to each assumption
            # Also validate assumption quality
            persona_id = hypothesis.get('persona_id', 'P1')  # Get persona_id from hypothesis
            
            for i, assumption in enumerate(assumptions):
                # MULTI-PERSONA: Each persona starts from 001, differentiated by persona_id field
                # Format: assumption-001, assumption-002, assumption-003 (for each persona)
                sequential_assumption_id = f"assumption-{start_assumption_number + i:03d}"
                
                assumption['id'] = sequential_assumption_id  # Simple sequential ID (001, 002, 003)
                assumption['hypothesis_id'] = hypothesis.get('id', f"hyp_{persona_name.lower().replace(' ', '_')}")
                assumption['persona_id'] = persona_id  # persona_id field differentiates between personas
                assumption['persona_name'] = persona_name
                assumption['generated_at'] = datetime.utcnow().isoformat()
                
                # Validate assumption quality
                assumption_text = assumption.get('text', '')
                validation_result = self._validate_assumption_quality(assumption_text)
                assumption['quality_validation'] = validation_result
                
                if not validation_result['is_valid']:
                    print(f"⚠️ QUALITY WARNING for {sequential_assumption_id}:")
                    for warning in validation_result['warnings']:
                        print(f"  {warning}")
                    print(f"  Assumption: {assumption_text[:100]}...")
                elif validation_result['warnings']:
                    print(f"ℹ️ QUALITY SUGGESTION for {sequential_assumption_id}:")
                    for warning in validation_result['warnings']:
                        print(f"  {warning}")
                else:
                    print(f"✅ QUALITY CHECK PASSED for {sequential_assumption_id}")
                
                print(f"✅ DEBUG: Generated assumption {sequential_assumption_id} for {persona_name}: {assumption.get('text', '')[:80]}...")
            
            print(f"✅ DEBUG: Generated {len(assumptions)} assumptions for {persona_name}")
            
            return assumptions
            
        except Exception as e:
            print(f"❌ ERROR: Failed to generate assumptions for hypothesis: {str(e)}")
            return []
    
    async def _save_assumptions_to_project(self, project_id: str, assumptions: List[Dict[str, Any]], user_id: str) -> bool:
        """
        Save generated assumptions to the project's field_prep_data.
        """
        try:
            # Get current project data using service role client
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            project_result = supabase.client.table('vmp_projects').select('*').eq('id', project_id).single().execute()
            if not project_result.data:
                return False
            
            project_data = project_result.data
            
            # Update field_prep_data with assumptions
            field_prep_data = project_data.get('field_prep_data', {})
            field_prep_data['assumptions'] = assumptions
            field_prep_data['assumptions_generated_at'] = datetime.utcnow().isoformat()
            field_prep_data['stage'] = 'assumptions_completed'
            
            print(f"🔍 DEBUG: [SAVE_ASSUMPTIONS] Updating field_prep_data with {len(assumptions)} assumptions")
            print(f"🔍 DEBUG: [SAVE_ASSUMPTIONS] Assumptions data: {[(a.get('id', 'No ID'), a.get('persona_name', 'Unknown')) for a in assumptions]}")
            
            # Save back to database (supabase already initialized above)
            result = supabase.client.table('vmp_projects').update({
                'field_prep_data': field_prep_data,
                'current_step': 'field_prep_questionnaires',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            print(f"🔍 DEBUG: [SAVE_ASSUMPTIONS] Database update result: {bool(result.data)}")
            if result.data:
                print(f"✅ DEBUG: [SAVE_ASSUMPTIONS] Updated project {project_id} with field_prep_data")
                
                # 📊 WORKFLOW STATUS: Mark assumptions as completed
                try:
                    from .workflow_status_service import get_workflow_status_service, WorkflowStage
                    tenant_id = project_data.get('tenant_id')
                    if tenant_id:
                        workflow_service = get_workflow_status_service()
                        workflow_service.set_stage_completed(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            stage=WorkflowStage.ASSUMPTIONS,
                            additional_metadata={"assumptions_count": len(assumptions)}
                        )
                except Exception as status_error:
                    print(f"⚠️ DEBUG: [SAVE_ASSUMPTIONS] Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk assumptions for "Chat with Project" feature
                try:
                    from .project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    # Get tenant_id from project data
                    tenant_id = project_data.get('tenant_id')
                    if tenant_id:
                        await chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.ASSUMPTIONS,
                            feature_data={"assumptions": assumptions}
                        )
                        print(f"🚀 DEBUG: [SAVE_ASSUMPTIONS] Background chunking spawned for assumptions")
                except Exception as chunk_error:
                    print(f"⚠️ DEBUG: [SAVE_ASSUMPTIONS] Background chunking failed (non-blocking): {chunk_error}")
            else:
                print(f"❌ DEBUG: [SAVE_ASSUMPTIONS] No data returned from database update")
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ ERROR: Failed to save assumptions: {str(e)}")
            return False
    
    # COMMENTED OUT - STAKEHOLDER ASSIGNMENT REMOVED FROM NEW WORKFLOW
    # Personas are used directly instead of stakeholder assignments
    # 
    # async def assign_stakeholders(
    #     self, 
    #     project_id: str, 
    #     user_id: str,
    #     stakeholder_preferences: Optional[List[StakeholderType]] = None
    # ) -> Dict[str, Any]:
    #     """
    #     Assign stakeholders to assumptions for field research.
    #     This implements the third step of Field Prep workflow.
    #     Uses VPC + PV Report + Actionable Insights + Hypothesis + Assumptions as context.
    #     """
    #     try:
    #         print(f"🔍 DEBUG: Starting stakeholder assignment for project: {project_id}")
    #         
    #         # Get project context (VPC + dual vector store)
    #         print(f"🔍 DEBUG: Getting project context for stakeholders...")
    #         project_context = await self._get_project_context(project_id)
    #         if not project_context['success']:
    #             print(f"❌ DEBUG: Failed to get project context: {project_context.get('error')}")
    #             return project_context
    #         
    #         print(f"✅ DEBUG: Project context retrieved successfully")
    #         
    #         # Check if VPC is completed
    #         vpc_data = project_context['data'].get('vpc_artifacts')
    #         if not vpc_data:
    #             print(f"❌ DEBUG: No VPC artifacts found")
    #             return {
    #                 'success': False,
    #                 'error': "VPC must be completed before assigning stakeholders"
    #             }
    #         
    #         print(f"✅ DEBUG: VPC data available for stakeholders")
    #         
    #         # Get hypothesis from field_prep_data
    #         print(f"🔍 DEBUG: Retrieving generated hypothesis...")
    #         hypothesis_data = await self._get_field_prep_artifact(
    #             project_id=project_id,
    #             stage=FieldPrepStage.HYPOTHESIS
    #         )
    #         
    #         if not hypothesis_data['success']:
    #             print(f"❌ DEBUG: No hypothesis found: {hypothesis_data.get('error')}")
    #             return {
    #                 'success': False,
    #                 'error': "Hypothesis must be generated before assigning stakeholders"
    #             }
    #         
    #         print(f"✅ DEBUG: Hypothesis retrieved successfully")
    #         
    #         # Get assumptions from field_prep_data
    #         print(f"🔍 DEBUG: Retrieving generated assumptions...")
    #         assumptions_data = await self._get_field_prep_artifact(
    #             project_id=project_id,
    #             stage=FieldPrepStage.ASSUMPTIONS
    #         )
    #         
    #         if not assumptions_data['success']:
    #             print(f"❌ DEBUG: No assumptions found: {assumptions_data.get('error')}")
    #             return {
    #                 'success': False,
    #                 'error': "Assumptions must be generated before assigning stakeholders"
    #             }
    #         
    #         print(f"✅ DEBUG: Assumptions retrieved successfully")
    #         print(f"🔍 DEBUG: Number of assumptions: {len(assumptions_data['artifact']) if isinstance(assumptions_data['artifact'], list) else 'Not a list'}")
    #         
    #         # Get dual vector store context for stakeholder assignment
    #         print(f"🔍 DEBUG: Performing dual vector store search for stakeholders...")
    #         context_data = await self.vector_adapter.dual_context_search(
    #             project_id=project_id,
    #             query="stakeholders customer user partner decision maker influencer",
    #             max_results_per_store=5
    #         )
    #         
    #         print(f"✅ DEBUG: Dual vector store search completed")
    #         if context_data:
    #             pv_context = context_data.get('pv_report_context', {})
    #             insights_context = context_data.get('actionable_insights_context', {})
    #             print(f"🔍 DEBUG: PV report context available: {bool(pv_context)}")
    #             print(f"🔍 DEBUG: Actionable insights context available: {bool(insights_context)}")
    #         
    #         # Assign stakeholders using original VPM service
    #         print(f"🔍 DEBUG: Calling original VPM service for stakeholder assignment...")
    #         stakeholders_result = await self._assign_stakeholders_with_original_service(
    #             project_id, vpc_data, context_data, hypothesis_data['artifact'], 
    #             assumptions_data['artifact'], stakeholder_preferences
    #         )
    #         
    #         if not stakeholders_result['success']:
    #             print(f"❌ DEBUG: Stakeholder assignment failed: {stakeholders_result.get('error')}")
    #             return stakeholders_result
    #         
    #         print(f"✅ DEBUG: Stakeholders assigned successfully")
    #         print(f"🔍 DEBUG: Number of stakeholder assignments: {len(stakeholders_result.get('stakeholder_assignments', []))}")
    #         
    #         # Store stakeholder assignments in field_prep_data
    #         print(f"🔍 DEBUG: Storing stakeholder assignments in database...")
    #         storage_result = await self._store_field_prep_artifact(
    #             project_id=project_id,
    #             stage=FieldPrepStage.STAKEHOLDERS,
    #             artifact_data=stakeholders_result['stakeholder_assignments'],
    #             user_id=user_id
    #         )
    #         
    #         if storage_result.get('success'):
    #             print(f"✅ DEBUG: Stakeholder assignments stored successfully in field_prep_data.{storage_result.get('stage')}")
    #             print(f"🔍 DEBUG: Updated field_prep_data keys: {storage_result.get('updated_keys')}")
    #         else:
    #             print(f"⚠️ DEBUG: Failed to store stakeholder assignments: {storage_result.get('error')}")
    #             # Continue anyway - don't fail the entire operation if storage fails
    #         
    #         return {
    #             'success': True,
    #             'stakeholder_assignments': stakeholders_result['stakeholder_assignments'],
    #             'assignment_summary': stakeholders_result.get('assignment_summary', {}),
    #             'assumptions_used': assumptions_data['artifact'],
    #             'hypothesis_used': hypothesis_data['artifact'],
    #             'context_summary': {
    #                 'vpc_available': bool(vpc_data),
    #                 'pv_context_available': bool(context_data.get('pv_report_context')),
    #                 'insights_context_available': bool(context_data.get('actionable_insights_context')),
    #                 'hypothesis_available': bool(hypothesis_data['artifact']),
    #                 'assumptions_available': bool(assumptions_data['artifact'])
    #             },
    #             'message': f"Assigned stakeholders to {len(assumptions_data['artifact'])} assumptions successfully"
    #         }
    #         
    #     except Exception as e:
    #         print(f"❌ DEBUG: Exception in stakeholder assignment: {str(e)}")
    #         return {
    #             'success': False,
    #             'error': f"Failed to assign stakeholders: {str(e)}"
    #         }
    
    async def generate_questionnaires(
        self, 
        project_id: str, 
        user_id: str,
        questions_per_assumption: int = 5,
        include_demographic_questions: bool = True,
        tenant_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate questionnaires for each assumption using persona-based workflow.
        
        NEW WORKFLOW: Personas → Hypotheses → Assumptions → Questionnaires (5 questions per assumption)
        No stakeholders needed - questions are targeted directly to personas.
        """
        try:
            print(f"🔍 DEBUG: Starting persona-based questionnaires generation for project: {project_id}")
            
            # Get project context (personas + customer profile + vector context)
            print(f"🔍 DEBUG: Getting project context for questionnaires...")
            project_context = await self._get_project_context_personas_only(project_id, tenant_id)
            if not project_context['success']:
                print(f"❌ DEBUG: Failed to get project context: {project_context.get('error')}")
                return project_context
            
            print(f"✅ DEBUG: Project context retrieved successfully")
            
            # Get personas and customer profile from context
            personas = project_context['data'].get('personas', [])
            customer_profile = project_context['data'].get('customer_profile', {})
            
            if not personas:
                print(f"❌ DEBUG: No personas found")
                return {
                    'success': False,
                    'error': "Personas must be identified before generating questionnaires"
                }
            
            if not customer_profile:
                print(f"❌ DEBUG: No customer profile found")
                return {
                    'success': False,
                    'error': "Customer profile must be completed before generating questionnaires"
                }
            
            print(f"✅ DEBUG: Found {len(personas)} personas and customer profile")
            
            # Get hypotheses and assumptions from field_prep_data
            print(f"🔍 DEBUG: Retrieving generated hypotheses and assumptions...")
            project_data = project_context['data'].get('project_data', {})
            field_prep_data = project_data.get('field_prep_data', {})
            
            print(f"🔍 DEBUG: Available field_prep_data keys: {list(field_prep_data.keys())}")
            
            hypotheses = field_prep_data.get('hypotheses', [])
            assumptions = field_prep_data.get('assumptions', [])
            
            print(f"🔍 DEBUG: Raw hypotheses data: {len(hypotheses)} items")
            print(f"🔍 DEBUG: Raw assumptions data: {len(assumptions)} items")
            
            if not hypotheses:
                print(f"❌ DEBUG: No hypotheses found in field_prep_data")
                print(f"🔍 DEBUG: field_prep_data content: {field_prep_data}")
                return {
                    'success': False,
                    'error': "Hypotheses must be generated before generating questionnaires"
                }
            
            if not assumptions:
                print(f"❌ DEBUG: No assumptions found in field_prep_data")
                return {
                    'success': False,
                    'error': "Assumptions must be generated before generating questionnaires"
                }
            
            print(f"✅ DEBUG: Found {len(hypotheses)} hypotheses and {len(assumptions)} assumptions")
            
            # Generate questionnaires for each assumption (5 questions per assumption)
            # Group assumptions by hypothesis to restart question numbering per hypothesis
            print(f"🔍 DEBUG: Generating {questions_per_assumption} questions per assumption...")
            all_questionnaires = []
            
            # Group assumptions by hypothesis_id
            assumptions_by_hypothesis = {}
            for assumption in assumptions:
                hyp_id = assumption.get('hypothesis_id', 'unknown')
                if hyp_id not in assumptions_by_hypothesis:
                    assumptions_by_hypothesis[hyp_id] = []
                assumptions_by_hypothesis[hyp_id].append(assumption)
            
            print(f"🔍 DEBUG: Grouped assumptions into {len(assumptions_by_hypothesis)} hypotheses")
            
            # Generate questions for each hypothesis group (reset counter per hypothesis)
            for hyp_id, hyp_assumptions in assumptions_by_hypothesis.items():
                question_counter = 1  # Reset counter for each hypothesis
                print(f"🔍 DEBUG: Generating questions for hypothesis {hyp_id} ({len(hyp_assumptions)} assumptions)")
                
                for i, assumption in enumerate(hyp_assumptions):
                    print(f"🔍 DEBUG: Generating questions for assumption {i+1}: {assumption.get('id', 'Unknown')}")
                    
                    assumption_questionnaires = await self._generate_questions_for_assumption(
                        project_id=project_id,
                        assumption=assumption,
                        context=project_context['data'],
                        questions_per_assumption=questions_per_assumption,
                        start_question_number=question_counter,
                        include_demographic_questions=include_demographic_questions
                    )
                    
                    if assumption_questionnaires:
                        all_questionnaires.extend(assumption_questionnaires)
                        question_counter += len(assumption_questionnaires)
                        print(f"✅ DEBUG: Generated {len(assumption_questionnaires)} questions for assumption {assumption.get('id', 'Unknown')}")
                    else:
                        print(f"❌ DEBUG: Failed to generate questions for assumption {assumption.get('id', 'Unknown')}")
            
            if not all_questionnaires:
                return {
                    'success': False,
                    'error': "Failed to generate any questionnaires for the assumptions"
                }
            
            # Save questionnaires to project
            print(f"🔍 DEBUG: [SAVE_QUESTIONNAIRES] Attempting to save {len(all_questionnaires)} questions to project {project_id}")
            save_result = await self._save_questionnaires_to_project(project_id, all_questionnaires, user_id)
            if save_result:
                print(f"✅ DEBUG: [SAVE_QUESTIONNAIRES] Successfully saved {len(all_questionnaires)} questions to database")
            else:
                print(f"❌ DEBUG: [SAVE_QUESTIONNAIRES] Failed to save questionnaires to project, but continuing...")
            
            return {
                'success': True,
                'questionnaires': all_questionnaires,
                'total_questions': len(all_questionnaires),
                'assumptions_count': len(assumptions),
                'personas_count': len(personas),
                'questions_per_assumption': questions_per_assumption,
                'message': f"Generated {len(all_questionnaires)} questions for {len(assumptions)} assumptions ({questions_per_assumption} questions per assumption)"
            }
            
        except Exception as e:
            print(f"❌ ERROR: Questionnaires generation failed: {str(e)}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Failed to generate questionnaires: {str(e)}"
            }
    
    async def _generate_questions_for_assumption(
        self,
        project_id: str,
        assumption: Dict[str, Any],
        context: Dict[str, Any],
        questions_per_assumption: int = 5,
        start_question_number: int = 1,
        include_demographic_questions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate 5 targeted questions for a specific assumption using persona context.
        """
        try:
            assumption_text = assumption.get('text', '')
            assumption_evidence = assumption.get('evidence', [])
            persona_name = assumption.get('persona_name', 'Unknown Persona')
            hypothesis_id = assumption.get('hypothesis_id', '')
            component_type = assumption.get('component_type', 'unknown')  # NEW: Get component type (jtbd, pain, gain)
            
            # Get the full persona data for rich context
            personas = context.get('personas', [])
            persona_data = None
            for p in personas:
                if p.get('name') == persona_name:
                    persona_data = p
                    break
            
            # Extract rich persona context if available
            persona_description = persona_data.get('description', '') if persona_data else ''
            persona_problem_relationship = persona_data.get('problem_relationship', '') if persona_data else ''
            persona_evidence_quotes = []
            if persona_data and persona_data.get('evidence'):
                for evidence in persona_data.get('evidence', []):
                    if isinstance(evidence, dict) and evidence.get('quote'):
                        persona_evidence_quotes.append(f"- {evidence['quote']}")
            
            # Get context data
            pv_context = context.get('pv_report_context', [])
            insights_context = context.get('actionable_insights_context', [])
            customer_profile = context.get('customer_profile', {})
            
            # Combine context into text format
            pv_text = '\n'.join([chunk.get('content', '') for chunk in pv_context if isinstance(chunk, dict)])
            insights_text = '\n'.join([chunk.get('content', '') for chunk in insights_context if isinstance(chunk, dict)])
            
            print(f"🔍 DEBUG: [QUESTIONS] Generating {questions_per_assumption} questions for assumption {assumption.get('id', 'Unknown')}")
            print(f"🔍 DEBUG: [QUESTIONS] Using persona context for {persona_name}: {bool(persona_data)}")
            
            # Build questions generation prompt
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert field researcher generating interview questions to validate market assumptions.\n\n"
                        f"Generate exactly {questions_per_assumption} targeted questions to test the given assumption with the specific persona.\n"
                        "The assumption is mapped to a specific customer profile component (JTBD, Pain, or Gain).\n\n"
                        "CRITICAL: Since assumptions focus on CURRENT STATE, questions must gather:\n"
                        "1. BASELINE DATA: Current behaviors, experiences, and challenges\n"
                        "2. CONTEXT DATA: Why they do what they do, what influences their decisions\n"
                        "3. VALIDATION DATA: Evidence that confirms or refutes the assumption\n\n"
                        "Requirements:\n"
                        f"- Exactly {questions_per_assumption} questions, no more, no less\n"
                        "- Questions must be open-ended and designed for interviews\n"
                        "- Questions should validate the assumption through real user behavior and needs\n"
                        "- Questions must be relevant to the specific persona's context and characteristics\n"
                        "- Questions must be tailored to the customer profile component being tested\n"
                        "- Include behavioral, attitudinal, and contextual questions\n"
                        "- Questions should uncover current state, not hypothetical futures\n"
                        "- Avoid leading questions - seek genuine validation or invalidation\n"
                        "- Each question gets a unique ID and component_type field\n\n"
                        "COMPONENT-SPECIFIC FOCUS:\n"
                        "- JTBD questions: Focus on what users currently do, try to accomplish, and their goals\n"
                        "  Example: 'Walk me through how you currently plan meals for your family'\n"
                        "- Pain questions: Focus on current frustrations, obstacles, and problems they face\n"
                        "  Example: 'What are the biggest challenges you face when trying to prepare nutritious meals?'\n"
                        "- Gain questions: Focus on what they currently value, desire, or prioritize\n"
                        "  Example: 'What would make meal planning easier for you right now?'\n\n"
                        "QUESTION TYPES TO INCLUDE:\n"
                        "1. BEHAVIORAL: 'Tell me about the last time you...' (reveals actual behavior)\n"
                        "2. FREQUENCY: 'How often do you...' (quantifies current patterns)\n"
                        "3. CONTEXTUAL: 'What factors influence your decision to...' (reveals motivations)\n"
                        "4. COMPARATIVE: 'How do you currently handle X compared to Y?' (reveals preferences)\n"
                        "5. EXPLORATORY: 'What have you tried so far?' (reveals current solutions)\n\n"
                        "AVOID THESE QUESTION TYPES:\n"
                        "❌ Hypothetical: 'Would you use X if...'\n"
                        "❌ Leading: 'Don't you think X would be better?'\n"
                        "❌ Future-focused: 'Will you do X in the future?'\n"
                        "❌ Pricing: 'How much would you pay for X?'\n\n"
                        f"JSON schema: {{\"questions\": [{{\"id\": \"string\", \"text\": \"string\", \"component_type\": \"jtbd|pain|gain\", \"type\": \"behavioral|attitudinal|contextual\", \"assumption_id\": \"string\", \"persona_name\": \"string\"}}]}}"
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
ASSUMPTION TO TEST: {assumption_text}
COMPONENT TYPE: {component_type.upper()} (This assumption tests the {component_type} aspect of the customer profile)

PERSONA PROFILE:
Name: {persona_name}
Description: {persona_description}
Problem Relationship: {persona_problem_relationship}

PERSONA EVIDENCE FROM ORIGINAL RESEARCH:
{chr(10).join(persona_evidence_quotes) if persona_evidence_quotes else 'No specific persona evidence available'}

ASSUMPTION EVIDENCE: {assumption_evidence}

CUSTOMER PROFILE CONTEXT FOR THIS PERSONA:
Jobs to be Done: {[item.get('label', '') for item in customer_profile.get('jtbd', [])]}
Pains: {[item.get('label', '') for item in customer_profile.get('pains', [])]}
Gains: {[item.get('label', '') for item in customer_profile.get('gains', [])]}

RESEARCH EVIDENCE [REPORT]:
{pv_text[:1000]}

RESEARCH EVIDENCE [INSIGHTS]:
{insights_text[:1000]}

Generate {questions_per_assumption} interview questions that:

1. VALIDATE THE CURRENT STATE ASSUMPTION with {persona_name}
   - Focus on what they currently do, experience, or need
   - Gather evidence about their present situation
   - Avoid asking about hypothetical futures or interventions

2. FOCUS ON THE {component_type.upper()} ASPECT
   - JTBD: Current jobs, tasks, goals they're trying to accomplish
   - Pain: Current frustrations, obstacles, problems they face
   - Gain: Current desires, values, priorities they have

3. USE THESE QUESTION PATTERNS:
   - "Tell me about the last time you..." (specific recent behavior)
   - "Walk me through how you currently..." (process understanding)
   - "What challenges do you face when..." (pain identification)
   - "How often do you..." (frequency quantification)
   - "What have you tried so far to..." (current solutions)

4. GATHER ACTIONABLE DATA:
   - Specific examples from their recent experience
   - Frequency and patterns of current behavior
   - Context and motivations behind their actions
   - Current workarounds and solutions they use
   - Concrete evidence that validates or invalidates the assumption

5. ENSURE QUESTIONS ARE:
   - Open-ended (not yes/no)
   - Non-leading (neutral tone)
   - Focused on current state (not future)
   - Specific to {persona_name}'s context
   - Grounded in the persona and research evidence

CRITICAL RULES:
✅ DO: Ask about current behavior, recent experiences, and present needs
✅ DO: Use "currently", "right now", "last time", "how often"
✅ DO: Seek specific examples and concrete evidence

❌ DON'T: Ask "would you" or "will you" questions
❌ DON'T: Ask about willingness to pay or future adoption
❌ DON'T: Lead the interviewee toward a desired answer
❌ DON'T: Ask hypothetical scenario questions

IMPORTANT: All questions must have component_type="{component_type}" and be specifically designed to validate the CURRENT STATE {component_type} assumption through concrete evidence from {persona_name}'s present experience.
""",
                },
            ]
            
            # Use original VPM AI service for consistency
            from core.ai_service import AIService
            ai_service = AIService()
            
            # Create monitoring context for AI usage tracking
            monitoring_context = None
            try:
                from monitor.tokens.models import AIUsageContext
                monitoring_context = AIUsageContext(
                    user_id=None,
                    tenant_id=None,
                    project_id=project_id,
                    feature_id="vpm_questionnaire_generation",
                    workflow_name="field_prep_workflow",
                    step_name="generate_questionnaire",
                    environment="prod"
                )
            except ImportError:
                pass
            
            # Call AI service with monitoring
            response_data = ai_service.chat_json(messages, {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "component_type": {"type": "string", "enum": ["jtbd", "pain", "gain"]},
                                "type": {"type": "string", "enum": ["behavioral", "attitudinal", "contextual"]},
                                "assumption_id": {"type": "string"},
                                "persona_name": {"type": "string"}
                            },
                            "required": ["id", "text", "component_type", "type", "assumption_id", "persona_name"]
                        },
                        "minItems": questions_per_assumption,
                        "maxItems": questions_per_assumption
                    }
                },
                "required": ["questions"]
            }, monitoring_context=monitoring_context)
            
            questions = response_data.get('questions', [])
            
            # COMPONENT TYPE VALIDATION: Ensure all questions have the correct component_type
            print(f"🔍 DEBUG: [QUESTIONS] Validating component_type for {len(questions)} questions")
            for question in questions:
                question_component = question.get('component_type', 'missing')
                if question_component != component_type:
                    print(f"⚠️ WARNING: Question component_type mismatch! Expected: {component_type}, Got: {question_component}")
                    print(f"  - Question: {question.get('text', '')[:60]}...")
                else:
                    print(f"✅ SUCCESS: Question has correct component_type: {component_type}")
            
            # Add metadata and sequential IDs to each question
            for i, question in enumerate(questions):
                sequential_question_id = f"question-{start_question_number + i:03d}"  # e.g., question-001, question-002
                
                question['id'] = sequential_question_id  # Override AI-generated ID with sequential one
                question['assumption_id'] = assumption.get('id', f"assumption_{persona_name.lower().replace(' ', '_')}")
                question['hypothesis_id'] = hypothesis_id
                question['persona_name'] = persona_name
                question['component_type'] = component_type  # Ensure component_type is set from assumption
                question['generated_at'] = datetime.utcnow().isoformat()
                
                print(f"✅ DEBUG: Generated question {sequential_question_id} for {persona_name}: {question.get('text', '')[:60]}...")
            
            print(f"✅ DEBUG: Generated {len(questions)} questions for assumption {assumption.get('id', 'Unknown')}")
            
            return questions
            
        except Exception as e:
            print(f"❌ ERROR: Failed to generate questions for assumption: {str(e)}")
            return []
    
    async def _save_questionnaires_to_project(self, project_id: str, questionnaires: List[Dict[str, Any]], user_id: str) -> bool:
        """
        Save generated questionnaires to the project's field_prep_data.
        """
        try:
            # Get current project data using service role client
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            project_result = supabase.client.table('vmp_projects').select('*').eq('id', project_id).single().execute()
            if not project_result.data:
                return False
            
            project_data = project_result.data
            
            # Update field_prep_data with questionnaires
            field_prep_data = project_data.get('field_prep_data', {})
            field_prep_data['questionnaires'] = questionnaires
            field_prep_data['questionnaires_generated_at'] = datetime.utcnow().isoformat()
            field_prep_data['stage'] = 'questionnaires_completed'
            
            print(f"🔍 DEBUG: [SAVE_QUESTIONNAIRES] Updating field_prep_data with {len(questionnaires)} questions")
            print(f"🔍 DEBUG: [SAVE_QUESTIONNAIRES] Questions data: {[(q.get('id', 'No ID'), q.get('persona_name', 'Unknown')) for q in questionnaires[:5]]}")  # Show first 5
            
            # Save back to database (supabase already initialized above)
            result = supabase.client.table('vmp_projects').update({
                'field_prep_data': field_prep_data,
                'current_step': 'completed',  # Final step after questionnaires
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            print(f"🔍 DEBUG: [SAVE_QUESTIONNAIRES] Database update result: {bool(result.data)}")
            if result.data:
                print(f"✅ DEBUG: [SAVE_QUESTIONNAIRES] Updated project {project_id} with field_prep_data")
                
                # 📊 WORKFLOW STATUS: Mark questionnaires as completed
                try:
                    from .workflow_status_service import get_workflow_status_service, WorkflowStage
                    tenant_id = project_data.get('tenant_id')
                    if tenant_id:
                        workflow_service = get_workflow_status_service()
                        workflow_service.set_stage_completed(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            stage=WorkflowStage.QUESTIONNAIRES,
                            additional_metadata={"questionnaires_count": len(questionnaires)}
                        )
                except Exception as status_error:
                    print(f"⚠️ DEBUG: [SAVE_QUESTIONNAIRES] Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk questionnaires for "Chat with Project" feature
                try:
                    from .project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    # Get tenant_id from project data
                    tenant_id = project_data.get('tenant_id')
                    if tenant_id:
                        await chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.QUESTIONNAIRE,
                            feature_data={"questionnaires": questionnaires}
                        )
                        print(f"🚀 DEBUG: [SAVE_QUESTIONNAIRES] Background chunking spawned for questionnaires")
                except Exception as chunk_error:
                    print(f"⚠️ DEBUG: [SAVE_QUESTIONNAIRES] Background chunking failed (non-blocking): {chunk_error}")
            else:
                print(f"❌ DEBUG: [SAVE_QUESTIONNAIRES] No data returned from database update")
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ ERROR: Failed to save questionnaires: {str(e)}")
            return False
    
    async def get_field_prep_progress(self, project_id: str) -> Dict[str, Any]:
        """Get the current Field Prep progress for a project."""
        try:
            # Get all field prep artifacts
            stages = [
                FieldPrepStage.HYPOTHESIS,
                FieldPrepStage.ASSUMPTIONS, 
                FieldPrepStage.STAKEHOLDERS,
                FieldPrepStage.QUESTIONNAIRES
            ]
            
            completed_stages = []
            artifacts_summary = {}
            
            for stage in stages:
                artifact = await self._get_field_prep_artifact(project_id, stage)
                if artifact['success']:
                    completed_stages.append(stage)
                    artifacts_summary[stage.value] = {
                        "completed": True,
                        "created_at": artifact.get('created_at'),
                        "item_count": len(artifact['artifact']) if isinstance(artifact['artifact'], list) else 1
                    }
                else:
                    artifacts_summary[stage.value] = {"completed": False}
            
            # Determine current and next stage
            if not completed_stages:
                current_stage = None
                next_stage = FieldPrepStage.HYPOTHESIS
            elif len(completed_stages) == len(stages):
                current_stage = FieldPrepStage.COMPLETED
                next_stage = None
            else:
                current_stage = completed_stages[-1]
                next_stage = stages[len(completed_stages)]
            
            # Calculate progress percentage
            progress_percentage = (len(completed_stages) / len(stages)) * 100
            
            # Check if can proceed to next stage
            can_proceed = next_stage is not None
            requirements = []
            
            if next_stage == FieldPrepStage.HYPOTHESIS:
                # Check if VPC is completed
                project_context = await self._get_project_context(project_id)
                if not project_context['success'] or not project_context['data'].get('vpc_artifacts'):
                    can_proceed = False
                    requirements.append("Complete VPC generation first")
            
            return {
                'success': True,
                'current_stage': current_stage,
                'completed_stages': completed_stages,
                'next_stage': next_stage,
                'progress_percentage': progress_percentage,
                'artifacts_summary': artifacts_summary,
                'can_proceed': can_proceed,
                'requirements_for_next_stage': requirements
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to get field prep progress: {str(e)}"
            }
    
    async def get_questionnaires(self, project_id: str, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Get generated questionnaires for a project.
        
        Args:
            project_id: Project ID
            user_id: User ID
            tenant_id: Tenant ID
            
        Returns:
            Dict containing success status and questionnaires data
        """
        try:
            print(f"🔍 DEBUG: [GET_QUESTIONNAIRES] Getting questionnaires for project: {project_id}")
            
            # FIXED: Use service role client like save operation to bypass user_id restrictions
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            project_result = supabase.client.table('vmp_projects').select('*').eq('id', project_id).execute()
            
            if not project_result.data:
                print(f"❌ DEBUG: [GET_QUESTIONNAIRES] Project not found: {project_id}")
                return {
                    'success': False,
                    'error': 'Project not found'
                }
            
            project_data = project_result.data[0]
            field_prep_data = project_data.get('field_prep_data', {})
            questionnaires = field_prep_data.get('questionnaires', [])
            
            if not questionnaires:
                print(f"❌ DEBUG: [GET_QUESTIONNAIRES] No questionnaires found in project")
                return {
                    'success': False,
                    'error': 'No questionnaires found for this project'
                }
            
            print(f"✅ DEBUG: [GET_QUESTIONNAIRES] Found {len(questionnaires)} questionnaires")
            
            return {
                'success': True,
                'questionnaires': questionnaires,
                'project_id': project_id,
                'stage': field_prep_data.get('stage', 'unknown'),
                'total_questions': len(questionnaires),
                'assumptions_count': field_prep_data.get('assumptions_count', 0),
                'personas_count': field_prep_data.get('personas_count', 0),
                'questions_per_assumption': field_prep_data.get('questions_per_assumption', 5)
            }
            
        except Exception as e:
            print(f"❌ ERROR: [GET_QUESTIONNAIRES] Failed to get questionnaires: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to get questionnaires: {str(e)}"
            }
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    async def _get_project_context(self, project_id: str) -> Dict[str, Any]:
        """Get complete project context including VPC and vector store data."""
        try:
            print(f"🔍 DEBUG: [_get_project_context] Starting for project: {project_id}")
            
            # Get VPC artifacts from database
            print(f"🔍 DEBUG: [_get_project_context] Retrieving VPC artifacts...")
            vpc_artifacts = await self._get_vpc_artifacts(project_id)
            if not vpc_artifacts:
                print(f"❌ DEBUG: [_get_project_context] No VPC artifacts found")
                return {
                    'success': False,
                    'error': "No VPC artifacts found. Complete VPC generation first."
                }
            
            print(f"✅ DEBUG: [_get_project_context] VPC artifacts retrieved successfully")
            print(f"🔍 DEBUG: [_get_project_context] VPC artifacts type: {type(vpc_artifacts)}")
            if isinstance(vpc_artifacts, dict):
                print(f"🔍 DEBUG: [_get_project_context] VPC artifacts keys: {list(vpc_artifacts.keys())}")
            
            # Get dual vector store context for additional context
            print(f"🔍 DEBUG: [_get_project_context] Getting dual vector store context...")
            dual_context = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query="value proposition customer profile pain reliever gain creator",
                max_results_per_store=3
            )
            
            print(f"✅ DEBUG: [_get_project_context] Dual context search completed")
            print(f"🔍 DEBUG: [_get_project_context] Dual context keys: {list(dual_context.keys()) if dual_context else 'None'}")
            
            return {
                'success': True,
                'data': {
                    'project_id': project_id,
                    'vpc_artifacts': vpc_artifacts,
                    'pv_report_context': dual_context.get('pv_report_context', {}),
                    'actionable_insights_context': dual_context.get('actionable_insights_context', {})
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to get project context: {str(e)}"
            }
    
    async def _get_vpc_artifacts(self, project_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get the VPC data from the project."""
        try:
            print(f"🔍 DEBUG: [_get_vpc_artifacts] Querying database for project: {project_id}")
            
            # Get project data which contains vpc_data
            # Use a placeholder user_id if not provided (we'll query without user filter if needed)
            if not user_id:
                # Try to get project data without user filter first
                try:
                    # Query project directly without user_id filter
                    project_result = self.db_adapter.supabase.client.table('vmp_projects').select('*').eq('id', project_id).execute()
                    if project_result.data:
                        project_data = project_result.data[0]
                        print(f"✅ DEBUG: [_get_vpc_artifacts] Project data retrieved directly")
                    else:
                        print(f"❌ DEBUG: [_get_vpc_artifacts] No project found with ID: {project_id}")
                        return None
                except Exception as e:
                    print(f"❌ DEBUG: [_get_vpc_artifacts] Direct query failed: {str(e)}")
                    return None
            else:
                project_data = await self.db_adapter.get_project_with_selections(project_id, user_id)
            
            if not project_data:
                print(f"❌ DEBUG: [_get_vpc_artifacts] No project data found")
                return None
            
            print(f"✅ DEBUG: [_get_vpc_artifacts] Project data retrieved")
            print(f"🔍 DEBUG: [_get_vpc_artifacts] Project data keys: {list(project_data.keys())}")
            
            # Get VPC data from the project
            vpc_data = project_data.get('vpc_data', {})
            
            if not vpc_data:
                print(f"❌ DEBUG: [_get_vpc_artifacts] No vpc_data found in project")
                return None
            
            print(f"✅ DEBUG: [_get_vpc_artifacts] VPC data found")
            print(f"🔍 DEBUG: [_get_vpc_artifacts] VPC data keys: {list(vpc_data.keys())}")
            
            # Check for expected VPC structure
            if 'customer_profile' in vpc_data:
                print(f"✅ DEBUG: [_get_vpc_artifacts] customer_profile found")
                cp = vpc_data['customer_profile']
                if isinstance(cp, dict):
                    print(f"🔍 DEBUG: [_get_vpc_artifacts] customer_profile keys: {list(cp.keys())}")
                    
            if 'value_map' in vpc_data:
                print(f"✅ DEBUG: [_get_vpc_artifacts] value_map found")
                vm = vpc_data['value_map']
                if isinstance(vm, dict):
                    print(f"🔍 DEBUG: [_get_vpc_artifacts] value_map keys: {list(vm.keys())}")
                    
            if 'vpc_complete' in vpc_data:
                print(f"✅ DEBUG: [_get_vpc_artifacts] VPC marked as complete: {vpc_data['vpc_complete']}")
            
            # Check if VPC is complete
            if not vpc_data.get('vpc_complete', False):
                print(f"⚠️ DEBUG: [_get_vpc_artifacts] VPC not marked as complete, but returning data anyway")
            
            # Return the VPC data directly
            return vpc_data
            
        except Exception as e:
            print(f"❌ DEBUG: [_get_vpc_artifacts] Failed to get VPC artifacts: {str(e)}")
            return None
    
    async def _store_field_prep_artifact(
        self, 
        project_id: str, 
        stage: FieldPrepStage, 
        artifact_data: Any,
        user_id: str
    ) -> Dict[str, Any]:
        """Store field prep artifact in the field_prep_data column of vmp_projects table."""
        try:
            print(f"🔍 DEBUG: [_store_field_prep_artifact] Storing {stage.value} for project {project_id}")
            
            from datetime import datetime
            
            # Get current project data
            project_result = self.db_adapter.supabase.client.table('vmp_projects').select('field_prep_data').eq('id', project_id).execute()
            
            if not project_result.data:
                print(f"❌ DEBUG: [_store_field_prep_artifact] Project not found: {project_id}")
                return {
                    'success': False,
                    'error': f'Project not found: {project_id}'
                }
            
            # Get existing field_prep_data or initialize empty structure
            current_data = project_result.data[0]
            field_prep_data = current_data.get('field_prep_data', {})
            
            print(f"🔍 DEBUG: [_store_field_prep_artifact] Current field_prep_data keys: {list(field_prep_data.keys())}")
            
            # Update the specific stage data
            stage_key = stage.value.replace('field_prep_', '')  # Remove prefix: "hypothesis", "assumptions", etc.
            field_prep_data[stage_key] = artifact_data
            field_prep_data[f'{stage_key}_created_at'] = datetime.utcnow().isoformat()
            
            # Update workflow status
            if 'workflow_status' not in field_prep_data:
                field_prep_data['workflow_status'] = {}
            field_prep_data['workflow_status'][f'{stage_key}_completed'] = True
            field_prep_data['workflow_status']['last_updated'] = datetime.utcnow().isoformat()
            
            print(f"🔍 DEBUG: [_store_field_prep_artifact] Updated field_prep_data keys: {list(field_prep_data.keys())}")
            
            # Update the project with new field_prep_data
            update_result = self.db_adapter.supabase.client.table('vmp_projects').update({
                'field_prep_data': field_prep_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            if update_result.data:
                print(f"✅ DEBUG: [_store_field_prep_artifact] Successfully stored {stage_key} in field_prep_data")
                return {
                    'success': True,
                    'stage': stage_key,
                    'updated_keys': list(field_prep_data.keys())
                }
            else:
                print(f"❌ DEBUG: [_store_field_prep_artifact] Failed to update project")
                return {
                    'success': False,
                    'error': 'Failed to update project with field prep data'
                }
                
        except Exception as e:
            print(f"❌ DEBUG: [_store_field_prep_artifact] Exception: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to store artifact: {str(e)}"
            }
    
    async def _get_field_prep_artifact(
        self, 
        project_id: str, 
        stage: FieldPrepStage
    ) -> Dict[str, Any]:
        """Get field prep artifact from field_prep_data column."""
        try:
            print(f"🔍 DEBUG: [_get_field_prep_artifact] Getting {stage.value} for project {project_id}")
            
            # Get project field_prep_data
            project_result = self.db_adapter.supabase.client.table('vmp_projects').select('field_prep_data').eq('id', project_id).execute()
            
            if not project_result.data:
                print(f"❌ DEBUG: [_get_field_prep_artifact] Project not found: {project_id}")
                return {
                    'success': False,
                    'error': f'Project not found: {project_id}',
                    'artifact': None,
                    'created_at': None
                }
            
            # Get field_prep_data
            current_data = project_result.data[0]
            field_prep_data = current_data.get('field_prep_data', {})
            
            print(f"🔍 DEBUG: [_get_field_prep_artifact] Available field_prep_data keys: {list(field_prep_data.keys())}")
            
            # Get specific stage data
            stage_key = stage.value.replace('field_prep_', '')  # Remove prefix: "hypothesis", "assumptions", etc.
            artifact_data = field_prep_data.get(stage_key)
            created_at = field_prep_data.get(f'{stage_key}_created_at')
            
            if artifact_data:
                print(f"✅ DEBUG: [_get_field_prep_artifact] Found {stage_key} artifact")
                return {
                    'success': True,
                    'artifact': artifact_data,
                    'created_at': created_at
                }
            else:
                print(f"❌ DEBUG: [_get_field_prep_artifact] No {stage_key} artifact found")
                return {
                    'success': False,
                    'artifact': None,
                    'created_at': None
                }
                
        except Exception as e:
            print(f"❌ DEBUG: [_get_field_prep_artifact] Exception: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to get artifact: {str(e)}",
                'artifact': None,
                'created_at': None
            }
    
    async def _update_project_stage(self, project_id: str, stage: FieldPrepStage):
        """Update project workflow stage."""
        try:
            # Update the project workflow stage in the database
            await self.db_adapter.update_project_stage(project_id, stage.value)
            print(f"✅ Updated project {project_id} to stage: {stage.value}")
        except Exception as e:
            print(f"Failed to update project stage: {str(e)}")
    
    def _format_vpc_data_for_field_prep(self, vpc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format VPC data for the original Field Prep service."""
        try:
            # The original Field Prep service expects vpc_v1 to have a specific structure
            # It should contain both customer_profile and value_map sections
            
            if not vpc_data:
                return {}
            
            # If vpc_data is already in the correct format, return as-is
            if "customer_profile" in vpc_data and "value_map" in vpc_data:
                print("✅ VPC data already in correct format")
                return vpc_data
            
            # If vpc_data contains artifact_data, extract it
            if "artifact_data" in vpc_data:
                vpc_content = vpc_data["artifact_data"]
            else:
                vpc_content = vpc_data
            
            # Ensure we have the required structure
            formatted_data = {
                "customer_profile": vpc_content.get("customer_profile", {}),
                "value_map": vpc_content.get("value_map", {})
            }
            
            # Validate that we have meaningful data
            if not formatted_data["customer_profile"] and not formatted_data["value_map"]:
                print("⚠️ WARNING: VPC data appears to be empty or malformed")
                print(f"Original VPC data keys: {list(vpc_data.keys())}")
                print(f"VPC data sample: {str(vpc_data)[:200]}...")
            
            print(f"✅ Formatted VPC data with customer_profile: {bool(formatted_data['customer_profile'])}, value_map: {bool(formatted_data['value_map'])}")
            return formatted_data
            
        except Exception as e:
            print(f"❌ Error formatting VPC data: {str(e)}")
            return {}
    
    # ==================== ORIGINAL VPM SERVICE METHODS ====================
    
    async def _generate_hypothesis_with_original_service(
        self, 
        project_id: str,
        vpc_data: Dict[str, Any], 
        context_data: Dict[str, Any],
        creativity_level: float
    ) -> Dict[str, Any]:
        """Generate hypothesis using original VPM Field Prep service."""
        try:
            # Create GraphState object that the original service expects
            state = self.GraphState()
            
            # Format VPC data properly for the original service
            # The original service expects vpc_v1 to contain both customer_profile and value_map
            formatted_vpc_data = self._format_vpc_data_for_field_prep(vpc_data)
            
            print(f"🔍 DEBUG: Formatted VPC data keys: {list(formatted_vpc_data.keys())}")
            print(f"🔍 DEBUG: VPC data structure: {json.dumps(formatted_vpc_data, indent=2)[:500]}...")
            
            # Populate state with formatted VPC data and context
            state["vpc_v1"] = formatted_vpc_data
            state["report_id"] = project_id  # Use the actual project_id for RAG content retrieval
            
            print(f"🔍 DEBUG: Set report_id to: {project_id}")
            
            # Add context from dual vector store for additional context
            if context_data.get("pv_report_context"):
                state["pv_report_context"] = context_data["pv_report_context"]
                print(f"🔍 DEBUG: Added PV report context")
            if context_data.get("actionable_insights_context"):
                state["actionable_insights_context"] = context_data["actionable_insights_context"]
                print(f"🔍 DEBUG: Added actionable insights context")
            
            print(f"🚀 DEBUG: Calling original Field Prep service with state keys: {list(state.keys())}")
            print(f"🔍 DEBUG: Final context summary before calling original service:")
            print(f"  - VPC data available: {bool(formatted_vpc_data)}")
            print(f"  - PV report context: {bool(context_data.get('pv_report_context'))}")
            print(f"  - Actionable insights context: {bool(context_data.get('actionable_insights_context'))}")
            print(f"  - Report ID: {state.get('report_id')}")
            
            # Call original VPM Field Prep service with context (bypasses RAG retrieval)
            print(f"🚀 DEBUG: Invoking original_field_prep.generate_hypothesis_with_context()...")
            
            # Prepare context data for the original service
            context_for_original = {
                'pv_report': {
                    'content': str(context_data.get('pv_report_context', {}))
                },
                'actionable_insights': {
                    'content': str(context_data.get('actionable_insights_context', {}))
                }
            }
            
            result_state = self.original_field_prep.generate_hypothesis_with_context(state, context_for_original)
            print(f"✅ DEBUG: Original Field Prep service completed")
            print(f"🔍 DEBUG: Result state keys: {list(result_state.keys()) if result_state else 'None'}")
            
            # Extract hypothesis from result state
            # The original service stores hypothesis in field_prep section
            if "field_prep" in result_state and result_state["field_prep"].get("hypothesis"):
                hypothesis = result_state["field_prep"]["hypothesis"]
                print(f"✅ DEBUG: Successfully extracted hypothesis from field_prep section")
                print(f"🔍 DEBUG: Hypothesis keys: {list(hypothesis.keys()) if isinstance(hypothesis, dict) else 'Not a dict'}")
                return {
                    'success': True,
                    'hypothesis': hypothesis
                }
            elif "error" in result_state:
                print(f"❌ DEBUG: Error in result state: {result_state['error']}")
                return {
                    'success': False,
                    'error': f"VPM Field Prep error: {result_state['error']}"
                }
            else:
                print(f"❌ DEBUG: No hypothesis found in result state")
                print(f"🔍 DEBUG: Available result state keys: {list(result_state.keys())}")
                if "field_prep" in result_state:
                    field_prep_keys = list(result_state["field_prep"].keys()) if isinstance(result_state["field_prep"], dict) else "Not a dict"
                    print(f"🔍 DEBUG: field_prep keys: {field_prep_keys}")
                return {
                    'success': False,
                    'error': "VPM Field Prep did not generate hypothesis"
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to call original VPM Field Prep service: {str(e)}"
            }
    
    async def _generate_assumptions_with_original_service(
        self, 
        project_id: str,
        vpc_data: Dict[str, Any], 
        context_data: Dict[str, Any],
        hypothesis: Dict[str, Any],
        max_assumptions: int
    ) -> Dict[str, Any]:
        """Generate assumptions using original VPM Field Prep service with full context."""
        try:
            print(f"🔍 DEBUG: [_generate_assumptions_with_original_service] Starting for project: {project_id}")
            
            # Create GraphState with all contexts
            state = self.GraphState()
            
            # Add hypothesis context
            state["field_prep"] = {"hypothesis": hypothesis}
            state["max_assumptions"] = max_assumptions
            state["report_id"] = project_id
            
            print(f"🔍 DEBUG: Added hypothesis context to state")
            print(f"🔍 DEBUG: Hypothesis keys: {list(hypothesis.keys()) if isinstance(hypothesis, dict) else 'Not a dict'}")
            
            # Add formatted VPC context
            formatted_vpc_data = self._format_vpc_data_for_field_prep(vpc_data)
            state["vpc_v1"] = formatted_vpc_data
            print(f"🔍 DEBUG: Added VPC data for assumptions generation")
            print(f"🔍 DEBUG: VPC data keys: {list(formatted_vpc_data.keys())}")
                
            # Add dual vector store context
            if context_data.get("pv_report_context"):
                state["pv_report_context"] = context_data["pv_report_context"]
                print(f"🔍 DEBUG: Added PV report context for assumptions")
            if context_data.get("actionable_insights_context"):
                state["actionable_insights_context"] = context_data["actionable_insights_context"]
                print(f"🔍 DEBUG: Added actionable insights context for assumptions")
            
            print(f"🚀 DEBUG: Calling original Field Prep service for assumptions with state keys: {list(state.keys())}")
            print(f"🔍 DEBUG: Final context summary for assumptions:")
            print(f"  - VPC data available: {bool(formatted_vpc_data)}")
            print(f"  - PV report context: {bool(context_data.get('pv_report_context'))}")
            print(f"  - Actionable insights context: {bool(context_data.get('actionable_insights_context'))}")
            print(f"  - Hypothesis available: {bool(hypothesis)}")
            print(f"  - Max assumptions: {max_assumptions}")
            
            # Call original VPM Field Prep service with context (bypasses RAG retrieval)
            print(f"🚀 DEBUG: Invoking original_field_prep.generate_assumptions_with_context()...")
            
            # Prepare context data for the original service
            context_for_original = {
                'pv_report': {
                    'content': str(context_data.get('pv_report_context', {}))
                },
                'actionable_insights': {
                    'content': str(context_data.get('actionable_insights_context', {}))
                }
            }
            
            result_state = self.original_field_prep.generate_assumptions_with_context(state, context_for_original)
            print(f"✅ DEBUG: Original Field Prep assumptions service completed")
            print(f"🔍 DEBUG: Result state keys: {list(result_state.keys()) if result_state else 'None'}")
            
            # Extract assumptions from result state
            # The original service stores assumptions in field_prep section
            if "field_prep" in result_state and result_state["field_prep"].get("assumptions"):
                assumptions = result_state["field_prep"]["assumptions"]
                print(f"✅ DEBUG: Successfully extracted assumptions from field_prep section")
                print(f"🔍 DEBUG: Number of assumptions: {len(assumptions) if isinstance(assumptions, list) else 'Not a list'}")
                return {
                    'success': True,
                    'assumptions': assumptions
                }
            elif "error" in result_state:
                print(f"❌ DEBUG: Error in result state: {result_state['error']}")
                return {
                    'success': False,
                    'error': f"VPM Field Prep error: {result_state['error']}"
                }
            else:
                print(f"❌ DEBUG: No assumptions found in result state")
                print(f"🔍 DEBUG: Available result state keys: {list(result_state.keys())}")
                if "field_prep" in result_state:
                    field_prep_keys = list(result_state["field_prep"].keys()) if isinstance(result_state["field_prep"], dict) else "Not a dict"
                    print(f"🔍 DEBUG: field_prep keys: {field_prep_keys}")
                return {
                    'success': False,
                    'error': "VPM Field Prep did not generate assumptions"
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to call original VPM Field Prep service: {str(e)}"
            }
    
    async def _assign_stakeholders_with_original_service(
        self, 
        project_id: str,
        vpc_data: Dict[str, Any], 
        context_data: Dict[str, Any],
        hypothesis: Dict[str, Any],
        assumptions: List[Dict[str, Any]], 
        stakeholder_preferences: Optional[List[StakeholderType]]
    ) -> Dict[str, Any]:
        """Assign stakeholders using original VPM Field Prep service with full context."""
        try:
            print(f"🔍 DEBUG: [_assign_stakeholders_with_original_service] Starting for project: {project_id}")
            
            # Create GraphState with all contexts
            state = self.GraphState()
            
            # Add assumptions and hypothesis context
            state["field_prep"] = {
                "hypothesis": hypothesis,
                "assumptions": assumptions
            }
            state["report_id"] = project_id
            
            print(f"🔍 DEBUG: Added hypothesis and assumptions context to state")
            print(f"🔍 DEBUG: Number of assumptions: {len(assumptions) if isinstance(assumptions, list) else 'Not a list'}")
            
            # Add stakeholder preferences if provided
            if stakeholder_preferences:
                state["stakeholder_preferences"] = [sp.value for sp in stakeholder_preferences]
                print(f"🔍 DEBUG: Added stakeholder preferences: {[sp.value for sp in stakeholder_preferences]}")
            
            # Add formatted VPC context
            formatted_vpc_data = self._format_vpc_data_for_field_prep(vpc_data)
            state["vpc_v1"] = formatted_vpc_data
            print(f"🔍 DEBUG: Added VPC data for stakeholder assignment")
            print(f"🔍 DEBUG: VPC data keys: {list(formatted_vpc_data.keys())}")
                
            # Add dual vector store context
            if context_data.get("pv_report_context"):
                state["pv_report_context"] = context_data["pv_report_context"]
                print(f"🔍 DEBUG: Added PV report context for stakeholders")
            if context_data.get("actionable_insights_context"):
                state["actionable_insights_context"] = context_data["actionable_insights_context"]
                print(f"🔍 DEBUG: Added actionable insights context for stakeholders")
            
            print(f"🚀 DEBUG: Calling original Field Prep service for stakeholders with state keys: {list(state.keys())}")
            print(f"🔍 DEBUG: Final context summary for stakeholders:")
            print(f"  - VPC data available: {bool(formatted_vpc_data)}")
            print(f"  - PV report context: {bool(context_data.get('pv_report_context'))}")
            print(f"  - Actionable insights context: {bool(context_data.get('actionable_insights_context'))}")
            print(f"  - Hypothesis available: {bool(hypothesis)}")
            print(f"  - Assumptions available: {bool(assumptions)}")
            print(f"  - Stakeholder preferences: {bool(stakeholder_preferences)}")
            
            # Call original VPM Field Prep service with context (bypasses RAG retrieval)
            print(f"🚀 DEBUG: Invoking original_field_prep.assign_stakeholders_with_context()...")
            
            # Prepare context data for the original service
            context_for_original = {
                'pv_report': {
                    'content': str(context_data.get('pv_report_context', {}))
                },
                'actionable_insights': {
                    'content': str(context_data.get('actionable_insights_context', {}))
                }
            }
            
            # Debug: Check assumptions before calling original service
            if "field_prep" in state and "assumptions" in state["field_prep"]:
                assumptions_before = state["field_prep"]["assumptions"]
                print(f"🔍 DEBUG: Assumptions before stakeholder assignment:")
                for i, assumption in enumerate(assumptions_before):
                    if isinstance(assumption, dict):
                        print(f"  Assumption {i}: id={assumption.get('id')}, text={assumption.get('text', '')[:50]}...")
                        print(f"  Has stakeholders: {bool(assumption.get('stakeholders'))}")
                    else:
                        print(f"  Assumption {i}: {type(assumption)} - {assumption}")
            
            result_state = self.original_field_prep.assign_stakeholders_with_context(state, context_for_original)
            print(f"✅ DEBUG: Original Field Prep stakeholders service completed")
            print(f"🔍 DEBUG: Result state keys: {list(result_state.keys()) if result_state else 'None'}")
            
            # Debug: Check assumptions after calling original service
            if "field_prep" in result_state and "assumptions" in result_state["field_prep"]:
                assumptions_after = result_state["field_prep"]["assumptions"]
                print(f"🔍 DEBUG: Assumptions after stakeholder assignment:")
                for i, assumption in enumerate(assumptions_after):
                    if isinstance(assumption, dict):
                        stakeholders = assumption.get('stakeholders', [])
                        print(f"  Assumption {i}: id={assumption.get('id')}")
                        print(f"  Assigned stakeholders: {stakeholders}")
                    else:
                        print(f"  Assumption {i}: {type(assumption)} - {assumption}")
            
            # Extract stakeholder assignments from result state
            # The original service adds stakeholders to each assumption in the assumptions array
            if "field_prep" in result_state and result_state["field_prep"].get("assumptions"):
                assumptions_with_stakeholders = result_state["field_prep"]["assumptions"]
                print(f"✅ DEBUG: Successfully extracted assumptions with stakeholders from field_prep section")
                print(f"🔍 DEBUG: Number of assumptions: {len(assumptions_with_stakeholders) if isinstance(assumptions_with_stakeholders, list) else 'Not a list'}")
                
                # Check if stakeholders were actually assigned
                stakeholder_count = 0
                for assumption in assumptions_with_stakeholders:
                    if isinstance(assumption, dict) and assumption.get("stakeholders"):
                        stakeholder_count += len(assumption["stakeholders"])
                
                print(f"🔍 DEBUG: Total stakeholders assigned: {stakeholder_count}")
                
                if stakeholder_count > 0:
                    return {
                        'success': True,
                        'stakeholder_assignments': assumptions_with_stakeholders,  # Assumptions with embedded stakeholders
                        'assignment_summary': {
                            'total_assumptions': len(assumptions_with_stakeholders),
                            'total_stakeholders_assigned': stakeholder_count
                        }
                    }
                else:
                    print(f"❌ DEBUG: No stakeholders were assigned to assumptions")
                    return {
                        'success': False,
                        'error': "No stakeholders were assigned to assumptions"
                    }
            elif "error" in result_state:
                print(f"❌ DEBUG: Error in result state: {result_state['error']}")
                return {
                    'success': False,
                    'error': f"VPM Field Prep error: {result_state['error']}"
                }
            else:
                print(f"❌ DEBUG: No assumptions found in result state")
                print(f"🔍 DEBUG: Available result state keys: {list(result_state.keys())}")
                if "field_prep" in result_state:
                    field_prep_keys = list(result_state["field_prep"].keys()) if isinstance(result_state["field_prep"], dict) else "Not a dict"
                    print(f"🔍 DEBUG: field_prep keys: {field_prep_keys}")
                return {
                    'success': False,
                    'error': "VPM Field Prep did not return assumptions with stakeholders"
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to call original VPM Field Prep service: {str(e)}"
            }
    
    async def _generate_questionnaires_with_original_service(
        self, 
        project_id: str,
        vpc_data: Dict[str, Any], 
        context_data: Dict[str, Any],
        hypothesis: Dict[str, Any],
        assumptions: List[Dict[str, Any]], 
        stakeholder_assignments: List[Dict[str, Any]], 
        questions_per_assumption: int,
        include_demographic_questions: bool
    ) -> Dict[str, Any]:
        """Generate questionnaires using original VPM Field Prep service with full context."""
        try:
            print(f"🔍 DEBUG: [_generate_questionnaires_with_original_service] Starting for project: {project_id}")
            
            # Create GraphState with all contexts
            state = self.GraphState()
            
            # Add full field prep context
            state["field_prep"] = {
                "hypothesis": hypothesis,
                "assumptions": stakeholder_assignments  # This contains assumptions with embedded stakeholders
            }
            state["questions_per_assumption"] = questions_per_assumption
            state["include_demographic_questions"] = include_demographic_questions
            state["report_id"] = project_id
            
            print(f"🔍 DEBUG: Added full field prep context to state")
            print(f"🔍 DEBUG: Number of stakeholder assignments: {len(stakeholder_assignments) if isinstance(stakeholder_assignments, list) else 'Not a list'}")
            print(f"🔍 DEBUG: Questions per assumption: {questions_per_assumption}")
            print(f"🔍 DEBUG: Include demographic questions: {include_demographic_questions}")
            
            # Debug: Check assumption structure
            print(f"🔍 DEBUG: Checking assumption structure for questionnaire generation:")
            for i, assumption in enumerate(stakeholder_assignments[:2]):  # Check first 2
                if isinstance(assumption, dict):
                    print(f"  Assumption {i}:")
                    print(f"    - id: {assumption.get('id')}")
                    print(f"    - type: {assumption.get('type')}")
                    print(f"    - text: {assumption.get('text', '')[:50]}...")
                    print(f"    - objective: {assumption.get('objective', '')[:50]}...")
                    print(f"    - indicators: {assumption.get('indicators', 'MISSING')}")
                    print(f"    - stakeholders: {assumption.get('stakeholders', 'MISSING')}")
                else:
                    print(f"  Assumption {i}: {type(assumption)} - {assumption}")
            
            # Add formatted VPC context
            formatted_vpc_data = self._format_vpc_data_for_field_prep(vpc_data)
            state["vpc_v1"] = formatted_vpc_data
            print(f"🔍 DEBUG: Added VPC data for questionnaire generation")
            print(f"🔍 DEBUG: VPC data keys: {list(formatted_vpc_data.keys())}")
                
            # Add dual vector store context
            if context_data.get("pv_report_context"):
                state["pv_report_context"] = context_data["pv_report_context"]
                print(f"🔍 DEBUG: Added PV report context for questionnaires")
            if context_data.get("actionable_insights_context"):
                state["actionable_insights_context"] = context_data["actionable_insights_context"]
                print(f"🔍 DEBUG: Added actionable insights context for questionnaires")
            
            print(f"🚀 DEBUG: Calling original Field Prep service for questionnaires with state keys: {list(state.keys())}")
            print(f"🔍 DEBUG: Final context summary for questionnaires:")
            print(f"  - VPC data available: {bool(formatted_vpc_data)}")
            print(f"  - PV report context: {bool(context_data.get('pv_report_context'))}")
            print(f"  - Actionable insights context: {bool(context_data.get('actionable_insights_context'))}")
            print(f"  - Hypothesis available: {bool(hypothesis)}")
            print(f"  - Assumptions available: {bool(assumptions)}")
            print(f"  - Stakeholder assignments available: {bool(stakeholder_assignments)}")
            
            # Call original VPM Field Prep service with context (bypasses RAG retrieval)
            print(f"🚀 DEBUG: Invoking original_field_prep.generate_questionnaires_with_context()...")
            
            # Prepare context data for the original service
            context_for_original = {
                'pv_report': {
                    'content': str(context_data.get('pv_report_context', {}))
                },
                'actionable_insights': {
                    'content': str(context_data.get('actionable_insights_context', {}))
                }
            }
            
            result_state = self.original_field_prep.generate_questionnaires_with_context(state, context_for_original)
            print(f"✅ DEBUG: Original Field Prep questionnaires service completed")
            print(f"🔍 DEBUG: Result state keys: {list(result_state.keys()) if result_state else 'None'}")
            
            # Extract questionnaires from result state
            # The original service adds questionnaires to each assumption in the assumptions array
            if "field_prep" in result_state and result_state["field_prep"].get("assumptions"):
                assumptions_with_questionnaires = result_state["field_prep"]["assumptions"]
                print(f"✅ DEBUG: Successfully extracted assumptions with questionnaires from field_prep section")
                print(f"🔍 DEBUG: Number of assumptions: {len(assumptions_with_questionnaires) if isinstance(assumptions_with_questionnaires, list) else 'Not a list'}")
                
                # Extract all questionnaires and count them
                all_questionnaires = []
                questionnaire_count = 0
                
                for assumption in assumptions_with_questionnaires:
                    if isinstance(assumption, dict) and assumption.get("questionnaires"):
                        assumption_questionnaires = assumption["questionnaires"]
                        questionnaire_count += len(assumption_questionnaires)
                        
                        # Add assumption context to each questionnaire
                        for questionnaire in assumption_questionnaires:
                            if isinstance(questionnaire, dict):
                                questionnaire["assumption_id"] = assumption.get("id")
                                questionnaire["assumption_text"] = assumption.get("text")
                                all_questionnaires.append(questionnaire)
                
                print(f"🔍 DEBUG: Total questionnaires extracted: {questionnaire_count}")
                
                if questionnaire_count > 0:
                    return {
                        'success': True,
                        'questionnaires': all_questionnaires,
                        'questionnaire_summary': {
                            'total_assumptions': len(assumptions_with_questionnaires),
                            'total_questionnaires': questionnaire_count,
                            'questionnaires_per_assumption': questionnaire_count / len(assumptions_with_questionnaires) if assumptions_with_questionnaires else 0
                        }
                    }
                else:
                    print(f"❌ DEBUG: No questionnaires were generated for assumptions")
                    return {
                        'success': False,
                        'error': "No questionnaires were generated for assumptions"
                    }
            elif "error" in result_state:
                print(f"❌ DEBUG: Error in result state: {result_state['error']}")
                return {
                    'success': False,
                    'error': f"VPM Field Prep error: {result_state['error']}"
                }
            else:
                print(f"❌ DEBUG: No assumptions found in result state")
                print(f"🔍 DEBUG: Available result state keys: {list(result_state.keys())}")
                if "field_prep" in result_state:
                    field_prep_keys = list(result_state["field_prep"].keys()) if isinstance(result_state["field_prep"], dict) else "Not a dict"
                    print(f"🔍 DEBUG: field_prep keys: {field_prep_keys}")
                return {
                    'success': False,
                    'error': "VPM Field Prep did not return assumptions with questionnaires"
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to call original VPM Field Prep service: {str(e)}"
            }
    
    async def get_progress(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get field prep progress from the current_step column in the database.
        
        Returns progress information including current step, completed steps, and next action.
        """
        try:
            # Get project from database
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            result = supabase.client.table('vmp_projects').select(
                'id, current_step, field_prep_data, vpc_data'
            ).eq('id', project_id).limit(1).execute()
            
            if not result.data:
                return {
                    'success': False,
                    'error': 'Project not found'
                }
            
            project = result.data[0]
            current_step = project.get('current_step', 'project_setup')
            field_prep_data = project.get('field_prep_data', {})
            
            # Define step progression
            step_order = [
                'project_setup',
                'persona_identification',
                'customer_profile',
                'field_prep_hypothesis',
                'field_prep_assumptions',
                'field_prep_questionnaires',
                'completed'
            ]
            
            # Calculate completed steps
            try:
                current_index = step_order.index(current_step)
            except ValueError:
                print(f"⚠️ WARNING: [GET_PROGRESS] Unknown current_step '{current_step}', defaulting to project_setup")
                # Handle legacy or unknown steps
                if current_step in ['value_map', 'project_setup']:
                    current_index = 0  # Reset to beginning
                elif current_step in ['persona_identification']:
                    current_index = 1
                else:
                    current_index = 0  # Default fallback
            
            completed_steps = step_order[:current_index]
            
            # Determine next action
            next_action = None
            if current_step == 'customer_profile':
                next_action = 'generate_hypothesis'
            elif current_step == 'field_prep_hypothesis':
                next_action = 'generate_assumptions'
            elif current_step == 'field_prep_assumptions':
                next_action = 'generate_questionnaires'
            elif current_step == 'field_prep_questionnaires':
                next_action = 'export_artifacts'
            elif current_step == 'completed':
                next_action = None
            else:
                next_action = 'continue_workflow'
            
            # Calculate progress percentage
            progress_percentage = (current_index / len(step_order)) * 100
            
            return {
                'success': True,
                'current_step': current_step,
                'completed_steps': completed_steps,
                'next_action': next_action,
                'progress_percentage': progress_percentage,
                'field_prep_data': field_prep_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to get progress: {str(e)}"
            }


def get_yuba_field_prep_service(auth_adapter, db_adapter, vector_adapter, credit_adapter):
    """Factory function to create YubaFieldPrepService instance."""
    return YubaFieldPrepService(auth_adapter, db_adapter, vector_adapter, credit_adapter)
