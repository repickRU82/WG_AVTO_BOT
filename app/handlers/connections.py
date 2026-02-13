"""Handlers for creating and viewing user WireGuard connections."""

import io

from aiogram import F, Router
import structlog
from aiogram import F, Router
import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.database.repositories import (
    DuplicateIPAddressError,
    LogsRepository,
    UsersRepository,
    WireGuardConfigsRepository,
)
from app.services.mikrotik_service import MikroTikClientError, MikroTikService
from app.services.wireguard_service import WireGuardCredentials, WireGuardService
from app.ui.keyboards import reissue_confirm_keyboard
from app.utils.logging_compat import get_logger
from app.ui import texts

router = Router(name="connections")
logger = get_logger(__name__)


async def _ensure_peer(
    user_id: int,
    telegram_id: int,
    config_id: int,
    ip_address: str,
    public_key: str,
    preshared_key: str,
    mikrotik_service: MikroTikService,
    logs_repo: LogsRepository,
) -> str | None:
    try:
        action, peer_id = await mikrotik_service.ensure_wireguard_peer(
            telegram_id=telegram_id,
            config_id=config_id,
            public_key=public_key,
            ip_address=ip_address,
            preshared_key=preshared_key,
        )
        await logs_repo.add(
            event_type=f"mikrotik_peer_{action}",
            user_id=user_id,
            details={"telegram_id": telegram_id, "config_id": config_id, "ip_address": ip_address, "peer_id": peer_id},
        )
        return peer_id
    except MikroTikClientError as exc:
        logger.exception("Failed to sync WireGuard peer", telegram_id=telegram_id, config_id=config_id)
        await logs_repo.add(
            event_type="mikrotik_peer_add_failed",
            user_id=user_id,
            details={"telegram_id": telegram_id, "config_id": config_id, "ip_address": ip_address, "reason": str(exc)},
        )
        return None


async def _send_config(message: Message, telegram_id: int, config_text: str) -> None:
    await message.answer(texts.VPN_FILE_READY)
    filename = f"wg_{telegram_id}_{abs(hash(config_text)) % 100000}.conf"
    file_bytes = io.BytesIO(config_text.encode("utf-8"))
    file_bytes.name = filename
    await message.answer_document(document=file_bytes, caption="WireGuard config")
    await message.answer(texts.VPN_TEXT.format(config=config_text))
    await message.answer(texts.VPN_WARNING)
from app.ui import texts

router = Router(name="connections")
logger = structlog.get_logger(__name__)


async def _ensure_peer(
    user_id: int,
    telegram_id: int,
    config_id: int,
    ip_address: str,
    public_key: str,
    preshared_key: str,
    mikrotik_service: MikroTikService,
    logs_repo: LogsRepository,
) -> str | None:
    try:
        action, peer_id = await mikrotik_service.ensure_wireguard_peer(
            telegram_id=telegram_id,
            config_id=config_id,
            public_key=public_key,
            ip_address=ip_address,
            preshared_key=preshared_key,
        )
        await logs_repo.add(
            event_type=f"mikrotik_peer_{action}",
            user_id=user_id,
            details={"telegram_id": telegram_id, "config_id": config_id, "ip_address": ip_address, "peer_id": peer_id},
        )
        return peer_id
    except MikroTikClientError as exc:
        logger.exception("Failed to sync WireGuard peer", telegram_id=telegram_id, config_id=config_id)
        await logs_repo.add(
            event_type="mikrotik_peer_add_failed",
            user_id=user_id,
            details={"telegram_id": telegram_id, "config_id": config_id, "ip_address": ip_address, "reason": str(exc)},
        )
        return None


async def _send_config(message: Message, telegram_id: int, config_text: str) -> None:
    await message.answer(texts.VPN_FILE_READY)
    filename = f"wg_{telegram_id}_{abs(hash(config_text)) % 100000}.conf"
    file_bytes = io.BytesIO(config_text.encode("utf-8"))
    file_bytes.name = filename
    await message.answer_document(document=file_bytes, caption="WireGuard config")
    await message.answer(texts.VPN_TEXT.format(config=config_text))
    await message.answer(texts.VPN_WARNING)

router = Router(name="connections")
logger = structlog.get_logger(__name__)


