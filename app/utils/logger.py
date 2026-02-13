"""Logging setup."""

import logging
import sys
from pathlib import Path

from app.utils.logging_compat import configure_structlog


def setup_logging(level: str = "INFO", log_file_path: str = "") -> None:
    """Configure stdlib and structlog (if installed)."""
    """Configure stdlib and structlog processors."""

    log_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file_path:
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file_path))

    logging.basicConfig(level=log_level, format="%(message)s", handlers=handlers, force=True)
    configure_structlog(log_level)

    logging.basicConfig(level=log_level, format="%(message)s", handlers=handlers, force=True)

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
