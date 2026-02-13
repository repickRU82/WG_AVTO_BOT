"""Logging setup helpers."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.utils.logging_compat import configure_structlog

try:  # optional dependency at runtime
    import structlog  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    structlog = None


def setup_logging(level: str = "INFO", log_file_path: str = "") -> None:
    """Configure stdlib logging and structlog (when available)."""

    log_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file_path:
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file_path))

    logging.basicConfig(level=log_level, format="%(message)s", handlers=handlers, force=True)
    configure_structlog(log_level)

    # Ensure import is safe and no NameError can occur even if structlog is absent.
    if structlog is None:
        logging.getLogger(__name__).debug("structlog is not installed; using stdlib logging fallback")
