"""Unified LLM Client Abstraction.

Provides a single interface for interacting with open-source LLMs
via Ollama (http://localhost:11434) or vLLM backends.

Supported models: Llama-3, Qwen-2.5, Mistral.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, TypeVar, runtime_checkable

import httpx
from pydantic import BaseModel, ValidationError

from src.common.exceptions import LLMClientError, SchemaRetryExhaustedError
from src.common.retry import with_exponential_backoff
from src.llm.schemas import LLMRequest, LLMResponse

try:
    from typing import Protocol
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol  # type: ignore[assignment]

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_llm_semaphore = asyncio.Semaphore(40)

_REPAIR_SYSTEM_PROMPT = (
    "Your previous JSON output failed validation with the following error:\n"
    "{error}\n\n"
    "Your previous (invalid) output was:\n"
    "{previous_output}\n\n"
    "Please output the corrected JSON structure. Output ONLY valid JSON — "
    "no markdown, no explanation, no preamble."
)


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol interface for LLM client implementations."""

    @property
    def default_model(self) -> str:
        """The model name used when a request does not specify one explicitly."""
        ...  # pragma: no cover

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send a single-shot generation request and return the raw response."""
        ...  # pragma: no cover

    async def generate_with_schema(
        self,
        request: LLMRequest,
        schema_type: type[T],
        *,
        max_retries: int = 1,
    ) -> T:
        """Generate and parse response through a Pydantic schema with auto-retry."""
        ...  # pragma: no cover


class OllamaClient:
    """Ollama /api/generate JSON client with Pydantic auto-retry middleware.

    Implements LLMClientProtocol for dependency injection and mock testing.
    """

    def __init__(
        self,
        base_url: str,
        *,
        default_model: str = "llama3",
        timeout_seconds: int = 120,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds

    @property
    def default_model(self) -> str:
        return self._default_model

    @with_exponential_backoff()
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """POST to Ollama /api/generate with JSON format enforcement."""
        async with _llm_semaphore:
            payload: dict[str, Any] = {
                "model": request.model or self._default_model,
                "prompt": request.user_prompt,
                "format": request.format,
                "stream": False,
            }
            if request.system_prompt:
                payload["system"] = request.system_prompt
            if request.temperature is not None:
                payload["options"] = {"temperature": request.temperature}
            if request.max_tokens is not None:
                payload.setdefault("options", {})["num_predict"] = request.max_tokens

            start_ms = _now_ms()
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    resp = await client.post(
                        f"{self._base_url}/api/generate",
                        json=payload,
                    )
                    resp.raise_for_status()
            except httpx.TimeoutException as exc:
                raise LLMClientError(
                    f"Ollama request timed out after {self._timeout_seconds}s"
                ) from exc
            except httpx.HTTPError as exc:
                raise LLMClientError(f"Ollama HTTP error: {exc}") from exc

            elapsed = _now_ms() - start_ms
            body = resp.json()
            raw_text = body.get("response", "")

            parsed_json: dict[str, Any] | None = None
            try:
                parsed_json = json.loads(raw_text)
            except (json.JSONDecodeError, TypeError):
                pass

            return LLMResponse(
                model=body.get("model", request.model),
                raw_text=raw_text,
                parsed_json=parsed_json,
                duration_ms=elapsed,
            )

    async def generate_with_schema(
        self,
        request: LLMRequest,
        schema_type: type[T],
        *,
        max_retries: int = 1,
    ) -> T:
        """Generate, parse through Pydantic, and auto-retry on validation failure.

        ADR 002: On first validation failure, sends a repair prompt with the
        exact validation error. On exhaustion, raises SchemaRetryExhaustedError.
        """

        response = await self.generate(request)
        last_error: str = ""
        last_raw_output: str = ""

        # Attempt initial parse
        if response.parsed_json is not None:
            try:
                return schema_type.model_validate(response.parsed_json)
            except ValidationError as exc:
                last_error = str(exc)
                last_raw_output = response.raw_text
                logger.warning(
                    "Schema validation failed (attempt 1/%d): %s",
                    1 + max_retries,
                    last_error,
                )
        else:
            last_error = f"LLM returned non-JSON text: {response.raw_text[:200]}"
            last_raw_output = response.raw_text
            logger.warning("Non-JSON response (attempt 1/%d): %s", 1 + max_retries, last_error)

        # Auto-retry loop — include the previous invalid output so the model
        # can see exactly what it produced and correct it.
        for attempt in range(max_retries):
            repair_request = LLMRequest(
                model=request.model,
                system_prompt=_REPAIR_SYSTEM_PROMPT.format(
                    error=last_error,
                    previous_output=last_raw_output[:500],
                ),
                user_prompt=request.user_prompt,
                format=request.format,
                temperature=request.temperature,
            )
            response = await self.generate(repair_request)

            if response.parsed_json is not None:
                try:
                    return schema_type.model_validate(response.parsed_json)
                except ValidationError as exc:
                    last_error = str(exc)
                    last_raw_output = response.raw_text
                    logger.warning(
                        "Schema validation failed (attempt %d/%d): %s",
                        attempt + 2,
                        1 + max_retries,
                        last_error,
                    )
            else:
                last_error = f"LLM returned non-JSON text: {response.raw_text[:200]}"
                last_raw_output = response.raw_text
                logger.warning(
                    "Non-JSON response (attempt %d/%d): %s",
                    attempt + 2,
                    1 + max_retries,
                    last_error,
                )

        raise SchemaRetryExhaustedError(
            f"Schema validation failed after {1 + max_retries} attempt(s). "
            f"Last error: {last_error}"
        )


def _now_ms() -> int:
    """Return current time in milliseconds."""
    return int(time.monotonic() * 1000)
