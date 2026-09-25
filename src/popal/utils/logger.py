"""POPAL logging configuration.

Sets up structured logging to both console and file.
Never logs passwords, API keys, tokens, or private secrets.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any


_SENSITIVE_KEYS = frozenset({
    "password", "passwd", "secret", "token", "api_key", "apikey", "auth",
})

_log_configured = False


def _redact(record: logging.LogRecord) -> bool:
    """Return False if the record contains sensitive data patterns."""
    msg = record.getMessage().lower()
    for key in _SENSITIVE_KEYS:
        if key in msg:
            record.msg = "[REDACTED — sensitive data detected in log message]"
            record.args = ()
            break
    return True


class SensitiveDataFilter(logging.Filter):
    """Filter that redacts log messages containing sensitive keywords."""

    def filter(self, record: logging.LogRecord) -> bool:
        return _redact(record)


def setup_logging(
    log_level: str = "INFO",
    log_directory: str | None = None,
    enabled: bool = True,
) -> None:
    """Configure POPAL logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_directory: Directory for log files. None disables file logging.
        enabled: Master switch to enable/disable logging.
    """
    global _log_configured  # noqa: PLW0603
    if _log_configured:
        return

    if not enabled:
        logging.disable(logging.CRITICAL)
        _log_configured = True
        return

    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger("popal")
    root_logger.setLevel(level)
    root_logger.addFilter(SensitiveDataFilter())

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_directory:
        log_dir = Path(log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "popal.log")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _log_configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'popal' namespace.

    Args:
        name: Logger name, typically the module name.

    Returns:
        A configured Logger instance.
    """
    return logging.getLogger(f"popal.{name}")