"""Main menu handlers."""

from aiogram import F, Router
from aiogram.types import Message

from app.ui import texts

router = Router(name="menu")


@router.message(F.text == "❓ Помощь")
async def help_message(message: Message) -> None:
    await message.answer(texts.HELP_TEXT)


@router.message(F.text == "🛠 Если не работает")
async def troubles(message: Message) -> None:
    await message.answer(texts.TROUBLESHOOT_TEXT)


@router.message(F.text == "🧩 Как установить")
async def install(message: Message) -> None:
    await message.answer("\n\n".join(texts.INSTALL_TEXTS.values()))
