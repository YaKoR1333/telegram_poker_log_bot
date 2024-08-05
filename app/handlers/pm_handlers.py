import re

import app.keyboards.pm_keyboards as kb

from asyncio import create_task

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram import F

from app.db.requests import *
from app.filter import (
    PrivateTypeFilter,
    SessionStartFilter,
    StatisticsViewingFilter,
    AdminFilter
)
from app.lud_logic import (
    is_int_more_zero,
    add_action,
    parse_log_message
)
from app.handlers.group_handlers import bot, remove_keyboard_after_delay

from app.db.models import LudActionOnSession

requisites_regex = r"^\b\d{4}(\s*|-)\d{4}(\s*|-)\d{4}(\s*|-)\d{4}\b ?(( |-) ?[А-яA-z]+)?$|" \
                   r"^8\d{10} ?(( |-) ?[А-яA-z]+)?$|^\+7\d{10} ?(( |-) ?[А-яA-z]+)?$"

pm_router = Router()
pm_router.message.filter(PrivateTypeFilter())


class Form(StatesGroup):
    requisites = State()
    re_buy = State()
    cash_out = State()
    new_summ = State()
    tg_name = State()
    pressed_button = State()


async def get_hot_tg_name(message: Message, state: FSMContext, user_list: list) -> None:
    """Отображает инлайн клавиатуру со списком пользователей"""
    inline_keyboard = kb.get_cansel_inline_button_and_hot_user(user_list)
    answer_message = "Выберите из следующих юзеров\nЛибо введите желаемый tg name\nНапример: @yacor123"
    message_answer = await message.answer(answer_message,
                                          reply_markup=inline_keyboard)
    await state.set_state(Form.tg_name)
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))


async def get_next_inline_keyboard_after_tg_name(state: FSMContext) -> InlineKeyboardMarkup:
    """Отображает следующую клавиатуру после выбора tg name в зависимости от того какая была нажата кнопка до этого"""
    state_data = await state.get_data()
    pressed_button = state_data["pressed_button"]

    if pressed_button == "Права 🛂":
        return kb.get_cansel_inline_button_and_rights()
    else:
        return kb.get_cancel_and_action_inline_button()


async def add_action_handler(state: FSMContext,
                             action_data: dict,
                             user_bot_action: Message | CallbackQuery) -> None:
    """Обрабатывает действие юзера и отвечает сообщением в групповой чат"""
    state_data = await state.get_data()
    state_tg_name = await check_tg_name_state(state_data)
    message_answer = ""
    if state_tg_name:
        user = await get_user_by_tg_name(state_tg_name)
        action_data["user_id"] = user.tg_id
        message_answer += f"Админ @{action_data['user_name']} добавил лог:\n\n"
    message_answer += await add_action(action_data)
    await user_bot_action.answer(message_answer)
    await group_chat_log(message_answer)
    await state.clear()


async def check_tg_name_state(state_data: dict) -> str | None:
    """Проверяет есть ли в форме ключ tg_name"""
    try:
        tg_name = state_data["tg_name"]
        return tg_name
    except KeyError:
        return None


async def group_chat_log(message: str) -> None:
    """Отправляет сообщение в чат-группу с логом действия (RE_BUY/CASH_OUT) пользователя"""
    session = await get_current_lud_session()
    await bot.send_message(chat_id=session.chat_id, text=message)


@pm_router.message(CommandStart())
async def bot_start(message: Message) -> None:
    """Запуск бота в pm"""
    user_id, user_name = message.from_user.id, message.from_user.username
    user = await get_user_by_tg_id(user_id)
    welcome_text = "Инструкция:\n\n" \
                   "* Кнопка Rebuy - записывает ребай в текущую сессию\n\n" \
                   "* Кнопка Cash out - записывает количество фишек, оставшихся у вас в конце игры\n\n" \
                   "Если вы записывали ребай в текущей сессии и в конце у вас 0 фишек, Cash out можно не писать.\n" \
                   "Если вы НЕ записывали ребай в текущей сессии и в конце у вас 0 фишек, Cash out ОБЯЗАТЕЛЬНО" \
                   " писать, чтобы бот внёс вас как игрока в текущей сессии.\n\n" \
                   "* Кнопка Реквизиты - можно задать свои реквизиты, чтобы в конце сессии другие люди знали куда" \
                   " конкретно вам отправлять деньги\n\n" \
                   "* Кнопка Статистика - можно посмотреть личную статистику или статистику всей группы.\n\n" \
                   "Если вы сделали ошибку при вводе Rebuy/Cash out обратитесь к админам.\n\n" \
                   "developed by @yacor123"
    if user:
        await message.answer(f"С возвращением @{user_name} 👋\n\n" + welcome_text, reply_markup=kb.main)
    else:
        if user_name is None:
            await message.answer("Задайте username в настройках телеграмма для корректной работы бота\n"
                                 "После снова используйте команду /start")
        else:
            await add_user(user_id, user_name)
            await message.answer(f"Добро пожаловать @{user_name} 👋\n\n" + welcome_text, reply_markup=kb.main)


