"""Middlewares package exports."""

from app.handlers.middlewares.auth_required import AuthRequiredMiddleware

__all__ = ["AuthRequiredMiddleware"]
