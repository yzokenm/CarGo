from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules import helper

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
	await message.answer(
		f"""
			🚖 Viloyatdan Toshkentga yoki Toshkentdan viloyatlarga safar qilmoqchimisiz? \n
			📲 CarGo botida buyurtma bering!
		""",
		reply_markup=helper.main_menu_kb()
	)
