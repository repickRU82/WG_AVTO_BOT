"""Main menu handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.ui.keyboards import main_menu
from app.ui import texts

router = Router(name="menu")


@router.message(Command("menu"))
async def cmd_menu(message: Message, session_role: str) -> None:
    await message.answer("Выбери действие в меню 👇", reply_markup=main_menu(session_role == "admin"))


@router.message(lambda m: m.text == "❓ Помощь")
async def help_message(message: Message) -> None:
    await message.answer(texts.HELP_TEXT)


@router.message(lambda m: m.text == "🛠 Если не работает")
async def troubles(message: Message) -> None:
    await message.answer(texts.TROUBLESHOOT_TEXT)


@router.message(lambda m: m.text == "🧩 Как установить")
async def install(message: Message) -> None:
    await message.answer("\n\n".join(texts.INSTALL_TEXTS.values()))
    """Show basic command menu for authenticated users."""

    admin_block = "\n/admin команды: /stats /users /logs /mt_test" if session_role == "admin" else ""
    await message.answer(
        "Доступные команды:\n"
        "/new_connection - создать WG профиль\n"
        "/my_connections - список ваших профилей"
        f"{admin_block}"
    )
