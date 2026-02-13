"""Middleware enforcing active Redis session for protected routers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.utils.session import SessionManager


class AuthRequiredMiddleware(BaseMiddleware):
    """Populate session role when available without blocking menu UX."""

    def __init__(self, session_manager: SessionManager) -> None:
        self._session_manager = session_manager

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)) or event.from_user is None:
            return await handler(event, data)

        role = await self._session_manager.get_role(event.from_user.id)
        data["session_role"] = role
        return await handler(event, data)
