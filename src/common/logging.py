"""Structured JSON Logging Configuration.

Sets up structured JSON logging with context-aware formatters,
log rotation, and configurable log levels.

Every log entry carries: deal_id, phase, agent, timestamp.
Context is injected via ``set_log_context()`` and automatically
included in every JSON log record.
"""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Thread/coroutine-safe context variables
# ---------------------------------------------------------------------------

_deal_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("deal_id", default="")
_phase_var: contextvars.ContextVar[str] = contextvars.ContextVar("phase", default="")
_agent_var: contextvars.ContextVar[str] = contextvars.ContextVar("agent", default="")


def set_log_context(
    *,
    deal_id: str | None = None,
    phase: str | None = None,
    agent: str | None = None,
) -> None:
    """Set contextual fields that are automatically attached to every log entry.

    Call this at the start of each deal processing pipeline, phase transition,
    or agent execution to ensure downstream log entries carry provenance.
    """
    if deal_id is not None:
        _deal_id_var.set(deal_id)
    if phase is not None:
        _phase_var.set(phase)
    if agent is not None:
        _agent_var.set(agent)


def clear_log_context() -> None:
    """Reset all contextual log fields to empty defaults."""
    _deal_id_var.set("")
    _phase_var.set("")
    _agent_var.set("")


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------


class StructuredJSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Fields:
        timestamp   — ISO-8601 UTC timestamp
        level       — log level name (INFO, WARNING, ERROR, etc.)
        logger      — logger name (module path)
        message     — formatted log message
        deal_id     — current deal ID from context (may be empty)
        phase       — current pipeline phase from context
        agent       — current agent name from context
        module      — Python module that emitted the log
        function    — function name
        line        — source line number
        exc_info    — exception traceback (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "deal_id": _deal_id_var.get(""),
            "phase": _phase_var.get(""),
            "agent": _agent_var.get(""),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exc_info"] = self.formatException(record.exc_info)

        # Include any extra fields passed via `logger.info("msg", extra={...})`
        for key in ("deal_id", "phase", "agent"):
            extra_value = getattr(record, key, None)
            if extra_value and not log_entry[key]:
                log_entry[key] = extra_value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILE = "verdictos.log"
_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


def configure_logging(
    *,
    level: int = logging.INFO,
    log_dir: Path | str = _DEFAULT_LOG_DIR,
    log_file: str = _DEFAULT_LOG_FILE,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """Configure the root logger with structured JSON output.

    Parameters
    ----------
    level:
        Minimum log level (default: INFO).
    log_dir:
        Directory for rotated log files.
    log_file:
        Name of the log file within ``log_dir``.
    enable_console:
        Emit JSON logs to stderr (default: True).
    enable_file:
        Emit JSON logs to a rotating file (default: True).
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any previously attached handlers to avoid duplicates
    # when configure_logging is called more than once.
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    formatter = StructuredJSONFormatter()

    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path / log_file,
            maxBytes=_MAX_LOG_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
