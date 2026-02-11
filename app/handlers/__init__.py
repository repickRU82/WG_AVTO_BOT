"""Handlers package exports and router wiring."""

from aiogram import Dispatcher

from app.handlers.auth import router as auth_router
from app.handlers.connections import router as connections_router
from app.handlers.menu import router as menu_router


def register_routers(dp: Dispatcher) -> None:
    """Include all command routers in dispatcher."""

    dp.include_router(auth_router)
    dp.include_router(menu_router)
    dp.include_router(connections_router)
