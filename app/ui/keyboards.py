"""Telegram keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def _user_rows() -> list[list[KeyboardButton]]:
    return [
        [KeyboardButton(text="✅ Запросить VPN"), KeyboardButton(text="🔄 Переустановить VPN")],
        [KeyboardButton(text="📄 Мой статус"), KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="🧩 Как установить"), KeyboardButton(text="🛠 Если не работает")],
    ]


def _admin_rows() -> list[list[KeyboardButton]]:
    return [
        [KeyboardButton(text="🧑‍💼 Заявки"), KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="🔧 MikroTik"), KeyboardButton(text="🧾 Журнал действий")],
    ]


def _superadmin_rows() -> list[list[KeyboardButton]]:
    return [[KeyboardButton(text="⚙️ Настройки")]]


def main_menu(role: str) -> ReplyKeyboardMarkup:
    rows = _user_rows()
    if role in {"admin", "superadmin"}:
        rows.extend(_admin_rows())
    if role == "superadmin":
        rows.extend(_superadmin_rows())
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def reissue_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, переустановить", callback_data="reissue:confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reissue:cancel")],
        ]
    )
