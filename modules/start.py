from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from modules import helper
from language.language import Lang
from settings import IMAGES_DIR

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
	photo = FSInputFile(IMAGES_DIR/"ad1.png")
	await message.answer_photo(
		photo=photo,
		caption=Lang.use("main_intro"),
		reply_markup=helper.main_menu_kb()
	)
