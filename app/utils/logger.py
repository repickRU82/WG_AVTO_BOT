"""Logging setup with structlog."""

import logging

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure stdlib and structlog processors."""

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
