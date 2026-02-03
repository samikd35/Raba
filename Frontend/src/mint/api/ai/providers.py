"""
LLM Provider implementations for MINT.

This module defines the LLMProvider abstract base class and concrete implementations
for OpenAI and Google Gemini.
"""

import json
import time
import re
from typing import Dict, List, Optional, Any, Literal
import asyncio
import openai
import os
import logging
import time
# Use the correct LangChain imports
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger(__name__)

from ...providers.registry import Provider, ProviderConfig, ProviderError


class LLMConfig(ProviderConfig):
    """Configuration for LLM providers."""
    provider_type: Literal["llm"] = "llm"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    # Azure OpenAI specific fields
    azure_endpoint: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For gpt-5-mini pattern
    
    class Config:
        extra = "allow"  # Allow extra fields for Azure OpenAI


class LLMResponse(BaseModel):
    """Standardized response from LLM providers."""
    content: Optional[str] = None  # Can be None when tool calls are used
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    
    
class LLMToolResponse(BaseModel):
    """Response from a tool call."""
    name: str
    arguments: Dict[str, Any]
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class LLMProvider(Provider[LLMResponse]):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        """Initialize with LLM-specific configuration."""
        super().__init__(config)
        self.config = config  # Re-assign for proper type inference
        
    async def generate_text(self, prompt: str) -> LLMResponse:
        """Generate text from a prompt."""
        raise NotImplementedError("Subclasses must implement generate_text method")
    
    async def generate_chat(
        self, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate response to a chat conversation.
        
        Args:
            messages: List of chat messages with role and content
            response_format: Optional format specification for the response (e.g., JSON schema)
                             Can be used to enforce JSON output structure with a schema
            max_tokens: Optional override for max output tokens
            temperature: Optional override for temperature
            
        Returns:
            LLMResponse with generated content
        """
        raise NotImplementedError("Subclasses must implement generate_chat method")
        
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the LLM.
        
        Args:
            messages: Chat messages
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        raise NotImplementedError("Subclasses must implement call_tool method")
    
    def with_circuit_breaker(self, method):
        """Simple circuit breaker pattern implementation."""
        def wrapper(*args, **kwargs):
            for attempt in range(self.config.max_retries):
                try:
                    return method(*args, **kwargs)
                except Exception as e:
                    if attempt == self.config.max_retries - 1:
                        raise ProviderError(f"Failed after {self.config.max_retries} attempts: {str(e)}")
                    time.sleep(2 ** attempt)  # Exponential backoff
        return wrapper


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM Provider."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize OpenAI provider."""
        config = config or LLMConfig(
            provider_name="openai",
            api_key_env_var="OPENAI_API_KEY",
            model_name="gpt-4.1-mini",
        )
        super().__init__(config)
        
        # Explicitly check for API key in environment and validate it
        self.api_key = os.environ.get("OPENAI_API_KEY") or self.api_key
        
        # Simple validation to avoid using placeholder keys
        invalid_placeholders = ["your_api_key_here", "YOUR_API_KEY", "sk-placeholder", "", None]
        # Azure OpenAI keys do not use the "sk-" prefix, so only check for
        # explicit placeholder values or an empty key.
        if self.api_key in invalid_placeholders or not self.api_key:
            logger.warning("Invalid or missing OpenAI API key; looking for alternative sources")

            # Try to load from any environment variable that looks like an OpenAI key
            for env_var, value in os.environ.items():
                if env_var.startswith("OPENAI") and "KEY" in env_var and value and value not in invalid_placeholders:
                    self.api_key = value
                    logger.info(f"Found alternative OpenAI API key in {env_var}")
                    break
        
        # Check if this is Azure OpenAI configuration
        self.is_azure = hasattr(self.config, 'azure_endpoint') and self.config.azure_endpoint
        
        if self.is_azure:
            # Use Azure OpenAI configuration with gpt-5-mini pattern
            azure_api_key = getattr(self.config, 'api_key', None) or os.environ.get("AZURE_OPENAI_API_KEY")
            if not azure_api_key:
                logger.error("No valid Azure OpenAI API key found.")
                self.client = None
                self.async_client = None
                self.langchain_client = None
            else:
                logger.info(f"Azure OpenAI API key found (length: {len(azure_api_key)}), initializing Azure clients")
                
                # Always set api_version for Azure OpenAI
                self.api_version = getattr(self.config, 'api_version', None) or os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
                
                # Build base_url for Azure OpenAI with deployment name
                base_url = getattr(self.config, 'base_url', None)
                if not base_url:
                    # Construct base_url from azure_endpoint with deployment name
                    endpoint = self.config.azure_endpoint.rstrip('/')
                    deployment_name = getattr(self.config, 'deployment_name', None) or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini")
                    # Azure OpenAI base_url format: {endpoint}/openai/deployments/{deployment}/
                    base_url = f"{endpoint}/openai/deployments/{deployment_name}/"
                
                logger.info(f"Using gpt-5-mini base_url: {base_url}")
                
                # Initialize OpenAI client with Azure OpenAI base_url
                # Add timeout to prevent indefinite hangs and default_query for api-version
                self.client = openai.OpenAI(
                    api_key=azure_api_key,
                    base_url=base_url,
                    timeout=120.0,
                    default_query={"api-version": self.api_version}
                )
                
                # Initialize async client for async methods like call_tool
                self.async_client = openai.AsyncOpenAI(
                    api_key=azure_api_key,
                    base_url=base_url,
                    timeout=120.0,
                    default_query={"api-version": self.api_version}
                )
                
                # Initialize LangChain client for Azure OpenAI with base_url
                self.langchain_client = ChatOpenAI(
                    model=self.config.model_name,
                    temperature=self.config.temperature,
                    api_key=azure_api_key,
                    base_url=base_url
                )
        else:
            # Regular OpenAI configuration
            if not self.api_key or self.api_key in invalid_placeholders:
                logger.error("No valid OpenAI API key found in environment variables. Provider will fail.")
                logger.error(f"Available env vars: {[k for k in os.environ.keys() if 'KEY' in k]}")
                self.client = None
                self.async_client = None
                self.langchain_client = None
            else:
                logger.info(f"OpenAI API key found (length: {len(self.api_key)}), initializing clients")
                # Initialize direct OpenAI client for tool calling
                # Add timeout to prevent indefinite hangs
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    timeout=120.0  # 120 second timeout for all requests
                )
                
                # Initialize async client for async methods like call_tool
                self.async_client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    timeout=120.0  # 120 second timeout for all requests
                )
                
                # Initialize LangChain client for other operations
                self.langchain_client = ChatOpenAI(
                    model=self.config.model_name,
                    temperature=self.config.temperature,
                    openai_api_key=self.api_key  # Explicitly pass the API key
                )
    
    def health_check(self) -> bool:
        """Check if OpenAI API is operational."""
        if not self.client:
            return False
        try:
            # Simple API call to check connectivity using the configured client
            self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def fallback_available(self) -> bool:
        """OpenAI doesn't have built-in fallbacks."""
        return False
    
    async def generate_text(self, prompt: str) -> LLMResponse:
        """Generate text using OpenAI."""
        if not self.client:
            raise ProviderError("OpenAI client not initialized. Check API key.")
        
        try:
            # Use self.client instead of directly using openai module
            completion = self.client.completions.create(
                model=self.config.model_name,
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens or 32000,
            )
            
            # Extract the simple usage values without nested structures
            usage_dict = None
            if completion.usage:
                usage_dict = {
                    "prompt_tokens": getattr(completion.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(completion.usage, "completion_tokens", 0),
                    "total_tokens": getattr(completion.usage, "total_tokens", 0)
                }
                
            return LLMResponse(
                content=completion.choices[0].text.strip(),
                model=self.config.model_name,
                finish_reason=completion.choices[0].finish_reason,
                usage=usage_dict,
            )
        except Exception as e:
            raise ProviderError(f"OpenAI generation failed: {str(e)}")
    
    async def generate_chat(
        self, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate chat response using OpenAI via LangChain.
        
        Args:
            messages: List of chat messages with role and content
            response_format: Optional format specification for the response (e.g., JSON schema)
            max_tokens: Optional override for max output tokens (uses config default if not specified)
            temperature: Optional override for temperature (uses config default if not specified)
            
        Returns:
            LLMResponse with generated content
        """
        if not self.async_client:
            raise ProviderError("OpenAI async client not initialized. Check API key.")
        
        try:
            # Use direct OpenAI client instead of LangChain for better control over response_format
            # Use passed parameters or fall back to config defaults
            effective_temperature = temperature if temperature is not None else self.config.temperature
            effective_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
            
            # Log the effective parameters being used
            logger.debug(f"🔧 OpenAI generate_chat: max_tokens={effective_max_tokens}, temperature={effective_temperature}, model={self.config.model_name}")
            
            # Build base kwargs
            kwargs = {
                "model": self.config.model_name,
                "messages": messages,
            }
            
            # Add temperature - gpt-5-mini and o1/o3 models only support default (1)
            model_name_lower = self.config.model_name.lower()
            if "gpt-5" in model_name_lower or "o1" in model_name_lower or "o3" in model_name_lower:
                # Don't set temperature for these models - they only support default (1)
                pass
            else:
                kwargs["temperature"] = effective_temperature
            
            # Add max_tokens if specified
            # Use max_completion_tokens for newer models (gpt-5-mini, o1, etc.) that don't support max_tokens
            if effective_max_tokens:
                model_name = self.config.model_name.lower()
                if "gpt-5" in model_name or "o1" in model_name or "o3" in model_name:
                    kwargs["max_completion_tokens"] = effective_max_tokens
                else:
                    kwargs["max_tokens"] = effective_max_tokens
                
            # Add response_format if specified
            if response_format:
                # Handle different schema formats for OpenAI structured outputs
                if response_format.get("type") == "json_schema":
                    if "json_schema" in response_format:
                        # Format: {"type": "json_schema", "json_schema": schema}
                        # Need to convert to: {"type": "json_schema", "json_schema": {"name": "...", "schema": {...}}}
                        schema_obj = response_format["json_schema"]
                        
                        if isinstance(schema_obj, dict) and "name" in schema_obj and "schema" not in schema_obj:
                            # Schema object has name but needs to be wrapped
                            schema_data = schema_obj.copy()
                            name = schema_data.pop("name")
                            
                            kwargs["response_format"] = {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": name,
                                    "schema": schema_data
                                }
                            }
                        else:
                            # Already in correct nested format or handle as-is
                            kwargs["response_format"] = response_format
                    else:
                        # Convert schema to nested format expected by OpenAI
                        schema_data = response_format.copy()
                        schema_data.pop("type", None)
                        
                        kwargs["response_format"] = {
                            "type": "json_schema",
                            "json_schema": {
                                "name": schema_data.get("name", "response"),
                                "schema": {k: v for k, v in schema_data.items() if k != "name"}
                            }
                        }
                else:
                    # Use the format as-is for non-JSON schema formats
                    kwargs["response_format"] = response_format
            
            # Make the API call using async client
            completion = await self.async_client.chat.completions.create(**kwargs)
            
            # Extract usage information
            usage_dict = None
            if completion.usage:
                usage_dict = {
                    "prompt_tokens": getattr(completion.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(completion.usage, "completion_tokens", 0),
                    "total_tokens": getattr(completion.usage, "total_tokens", 0)
                }
            
            # Get content from response, handle None/empty case
            message = completion.choices[0].message
            content = message.content
            finish_reason = completion.choices[0].finish_reason
            
            # Check for refusal (gpt-5-mini/o1/o3 models can refuse)
            refusal = getattr(message, 'refusal', None)
            if refusal:
                logger.error(f"LLM refused to respond: {refusal}")
                # Return the refusal as content so caller can handle it
                content = f"[REFUSAL] {refusal}"
            elif content is None or content == "":
                # Check if this is a tool call response (content can be None when tools are called)
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    logger.warning("Response has tool_calls but generate_chat was called instead of call_tool. Content is None.")
                else:
                    logger.warning(f"LLM returned empty content. Finish reason: {finish_reason}, model: {self.config.model_name}")
                    # Log more details for debugging
                    logger.warning(f"Full message object: {message}")
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                finish_reason=completion.choices[0].finish_reason,
                usage=usage_dict,
            )
        except Exception as e:
            raise ProviderError(f"OpenAI chat generation failed: {str(e)}")
    
    async def generate_responses(
        self,
        messages: List[Dict[str, str]],
        reasoning_effort: str = "minimal",
        verbosity: str = "low",
        max_output_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Generate response using the OpenAI Responses API (gpt-5-mini and newer).
        
        This is the centralized implementation for the Responses API migration.
        Use this method instead of generate_chat() for gpt-5-mini models to gain
        access to reasoning.effort and text.verbosity parameters.
        
        MIGRATION FROM CHAT COMPLETIONS API:
        - client.chat.completions.create() → client.responses.create()
        - messages=[...] → input=[...]
        - resp.choices[0].message.content → resp.output_text
        - temperature=0.2 → reasoning={"effort": "minimal"}, text={"verbosity": "low"}
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            reasoning_effort: Controls reasoning depth - "minimal", "low", "medium", "high"
                             Use "minimal" for factually grounded, direct responses
            verbosity: Controls output expansiveness - "low", "medium", "high"
                       Use "low" for concise, focused outputs
            max_output_tokens: Maximum tokens in response (default: uses config or 16000)
            response_format: Optional format specification for structured output
            
        Returns:
            LLMResponse with content, model, usage, and finish_reason
            
        Example:
            >>> provider = OpenAIProvider(config)
            >>> response = await provider.generate_responses(
            ...     messages=[
            ...         {"role": "system", "content": "You are a helpful assistant."},
            ...         {"role": "user", "content": "What is 2+2?"}
            ...     ],
            ...     reasoning_effort="minimal",
            ...     verbosity="low"
            ... )
            >>> print(response.content)
        """
        if not self.async_client:
            raise ProviderError("OpenAI async client not initialized. Check API key.")
        
        # Validate reasoning_effort parameter
        valid_efforts = ["minimal", "low", "medium", "high"]
        if reasoning_effort not in valid_efforts:
            logger.warning(f"Invalid reasoning_effort '{reasoning_effort}', defaulting to 'minimal'")
            reasoning_effort = "minimal"
        
        # Validate verbosity parameter
        valid_verbosity = ["low", "medium", "high"]
        if verbosity not in valid_verbosity:
            logger.warning(f"Invalid verbosity '{verbosity}', defaulting to 'low'")
            verbosity = "low"
        
        # Determine max_output_tokens
        effective_max_tokens = max_output_tokens or self.config.max_tokens or 16000
        
        # Azure OpenAI doesn't support Responses API, use Chat Completions instead
        if getattr(self, 'is_azure', False):
            logger.info(
                f"📤 AZURE CHAT COMPLETIONS: model={self.config.model_name}, "
                f"max_tokens={effective_max_tokens}"
            )
            
            try:
                # Build kwargs for Chat Completions API
                kwargs = {
                    "model": self.config.model_name,
                    "messages": messages,
                    "max_completion_tokens": effective_max_tokens
                }
                
                # Add response_format if specified
                if response_format:
                    kwargs["response_format"] = response_format
                
                # Call Chat Completions API
                response = await self.async_client.chat.completions.create(**kwargs)
                
                # Extract content from Chat Completions response
                content = response.choices[0].message.content if response.choices else ""
                
                # Extract usage information
                usage_dict = None
                if hasattr(response, 'usage') and response.usage:
                    usage_dict = {
                        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                        "total_tokens": getattr(response.usage, "total_tokens", 0)
                    }
                
                # Get finish reason
                finish_reason = response.choices[0].finish_reason if response.choices else None
                
                # Log success
                token_info = usage_dict.get('total_tokens', 'N/A') if usage_dict else 'N/A'
                logger.info(
                    f"✅ AZURE CHAT COMPLETIONS SUCCESS: {len(content) if content else 0} chars, "
                    f"tokens={token_info}"
                )
                
                return LLMResponse(
                    content=content,
                    model=self.config.model_name,
                    finish_reason=finish_reason,
                    usage=usage_dict
                )
                
            except Exception as e:
                logger.error(f"❌ AZURE CHAT COMPLETIONS ERROR: {type(e).__name__}: {str(e)}")
                raise ProviderError(f"Azure OpenAI Chat Completions failed: {str(e)}")
        
        # Standard OpenAI Responses API
        logger.info(
            f"📤 RESPONSES API: model={self.config.model_name}, "
            f"reasoning.effort={reasoning_effort}, text.verbosity={verbosity}, "
            f"max_output_tokens={effective_max_tokens}"
        )
        
        try:
            # Build kwargs for Responses API
            kwargs = {
                "model": self.config.model_name,
                "input": messages,  # Responses API uses 'input' instead of 'messages'
                "reasoning": {"effort": reasoning_effort},
                "text": {"verbosity": verbosity},
                "max_output_tokens": effective_max_tokens
            }
            
            # Add response_format if specified (for structured outputs)
            # IMPORTANT: Responses API requires text.format.name for json_schema types
            if response_format:
                if response_format.get("type") == "json_schema":
                    # Responses API format: {"type": "json_schema", "name": "...", "schema": {...}}
                    json_schema = response_format.get("json_schema", {})
                    kwargs["text"]["format"] = {
                        "type": "json_schema",
                        "name": json_schema.get("name", "response_schema"),
                        "schema": json_schema.get("schema", json_schema)
                    }
                elif response_format.get("type") == "json_object":
                    # For simple JSON object output, use text format
                    kwargs["text"]["format"] = {"type": "json_object"}
                else:
                    # Pass through other formats (e.g., text)
                    kwargs["text"]["format"] = response_format
            
            # Call the Responses API
            response = await self.async_client.responses.create(**kwargs)
            
            # Extract output using Responses API accessor
            # Responses API: resp.output_text instead of resp.choices[0].message.content
            content = response.output_text
            
            # Extract usage information
            usage_dict = None
            if hasattr(response, 'usage') and response.usage:
                usage_dict = {
                    "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                    "completion_tokens": getattr(response.usage, "output_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0)
                }
            
            # Get finish reason if available
            finish_reason = None
            if hasattr(response, 'status'):
                finish_reason = response.status
            
            # Log success
            token_info = usage_dict.get('total_tokens', 'N/A') if usage_dict else 'N/A'
            logger.info(
                f"✅ RESPONSES API SUCCESS: {len(content) if content else 0} chars, "
                f"tokens={token_info}"
            )
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                finish_reason=finish_reason,
                usage=usage_dict
            )
            
        except Exception as e:
            logger.error(f"❌ RESPONSES API ERROR: {type(e).__name__}: {str(e)}")
            raise ProviderError(f"OpenAI Responses API failed: {str(e)}")
    
    async def generate_responses_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        reasoning_effort: str = "minimal",
        verbosity: str = "low",
        max_output_tokens: Optional[int] = None
    ) -> LLMToolResponse:
        """
        Call tools/functions using the OpenAI Responses API (gpt-5-mini and newer).
        
        This is the Responses API equivalent of call_tool() for gpt-5-mini models.
        
        Args:
            messages: Chat messages in OpenAI format
            tools: List of tools/functions in OpenAI format
            reasoning_effort: Controls reasoning depth - "minimal", "low", "medium", "high"
            verbosity: Controls output expansiveness - "low", "medium", "high"
            max_output_tokens: Maximum tokens in response
            
        Returns:
            LLMToolResponse with tool call results
        """
        if not self.async_client:
            raise ProviderError("OpenAI async client not initialized. Check API key.")
        
        # Validate parameters
        valid_efforts = ["minimal", "low", "medium", "high"]
        if reasoning_effort not in valid_efforts:
            reasoning_effort = "minimal"
        
        valid_verbosity = ["low", "medium", "high"]
        if verbosity not in valid_verbosity:
            verbosity = "low"
        
        effective_max_tokens = max_output_tokens or self.config.max_tokens or 16000
        
        # Azure OpenAI doesn't support Responses API, use Chat Completions with tools
        if getattr(self, 'is_azure', False):
            logger.info(
                f"📤 AZURE CHAT COMPLETIONS (tools): model={self.config.model_name}, "
                f"tools={[t.get('function', {}).get('name', 'unknown') for t in tools]}"
            )
            
            try:
                # Build kwargs for Chat Completions API with tools
                kwargs = {
                    "model": self.config.model_name,
                    "messages": messages,
                    "tools": tools,  # Chat Completions uses original tool format
                    "tool_choice": "required",
                    "max_completion_tokens": effective_max_tokens
                }
                
                # Call Chat Completions API
                response = await self.async_client.chat.completions.create(**kwargs)
                
                # Extract usage information
                usage_dict = {}
                if hasattr(response, 'usage') and response.usage:
                    usage_dict = {
                        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                        "total_tokens": getattr(response.usage, "total_tokens", 0)
                    }
                
                # Check for tool calls in response
                if response.choices and response.choices[0].message.tool_calls:
                    tool_call = response.choices[0].message.tool_calls[0]
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    logger.info(f"✅ AZURE CHAT COMPLETIONS (tools) SUCCESS: {tool_call.function.name}")
                    
                    return LLMToolResponse(
                        name=tool_call.function.name,
                        arguments=arguments,
                        model=self.config.model_name,
                        finish_reason=response.choices[0].finish_reason,
                        usage=usage_dict
                    )
                
                # No tool calls, try to parse content as JSON
                content = response.choices[0].message.content if response.choices else ""
                if content:
                    try:
                        parsed = json.loads(content)
                        if "name" in parsed and "arguments" in parsed:
                            return LLMToolResponse(
                                name=parsed["name"],
                                arguments=parsed.get("arguments", {}),
                                model=self.config.model_name,
                                finish_reason=response.choices[0].finish_reason,
                                usage=usage_dict
                            )
                    except json.JSONDecodeError:
                        pass
                
                raise ProviderError("Azure Chat Completions did not return any tool calls")
                
            except Exception as e:
                logger.error(f"❌ AZURE CHAT COMPLETIONS (tools) ERROR: {type(e).__name__}: {str(e)}")
                raise ProviderError(f"Azure OpenAI Chat Completions tool calling failed: {str(e)}")
        
        logger.info(
            f"📤 RESPONSES API (tools): model={self.config.model_name}, "
            f"tools={[t.get('function', {}).get('name', 'unknown') for t in tools]}"
        )
        
        try:
            # Format tools for Responses API
            # IMPORTANT: Responses API uses a DIFFERENT tool format than chat completions
            # Chat completions: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
            # Responses API: {"type": "function", "name": ..., "description": ..., "parameters": ...}
            formatted_tools = []
            for tool in tools:
                if "function" in tool:
                    # Convert chat completions format to Responses API format
                    func = tool["function"]
                    formatted_tools.append({
                        "type": "function",
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {})
                    })
                elif "type" in tool and tool["type"] == "function" and "name" in tool:
                    # Already in Responses API format
                    formatted_tools.append(tool)
            
            if not formatted_tools:
                raise ProviderError("No valid tools provided")
            
            # Build kwargs for Responses API with tools
            kwargs = {
                "model": self.config.model_name,
                "input": messages,
                "tools": formatted_tools,
                "tool_choice": "required",  # Force the model to use a tool
                "reasoning": {"effort": reasoning_effort},
                "text": {"verbosity": verbosity},
                "max_output_tokens": effective_max_tokens
            }
            
            # Call the Responses API
            response = await self.async_client.responses.create(**kwargs)
            
            # Extract usage information
            usage_dict = {}
            if hasattr(response, 'usage') and response.usage:
                usage_dict = {
                    "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                    "completion_tokens": getattr(response.usage, "output_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0)
                }
            
            # Check for tool calls in output
            # Responses API returns tool calls in response.output
            if hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'function_call':
                        # Parse the function call
                        try:
                            arguments = json.loads(output_item.arguments) if isinstance(output_item.arguments, str) else output_item.arguments
                        except json.JSONDecodeError:
                            arguments = {"raw": output_item.arguments}
                        
                        return LLMToolResponse(
                            name=output_item.name,
                            arguments=arguments,
                            model=self.config.model_name,
                            finish_reason=getattr(response, 'status', None),
                            usage=usage_dict
                        )
            
            # If no tool call found, try to parse output_text as JSON
            if response.output_text:
                try:
                    content_json = json.loads(response.output_text)
                    # formatted_tools are already flattened - 'name' is at top level, not under 'function'
                    first_tool_name = formatted_tools[0].get('name', 'unknown') if formatted_tools else 'unknown'
                    
                    return LLMToolResponse(
                        name=first_tool_name,
                        arguments=content_json,
                        model=self.config.model_name,
                        finish_reason="content_fallback",
                        usage=usage_dict
                    )
                except json.JSONDecodeError:
                    pass
            
            raise ProviderError("Responses API did not return any tool calls")
            
        except Exception as e:
            logger.error(f"❌ RESPONSES API (tools) ERROR: {type(e).__name__}: {str(e)}")
            raise ProviderError(f"OpenAI Responses API tool calling failed: {str(e)}")
            
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the OpenAI API.
        
        Args:
            messages: Chat messages in the OpenAI format
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        if not self.api_key:
            raise ProviderError("OpenAI API key not set")
        
        try:
            # All GPT-4.1 models and Azure deployments support tool calls reliably
            model_name = self.config.model_name
            tool_compatible_models = [
                "gpt-4o-mini", 
                "gpt-4.1-2025-04-14", 
                "gpt-4.1-mini",
                "gpt-5-mini",  # Azure gpt-5-mini deployment
                "gpt41",      # Legacy Azure deployment for gpt-4.1
                "gpt41mini",
                "gpt41nano",   # Legacy Azure deployment for gpt-4.1-mini
            ]
            
            # Check if model is tool compatible (most modern models are)
            is_tool_compatible = any(name in model_name for name in tool_compatible_models) or "gpt-4" in model_name
            
            if not is_tool_compatible:
                logger.warning(f"Model {model_name} might not support tool calls reliably.")
                # Note: Removed Gemini fallback as requested - all GPT-4.1 models support tools
        
            # Use the async client instance for async methods
            if not self.async_client:
                raise ProviderError("OpenAI async client not initialized. Check API key.")
            
            # Ensure all tools have the correct format with 'type' field
            formatted_tools = []
            for tool in tools:
                if "function" in tool:
                    # Structure the tool correctly for OpenAI
                    formatted_tool = {"type": "function"}
                    # Copy the function definition
                    formatted_tool["function"] = tool["function"]
                    formatted_tools.append(formatted_tool)
                elif "type" in tool and tool["type"] == "function":
                    # Already correctly formatted
                    formatted_tools.append(tool)
                else:
                    logger.warning(f"Skipping invalid tool format: {tool}")
            
            if not formatted_tools:
                raise ProviderError("No valid tools provided")
            
            # Call the OpenAI API with proper tool format and force tool usage
            # For best tool calling, force the model to use the first tool
            first_tool = formatted_tools[0]['function']['name']
            force_tool = {"type": "function", "function": {"name": first_tool}}
            
            # Build kwargs for API call
            # Use max_completion_tokens for newer models (gpt-5-mini, o1, etc.)
            model_name_lower = model_name.lower()
            api_kwargs = {
                "model": model_name,
                "messages": messages,
                "tools": formatted_tools,
                "tool_choice": force_tool,
            }
            
            # Add temperature - gpt-5-mini and o1/o3 models only support default (1)
            if "gpt-5" in model_name_lower or "o1" in model_name_lower or "o3" in model_name_lower:
                # Don't set temperature for these models
                pass
            else:
                api_kwargs["temperature"] = self.config.temperature
            
            if self.config.max_tokens:
                if "gpt-5" in model_name_lower or "o1" in model_name_lower or "o3" in model_name_lower:
                    api_kwargs["max_completion_tokens"] = self.config.max_tokens
                else:
                    api_kwargs["max_tokens"] = self.config.max_tokens
            
            response = await self.async_client.chat.completions.create(**api_kwargs)
            
            # Process the response
            message = response.choices[0].message
            
            # Check if the model called a tool
            if message.tool_calls and len(message.tool_calls) > 0:
                tool_call = message.tool_calls[0]  # Take the first tool call
                
                # Extract usage data
                usage_data = {}
                if response.usage:
                    usage_data = {
                        "completion_tokens": response.usage.completion_tokens,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                
                # Attempt to parse JSON with enhanced error handling
                try:
                    # First attempt to parse the JSON as is
                    parsed_arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as json_err:
                    # Log detailed information about the parsing error
                    error_position = json_err.pos
                    error_msg = str(json_err)
                    logger.error(f"JSON parsing error at position {error_position}: {error_msg}")
                    
                    # Get the original arguments string
                    arguments_str = tool_call.function.arguments
                    
                    # Debug logging for context around error
                    context_start = max(0, error_position - 50)
                    context_end = min(len(arguments_str), error_position + 50)
                    logger.error(f"Context around error: ...{arguments_str[context_start:context_end]}...")
                    
                    # Initialize variables for error recovery
                    fixed = False
                    fixed_str = arguments_str
                    
                    # Case 1: Unterminated string errors
                    if "Unterminated string" in error_msg:
                        # Try multiple approaches to fix unterminated strings
                        # Approach 1: Add a quote at the error position
                        fixed_str = arguments_str[:error_position] + '"' + arguments_str[error_position:]
                        
                        # Approach 2: If that doesn't work, try to clean up the entire structure
                        if not fixed:
                            # Remove JavaScript-like comments and code
                            cleaned = re.sub(r'//.*?$', '', arguments_str, flags=re.MULTILINE)
                            cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
                            
                            # Fix malformed arrays with incomplete strings
                            cleaned = re.sub(r'\[\s*"\s*\]', '[]', cleaned)  # Empty arrays with quotes
                            cleaned = re.sub(r'\[\s*"[^"]*"\s*\]\s*,\s*"\s*\]', '[]', cleaned)  # Malformed nested arrays
                            cleaned = re.sub(r'"\s*\]\s*,\s*"\s*\]', '"]]', cleaned)  # Fix broken array endings
                            
                            # Fix incomplete key-value pairs
                            cleaned = re.sub(r'"\s*:\s*"\s*\]', '":""]', cleaned)
                            
                            # Remove trailing JavaScript-like code
                            if '));' in cleaned:
                                cleaned = cleaned.split('));')[0]
                            
                            fixed_str = cleaned
                        
                        fixed = True
                        logger.info(f"Attempted to fix unterminated string at position {error_position}")
                    
                    # Case 2: Missing comma between elements
                    elif "Expecting ',' delimiter" in error_msg:
                        # Add a comma at the position of the error
                        fixed_str = arguments_str[:error_position] + ',' + arguments_str[error_position:]
                        fixed = True
                        logger.info(f"Attempted to fix missing comma at position {error_position}")
                    
                    # Case 3: Extra comma before closing bracket/brace
                    elif "Expecting property name" in error_msg:
                        # Remove the trailing comma
                        if error_position > 0 and arguments_str[error_position-1] == ',':
                            fixed_str = arguments_str[:error_position-1] + arguments_str[error_position:]
                            fixed = True
                            logger.info(f"Attempted to fix trailing comma at position {error_position-1}")
                    
                    # Case 4: Missing colon between key and value
                    elif "Expecting ':' delimiter" in error_msg:
                        # Add a colon at the position of the error
                        fixed_str = arguments_str[:error_position] + ':' + arguments_str[error_position:]
                        fixed = True
                        logger.info(f"Attempted to fix missing colon at position {error_position}")
                        
                    # Case 5: Malformed JSON structure with extra/missing brackets
                    elif "Extra data" in error_msg or "Expecting value" in error_msg:
                        # Try to extract a valid JSON object if possible
                        json_pattern = r'\{[^{}]*((\{[^{}]*\})[^{}]*)*\}'
                        matches = re.findall(json_pattern, arguments_str)
                        if matches:
                            fixed_str = matches[0][0] if matches[0][0] else matches[0]
                            fixed = True
                            logger.info("Attempted to extract valid JSON object from malformed structure")
                    
                    # Try to parse the fixed string if any fixes were applied
                    if fixed:
                        try:
                            parsed_arguments = json.loads(fixed_str)
                            logger.info("Successfully recovered from JSON parsing error")
                        except json.JSONDecodeError as retry_err:
                            logger.error(f"Fix attempt failed, trying additional recovery: {retry_err}")
                            
                            # Advanced recovery: try cleaning up common patterns
                            try:
                                # Replace problematic patterns
                                cleaned = re.sub(r'\s+', ' ', fixed_str)  # Normalize whitespace
                                cleaned = re.sub(r',\s*([\]\}])', r'\1', cleaned)  # Remove trailing commas
                                cleaned = re.sub(r'(["\w])\s*([{\[])', r'\1,\2', cleaned)  # Add missing commas
                                cleaned = re.sub(r'(["\w])\s+(["\w])', r'\1,"\2', cleaned)  # Fix missing quotes/commas
                                
                                # Additional cleaning for severely malformed JSON
                                cleaned = re.sub(r'"\s*\]\s*,\s*"\s*\]', '"]', cleaned)  # Fix nested array issues
                                cleaned = re.sub(r'\[\s*"\s*\]', '[]', cleaned)  # Fix empty arrays with quotes
                                cleaned = re.sub(r'"\s*:\s*"\s*\]', '":""', cleaned)  # Fix incomplete values
                                
                                # Attempt to parse again with cleaned string
                                parsed_arguments = json.loads(cleaned)
                                logger.info("Successfully recovered using advanced cleaning")
                            except Exception:
                                # Last attempt: Try to salvage by using multiple regex patterns
                                try:
                                    # Try different patterns to extract valid JSON
                                    patterns = [
                                        r'\{[^}]*"[^"]*"\s*:\s*\{[^}]*\}[^}]*\}',  # Nested object pattern
                                        r'\{[^}]*"[^"]*"\s*:\s*\[[^\]]*\][^}]*\}',  # Array value pattern
                                        r'\{[^}]*"[^"]*"\s*:\s*"[^"]*"[^}]*\}',   # String value pattern
                                        r'\{.*?\}',  # Any complete object
                                    ]
                                    
                                    potential_json = None
                                    for pattern in patterns:
                                        match = re.search(pattern, arguments_str, re.DOTALL)
                                        if match:
                                            potential_json = match.group(0)
                                            # Clean up the extracted JSON
                                            potential_json = re.sub(r'//.*?$', '', potential_json, flags=re.MULTILINE)
                                            potential_json = re.sub(r'/\*.*?\*/', '', potential_json, flags=re.DOTALL)
                                            try:
                                                parsed_arguments = json.loads(potential_json)
                                                logger.info(f"Recovered JSON using pattern: {pattern[:30]}...")
                                                break
                                            except:
                                                continue
                                    
                                    if not potential_json or 'parsed_arguments' not in locals():
                                        # Final fallback: create a minimal valid response
                                        logger.warning("Creating fallback response due to JSON parsing failure")
                                        parsed_arguments = {
                                            "error": "JSON parsing failed",
                                            "original_response": arguments_str[:200] + "..." if len(arguments_str) > 200 else arguments_str,
                                            "analysis_result": "Error occurred during analysis due to malformed response"
                                        }
                                except Exception as final_err:
                                    # If all recovery attempts fail, create a fallback response
                                    logger.error(f"All JSON recovery attempts failed. Original error: {error_msg}")
                                    logger.error(f"Final recovery error: {str(final_err)}")
                                    
                                    # Create a fallback response instead of crashing
                                    parsed_arguments = {
                                        "error": "Critical JSON parsing failure",
                                        "original_error": error_msg,
                                        "recovery_error": str(final_err),
                                        "partial_response": arguments_str[:500] + "..." if len(arguments_str) > 500 else arguments_str,
                                        "analysis_result": "Analysis failed due to malformed LLM response",
                                        "fallback_used": True
                                    }
                                    logger.warning("Using fallback response structure due to complete JSON parsing failure")
                    else:
                        # If no fixes were attempted, create a fallback response
                        logger.error(f"No applicable fixes found for this JSON error type: {error_msg}")
                        logger.warning("Creating fallback response for unhandled JSON error")
                        parsed_arguments = {
                            "error": "Unhandled JSON parsing error",
                            "error_type": error_msg,
                            "original_response": arguments_str[:300] + "..." if len(arguments_str) > 300 else arguments_str,
                            "analysis_result": "Analysis could not be completed due to response format issues",
                            "fallback_used": True
                        }
                
                # Return the structured tool response
                return LLMToolResponse(
                    name=tool_call.function.name,
                    arguments=parsed_arguments,
                    model=model_name,
                    finish_reason=response.choices[0].finish_reason,
                    usage=usage_data
                )
            else:
                # No tool was called despite being requested
                # Try to parse the content as JSON if available (gpt-5-mini sometimes returns content instead of tool calls)
                if message.content:
                    logger.warning(f"Model did not call tool, but returned content. Attempting to parse content as JSON.")
                    try:
                        # Try to parse the content as JSON
                        content_json = json.loads(message.content)
                        
                        # Create a synthetic tool response from the content
                        usage_data = {}
                        if response.usage:
                            usage_data = {
                                "completion_tokens": response.usage.completion_tokens,
                                "prompt_tokens": response.usage.prompt_tokens,
                                "total_tokens": response.usage.total_tokens
                            }
                        
                        return LLMToolResponse(
                            name=first_tool,  # Use the tool name we tried to call
                            arguments=content_json,
                            model=model_name,
                            finish_reason="content_fallback",
                            usage=usage_data
                        )
                    except json.JSONDecodeError:
                        logger.error(f"Content is not valid JSON: {message.content[:200]}...")
                        raise ProviderError("OpenAI did not call any tool and content is not valid JSON")
                else:
                    raise ProviderError("OpenAI did not call any tool despite being requested to do so")
                
        except Exception as e:
            # Handle any errors that occur during the API call
            raise ProviderError(f"OpenAI tool calling failed: {str(e)}")



class GeminiProvider(LLMProvider):
    """Google Gemini implementation of LLM Provider."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Gemini provider."""
        config = config or LLMConfig(
            provider_name="gemini",
            api_key_env_var="GOOGLE_API_KEY",
            model_name="gemini-2.5-flash", # Updated to use newer model with longer context
        )
        super().__init__(config)
        self.client = None
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.config.model_name)
            
    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> List[Dict]:
        """Convert OpenAI-style messages to Gemini format.
        
        Args:
            messages: List of OpenAI format messages with role and content
            
            
        Returns:
            List of messages in Gemini format
        """
        gemini_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                # Gemini doesn't have system messages, convert to user
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "user":
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [content]})
            # Ignore any other roles
                
        return gemini_messages
    
    def health_check(self) -> bool:
        """Check if Gemini API is operational."""
        if not self.api_key or not self.client:
            return False
        try:
            # Test connectivity with a simple request
            genai.list_models()
            return True
        except Exception:
            return False
    
    def fallback_available(self) -> bool:
        """Gemini doesn't have built-in fallbacks."""
        return False
    
    async def generate_text(self, prompt: str) -> LLMResponse:
        """Generate text using Gemini."""
        if not self.client:
            raise ProviderError("Gemini client not initialized. Check API key.")
        
        try:
            response = self.client.generate_content(prompt)

            # Safely extract text from response similar to generate_chat
            content = ""
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                content += part.text

            # Safely handle response content access
            if not content:
                try:
                    # First try structured access to the response parts
                    if hasattr(response, 'content'):
                        content = response.content
                    # Don't directly access response.text which fails with content filtering
                    # Instead, check if we can get text representation of response
                    elif hasattr(response, '__str__'):
                        content = str(response)
                except ValueError as content_error:
                    # Specifically handle the case when content accessor fails
                    # But log at debug level instead of warning to avoid unnecessary logs
                    logger.debug(f"Could not access response content: {str(content_error)}")
                    # Continue execution - we'll handle empty content below
                
            # If content is still empty, try to get useful information for error reporting
            if not content:
                finish_reason = "unknown"
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                    
                    # Add fallback content for specific finish reasons
                    if finish_reason == 2:  # This is the code for content filtering
                        logger.warning("Gemini response was blocked by content filtering")
                        content = "[The response was filtered due to safety concerns. Please try rephrasing your query.]"                        
                    elif finish_reason == 3:  # This is the code for max tokens
                        logger.warning("Gemini response reached token limit")
                        content = "[The response exceeded the maximum token limit. Try simplifying your request or breaking it into smaller parts.]"                        
                    else:
                        logger.warning(f"Empty response from Gemini. Finish reason: {finish_reason}")
                        content = f"[Empty response from Gemini model with finish reason: {finish_reason}. Please try again.]"

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                usage=None,
            )
        except Exception as e:
            logger.error(f"Error in Gemini text generation: {str(e)}")
            raise ProviderError(f"Gemini generation failed: {str(e)}")
    
    async def generate_chat(
        self, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate chat response using Gemini."""
        if not self.client:
            raise ProviderError("Gemini client not initialized. Check API key.")
        
        try:
            # Convert OpenAI-style messages to Gemini format
            system_content = ""
            gemini_messages = []
            
            # First extract any system message
            for msg in messages:
                if msg.get("role") == "system":
                    system_content = msg.get("content", "")
                    break
            
            # First user message should include system prompt if available
            first_user_msg = True
            
            # Build the conversation history
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                
                # Skip system messages as we handle them separately
                if role == "system":
                    continue
                
                if role == "user":
                    # If this is the first user message and we have a system message,
                    # combine them
                    if first_user_msg and system_content:
                        user_content = f"{system_content}\n\n{content}"
                        gemini_messages.append({"role": "user", "parts": [{"text": user_content}]})
                        first_user_msg = False
                    else:
                        gemini_messages.append({"role": "user", "parts": [{"text": content}]})
                        first_user_msg = False
                elif role == "assistant":
                    gemini_messages.append({"role": "model", "parts": [{"text": content}]})
            
            # If we don't have any messages (unlikely), use system content alone
            if not gemini_messages and system_content:
                gemini_messages.append({"role": "user", "parts": [{"text": system_content}]})
            elif not gemini_messages:
                raise ValueError("No messages to send to Gemini")
            
            # Use generate_content directly with the conversation history
            generation_config = genai.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens or 65535,  # Increase max tokens
                top_p=0.95,  # Add top_p for better quality
            )
            
            # Handle response_format for JSON output if specified
            if response_format and response_format.get("type") in ["json_object", "json_schema"]:
                # Add instructions for JSON output
                json_instruction = "Respond with valid JSON only."
                
                # If schema is provided, add it to the instruction
                if "schema" in response_format or "json_schema" in response_format:
                    schema = response_format.get("schema") or response_format.get("json_schema")
                    json_instruction = f"Respond with valid JSON that follows this schema: {json.dumps(schema)}"
                
                # Add JSON instruction to the last user message
                last_user_idx = -1
                for i in range(len(gemini_messages) - 1, -1, -1):
                    if gemini_messages[i]["role"] == "user":
                        last_user_idx = i
                        break
                
                if last_user_idx >= 0:
                    # Add JSON instruction to the last user message
                    current_text = gemini_messages[last_user_idx]["parts"][0]["text"]
                    gemini_messages[last_user_idx]["parts"][0]["text"] = f"{current_text}\n\n{json_instruction}"
                    
                # Set response mime type to JSON in generation config
                generation_config.response_mime_type = "application/json"
            
            # Log the generation parameters
            logger.info(f"Generating with Gemini model {self.config.model_name}, max_tokens={self.config.max_tokens or 65535}, temp={self.config.temperature}")
            logger.info(f"Input size: {sum(len(str(msg)) for msg in gemini_messages)} characters")
            
            # Generate content
            response = self.client.generate_content(
                gemini_messages,
                generation_config=generation_config,
                safety_settings=[
                    # Adjust safety thresholds to allow more content through
                    {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_HATE", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
                ]
            )
            
            # Safely extract text from response
            content = ""
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                content += part.text
            
            # If content is empty, try content or text attribute as fallback
            if not content:
                try:
                    # First try structured access to the response parts
                    if hasattr(response, 'content'):
                        content = response.content
                    # Don't directly access response.text which fails with content filtering
                    # Instead, check if we can get text representation of response
                    elif hasattr(response, '__str__'):
                        content = str(response)
                except Exception as e_content:
                    # Log at debug level instead of warning to avoid unnecessary logs
                    logger.debug(f"Could not access response content: {e_content}")
                    content = ""
                
            if not content:
                finish_reason = "unknown"
                if hasattr(response, 'candidates') and response.candidates:
                    finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else "unknown"
                logger.warning(f"Empty response from Gemini. Finish reason: {finish_reason}")
                raise ProviderError(f"Empty response from Gemini model {self.config.model_name} with finish reason: {finish_reason}")
                
            logger.info(f"Successfully generated {len(content)} characters of content")
            
            # If JSON was requested, validate that the response is valid JSON
            if response_format and response_format.get("type") in ["json_object", "json_schema"]:
                try:
                    # Try to parse as JSON to validate
                    json.loads(content)
                except json.JSONDecodeError as json_err:
                    logger.warning(f"Gemini returned invalid JSON: {json_err}")
                    # Try to extract JSON from the response if it contains markdown code blocks
                    if "```json" in content:
                        try:
                            # Extract JSON from markdown code block
                            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                            if json_match:
                                extracted_json = json_match.group(1)
                                # Validate the extracted JSON
                                json.loads(extracted_json)
                                # Use the extracted JSON as the content
                                content = extracted_json
                                logger.info("Successfully extracted JSON from markdown code block")
                        except Exception as extract_err:
                            logger.error(f"Failed to extract JSON from markdown: {extract_err}")
                
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                usage=None,
            )
        except Exception as e:
            logger.error(f"Error in Gemini content generation: {str(e)}")
            raise ProviderError(f"Gemini chat generation failed: {str(e)}")
            
    async def call_tool(self, messages: List[Dict[str, str]], tools: List[Dict]) -> LLMToolResponse:
        """Call a tool/function with the Gemini API.
        
        Args:
            messages: Chat messages in the OpenAI format
            tools: List of tools/functions in the OpenAI format
            
        Returns:
            Tool call results with name, arguments and model info
        """
        if not self.api_key:
            raise ProviderError("Google API key not set")
        
        try:
            # Convert OpenAI-style messages to Gemini format
            gemini_messages = self._convert_messages_to_gemini(messages)
            
            # Extract function specs from OpenAI-style tools
            tool_specs = []
            for tool in tools:
                if "function" in tool:
                    # Handle tool format without type field
                    function_spec = {
                        "name": tool["function"]["name"],
                        "description": tool["function"].get("description", ""),
                        "parameters": tool["function"]["parameters"]
                    }
                    tool_specs.append(function_spec)
                elif "type" in tool and tool["type"] == "function" and "function" in tool:
                    # Handle tool format with type field
                    function_spec = {
                        "name": tool["function"]["name"],
                        "description": tool["function"].get("description", ""),
                        "parameters": tool["function"]["parameters"]
                    }
                    tool_specs.append(function_spec)
            
            if not tool_specs:
                raise ProviderError("No valid tool definitions found for Gemini")
                    
            # Configure the model
            genai.configure(api_key=self.api_key)
            
            # Create the model with tool definitions
            model = genai.GenerativeModel(
                self.config.model_name,
                generation_config={
                    "temperature": self.config.temperature,
                },
                tools=tool_specs
            )
            
            # Generate content with the messages
            response = model.generate_content(gemini_messages)
            
            # Check if there's a function call in the response
            if hasattr(response, "candidates") and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call"):
                            func_call = part.function_call
                            
                            # Extract usage data if available
                            usage_data = None
                            if hasattr(response, "usage"):
                                usage_data = {
                                    "prompt_tokens": getattr(response.usage, "prompt_token_count", 0),
                                    "completion_tokens": getattr(response.usage, "candidates_token_count", 0),
                                    "total_tokens": getattr(response.usage, "total_token_count", 0)
                                }
                            
                            # Return the structured tool response
                            return LLMToolResponse(
                                name=func_call.name,
                                arguments=func_call.args,
                                model=self.config.model_name,
                                finish_reason="tool_calls",
                                usage=usage_data
                            )
            
            # If we get here, no function was called
            raise ProviderError("Gemini did not call any function/tool despite being requested to do so")
            
        except ValueError as text_error:
            # Handle the specific case where response.text fails due to content filtering
            if "finish_reason" in str(text_error) and "2" in str(text_error):
                logger.warning(f"Gemini tool call was blocked by content filtering: {str(text_error)}")
                # Return a graceful error response
                return LLMToolResponse(
                    name="error_handler",
                    arguments={"error": "The response was filtered due to safety concerns. Please try rephrasing your query."},
                    model=self.config.model_name,
                    finish_reason="content_filter"
                )
            else:
                logger.error(f"ValueError in Gemini tool call: {str(text_error)}")
                # For other value errors, create a meaningful response
                return LLMToolResponse(
                    name="error_handler",
                    arguments={"error": f"Tool call encountered an error: {str(text_error)}"},
                    model=self.config.model_name,
                    finish_reason="error"
                )
        except Exception as e:
            logger.error(f"Error in Gemini tool call: {str(e)}")
            # Instead of raising an exception, return an error tool response
            return LLMToolResponse(
                name="error_handler",
                arguments={"error": f"Tool call failed: {str(e)}"},
                model=self.config.model_name,
                finish_reason="error"
            )
