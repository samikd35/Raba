"""
Comprehensive Logging Configuration for Problem Generator

This module provides structured logging with different levels and formats
for development, testing, and production environments.
"""

import os
import sys
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

class ProblemGeneratorFormatter(logging.Formatter):
    """Custom formatter for Problem Generator logs."""
    
    def __init__(self):
        super().__init__()
        
    def format(self, record):
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()
        
        # Add job_id and user_id if available
        job_id = getattr(record, 'job_id', None)
        user_id = getattr(record, 'user_id', None)
        
        # Get the formatted message
        message = record.getMessage()
        
        # Create formatted output
        if job_id and user_id:
            formatted = f"[{record.timestamp}] {record.levelname} {record.name} [USER:{user_id}|JOB:{job_id}]: {message}"
        elif job_id:
            formatted = f"[{record.timestamp}] {record.levelname} {record.name} [JOB:{job_id}]: {message}"
        elif user_id:
            formatted = f"[{record.timestamp}] {record.levelname} {record.name} [USER:{user_id}]: {message}"
        else:
            formatted = f"[{record.timestamp}] {record.levelname} {record.name}: {message}"
            
        return formatted

def get_logging_config(environment: str = "development") -> Dict[str, Any]:
    """
    Get logging configuration for the specified environment.
    
    Args:
        environment: Environment name (development, testing, production)
        
    Returns:
        Logging configuration dictionary
    """
    
    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "[{asctime}] {levelname} {name} [{process}:{thread}]: {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "[{asctime}] {levelname}: {message}",
                "style": "{",
                "datefmt": "%H:%M:%S"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(job_id)s %(user_id)s"
            },
            "custom": {
                "()": ProblemGeneratorFormatter
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(LOGS_DIR / "pgen.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(LOGS_DIR / "pgen_errors.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "pgen": {
                "level": "DEBUG",
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "pgen.api": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "pgen.agents": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "pgen.services": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "pgen.errors": {
                "level": "ERROR",
                "handlers": ["console", "error_file"],
                "propagate": False
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"]
        }
    }
    
    # Environment-specific adjustments
    if environment == "production":
        # More structured logging for production
        config["handlers"]["console"]["formatter"] = "json"
        config["handlers"]["file"]["formatter"] = "json"
        config["loggers"]["pgen"]["level"] = "INFO"
        config["loggers"]["pgen.agents"]["level"] = "INFO"
        config["loggers"]["pgen.services"]["level"] = "INFO"
        
        # Add performance logging
        config["handlers"]["performance"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": str(LOGS_DIR / "pgen_performance.log"),
            "maxBytes": 10485760,
            "backupCount": 10
        }
        
        config["loggers"]["pgen.performance"] = {
            "level": "INFO",
            "handlers": ["performance"],
            "propagate": False
        }
        
    elif environment == "testing":
        # Minimal logging for tests
        config["handlers"]["console"]["level"] = "WARNING"
        config["loggers"]["pgen"]["level"] = "WARNING"
        
    elif environment == "development":
        # Verbose logging for development
        config["handlers"]["console"]["formatter"] = "custom"
        config["loggers"]["pgen"]["level"] = "DEBUG"
        
        # Add debug file handler
        config["handlers"]["debug_file"] = {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "pgen_debug.log"),
            "mode": "w"  # Overwrite on each run
        }
        
        config["loggers"]["pgen"]["handlers"].append("debug_file")
    
    return config

def setup_logging(environment: str = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        environment: Environment name (auto-detected if None)
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()
    
    config = get_logging_config(environment)
    logging.config.dictConfig(config)
    
    # Log the setup
    logger = logging.getLogger("pgen")
    logger.info(f"Logging configured for {environment} environment")

class ContextualLogger:
    """Logger that automatically includes job_id and user_id context."""
    
    def __init__(self, name: str, job_id: str = None, user_id: str = None):
        self.logger = logging.getLogger(name)
        self.job_id = job_id
        self.user_id = user_id
    
    def _log(self, level: int, message: str, *args, **kwargs):
        """Internal logging method that adds context."""
        extra = kwargs.get('extra', {})
        if self.job_id:
            extra['job_id'] = self.job_id
        if self.user_id:
            extra['user_id'] = self.user_id
        kwargs['extra'] = extra
        
        self.logger.log(level, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        self._log(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self._log(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self._log(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self._log(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        self._log(logging.CRITICAL, message, *args, **kwargs)

def get_contextual_logger(name: str, job_id: str = None, user_id: str = None, session_id: str = None) -> ContextualLogger:
    """
    Get a contextual logger with job_id and user_id context.
    
    Args:
        name: Logger name
        job_id: Job ID for context
        user_id: User ID for context
        session_id: Session ID for context (alias for job_id)
        
    Returns:
        ContextualLogger instance
    """
    # Use session_id as job_id if job_id is not provided but session_id is
    effective_job_id = job_id or session_id
    return ContextualLogger(name, effective_job_id, user_id)

# Performance logging utilities
class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self):
        self.logger = logging.getLogger("pgen.performance")
    
    def log_generation_metrics(
        self,
        job_id: str,
        user_id: str,
        total_time_ms: int,
        problems_generated: int,
        parameters: Dict[str, Any],
        success: bool,
        error: Optional[str] = None
    ):
        """Log problem generation performance metrics."""
        metrics = {
            "event": "problem_generation_completed",
            "job_id": job_id,
            "user_id": user_id,
            "total_time_ms": total_time_ms,
            "problems_generated": problems_generated,
            "success": success,
            "parameters": parameters,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            metrics["error"] = error
            
        self.logger.info("Generation metrics", extra=metrics)
    
    def log_api_metrics(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        user_id: Optional[str] = None
    ):
        """Log API endpoint performance metrics."""
        metrics = {
            "event": "api_request_completed",
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            metrics["user_id"] = user_id
            
        self.logger.info("API metrics", extra=metrics)

# Initialize performance logger
performance_logger = PerformanceLogger()

# Auto-setup logging when module is imported
if not logging.getLogger("pgen").handlers:
    setup_logging()
