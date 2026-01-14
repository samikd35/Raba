"""RABA Gemini Service.

Wrapper for Google GenAI SDK providing structured output generation.
"""

import asyncio
from typing import Any, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

GEMINI_3_FLASH = "gemini-3-flash-preview"
GEMINI_3_PRO = "gemini-3-pro-preview"
GEMINI_2_5_FLASH = "gemini-2.5-flash-preview-05-20"
GEMINI_2_5_PRO = "gemini-2.5-pro-preview-06-05"


class GeminiServiceError(Exception):
    """Base exception for Gemini service errors."""
    pass


class GeminiAPIError(GeminiServiceError):
    """Error from Gemini API call."""
    pass


class GeminiValidationError(GeminiServiceError):
    """Error validating response against schema."""
    pass


class GeminiService:
    """
    Service wrapper for Google GenAI SDK.
    
    Provides structured output generation with Pydantic models,
    text generation, and grounded search capabilities.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.
        
        Args:
            api_key: Google API key. If None, loads from settings.
        """
        self._api_key = api_key or get_settings().google_api_key
        self._client: Optional[genai.Client] = None
        
        if not self._api_key:
            logger.warning("No Google API key configured")
    
    def _get_client(self) -> genai.Client:
        """Get or create GenAI client."""
        if self._client is None:
            if not self._api_key:
                raise GeminiServiceError("Google API key not configured")
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Created GenAI client")
        return self._client
    
    async def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[T],
        model: str = GEMINI_3_FLASH,
        system_instruction: Optional[str] = None,
        thinking_level: str = "low",
        temperature: float = 1.0,
        max_retries: int = 3,
    ) -> T:
        """
        Generate structured output matching a Pydantic model.
        
        Args:
            prompt: User prompt
            response_model: Pydantic model class for response
            model: Gemini model to use
            system_instruction: Optional system instruction
            thinking_level: Thinking depth (minimal, low, medium, high)
            temperature: Generation temperature (default 1.0 per Gemini 3 docs)
            max_retries: Number of retry attempts
            
        Returns:
            Parsed Pydantic model instance
            
        Raises:
            GeminiAPIError: If API call fails
            GeminiValidationError: If response doesn't match schema
        """
        client = self._get_client()
        
        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_json_schema": response_model.model_json_schema(),
            "temperature": temperature,
        }
        
        if thinking_level != "high":
            config["thinking_config"] = types.ThinkingConfig(
                thinking_level=thinking_level
            )
        
        contents = prompt
        if system_instruction:
            config["system_instruction"] = system_instruction
        
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(f"Gemini API call attempt {attempt + 1}/{max_retries}")
                logger.debug(f"Model: {model}, thinking_level: {thinking_level}")
                
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=config,
                )
                
                if not response.text:
                    raise GeminiAPIError("Empty response from Gemini API")
                
                logger.debug(f"Raw response: {response.text[:200]}...")
                
                result = response_model.model_validate_json(response.text)
                logger.info(f"Successfully parsed {response_model.__name__}")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
        
        if isinstance(last_error, GeminiServiceError):
            raise last_error
        raise GeminiAPIError(f"Failed after {max_retries} attempts: {last_error}")
    
    async def generate_text(
        self,
        prompt: str,
        model: str = GEMINI_3_FLASH,
        system_instruction: Optional[str] = None,
        thinking_level: str = "high",
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate plain text response.
        
        Args:
            prompt: User prompt
            model: Gemini model to use
            system_instruction: Optional system instruction
            thinking_level: Thinking depth
            temperature: Generation temperature
            max_output_tokens: Max tokens in response
            
        Returns:
            Generated text
        """
        client = self._get_client()
        
        config: dict[str, Any] = {
            "temperature": temperature,
        }
        
        if thinking_level != "high":
            config["thinking_config"] = types.ThinkingConfig(
                thinking_level=thinking_level
            )
        
        if system_instruction:
            config["system_instruction"] = system_instruction
            
        if max_output_tokens:
            config["max_output_tokens"] = max_output_tokens
        
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=config,
            )
            
            return response.text or ""
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise GeminiAPIError(f"Text generation failed: {e}")
    
    async def generate_with_grounding(
        self,
        prompt: str,
        model: str = GEMINI_3_PRO,
        system_instruction: Optional[str] = None,
        thinking_level: str = "high",
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Generate text with Google Search grounding.
        
        Args:
            prompt: User prompt
            model: Gemini model (Pro recommended for grounding)
            system_instruction: Optional system instruction
            thinking_level: Thinking depth
            
        Returns:
            Tuple of (generated_text, citations)
        """
        client = self._get_client()
        
        config: dict[str, Any] = {
            "tools": [{"google_search": {}}],
            "temperature": 1.0,
        }
        
        if thinking_level != "high":
            config["thinking_config"] = types.ThinkingConfig(
                thinking_level=thinking_level
            )
        
        if system_instruction:
            config["system_instruction"] = system_instruction
        
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=config,
            )
            
            text = response.text or ""
            citations = []
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'grounding_chunks'):
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                citations.append({
                                    "url": getattr(chunk.web, 'uri', ''),
                                    "title": getattr(chunk.web, 'title', ''),
                                })
            
            logger.info(f"Generated grounded response with {len(citations)} citations")
            return text, citations
            
        except Exception as e:
            logger.error(f"Grounded generation failed: {e}")
            raise GeminiAPIError(f"Grounded generation failed: {e}")
    
    def generate_structured_output_sync(
        self,
        prompt: str,
        response_model: Type[T],
        model: str = GEMINI_3_FLASH,
        system_instruction: Optional[str] = None,
        thinking_level: str = "low",
    ) -> T:
        """
        Synchronous version of generate_structured_output.
        
        Use for non-async contexts (e.g., testing).
        """
        return asyncio.run(
            self.generate_structured_output(
                prompt=prompt,
                response_model=response_model,
                model=model,
                system_instruction=system_instruction,
                thinking_level=thinking_level,
            )
        )


_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Get singleton Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
