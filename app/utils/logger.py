"""Logging setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

try:
    import structlog
except Exception:
    structlog = None  # type: ignore

from app.utils.logging_compat import configure_structlog


def setup_logging(level: str = "INFO", log_file_path: str = "") -> None:
    """Configure stdlib logging and structlog (if available)."""

    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file_path:
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file_path))

    logging.basicConfig(level=log_level, format="%(message)s", handlers=handlers, force=True)

    # Keep compatibility logic in one place
    configure_structlog(log_level)

    # If structlog isn't available, do not crash the app
    if structlog is None:
        logging.getLogger(__name__).warning("structlog is not installed; using stdlib logging only")
        return

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
PY
