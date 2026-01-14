"""RABA Logging Utilities.

Provides structured logging for all RABA components.
"""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the RABA application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
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
