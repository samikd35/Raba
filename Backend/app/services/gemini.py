"""RABA Gemini Service.

Wrapper for Google GenAI SDK providing structured output generation.
"""

import asyncio
import os
import tempfile
from typing import Any, Optional, Type, TypeVar, cast

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

GEMINI_3_FLASH = "gemini-3-flash-preview"
GEMINI_3_PRO = "gemini-3-pro-preview"
GEMINI_2_5_FLASH = "gemini-2.5-flash"  # Stable version (preview was deprecated)
GEMINI_2_5_PRO = "gemini-2.5-pro"  # Stable version


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
        thinking_budget: int = 0,
        temperature: float = 1.0,
        max_retries: int = 3,
        *,
        video_id: Optional[str] = None,
    ) -> T:
        """
        Generate structured output matching a Pydantic model.

        Args:
            prompt: User prompt
            response_model: Pydantic model class for response
            model: Gemini model to use
            system_instruction: Optional system instruction
            thinking_budget: Token budget for thinking (0 = disabled, default for structured output)
            temperature: Generation temperature (default 1.0 per Gemini 3 docs)
            max_retries: Number of retry attempts

        Returns:
            Parsed Pydantic model instance

        Raises:
            GeminiAPIError: If API call fails
            GeminiValidationError: If response doesn't match schema
        """
        client = self._get_client()

        # Gemini 3 Pro requires thinking_budget > 0. "Budget 0 is invalid. This model only works in thinking mode."
        if "gemini-3-pro" in model.lower() and thinking_budget <= 0:
            thinking_budget = 8192
            logger.debug(
                f"gemini-3-pro requires thinking mode; using thinking_budget={thinking_budget}"
            )

        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_json_schema": response_model.model_json_schema(),
            "temperature": temperature,
        }

        # Disable thinking for most models; Gemini 3 Pro requires it (handled above)
        try:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        except Exception as e:
            logger.debug(f"ThinkingConfig not supported: {e}")

        contents = prompt
        if system_instruction:
            config["system_instruction"] = system_instruction

        last_error = None
        start_time = asyncio.get_event_loop().time()
        for attempt in range(max_retries):
            try:
                logger.debug(f"Gemini API call attempt {attempt + 1}/{max_retries}")
                logger.debug(f"Model: {model}, thinking_budget: {thinking_budget}")

                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=cast(Any, config),
                )

                if not response.text:
                    raise GeminiAPIError("Empty response from Gemini API")

                logger.debug(f"Raw response: {response.text[:200]}...")

                result = response_model.model_validate_json(response.text)
                logger.info(f"Successfully parsed {response_model.__name__}")
                # Monitoring: estimate token usage and record
                try:
                    from app.services.monitoring import get_monitoring_service

                    duration = asyncio.get_event_loop().time() - start_time
                    usage_tokens = self._extract_usage_tokens(response)
                    estimated = usage_tokens is None
                    if usage_tokens:
                        in_tok, out_tok = usage_tokens
                    else:
                        in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
                        out_tok = self._estimate_tokens(response.text)
                    asyncio.create_task(
                        get_monitoring_service().record_text_usage(
                            video_id=video_id,
                            model=model,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            duration_seconds=duration,
                            success=True,
                            metadata={
                                "method": "generate_structured_output",
                                "response_model": response_model.__name__,
                                "estimated": estimated,
                            },
                        )
                    )
                except Exception:
                    pass
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))

        # Monitoring on failure
        try:
            from app.services.monitoring import get_monitoring_service

            duration = asyncio.get_event_loop().time() - start_time
            in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
            asyncio.create_task(
                get_monitoring_service().record_text_usage(
                    video_id=video_id,
                    model=model,
                    input_tokens=in_tok,
                    output_tokens=0,
                    duration_seconds=duration,
                    success=False,
                    error_message=str(last_error),
                    metadata={"method": "generate_structured_output", "estimated": True},
                )
            )
        except Exception:
            pass
        if isinstance(last_error, GeminiServiceError):
            raise last_error
        raise GeminiAPIError(f"Failed after {max_retries} attempts: {last_error}")

    async def generate_structured_output_with_video(
        self,
        prompt: str,
        response_model: Type[T],
        video_bytes: bytes,
        mime_type: str,
        model: str = GEMINI_2_5_FLASH,
        system_instruction: Optional[str] = None,
        thinking_budget: int = 0,
        temperature: float = 1.0,
        max_retries: int = 3,
        *,
        use_file_api: bool = False,
        file_display_name: Optional[str] = None,
        video_id: Optional[str] = None,
    ) -> T:
        """
        Generate structured output from a prompt and a video input.

        Args:
            prompt: User prompt
            response_model: Pydantic model class for response
            video_bytes: Video bytes
            mime_type: Video MIME type
            model: Gemini model to use
            system_instruction: Optional system instruction
            thinking_budget: Token budget for thinking (0 = disabled)
            temperature: Generation temperature
            max_retries: Number of retry attempts
            use_file_api: Whether to upload video via Files API
            file_display_name: Optional display name for uploaded file
            video_id: Optional workflow/video ID for monitoring
        """
        client = self._get_client()

        if "gemini-3-pro" in model.lower() and thinking_budget <= 0:
            thinking_budget = 8192
            logger.debug(
                f"gemini-3-pro requires thinking mode; using thinking_budget={thinking_budget}"
            )

        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_json_schema": response_model.model_json_schema(),
            "temperature": temperature,
        }

        try:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        except Exception as e:
            logger.debug(f"ThinkingConfig not supported: {e}")

        contents: list[Any] = []
        if use_file_api:
            uploaded_file = await self._upload_file(video_bytes, mime_type, file_display_name)
            await self._wait_for_file_active(uploaded_file.name)
            contents.append(
                types.Part(
                    file_data=types.FileData(
                        file_uri=uploaded_file.uri,
                        mime_type=mime_type,
                        display_name=file_display_name,
                    )
                )
            )
        else:
            contents.append(
                types.Part(inline_data=types.Blob(data=video_bytes, mime_type=mime_type))
            )

        contents.append(prompt)

        if system_instruction:
            config["system_instruction"] = system_instruction

        last_error = None
        start_time = asyncio.get_event_loop().time()
        for attempt in range(max_retries):
            try:
                logger.debug(f"Gemini video API call attempt {attempt + 1}/{max_retries}")
                logger.debug(f"Model: {model}, thinking_budget: {thinking_budget}")

                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=cast(Any, config),
                )

                if not response.text:
                    raise GeminiAPIError("Empty response from Gemini API")

                result = response_model.model_validate_json(response.text)
                logger.info(f"Successfully parsed {response_model.__name__} (video)")
                try:
                    from app.services.monitoring import get_monitoring_service

                    duration = asyncio.get_event_loop().time() - start_time
                    usage_tokens = self._extract_usage_tokens(response)
                    estimated = usage_tokens is None
                    if usage_tokens:
                        in_tok, out_tok = usage_tokens
                    else:
                        in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
                        out_tok = self._estimate_tokens(response.text)
                    asyncio.create_task(
                        get_monitoring_service().record_text_usage(
                            video_id=video_id,
                            model=model,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            duration_seconds=duration,
                            success=True,
                            metadata={
                                "method": "generate_structured_output_with_video",
                                "response_model": response_model.__name__,
                                "estimated": estimated,
                                "used_file_api": use_file_api,
                            },
                        )
                    )
                except Exception:
                    pass
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Video attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))

        try:
            from app.services.monitoring import get_monitoring_service

            duration = asyncio.get_event_loop().time() - start_time
            in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
            asyncio.create_task(
                get_monitoring_service().record_text_usage(
                    video_id=video_id,
                    model=model,
                    input_tokens=in_tok,
                    output_tokens=0,
                    duration_seconds=duration,
                    success=False,
                    error_message=str(last_error),
                    metadata={
                        "method": "generate_structured_output_with_video",
                        "estimated": True,
                        "used_file_api": use_file_api,
                    },
                )
            )
        except Exception:
            pass
        if isinstance(last_error, GeminiServiceError):
            raise last_error
        raise GeminiAPIError(f"Failed after {max_retries} attempts: {last_error}")

    async def generate_text(
        self,
        prompt: str,
        model: str = GEMINI_3_FLASH,
        system_instruction: Optional[str] = None,
        thinking_budget: int = 0,
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
        *,
        video_id: Optional[str] = None,
    ) -> str:
        """
        Generate plain text response.

        Args:
            prompt: User prompt
            model: Gemini model to use
            system_instruction: Optional system instruction
            thinking_budget: Token budget for thinking (0 = disabled by default)
            temperature: Generation temperature
            max_output_tokens: Max tokens in response

        Returns:
            Generated text
        """
        client = self._get_client()

        # Gemini 3 Pro requires thinking_budget > 0
        if "gemini-3-pro" in model.lower() and thinking_budget <= 0:
            thinking_budget = 8192

        config: dict[str, Any] = {
            "temperature": temperature,
        }

        # Disable thinking by default to avoid thought_signature warnings
        try:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        except Exception as e:
            logger.debug(f"ThinkingConfig not supported: {e}")

        if system_instruction:
            config["system_instruction"] = system_instruction

        if max_output_tokens:
            config["max_output_tokens"] = max_output_tokens

        start_time = asyncio.get_event_loop().time()
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=cast(Any, config),
            )

            text = response.text or ""
            # Monitoring
            try:
                from app.services.monitoring import get_monitoring_service

                duration = asyncio.get_event_loop().time() - start_time
                usage_tokens = self._extract_usage_tokens(response)
                estimated = usage_tokens is None
                if usage_tokens:
                    in_tok, out_tok = usage_tokens
                else:
                    in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
                    out_tok = self._estimate_tokens(text)
                asyncio.create_task(
                    get_monitoring_service().record_text_usage(
                        video_id=video_id,
                        model=model,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        duration_seconds=duration,
                        success=True,
                        metadata={"method": "generate_text", "estimated": estimated},
                    )
                )
            except Exception:
                pass
            return text

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            try:
                from app.services.monitoring import get_monitoring_service

                duration = asyncio.get_event_loop().time() - start_time
                in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
                asyncio.create_task(
                    get_monitoring_service().record_text_usage(
                        video_id=video_id,
                        model=model,
                        input_tokens=in_tok,
                        output_tokens=0,
                        duration_seconds=duration,
                        success=False,
                        error_message=str(e),
                        metadata={"method": "generate_text", "estimated": True},
                    )
                )
            except Exception:
                pass
            raise GeminiAPIError(f"Text generation failed: {e}")

    async def generate_with_grounding(
        self,
        prompt: str,
        model: str = GEMINI_3_PRO,
        system_instruction: Optional[str] = None,
        thinking_budget: int = 8192,
        *,
        video_id: Optional[str] = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Generate text with Google Search grounding.

        Args:
            prompt: User prompt
            model: Gemini model (Pro recommended for grounding)
            system_instruction: Optional system instruction
            thinking_budget: Token budget for thinking (must be >0 for Gemini 3 Pro with grounding)

        Returns:
            Tuple of (generated_text, citations)
        """
        client = self._get_client()

        config: dict[str, Any] = {
            "tools": [{"google_search": {}}],
            "temperature": 1.0,
        }

        # Gemini 3 Pro with grounding REQUIRES thinking mode enabled (budget > 0)
        # Error: "Budget 0 is invalid. This model only works in thinking mode."
        if thinking_budget <= 0:
            thinking_budget = 8192  # Default for grounding

        try:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        except Exception as e:
            logger.debug(f"ThinkingConfig not supported: {e}")

        if system_instruction:
            config["system_instruction"] = system_instruction

        start_time = asyncio.get_event_loop().time()
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=cast(Any, config),
            )

            text = response.text or ""
            citations = []

            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    metadata = candidate.grounding_metadata
                    if metadata and hasattr(metadata, "grounding_chunks"):
                        for chunk in metadata.grounding_chunks or []:
                            if hasattr(chunk, "web"):
                                citations.append(
                                    {
                                        "url": getattr(chunk.web, "uri", ""),
                                        "title": getattr(chunk.web, "title", ""),
                                    }
                                )

            logger.info(f"Generated grounded response with {len(citations)} citations")
            # Monitoring
            try:
                from app.services.monitoring import get_monitoring_service

                duration = asyncio.get_event_loop().time() - start_time
                usage_tokens = self._extract_usage_tokens(response)
                estimated = usage_tokens is None
                if usage_tokens:
                    in_tok, out_tok = usage_tokens
                else:
                    in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
                    out_tok = self._estimate_tokens(text)
                asyncio.create_task(
                    get_monitoring_service().record_text_usage(
                        video_id=video_id,
                        model=model,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        duration_seconds=duration,
                        success=True,
                        metadata={
                            "method": "generate_with_grounding",
                            "citations": len(citations),
                            "estimated": estimated,
                        },
                    )
                )
            except Exception:
                pass
            return text, citations

        except Exception as e:
            logger.error(f"Grounded generation failed: {e}")
            try:
                from app.services.monitoring import get_monitoring_service

                duration = asyncio.get_event_loop().time() - start_time
                in_tok = self._estimate_tokens(f"{system_instruction or ''}\n{prompt}")
                asyncio.create_task(
                    get_monitoring_service().record_text_usage(
                        video_id=video_id,
                        model=model,
                        input_tokens=in_tok,
                        output_tokens=0,
                        duration_seconds=duration,
                        success=False,
                        error_message=str(e),
                        metadata={"method": "generate_with_grounding", "estimated": True},
                    )
                )
            except Exception:
                pass
            raise GeminiAPIError(f"Grounded generation failed: {e}")

    async def _upload_file(
        self,
        file_bytes: bytes,
        mime_type: str,
        display_name: Optional[str] = None,
    ) -> types.File:
        """Upload a file to Gemini Files API and return the file object."""
        client = self._get_client()
        suffix = ".bin"
        if mime_type == "video/mp4":
            suffix = ".mp4"
        elif mime_type == "video/quicktime":
            suffix = ".mov"
        elif mime_type == "video/webm":
            suffix = ".webm"

        temp_path = tempfile.mktemp(suffix=suffix)
        try:
            with open(temp_path, "wb") as f:
                f.write(file_bytes)

            uploaded = await asyncio.to_thread(
                client.files.upload,
                file=temp_path,
                config=types.UploadFileConfig(
                    display_name=display_name or os.path.basename(temp_path),
                    mime_type=mime_type,
                ),
            )
            return uploaded
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def _wait_for_file_active(
        self,
        file_name: str,
        timeout_seconds: int = 120,
        poll_interval: int = 2,
    ) -> None:
        """Wait for uploaded file to reach ACTIVE state."""
        client = self._get_client()
        max_attempts = max(1, int(timeout_seconds / poll_interval))
        attempt = 0
        while attempt < max_attempts:
            file_obj = await asyncio.to_thread(client.files.get, name=file_name)
            state = getattr(file_obj, "state", None)
            if state == types.FileState.ACTIVE:
                return
            if state == types.FileState.FAILED:
                raise GeminiAPIError("Uploaded file processing failed")
            await asyncio.sleep(poll_interval)
            attempt += 1
        raise GeminiAPIError("Uploaded file did not become ACTIVE in time")

    def _estimate_tokens(self, text: Optional[str]) -> int:
        if not text:
            return 0
        # Rough heuristic: ~4 characters per token
        try:
            return max(0, int(len(text) / 4))
        except Exception:
            return 0

    def _extract_usage_tokens(self, response: Any) -> Optional[tuple[int, int]]:
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return None
        try:
            input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
            output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
            return input_tokens, output_tokens
        except Exception:
            return None

    def generate_structured_output_sync(
        self,
        prompt: str,
        response_model: Type[T],
        model: str = GEMINI_3_FLASH,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
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
                thinking_budget=thinking_budget or 0,
            )
        )


_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Get singleton Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
