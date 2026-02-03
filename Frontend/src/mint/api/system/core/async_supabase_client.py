"""
Async Supabase client for high-performance database operations.

This module provides an async Supabase client that doesn't block the event loop,
enabling true concurrent request handling in FastAPI.
"""

import os
import logging
import asyncio
from typing import Optional

from supabase._async.client import AsyncClient, create_client as create_async_client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Global async client singletons
_async_client_service: Optional[AsyncClient] = None
_async_client_standard: Optional[AsyncClient] = None
_init_lock = asyncio.Lock()


async def get_async_supabase_client(use_service_role: bool = True) -> AsyncClient:
    """
    Get singleton async Supabase client.

    Args:
        use_service_role: If True, returns service role client (bypasses RLS).
                         If False, returns standard client (subject to RLS).

    Returns:
        AsyncClient: Async Supabase client instance
    """
    global _async_client_service, _async_client_standard

    async with _init_lock:
        if use_service_role:
            if _async_client_service is None:
                _async_client_service = await _create_async_client(use_service_role=True)
                logger.info("Async Supabase service role client initialized")
            return _async_client_service
        else:
            if _async_client_standard is None:
                _async_client_standard = await _create_async_client(use_service_role=False)
                logger.info("Async Supabase standard client initialized")
            return _async_client_standard


async def _create_async_client(use_service_role: bool) -> AsyncClient:
    """
    Create a new async Supabase client.
    """
    supabase_url = os.getenv("SUPABASE_URL")

    if use_service_role:
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_key:
            supabase_key = os.getenv("SUPABASE_KEY")
            logger.warning("SUPABASE_SERVICE_ROLE_KEY not found, falling back to SUPABASE_KEY")
    else:
        supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

    client = await create_async_client(supabase_url, supabase_key)
    return client


async def get_async_service_role_client() -> AsyncClient:
    """Get the async service role Supabase client (bypasses RLS)."""
    return await get_async_supabase_client(use_service_role=True)


async def get_async_standard_client() -> AsyncClient:
    """Get the async standard Supabase client (subject to RLS)."""
    return await get_async_supabase_client(use_service_role=False)


async def close_async_clients():
    """
    Close async clients on application shutdown.
    Call this in your FastAPI shutdown event.
    """
    global _async_client_service, _async_client_standard

    async with _init_lock:
        _async_client_service = None
        _async_client_standard = None
        logger.info("Async Supabase clients closed")
