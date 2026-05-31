"""Tests for the FastAPI main application."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app, create_app, _EXCEPTION_MAP
from src.common.exceptions import DocumentIngestionError, VerdictOSError

def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_verdictos_error_handler() -> None:
    test_app = create_app()
    @test_app.get("/error-verdictos")
    async def trigger_verdictos_error() -> None:
        raise DocumentIngestionError("Test ingestion error")
        
    client = TestClient(test_app, raise_server_exceptions=False, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/error-verdictos")
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "DOCUMENT_INGESTION_ERROR"
    assert "Test ingestion error" in data["message"]

def test_verdictos_error_handler_500() -> None:
    test_app = create_app()
    @test_app.get("/error-verdictos-500")
    async def trigger_verdictos_500() -> None:
        raise VerdictOSError("Generic verdictos error")
        
    client = TestClient(test_app, raise_server_exceptions=False, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/error-verdictos-500")
    assert response.status_code == 500
    data = response.json()
    assert data["error_code"] == "INTERNAL_ERROR"

def test_value_error_handler() -> None:
    test_app = create_app()
    @test_app.get("/error-value")
    async def trigger_value_error() -> None:
        raise ValueError("Test value error")
        
    client = TestClient(test_app, raise_server_exceptions=False, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/error-value")
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "Test value error" in data["message"]

def test_unexpected_error_handler() -> None:
    test_app = create_app()
    @test_app.get("/error-generic")
    async def trigger_generic_error() -> None:
        raise RuntimeError("Test generic error")
        
    client = TestClient(test_app, raise_server_exceptions=False, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/error-generic")
    assert response.status_code == 500
    data = response.json()
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "An unexpected error occurred" in data["message"]

@pytest.mark.asyncio
async def test_lifespan() -> None:
    from src.api.main import lifespan
    async with lifespan(app):
        pass

def test_missing_api_key() -> None:
    # No headers provided
    test_app = create_app()
    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get("/error-verdictos")
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"
