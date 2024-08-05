import asyncio
import logging
import sys
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from app.handlers.pm_handlers import pm_router
from app.handlers.group_handlers import group_router
from app.db.models import async_main
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def main() -> None:
    await async_main()

    bot = Bot(API_TOKEN, parse_mode=ParseMode.HTML)
    dp.include_router(pm_router)
    dp.include_router(group_router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

