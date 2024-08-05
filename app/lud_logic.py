import re

from collections import defaultdict

from app.db.requests import (
    update_session_inaccuracy,
    get_user_by_tg_id,
    get_current_lud_session,
    add_action_user_to_log,
    get_session_amount_data,
    get_user_cash_out_in_session,
    update_amount_cash_from_cash_out,
)

from app.db.models import (
    LudActionOnSession,
    LudSessionLog,
)


async def parse_log_message(log_message: str) -> tuple:
    """Парсит сообщение из лога для получения id, tg_name, action, amount_cash из строки лога"""
    log_id, log_user_tg_name, log_action, log_summ = \
        re.findall(r"(\d+). Игрок: @(\w+), действие: (\w+), сумма: (\w+)", log_message)[0]

    return log_id, log_user_tg_name, log_action, log_summ


async def is_int_more_zero(number: str) -> int | None:
    """Проверка того что строка может быть числом больше 0"""
    try:
        int_number = int(number)
        if int_number >= 0:
            return int_number
    except ValueError:
        return None


async def add_action(action_data: dict) -> str:
    """Добавляет строку с логом в БД, если пользователь сделал первый RE_BUY автоматически добавляется CASH_OUT"""
    user = await get_user_by_tg_id(action_data["user_id"])
    lud_session = await get_current_lud_session()
    amount_cash = action_data["amount_cash"]
    action_list = []
    user_cash_out = await get_user_cash_out_in_session(user.id, lud_session.id)

    if action_data["action"] == LudActionOnSession.RE_BUY:
        action_list.append(
            LudSessionLog(
                user_id=user.id,
                lud_session_id=lud_session.id,
                amount_cash=amount_cash,
                action=LudActionOnSession.RE_BUY
            )
        )

        if user_cash_out is None:
            action_list.append(
                LudSessionLog(
                    user_id=user.id,
                    lud_session_id=lud_session.id,
                    amount_cash=0,
                    action=LudActionOnSession.CASH_OUT
                )
            )

        message_answer = f"@{user.tg_name} ребай на {amount_cash}"

    elif action_data["action"] == LudActionOnSession.CASH_OUT and user_cash_out is not None:
        await update_amount_cash_from_cash_out(user_id=user.id,
                                               lud_session_id=lud_session.id,
                                               amount_cash=amount_cash)

        message_answer = f"@{user.tg_name} cash out {amount_cash} 💲 ➡️"
    else:
        action_list.append(
            LudSessionLog(
                user_id=user.id,
                lud_session_id=lud_session.id,
                amount_cash=amount_cash,
                action=LudActionOnSession.CASH_OUT
            )
        )
        message_answer = f"@{user.tg_name} cash out {amount_cash} 💲 ➡️"

    if action_list:
        await add_action_user_to_log(action_list)

    return message_answer


async def __get_cash_loss_win_data(lud_session_id: int) -> tuple[int, int]:
    """Определяет сколько денег проиграно и выиграно в текущей сессии"""
    lud_data = await get_session_amount_data(lud_session_id)  # FIXME повторный запрос
    cash_loss, cash_win = 0, 0
    for lud in lud_data:
        profit = lud.profit
        if profit < 0:
            cash_loss += profit
        elif profit > 0:
            cash_win += profit

    return cash_win, cash_loss


async def __get_lud_data_with_inaccuracy() -> dict[int: int]:
    """Получение словаря с данным по пользователям и их профитом в текущей сессии с учётом погрешности"""
    lud_session = await get_current_lud_session()
    lud_data = await get_session_amount_data(lud_session.id)
    cash_win, cash_loss = await __get_cash_loss_win_data(lud_session.id)
    inaccuracy = cash_win + cash_loss
    await update_session_inaccuracy(inaccuracy)
    lud_data_with_inaccuracy = {}

    if inaccuracy > 0:
        for user_id, profit in lud_data:
            profit = profit
            if profit > 0:
                lud_data_with_inaccuracy[user_id] = profit + round(profit / cash_win * -inaccuracy)
            else:
                lud_data_with_inaccuracy[user_id] = profit

    elif inaccuracy < 0:
        for user_id, profit in lud_data:
            if profit < 0:
                lud_data_with_inaccuracy[user_id] = profit + round(profit / cash_loss * -inaccuracy)
            else:
                lud_data_with_inaccuracy[user_id] = profit

    else:
        for user_id, profit in lud_data:
            lud_data_with_inaccuracy[user_id] = profit

    return lud_data_with_inaccuracy


async def get_payments_and_debtors_data() -> tuple[defaultdict[dict], defaultdict[dict]]:
    """Получение словарей с коллекторами и должниками"""
    lud_data_with_inaccuracy = await __get_lud_data_with_inaccuracy()
    collectors_data = defaultdict(dict)
    debtors_data = defaultdict(dict)

    def update_collectors_and_debtors_data(debtor_dict: dict, collector_dict: dict) -> None:
        if collectors_data[max_minus_lud] is not None:
            collectors_data[max_minus_lud].update(debtor_dict)
            debtors_data[max_plus_lud].update(collector_dict)
        else:
            collectors_data[max_minus_lud] = debtor_dict
            debtors_data[max_plus_lud] = collector_dict

    while len(lud_data_with_inaccuracy) > 1:
        max_minus_lud, max_minus = list(lud_data_with_inaccuracy.items())[0]
        max_plus_lud, max_plus = list(lud_data_with_inaccuracy.items())[-1]

        if -max_minus < max_plus:

            lud_data_with_inaccuracy[max_plus_lud] += lud_data_with_inaccuracy[max_minus_lud]
            debtor, collector = {max_plus_lud: -max_minus}, {max_minus_lud: -max_minus}
            update_collectors_and_debtors_data(debtor, collector)
            del lud_data_with_inaccuracy[max_minus_lud]

        elif -max_minus > max_plus:
            lud_data_with_inaccuracy[max_minus_lud] += lud_data_with_inaccuracy[max_plus_lud]
            debtor, collector = {max_plus_lud: max_plus}, {max_minus_lud: max_plus}
            update_collectors_and_debtors_data(debtor, collector)
            del lud_data_with_inaccuracy[max_plus_lud]

        else:
            debtor, collector = {max_plus_lud: max_plus}, {max_minus_lud: max_plus}
            update_collectors_and_debtors_data(debtor, collector)
            del lud_data_with_inaccuracy[max_minus_lud]
            del lud_data_with_inaccuracy[max_plus_lud]

    return collectors_data, debtors_data
