from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules import helper
from language import Lang

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
	await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())
