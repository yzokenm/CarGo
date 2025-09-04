from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
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
@driver_router.message(F.text == "🧑‍✈️ Taksida ishlash")
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


@driver_router.callback_query(F.data.startswith("accept:"))
async def handle_accept_order(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	driver_telegram_id = callback.from_user.id
	driver_name = callback.from_user.full_name

	conn = get_connection()
	cur = conn.cursor(dictionary=True)

	try:
		# Get driver ID
		cur.execute("SELECT id FROM users WHERE telegram_id=%s AND role='driver'", (driver_telegram_id,))
		driver_row = cur.fetchone()
		if not driver_row:
			await callback.answer("❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
			return

		driver_id = driver_row["id"]

		# Try to accept only if still pending
		cur.execute("""
			UPDATE ride_requests
			SET status='taken', taken_by_driver_id=%s
			WHERE id=%s AND status='pending'
		""", (driver_id, request_id))
		conn.commit()

		if cur.rowcount == 0:
			# No row updated → someone else already accepted
			await callback.answer("❌ Bu buyurtma allaqachon boshqa haydovchi tomonidan qabul qilindi. Iltimos keyingi so'rovni kuting!", show_alert=True)
			return

		# Get passenger details
		cur.execute("""
			SELECT passenger_name, passenger_phone, from_city, to_city, date
			FROM ride_requests WHERE id=%s
		""", (request_id,))
		ride = cur.fetchone()

	finally:
		cur.close()
		conn.close()

	# Notify driver
	await callback.message.edit_reply_markup()  # remove the button
	await callback.message.answer(
		f"✅ You accepted this order!\n"
		f"👤 Passenger: {ride['passenger_name']} ({ride['passenger_phone']})\n"
		f"📍 {ride['from_city']} → {ride['to_city']}\n"
		f"📅 Date: {ride['date']}\n\n"
		"☎️ Please contact the passenger directly."
	)
