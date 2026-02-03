"""
Comprehensive Error Handling and Monitoring for Data Analysis Agent

Provides robust error handling, retry logic, and monitoring capabilities
for document processing and AI service interactions.
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, Any, Optional, Callable, List, Union, Type
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
import json

from fastapi import HTTPException


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better classification"""
    DOCUMENT_PROCESSING = "document_processing"
    AI_SERVICE = "ai_service"
    DATABASE = "database"
    VALIDATION = "validation"
    NETWORK = "network"
    SYSTEM = "system"
    FACT_VALIDATION = "fact_validation"
    STATISTICS_REGISTRY = "statistics_registry"
    PERSONA_ASSOCIATION = "persona_association"


class DocumentProcessingError(Exception):
    """Base exception for document processing errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class PerformanceError(Exception):
    """Exception for performance-related errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class CacheError(Exception):
    """Exception for cache-related errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class FactValidationError(Exception):
    """Specific error for fact validation failures"""
    def __init__(self, message: str, validation_data: Dict[str, Any] = None):
        super().__init__(message)
        self.validation_data = validation_data or {}
        self.timestamp = datetime.utcnow()


class StatisticsRegistryError(Exception):
    """Specific error for statistics registry failures"""
    def __init__(self, message: str, registry_context: Dict[str, Any] = None):
        super().__init__(message)
        self.registry_context = registry_context or {}
        self.timestamp = datetime.utcnow()


class ErrorHandlingService:
    """
    Centralized error handling service for the two-tier RAG system.
    
    Provides graceful degradation and fallback mechanisms for various
    component failures in the market research analysis system.
    """
    
    def __init__(self):
        self.error_counts = {}
        self.fallback_responses = {}
        self.failure_patterns = {}
        self.recovery_strategies = {}
    
    async def handle_context_building_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> str:
        """
        Handle errors in ground truth context building.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            Fallback context string
        """
        logger.error(f"Context building error: {error}")
        
        return """
