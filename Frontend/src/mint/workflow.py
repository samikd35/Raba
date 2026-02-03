#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MINT Multi-Agent Workflow Orchestrator

This module orchestrates the complete MINT multi-agent workflow including:
- Clarification of user queries
- Specification of research tasks
- Industry analysis
- PESTEL analysis
- Recommendation generation
- Final report generation

The workflow can be run end-to-end or paused for user input during clarification.
Features include robust error handling, state validation, and extensibility hooks.
"""

import os
import sys
import json
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# Add the project root to the Python path for imports to work
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import metrics tracking if available
try:
    from prometheus_client import Counter, Histogram
    METRICS_ENABLED = True
    
    # Initialize Prometheus metrics
    RUNS_COUNTER = Counter("mint_workflow_runs_total", "Total number of workflow runs", ["status"])
    STEP_DURATION = Histogram("mint_workflow_step_seconds", "Duration of workflow steps", ["step"])
    FAILURES_COUNTER = Counter("mint_workflow_failures_total", "Total number of workflow failures", ["step"])
except ImportError:
    logger.warning("Prometheus client not available, metrics will be disabled")
    METRICS_ENABLED = False

# Import traceable decorator for tracing function calls
# TEMPORARILY DISABLED: LangSmith causes memory issues with large research data (314MB+)
try:
    # import langsmith
    # from langsmith.run_helpers import traceable
    # LANGSMITH_ENABLED = True
    # logger.info("LangSmith tracing enabled")
    raise ImportError("LangSmith temporarily disabled")
except ImportError:
    # Define a simple traceable decorator if LangSmith is not available
    def traceable(name=None):
        """Simple decorator for function tracing without LangSmith."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                logger.info(f"Starting {name or func.__name__}")
                start_time = datetime.now()
                result = await func(*args, **kwargs)
                end_time = datetime.now()
                logger.info(f"Completed {name or func.__name__} in {end_time - start_time}")
                return result
            return wrapper if asyncio.iscoroutinefunction(func) else func
        return decorator
    LANGSMITH_ENABLED = False
    logger.warning("LangSmith not available, using local tracing instead")

# Import MINT components
from .agents.clarifier import run_clarification
from .agents.specifier import run_specification
from .agents.industry_agent import run_industry_analysis
from .agents.pestel_agent import run_pestel_analysis
from .agents.report_generator import ReportGenerator, run_report_generator

# Constants
DEFAULT_OUTPUT_DIR = os.path.join(project_root, "output")

# Create output directory if it doesn't exist
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)


# Utility functions for workflow management
class WorkflowError(Exception):
    """Base exception for workflow errors."""
    pass


class ValidationError(WorkflowError):
    """Raised when validation fails for workflow input or output."""
    pass


class AgentError(WorkflowError):
    """Raised when an agent fails to complete its task."""
    pass


