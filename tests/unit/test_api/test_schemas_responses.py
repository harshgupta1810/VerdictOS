"""Tests for API response schemas."""

import pytest
from datetime import datetime, timezone
from src.api.schemas.responses import ErrorResponse, HealthResponse

def test_error_response_default_timestamp() -> None:
    response = ErrorResponse(error_code="TEST", message="test message")
    assert response.error_code == "TEST"
    assert response.message == "test message"
    assert isinstance(response.timestamp, datetime)
    assert response.timestamp.tzinfo == timezone.utc

def test_health_response_default_timestamp() -> None:
    response = HealthResponse()
    assert response.status == "ok"
    assert isinstance(response.timestamp, datetime)
    assert response.timestamp.tzinfo == timezone.utc
