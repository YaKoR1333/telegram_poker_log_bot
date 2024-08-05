import datetime

from enum import Enum as En

from typing import Annotated
from sqlalchemy import BigInteger, ForeignKey, func, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from app.config import postgres_url

engine = create_async_engine(postgres_url, echo=True)

async_session = async_sessionmaker(engine)

intpk = Annotated[int, mapped_column(primary_key=True)]


class LudActionOnSession(En):
    RE_BUY = "RE_BUY"
    CASH_OUT = "CASH_OUT"


class Base(AsyncAttrs, DeclarativeBase):
    pass


class LudSessionLog(Base):
    __tablename__ = "lud_session_log"

    id: Mapped[intpk]
    user_id = mapped_column(ForeignKey("users.id"))
    lud_session_id = mapped_column(ForeignKey("lud_sessions.id"))
    action = mapped_column(Enum(LudActionOnSession))
    amount_cash: Mapped[int]


class Payments(Base):
    __tablename__ = "payments"

    id: Mapped[intpk]
    debtor_id = mapped_column(ForeignKey("users.id"))
    collector_id = mapped_column(ForeignKey("users.id"))
    lud_session_id = mapped_column(ForeignKey("lud_sessions.id"))
    cash_received: Mapped[int]
    debtor = relationship("User", foreign_keys=[debtor_id])
    collector = relationship("User", foreign_keys=[collector_id])
    lud_session = relationship("LudSession", foreign_keys=[lud_session_id])


class User(Base):
    __tablename__ = "users"

    id: Mapped[intpk]
    tg_id = mapped_column(BigInteger)
    tg_name: Mapped[str]
    requisites: Mapped[str | None]
    admin: Mapped[bool] = mapped_column(default=False)
    statistics_viewing: Mapped[bool] = mapped_column(default=False)
    lud_sessions = relationship("LudSession", secondary="lud_session_log", back_populates="users")


class LudSession(Base):
    __tablename__ = "lud_sessions"

    id: Mapped[intpk]
    buy_in: Mapped[int]
    session_start_time: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    session_end_time: Mapped[datetime.datetime | None]
    chat_id = mapped_column(BigInteger)
    inaccuracy: Mapped[int | None]
    users = relationship("User", secondary="lud_session_log", back_populates="lud_sessions")


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
