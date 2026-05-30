"""Tests for unified LLM client and schemas."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.common.exceptions import LLMClientError, SchemaRetryExhaustedError
from src.llm.client import LLMClientProtocol, OllamaClient
from src.llm.schemas import LLMRequest, LLMResponse


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestLLMRequest:
    """LLMRequest Pydantic validation."""

    def test_valid_request(self) -> None:
        req = LLMRequest(model="llama3", user_prompt="Analyze this clause.")
        assert req.model == "llama3"
        assert req.format == "json"
        assert req.temperature == 0.1

    def test_model_min_length(self) -> None:
        with pytest.raises(ValidationError):
            LLMRequest(model="", user_prompt="test")

    def test_user_prompt_min_length(self) -> None:
        with pytest.raises(ValidationError):
            LLMRequest(model="llama3", user_prompt="")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            LLMRequest(model="llama3", user_prompt="test", extra_field="bad")  # type: ignore[call-arg]

    def test_temperature_bounds(self) -> None:
        LLMRequest(model="llama3", user_prompt="test", temperature=0.0)
        LLMRequest(model="llama3", user_prompt="test", temperature=2.0)
        with pytest.raises(ValidationError):
            LLMRequest(model="llama3", user_prompt="test", temperature=-0.1)
        with pytest.raises(ValidationError):
            LLMRequest(model="llama3", user_prompt="test", temperature=2.1)


class TestLLMResponse:
    """LLMResponse Pydantic validation."""

    def test_valid_response(self) -> None:
        resp = LLMResponse(model="llama3", raw_text='{"key":"val"}', parsed_json={"key": "val"})
        assert resp.parsed_json == {"key": "val"}

    def test_parsed_json_optional(self) -> None:
        resp = LLMResponse(model="llama3", raw_text="not json")
        assert resp.parsed_json is None

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            LLMResponse(model="llama3", extra="bad")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Helper schema for generate_with_schema tests
# ---------------------------------------------------------------------------


class _MockFinding(BaseModel):
    """Minimal schema used for auto-retry tests."""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _build_request(prompt: str = "Analyze clause") -> LLMRequest:
    return LLMRequest(model="llama3", user_prompt=prompt)


def _mock_httpx_response(body: dict[str, Any], status: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    resp.json.return_value = body
    return resp


# ---------------------------------------------------------------------------
# OllamaClient.generate() tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestOllamaClientGenerate:
    """Test OllamaClient.generate() with mocked httpx."""

    @pytest.mark.asyncio
    async def test_generate_happy_path(self) -> None:
        valid_json = json.dumps({"claim": "Risk found", "confidence": 0.8})
        mock_resp = _mock_httpx_response({"model": "llama3", "response": valid_json})

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("src.llm.client.httpx.AsyncClient", return_value=mock_client_instance):
            client = OllamaClient("http://localhost:11434", default_model="llama3")
            response = await client.generate(_build_request())

        assert response.model == "llama3"
        assert response.parsed_json == {"claim": "Risk found", "confidence": 0.8}

    @pytest.mark.asyncio
    async def test_generate_non_json_response(self) -> None:
        mock_resp = _mock_httpx_response({"model": "llama3", "response": "not valid json"})

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("src.llm.client.httpx.AsyncClient", return_value=mock_client_instance):
            client = OllamaClient("http://localhost:11434")
            response = await client.generate(_build_request())

        assert response.parsed_json is None
        assert response.raw_text == "not valid json"

    @pytest.mark.asyncio
    async def test_generate_timeout_raises_llm_error(self) -> None:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("src.llm.client.httpx.AsyncClient", return_value=mock_client_instance):
            client = OllamaClient("http://localhost:11434", timeout_seconds=5)
            with pytest.raises(LLMClientError, match="timed out"):
                await client.generate(_build_request())


# ---------------------------------------------------------------------------
# OllamaClient.generate_with_schema() tests (Pydantic auto-retry)
# ---------------------------------------------------------------------------


class TestOllamaClientGenerateWithSchema:
    """Test Pydantic auto-retry middleware."""

    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        """Valid JSON on first attempt parses successfully."""
        client = OllamaClient("http://localhost:11434")
        valid = {"claim": "Tax risk", "confidence": 0.9}
        client.generate = AsyncMock(  # type: ignore[method-assign]
            return_value=LLMResponse(model="llama3", raw_text=json.dumps(valid), parsed_json=valid),
        )

        result = await client.generate_with_schema(_build_request(), _MockFinding)
        assert isinstance(result, _MockFinding)
        assert result.claim == "Tax risk"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_auto_retry_succeeds_on_second_attempt(self) -> None:
        """Invalid JSON first, valid JSON on retry."""
        client = OllamaClient("http://localhost:11434")
        invalid = {"claim": ""}  # min_length=1 violation
        valid = {"claim": "IP risk", "confidence": 0.7}

        client.generate = AsyncMock(  # type: ignore[method-assign]
            side_effect=[
                LLMResponse(model="llama3", raw_text=json.dumps(invalid), parsed_json=invalid),
                LLMResponse(model="llama3", raw_text=json.dumps(valid), parsed_json=valid),
            ],
        )

        result = await client.generate_with_schema(_build_request(), _MockFinding, max_retries=1)
        assert result.claim == "IP risk"
        assert client.generate.call_count == 2  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self) -> None:
        """Invalid JSON on all attempts raises SchemaRetryExhaustedError."""
        client = OllamaClient("http://localhost:11434")
        invalid = {"claim": ""}

        client.generate = AsyncMock(  # type: ignore[method-assign]
            return_value=LLMResponse(model="llama3", raw_text=json.dumps(invalid), parsed_json=invalid),
        )

        with pytest.raises(SchemaRetryExhaustedError, match="2 attempt"):
            await client.generate_with_schema(_build_request(), _MockFinding, max_retries=1)

    @pytest.mark.asyncio
    async def test_non_json_triggers_retry(self) -> None:
        """Non-JSON text triggers repair prompt retry."""
        client = OllamaClient("http://localhost:11434")
        valid = {"claim": "Found issue", "confidence": 0.5}

        client.generate = AsyncMock(  # type: ignore[method-assign]
            side_effect=[
                LLMResponse(model="llama3", raw_text="Sure, here's the analysis:", parsed_json=None),
                LLMResponse(model="llama3", raw_text=json.dumps(valid), parsed_json=valid),
            ],
        )

        result = await client.generate_with_schema(_build_request(), _MockFinding, max_retries=1)
        assert result.claim == "Found issue"


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestLLMClientProtocol:
    """Verify OllamaClient satisfies the LLMClientProtocol."""

    def test_protocol_compliance(self) -> None:
        client = OllamaClient("http://localhost:11434")
        assert isinstance(client, LLMClientProtocol)
