"""
Structured logging utilities for the MINT workflow.

This module provides structured logging capabilities to track workflow execution,
store metrics, and integrate with observability systems.
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class StructLogger:
    """
    Structured logger that outputs JSON for easier parsing and analysis.
    Supports multiple output targets (console, file, external services).
    """
    
    def __init__(
        self,
        service_name: str = "mint",
        level: int = logging.INFO,
        log_to_console: bool = True,
        log_to_file: bool = False,
        log_file: Optional[str] = None,
    ):
        """Initialize the structured logger."""
        self.service_name = service_name
        self.level = level
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_file = log_file or f"logs/{service_name}.log"
        
        # Ensure log directory exists
        if log_to_file and not os.path.exists(os.path.dirname(self.log_file)):
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Configure the logger
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add console handler if requested
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler if requested
        if log_to_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _prepare_log_entry(
        self,
        message: str,
        level: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Prepare a structured log entry."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        log_id = str(uuid.uuid4())
        
        log_entry = {
            "timestamp": timestamp,
            "log_id": log_id,
            "level": level,
            "service": self.service_name,
            "message": message,
        }
        
        # Add context if provided
        if context:
            log_entry["context"] = context
        
        # Add additional fields
        for key, value in kwargs.items():
            log_entry[key] = value
        
        return log_entry
    
    def log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log a message with the specified level and context."""
        log_entry = self._prepare_log_entry(message, level, context, **kwargs)
        
        # Convert to JSON
        try:
            log_json = json.dumps(log_entry)
        except (TypeError, OverflowError):
            # Handle non-serializable objects
            if context:
                log_entry["context"] = str(context)
            for key, value in kwargs.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    log_entry[key] = str(value)
            log_json = json.dumps(log_entry)
        
        # Log using the appropriate level
        if level.upper() == "DEBUG":
            self.logger.debug(log_json)
        elif level.upper() == "INFO":
            self.logger.info(log_json)
        elif level.upper() == "WARNING":
            self.logger.warning(log_json)
        elif level.upper() == "ERROR":
            self.logger.error(log_json)
        elif level.upper() == "CRITICAL":
            self.logger.critical(log_json)
        else:
            self.logger.info(log_json)
        
        return log_entry
    
    def info(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log an info message."""
        return self.log("INFO", message, context, **kwargs)
    
    def warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log a warning message."""
        return self.log("WARNING", message, context, **kwargs)
    
    def error(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log an error message."""
        return self.log("ERROR", message, context, **kwargs)
    
    def debug(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log a debug message."""
        return self.log("DEBUG", message, context, **kwargs)
    
    def critical(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log a critical message."""
        return self.log("CRITICAL", message, context, **kwargs)


class WorkflowLogger:
    """
    Specialized logger for workflow events with LangSmith integration.
    """
    
    def __init__(
        self,
        job_id: str,
        user_id: Optional[str] = None,
        structured_logger: Optional[StructLogger] = None,
    ):
        """Initialize the workflow logger."""
        self.job_id = job_id
        self.user_id = user_id
        self.structured_logger = structured_logger or StructLogger(service_name="workflow")
    
    def log_step_start(
        self,
        step_name: str,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log the start of a workflow step."""
        context = {
            "job_id": self.job_id,
            "step": step_name,
            "event": "step_start",
            "timestamp_ms": int(time.time() * 1000),
        }
        
        if self.user_id:
            context["user_id"] = self.user_id
        
        if inputs:
            # Avoid logging large inputs
            context["inputs_summary"] = {
                key: f"{str(value)[:100]}..." if isinstance(value, str) else type(value).__name__
                for key, value in inputs.items()
            }
        
        return self.structured_logger.info(
            f"Starting workflow step: {step_name}", context, **kwargs
        )
    
    def log_step_end(
        self,
        step_name: str,
        duration_ms: float,
        outputs: Optional[Dict[str, Any]] = None,
        langsmith_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log the successful completion of a workflow step."""
        context = {
            "job_id": self.job_id,
            "step": step_name,
            "event": "step_end",
            "duration_ms": duration_ms,
            "timestamp_ms": int(time.time() * 1000),
        }
        
        if self.user_id:
            context["user_id"] = self.user_id
        
        if langsmith_run_id:
            context["langsmith_run_id"] = langsmith_run_id
        
        if outputs:
            # Avoid logging large outputs
            context["outputs_summary"] = {
                key: f"{str(value)[:100]}..." if isinstance(value, str) else type(value).__name__
                for key, value in outputs.items()
            }
        
        return self.structured_logger.info(
            f"Completed workflow step: {step_name} ({duration_ms:.2f}ms)",
            context,
            **kwargs,
        )
    
    def log_step_error(
        self,
        step_name: str,
        error: Union[str, Exception],
        duration_ms: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log an error in a workflow step."""
        context = {
            "job_id": self.job_id,
            "step": step_name,
            "event": "step_error",
            "error": str(error),
            "timestamp_ms": int(time.time() * 1000),
        }
        
        if self.user_id:
            context["user_id"] = self.user_id
        
        if duration_ms is not None:
            context["duration_ms"] = duration_ms
        
        if isinstance(error, Exception):
            context["error_type"] = error.__class__.__name__
        
        return self.structured_logger.error(
            f"Error in workflow step: {step_name} - {str(error)}",
            context,
            **kwargs,
        )
    
    def log_workflow_start(
        self,
        initial_query: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log the start of a workflow."""
        context = {
            "job_id": self.job_id,
            "event": "workflow_start",
            "initial_query": initial_query,
            "timestamp_ms": int(time.time() * 1000),
        }
        
        if self.user_id:
            context["user_id"] = self.user_id
        
        return self.structured_logger.info(
            f"Starting workflow for job {self.job_id}",
            context,
            **kwargs,
        )
    
    def log_workflow_end(
        self,
        duration_ms: float,
        status: str = "completed",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log the successful completion of a workflow."""
        context = {
            "job_id": self.job_id,
            "event": "workflow_end",
            "status": status,
            "duration_ms": duration_ms,
            "timestamp_ms": int(time.time() * 1000),
        }
        
        if self.user_id:
            context["user_id"] = self.user_id
        
        return self.structured_logger.info(
            f"Workflow {status} for job {self.job_id} ({duration_ms:.2f}ms)",
            context,
            **kwargs,
        )
    
    def log_langsmith_run(
        self,
        run_id: str,
        step_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Log a LangSmith run ID for tracing."""
        context = {
            "job_id": self.job_id,
            "step": step_name,
            "event": "langsmith_run",
            "langsmith_run_id": run_id,
            "timestamp_ms": int(time.time() * 1000),
        }
        
        if self.user_id:
            context["user_id"] = self.user_id
        
        return self.structured_logger.info(
            f"LangSmith run {run_id} for step {step_name}",
            context,
            **kwargs,
        )
