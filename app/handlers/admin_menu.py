"""Admin menu handlers for reply keyboard admin actions."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.repositories import LogsRepository, UsersRepository
from app.handlers.connections import run_mikrotik_test
from app.services.mikrotik_service import MikroTikService
from app.ui.labels import BTN_AUDIT, BTN_MIKROTIK, BTN_REQUESTS, BTN_SETTINGS, BTN_USERS

router = Router(name="admin_menu")

_ADMIN_ONLY_MESSAGE = "Доступно только администраторам"


def _is_admin(role: str) -> bool:
    return role in {"admin", "superadmin"}


@router.message(F.text == BTN_MIKROTIK)
async def mikrotik_from_menu(message: Message, session_role: str, mikrotik_service: MikroTikService) -> None:
    if not _is_admin(session_role):
        await message.answer(_ADMIN_ONLY_MESSAGE)
        return
    await run_mikrotik_test(message, session_role, mikrotik_service)


@router.message(F.text == BTN_AUDIT)
async def audit_from_menu(message: Message, session_role: str, logs_repo: LogsRepository) -> None:
    if not _is_admin(session_role):
        await message.answer(_ADMIN_ONLY_MESSAGE)
        return

    rows = await logs_repo.list_recent(limit=20)
    if not rows:
        await message.answer("Журнал пока пуст.")
        return

    lines = ["🧾 Последние 20 событий:"]
    for row in rows:
        lines.append(
            f"• #{row['id']} | {row['event_type']} | user_id={row['user_id'] or '-'} | {row['created_at']}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_REQUESTS)
async def requests_from_menu(message: Message, session_role: str, users_repo: UsersRepository) -> None:
    if not _is_admin(session_role):
        await message.answer(_ADMIN_ONLY_MESSAGE)
        return

    pending = await users_repo.list_pending()
    if not pending:
        await message.answer("Нет заявок в статусе pending.")
        return

    await message.answer(f"Найдено заявок: {len(pending)}")
    for row in pending:
        telegram_id = int(row["telegram_id"])
        username = row["username"] or "(без username)"
        full_name = row["full_name"] or "(без имени)"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"admin:approve:{telegram_id}"),
                    InlineKeyboardButton(text="⛔ Reject", callback_data=f"admin:reject:{telegram_id}"),
                ]
            ]
        )
        await message.answer(
            f"🧑‍💼 Заявка\nID: {telegram_id}\nUsername: {username}\nИмя: {full_name}",
            reply_markup=kb,
        )


@router.message(F.text == BTN_USERS)
async def users_from_menu(message: Message, session_role: str, users_repo: UsersRepository) -> None:
    if not _is_admin(session_role):
        await message.answer(_ADMIN_ONLY_MESSAGE)
        return

    rows = await users_repo.list_recent(limit=20)
    if not rows:
        await message.answer("Пользователи не найдены.")
        return

    lines = ["👥 Последние пользователи:"]
    for row in rows:
        lines.append(
            f"• {row['telegram_id']} | @{row['username'] or '-'} | {row['role']} | {row['access_status']}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text.regexp(r"^/users\s+.+"))
async def users_search(message: Message, session_role: str, users_repo: UsersRepository) -> None:
    if message.text is None:
        return
    if not _is_admin(session_role):
        await message.answer(_ADMIN_ONLY_MESSAGE)
        return

    query = message.text.split(maxsplit=1)[1].strip()
    rows = await users_repo.search(query, limit=20)
    if not rows:
        await message.answer("Совпадений не найдено.")
        return

    lines = [f"🔎 Найдено: {len(rows)}"]
    for row in rows:
        lines.append(
            f"• {row['telegram_id']} | @{row['username'] or '-'} | {row['role']} | {row['access_status']}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_SETTINGS)
async def settings_from_menu(message: Message, session_role: str) -> None:
    if session_role != "superadmin":
        await message.answer(_ADMIN_ONLY_MESSAGE)
        return
    await message.answer("⚙️ Настройки: пока не реализовано.")


@router.callback_query(F.data.regexp(r"^admin:(approve|reject):\d+$"))
async def process_request_action(callback: CallbackQuery, session_role: str, users_repo: UsersRepository) -> None:
    if callback.data is None:
        return
    if not _is_admin(session_role):
        await callback.answer(_ADMIN_ONLY_MESSAGE, show_alert=True)
        return

    action, telegram_id_raw = callback.data.split(":")[1:]
    target_telegram_id = int(telegram_id_raw)
    new_status = "approved" if action == "approve" else "blocked"
    await users_repo.set_access_status(target_telegram_id, new_status)

    if callback.message is not None:
        text_status = "одобрена" if action == "approve" else "отклонена"
        await callback.message.answer(f"Заявка {target_telegram_id} {text_status}.")
    await callback.answer("Готово")
