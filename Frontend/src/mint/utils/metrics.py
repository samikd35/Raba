"""
Prometheus metrics utilities for the MINT workflow.

This module provides standardized metric collection for the workflow,
with Prometheus integration for observability dashboards.
"""

import os
import time
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client import start_http_server, REGISTRY
import threading

# Metrics prefix
PREFIX = "mint"

# Define metrics
WORKFLOW_RUNS = Counter(
    f"{PREFIX}_workflow_runs_total",
    "Total number of workflow runs",
    ["status", "user_id"]
)

WORKFLOW_DURATION = Histogram(
    f"{PREFIX}_workflow_duration_seconds",
    "Duration of workflow runs",
    ["user_id"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600, 7200]
)

STEP_RUNS = Counter(
    f"{PREFIX}_step_runs_total",
    "Total number of workflow step runs",
    ["step", "status"]
)

STEP_DURATION = Histogram(
    f"{PREFIX}_step_duration_seconds",
    "Duration of workflow steps",
    ["step"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

PROVIDER_CALLS = Counter(
    f"{PREFIX}_provider_calls_total",
    "Total number of provider API calls",
    ["provider", "method", "status"]
)

PROVIDER_DURATION = Histogram(
    f"{PREFIX}_provider_duration_seconds",
    "Duration of provider API calls",
    ["provider", "method"],
    buckets=[0.1, 0.5, 1, 3, 5, 10, 30, 60]
)

TOKEN_USAGE = Counter(
    f"{PREFIX}_token_usage_total",
    "Total number of tokens used",
    ["provider", "model", "type"]  # type = prompt, completion
)

COST_USD = Counter(
    f"{PREFIX}_cost_usd_total",
    "Total cost in USD",
    ["provider", "model"]
)

ACTIVE_JOBS = Gauge(
    f"{PREFIX}_active_jobs",
    "Number of active jobs",
    ["status"]  # pending, running, etc.
)

CIRCUIT_BREAKER_STATUS = Gauge(
    f"{PREFIX}_circuit_breaker_status",
    "Circuit breaker status (1=open, 0=closed)",
    ["provider"]
)

QUEUE_SIZE = Gauge(
    f"{PREFIX}_queue_size",
    "Number of jobs in queue",
    ["queue"]
)

# Server startup flag
_server_started = False
_server_lock = threading.Lock()


def start_metrics_server(port: int = 8000) -> None:
    """
    Start the Prometheus metrics server.
    
    Args:
        port: Port to listen on
    """
    global _server_started
    
    with _server_lock:
        if not _server_started:
            start_http_server(port)
            _server_started = True


def record_workflow_start(user_id: str) -> None:
    """
    Record the start of a workflow.
    
    Args:
        user_id: User ID for the workflow
    """
    ACTIVE_JOBS.labels(status="running").inc()


def record_workflow_end(user_id: str, status: str, duration_seconds: float) -> None:
    """
    Record the end of a workflow.
    
    Args:
        user_id: User ID for the workflow
        status: Workflow status (success, error)
        duration_seconds: Workflow duration in seconds
    """
    WORKFLOW_RUNS.labels(status=status, user_id=user_id).inc()
    WORKFLOW_DURATION.labels(user_id=user_id).observe(duration_seconds)
    ACTIVE_JOBS.labels(status="running").dec()


def record_step_start(step: str) -> None:
    """
    Record the start of a workflow step.
    
    Args:
        step: Step name
    """
    pass  # Just used for timing


def record_step_end(step: str, status: str, duration_seconds: float) -> None:
    """
    Record the end of a workflow step.
    
    Args:
        step: Step name
        status: Step status (success, error)
        duration_seconds: Step duration in seconds
    """
    STEP_RUNS.labels(step=step, status=status).inc()
    STEP_DURATION.labels(step=step).observe(duration_seconds)


def record_provider_call(
    provider: str,
    method: str,
    status: str,
    duration_seconds: float
) -> None:
    """
    Record a provider API call.
    
    Args:
        provider: Provider name
        method: Method name
        status: Call status (success, error)
        duration_seconds: Call duration in seconds
    """
    PROVIDER_CALLS.labels(provider=provider, method=method, status=status).inc()
    PROVIDER_DURATION.labels(provider=provider, method=method).observe(duration_seconds)


def record_token_usage(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> None:
    """
    Record token usage.
    
    Args:
        provider: Provider name
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
    """
    TOKEN_USAGE.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
    TOKEN_USAGE.labels(provider=provider, model=model, type="completion").inc(completion_tokens)


def record_cost(provider: str, model: str, cost_usd: float) -> None:
    """
    Record cost in USD.
    
    Args:
        provider: Provider name
        model: Model name
        cost_usd: Cost in USD
    """
    COST_USD.labels(provider=provider, model=model).inc(cost_usd)


def update_circuit_breaker_status(provider: str, is_open: bool) -> None:
    """
    Update circuit breaker status.
    
    Args:
        provider: Provider name
        is_open: Whether the circuit is open (tripped)
    """
    CIRCUIT_BREAKER_STATUS.labels(provider=provider).set(1 if is_open else 0)


def update_queue_size(queue: str, size: int) -> None:
    """
    Update queue size.
    
    Args:
        queue: Queue name
        size: Queue size
    """
    QUEUE_SIZE.labels(queue=queue).set(size)


# Timer context manager for measuring execution time
class Timer:
    """Context manager for measuring execution time."""
    
    def __init__(self):
        """Initialize the timer."""
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start the timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer."""
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """Get the duration in seconds."""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time


# Initialize metrics server if environment variable is set
METRICS_PORT = int(os.environ.get("MINT_METRICS_PORT", "0"))
if METRICS_PORT > 0:
    start_metrics_server(METRICS_PORT)
