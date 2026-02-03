"""
Circuit Breaker Pattern Implementation

This module provides a circuit breaker pattern for handling failures
in external services and database operations with automatic fallback
and recovery mechanisms.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changed_time: float = field(default_factory=time.time)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for handling service failures.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests fail fast
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker for logging
            config: Configuration for the circuit breaker
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from the function
        """
        async with self._lock:
            # Check if we should fail fast
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.stats.state_changed_time = time.time()
                    logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Last failure: {self.stats.last_failure_time}"
                    )
        
        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = func(*args, **kwargs)
                
            await self._on_success()
            return result
            
        except self.config.expected_exception as e:
            await self._on_failure()
            raise
        except asyncio.TimeoutError as e:
            await self._on_failure()
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' timeout") from e
            
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.stats.last_failure_time is None:
            return True
            
        return (time.time() - self.stats.last_failure_time) >= self.config.recovery_timeout
        
    async def _on_success(self):
        """Handle successful execution."""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.last_success_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.stats.failure_count = 0
                    self.stats.success_count = 0
                    self.stats.state_changed_time = time.time()
                    logger.info(f"Circuit breaker '{self.name}' moved to CLOSED")
                    
    async def _on_failure(self):
        """Handle failed execution."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.last_failure_time = time.time()
            
            if self.state == CircuitState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.stats.state_changed_time = time.time()
                    logger.warning(f"Circuit breaker '{self.name}' moved to OPEN")
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.stats.success_count = 0
                self.stats.state_changed_time = time.time()
                logger.warning(f"Circuit breaker '{self.name}' moved back to OPEN")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "state_changed_time": self.stats.state_changed_time,
            "uptime_percentage": self._calculate_uptime_percentage()
        }
        
    def _calculate_uptime_percentage(self) -> float:
        """Calculate uptime percentage."""
        total_calls = self.stats.failure_count + self.stats.success_count
        if total_calls == 0:
            return 100.0
        return (self.stats.success_count / total_calls) * 100.0
        
    def reset(self):
        """Reset the circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker.
        
        Args:
            name: Name of the circuit breaker
            config: Configuration for the circuit breaker
            
        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
        
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
        
    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def circuit_breaker(
    name: str = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 3,
    timeout: int = 30,
    expected_exception: tuple = (Exception,)
):
    """
    Decorator for applying circuit breaker pattern to functions.
    
    Args:
        name: Name of the circuit breaker (defaults to function name)
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before trying half-open
        success_threshold: Successes needed to close from half-open
        timeout: Request timeout in seconds
        expected_exception: Exceptions that count as failures
    """
    def decorator(func):
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout,
            expected_exception=expected_exception
        )
        breaker = circuit_breaker_manager.get_breaker(breaker_name, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            return loop.run_until_complete(breaker.call(func, *args, **kwargs))
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator