"""
keyboards/reply.py — ReplyKeyboardMarkup definitions for FinGuard.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# ─── Main menu (shown after onboarding is complete) ───────────────
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔔 Уведомления"),
            KeyboardButton(text="💳 Проверить покупку"),
            KeyboardButton(text="🎮 Что если?"),
        ],
        [
            KeyboardButton(text="📊 Статус"),
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),
            KeyboardButton(text="📜 История"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Введи покупку или выбери действие…",
)

# ─── Convenience: remove keyboard during FSM input ────────────────
remove_kb = ReplyKeyboardRemove()
