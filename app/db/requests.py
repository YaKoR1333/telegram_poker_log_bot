from datetime import datetime

from app.db.models import (
    User,
    LudSession,
    LudSessionLog,
    async_session,
    LudActionOnSession,
)
from sqlalchemy import (
    select,
    update,
    func,
    text,
)


# ----------------------------------------------------User request------------------------------------------------------

async def get_user_by_tg_id(tg_id: int) -> list:
    """Получение юзера по id в телеграмме"""
    async with async_session() as session:
        result = await session.scalar(select(User)
                                      .where(User.tg_id == tg_id))
        return result


async def get_user_by_tg_name(tg_name: str) -> list:
    """Получение юзера по id в телеграмме"""
    async with async_session() as session:
        result = await session.scalar(select(User)
                                      .where(User.tg_name == tg_name))
        return result


async def add_user(tg_id: int, tg_name: str) -> None:
    """Добавление юзера"""
    async with async_session() as session:
        session.add_all([User(tg_id=tg_id, tg_name=tg_name)])
        await session.commit()


async def update_requisites(tg_id: int, requisites: str) -> None:
    """Обновить реквизиты юзера"""
    async with async_session() as session:
        await session.execute(update(User).
                              values(requisites=requisites).
                              where(User.tg_id == tg_id))
        await session.commit()


async def update_admin_or_statistics_viewing(tg_name: str, field: str, value: bool) -> None:
    """Обновить реквизиты юзера"""
    async with async_session() as session:

        sql_query = text(f"""
        UPDATE users
        SET {field} = {value}
        WHERE tg_name = '{tg_name}'""")

        await session.execute(sql_query)

        await session.commit()


async def get_new_9_users() -> list:
    """Получение 9 новых юзеров"""
    async with async_session() as session:
        result = await session.execute(select(User.tg_name)
                                       .select_from(User)
                                       .limit(9)
                                       .order_by(User.id.desc())
                                       )
        return result


# ----------------------------------------------------LudSession request------------------------------------------------


async def add_lud_session(buy_in: int, chat_id: int) -> None:
    """Добавление сессии"""
    async with async_session() as session:
        session.add_all([LudSession(buy_in=buy_in,
                                    chat_id=chat_id)])
        await session.commit()


async def update_session_end_time(session_end_time: datetime) -> None:
    """Установить время завершения сессии"""
    async with async_session() as session:
        await session.execute(update(LudSession).
                              values(session_end_time=session_end_time).
                              where(LudSession.session_end_time == None))
        await session.commit()


async def update_session_buy_in(buy_in: int) -> None:
    """Установить новый buy in для сессии"""
    async with async_session() as session:
        await session.execute(update(LudSession).
                              values(buy_in=buy_in).
                              where(LudSession.session_end_time == None))
        await session.commit()


async def update_session_inaccuracy(inaccuracy: int) -> None:
    """Установить количество потерянных денег в сессии"""
    async with async_session() as session:
        await session.execute(update(LudSession).
                              values(inaccuracy=inaccuracy).
                              where(LudSession.session_end_time == None))
        await session.commit()


async def get_current_lud_session() -> list:
    """Получение текущей сессии"""
    async with async_session() as session:
        result = await session.scalar(select(LudSession)
                                      .where(LudSession.session_end_time == None))
        return result


async def get_count_lud_session() -> int:
    """Получение общего количества сессий"""
    async with async_session() as session:
        result = await session.scalar(select(func.count(LudSession.id)))
        return result


async def get_total_lost_cash() -> int:
    """Получение общего количества потерянных денег из-за неправильного подсчёта"""
    async with async_session() as session:
        result = await session.scalar(select(func.sum(func.abs(LudSession.inaccuracy))))
        return result


# ----------------------------------------------------LudSessionLog request--------------------------------------------


async def delete_row_from_log(row_id: int) -> None:
    """Удаляет строку лога из таблицы"""
    async with async_session() as session:
        sql_query = text(f"""
        DELETE FROM lud_session_log
        WHERE lud_session_log.id = {row_id}""")

        await session.execute(sql_query)

        await session.commit()


async def update_row_from_log(row_id: int, new_summ: int) -> None:
    """Обновляет сумму лога в таблице"""
    async with async_session() as session:
        sql_query = text(f"""
        UPDATE lud_session_log
        SET amount_cash = {new_summ}
        WHERE lud_session_log.id = {row_id}""")

        await session.execute(sql_query)

        await session.commit()


