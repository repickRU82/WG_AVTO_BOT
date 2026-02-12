"""Telegram keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

USER_BUTTONS = [
    [KeyboardButton(text="✅ Получить VPN"), KeyboardButton(text="🔄 Переустановить VPN")],
    [KeyboardButton(text="📄 Мой статус"), KeyboardButton(text="🧩 Как установить")],
    [KeyboardButton(text="🛠 Если не работает"), KeyboardButton(text="❓ Помощь")],
]

ADMIN_BUTTONS = [
    [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="➕ Выдать доступ")],
    [KeyboardButton(text="⛔ Заблокировать"), KeyboardButton(text="♻️ Перевыпустить пользователю")],
    [KeyboardButton(text="🧹 Удалить VPN у пользователя"), KeyboardButton(text="📊 Статистика")],
    [KeyboardButton(text="🧾 Логи (последние 50)")],
]


def main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = USER_BUTTONS + (ADMIN_BUTTONS if is_admin else [])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def reissue_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, переустановить", callback_data="reissue:confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reissue:cancel")],
        ]
    )
