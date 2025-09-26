import logging
import asyncio
from aiogram import Bot, Dispatcher

from config import DB_CONFIG, BOT_TOKEN
from database.db import init_db

from modules import start
from modules import helper

# Load JSON dict once and "uz" by default
from settings import LANG_FILE
from language.language import Lang
Lang.load(LANG_FILE)
Lang.set("uz")

from routes import passenger, driver, common

logging.basicConfig(level=logging.INFO)

async def main():
	init_db()

	# Create bot and dispatcher
	bot = Bot(token=BOT_TOKEN)
	dp = Dispatcher()

	# Include routers from handlers
	dp.include_router(start.router)
	dp.include_router(common.common_router)
	dp.include_router(driver.driver_router)
	dp.include_router(passenger.passenger_router)

	# Set persistent menu
	await helper.set_bot_commands(bot)

	# Start polling
	await dp.start_polling(bot)

if __name__ == "__main__":
	asyncio.run(main())
