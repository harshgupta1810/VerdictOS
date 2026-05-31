"""Tests for API dependencies."""

from src.api.dependencies import get_db

def test_dependencies_import() -> None:
    # Just verify get_db is exposed
    assert callable(get_db)
