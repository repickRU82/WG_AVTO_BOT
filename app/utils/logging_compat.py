"""Compatibility wrapper for structlog/std logging."""

from __future__ import annotations

import logging
from typing import Any

try:
    import structlog as _structlog
except ModuleNotFoundError:  # pragma: no cover
    _structlog = None


class BoundLogger:
    """Small wrapper that mimics structlog bound logger methods."""

    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None = None) -> None:
        self._logger = logger
        self._context = context or {}

    def bind(self, **kwargs: Any) -> "BoundLogger":
        merged = {**self._context, **kwargs}
        return BoundLogger(self._logger, merged)

    def _msg(self, message: str, **kwargs: Any) -> str:
        payload = {**self._context, **kwargs}
        return f"{message} | {payload}" if payload else message

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(self._msg(message, **kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(self._msg(message, **kwargs))

    def exception(self, message: str, **kwargs: Any) -> None:
        self._logger.exception(self._msg(message, **kwargs))


def get_logger(name: str) -> Any:
    """Return structlog logger if available, fallback to std logger wrapper."""

    if _structlog is not None:
        return _structlog.get_logger(name)
    return BoundLogger(logging.getLogger(name))


def has_structlog() -> bool:
    return _structlog is not None


def configure_structlog(log_level: int) -> None:
    """Configure structlog when installed."""

    if _structlog is None:
        return

    _structlog.configure(
        processors=[
            _structlog.contextvars.merge_contextvars,
            _structlog.processors.TimeStamper(fmt="iso"),
            _structlog.processors.add_log_level,
            _structlog.processors.JSONRenderer(),
        ],
        wrapper_class=_structlog.make_filtering_bound_logger(log_level),
        logger_factory=_structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