async def update_amount_cash_from_cash_out(user_id: int, lud_session_id: int, amount_cash: int) -> None:
    """Обновляет сумму CASH_OUT текущей сессии в логе у юзера"""
    async with async_session() as session:
        sql_query = text(f"""
        UPDATE lud_session_log
        SET amount_cash = {amount_cash}
        WHERE lud_session_id = {lud_session_id} AND user_id = {user_id} AND action = 'CASH_OUT'""")

        await session.execute(sql_query)

        await session.commit()


async def add_action_user_to_log(action_data: list) -> None:
    """Добавление строки/строк лога"""
    async with async_session() as session:
        session.add_all(action_data)
        await session.commit()


async def get_user_cash_out_in_session(user_id: int, session_id: int) -> int | None:
    """Получить cahs_out юзера в сессии"""
    async with async_session() as session:
        result = await session.scalar(select(LudSessionLog)
                                      .where(LudSessionLog.user_id == user_id)
                                      .where(LudSessionLog.lud_session_id == session_id)
                                      .where(LudSessionLog.action == LudActionOnSession.CASH_OUT))
        return result


async def get_current_inaccuracy_session() -> int:
    """Получение текущей погрешности(inaccuracy) сессии
     (Разница между суммой CASH_OUT всех игроков и суммой RE_BUY + buy_in сессии всех игроков)"""
    async with async_session() as session:
        sql_query = text(f"""
        SELECT 
            (SUM(CASE WHEN action = 'CASH_OUT' THEN amount_cash ELSE 0 END) - 
             SUM(CASE WHEN action = 'RE_BUY' THEN amount_cash ELSE 0 END) - 
             COUNT(CASE WHEN action = 'CASH_OUT' THEN 1 ELSE NULL END) * lud_sessions.buy_in) AS result
        FROM 
            lud_session_log
        JOIN lud_sessions on lud_session_log.lud_session_id = lud_sessions.id
        WHERE lud_sessions.session_end_time is NULL
        GROUP BY lud_sessions.buy_in
        """)

        result = await session.scalar(sql_query)

        return result


async def get_session_amount_data(session_id: int) -> list:
    """Получение данных по CASH_OUT, суммарному RE_BUY и профит для каждого юзера в сессии"""
    async with async_session() as session:
        sql_query = text(f"""
        SELECT 
            users.tg_id,
            COALESCE(co.amount_cash, 0) - 
            SUM(COALESCE(rb.amount_cash, 0)) - 
            lud_sessions.buy_in as profit
        FROM 
            (SELECT user_id, amount_cash, lud_session_id
             FROM lud_session_log 
             WHERE lud_session_id = {session_id} AND action = 'CASH_OUT') co
        LEFT JOIN 
            (SELECT user_id, amount_cash, lud_session_id
             FROM lud_session_log 
             WHERE lud_session_id = {session_id} AND action = 'RE_BUY') rb
        ON co.user_id = rb.user_id
        JOIN lud_sessions ON co.lud_session_id = lud_sessions.id
        JOIN users ON co.user_id = users.id
        GROUP BY users.tg_id, COALESCE(co.amount_cash, 0), lud_sessions.buy_in
        ORDER BY profit
        """)

        result = await session.execute(sql_query)

        return result


async def get_total_deposit() -> int:
    """Получение общего количества внесённых денег за все сессии"""
    async with async_session() as session:
        result = await session.scalar(select(func.coalesce(func.sum(LudSessionLog.amount_cash), 0) +
                                             select(func.sum(LudSession.buy_in))
                                             .select_from(LudSessionLog)
                                             .join(LudSession)
                                             .join(User)
                                             .where(LudSessionLog.action == 'CASH_OUT')
                                             )
                                      .select_from(LudSessionLog)
                                      .join(LudSession)
                                      .join(User)
                                      .where(LudSessionLog.action == 'RE_BUY')
                                      )
        return result


async def get_log_current_session_deposit() -> list:
    """Получение лога текущей сессии"""
    async with async_session() as session:
        result = await session.execute(select(User.tg_name,
                                              LudSessionLog.action,
                                              LudSessionLog.amount_cash,
                                              LudSessionLog.id)
                                       .join(LudSession)
                                       .join(User)
                                       .where(LudSession.session_end_time == None))
        return result


