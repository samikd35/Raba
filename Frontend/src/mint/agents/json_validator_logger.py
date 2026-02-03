"""
JSON Validator Logger.

This module provides comprehensive logging capabilities for the JSON validation system,
including detailed error logging, repair attempt tracking, retry monitoring, and
notification for persistent failures.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from collections import defaultdict, Counter

from ..utils.logging import StructLogger
from ..api.services.communication.notification_service import notification_manager, NotificationLevel
from ..api.services.communication.email_service import email_service

# Configure basic logging
logger = logging.getLogger(__name__)

class JSONValidationMetrics:
    """
    Class for tracking JSON validation metrics.
    
    This class maintains counters and statistics for JSON validation operations,
    including success rates, repair attempts, and retry counts.
    """
    
    def __init__(self):
        """Initialize the metrics tracker."""
        # Reset metrics
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        # Total validation attempts
        self.total_validations = 0
        
        # Success/failure counts
        self.successful_validations = 0
        self.failed_validations = 0
        
        # Repair attempts
        self.repair_attempts = 0
        self.successful_repairs = 0
        
        # Retry counts
        self.retry_attempts = 0
        self.successful_retries = 0
        
        # Fallback counts
        self.fallback_responses = 0
        
        # Error types
        self.error_types = Counter()
        
        # Agent-specific metrics
        self.agent_metrics = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "repairs": 0,
            "retries": 0,
            "fallbacks": 0
        })
        
        # Time-based metrics
        self.validation_times = []
        self.repair_times = []
        self.retry_times = []
        
        # Persistent failure tracking
        self.persistent_failures = defaultdict(int)
    
    def record_validation_attempt(self, agent_type: str, success: bool, duration_ms: float):
        """
        Record a validation attempt.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            success: Whether the validation was successful
            duration_ms: The duration of the validation in milliseconds
        """
        self.total_validations += 1
        self.validation_times.append(duration_ms)
        
        if success:
            self.successful_validations += 1
        else:
            self.failed_validations += 1
        
        # Update agent-specific metrics
        self.agent_metrics[agent_type]["total"] += 1
        if success:
            self.agent_metrics[agent_type]["success"] += 1
        else:
            self.agent_metrics[agent_type]["failure"] += 1
    
    def record_repair_attempt(self, agent_type: str, success: bool, duration_ms: float):
        """
        Record a repair attempt.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            success: Whether the repair was successful
            duration_ms: The duration of the repair in milliseconds
        """
        self.repair_attempts += 1
        self.repair_times.append(duration_ms)
        
        if success:
            self.successful_repairs += 1
        
        # Update agent-specific metrics
        self.agent_metrics[agent_type]["repairs"] += 1
    
    def record_retry_attempt(self, agent_type: str, success: bool, duration_ms: float):
        """
        Record a retry attempt.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            success: Whether the retry was successful
            duration_ms: The duration of the retry in milliseconds
        """
        self.retry_attempts += 1
        self.retry_times.append(duration_ms)
        
        if success:
            self.successful_retries += 1
        
        # Update agent-specific metrics
        self.agent_metrics[agent_type]["retries"] += 1
    
    def record_fallback(self, agent_type: str):
        """
        Record a fallback response.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
        """
        self.fallback_responses += 1
        
        # Update agent-specific metrics
        self.agent_metrics[agent_type]["fallbacks"] += 1
    
    def record_error(self, error_type: str, agent_type: str):
        """
        Record an error.
        
        Args:
            error_type: The type of error (e.g., "JSONDecodeError", "ValidationError")
            agent_type: The type of agent (e.g., "industry", "pestel")
        """
        self.error_types[error_type] += 1
        
        # Track persistent failures
        key = f"{agent_type}:{error_type}"
        self.persistent_failures[key] += 1
    
    def get_success_rate(self) -> float:
        """
        Get the overall success rate.
        
        Returns:
            The success rate as a percentage (0-100)
        """
        if self.total_validations == 0:
            return 100.0
        
        return (self.successful_validations / self.total_validations) * 100
    
    def get_repair_success_rate(self) -> float:
        """
        Get the repair success rate.
        
        Returns:
            The repair success rate as a percentage (0-100)
        """
        if self.repair_attempts == 0:
            return 100.0
        
        return (self.successful_repairs / self.repair_attempts) * 100
    
    def get_retry_success_rate(self) -> float:
        """
        Get the retry success rate.
        
        Returns:
            The retry success rate as a percentage (0-100)
        """
        if self.retry_attempts == 0:
            return 100.0
        
        return (self.successful_retries / self.retry_attempts) * 100
    
    def get_average_validation_time(self) -> float:
        """
        Get the average validation time.
        
        Returns:
            The average validation time in milliseconds
        """
        if not self.validation_times:
            return 0.0
        
        return sum(self.validation_times) / len(self.validation_times)
    
    def get_average_repair_time(self) -> float:
        """
        Get the average repair time.
        
        Returns:
            The average repair time in milliseconds
        """
        if not self.repair_times:
            return 0.0
        
        return sum(self.repair_times) / len(self.repair_times)
    
    def get_average_retry_time(self) -> float:
        """
        Get the average retry time.
        
        Returns:
            The average retry time in milliseconds
        """
        if not self.retry_times:
            return 0.0
        
        return sum(self.retry_times) / len(self.retry_times)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            A dictionary containing all metrics
        """
        return {
            "total_validations": self.total_validations,
            "successful_validations": self.successful_validations,
            "failed_validations": self.failed_validations,
            "success_rate": self.get_success_rate(),
            "repair_attempts": self.repair_attempts,
            "successful_repairs": self.successful_repairs,
            "repair_success_rate": self.get_repair_success_rate(),
            "retry_attempts": self.retry_attempts,
            "successful_retries": self.successful_retries,
            "retry_success_rate": self.get_retry_success_rate(),
            "fallback_responses": self.fallback_responses,
            "error_types": dict(self.error_types),
            "agent_metrics": dict(self.agent_metrics),
            "average_validation_time_ms": self.get_average_validation_time(),
            "average_repair_time_ms": self.get_average_repair_time(),
            "average_retry_time_ms": self.get_average_retry_time(),
            "persistent_failures": dict(self.persistent_failures)
        }
    
    def check_persistent_failures(self, threshold: int = 5) -> List[Tuple[str, int]]:
        """
        Check for persistent failures that exceed a threshold.
        
        Args:
            threshold: The threshold for persistent failures
            
        Returns:
            A list of (failure_key, count) tuples for failures that exceed the threshold
        """
        return [(key, count) for key, count in self.persistent_failures.items() if count >= threshold]


