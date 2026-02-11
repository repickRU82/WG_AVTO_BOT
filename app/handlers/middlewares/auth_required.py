"""Middleware enforcing active Redis session for protected routers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.utils.session import SessionManager


class AuthRequiredMiddleware(BaseMiddleware):
    """Block handler execution when user has no active session."""

    def __init__(self, session_manager: SessionManager) -> None:
        self._session_manager = session_manager

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        role = await self._session_manager.get_role(event.from_user.id)
        if role is None:
            await event.answer("Сессия не найдена или истекла (15 мин). Выполните /login")
            return None

        data["session_role"] = role
        return await handler(event, data)
