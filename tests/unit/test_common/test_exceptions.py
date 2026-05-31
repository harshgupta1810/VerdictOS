import pytest
from src.common.exceptions import (
    VerdictOSError,
    DocumentIngestionError,
    UnsupportedDocumentTypeError,
    SearchEngineError,
    LLMClientError,
    SchemaRetryExhaustedError,
    DebateEngineError,
    GateValidationError,
    PersonaDropoutError
)

def test_exceptions_hierarchy():
    assert issubclass(DocumentIngestionError, VerdictOSError)
    assert issubclass(UnsupportedDocumentTypeError, DocumentIngestionError)
    assert issubclass(SearchEngineError, VerdictOSError)
    assert issubclass(LLMClientError, VerdictOSError)
    assert issubclass(SchemaRetryExhaustedError, VerdictOSError)
    assert issubclass(DebateEngineError, VerdictOSError)
    assert issubclass(GateValidationError, VerdictOSError)
    assert issubclass(PersonaDropoutError, VerdictOSError)
