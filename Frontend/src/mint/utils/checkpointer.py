"""
Checkpointing utilities for the MINT workflow.

This module provides abstract and concrete implementations for workflow state checkpointing,
allowing different storage backends (Redis, Supabase) to be used interchangeably.
"""

import abc
import json
import os
from typing import Any, Dict, Optional, Protocol, runtime_checkable

import redis
from langgraph.checkpoint.redis import RedisSaver

# Fix import path to use correct module references
from src.mint.schemas.graph_state import GraphState


@runtime_checkable
class CheckpointInterface(Protocol):
    """Protocol defining the interface for checkpoint storage."""
    
    def save_state(self, job_id: str, state: GraphState) -> None:
        """Save a workflow state checkpoint."""
        ...
    
    def load_state(self, job_id: str) -> Optional[GraphState]:
        """Load a workflow state checkpoint."""
        ...
    
    def delete_state(self, job_id: str) -> None:
        """Delete a workflow state checkpoint."""
        ...


class AbstractCheckpointer(abc.ABC):
    """Abstract base class for checkpoint storage implementations."""
    
    @abc.abstractmethod
    def save_state(self, job_id: str, state: GraphState) -> None:
        """Save a workflow state checkpoint."""
        pass
    
    @abc.abstractmethod
    def load_state(self, job_id: str) -> Optional[GraphState]:
        """Load a workflow state checkpoint."""
        pass
    
    @abc.abstractmethod
    def delete_state(self, job_id: str) -> None:
        """Delete a workflow state checkpoint."""
        pass


