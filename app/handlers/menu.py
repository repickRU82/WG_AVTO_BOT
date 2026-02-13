"""Main menu handlers."""

from aiogram import F, Router
from aiogram.types import Message

from app.ui import texts
from app.ui.labels import BTN_HELP, BTN_INSTALL, BTN_TROUBLE

router = Router(name="menu")


@router.message(F.text == BTN_HELP)
async def help_message(message: Message) -> None:
    await message.answer(texts.HELP_TEXT)


@router.message(F.text == BTN_TROUBLE)
async def troubles(message: Message) -> None:
    await message.answer(texts.TROUBLESHOOT_TEXT)


@router.message(F.text == BTN_INSTALL)
async def install(message: Message) -> None:
    await message.answer("\n\n".join(texts.INSTALL_TEXTS.values()))
