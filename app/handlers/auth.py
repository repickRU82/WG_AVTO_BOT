"""Authentication handlers with PIN-based login/registration."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.services.auth_service import AuthService

router = Router(name="auth")


class AuthStates(StatesGroup):
    """FSM states for auth flow."""

    waiting_for_registration_pin = State()
    waiting_for_login_pin = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, auth_service: AuthService) -> None:
    """Start command: register new user or route existing to login."""

    if message.from_user is None:
        return

    user = await auth_service.users_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(
            "Добро пожаловать! Вы еще не зарегистрированы. "
            "Введите PIN (4-10 цифр), чтобы создать аккаунт."
        )
        await state.set_state(AuthStates.waiting_for_registration_pin)
        return

    await message.answer("Вы зарегистрированы. Для входа используйте /login")


@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext) -> None:
    """Ask for PIN and start login state."""

    await state.set_state(AuthStates.waiting_for_login_pin)
    await message.answer("Введите ваш PIN для входа:")


@router.message(AuthStates.waiting_for_registration_pin, F.text.regexp(r"^\d{4,10}$"))
async def register_with_pin(message: Message, state: FSMContext, auth_service: AuthService) -> None:
    """Register user with chosen PIN."""

    if message.from_user is None or message.text is None:
        return

    user = await auth_service.register_if_absent(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        pin=message.text,
    )
    await state.clear()
    await message.answer(
        f"Регистрация завершена. Роль: <b>{user.role}</b>. "
        "Теперь выполните /login для входа."
    )


@router.message(AuthStates.waiting_for_registration_pin)
async def invalid_registration_pin(message: Message) -> None:
    """Validate registration PIN format."""

    await message.answer("PIN должен быть числовым и длиной от 4 до 10 символов.")


@router.message(AuthStates.waiting_for_login_pin, F.text.regexp(r"^\d{4,10}$"))
async def login_with_pin(message: Message, state: FSMContext, auth_service: AuthService) -> None:
    """Login existing user and open menu on success."""

    if message.from_user is None or message.text is None:
        return

    success, role = await auth_service.login(telegram_id=message.from_user.id, pin=message.text)
    await state.clear()

    if not success:
        await message.answer("Неверный PIN или пользователь не найден. Повторите /login")
        return

    await message.answer(f"Успешный вход. Ваша роль: <b>{role}</b>. Используйте /menu")


@router.message(AuthStates.waiting_for_login_pin)
async def invalid_login_pin(message: Message) -> None:
    """Validate login PIN format."""

    await message.answer("PIN должен быть числовым и длиной от 4 до 10 символов.")
