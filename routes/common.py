from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database.config import CITIES_TO_TASHKENT, CITIES_FROM_TASHKENT, NAVIGATE_BACK, NAVIGATE_HOME, REGISTER_AS_DRIVER
from modules import helper

common_router = Router()

# ---- Main Menu ----
@common_router.message(F.text == NAVIGATE_HOME)
async def go_main_menu(message: Message, state: FSMContext):
	await state.clear()
	await message.answer(
		f"""
			🚖 Viloyatdan Toshkentga yoki Toshkentdan viloyatlarga safar qilmoqchimisiz? \n
			📲 CarGo botida buyurtma bering!
		""",
		reply_markup=helper.main_menu_kb()
	)


# ---- Back Button ----
@common_router.message(F.text == NAVIGATE_BACK)
async def go_back(message: Message, state: FSMContext):
	current_state = await state.get_state()
	if not current_state:
		# Already at root → just show main menu
		await message.answer(
			f"""
				🚖 Viloyatdan Toshkentga yoki Toshkentdan viloyatlarga safar qilmoqchimisiz? \n
				📲 CarGo botida buyurtma bering!
			""",
			reply_markup=helper.main_menu_kb()
		)
		return

	# FSM states look like: DriverForm:route, PassengerForm:phone, etc.
	group, step = current_state.split(":")

	# Define back navigation rules
	if group == "DriverForm":
		if step == "phone_number":
			await state.set_state("DriverForm:route")
			await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))
		elif step == "route":
			await state.clear()
			await message.answer(
				f"""
					🚖 Viloyatdan Toshkentga yoki Toshkentdan viloyatlarga safar qilmoqchimisiz? \n
					📲 CarGo botida buyurtma bering!
				""",
				reply_markup=helper.main_menu_kb()
			)

	elif group == "PassengerForm":
		if step == "seats":
			await state.set_state("PassengerForm:route")
			await message.answer("🗺 Yo'nalishni tanlang:", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))
		elif step == "route":
			await state.clear()
			await message.answer(NAVIGATE_HOME, reply_markup=helper.main_menu_kb())

	else:
		# Default fallback
		await state.clear()
		await message.answer(NAVIGATE_HOME, reply_markup=helper.main_menu_kb())