class RedisStateCheckpointer(AbstractCheckpointer):
    """Redis implementation of workflow state checkpointing."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize with Redis connection parameters."""
        if redis_url:
            self.redis_url = redis_url
            self.client = redis.Redis.from_url(self.redis_url)
        else:
            # Use individual connection parameters if available
            host = os.environ.get("REDIS_HOST", "localhost")
            port = int(os.environ.get("REDIS_PORT", "6379"))
            password = os.environ.get("REDIS_PASSWORD", None)
            db = int(os.environ.get("REDIS_DB", "0"))
            
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=False
            )
    
    def save_state(self, job_id: str, state: GraphState) -> None:
        """Save state to Redis."""
        key = f"graph:{job_id}:state"
        # Convert any non-serializable objects to strings
        serializable_state = self._prepare_for_serialization(state)
        self.client.set(key, json.dumps(serializable_state))
    
    def load_state(self, job_id: str) -> Optional[GraphState]:
        """Load state from Redis."""
        key = f"graph:{job_id}:state"
        state_data = self.client.get(key)
        if not state_data:
            return None
        
        return json.loads(state_data)
    
    def delete_state(self, job_id: str) -> None:
        """Delete state from Redis."""
        key = f"graph:{job_id}:state"
        self.client.delete(key)
    
    def _prepare_for_serialization(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare state for serialization by handling non-JSON-serializable types."""
        result = {}
        for key, value in state.items():
            if hasattr(value, "model_dump"):  # Handle Pydantic models
                result[key] = value.model_dump()
            elif isinstance(value, dict):
                result[key] = self._prepare_for_serialization(value)
            else:
                try:
                    # Test if JSON serializable
                    json.dumps(value)
                    result[key] = value
                except (TypeError, OverflowError):
                    # Fall back to string representation
                    result[key] = str(value)
        return result


class CheckpointFactory:
    """Factory for creating checkpointers."""
    
    @staticmethod
    def create_checkpointer(provider: str = "redis") -> AbstractCheckpointer:
        """Create a checkpointer of the specified type."""
        if provider == "redis":
            return RedisStateCheckpointer()
        # Future: Add Supabase implementation
        # elif provider == "supabase":
        #     return SupabaseStateCheckpointer()
        else:
            raise ValueError(f"Unsupported checkpointer provider: {provider}")
    
    @staticmethod
    def create_langgraph_checkpointer(job_id: str, provider: str = "redis") -> Any:
        """Create a LangGraph-compatible checkpointer."""
        if provider == "redis":
            # Create a prefix for the keys using job_id for multi-tenant support
            # Note: We don't use connection_args for key_prefix as it's not a valid Redis connection parameter
            # Instead, we'll handle key prefixing in our checkpointer wrappers
            
            # Set a TTL of 24 hours (1440 minutes) for all checkpoint keys
            ttl = {
                "default_ttl": 1440,  # 24 hours in minutes
                "refresh_on_read": True
            }
            
            # Try two approaches - first create a direct Redis client, then pass it to RedisSaver
            import redis
            
            # Extract connection info from environment variables
            host = os.environ.get("REDIS_HOST", "localhost")
            
            # Handle the case where hostname might include port already (common in cloud Redis)
            if ":" in host and host.split(":")[1].isdigit():
                host_parts = host.split(":")
                host = host_parts[0]
                port = int(host_parts[1])
                print(f"Extracted port {port} from host")
            else:
                port = int(os.environ.get("REDIS_PORT", "6379"))
                
            # Get API key/password and DB number
            password = os.environ.get("REDIS_PASSWORD")
            db = int(os.environ.get("REDIS_DB", "0"))
            
            # Try to load environment variables directly if not found initially
            if not password:
                # Try to explicitly load from .env file
                from dotenv import load_dotenv
                # Look for .env in the project root directory
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                dotenv_path = os.path.join(project_root, '.env')
                
                if os.path.exists(dotenv_path):
                    print(f"Attempting to load Redis password from .env file at: {dotenv_path}")
                    # Override existing env vars with .env contents
                    load_dotenv(dotenv_path=dotenv_path, override=True, verbose=True)
                    # Try to get password again
                    password = os.environ.get("REDIS_PASSWORD")
            
            # Debug password information without exposing actual value
            password_len = len(password) if password else 0
            print(f"Redis connection info: host={host}, port={port}, db={db}")
            print(f"Password provided: {bool(password)}, length: {password_len}")
            
            # If password is still empty, this is a critical error
            if not password:
                print("\n\n🚨 CRITICAL ERROR: Redis password is missing!")
                print("Please check your .env file and make sure REDIS_PASSWORD is set correctly.")
                print("Current environment variables:")
                print(f"  REDIS_HOST: {os.environ.get('REDIS_HOST', 'Not set')}")
                print(f"  REDIS_PORT: {os.environ.get('REDIS_PORT', 'Not set')}")
                print(f"  REDIS_DB: {os.environ.get('REDIS_DB', 'Not set')}")
                raise ValueError("Redis password is required but not found in environment variables.")
            
            # Set a TTL of 24 hours (1440 minutes) for all checkpoint keys
            ttl = {
                "default_ttl": 1440,  # 24 hours in minutes
                "refresh_on_read": True
            }
            
            # Based on our testing, we know the standard Redis Cloud format works:
            # redis://:password@host:port/0 (with no username and db index 0)
            
            from urllib.parse import quote_plus
            
            # Format the password for URL inclusion
            safe_password = quote_plus(password) if password else ""
            
            # Use database 0 instead of the configured DB - Redis Cloud instance has limitations
            # on available db indexes
            actual_db = 0  # Override to always use database 0
            
            # Standard Redis Cloud format (no username)
            redis_url = f"redis://:{safe_password}@{host}:{port}/{actual_db}"
            print(f"Connecting with Redis URL: {redis_url[:20]}...")
            
            try:
                # Create Redis client and test connection
                redis_client = redis.from_url(
                    redis_url,
                    socket_timeout=5, 
                    decode_responses=False
                )
                
                # Test connection with a simple ping
                redis_client.ping()
                print("✅ Redis connection successful!")
                
                # Create RedisSaver with the successful client
                saver = RedisSaver(redis_client=redis_client, ttl=ttl)
                
            except Exception as e:
                print(f"❌ Error connecting to Redis: {str(e)}")
                print("Falling back to URL method (likely to fail)")
                # Try to create the RedisSaver directly with URL as a fallback
                # This likely won't work, but we'll try anyway
                saver = RedisSaver(redis_url=redis_url, ttl=ttl)
            
            # Wrap the saver in a class that handles key prefixing if needed
            # For now, just return the saver directly
            return saver
        # Future: Add Supabase adapter for LangGraph
        # elif provider == "supabase":
        #     return SupabaseLangGraphAdapter(job_id)
        else:
            raise ValueError(f"Unsupported LangGraph checkpointer provider: {provider}")