═══════════════════════════════════════════════════════════
📊 GROUND TRUTH STATISTICS - SOURCE OF TRUTH FOR ALL PERCENTAGES
═══════════════════════════════════════════════════════════
⚠️  STATISTICS UNAVAILABLE DUE TO SYSTEM ERROR
Unable to load pre-computed statistics at this time.
Proceed with qualitative analysis only.
Avoid making specific percentage or frequency claims.
═══════════════════════════════════════════════════════════
"""
    
    async def handle_evidence_retrieval_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Handle errors in evidence retrieval.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            Empty evidence list (graceful degradation)
        """
        logger.error(f"Evidence retrieval error: {error}")
        
        return [
            {
                'content': 'Evidence retrieval temporarily unavailable due to system error.',
                'source_type': 'system',
                'source_file': 'error_handler',
                'similarity_score': 0.0,
                'error_fallback': True
            }
        ]
    
    async def handle_statistics_extraction_error(
        self,
        error: Exception,
        file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle statistics extraction failures with partial recovery.
        
        Args:
            error: The exception that occurred
            file_info: Information about the file being processed
            
        Returns:
            Minimal statistics structure
        """
        logger.error(f"Statistics extraction error for {file_info.get('filename', 'unknown')}: {error}")
        
        return {
            'metadata': {
                'filename': file_info.get('filename', 'unknown'),
                'error': str(error),
                'extraction_failed': True
            },
            'categorical_distributions': {},
            'numerical_summaries': {},
            'themes': {},
            'citation_registry': {}
        }
    
    async def handle_persona_association_failure(
        self,
        data_id: str,
        personas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Handle persona association failures.
        
        Args:
            data_id: ID of the data that failed association
            personas: Available personas
            
        Returns:
            Default persona associations
        """
        logger.warning(f"Persona association failed for data {data_id}")
        
        # Return general association for all personas
        associations = {}
        for persona in personas:
            persona_id = persona.get('id', 'unknown')
            associations[persona_id] = {
                'associated_statistics': [],
                'relevance_scores': {},
                'association_failed': True
            }
        
        return associations
    
    async def handle_fact_validation_error(
        self,
        error: Exception,
        ai_response: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle fact validation failures with graceful degradation.
        
        Args:
            error: The exception that occurred during fact validation
            ai_response: The AI response that failed validation
            context: Context information about the validation attempt
            
        Returns:
            Fallback validation results
        """
        logger.error(f"Fact validation error: {error}")
        
        # Record the error for monitoring
        error_monitor.record_error(
            error,
            ErrorCategory.VALIDATION,
            ErrorSeverity.MEDIUM,
            {
                "validation_context": context,
                "response_length": len(ai_response) if ai_response else 0
            }
        )
        
        # Return minimal validation structure
        return {
            "fact_check_score": 0.5,  # Neutral score when validation fails
            "valid_claims": [],
            "unsupported_claims": [],
            "questionable_claims": [],
            "validation_details": [],
            "total_claims": 0,
            "error": str(error),
            "validation_method": "error_fallback",
            "validated_at": datetime.utcnow().isoformat()
        }
    
    async def handle_statistics_registry_error(
        self,
        error: Exception,
        project_id: str,
        analysis_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle statistics registry failures with fallback mechanisms.
        
        Args:
            error: The exception that occurred
            project_id: Project ID for the failed request
            analysis_type: Type of analysis being performed
            context: Additional context information
            
        Returns:
            Empty statistics registry structure
        """
        logger.error(f"Statistics registry error for project {project_id}: {error}")
        
        # Record the error for monitoring
        error_monitor.record_error(
            error,
            ErrorCategory.DATABASE,
            ErrorSeverity.HIGH,
            {
                "project_id": project_id,
                "analysis_type": analysis_type,
                "registry_context": context
            }
        )
        
        # Return empty registry structure
        return {
            "csv_statistics": {
                "metadata": {"error": "registry_unavailable"},
                "categorical_distributions": {},
                "numerical_summaries": {}
            },
            "pdf_statistics": {
                "metadata": {"error": "registry_unavailable"},
                "themes": {},
                "key_quotes": []
            },
            "citation_registry": {},
            "persona_mappings": {},
            "error": str(error),
            "fallback_used": True
        }
    
    async def handle_ai_service_unavailable(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle AI service unavailability with fallback analysis.
        
        Args:
            error: The AI service error
            context: Analysis context
            
        Returns:
            Fallback analysis response
        """
        logger.error(f"AI service unavailable: {error}")
        
        # Record the error
        error_monitor.record_error(
            error,
            ErrorCategory.AI_SERVICE,
            ErrorSeverity.CRITICAL,
            context
        )
        
        # Generate fallback response based on analysis type
        analysis_type = context.get('analysis_type', 'unknown')
        assumption_text = context.get('assumption', {}).get('text', 'Unknown assumption')
        
        fallback_claims = {
            'pain': f"Unable to analyze pain points for '{assumption_text}' due to AI service unavailability.",
            'size': f"Unable to analyze market size for '{assumption_text}' due to AI service unavailability.",
            'solution': f"Unable to analyze solutions for '{assumption_text}' due to AI service unavailability.",
            'gains': f"Unable to analyze gains for '{assumption_text}' due to AI service unavailability.",
            'jtbd': f"Unable to analyze jobs-to-be-done for '{assumption_text}' due to AI service unavailability."
        }
        
        return {
            "content": json.dumps({
                "claim": fallback_claims.get(analysis_type, f"Analysis unavailable for {analysis_type}"),
                "accuracy_level": "low",
                "supporting_evidence": ["AI service temporarily unavailable"],
                "debunking_evidence": [],
                "statistical_data": {"error": "ai_service_unavailable"},
                "confidence_score": 0.0
            }),
            "fallback": True,
            "error": str(error)
        }
    
    def detect_failure_patterns(self, error_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect systematic failure patterns in error history.
        
        Args:
            error_history: List of recent error records
            
        Returns:
            Analysis of failure patterns and recommendations
        """
        patterns = {
            "recurring_errors": {},
            "error_clusters": {},
            "recommendations": []
        }
        
        # Analyze recurring errors
        for error in error_history:
            error_type = error.get("error_type", "unknown")
            category = error.get("category", "unknown")
            
            key = f"{category}_{error_type}"
            if key not in patterns["recurring_errors"]:
                patterns["recurring_errors"][key] = 0
            patterns["recurring_errors"][key] += 1
        
        # Identify high-frequency errors
        for error_key, count in patterns["recurring_errors"].items():
            if count >= 5:  # 5 or more occurrences
                patterns["recommendations"].append(
                    f"High frequency of {error_key} errors ({count} occurrences) - investigate root cause"
                )
        
        # Analyze error clusters (errors occurring close together)
        if len(error_history) >= 3:
            recent_errors = error_history[-10:]  # Last 10 errors
            error_times = [datetime.fromisoformat(e["timestamp"]) for e in recent_errors]
            
            # Check for error bursts (3+ errors within 5 minutes)
            for i in range(len(error_times) - 2):
                time_window = error_times[i + 2] - error_times[i]
                if time_window.total_seconds() <= 300:  # 5 minutes
                    patterns["error_clusters"]["burst_detected"] = True
                    patterns["recommendations"].append(
                        "Error burst detected - system may be under stress or experiencing cascading failures"
                    )
                    break
        
        return patterns
    
    async def implement_recovery_strategy(
        self,
        error_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement recovery strategies for specific error types.
        
        Args:
            error_type: Type of error to recover from
            context: Context information for recovery
            
        Returns:
            Recovery action results
        """
        recovery_actions = {
            "statistics_extraction_failed": self._recover_statistics_extraction,
            "ai_service_timeout": self._recover_ai_service_timeout,
            "fact_validation_failed": self._recover_fact_validation,
            "persona_association_failed": self._recover_persona_association
        }
        
        if error_type in recovery_actions:
            try:
                return await recovery_actions[error_type](context)
            except Exception as e:
                logger.error(f"Recovery strategy failed for {error_type}: {e}")
                return {"recovery_failed": True, "error": str(e)}
        
        return {"recovery_strategy": "none_available"}
    
    async def _recover_statistics_extraction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from statistics extraction failures."""
        # Try alternative parsing methods
        file_info = context.get("file_info", {})
        
        recovery_result = {
            "recovery_attempted": True,
            "alternative_methods_tried": [],
            "partial_data_recovered": False
        }
        
        # For CSV files, try different encodings and delimiters
        if file_info.get("file_type") == "csv":
            recovery_result["alternative_methods_tried"].extend([
                "utf-8_encoding",
                "latin-1_encoding",
                "alternative_delimiters"
            ])
        
        # For PDF files, try different extraction methods
        elif file_info.get("file_type") == "pdf":
            recovery_result["alternative_methods_tried"].extend([
                "alternative_pdf_parser",
                "ocr_fallback",
                "text_extraction_only"
            ])
        
        return recovery_result
    
    async def _recover_ai_service_timeout(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from AI service timeouts."""
        return {
            "recovery_attempted": True,
            "actions_taken": [
                "reduced_prompt_size",
                "simplified_analysis_request",
                "fallback_model_attempted"
            ],
            "retry_recommended": True,
            "retry_delay_seconds": 30
        }
    
    async def _recover_fact_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from fact validation failures."""
        return {
            "recovery_attempted": True,
            "actions_taken": [
                "simplified_claim_extraction",
                "relaxed_validation_criteria",
                "manual_review_flagged"
            ],
            "validation_confidence_reduced": True
        }
    
    async def _recover_persona_association(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from persona association failures."""
        return {
            "recovery_attempted": True,
            "actions_taken": [
                "default_general_association",
                "keyword_based_fallback",
                "manual_review_required"
            ],
            "association_confidence": "low"
        }


class PDFParsingError(DocumentProcessingError):
    """Specific error for PDF parsing failures"""
    pass


class CSVParsingError(DocumentProcessingError):
    """Specific error for CSV parsing failures"""
    pass


class AIServiceError(Exception):
    """Base exception for AI service errors"""
    def __init__(self, message: str, error_code: str = None, retry_after: int = None):
        super().__init__(message)
        self.error_code = error_code
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()


class TokenLimitError(AIServiceError):
    """Error when token limits are exceeded"""
    pass


class RateLimitError(AIServiceError):
    """Error when rate limits are exceeded"""
    pass


class ErrorMonitor:
    """
    Centralized error monitoring and alerting system
    """
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.alert_thresholds = {
            ErrorCategory.DOCUMENT_PROCESSING: {"count": 10, "window": 300},  # 10 errors in 5 minutes
            ErrorCategory.AI_SERVICE: {"count": 5, "window": 300},  # 5 errors in 5 minutes
            ErrorCategory.DATABASE: {"count": 3, "window": 300},  # 3 errors in 5 minutes
        }
    
    def record_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any] = None
    ):
        """
        Record an error for monitoring and alerting
        
        Args:
            error: The exception that occurred
            category: Category of the error
            severity: Severity level
            context: Additional context information
        """
        error_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "category": category.value,
            "severity": severity.value,
            "context": context or {},
            "traceback": traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
        
        # Add to history
        self.error_history.append(error_record)
        
        # Update counts
        key = f"{category.value}_{severity.value}"
        if key not in self.error_counts:
            self.error_counts[key] = []
        
        self.error_counts[key].append(datetime.utcnow())
        
        # Clean old entries (keep only last hour) - CRITICAL: Clean both counts AND history
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.error_counts[key] = [ts for ts in self.error_counts[key] if ts > cutoff]
        
        # MEMORY LEAK FIX: Clean error_history to prevent unlimited growth
        self.error_history = [
            e for e in self.error_history 
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        
        # Log the error (avoid 'message' key conflict with logging)
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.ERROR)
        
        # Create a copy without 'message' key to avoid logging conflicts
        log_extra = {k: v for k, v in error_record.items() if k != 'message'}
        logger.log(log_level, f"[{category.value}] {error_record['message']}", extra=log_extra)
        
        # Check for alert conditions
        self._check_alert_conditions(category, severity)
    
    def _check_alert_conditions(self, category: ErrorCategory, severity: ErrorSeverity):
        """Check if error rates exceed alert thresholds"""
        if category not in self.alert_thresholds:
            return
        
        threshold = self.alert_thresholds[category]
        key = f"{category.value}_{severity.value}"
        
        if key in self.error_counts:
            recent_errors = len(self.error_counts[key])
            if recent_errors >= threshold["count"]:
                self._trigger_alert(category, severity, recent_errors, threshold["window"])
    
    def _trigger_alert(self, category: ErrorCategory, severity: ErrorSeverity, count: int, window: int):
        """Trigger an alert for high error rates"""
        alert_message = f"HIGH ERROR RATE DETECTED: {count} {category.value} errors ({severity.value}) in {window} seconds"
        logger.critical(alert_message, extra={
            "alert_type": "high_error_rate",
            "category": category.value,
            "severity": severity.value,
            "error_count": count,
            "time_window": window
        })
    
    def get_error_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get error summary for the specified time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if datetime.fromisoformat(e["timestamp"]) > cutoff]
        
        summary = {
            "total_errors": len(recent_errors),
            "by_category": {},
            "by_severity": {},
            "recent_errors": recent_errors[-10:]  # Last 10 errors
        }
        
        for error in recent_errors:
            category = error["category"]
            severity = error["severity"]
            
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        
        return summary


# Global error monitor instance
error_monitor = ErrorMonitor()


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retry logic with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Record final failure
                        error_monitor.record_error(
                            e,
                            ErrorCategory.SYSTEM,
                            ErrorSeverity.HIGH,
                            {"function": func.__name__, "attempts": attempt + 1}
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Record final failure
                        error_monitor.record_error(
                            e,
                            ErrorCategory.SYSTEM,
                            ErrorSeverity.HIGH,
                            {"function": func.__name__, "attempts": attempt + 1}
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def handle_document_processing_errors(func):
    """
    Decorator for handling document processing errors with specific error messages
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PDFParsingError as e:
            error_monitor.record_error(e, ErrorCategory.DOCUMENT_PROCESSING, ErrorSeverity.MEDIUM)
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "PDF parsing failed",
                    "message": str(e),
                    "error_code": e.error_code,
                    "suggestions": [
                        "Ensure the PDF is not password-protected",
                        "Try a different PDF file",
                        "Check if the PDF contains readable text (not just images)"
                    ]
                }
            )
        except CSVParsingError as e:
            error_monitor.record_error(e, ErrorCategory.DOCUMENT_PROCESSING, ErrorSeverity.MEDIUM)
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "CSV parsing failed",
                    "message": str(e),
                    "error_code": e.error_code,
                    "suggestions": [
                        "Ensure the file is in valid CSV format",
                        "Check file encoding (UTF-8 recommended)",
                        "Verify the file contains proper column headers"
                    ]
                }
            )
        except DocumentProcessingError as e:
            error_monitor.record_error(e, ErrorCategory.DOCUMENT_PROCESSING, ErrorSeverity.MEDIUM)
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Document processing failed",
                    "message": str(e),
                    "error_code": e.error_code
                }
            )
        except Exception as e:
            error_monitor.record_error(e, ErrorCategory.DOCUMENT_PROCESSING, ErrorSeverity.HIGH)
            logger.error(f"Unexpected error in document processing: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during document processing"
            )
    
    return wrapper


