"""
Search Provider implementations for MINT.

This module defines the SearchProvider abstract base class and concrete implementations
for Brave Search, Tavily, and Serper.
"""

import json
from typing import Dict, List, Literal, Optional, Any

import requests
from pydantic import BaseModel, Field, HttpUrl

from .registry import Provider, ProviderConfig, ProviderError


class LLMToolResponse(BaseModel):
    """Response model for LLM tool calls."""
    content: str = Field(..., description="The response content from the LLM")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tool calls made by the LLM")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")


class SearchProviderError(ProviderError):
    """Error class for search provider related errors."""
    pass


class SearchResult(BaseModel):
    """Standardized search result format."""
    title: str
    url: HttpUrl
    snippet: str
    source: str
    position: int
    published_date: Optional[str] = None
    is_pdf: bool = False
    metadata: Optional[Dict[str, Any]] = None


class SearchConfig(ProviderConfig):
    """Configuration for search providers."""
    provider_type: Literal["search"] = "search"
    num_results: int = 10
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    safe_search: bool = True


import time
import logging
import random
import asyncio

logger = logging.getLogger(__name__)

# Helper function for retrying API calls with exponential backoff
async def retry_with_backoff(func, *args, max_retries=3, base_delay=1.0, **kwargs):
    """
    Execute an async function with exponential backoff retries for rate limiting.
    
    Args:
        func: Async function to execute
        *args: Arguments to pass to the function
        max_retries: Maximum number of retries (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The function result if successful
        
    Raises:
        The last encountered exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):  # +1 for the initial try
        try:
            if attempt > 0:
                # Add some randomness (jitter) to avoid synchronized retries
                jitter = random.uniform(0.8, 1.2)
                delay = base_delay * (2 ** (attempt - 1)) * jitter  # Exponential backoff with jitter
                logger.info(f"Retry attempt {attempt}/{max_retries} after {delay:.2f}s delay")
                await asyncio.sleep(delay)
                
            return await func(*args, **kwargs)
            
        except Exception as e:
            last_exception = e
            # Only retry on 429 Too Many Requests or specific network errors
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                logger.warning(f"Rate limit exceeded, retrying: {str(e)}")
                continue
            elif isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                logger.warning(f"Network error, retrying: {str(e)}")
                continue
            else:
                # Don't retry other types of errors
                raise
    
    # If we've exhausted all retries, raise the last exception
    logger.error(f"All retry attempts failed: {str(last_exception)}")
    raise last_exception

class SearchProvider(Provider[List[SearchResult]]):
    """Abstract base class for search providers."""
    
    def __init__(self, config: SearchConfig):
        """Initialize with search-specific configuration."""
        super().__init__(config)
        self.config = config  # Re-assign for proper type inference
        
    async def search(self, query: str) -> List[SearchResult]:
        """Perform a search query."""
        raise NotImplementedError("Subclasses must implement search method")
    
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the search provider.
        
        This method allows search providers to be used with the same tool calling interface
        as LLM providers, enabling structured data extraction via tool schemas.
        
        Args:
            messages: Chat messages in the OpenAI format
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        raise NotImplementedError("Subclasses must implement call_tool method")


class BraveSearchProvider(SearchProvider):
    """Brave Search implementation of Search Provider."""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        """Initialize Brave Search provider."""
        config = config or SearchConfig(
            provider_name="brave",
            api_key_env_var="BRAVE_API_KEY",
        )
        super().__init__(config)
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the Brave Search API.
        
        Args:
            messages: Chat messages to extract the search query from
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        # Extract query from messages - use last user message as default
        query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                query = msg.get("content")
                break
                
        if not query:
            raise ProviderError("No valid query found in messages")
            
        # Get search results using the standard search method
        search_results = await self.search(query)
            
        # Prepare the tool response with search results
        return LLMToolResponse(
            name="search",  # Use generic name since we don't have actual tool names
            arguments={"results": [result.model_dump() for result in search_results]},
            model="brave_search",
            finish_reason="tool_calls",
            usage=None
        )
    
    def health_check(self) -> bool:
        """Check if Brave Search API is operational."""
        if not self.api_key:
            return False
        try:
            headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key}
            response = requests.get(
                f"{self.base_url}?q=test",
                headers=headers,
                timeout=self.config.timeout_seconds
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def fallback_available(self) -> bool:
        """Brave Search doesn't have built-in fallbacks."""
        return False
    
    async def search(self, query: str) -> List[SearchResult]:
        """Perform a search using Brave Search API with retry mechanism for rate limits."""
        if not self.api_key:
            raise ProviderError("Brave Search API key not provided.")
        
        headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key}
        params = {
            "q": query,
            "count": self.config.num_results,
            "safe_search": str(self.config.safe_search).lower(),
        }
        
        logger.debug(f"Executing Brave Search for query: {query[:50]}{'...' if len(query) > 50 else ''}")  
        
        # Define the actual search function that will be retried
        async def execute_search():
            # Convert to async since requests is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    self.base_url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout_seconds
                )
            )
            response.raise_for_status()  # Will trigger retry on 429 errors
            return response.json()
            
        try:
            # Use retry with exponential backoff
            data = await retry_with_backoff(execute_search, max_retries=3, base_delay=1.0)
            
            results = []
            for i, result in enumerate(data.get("web", {}).get("results", [])):
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("description", ""),
                    source="brave",
                    position=i + 1,
                    published_date=result.get("published_date", None),
                    is_pdf=result.get("url", "").lower().endswith(".pdf")
                ))
            return results
        
        except requests.exceptions.RequestException as e:
            # After all retries have failed
            logger.error(f"Brave Search API error after retries: {str(e)}")
            raise ProviderError(f"Brave Search API error: {str(e)}")


