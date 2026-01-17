#!/usr/bin/env python3
"""Entry point for running the RABA backend directly.

Usage:
    python main.py

This is equivalent to:
    python -m uvicorn app.main:app --reload
    python -m app.main
"""

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    from app.utils.logging import get_logger
    
    logger = get_logger(__name__)
    logger.info("Starting RABA Backend with uvicorn...")
    
    # Use import string format to enable reload functionality
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
