from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules import helper
from dictionary import MAIN_INTRO

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
	await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())