class TavilySearchProvider(SearchProvider):
    """Tavily Search implementation of Search Provider."""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        """Initialize Tavily Search provider."""
        config = config or SearchConfig(
            provider_name="tavily",
            api_key_env_var="TAVILY_API_KEY",
        )
        super().__init__(config)
        self.base_url = "https://api.tavily.com/search"
        
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the Tavily Search API.
        
        Args:
            messages: Chat messages to extract the search query from
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        # Extract query from messages - use last user message as default
        query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                query = msg.get("content")
                break
                
        if not query:
            raise ProviderError("No valid query found in messages")
            
        # Get search results using the standard search method
        search_results = await self.search(query)
            
        # Prepare the tool response with search results
        return LLMToolResponse(
            name="search",  # Use generic name since we don't have actual tool names
            arguments={"results": [result.model_dump() for result in search_results]},
            model="tavily_search",
            finish_reason="tool_calls",
            usage=None
        )
    
    def health_check(self) -> bool:
        """Check if Tavily API is operational."""
        if not self.api_key:
            return False
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "api_key": self.api_key,
                "query": "test",
                "search_depth": "basic"
            }
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=self.config.timeout_seconds
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def fallback_available(self) -> bool:
        """Tavily doesn't have built-in fallbacks."""
        return False
    
    async def search(self, query: str) -> List[SearchResult]:
        """Perform a search using Tavily API with retry mechanism for rate limits."""
        if not self.api_key:
            raise ProviderError("Tavily API key not provided.")
        
        headers = {"Content-Type": "application/json"}
        data = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "include_domains": self.config.include_domains,
            "exclude_domains": self.config.exclude_domains,
            "max_results": self.config.num_results
        }
        
        logger.debug(f"Executing Tavily Search for query: {query[:50]}{'...' if len(query) > 50 else ''}")  
        
        # Define the actual search function that will be retried
        async def execute_search():
            # Convert to async since requests is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=self.config.timeout_seconds
                )
            )
            response.raise_for_status()  # Will trigger retry on 429 errors
            return response.json()
            
        try:
            # Use retry with exponential backoff
            result_data = await retry_with_backoff(execute_search, max_retries=3, base_delay=1.0)
            
            results = []
            for i, result in enumerate(result_data.get("results", [])):
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("content", ""),
                    source="tavily",
                    position=i + 1,
                    is_pdf=result.get("url", "").lower().endswith(".pdf")
                ))
            return results
        
        except requests.exceptions.RequestException as e:
            # After all retries have failed
            logger.error(f"Tavily API error after retries: {str(e)}")
            raise ProviderError(f"Tavily API error: {str(e)}")


class SerperSearchProvider(SearchProvider):
    """Serper.dev implementation of Search Provider."""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        """Initialize Serper Search provider."""
        config = config or SearchConfig(
            provider_name="serper",
            api_key_env_var="SERPER_API_KEY",
        )
        super().__init__(config)
        self.base_url = "https://google.serper.dev/search"
        
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the Serper API.
        
        Args:
            messages: Chat messages to extract the search query from
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        # Extract query from messages - use last user message as default
        query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                query = msg.get("content")
                break
                
        if not query:
            raise ProviderError("No valid query found in messages")
            
        # Get search results using the standard search method
        search_results = await self.search(query)
            
        # Prepare the tool response with search results
        return LLMToolResponse(
            name="search",  # Use generic name since we don't have actual tool names
            arguments={"results": [result.model_dump() for result in search_results]},
            model="serper_search",
            finish_reason="tool_calls",
            usage=None
        )
    
    def health_check(self) -> bool:
        """Check if Serper API is operational."""
        if not self.api_key:
            return False
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            data = {"q": "test"}
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=self.config.timeout_seconds
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def fallback_available(self) -> bool:
        """Serper doesn't have built-in fallbacks."""
        return False
    
    async def search(self, query: str) -> List[SearchResult]:
        """Perform a search using Serper API with retry mechanism for rate limits."""
        if not self.api_key:
            raise ProviderError("Serper API key not provided.")
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "q": query,
            "num": self.config.num_results,
            "gl": "us",  # Geolocation
        }
        
        logger.debug(f"Executing Serper Search for query: {query[:50]}{'...' if len(query) > 50 else ''}")  
        
        # Define the actual search function that will be retried
        async def execute_search():
            # Convert to async since requests is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=self.config.timeout_seconds
                )
            )
            response.raise_for_status()  # Will trigger retry on 429 errors
            return response.json()
            
        try:
            # Use retry with exponential backoff
            result_data = await retry_with_backoff(execute_search, max_retries=3, base_delay=1.0)
            
            results = []
            for i, result in enumerate(result_data.get("organic", [])):
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    source="serper",
                    position=i + 1,
                    is_pdf=result.get("link", "").lower().endswith(".pdf")
                ))
            return results
        
        except requests.exceptions.RequestException as e:
            # After all retries have failed
            logger.error(f"Serper API error after retries: {str(e)}")
            raise ProviderError(f"Serper API error: {str(e)}")
