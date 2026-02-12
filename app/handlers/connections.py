"""Handlers for creating and viewing user WireGuard connections."""

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.repositories import (
    DuplicateIPAddressError,
    LogsRepository,
    UsersRepository,
    WireGuardConfigsRepository,
)
from app.services.mikrotik_service import MikroTikClientError, MikroTikService
from app.services.wireguard_service import WireGuardCredentials, WireGuardService

router = Router(name="connections")
logger = structlog.get_logger(__name__)


@router.message(Command("new_connection"))
async def cmd_new_connection(
    message: Message,
    users_repo: UsersRepository,
    logs_repo: LogsRepository,
    wg_repo: WireGuardConfigsRepository,
    wg_service: WireGuardService,
    mikrotik_service: MikroTikService,
) -> None:
    """Create new WireGuard client profile for authenticated user."""

    if message.from_user is None:
        return

    telegram_id = message.from_user.id
    user = await users_repo.get_by_telegram_id(telegram_id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
        return

    profile_cache: dict[str, WireGuardCredentials] = {}

    def build_profile(ip_address: str) -> tuple[str, str, str, str]:
        creds = wg_service.generate_profile(ip_address=ip_address)
        profile_cache[ip_address] = creds
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

    credentials = profile_cache[ip_address]

    if mikrotik_service.settings.mikrotik_enabled:
        try:
            created = await mikrotik_service.ensure_wireguard_peer(
                telegram_id=telegram_id,
                config_id=config_id,
                public_key=credentials.public_key,
                ip_address=ip_address,
                preshared_key=credentials.preshared_key,
            )
            event_type = "mikrotik_peer_added" if created else "mikrotik_peer_exists"
            await logs_repo.add(
                event_type=event_type,
                user_id=user.id,
                details={
                    "telegram_id": telegram_id,
                    "config_id": config_id,
                    "ip_address": ip_address,
                    "public_key_tail": credentials.public_key[-8:],
                },
            )
        except MikroTikClientError as exc:
            logger.exception(
                "Failed to add WireGuard peer on MikroTik",
                telegram_id=telegram_id,
                user_id=user.id,
                config_id=config_id,
                ip_address=ip_address,
            )
            await logs_repo.add(
                event_type="mikrotik_peer_add_failed",
                user_id=user.id,
                details={
                    "telegram_id": telegram_id,
                    "config_id": config_id,
                    "ip_address": ip_address,
                    "public_key_tail": credentials.public_key[-8:],
                    "reason": str(exc),
                },
            )
            await message.answer(
                "Конфиг создан, но применить на сервере не удалось — обратитесь к администратору."
            )

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
