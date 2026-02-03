"""
Bootstrap LangGraph Workflow

Orchestrates the complete bootstrap context generation process:
1. Load raw input (idea text + PDF files)
2. Extract text from PDFs
3. Chunk and embed all content
4. Generate clarifying questions
5. [INTERRUPT] Wait for user answers
6. Ingest answers and embed
7. Plan and execute web research
8. Compose enhanced context
9. Finalize and charge credits
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.mvp.bootstrap.models.state_models import BootstrapState, ContextStatus

logger = logging.getLogger(__name__)


class Module3BootstrapWorkflow:
    """
    LangGraph-style workflow for bootstrap context generation.
    
    This workflow can be interrupted after question generation to wait
    for user answers, then resumed to complete research and context composition.
    """
    
    def __init__(self):
        """Initialize workflow with required services."""
        self._init_services()
        logger.info("Module3 Bootstrap Workflow initialized")
    
    def _init_services(self):
        """Initialize all required services."""
        try:
            from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
            self.db_adapter = get_bootstrap_database_adapter()
        except Exception as e:
            logger.error(f"Failed to initialize database adapter: {e}")
            self.db_adapter = None
        
        try:
            from src.mvp.bootstrap.services.pdf_extractor import get_pdf_extractor_service
            self.pdf_extractor = get_pdf_extractor_service()
        except Exception as e:
            logger.warning(f"Failed to initialize PDF extractor: {e}")
            self.pdf_extractor = None
        
        try:
            from src.mvp.bootstrap.services.embedding_service import get_bootstrap_embedding_service
            self.embedding_service = get_bootstrap_embedding_service()
        except Exception as e:
            logger.warning(f"Failed to initialize embedding service: {e}")
            self.embedding_service = None
        
        try:
            from src.mvp.bootstrap.services.question_generator import get_question_generator_service
            self.question_generator = get_question_generator_service()
        except Exception as e:
            logger.warning(f"Failed to initialize question generator: {e}")
            self.question_generator = None
        
        try:
            from src.mvp.bootstrap.services.research_service import get_bootstrap_research_service
            self.research_service = get_bootstrap_research_service()
        except Exception as e:
            logger.warning(f"Failed to initialize research service: {e}")
            self.research_service = None
        
        try:
            from src.mvp.bootstrap.services.context_composer import get_context_composer_service
            self.context_composer = get_context_composer_service()
        except Exception as e:
            logger.warning(f"Failed to initialize context composer: {e}")
            self.context_composer = None
    
    async def start_run(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        idea_text: Optional[str] = None,
        file_keys: Optional[list] = None,
        is_super_admin: bool = False,
        plan_type: str = "individual"
    ) -> Dict[str, Any]:
        """
        Start a new bootstrap workflow run.
        
        This runs until the question generation step, then pauses
        to wait for user answers.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            user_id: User ID
            idea_text: Optional initial idea text
            file_keys: Optional list of uploaded file storage keys
            is_super_admin: Whether user is super admin (bypasses credits)
            plan_type: User's plan type for credit calculation
            
        Returns:
            Current state including generated questions
        """
        logger.info(f"🚀 Starting bootstrap workflow for project {project_id}")
        
        # Initialize state
        state: BootstrapState = {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "idea_text": idea_text,
            "file_keys": file_keys or [],
            "is_super_admin": is_super_admin,
            "plan_type": plan_type,
            "pdf_extracts": [],
            "chunks_embedded": False,
            "chunk_count": 0,
            "clarifying_questions": [],
            "clarifying_answers": [],
            "research_queries": [],
            "research_results": {},
            "enhanced_context": None,
            "status": ContextStatus.EMBEDDING.value,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        try:
            # Node 1: Load and validate raw input
            state = await self._load_raw_input(state)
            if state.get("error"):
                # Update database status to failed before returning
                self.db_adapter.update_context_status(
                    project_id, tenant_id, ContextStatus.FAILED.value, state.get("error")
                )
                logger.error(f"❌ Node 1 failed: {state.get('error')}")
                return state
            
            # Node 2: Extract text from PDFs
            state = await self._pdf_extract(state)
            if state.get("error"):
                self.db_adapter.update_context_status(
                    project_id, tenant_id, ContextStatus.FAILED.value, state.get("error")
                )
                logger.error(f"❌ Node 2 failed: {state.get('error')}")
                return state
            
            # Node 3: Chunk and embed content
            state = await self._chunk_embed(state)
            if state.get("error"):
                self.db_adapter.update_context_status(
                    project_id, tenant_id, ContextStatus.FAILED.value, state.get("error")
                )
                logger.error(f"❌ Node 3 failed: {state.get('error')}")
                return state
            
            # Node 4: Generate clarifying questions
            state = await self._question_gen(state)
            
            # INTERRUPT - workflow pauses here
            # State is saved, questions returned to user
            logger.info(f"⏸️ Workflow paused at questions_pending for project {project_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Workflow error: {e}")
            state["status"] = ContextStatus.FAILED.value
            state["error"] = str(e)
            self.db_adapter.update_context_status(
                project_id, tenant_id, ContextStatus.FAILED.value, str(e)
            )
            return state
    
    async def resume_with_answers(
        self,
        project_id: str,
        tenant_id: str,
        answers: list,
        is_super_admin: bool = False,
        plan_type: str = "individual"
    ) -> Dict[str, Any]:
        """
        Resume workflow after receiving user answers.
        
        Continues from answers_received through to completion.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            answers: List of answer objects [{question_id, answer}]
            is_super_admin: If True, skip credit checks
            plan_type: Plan type for credit lookup
            
        Returns:
            Final state with enhanced_context
        """
        logger.info(f"▶️ Resuming bootstrap workflow for project {project_id}")
        
        try:
            # Get current project state
            project = self.db_adapter.get_bootstrap_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            enhanced_context = project.get("enhanced_context", {})
            metadata = enhanced_context.get("metadata", {})
            
            # Rebuild state from project data
            user_id = project.get("user_id")
            state: BootstrapState = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "idea_text": metadata.get("intake", {}).get("idea_text"),
                "file_keys": metadata.get("intake", {}).get("file_keys", []),
                "is_super_admin": is_super_admin,
                "plan_type": plan_type,
                "pdf_extracts": [],
                "chunks_embedded": True,
                "chunk_count": 0,
                "clarifying_questions": metadata.get("clarifying_questions", []),
                "clarifying_answers": answers,
                "research_queries": [],
                "research_results": {},
                "enhanced_context": None,
                "status": ContextStatus.ANSWERS_RECEIVED.value,
                "error": None,
                "started_at": project.get("created_at"),
                "completed_at": None
            }
            
            # Check credits upfront before expensive operations (skip for super admins)
            if state.get("is_super_admin", False):
                logger.info(f"👑 Super admin - skipping credit check for project {project_id}")
            else:
                has_credits = await self._check_credits_available(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    plan_type=state.get("plan_type", "individual")
                )
                if not has_credits:
                    logger.warning(f"❌ Insufficient credits for project {project_id} - aborting workflow")
                    state["status"] = ContextStatus.PAYMENT_REQUIRED.value
                    state["error"] = "Insufficient credits. Please add credits to continue."
                    self.db_adapter.update_context_status(
                        project_id, tenant_id, ContextStatus.PAYMENT_REQUIRED.value
                    )
                    return state
                logger.info(f"✅ Credit check passed for project {project_id}")
            
            # Node 5: Ingest answers
            state = await self._answers_ingest(state)
            if state.get("error"):
                return state
            
            # Node 6: Plan research queries
            state = await self._research_plan(state)
            if state.get("error"):
                return state
            
            # Node 7: Execute web search
            state = await self._web_search(state)
            if state.get("error"):
                return state
            
            # Node 8: Compose enhanced context
            state = await self._compose_context(state)
            if state.get("error"):
                return state
            
            # Node 9: Finalize and charge credits
            state = await self._finalize_and_charge(state)
            
            logger.info(f"✅ Workflow completed for project {project_id}")
            return state
            
        except Exception as e:
            logger.error(f"❌ Workflow resume error: {e}")
            self.db_adapter.update_context_status(
                project_id, tenant_id, ContextStatus.FAILED.value, str(e)
            )
            return {
                "project_id": project_id,
                "status": ContextStatus.FAILED.value,
                "error": str(e)
            }
    
    # ==================== WORKFLOW NODES ====================
    
    async def _load_raw_input(self, state: BootstrapState) -> BootstrapState:
        """Node 1: Load and validate raw input."""
        logger.info(f"📥 Node 1: Loading raw input")
        
        idea_text = state.get("idea_text", "")
        file_keys = state.get("file_keys", [])
        
        # Validate: at least one input required
        if not idea_text and not file_keys:
            state["error"] = "At least one of idea_text or file uploads is required"
            state["status"] = ContextStatus.FAILED.value
            return state
        
        logger.info(f"   Idea text: {len(idea_text) if idea_text else 0} chars")
        logger.info(f"   Files: {len(file_keys)}")
        
        return state
    
    async def _pdf_extract(self, state: BootstrapState) -> BootstrapState:
        """Node 2: Extract text from PDF files."""
        logger.info(f"📄 Node 2: Extracting PDFs")
        
        file_keys = state.get("file_keys", [])
        
        if not file_keys:
            logger.info("   No files to extract")
            return state
        
        if not self.pdf_extractor:
            logger.warning("   PDF extractor not available, skipping")
            return state
        
        try:
            extracts = await self.pdf_extractor.extract_text_from_files(file_keys)
            state["pdf_extracts"] = extracts
            
            successful = sum(1 for e in extracts if e.get("success"))
            logger.info(f"   Extracted {successful}/{len(file_keys)} files")
            
        except Exception as e:
            logger.error(f"   PDF extraction error: {e}")
            # Don't fail workflow, continue with idea_text
        
        return state
    
    async def _chunk_embed(self, state: BootstrapState) -> BootstrapState:
        """Node 3: Chunk and embed all content."""
        logger.info(f"🧩 Node 3: Chunking and embedding")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        
        if not self.embedding_service:
            logger.warning("   Embedding service not available")
            state["chunks_embedded"] = False
            return state
        
        try:
            result = await self.embedding_service.process_bootstrap_input(
                project_id=project_id,
                tenant_id=tenant_id,
                idea_text=state.get("idea_text"),
                pdf_extracts=state.get("pdf_extracts"),
                user_id=state.get("user_id")
            )
            
            state["chunks_embedded"] = result.get("success", False)
            state["chunk_count"] = result.get("chunk_count", 0)
            
            logger.info(f"   Embedded {state['chunk_count']} chunks")
            
        except Exception as e:
            logger.error(f"   Embedding error: {e}")
            state["chunks_embedded"] = False
        
        return state
    
    async def _question_gen(self, state: BootstrapState) -> BootstrapState:
        """Node 4: Generate clarifying questions using LLM."""
        logger.info(f"❓ Node 4: Generating questions with LLM")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        
        # Build intake content from idea_text + PDF extracts for LLM analysis
        intake_parts = []
        if state.get("idea_text"):
            intake_parts.append(f"=== USER'S IDEA DESCRIPTION ===\n{state['idea_text']}")
        
        pdf_extracts = state.get("pdf_extracts", [])
        for extract in pdf_extracts:
            if extract.get("success") and extract.get("text"):
                filename = extract.get("filename", "uploaded file")
                intake_parts.append(f"=== CONTENT FROM {filename} ===\n{extract['text'][:3000]}")
        
        intake_content = "\n\n".join(intake_parts) if intake_parts else ""
        
        if not self.question_generator:
            logger.warning("   Question generator not available, using fallback")
            from src.mvp.bootstrap.services.question_generator import FALLBACK_QUESTIONS
            state["clarifying_questions"] = FALLBACK_QUESTIONS[:6]
        else:
            try:
                # Pass intake content for LLM-based dynamic question generation
                questions = await self.question_generator.generate_questions(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    intake_content=intake_content,
                    max_questions=6
                )
                state["clarifying_questions"] = questions
                logger.info(f"   Generated {len(questions)} contextual questions via LLM")
            except Exception as e:
                logger.error(f"   Question generation error: {e}")
                state["error"] = str(e)
                return state
        
        # Save questions to database
        self.db_adapter.save_clarifying_questions(
            project_id, tenant_id, state["clarifying_questions"]
        )
        
        state["status"] = ContextStatus.QUESTIONS_PENDING.value
        logger.info(f"   Generated {len(state['clarifying_questions'])} questions")
        
        return state
    
    async def _answers_ingest(self, state: BootstrapState) -> BootstrapState:
        """Node 5: Ingest and embed user answers."""
        logger.info(f"📝 Node 5: Ingesting answers")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        user_id = state.get("user_id")  # Get user_id for created_by field
        answers = state.get("clarifying_answers", [])
        
        # Save answers to database
        self.db_adapter.save_clarifying_answers(project_id, tenant_id, answers)
        
        # Embed answers
        if self.embedding_service and answers:
            try:
                result = await self.embedding_service.process_bootstrap_input(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    qa_answers=answers,
                    user_id=user_id  # Pass user_id for created_by field
                )
                logger.info(f"   Embedded {result.get('chunk_count', 0)} answer chunks")
            except Exception as e:
                logger.warning(f"   Answer embedding error: {e}")
        
        state["status"] = ContextStatus.RESEARCHING.value
        self.db_adapter.update_context_status(
            project_id, tenant_id, ContextStatus.RESEARCHING.value
        )
        
        return state
    
    async def _research_plan(self, state: BootstrapState) -> BootstrapState:
        """Node 6: Plan research queries."""
        logger.info(f"📋 Node 6: Planning research")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        
        if not self.research_service:
            logger.warning("   Research service not available")
            return state
        
        try:
            # Build context summary from answers
            answers = state.get("clarifying_answers", [])
            questions = state.get("clarifying_questions", [])
            
            context_summary = {}
            for answer in answers:
                q_id = answer.get("question_id")
                for q in questions:
                    if q.get("id") == q_id:
                        category = q.get("category", "")
                        if category == "target_customer":
                            context_summary["customer_segment"] = answer.get("answer", "")
                        elif category == "market_scope":
                            context_summary["geography"] = answer.get("answer", "")
                        elif category == "problem":
                            context_summary["problem"] = answer.get("answer", "")
                        elif category == "solution":
                            context_summary["solution"] = answer.get("answer", "")
                        break
            
            queries = await self.research_service.generate_research_queries(
                project_id=project_id,
                tenant_id=tenant_id,
                context_summary=context_summary
            )
            
            state["research_queries"] = queries
            logger.info(f"   Planned {len(queries)} research queries")
            
        except Exception as e:
            logger.warning(f"   Research planning error: {e}")
        
        return state
    
    async def _web_search(self, state: BootstrapState) -> BootstrapState:
        """Node 7: Execute web research."""
        logger.info(f"🔍 Node 7: Executing web research")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        queries = state.get("research_queries", [])
        
        if not queries:
            logger.info("   No research queries to execute")
            return state
        
        if not self.research_service:
            logger.warning("   Research service not available")
            return state
        
        try:
            results = await self.research_service.execute_research(queries)
            state["research_results"] = results
            
            # Store in database
            self.db_adapter.save_research_results(project_id, tenant_id, results)
            
            # Embed research results
            user_id = state.get("user_id")
            await self.research_service.store_research_results(
                project_id, tenant_id, results, user_id=user_id
            )
            
            logger.info(f"   Research complete: {results.get('source_count', 0)} sources")
            
        except Exception as e:
            logger.warning(f"   Web search error: {e}")
        
        return state
    
    async def _compose_context(self, state: BootstrapState) -> BootstrapState:
        """Node 8: Compose enhanced context."""
        logger.info(f"🎨 Node 8: Composing enhanced context")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        
        if not self.context_composer:
            logger.error("   Context composer not available")
            state["error"] = "Context composer service not available"
            return state
        
        try:
            enhanced_context = await self.context_composer.compose_enhanced_context(
                project_id=project_id,
                tenant_id=tenant_id
            )
            
            state["enhanced_context"] = enhanced_context
            logger.info(f"   Enhanced context composed successfully")
            
        except Exception as e:
            logger.error(f"   Context composition error: {e}")
            state["error"] = str(e)
        
        return state
    
    async def _finalize_and_charge(self, state: BootstrapState) -> BootstrapState:
        """
        Node 9: Finalize context and charge credits.
        
        Atomic operation:
        1. Save enhanced_context.draft
        2. Deduct credits (idempotent via project_id)
        3. Set context_status='context_ready'
        
        On failure: set context_status='payment_required'
        """
        logger.info(f"💳 Node 9: Finalizing and charging credits")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        user_id = state["user_id"]
        is_super_admin = state.get("is_super_admin", False)
        plan_type = state.get("plan_type", "individual")
        enhanced_context = state.get("enhanced_context")
        
        if not enhanced_context:
            state["error"] = "No enhanced context to finalize"
            state["status"] = ContextStatus.FAILED.value
            self.db_adapter.update_context_status(
                project_id, tenant_id, ContextStatus.FAILED.value, state["error"]
            )
            return state
        
        try:
            # Step 1: Save enhanced context
            success = self.db_adapter.save_enhanced_context(
                project_id=project_id,
                tenant_id=tenant_id,
                enhanced_context=enhanced_context,
                version=1
            )
            
            if not success:
                raise Exception("Failed to save enhanced context")
            
            # Step 2: Deduct credits (skip for super admins)
            if not is_super_admin:
                try:
                    from src.mint.api.credit.service import CreditService
                    from src.mint.api.features.dependencies import resolve_feature_id
                    
                    credit_service = CreditService()
                    feature_id = await resolve_feature_id("module3_bootstrap_context")
                    
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=project_id,  # Idempotency key
                        reason="Module 3 bootstrap context generation",
                        project_id=project_id,
                        metadata={
                            "context_version": 1,
                            "source": "bootstrap_workflow"
                        }
                    )
                    logger.info(f"   Credits deducted for project {project_id}")
                    
                except Exception as credit_error:
                    from src.mint.api.credit.service import InsufficientCreditsError
                    if isinstance(credit_error, InsufficientCreditsError):
                        # Insufficient credits - set payment_required
                        state["status"] = ContextStatus.PAYMENT_REQUIRED.value
                        state["error"] = "Insufficient credits"
                        self.db_adapter.update_context_status(
                            project_id, tenant_id, ContextStatus.PAYMENT_REQUIRED.value
                        )
                        logger.warning(f"   Insufficient credits for project {project_id}")
                        return state
                    else:
                        # Other credit error - log but continue
                        logger.error(f"   Credit deduction error: {credit_error}")
            else:
                logger.info(f"   Super admin - skipping credit deduction")
            
            # Step 3: Set context_status='context_ready'
            self.db_adapter.update_context_status(
                project_id, tenant_id, ContextStatus.CONTEXT_READY.value
            )
            
            state["status"] = ContextStatus.CONTEXT_READY.value
            state["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"✅ Finalization complete for project {project_id}")
            return state
            
        except Exception as e:
            logger.error(f"❌ Finalization error: {e}")
            state["status"] = ContextStatus.FAILED.value
            state["error"] = str(e)
            self.db_adapter.update_context_status(
                project_id, tenant_id, ContextStatus.FAILED.value, str(e)
            )
            return state
    
    async def _check_credits_available(
        self,
        tenant_id: str,
        user_id: str,
        plan_type: str = "individual"
    ) -> bool:
        """
        Check if tenant has sufficient credits for bootstrap context generation.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            plan_type: Plan type for cost lookup
            
        Returns:
            True if credits available, False otherwise
        """
        try:
            from src.mint.api.credit.service import CreditService
            from src.mint.api.features.dependencies import resolve_feature_id
            
            credit_service = CreditService()
            feature_id = await resolve_feature_id("module3_bootstrap_context")
            
            # Get feature cost
            cost = credit_service.get_feature_cost(feature_id, plan_type)
            
            # Get available credits
            available = credit_service.get_tenant_credits(tenant_id)
            
            logger.info(f"💳 Credit check: {available} available, {cost} required")
            
            return available >= cost
            
        except Exception as e:
            logger.error(f"Credit check error: {e}")
            # On error, allow workflow to continue (will fail at charge step if truly no credits)
            return True


def get_bootstrap_workflow() -> Module3BootstrapWorkflow:
    """Factory function for Module3BootstrapWorkflow."""
    return Module3BootstrapWorkflow()
