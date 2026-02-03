"""
AI Service Wrapper with Enhanced Error Handling and Monitoring

Provides robust AI service integration with retry logic, token monitoring,
rate limiting, and graceful degradation for the Data Analysis Agent.

MIGRATED TO RESPONSES API (Dec 2025):
- Uses generate_responses() for gpt-5-mini
- Leverages reasoning.effort and text.verbosity for grounded output
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import json

from ..utils.error_handling import (
    AIServiceError, TokenLimitError, RateLimitError,
    retry_with_exponential_backoff, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity, resource_monitor
)

# Import the real AI providers used throughout the codebase
from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig, ModelProvider
from src.mint.api.ai.config import get_client_config, ModelUseCase

# Import AI token monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext


logger = logging.getLogger(__name__)


class TokenUsageMonitor:
    """
    Monitor token usage across AI service calls
    """
    
    def __init__(self):
        self.usage_history = []
        self.daily_limits = {
            "gpt-4": 150000,  # Conservative daily limit
            "gpt-3.5-turbo": 1000000,
            "text-embedding-ada-002": 1000000
        }
        self.current_usage = {}
        self.rate_limits = {
            "requests_per_minute": 60,
            "tokens_per_minute": 90000
        }
        self.request_timestamps = []
    
    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int = 0,
        total_tokens: int = None
    ):
        """Record token usage for a model"""
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        
        usage_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
        
        self.usage_history.append(usage_record)
        
        # Update current usage
        today = datetime.utcnow().date().isoformat()
        if today not in self.current_usage:
            self.current_usage[today] = {}
        
        if model not in self.current_usage[today]:
            self.current_usage[today][model] = {
                "requests": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0
            }
        
        self.current_usage[today][model]["requests"] += 1
        self.current_usage[today][model]["total_tokens"] += total_tokens
        self.current_usage[today][model]["prompt_tokens"] += prompt_tokens
        self.current_usage[today][model]["completion_tokens"] += completion_tokens
        
        # Check limits
        self._check_usage_limits(model, today)
    
    def _check_usage_limits(self, model: str, date: str):
        """Check if usage is approaching limits"""
        if model in self.daily_limits:
            current_tokens = self.current_usage[date][model]["total_tokens"]
            limit = self.daily_limits[model]
            
            usage_percentage = (current_tokens / limit) * 100
            
            if usage_percentage > 90:
                logger.critical(f"Token usage critical: {usage_percentage:.1f}% of daily limit for {model}")
                error_monitor.record_error(
                    Exception(f"High token usage: {usage_percentage:.1f}%"),
                    ErrorCategory.AI_SERVICE,
                    ErrorSeverity.CRITICAL,
                    {"model": model, "usage_percentage": usage_percentage}
                )
            elif usage_percentage > 75:
                logger.warning(f"Token usage high: {usage_percentage:.1f}% of daily limit for {model}")
    
    def check_rate_limits(self) -> Optional[int]:
        """Check if we're hitting rate limits. Returns wait time if needed."""
        now = time.time()
        
        # Clean old timestamps (older than 1 minute)
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        
        # Check requests per minute
        if len(self.request_timestamps) >= self.rate_limits["requests_per_minute"]:
            oldest_request = min(self.request_timestamps)
            wait_time = 60 - (now - oldest_request)
            if wait_time > 0:
                return int(wait_time) + 1
        
        return None
    
    def record_request(self):
        """Record a new request timestamp"""
        self.request_timestamps.append(time.time())
    
    def get_usage_summary(self, days: int = 1) -> Dict[str, Any]:
        """Get usage summary for the specified number of days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_usage = [
            u for u in self.usage_history 
            if datetime.fromisoformat(u["timestamp"]) > cutoff
        ]
        
        summary = {
            "total_requests": len(recent_usage),
            "total_tokens": sum(u["total_tokens"] for u in recent_usage),
            "by_model": {}
        }
        
        for usage in recent_usage:
            model = usage["model"]
            if model not in summary["by_model"]:
                summary["by_model"][model] = {
                    "requests": 0,
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }
            
            summary["by_model"][model]["requests"] += 1
            summary["by_model"][model]["total_tokens"] += usage["total_tokens"]
            summary["by_model"][model]["prompt_tokens"] += usage["prompt_tokens"]
            summary["by_model"][model]["completion_tokens"] += usage["completion_tokens"]
        
        return summary


class AIServiceWrapper:
    """
    Wrapper for AI service with enhanced error handling, monitoring, and recovery
    """
    
    def __init__(self):
        # CRITICAL: Use same Azure OpenAI configuration as PV report generator
        # This ensures consistent model usage (GPT-4.1) across all analysis agents
        from src.mint.api.ai.config import get_client_config
        from src.mint.api.ai.models import ModelUseCase
        
        # Get Azure OpenAI config with GPT-4.1 for report generation
        provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
        
        logger.info(f"🔧 MARKET_RESEARCH: Initializing with provider={provider_type}, model={model_name}")
        
        # Create LLM config - gpt-5-mini doesn't support temperature
        is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
        
        config_kwargs = {
            "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
            "model_name": model_name,
            "max_tokens": 4000 if is_gpt5_model else 2000,  # gpt-5-mini needs more tokens
            "azure_endpoint": client_config.get("azure_endpoint"),
            "api_version": client_config.get("api_version"),
            "api_key": client_config.get("api_key")
        }
        
        if not is_gpt5_model:
            config_kwargs["temperature"] = 0.1  # Slightly lower for analysis precision
        
        llm_config = LLMConfig(**config_kwargs)
        
        # Initialize the OpenAI provider (supports both Azure and standard OpenAI)
        self.ai_service = OpenAIProvider(llm_config)
        self.llm_config = llm_config
        
        logger.info(f"✅ MARKET_RESEARCH: AI service initialized with {provider_type} using {model_name}")
        self.token_monitor = TokenUsageMonitor()
        self.circuit_breaker = CircuitBreaker()
        self.fallback_responses = {
            "analysis_failed": "Analysis could not be completed due to service limitations. Please try again later.",
            "partial_analysis": "Partial analysis completed. Some sections may be incomplete due to service constraints."
        }
    
    @monitor_performance("ai_service_call")
    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0,
        exceptions=(AIServiceError, RateLimitError)
    )
    async def generate_analysis_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-5-mini",
        max_tokens: int = None,
        max_completion_tokens: int = 16000,  # Increased for gpt-5-mini which needs more tokens
        temperature: float = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate AI response with comprehensive error handling and monitoring
        
        Args:
            messages: List of message dictionaries
            model: Model to use for generation
            max_tokens: DEPRECATED - use max_completion_tokens instead
            max_completion_tokens: Maximum tokens in response (for gpt-5-mini compatibility)
            temperature: Temperature for generation (not used for gpt-5-mini)
            **kwargs: Additional parameters (including monitoring_context for AI usage tracking)
            
        Returns:
            Dictionary with response content and metadata
            
        Raises:
            AIServiceError: If service fails
            TokenLimitError: If token limits exceeded
            RateLimitError: If rate limits exceeded
        """
        # Handle max_tokens backward compatibility
        if max_tokens is not None and max_completion_tokens == 16000:
            max_completion_tokens = max_tokens
        operation_data = resource_monitor.start_operation(
            f"ai_generation_{model}",
            {"model": model, "max_tokens": max_tokens}
        )
        
        # Extract monitoring context from kwargs (if provided)
        monitoring_context = kwargs.pop('monitoring_context', None)
        
        # Record start time for monitoring
        started_at = datetime.utcnow()
        
        try:
            # Check circuit breaker
            if not self.circuit_breaker.can_proceed():
                raise AIServiceError(
                    "AI service temporarily unavailable due to repeated failures",
                    error_code="CIRCUIT_BREAKER_OPEN"
                )
            
            # Check rate limits
            wait_time = self.token_monitor.check_rate_limits()
            if wait_time:
                logger.warning(f"Rate limit approaching, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
            
            # Record request
            self.token_monitor.record_request()
            
            # Estimate token count for input
            estimated_input_tokens = self._estimate_token_count(messages)
            
            # Check if request would exceed limits
            if estimated_input_tokens > 8000:  # Conservative limit
                raise TokenLimitError(
                    f"Input too large: {estimated_input_tokens} estimated tokens",
                    error_code="INPUT_TOKEN_LIMIT"
                )
            
            # Make AI service call using the OpenAI provider
            try:
                # Convert messages to the format expected by the provider
                formatted_messages = []
                for msg in messages:
                    formatted_messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
                
                # Use the OpenAI provider's generate_responses method for gpt-5-mini
                # The provider uses Responses API with reasoning.effort and text.verbosity
                response = await self.ai_service.generate_responses(
                    formatted_messages,
                    max_output_tokens=max_completion_tokens
                )
                
                # Record successful call
                self.circuit_breaker.record_success()
                
                # Extract and record token usage if available (response is LLMResponse object)
                usage = response.usage or {}
                if usage:
                    self.token_monitor.record_usage(
                        model=model,
                        prompt_tokens=usage.get("prompt_tokens", estimated_input_tokens),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens")
                    )
                
                # Record AI usage in monitoring system (fire-and-forget)
                finished_at = datetime.utcnow()
                if monitoring_context:
                    try:
                        monitoring_service = get_monitoring_service()
                        asyncio.create_task(
                            monitoring_service.record_ai_usage(
                                context=monitoring_context,
                                provider=self.llm_config.provider_name,
                                model_name=response.model or model,
                                operation_type="responses_api",
                                started_at=started_at,
                                finished_at=finished_at,
                                status="success",
                                prompt_tokens=usage.get("prompt_tokens"),
                                completion_tokens=usage.get("completion_tokens"),
                                total_tokens=usage.get("total_tokens")
                            )
                        )
                    except Exception as monitor_error:
                        # Never let monitoring errors affect the main operation
                        logger.warning(f"Failed to record AI usage monitoring: {monitor_error}")
                
                # Validate response content is not empty
                if not response.content:
                    logger.error(f"AI returned empty content. Finish reason: {response.finish_reason}, model: {model}")
                    raise AIServiceError(
                        f"AI returned empty content (finish_reason: {response.finish_reason})",
                        error_code="AI_EMPTY_RESPONSE"
                    )
                
                return {
                    "content": response.content,  # LLMResponse.content
                    "model": response.model,      # LLMResponse.model
                    "usage": usage,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                # Log the actual error for debugging
                logger.error(f"AI service call failed: {type(e).__name__}: {str(e)}")
                
                # Record failure
                self.circuit_breaker.record_failure()
                
                # Record AI usage error in monitoring system (fire-and-forget)
                finished_at = datetime.utcnow()
                if monitoring_context:
                    try:
                        monitoring_service = get_monitoring_service()
                        
                        # Classify error type for monitoring
                        error_msg = str(e).lower()
                        if "rate limit" in error_msg or "too many requests" in error_msg:
                            error_type = "rate_limit"
                        elif "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
                            error_type = "token_limit"
                        elif "timeout" in error_msg or "connection" in error_msg:
                            error_type = "timeout"
                        else:
                            error_type = "provider_error"
                        
                        asyncio.create_task(
                            monitoring_service.record_ai_usage(
                                context=monitoring_context,
                                provider=self.llm_config.provider_name,
                                model_name=model,
                                operation_type="responses_api",
                                started_at=started_at,
                                finished_at=finished_at,
                                status="error",
                                error_type=error_type,
                                prompt_tokens=estimated_input_tokens
                            )
                        )
                    except Exception as monitor_error:
                        # Never let monitoring errors affect the main operation
                        logger.warning(f"Failed to record AI usage error monitoring: {monitor_error}")
                
                # Classify error and raise appropriate exception
                error_msg = str(e).lower()
                
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    retry_after = self._extract_retry_after(str(e))
                    raise RateLimitError(
                        f"Rate limit exceeded: {str(e)}",
                        error_code="AI_RATE_LIMIT",
                        retry_after=retry_after
                    )
                elif "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
                    raise TokenLimitError(
                        f"Token limit exceeded: {str(e)}",
                        error_code="AI_TOKEN_LIMIT"
                    )
                elif "timeout" in error_msg or "connection" in error_msg:
                    raise AIServiceError(
                        f"AI service connection error: {str(e)}",
                        error_code="AI_CONNECTION_ERROR"
                    )
                else:
                    raise AIServiceError(
                        f"AI service error: {str(e)}",
                        error_code="AI_SERVICE_ERROR"
                    )
        
        except (AIServiceError, TokenLimitError, RateLimitError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in AI service wrapper: {e}")
            raise AIServiceError(
                f"Unexpected AI service error: {str(e)}",
                error_code="AI_UNEXPECTED_ERROR"
            )
        finally:
            resource_monitor.end_operation(operation_data)
    
    async def generate_with_fallback(
        self,
        messages: List[Dict[str, str]],
        fallback_key: str = "analysis_failed",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response with graceful fallback on failure
        
        Args:
            messages: Messages for AI generation
            fallback_key: Key for fallback response
            **kwargs: Additional parameters
            
        Returns:
            AI response or fallback response
        """
        try:
            return await self.generate_analysis_response(messages, **kwargs)
        except (AIServiceError, TokenLimitError, RateLimitError) as e:
            logger.warning(f"AI service failed, using fallback: {e}")
            
            error_monitor.record_error(
                e,
                ErrorCategory.AI_SERVICE,
                ErrorSeverity.MEDIUM,
                {"fallback_used": fallback_key}
            )
            
            return {
                "content": self.fallback_responses.get(fallback_key, "Service temporarily unavailable"),
                "model": "fallback",
                "usage": {},
                "success": False,
                "fallback": True,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _estimate_token_count(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        # Rough estimation: 1 token ≈ 4 characters for English text
        return int(total_chars / 4 * 1.2)  # Add 20% buffer
    
    def _extract_retry_after(self, error_message: str) -> int:
        """Extract retry-after time from error message"""
        import re
        match = re.search(r'retry after (\d+)', error_message.lower())
        if match:
            return int(match.group(1))
        return 60  # Default to 60 seconds
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and metrics"""
        return {
            "circuit_breaker": self.circuit_breaker.get_status(),
            "token_usage": self.token_monitor.get_usage_summary(),
            "current_requests": len(self.token_monitor.request_timestamps),
            "service_available": self.circuit_breaker.can_proceed()
        }


class CircuitBreaker:
    """
    Circuit breaker pattern for AI service reliability
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_proceed(self) -> bool:
        """Check if requests can proceed"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        """Record successful operation"""
        if self.state == "half-open":
            self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time > self.recovery_timeout
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "can_proceed": self.can_proceed()
        }


# Global AI service wrapper instance
_ai_service_wrapper: Optional[AIServiceWrapper] = None

def get_ai_service_wrapper() -> AIServiceWrapper:
    """Get AI service wrapper singleton"""
    global _ai_service_wrapper
    if _ai_service_wrapper is None:
        _ai_service_wrapper = AIServiceWrapper()
    return _ai_service_wrapper