@pm_router.message(Form.requisites)
async def update_requisites_form(message: Message, state: FSMContext) -> None:
    """Форма для изменения реквизитов"""
    user_id, user_name, requisites = message.from_user.id, message.from_user.username, message.text.strip()
    if re.findall(requisites_regex, requisites):
        await state.update_data(requisites=requisites)
        await update_requisites(user_id, message.text)
        answer_message = f"@{user_name} ваши реквизиты обновлены"
        await message.reply(answer_message)
        await state.clear()
    else:
        answer_message = f"@{user_name} неверный формат реквизитов\nВведите реквезиты повторно"
        message_answer = await message.reply(answer_message, reply_markup=kb.get_cansel_inline_button())
        create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 60))
        await state.set_state(Form.requisites)


@pm_router.message(Command("back"))
@pm_router.message(F.text.regexp(r"Назад|назад"))
async def back_main_menu_handler(message: Message) -> None:
    """Отображает main клавиатуру"""
    await message.reply("Назад", reply_markup=kb.main)


@pm_router.message(Command("requisites"))
@pm_router.message(F.text.regexp(r"Реквизиты|реквизиты"))
async def get_requisites_kb_handler(message: Message) -> None:
    """Отображает клавиатуру для реквизитов"""
    await message.reply("Реквизиты", reply_markup=kb.requisites)


@pm_router.message(Command("change_requisites"))
@pm_router.message(F.text.regexp(r"Изменить реквизиты|изменить реквизиты"))
async def update_requisites_handler(message: Message, state: FSMContext) -> None:
    """Изменить реквизиты"""
    await state.set_state(Form.requisites)
    message_answer = await message.reply("Введите новые реквизиты (номер карты или телефона)\nПример: 88005553535 - "
                                         "Тинькофф",
                                         reply_markup=kb.get_cansel_inline_button())
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 60))


@pm_router.message(Command("get_requisites"))
@pm_router.message(F.text.regexp(r"Текущие реквизиты|текущие реквизиты"))
async def get_requisites_handler(message: Message) -> None:
    """Получить текущие реквизиты"""
    user_id = message.from_user.id
    user = await get_user_by_tg_id(user_id)
    await message.reply(f"Ваши текущие реквизиты - {user.requisites}")


@pm_router.message(
    Command("statistics"),
    StatisticsViewingFilter(),
)
@pm_router.message(
    F.text.regexp(r"Статистика|статистика"),
    StatisticsViewingFilter(),
)
async def get_statistics_kb_handler(message: Message) -> None:
    """Отображает клавиатуру для статистики"""
    await message.reply("Статистика", reply_markup=kb.statistics)


@pm_router.message(
    Command("personal_statistics"),
    StatisticsViewingFilter(),
)
@pm_router.message(
    F.text.regexp(r"Личная статистика|личная статистика"),
    StatisticsViewingFilter(),
)
async def get_personal_statistics_handler(message: Message) -> None:
    """Получить личную статистику"""
    user_id, user_name = message.from_user.id, message.from_user.username
    user_count_lud_session = await get_count_lud_session_for_lud(user_id)
    user_total_deposit = await get_total_deposit_for_lud(user_id)
    user_profit = await get_profit_for_lud(user_id)

    message_answer = f"Статистика пользователя @{user_name}:\n\n" \
                     f"Количество лудо-сессий: {user_count_lud_session}\n\n" \
                     f"Депнуто денег: {user_total_deposit}\n\n" \
                     f"Профит: {user_profit}\n\n"

    await message.reply(message_answer)


