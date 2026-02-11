"""Handlers for creating and viewing user WireGuard connections."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.repositories import (
    DuplicateIPAddressError,
    UsersRepository,
    WireGuardConfigsRepository,
)
from app.services.wireguard_service import WireGuardService

router = Router(name="connections")


@router.message(Command("new_connection"))
async def cmd_new_connection(
    message: Message,
    users_repo: UsersRepository,
    wg_repo: WireGuardConfigsRepository,
    wg_service: WireGuardService,
) -> None:
    """Create new WireGuard client profile for authenticated user."""

    if message.from_user is None:
        return

    user = await users_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
        return

    def build_profile(ip_address: str) -> tuple[str, str, str, str]:
        creds = wg_service.generate_profile(ip_address=ip_address)
        return (
            creds.private_key,
            creds.public_key,
            creds.preshared_key,
            wg_service.render_config(creds),
        )

    try:
        config_id, ip_address, config_text = await wg_repo.allocate_and_create(
            user_id=user.id,
            network_cidr=wg_service.settings.wg_network_cidr,
            profile_builder=build_profile,
        )
    except DuplicateIPAddressError:
        await message.answer("Не удалось выделить уникальный IP. Попробуйте снова.")
        return

    await message.answer(
        f"Новый профиль создан (ID: {config_id}).\n"
        f"IP: {ip_address}\n\n"
        f"<pre>{config_text}</pre>"
    )


@router.message(Command("my_connections"))
async def cmd_my_connections(
    message: Message,
    users_repo: UsersRepository,
    wg_repo: WireGuardConfigsRepository,
) -> None:
    """List user's generated WireGuard profiles."""

    if message.from_user is None:
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
