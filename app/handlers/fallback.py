"""Fallback handler for unmatched text messages."""

from aiogram import F, Router
from aiogram.types import Message

from app.utils.logging_compat import get_logger

router = Router(name="fallback")
logger = get_logger(__name__)


@router.message(F.text)
async def fallback_text(message: Message) -> None:
    logger.info("Unmatched text message", text=message.text, user_id=message.from_user.id if message.from_user else None)
    await message.answer("Команда не распознана. Нажмите /menu")
