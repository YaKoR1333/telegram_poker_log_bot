from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

kb_main = [
    [
        KeyboardButton(text="Начать лудо-сессию ✅"),
    ],
]

kb_main_session_start = [
    [
        KeyboardButton(text="Остановить лудо-сессию ❌"),
    ],
    [
        KeyboardButton(text="Изменить buy-in 💎"),
        KeyboardButton(text="Текущая погрешность↗️↙️"),
    ],
]


main = ReplyKeyboardMarkup(keyboard=kb_main,
                           resize_keyboard=True)

main_session_start = ReplyKeyboardMarkup(keyboard=kb_main_session_start,
                                         resize_keyboard=True)


def get_cansel_inline_button():
    button = [
        [
            InlineKeyboardButton(text="Отмена", callback_data="cancel")
        ]
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=button)

    return kb
