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
		# Get driver info
		cur.execute("SELECT id, phone_number, city FROM users WHERE telegram_id=%s AND role='driver'",
					(driver_telegram_id,))
		driver_row = cur.fetchone()
		if not driver_row:
			await callback.answer("❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
			return

		driver_id = driver_row["id"]
		driver_phone = driver_row["phone_number"]
		driver_city = driver_row["city"]

		# Try to accept only if still pending
		cur.execute("""
			UPDATE ride_requests
			SET status='taken', taken_by_driver_id=%s
			WHERE id=%s AND status='pending'
		""", (driver_id, request_id))
		conn.commit()

		if cur.rowcount == 0:
			await callback.answer("❌ Bu buyurtma allaqachon boshqa haydovchi tomonidan qabul qilindi.", show_alert=True)
			return

		# Get passenger details
		cur.execute("""
			SELECT
				ride_requests.passenger_name,
				ride_requests.passenger_phone,
				ride_requests.from_city,
				ride_requests.to_city,
				ride_requests.date,
				users.telegram_id AS passenger_telegram_id
			FROM ride_requests
			JOIN users ON ride_requests.passenger_id = users.id
			WHERE ride_requests.id=%s
		""", (request_id,))
		ride = cur.fetchone()

	finally:
		cur.close()
		conn.close()

	# Notify driver
	await callback.message.edit_reply_markup()  # remove button
	await callback.message.answer(
		f"✅ Siz ushbu so'rovni qabul qildingiz!\n"
		f"👤 Yo'lovchi: {ride['passenger_name']} ({ride['passenger_phone']})\n"
		f"📍 {ride['from_city']} → {ride['to_city']}\n"
		f"📅 Sana: {ride['date']}\n\n"
		"☎️ Iltimos, yo'lovchi bilan bog'laning."
	)

	# Notify passenger with cancel option
	await callback.bot.send_message(
		chat_id=ride['passenger_telegram_id'],
		text=(
			f"🚖 Haydovchi so'rovingizni qabul qildi!\n\n"
			f"👨‍✈️ {driver_name}\n"
			f"📞 {driver_phone}\n"
			f"🏙 Shahar: {driver_city}\n"
			f"📍 {ride['from_city']} → {ride['to_city']}\n"
			f"📅 Sana: {ride['date']}\n\n"
			"☎️ Haydovchi bilan bog'lanishingiz mumkin.\n"
			"❌ Agar haydovchi bilan kelisha olmasangiz, bekor qilishingiz va boshqa haydovchini kutishingiz mumkin."
		),
		reply_markup=helper.cancel_driver_kb(request_id)
	)


@driver_router.callback_query(F.data.startswith("cancel_driver:"))
async def handle_cancel_driver(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	cancelled_driver_id = None
	cancelled_driver_telegram = None

	conn = get_connection()
	cur = conn.cursor(dictionary=True)
	try:
		# Find the driver who was just cancelled
		cur.execute("""
			SELECT r.taken_by_driver_id, u.telegram_id
			FROM ride_requests r
			LEFT JOIN users u ON r.taken_by_driver_id = u.id
			WHERE r.id=%s AND r.status='taken'
		""", (request_id,))
		row = cur.fetchone()
		if row:
			cancelled_driver_id = row["taken_by_driver_id"]
			cancelled_driver_telegram = row["telegram_id"]

		# Reset ride status
		cur.execute("""
			UPDATE ride_requests
			SET status='pending', taken_by_driver_id=NULL
			WHERE id=%s AND status='taken'
		""", (request_id,))
		conn.commit()

		# Fetch ride + passenger info again
		cur.execute("""
			SELECT r.id, r.passenger_name, r.passenger_phone, r.from_city, r.to_city, r.date,
				u.telegram_id AS passenger_telegram_id
			FROM ride_requests r
			JOIN users u ON r.passenger_id = u.id
			WHERE r.id=%s
		""", (request_id,))
		ride = cur.fetchone()

		# Get all drivers except cancelled one
		if cancelled_driver_id:
			cur.execute("""
				SELECT telegram_id, name
				FROM users
				WHERE role='driver' AND id != %s
			""", (cancelled_driver_id,))
		else:
			cur.execute("SELECT telegram_id, name FROM users WHERE role='driver'")
		drivers = cur.fetchall()

	finally:
		cur.close()
		conn.close()

	# Notify passenger
	await callback.message.edit_text(
		"❌ Siz haydovchini bekor qildingiz. Sizning so'rovingiz qayta faollashtirildi. 🚖 Boshqa haydovchilar tez orada sizga aloqaga chiqishadi."
	)

	# Notify the cancelled driver (nice UX)
	if cancelled_driver_telegram:
		try:
			await callback.bot.send_message(
				chat_id=cancelled_driver_telegram,
				text="⚠️ Yo‘lovchi sayohatingizni bekor qildi. So'rov qayta faollashtirildi."
			)
		except Exception:
			pass

	# Re-send ride details to other drivers
	for d in drivers:
		print(ride)
		print(d)
		try:
			await callback.bot.send_message(
				d["telegram_id"],
				f"🚕 Yangi so'rov!\n"
				f"👤 Yo'lovchi: {ride['passenger_name']}\n"
				f"📍 {ride['from_city']} → {ride['to_city']}\n"
				f"📅 Sana: {ride['date']}\n"
				f"💺 Telefon: {ride['passenger_phone']}\n",
				reply_markup=helper.accept_driver_kb(ride['id'])
			)
		except Exception:
			pass

