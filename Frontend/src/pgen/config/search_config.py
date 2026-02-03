"""
Search Configuration Module

This module provides default configuration for search providers and parameters.
Can be overridden at runtime through environment variables or workflow state.
"""

from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_default_search_config() -> Dict[str, Any]:
    """
    Get default search configuration with environment variable overrides.
    
    Returns:
        Dict with search configuration
    """
    # Default configuration
    config = {
        # Search provider configuration
        "news_provider": "brave",  # Options: "brave", "serper"
        "deep_provider": "brave",   # Options: "brave", "serper" (was "tavily")
        
        # Recency configuration
        "recency_days": 90,  # How recent should the information be (in days)
        
        # Results configuration
        "max_results": 5,  # Maximum results per query
        "max_queries": {
            "db": 5,     # Max queries for database search
            "news": 7,   # Max queries for news search
            "deep": 15   # Max queries for deep search
        },
        
        # Provider-specific configuration
        "brave": {
            "freshness": "qdr:m3",  # Last 3 months
            "count": 10
        },
        "tavily": {
            "search_depth": "advanced",  # Options: "basic", "advanced" (DEPRECATED)
            "include_domains": [],
            "exclude_domains": []
        },
        "serper": {
            "gl": "us",  # Country code
            "hl": "en"   # Language
        }
    }
    
    # Override with environment variables if present
    if os.environ.get("SEARCH_NEWS_PROVIDER"):
        config["news_provider"] = os.environ.get("SEARCH_NEWS_PROVIDER")
        
    if os.environ.get("SEARCH_DEEP_PROVIDER"):
        config["deep_provider"] = os.environ.get("SEARCH_DEEP_PROVIDER")
        
    if os.environ.get("SEARCH_RECENCY_DAYS"):
        try:
            config["recency_days"] = int(os.environ.get("SEARCH_RECENCY_DAYS"))
        except (ValueError, TypeError):
            pass  # Keep default if invalid
    
    return config

def update_search_config(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update search configuration from workflow state.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with search configuration
    """
    # Get default configuration
    default_config = get_default_search_config()
    
    # Initialize config in state if not present
    if "config" not in state:
        state["config"] = {}
    
    if "search" not in state["config"]:
        state["config"]["search"] = default_config
    else:
        # Update with defaults for missing keys
        for key, value in default_config.items():
            if key not in state["config"]["search"]:
                state["config"]["search"][key] = value
    
    return state
