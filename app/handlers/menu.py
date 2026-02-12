"""Main menu handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="menu")


@router.message(Command("menu"))
async def cmd_menu(message: Message, session_role: str) -> None:
    """Show basic command menu for authenticated users."""

    admin_block = "\n/admin команды: /stats /users /logs /mt_test" if session_role == "admin" else ""
    await message.answer(
        "Доступные команды:\n"
        "/new_connection - создать WG профиль\n"
        "/my_connections - список ваших профилей"
        f"{admin_block}"
    )
