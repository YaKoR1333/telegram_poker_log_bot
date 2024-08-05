import datetime
import os

from asyncio import create_task, sleep

from aiogram.enums import ParseMode

import app.keyboards.group_keyboards as kb

from aiogram.exceptions import TelegramBadRequest
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram import F

from app.db.requests import (
    update_session_buy_in,
    update_session_end_time,
    add_lud_session,
    get_current_lud_session,
    get_user_by_tg_id,
    add_payments,
    get_session_deposit,
    get_current_inaccuracy_session,
)

from app.filter import (
    NonPrivateTypeFilter,
    NonRegFilter,
    SessionStartFilter,
    SessionNonStartFilter,
    AdminFilter,
)

from app.lud_logic import (
    get_payments_and_debtors_data,
    is_int_more_zero,
)

from app.db.models import Payments

group_router = Router()
group_router.message.filter(
    NonPrivateTypeFilter(),
)

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
bot = Bot(API_TOKEN, parse_mode=ParseMode.HTML)


async def remove_keyboard_after_delay(chat_id, message_id, delay):
    """Удаляет инлайн клавиатуру сообщения через определённое количество времени"""
    await sleep(delay)
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
    except TelegramBadRequest:
        pass


class CashForm(StatesGroup):
    buy_in = State()


async def debtor_mailing(debtors_data: dict) -> None:
    """Рассылает всем игрокам в плюсе (коллекторам) сообщение об их должниках и добавляет строку платежа в БД"""
    payments_list = []
    lud_session = await get_current_lud_session()
    for collector_id, debtor_data in debtors_data.items():
        collector = await get_user_by_tg_id(collector_id)  # FIXME убрать запросы к бд в цикле
        message = "Сегодня вы мистер плюсовый!\nВаши должники:\n"
        for debtor_id, debtor_cash in debtor_data.items():
            debtor = await get_user_by_tg_id(debtor_id)  # FIXME убрать запросы к бд в цикле
            payments_list.append(
                Payments(
                    debtor_id=debtor.id,
                    collector_id=collector.id,
                    cash_received=debtor_cash,
                    lud_session_id=lud_session.id,
                )
            )
            debtor_tg_name = debtor.tg_name
            message += (
                f"\nПользователь @{debtor_tg_name}\n"
                f"Должен {debtor_cash} рублей\n"
            )

        await bot.send_message(chat_id=collector_id, text=message)

    await add_payments(payments_list)


async def collectors_mailing(collectors_data: dict) -> None:
    """Рассылает всем игрокам в минусе (должникам) сообщение кому они должны перевести деньги
     и по каким реквизитам, если они указаны"""
    for debtor_id, collector_data in collectors_data.items():
        message = "В следующий раз повезёт!\n"
        for collector_id, collector_cash in collector_data.items():
            collector = await get_user_by_tg_id(collector_id)
            collector_tg_name, collector_requisites = collector.tg_name, collector.requisites
            message += (
                f"\nПереведите {collector_cash} рублей\n"
                f"Пользователю @{collector_tg_name}\n"
                f"По реквезитам {collector_requisites}\n"
            )

        await bot.send_message(chat_id=debtor_id, text=message)


@group_router.message(
    CommandStart(),
    NonRegFilter(),
)
async def bot_start(message: Message) -> None:
    """Запуск бота в gm"""
    welcome_text = "Всем привет, я буду вести логи ваших игр 👋\nи записывать статистику\n\n" \
                   "Инструкция:\n\n" \
                   "* Кнопка Начать лудо-сессию - начинает игровую сессию," \
                   " кнопки rebuy и cash out в личных сообщениях становятся активными\n\n" \
                   "Следующие кнопки появятся после запуска сессии:\n\n" \
                   "* Кнопка Остановить лудо-сессию - останавливает сессию, выводит краткие итоги" \
                   " и рассылает в личные сообщения кому вы должны/кто должен вам\n\n" \
                   "* Кнопка Изменить buy-in - изменяет buy in в текущей сессии\n\n" \
                   "* Кнопка Текущая погрешность - показывает текущую погрешность в сессии" \
                   " (разницу между выигранными деньгами и проигранными)\n\n" \
                   "developed by @yacor123\n"
    if await get_current_lud_session() is not None:
        await message.answer(welcome_text + "сессия уже идёт!", reply_markup=kb.main_session_start)
    else:
        await message.answer(welcome_text, reply_markup=kb.main)


