"""Custom Exception Hierarchy.

Defines domain-specific exceptions for ingestion failures,
search errors, debate validation errors, and API errors.
"""


class VerdictOSError(Exception):
    """Base exception for expected VerdictOS failures."""


class DocumentIngestionError(VerdictOSError):
    """Raised when a supported source document cannot be parsed."""


class UnsupportedDocumentTypeError(DocumentIngestionError):
    """Raised when ingestion receives an unsupported file extension."""


class SearchEngineError(VerdictOSError):
    """Raised when sparse retrieval fails."""


class LLMClientError(VerdictOSError):
    """Raised when the local LLM service is unreachable or times out."""


class SchemaRetryExhaustedError(VerdictOSError):
    """Raised when the Pydantic auto-retry middleware exhausts all retries."""
