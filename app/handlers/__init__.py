"""Handlers package exports and router wiring."""

from aiogram import Dispatcher

from app.handlers.auth import router as auth_router
from app.handlers.connections import router as connections_router
from app.handlers.menu import router as menu_router
from app.handlers.middlewares import AuthRequiredMiddleware
from app.utils.session import SessionManager


def register_routers(dp: Dispatcher, session_manager: SessionManager) -> None:
    """Include all command routers in dispatcher and apply middlewares."""

    auth_required = AuthRequiredMiddleware(session_manager=session_manager)
    menu_router.message.middleware(auth_required)
    connections_router.message.middleware(auth_required)

    dp.include_router(auth_router)
    dp.include_router(menu_router)
    dp.include_router(connections_router)