@pm_router.message(
    Command("overall_statistics"),
    StatisticsViewingFilter(),
)
@pm_router.message(
    F.text.regexp(r"Общая статистика|общая статистика"),
    StatisticsViewingFilter(),
)
async def get_overall_statistics_handler(message: Message) -> None:
    """Получить общую статистику группы"""
    count_lud_session = await get_count_lud_session()
    total_deposit = await get_total_deposit()
    total_lost_cash = await get_total_lost_cash()

    message_answer = f"Общаяя статистика лудоманской группы:\n\n" \
                     f"Количество лудо-сессий: {count_lud_session}\n\n" \
                     f"Количество разыгранных денег: {total_deposit}\n\n" \
                     f"Количество потерянных денег из-за неверного подсчёта: {total_lost_cash}\n\n"

    await message.reply(message_answer)


@pm_router.message(
    Command("top_statistics"),
    StatisticsViewingFilter(),
)
@pm_router.message(
    F.text.regexp(r"Топ лудов|топ лудов"),
    StatisticsViewingFilter(),
)
async def get_top_statistics_handler(message: Message) -> None:
    """Получить топ игроков по полученным деньгам"""
    message_answer = ""
    top_statistics = await get_top_lud()

    for idx, (tg_name, sum_cash_received, count_sessions) in enumerate(top_statistics, start=1):
        message_answer += f"{idx}. Игрок - @{tg_name}, профит: {sum_cash_received}, за лудо-сессий: {count_sessions}\n"

    await message.reply(message_answer)


@pm_router.callback_query(F.data.casefold() == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback для инлайн кнопки отмена"""
    current_state = await state.get_state()

    if current_state is None:
        return

    await state.clear()
    await callback.answer("Отмена")
    await callback.message.delete()


@pm_router.callback_query(F.data.casefold() == "log_re_buy")
async def log_re_buy_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback для ввода лога re buy"""
    user_name = callback.from_user.username
    await callback.answer(f"Выбрано действие {LudActionOnSession.RE_BUY.value}")
    message_answer = await bot.send_message(chat_id=callback.message.chat.id,
                                            text=f"@{user_name} Введите сумму:",
                                            reply_markup=kb.get_cansel_inline_button_and_hot_re_buy())
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))
    await state.set_state(Form.re_buy)
    await callback.message.delete()


