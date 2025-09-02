from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import mysql.connector
from database.config import DB_CONFIG, CITIES
from database.db import get_connection
from handlers import helper

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	city = State()
	phone_number = State()

# Ensure user exists (driver)
def ensure_driver_and_get_id(telegram_id, name, phone, city):
	connection = get_connection()
	cursor = connection.cursor()
	cursor.execute(
		"""
		INSERT INTO users (telegram_id, role, name, phone_number, city)
		VALUES (%s, 'driver', %s, %s, %s)
		ON DUPLICATE KEY UPDATE
			role='driver',
			name=VALUES(name),
			phone_number=VALUES(phone_number),
			city=VALUES(city)
		""",
		(telegram_id, name, phone, city)
	)
	connection.commit()
	cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
	user_id = cursor.fetchone()[0]
	cursor.close()
	connection.close()
	return user_id


# --- Route Start ---
@driver_router.message(F.text == "🧑‍✈️ Register as Driver")
async def start_driver_flow(message: Message, state: FSMContext):
	await state.set_state(DriverForm.city)
	kb = helper.build_kb(CITIES, per_row=2)
	await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=kb)

@driver_router.message(DriverForm.city)
async def handle_city(message: Message, state: FSMContext):
	city = message.text.strip()
	if city not in CITIES:
		kb = helper.build_kb(CITIES, per_row=2)
		await message.answer("❌ Noto‘g‘ri shahar. Iltimos, menyudagi shaharni tanlang:", reply_markup=kb)
		return

	await state.update_data(city=city)
	await state.set_state(DriverForm.phone_number)
	await message.answer("📱 Iltimos, telefon raqamingizni ulashing:", reply_markup=helper.phone_request_kb())


@driver_router.message(DriverForm.phone_number, F.contact)
async def handle_phone(message: Message, state: FSMContext):
	phone_number = message.contact.phone_number if message.contact else message.text
	await state.update_data(phone_number=phone_number)

	data = await state.get_data()
	city = data["city"]

	try:
		driver_id = ensure_driver_and_get_id(
			telegram_id=message.from_user.id,
			name=message.from_user.full_name,
			phone=phone_number,
			city=city
		)
	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e.msg}", reply_markup=ReplyKeyboardRemove())
		await state.clear()
		return

	await message.answer(
		f"✅ Siz muvaffaqiyatli haydovchi sifatida ro‘yxatdan o‘tdingiz!\n\n"
		f"👤 Ism: {message.from_user.full_name}\n"
		f"📞 Telefon: {phone_number}\n"
		f"🏙 Shahar: {city}",
		reply_markup=ReplyKeyboardRemove()
	)
	await state.clear()
