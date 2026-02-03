"""LLM Utilities for Problem Generator Agents

Shared utilities for LLM calls with timeout protection and retry logic.

MIGRATED TO RESPONSES API (Dec 2025):
- Uses generate_responses_with_tools() instead of call_tool()
- Leverages reasoning.effort and text.verbosity for grounded output
"""

import logging
import asyncio
from typing import Any, List, Dict, Optional

logger = logging.getLogger(__name__)


async def call_llm_with_timeout_and_retry(
    llm_provider, 
    messages: List[Dict[str, str]], 
    tools: List[Dict[str, Any]], 
    operation_id: str, 
    max_retries: int = 3, 
    timeout_seconds: int = 30
) -> Optional[Any]:
    """
    Call LLM with timeout protection and retry logic for Azure OpenAI hanging issues.
    
    Args:
        llm_provider: LLM provider instance
        messages: Messages to send to LLM
        tools: Tools to use for structured output
        operation_id: Identifier for logging (e.g., cluster_id, story_id)
        max_retries: Maximum retry attempts
        timeout_seconds: Timeout in seconds per attempt
        
    Returns:
        LLM response or None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"LLM call attempt {attempt + 1}/{max_retries} for {operation_id}")
            
            # Use asyncio.wait_for to add timeout protection
            # Use Responses API with tools for gpt-5-mini
            response = await asyncio.wait_for(
                llm_provider.generate_responses_with_tools(messages, tools),
                timeout=timeout_seconds
            )
            
            logger.info(f"LLM call successful for {operation_id} on attempt {attempt + 1}")
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"LLM call timeout ({timeout_seconds}s) for {operation_id} on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                # Exponential backoff: 2s, 4s, 8s
                wait_time = 2 ** (attempt + 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All LLM retry attempts failed for {operation_id} due to timeouts")
                
        except Exception as e:
            logger.error(f"LLM call error for {operation_id} on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                # Shorter wait for non-timeout errors
                wait_time = 1 + attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All LLM retry attempts failed for {operation_id}: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
    
    return None


async def call_llm_with_timeout(
    llm_provider,
    messages: List[Dict[str, str]], 
    tools: List[Dict[str, Any]], 
    operation_id: str,
    timeout_seconds: int = 30
) -> Optional[Any]:
    """
    Simple LLM call with timeout protection (no retries).
    
    Args:
        llm_provider: LLM provider instance
        messages: Messages to send to LLM
        tools: Tools to use for structured output
        operation_id: Identifier for logging
        timeout_seconds: Timeout in seconds
        
    Returns:
        LLM response or None if timeout/error
    """
    try:
        logger.info(f"LLM call for {operation_id} with {timeout_seconds}s timeout")
        
        # Use Responses API with tools for gpt-5-mini
        response = await asyncio.wait_for(
            llm_provider.generate_responses_with_tools(messages, tools),
            timeout=timeout_seconds
        )
        
        logger.info(f"LLM call successful for {operation_id}")
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"LLM call timeout ({timeout_seconds}s) for {operation_id}")
        return None
        
    except Exception as e:
        logger.error(f"LLM call error for {operation_id}: {str(e)}")
        return None
