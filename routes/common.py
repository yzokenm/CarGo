from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from dictionary import	CITIES_TO_TASHKENT,	CITIES_FROM_TASHKENT, NAVIGATE_BACK, NAVIGATE_HOME,	REGISTER_AS_DRIVER,	MAIN_INTRO,	CANCEL_REQUEST,	DIRECTIONS
from modules import helper

common_router = Router()

# ---- Main Menu Button ----
@common_router.message(F.text == NAVIGATE_HOME)
async def go_main_menu(message: Message, state: FSMContext):
	await state.clear()
	await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())


# ---- Back Button ----
@common_router.message(F.text == NAVIGATE_BACK)
async def go_back(message: Message, state: FSMContext):
	current_state = await state.get_state()
	if not current_state:
		# Already at root → just show main menu
		await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())
		return

	# FSM states look like: DriverForm:route, PassengerForm:phone, etc.
	group, step = current_state.split(":")

	# Define back navigation rules
	if group == "DriverForm":
		if step == "phone":
			await state.set_state("DriverForm:route")
			await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))
		elif step == "route":
			await state.clear()
			await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())

	elif group == "PassengerForm":
		if step == "seats":
			await state.set_state("PassengerForm:route")
			await message.answer("🗺 Yo'nalishni tanlang:", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))
		elif step == "route":
			await state.set_state("PassengerForm:direction")
			await message.answer(NAVIGATE_BACK, reply_markup=helper.build_kb(DIRECTIONS, per_row=2))
		elif step == "direction":
			await state.clear()
			await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())

	else:
		# Default fallback
		await state.clear()
		await message.answer(NAVIGATE_HOME, reply_markup=helper.main_menu_kb())


# Cancel Request Button
@common_router.message(F.text == CANCEL_REQUEST)
async def cancel_request(message: Message, state: FSMContext):
	current_state = await state.get_state()
	group, step = current_state.split(":")

	if group == "PassengerForm":
		if step == "phone":
			data = await state.get_data()
			direction = data.get("direction")

			if direction == "🚖 Viloyatdan → Toshkentga": direction_cities = CITIES_TO_TASHKENT
			elif direction == "🚖 Toshkentdan → Viloyatga": direction_cities = CITIES_FROM_TASHKENT
			else:
				# fallback to main menu if no direction is stored
				await state.clear()
				await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())
				return

			await state.set_state("PassengerForm:route")
			await message.answer("Kerakli yo’nalishni tanlang 👇", reply_markup=helper.build_kb(direction_cities, per_row=2))

	if group == "DriverForm":
		if step == "phone":
			await message.answer(MAIN_INTRO, reply_markup=helper.main_menu_kb())
			return
