"""Authentication handlers with global PIN and admin approval workflow."""

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.database.repositories import UsersRepository
from app.services.auth_service import AuthService
from app.ui.keyboards import main_menu
from app.ui import texts

router = Router(name="auth")
logger = structlog.get_logger(__name__)


class AuthStates(StatesGroup):
    waiting_for_pin = State()


async def _notify_admins_about_pending(message: Message, auth_service: AuthService) -> None:
    if message.bot is None or message.from_user is None:
        return

    for admin_id in auth_service.admin_ids:
        if admin_id == message.from_user.id:
            continue
        username = f"@{message.from_user.username}" if message.from_user.username else "(нет username)"
        await message.bot.send_message(
            admin_id,
            "🔔 Запрос доступа к VPN\n"
            f"👤 Имя: {message.from_user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n\n"
            f"Для выдачи: /approve {message.from_user.id}\n"
            f"Для блокировки: /block {message.from_user.id}",
        )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AuthStates.waiting_for_pin)
    await message.answer(texts.START_ASK_PIN)


@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext) -> None:
    await state.set_state(AuthStates.waiting_for_pin)
    await message.answer(texts.START_ASK_PIN)


@router.message(AuthStates.waiting_for_pin, F.text)
async def process_pin(message: Message, state: FSMContext, auth_service: AuthService) -> None:
    if message.from_user is None or message.text is None:
        return

    user = await auth_service.register_if_absent(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    pin_ok, user = await auth_service.check_pin(message.from_user.id, message.text.strip())
    if not pin_ok or user is None:
        await message.answer(texts.PIN_INVALID)
        return

    if user.access_status == "blocked":
        await message.answer(texts.PIN_BLOCKED)
        await state.clear()
        return

    if user.access_status != "approved":
        await message.answer(texts.PIN_PENDING)
        await _notify_admins_about_pending(message, auth_service)
        await state.clear()
        return

    await auth_service.login_approved(user)
    await state.clear()
    await message.answer(texts.PIN_APPROVED, reply_markup=main_menu(user.role == "admin"))


@router.message(Command("approve"))
async def cmd_approve(message: Message, users_repo: UsersRepository, auth_service: AuthService) -> None:
    if message.from_user is None or message.text is None:
        return
    if message.from_user.id not in auth_service.admin_ids:
        await message.answer("Команда только для админа.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /approve <telegram_id>")
        return
    target = int(parts[1])
    await users_repo.set_access_status(target, "approved")
    await message.answer(f"✅ Доступ выдан: {target}")
    try:
        await message.bot.send_message(target, texts.PIN_APPROVED)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to notify approved user", telegram_id=target)


@router.message(Command("block"))
async def cmd_block(message: Message, users_repo: UsersRepository, auth_service: AuthService) -> None:
    if message.from_user is None or message.text is None:
        return
    if message.from_user.id not in auth_service.admin_ids:
        await message.answer("Команда только для админа.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /block <telegram_id>")
        return
    target = int(parts[1])
    await users_repo.set_access_status(target, "blocked")
    await message.answer(f"⛔ Пользователь заблокирован: {target}")
    try:
        await message.bot.send_message(target, "⛔ Доступ к VPN заблокирован администратором.")
    except Exception:  # noqa: BLE001
        logger.warning("Failed to notify blocked user", telegram_id=target)
