from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import mysql.connector
from database.db import get_connection
from database.config import CITIES
from handlers import helper

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	city = State()
	phone_number = State()

# Ensure user exists (driver)
def ensure_driver_and_get_id(telegram_id, name, phone, city):
	conn = get_connection()
	cur = conn.cursor()
	cur.execute(
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
	conn.commit()
	cur.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
	user_id = cur.fetchone()[0]
	cur.close()
	conn.close()
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
		ensure_driver_and_get_id(
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


# ---- Accept order ----
@driver_router.callback_query(F.data.startswith("accept:"))
async def handle_accept_order(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	driver_telegram_id = callback.from_user.id
	driver_name = callback.from_user.full_name

	conn = get_connection()
	cur = conn.cursor(dictionary=True)

	try:
		# Get driver ID
		cur.execute("SELECT id, phone_number, city FROM users WHERE telegram_id=%s AND role='driver'", (driver_telegram_id,))
		driver_row = cur.fetchone()
		if not driver_row:
			await callback.answer("❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
			return

		driver_id = driver_row["id"]

		# Accept ride if still pending
		cur.execute("""
			UPDATE ride_requests
			SET
				status='taken',
				taken_by_driver_id=%s
			WHERE
				id=%s AND
				status='pending'
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

		# Log notification for this driver (consistency with passenger flow)
		cur.execute("""
			INSERT INTO ride_notifications (ride_id, driver_id)
			VALUES (%s, %s)
			ON DUPLICATE KEY UPDATE notified_at=NOW()
		""", (request_id, driver_id))
		conn.commit()

	finally:
		cur.close()
		conn.close()

	# Notify driver
	await callback.message.edit_reply_markup()
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


# ---- Cancel diver (passenger action) ----
@driver_router.callback_query(F.data.startswith("cancel_driver:"))
async def handle_cancel_driver(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	cancelled_driver_telegram = None

	conn = get_connection()
	cur = conn.cursor(dictionary=True)
	try:
		# Get cancelled driver
		cur.execute("""
			SELECT
				ride_requests.taken_by_driver_id,
				users.telegram_id
			FROM ride_requests
			LEFT JOIN users ON ride_requests.taken_by_driver_id = users.id
			WHERE ride_requests.id=%s AND ride_requests.status='taken'
		""", (request_id,))
		row = cur.fetchone()
		cancelled_driver_id = row["taken_by_driver_id"] if row else None
		cancelled_driver_telegram = row["telegram_id"] if row else None

		# Reset ride
		cur.execute("""
			UPDATE ride_requests
			SET
				status='pending',
				taken_by_driver_id=NULL
			WHERE
				id=%s AND
				status='taken'
		""",
		(request_id,))
		conn.commit()

		# Fetch ride
		cur.execute("""
			SELECT
				ride_requests.id,
				ride_requests.passenger_name,
				ride_requests.passenger_phone,
				ride_requests.from_city,
				ride_requests.to_city,
				ride_requests.date,
				users.telegram_id AS passenger_telegram_id
			FROM ride_requests
			JOIN users ON users.id = ride_requests.passenger_id
			WHERE ride_requests.id=%s
		""", (request_id,))
		ride = cur.fetchone()

		# Get all drivers except cancelled one
		if cancelled_driver_id:
			cur.execute("SELECT id, telegram_id FROM users WHERE role='driver' AND id != %s", (cancelled_driver_id,))
		else:
			cur.execute("SELECT id, telegram_id FROM users WHERE role='driver'")
		drivers = cur.fetchall()

	finally:
		cur.close()
		conn.close()

	# Notify passenger
	await callback.message.edit_text("❌ Siz haydovchini bekor qildingiz. So'rovingiz qayta faollashtirildi. 🚖 Boshqa haydovchilar tez orada sizga aloqaga chiqishadi.")

	# Notify cancelled driver
	if cancelled_driver_telegram:
		try:
			await callback.bot.send_message(
				chat_id=cancelled_driver_telegram,
				text="⚠️ Yo‘lovchi sayohatingizni bekor qildi. So'rov qayta faollashtirildi."
			)
		except:
			pass

	# Re-send ride to unnotified drivers
	conn = get_connection()
	cur = conn.cursor(dictionary=True)
	for d in drivers:
		try:
			cur.execute("SELECT 1 FROM ride_notifications WHERE ride_id=%s AND driver_id=%s", (ride['id'], d['id']))
			already_notified = cur.fetchone()
			if not already_notified:
				await callback.bot.send_message(
					d["telegram_id"],
					f"🚕 Yangi so'rov!\n"
					f"👤 Yo'lovchi: {ride['passenger_name']}\n"
					f"📍 {ride['from_city']} → {ride['to_city']}\n"
					f"📅 Sana: {ride['date']}\n"
					f"💺 Telefon: {ride['passenger_phone']}\n",
					reply_markup=helper.accept_driver_kb(ride['id'])
				)
				cur.execute("""
					INSERT INTO ride_notifications (ride_id, driver_id)
					VALUES (%s, %s)
					ON DUPLICATE KEY UPDATE notified_at=NOW()
				""", (ride['id'], d['id']))
				conn.commit()
		except Exception as e:
			print(f"⚠️ Could not notify driver {d['id']}: {e}")
	cur.close()
	conn.close()
