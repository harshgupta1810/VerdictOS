"""Unit tests for Step 55 — Asyncio Semaphore(40) for LLM Calls."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.client import OllamaClient, _llm_semaphore
from src.llm.schemas import LLMRequest


class TestLLMSemaphore:
    """Validate that the LLM client enforces the Semaphore(40) concurrency limit."""

    def test_semaphore_limit_is_40(self) -> None:
        """Verify the module-level semaphore is initialized to 40."""
        assert isinstance(_llm_semaphore, asyncio.Semaphore)
        # In newer Python versions (or depending on state), the initial value is stored in _value
        assert _llm_semaphore._value == 40

    @pytest.mark.asyncio
    async def test_generate_acquires_semaphore(self) -> None:
        """Verify OllamaClient.generate acquires the semaphore during HTTP calls."""
        # Create a mock response for the generate call
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"model": "llama3.2:1b", "response": "{\"claim\": \"test\"}"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # We will make post check the semaphore value while active
        async def mock_post(*args, **kwargs):
            # Assert semaphore is currently acquired (its counter should be decreased)
            assert _llm_semaphore.locked() or _llm_semaphore._value < 40
            return mock_resp

        mock_client.post = AsyncMock(side_effect=mock_post)

        client = OllamaClient("http://localhost:11434")
        req = LLMRequest(model="llama3.2:1b", user_prompt="test prompt")

        with patch("src.llm.client.httpx.AsyncClient", return_value=mock_client):
            # Verify semaphore is initially fully available
            assert _llm_semaphore._value == 40
            response = await client.generate(req)
            # Verify semaphore is released after call
            assert _llm_semaphore._value == 40

        assert response.model == "llama3.2:1b"
