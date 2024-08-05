from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.db.models import LudActionOnSession

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class HotReBuyCallbackFactory(CallbackData, prefix="hot_re_buy"):
    """Фабрика для горячих inline клавиш ребая"""
    value: int


class HotUserCallbackFactory(CallbackData, prefix="hot_user"):
    """Фабрика для горячих inline клавиш tg name юзеров"""
    value: str


class RightsCallbackFactory(CallbackData, prefix="rights"):
    """Фабрика для прав"""
    field: str
    value: bool


kb_main = [
    [
        KeyboardButton(text="Rebuy  💲"),
        KeyboardButton(text="Cash Out 💲 ➡️"),
    ],
    [
        KeyboardButton(text="Реквизиты 💳"),
        KeyboardButton(text="Статистика 📊"),
    ],
]

kb_requisites = [
    [
        KeyboardButton(text="Изменить реквизиты 💳"),
        KeyboardButton(text="Текущие реквизиты 💳"),
    ],
    [
        KeyboardButton(text="Назад ◀️"),
    ],
]

kb_statistics = [
    [
        KeyboardButton(text="Личная статистика 👤"),
        KeyboardButton(text="Общая статистика 👥"),
    ],
    [
        KeyboardButton(text="Топ лудов 🔝"),
    ],
    [
        KeyboardButton(text="Назад ◀️"),
    ],
]

kb_admin = [
    [
        KeyboardButton(text="Текущий лог сессии 📝"),
    ],
    [
        KeyboardButton(text="Добавить лог в текущую сессию ➕ 📝"),
    ],
    [
        KeyboardButton(text="Права 🛂"),
        KeyboardButton(text="Добавить сессию 🃏"),
    ],
    [
        KeyboardButton(text="Назад ◀️"),
    ],
]

main = ReplyKeyboardMarkup(keyboard=kb_main,
                           resize_keyboard=True,
                           )

requisites = ReplyKeyboardMarkup(keyboard=kb_requisites,
                                 resize_keyboard=True
                                 )

statistics = ReplyKeyboardMarkup(keyboard=kb_statistics,
                                 resize_keyboard=True
                                 )

admin = ReplyKeyboardMarkup(keyboard=kb_admin,
                            resize_keyboard=True
                            )


def get_cansel_inline_button() -> InlineKeyboardMarkup:
    """inline кнопка ОТМЕНА"""
    button = [
        [
            InlineKeyboardButton(text="Отмена", callback_data="cancel")
        ]
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=button)

    return kb


def get_cancel_and_action_inline_button() -> InlineKeyboardMarkup:
    """inline кнопка ОТМЕНА"""
    button = [
        [
            InlineKeyboardButton(text=f"{LudActionOnSession.RE_BUY.value}", callback_data="log_re_buy"),
            InlineKeyboardButton(text=f"{LudActionOnSession.CASH_OUT.value}", callback_data="log_cash_out")
        ],
        [
            InlineKeyboardButton(text="Отмена", callback_data="cancel")
        ],
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=button)

    return kb


def get_cansel_inline_button_and_hot_re_buy() -> InlineKeyboardMarkup:
    """inline кнопка ОТМЕНА и горячие кнопки ребая"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="500", callback_data=HotReBuyCallbackFactory(value=500),
    )
    builder.button(
        text="Отмена", callback_data="cancel"
    )
    builder.adjust(1)

    return builder.as_markup()


def get_cansel_inline_button_and_rights() -> InlineKeyboardMarkup:
    """inline кнопка ОТМЕНА и различные права пользователя"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="👀 Статистика ✅", callback_data=RightsCallbackFactory(field="statistics_viewing", value=True),
    )
    builder.button(
        text="👀 Статистика ❌", callback_data=RightsCallbackFactory(field="statistics_viewing", value=False),
    )
    builder.button(
        text="Права Админа ✅", callback_data=RightsCallbackFactory(field="admin", value=True),
    )
    builder.button(
        text="Права Админа ❌", callback_data=RightsCallbackFactory(field="admin", value=False),
    )
    builder.button(
        text="Отмена", callback_data="cancel"
    )
    builder.adjust(2)

    return builder.as_markup()


def get_cansel_inline_button_and_hot_user(user_list: list) -> InlineKeyboardMarkup:
    """inline кнопка ОТМЕНА и горячие кнопки tg name юзеров"""

    builder = InlineKeyboardBuilder()
    for user in user_list:
        builder.button(
            text=f"{user.tg_name}", callback_data=HotUserCallbackFactory(value=user.tg_name),
        )
    builder.button(
        text="Отмена", callback_data="cancel"
    )
    builder.adjust(3)

    return builder.as_markup()


def get_delete_and_change_log() -> InlineKeyboardMarkup:
    """inline кнопки УДАЛИТЬ и ИЗЕМЕНТЬ СУММУ для лога"""
    button = [
        [
            InlineKeyboardButton(text="Удалить", callback_data="delete_log"),
            InlineKeyboardButton(text="Изменить сумму", callback_data="change_summ"),
        ],
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=button)

    return kb