@group_router.message(
    Command("session-start"),
    NonRegFilter(),
    AdminFilter(),
    SessionNonStartFilter(),
)
@group_router.message(
    F.text.regexp(r"Начать лудо-сессию|начать лудо-сессию"),
    NonRegFilter(),
    AdminFilter(),
    SessionNonStartFilter(),
)
async def session_start_handler(message: Message) -> None:
    """Запустить игровую сессию со стандартным buy in"""
    buy_in, chat_id = 500, message.chat.id
    await add_lud_session(buy_in, chat_id)
    await message.reply("Лудка началась 🥳 🥳 🥳", reply_markup=kb.main_session_start)


@group_router.message(
    Command("session-stop"),
    SessionStartFilter(),
    NonRegFilter(),
    AdminFilter(),
)
@group_router.message(
    F.text.regexp(r"Остановить лудо-сессию|остановить лудо-сессию"),
    SessionStartFilter(),
    NonRegFilter(),
    AdminFilter(),
)
async def session_end_handler(message: Message) -> None:
    """Закончить игровую сессию и сделать расчёт разыгранных денег и потерянных денег"""
    collectors_data, debtors_data = await get_payments_and_debtors_data()
    lud_session = await get_current_lud_session()
    cash_loss = await get_session_deposit(lud_session.id)
    await collectors_mailing(collectors_data)
    await debtor_mailing(debtors_data)
    await update_session_end_time(datetime.datetime.now())
    await message.reply(f"Лудка закончилась 😞 😞 😞\n\n"
                        f"Краткие итоги сессии:\n\n"
                        f"Всего было разыгранно денег: {cash_loss}\n"
                        f"Потерянно денег из-за неверного подсчёта: {lud_session.inaccuracy}",
                        reply_markup=kb.main)


@group_router.message(
    Command("change_buy_in"),
    SessionStartFilter(),
    NonRegFilter(),
    AdminFilter(),
)
@group_router.message(
    F.text.regexp(r"Изменить buy-in|изменить buy-in"),
    SessionStartFilter(),
    NonRegFilter(),
    AdminFilter(),
)
async def new_buy_in_handler(message: Message, state: FSMContext) -> None:
    """Изменить buy in текущей сессии"""
    user_name = message.from_user.username
    message_answer = await message.reply(f"@{user_name} введите новый buy_in лудо-сесии",
                                         reply_markup=kb.get_cansel_inline_button())
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 60))
    await state.set_state(CashForm.buy_in)


@group_router.message(
    F.text.regexp(r"Текущая погрешность|текущая погрешность"),
    SessionStartFilter(),
    NonRegFilter(),
    AdminFilter(),
)
async def current_inaccuracy_handler(message: Message) -> None:
    """Текущая погрешность в сессии"""
    inaccuracy = await get_current_inaccuracy_session()
    await message.reply(f"Текущая погрешность в сессии {inaccuracy}", reply_markup=kb.main_session_start)


@group_router.message(CashForm.buy_in)
async def update_buy_in_form(message: Message, state: FSMContext) -> None:
    """Форма для изменения buy in текущей сессии"""
    user_id, user_name, buy_in = message.from_user.id, message.from_user.username, message.text.strip()
    buy_in_int = await is_int_more_zero(buy_in)
    if buy_in_int:
        await state.update_data(buy_in=buy_in_int)
        await update_session_buy_in(buy_in_int)
        await message.answer(f"@{user_name} buy-in лудо-сесии изменён на {buy_in_int}")
        await state.clear()
    else:
        message_answer = await message.answer(f"@{user_name} buy-in должен быть целым числом больше 0",
                                              reply_markup=kb.get_cansel_inline_button())
        create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 60))
        await state.set_state(CashForm.buy_in)


@group_router.callback_query(
    F.data.casefold() == "cancel",
    NonRegFilter(),
)
async def cancel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback для инлайн кнопки отмена"""
    current_state = await state.get_state()

    if current_state is None:
        return

    await state.clear()
    await callback.answer("Отмена")
    await callback.message.delete()