async def get_session_deposit(session_id: int) -> int:
    """Получение общего количества внесённых денег за сессию"""
    async with async_session() as session:
        result = await session.scalar(select(func.coalesce(func.sum(LudSessionLog.amount_cash), 0) +
                                             select(func.sum(LudSession.buy_in))
                                             .select_from(LudSessionLog)
                                             .join(LudSession)
                                             .join(User)
                                             .where(LudSessionLog.action == 'CASH_OUT')
                                             .where(LudSession.id == session_id)
                                             )
                                      .select_from(LudSessionLog)
                                      .join(LudSession)
                                      .join(User)
                                      .where(LudSessionLog.action == 'RE_BUY')
                                      .where(LudSession.id == session_id)
                                      )
        return result


async def get_count_lud_session_for_lud(tg_id: int) -> int:
    """Получение количества сессий у юзера"""
    async with async_session() as session:
        result = await session.scalar(select(func.count(LudSessionLog.user_id))
                                      .select_from(LudSessionLog)
                                      .join(User)
                                      .where(User.tg_id == tg_id)
                                      .where(LudSessionLog.action == 'CASH_OUT')
                                      )
        return result


async def get_count_lud_session_group_by_user_top_9() -> list:
    """Получение 9 топ юзеров по количеству сессий"""
    async with async_session() as session:
        result = await session.execute(select(User.tg_name, func.count(LudSessionLog.user_id))
                                       .select_from(LudSessionLog)
                                       .join(User)
                                       .where(LudSessionLog.action == 'CASH_OUT')
                                       .group_by(User.tg_name)
                                       .limit(9)
                                       .order_by(func.count(LudSessionLog.user_id).desc())
                                       )
        return result


async def get_total_deposit_for_lud(tg_id: int) -> int:
    """Получение суммарного депозита у юзера"""
    async with async_session() as session:
        result = await session.scalar(select(func.sum(LudSessionLog.amount_cash) +
                                             select(func.sum(LudSession.buy_in))
                                             .select_from(LudSessionLog)
                                             .join(LudSession)
                                             .join(User)
                                             .where(User.tg_id == tg_id)
                                             .where(LudSessionLog.action == 'CASH_OUT')
                                             )
                                      .select_from(LudSessionLog)
                                      .join(LudSession)
                                      .join(User)
                                      .where(User.tg_id == tg_id)
                                      .where(LudSessionLog.action == 'RE_BUY')
                                      )

        return result


# ----------------------------------------------------Payments request-------------------------------------------------


async def add_payments(payments_list: list) -> None:
    """Добавление платежей"""
    async with async_session() as session:
        session.add_all(payments_list)
        await session.commit()


async def get_profit_for_lud(tg_id: int) -> int:
    """Получение суммарного профита у юзера"""
    async with async_session() as session:
        sql_query = text(f"""
        SELECT 
            COALESCE(SUM(CASE WHEN user_role = 'collector' THEN cash_received END), 0) -
            COALESCE(SUM(CASE WHEN user_role = 'debtor' THEN cash_received END), 0) AS balance
        FROM (
            SELECT debtor_id AS user_id, cash_received, lud_session_id, 'debtor' AS user_role FROM payments
            UNION ALL
            SELECT collector_id AS user_id, cash_received, lud_session_id, 'collector' AS user_role FROM payments
        ) AS combined
        JOIN users ON combined.user_id = users.id
        WHERE users.tg_id = {tg_id}""")

        result = await session.scalar(sql_query)

        return result


async def get_top_lud() -> list:
    """Получение топа юзеров по профиту в порядке убывания"""
    async with async_session() as session:
        sql_query = text("""
        SELECT 
            users.tg_name,
            COALESCE(SUM(CASE WHEN user_role = 'collector' THEN cash_received END), 0) -
            COALESCE(SUM(CASE WHEN user_role = 'debtor' THEN cash_received END), 0) AS balance,
            COALESCE(session_log.session_count, 0) AS session_count
        FROM (
            SELECT debtor_id AS user_id, cash_received, lud_session_id, 'debtor' AS user_role FROM payments
            UNION ALL
            SELECT collector_id AS user_id, cash_received, lud_session_id, 'collector' AS user_role FROM payments
        ) AS combined
        JOIN users ON combined.user_id = users.id
        LEFT JOIN (
            SELECT user_id, COUNT(DISTINCT lud_session_id) AS session_count
            FROM lud_session_log
            GROUP BY user_id
        ) AS session_log
        ON combined.user_id = session_log.user_id
        GROUP BY users.tg_name, session_log.session_count
        ORDER BY balance DESC
        """)

        result = await session.execute(sql_query)

        return result
