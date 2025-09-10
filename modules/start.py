from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from menu.menus import role_selection_kb

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
	await message.answer(
		"-Men CarGo tanlayman! Viloyatga ketmoqchimizsiz yoki viloyatdan poytaxtga kelmoqchmisiz, unda CarGo sizga yordam beradi. CarGo - Harakatdagi qulaylik🧡",
		reply_markup=role_selection_kb()
	)
