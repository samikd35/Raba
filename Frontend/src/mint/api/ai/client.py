"""
LLM Client Service for Report Chat Feature

This module provides functionality for interacting with the Gemini 2.5 Flash API.
It handles sending prompts, receiving responses, and implementing error handling and retry logic.
It also includes circuit breaker pattern and fallback mechanisms for handling service failures.
"""

import os
import time
import json
import logging
import httpx
from typing import Dict, Any, Optional, List, Union, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ...utils.circuit_breaker import circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)

class LLMClientService:
    """Service for interacting with the Gemini 2.5 Flash API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """
        Initialize the LLM client service.
        
        Args:
            api_key: The API key for accessing the Gemini API. If None, will try to get from environment.
            model: The model to use for generating responses.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("No Gemini API key provided. Service will not function properly.")
        
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.client = httpx.Client(timeout=60.0)  # 60 second timeout
        self.fallback_enabled = True  # Whether to use fallback mechanisms
        
    def generate_fallback_response(self, query: str, context: str) -> Dict[str, Any]:
        """
        Generate a simple fallback response when the LLM service is unavailable.
        
        Args:
            query: The user's query
            context: The context from retrieved chunks
            
        Returns:
            Dict containing a simple response
        """
        logger.info("Generating fallback response")
        
        # Extract chunk citations from the context
        chunk_citations = []
        if context:
            lines = context.split("\n\n")
            for line in lines:
                if line.startswith("[") and "]" in line:
                    citation_num = line[1:line.find("]")]
                    if citation_num.isdigit():
                        chunk_citations.append(int(citation_num))
        
        # Generate a simple response based on the query type
        query_lower = query.lower()
        
        # Check if it's a summary request
        if "summary" in query_lower or "summarize" in query_lower or "overview" in query_lower:
            response = "I'm currently experiencing technical difficulties accessing the full capabilities of my language model. "
            response += "However, I can see that your report contains relevant information. "
            response += "Please check the report sections directly for a comprehensive summary."
            
            # Add citations if available
            if chunk_citations:
                response += " You might find useful information in sections "
                response += ", ".join(f"[{i}]" for i in chunk_citations[:3])
                response += " of the report."
        
        # Check if it's a specific question
        elif any(q in query_lower for q in ["what", "how", "why", "when", "where", "who", "which"]):
            response = "I'm currently experiencing technical difficulties accessing the full capabilities of my language model. "
            response += "Your question appears to be about specific information in the report. "
            
            # Add citations if available
            if chunk_citations:
                response += "Based on the context, you might find relevant information in sections "
                response += ", ".join(f"[{i}]" for i in chunk_citations[:3])
                response += " of the report."
            else:
                response += "Please check the relevant sections of the report for this information."
        
        # Default response
        else:
            response = "I'm currently experiencing technical difficulties accessing the full capabilities of my language model. "
            response += "Please try again later or refer directly to the report for the information you need."
            
            # Add citations if available
            if chunk_citations:
                response += " You might find useful information in sections "
                response += ", ".join(f"[{i}]" for i in chunk_citations[:3])
                response += " of the report."
        
        return {
            "text": response,
            "raw_response": {"fallback": True},
            "finish_reason": "FALLBACK",
            "usage": {}
        }
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    @circuit_breaker(
        name="gemini_llm",
        failure_threshold=5,
        recovery_timeout=300  # 5 minutes
    )
    def _call_llm_api(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make the actual API call to the LLM service with circuit breaker pattern.
        
        Args:
            url: The API endpoint URL
            payload: The request payload
            
        Returns:
            Dict containing the API response
            
        Raises:
            httpx.RequestError: If there's a network-related error
            httpx.HTTPStatusError: If the API returns an error status code
            ValueError: If the response format is invalid
        """
        response = self.client.post(
            url,
            json=payload,
            params={"key": self.api_key},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        # Parse and return the response
        result = response.json()
        
        # Extract the text from the response
        if not result.get("candidates"):
            raise ValueError("No candidates in response")
        
        content = result["candidates"][0]["content"]
        text = ""
        for part in content.get("parts", []):
            if "text" in part:
                text += part["text"]
        
        return {
            "text": text,
            "raw_response": result,
            "finish_reason": result["candidates"][0].get("finishReason", "STOP"),
            "usage": result.get("usageMetadata", {})
        }
    
    def generate_response(self, 
                         prompt: Dict[str, Any], 
                         web_search_enabled: bool = False,
                         temperature: float = 0.2,
                         max_tokens: int = 32000) -> Dict[str, Any]:
        """
        Generate a response from the LLM based on the provided prompt.
        With fallback to a simpler response if the LLM service fails.
        
        Args:
            prompt: The prompt to send to the LLM
            web_search_enabled: Whether to enable web search for this request
            temperature: Controls randomness in the response (0.0-1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dict containing the LLM response or a fallback response
        """
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [{"text": msg["content"]}]
                }
                for msg in prompt.get("messages", [])
            ],
            "systemInstruction": {
                "parts": [{"text": prompt.get("system", "")}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        # Add web search if enabled
        if web_search_enabled:
            payload["tools"] = [{"googleSearchRetrieval": {}}]
        
        # Extract query and context for potential fallback
        query = ""
        context = ""
        for msg in prompt.get("messages", []):
            if msg["role"] == "user":
                content = msg["content"]
                if "Question:" in content:
                    parts = content.split("Question:", 1)
                    if len(parts) > 1:
                        query = parts[1].strip()
                    if "Context:" in parts[0]:
                        context = parts[0].split("Context:", 1)[1].strip()
        
        # Try to call the LLM API with circuit breaker pattern
        try:
            return self._call_llm_api(url, payload)
            
        except CircuitBreakerError as e:
            # Circuit is open, use fallback immediately
            logger.warning(f"Circuit breaker open for LLM API: {str(e)}")
            if self.fallback_enabled:
                return self.generate_fallback_response(query, context)
            raise
            
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # Network or HTTP error, try fallback
            logger.error(f"LLM API request error: {str(e)}")
            if self.fallback_enabled:
                return self.generate_fallback_response(query, context)
            raise
            
        except (KeyError, ValueError) as e:
            # Response parsing error, try fallback
            logger.error(f"LLM response parsing error: {str(e)}")
            if self.fallback_enabled:
                return self.generate_fallback_response(query, context)
            raise ValueError(f"Failed to parse LLM response: {str(e)}")
    
    @circuit_breaker(
        name="gemini_llm_stream",
        failure_threshold=5,
        recovery_timeout=300  # 5 minutes
    )
    def _stream_llm_api(self, url: str, payload: Dict[str, Any]):
        """
        Stream from the LLM API with circuit breaker pattern.
        
        Args:
            url: The API endpoint URL
            payload: The request payload
            
        Yields:
            Chunks of the LLM response as they become available
        """
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                url,
                json=payload,
                params={"key": self.api_key, "alt": "sse"},
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    # Convert bytes to string
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data = line_str[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if "candidates" in chunk and chunk["candidates"]:
                                candidate = chunk["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            yield part["text"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse chunk: {data}")
                            continue
    
    def stream_response(self, 
                       prompt: Dict[str, Any], 
                       web_search_enabled: bool = False,
                       temperature: float = 0.2,
                       max_tokens: int = 32000):
        """
        Stream a response from the LLM based on the provided prompt.
        With fallback to a non-streaming response if the LLM service fails.
        
        Args:
            prompt: The prompt to send to the LLM
            web_search_enabled: Whether to enable web search for this request
            temperature: Controls randomness in the response (0.0-1.0)
            max_tokens: Maximum number of tokens to generate
            
        Yields:
            Chunks of the LLM response as they become available
        """
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent"
        
        # Prepare the request payload (same as generate_response)
        payload = {
            "contents": [
                {
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [{"text": msg["content"]}]
                }
                for msg in prompt.get("messages", [])
            ],
            "systemInstruction": {
                "parts": [{"text": prompt.get("system", "")}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        # Add web search if enabled
        if web_search_enabled:
            payload["tools"] = [{"googleSearchRetrieval": {}}]
        
        # Extract query and context for potential fallback
        query = ""
        context = ""
        for msg in prompt.get("messages", []):
            if msg["role"] == "user":
                content = msg["content"]
                if "Question:" in content:
                    parts = content.split("Question:", 1)
                    if len(parts) > 1:
                        query = parts[1].strip()
                    if "Context:" in parts[0]:
                        context = parts[0].split("Context:", 1)[1].strip()
        
        # Try to stream from the LLM API with circuit breaker pattern
        try:
            yield from self._stream_llm_api(url, payload)
            
        except CircuitBreakerError as e:
            # Circuit is open, use fallback immediately
            logger.warning(f"Circuit breaker open for LLM streaming API: {str(e)}")
            if self.fallback_enabled:
                # Return the fallback response as a single chunk
                fallback = self.generate_fallback_response(query, context)
                yield fallback["text"]
            else:
                raise
            
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # Network or HTTP error, try fallback
            logger.error(f"LLM streaming API request error: {str(e)}")
            if self.fallback_enabled:
                # Return the fallback response as a single chunk
                fallback = self.generate_fallback_response(query, context)
                yield fallback["text"]
            else:
                raise
            
        except Exception as e:
            # Any other error, try fallback
            logger.error(f"LLM streaming error: {str(e)}")
            if self.fallback_enabled:
                # Return the fallback response as a single chunk
                fallback = self.generate_fallback_response(query, context)
                yield fallback["text"]
            else:
                raise
    
    @circuit_breaker(
        name="gemini_api_status",
        failure_threshold=3,
        recovery_timeout=60  # 1 minute
    )
    def _check_api_status_with_circuit_breaker(self) -> bool:
        """
        Check if the Gemini API is available and responding with circuit breaker pattern.
        
        Returns:
            bool: True if the API is available
            
        Raises:
            CircuitBreakerError: If the circuit is open
            httpx.RequestError: If there's a network-related error
            httpx.HTTPStatusError: If the API returns an error status code
        """
        response = self.client.get(
            f"{self.base_url}/models",
            params={"key": self.api_key}
        )
        response.raise_for_status()
        return True
    
    def check_api_status(self) -> bool:
        """
        Check if the Gemini API is available and responding.
        
        Returns:
            bool: True if the API is available, False otherwise
        """
        try:
            return self._check_api_status_with_circuit_breaker()
        except Exception as e:
            logger.error(f"API status check failed: {str(e)}")
            return False