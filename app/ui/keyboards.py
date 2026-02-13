"""Telegram keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.ui.labels import (
    BTN_AUDIT,
    BTN_HELP,
    BTN_INSTALL,
    BTN_MIKROTIK,
    BTN_REISSUE,
    BTN_REQUESTS,
    BTN_SETTINGS,
    BTN_STATUS,
    BTN_TROUBLE,
    BTN_USERS,
    BTN_VPN_REQUEST,
)


def _user_rows() -> list[list[KeyboardButton]]:
    return [
        [KeyboardButton(text=BTN_VPN_REQUEST), KeyboardButton(text=BTN_REISSUE)],
        [KeyboardButton(text=BTN_STATUS), KeyboardButton(text=BTN_HELP)],
        [KeyboardButton(text=BTN_INSTALL), KeyboardButton(text=BTN_TROUBLE)],
    ]


def _admin_rows() -> list[list[KeyboardButton]]:
    return [
        [KeyboardButton(text=BTN_REQUESTS), KeyboardButton(text=BTN_USERS)],
        [KeyboardButton(text=BTN_MIKROTIK), KeyboardButton(text=BTN_AUDIT)],
    ]


def _superadmin_rows() -> list[list[KeyboardButton]]:
    return [[KeyboardButton(text=BTN_SETTINGS)]]


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
