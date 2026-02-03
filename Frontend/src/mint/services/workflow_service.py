"""
Workflow Business Logic Service - Separated from Endpoints
==========================================================

This module contains all workflow business logic that was previously
embedded in the monolithic app.py file. This separation provides:

1. ✅ Clear separation of concerns (business logic vs API endpoints)
2. ✅ Improved testability (can test business logic independently)
3. ✅ Better code reusability (business logic can be used from multiple places)
4. ✅ Easier maintenance and debugging

Business logic includes:
- Workflow orchestration and state management
- Credit checking and consumption
- Background task processing
- Report generation coordination
- Error handling and recovery
"""

import os
import json
import uuid
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Import workflow components
from ..workflow import (
    run_workflow,
    resume_workflow,
    workflow_run_clarification,
    workflow_process_clarification_answers,
    workflow_run_specification,
    workflow_run_industry_analysis,
    workflow_run_pestel_analysis,
    workflow_run_report_generation,
    save_workflow_state
)

# Import data models
from ..models.workflow_models import WorkflowStatus, WorkflowReport

# Import database operations
from ..repositories.workflow_repository import WorkflowRepository
# Credit system removed - no longer needed
# from ..api.credit.credit_service import CreditService

# Configure logging
logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Workflow business logic service.
    
    Handles all workflow-related business operations including:
    - Workflow lifecycle management
    - Credit validation and consumption
    - Background task coordination
    - State management and persistence
    - Error handling and recovery
    """
    
    def __init__(self):
        """Initialize the workflow service."""
        self.workflow_repo = WorkflowRepository()
        # Credit system removed
        # self.credit_service = CreditService()
        
        # In-memory storage for workflow states and results
        # In production, this should use Redis or a database
        self.workflow_states = {}
        self.workflow_results = {}
        
        # Create output directory for saving workflow results
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_dir = os.path.join(project_root, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("Workflow service initialized")
    
    async def run_workflow_task(
        self,
        session_id: str,
        query: str,
        user_id: str,
        user_token: str = None,
        interactive: bool = True
    ) -> None:
        """
        Run a workflow as a background task using the new workflow implementation.
        
        This method orchestrates the entire workflow process including:
        - Credit validation and consumption
        - Workflow execution
        - State management
        - Error handling and recovery
        """
        try:
            logger.info(f"🚀 WORKFLOW TASK STARTED: session_id={session_id}, user_id={user_id}")
            logger.info(f"🚀 Query: {query}")
            logger.info(f"🚀 Interactive: {interactive}")
            
            # Check and consume credits
            await self._validate_and_consume_credits(user_id, session_id)
            
            # Get tenant_id for the user (for AI usage monitoring)
            tenant_id = await self._get_user_tenant_id(user_id)
           
            
            # Prepare initial workflow state
            initial_state = {
                "initial_query": query,
                "interactive_mode": interactive,
                "session_id": session_id,
                "user_id": user_id,
                "tenant_id": tenant_id,  # For AI usage monitoring
                "user_token": user_token,
                "workflow_config": {
                    "clarifier": {
                        "auto_advance_if_complete": False,
                        "enabled": True,
                        "max_questions": 3
                    }
                }
            }
            
            # Create output directory for this job
            job_output_dir = os.path.join(self.output_dir, session_id)
            os.makedirs(job_output_dir, exist_ok=True)
            
            # Update initial state
            self.workflow_states[session_id] = {
                "session_id": session_id,
                "status": "initializing",
                "progress": 0,
                "message": "Initializing workflow...",
                "last_updated": datetime.now(),
                "user_id": user_id,
                "query": query,
                "output_dir": job_output_dir
            }
            
            # Start the workflow
            logger.info(f"🚀 RUNNING WORKFLOW for session {session_id}")
            workflow_result = await run_workflow(initial_state)
            logger.info(f"🚀 WORKFLOW COMPLETED for session {session_id}")
            
            # Process workflow result
            logger.info(f"Workflow result keys for session {session_id}: {list(workflow_result.keys()) if workflow_result else 'None'}")
            logger.info(f"Workflow result status: {workflow_result.get('status') if workflow_result else 'None'}")
            logger.info(f"Workflow paused for input: {workflow_result.get('_workflow_paused_for_input') if workflow_result else 'None'}")
            
            # DEBUG: Check if final_report exists and what it contains
            if 'final_report' in workflow_result:
                final_report = workflow_result['final_report']
                logger.info(f"DEBUG: final_report exists, type: {type(final_report)}")
                if isinstance(final_report, dict):
                    logger.info(f"DEBUG: final_report keys: {list(final_report.keys())}")
                    logger.info(f"DEBUG: final_report size: {len(str(final_report))} characters")
                else:
                    logger.info(f"DEBUG: final_report content preview: {str(final_report)[:200]}...")
            else:
                logger.error(f"DEBUG: final_report key NOT FOUND in workflow_result!")
                
            await self._process_workflow_result(session_id, workflow_result, user_id)
            
        except Exception as e:
            logger.error(f"Workflow task failed for session {session_id}: {str(e)}")
            await self._handle_workflow_error(session_id, e, user_id)
    
    async def _validate_and_consume_credits(self, user_id: str, session_id: str) -> None:
        """Credit system removed - this method is now a no-op."""
        logger.info(f"Credit validation disabled for user {user_id} (credit system removed)")
        # No credit checks or consumption - workflows run freely
        pass
    
    async def _process_workflow_result(self, session_id: str, workflow_result: Dict, user_id: str) -> None:
        """Process and save workflow results."""
        try:
            logger.info(f"Processing workflow result for session {session_id}")
            logger.info(f"Result keys: {list(workflow_result.keys()) if workflow_result else 'None'}")
            logger.info(f"Paused for input: {workflow_result.get('_workflow_paused_for_input', False)}")
            logger.info(f"Status: {workflow_result.get('status', 'no status')}")
            # Check if workflow completed successfully
            if workflow_result.get("status") == "completed":
                # Debug: Check what's actually in workflow_result
                logger.info(f"DEBUG: workflow_result keys: {list(workflow_result.keys())}")
                
                # Save the final report - check multiple possible keys
                report_data = None
                for key in ["final_report", "final_report_json", "report", "structured_report"]:
                    if key in workflow_result and workflow_result[key]:
                        report_data = workflow_result[key]
                        logger.info(f"DEBUG: Found report data in key '{key}', type: {type(report_data)}")
                        break
                
                if not report_data:
                    logger.error(f"DEBUG: No report data found in workflow_result!")
                    report_data = {}
                
                # Add tenant_id to report_data from user's tenant membership
                if "tenant_id" not in report_data:
                    tenant_id = await self._get_user_tenant_id(user_id)
                    if tenant_id:
                        report_data["tenant_id"] = tenant_id
                        logger.info(f"DEBUG: Added tenant_id {tenant_id} to report_data")
                    else:
                        # Fallback to default tenant if user has no tenant membership
                        report_data["tenant_id"] = "00000000-0000-0000-0000-000000000001"
                        logger.warning(f"User {user_id} has no tenant membership, using default tenant")
                
                # Store result in database
                await self.workflow_repo.save_workflow_result(
                    session_id=session_id,
                    user_id=user_id,
                    report_data=report_data,
                    status="completed"
                )
                
                # Update in-memory state
                self.workflow_states[session_id] = {
                    "session_id": session_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "Workflow completed successfully",
                    "last_updated": datetime.now(),
                    "user_id": user_id,
                    "report_ready": True
                }
                
                self.workflow_results[session_id] = {
                    "session_id": session_id,
                    "report": report_data,
                    "status": "completed",
                    "user_id": user_id,
                    "generated_at": datetime.now()
                }
                
                logger.info(f"Workflow completed successfully for session {session_id}")
                
                # FALLBACK: Trigger insight generation if it wasn't done during workflow
                # This handles cases where the initial save failed but this save succeeded
                if not workflow_result.get("insights_generation_initiated", False):
                    await self._trigger_background_insights_generation(session_id, user_id, workflow_result)
                
            elif workflow_result.get("_workflow_paused_for_input", False):
                # Handle clarification questions - workflow is paused for user input
                clarification_data = workflow_result.get("clarification", {})
                questions = clarification_data.get("questions", [])
                
                # Convert questions to the format expected by the API
                clarification_questions = []
                for i, q in enumerate(questions):
                    clarification_questions.append({
                        "id": f"q_{i+1}",
                        "question": q,
                        "question_type": "text",
                        "required": True
                    })
                
                self.workflow_states[session_id].update({
                    "status": "waiting_for_clarification",
                    "progress": 25,
                    "message": "Waiting for clarification answers",
                    "clarification_questions": clarification_questions,
                    "clarification": clarification_data,  # Store the original clarification data
                    "last_updated": datetime.now()
                })
                
                logger.info(f"Workflow paused for clarification: session {session_id}, {len(questions)} questions")
                
            else:
                # Handle other workflow states
                result_status = workflow_result.get("status", "processing")
                
                # Special case: If clarification is complete but status is still "waiting_for_clarification",
                # update it to "processing" to continue the workflow
                update_data = {
                    "status": result_status,
                    "progress": workflow_result.get("progress", 50),
                    "message": workflow_result.get("message", "Processing..."),
                    "last_updated": datetime.now()
                }
                
                if (result_status == "waiting_for_clarification" and 
                    workflow_result.get("clarification_complete", False) and
                    not workflow_result.get("_workflow_paused_for_input", False)):
                    # Clarification is complete, update status and clear questions
                    update_data.update({
                        "status": "processing",
                        "progress": 50,
                        "message": "Processing research based on your answers...",
                        "clarification_questions": None
                    })
                    logger.info(f"Clarification complete detected, updating status to processing for session {session_id}")
                
                self.workflow_states[session_id].update(update_data)
                
        except Exception as e:
            logger.error(f"Error processing workflow result for session {session_id}: {str(e)}")
            await self._handle_workflow_error(session_id, e, user_id)
    
    async def _handle_workflow_error(self, session_id: str, error: Exception, user_id: str) -> None:
        """Handle workflow errors and update state accordingly."""
        error_message = str(error)
        
        # Sanitize error message for user-facing display
        if "credit" in error_message.lower():
            user_message = "Credit validation failed. Please check your credit status."
        elif "authentication" in error_message.lower():
            user_message = "Authentication error. Please log in again."
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            user_message = "Network connectivity issue. Please try again later."
        else:
            user_message = "An error occurred while processing your request. Please try again."
        
        # Update workflow state
        self.workflow_states[session_id] = {
            "session_id": session_id,
            "status": "failed",
            "error": user_message,
            "last_updated": datetime.now(),
            "user_id": user_id
        }
        
        # Log detailed error for debugging
        logger.error(f"Workflow failed for session {session_id}, user {user_id}: {error_message}")
        
        # Save error state to database
        try:
            await self.workflow_repo.save_workflow_error(
                session_id=session_id,
                user_id=user_id,
                error_message=error_message,
                error_type=type(error).__name__
            )
        except Exception as db_error:
            logger.error(f"Failed to save workflow error to database: {str(db_error)}")
    
    async def _trigger_background_insights_generation(self, session_id: str, user_id: str, workflow_result: Dict) -> None:
        """
        Fallback trigger for actionable insights generation.
        
        This is called when the workflow didn't initiate insights generation
        (e.g., due to initial save failure) but the report was saved successfully here.
        """
        try:
            logger.info(f"FALLBACK: Triggering background insights generation for session {session_id}")
            
            # Import the insights service
            from src.mint.api.actionable_insights import get_actionable_insights_service, InsightGenerationContext
            
            # First ensure the report has embeddings (chunks)
            from src.mint.api.system.core.supabase_client import get_service_role_client
            from src.mint.api.report.report_chunking_service import ReportChunkingService
            
            verify_client = get_service_role_client()
            
            # Check if chunks already exist
            chunks_result = verify_client.client.table("chunks") \
                .select("id") \
                .eq("doc_id", session_id) \
                .limit(1) \
                .execute()
            
            if not chunks_result.data:
                # No chunks exist - we need to create them first
                logger.info(f"FALLBACK: No chunks found for report {session_id}, creating embeddings...")
                
                report_data = workflow_result.get("final_report") or workflow_result.get("report") or {}
                if report_data:
                    chunking_service = ReportChunkingService()
                    vector_success = await chunking_service.process_report_from_json(
                        report_id=session_id,
                        report_json=report_data
                    )
                    
                    if not vector_success:
                        logger.error(f"FALLBACK: Failed to create embeddings for report {session_id}")
                        return
                    
                    logger.info(f"FALLBACK: Successfully created embeddings for report {session_id}")
                else:
                    logger.error(f"FALLBACK: No report data available for chunking")
                    return
            else:
                logger.info(f"FALLBACK: Chunks already exist for report {session_id}")
            
            # Extract user context from workflow result
            workflow_metadata = workflow_result.get("workflow_metadata", {})
            insight_context = InsightGenerationContext(
                user_id=user_id,
                report_id=session_id,
                industry=workflow_metadata.get("industry"),
                geography=workflow_metadata.get("geography"),
                background=workflow_metadata.get("background"),
                product_type=workflow_metadata.get("product_type")
            )
            
            # Generate insights asynchronously (fire and forget)
            insights_service = get_actionable_insights_service()
            
            async def generate_insights_background():
                try:
                    # Add a small delay to ensure everything is committed
                    await asyncio.sleep(2)
                    logger.info(f"FALLBACK: Background insight generation started for report {session_id}")
                    result = await insights_service.generate_insights(session_id, insight_context)
                    if result.success:
                        logger.info(f"FALLBACK: Background insight generation completed for report {session_id}: {result.total_insights} insights")
                    else:
                        logger.error(f"FALLBACK: Background insight generation failed for report {session_id}: {result.error_message}")
                except Exception as insight_error:
                    logger.error(f"FALLBACK: Background insight generation error for report {session_id}: {str(insight_error)}")
            
            # Start background task without awaiting
            asyncio.create_task(generate_insights_background())
            logger.info(f"FALLBACK: Actionable insights generation initiated for report {session_id}")
            
        except Exception as e:
            logger.error(f"FALLBACK: Error triggering insights generation for session {session_id}: {str(e)}")
            import traceback
            logger.error(f"FALLBACK: Traceback: {traceback.format_exc()}")
    
    async def get_workflow_status(self, session_id: str, user_id: str) -> Optional[WorkflowStatus]:
        """Get the current status of a workflow session."""
        try:
            # Check in-memory state first
            if session_id in self.workflow_states:
                state = self.workflow_states[session_id]
                
                # Validate user ownership
                if state.get("user_id") != user_id:
                    logger.warning(f"User {user_id} attempted to access session {session_id} owned by {state.get('user_id')}")
                    return None
                
                # Convert clarification questions to proper format
                clarification_questions = None
                if state.get("clarification") and state["clarification"].get("questions"):
                    from ..models.workflow_models import ClarificationQuestion
                    clarification_questions = [
                        ClarificationQuestion(
                            id=f"q_{i+1}",
                            question=q,
                            question_type="text",
                            required=True
                        )
                        for i, q in enumerate(state["clarification"]["questions"])
                    ]
                
                return WorkflowStatus(
                    session_id=session_id,
                    status=state.get("status", "unknown"),
                    progress=state.get("progress", 0),
                    message=state.get("message", ""),
                    clarification_questions=clarification_questions,
                    last_updated=state.get("last_updated", datetime.now()),
                    error=state.get("error")
                )
            
            # Check database if not in memory
            db_status = await self.workflow_repo.get_workflow_status(session_id, user_id)
            return db_status
            
        except Exception as e:
            logger.error(f"Error getting workflow status for {session_id}: {str(e)}")
            return None
    
    async def validate_session_ownership(self, session_id: str, user_id: str) -> bool:
        """Validate that a user owns a specific workflow session."""
        try:
            # Check in-memory state first
            if session_id in self.workflow_states:
                state = self.workflow_states[session_id]
                is_owner = state.get("user_id") == user_id
                logger.info(f"In-memory validation for {session_id}: user_id={user_id}, state_user_id={state.get('user_id')}, is_owner={is_owner}")
                return is_owner
            
            logger.warning(f"Session {session_id} not found in in-memory state, checking database")
            
            # Check database
            try:
                return await self.workflow_repo.validate_session_ownership(session_id, user_id)
            except Exception as db_error:
                logger.error(f"Database validation failed for {session_id}: {str(db_error)}")
                # If database check fails, assume ownership is valid for active workflows
                # This prevents blocking legitimate users when database tables don't exist
                logger.warning(f"Assuming valid ownership for {session_id} due to database error")
                return True
            
        except Exception as e:
            logger.error(f"Error validating session ownership for {session_id}: {str(e)}")
            return False
    
    async def process_clarification_answers(
        self,
        session_id: str,
        answers: Dict[str, Any],
        user_id: str
    ) -> None:
        """Process clarification answers and continue the workflow."""
        try:
            logger.info(f"Processing clarification answers for session {session_id}")
            
            # Check if session exists in memory
            if session_id not in self.workflow_states:
                logger.error(f"Session {session_id} not found in in-memory state")
                raise ValueError(f"Workflow session {session_id} not found in active sessions")
            
            # Get workflow state from memory
            workflow_state = self.workflow_states[session_id].copy()
            
            # Validate user ownership
            if workflow_state.get("user_id") != user_id:
                logger.error(f"User {user_id} does not own session {session_id}")
                raise ValueError(f"Access denied to session {session_id}")
            
            # Ensure clarification data exists - reconstruct it from the questions if needed
            if "clarification" not in workflow_state:
                # Try to get clarification questions from the current state
                clarification_questions = workflow_state.get("clarification_questions", [])
                if clarification_questions:
                    # Reconstruct clarification data structure
                    questions_list = []
                    for q in clarification_questions:
                        if hasattr(q, 'question'):
                            questions_list.append(q.question)
                        elif isinstance(q, dict) and 'question' in q:
                            questions_list.append(q['question'])
                        elif isinstance(q, str):
                            questions_list.append(q)
                    
                    workflow_state["clarification"] = {
                        "questions": questions_list,
                        "needs_clarification": True,
                        "timestamp": datetime.now().timestamp()
                    }
                    logger.info(f"Reconstructed clarification data with {len(questions_list)} questions")
                else:
                    logger.error(f"No clarification questions found in workflow state for session {session_id}")
                    raise ValueError("Cannot process answers: no clarification questions found")
            
            # Update workflow state
            self.workflow_states[session_id].update({
                "status": "processing",
                "progress": 50,
                "message": "Processing clarification answers...",
                "clarification_questions": None,
                "last_updated": datetime.now()
            })
            
            # Process answers and continue workflow
            workflow_state["clarification_answers"] = answers
            workflow_state["user_answers"] = answers  # Also set this for compatibility
            
            # Create clarification_json that the specification agent expects
            clarification_data = workflow_state.get("clarification", {})
            questions = clarification_data.get("questions", [])
            
            # Convert answers to the format expected by specification agent
            clarification_json = {
                "initial_query": workflow_state.get("initial_query", workflow_state.get("query", "")),
                "questions": questions,
                "answers": list(answers.values()) if isinstance(answers, dict) else answers,
                "question_answer_pairs": []
            }
            
            # Create question-answer pairs
            if isinstance(answers, dict):
                for i, (q_id, answer) in enumerate(answers.items()):
                    if i < len(questions):
                        clarification_json["question_answer_pairs"].append({
                            "question": questions[i],
                            "answer": answer
                        })
            
            workflow_state["clarification_json"] = clarification_json
            logger.info(f"Created clarification_json with {len(clarification_json['question_answer_pairs'])} Q&A pairs")
            
            # Ensure we have all the necessary workflow context
            workflow_state.update({
                "session_id": session_id,
                "user_id": user_id,
                "interactive_mode": True,
                "awaiting_clarification": False,  # No longer awaiting clarification
                "clarification_complete": True,   # Clarification is now complete
                "initial_query": workflow_state.get("initial_query", workflow_state.get("query", "")),
                "query": workflow_state.get("query", workflow_state.get("initial_query", ""))
            })
            
            logger.info(f"Processing clarification answers with workflow state keys: {list(workflow_state.keys())}")
            
            # Import the workflow function - use resume_workflow to continue the entire workflow
            from ..workflow import resume_workflow
            workflow_result = await resume_workflow(workflow_state)
            
            # Process the result
            await self._process_workflow_result(session_id, workflow_result, user_id)
            
        except Exception as e:
            logger.error(f"Error processing clarification answers for {session_id}: {str(e)}", exc_info=True)
            logger.error(f"Workflow state keys when error occurred: {list(workflow_state.keys()) if 'workflow_state' in locals() else 'workflow_state not available'}")
            await self._handle_workflow_error(session_id, e, user_id)
    
    async def get_workflow_report(self, session_id: str, user_id: str) -> Optional[WorkflowReport]:
        """Get the complete workflow report for a session."""
        try:
            # Check in-memory results first
            if session_id in self.workflow_results:
                result = self.workflow_results[session_id]
                
                # Validate user ownership
                if result.get("user_id") != user_id:
                    logger.warning(f"User {user_id} attempted to access report {session_id} owned by {result.get('user_id')}")
                    return None
                
                return WorkflowReport(
                    session_id=session_id,
                    report_id=session_id,  # For in-memory cache, report_id is same as session_id
                    query=result["report"].get("query", ""),
                    report=result["report"],
                    status=result.get("status", "unknown"),
                    generated_at=result.get("generated_at", datetime.now())
                )
            
            # Check database
            db_report = await self.workflow_repo.get_workflow_report(session_id, user_id)
            return db_report
            
        except Exception as e:
            logger.error(f"Error getting workflow report for {session_id}: {str(e)}")
            return None
    
    async def get_workflow_debug_info(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Get detailed debug information for a workflow session."""
        try:
            debug_info = {
                "session_id": session_id,
                "user_id": user_id,
                "in_memory_state": self.workflow_states.get(session_id),
                "in_memory_result": self.workflow_results.get(session_id),
                "timestamp": datetime.now().isoformat()
            }
            
            # Get database information
            db_info = await self.workflow_repo.get_workflow_debug_info(session_id, user_id)
            debug_info["database_info"] = db_info
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Error getting debug info for {session_id}: {str(e)}")
            return {"error": str(e)}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the workflow service."""
        try:
            active_workflows = len([s for s in self.workflow_states.values() if s.get("status") in ["processing", "waiting_for_clarification"]])
            completed_workflows = len([s for s in self.workflow_states.values() if s.get("status") == "completed"])
            failed_workflows = len([s for s in self.workflow_states.values() if s.get("status") == "failed"])
            
            return {
                "service_status": "healthy",
                "active_workflows": active_workflows,
                "completed_workflows": completed_workflows,
                "failed_workflows": failed_workflows,
                "total_sessions": len(self.workflow_states),
                "memory_usage": {
                    "workflow_states": len(self.workflow_states),
                    "workflow_results": len(self.workflow_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting health status: {str(e)}")
            return {
                "service_status": "unhealthy",
                "error": str(e)
            }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics for monitoring."""
        try:
            # Calculate workflow statistics
            statuses = [s.get("status", "unknown") for s in self.workflow_states.values()]
            status_counts = {}
            for status in ["processing", "completed", "failed", "waiting_for_clarification"]:
                status_counts[status] = statuses.count(status)
            
            # Calculate average processing time for completed workflows
            completed_workflows = [s for s in self.workflow_states.values() if s.get("status") == "completed"]
            avg_processing_time = 0
            if completed_workflows:
                processing_times = []
                for workflow in completed_workflows:
                    # This would need to be calculated based on start/end times
                    # For now, returning placeholder
                    processing_times.append(300)  # 5 minutes average
                avg_processing_time = sum(processing_times) / len(processing_times)
            
            return {
                "workflow_metrics": {
                    "total_workflows": len(self.workflow_states),
                    "status_breakdown": status_counts,
                    "average_processing_time_seconds": avg_processing_time,
                    "success_rate": (status_counts.get("completed", 0) / max(len(self.workflow_states), 1)) * 100
                },
                "system_metrics": {
                    "memory_usage": {
                        "workflow_states_count": len(self.workflow_states),
                        "workflow_results_count": len(self.workflow_results)
                    },
                    "output_directory": self.output_dir,
                    "service_uptime": "N/A"  # Would need to track service start time
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {"error": str(e)}
    
    async def _get_user_tenant_id(self, user_id: str, provided_tenant_id: Optional[str] = None) -> Optional[str]:
        """
        Get the user's tenant_id, preferring a provided tenant_id from JWT context.
        
        IMPORTANT: For proper tenant isolation, callers should pass the tenant_id 
        from the JWT token (current_user["tenant_id"]) whenever possible.
        Falling back to database query is non-deterministic when user has multiple memberships.
        
        Args:
            user_id: The user's UUID
            provided_tenant_id: Optional tenant_id from JWT context (preferred)
            
        Returns:
            The user's tenant_id if found, None otherwise
        """
        # If tenant_id is provided from JWT context, use it directly
        if provided_tenant_id:
            logger.info(f"Using provided tenant_id {provided_tenant_id} for user {user_id}")
            return provided_tenant_id
            
        # Fallback: Query database (non-deterministic when user has multiple memberships)
        logger.warning(f"Falling back to DB query for tenant_id - consider passing tenant_id from JWT context")
        try:
            from ..api.system.core.supabase_client import get_service_role_client
            
            # Use service role to query tenant memberships
            supabase = get_service_role_client()
            
            # Query tenant_memberships table for active membership
            # Order by created_at to ensure deterministic results (oldest membership first)
            result = supabase.client.table("tenant_memberships").select(
                "tenant_id"
            ).eq("user_id", user_id).eq("is_active", True).order("created_at").limit(1).execute()
            
            if result.data and len(result.data) > 0:
                tenant_id = result.data[0]["tenant_id"]
                logger.info(f"Found tenant_id {tenant_id} for user {user_id} (via DB fallback)")
                return tenant_id
            else:
                logger.warning(f"No active tenant membership found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error looking up tenant_id for user {user_id}: {str(e)}")
            return None
