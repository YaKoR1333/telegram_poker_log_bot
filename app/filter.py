from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.db.requests import get_user_by_tg_id, get_current_lud_session


class PrivateTypeFilter(BaseFilter):
    """Фильтр для определения сообщений в приватных чатах (pm)"""
    async def __call__(self, message: Message) -> bool:
        return message.chat.type == "private"


class NonPrivateTypeFilter(BaseFilter):
    """Фильтр для определения сообщений в НЕ приватных чатах (gm)"""
    async def __call__(self, message: Message) -> bool:
        return message.chat.type != "private"


class AdminFilter(BaseFilter):
    """Фильтр для определения является ли пользователь админом"""
    async def __call__(self, message: Message) -> bool:
        user_id, user_name = message.from_user.id, message.from_user.username
        user = await get_user_by_tg_id(user_id)
        if user.admin:
            return True
        else:
            await message.answer(f"@{user_name} эта команда доступна только админу")
            return False


class StatisticsViewingFilter(BaseFilter):
    """Фильтр для определения есть ли доступ у пользователя к просмотру статистики"""
    async def __call__(self, message: Message) -> bool:
        user_id, user_name = message.from_user.id, message.from_user.username
        user = await get_user_by_tg_id(user_id)
        if user.statistics_viewing:
            return True
        else:
            await message.answer(f"@{user_name} к сожалению вы не можете просматривать статистику")
            return False


class NonRegFilter(BaseFilter):
    """Фильтр для определения есть ли доступ у пользователя к просмотру статистики"""
    async def __call__(self, message: Message) -> bool:
        user_id, user_name = message.from_user.id, message.from_user.username
        user = await get_user_by_tg_id(user_id)
        if user:
            return True
        else:
            await message.answer(f"@{user_name} В начале нужно познакомиться\nНапиши мне в личные сообщения")
            return False


class SessionStartFilter(BaseFilter):
    """Фильтр для определения запущенной сессии"""
    async def __call__(self, *args, **kwargs) -> bool:
        current_session = await get_current_lud_session()
        if current_session is None:
            return False
        else:
            return True


class SessionNonStartFilter(BaseFilter):
    """Фильтр для определения НЕ запущенной сессии"""
    async def __call__(self, *args, **kwargs) -> bool:
        current_session = await get_current_lud_session()
        if current_session is None:
            return True
        else:
            return False
