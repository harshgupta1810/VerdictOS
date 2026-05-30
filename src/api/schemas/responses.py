"""API Response Models.

Pydantic schemas for outgoing API response bodies
(verdict payloads, status updates, audit trail records).
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standardized error response returned by all exception handlers.

    Every error response carries a machine-readable ``error_code``,
    a human-readable ``message``, an optional ``detail`` payload for
    debugging, and the server timestamp.
    """

    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(
        min_length=1,
        description="Machine-readable error category (e.g. 'DOCUMENT_INGESTION_ERROR').",
    )
    message: str = Field(
        min_length=1,
        description="Human-readable summary of the error.",
    )
    detail: str | None = Field(
        default=None,
        description="Additional diagnostic information (omitted in production).",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the error occurred.",
    )


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
