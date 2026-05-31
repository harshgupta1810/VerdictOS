"""FastAPI Application Factory.

Creates and configures the FastAPI app instance with middleware,
route registration, global exception handlers, and startup/shutdown
lifecycle hooks.
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.common.exceptions import (
    DocumentIngestionError,
    LLMClientError,
    SchemaRetryExhaustedError,
    SearchEngineError,
    UnsupportedDocumentTypeError,
    VerdictOSError,
)
from src.common.logging import configure_logging
from src.api.schemas.responses import ErrorResponse, HealthResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.middleware.auth import APIKeyMiddleware
from src.api.routes import deals, escalations

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception → (HTTP status, error_code) mapping
# ---------------------------------------------------------------------------

_EXCEPTION_MAP: dict[type[Exception], tuple[int, str]] = {
    UnsupportedDocumentTypeError: (400, "UNSUPPORTED_DOCUMENT_TYPE"),
    DocumentIngestionError: (422, "DOCUMENT_INGESTION_ERROR"),
    SearchEngineError: (503, "SEARCH_ENGINE_ERROR"),
    LLMClientError: (503, "LLM_CLIENT_ERROR"),
    SchemaRetryExhaustedError: (422, "SCHEMA_RETRY_EXHAUSTED"),
}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


# pyrefly: ignore [deprecated]
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    configure_logging()
    logger.info("VerdictOS API starting up")
    yield
    logger.info("VerdictOS API shutting down")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Build and return the fully configured FastAPI application."""

    application = FastAPI(
        title="VerdictOS",
        description="Autonomous M&A Due Diligence Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # Middleware
    # -----------------------------------------------------------------------
    
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(APIKeyMiddleware)

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    
    application.include_router(deals.router, prefix="/api/v1")
    application.include_router(escalations.router, prefix="/api/v1")

    # -----------------------------------------------------------------------
    # Global exception handlers
    # -----------------------------------------------------------------------

    @application.exception_handler(VerdictOSError)
    async def handle_verdictos_error(
        request: Request, exc: VerdictOSError
    ) -> JSONResponse:
        """Handle all VerdictOSError subclasses with the standardized schema."""
        status_code, error_code = _EXCEPTION_MAP.get(
            type(exc), (500, "INTERNAL_ERROR")
        )
        body = ErrorResponse(
            error_code=error_code,
            message=str(exc),
            detail=repr(exc) if status_code >= 500 else None,
        )
        logger.warning(
            "Handled %s: %s", type(exc).__name__, exc, exc_info=(status_code >= 500),
        )
        return JSONResponse(
            status_code=status_code,
            content=body.model_dump(mode="json"),
        )

    @application.exception_handler(ValueError)
    async def handle_value_error(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Catch Pydantic / validation ValueError escapes."""
        body = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=str(exc),
        )
        logger.warning("ValueError: %s", exc)
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Last-resort handler for uncaught exceptions."""
        body = ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            detail=repr(exc),
        )
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))

    # -----------------------------------------------------------------------
    # Health check
    # -----------------------------------------------------------------------

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health_check() -> HealthResponse:
        """Lightweight liveness probe."""
        return HealthResponse()

    return application


# Module-level singleton used by uvicorn (src.api.main:app)
app = create_app()
