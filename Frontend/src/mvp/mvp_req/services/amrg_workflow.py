"""
LangGraph Workflow for MVP Requirements Generator (AMRG)

Orchestrates the multi-agent PRD generation workflow with:
- Eligibility validation
- Context loading
- Two-stage template routing
- Clarifying questions (with interrupt/resume)
- Optional web research
- PRD generation with validation and repair
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from ..models.state_models import AMRGState
from ..models.enums import RunStatus, ResearchMode, TemplateCode, ValidationStatus
from ..agents.template_router_coarse import TemplateRouterCoarseAgent
from ..agents.template_router_final import TemplateRouterFinalAgent
from ..agents.clarifying_questions import ClarifyingQuestionsAgent
from ..agents.prd_generator import PRDGeneratorAgent
from ..agents.repair_agent import RepairAgent
from .context_loader import ContextLoaderService
from .database_adapter import AMRGDatabaseAdapter
from .schema_validator import SchemaValidatorService
from ..templates.registry import get_template_spec

logger = logging.getLogger(__name__)


class AMRGWorkflow:
    """
    LangGraph workflow for AMRG PRD generation.
    
    Two-phase execution:
    1. Phase 1: Context → Coarse Routing → Questions (returns for user input)
    2. Phase 2: Answers → Final Routing → PRD Generation → Validation
    """
    
    def __init__(self):
        """Initialize workflow with agents and services."""
        # Services
        self.context_loader = ContextLoaderService()
        self.db_adapter = AMRGDatabaseAdapter()
        self.schema_validator = SchemaValidatorService()
        
        # Agents
        self.router_coarse = TemplateRouterCoarseAgent()
        self.router_final = TemplateRouterFinalAgent()
        self.questions_agent = ClarifyingQuestionsAgent()
        self.prd_generator = PRDGeneratorAgent()
        self.repair_agent = RepairAgent()
        
        logger.info("AMRG Workflow initialized")
    
    # ==================== PHASE 1: START RUN ====================
    
    async def start_run(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        research_mode: ResearchMode = ResearchMode.AUTO
    ) -> Dict[str, Any]:
        """
        Start a new AMRG run (Phase 1).
        
        Performs:
        1. Eligibility validation
        2. Context loading
        3. Coarse template routing
        4. Clarifying questions generation
        
        Returns run_id and questions for user to answer.
        """
        run_id = str(uuid.uuid4())
        
        logger.info(f"🚀 Starting AMRG run {run_id} for project {project_id}")
        
        try:
            # Step 1: Validate eligibility
            logger.info("Step 1: Validating eligibility...")
            is_eligible, missing_names, missing_details = self.context_loader.validate_eligibility(
                project_id, tenant_id
            )
            
            if not is_eligible:
                logger.error(f"Eligibility check failed: {missing_names}")
                return {
                    "success": False,
                    "error_code": "MISSING_REQUIRED_ARTIFACTS",
                    "missing_artifacts": missing_names,
                    "artifact_details": [d.model_dump() if hasattr(d, 'model_dump') else d.__dict__ for d in missing_details]
                }
            
            logger.info("✅ Step 1: Eligibility passed")
            
            # Step 2: Load context pack
            logger.info("Step 2: Loading context pack...")
            context_pack, error = self.context_loader.load_context_pack(project_id, tenant_id)
            
            if error:
                logger.error(f"Context loading failed: {error}")
                return {
                    "success": False,
                    "error_code": "CONTEXT_LOAD_FAILED",
                    "message": error
                }
            
            logger.info("✅ Step 2: Context pack loaded")
            
            # Step 3: Coarse routing
            logger.info("Step 3: Performing coarse template routing...")
            coarse_routing = await self.router_coarse.route(
                context_pack=context_pack,
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id
            )
            logger.info("✅ Step 3: Coarse routing complete")
            
            # Step 4: Generate clarifying questions
            logger.info("Step 4: Generating clarifying questions...")
            questions = await self.questions_agent.generate_questions(
                context_pack=context_pack,
                coarse_routing=coarse_routing,
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id
            )
            logger.info("✅ Step 4: Questions generated")
            
            # Step 5: Save run state
            logger.info("Step 5: Saving run state...")
            run_data = {
                "run_id": run_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "status": RunStatus.AWAITING_ANSWERS.value,
                "research_mode": research_mode.value,
                "context_pack": context_pack,
                "coarse_routing": coarse_routing,
                "clarifying_questions": questions,
                "clarifying_answers": [],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.db_adapter.save_amrg_run(project_id, tenant_id, run_data)
            logger.info("✅ Step 5: Run state saved")
            
            # Build response with questions
            from ..templates.registry import get_template_spec
            top_templates_response = []
            for t in coarse_routing["top_templates"]:
                spec = get_template_spec(TemplateCode(t["code"]))
                top_templates_response.append({
                    "code": t["code"],
                    "name": spec.name if spec else t["code"],
                    "confidence": t["confidence"],
                    "rationale": t["rationale"]
                })
            
            logger.info(f"✅ AMRG run {run_id} started successfully")
            
            return {
                "success": True,
                "run_id": run_id,
                "status": RunStatus.AWAITING_ANSWERS.value,
                "message": "Please answer the clarifying questions to continue",
                "coarse_routing": {
                    "top_templates": top_templates_response,
                    "confidence_threshold_met": coarse_routing["confidence_threshold_met"],
                    "routing_rationale": coarse_routing["routing_rationale"]
                },
                "questions": questions,
                "estimated_completion_seconds": 60
            }
            
        except Exception as e:
            logger.error(f"❌ AMRG run start failed: {e}")
            return {
                "success": False,
                "error_code": "RUN_START_FAILED",
                "message": str(e)
            }
    
    # ==================== PHASE 2: CONTINUE WITH ANSWERS ====================
    
    async def continue_with_answers(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str,
        answers: list
    ) -> Dict[str, Any]:
        """
        Continue AMRG run after receiving answers (Phase 2).
        
        Performs:
        1. Final template routing
        2. Optional web research
        3. PRD generation
        4. Schema validation
        5. Repair if needed
        """
        logger.info(f"🔄 Continuing AMRG run {run_id} with answers")
        
        try:
            # Step 1: Load run state
            run_data = self.db_adapter.get_amrg_run(project_id, tenant_id, run_id)
            
            if not run_data:
                return {
                    "success": False,
                    "error_code": "RUN_NOT_FOUND",
                    "message": f"Run {run_id} not found"
                }
            
            if run_data["status"] != RunStatus.AWAITING_ANSWERS.value:
                return {
                    "success": False,
                    "error_code": "INVALID_STATUS",
                    "message": f"Run status is {run_data['status']}, expected awaiting_answers"
                }
            
            # Step 2: Save answers
            clarifying_answers = []
            for ans in answers:
                clarifying_answers.append({
                    "q_index": ans.get("q_index"),
                    "answer_text": ans.get("answer_text"),
                    "answered_at": datetime.utcnow().isoformat()
                })
            
            self.db_adapter.save_amrg_answers(project_id, tenant_id, run_id, clarifying_answers)
            
            # Update status to running
            self.db_adapter.update_amrg_status(
                project_id, tenant_id, run_id, RunStatus.RUNNING
            )
            
            # Get stored data
            context_pack = run_data["context_pack"]
            coarse_routing = run_data["coarse_routing"]
            clarifying_questions = run_data["clarifying_questions"]
            user_id = run_data["user_id"]
            
            # Step 3: Final routing
            logger.info("Step 3: Performing final template routing...")
            final_routing = await self.router_final.route(
                context_pack=context_pack,
                coarse_routing=coarse_routing,
                clarifying_questions=clarifying_questions,
                clarifying_answers=clarifying_answers,
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id
            )
            
            selected_template = final_routing["selected_template_code"]
            logger.info(f"✅ Step 3: Selected template {selected_template}")
            
            # Step 4: Optional research (skip for now - can add later)
            research_results = None
            research_mode = run_data.get("research_mode", "auto")
            # TODO: Implement research if research_mode != "off"
            
            # Step 5: Generate PRD
            logger.info("Step 5: Generating PRD...")
            prd_json = await self.prd_generator.generate_prd(
                context_pack=context_pack,
                selected_template_code=selected_template,
                clarifying_questions=clarifying_questions,
                clarifying_answers=clarifying_answers,
                research_results=research_results,
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id
            )
            logger.info("✅ Step 5: PRD generated")
            
            # Step 6: Validate PRD
            logger.info("Step 6: Validating PRD...")
            template_code = TemplateCode(selected_template)
            status, errors, warnings = self.schema_validator.validate_prd(
                prd_json, template_code
            )
            
            # Step 7: Repair if needed
            repair_attempts = 0
            if status == ValidationStatus.INVALID and errors:
                logger.info("Step 7: Attempting repair...")
                prd_json, status, errors = await self.repair_agent.repair_prd(
                    prd_json=prd_json,
                    validation_errors=errors,
                    template_code=selected_template,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    project_id=project_id
                )
                repair_attempts = 2 if status == ValidationStatus.REPAIR_FAILED else 1
            
            # Step 8: Create validation report
            validation_report = self.schema_validator.create_validation_report(
                status, errors, warnings, repair_attempts
            )
            
            # Step 9: Save output
            logger.info("Step 9: Saving PRD output...")
            self.db_adapter.save_amrg_output(
                project_id=project_id,
                tenant_id=tenant_id,
                run_id=run_id,
                prd_json=prd_json,
                validation_report=validation_report
            )
            
            # Get template spec for response
            spec = get_template_spec(template_code)
            
            logger.info(f"✅ AMRG run {run_id} completed successfully")
            
            return {
                "success": True,
                "run_id": run_id,
                "project_id": project_id,
                "status": RunStatus.COMPLETED.value,
                "prd_json": prd_json,
                "prd_metadata": {
                    "template_code": selected_template,
                    "template_name": spec.name if spec else selected_template,
                    "template_version": prd_json.get("template_version", "1.0.0"),
                    "schema_version": prd_json.get("schema_version", "1.0.0"),
                    "generated_at": prd_json.get("generated_at"),
                    "research_used": research_results is not None,
                    "research_sources_count": len(research_results.get("sources", [])) if research_results else 0
                },
                "validation_status": validation_report["status"],
                "validation_warnings": validation_report.get("warnings", []),
                "version": 1,
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ AMRG run continuation failed: {e}")
            
            # Update status to failed
            self.db_adapter.update_amrg_status(
                project_id, tenant_id, run_id, RunStatus.FAILED,
                {"error": str(e)}
            )
            
            return {
                "success": False,
                "run_id": run_id,
                "error_code": "GENERATION_FAILED",
                "message": str(e)
            }
    
    # ==================== STATUS CHECK ====================
    
    def get_run_status(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str
    ) -> Dict[str, Any]:
        """Get status of an AMRG run."""
        run_data = self.db_adapter.get_amrg_run(project_id, tenant_id, run_id)
        
        if not run_data:
            return {
                "success": False,
                "error_code": "RUN_NOT_FOUND",
                "message": f"Run {run_id} not found"
            }
        
        return {
            "success": True,
            "run_id": run_id,
            "project_id": project_id,
            "status": run_data.get("status"),
            "created_at": run_data.get("created_at"),
            "updated_at": run_data.get("updated_at"),
            "completed_at": run_data.get("completed_at"),
            "prd_available": run_data.get("status") == RunStatus.COMPLETED.value,
            "error": run_data.get("error")
        }


# Singleton instance
_amrg_workflow: Optional[AMRGWorkflow] = None


def get_amrg_workflow() -> AMRGWorkflow:
    """Get singleton instance of AMRG workflow."""
    global _amrg_workflow
    if _amrg_workflow is None:
        _amrg_workflow = AMRGWorkflow()
    return _amrg_workflow
