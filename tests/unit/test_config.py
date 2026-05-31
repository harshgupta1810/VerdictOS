"""Tests for the configuration settings."""

import pytest
from src.config import Settings, _INSECURE_DEFAULT

def test_settings_instantiation(caplog: pytest.LogCaptureFixture) -> None:
    """Test that settings instantiation triggers validator."""
    Settings(jwt_secret="secure")
    assert "JWT_SECRET is set to the insecure default" not in caplog.text
    
    Settings(jwt_secret=_INSECURE_DEFAULT)
    assert "JWT_SECRET is set to the insecure default" in caplog.text