@pm_router.callback_query(F.data.casefold() == "log_cash_out")
async def log_cash_out_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback для ввода лога cash out"""
    user_name = callback.from_user.username
    await callback.answer(f"Выбрано действие {LudActionOnSession.CASH_OUT.value}")
    message_answer = await bot.send_message(chat_id=callback.message.chat.id,
                                            text=f"@{user_name} Введите сумму:",
                                            reply_markup=kb.get_cansel_inline_button())
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))
    await state.set_state(Form.cash_out)
    await callback.message.delete()


@pm_router.callback_query(kb.HotReBuyCallbackFactory.filter())
async def hot_re_buy_callback(callback: CallbackQuery,
                              state: FSMContext,
                              callback_data: kb.HotReBuyCallbackFactory) -> None:
    """Callback для горячих re buy кнопок"""
    user_name, user_id = callback.from_user.username, callback.from_user.id
    re_buy = int(callback_data.value)
    await state.update_data(re_buy=re_buy)
    re_buy_data = {
        "user_name": user_name,
        "user_id": user_id,
        "amount_cash": re_buy,
        "action": LudActionOnSession.RE_BUY
    }
    await add_action_handler(state, re_buy_data, callback)
    await callback.message.delete()


@pm_router.callback_query(kb.RightsCallbackFactory.filter())
async def rights_callback(callback: CallbackQuery,
                          state: FSMContext,
                          callback_data: kb.RightsCallbackFactory,
                          ) -> None:
    """Callback для выдачи/отбора прав"""
    state_data = await state.get_data()
    field, value = callback_data.field, callback_data.value
    tg_name = state_data["tg_name"]
    await update_admin_or_statistics_viewing(tg_name=tg_name, field=field, value=value)
    await callback.answer(f"Выбран пользователь: @{tg_name}\nПрава: {field}\nЗначение: {value}")
    await state.clear()
    await callback.message.delete()


@pm_router.callback_query(kb.HotUserCallbackFactory.filter())
async def hot_tg_name_callback(callback: CallbackQuery,
                               state: FSMContext,
                               callback_data: kb.HotUserCallbackFactory,
                               ) -> None:
    """Callback для горячих tg name кнопок"""
    user_name = callback.from_user.username
    tg_name = callback_data.value
    await state.update_data(tg_name=tg_name)
    keyboard = await get_next_inline_keyboard_after_tg_name(state=state)
    await callback.answer(f"Выбран пользователь @{tg_name}")
    await bot.send_message(chat_id=callback.message.chat.id,
                           text=f"Выбран пользователь @{tg_name}\n\n@{user_name} Выберите действе:",
                           reply_markup=keyboard)
    await callback.message.delete()


@pm_router.message(
    Command("rebuy"),
    SessionStartFilter(),
)
@pm_router.message(
    F.text.regexp(r"Rebuy|rebuy"),
    SessionStartFilter(),
)
async def re_buy_handler(message: Message, state: FSMContext) -> None:
    """Ввести новый re buy"""
    user_id, user_name = message.from_user.id, message.from_user.username
    message_answer = await message.reply(f"@{user_name} введите ваш ребай",
                                         reply_markup=kb.get_cansel_inline_button_and_hot_re_buy())
    await state.set_state(Form.re_buy)
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))


@pm_router.message(Form.re_buy)
async def update_re_buy_form(message: Message, state: FSMContext) -> None:
    """Форма для ввода нового re buy"""
    user_id, user_name, re_buy = message.from_user.id, message.from_user.username, message.text.strip()
    re_buy_int = await is_int_more_zero(re_buy)
    if re_buy_int:
        await state.update_data(re_buy=re_buy_int)
        re_buy_data = {
            "user_name": user_name,
            "user_id": user_id,
            "amount_cash": re_buy_int,
            "action": LudActionOnSession.RE_BUY
        }
        await add_action_handler(state, re_buy_data, message)
    else:
        message_answer = await message.answer(f"@{user_name} Ребай должен быть целым числом больше 0",
                                              reply_markup=kb.get_cansel_inline_button())
        create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))
        await state.set_state(Form.re_buy)


@pm_router.message(Form.cash_out)
async def update_cash_out_form(message: Message, state: FSMContext) -> None:
    """Форма для ввода cash out"""
    user_id, user_name, cash_out = message.from_user.id, message.from_user.username, message.text.strip()
    cash_out_int = await is_int_more_zero(cash_out)
    if cash_out_int is not None:
        await state.update_data(cash_out=cash_out_int)
        cash_out_data = {
            "user_name": user_name,
            "user_id": user_id,
            "amount_cash": cash_out_int,
            "action": LudActionOnSession.CASH_OUT
        }
        await add_action_handler(state, cash_out_data, message)
    else:
        message_answer = await message.answer(f"@{user_name} Cash out должен быть числом больше или равным 0",
                                              reply_markup=kb.get_cansel_inline_button())
        create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))
        await state.set_state(Form.cash_out)


@pm_router.message(Form.tg_name)
async def update_cash_out_form(message: Message, state: FSMContext) -> None:
    """Форма для ввода tg name"""
    user_name, tg_name = message.from_user.username, message.text.strip().replace("@", "")
    user = await get_user_by_tg_name(tg_name)
    if user:
        await state.update_data(tg_name=tg_name)
        keyboard = await get_next_inline_keyboard_after_tg_name(state=state)
        await message.answer(f"Выбран пользователь @{tg_name}\n\n@{user_name} Выберите действе:", reply_markup=keyboard)
    else:
        message_answer = await message.answer(f"@{user_name} такого tg name не существует в базе данных,"
                                              f" проверьте всё ли вы верно ввели, если ввод оказался верным возможно"
                                              f" человек сменил tg name, в таком случае попросите его снова прописать"
                                              f" команду /start в личных сообщениях бота, чтобы это исправить.",
                                              reply_markup=kb.get_cansel_inline_button())
        create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))
        await state.set_state(Form.tg_name)


@pm_router.message(Form.new_summ)
async def change_summ_form(message: Message, state: FSMContext) -> None:
    """Форма для ввода другой суммы в логе"""
    user_id, user_name, new_summ = message.from_user.id, message.from_user.username, message.text.strip()
    new_summ_int = await is_int_more_zero(new_summ)
    if new_summ_int is not None:
        state_data = await state.get_data()
        await state.update_data(change_summ=new_summ_int)
        text_message = state_data["message_text"]
        log_id, log_user_tg_name, log_action, log_summ = await parse_log_message(text_message)
        await update_row_from_log(log_id, new_summ_int)
        group_chat_log_message = f"Админ: @{user_name} изменил сумму {log_summ} -> {new_summ_int}\n" \
                                 f"в логе:\n\n@{log_user_tg_name} {log_action} {log_summ}"
        message_answer = f"Сумма лога №{log_id} изменена на {new_summ_int}"
        await message.answer(message_answer)
        await group_chat_log(group_chat_log_message)
        await state.clear()
    else:
        message_answer = await message.answer(f"@{user_name} сумма должна быть числом больше или равным 0",
                                              reply_markup=kb.get_cansel_inline_button())
        create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))
        await state.set_state(Form.new_summ)


@pm_router.message(
    Command("cash_out"),
    SessionStartFilter(),
)
@pm_router.message(
    F.text.regexp(r"Cash Out|cash out"),
    SessionStartFilter(),
)
async def cash_out_handler(message: Message, state: FSMContext) -> None:
    """Ввести cash out"""
    user_name, user_id = message.from_user.username, message.from_user.id
    message_answer = await message.reply(f"@{user_name} введите ваш cash out",
                                         reply_markup=kb.get_cansel_inline_button())
    await state.set_state(Form.cash_out)
    create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))


@pm_router.message(
    Command("admin"),
    AdminFilter(),
)
async def admin_panel_handler(message: Message) -> None:
    """Отображает клавиатуру админа"""
    user_name, user_id = message.from_user.username, message.from_user.id
    await message.reply(f"Добро пожаловать! Админ - @{user_name}", reply_markup=kb.admin)


@pm_router.callback_query(F.data.casefold() == "delete_log")
async def delete_log_callback(callback: CallbackQuery) -> None:
    """Callback для инлайн кнопки удалить лог.
    Id лога получается из сообщения разделением сообщения по символу '.' """
    message_text, user_name = callback.message.text, callback.from_user.username
    log_id, log_user_tg_name, log_action, log_summ = await parse_log_message(message_text)
    group_chat_log_message = f"Админ: @{user_name} удалил лог:\n\n@{log_user_tg_name} {log_action} {log_summ}"
    await delete_row_from_log(int(log_id))
    await callback.answer(f"Удалён лог №{log_id}")
    await group_chat_log(group_chat_log_message)
    await callback.message.delete()


@pm_router.callback_query(F.data.casefold() == "change_summ")
async def change_summ_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback для инлайн кнопки изменить сумму.
    Id лога получается из сообщения разделением сообщения по символу '.' """
    message_text = callback.message.text
    await state.update_data(message_text=message_text)
    await state.set_state(Form.new_summ)
    await callback.answer(f"Введите новую сумму лога")
    await callback.message.delete_reply_markup()