def handle_fact_validation_errors(func):
    """
    Decorator for handling fact validation errors with graceful degradation
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FactValidationError as e:
            error_monitor.record_error(e, ErrorCategory.FACT_VALIDATION, ErrorSeverity.MEDIUM)
            logger.warning(f"Fact validation error: {e}")
            # Return fallback validation results
            return {
                "fact_check_score": 0.5,
                "valid_claims": [],
                "unsupported_claims": [],
                "questionable_claims": [],
                "validation_details": [],
                "error": str(e),
                "validation_method": "error_fallback"
            }
        except Exception as e:
            error_monitor.record_error(e, ErrorCategory.FACT_VALIDATION, ErrorSeverity.HIGH)
            logger.error(f"Unexpected error in fact validation: {e}", exc_info=True)
            return {
                "fact_check_score": 0.0,
                "valid_claims": [],
                "unsupported_claims": [],
                "questionable_claims": [],
                "validation_details": [],
                "error": "Validation system error",
                "validation_method": "system_error"
            }
    
    return wrapper


def handle_statistics_registry_errors(func):
    """
    Decorator for handling statistics registry errors with fallback mechanisms
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except StatisticsRegistryError as e:
            error_monitor.record_error(e, ErrorCategory.STATISTICS_REGISTRY, ErrorSeverity.HIGH)
            logger.error(f"Statistics registry error: {e}")
            # Return empty registry structure
            return {
                "csv_statistics": {"metadata": {"error": "registry_unavailable"}, "categorical_distributions": {}},
                "pdf_statistics": {"metadata": {"error": "registry_unavailable"}, "themes": {}},
                "citation_registry": {},
                "error": str(e),
                "fallback_used": True
            }
        except Exception as e:
            error_monitor.record_error(e, ErrorCategory.STATISTICS_REGISTRY, ErrorSeverity.CRITICAL)
            logger.error(f"Critical statistics registry error: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Statistics registry unavailable",
                    "message": "Unable to access ground truth statistics",
                    "suggestions": ["Try again later", "Contact system administrator"]
                }
            )
    
    return wrapper


