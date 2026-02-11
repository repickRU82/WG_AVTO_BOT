"""Application entrypoint for aiogram bot."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from redis.asyncio import Redis

from app.config import get_settings
from app.database import Database
from app.database.repositories import LogsRepository, UsersRepository, WireGuardConfigsRepository
from app.handlers import register_routers
from app.services.auth_service import AuthService
from app.services.mikrotik_service import MikroTikService
from app.services.wireguard_service import WireGuardService
from app.utils.logger import setup_logging
from app.utils.session import SessionManager


async def set_bot_commands(bot: Bot) -> None:
    """Register MVP command list in Telegram UI."""

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать работу"),
            BotCommand(command="login", description="Войти по PIN"),
            BotCommand(command="menu", description="Открыть меню"),
            BotCommand(command="new_connection", description="Создать WireGuard подключение"),
            BotCommand(command="my_connections", description="Мои подключения"),
        ]
    )


async def main() -> None:
    """Bootstrap app services and start long-polling."""

    settings = get_settings()
    setup_logging(settings.log_level)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode(settings.bot_parse_mode)))
    dp = Dispatcher()

    database = Database(settings.database_dsn)
    await database.connect()
    await database.init_schema()

    redis = Redis.from_url(settings.redis_dsn, decode_responses=False)
    sessions = SessionManager(redis=redis, ttl_seconds=settings.session_ttl_seconds)

    users_repo = UsersRepository(database.pool)
    logs_repo = LogsRepository(database.pool)
    wg_repo = WireGuardConfigsRepository(database.pool)

    auth_service = AuthService(
        users_repo=users_repo,
        logs_repo=logs_repo,
        sessions=sessions,
        pin_bcrypt_rounds=settings.pin_bcrypt_rounds,
        admin_ids=settings.admin_ids,
    )
    wg_service = WireGuardService(settings=settings)
    mikrotik_service = MikroTikService(settings=settings)

    dp["settings"] = settings
    dp["db"] = database
    dp["redis"] = redis
    dp["session_manager"] = sessions
    dp["users_repo"] = users_repo
    dp["logs_repo"] = logs_repo
    dp["wg_repo"] = wg_repo
    dp["auth_service"] = auth_service
    dp["wg_service"] = wg_service
    dp["mikrotik_service"] = mikrotik_service

    register_routers(dp)
    await set_bot_commands(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await redis.close()
        await database.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
