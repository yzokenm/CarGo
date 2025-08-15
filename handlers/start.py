from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.menus import role_selection_kb

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
	await message.answer(
		"👋 Welcome to Shakhrikhan ↔ Tashkent Taxi Finder!\nPlease select your role:",
		reply_markup=role_selection_kb()
	)


