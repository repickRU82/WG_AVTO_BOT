"""Main menu handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.session import SessionManager

router = Router(name="menu")


@router.message(Command("menu"))
async def cmd_menu(message: Message, session_manager: SessionManager) -> None:
    """Show basic command menu for authenticated users."""

    if message.from_user is None:
        return

    role = await session_manager.get_role(message.from_user.id)
    if role is None:
        await message.answer("Сессия не найдена или истекла (15 мин). Выполните /login")
        return

    admin_block = "\n/admin команды: /stats /users /logs" if role == "admin" else ""
    await message.answer(
        "Доступные команды:\n"
        "/new_connection - создать WG профиль\n"
        "/my_connections - список ваших профилей"
        f"{admin_block}"
    )
