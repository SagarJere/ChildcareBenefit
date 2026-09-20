"""Structured JSON logging configuration.

Every log record is emitted as a single JSON line containing a timestamp,
level, logger name, message, and the current request correlation ID (when
available). No secrets, tokens, or document contents are ever logged.
"""
import json
import logging
import sys
from datetime import UTC, datetime

from app.core.request_context import get_correlation_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlationId": get_correlation_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(log_level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if configure_logging is called more than once
    # (e.g. under the test runner's app fixture reuse).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers to WARNING unless the app itself is in
    # DEBUG mode.
    for noisy_logger in ("uvicorn.access",):
        logging.getLogger(noisy_logger).setLevel(
            "WARNING" if log_level != "DEBUG" else "DEBUG"
        )