# Extensibility hooks for workflow customization
class WorkflowHooks:
    """
    Extension points to customize workflow behavior without modifying core logic.
    
    These hooks can be used to add custom behavior at various points in the workflow,
    such as pre/post processing for each agent, custom validation, or special logging.
    """
    
    @staticmethod
    def pre_clarification(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the clarification agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_clarification(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the clarification agent runs.
        
        Args:
            state: The workflow state with clarification results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_specification(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the specification agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_specification(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the specification agent runs.
        
        Args:
            state: The workflow state with specification results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_industry_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the industry analysis agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_industry_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the industry analysis agent runs.
        
        Args:
            state: The workflow state with industry analysis results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_pestel_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the PESTEL analysis agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_pestel_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the PESTEL analysis agent runs.
        
        Args:
            state: The workflow state with PESTEL analysis results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_recommendations(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the recommender agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_recommendations(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the recommender agent runs.
        
        Args:
            state: The workflow state with recommendation results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_report_generation(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the report generator runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_report_generation(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the report generator runs.
        
        Args:
            state: The workflow state with final report results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def on_workflow_error(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Hook executed when an error occurs in the workflow.
        
        Args:
            state: The current workflow state
            error: The exception that was raised
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def custom_validation(state: Dict[str, Any], step_name: str) -> Optional[str]:
        """
        Custom validation hook for workflow state at a specific step.
        
        Args:
            state: The workflow state to validate
            step_name: The name of the current step
            
        Returns:
            None if valid, or error message string if invalid
        """
        return None


# Default hooks implementation for use in workflow
hooks = WorkflowHooks()


def register_workflow_hooks(custom_hooks: WorkflowHooks) -> None:
    """
    Register custom workflow hooks for extensibility.
    
    Args:
        custom_hooks: Custom implementation of WorkflowHooks
    """
    global hooks
    hooks = custom_hooks
    logger.info("Custom workflow hooks registered")




def validate_workflow_ids(state: Dict[str, Any]) -> bool:
    """Validate all IDs in the workflow state for consistency.
    
    Args:
        state: The workflow state dictionary
        
    Returns:
        bool: True if all IDs are valid and consistent
    """
    import uuid
    
    # Import ID logging service
    try:
        from src.mint.api.id_logging_service import log_id_validation_result, log_report_generation_pipeline
    except ImportError:
        # Fallback if import fails
        def log_id_validation_result(*args, **kwargs):
            pass
        def log_report_generation_pipeline(*args, **kwargs):
            pass
    
    try:
        all_valid = True
        
        # Validate session_id
        session_id = state.get("session_id")
        if session_id:
            try:
                uuid.UUID(session_id)
                logger.info(f"WORKFLOW ID VALIDATION: Session ID {session_id} is valid")
                log_id_validation_result("session_id", session_id, True, "workflow_validation")
            except (ValueError, TypeError):
                logger.error(f"WORKFLOW ID VALIDATION: Invalid session ID format: {session_id}")
                log_id_validation_result("session_id", session_id, False, "workflow_validation")
                all_valid = False
        
        # Validate user_id if present
        user_id = state.get("user_id")
        if user_id:
            try:
                uuid.UUID(user_id)
                logger.info(f"WORKFLOW ID VALIDATION: User ID {user_id} is valid")
                log_id_validation_result("user_id", user_id, True, "workflow_validation")
            except (ValueError, TypeError):
                logger.error(f"WORKFLOW ID VALIDATION: Invalid user ID format: {user_id}")
                log_id_validation_result("user_id", user_id, False, "workflow_validation")
                all_valid = False
        
        # Log the overall validation result
        if all_valid:
            logger.info("WORKFLOW ID VALIDATION: All IDs are valid")
            log_report_generation_pipeline("ID_VALIDATION_SUCCESS", 
                                         session_id or "unknown", 
                                         user_id=user_id,
                                         session_id=session_id)
        else:
            log_report_generation_pipeline("ID_VALIDATION_FAILED", 
                                         session_id or "unknown", 
                                         user_id=user_id,
                                         session_id=session_id)
        
        return all_valid
        
    except Exception as e:
        logger.error(f"WORKFLOW ID VALIDATION: Error validating IDs: {e}")
        return False


def ensure_state_key(state: Dict[str, Any], key: str, default_value: Any = None) -> Any:
    """
    Ensure that a key exists in the state dictionary.
    
    Args:
        state: The workflow state dictionary
        key: The key to check for
        default_value: Default value to set if key is missing
        
    Returns:
        The value of the key (either existing or newly set)
    """
    if key not in state:
        state[key] = default_value
    return state[key]

def validate_file_exists(file_path: str, description: str) -> None:
    """
    Validate that a file exists at the given path.
    
    Args:
        file_path: Path to the file to check (local path or supabase URL)
        description: Description of the file for error messages
    """
    # Supabase URIs are not local files, assume existence
    if file_path.startswith("supabase://"):
        return
    if not os.path.exists(file_path):
        raise ValidationError(f"Missing {description} at path: {file_path}")


def update_metrics(step_name: str, start_time: float, success: bool = True) -> None:
    """
    Update metrics for a workflow step if metrics are enabled.
    
    Args:
        step_name: Name of the workflow step
        start_time: Start time of the step (from time.time())
        success: Whether the step completed successfully
    """
    if not METRICS_ENABLED:
        return
        
    duration = time.time() - start_time
    STEP_DURATION.labels(step=step_name).observe(duration)
    
    if not success:
        FAILURES_COUNTER.labels(step=step_name).inc()


# Clarification Agent Integration
@traceable(name="Clarification")
async def workflow_run_clarification(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the clarification agent to generate questions for the user.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated state with clarification results
    """
    start_time = time.time()
    logger.info("Starting clarification step...")
    
    try:
        # Ensure required keys exist in state
        ensure_state_key(state, "initial_query", "")
        
        if not state["initial_query"]:
            raise ValidationError("Missing initial query in workflow state")
            
        # Set default workflow configuration if not present
        workflow_config = ensure_state_key(state, "workflow_config", {})
        ensure_state_key(workflow_config, "clarifier", {})
        ensure_state_key(workflow_config["clarifier"], "enabled", True)
        ensure_state_key(workflow_config["clarifier"], "auto_advance_if_complete", True)
        
        # Skip clarification if disabled in config
        if not workflow_config["clarifier"].get("enabled", True):
            logger.info("Clarification agent is disabled in configuration, skipping")
            ensure_state_key(state, "clarification", {"needs_clarification": False, "questions": []})
            ensure_state_key(state, "clarification_complete", True)
            return state
            
        # Run clarification agent
        logger.info(f"Running clarification agent for query: {state['initial_query']}")
        clarifier_state = run_clarification(state)
        
        # Validate clarifier output
        if "clarification" not in clarifier_state:
            raise ValidationError("Missing clarification data in result state")
            
        clarification = clarifier_state["clarification"]
        
        if "questions" not in clarification:
            raise ValidationError("Missing questions in clarification data")
            
        # Update the original state with clarification results
        state.update(clarifier_state)
        
        # Log clarification questions if any
        questions = clarification.get("questions", [])
        if questions:
            logger.info(f"Generated {len(questions)} clarification questions:")
            for i, question in enumerate(questions):
                logger.info(f"Question {i+1}: {question}")
                
            # Set flags for interactive mode
            state["awaiting_clarification"] = True
            if state.get("interactive_mode", False):
                state["_workflow_paused_for_input"] = True
                
            # Auto-advance if specified in config and we're not in interactive mode
            if not state.get("interactive_mode") and workflow_config["clarifier"].get("auto_advance_if_complete"):
                logger.info("Auto-advancing past clarification questions in non-interactive mode")
                state["clarification_complete"] = True
                state["awaiting_clarification"] = False
        else:
            # No questions needed, mark as complete
            state["clarification_complete"] = True
            state["awaiting_clarification"] = False
        
        update_metrics("clarification", start_time, True)
        return state
        
    except Exception as e:
        logger.error(f"Clarification step failed: {str(e)}", exc_info=True)
        update_metrics("clarification", start_time, False)
        raise AgentError(f"Clarification agent failed: {str(e)}")


@traceable(name="Process_clarification_answers")
async def workflow_process_clarification_answers(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process user answers to clarification questions.
    
    Args:
        state: The current workflow state with user answers
        
    Returns:
        Updated state with processed answers
    """
    start_time = time.time()
    logger.info("Processing user answers to clarification questions...")
    
    try:
        # Check if we have clarification questions and user answers
        if "clarification" not in state:
            raise ValidationError("Missing clarification data in workflow state")
            
        if "user_answers" not in state or not state["user_answers"]:
            if state.get("interactive_mode", False):
                logger.info("No user answers provided, workflow remains paused")
                return state
            else:
                raise ValidationError("Missing user answers in non-interactive mode")
        
        # Mark clarification as complete since we have user answers
        state["clarification_complete"] = True
        state["awaiting_clarification"] = False
        
        # Remove the pause flag if it exists
        if "_workflow_paused_for_input" in state:
            del state["_workflow_paused_for_input"]
            
        logger.info("User answers processed successfully, clarification complete")
        update_metrics("process_answers", start_time, True)
        return state
        
    except Exception as e:
        logger.error(f"Processing clarification answers failed: {str(e)}", exc_info=True)
        update_metrics("process_answers", start_time, False)
        raise AgentError(f"Processing clarification answers failed: {str(e)}")


def check_clarification_needed(state: Dict[str, Any]) -> str:
    """
    Determine if we need user clarification or can proceed.
    
    Args:
        state: The current workflow state
        
    Returns:
        String with next step: "process_answers" if answers exist,
        "await_answers" if awaiting clarification, or "specification" to proceed
    """
    # Check if we're awaiting clarification
    if state.get("awaiting_clarification", False) and not state.get("clarification_complete", False):
        # Check if we have answers
        if "user_answers" in state and state["user_answers"]:
            return "process_answers"
        else:
            return "await_answers"
    else:
        # No clarification needed or already complete
        return "specification"


# Specification Agent Integration
@traceable(name="Specification")
async def workflow_run_specification(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the specification agent to generate research specifications.
    
    Args:
        state: The current workflow state with clarification data
        
    Returns:
        Updated state with specification results
    """
    start_time = time.time()
    logger.info("Starting specification step...")
    
    try:
        # Ensure required keys exist in state
        ensure_state_key(state, "initial_query", "")
        ensure_state_key(state, "clarification", {})
        ensure_state_key(state, "clarification_complete", False)
        
        if not state["initial_query"]:
            raise ValidationError("Missing initial query in workflow state")
        
        # Check if clarification is complete
        if not state["clarification_complete"]:
            logger.warning("Specification step called but clarification is not complete")
            if state.get("interactive_mode", False):
                logger.info("In interactive mode, pausing for user input")
                state["awaiting_clarification"] = True
                state["_workflow_paused_for_input"] = True
                return state
            else:
                # Auto-advance in non-interactive mode
                logger.info("Auto-advancing in non-interactive mode")
                state["clarification_complete"] = True
        
        # Set default workflow configuration if not present
        workflow_config = ensure_state_key(state, "workflow_config", {})
        ensure_state_key(workflow_config, "specifier", {})
        ensure_state_key(workflow_config["specifier"], "enabled", True)
        
        # Skip specification if disabled in config
        if not workflow_config["specifier"].get("enabled", True):
            logger.info("Specification agent is disabled in configuration, skipping")
            # Create minimal placeholder specifications
            if "industry_specification" not in state:
                state["industry_specification"] = json.dumps({
                    "title": "Industry Analysis",
                    "description": state["initial_query"],
                    "key_questions": [state["initial_query"]],
                    "required_fact_categories": ["Market Size", "Market Growth", "Competition"],
                    "geography_focus": ["Global"],
                    "industry_focus": ["General"],
                    "keywords": []
                })
            if "pestel_specification" not in state:
                state["pestel_specification"] = json.dumps({
                    "title": "PESTEL Analysis",
                    "description": state["initial_query"],
                    "key_questions": [state["initial_query"]],
                    "required_fact_categories": ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"],
                    "geography_focus": ["Global"],
                    "industry_focus": ["General"],
                    "keywords": []
                })
            return state
            
        # Run specification agent
        logger.info("Running specification agent to generate research specifications")
        specification_state = run_specification(state)
        
        # Validate specification output
        if "industry_specification" not in specification_state:
            raise ValidationError("Missing industry_specification in result state")
            
        if "pestel_specification" not in specification_state:
            raise ValidationError("Missing pestel_specification in result state")
            
        # Update the original state with specification results
        state.update(specification_state)
        
        logger.info("Specifications generated successfully")
        update_metrics("specification", start_time, True)
        return state
        
    except Exception as e:
        logger.error(f"Specification step failed: {str(e)}", exc_info=True)
        update_metrics("specification", start_time, False)
        raise AgentError(f"Specification agent failed: {str(e)}")


async def check_specifications_complete(state: Dict[str, Any]) -> bool:
    """
    Check if specification step is complete and valid.
    
    Args:
        state: The current workflow state
        
    Returns:
        Boolean indicating if specifications are complete and valid
    """
    try:
        # Check if we have both industry and PESTEL specifications
        has_industry = "industry_specification" in state and state["industry_specification"]
        has_pestel = "pestel_specification" in state and state["pestel_specification"]
        
        # Validate JSON format
        if has_industry:
            try:
                industry_spec = json.loads(state["industry_specification"]) if isinstance(state["industry_specification"], str) else state["industry_specification"]
                # Validate industry spec has required keys
                required_keys = ["title", "description", "key_questions", "keywords"]
                if not all(key in industry_spec for key in required_keys):
                    logger.warning("Industry specification missing required keys")
                    return False
            except json.JSONDecodeError:
                logger.warning("Industry specification is not valid JSON")
                return False
                
        if has_pestel:
            try:
                pestel_spec = json.loads(state["pestel_specification"]) if isinstance(state["pestel_specification"], str) else state["pestel_specification"]
                # Validate PESTEL spec has required keys
                required_keys = ["title", "description", "key_questions", "keywords"]
                if not all(key in pestel_spec for key in required_keys):
                    logger.warning("PESTEL specification missing required keys")
                    return False
            except json.JSONDecodeError:
                logger.warning("PESTEL specification is not valid JSON")
                return False
                
        return has_industry and has_pestel
        
    except Exception as e:
        logger.error(f"Error checking specifications: {str(e)}")
        return False


# Industry Agent Integration
@traceable(name="Industry_analysis")
async def workflow_run_industry_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the industry analysis agent to generate the industry mini-report.
    
    Args:
        state: The current workflow state with specifications
        
    Returns:
        Updated state with industry analysis results
    """
    start_time = time.time()
    logger.info("Starting industry analysis step...")
    
    try:
        # Check if specifications are complete
        if not await check_specifications_complete(state):
            raise ValidationError("Specifications are incomplete or invalid")
            
        # Set default workflow configuration if not present
        workflow_config = ensure_state_key(state, "workflow_config", {})
        ensure_state_key(workflow_config, "industry_agent", {})
        ensure_state_key(workflow_config["industry_agent"], "enabled", True)
        
        # Skip industry analysis if disabled in config
        if not workflow_config["industry_agent"].get("enabled", True):
            logger.info("Industry analysis agent is disabled in configuration, skipping")
            return state
            
        # Create output directory if it doesn't exist
        industry_output_dir = os.path.join(DEFAULT_OUTPUT_DIR, state["session_id"])
        os.makedirs(industry_output_dir, exist_ok=True)
        
        # Set the output path for industry report
        industry_output_path = os.path.join(industry_output_dir, "industry_report.json")
        
        # Run industry analysis agent
        logger.info("Running industry analysis agent")
        industry_state = await run_industry_analysis(state)
        
        # Check if industry report is in the state
        if "industry_report" not in industry_state:
            raise ValidationError("Missing industry_report in result state")
            
        # Industry report is kept in memory only - no Supabase saving
        # The report will be passed directly to the report generator
        logger.info("Industry report generated and kept in memory for direct merging")

                
        # Update the original state with industry analysis results
        state.update(industry_state)
        
        logger.info(f"Industry analysis completed successfully with in-memory report")
        update_metrics("industry_analysis", start_time, True)
        return state
        
    except Exception as e:
        logger.error(f"Industry analysis step failed: {str(e)}", exc_info=True)
        update_metrics("industry_analysis", start_time, False)
        raise AgentError(f"Industry analysis agent failed: {str(e)}")


def industry_analysis_path(state: Dict[str, Any]) -> str:
    """
    Determine the expected file path for industry analysis output.
    
    Args:
        state: The current workflow state
        
    Returns:
        File path for industry analysis output
    """
    session_id = state.get("session_id", "unknown_job")
    return os.path.join(DEFAULT_OUTPUT_DIR, session_id, "industry_report.json")


# PESTEL Agent Integration
@traceable(name="Pestel_analysis")
async def workflow_run_pestel_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the PESTEL analysis agent to generate the PESTEL mini-report.
    
    Args:
        state: The current workflow state with specifications
        
    Returns:
        Updated state with PESTEL analysis results
    """
    start_time = time.time()
    logger.info("Starting PESTEL analysis step...")
    
    try:
        # Check if specifications are complete
        if not await check_specifications_complete(state):
            raise ValidationError("Specifications are incomplete or invalid")
            
        # Set default workflow configuration if not present
        workflow_config = ensure_state_key(state, "workflow_config", {})
        ensure_state_key(workflow_config, "pestel_agent", {})
        ensure_state_key(workflow_config["pestel_agent"], "enabled", True)
        
        # Skip PESTEL analysis if disabled in config
        if not workflow_config["pestel_agent"].get("enabled", True):
            logger.info("PESTEL analysis agent is disabled in configuration, skipping")
            return state
            
        # Create output directory if it doesn't exist
        pestel_output_dir = os.path.join(DEFAULT_OUTPUT_DIR, state["session_id"])
        os.makedirs(pestel_output_dir, exist_ok=True)
        
        # Set the output path for PESTEL report
        pestel_output_path = os.path.join(pestel_output_dir, "pestel_report.json")
        
        # Run PESTEL analysis agent
        logger.info("Running PESTEL analysis agent")
        pestel_state = await run_pestel_analysis(state)
        
        # Check if PESTEL report is in the state
        if "pestel_report" not in pestel_state:
            raise ValidationError("Missing pestel_report in result state")
            
        # PESTEL report is kept in memory only - no Supabase saving
        # The report will be passed directly to the report generator
        logger.info("PESTEL report generated and kept in memory for direct merging")        
        # Update the original state with PESTEL analysis results
        state.update(pestel_state)
        
        logger.info(f"PESTEL analysis completed successfully with in-memory report")
        update_metrics("pestel_analysis", start_time, True)
        return state
        
    except Exception as e:
        logger.error(f"PESTEL analysis step failed: {str(e)}", exc_info=True)
        update_metrics("pestel_analysis", start_time, False)
        raise AgentError(f"PESTEL analysis agent failed: {str(e)}")


def pestel_analysis_path(state: Dict[str, Any]) -> str:
    """
    Determine the expected file path for PESTEL analysis output.
    
    Args:
        state: The current workflow state
        
    Returns:
        File path for PESTEL analysis output
    """
    session_id = state.get("session_id", "unknown_job")
    return os.path.join(DEFAULT_OUTPUT_DIR, session_id, "pestel_report.json")


async def check_analysis_reports_complete(state: Dict[str, Any]) -> bool:
    """
    Check if both industry and PESTEL analysis reports are complete and valid in memory.
    
    Args:
        state: The current workflow state
        
    Returns:
        Boolean indicating if both reports are complete and valid
    """
    try:
        # Check if reports are in memory
        industry_report = state.get("industry_report")
        pestel_report = state.get("pestel_report")
        
        if not industry_report:
            logger.warning("Missing industry report in state")
            return False
            
        if not pestel_report:
            logger.warning("Missing PESTEL report in state")
            return False
        
        logger.info("Checking in-memory analysis reports")
        
        # Parse reports if they are JSON strings
        try:
            if isinstance(industry_report, str):
                industry_data = json.loads(industry_report)
            else:
                industry_data = industry_report
                
            if isinstance(pestel_report, str):
                pestel_data = json.loads(pestel_report)
            else:
                pestel_data = pestel_report
                
            logger.info(f"Industry report loaded successfully with keys: {list(industry_data.keys()) if isinstance(industry_data, dict) else 'not a dict'}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse industry report JSON: {str(e)}")
            return False
        
        logger.info(f"PESTEL report loaded successfully with keys: {list(pestel_data.keys()) if isinstance(pestel_data, dict) else 'not a dict'}")
        
        # Validate industry report content
        if not industry_data:
            logger.warning(f"Industry report is empty or failed to load")
            return False
            
        # Check for required keys - accept both 'sections' and 'analysis' formats
        required_base_keys = ["title", "summary"]
        if not all(key in industry_data for key in required_base_keys):
            missing_keys = [k for k in required_base_keys if k not in industry_data]
            logger.warning(f"Industry report is missing required keys: {missing_keys}")
            return False
            
        # Check for content section - accept either 'sections' or 'analysis'
        if "sections" not in industry_data and "analysis" not in industry_data:
            logger.warning(f"Industry report is missing content section (either 'sections' or 'analysis')")
            logger.warning(f"Industry report content structure: {json.dumps({k: type(v).__name__ for k, v in industry_data.items()}, indent=2)}")
            return False
        
        # Validate industry content format (sections or analysis)
        content_key = "sections" if "sections" in industry_data else "analysis"
        sections = industry_data[content_key]
        if isinstance(sections, dict):
            if not sections:  # Empty dict
                logger.warning("Industry report has empty content dictionary")
                return False
            logger.info(f"Industry report has dictionary content with {len(sections)} keys: {list(sections.keys())[:5]}..." if len(sections) > 5 else f"Industry report has dictionary content with {len(sections)} keys: {list(sections.keys())}")
        elif isinstance(sections, list):
            if not sections:  # Empty list
                logger.warning("Industry report has empty content list")
                return False
            logger.info(f"Industry report has list content with {len(sections)} items")
        else:
            logger.warning(f"Industry report has invalid content format: {type(sections).__name__}")
            return False
                
        # Validate PESTEL report content
        if not pestel_data:
            logger.warning(f"PESTEL report is empty or failed to load")
            return False
            
        # Check for required keys - accept both 'sections' and 'analysis' formats
        required_base_keys = ["title", "summary"]
        if not all(key in pestel_data for key in required_base_keys):
            missing_keys = [k for k in required_base_keys if k not in pestel_data]
            logger.warning(f"PESTEL report is missing required keys: {missing_keys}")
            return False
            
        # Check for content section - accept either 'sections' or 'analysis'
        if "sections" not in pestel_data and "analysis" not in pestel_data:
            logger.warning(f"PESTEL report is missing content section (either 'sections' or 'analysis')")
            logger.warning(f"PESTEL report content structure: {json.dumps({k: type(v).__name__ for k, v in pestel_data.items()}, indent=2)}")
            return False
            
        # Validate PESTEL content format (sections or analysis)
        content_key = "sections" if "sections" in pestel_data else "analysis"
        sections = pestel_data[content_key]
        if isinstance(sections, dict):
            if not sections:  # Empty dict
                logger.warning("PESTEL report has empty content dictionary")
                return False
            logger.info(f"PESTEL report has dictionary content with {len(sections)} keys: {list(sections.keys())[:5]}..." if len(sections) > 5 else f"PESTEL report has dictionary content with {len(sections)} keys: {list(sections.keys())}")
        elif isinstance(sections, list):
            if not sections:  # Empty list
                logger.warning("PESTEL report has empty content list")
                return False
            logger.info(f"PESTEL report has list content with {len(sections)} items")
        else:
            logger.warning(f"PESTEL report has invalid content format: {type(sections).__name__}")
            return False
            
        # If we get here, both reports are valid
        logger.info("Both industry and PESTEL reports are valid and complete")
        return True
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing report JSON: {str(e)}")
        return False
    except IOError as e:
        logger.error(f"File I/O error accessing reports: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error checking analysis reports: {str(e)}", exc_info=True)
        return False


# Recommender Agent Integration
# Recommendation generation is now handled directly by industry and PESTEL agents
# The standalone recommender agent has been removed


def recommendations_path(state: Dict[str, Any]) -> str:
    """
    Determine the expected file path for recommendations output.
    Note: This is maintained for backwards compatibility. Recommendations are now 
    embedded directly in industry and PESTEL mini reports and merged in the final report.
    
    Args:
        state: The current workflow state
        
    Returns:
        File path for recommendations output
    """
    session_id = state.get("session_id", "unknown_job")
    return os.path.join(DEFAULT_OUTPUT_DIR, session_id, "recommendations.json")


# Report Generator Integration
@traceable(name="Report_Generation")
async def workflow_run_report_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the report generator to create the final report from all analyses.
    
    Args:
        state: The current workflow state with recommendations and analysis reports
        
    Returns:
        Updated state with final report
    """
    start_time = time.time()
    logger.info("Starting report generation step...")
    
    try:
        # Recommendations are now embedded in industry and PESTEL reports
        # No need to check for standalone recommendations
        logger.info("Using recommendations embedded in industry and PESTEL reports")
            
        # Check if analysis reports are complete
        if not await check_analysis_reports_complete(state):
            raise ValidationError("Analysis reports are incomplete or invalid")
            
        # Set default workflow configuration if not present
        workflow_config = ensure_state_key(state, "workflow_config", {})
        ensure_state_key(workflow_config, "report_generator", {})
        ensure_state_key(workflow_config["report_generator"], "enabled", True)
        ensure_state_key(workflow_config["report_generator"], "format", "markdown")
        
        # Skip report generation if disabled in config
        if not workflow_config["report_generator"].get("enabled", True):
            logger.info("Report generator is disabled in configuration, skipping")
            return state
            
        # Create output directory if it doesn't exist
        report_output_dir = os.path.join(DEFAULT_OUTPUT_DIR, state["session_id"])
        os.makedirs(report_output_dir, exist_ok=True)
        
        # Set the output path for final report - always use JSON format
        report_output_path = os.path.join(report_output_dir, "final_report.json")
        
        # Run report generator agent using in-memory reports
        logger.info("Running report generator with in-memory reports")
        
        # Get the industry and PESTEL reports directly from memory
        industry_report = state.get("industry_report")
        pestel_report = state.get("pestel_report")
        
        # Validate that we have both reports in memory
        if not industry_report:
            raise ValidationError("Industry report not found in state")
        if not pestel_report:
            raise ValidationError("PESTEL report not found in state")
            
        # Parse reports if they are JSON strings
        if isinstance(industry_report, str):
            try:
                industry_report = json.loads(industry_report)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Failed to parse industry report JSON: {str(e)}")
                
        if isinstance(pestel_report, str):
            try:
                pestel_report = json.loads(pestel_report)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Failed to parse PESTEL report JSON: {str(e)}")
        
        # Generate a title for the report based on the original query
        report_title = f"MINT Analysis Report: {state.get('initial_query', '')}"
        
        logger.info("Generating final report from in-memory industry and PESTEL reports")
        
        try:
            # Import and run the report generator with in-memory data
            from src.mint.agents.report_generator import ReportGenerator
            
            # Create report generator instance
            report_generator = ReportGenerator()
            
            # Generate the final report using in-memory reports
            structured_report = report_generator.merge_reports_manually(
                industry_report=industry_report,
                pestel_report=pestel_report
            )
            
            if not structured_report:
                raise ValidationError("Report generator returned empty report")
                
            # Save the final report to local file
            with open(report_output_path, "w") as f:
                json.dump(structured_report, f, indent=2)
            logger.info(f"Saved final report to local file: {report_output_path}")
            
        except Exception as e:
            logger.error(f"Error generating final report: {str(e)}")
            raise ValidationError(f"Failed to generate final report: {str(e)}")
            
        # Ensure user_id is properly extracted and validated
        user_id = state.get("user_id")
        user_token = state.get("user_token")
        
        # Extract user_id from token if not already present
        if not user_id and user_token:
            try:
                import jwt
                payload = jwt.decode(user_token, options={"verify_signature": False})
                user_id = payload.get("sub")
                state["user_id"] = user_id
                logger.info(f"Extracted user_id from token: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to extract user_id from token: {e}")
        
        # Validate that we have a user_id
        if not user_id:
            logger.error("No user_id available for report creation")
            raise ValueError("user_id is required for report creation")
        
        logger.info(f"Using user_id: {user_id} for report creation")
        
        # Credit system removed - skip final credit validation
        logger.info(f"Credit validation bypassed for user {user_id} (credit system removed)")
        # Save the final report to Supabase
        try:
            from src.mint.api.system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
            from src.mint.api.services.utilities.id_logging_service import log_report_generation_pipeline, IDOperationTracker
            
            # Extract user token and session info from state
            user_token = state.get("user_token")
            user_id = state.get("user_id")
            session_id = state["session_id"]
            
            # Start comprehensive ID tracking for report saving
            with IDOperationTracker("REPORT_SAVE_TO_SUPABASE", 
                                  session_id=session_id, 
                                  user_id=user_id) as tracker:
                
                logger.info(f"DEBUG: About to save final report to Supabase for session {session_id}")
                logger.info(f"DEBUG: User token present: {user_token is not None}")
                logger.info(f"DEBUG: User token length: {len(user_token) if user_token else 0}")
                logger.info(f"DEBUG: User token value (first 50 chars): {user_token[:50] if user_token else 'None'}")
                logger.info(f"DEBUG: State keys available: {list(state.keys())}")
                logger.info(f"DEBUG: User ID from state: {state.get('user_id', 'Not found')}")
                
                # Validate IDs before proceeding
                tracker.validate_id("session_id", session_id, required=True)
                tracker.validate_id("user_id", user_id, required=False)
                
                # Log the report generation pipeline stage
                log_report_generation_pipeline("REPORT_SAVE_START", 
                                             session_id, 
                                             user_id=user_id,
                                             session_id=session_id,
                                             has_user_token=user_token is not None)
                        
                # Try with user token first, fall back to service role if needed
                supabase_client = None
                saved_report_id = None
                
                if user_token and user_id:
                    try:
                        logger.info(f"Attempting to save report with user token for session {session_id}")
                        supabase_client = get_standard_client()
                        saved_report_id = await supabase_client.update_workflow_report(
                            session_id=session_id,
                            report_type="final",
                            content=structured_report,
                            user_token=user_token,
                            workflow_state=state
                        )
                        logger.info(f"Successfully saved report with user token, report ID: {saved_report_id}")
                        
                        # Log successful save with ID tracking
                        tracker.update_ids("USER_TOKEN_SAVE_SUCCESS", saved_report_id=saved_report_id)
                        log_report_generation_pipeline("REPORT_SAVED_USER_TOKEN", 
                                                     saved_report_id, 
                                                     user_id=user_id,
                                                     session_id=session_id)
                    except Exception as token_error:
                        logger.warning(f"Failed to save with user token, will try service role: {token_error}")
                        saved_report_id = None
                
                # Fall back to service role if user token failed or wasn't available
                if not saved_report_id:
                    try:
                        logger.info(f"Attempting to save report with service role for session {session_id}")
                        service_client = get_service_role_client()
                        
                        # Create a modified state that includes user_id for service role usage
                        service_state = state.copy()
                        service_state["user_id"] = user_id  # Ensure user_id is available
                        
                        # Validate user_id before proceeding
                        if not user_id:
                            logger.error("Cannot save report: user_id is missing")
                            raise ValueError("user_id is required for report creation")
                        
                        logger.info(f"Service role save: using user_id {user_id}")
                        
                        saved_report_id = await service_client.update_workflow_report(
                            session_id=session_id,
                            report_type="final",
                            content=structured_report,
                            user_token=None,  # No token - use service role
                            workflow_state=service_state
                        )
                        logger.info(f"Successfully saved report with service role, report ID: {saved_report_id}")
                        
                        # Log successful save with ID tracking
                        tracker.update_ids("SERVICE_ROLE_SAVE_SUCCESS", saved_report_id=saved_report_id)
                        log_report_generation_pipeline("REPORT_SAVED_SERVICE_ROLE", 
                                                     saved_report_id, 
                                                     user_id=user_id,
                                                     session_id=session_id)
                    except Exception as service_error:
                        logger.error(f"Failed to save with service role: {service_error}")
                        saved_report_id = None
                
                # ALWAYS set the final report data, regardless of Supabase save success
                # This ensures the workflow service can access the report even if Supabase save fails
                state["status"] = "completed"
                state["final_report_uri"] = report_output_path
                state["final_report_json"] = structured_report
                state["final_report"] = structured_report
                state["report"] = structured_report
                
                if saved_report_id:
                    logger.info(f"Final report saved to Supabase for session {session_id}")
                    
                    # Store the report ID in workflow state for frontend access
                    state["saved_report_id"] = saved_report_id
                    state["report_id"] = saved_report_id  # Also store as report_id for consistency
                else:
                    logger.warning(f"Supabase save failed, but workflow completed with report data in memory")
                
                logger.info(f"Report generation completed successfully: {report_output_path}")
                logger.info(f"Starting background vector storage integration for session {session_id} with report ID {saved_report_id}")
                
                # Add vector storage integration - chunk, embed, and store the report (in background)
                try:
                        
                        # Log vector storage start with comprehensive ID tracking
                        tracker.update_ids("VECTOR_STORAGE_START", saved_report_id=saved_report_id)
                        log_report_generation_pipeline("VECTOR_STORAGE_START", 
                                                     saved_report_id, 
                                                     user_id=user_id,
                                                     session_id=session_id)
                        
                        # Enhanced ID consistency logging
                        logger.info(f"ID CONSISTENCY TRACKING:")
                        logger.info(f"  Session ID: {session_id} (type: {type(session_id).__name__})")
                        logger.info(f"  Report ID: {saved_report_id} (type: {type(saved_report_id).__name__})")
                        logger.info(f"  User ID: {user_id} (type: {type(user_id).__name__})")
                        
                        from src.mint.api.report.report_chunking_service import ReportChunkingService
                        
                        # Use the actual report ID from the database, fallback to session_id if save failed
                        report_id = saved_report_id if saved_report_id else session_id
                        
                        # Verify report exists before chunking
                        from src.mint.api.system.core.supabase_client import get_service_role_client
                        verify_client = get_service_role_client()
                        verify_result = verify_client.client.table("documents") \
                            .select("id, created_by, title") \
                            .eq("id", report_id) \
                            .eq("source_type", "pv_report") \
                            .execute()
                        
                        if not verify_result.data:
                            logger.error(f"CRITICAL: Report {report_id} not found in database before chunking!")
                            state["vector_storage_complete"] = False
                        else:
                            report_data = verify_result.data[0]
                            logger.info(f"Verified report exists: {report_data['title']} (User: {report_data['created_by']})")
                            
                            # Initialize the chunking service
                            chunking_service = ReportChunkingService()
                            
                            # Process the report for vector storage with enhanced logging
                            logger.info(f"Processing report {report_id} for vector storage...")
                            vector_storage_success = await chunking_service.process_report_from_json(
                                report_id=report_id,
                                report_json=structured_report
                            )
                            
                            if vector_storage_success:
                                logger.info(f"Successfully stored report {report_id} in vector store")
                                
                                # Log successful vector storage
                                tracker.update_ids("VECTOR_STORAGE_SUCCESS", report_id=report_id)
                                log_report_generation_pipeline("VECTOR_STORAGE_SUCCESS", 
                                                             report_id, 
                                                             user_id=user_id,
                                                             session_id=session_id)
                                
                                # Verify chunks were created
                                chunks_verify = verify_client.client.table("chunks") \
                                    .select("id") \
                                    .eq("doc_id", report_id) \
                                    .execute()
                                
                                chunk_count = len(chunks_verify.data) if chunks_verify.data else 0
                                logger.info(f"Verification: {chunk_count} chunks created for report {report_id}")
                                
                                state["vector_storage_complete"] = True
                                state["chunks_created"] = chunk_count
                                
                                # Trigger background chat preparation for immediate availability
                                logger.info(f"Vector storage completed successfully - chat is now ready for report {report_id}")
                                state["chat_ready"] = True
                            else:
                                logger.error(f"Failed to store report {report_id} in vector store")
                                state["vector_storage_complete"] = False
                            
                except Exception as vector_error:
                        logger.error(f"Error during vector storage integration: {str(vector_error)}")
                        logger.error(f"Vector storage error type: {type(vector_error).__name__}")
                        logger.error(f"Report ID context: {saved_report_id}")
                        import traceback
                        logger.error(f"Vector storage traceback: {traceback.format_exc()}")
                        state["vector_storage_complete"] = False
                        # Don't fail the entire workflow if vector storage fails
                    
                    # Add actionable insights generation - ONLY after vector storage is complete
                if state.get("vector_storage_complete", False):
                        try:
                            logger.info(f"Vector storage complete - starting background actionable insights generation for session {session_id} with report ID {saved_report_id}")
                            
                            # Import the insights service
                            from src.mint.api.actionable_insights import get_actionable_insights_service, InsightGenerationContext
                            
                            # Extract user context from workflow state
                            workflow_metadata = state.get("workflow_metadata", {})
                            insight_context = InsightGenerationContext(
                                user_id=user_id,
                                report_id=saved_report_id,
                                industry=workflow_metadata.get("industry"),
                                geography=workflow_metadata.get("geography"), 
                                background=workflow_metadata.get("background"),
                                product_type=workflow_metadata.get("product_type")
                            )
                            
                            # Generate insights asynchronously (fire and forget)
                            insights_service = get_actionable_insights_service()
                            
                            # Use asyncio.create_task to run in background without blocking
                            import asyncio
                            async def generate_insights_background():
                                try:
                                    # Add a small delay to ensure chunks are fully committed to database
                                    await asyncio.sleep(2)
                                    logger.info(f"Background insight generation started for report {saved_report_id}")
                                    result = await insights_service.generate_insights(saved_report_id, insight_context)
                                    if result.success:
                                        logger.info(f"Background insight generation completed successfully for report {saved_report_id}: {result.total_insights} insights generated")
                                    else:
                                        logger.error(f"Background insight generation failed for report {saved_report_id}: {result.error_message}")
                                except Exception as insight_error:
                                    logger.error(f"Background insight generation error for report {saved_report_id}: {str(insight_error)}")
                            
                            # Start background task without awaiting
                            asyncio.create_task(generate_insights_background())
                            
                            logger.info(f"Actionable insights generation initiated in background for report {saved_report_id}")
                            state["insights_generation_initiated"] = True
                            
                        except Exception as insights_error:
                            logger.error(f"Error initiating actionable insights generation: {str(insights_error)}")
                            logger.error(f"Insights error type: {type(insights_error).__name__}")
                            import traceback
                            logger.error(f"Insights error traceback: {traceback.format_exc()}")
                            state["insights_generation_initiated"] = False
                            # Don't fail the entire workflow if insights initiation fails
                    
        except Exception as e:
            logger.error(f"Failed to save final report to Supabase: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Continue execution - local file is sufficient
                
        # State already set above before chunking - no need to duplicate
        # The workflow is marked as completed before chunking to allow immediate navigation
        update_metrics("report_generation", start_time, True)
        return state
            
    except ValidationError as ve:
        logger.error(f"Validation error in report generation: {str(ve)}")
        state["status"] = "failed"
        state["error"] = str(ve)
        update_metrics("report_generation", start_time, False)
        raise
            
    except Exception as e:
        logger.error(f"Report generation step failed: {str(e)}", exc_info=True)
        state["status"] = "failed"
        state["error"] = str(e)
        update_metrics("report_generation", start_time, False)
        raise AgentError(f"Report generation failed: {str(e)}")


async def get_report_content_from_uri(uri: str) -> Dict[str, Any]:
    """Load report content from a URI, which can be a file path or a Supabase URI.

{{ ... }}
    Args:
        uri: The URI of the report, either a file path or a Supabase URI.
             Format supported: supabase://<workflow_id>:<report_type>
             where report_type is industry, pestel, etc.

    Returns:
        The report content as a dictionary in JSON format ready for the LLM.
    """
    if uri.startswith("supabase://"):
        try:
            # Extract parts from the URI
            uri_parts = uri.replace("supabase://", "").split(":")
            
            from src.mint.api.system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
            supabase = get_standard_client()
            
            if len(uri_parts) == 2:
                # Format: supabase://<workflow_id>:<report_type>
                workflow_id = uri_parts[0]
                report_type = uri_parts[1]
                
                logger.info(f"Loading {report_type} report from unified report with ID {workflow_id}")
                
                # Query directly by ID - this is a unified report
                query = supabase.client.table("mint_reports")\
                    .select("*")\
                    .eq("id", workflow_id)  # Using ID directly
                
                response = query.execute()
                
                if not response.data or len(response.data) == 0:
                    logger.error(f"No report found with ID: {workflow_id}")
                    return {}
                
                # Get the report
                report = response.data[0]
                
                # Check for content field
                if "content" not in report or not report["content"]:
                    logger.error(f"Report has no content field or it's empty for ID: {workflow_id}")
                    return {}
                
                content = report["content"]
                logger.info(f"Content has these keys: {list(content.keys()) if isinstance(content, dict) else 'Not a dict'}")
                
                # Extract the specific report from the reports structure
                reports = content.get("reports", {})
                if report_type not in reports:
                    logger.error(f"Report type '{report_type}' not found in unified report with ID: {workflow_id}")
                    return {}
                
                report_content = reports.get(report_type, {})
                logger.info(f"Found {report_type} report with keys: {list(report_content.keys()) if isinstance(report_content, dict) else 'Not a dict'}")
                
                # Ensure the report has the required keys for LLM consumption
                if "title" not in report_content:
                    logger.info(f"Added missing 'title' to report from {uri}")
                    report_content["title"] = "Generated Report"
                    
                if "summary" not in report_content:
                    logger.info(f"Added missing 'summary' to report from {uri}")
                    report_content["summary"] = "This is an automatically generated report."
                    
                if "sections" not in report_content:
                    logger.info(f"Added missing 'sections' to report from {uri}")
                    report_content["sections"] = [{"heading": "Generated Content", "content": "No content available"}]
                
                logger.info(f"Report from {uri} has keys: {list(report_content.keys())}")
                return report_content
            else:
                logger.error(f"Invalid Supabase URI format: {uri}, expected format: supabase://workflow_id:report_type")
                return {}
            
            return report_content
        except Exception as e:
            logger.error(f"Error loading report from Supabase: {str(e)}")
            return {}
    else:
        # Load from local file
        try:
            with open(uri, "r") as f:
                report_content = json.load(f)
                
                # Ensure it has the basic structure expected by the validation
                if isinstance(report_content, dict):
                    # Add required keys if missing
                    if "title" not in report_content:
                        report_content["title"] = "Generated Report"
                    if "summary" not in report_content:
                        report_content["summary"] = "Summary not available"
                    if "sections" not in report_content:
                        report_content["sections"] = [{
                            "title": "Content",
                            "content": str(report_content)
                        }]
                        
                return report_content
        except Exception as e:
            logger.error(f"Error loading report from file: {str(e)}")
            return {}


def final_report_path(state: Dict[str, Any], format: str = "markdown") -> str:
    """
    Determine the expected file path for final report output.
    
    Args:
        state: The current workflow state
        format: The report format (markdown or json)
        
    Returns:
        File path for final report output
    """
    session_id = state.get("session_id", "unknown_job")
    extension = ".md" if format.lower() == "markdown" else ".json"
    return os.path.join(DEFAULT_OUTPUT_DIR, session_id, f"final_report{extension}")


# Comprehensive error handling and validation
def validate_job_inputs(state: Dict[str, Any]) -> None:
    """
    Validate initial job inputs to ensure they are well-formed.
    
    Args:
        state: The workflow state dictionary
        
    Raises:
        ValidationError: If required fields are missing or invalid
    """
    # Check for required initial fields
    if "initial_query" not in state or not state["initial_query"]:
        raise ValidationError("Missing or empty initial query")
        
    if "session_id" not in state or not state["session_id"]:
        raise ValidationError("Missing job identifier")
        
    if "user_id" not in state or not state["user_id"]:
        raise ValidationError("Missing user identifier")
        
    # Validate workflow configuration if present
    if "workflow_config" in state and state["workflow_config"]:
        if not isinstance(state["workflow_config"], dict):
            raise ValidationError("workflow_config must be a dictionary")


async def validate_workflow_state(state: Dict[str, Any], step_name: str) -> None:
    """
    Validate the workflow state at a specific step to ensure it has all
    required inputs for that step.
    
    Args:
        state: The workflow state dictionary
        step_name: The name of the step to validate for
        
    Raises:
        ValidationError: If required fields for the step are missing or invalid
    """
    # Always validate basic job inputs
    validate_job_inputs(state)
    
    # Specific validations by step
    if step_name == "clarification":
        # Nothing additional to validate beyond basic inputs
        pass
    
    elif step_name == "process_answers":
        if "clarification" not in state or not state["clarification"]:
            raise ValidationError("Missing clarification data for processing answers")
            
        if "user_answers" not in state or not state["user_answers"]:
            raise ValidationError("Missing user answers")
    
    elif step_name == "specification":
        if not state.get("clarification_complete", False):
            raise ValidationError("Clarification step not marked as complete")
    
    elif step_name == "industry_analysis" or step_name == "pestel_analysis":
        if not await check_specifications_complete(state):
            raise ValidationError("Specifications are incomplete or invalid")
    
    elif step_name == "recommendations":
        if not check_analysis_reports_complete(state):
            raise ValidationError("Analysis reports are incomplete or invalid")
    
    elif step_name == "report_generation":
        if "recommendations" not in state or not state["recommendations"]:
            raise ValidationError("Missing recommendations for report generation")
            
        if not check_analysis_reports_complete(state):
            raise ValidationError("Analysis reports are incomplete or invalid")
            

def save_workflow_state(state: Dict[str, Any], filename: str = None) -> str:
    """
    Save the current workflow state to a file for persistence or debugging.
    
    Args:
        state: The workflow state dictionary
        filename: Optional filename prefix to use
        
    Returns:
        Path to the saved state file
    """
    # Create directory if needed
    session_id = state.get("session_id", "unknown_job")
    state_dir = os.path.join(DEFAULT_OUTPUT_DIR, session_id)
    os.makedirs(state_dir, exist_ok=True)
    
    # Generate filename with timestamp
    if filename:
        state_path = os.path.join(state_dir, f"{filename}.json")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        state_path = os.path.join(state_dir, f"workflow_state_{timestamp}.json")
    
    # Save state, filtering out non-serializable objects
    try:
        # Create a copy to avoid modifying original state
        serializable_state = {}
        for k, v in state.items():
            # Skip callable objects and some potentially large data fields
            if not callable(v) and k not in ["industry_report_data", "pestel_report_data"]:
                try:
                    # Test JSON serialization
                    json.dumps({k: v})
                    serializable_state[k] = v
                except (TypeError, OverflowError):
                    # If not serializable, convert to string representation
                    serializable_state[k] = str(v)
        
        with open(state_path, "w") as f:
            json.dump(serializable_state, f, indent=2)
            
        return state_path
        
    except Exception as e:
        logger.error(f"Failed to save workflow state: {str(e)}")
        return ""
        

# Main workflow runner
@traceable(name="mint_workflow")
async def run_workflow(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete MINT workflow orchestrating all agent steps.
    
    Args:
        state: The initial workflow state with query and identifiers
        
    Returns:
        Updated state with all workflow results
    """
    start_time = time.time()
    workflow_state_path = ""
    
    try:
        # Validate initial inputs
        validate_job_inputs(state)
        
        # Set initial status if not present
        if "status" not in state:
            state["status"] = "pending"
            
        # Set up default configuration
        ensure_state_key(state, "workflow_config", {})
        ensure_state_key(state, "interactive_mode", False)
        
        # Create job output directory
        job_output_dir = os.path.join(DEFAULT_OUTPUT_DIR, state["session_id"])
        os.makedirs(job_output_dir, exist_ok=True)
        
        logger.info(f"Starting MINT workflow for job {state['session_id']} with query: {state['initial_query']}")
        
        # Save initial state
        workflow_state_path = save_workflow_state(state)
        
        # Step 1: Clarification
        logger.info("Running clarification step")
        state["status"] = "clarifying"
        state = await workflow_run_clarification(state)
        
        # Check if we should proceed or wait for user input
        if state.get("_workflow_paused_for_input", False):
            logger.info("Workflow paused for user input on clarification questions")
            return state
            
        # If user answers are already provided, process them
        if state.get("awaiting_clarification", False) and "user_answers" in state and state["user_answers"]:
            logger.info("Processing user answers to clarification questions")
            state = await workflow_process_clarification_answers(state)
        
        # Step 2: Specification
        logger.info("Running specification step")
        state["status"] = "researching"
        state = await workflow_run_specification(state)
        
        # Step 3: Industry Analysis (can run in parallel with PESTEL)
        logger.info("Running industry analysis step")
        industry_task = asyncio.create_task(workflow_run_industry_analysis(state))
        
        # Step 4: PESTEL Analysis (can run in parallel with Industry)
        logger.info("Running PESTEL analysis step")
        pestel_task = asyncio.create_task(workflow_run_pestel_analysis(state))
        
        # Wait for both industry and PESTEL analysis to complete
        industry_state = await industry_task
        pestel_state = await pestel_task
        
        # Merge results from both tasks
        if "industry_report_uri" in industry_state:
            state["industry_report_uri"] = industry_state["industry_report_uri"]
            
        if "pestel_report_uri" in pestel_state:
            state["pestel_report_uri"] = pestel_state["pestel_report_uri"]
        
        # Recommendations are now generated directly by industry and PESTEL agents
        # No need for a separate recommendation step
        logger.info("Skipping separate recommendations step - now integrated with analysis agents")
        state["status"] = "analyzing"
        
        # Step 6: Report Generation
        logger.info("Running report generation step")
        state["status"] = "generating"
        state = await workflow_run_report_generation(state)
        
        # Workflow completed successfully
        state["status"] = "completed"
        logger.info(f"Workflow completed successfully for job {state['session_id']}")
        
        # Save final state
        workflow_state_path = save_workflow_state(state)
        
        update_metrics("full_workflow", start_time, True)
        return state
        
    except AgentError as e:
        logger.error(f"Agent error in workflow: {str(e)}")
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("full_workflow", start_time, False)
        raise
        
    except ValidationError as e:
        logger.error(f"Validation error in workflow: {str(e)}")
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("full_workflow", start_time, False)
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in workflow: {str(e)}", exc_info=True)
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("full_workflow", start_time, False)
        raise WorkflowError(f"Workflow failed unexpectedly: {str(e)}")


# Placeholder to preserve formatting and code structure
# This section intentionally left empty to remove the duplicate function


# End of workflow implementation functions
        
    @staticmethod
    def pre_specification(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the specification agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_specification(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the specification agent runs.
        
        Args:
            state: The workflow state with specification results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_industry_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the industry analysis agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_industry_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the industry analysis agent runs.
        
        Args:
            state: The workflow state with industry analysis results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_pestel_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the PESTEL analysis agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_pestel_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the PESTEL analysis agent runs.
        
        Args:
            state: The workflow state with PESTEL analysis results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_recommendations(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the recommender agent runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_recommendations(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the recommender agent runs.
        
        Args:
            state: The workflow state with recommendation results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def pre_report_generation(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed before the report generator runs.
        
        Args:
            state: The current workflow state
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def post_report_generation(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook executed after the report generator runs.
        
        Args:
            state: The workflow state with final report results
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def on_workflow_error(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Hook executed when an error occurs in the workflow.
        
        Args:
            state: The current workflow state
            error: The exception that was raised
            
        Returns:
            Potentially modified state
        """
        return state
        
    @staticmethod
    def custom_validation(state: Dict[str, Any], step_name: str) -> Optional[str]:
        """
        Custom validation hook for workflow state at a specific step.
        
        Args:
            state: The workflow state to validate
            step_name: The name of the current step
            
        Returns:
            None if valid, or error message string if invalid
        """
        return None


# Default hooks implementation for use in workflow
hooks = WorkflowHooks()


def register_workflow_hooks(custom_hooks: WorkflowHooks) -> None:
    """
    Register custom workflow hooks for extensibility.
    
    Args:
        custom_hooks: Custom implementation of WorkflowHooks
    """
    global hooks
    hooks = custom_hooks
    logger.info("Custom workflow hooks registered")


# Main workflow runner with hooks support
@traceable(name="mint_workflow")
async def run_workflow(state: Dict[str, Any], custom_hooks: Optional[WorkflowHooks] = None) -> Dict[str, Any]:
    """
    Run the complete MINT workflow orchestrating all agent steps.
    
    Args:
        state: The initial workflow state with query and identifiers
{{ ... }}
        custom_hooks: Optional custom hooks implementation
        
    Returns:
        Updated state with all workflow results
    """
    start_time = time.time()
    workflow_state_path = ""
    
    # Register custom hooks if provided
    if custom_hooks:
        register_workflow_hooks(custom_hooks)
    
    try:
        # Validate initial inputs
        validate_job_inputs(state)
        
        # Set initial status if not present
        if "status" not in state:
            state["status"] = "pending"
            
        # Set up default configuration
        ensure_state_key(state, "workflow_config", {})
        ensure_state_key(state, "interactive_mode", False)
        
        # Create job output directory
        job_output_dir = os.path.join(DEFAULT_OUTPUT_DIR, state["session_id"])
        os.makedirs(job_output_dir, exist_ok=True)
        
        logger.info(f"Starting MINT workflow for job {state['session_id']} with query: {state['initial_query']}")
        
        # Save initial state
        workflow_state_path = save_workflow_state(state)
        
        # Step 1: Clarification with hooks
        logger.info("Running clarification step")
        state["status"] = "clarifying"
        state = hooks.pre_clarification(state)
        state = await workflow_run_clarification(state)
        state = hooks.post_clarification(state)
        
        # Check if we should proceed or wait for user input
        if state.get("_workflow_paused_for_input", False):
            logger.info("Workflow paused for user input on clarification questions")
            return state
            
        # If user answers are already provided, process them
        if state.get("awaiting_clarification", False) and "user_answers" in state and state["user_answers"]:
            logger.info("Processing user answers to clarification questions")
            state = await workflow_process_clarification_answers(state)
        
        # Step 2: Specification with hooks
        logger.info("Running specification step")
        state["status"] = "researching"
        state = hooks.pre_specification(state)
        state = await workflow_run_specification(state)
        state = hooks.post_specification(state)
        
        # Step 3: Industry Analysis with hooks (can run in parallel with PESTEL)
        logger.info("Running industry analysis step")
        state = hooks.pre_industry_analysis(state)
        industry_task = asyncio.create_task(workflow_run_industry_analysis(state))
        
        # Step 4: PESTEL Analysis with hooks (can run in parallel with Industry)
        logger.info("Running PESTEL analysis step")
        state = hooks.pre_pestel_analysis(state)
        pestel_task = asyncio.create_task(workflow_run_pestel_analysis(state))
        
        # Wait for both industry and PESTEL analysis to complete
        industry_state = await industry_task
        industry_state = hooks.post_industry_analysis(industry_state)
        
        pestel_state = await pestel_task
        pestel_state = hooks.post_pestel_analysis(pestel_state)
        
        # Merge results from both tasks
        if "industry_report_uri" in industry_state:
            state["industry_report_uri"] = industry_state["industry_report_uri"]
            
        if "pestel_report_uri" in pestel_state:
            state["pestel_report_uri"] = pestel_state["pestel_report_uri"]
        
        # Recommendations are now generated directly by industry and PESTEL agents
        # No need for a separate recommendation step
        logger.info("Skipping separate recommendations step - now integrated with analysis agents")
        state["status"] = "analyzing"
        
        # Step 6: Report Generation with hooks
        logger.info("Running report generation step")
        state["status"] = "generating"
        state = hooks.pre_report_generation(state)
        state = await workflow_run_report_generation(state)
        state = hooks.post_report_generation(state)
        
        # Workflow completed successfully
        state["status"] = "completed"
        logger.info(f"Workflow completed successfully for job {state['session_id']}")
        
        # Save final state
        workflow_state_path = save_workflow_state(state)
        
        update_metrics("full_workflow", start_time, True)
        return state
        
    except AgentError as e:
        logger.error(f"Agent error in workflow: {str(e)}")
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Execute error hook
        state = hooks.on_workflow_error(state, e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("full_workflow", start_time, False)
        raise
        
    except ValidationError as e:
        logger.error(f"Validation error in workflow: {str(e)}")
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Execute error hook
        state = hooks.on_workflow_error(state, e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("full_workflow", start_time, False)
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in workflow: {str(e)}", exc_info=True)
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Execute error hook
        state = hooks.on_workflow_error(state, e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("full_workflow", start_time, False)
        raise WorkflowError(f"Workflow failed unexpectedly: {str(e)}")


# Handler for resumed workflow (after user input) with hooks support
@traceable(name="mint_resume_workflow")
async def resume_workflow(state: Dict[str, Any], custom_hooks: Optional[WorkflowHooks] = None) -> Dict[str, Any]:
    """
    Resume the MINT workflow after it was paused for user input.
    
    Args:
        state: The current workflow state with user answers
        custom_hooks: Optional custom hooks implementation
        
    Returns:
        Updated state with remaining workflow steps completed
    """

    start_time = time.time()
    
    try:
        # Validate that we have a valid job state
        validate_job_inputs(state)
        
        if not state.get("_workflow_paused_for_input", False):
            logger.warning("Attempting to resume a workflow that was not paused")
            
        # Process user answers if we were awaiting clarification
        if state.get("awaiting_clarification", False):
            logger.info("Processing user answers and resuming workflow")
            state = await workflow_process_clarification_answers(state)
            
            # Remove the pause flag
            if "_workflow_paused_for_input" in state:
                del state["_workflow_paused_for_input"]
        
        # Check what stage we're in and continue from there
        if not state.get("clarification_complete", False):
            # Still in clarification phase
            return await run_workflow(state)
            
        elif "industry_specification" not in state or "pestel_specification" not in state:
            # Need to run specification first
            logger.info("Resuming at specification step")
            state["status"] = "researching"
            state = await workflow_run_specification(state)
            
        # Continue with each remaining step in sequence rather than restarting
        logger.info("Continuing workflow execution with remaining steps")
        
        # Run industry analysis if we don't have results yet
        if "industry_analysis" not in state:
            state = await workflow_run_industry_analysis(state)
            
        # Run PESTEL analysis if we don't have results yet
        if "pestel_analysis" not in state:
            state = await workflow_run_pestel_analysis(state)
            
        # Recommendations are now generated directly by industry and PESTEL agents
        # No separate recommendation step is needed
            
        # Generate final report if we don't have it yet
        if "report" not in state:
            state = await workflow_run_report_generation(state)
            
        # Mark workflow as completed
        state["status"] = "completed"
        state["completion_time"] = datetime.now().isoformat()
        
        # Final state save
        save_workflow_state(state)
        
        logger.info(f"MINT workflow completed for job {state.get('session_id', 'unknown')}")
        update_metrics("workflow_resume", start_time, True)
        return state
        
    except Exception as e:
        logger.error(f"Error resuming workflow: {str(e)}", exc_info=True)
        state["status"] = "failed"
        state["error"] = str(e)
        
        # Save error state
        save_workflow_state(state)
        update_metrics("workflow_resume", start_time, False)
        raise WorkflowError(f"Failed to resume workflow: {str(e)}")


# For backward compatibility with existing code that imports execute_workflow
@traceable(name="mint_execute_workflow")
def execute_workflow(state: Dict[str, Any], checkpoint_manager=None) -> Dict[str, Any]:
    """
    Execute the workflow - this is a compatibility function for the celery worker.
    
    Args:
        state: The initial workflow state with query and identifiers
        checkpoint_manager: Optional checkpoint manager (ignored, kept for compatibility)
        
    Returns:
        Updated state with all workflow results
    """
    logger.info(f"Starting execute_workflow (compatibility function) with job ID: {state.get('session_id')}")
    # Just call run_workflow directly
    return asyncio.run(run_workflow(state))


# Checkpoint manager for workflow state persistence
class CheckpointManager:
    """
    Manages workflow checkpoints and state persistence.
    
    This class provides functionality to save and restore workflow state at various
    checkpoints during execution. Implemented for compatibility with existing code.
    """
    
    def __init__(self, job_id: str):
        """
        Initialize the checkpoint manager for a specific job.
        
        Args:
            job_id: The unique identifier for the job (session_id)
        """
        self.job_id = job_id
        logger.info(f"Initialized CheckpointManager for job {job_id}")
    
    def save_checkpoint(self, state: Dict[str, Any], checkpoint_name: str) -> bool:
        """
        Save a checkpoint of the current workflow state.
        
        Args:
            state: The workflow state to save
            checkpoint_name: Name/identifier for this checkpoint
            
        Returns:
            Boolean indicating success
        """
        logger.info(f"Saving checkpoint '{checkpoint_name}' for job {self.job_id}")
        # In a real implementation, this would save to Redis or another persistence store
        return True
    
    def load_checkpoint(self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a workflow state from a named checkpoint.
        
        Args:
            checkpoint_name: Name/identifier for the checkpoint to load
            
        Returns:
            The saved workflow state, or None if not found
        """
        logger.info(f"Loading checkpoint '{checkpoint_name}' for job {self.job_id}")
        # In a real implementation, this would load from Redis or another persistence store
        return None
    
    def list_checkpoints(self) -> List[str]:
        """
        List all available checkpoints for this job.
        
        Returns:
            List of checkpoint names
        """
        # In a real implementation, this would query Redis or another persistence store
        return []
