"""Tests for the common logging module."""
import json
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.common.logging import (
    set_log_context,
    clear_log_context,
    StructuredJSONFormatter,
    configure_logging,
)

def test_set_log_context() -> None:
    set_log_context(deal_id="test-deal", phase="test-phase", agent="test-agent")
    clear_log_context()

def test_structured_json_formatter() -> None:
    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    try:
        raise ValueError("test error")
    except ValueError as e:
        import sys
        record.exc_info = sys.exc_info()
    
    record.deal_id = "extra_deal"
    
    set_log_context(phase="test-phase")
    
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    
    assert parsed["message"] == "Test message"
    assert parsed["deal_id"] == "extra_deal"
    assert parsed["phase"] == "test-phase"
    assert "exc_info" in parsed
    
    clear_log_context()

def test_configure_logging(tmp_path: Path) -> None:
    configure_logging(
        level=logging.DEBUG,
        log_dir=tmp_path,
        log_file="test.log",
        enable_console=True,
        enable_file=True,
    )
    
    logger = logging.getLogger()
    assert logger.level == logging.DEBUG
    
    # We should have stream and rotating file handlers
    handlers = [type(h).__name__ for h in logger.handlers]
    assert "StreamHandler" in handlers
    assert "RotatingFileHandler" in handlers