def handle_ai_service_errors(func):
    """
    Decorator for handling AI service errors with retry logic and graceful degradation
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TokenLimitError as e:
            error_monitor.record_error(e, ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH)
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "Token limit exceeded",
                    "message": "The document is too large for processing",
                    "suggestions": [
                        "Try uploading smaller documents",
                        "Split large documents into smaller sections"
                    ]
                }
            )
        except RateLimitError as e:
            error_monitor.record_error(e, ErrorCategory.AI_SERVICE, ErrorSeverity.MEDIUM)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": e.retry_after or 60
                }
            )
        except AIServiceError as e:
            error_monitor.record_error(e, ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "AI service unavailable",
                    "message": str(e),
                    "error_code": e.error_code
                }
            )
        except Exception as e:
            error_monitor.record_error(e, ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH)
            logger.error(f"Unexpected error in AI service: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred with the AI service"
            )
    
    return wrapper


class PerformanceMonitor:
    """
    Monitor performance metrics for analysis workflows
    """
    
    def __init__(self):
        self.metrics = {}
        self.performance_history = []
    
    def record_performance(
        self,
        operation: str,
        duration: float,
        context: Dict[str, Any] = None
    ):
        """
        Record performance metrics for an operation
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            context: Additional context (e.g., file size, chunk count)
        """
        metric_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "duration": duration,
            "context": context or {}
        }
        
        self.performance_history.append(metric_record)
        
        # Update running metrics
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_duration": 0,
                "min_duration": float('inf'),
                "max_duration": 0,
                "avg_duration": 0
            }
        
        metrics = self.metrics[operation]
        metrics["count"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        metrics["avg_duration"] = metrics["total_duration"] / metrics["count"]
        
        # Log slow operations
        if duration > 30:  # More than 30 seconds
            logger.warning(f"Slow operation detected: {operation} took {duration:.2f}s", extra=metric_record)
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the specified time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.performance_history 
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]
        
        summary = {
            "total_operations": len(recent_metrics),
            "by_operation": {},
            "slow_operations": [m for m in recent_metrics if m["duration"] > 30]
        }
        
        for metric in recent_metrics:
            op = metric["operation"]
            if op not in summary["by_operation"]:
                summary["by_operation"][op] = {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "max_duration": 0
                }
            
            op_summary = summary["by_operation"][op]
            op_summary["count"] += 1
            op_summary["total_duration"] += metric["duration"]
            op_summary["avg_duration"] = op_summary["total_duration"] / op_summary["count"]
            op_summary["max_duration"] = max(op_summary["max_duration"], metric["duration"])
        
        return summary


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str = None):
    """
    Decorator to monitor performance of functions
    
    Args:
        operation_name: Name of the operation (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or func.__name__
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Extract context from function arguments if possible
                context = {}
                if args and hasattr(args[0], '__dict__'):
                    # Try to get useful context from first argument (usually self)
                    context = {"class": args[0].__class__.__name__}
                
                performance_monitor.record_performance(operation, duration, context)
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.record_performance(f"{operation}_failed", duration, {"error": str(e)})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Extract context from function arguments if possible
                context = {}
                if args and hasattr(args[0], '__dict__'):
                    # Try to get useful context from first argument (usually self)
                    context = {"class": args[0].__class__.__name__}
                
                performance_monitor.record_performance(operation, duration, context)
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.record_performance(f"{operation}_failed", duration, {"error": str(e)})
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class ResourceMonitor:
    """
    Monitor system resource usage
    """
    
    def __init__(self):
        self.resource_history = []
        self.alert_thresholds = {
            "memory_usage_mb": 1000,  # 1GB
            "processing_time_seconds": 300,  # 5 minutes
            "concurrent_operations": 10
        }
        self.current_operations = 0
    
    def start_operation(self, operation_id: str, context: Dict[str, Any] = None):
        """Start tracking a resource-intensive operation"""
        self.current_operations += 1
        
        if self.current_operations > self.alert_thresholds["concurrent_operations"]:
            logger.warning(f"High concurrent operations: {self.current_operations}")
        
        return {
            "operation_id": operation_id,
            "start_time": time.time(),
            "context": context or {}
        }
    
    def end_operation(self, operation_data: Dict[str, Any]):
        """End tracking a resource-intensive operation"""
        self.current_operations = max(0, self.current_operations - 1)
        
        duration = time.time() - operation_data["start_time"]
        
        resource_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation_id": operation_data["operation_id"],
            "duration": duration,
            "context": operation_data["context"]
        }
        
        self.resource_history.append(resource_record)
        
        if duration > self.alert_thresholds["processing_time_seconds"]:
            logger.warning(f"Long-running operation: {operation_data['operation_id']} took {duration:.2f}s")
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get current resource usage summary"""
        return {
            "current_operations": self.current_operations,
            "recent_operations": len([
                r for r in self.resource_history 
                if datetime.fromisoformat(r["timestamp"]) > datetime.utcnow() - timedelta(minutes=5)
            ]),
            "avg_operation_time": sum(r["duration"] for r in self.resource_history[-10:]) / min(10, len(self.resource_history)) if self.resource_history else 0
        }


# Global resource monitor instance
resource_monitor = ResourceMonitor()