"""
Timeout utilities for the MINT workflow.

This module provides timeout functionality for workflow steps,
ensuring that operations don't exceed their allocated time budgets.
"""

import asyncio
import functools
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, TypeVar, cast

T = TypeVar("T")


class TimeoutError(Exception):
    """Exception raised when a function call times out."""
    
    def __init__(self, function_name: str, timeout_seconds: int):
        """Initialize with function details."""
        self.function_name = function_name
        self.timeout_seconds = timeout_seconds
        message = f"Function {function_name} timed out after {timeout_seconds} seconds"
        super().__init__(message)


def timeout(seconds: int) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to apply a timeout to a function.
    Works with both synchronous and asynchronous functions.
    
    Args:
        seconds: Timeout in seconds
        
    Returns:
        Decorated function with timeout
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper_sync(*args: Any, **kwargs: Any) -> T:
            """Wrapper for synchronous functions."""
            # Define a wrapper that will be run in a separate thread
            def target() -> T:
                return func(*args, **kwargs)
            
            # Use ThreadPoolExecutor for the timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(target)
                try:
                    return future.result(timeout=seconds)
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(func.__name__, seconds)
        
        @functools.wraps(func)
        async def wrapper_async(*args: Any, **kwargs: Any) -> T:
            """Wrapper for asynchronous functions."""
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(func.__name__, seconds)
        
        # Determine if the function is asynchronous
        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        else:
            return wrapper_sync
    
    return decorator


class TimeoutContext:
    """
    Context manager for applying timeout to a block of code.
    Note: This only works reliably in the main thread due to signal limitations.
    """
    
    def __init__(self, seconds: int, error_message: Optional[str] = None):
        """
        Initialize the timeout context.
        
        Args:
            seconds: Timeout in seconds
            error_message: Custom error message
        """
        self.seconds = seconds
        self.error_message = error_message or f"Operation timed out after {seconds} seconds"
        self.timer = None
        self.original_handler = None
    
    def _timeout_handler(self, signum: int, frame: Any) -> None:
        """Handle the timeout signal."""
        raise TimeoutError("TimeoutContext", self.seconds)
    
    def __enter__(self) -> 'TimeoutContext':
        """Start the timeout timer."""
        # Save the original signal handler
        self.original_handler = signal.getsignal(signal.SIGALRM)
        
        # Set the new signal handler
        signal.signal(signal.SIGALRM, self._timeout_handler)
        
        # Set the alarm
        signal.alarm(self.seconds)
        
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clear the timeout timer."""
        # Cancel the alarm
        signal.alarm(0)
        
        # Restore the original signal handler
        signal.signal(signal.SIGALRM, self.original_handler)


class AsyncTimeoutContext:
    """Context manager for applying timeout to a block of asynchronous code."""
    
    def __init__(self, seconds: int, error_message: Optional[str] = None):
        """
        Initialize the timeout context.
        
        Args:
            seconds: Timeout in seconds
            error_message: Custom error message
        """
        self.seconds = seconds
        self.error_message = error_message or f"Operation timed out after {seconds} seconds"
        self.task = None
    
    async def __aenter__(self) -> 'AsyncTimeoutContext':
        """Start the timeout timer."""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clear the timeout timer."""
        # Nothing to clean up
        pass
    
    async def run(self, coro: Any) -> Any:
        """
        Run a coroutine with a timeout.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Result of the coroutine
        
        Raises:
            TimeoutError: If the coroutine takes too long to complete
        """
        try:
            return await asyncio.wait_for(coro, timeout=self.seconds)
        except asyncio.TimeoutError:
            raise TimeoutError("AsyncTimeoutContext", self.seconds)
