"""Unit tests for Step 56 — Exponential Backoff Retry Handler."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.common.exceptions import LLMClientError
from src.common.retry import with_exponential_backoff


class TestExponentialBackoff:
    """Validate the exponential backoff retry handler decorator/utility."""

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_retry_happy_path(self, mock_sleep: MagicMock) -> None:
        """Verify decorated function returns immediately if no exception occurs."""
        call_count = 0

        @with_exponential_backoff(retries=3, base_delay=0.1)
        async def mock_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_func()
        assert result == "success"
        assert call_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_retries_on_llm_client_error(self, mock_sleep: MagicMock) -> None:
        """Verify that it retries on LLMClientError up to limit and then raises."""
        call_count = 0

        @with_exponential_backoff(retries=2, base_delay=1.0)
        async def mock_func() -> None:
            nonlocal call_count
            call_count += 1
            raise LLMClientError("Ollama is busy")

        with pytest.raises(LLMClientError, match="Ollama is busy"):
            await mock_func()

        # Should attempt 3 times total (1 initial + 2 retries)
        assert call_count == 3
        assert mock_sleep.call_count == 2
        # Check backoff delays: base_delay * 2^0 = 1.0, base_delay * 2^1 = 2.0
        # Jitter is +/- 10%, so first sleep should be between 0.9 and 1.1, second between 1.8 and 2.2
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 0.9 <= calls[0] <= 1.1
        assert 1.8 <= calls[1] <= 2.2

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_succeeds_after_retries(self, mock_sleep: MagicMock) -> None:
        """Verify that it succeeds if a subsequent retry is successful."""
        call_count = 0

        @with_exponential_backoff(retries=3, base_delay=1.0)
        async def mock_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMClientError("temporary error")
            return "ok"

        result = await mock_func()
        assert result == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_retries_on_http_429_but_raises_other_http_errors(self, mock_sleep: MagicMock) -> None:
        """Verify retry on 429 status code, but immediate raise on other codes like 400."""
        # Case 1: HTTP 429 Rate Limit
        call_count_429 = 0
        resp_429 = MagicMock(spec=httpx.Response)
        resp_429.status_code = 429
        exc_429 = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=resp_429)

        @with_exponential_backoff(retries=1, base_delay=1.0)
        async def func_429() -> None:
            nonlocal call_count_429
            call_count_429 += 1
            raise exc_429

        with pytest.raises(httpx.HTTPStatusError):
            await func_429()
        assert call_count_429 == 2

        # Case 2: HTTP 400 Bad Request (non-retryable)
        call_count_400 = 0
        resp_400 = MagicMock(spec=httpx.Response)
        resp_400.status_code = 400
        exc_400 = httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=resp_400)

        @with_exponential_backoff(retries=3, base_delay=1.0)
        async def func_400() -> None:
            nonlocal call_count_400
            call_count_400 += 1
            raise exc_400

        with pytest.raises(httpx.HTTPStatusError):
            await func_400()
        # Should raise immediately on first call
        assert call_count_400 == 1
