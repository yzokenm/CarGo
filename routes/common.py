from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from modules import helper
from language import Lang

from pathlib import Path

common_router = Router()

# ---- Main Menu Button ----
@common_router.message(F.text == Lang.use("navigate_home"))
async def go_main_menu(message: Message, state: FSMContext):
	await state.clear()
	await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())


# ---- Back Button ----
@common_router.message(F.text == Lang.use("navigate_back"))
async def go_back(message: Message, state: FSMContext):
	current_state = await state.get_state()
	if not current_state:
		# Already at root → just show main menu
		await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())
		return

	# FSM states look like: DriverForm:route, PassengerForm:phone, etc.
	group, step = current_state.split(":")

	# Define back navigation rules
	if group == "DriverForm":
		if step == "phone":
			await state.set_state("DriverForm:route")
			await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=helper.build_kb(Lang.use("cities_to_tashkent"), per_row=2))
		elif step == "route":
			await state.set_state("DriverForm:terms_and_conditions")
			await message.answer(Lang.use("main_intro"), reply_markup=helper.build_kb([Lang.use("terms_and_conditions")], per_row=2))
		elif step == "terms_and_conditions":
			await state.clear()
			await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())

	elif group == "PassengerForm":
		if step == "seats":
			await state.set_state("PassengerForm:route")
			await message.answer("🗺 Yo'nalishni tanlang:", reply_markup=helper.build_kb(Lang.use("cities_to_tashkent"), per_row=2))
		elif step == "route":
			await state.set_state("PassengerForm:direction")
			await message.answer(Lang.use("navigate_back"), reply_markup=helper.build_kb(Lang.use("directions"), per_row=2))
		elif step == "direction":
			await state.clear()
			await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())

	else:
		# Default fallback
		await state.clear()
		await message.answer(Lang.use("navigate_home"), reply_markup=helper.main_menu_kb())


BASE_DIR = Path(__file__).resolve().parent.parent
photo_path = BASE_DIR / "images" / "Logo.jpg"
# ---- Contact Us Button ----
@common_router.message(F.text == Lang.use("contact_us"))
async def contact_us(message: Message):
	photo = FSInputFile(photo_path)
	await message.answer_photo(photo=photo, caption=Lang.use("contact_us_msg"))

@common_router.message(F.text == Lang.use("how_it_works"))
async def contact_us(message: Message):
	photo = FSInputFile(photo_path)
	await message.answer_photo(photo=photo, caption=Lang.use("how_it_works_msg"), parse_mode="HTML")


# Cancel Request Button
@common_router.message(F.text == Lang.use("cancel_request"))
async def cancel_request(message: Message, state: FSMContext):
	current_state = await state.get_state()
	group, step = current_state.split(":")

	if group == "PassengerForm":
		if step == "phone":
			data = await state.get_data()
			direction = data.get("direction")

			if direction == "🚖 Viloyatdan → Toshkentga": direction_cities = Lang.use("cities_to_tashkent")
			elif direction == "🚖 Toshkentdan → Viloyatga": direction_cities = Lang.use("cities_from_tashkent")
			else:
				# fallback to main menu if no direction is stored
				await state.clear()
				await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())
				return

			await state.set_state("PassengerForm:route")
			await message.answer("Kerakli yo’nalishni tanlang 👇", reply_markup=helper.build_kb(direction_cities, per_row=2))

	if group == "DriverForm":
		if step == "phone":
			await state.clear()
			await message.answer(Lang.use("main_intro"), reply_markup=helper.main_menu_kb())
			return
