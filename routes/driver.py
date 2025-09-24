import re

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import mysql.connector

from database.db import get_connection
from dictionary import CITIES_TO_TASHKENT, REGISTER_AS_DRIVER, phone_number_regEx, INVALID_COMMAND, TERMS_AND_CONDITIONS_MSG, TERMS_AND_CONDITIONS_TEXT
from modules import helper

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	terms_and_conditions = State()
	route = State()
	phone = State()

# --- Route Start ---
@driver_router.message(F.text == REGISTER_AS_DRIVER)
async def start_driver_flow(message: Message, state: FSMContext):
	await state.set_state(DriverForm.terms_and_conditions)
	await message.answer(TERMS_AND_CONDITIONS_MSG, reply_markup=helper.build_kb([TERMS_AND_CONDITIONS_TEXT], per_row=2), parse_mode="HTML")



@driver_router.message(DriverForm.terms_and_conditions)
async def handle_terms(message: Message, state: FSMContext):
	if message.text.strip() == TERMS_AND_CONDITIONS_TEXT:
		await state.update_data(is_contract_signed=True)
		await state.set_state(DriverForm.route)
		await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))
	else: await message.answer(INVALID_COMMAND, reply_markup=helper.build_kb([TERMS_AND_CONDITIONS_TEXT], per_row=2), parse_mode="HTML")

@driver_router.message(DriverForm.route)
async def handle_route(message: Message, state: FSMContext):
	selected_route = message.text.strip()
	if selected_route not in CITIES_TO_TASHKENT:
		await message.answer(INVALID_COMMAND, reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2), parse_mode="HTML")
		await state.set_state(DriverForm.route)
		return

	# Split into from/to cities
	from_city, to_city = selected_route.split(" → ")
	await state.update_data(from_city=from_city, to_city=to_city)

	# Ask for phone number
	await state.set_state(DriverForm.phone)
	await message.answer(
		f"🚖 {from_city} → {to_city} yo'nalishi\n\n"
		f"📞 Ro'yxatdan o'tish uchun telefon raqamingizni to'liq yuboring:\n\n"
		"❗️ Namuna: +998901234567",
		reply_markup=helper.cancel_request_kb()
	)


@driver_router.message(DriverForm.phone)
async def handle_phone(message: Message, state: FSMContext):
	phone = message.text.strip()

	if not re.match(phone_number_regEx, phone):
		await message.answer("❌ Telefon formati noto'g'i. Namuna: +998901234567")
		return

	await state.update_data(phone=phone)
	data = await state.get_data()

	try:
		result = helper.save_driver(
			telegram_id=message.from_user.id,
			name=message.from_user.full_name,
			phone=phone,
			from_city=data["from_city"],
			to_city=data["to_city"],
			is_contract_signed=data["is_contract_signed"]
		)

		if result == "driver_exist":
			await message.answer("🚖 Siz ro'yxatdan o'tib bo'lgansiz!\n\n ❗Takroriy ro'yxatdan o'tish talab qilinmaydi.")
			return
		else:
			await message.answer(
				f"✅ Siz muvaffaqiyatli haydovchi sifatida ro'yxatdan o'tdingiz!\n\n"
				f"👤 Ism: {message.from_user.full_name}\n"
				f"📞 Telefon: {phone}\n"
				f"🏙 Qatnov yo'nalish: {data["from_city"]} → {data["to_city"]}",
				reply_markup=ReplyKeyboardRemove()
			)

	except mysql.connector.Error as e: await message.answer(f"❌ Database error: {e.msg}", reply_markup=ReplyKeyboardRemove())



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
					drivers.id,
					drivers.from_city,
					drivers.to_city,
					users.name,
					users.phone
				FROM drivers
				JOIN users ON users.id = drivers.user_id
				WHERE users.telegram_id=%s
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
					ride_requests.seats,
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
		f"🎉 So'rov qabul qilindi!\n\n"
		f"🧑‍💼 Yo'lovchi: {ride['passenger_name']}\n"
		f"☎️ Telefon: {ride['passenger_phone']}\n"
		f"📍 Yo'nalish: {ride['from_city']} → {ride['to_city']}\n"
		f"💺 Kerakli o'rindiqlar: {ride['seats']}\n\n"
		"🤝 Iltimos, yo'lovchi bilan bog'laning!"
	)

	# Notify passenger with cancel option
	await callback.bot.send_message(
		chat_id=ride['passenger_telegram_id'],
		text=(
			f"✅ Haydovchi so'rovingizni qabul qildi!\n\n"
			f"👨‍✈️ Haydovchi: {driver_row["name"]}\n"
			f"📞 Telefon: {driver_row["phone"]}\n\n"
			"📲 Haydovchi bilan bog'lanishingiz mumkin.\n"
			"❌ Agar haydovchi bilan kelisha olmasangiz, <b>Bekor qilish</b> tugmasini bosing va boshqa haydovchini kutishingiz mumkin."
		),
		reply_markup=helper.cancel_driver_kb(request_id),
		parse_mode="HTML"
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
				JOIN drivers ON drivers.id = ride_requests.taken_by_driver_id
				JOIN users ON users.id = drivers.user_id
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
		if cancelled_driver_id:
			cur.execute("""
				SELECT
					drivers.id,
					users.telegram_id
				FROM drivers
				JOIN users ON users.id = drivers.user_id
				WHERE drivers.id != %s
			""", (cancelled_driver_id,))
		else:
			cur.execute("""
				SELECT
					drivers.id,
					users.telegram_id
				FROM drivers
				JOIN users ON users.id = drivers.user_id
			""")
		drivers = cur.fetchall()


	finally:
		cur.close()
		conn.close()

	# Notify passenger
	await callback.message.edit_text("❌ Siz haydovchini bekor qildingiz.\n\n 🔄 So'rovingiz qayta faollashtirildi. \n\n ⏳ Boshqa haydovchilar tez orada sizga aloqaga chiqishadi.")

	# Notify cancelled driver
	if cancelled_driver_telegram:
		try:
			await callback.bot.send_message(
				chat_id=cancelled_driver_telegram,
				text="⚠️ Yo‘lovchi so'rovni bekor qildi. \n\n ⏳ So'rov qayta faollashtirildi."
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
