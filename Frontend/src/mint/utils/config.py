"""
MINT Configuration Manager

This module loads and manages configuration settings for the MINT system,
allowing easy access to configuration parameters throughout the codebase.
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Union, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_PATH = "config/mint_config.yaml"
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

class ConfigurationError(Exception):
    """Raised when there is an error in configuration loading or validation."""
    pass

class MintConfig:
    """
    Configuration manager for the MINT system.
    
    Handles loading and accessing configuration parameters from YAML file
    with environment variable overrides.
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls, config_path: Optional[str] = None):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super(MintConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration YAML file
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return
            
        self._initialized = True
        self._config_data = {}
        
        # Resolve config path
        if config_path is None:
            config_path = os.environ.get("MINT_CONFIG_PATH", DEFAULT_CONFIG_PATH)
        
        # Convert to absolute path if needed
        if not os.path.isabs(config_path):
            config_path = os.path.join(PROJECT_ROOT, config_path)
            
        self.config_path = config_path
        self._load_config()
        
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            logger.info(f"Loading configuration from {self.config_path}")
            
            if not os.path.exists(self.config_path):
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f)
                
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def reload(self):
        """Reload configuration from the YAML file."""
        self._load_config()
        
    def get_raw_config(self) -> Dict[str, Any]:
        """Return the full raw configuration dictionary.
        
        Returns:
            The complete configuration dictionary
        """
        return self._config_data
        
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation path.
        
        Args:
            path: Dot-separated path to the configuration value
            default: Default value to return if path not found
            
        Returns:
            The configuration value or default if not found
        """
        keys = path.split(".")
        value = self._config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, path: str, value: Any):
        """
        Set a configuration value using dot notation path.
        
        Args:
            path: Dot-separated path to the configuration value
            value: The value to set
        """
        keys = path.split(".")
        config = self._config_data
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
            
        config[keys[-1]] = value
        
    def save(self):
        """Save the current configuration back to the YAML file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(self._config_data, f, default_flow_style=False)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            raise ConfigurationError(f"Failed to save configuration: {str(e)}")
            
    def get_env_value(self, env_var: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a value from an environment variable.
        
        Args:
            env_var: The environment variable name
            default: Default value if environment variable is not set
            
        Returns:
            The environment variable value or default
        """
        return os.environ.get(env_var, default)
    
    def resolve_env_var(self, path: str) -> Optional[str]:
        """
        Get the value of an environment variable specified in the config.
        
        Args:
            path: Path to the config key containing the environment variable name
            
        Returns:
            The value of the environment variable or None if not set
        """
        env_var = self.get(path)
        if not env_var:
            return None
        return self.get_env_value(env_var)
        
    def get_llm_config(self) -> Dict[str, Any]:
        """Get the LLM configuration for the current provider."""
        provider = self.get("llm.provider", "openai")
        
        # Get provider-specific config
        provider_config = self.get(f"llm.{provider}", {})
        
        # Get common config
        common_config = self.get("llm.common", {})
        
        # Merge configs, with provider-specific taking precedence
        config = {**common_config, **provider_config}
        
        # Add provider name
        config["provider"] = provider
        
        return config
        
    def get_search_config(self) -> Dict[str, Any]:
        """Get the full search configuration including hybrid strategy."""
        # Get the entire search section
        search_config = self.get("search", {})
        
        # Ensure provider is set
        if "provider" not in search_config:
            search_config["provider"] = "tavily"
        
        return search_config
        
    def get_vector_config(self) -> Dict[str, Any]:
        """Get the vector store configuration for the current provider."""
        provider = self.get("vector.provider", "pgvector")
        
        # Get provider-specific config
        provider_config = self.get(f"vector.{provider}", {})
        
        # Add provider name
        provider_config["provider"] = provider
        
        return provider_config


# Create a singleton instance for global use
config = MintConfig()

def get_config() -> MintConfig:
    """Get the global configuration instance."""
    return config


def get_agent_config(agent_name: str, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific agent, with optional state override.
    
    Args:
        agent_name: Name of the agent (e.g., 'industry_agent', 'pestel_analysis')
        state: Optional workflow state dictionary that may contain config overrides
        
    Returns:
        Dictionary containing agent configuration
    """
    # Get from central config
    agent_cfg = config.get(f"agents.{agent_name}", {})
    
    # Check for runtime overrides in state
    if state and isinstance(state, dict):
        state_config = state.get("config", {})
        agent_state_cfg = state_config.get(agent_name, {})
        
        if agent_state_cfg:
            # Merge with state config taking precedence
            agent_cfg = {**agent_cfg, **agent_state_cfg}
    
    return agent_cfg


def get_llm_config(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get LLM configuration with optional state override.
    
    Args:
        state: Optional workflow state dictionary that may contain config overrides
        
    Returns:
        Dictionary containing LLM configuration
    """
    # Get from central config
    llm_cfg = config.get_llm_config()
    
    # Check for runtime overrides in state
    if state and isinstance(state, dict):
        state_config = state.get("config", {})
        llm_state_cfg = state_config.get("llm", {})
        
        if llm_state_cfg:
            # Merge with state config taking precedence
            llm_cfg = {**llm_cfg, **llm_state_cfg}
    
    return llm_cfg


def get_search_config(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get search configuration with optional state override.
    
    Args:
        state: Optional workflow state dictionary that may contain config overrides
        
    Returns:
        Dictionary containing search configuration
    """
    # Get from central config
    search_cfg = config.get_search_config()
    
    # Check for runtime overrides in state
    if state and isinstance(state, dict):
        state_config = state.get("config", {})
        search_state_cfg = state_config.get("search", {})
        
        if search_state_cfg:
            # Merge with state config taking precedence
            search_cfg = {**search_cfg, **search_state_cfg}
    
    return search_cfg
