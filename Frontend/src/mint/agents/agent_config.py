"""
Agent Configuration Helper Module

This module provides utilities for agents to access their configuration from the workflow state.
"""

from typing import Dict, Any
import logging
from ..utils.config import get_config

logger = logging.getLogger(__name__)


def get_agent_config(state: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific agent from the workflow state.
    
    Args:
        state: The workflow state containing configuration
        agent_name: Name of the agent (clarifier, specifier, etc.)
        
    Returns:
        Agent configuration dict
    """
    # Try to get from state first (runtime config)
    if "config" in state and "agents" in state["config"] and agent_name in state["config"]["agents"]:
        return state["config"]["agents"][agent_name]
    
    # Fallback to global config
    config = get_config()
    return config.get(f"agents.{agent_name}", {})

def get_llm_config(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get LLM configuration from the workflow state.
    
    Args:
        state: The workflow state containing configuration
        
    Returns:
        LLM configuration dict
    """
    # Try to get from state first (runtime config)
    if "config" in state and "llm" in state["config"]:
        return state["config"]["llm"]
    
    # Fallback to global config
    config = get_config()
    return config.get_llm_config()

def get_search_config(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get search configuration from the workflow state.
    
    Args:
        state: The workflow state containing configuration
        
    Returns:
        Search configuration dict
    """
    # Try to get from state first (runtime config)
    if "config" in state and "search" in state["config"]:
        return state["config"]["search"]
    
    # Fallback to global config
    config = get_config()
    return config.get_search_config()

def get_hybrid_search_strategy(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get hybrid search strategy configuration.
    
    Args:
        state: The workflow state containing configuration
        
    Returns:
        Hybrid search strategy configuration dict
    """
    search_config = get_search_config(state)
    
    if search_config.get('provider') == 'hybrid':
        hybrid_config = search_config.get('hybrid_strategy', {})
        return {
            'mode': 'hybrid',
            'primary_provider': hybrid_config.get('primary_provider', 'tavily'),
            'secondary_provider': hybrid_config.get('secondary_provider', 'brave'),
            'fallback_provider': hybrid_config.get('fallback_provider', 'serper'),
            'primary_query_count': hybrid_config.get('primary_query_count', 3),
            'paid_tier': hybrid_config.get('paid_tier', False),
            'concurrent_searches': hybrid_config.get('concurrent_searches', False),
            'rate_limiting': hybrid_config.get('rate_limiting', True)
        }
    else:
        return {
            'mode': 'single', 
            'provider': search_config.get('provider', 'tavily'),
            'paid_tier': False,
            'concurrent_searches': False,
            'rate_limiting': True
        }

