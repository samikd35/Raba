"""
Tracing module for MINT workflow.

This module provides centralized LangSmith tracing functionality for all MINT components.
It ensures consistent tracing behavior across agents, workflow, and other modules.
"""

import os
import logging
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for better type hinting
F = TypeVar('F', bound=Callable[..., Any])

# Check if LangSmith is available and properly configured
# TEMPORARILY DISABLED: LangSmith causes memory issues with large research data (314MB+)
LANGSMITH_ENABLED = False  # bool(os.environ.get("LANGSMITH_API_KEY"))

if LANGSMITH_ENABLED:
    try:
        import langsmith
        from langsmith.run_helpers import traceable as langsmith_traceable
        logger.info("LangSmith tracing enabled")
    except ImportError:
        logger.warning("LangSmith package not installed but LANGSMITH_API_KEY is set")
        LANGSMITH_ENABLED = False

# Define the centralized traceable decorator
def traceable(name: Optional[str] = None, run_type: str = "chain", **kwargs: Any):
    """
    Decorator for tracing function execution with LangSmith.

    Args:
        name: A name for the traced run. If None, uses the function name.
        run_type: The type of run for LangSmith categories (chain, llm, tool, etc.)
        **kwargs: Additional keyword arguments for LangSmith tracing.

    Returns:
        A decorator that wraps the function with tracing.
    """
    def decorator(func):
        # Only trace if LangSmith is configured
        if LANGSMITH_ENABLED:
            try:
                # Use LangSmith's traceable with run_type parameter
                traced_func = langsmith_traceable(
                    name=name or func.__name__, 
                    run_type=run_type,
                    **kwargs
                )(func)
                return traced_func
            except Exception as e:
                logger.warning(f"Error setting up LangSmith tracing for {func.__name__}: {e}")
                return func
        else:
            # Return the original function if LangSmith is not enabled
            return func

    return decorator
