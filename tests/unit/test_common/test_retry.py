import pytest
import httpx
from src.common.retry import with_exponential_backoff
from src.common.exceptions import LLMClientError
import asyncio
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_retry_success_first_try():
    mock_func = MagicMock(return_value="success")
    async def async_func():
        return mock_func()
    decorated = with_exponential_backoff(retries=3, base_delay=0.1, max_delay=0.5)(async_func)
    assert await decorated() == "success"
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_retry_success_after_failure():
    mock_func = MagicMock(side_effect=[LLMClientError("error"), "success"])
    async def async_func():
        return mock_func()
    decorated = with_exponential_backoff(retries=3, base_delay=0.1, max_delay=0.5)(async_func)
    assert await decorated() == "success"
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_retry_exhausted():
    mock_func = MagicMock(side_effect=LLMClientError("error"))
    async def async_func():
        mock_func()
        raise LLMClientError("error")
    decorated = with_exponential_backoff(retries=2, base_delay=0.1, max_delay=0.5)(async_func)
    with pytest.raises(LLMClientError):
        await decorated()
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_retry_http_429():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    error = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_resp)
    mock_func = MagicMock(side_effect=[error, "success"])
    async def async_func():
        return mock_func()
    decorated = with_exponential_backoff(retries=2, base_delay=0.1, max_delay=0.5)(async_func)
    assert await decorated() == "success"
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_no_retry_http_400():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 400
    error = httpx.HTTPStatusError("400", request=MagicMock(), response=mock_resp)
    mock_func = MagicMock(side_effect=error)
    async def async_func():
        return mock_func()
    decorated = with_exponential_backoff(retries=2, base_delay=0.1, max_delay=0.5)(async_func)
    with pytest.raises(httpx.HTTPStatusError):
        await decorated()
    assert mock_func.call_count == 1