@pm_router.message(
    Command("session_log"),
    AdminFilter(),
    SessionStartFilter(),
)
@pm_router.message(
    F.text.regexp(r"Текущий лог сессии|текущий лог сессии"),
    AdminFilter(),
    SessionStartFilter(),
)
async def session_log_handler(message: Message) -> None:
    """Отображает лог текущей сессии с вариантами действий в виде инлайе кнопок"""
    session_logs = await get_log_current_session_deposit()
    if session_logs is None:
        await message.reply("В текущей сессии ещё ничего не произошло....", reply_markup=kb.admin)
    else:
        for log in session_logs:
            answer_message = f"{log.id}. Игрок: @{log.tg_name}, действие: {log.action.value}, сумма: {log.amount_cash}"
            message_answer = await message.answer(answer_message, reply_markup=kb.get_delete_and_change_log())
            create_task(remove_keyboard_after_delay(message_answer.chat.id, message_answer.message_id, 180))


@pm_router.message(
    Command("add_session_log"),
    AdminFilter(),
    SessionStartFilter(),
)
@pm_router.message(
    F.text.regexp(r"Добавить лог в текущую сессию|добавить лог в текущую сессию"),
    AdminFilter(),
    SessionStartFilter(),
)
async def session_log_handler(message: Message, state: FSMContext) -> None:
    """Отображает админу tg name топ 9 игроков по количеству сессий"""
    user_list = await get_count_lud_session_group_by_user_top_9()
    await state.update_data(pressed_button=message.text)
    await get_hot_tg_name(message=message, state=state, user_list=user_list)


@pm_router.message(
    Command("issue_rights"),
    AdminFilter(),
)
@pm_router.message(
    F.text.regexp(r"Права|права"),
    AdminFilter(),
)
async def issue_rights_handler(message: Message, state: FSMContext) -> None:
    """Отображает админу tg name 9 новых игроков"""
    user_list = await get_new_9_users()
    await state.update_data(pressed_button=message.text)
    await get_hot_tg_name(message=message, state=state, user_list=user_list)
