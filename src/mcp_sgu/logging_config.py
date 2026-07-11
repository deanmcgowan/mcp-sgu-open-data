"""Structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

# Context variables for request-scoped logging
_request_id: ContextVar[str] = ContextVar("request_id", default="")
_tool_name: ContextVar[str] = ContextVar("tool_name", default="")
_mcp_session: ContextVar[str] = ContextVar("mcp_session", default="")


def get_request_id() -> str:
    return _request_id.get() or str(uuid.uuid4())


def set_request_id(req_id: str) -> None:
    _request_id.set(req_id)


def set_tool_name(name: str) -> None:
    _tool_name.set(name)


def set_mcp_session(session: str) -> None:
    _mcp_session.set(session)


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get() or None,
            "tool_name": _tool_name.get() or None,
            "mcp_session": _mcp_session.get() or None,
        }
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "exc_info", "exc_text",
                "message",
            ) and not key.startswith("_"):
                log_data[key] = value
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        return json.dumps(log_data, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured JSON logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Quieten noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name."""
    return logging.getLogger(name)


def log_upstream_call(
    logger: logging.Logger,
    service: str,
    url: str,
    status: int,
    duration_ms: float,
    *,
    cache_hit: bool = False,
    result_count: int | None = None,
    error: str | None = None,
) -> None:
    """Log a structured upstream HTTP call."""
    extra: dict[str, Any] = {
        "upstream_service": service,
        "upstream_status": status,
        "duration_ms": round(duration_ms, 2),
        "cache_hit": cache_hit,
    }
    if result_count is not None:
        extra["result_count"] = result_count
    if error:
        extra["error_category"] = error

    if error:
        logger.warning("Upstream call failed", extra=extra)
    else:
        logger.info("Upstream call completed", extra=extra)