@router.message(Command("new_connection"))
@router.message(F.text == "✅ Получить VPN")
async def cmd_new_connection(
    message: Message,
    users_repo: UsersRepository,
    logs_repo: LogsRepository,
    wg_repo: WireGuardConfigsRepository,
    wg_service: WireGuardService,
    mikrotik_service: MikroTikService,
) -> None:
    if message.from_user is None:
        return

    user = await users_repo.get_by_telegram_id(message.from_user.id)
    if user is None or user.access_status != "approved":
        await message.answer(texts.PIN_PENDING)
        return

    existing = await wg_repo.get_active_for_user(user.id)
    if existing is not None:
        await message.answer(texts.VPN_ALREADY_EXISTS)
        await _send_config(message, message.from_user.id, str(existing["config_text"]))
        return

    await message.answer(texts.VPN_PREPARE)

        return

    existing = await wg_repo.get_active_for_user(user.id)
    if existing is not None:
        await message.answer(texts.VPN_ALREADY_EXISTS)
        await _send_config(message, message.from_user.id, str(existing["config_text"]))
        return

    await message.answer(texts.VPN_PREPARE)

    telegram_id = message.from_user.id
    user = await users_repo.get_by_telegram_id(telegram_id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
        return

    profile_cache: dict[str, WireGuardCredentials] = {}

    def build_profile(ip_address: str) -> tuple[str, str, str, str]:
        creds = wg_service.generate_profile(ip_address=ip_address)
        profile_cache[ip_address] = creds
        return creds.private_key, creds.public_key, creds.preshared_key, wg_service.render_config(creds)
        return (
            creds.private_key,
            creds.public_key,
            creds.preshared_key,
            wg_service.render_config(creds),
        )

    try:
        config_id, ip_address, config_text, public_key, preshared_key = await wg_repo.allocate_and_create(
            user_id=user.id,
            telegram_id=message.from_user.id,
            network_cidr=wg_service.settings.wg_network_cidr,
            profile_builder=build_profile,
        )
    except DuplicateIPAddressError:
        await message.answer("Не удалось выделить уникальный IP. Попробуйте снова.")
        return

    peer_id = None
    if mikrotik_service.settings.mikrotik_enabled:
        peer_id = await _ensure_peer(
            user_id=user.id,
            telegram_id=message.from_user.id,
            config_id=config_id,
            ip_address=ip_address,
            public_key=public_key,
            preshared_key=preshared_key,
            mikrotik_service=mikrotik_service,
            logs_repo=logs_repo,
        )
    await wg_repo.attach_mikrotik_peer(config_id, peer_id)
    if mikrotik_service.settings.mikrotik_enabled and peer_id is None and not mikrotik_service.settings.mikrotik_dry_run:
        await message.answer(texts.MIKROTIK_FAIL)
    await _send_config(message, message.from_user.id, config_text)
    credentials = profile_cache[ip_address]

    if mikrotik_service.settings.mikrotik_enabled:
        try:
            action, peer_id = await mikrotik_service.ensure_wireguard_peer(
                telegram_id=telegram_id,
                config_id=config_id,
                public_key=credentials.public_key,
                ip_address=ip_address,
                preshared_key=credentials.preshared_key,
            )
            await logs_repo.add(
                event_type=f"mikrotik_peer_{action}",
                user_id=user.id,
                details={
                    "telegram_id": telegram_id,
                    "config_id": config_id,
                    "ip_address": ip_address,
                    "peer_id": peer_id,
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
                "Конфиг создан, но peer на сервере не создан — обратитесь к администратору."
            )

    await message.answer(
        f"Новый профиль создан (ID: {config_id}).\n"
        f"IP: {ip_address}\n\n"
        f"<pre>{config_text}</pre>"
    )


@router.message(Command("my_connections"))
@router.message(F.text == "📄 Мой статус")
async def my_status(message: Message, users_repo: UsersRepository, wg_repo: WireGuardConfigsRepository) -> None:
    if message.from_user is None:
        return
    user = await users_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
    if message.from_user is None:
        return
    user = await users_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Пользователь не найден. Выполните /start")
        return
    cfg = await wg_repo.get_active_for_user(user.id)
    vpn = "выдан" if cfg else "не выдан"
    last = str(cfg["created_at"]) if cfg else "—"
    await message.answer(
        f"📄 Твой статус: {user.access_status.upper()}\n🔐 VPN: {vpn}\n🕒 Последняя выдача: {last}\n"
        "🧩 Устройство: можно подключать только на одно (через этот бот)"
    )


@router.message(F.text == "🔄 Переустановить VPN")
async def ask_reissue(message: Message) -> None:
    await message.answer(texts.REISSUE_CONFIRM, reply_markup=reissue_confirm_keyboard())


@router.callback_query(F.data == "reissue:cancel")
async def cancel_reissue(callback: CallbackQuery) -> None:
    await callback.message.answer("Отменено.")
    await callback.answer()


@router.callback_query(F.data == "reissue:confirm")
async def confirm_reissue(
    callback: CallbackQuery,
    users_repo: UsersRepository,
    wg_repo: WireGuardConfigsRepository,
    wg_service: WireGuardService,
    logs_repo: LogsRepository,
    mikrotik_service: MikroTikService,
) -> None:
    if callback.from_user is None or callback.message is None:
        return
    user = await users_repo.get_by_telegram_id(callback.from_user.id)
    if user is None or user.access_status != "approved":
        await callback.message.answer(texts.PIN_PENDING)
        await callback.answer()
        return

    def build_profile(ip_address: str) -> tuple[str, str, str, str]:
        creds = wg_service.generate_profile(ip_address=ip_address)
        return creds.private_key, creds.public_key, creds.preshared_key, wg_service.render_config(creds)

    config_id, ip, config_text, public_key, psk, _ = await wg_repo.reissue_for_user(
        user.id,
        callback.from_user.id,
        build_profile,
    )
    peer_id = None
    if mikrotik_service.settings.mikrotik_enabled:
        peer_id = await _ensure_peer(
            user_id=user.id,
            telegram_id=callback.from_user.id,
            config_id=config_id,
            ip_address=ip,
            public_key=public_key,
            preshared_key=psk,
            mikrotik_service=mikrotik_service,
            logs_repo=logs_repo,
        )
    await wg_repo.attach_mikrotik_peer(config_id, peer_id)

    await callback.message.answer(texts.REISSUE_DONE)
    await _send_config(callback.message, callback.from_user.id, config_text)
    await callback.answer()


@router.message(Command("mt_test"))
async def cmd_mt_test(message: Message, session_role: str, mikrotik_service: MikroTikService) -> None:
    if message.from_user is None:
        return
    if session_role != "admin":
        await message.answer("Команда доступна только администраторам.")
        return
    try:
        identity, peers_count = await mikrotik_service.test_connection()
    except MikroTikClientError as exc:
        await message.answer(f"MikroTik test failed: {exc}")
        return
    await message.answer(
        f"MikroTik API OK\nIdentity: {identity}\nInterface: {mikrotik_service.settings.wg_interface_name}\nPeers: {peers_count}"
    await message.answer("\n".join(lines))


@router.message(Command("mt_test"))
async def cmd_mt_test(
    message: Message,
    mikrotik_service: MikroTikService,
    session_role: str,
) -> None:
    """Admin command for MikroTik API diagnostics."""

    if message.from_user is None:
        return

    if session_role != "admin":
        await message.answer("Команда доступна только администраторам.")
        return
    cfg = await wg_repo.get_active_for_user(user.id)
    vpn = "выдан" if cfg else "не выдан"
    last = str(cfg["created_at"]) if cfg else "—"
    await message.answer(
        f"📄 Твой статус: {user.access_status.upper()}\n🔐 VPN: {vpn}\n🕒 Последняя выдача: {last}\n"
        "🧩 Устройство: можно подключать только на одно (через этот бот)"
    )


@router.message(F.text == "🔄 Переустановить VPN")
async def ask_reissue(message: Message) -> None:
    await message.answer(texts.REISSUE_CONFIRM, reply_markup=reissue_confirm_keyboard())


@router.callback_query(F.data == "reissue:cancel")
async def cancel_reissue(callback: CallbackQuery) -> None:
    await callback.message.answer("Отменено.")
    await callback.answer()


@router.callback_query(F.data == "reissue:confirm")
async def confirm_reissue(
    callback: CallbackQuery,
    users_repo: UsersRepository,
    wg_repo: WireGuardConfigsRepository,
    wg_service: WireGuardService,
    logs_repo: LogsRepository,
    mikrotik_service: MikroTikService,
) -> None:
    if callback.from_user is None or callback.message is None:
    if not mikrotik_service.settings.mikrotik_enabled:
        await message.answer("MikroTik интеграция отключена (MIKROTIK_ENABLED=false).")
        return
    user = await users_repo.get_by_telegram_id(callback.from_user.id)
    if user is None or user.access_status != "approved":
        await callback.message.answer(texts.PIN_PENDING)
        await callback.answer()
        return

    def build_profile(ip_address: str) -> tuple[str, str, str, str]:
        creds = wg_service.generate_profile(ip_address=ip_address)
        return creds.private_key, creds.public_key, creds.preshared_key, wg_service.render_config(creds)

    config_id, ip, config_text, public_key, psk, _ = await wg_repo.reissue_for_user(
        user.id,
        callback.from_user.id,
        build_profile,
    )
    peer_id = None
    if mikrotik_service.settings.mikrotik_enabled:
        peer_id = await _ensure_peer(
            user_id=user.id,
            telegram_id=callback.from_user.id,
            config_id=config_id,
            ip_address=ip,
            public_key=public_key,
            preshared_key=psk,
            mikrotik_service=mikrotik_service,
            logs_repo=logs_repo,
        )
    await wg_repo.attach_mikrotik_peer(config_id, peer_id)

    await callback.message.answer(texts.REISSUE_DONE)
    await _send_config(callback.message, callback.from_user.id, config_text)
    await callback.answer()


@router.message(Command("mt_test"))
async def cmd_mt_test(message: Message, session_role: str, mikrotik_service: MikroTikService) -> None:
    if message.from_user is None:
        return
    if session_role != "admin":
        await message.answer("Команда доступна только администраторам.")
        return
    try:
        identity, peers_count = await mikrotik_service.test_connection()
    except MikroTikClientError as exc:
        await message.answer(f"MikroTik test failed: {exc}")
        return
    await message.answer(
        f"MikroTik API OK\nIdentity: {identity}\nInterface: {mikrotik_service.settings.wg_interface_name}\nPeers: {peers_count}"
    try:
        identity, peers_count = await mikrotik_service.test_connection()
    except MikroTikClientError as exc:
        logger.exception("MikroTik test failed", telegram_id=message.from_user.id)
        await message.answer(f"MikroTik test failed: {exc}")
        return

    await message.answer(
        "MikroTik API OK\n"
        f"Identity: {identity}\n"
        f"Interface: {mikrotik_service.settings.wg_interface_name}\n"
        f"Peers count: {peers_count}"
    )
