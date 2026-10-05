"""Structured key=value logging built on the standard library."""

from __future__ import annotations

import logging
import sys
from typing import Any

_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()) | {"message"}


class KeyValueFormatter(logging.Formatter):
    """Render records as ``ts=... level=... logger=... msg="..." key=value``."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"ts={self.formatTime(record, '%Y-%m-%dT%H:%M:%S')}",
            f"level={record.levelname}",
            f"logger={record.name}",
            f'msg="{record.getMessage()}"',
        ]
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                parts.append(f"{key}={_fmt(value)}")
        if record.exc_info:
            parts.append(f'exc="{self.formatException(record.exc_info)!r}"')
        return " ".join(parts)


def _fmt(value: Any) -> str:
    text = str(value)
    return f'"{text}"' if " " in text else text


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger with a single key=value stderr handler (idempotent)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(KeyValueFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger
