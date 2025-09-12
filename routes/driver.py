from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import mysql.connector

from database.db import get_connection
from database.config import CITIES_TO_TASHKENT, REGISTER_AS_DRIVER
from modules import helper

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	route = State()
	phone_number = State()

# --- Route Start ---
@driver_router.message(F.text == REGISTER_AS_DRIVER)
async def start_driver_flow(message: Message, state: FSMContext):
	await state.set_state(DriverForm.route)
	await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))


@driver_router.message(DriverForm.route)
async def handle_route(message: Message, state: FSMContext):
	route = message.text.strip()
	if route not in CITIES_TO_TASHKENT:
		await message.answer(
			"❌ Noto‘g‘ri yo‘nalish. Iltimos, menyudan tanlang 👇",
			reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2)
		)
		return

	# Split into from/to cities
	from_city, to_city = route.split(" → ")
	await state.update_data(from_city=from_city, to_city=to_city)

	# move to next step
	await state.set_state(DriverForm.phone_number)
	await message.answer("📱 Iltimos, telefon raqamingizni ulashing 👇", reply_markup=helper.phone_request_kb())


@driver_router.message(DriverForm.phone_number, F.contact)
async def handle_phone(message: Message, state: FSMContext):
	phone_number = message.contact.phone_number if message.contact else message.text
	await state.update_data(phone_number=phone_number)
	data = await state.get_data()

	try:
		helper.save_driver(
			telegram_id=message.from_user.id,
			name=message.from_user.full_name,
			phone=phone_number,
			from_city=data["from_city"],
			to_city=data["to_city"]
		)
	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e.msg}", reply_markup=ReplyKeyboardRemove())
		await state.clear()
		return

	await message.answer(
		f"✅ Siz muvaffaqiyatli haydovchi sifatida ro‘yxatdan o‘tdingiz!\n\n"
		f"👤 Ism: {message.from_user.full_name}\n"
		f"📞 Telefon: {phone_number}\n"
		f"🏙 Qatnov yo'nalish: {data["from_city"]} → {data["to_city"]}",
		reply_markup=ReplyKeyboardRemove()
	)
	await state.clear()


# ---- Accept order ----
@driver_router.callback_query(F.data.startswith("accept:"))
async def handle_accept_order(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	driver_telegram_id = callback.from_user.id

	conn = get_connection()
	cur = conn.cursor(dictionary=True)

	try:
		# Get driver Info
		cur.execute(
			"""
				SELECT
					id,
					name,
					phone_number,
					from_city,
					to_city
				FROM users
				WHERE
					telegram_id=%s AND
					role='driver'
			""",
			(driver_telegram_id,)
		)
		driver_row = cur.fetchone()

		if driver_row: driver_id = driver_row["id"]
		else:
			await callback.answer("❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
			return

		# Accept ride if still pending
		cur.execute(
			"""
				UPDATE ride_requests
				SET
					status='taken',
					taken_by_driver_id=%s
				WHERE
					id=%s AND
					status='pending'
			""",
			(driver_id, request_id)
		)
		conn.commit()

		if cur.rowcount == 0:
			await callback.answer("❌ Bu buyurtma allaqachon boshqa haydovchi tomonidan qabul qilindi.", show_alert=True)
			return

		# Get passenger details
		cur.execute(
			"""
				SELECT
					ride_requests.passenger_name,
					ride_requests.passenger_phone,
					ride_requests.from_city,
					ride_requests.to_city,
					ride_requests.seats
					users.telegram_id AS passenger_telegram_id
				FROM ride_requests
				JOIN users ON ride_requests.passenger_id = users.id
				WHERE ride_requests.id=%s
			""",
			(request_id,)
		)
		ride = cur.fetchone()

		# Log notification for this driver (consistency with passenger flow)
		cur.execute(
			"""
				INSERT INTO ride_notifications (ride_id, driver_id)
				VALUES (%s, %s)
				ON DUPLICATE KEY UPDATE notified_at=NOW()
			""", (request_id, driver_id)
		)
		conn.commit()

	finally:
		cur.close()
		conn.close()

	# Notify driver
	await callback.message.edit_reply_markup()
	await callback.message.answer(
		f"✅ Siz ushbu so'rovni qabul qildingiz!\n"
		f"👤 Yo'lovchi: {ride['passenger_name']}\n"
		f"☎️ Telefon: {ride['passenger_phone']}\n"
		f"📍 Yo'nalish: {ride['from_city']} → {ride['to_city']}\n"
		f"💺 Kerakli o'rindiqlar: {ride['seats']}\n"
		"☎️ Iltimos, yo'lovchi bilan bog'laning."
	)

	# Notify passenger with cancel option
	await callback.bot.send_message(
		chat_id=ride['passenger_telegram_id'],
		text=(
			f"🚖 Haydovchi so'rovingizni qabul qildi!\n\n"
			f"👨‍✈️ Haydovchi: {driver_row["name"]}\n"
			f"📞 Telefon: {driver_row["phone_number"]}\n"
			"☎️ Haydovchi bilan bog'lanishingiz mumkin.\n"
			"❌ Agar haydovchi bilan kelisha olmasangiz, bekor qilishingiz va boshqa haydovchini kutishingiz mumkin."
		),
		reply_markup=helper.cancel_driver_kb(request_id)
	)


# ---- Cancel driver (passenger action) ----
@driver_router.callback_query(F.data.startswith("cancel_driver:"))
async def handle_cancel_driver(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	cancelled_driver_telegram = None

	conn = get_connection()
	cur = conn.cursor(dictionary=True)
	try:
		# Get cancelled driver
		cur.execute(
			"""
				SELECT
					ride_requests.taken_by_driver_id,
					users.telegram_id
				FROM ride_requests
				LEFT JOIN users ON ride_requests.taken_by_driver_id = users.id
				WHERE
					ride_requests.id=%s AND
					ride_requests.status='taken'
			""",
			(request_id,)
		)
		row = cur.fetchone()
		cancelled_driver_id = row["taken_by_driver_id"] if row else None
		cancelled_driver_telegram = row["telegram_id"] if row else None

		# Reset ride
		cur.execute(
			"""
				UPDATE ride_requests
				SET
					status='pending',
					taken_by_driver_id=NULL
				WHERE
					id=%s AND
					status='taken'
			""",
			(request_id,)
		)
		conn.commit()

		# Delete all old notifications for this ride
		cur.execute("DELETE FROM ride_notifications WHERE ride_id=%s", (request_id,))
		conn.commit()

		# Fetch ride
		cur.execute(
			"""
				SELECT
					ride_requests.id,
					ride_requests.passenger_name,
					ride_requests.passenger_phone,
					ride_requests.from_city,
					ride_requests.to_city,
					ride_requests.seats,
					users.telegram_id AS passenger_telegram_id
				FROM ride_requests
				JOIN users ON users.id = ride_requests.passenger_id
				WHERE ride_requests.id=%s
			""",
			(request_id,)
		)
		ride = cur.fetchone()

		# Get all drivers (optional: exclude cancelled driver)
		if cancelled_driver_id: cur.execute("SELECT id, telegram_id FROM users WHERE role='driver' AND id != %s", (cancelled_driver_id,))
		else: cur.execute("SELECT id, telegram_id FROM users WHERE role='driver'")
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
		except: pass

	# Re-send ride to all available drivers
	conn = get_connection()
	cur = conn.cursor(dictionary=True)
	for driver in drivers:
		try:
			await callback.bot.send_message(
				driver["telegram_id"],
				f"🚕 Yangi so'rov!\n"
				f"👤 Yo'lovchi: {ride['passenger_name']}\n"
				f"📍 Yo'nalish: {ride['from_city']} → {ride['to_city']}\n"
				f"💺 Kerakli o'rindiqlar: {ride['seats']}\n",
				reply_markup=helper.driver_accept_kb(ride['id'])
			)
			cur.execute(
				"""
					INSERT INTO ride_notifications (ride_id, driver_id)
					VALUES (%s, %s)
				""",
				(ride['id'], driver['id'])
			)
			conn.commit()
		except Exception as e: print(f"⚠️ Could not notify driver {driver['id']}: {e}")

	cur.close()
	conn.close()
