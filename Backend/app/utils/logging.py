"""RABA Logging Utilities.

Provides structured logging for all RABA components with colored output
and detailed request/response logging for terminal monitoring.
"""

import logging
import sys
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for terminal."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM + Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        
        # Format the base message
        original_levelname = record.levelname
        record.levelname = f"{level_color}{record.levelname:8}{Colors.RESET}"
        
        # Add module color
        original_name = record.name
        record.name = f"{Colors.CYAN}{record.name}{Colors.RESET}"
        
        result = super().format(record)
        
        # Restore original values
        record.levelname = original_levelname
        record.name = original_name
        
        return result


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the RABA application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create colored formatter
    formatter = ColoredFormatter(
        fmt="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Create handler with colored output
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level: {level}")


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        level: Optional override for log level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)
    
    return logger


# =============================================================================
# Structured Logging Helpers
# =============================================================================

def log_separator(logger: logging.Logger, char: str = "=", length: int = 70) -> None:
    """Log a separator line."""
    logger.info(f"{Colors.DIM}{char * length}{Colors.RESET}")


def log_header(logger: logging.Logger, title: str) -> None:
    """Log a section header with visual emphasis."""
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'═' * 70}{Colors.RESET}")
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}  {title}{Colors.RESET}")
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'═' * 70}{Colors.RESET}")


def log_subheader(logger: logging.Logger, title: str) -> None:
    """Log a subsection header."""
    logger.info(f"{Colors.CYAN}── {title} {'─' * (60 - len(title))}{Colors.RESET}")


def log_key_value(logger: logging.Logger, key: str, value: Any, indent: int = 2) -> None:
    """Log a key-value pair with formatting."""
    spaces = " " * indent
    logger.info(f"{spaces}{Colors.BRIGHT_BLUE}{key}:{Colors.RESET} {value}")


def log_success(logger: logging.Logger, message: str) -> None:
    """Log a success message with green checkmark."""
    logger.info(f"{Colors.BRIGHT_GREEN}✓ {message}{Colors.RESET}")


def log_warning_msg(logger: logging.Logger, message: str) -> None:
    """Log a warning message with yellow indicator."""
    logger.warning(f"{Colors.BRIGHT_YELLOW}⚠ {message}{Colors.RESET}")


def log_error_msg(logger: logging.Logger, message: str) -> None:
    """Log an error message with red indicator."""
    logger.error(f"{Colors.BRIGHT_RED}✗ {message}{Colors.RESET}")


def log_request_start(
    logger: logging.Logger,
    method: str,
    path: str,
    params: Optional[dict] = None,
) -> None:
    """Log the start of an API request."""
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}→ {method} {path}{Colors.RESET}")
    if params:
        for key, value in params.items():
            if value is not None:
                log_key_value(logger, key, value, indent=4)


def log_request_end(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    """Log the end of an API request with timing."""
    status_color = Colors.BRIGHT_GREEN if status_code < 400 else Colors.BRIGHT_RED
    logger.info(
        f"{Colors.BOLD}{status_color}← {method} {path} "
        f"[{status_code}] ({duration_ms:.1f}ms){Colors.RESET}"
    )


@contextmanager
def log_operation(logger: logging.Logger, operation_name: str):
    """Context manager for logging operation duration."""
    start_time = time.time()
    logger.info(f"{Colors.CYAN}▶ Starting: {operation_name}{Colors.RESET}")
    try:
        yield
        duration = (time.time() - start_time) * 1000
        logger.info(
            f"{Colors.BRIGHT_GREEN}✓ Completed: {operation_name} "
            f"({duration:.1f}ms){Colors.RESET}"
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(
            f"{Colors.BRIGHT_RED}✗ Failed: {operation_name} "
            f"({duration:.1f}ms) - {str(e)}{Colors.RESET}"
        )
        raise


def log_workflow_event(
    logger: logging.Logger,
    workflow_id: str,
    event: str,
    details: Optional[dict] = None,
) -> None:
    """Log a workflow-related event with structured format."""
    logger.info(
        f"{Colors.BRIGHT_MAGENTA}[WF:{workflow_id[:12]}]{Colors.RESET} "
        f"{Colors.BOLD}{event}{Colors.RESET}"
    )
    if details:
        for key, value in details.items():
            log_key_value(logger, key, value, indent=4)


def log_agent_event(
    logger: logging.Logger,
    agent_name: str,
    event: str,
    workflow_id: Optional[str] = None,
) -> None:
    """Log an agent-related event."""
    wf_prefix = f"[WF:{workflow_id[:12]}] " if workflow_id else ""
    logger.info(
        f"{Colors.BRIGHT_MAGENTA}{wf_prefix}{Colors.RESET}"
        f"{Colors.BRIGHT_YELLOW}[{agent_name}]{Colors.RESET} {event}"
    )


def log_hitl_event(
    logger: logging.Logger,
    workflow_id: str,
    gate: str,
    action: str,
    details: Optional[dict] = None,
) -> None:
    """Log an HITL-related event."""
    logger.info(
        f"{Colors.BRIGHT_MAGENTA}[WF:{workflow_id[:12]}]{Colors.RESET} "
        f"{Colors.BG_YELLOW}{Colors.BLACK} HITL {Colors.RESET} "
        f"Gate: {gate} | Action: {action}"
    )
    if details:
        for key, value in details.items():
            log_key_value(logger, key, value, indent=4)


def log_api_metrics(
    logger: logging.Logger,
    tokens_used: Optional[int] = None,
    cost_usd: Optional[float] = None,
    cache_hit: bool = False,
) -> None:
    """Log API usage metrics."""
    parts = []
    if tokens_used is not None:
        parts.append(f"Tokens: {tokens_used:,}")
    if cost_usd is not None:
        parts.append(f"Cost: ${cost_usd:.4f}")
    if cache_hit:
        parts.append(f"{Colors.BRIGHT_GREEN}(cached){Colors.RESET}")
    
    if parts:
        logger.info(f"  {Colors.DIM}📊 {' | '.join(parts)}{Colors.RESET}")
