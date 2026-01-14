"""RABA Configuration Module.

Centralized configuration using Pydantic Settings.
All configuration is loaded from environment variables with .env file support.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Master configuration for RABA Backend."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # === App Settings ===
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=True, description="Debug mode")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # === Google Gen AI ===
    google_api_key: Optional[str] = Field(default=None, description="Google API Key for Gemini")
    
    # === Supabase ===
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase anon key")
    supabase_service_key: Optional[str] = Field(default=None, description="Supabase service key")
    
    # === Redis ===
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    
    # === Google Custom Search ===
    google_custom_search_api_key: Optional[str] = Field(default=None, description="Google Custom Search API Key")
    google_custom_search_cx: Optional[str] = Field(default=None, description="Google Custom Search Engine ID")
    
    # === LangSmith ===
    langchain_tracing_v2: bool = Field(default=True, description="Enable LangSmith tracing")
    langchain_api_key: Optional[str] = Field(default=None, description="LangSmith API Key")
    langchain_project: str = Field(default="Raba", description="LangSmith project name")
    
    # === Video Generation Defaults ===
    default_duration_seconds: int = Field(default=18, ge=8, le=25)
    default_aspect_ratio: str = Field(default="9:16")
    default_resolution: str = Field(default="1080p")
    default_category: str = Field(default="auto")
    default_hitl_mode: str = Field(default="auto")
    
    # === Cache TTL (seconds) ===
    cache_ttl_research: int = Field(default=604800, description="Research cache TTL (7 days)")
    cache_ttl_tools: int = Field(default=3600, description="Tools cache TTL (1 hour)")
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    def validate_required_for_production(self) -> list[str]:
        """Validate required settings for production. Returns list of missing keys."""
        required = [
            ("google_api_key", self.google_api_key),
            ("supabase_url", self.supabase_url),
            ("supabase_key", self.supabase_key),
            ("redis_url", self.redis_url),
        ]
        return [name for name, value in required if not value]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance (cached)
    """
    logger.info("Loading application settings...")
    settings = Settings()
    
    setup_logging(settings.log_level)
    
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API prefix: {settings.api_v1_prefix}")
    logger.info(f"Supabase configured: {bool(settings.supabase_url)}")
    logger.info(f"Redis configured: {bool(settings.redis_url)}")
    logger.info(f"Google API configured: {bool(settings.google_api_key)}")
    logger.info(f"LangSmith tracing: {settings.langchain_tracing_v2}")
    
    if settings.is_production():
        missing = settings.validate_required_for_production()
        if missing:
            logger.warning(f"Missing required production settings: {missing}")
    
    return settings


settings = get_settings()