class JSONValidatorLogger:
    """
    Logger for JSON validation operations.
    
    This class provides comprehensive logging for JSON validation operations,
    including detailed error logging, repair attempt tracking, retry monitoring,
    and notification for persistent failures.
    """
    
    def __init__(
        self,
        service_name: str = "json_validator",
        notification_threshold: int = 5,
        admin_emails: Optional[List[str]] = None
    ):
        """
        Initialize the JSON validator logger.
        
        Args:
            service_name: The name of the service for logging
            notification_threshold: The threshold for persistent failures before sending notifications
            admin_emails: List of admin email addresses for notifications
        """
        self.service_name = service_name
        self.notification_threshold = notification_threshold
        self.admin_emails = admin_emails or []
        
        # Create structured logger
        self.logger = StructLogger(
            service_name=service_name,
            level=logging.INFO,
            log_to_console=True,
            log_to_file=True,
            log_file=f"logs/{service_name}.log"
        )
        
        # Initialize metrics tracker
        self.metrics = JSONValidationMetrics()
    
    def log_validation_attempt(
        self,
        agent_type: str,
        success: bool,
        duration_ms: float,
        response_text: str,
        error: Optional[Exception] = None
    ):
        """
        Log a validation attempt.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            success: Whether the validation was successful
            duration_ms: The duration of the validation in milliseconds
            response_text: The raw response text
            error: The error that occurred (if any)
        """
        # Update metrics
        self.metrics.record_validation_attempt(agent_type, success, duration_ms)
        
        # Prepare context
        context = {
            "agent_type": agent_type,
            "success": success,
            "duration_ms": duration_ms,
            "response_length": len(response_text),
            "response_preview": response_text[:100] + "..." if len(response_text) > 100 else response_text
        }
        
        # Add error information if present
        if error:
            error_type = error.__class__.__name__
            context["error_type"] = error_type
            context["error_message"] = str(error)
            
            # Record error in metrics
            self.metrics.record_error(error_type, agent_type)
            
            # Log error
            self.logger.error(
                f"JSON validation failed for {agent_type} agent: {error_type} - {str(error)}",
                context=context
            )
            
            # Check for persistent failures
            self._check_and_notify_persistent_failures()
        else:
            # Log success
            self.logger.info(
                f"JSON validation successful for {agent_type} agent",
                context=context
            )
    
    def log_repair_attempt(
        self,
        agent_type: str,
        success: bool,
        duration_ms: float,
        original_text: str,
        repaired_text: str,
        error: Optional[Exception] = None
    ):
        """
        Log a repair attempt.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            success: Whether the repair was successful
            duration_ms: The duration of the repair in milliseconds
            original_text: The original response text
            repaired_text: The repaired response text
            error: The error that occurred (if any)
        """
        # Update metrics
        self.metrics.record_repair_attempt(agent_type, success, duration_ms)
        
        # Prepare context
        context = {
            "agent_type": agent_type,
            "success": success,
            "duration_ms": duration_ms,
            "original_length": len(original_text),
            "repaired_length": len(repaired_text),
            "original_preview": original_text[:100] + "..." if len(original_text) > 100 else original_text,
            "repaired_preview": repaired_text[:100] + "..." if len(repaired_text) > 100 else repaired_text
        }
        
        # Add error information if present
        if error:
            error_type = error.__class__.__name__
            context["error_type"] = error_type
            context["error_message"] = str(error)
            
            # Record error in metrics
            self.metrics.record_error(error_type, agent_type)
            
            # Log error
            self.logger.error(
                f"JSON repair failed for {agent_type} agent: {error_type} - {str(error)}",
                context=context
            )
        else:
            # Log success
            self.logger.info(
                f"JSON repair {'successful' if success else 'failed'} for {agent_type} agent",
                context=context
            )
    
    def log_retry_attempt(
        self,
        agent_type: str,
        attempt_number: int,
        max_retries: int,
        success: bool,
        duration_ms: float,
        error: Optional[Exception] = None
    ):
        """
        Log a retry attempt.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            attempt_number: The current attempt number
            max_retries: The maximum number of retries
            success: Whether the retry was successful
            duration_ms: The duration of the retry in milliseconds
            error: The error that occurred (if any)
        """
        # Update metrics
        self.metrics.record_retry_attempt(agent_type, success, duration_ms)
        
        # Prepare context
        context = {
            "agent_type": agent_type,
            "attempt_number": attempt_number,
            "max_retries": max_retries,
            "success": success,
            "duration_ms": duration_ms
        }
        
        # Add error information if present
        if error:
            error_type = error.__class__.__name__
            context["error_type"] = error_type
            context["error_message"] = str(error)
            
            # Record error in metrics
            self.metrics.record_error(error_type, agent_type)
            
            # Log error
            self.logger.error(
                f"JSON retry {attempt_number}/{max_retries} failed for {agent_type} agent: {error_type} - {str(error)}",
                context=context
            )
            
            # Check if this is the last retry
            if attempt_number >= max_retries:
                self.logger.critical(
                    f"All retry attempts failed for {agent_type} agent",
                    context=context
                )
                
                # Record fallback
                self.metrics.record_fallback(agent_type)
                
                # Send notification for max retries reached
                self._notify_max_retries_reached(agent_type, max_retries, error)
        else:
            # Log success
            self.logger.info(
                f"JSON retry {attempt_number}/{max_retries} {'successful' if success else 'failed'} for {agent_type} agent",
                context=context
            )
    
    def log_fallback_response(
        self,
        agent_type: str,
        fallback_response: Dict[str, Any]
    ):
        """
        Log a fallback response.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            fallback_response: The fallback response
        """
        # Update metrics
        self.metrics.record_fallback(agent_type)
        
        # Prepare context
        context = {
            "agent_type": agent_type,
            "fallback_response": fallback_response
        }
        
        # Log fallback
        self.logger.warning(
            f"Using fallback response for {agent_type} agent",
            context=context
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            A dictionary containing all metrics
        """
        return self.metrics.get_metrics_summary()
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics.reset()
    
    def _check_and_notify_persistent_failures(self):
        """Check for persistent failures and send notifications if needed."""
        persistent_failures = self.metrics.check_persistent_failures(self.notification_threshold)
        
        for failure_key, count in persistent_failures:
            agent_type, error_type = failure_key.split(":")
            
            # Log persistent failure
            self.logger.critical(
                f"Persistent failure detected: {error_type} in {agent_type} agent ({count} occurrences)",
                context={
                    "agent_type": agent_type,
                    "error_type": error_type,
                    "count": count
                }
            )
            
            # Send notification
            self._notify_persistent_failure(agent_type, error_type, count)
    
    def _notify_persistent_failure(self, agent_type: str, error_type: str, count: int):
        """
        Send notification for persistent failure.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            error_type: The type of error
            count: The number of occurrences
        """
        # Create notification message
        title = f"Persistent JSON Validation Failure: {error_type}"
        message = (
            f"The {agent_type} agent has experienced {count} {error_type} errors. "
            f"This may indicate a systematic issue with the JSON validation system."
        )
        
        # Send notification to admin users
        try:
            notification_manager.broadcast_admin_notification({
                "type": "system_alert",
                "level": NotificationLevel.ERROR,
                "title": title,
                "message": message,
                "source": "json_validator",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "agent_type": agent_type,
                    "error_type": error_type,
                    "count": count
                }
            })
            
            logger.info(f"Sent admin notification for persistent failure: {error_type} in {agent_type} agent")
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")
        
        # Send email to admin users
        for admin_email in self.admin_emails:
            try:
                html_content = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #e24a4a; color: white; padding: 10px 20px; text-align: center; }}
                        .content {{ padding: 20px; }}
                        .details {{ background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>JSON Validation System Alert</h1>
                        </div>
                        <div class="content">
                            <p>Hello,</p>
                            <p>The JSON validation system has detected a persistent failure:</p>
                            <div class="details">
                                <p><strong>Agent Type:</strong> {agent_type}</p>
                                <p><strong>Error Type:</strong> {error_type}</p>
                                <p><strong>Occurrences:</strong> {count}</p>
                                <p><strong>Timestamp:</strong> {datetime.now().isoformat()}</p>
                            </div>
                            <p>This may indicate a systematic issue with the JSON validation system that requires attention.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message from the JSON validation system.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                text_content = f"""
                JSON Validation System Alert

                Hello,

                The JSON validation system has detected a persistent failure:

                Agent Type: {agent_type}
                Error Type: {error_type}
                Occurrences: {count}
                Timestamp: {datetime.now().isoformat()}

                This may indicate a systematic issue with the JSON validation system that requires attention.

                This is an automated message from the JSON validation system.
                """
                
                email_service.send_email(
                    to_email=admin_email,
                    subject=title,
                    html_content=html_content,
                    text_content=text_content
                )
                
                logger.info(f"Sent email notification to {admin_email} for persistent failure")
            except Exception as e:
                logger.error(f"Failed to send email notification to {admin_email}: {str(e)}")
    
    def _notify_max_retries_reached(self, agent_type: str, max_retries: int, error: Exception):
        """
        Send notification for max retries reached.
        
        Args:
            agent_type: The type of agent (e.g., "industry", "pestel")
            max_retries: The maximum number of retries
            error: The error that occurred
        """
        error_type = error.__class__.__name__
        
        # Create notification message
        title = f"JSON Validation Max Retries Reached: {agent_type} Agent"
        message = (
            f"The {agent_type} agent has reached the maximum number of retries ({max_retries}) "
            f"with error: {error_type} - {str(error)}. Using fallback response."
        )
        
        # Send notification to admin users
        try:
            notification_manager.broadcast_admin_notification({
                "type": "system_alert",
                "level": NotificationLevel.WARNING,
                "title": title,
                "message": message,
                "source": "json_validator",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "agent_type": agent_type,
                    "max_retries": max_retries,
                    "error_type": error_type,
                    "error_message": str(error)
                }
            })
            
            logger.info(f"Sent admin notification for max retries reached: {agent_type} agent")
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")


# Create a singleton instance of the JSON validator logger
json_validator_logger = JSONValidatorLogger(
    admin_emails=[
        # Add admin emails here
    ]
)