"""Handlers for creating and viewing user WireGuard connections."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.repositories import UsersRepository, WireGuardConfigsRepository
from app.services.wireguard_service import WireGuardService
from app.utils.ip_pool import allocate_next_ip
from app.utils.session import SessionManager

router = Router(name="connections")


@router.message(Command("new_connection"))
async def cmd_new_connection(
    message: Message,
    session_manager: SessionManager,
    users_repo: UsersRepository,
    wg_repo: WireGuardConfigsRepository,
    wg_service: WireGuardService,
) -> None:
    """Create new WireGuard client profile for authenticated user."""

    if message.from_user is None:
        return

    role = await session_manager.get_role(message.from_user.id)
    if role is None:
        await message.answer("Сессия истекла. Выполните /login")
        return

    user = await users_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
        return

    used_ips = await wg_repo.used_ips()
    ip_address = allocate_next_ip(wg_service.settings.wg_network_cidr, used_ips)
    creds = wg_service.generate_profile(ip_address=ip_address)
    config_text = wg_service.render_config(creds)

    config_id = await wg_repo.create(
        user_id=user.id,
        private_key=creds.private_key,
        public_key=creds.public_key,
        preshared_key=creds.preshared_key,
        ip_address=creds.ip_address,
        config_text=config_text,
    )

    await message.answer(
        f"Новый профиль создан (ID: {config_id}).\n"
        f"IP: {creds.ip_address}\n\n"
        f"<pre>{config_text}</pre>"
    )


@router.message(Command("my_connections"))
async def cmd_my_connections(
    message: Message,
    session_manager: SessionManager,
    users_repo: UsersRepository,
    wg_repo: WireGuardConfigsRepository,
) -> None:
    """List user's generated WireGuard profiles."""

    if message.from_user is None:
        return

    role = await session_manager.get_role(message.from_user.id)
    if role is None:
        await message.answer("Сессия истекла. Выполните /login")
        return

    user = await users_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
        return

    configs = await wg_repo.list_for_user(user.id)
    if not configs:
        await message.answer("У вас пока нет подключений. Используйте /new_connection")
        return

    lines = ["Ваши подключения:"]
    for item in configs:
        lines.append(f"- ID {item['id']} | IP {item['ip_address']} | active={item['is_active']}")

    await message.answer("\n".join(lines))
